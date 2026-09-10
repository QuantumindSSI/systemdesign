"""Attention does not know what order anything is in, measured.

Companion artifact for the week-3 Friday morning consolidation
(2026-09-11), which restores the Monday 2026-09-07 self-attention post that
never reached readers.

The claim is easy to state and usually left as an assertion: self-attention
is permutation equivariant. Shuffle the input rows and the output rows come
out in exactly the same shuffled order, unchanged. The mechanism has no
concept of first, next or last, and every ordering of the same multiset of
tokens is, to it, the same input.

That is worth measuring rather than repeating, because it is the entire
reason positional encoding exists, and because the two usual escape hatches
turn out to behave differently from how they are usually described.

  ESCAPE HATCH ONE, THE CAUSAL MASK. A decoder mask forbids attending to
  later positions, which is itself indexed by position, so it does break
  equivariance. What it does not do is make the model order-aware in the
  way people mean: the mask constrains WHO may be looked at, not WHERE the
  looker sits among its permitted targets. Measured below.

  ESCAPE HATCH TWO, POSITION EMBEDDING. Adding a learned position row to
  every token, as `lib/embedding.py` does, breaks equivariance properly,
  because the input rows themselves stop being a function of the token
  alone.

Four claims are asserted at the end. Each one can fail, and if it fails the
article that quotes it is wrong and has to change.

  CLAIM 1  Unmasked self-attention is permutation equivariant to machine
           precision. Permuting the input permutes the output identically,
           with no other change.

  CLAIM 2  It follows that two sentences which are anagrams of each other
           at the token level produce the same multiset of output rows. The
           model cannot distinguish them, and this is shown on a real pair
           of token sequences from our own tokenizer.

  CLAIM 3  A causal mask breaks equivariance, so masked outputs are NOT a
           permutation of each other. The mask is genuine positional
           information and is often the reason a decoder-only model half
           works without anything else.

  CLAIM 4  Learned absolute position embedding breaks equivariance too, and
           does so at the input rather than at the mask, which is why it
           composes with any attention pattern including no mask at all.

Determinism: every weight comes from a stated seed and the permutation is
fixed and printed. Two runs produce byte-identical output.

Run:      python3 experiments/week-03/permutation_equivariance.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  under two seconds.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.attention import MultiHeadSelfAttention, causal_mask  # noqa: E402
from lib.bpe import BPETokenizer  # noqa: E402
from lib.embedding import TokenAndPositionEmbedding  # noqa: E402

CORPUS_PATH = os.path.join(REPO_ROOT, "data", "week-03", "tokenizer_corpus.txt")

TOKENIZER_VOCAB = 1024
D_MODEL = 32
NUM_HEADS = 4
MAX_POSITIONS = 64
ATTENTION_SEED = 42
EMBEDDING_SEED = 42

# Two sentences built from the same words in a different order. At the
# token level one is very nearly an anagram of the other, which is the
# point: to unmasked attention they are the same bag of rows.
SENTENCE = "the cache expired before the request arrived"

# A fixed permutation, printed so the reader can apply it by hand.
PERMUTATION = (4, 0, 6, 2, 9, 1, 7, 3, 10, 5, 8)

TOLERANCE = 1e-12


def load_corpus(path):
    """Read the training corpus, or exit with an actionable message."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        print(f"cannot read corpus at {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def permute(rows, order):
    """Return `rows` reordered by `order`, which must be a permutation.

    Raises:
        ValueError: if `order` is not a permutation of range(len(rows)).
    """
    if sorted(order) != list(range(len(rows))):
        raise ValueError(
            f"order {order} is not a permutation of 0..{len(rows) - 1}"
        )
    return [list(rows[index]) for index in order]


def largest_difference(left, right):
    """Return the largest absolute element-wise gap between two matrices.

    Raises:
        ValueError: if the shapes differ, because comparing matrices of
            different shapes silently would hide the very failure this
            script exists to detect.
    """
    if len(left) != len(right):
        raise ValueError(f"row counts differ: {len(left)} and {len(right)}")
    worst = 0.0
    for left_row, right_row in zip(left, right):
        if len(left_row) != len(right_row):
            raise ValueError(
                f"widths differ: {len(left_row)} and {len(right_row)}"
            )
        for a, b in zip(left_row, right_row):
            worst = max(worst, abs(a - b))
    return worst


def mean_magnitude(rows):
    """Mean absolute value over every element, as a scale reference.

    A raw gap of 1e-17 or 8e-02 means nothing without knowing how large
    the outputs are. Everything here is untrained and initialised small,
    so gaps are reported against this.

    Raises:
        ValueError: if `rows` is empty.
    """
    values = [abs(value) for row in rows for value in row]
    if not values:
        raise ValueError("mean_magnitude needs at least one value")
    return sum(values) / len(values)


def row_multiset(rows, places=9):
    """Return the rows as a sorted tuple of rounded tuples.

    Two matrices with the same multiset of rows are the same bag of
    vectors in a different order. Rounding is needed because the two
    computations sum their products in different orders, so identical
    mathematics can land a few ulps apart.
    """
    return tuple(sorted(tuple(round(value, places) for value in row) for row in rows))


def run_unmasked(attention, embedded):
    """Compare attention(permuted input) against permute(attention(input))."""
    baseline, _ = attention.forward(embedded)
    permuted_input = permute(embedded, PERMUTATION)
    from_permuted, _ = attention.forward(permuted_input)
    expected = permute(baseline, PERMUTATION)
    gap = largest_difference(from_permuted, expected)
    scale = mean_magnitude(baseline)
    print("UNMASKED: is attention permutation equivariant?")
    print(f"  sequence length          {len(embedded)}")
    print(f"  permutation              {PERMUTATION}")
    print(f"  mean |output value|      {scale:.6f}   (the scale to read gaps against)")
    print(f"  largest gap between attention(P x) and P attention(x): {gap:.3e}")
    print(f"  gap as a share of scale  {gap / scale:.3e}")
    print(f"  same multiset of rows    "
          f"{row_multiset(baseline) == row_multiset(from_permuted)}")
    return gap


def run_masked(attention, embedded):
    """Repeat the comparison with a causal mask in place."""
    length = len(embedded)
    mask = causal_mask(length)
    baseline, _ = attention.forward(embedded, mask)
    permuted_input = permute(embedded, PERMUTATION)
    from_permuted, _ = attention.forward(permuted_input, mask)
    expected = permute(baseline, PERMUTATION)
    gap = largest_difference(from_permuted, expected)
    same_bag = row_multiset(baseline) == row_multiset(from_permuted)
    scale = mean_magnitude(baseline)
    print()
    print("CAUSAL MASK: does forbidding the future restore order awareness?")
    print(f"  mean |output value|      {scale:.6f}")
    print(f"  largest gap between attention(P x) and P attention(x): {gap:.3e}")
    print(f"  gap as a share of scale  {gap / scale:.3e}")
    print(f"  same multiset of rows    {same_bag}")
    print("  the mask is indexed by position, so it is itself positional")
    print("  information. It constrains who may be looked at, not where the")
    print("  looker sits among the positions it is allowed to look at.")
    return gap, same_bag


def run_token_only(tokenizer, attention, ids):
    """Show two token orderings colliding when only token rows are used."""
    layer = TokenAndPositionEmbedding(
        tokenizer.vocab_size, MAX_POSITIONS, D_MODEL, EMBEDDING_SEED
    )
    token_rows = layer.tokens.lookup(ids)
    shuffled_ids = [ids[index] for index in PERMUTATION]
    shuffled_rows = layer.tokens.lookup(shuffled_ids)
    original_out, _ = attention.forward(token_rows)
    shuffled_out, _ = attention.forward(shuffled_rows)
    same_bag = row_multiset(original_out) == row_multiset(shuffled_out)
    print()
    print("TOKEN ROWS ONLY: two orderings of the same tokens")
    print(f"  ids in order             {ids}")
    print(f"  ids shuffled             {shuffled_ids}")
    print(f"  same multiset of output rows: {same_bag}")
    print("  the two sequences are, to this mechanism, the same input")
    return layer, same_bag


def run_with_positions(layer, attention, ids):
    """Show position embedding breaking the collision at the input."""
    in_order = layer.forward(ids)
    shuffled_ids = [ids[index] for index in PERMUTATION]
    shuffled = layer.forward(shuffled_ids)
    original_out, _ = attention.forward(in_order)
    shuffled_out, _ = attention.forward(shuffled)
    same_bag = row_multiset(original_out) == row_multiset(shuffled_out)
    gap = largest_difference(
        original_out, permute(shuffled_out, invert(PERMUTATION))
    )
    scale = mean_magnitude(original_out)
    print()
    print("TOKEN ROWS PLUS POSITION ROWS: the same two orderings")
    print(f"  same multiset of output rows: {same_bag}")
    print(f"  mean |output value|      {scale:.6f}")
    print(f"  largest gap after undoing the shuffle: {gap:.3e}")
    print(f"  gap as a share of scale  {gap / scale:.3e}")
    print("  position was added before attention ran, so the input rows")
    print("  themselves are no longer a function of the token alone")
    return same_bag, gap


def invert(order):
    """Return the inverse permutation of `order`."""
    inverse = [0] * len(order)
    for index, target in enumerate(order):
        inverse[target] = index
    return tuple(inverse)


def check_claims(unmasked_gap, masked, token_only_same, positional):
    """Assert the four claims the article makes. Raises AssertionError."""
    assert unmasked_gap < TOLERANCE, (
        f"CLAIM 1 died: attention(P x) and P attention(x) differ by "
        f"{unmasked_gap:.3e}, which is above {TOLERANCE:.0e}. Unmasked "
        "attention is not permutation equivariant in this implementation"
    )

    assert token_only_same, (
        "CLAIM 2 died: two orderings of the same token ids produced "
        "different multisets of output rows without any position "
        "information, so the collision the article describes does not occur"
    )

    masked_gap, masked_same_bag = masked
    assert masked_gap > TOLERANCE, (
        f"CLAIM 3 died: with a causal mask, attention(P x) still equals "
        f"P attention(x) to within {masked_gap:.3e}, so the mask carried no "
        "positional information"
    )
    assert not masked_same_bag, (
        "CLAIM 3 died: the masked outputs are still the same multiset of "
        "rows, so the mask changed the ordering but not the content"
    )

    positional_same_bag, positional_gap = positional
    assert not positional_same_bag, (
        "CLAIM 4 died: adding position rows left the two orderings producing "
        "the same multiset of outputs, so the position table is not reaching "
        "the attention computation"
    )
    assert positional_gap > TOLERANCE, (
        f"CLAIM 4 died: undoing the shuffle recovered the original output to "
        f"within {positional_gap:.3e}, which means position contributed "
        "nothing distinguishable"
    )


def main():
    """Run all four comparisons, then verify."""
    corpus = load_corpus(CORPUS_PATH)
    tokenizer = BPETokenizer.train(corpus, TOKENIZER_VOCAB)
    ids = tokenizer.encode(SENTENCE)
    if len(ids) != len(PERMUTATION):
        print(
            f"{SENTENCE!r} encodes to {len(ids)} tokens but PERMUTATION has "
            f"{len(PERMUTATION)} entries. The fixed permutation is printed in "
            "the article, so it must match the sentence exactly.",
            file=sys.stderr,
        )
        return 2

    attention = MultiHeadSelfAttention(D_MODEL, NUM_HEADS, ATTENTION_SEED)
    layer = TokenAndPositionEmbedding(
        tokenizer.vocab_size, MAX_POSITIONS, D_MODEL, EMBEDDING_SEED
    )
    embedded = layer.forward(ids)

    print(f"sentence: {SENTENCE!r}")
    print(f"pieces:   {tokenizer.token_pieces(SENTENCE)}")
    print(f"d_model {D_MODEL}, heads {NUM_HEADS}, attention seed "
          f"{ATTENTION_SEED}, embedding seed {EMBEDDING_SEED}")
    print()

    unmasked_gap = run_unmasked(attention, embedded)
    masked = run_masked(attention, embedded)
    layer, token_only_same = run_token_only(tokenizer, attention, ids)
    positional = run_with_positions(layer, attention, ids)

    try:
        check_claims(unmasked_gap, masked, token_only_same, positional)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
