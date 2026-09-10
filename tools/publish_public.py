#!/usr/bin/env python3
"""Build the reader-facing Technologues tree from this repository.

The public repository at github.com/QuantumindSSI/Technologues is what readers
are given. It carries the articles and the code a reader can actually run, and
none of the editorial machinery: no AGENTS.md, no prep/ working notes, no
tools/, no content calendar.

Three transformations happen on the way out.

1. Each post is cut down to its reader-facing copy. The level-one heading is
   kept because it is the article title. The editorial audit block between that
   heading and the first `---` marker is dropped, which is also what removes
   every reference to the internal prep/ tree. Everything below the marker is
   kept verbatim, including the closing teasers.
2. Every embedded systemdesign URL is rewritten to the public repository, so a
   link a reader clicks resolves inside the repository they are already reading.
3. README.md is regenerated as the public index, listing only the posts that
   were published.

Code trees are copied whole, because the articles promise a reader can run the
experiments, and every experiment imports from lib/ while two of them read the
corpus in data/. Shipping posts without those trees would ship scripts that
die on their import line.

Nothing is committed and nothing is pushed. This script writes a tree and
verifies it. Publishing it is a separate, deliberate act.

Exit codes: 0 success, 1 verification failure, 2 usage or IO error.
"""

import argparse
import datetime as dt
import os
import re
import shutil
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

SOURCE_BLOB = "https://github.com/QuantumindSSI/systemdesign/blob/main/"
PUBLIC_BLOB = "https://github.com/QuantumindSSI/Technologues/blob/main/"

POSTS_DIR = "posts"
ARCHIVE_DIR = "_archive"
OUTPUT_README = "README.md"

# Copied verbatim. lib/ is required by every experiment, data/ is read at
# runtime by two of them, tests/ is how a reader checks the code does what the
# articles claim.
CODE_TREES = ("lib", "tests", "data")

# experiments/ is copied per week so that consolidating earlier weeks stays a
# deliberate decision rather than a side effect of running this script.
EXPERIMENT_WEEKS = ("week-03",)

# These test the editorial machinery in tools/, which is not published. Copying
# them would put a test suite in the public repository that fails on import.
SKIP_FILES = frozenset(
    {
        os.path.join("tests", "test_build_index.py"),
        os.path.join("tests", "test_publication_gate.py"),
        os.path.join("tests", "test_publish_public.py"),
    }
)

# Anything matching these must never appear in the published tree. The verifier
# treats a match as a hard failure rather than a warning.
FORBIDDEN_PATHS = ("AGENTS.md", "prep", "tools", "content_calendar.csv")
FORBIDDEN_TEXT = ("prep/", "content_calendar", "AGENTS.md")

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")

FILENAME = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<day>[a-z]{3})-(?P<rest>.+)\.md$"
)
HEADING = re.compile(r"^#\s+(?P<title>.*?)\s*$")
SLOT_HINT = re.compile(r"\b(am|pm)\b")
MARKER = "---"
LINK = re.compile(re.escape(PUBLIC_BLOB) + r"([^)\s\"'`]+)")

WEEK_ONE_START = dt.date(2026, 8, 17)
DEFAULT_SINCE = dt.date(2026, 9, 10)


class PublishError(Exception):
    """A post could not be converted into reader-facing copy."""


class Entry(NamedTuple):
    """One published post, as the public index needs to see it."""

    date: dt.date
    slot: str
    title: str
    name: str

    @property
    def week(self) -> int:
        """Calendar week number, counting the first week as 1."""
        return max(0, (self.date - WEEK_ONE_START).days // 7 + 1)


def slot_of(rest: str) -> str:
    """Classify a filename tail as AM, PM, or a whole-day artifact."""
    match = SLOT_HINT.search(rest)
    return match.group(1).upper() if match else "DAY"


def split_reader_copy(text: str, name: str) -> Tuple[str, str]:
    """Split a post into its title and its reader-facing body.

    The body is everything below the first `---` marker, with the editorial
    audit block above the marker discarded. Leading blank lines are trimmed so
    the public file opens on the Topic block.

    Raises PublishError if the post has no level-one heading on its first line
    or no `---` marker, because both are required by AGENTS.md and a post
    missing either is malformed rather than merely unusual.
    """
    lines = text.splitlines()
    if not lines:
        raise PublishError(f"{name} is empty")
    heading = HEADING.match(lines[0])
    if heading is None:
        raise PublishError(f"{name} does not open with a level-one heading")
    try:
        marker = lines.index(MARKER)
    except ValueError:
        raise PublishError(f"{name} has no '{MARKER}' editorial marker") from None
    body = lines[marker + 1 :]
    while body and not body[0].strip():
        body.pop(0)
    if not body:
        raise PublishError(f"{name} has no reader-facing copy below the marker")
    return heading.group("title"), "\n".join(body).rstrip() + "\n"


def rewrite_links(text: str) -> str:
    """Point every embedded source-repository URL at the public repository."""
    return text.replace(SOURCE_BLOB, PUBLIC_BLOB)


def collect_posts(root: str, since: dt.date, today: dt.date) -> List[str]:
    """Return post filenames dated within [since, today], sorted by date.

    The upper bound is the embargo: a post is never published before its day.
    The lower bound is the consolidation boundary, so earlier material joins the
    public repository only when that is asked for explicitly.
    """
    posts_root = os.path.join(root, POSTS_DIR)
    if not os.path.isdir(posts_root):
        raise PublishError(f"no posts directory at {posts_root}")
    chosen: List[str] = []
    for name in sorted(os.listdir(posts_root)):
        if name == ARCHIVE_DIR:
            continue
        if not os.path.isfile(os.path.join(posts_root, name)):
            continue
        match = FILENAME.match(name)
        if match is None:
            continue
        try:
            date = dt.date.fromisoformat(match.group("date"))
        except ValueError:
            continue
        if since <= date <= today:
            chosen.append(name)
    return chosen


def publish_posts(root: str, dest: str, names: Sequence[str]) -> List[Entry]:
    """Write each post's reader-facing copy into the destination tree."""
    out_dir = os.path.join(dest, POSTS_DIR)
    os.makedirs(out_dir, exist_ok=True)
    entries: List[Entry] = []
    for name in names:
        source = os.path.join(root, POSTS_DIR, name)
        try:
            with open(source, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            raise PublishError(f"cannot read {source}: {exc}") from exc
        title, body = split_reader_copy(text, name)
        match = FILENAME.match(name)
        assert match is not None, f"{name} passed collect_posts but not FILENAME"
        document = f"# {title}\n\n{rewrite_links(body)}"
        try:
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
                handle.write(document)
        except OSError as exc:
            raise PublishError(f"cannot write {name}: {exc}") from exc
        entries.append(
            Entry(
                date=dt.date.fromisoformat(match.group("date")),
                slot=slot_of(match.group("rest")),
                title=title,
                name=name,
            )
        )
    return entries


def copy_code(root: str, dest: str) -> List[str]:
    """Copy the runnable trees, skipping files that depend on tools/.

    Returns the relative paths written, so the caller can report the size of
    what was published.
    """
    written: List[str] = []
    for tree in CODE_TREES:
        source = os.path.join(root, tree)
        if not os.path.isdir(source):
            raise PublishError(f"expected a {tree}/ directory at {source}")
        target = os.path.join(dest, tree)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target, ignore=IGNORE)
        for relative in sorted(SKIP_FILES):
            candidate = os.path.join(dest, relative)
            if os.path.isfile(candidate):
                os.remove(candidate)
        written.extend(walk_relative(target, dest))
    experiments = os.path.join(dest, "experiments")
    shutil.rmtree(experiments, ignore_errors=True)
    for week in EXPERIMENT_WEEKS:
        source = os.path.join(root, "experiments", week)
        if not os.path.isdir(source):
            raise PublishError(f"expected experiments/{week} at {source}")
        shutil.copytree(source, os.path.join(experiments, week), ignore=IGNORE)
    written.extend(walk_relative(experiments, dest))
    return written


def walk_relative(target: str, dest: str) -> List[str]:
    """List every file under `target`, as paths relative to `dest`."""
    found: List[str] = []
    for current, _, files in os.walk(target):
        for name in sorted(files):
            found.append(os.path.relpath(os.path.join(current, name), dest))
    return sorted(found)


def render_public_readme(entries: Sequence[Entry]) -> str:
    """Build the public index, grouped by week and ordered by date."""
    lines = [
        "# Technologues",
        "",
        "Long-form engineering writing, one morning piece and one evening",
        "follow-up per day. Every article is built on code in this repository,",
        "and every number an article quotes came out of running it.",
        "",
        "Standard library Python only. No install step:",
        "",
        "```",
        "git clone https://github.com/QuantumindSSI/Technologues.git",
        "cd Technologues",
        "python3 experiments/week-03/embedding_lab.py",
        "python3 -m unittest discover -s tests -t .",
        "```",
        "",
        "## Articles",
        "",
    ]
    by_week: Dict[int, List[Entry]] = {}
    for entry in entries:
        by_week.setdefault(entry.week, []).append(entry)
    for week in sorted(by_week):
        lines.append(f"### Week {week}")
        lines.append("")
        for entry in sorted(by_week[week], key=lambda item: (item.date, item.slot)):
            stamp = f"{entry.date.isoformat()} {entry.slot}"
            url = f"{PUBLIC_BLOB}{POSTS_DIR}/{entry.name}"
            lines.append(f"- **{stamp}** [{entry.title}]({url})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def verify_tree(dest: str) -> List[str]:
    """Return every reason the published tree is unsafe to push.

    Four classes of failure: an excluded path present, an excluded string
    surviving in published text, a source-repository URL left unrewritten, and
    an embedded link pointing at a path that does not exist in the tree.
    """
    problems: List[str] = []
    for forbidden in FORBIDDEN_PATHS:
        if os.path.exists(os.path.join(dest, forbidden)):
            problems.append(f"excluded path present in output: {forbidden}")
    for relative in walk_relative(dest, dest):
        if not relative.endswith(".md"):
            continue
        if relative.startswith("data" + os.sep):
            continue
        path = os.path.join(dest, relative)
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            problems.append(f"cannot read {relative}: {exc}")
            continue
        problems.extend(verify_text(dest, relative, text))
    return problems


def verify_text(dest: str, relative: str, text: str) -> List[str]:
    """Check one published document for leaks, stale URLs, and dead links."""
    problems: List[str] = []
    if SOURCE_BLOB in text:
        problems.append(f"{relative}: unrewritten source-repository URL")
    for banned in FORBIDDEN_TEXT:
        if banned in text:
            problems.append(f"{relative}: references excluded material '{banned}'")
    for target in LINK.findall(text):
        if not os.path.exists(os.path.join(dest, target)):
            problems.append(f"{relative}: link to missing path '{target}'")
    return problems


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="source repository root")
    parser.add_argument("--dest", required=True, help="public repository checkout")
    parser.add_argument(
        "--since",
        default=DEFAULT_SINCE.isoformat(),
        help="earliest post date to publish (default 2026-09-10)",
    )
    parser.add_argument("--date", help="treat this ISO date as today")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify an already-built tree without writing to it",
    )
    return parser.parse_args(argv)


def resolve_dates(args: argparse.Namespace) -> Tuple[dt.date, dt.date]:
    """Turn the date arguments into a (since, today) pair."""
    try:
        since = dt.date.fromisoformat(args.since)
    except ValueError as exc:
        raise PublishError(f"invalid --since: {exc}") from exc
    if args.date is None:
        return since, dt.date.today()
    try:
        return since, dt.date.fromisoformat(args.date)
    except ValueError as exc:
        raise PublishError(f"invalid --date: {exc}") from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build and verify the public tree. Returns a process exit code."""
    args = parse_args(argv)
    try:
        since, today = resolve_dates(args)
        if not os.path.isdir(args.dest):
            raise PublishError(f"destination is not a directory: {args.dest}")
        if not args.check:
            names = collect_posts(args.root, since, today)
            if not names:
                raise PublishError(
                    f"no posts dated between {since} and {today}; nothing to publish"
                )
            entries = publish_posts(args.root, args.dest, names)
            files = copy_code(args.root, args.dest)
            readme = os.path.join(args.dest, OUTPUT_README)
            with open(readme, "w", encoding="utf-8") as handle:
                handle.write(render_public_readme(entries))
            print(f"published {len(entries)} post(s) and {len(files)} code file(s)")
    except PublishError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 2
    problems = verify_tree(args.dest)
    for problem in problems:
        print(f"  [leak] {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s). Nothing should be pushed.", file=sys.stderr)
        return 1
    print("public tree verified: no excluded material, every link resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
