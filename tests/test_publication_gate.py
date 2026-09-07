"""Tests for tools/publication_gate.py.

A gate that cannot fail is decoration. Every rule here is tested in both
directions: a clean case that must pass, and a dirty case that must be
caught, with the violation located on the right line.
"""

import datetime as dt
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import publication_gate as gate  # noqa: E402

CLEAN_POST = """# A post

> Editorial header. May safely name posts/2026-01-02-mon-am-other.md here.

---

**Topic:** Something

Body text with a link to [`lib/thing.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/thing.py).
"""


def write(root, relative, text):
    """Write `text` to root/relative, creating parent directories."""
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class TestPostDate(unittest.TestCase):
    def test_parses_dated_filename(self):
        self.assertEqual(
            gate.post_date("posts/2026-09-06-sun-am-theme-kickoff.md"),
            dt.date(2026, 9, 6),
        )

    def test_undated_filename_returns_none(self):
        self.assertIsNone(gate.post_date("posts/README.md"))

    def test_impossible_date_returns_none(self):
        self.assertIsNone(gate.post_date("posts/2026-13-45-mon-am-x.md"))


class TestSplitEditorial(unittest.TestCase):
    def test_returns_only_copy_below_the_marker(self):
        body = gate.split_editorial("# T\n\n> header\n\n---\n\nreader copy\n")
        self.assertNotIn("header", body)
        self.assertIn("reader copy", body)

    def test_file_without_marker_is_all_reader_facing(self):
        self.assertIn("everything", gate.split_editorial("everything here"))

    def test_offset_points_at_the_first_body_line(self):
        text = "# T\n\n> header\n\n---\n\nreader copy\n"
        self.assertEqual(text.split("\n")[gate._body_offset(text)], "")


class TestLinkResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_existing_target_passes(self):
        write(self.root, "lib/thing.py", "x = 1\n")
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        self.assertEqual(gate.check_links(self.root), [])

    def test_missing_target_is_caught(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        found = gate.check_links(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].rule, "R2")
        self.assertIn("lib/thing.py", found[0].detail)

    def test_line_number_is_reported(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        self.assertEqual(gate.check_links(self.root)[0].line, 9)


class TestReadAhead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_clean_body_passes(self):
        write(self.root, "lib/thing.py", "x = 1\n")
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        self.assertEqual(gate.check_read_ahead(self.root), [])

    def test_header_may_name_a_post_path(self):
        # The header in CLEAN_POST names a post path deliberately.
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        self.assertEqual(
            [v for v in gate.check_read_ahead(self.root) if "names another" in v.detail],
            [],
        )

    def test_forward_post_reference_is_caught(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n---\n\nSee posts/2026-01-02-fri-am-b.md for more.\n")
        found = gate.check_read_ahead(self.root)
        self.assertEqual(len(found), 1)
        self.assertIn("not published yet", found[0].detail)

    def test_backward_post_reference_is_allowed(self):
        # Pointing a reader at an already published article is the whole
        # purpose of this repository, so it must not be a violation.
        write(self.root, "posts/2026-01-05-mon-am-a.md",
              "# T\n\n---\n\nAs covered in posts/2026-01-02-fri-am-b.md.\n")
        self.assertEqual(gate.check_read_ahead(self.root), [])

    def test_same_date_reference_is_treated_as_forward(self):
        # The 09:00 post precedes the 17:00 post and filenames carry no
        # time, so a same-date link cannot be shown to be safe.
        write(self.root, "posts/2026-01-05-mon-am-a.md",
              "# T\n\n---\n\nTonight: posts/2026-01-05-mon-pm-b.md.\n")
        self.assertEqual(len(gate.check_read_ahead(self.root)), 1)

    def test_read_ahead_phrase_is_caught(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n---\n\nClone it if you want to read ahead.\n")
        found = gate.check_read_ahead(self.root)
        self.assertEqual(len(found), 1)
        self.assertIn("read ahead", found[0].detail)

    def test_phrase_match_is_case_insensitive(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n---\n\nSNEAK PEEK below.\n")
        self.assertEqual(len(gate.check_read_ahead(self.root)), 1)

    def test_every_forbidden_phrase_is_actually_detected(self):
        for phrase in gate.READ_AHEAD_PHRASES:
            with self.subTest(phrase=phrase):
                write(self.root, "posts/2026-01-01-thu-am-a.md",
                      f"# T\n\n---\n\ntext {phrase} text\n")
                self.assertEqual(len(gate.check_read_ahead(self.root)), 1)


class TestForwardReference(unittest.TestCase):
    def test_earlier_date_is_backward(self):
        self.assertFalse(gate.is_forward_reference(
            "posts/2026-02-01-mon-am-a.md", "posts/2026-01-01-thu-am-b.md"))

    def test_later_date_is_forward(self):
        self.assertTrue(gate.is_forward_reference(
            "posts/2026-01-01-thu-am-a.md", "posts/2026-02-01-mon-am-b.md"))

    def test_same_date_is_forward(self):
        self.assertTrue(gate.is_forward_reference(
            "posts/2026-01-01-thu-am-a.md", "posts/2026-01-01-thu-pm-b.md"))

    def test_undated_referrer_is_forward(self):
        self.assertTrue(gate.is_forward_reference(
            "posts/README.md", "posts/2026-01-01-thu-am-b.md"))

    def test_undated_target_is_forward(self):
        self.assertTrue(gate.is_forward_reference(
            "posts/2026-01-01-thu-am-a.md", "posts/notes.md"))


class TestExternalRepos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_our_own_repo_url_is_allowed(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md", CLEAN_POST)
        self.assertEqual(gate.check_external_repos(self.root), [])

    def test_external_url_is_caught(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n---\n\nSee github.com/someone/somelib for details.\n")
        found = gate.check_external_repos(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].rule, "R4")

    def test_bare_owner_name_is_caught(self):
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n---\n\nAdapted from rasbt's implementation.\n")
        self.assertEqual(len(gate.check_external_repos(self.root)), 1)

    def test_header_is_also_checked(self):
        # R4 applies to the whole file: a header a reader could see counts.
        write(self.root, "posts/2026-01-01-thu-am-a.md",
              "# T\n\n> Source: github.com/someone/somelib\n\n---\n\nbody\n")
        self.assertEqual(len(gate.check_external_repos(self.root)), 1)


class TestEmbargo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        for command in (["git", "init", "-q"],
                        ["git", "config", "user.email", "t@example.com"],
                        ["git", "config", "user.name", "t"]):
            subprocess.run(command, cwd=self.root, check=True, capture_output=True)

    def _track(self, relative):
        write(self.root, relative, "# T\n\n---\n\nbody\n")
        subprocess.run(["git", "add", relative], cwd=self.root, check=True,
                       capture_output=True)

    def test_past_post_is_allowed(self):
        self._track("posts/2026-01-01-thu-am-a.md")
        self.assertEqual(
            gate.check_embargo(self.root, dt.date(2026, 6, 1)), []
        )

    def test_same_day_post_is_allowed(self):
        self._track("posts/2026-06-01-mon-am-a.md")
        self.assertEqual(
            gate.check_embargo(self.root, dt.date(2026, 6, 1)), []
        )

    def test_future_post_is_caught(self):
        self._track("posts/2026-12-25-fri-am-a.md")
        found = gate.check_embargo(self.root, dt.date(2026, 6, 1))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].rule, "R1")
        self.assertIn("2026-12-25", found[0].detail)

    def test_untracked_future_post_is_fine(self):
        # Prep work in the working tree, never staged, is exactly the workflow.
        write(self.root, "posts/2026-12-25-fri-am-a.md", "# T\n\n---\n\nbody\n")
        self.assertEqual(
            gate.check_embargo(self.root, dt.date(2026, 6, 1)), []
        )

    def test_non_post_files_are_not_embargoed(self):
        self._track("lib/2026-12-25-thing.py")
        self.assertEqual(
            gate.check_embargo(self.root, dt.date(2026, 6, 1)), []
        )


class TestCli(unittest.TestCase):
    def test_bad_date_returns_two(self):
        self.assertEqual(gate.main(["--date", "not-a-date"]), 2)

    def test_clean_tree_returns_zero(self):
        with tempfile.TemporaryDirectory() as root:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True,
                           capture_output=True)
            write(root, "posts/2026-01-01-thu-am-a.md", "# T\n\n---\n\nbody\n")
            self.assertEqual(gate.main(["--root", root, "--date", "2026-06-01"]), 0)

    def test_dirty_tree_returns_one(self):
        with tempfile.TemporaryDirectory() as root:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True,
                           capture_output=True)
            write(root, "posts/2026-01-01-thu-am-a.md",
                  "# T\n\n---\n\nplease read ahead\n")
            self.assertEqual(gate.main(["--root", root, "--date", "2026-06-01"]), 1)


if __name__ == "__main__":
    unittest.main()
