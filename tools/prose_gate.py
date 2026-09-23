"""Enforce the mechanically checkable prose rules over reader-facing copy.

`AGENTS.md` lists seven prose style rules and says of three of them that
they "are mechanically checkable and should be verified by grep over the
reader-facing copy before any post is staged". Grep by hand is a step that
gets skipped, so this is that grep, written once and testable.

Three rules are checked, and only below the editorial `---` marker, because
audit headers are internal working notes.

  P1 NO EM DASHES. U+2014 anywhere in reader-facing copy. This restates
     C-08 of the persona constitution and carries the same zero tolerance.

  P2 NO SENTENCE OPENS WITH A CONJUNCTION. "And", "But", "So", "Or",
     "Because", "Yet" and "Nor" never begin a sentence, headings included.
     Detection is deliberately conservative about what counts as a
     sentence start: the beginning of a line, the beginning of a heading,
     the beginning of a list item, or immediately after a sentence-ending
     mark followed by a space.

  P3 NO COLLAPSED CONTRASTIVE FRAMING. Constructions of the shape "not X,
     Y" and "not X. It is Y" read as a sequence of self-corrections rather
     than one continuous thought. This catches the common written forms and
     cannot catch every paraphrase, so a pass here is a floor rather than a
     certificate.

WHAT IS DELIBERATELY NOT CHECKED. Fenced code blocks are skipped entirely.
Code is quoted verbatim from committed artifacts, prose rules do not apply
to it, and rule 7 forbids altering it. Inline code spans are skipped for
the same reason. Quoted material from a cited paper is NOT skipped,
because a quotation containing an em dash would still put one in front of
a reader, and the correct fix is to paraphrase around it.

Run:      python3 tools/prose_gate.py
          python3 tools/prose_gate.py posts/2026-09-14-mon-am-essay.md
Depends:  Python 3.8+ standard library.
Exit:     0 if every rule passes, 1 if any violation is found, 2 if a file
          cannot be read.
"""

import argparse
import os
import re
import sys
from typing import List, NamedTuple, Optional, Sequence

POSTS_DIR = "posts"
EDITORIAL_MARKER = "---"

EM_DASH = "\u2014"

CONJUNCTIONS = ("And", "But", "So", "Or", "Because", "Yet", "Nor")

# A sentence start is the start of a line, optionally after markdown
# heading hashes, list bullets, blockquote markers or emphasis, or a point
# just after a sentence-ending mark and a space.
SENTENCE_START = re.compile(
    r"(?:^|(?<=[.!?])\s)[\s>#*_\-]*(" + "|".join(CONJUNCTIONS) + r")\b"
)

# "not X, Y" and "not X. It is Y", the two written forms of the collapsed
# antithesis. The comma form is restricted to short spans so that ordinary
# negation followed by a subordinate clause is not swept up.
ANTITHESIS = (
    re.compile(r"\bnot\s+(?:a|an|the)?\s*[\w' ]{1,24},\s*(?:it'?s|its)\b"),
    re.compile(r"\b[Nn]ot\s+[\w']{1,18},\s+[\w']{1,18}\.", re.UNICODE),
    re.compile(r"\b[Ii]t\s+is\s+not\s+[\w' ]{1,30}\.\s+It\s+is\s+"),
    re.compile(r"\b[Nn]ot\s+because\b[^.]{0,80}\.\s*Because\b"),
)

FENCE = re.compile(r"^\s*```")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")


class Violation(NamedTuple):
    """One rule failure, located precisely enough to fix without searching."""

    rule: str
    path: str
    line: int
    detail: str

    def render(self) -> str:
        return f"  [{self.rule}] {self.path}:{self.line}\n        {self.detail}"


DESCRIPTIONS = {
    "P1": "no em dashes in reader-facing copy",
    "P2": "no sentence opens with a conjunction",
    "P3": "no collapsed contrastive framing",
}


def reader_facing_lines(text: str) -> List[tuple]:
    """Return (line number, line) for prose below the editorial marker.

    Fenced code blocks are dropped. Inline code spans and link targets are
    blanked rather than removed, so column positions stay usable and a URL
    containing a hyphen cannot be mistaken for prose.

    A file with no marker is treated as entirely reader-facing, which is
    the conservative choice: it can only produce more checking, not less.
    """
    lines = text.split("\n")
    start = 0
    for index, line in enumerate(lines):
        if line.strip() == EDITORIAL_MARKER:
            start = index + 1
            break
    kept = []
    in_fence = False
    for offset, line in enumerate(lines[start:], start=start + 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cleaned = INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)
        cleaned = LINK_TARGET.sub(lambda m: " " * len(m.group(0)), cleaned)
        kept.append((offset, cleaned))
    return kept


def check_text(path: str, text: str) -> List[Violation]:
    """Run every prose rule over one document's reader-facing copy."""
    violations: List[Violation] = []
    for number, line in reader_facing_lines(text):
        if EM_DASH in line:
            violations.append(
                Violation("P1", path, number, "contains an em dash (U+2014)")
            )
        for match in SENTENCE_START.finditer(line):
            violations.append(
                Violation(
                    "P2",
                    path,
                    number,
                    f"sentence opens with {match.group(1)!r}: "
                    f"{line[match.start():match.start() + 72].strip()!r}",
                )
            )
        for pattern in ANTITHESIS:
            match = pattern.search(line)
            if match:
                violations.append(
                    Violation(
                        "P3",
                        path,
                        number,
                        f"collapsed contrast: {match.group(0).strip()!r}",
                    )
                )
                break
    return violations


def check_file(path: str) -> List[Violation]:
    """Read one file and check it.

    Raises:
        SystemExit: if the file cannot be read, because silently skipping
            an unreadable post would report a pass it did not earn.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return check_text(path, text)


def markdown_posts(root: str) -> List[str]:
    """Every markdown file under posts/, relative to root, sorted."""
    found = []
    posts_root = os.path.join(root, POSTS_DIR)
    for directory, _, filenames in os.walk(posts_root):
        for name in sorted(filenames):
            if name.endswith(".md"):
                found.append(
                    os.path.relpath(os.path.join(directory, name), root)
                )
    return sorted(found)


def report(violations: Sequence[Violation], checked: int) -> int:
    """Print a per-rule report. Returns the process exit code."""
    print(f"prose gate, {checked} document(s) checked")
    print()
    total = 0
    for rule in ("P1", "P2", "P3"):
        found = [v for v in violations if v.rule == rule]
        total += len(found)
        status = "PASS" if not found else f"FAIL ({len(found)})"
        print(f"{rule}  {status:<10} {DESCRIPTIONS[rule]}")
        for violation in found:
            print(violation.render())
    print()
    if total:
        print(f"{total} violation(s). Fix before staging.")
        return 1
    print("All prose rules passed.")
    return 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="files to check (defaults to every markdown file under posts/)",
    )
    parser.add_argument(
        "--root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="repository root",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the gate and report. Returns the process exit code."""
    args = parse_args(argv)
    if args.paths:
        targets = list(args.paths)
    else:
        targets = [
            os.path.join(args.root, path) for path in markdown_posts(args.root)
        ]
    violations: List[Violation] = []
    for path in targets:
        violations.extend(check_file(path))
    return report(violations, len(targets))


if __name__ == "__main__":
    sys.exit(main())
