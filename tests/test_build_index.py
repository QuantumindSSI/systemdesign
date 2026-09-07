"""Tests for tools/build_index.py.

The index is the repository's front door, so the property that matters
most is negative: an unpublished post must never appear in it.
"""

import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import build_index as index  # noqa: E402


def write_post(root, name, title="Week 1 \u00b7 Mon 2026-08-24 \u00b7 A Real Title"):
    """Create a post file with a level-one heading and a reader body."""
    directory = os.path.join(root, "posts")
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n> header\n\n---\n\nbody\n")


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_published_post_is_collected(self):
        write_post(self.root, "2026-08-24-mon-am-essay-a.md")
        found = index.collect(self.root, dt.date(2026, 9, 1))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].slot, "AM")

    def test_same_day_post_is_collected(self):
        write_post(self.root, "2026-08-24-mon-am-essay-a.md")
        self.assertEqual(len(index.collect(self.root, dt.date(2026, 8, 24))), 1)

    def test_future_post_is_omitted(self):
        write_post(self.root, "2026-12-25-fri-am-essay-future.md")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_archive_is_omitted(self):
        archive = os.path.join(self.root, "posts", "_archive")
        os.makedirs(archive, exist_ok=True)
        with open(os.path.join(archive, "2026-08-24-mon-am-old.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# Old\n")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_teaser_bundle_is_omitted(self):
        write_post(self.root, "2026-08-24-mon-teasers.md")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_video_plan_is_omitted(self):
        write_post(self.root, "2026-08-27-thu-video-production-plan.md")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_file_without_heading_is_skipped(self):
        directory = os.path.join(self.root, "posts")
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "2026-08-24-mon-am-x.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("no heading here\n")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_missing_posts_directory_is_not_an_error(self):
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1)), [])

    def test_pm_slot_detected(self):
        write_post(self.root, "2026-08-24-mon-pm-followup-a.md")
        self.assertEqual(index.collect(self.root, dt.date(2026, 9, 1))[0].slot, "PM")

    def test_results_are_sorted_by_date(self):
        write_post(self.root, "2026-08-31-mon-am-b.md")
        write_post(self.root, "2026-08-24-mon-am-a.md")
        found = index.collect(self.root, dt.date(2026, 9, 1))
        self.assertEqual([p.date.day for p in found], [24, 31])


class TestWeekNumbering(unittest.TestCase):
    def test_series_start_is_week_one(self):
        post = index.Post(dt.date(2026, 8, 23), "AM", "posts/x.md", "T")
        self.assertEqual(post.week, 1)

    def test_seventh_day_is_still_week_one(self):
        post = index.Post(dt.date(2026, 8, 29), "AM", "posts/x.md", "T")
        self.assertEqual(post.week, 1)

    def test_eighth_day_is_week_two(self):
        post = index.Post(dt.date(2026, 8, 30), "AM", "posts/x.md", "T")
        self.assertEqual(post.week, 2)

    def test_week_three_boundary(self):
        post = index.Post(dt.date(2026, 9, 6), "AM", "posts/x.md", "T")
        self.assertEqual(post.week, 3)


class TestRender(unittest.TestCase):
    def test_strip_prefix_removes_internal_metadata(self):
        self.assertEqual(
            index.strip_prefix("Week 1 \u00b7 Mon 2026-08-24 \u00b7 Real Title"),
            "Real Title",
        )

    def test_strip_prefix_leaves_a_plain_title(self):
        self.assertEqual(index.strip_prefix("Plain Title"), "Plain Title")

    def test_empty_index_says_so(self):
        self.assertIn("No articles have published yet", index.render([]))

    def test_rendered_link_points_at_this_repository(self):
        post = index.Post(dt.date(2026, 8, 24), "AM", "posts/a.md", "T")
        self.assertIn(index.REPO_BLOB + "posts/a.md", index.render([post]))

    def test_weeks_render_newest_first(self):
        early = index.Post(dt.date(2026, 8, 24), "AM", "posts/a.md", "Early")
        late = index.Post(dt.date(2026, 9, 6), "AM", "posts/b.md", "Late")
        out = index.render([early, late])
        self.assertLess(out.index("## Week 3"), out.index("## Week 1"))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_writes_the_file(self):
        write_post(self.root, "2026-08-24-mon-am-a.md")
        self.assertEqual(index.main(["--root", self.root, "--date", "2026-09-01"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "README.md")))

    def test_check_fails_when_missing(self):
        self.assertEqual(
            index.main(["--root", self.root, "--date", "2026-09-01", "--check"]), 1
        )

    def test_check_passes_after_build(self):
        write_post(self.root, "2026-08-24-mon-am-a.md")
        index.main(["--root", self.root, "--date", "2026-09-01"])
        self.assertEqual(
            index.main(["--root", self.root, "--date", "2026-09-01", "--check"]), 0
        )

    def test_check_fails_when_a_new_post_lands(self):
        write_post(self.root, "2026-08-24-mon-am-a.md")
        index.main(["--root", self.root, "--date", "2026-09-01"])
        write_post(self.root, "2026-08-25-tue-am-b.md")
        self.assertEqual(
            index.main(["--root", self.root, "--date", "2026-09-01", "--check"]), 1
        )

    def test_bad_date_returns_two(self):
        self.assertEqual(index.main(["--root", self.root, "--date", "nope"]), 2)

    def test_committed_readme_is_current(self):
        """The real README in this repository must not be stale."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertEqual(index.main(["--root", repo, "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
