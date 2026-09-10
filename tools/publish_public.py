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
import csv
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

# Read for series structure only. The calendar's `source` column names
# third-party repositories and is never read, so it cannot reach a reader.
CALENDAR = "content_calendar.csv"

# The launch week announces the series. It is not one of the subject pillars
# and it is not one of the passes, so it is excluded from both summaries.
LAUNCH_PILLAR = "Series Launch"

NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}
WEEK_DAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)

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
PART_SUFFIX = re.compile(r",\s*part\s*\d+\s*$", re.IGNORECASE)

# Any GitHub reference that is not our own public repository. The canonical
# source rule forbids naming a third-party repository to a reader, so a match
# here is a leak rather than a style question.
FOREIGN_REPO = re.compile(
    r"github\.com/(?!QuantumindSSI/Technologues)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
)

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
    week: int


def slot_of(rest: str) -> str:
    """Classify a filename tail as AM, PM, or a whole-day artifact."""
    match = SLOT_HINT.search(rest)
    return match.group(1).upper() if match else "DAY"


def strip_internal_prefix(title: str) -> str:
    """Drop the editorial 'Week N · Day date · time ·' prefix from a heading.

    The prefix is how a post is identified against the calendar while it is
    being written. A reader wants the article's actual title, which is
    whatever follows the last separator.
    """
    parts = title.split("\u00b7")
    return parts[-1].strip() if len(parts) > 1 else title.strip()


def week_of(date: dt.date, weeks_by_date: Dict[str, int]) -> int:
    """Series week for a date, preferring the calendar's own numbering.

    The calendar is authoritative because its week number is what appears in
    the articles themselves. The arithmetic fallback only runs for a date the
    calendar does not cover, which would otherwise crash the index.
    """
    calendar_week = weeks_by_date.get(date.isoformat())
    if calendar_week is not None:
        return calendar_week
    return max(0, (date - WEEK_ONE_START).days // 7 + 1)


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


def publish_posts(
    root: str,
    dest: str,
    names: Sequence[str],
    weeks_by_date: Dict[str, int],
) -> List[Entry]:
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
        raw_title, body = split_reader_copy(text, name)
        title = strip_internal_prefix(raw_title)
        match = FILENAME.match(name)
        assert match is not None, f"{name} passed collect_posts but not FILENAME"
        document = f"# {title}\n\n{rewrite_links(body)}"
        try:
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
                handle.write(document)
        except OSError as exc:
            raise PublishError(f"cannot write {name}: {exc}") from exc
        date = dt.date.fromisoformat(match.group("date"))
        entries.append(
            Entry(
                date=date,
                slot=slot_of(match.group("rest")),
                title=title,
                name=name,
                week=week_of(date, weeks_by_date),
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


class Series(NamedTuple):
    """The shape of the whole series, derived from the editorial calendar.

    Only structural columns are read. The calendar's `source` column is an
    internal routing hint naming third-party repositories, and it is never
    read here, so it cannot reach a reader.
    """

    total_posts: int
    weeks: int
    first_date: str
    last_date: str
    pillars: List[Tuple[str, int, int]]
    passes: List[str]
    rhythm: List[Tuple[str, str, str]]
    weeks_by_date: Dict[str, int]


def load_series(root: str) -> Series:
    """Read the editorial calendar and summarise the series structure."""
    path = os.path.join(root, CALENDAR)
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise PublishError(f"cannot read {path}: {exc}") from exc
    if not rows:
        raise PublishError(f"{path} has no rows")
    required = {"week", "date", "day", "slot", "pillar", "weekly_theme", "format"}
    missing = required - set(rows[0])
    if missing:
        raise PublishError(f"{path} is missing columns: {sorted(missing)}")
    return Series(
        total_posts=len(rows),
        weeks=max(int(row["week"]) for row in rows),
        first_date=min(row["date"] for row in rows),
        last_date=max(row["date"] for row in rows),
        pillars=summarise_pillars(rows),
        passes=summarise_passes(rows),
        rhythm=summarise_rhythm(rows),
        weeks_by_date={row["date"]: int(row["week"]) for row in rows},
    )


def summarise_pillars(rows: Sequence[Dict[str, str]]) -> List[Tuple[str, int, int]]:
    """Return (pillar, distinct weeks, post count), ordered by first week.

    The launch week is excluded. It announces the series rather than teaching
    a subject, so counting it would report eleven pillars where there are ten.
    """
    first: Dict[str, int] = {}
    weeks: Dict[str, set] = {}
    counts: Dict[str, int] = {}
    for row in rows:
        pillar, week = row["pillar"], int(row["week"])
        if pillar == LAUNCH_PILLAR:
            continue
        first.setdefault(pillar, week)
        weeks.setdefault(pillar, set()).add(week)
        counts[pillar] = counts.get(pillar, 0) + 1
    ordered = sorted(first, key=lambda name: first[name])
    return [(name, len(weeks[name]), counts[name]) for name in ordered]


def summarise_passes(rows: Sequence[Dict[str, str]]) -> List[str]:
    """Return each named pass over the pillars, in the order it runs.

    A weekly theme reads "Pillar - Pass name, part N". The pass name is what
    survives once the pillar prefix and the part suffix are removed. The launch
    week is excluded for the same reason it is excluded from the pillars: its
    theme names an event rather than a pass.
    """
    first: Dict[str, int] = {}
    for row in rows:
        if row["pillar"] == LAUNCH_PILLAR:
            continue
        theme = row["weekly_theme"]
        if " - " not in theme:
            continue
        name = PART_SUFFIX.sub("", theme.split(" - ", 1)[1]).strip()
        if name:
            first.setdefault(name, int(row["week"]))
    return sorted(first, key=lambda name: first[name])


def summarise_rhythm(rows: Sequence[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """Return (day, morning format, evening format) for a standard week."""
    tally: Dict[Tuple[str, str], Dict[str, int]] = {}
    for row in rows:
        key = (row["day"], row["slot"])
        bucket = tally.setdefault(key, {})
        bucket[row["format"]] = bucket.get(row["format"], 0) + 1
    rhythm: List[Tuple[str, str, str]] = []
    for day in WEEK_DAYS:
        morning = tally.get((day, "AM"))
        evening = tally.get((day, "PM"))
        if not morning or not evening:
            continue
        rhythm.append(
            (
                day,
                max(morning, key=lambda name: morning[name]),
                max(evening, key=lambda name: evening[name]),
            )
        )
    return rhythm


def render_header(series: Series) -> List[str]:
    """The opening pitch: what the series is and what it commits to."""
    return [
        "# Technologues",
        "",
        "**Agentic and machine-learning systems engineering, written from",
        f"scratch over {series.weeks} weeks.** Two articles a day, one at 09:00",
        "and one at 17:00, every day.",
        "",
        f"The full run is {series.total_posts:,} articles across {series.weeks} "
        f"weeks, {series.first_date} to {series.last_date}.",
        "",
        "The premise is that the skills behind a working agent form a",
        "dependency graph, and that most engineers study the wrong layers of it",
        "first. The series walks that graph from the bottom, one mechanism at a",
        "time, building each one before discussing it.",
        "",
        "Every implementation an article discusses lives in this repository. It",
        "is written here, tested here, and then read line by line in the",
        "article. Nothing is summarised from somebody else's code. Every number",
        "quoted in an article came out of running a file you can run too.",
        "",
    ]


def render_quickstart() -> List[str]:
    """The shortest path from clone to a reproduced number."""
    return [
        "## Quick start",
        "",
        "Python 3.8 or newer. Standard library only, so there is no install",
        "step, no virtualenv, and no requirements file.",
        "",
        "```bash",
        "git clone https://github.com/QuantumindSSI/Technologues.git",
        "cd Technologues",
        "",
        "# reproduce a measurement quoted in an article",
        "python3 experiments/week-03/embedding_lab.py",
        "",
        "# check the library does what the articles claim",
        "python3 -m unittest discover -s tests -t .",
        "```",
        "",
        "Every experiment prints `All assertions passed` and exits 0. Anything",
        "else is a bug, and it is worth telling me about.",
        "",
    ]


def spell(count: int) -> str:
    """Spell a small count, so prose reads naturally and cannot drift."""
    return NUMBER_WORDS.get(count, str(count))


def render_pillars(series: Series) -> List[str]:
    """The subject areas the calendar rotates through."""
    count = spell(len(series.pillars))
    lines = [
        f"## The {count} pillars",
        "",
        f"The series rotates through {count} subject areas. Each one gets a",
        "two-week block, then hands over to the next, so no single topic runs",
        "long enough to go stale and every topic is returned to later at",
        "greater depth.",
        "",
        "| Pillar | Weeks | Articles |",
        "|---|---:|---:|",
    ]
    for name, weeks, posts in series.pillars:
        lines.append(f"| {name} | {weeks} | {posts} |")
    lines.append("")
    return lines


def render_passes(series: Series) -> List[str]:
    """The sweeps that revisit every pillar at increasing depth."""
    count = len(series.passes)
    lines = [
        f"## {spell(count).capitalize()} passes over the same ground",
        "",
        f"Each pillar is covered {spell(count)} times, and the pass decides the",
        "altitude. The first time through a topic asks how it works. The last",
        "time asks what it costs at scale and where it breaks.",
        "",
    ]
    for index, name in enumerate(series.passes, start=1):
        lines.append(f"{index}. **{name}**")
    lines.append("")
    return lines


def render_rhythm(series: Series) -> List[str]:
    """The fixed weekly format rotation, so a reader knows what is coming."""
    lines = [
        "## The weekly rhythm",
        "",
        "The format of each slot is fixed, so the shape of a week is",
        "predictable even when the subject is new.",
        "",
        "| Day | 09:00 | 17:00 |",
        "|---|---|---|",
    ]
    for day, morning, evening in series.rhythm:
        lines.append(f"| {day} | {morning} | {evening} |")
    lines.append("")
    return lines


def render_layout() -> List[str]:
    """What each directory is for."""
    return [
        "## Repository layout",
        "",
        "| Tree | What it holds |",
        "|---|---|",
        "| `posts/` | The articles, published on the day they go out |",
        "| `lib/` | Reference implementations the articles walk through |",
        "| `tests/` | The suite proving `lib/` behaves as described |",
        "| `experiments/` | Runnable measurements quoted in specific articles |",
        "| `data/` | Frozen corpora, so a quoted number stays reproducible |",
        "",
        "`lib/` is the durable code. `experiments/` is written per article and",
        "left alone afterwards, so a measurement stays reproducible exactly as",
        "it was published.",
        "",
    ]


def render_articles(entries: Sequence[Entry]) -> List[str]:
    """The published index, grouped by week and ordered by date."""
    lines = [
        "## Published articles",
        "",
        f"{len(entries)} published so far. Articles appear here on the day they",
        "go out. Nothing is posted early.",
        "",
    ]
    by_week: Dict[int, List[Entry]] = {}
    for entry in entries:
        by_week.setdefault(entry.week, []).append(entry)
    for week in sorted(by_week, reverse=True):
        lines.append(f"### Week {week}")
        lines.append("")
        for entry in sorted(by_week[week], key=lambda item: (item.date, item.slot)):
            stamp = f"{entry.date.isoformat()} {entry.slot}"
            url = f"{PUBLIC_BLOB}{POSTS_DIR}/{entry.name}"
            lines.append(f"- **{stamp}** [{entry.title}]({url})")
        lines.append("")
    return lines


def render_conventions() -> List[str]:
    """How to read the repository, and how it is maintained."""
    return [
        "## How this repository is built",
        "",
        "This tree is generated. Articles and code are written in a working",
        "repository and published here once the day arrives, which is why you",
        "will not find editorial notes, drafts, or unpublished articles.",
        "Opening a pull request against a generated file will not stick, so",
        "raise an issue instead and the fix goes in upstream.",
        "",
        "Two rules the series holds itself to, and which you should hold it to:",
        "",
        "- **Every number names its source.** A figure is either measured by a",
        "  file in this repository, cited to a paper or a vendor document, or",
        "  flagged in the text as unverified. There is no fourth option.",
        "- **Every code listing is copied from a committed file.** If an",
        "  article shows you a function, that function exists here, is tested",
        "  here, and runs.",
        "",
        "## Reproducing anything you read",
        "",
        "Articles quote the file they came from. Run that file and compare. The",
        "experiments are seeded, so a given article's numbers are stable across",
        "machines and across runs. If a number here does not reproduce for you,",
        "that is a defect worth an issue.",
        "",
    ]


def render_public_readme(entries: Sequence[Entry], series: Series) -> str:
    """Assemble the full public README."""
    lines: List[str] = []
    lines.extend(render_header(series))
    lines.extend(render_quickstart())
    lines.extend(render_articles(entries))
    lines.extend(render_pillars(series))
    lines.extend(render_passes(series))
    lines.extend(render_rhythm(series))
    lines.extend(render_layout())
    lines.extend(render_conventions())
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
    for foreign in sorted(set(FOREIGN_REPO.findall(text))):
        problems.append(f"{relative}: names a third-party repository '{foreign}'")
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
            series = load_series(args.root)
            entries = publish_posts(args.root, args.dest, names, series.weeks_by_date)
            files = copy_code(args.root, args.dest)
            readme = os.path.join(args.dest, OUTPUT_README)
            with open(readme, "w", encoding="utf-8") as handle:
                handle.write(render_public_readme(entries, series))
            print(
                f"published {len(entries)} post(s), {len(files)} code file(s), "
                f"README covering {series.total_posts} planned articles"
            )
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
