"""Tests for tools/publish_public.py.

The publisher decides what readers see, so the cases that matter are the ones
where something internal escapes: an audit header surviving, a prep/ reference
surviving, a source-repository URL left unrewritten, or a link pointing at a
file the public tree does not contain.
"""

import datetime as dt
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
    ),
)

import publish_public as pub  # noqa: E402

POST = """# Week 3 · Thu 2026-09-10 · 09:00 · Hands-on: Build an Embedding Layer

> Calendar row: W3 Thu AM (CSV row `44:3`). Format: hands-on tutorial.
> Artifacts: `lib/embedding.py`, 356 lines.
> **Standing rule.** `prep/README.md` requires a re-run on posting day.

---

**Topic:** Building a token and position embedding layer

**Subtitle:** One file, no installs.

Good morning.

Read [`lib/embedding.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/embedding.py).

---

*This evening, 17:00: the five checks.*
"""


class TestSplitReaderCopy(unittest.TestCase):
    """The audit header is the thing that must not reach a reader."""

    def test_title_is_taken_from_the_level_one_heading(self):
        title, _ = pub.split_reader_copy(POST, "post.md")
        self.assertEqual(
            title, "Week 3 · Thu 2026-09-10 · 09:00 · Hands-on: Build an Embedding Layer"
        )

    def test_audit_block_is_dropped_entirely(self):
        _, body = pub.split_reader_copy(POST, "post.md")
        self.assertNotIn("Calendar row", body)
        self.assertNotIn("CSV row", body)
        self.assertNotIn("prep/README.md", body)
        self.assertNotIn("Standing rule", body)

    def test_body_opens_on_the_topic_block(self):
        _, body = pub.split_reader_copy(POST, "post.md")
        self.assertTrue(body.startswith("**Topic:**"), body[:40])

    def test_closing_teaser_below_the_second_marker_is_kept(self):
        _, body = pub.split_reader_copy(POST, "post.md")
        self.assertIn("This evening, 17:00", body)

    def test_missing_heading_is_an_error(self):
        with self.assertRaises(pub.PublishError):
            pub.split_reader_copy("no heading here\n\n---\n\nbody\n", "x.md")

    def test_missing_marker_is_an_error(self):
        with self.assertRaises(pub.PublishError):
            pub.split_reader_copy("# Title\n\n> audit only\n", "x.md")

    def test_empty_file_is_an_error(self):
        with self.assertRaises(pub.PublishError):
            pub.split_reader_copy("", "x.md")

    def test_marker_with_nothing_below_it_is_an_error(self):
        with self.assertRaises(pub.PublishError):
            pub.split_reader_copy("# Title\n\n> audit\n\n---\n\n", "x.md")


class TestRewriteLinks(unittest.TestCase):
    """A reader clicking a link must stay inside the repository they are in."""

    def test_source_urls_become_public_urls(self):
        text = pub.SOURCE_BLOB + "lib/embedding.py"
        self.assertEqual(pub.rewrite_links(text), pub.PUBLIC_BLOB + "lib/embedding.py")

    def test_unrelated_urls_are_untouched(self):
        text = "see https://arxiv.org/abs/1706.03762 for the paper"
        self.assertEqual(pub.rewrite_links(text), text)


class TestSlotOf(unittest.TestCase):
    def test_am_and_pm_and_day(self):
        self.assertEqual(pub.slot_of("thu-am-tutorial-x"), "AM")
        self.assertEqual(pub.slot_of("thu-pm-followup-x"), "PM")
        self.assertEqual(pub.slot_of("sat-recap"), "DAY")


class TestCollectPosts(unittest.TestCase):
    """Both bounds matter: the embargo above, the consolidation line below."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "posts", "_archive"))
        for name in (
            "2026-09-08-tue-am-old.md",
            "2026-09-10-thu-am-today.md",
            "2026-09-10-thu-pm-today.md",
            "2026-09-12-sat-am-future.md",
            "not-a-post.txt",
        ):
            open(os.path.join(self.root, "posts", name), "w").close()

    def test_earlier_posts_are_excluded_by_since(self):
        names = pub.collect_posts(self.root, dt.date(2026, 9, 10), dt.date(2026, 9, 10))
        self.assertNotIn("2026-09-08-tue-am-old.md", names)

    def test_later_posts_are_excluded_by_the_embargo(self):
        names = pub.collect_posts(self.root, dt.date(2026, 9, 10), dt.date(2026, 9, 10))
        self.assertNotIn("2026-09-12-sat-am-future.md", names)

    def test_both_of_todays_slots_are_included(self):
        names = pub.collect_posts(self.root, dt.date(2026, 9, 10), dt.date(2026, 9, 10))
        self.assertEqual(
            names, ["2026-09-10-thu-am-today.md", "2026-09-10-thu-pm-today.md"]
        )

    def test_non_post_files_are_ignored(self):
        names = pub.collect_posts(self.root, dt.date(2026, 1, 1), dt.date(2027, 1, 1))
        self.assertNotIn("not-a-post.txt", names)

    def test_missing_posts_directory_is_an_error(self):
        with self.assertRaises(pub.PublishError):
            pub.collect_posts(tempfile.mkdtemp(), dt.date(2026, 1, 1), dt.date(2027, 1, 1))


class TestVerifyTree(unittest.TestCase):
    """Verification is the last thing standing between internal and public."""

    def setUp(self):
        self.dest = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dest, True)
        os.makedirs(os.path.join(self.dest, "posts"))

    def write(self, relative, text):
        path = os.path.join(self.dest, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_clean_tree_has_no_problems(self):
        self.write("lib/embedding.py", "x = 1\n")
        self.write("posts/a.md", f"see [x]({pub.PUBLIC_BLOB}lib/embedding.py)\n")
        self.assertEqual(pub.verify_tree(self.dest), [])

    def test_excluded_directory_is_caught(self):
        os.makedirs(os.path.join(self.dest, "prep"))
        problems = pub.verify_tree(self.dest)
        self.assertTrue(any("prep" in p for p in problems), problems)

    def test_excluded_file_is_caught(self):
        self.write("AGENTS.md", "internal\n")
        problems = pub.verify_tree(self.dest)
        self.assertTrue(any("AGENTS.md" in p for p in problems), problems)

    def test_unrewritten_source_url_is_caught(self):
        self.write("posts/a.md", f"[x]({pub.SOURCE_BLOB}lib/embedding.py)\n")
        problems = pub.verify_tree(self.dest)
        self.assertTrue(any("unrewritten" in p for p in problems), problems)

    def test_surviving_prep_reference_is_caught(self):
        self.write("posts/a.md", "as recorded in prep/README.md\n")
        problems = pub.verify_tree(self.dest)
        self.assertTrue(any("excluded material" in p for p in problems), problems)

    def test_link_to_missing_path_is_caught(self):
        self.write("posts/a.md", f"[x]({pub.PUBLIC_BLOB}lib/absent.py)\n")
        problems = pub.verify_tree(self.dest)
        self.assertTrue(any("missing path" in p for p in problems), problems)


class TestRenderPublicReadme(unittest.TestCase):
    def test_entries_are_grouped_by_week_and_linked_publicly(self):
        entries = [
            pub.Entry(dt.date(2026, 9, 10), "AM", "Morning piece", "a.md"),
            pub.Entry(dt.date(2026, 9, 10), "PM", "Evening piece", "b.md"),
        ]
        text = pub.render_public_readme(entries)
        self.assertIn("### Week 4", text)
        self.assertIn(f"{pub.PUBLIC_BLOB}posts/a.md", text)
        self.assertIn("Morning piece", text)
        self.assertIn("Evening piece", text)
        self.assertNotIn(pub.SOURCE_BLOB, text)


class TestEndToEnd(unittest.TestCase):
    """Build a whole tree from a miniature repository and verify it."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.dest = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(shutil.rmtree, self.dest, True)
        for tree in ("lib", "tests", "data", "posts"):
            os.makedirs(os.path.join(self.root, tree))
        os.makedirs(os.path.join(self.root, "experiments", "week-03"))
        os.makedirs(os.path.join(self.root, "prep"))
        self.put("lib/embedding.py", "VALUE = 1\n")
        self.put("tests/test_embedding.py", "import lib.embedding\n")
        self.put("tests/test_build_index.py", "import tools.build_index\n")
        self.put("data/corpus.txt", "text\n")
        self.put("experiments/week-03/embedding_lab.py", "from lib.embedding import VALUE\n")
        self.put("prep/README.md", "internal notes\n")
        self.put("AGENTS.md", "internal rules\n")
        self.put("posts/2026-09-10-thu-am-tutorial.md", POST)

    def put(self, relative, text):
        with open(os.path.join(self.root, relative), "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_publisher(self):
        return pub.main(
            [
                "--root",
                self.root,
                "--dest",
                self.dest,
                "--since",
                "2026-09-10",
                "--date",
                "2026-09-10",
            ]
        )

    def test_publish_succeeds_and_verifies(self):
        self.assertEqual(self.run_publisher(), 0)

    def test_internal_trees_are_absent_from_the_output(self):
        self.run_publisher()
        self.assertFalse(os.path.exists(os.path.join(self.dest, "prep")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "AGENTS.md")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "tools")))

    def test_runnable_trees_are_present(self):
        self.run_publisher()
        for relative in (
            "lib/embedding.py",
            "data/corpus.txt",
            "experiments/week-03/embedding_lab.py",
            "tests/test_embedding.py",
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(self.dest, relative)), relative
            )

    def test_tests_that_import_tools_are_not_copied(self):
        self.run_publisher()
        self.assertFalse(
            os.path.exists(os.path.join(self.dest, "tests", "test_build_index.py"))
        )

    def test_published_post_carries_no_audit_header(self):
        self.run_publisher()
        path = os.path.join(self.dest, "posts", "2026-09-10-thu-am-tutorial.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("Calendar row", text)
        self.assertNotIn("prep/README.md", text)
        self.assertTrue(text.startswith("# Week 3 · Thu 2026-09-10"), text[:40])
        self.assertIn("**Topic:**", text)

    def test_published_post_links_to_the_public_repository(self):
        self.run_publisher()
        path = os.path.join(self.dest, "posts", "2026-09-10-thu-am-tutorial.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(pub.PUBLIC_BLOB + "lib/embedding.py", text)
        self.assertNotIn(pub.SOURCE_BLOB, text)

    def test_readme_is_written(self):
        self.run_publisher()
        path = os.path.join(self.dest, OUTPUT := "README.md")
        self.assertTrue(os.path.isfile(path), OUTPUT)

    def test_no_posts_in_range_is_an_error(self):
        code = pub.main(
            [
                "--root",
                self.root,
                "--dest",
                self.dest,
                "--since",
                "2026-10-01",
                "--date",
                "2026-10-02",
            ]
        )
        self.assertEqual(code, 2)

    def test_missing_destination_is_an_error(self):
        code = pub.main(
            ["--root", self.root, "--dest", os.path.join(self.dest, "absent")]
        )
        self.assertEqual(code, 2)

    def test_check_mode_reports_a_leak_without_rebuilding(self):
        self.assertEqual(self.run_publisher(), 0)
        os.makedirs(os.path.join(self.dest, "prep"), exist_ok=True)
        code = pub.main(["--root", self.root, "--dest", self.dest, "--check"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
