"""Byte pair encoding, traced merge by merge, plus the two traps.

Companion artifact for the week-3 Wednesday code deep-dive (2026-09-09).

The morning's case study is about where the merge boundary goes. This is
about what happens inside the boundary: how merges are learned, in what
order they are replayed, and the two places an implementation that looks
correct is not.

Part one traces training on a corpus small enough to check by hand. Every
round prints the winning pair, its count, and the string the new symbol
now stands for.

Part two is the tie-break trap. When two pairs are equally frequent, some
pair still has to win. `max(pair_counts, key=pair_counts.get)` returns the
first key holding the maximum in dictionary insertion order, and insertion
order depends on the order the corpus happened to be read in. The result
is a tokenizer that is not a function of its training data. `lib/bpe.py`
breaks ties on the numerically smallest pair instead, which depends on
nothing but the pair.

Part three is the encode-order trap. Training learns merges in an order.
Encoding must replay them in that order, which is not the same as walking
the string left to right and taking the first merge that fits. Both
implementations run, both round trip, and they disagree.

Three claims are asserted at the end. Each one can fail, and if it fails
the article that quotes it is wrong and has to change.

  CLAIM 1  The stable tie-break makes training a function of the corpus.
           Shuffling the order the word types were counted in changes
           nothing. The unstable tie-break changes its answer.

  CLAIM 2  Replaying merges by rank and scanning left to right are
           different algorithms, not two spellings of one. They disagree
           on hundreds of chunk types, and left to right costs more
           tokens for the same merge table.

  CLAIM 3  Encoding by rank round trips exactly, on the training corpus
           and on text the tokenizer has never seen, including non-ASCII.

Determinism: everything here is a pure function of the corpus and the
stated shuffle seed. Two runs produce byte-identical output.

Run:      python3 experiments/week-03/bpe_trace.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about three seconds.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import os
import random
import sys
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.bpe import (  # noqa: E402
    BYTE_VOCAB_SIZE,
    BPETokenizer,
    _best_pair,
    _count_pairs,
    _merge_once,
    pre_tokenize,
)

CORPUS_PATH = os.path.join(REPO_ROOT, "data", "week-03", "tokenizer_corpus.txt")

# Small enough that every merge can be checked by eye.
TINY_CORPUS = (
    "the cache expired. the cache expired again. "
    "the request missed the cache and the request waited."
)
TINY_VOCAB = 268

# The tie-break trap needs enough word types for ties to occur and few
# enough merges to run four times over.
TIE_BREAK_BYTES = 40000
TIE_BREAK_VOCAB = 320
SHUFFLE_SEED = 42
SHUFFLE_TRIALS = 4

# The encode-order trap.
ENCODE_VOCAB = 512
ENCODE_SAMPLE_BYTES = 60000

ROUND_TRIP_CASES = (
    "",
    " ",
    "the cache expired before the request arrived",
    "A totally unseen sentence, with punctuation!",
    "caf\u00e9 na\u00efve \u4f60\u597d \U0001f600",
    "order_id=8f3a91c4 status=PENDING",
)


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


def show(piece_bytes):
    """Render a token's bytes for display, never for a round trip."""
    return repr(piece_bytes.decode("utf-8", errors="replace"))


def trace_training(text, vocab_size):
    """Train with the textbook recount, printing every round.

    Uses `train_merges_naive`'s algorithm inline rather than calling it,
    because the point of this function is to show the loop body. The
    merges it produces are asserted equal to the library's.

    Returns:
        The learned merge list, in order.
    """
    counts = BPETokenizer.word_counts(text)
    vocab = {index: bytes([index]) for index in range(BYTE_VOCAB_SIZE)}
    merges = []
    print(f"corpus: {len(text)} characters, {len(counts)} distinct word types")
    print()
    print(f"{'round':>5} {'new id':>7} {'count':>6}  {'pair':<24} stands for")
    print("-" * 72)
    for new_id in range(BYTE_VOCAB_SIZE, vocab_size):
        pair_counts = _count_pairs(counts)
        best = _best_pair(pair_counts)
        if best is None:
            print(f"{new_id - BYTE_VOCAB_SIZE + 1:>5}  no pair remains, training stops")
            break
        vocab[new_id] = vocab[best[0]] + vocab[best[1]]
        merges.append((best, new_id))
        pair_text = f"{show(vocab[best[0]])} + {show(vocab[best[1]])}"
        print(
            f"{new_id - BYTE_VOCAB_SIZE + 1:>5} {new_id:>7} "
            f"{pair_counts[best]:>6}  {pair_text:<24} {show(vocab[new_id])}"
        )
        counts = _rebuild(counts, best, new_id)
    return merges


def _rebuild(counts, pair, new_id):
    """Apply one merge to every word and re-accumulate the frequencies."""
    rebuilt = Counter()
    for word, frequency in counts.items():
        rebuilt[_merge_once(word, pair, new_id)] += frequency
    return rebuilt


def train_with_tie_break(word_counts, vocab_size, stable):
    """Learn merges with either tie-break rule, same algorithm otherwise.

    Args:
        word_counts: word type to frequency.
        vocab_size: target vocabulary size.
        stable: True for the smallest-pair rule `lib/bpe.py` uses, False
            for `max(..., key=...)`, which returns the first key holding
            the maximum in insertion order.

    Returns:
        The learned merge list, in order.

    Termination: at most `vocab_size - 256` rounds, and it stops early
    when no pair remains.
    """
    counts = Counter(word_counts)
    merges = []
    for new_id in range(BYTE_VOCAB_SIZE, vocab_size):
        pair_counts = _count_pairs(counts)
        if not pair_counts:
            break
        if stable:
            best = _best_pair(pair_counts)
        else:
            best = max(pair_counts, key=pair_counts.get)
        merges.append((best, new_id))
        counts = _rebuild(counts, best, new_id)
    return merges


def tie_break_trial(word_counts, rng):
    """Recount the same word types in a shuffled order and retrain both ways.

    Returns:
        (stable_merges, unstable_merges) for this ordering.
    """
    items = list(word_counts.items())
    rng.shuffle(items)
    reordered = Counter(dict(items))
    return (
        train_with_tie_break(reordered, TIE_BREAK_VOCAB, stable=True),
        train_with_tie_break(reordered, TIE_BREAK_VOCAB, stable=False),
    )


def first_divergence(left, right):
    """Index of the first position where two merge lists differ, or None."""
    for index, (one, other) in enumerate(zip(left, right)):
        if one != other:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return None


def run_tie_break_trap(corpus):
    """Retrain under several word orderings and report what each rule did.

    Returns:
        (stable_is_stable, unstable_is_stable) as booleans.
    """
    word_counts = BPETokenizer.word_counts(corpus[:TIE_BREAK_BYTES])
    rng = random.Random(SHUFFLE_SEED)
    trials = [tie_break_trial(word_counts, rng) for _ in range(SHUFFLE_TRIALS)]
    stable_first, unstable_first = trials[0]
    print(
        f"{len(word_counts)} word types, vocabulary {TIE_BREAK_VOCAB}, "
        f"{SHUFFLE_TRIALS} shuffled orderings, seed {SHUFFLE_SEED}"
    )
    print()
    print(f"{'ordering':>9} {'smallest-pair tie-break':>25} {'max() tie-break':>18}")
    print("-" * 56)
    for index, (stable, unstable) in enumerate(trials):
        stable_note = _divergence_note(first_divergence(stable, stable_first))
        unstable_note = _divergence_note(first_divergence(unstable, unstable_first))
        print(f"{index:>9} {stable_note:>25} {unstable_note:>18}")
    return (
        all(stable == stable_first for stable, _ in trials),
        all(unstable == unstable_first for _, unstable in trials),
    )


def _divergence_note(index):
    """Render a divergence index as text for the trial table."""
    return "identical" if index is None else f"differs at merge {index}"


def merge_rank(tokenizer):
    """Build pair to rank from the public merge list.

    The wrong implementation below is written entirely against the public
    API, because that is how a reader would write it. Nothing here reaches
    into the tokenizer's internals to make its mistake.
    """
    return {pair: rank for rank, (pair, _) in enumerate(tokenizer.merges)}


def encode_left_to_right(tokenizer, ranks, chunk):
    """Encode by taking the leftmost applicable merge, not the earliest learned.

    This is the plausible wrong implementation. It round trips, it never
    crashes, and it is a different algorithm from the one that trained the
    merge table.

    Complexity: O(len(chunk)^2).

    Termination: every accepted merge removes one symbol, so the loop runs
    at most len(chunk) times. The explicit budget makes that a checked
    property rather than an argument.
    """
    symbols = list(chunk.encode("utf-8"))
    budget = len(symbols)
    while budget > 0:
        budget -= 1
        applied = False
        for position in range(len(symbols) - 1):
            rank = ranks.get((symbols[position], symbols[position + 1]))
            if rank is None:
                continue
            symbols[position:position + 2] = [tokenizer.merges[rank][1]]
            applied = True
            break
        if not applied:
            return symbols
    return symbols


def is_readable(chunk):
    """True for a chunk worth printing as the worked example.

    Whitespace-only and mixed-whitespace chunks disagree just as often,
    but they read as escape sequences and teach nothing, so the example
    picker skips them. What is wanted is one ordinary word, optionally
    carrying the single leading space the boundary rule attaches to it.
    """
    word = chunk[1:] if chunk.startswith(" ") else chunk
    return word.isalpha() and chunk.count(" ") <= 1 and 6 <= len(chunk) <= 12


def run_encode_trap(tokenizer, corpus):
    """Compare rank-order encoding against left-to-right on every chunk type.

    A chunk is already maximal under `pre_tokenize`, so `encode` on a
    single chunk is exactly the per-chunk encoder, reached through the
    public API.

    Returns:
        (chunk_types, disagreements, rank_tokens, left_to_right_tokens).
    """
    ranks = merge_rank(tokenizer)
    chunk_types = sorted(set(pre_tokenize(corpus[:ENCODE_SAMPLE_BYTES])))
    disagreements = 0
    rank_tokens = 0
    left_tokens = 0
    example = None
    for chunk in chunk_types:
        by_rank = tokenizer.encode(chunk)
        by_position = encode_left_to_right(tokenizer, ranks, chunk)
        rank_tokens += len(by_rank)
        left_tokens += len(by_position)
        if by_rank == by_position:
            continue
        disagreements += 1
        if example is None and is_readable(chunk):
            example = (chunk, by_rank, by_position)
    _print_encode_result(
        tokenizer, chunk_types, disagreements, rank_tokens, left_tokens, example
    )
    return len(chunk_types), disagreements, rank_tokens, left_tokens


def _print_encode_result(tokenizer, chunk_types, disagreements, rank, left, example):
    """Print the encode-order comparison and one worked example."""
    print(
        f"{len(chunk_types)} distinct chunk types from the first "
        f"{ENCODE_SAMPLE_BYTES} characters, vocabulary {tokenizer.vocab_size}"
    )
    print(f"  disagreements            {disagreements}")
    print(f"  tokens, replay by rank   {rank}")
    print(f"  tokens, left to right    {left}")
    print(f"  left to right costs      {(left - rank) / rank:+.2%}")
    if example is None:
        return
    chunk, by_rank, by_position = example
    print()
    print(f"  worked example: {chunk!r}")
    print(f"    by rank         {[show(tokenizer.vocab[i]) for i in by_rank]}")
    print(f"    left to right   {[show(tokenizer.vocab[i]) for i in by_position]}")


def check_claims(tie_break_result, encode_result, tokenizer, corpus):
    """Assert the three claims the article makes. Raises AssertionError."""
    stable_is_stable, unstable_is_stable = tie_break_result
    assert stable_is_stable, (
        "CLAIM 1 died: the smallest-pair tie-break produced different merges "
        "when the same word types were counted in a different order"
    )
    assert not unstable_is_stable, (
        "CLAIM 1 died: max() happened to agree across every shuffled ordering "
        "here, so this corpus does not demonstrate the trap and the article "
        "must not claim it does"
    )

    _, disagreements, rank_tokens, left_tokens = encode_result
    assert disagreements > 0, (
        "CLAIM 2 died: left-to-right encoding agreed with rank-order encoding "
        "on every chunk type, so the two are not distinguishable here"
    )
    assert left_tokens > rank_tokens, (
        f"CLAIM 2 died: left-to-right produced {left_tokens} tokens against "
        f"rank order's {rank_tokens}, which is not more"
    )

    assert tokenizer.decode(tokenizer.encode(corpus)) == corpus, (
        "CLAIM 3 died: the training corpus did not survive a round trip"
    )
    for text in ROUND_TRIP_CASES:
        assert tokenizer.decode(tokenizer.encode(text)) == text, (
            f"CLAIM 3 died: {text!r} did not survive a round trip"
        )


def main():
    """Trace, run both traps, verify, and report."""
    corpus = load_corpus(CORPUS_PATH)

    print("PART ONE: training traced merge by merge")
    print()
    traced = trace_training(TINY_CORPUS, TINY_VOCAB)
    library = BPETokenizer.train(TINY_CORPUS, TINY_VOCAB).merges
    assert traced == library, (
        "the traced loop and lib/bpe.py disagree, so the trace is not a trace"
    )
    print()
    print(f"traced {len(traced)} merges, identical to lib/bpe.py's")

    print()
    print()
    print("PART TWO: the tie-break trap")
    print()
    tie_break_result = run_tie_break_trap(corpus)

    print()
    print()
    print("PART THREE: the encode-order trap")
    print()
    tokenizer = BPETokenizer.train(corpus, ENCODE_VOCAB)
    encode_result = run_encode_trap(tokenizer, corpus)

    try:
        check_claims(tie_break_result, encode_result, tokenizer, corpus)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
