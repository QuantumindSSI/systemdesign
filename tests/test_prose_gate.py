"""Tests for tools/prose_gate.py.

A gate is only worth running if it fails on the thing it claims to catch
and stays quiet on the thing it claims to allow. Both directions are
tested here, because a gate that never fires and a gate that fires on
everything are equally useless and look the same from a passing build.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
)

import prose_gate  # noqa: E402


def rules(text):
    """Rule ids fired by one document, in order."""
    return [violation.rule for violation in prose_gate.check_text("t.md", text)]


def wrap(body):
    """Put a body below an editorial marker, the way a post is shaped."""
    return "# Heading\n\n> audit note\n\n---\n\n" + body


class TestEditorialSplit(unittest.TestCase):
    def test_audit_header_is_not_checked(self):
        text = "# Heading\n\n> And an em dash \u2014 here.\n\n---\n\nClean copy.\n"
        self.assertEqual(rules(text), [])

    def test_body_is_checked(self):
        self.assertEqual(rules(wrap("An em dash \u2014 here.\n")), ["P1"])

    def test_a_file_with_no_marker_is_checked_entirely(self):
        self.assertEqual(rules("An em dash \u2014 here.\n"), ["P1"])

    def test_line_numbers_point_into_the_real_file(self):
        text = wrap("Line one.\nAn em dash \u2014 here.\n")
        violation = prose_gate.check_text("t.md", text)[0]
        self.assertEqual(text.split("\n")[violation.line - 1],
                         "An em dash \u2014 here.")


class TestEmDashes(unittest.TestCase):
    def test_em_dash_fails(self):
        self.assertIn("P1", rules(wrap("A sentence \u2014 with a dash.\n")))

    def test_en_dash_and_hyphen_pass(self):
        self.assertEqual(rules(wrap("A range 1\u20132 and a co-author.\n")), [])

    def test_em_dash_inside_a_fenced_block_is_ignored(self):
        body = "Prose.\n\n```\ncode \u2014 with a dash\n```\n\nMore prose.\n"
        self.assertEqual(rules(wrap(body)), [])

    def test_em_dash_inside_an_inline_span_is_ignored(self):
        self.assertEqual(rules(wrap("The flag `--x \u2014 y` is fine.\n")), [])

    def test_em_dash_in_a_quotation_still_fails(self):
        """A quoted dash is still a dash in front of a reader."""
        self.assertIn(
            "P1", rules(wrap('They wrote "deeper \u2014 8x deeper" in it.\n'))
        )


class TestLeadingConjunctions(unittest.TestCase):
    def test_line_opening_with_and_fails(self):
        self.assertIn("P2", rules(wrap("And then it failed.\n")))

    def test_mid_sentence_conjunction_passes(self):
        self.assertEqual(rules(wrap("It ran and then it failed.\n")), [])

    def test_after_a_full_stop_fails(self):
        self.assertIn("P2", rules(wrap("It ran. But it failed.\n")))

    def test_after_a_question_mark_fails(self):
        self.assertIn("P2", rules(wrap("Did it run? So we checked.\n")))

    def test_heading_opening_with_a_conjunction_fails(self):
        self.assertIn("P2", rules(wrap("## But what about cost\n")))

    def test_list_item_opening_with_a_conjunction_fails(self):
        self.assertIn("P2", rules(wrap("- Because it is cheaper.\n")))

    def test_bold_opening_with_a_conjunction_fails(self):
        self.assertIn("P2", rules(wrap("**So** we measured it.\n")))

    def test_every_listed_conjunction_is_caught(self):
        for word in prose_gate.CONJUNCTIONS:
            self.assertIn("P2", rules(wrap(f"{word} it happened.\n")), word)

    def test_a_word_merely_starting_with_a_conjunction_passes(self):
        self.assertEqual(rules(wrap("Android shipped it.\n")), [])
        self.assertEqual(rules(wrap("Sorting is the cost.\n")), [])
        self.assertEqual(rules(wrap("Butler wrote it.\n")), [])

    def test_conjunction_inside_a_fenced_block_is_ignored(self):
        body = "Prose.\n\n```\nBut this is code.\n```\n\nMore prose.\n"
        self.assertEqual(rules(wrap(body)), [])

    def test_a_decimal_point_does_not_start_a_sentence(self):
        """The dot in 1.5 is followed by a digit, so nothing begins there."""
        self.assertEqual(rules(wrap("It grew 1.5 Or so we thought.\n")), [])

    def test_a_real_full_stop_before_a_conjunction_still_fires(self):
        self.assertIn("P2", rules(wrap("It grew by 1.5. Or so we thought.\n")))


class TestAntithesis(unittest.TestCase):
    def test_not_x_comma_its_y_fails(self):
        self.assertIn("P3", rules(wrap("It is not small, it's zero.\n")))

    def test_not_x_comma_y_full_stop_fails(self):
        self.assertIn("P3", rules(wrap("Not small, zero.\n")))

    def test_it_is_not_x_it_is_y_fails(self):
        self.assertIn(
            "P3", rules(wrap("It is not a bug. It is a constraint.\n"))
        )

    def test_not_because_x_because_y_fails(self):
        self.assertIn(
            "P3",
            rules(wrap("We chose it. Not because it is best. Because it is safe.\n")),
        )

    def test_rather_than_phrasing_passes(self):
        self.assertEqual(
            rules(wrap("The value is zero rather than merely small.\n")), []
        )

    def test_ordinary_negation_passes(self):
        self.assertEqual(
            rules(wrap("This does not change the quadratic term at all.\n")), []
        )

    def test_a_long_negated_clause_is_not_swept_up(self):
        body = (
            "This is not the regime the paper concerns, and the article "
            "says so at the point of use.\n"
        )
        self.assertEqual(rules(wrap(body)), [])

    def test_only_one_antithesis_is_reported_per_line(self):
        body = "Not small, zero. It is not a bug. It is a constraint.\n"
        self.assertEqual(rules(wrap(body)).count("P3"), 1)


class TestCommittedPosts(unittest.TestCase):
    """The posts in this repository must satisfy the rules they declare."""

    def test_week_four_posts_pass(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        targets = [
            path
            for path in prose_gate.markdown_posts(root)
            if os.path.basename(path) >= "2026-09-13"
        ]
        self.assertTrue(targets, "no week-4 posts found to check")
        violations = []
        for path in targets:
            violations.extend(prose_gate.check_file(os.path.join(root, path)))
        self.assertEqual(
            [violation.render() for violation in violations], []
        )


class TestCli(unittest.TestCase):
    def test_clean_file_exits_zero(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "clean.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(wrap("Clean copy, with nothing to find.\n"))
            self.assertEqual(prose_gate.main([path]), 0)

    def test_dirty_file_exits_one(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "dirty.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(wrap("And a dash \u2014 too.\n"))
            self.assertEqual(prose_gate.main([path]), 1)

    def test_unreadable_file_exits_two(self):
        with self.assertRaises(SystemExit) as context:
            prose_gate.main(["/nonexistent/path/to/post.md"])
        self.assertEqual(context.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
