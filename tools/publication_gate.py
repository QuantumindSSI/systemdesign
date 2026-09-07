"""Enforce the publication rules mechanically, before anything is pushed.

Four rules are checked. All of them exist because the failure they prevent
is silent: nothing breaks at commit time, and the damage is only visible
after the repository is public.

  R1 EMBARGO. No post may be readable before its own post day. A file
     under `posts/` named with a date later than today must not be tracked
     by git, because anything tracked is pushed and anything pushed is
     public. Prep work stays in the working tree, unstaged.

  R2 LINK RESOLUTION. Every repository URL embedded in a post must point
     at a path that actually exists. A published article containing a
     404 is worse than one containing no link.

  R3 NO READING AHEAD. Reader-facing copy must not invite anyone to go
     and read material before its post day, and must not name the path of
     a post that has not been published yet. Pointing a reader at an
     ALREADY PUBLISHED article of ours is the intended use of this
     repository and is allowed; pointing forward is not.

     "Already published" means strictly earlier than the referring post's
     own date. A same-date reference is treated as forward, because the
     09:00 post precedes the 17:00 post and filenames carry no time. Refer
     to the same day's other slot in prose ("This evening, 17:00: ...").

  R4 CANONICAL SOURCE. No external code repository may appear anywhere
     under `posts/`. See AGENTS.md.

Only text below the editorial `---` marker counts as reader-facing for R3.
Audit headers above it are internal working notes and may reference other
posts by path.

Run:      python3 tools/publication_gate.py
          python3 tools/publication_gate.py --date 2026-09-12
Depends:  Python 3.8+ standard library, plus `git` on PATH for R1.
Exit:     0 if every rule passes, 1 if any violation is found, 2 if the
          repository state cannot be read.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence

REPO_URL_PREFIX = "https://github.com/QuantumindSSI/systemdesign/blob/main/"

POSTS_DIR = "posts"
EDITORIAL_MARKER = "---"

DATE_IN_NAME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-")
REPO_URL = re.compile(re.escape(REPO_URL_PREFIX) + r"([\w./-]+)")
POST_PATH = re.compile(r"posts/\d{4}-\d{2}-\d{2}-[\w.-]+\.md")

# Phrases that invite a reader to consume material before its post day.
READ_AHEAD_PHRASES = (
    "read ahead",
    "reading ahead",
    "read it early",
    "read them early",
    "skip ahead",
    "sneak peek",
    "early access",
    "before it publishes",
    "before it goes out",
    "ahead of publication",
)

# Owners of external code repositories that must never appear under posts/.
EXTERNAL_REPO = re.compile(
    r"github\.com/(?!QuantumindSSI/)[\w.-]+/[\w.-]+"
    r"|\b(?:rasbt|RUCAIBox|ashishps1|karanpratapsingh|donnemartin|ByteByteGoHq"
    r"|binhnguyennus|Engineer1999|alexeygrigorev|checkcheckzz|OpenRLHF"
    r"|vllm-project|ggml-org|DenisSergeevitch|amanchadha|openai-community)\b"
)


class Violation(NamedTuple):
    """One rule failure, located precisely enough to fix without searching."""

    rule: str
    path: str
    line: int
    detail: str

    def render(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"  [{self.rule}] {where}\n        {self.detail}"


def post_date(path: str) -> Optional[dt.date]:
    """Extract the post date from a filename, or None if it carries no date."""
    match = DATE_IN_NAME.match(os.path.basename(path))
    if not match:
        return None
    try:
        return dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def tracked_files(root: str) -> List[str]:
    """Return every path git tracks, which is exactly what a push publishes.

    Raises:
        SystemExit: if git is unavailable or the directory is not a repo.
    """
    try:
        output = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"cannot read the git index: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return [line for line in output.splitlines() if line]


def split_editorial(text: str) -> str:
    """Return only the reader-facing copy, below the editorial marker.

    A file with no marker is treated as entirely reader-facing, which is
    the conservative choice: it can only produce more checking, not less.
    """
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.strip() == EDITORIAL_MARKER:
            return "\n".join(lines[index + 1:])
    return text


def _body_offset(text: str) -> int:
    """Number of lines above the reader-facing copy, for accurate line numbers."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.strip() == EDITORIAL_MARKER:
            return index + 1
    return 0


def markdown_posts(root: str) -> List[str]:
    """Every markdown file under posts/, relative to root, sorted."""
    found = []
    for directory, _, filenames in os.walk(os.path.join(root, POSTS_DIR)):
        for name in sorted(filenames):
            if name.endswith(".md"):
                found.append(os.path.relpath(os.path.join(directory, name), root))
    return sorted(found)


def check_embargo(root: str, today: dt.date) -> List[Violation]:
    """R1: no post dated after `today` may be tracked by git."""
    violations = []
    for path in tracked_files(root):
        if not path.startswith(POSTS_DIR + "/") or not path.endswith(".md"):
            continue
        date = post_date(path)
        if date is None:
            continue
        if date > today:
            violations.append(
                Violation(
                    "R1",
                    path,
                    0,
                    f"dated {date.isoformat()}, which is after {today.isoformat()}. "
                    "Tracked files are published. Unstage it until its post day.",
                )
            )
    return violations


def linked_documents(root: str) -> List[str]:
    """Every file whose embedded repository URLs must resolve.

    The reader-facing README is included: it is the repository's front
    door, so a dead link in it is seen before any article is.
    """
    documents = list(markdown_posts(root))
    if os.path.exists(os.path.join(root, "README.md")):
        documents.append("README.md")
    return documents


def check_links(root: str) -> List[Violation]:
    """R2: every embedded repository URL resolves to an existing path."""
    violations = []
    for path in linked_documents(root):
        with open(os.path.join(root, path), encoding="utf-8") as handle:
            text = handle.read()
        for number, line in enumerate(text.split("\n"), start=1):
            for match in REPO_URL.finditer(line):
                target = match.group(1)
                if not os.path.exists(os.path.join(root, target)):
                    violations.append(
                        Violation("R2", path, number,
                                  f"links to {target!r}, which does not exist")
                    )
    return violations


def is_forward_reference(referring: str, referenced: str) -> bool:
    """True when `referenced` is not published yet from `referring`'s vantage.

    A reference is backward, and therefore allowed, only when the
    referenced post's date is strictly earlier than the referring post's.
    Same-date references count as forward: the 09:00 post precedes the
    17:00 post and a filename carries no time of day, so treating them as
    backward would let a morning post link an unpublished evening one.

    Undated filenames on either side are treated as forward, because a
    date that cannot be read cannot be shown to be safe.
    """
    here = post_date(referring)
    there = post_date(referenced)
    if here is None or there is None:
        return True
    return there >= here


def check_read_ahead(root: str) -> List[Violation]:
    """R3: no read-ahead invitations, no links to unpublished posts."""
    violations = []
    for path in markdown_posts(root):
        with open(os.path.join(root, path), encoding="utf-8") as handle:
            text = handle.read()
        offset = _body_offset(text)
        for number, line in enumerate(split_editorial(text).split("\n"), start=1):
            lowered = line.lower()
            for phrase in READ_AHEAD_PHRASES:
                if phrase in lowered:
                    violations.append(
                        Violation("R3", path, offset + number,
                                  f"reader-facing copy contains {phrase!r}")
                    )
            for match in POST_PATH.finditer(line):
                target = match.group(0)
                if is_forward_reference(path, target):
                    violations.append(
                        Violation("R3", path, offset + number,
                                  f"points at {target!r}, which is not published "
                                  "yet from this post's date. Refer to it by day "
                                  "and time instead.")
                    )
    return violations


def check_external_repos(root: str) -> List[Violation]:
    """R4: no external code repository appears anywhere under posts/."""
    violations = []
    for path in markdown_posts(root):
        with open(os.path.join(root, path), encoding="utf-8") as handle:
            text = handle.read()
        for number, line in enumerate(text.split("\n"), start=1):
            match = EXTERNAL_REPO.search(line)
            if match:
                violations.append(
                    Violation("R4", path, number,
                              f"external repository reference {match.group(0)!r}")
                )
    return violations


def run_all(root: str, today: dt.date) -> Dict[str, List[Violation]]:
    """Run every rule and return violations grouped by rule id."""
    return {
        "R1": check_embargo(root, today),
        "R2": check_links(root),
        "R3": check_read_ahead(root),
        "R4": check_external_repos(root),
    }


DESCRIPTIONS = {
    "R1": "embargo: no post tracked before its post day",
    "R2": "link resolution: every embedded repo URL exists",
    "R3": "no read-ahead invitations, no links to unpublished posts",
    "R4": "canonical source: no external repository under posts/",
}


def report(results: Dict[str, List[Violation]], today: dt.date) -> int:
    """Print a per-rule report. Returns the process exit code."""
    print(f"publication gate, evaluated for {today.isoformat()}")
    print()
    total = 0
    for rule in ("R1", "R2", "R3", "R4"):
        found = results[rule]
        total += len(found)
        status = "PASS" if not found else f"FAIL ({len(found)})"
        print(f"{rule}  {status:<10} {DESCRIPTIONS[rule]}")
        for violation in found:
            print(violation.render())
    print()
    if total:
        print(f"{total} violation(s). Nothing should be pushed until these are fixed.")
        return 1
    print("All rules passed. Safe to push.")
    return 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--date",
        help="evaluate the embargo as of this ISO date instead of today",
    )
    parser.add_argument(
        "--root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="repository root (defaults to this file's repository)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the gate and report. Returns the process exit code."""
    args = parse_args(argv)
    if args.date:
        try:
            today = dt.date.fromisoformat(args.date)
        except ValueError:
            print(f"--date must be ISO format, got {args.date!r}", file=sys.stderr)
            return 2
    else:
        today = dt.date.today()
    return report(run_all(args.root, today), today)


if __name__ == "__main__":
    sys.exit(main())
