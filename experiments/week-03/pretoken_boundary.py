"""What the pre-token boundary costs, and what it buys, measured.

Companion artifact for the week-3 Wednesday case study (2026-09-09).

Radford et al., in the GPT-2 paper, report a problem and a fix. The
problem: applying byte pair encoding straight to a byte sequence produces
"sub-optimal merges", because the algorithm is a greedy frequency
heuristic and frequency does not respect word boundaries. They observed
BPE learning many versions of the same common word, since a word occurs
with a full stop after it, and with an exclamation mark, and with a
question mark. Each variant claims its own vocabulary slot. The fix: stop
merges crossing a character-category boundary, with one exception for
spaces.

That is a design decision with a cost on both sides, and a decision with
a cost on both sides should be measured rather than repeated. This script
trains our own byte-level BPE (`lib/bpe.py`) on our own corpus
(`data/week-03/tokenizer_corpus.txt`) under four boundary rules, from the
most permissive to the strictest, and reports what each one does to the
vocabulary and to the compression.

  lines          boundary at newlines only. Merges may cross spaces, so a
                 phrase like "of the" is a mergeable pair like any other.
  whitespace     boundary at whitespace. This is what `lib/bpe.py` ships
                 as its default and what every earlier week-3 artifact
                 used.
  categories     boundary at whitespace and at letter/digit/other
                 transitions, with a single leading space allowed to
                 attach forward. This is the rule the paper describes.
  category-runs  the same, minus the space exception, so the value of the
                 exception can be read off rather than assumed.

Four claims are asserted at the end. Each one can fail, and if it fails
the article that quotes it is wrong and has to change.

  CLAIM 1  Only the permissive rule spends vocabulary slots on tokens
           that span a word boundary. The other three spend exactly zero,
           by construction, and this asserts the construction works.

  CLAIM 2  The whitespace rule, which is the obvious choice and our own
           default, still spends slots on tokens that mix letters with
           punctuation. The category rule spends exactly zero. This is
           the paper's observation, reproduced on our own corpus with our
           own implementation.

  CLAIM 3  Removing the boundary does not buy compression. The permissive
           rule is allowed to merge strictly more pairs than the
           whitespace rule and still ends up with fewer bytes per token,
           because it spends its budget on phrases that occur in few
           places instead of words that occur everywhere.

  CLAIM 4  The space exception is load-bearing, not a detail. Dropping it
           costs more than a quarter of the compression on the full
           corpus, which is what "significantly improves the compression
           efficiency" looks like in numbers.

Determinism: training is a pure function of (text, vocab_size,
pre_tokenizer), ties broken by the smallest pair. No seed, no sampling,
no wall-clock dependence. Two runs produce byte-identical output.

Run:      python3 experiments/week-03/pretoken_boundary.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about forty seconds, almost all of it the permissive rule,
          which has 258,125 symbols in its longest chunk type instead of
          the seven or so a word has.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.bpe import (  # noqa: E402
    BYTE_VOCAB_SIZE,
    BPETokenizer,
    char_category,
    pre_tokenize,
    pre_tokenize_categories,
    pre_tokenize_category_runs,
    pre_tokenize_lines,
)

CORPUS_PATH = os.path.join(REPO_ROOT, "data", "week-03", "tokenizer_corpus.txt")

VOCAB_SIZE = 1024

# The permissive rule's cost grows with the length of a chunk, and its
# chunks are whole lines. On the full corpus it takes about four minutes,
# which is too long to ask anyone to run, so the four-way ladder uses a
# prefix and the number is stated everywhere it is quoted.
SLICE_BYTES = 40000

RULES = (
    ("lines", pre_tokenize_lines),
    ("whitespace", pre_tokenize),
    ("categories", pre_tokenize_categories),
    ("category-runs", pre_tokenize_category_runs),
)

# The three rules cheap enough to run over the whole corpus.
FULL_CORPUS_RULES = ("whitespace", "categories", "category-runs")

# Held out of every table, used to show where the boundaries land.
HELD_OUT = "the cache expired. the cache expired! order_id=8f3a91c4"


def load_corpus(path):
    """Read the training corpus, or exit with an actionable message.

    Returns:
        The corpus text as a str.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        print(f"cannot read corpus at {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def learned_pieces(tokenizer):
    """Return the text of every token the tokenizer learned, ids 256 and up.

    The 256 base bytes are not learned and are excluded: they cost no
    decision and are present in every vocabulary regardless of the rule.
    """
    return [
        tokenizer.vocab[token_id].decode("utf-8", errors="replace")
        for token_id in range(BYTE_VOCAB_SIZE, tokenizer.vocab_size)
    ]


def body(piece):
    """Strip one leading space, the one the space exception allows.

    A leading space is part of the rule rather than a violation of it, so
    it must not make every token look like it mixes categories.
    """
    return piece[1:] if piece.startswith(" ") else piece


def spans_word_boundary(piece):
    """True if the token contains whitespace with non-whitespace on both sides.

    This is what "the vocabulary filled up with phrases" means, made
    checkable: the token covers the end of one word and the start of
    another, so it can only ever match that exact pairing.
    """
    stripped = piece.strip()
    return any(character.isspace() for character in stripped)


def mixes_categories(piece):
    """True if the token's body spans more than one character category."""
    return len({char_category(character) for character in body(piece)}) > 1


def letter_core(piece):
    """Return the leading run of letters in the token's body, or "".

    Used to group `dog.` with `dog!`: both have the core "dog", so they
    are two slots describing one word.
    """
    text = body(piece)
    core = []
    for character in text:
        if char_category(character) != "letter":
            break
        core.append(character)
    return "".join(core)


def variant_families(pieces):
    """Group mixed tokens that share a letter core, the `dog. dog!` case.

    Returns:
        A dict mapping a letter core to the sorted list of tokens built on
        it, including only cores carrying two or more such tokens. A
        family of k members occupies k slots to say one word, so k - 1 of
        them are the cost the boundary rule removes.
    """
    families = {}
    for piece in pieces:
        if not mixes_categories(piece):
            continue
        core = letter_core(piece)
        if not core:
            continue
        families.setdefault(core, []).append(piece)
    return {
        core: sorted(members)
        for core, members in families.items()
        if len(members) >= 2
    }


def measure(text, rule_name, rule, vocab_size):
    """Train under one boundary rule and count what the vocabulary holds.

    Args:
        text: the corpus to train and measure on.
        rule_name: the label used in the tables.
        rule: a pre-tokenizer from `lib.bpe`.
        vocab_size: the target vocabulary size.

    Returns:
        A dict of measurements. `tokens` is never zero for a non-empty
        corpus, so `bytes_per_token` cannot divide by zero.
    """
    tokenizer = BPETokenizer.train(text, vocab_size, pre_tokenizer=rule)
    pieces = learned_pieces(tokenizer)
    token_count = len(tokenizer.encode(text))
    byte_count = len(text.encode("utf-8"))
    assert token_count > 0, f"{rule_name} encoded a non-empty corpus to nothing"
    families = variant_families(pieces)
    return {
        "rule": rule_name,
        "merges": len(tokenizer.merges),
        "tokens": token_count,
        "bytes_per_token": byte_count / token_count,
        "phrase_slots": sum(1 for piece in pieces if spans_word_boundary(piece)),
        "mixed_slots": sum(1 for piece in pieces if mixes_categories(piece)),
        "variant_slots": sum(len(members) - 1 for members in families.values()),
        "families": families,
        "tokenizer": tokenizer,
    }


def print_table(title, byte_count, rows):
    """Print one boundary-rule table."""
    print(title)
    print(f"corpus: {byte_count} bytes, vocabulary {VOCAB_SIZE}")
    print()
    header = (
        f"{'boundary rule':>14} {'merges':>7} {'tokens':>8} {'bytes/token':>12} "
        f"{'phrase':>7} {'mixed':>6} {'variant':>8}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['rule']:>14} {row['merges']:>7} {row['tokens']:>8} "
            f"{row['bytes_per_token']:>12.3f} {row['phrase_slots']:>7} "
            f"{row['mixed_slots']:>6} {row['variant_slots']:>8}"
        )


def print_wasted_slots(rows):
    """Show the actual tokens each rule spent on phrases and on variants."""
    for row in rows:
        pieces = learned_pieces(row["tokenizer"])
        phrases = [piece for piece in pieces if spans_word_boundary(piece)]
        print()
        print(f"{row['rule']}: {len(phrases)} slot(s) spanning a word boundary")
        if phrases:
            print(f"  {[piece for piece in phrases[:8]]}")
        families = row["families"]
        print(f"{row['rule']}: {len(families)} letter core(s) holding two or more "
              "punctuated variants")
        for core in sorted(families)[:6]:
            print(f"  {core!r}: {families[core]}")


def print_segmentation(rows, text):
    """Show how each rule cuts up one held-out string."""
    print()
    print(f"segmentation of {text!r}:")
    for row in rows:
        pieces = row["tokenizer"].token_pieces(text)
        print(f"  {row['rule']:>14}  {len(pieces):3d} tokens  {pieces}")


def check_claims(slice_rows, full_rows):
    """Assert the four claims the article makes. Raises AssertionError."""
    by_rule = {row["rule"]: row for row in slice_rows}
    full = {row["rule"]: row for row in full_rows}

    assert by_rule["lines"]["phrase_slots"] > 0, (
        "CLAIM 1 died: the permissive rule learned no token spanning a word "
        "boundary, so there is nothing for a boundary to prevent"
    )
    for rule in ("whitespace", "categories", "category-runs"):
        assert by_rule[rule]["phrase_slots"] == 0, (
            f"CLAIM 1 died: {rule} learned "
            f"{by_rule[rule]['phrase_slots']} token(s) spanning a word boundary"
        )

    assert full["whitespace"]["mixed_slots"] > 0, (
        "CLAIM 2 died: the whitespace rule spent no slots on mixed-category "
        "tokens, so the paper's observation does not reproduce here"
    )
    assert full["categories"]["mixed_slots"] == 0, (
        f"CLAIM 2 died: the category rule spent "
        f"{full['categories']['mixed_slots']} slot(s) on mixed-category tokens"
    )

    assert (
        by_rule["lines"]["bytes_per_token"] < by_rule["whitespace"]["bytes_per_token"]
    ), (
        "CLAIM 3 died: the permissive rule compressed at least as well as the "
        f"whitespace rule, {by_rule['lines']['bytes_per_token']:.3f} against "
        f"{by_rule['whitespace']['bytes_per_token']:.3f} bytes per token"
    )

    penalty = (
        full["category-runs"]["tokens"] - full["categories"]["tokens"]
    ) / full["categories"]["tokens"]
    assert penalty > 0.25, (
        f"CLAIM 4 died: dropping the space exception cost only {penalty:.1%} "
        "more tokens, which is not a significant improvement"
    )


def main():
    """Measure both tables, print them, then verify the article's claims."""
    corpus = load_corpus(CORPUS_PATH)
    corpus_slice = corpus[:SLICE_BYTES]

    slice_rows = [
        measure(corpus_slice, name, rule, VOCAB_SIZE) for name, rule in RULES
    ]
    print_table(
        "TABLE 1: the boundary ladder, on a prefix of the corpus",
        len(corpus_slice.encode("utf-8")),
        slice_rows,
    )
    print_wasted_slots(slice_rows)

    full_rows = [
        measure(corpus, name, rule, VOCAB_SIZE)
        for name, rule in RULES
        if name in FULL_CORPUS_RULES
    ]
    print()
    print()
    print_table(
        "TABLE 2: the three practical rules, on the whole corpus",
        len(corpus.encode("utf-8")),
        full_rows,
    )
    print_segmentation(full_rows, HELD_OUT)

    full = {row["rule"]: row for row in full_rows}
    penalty = (
        full["category-runs"]["tokens"] - full["categories"]["tokens"]
    ) / full["categories"]["tokens"]
    cost = (
        full["categories"]["tokens"] - full["whitespace"]["tokens"]
    ) / full["whitespace"]["tokens"]
    print()
    print(f"the category boundary costs {cost:+.2%} tokens against whitespace")
    print(f"dropping the space exception costs {penalty:+.2%} tokens")

    try:
        check_claims(slice_rows, full_rows)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
