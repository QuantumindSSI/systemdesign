"""What a bigger tokenizer vocabulary actually buys, measured.

Companion artifact for the week-3 Sunday kickoff (2026-09-06).

The intuition most people carry is that a bigger vocabulary means fewer
tokens, roughly in proportion. This script trains our own byte-level BPE
tokenizer (`lib/bpe.py`) on our own corpus (`data/week-03/`) at five
vocabulary sizes and measures what each one costs and returns.

Three claims are asserted at the end. Each one can fail, and if it fails
the article that quotes it is wrong and has to change.

  CLAIM 1  More vocabulary never lengthens the encoding. Merges only ever
           replace two symbols with one, so the token count is monotone
           non-increasing in vocabulary size. This is the easy one, and it
           is asserted because it is the floor the other two stand on.

  CLAIM 2  The returns diminish, and they diminish every single time. Each
           doubling of the vocabulary removes a smaller FRACTION of the
           remaining tokens than the doubling before it. This is the claim
           that contradicts the linear intuition.

  CLAIM 3  A long digit string stays fragmented even at the largest
           vocabulary trained here. Merges are learned by frequency, and
           an arbitrary seven-digit number is not frequent, so nothing in
           the merge table ever learns it. The model does not receive your
           number; it receives the pieces frequency happened to leave.

Determinism: training is a pure function of (corpus, vocab_size), tie
broken by the smallest pair. No seed, no sampling, no wall-clock
dependence. Two runs produce byte-identical output.

Run:      python3 experiments/week-03/vocab_vs_tokens.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about one minute, dominated by training at vocab 2048 and 4096.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.bpe import BYTE_VOCAB_SIZE, BPETokenizer  # noqa: E402

CORPUS_PATH = os.path.join(REPO_ROOT, "data", "week-03", "tokenizer_corpus.txt")

VOCAB_SIZES = (BYTE_VOCAB_SIZE, 512, 1024, 2048, 4096)

# Strings held out of the measurement table, used to show segmentation.
# None of these is drawn from the corpus verbatim.
HELD_OUT = (
    "the cache expired before the request arrived",
    "the invoice total was 1234567 dollars",
    "order_id=8f3a91c4 status=PENDING",
    "unhappiest",
)

# The digit string CLAIM 3 is about.
NUMBER_SAMPLE = "1234567"


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


def measure(corpus):
    """Train at every vocabulary size and measure the corpus token count.

    Returns:
        A list of dicts with keys: vocab_size, merges, tokens, bytes_per_token.
    """
    corpus_bytes = len(corpus.encode("utf-8"))
    rows = []
    tokenizers = {}
    for vocab_size in VOCAB_SIZES:
        tokenizer = BPETokenizer.train(corpus, vocab_size)
        tokens = len(tokenizer.encode(corpus))
        rows.append(
            {
                "vocab_size": tokenizer.vocab_size,
                "requested": vocab_size,
                "merges": len(tokenizer.merges),
                "tokens": tokens,
                "bytes_per_token": corpus_bytes / tokens,
            }
        )
        tokenizers[vocab_size] = tokenizer
    return rows, tokenizers, corpus_bytes


def print_table(rows, corpus_bytes):
    """Print the vocabulary against token-count table with per-step deltas."""
    print(f"corpus: {corpus_bytes} bytes, {corpus_bytes / 1024:.1f} KiB")
    print()
    header = f"{'vocab':>7} {'merges':>7} {'tokens':>9} {'bytes/token':>12} {'cut vs previous':>16}"
    print(header)
    print("-" * len(header))
    previous = None
    for row in rows:
        if previous is None:
            cut = "baseline"
        else:
            cut = f"{100.0 * (previous - row['tokens']) / previous:.1f}%"
        print(
            f"{row['vocab_size']:>7} {row['merges']:>7} {row['tokens']:>9} "
            f"{row['bytes_per_token']:>12.2f} {cut:>16}"
        )
        previous = row["tokens"]


def print_segmentation(tokenizer, vocab_size):
    """Show how the largest tokenizer cuts up held-out strings."""
    print()
    print(f"segmentation at vocab {vocab_size}, on strings held out of the table:")
    for text in HELD_OUT:
        pieces = tokenizer.token_pieces(text)
        print(f"  {len(pieces):3d} tokens  {pieces}")


def fractional_cuts(rows):
    """Return the fraction of tokens removed at each step after the first."""
    cuts = []
    for previous, current in zip(rows, rows[1:]):
        cuts.append((previous["tokens"] - current["tokens"]) / previous["tokens"])
    return cuts


def check_claims(rows, largest):
    """Assert the three claims the kickoff makes. Raises AssertionError."""
    token_counts = [row["tokens"] for row in rows]
    for previous, current in zip(token_counts, token_counts[1:]):
        assert current <= previous, (
            f"CLAIM 1 died: token count rose from {previous} to {current} "
            "when the vocabulary grew"
        )

    cuts = fractional_cuts(rows)
    for earlier, later in zip(cuts, cuts[1:]):
        assert later < earlier, (
            f"CLAIM 2 died: a later doubling cut {later:.4f} of the tokens, "
            f"which is not less than the previous doubling's {earlier:.4f}"
        )

    number_tokens = largest.token_pieces(NUMBER_SAMPLE)
    assert len(number_tokens) > 1, (
        f"CLAIM 3 died: {NUMBER_SAMPLE!r} became a single token {number_tokens}"
    )
    assert "".join(number_tokens) == NUMBER_SAMPLE, (
        "CLAIM 3 died: the token pieces do not reconstruct the number"
    )


def main():
    """Measure, print, then verify the article's claims against the numbers."""
    corpus = load_corpus(CORPUS_PATH)
    rows, tokenizers, corpus_bytes = measure(corpus)
    print_table(rows, corpus_bytes)

    largest_requested = VOCAB_SIZES[-1]
    largest = tokenizers[largest_requested]
    print_segmentation(largest, largest.vocab_size)

    print()
    print(f"{NUMBER_SAMPLE!r} at vocab {largest.vocab_size}: "
          f"{largest.token_pieces(NUMBER_SAMPLE)}")

    cuts = fractional_cuts(rows)
    print()
    print("fraction of remaining tokens removed by each step: "
          + ", ".join(f"{cut * 100:.1f}%" for cut in cuts))

    try:
        check_claims(rows, largest)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
