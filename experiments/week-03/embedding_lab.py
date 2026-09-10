"""The embedding layer, built and checked step by step.

Companion artifact for the week-3 Thursday tutorial (2026-09-10).

Six steps, in the order the tutorial walks them. Each step prints what it
did, and the assertions at the end are the tutorial's verification step:
if one of them fails, a claim in the article is wrong and the article has
to change.

  STEP 1  Get real token ids, from our own tokenizer trained on our own
          corpus, so the vocabulary size is a measured fact and not a
          placeholder.
  STEP 2  Build the token table and prove the lookup identity: reading
          row i equals multiplying by a one-hot row.
  STEP 3  Add the position table and show the same token at two places
          comes out as two different rows.
  STEP 4  Size it. Compute the embedding share of the parameter budget
          for four published configurations and watch it collapse.
  STEP 5  Tie the output projection to the input table and confirm the
          saving is exactly vocab_size times d_model.
  STEP 6  Verify, including the part nobody wants to hear: an untrained
          embedding carries no meaning, and its nearest neighbours are a
          property of the seed.

Five claims are asserted at the end.

  CLAIM 1  Lookup and one-hot matmul agree to within 1e-12 on every value.

  CLAIM 2  The same token id at position 0 and position 5 produces two
          different rows, and the difference is exactly the difference
          between two position rows.

  CLAIM 3  The embedding share of the parameter budget falls strictly as
          the published configurations get larger, from about a third of
          the smallest to about a twentieth of the largest.

  CLAIM 4  Weight tying saves exactly vocab_size times d_model floats.

  CLAIM 5  Untrained embeddings carry no meaning. Three ways of saying
          it, all measured. The mean absolute cosine similarity between
          token rows matches sqrt(2 / (pi * d_model)), which is what
          vectors with no structure whatsoever produce. A pair of tokens
          any reader would call related scores inside the bulk of the
          arbitrary-pair distribution, not above it. And the nearest
          neighbour of a token changes when only the seed changes.

Determinism: every weight comes from a stated seed, and tokenizer
training is a pure function of the corpus. Two runs produce
byte-identical output.

Run:      python3 experiments/week-03/embedding_lab.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  under two seconds, most of it training the tokenizer.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.bpe import BPETokenizer  # noqa: E402
from lib.embedding import (  # noqa: E402
    EmbeddingTable,
    TokenAndPositionEmbedding,
    cosine_similarity,
    embed_by_matmul,
    parameter_report,
)

CORPUS_PATH = os.path.join(REPO_ROOT, "data", "week-03", "tokenizer_corpus.txt")

TOKENIZER_VOCAB = 1024
D_MODEL = 64
MAX_POSITIONS = 128
SEED = 42
RIVAL_SEED = 43

SENTENCE = "the cache expired before the request arrived"

# Two words any reader of this series would call related. Both must be a
# single token, and they must be different tokens, or the comparison in
# step six is a row against itself and scores 1.0 for a stupid reason.
# That is checked, not assumed.
RELATED_PAIR = (" cache", " database")

# Pairwise cosine similarity over every token would be half a million
# pairs. A seeded sample of ids is enough to show the distribution.
SAMPLE_TOKENS = 300
SAMPLE_SEED = 7

# The related pair is called unremarkable if it sits below this quantile
# of the arbitrary-pair distribution.
BULK_QUANTILE = 0.95

TOLERANCE = 1e-12

# Table 2 of Radford et al., "Language Models are Unsupervised Multitask
# Learners": parameter count, layer count and d_model for the four sizes.
# The vocabulary and context length are stated in the same section as
# 50,257 and 1,024. Everything below is arithmetic on those published
# columns, not a benchmark and not an estimate.
PUBLISHED_VOCAB = 50257
PUBLISHED_CONTEXT = 1024
PUBLISHED_SIZES = (
    ("117M", 117_000_000, 12, 768),
    ("345M", 345_000_000, 24, 1024),
    ("762M", 762_000_000, 36, 1280),
    ("1542M", 1_542_000_000, 48, 1600),
)


def load_corpus(path):
    """Read the training corpus, or exit with an actionable message."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        print(f"cannot read corpus at {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def step_one_real_ids(corpus):
    """Train the tokenizer and encode one sentence. Returns (tokenizer, ids)."""
    tokenizer = BPETokenizer.train(corpus, TOKENIZER_VOCAB)
    ids = tokenizer.encode(SENTENCE)
    print("STEP 1: real token ids from our own tokenizer")
    print(f"  corpus            {len(corpus)} characters")
    print(f"  vocabulary        {tokenizer.vocab_size}")
    print(f"  sentence          {SENTENCE!r}")
    print(f"  ids               {ids}")
    print(f"  pieces            {tokenizer.token_pieces(SENTENCE)}")
    return tokenizer, ids


def step_two_lookup_identity(vocab_size, ids):
    """Build the token table and compare both routes. Returns the max gap."""
    table = EmbeddingTable(vocab_size, D_MODEL, random.Random(SEED))
    by_lookup = table.lookup(ids)
    by_matmul = embed_by_matmul(table.weight, ids)
    worst = 0.0
    for left_row, right_row in zip(by_lookup, by_matmul):
        for left, right in zip(left_row, right_row):
            worst = max(worst, abs(left - right))
    print()
    print("STEP 2: a lookup is a matrix multiplication")
    print(f"  table             {vocab_size} by {D_MODEL}, "
          f"{table.parameter_count} floats")
    print(f"  rows returned     {len(by_lookup)}")
    print(f"  largest gap between lookup and one-hot matmul: {worst:.3e}")
    return table, worst


def step_three_position(vocab_size, ids):
    """Add positions and measure what position contributes. Returns the layer."""
    layer = TokenAndPositionEmbedding(vocab_size, MAX_POSITIONS, D_MODEL, SEED)
    rows = layer.forward(ids)
    repeated = layer.forward([ids[0]] * 6)
    gap = max(abs(a - b) for a, b in zip(repeated[0], repeated[5]))
    position_gap = max(
        abs(a - b)
        for a, b in zip(layer.positions.weight[0], layer.positions.weight[5])
    )
    print()
    print("STEP 3: position is a second table, not a property of the token")
    print(f"  output shape      {len(rows)} by {len(rows[0])}")
    print(f"  same id at positions 0 and 5, largest difference: {gap:.6f}")
    print(f"  positions 0 and 5 of the position table differ by: "
          f"{position_gap:.6f}")
    return layer, gap, position_gap


def step_four_sizing():
    """Size the tables against four published configurations. Returns rows."""
    print()
    print("STEP 4: how much of the model is the lookup table")
    print(f"  vocabulary {PUBLISHED_VOCAB}, context {PUBLISHED_CONTEXT}, "
          "both as published")
    print()
    header = (
        f"{'model':>7} {'d_model':>8} {'layers':>7} {'token table':>13} "
        f"{'+positions':>12} {'share of total':>15}"
    )
    print(f"  {header}")
    print("  " + "-" * len(header))
    rows = []
    for name, total, layers, width in PUBLISHED_SIZES:
        report = parameter_report(
            PUBLISHED_VOCAB, PUBLISHED_CONTEXT, width, total
        )
        rows.append((name, report))
        print(
            f"  {name:>7} {width:>8} {layers:>7} "
            f"{report['token_parameters']:>13,} "
            f"{report['embedding_parameters']:>12,} "
            f"{report['embedding_share']:>14.1%}"
        )
    return rows


def step_five_tying(layer):
    """Confirm the tied projection scores correctly and costs nothing extra."""
    hidden = layer.forward([layer.tokens.num_entries - 1])
    logits = layer.tied_logits(hidden)
    saving = parameter_report(
        layer.vocab_size, layer.max_positions, layer.d_model, 1
    )["tying_saving"]
    print()
    print("STEP 5: tying the output projection to the input table")
    print(f"  logits shape      {len(logits)} by {len(logits[0])}")
    print(f"  a separate output projection would hold {saving:,} more floats")
    print(f"  which is {saving / layer.parameter_count:.1%} of this layer's "
          "own parameters")
    return saving


def sample_similarities(table, ids):
    """Return every pairwise cosine similarity over the sampled ids."""
    similarities = []
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            similarities.append(
                cosine_similarity(table.weight[left], table.weight[right])
            )
    return similarities


def nearest_neighbour(table, token_id):
    """Return the id whose row is closest in cosine to `token_id`'s."""
    best_id = None
    best_score = -2.0
    for candidate in range(table.num_entries):
        if candidate == token_id:
            continue
        score = cosine_similarity(table.weight[token_id], table.weight[candidate])
        if score > best_score:
            best_score = score
            best_id = candidate
    return best_id, best_score


def quantile(sorted_values, fraction):
    """Return the value at `fraction` of the way through a sorted list.

    Nearest-rank, which needs no interpolation and no third-party stats
    package. `sorted_values` must be non-empty and already sorted.
    """
    index = min(len(sorted_values) - 1, int(fraction * len(sorted_values)))
    return sorted_values[index]


def single_token_id(tokenizer, text):
    """Return the one token id `text` encodes to, or exit saying it does not.

    Step six is meaningless if either word of the related pair is more
    than one token, so this refuses to continue rather than silently
    comparing the first fragment of one word with the first fragment of
    another.
    """
    ids = tokenizer.encode(text)
    if len(ids) != 1:
        print(
            f"{text!r} is {len(ids)} tokens at vocabulary "
            f"{tokenizer.vocab_size}, not one, so the related-pair "
            "comparison in step six cannot be made. Pick another word or "
            "raise the vocabulary.",
            file=sys.stderr,
        )
        sys.exit(2)
    return ids[0]


def step_six_no_meaning(tokenizer, layer):
    """Measure that a fresh table has no semantics. Returns the evidence."""
    rng = random.Random(SAMPLE_SEED)
    sampled = rng.sample(range(layer.vocab_size), SAMPLE_TOKENS)
    similarities = sample_similarities(layer.tokens, sampled)
    magnitudes = sorted(abs(value) for value in similarities)
    mean_absolute = sum(magnitudes) / len(magnitudes)
    predicted = math.sqrt(2.0 / (math.pi * layer.d_model))
    bulk = quantile(magnitudes, BULK_QUANTILE)

    left = single_token_id(tokenizer, RELATED_PAIR[0])
    right = single_token_id(tokenizer, RELATED_PAIR[1])
    assert left != right, "the related pair collapsed to one token id"
    related = cosine_similarity(layer.tokens.weight[left], layer.tokens.weight[right])

    same_seed = nearest_neighbour(layer.tokens, left)
    rival = TokenAndPositionEmbedding(
        layer.vocab_size, layer.max_positions, layer.d_model, RIVAL_SEED
    )
    other_seed = nearest_neighbour(rival.tokens, left)

    print()
    print("STEP 6: what an untrained table does not know")
    print(f"  {len(similarities)} pairs from {SAMPLE_TOKENS} sampled ids, "
          f"sample seed {SAMPLE_SEED}")
    print(f"  mean |cosine|, measured                {mean_absolute:.4f}")
    print(f"  mean |cosine|, predicted for no structure  {predicted:.4f}"
          f"   (sqrt(2 / (pi * {layer.d_model})))")
    print(f"  {BULK_QUANTILE:.0%} of arbitrary pairs sit below   {bulk:.4f}")
    print(f"  largest |cosine|                       {magnitudes[-1]:.4f}")
    print(f"  {RELATED_PAIR[0]!r} (id {left}) against {RELATED_PAIR[1]!r} "
          f"(id {right}): cosine {related:+.4f}")
    print(f"  nearest neighbour of {RELATED_PAIR[0]!r} at seed {SEED}: "
          f"id {same_seed[0]} "
          f"{tokenizer.vocab[same_seed[0]].decode('utf-8', 'replace')!r} "
          f"({same_seed[1]:+.4f})")
    print(f"  nearest neighbour of {RELATED_PAIR[0]!r} at seed {RIVAL_SEED}: "
          f"id {other_seed[0]} "
          f"{tokenizer.vocab[other_seed[0]].decode('utf-8', 'replace')!r} "
          f"({other_seed[1]:+.4f})")
    return mean_absolute, predicted, bulk, related, same_seed[0], other_seed[0]


def step_six_refusals(layer):
    """Show the two refusals that a silent implementation would not make."""
    print()
    print("  the two things this layer refuses to do quietly:")
    try:
        layer.forward([layer.vocab_size])
    except IndexError as exc:
        print(f"    out-of-range id  -> IndexError: {exc}")
    try:
        layer.forward([0] * (layer.max_positions + 1))
    except ValueError as exc:
        print(f"    over-long input  -> ValueError: {exc}")


def check_claims(worst_gap, position_evidence, sizing, saving, layer, meaning):
    """Assert the five claims the article makes. Raises AssertionError."""
    assert worst_gap < TOLERANCE, (
        f"CLAIM 1 died: lookup and one-hot matmul differ by {worst_gap:.3e}, "
        f"which is not below {TOLERANCE:.0e}"
    )

    gap, position_gap = position_evidence
    assert gap > 0.0, (
        "CLAIM 2 died: the same token at two positions produced identical "
        "rows, so this layer carries no position information"
    )
    assert abs(gap - position_gap) < TOLERANCE, (
        f"CLAIM 2 died: the difference between two positions of one token, "
        f"{gap:.9f}, is not the difference between two position rows, "
        f"{position_gap:.9f}, so something other than position moved"
    )

    shares = [report["embedding_share"] for _, report in sizing]
    for earlier, later in zip(shares, shares[1:]):
        assert later < earlier, (
            f"CLAIM 3 died: embedding share rose from {earlier:.1%} to "
            f"{later:.1%} as the model got larger"
        )
    assert shares[0] > 0.30, (
        f"CLAIM 3 died: the smallest configuration's embedding share is "
        f"{shares[0]:.1%}, not about a third"
    )
    assert shares[-1] < 0.06, (
        f"CLAIM 3 died: the largest configuration's embedding share is "
        f"{shares[-1]:.1%}, not about a twentieth"
    )

    assert saving == layer.vocab_size * layer.d_model, (
        f"CLAIM 4 died: tying saved {saving}, not "
        f"{layer.vocab_size * layer.d_model}"
    )

    mean_absolute, predicted, bulk, related, same_seed, other_seed = meaning
    assert abs(mean_absolute - predicted) < 0.01, (
        f"CLAIM 5 died: mean |cosine| is {mean_absolute:.4f} but vectors with "
        f"no structure predict {predicted:.4f}. A gap that size means the "
        "table has structure the article says it does not have"
    )
    assert abs(related) < bulk, (
        f"CLAIM 5 died: the related pair scored {related:+.4f}, at or above "
        f"the {BULK_QUANTILE:.0%} mark of arbitrary pairs, {bulk:.4f}. On this "
        "run the untrained table appears to know something, so the article's "
        "claim does not hold and must change"
    )
    assert same_seed != other_seed, (
        f"CLAIM 5 died: both seeds chose id {same_seed} as the nearest "
        "neighbour, so this run does not show the neighbour is seed-dependent"
    )


def main():
    """Run all six steps, then verify."""
    corpus = load_corpus(CORPUS_PATH)
    tokenizer, ids = step_one_real_ids(corpus)
    _, worst_gap = step_two_lookup_identity(tokenizer.vocab_size, ids)
    layer, gap, position_gap = step_three_position(tokenizer.vocab_size, ids)
    sizing = step_four_sizing()
    saving = step_five_tying(layer)
    meaning = step_six_no_meaning(tokenizer, layer)
    step_six_refusals(layer)

    try:
        check_claims(
            worst_gap, (gap, position_gap), sizing, saving, layer, meaning
        )
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
