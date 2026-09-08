"""What the sqrt(d_k) divisor buys, and what a second head buys, measured.

Companion artifact for the week-3 Tuesday posts (2026-09-08).

`lib/attention.py` makes two claims in prose that a reader should not have
to take on trust. This script measures both, and a third that the module
implies but never states.

  CLAIM 1  Raw dot-product scores grow with the width of the head. If the
           components of q and k are independent with mean 0 and variance
           1, the dot product over d_k terms has variance d_k. The module
           docstring asserts this. Here it is sampled instead, and the
           ratio of measured variance to d_k is checked to sit near 1.

  CLAIM 2  That growth is not cosmetic. Feed unscaled scores to softmax
           and the distribution collapses onto its largest entry as d_k
           rises, which is the regime where gradients vanish. Dividing by
           sqrt(d_k) holds the distribution open at every width tested.
           Measured as mean largest weight and mean entropy per row.

  CLAIM 3  One attention head cannot carry two signals at once, and this
           is arithmetic rather than a training failure. A softmax row is
           a probability distribution, so a head's output is a convex
           combination of the value rows: one point, one budget of 1.0 to
           divide. Two different value sets are constructed below that a
           single head maps to the identical output, and that two heads
           keep distinct. The collision is exact, not approximate.

  CLAIM 4  Splitting d_model into more heads costs no parameters. Every
           head count tested holds 4 * d_model^2 weights, because the
           heads divide the width rather than adding to it. What changes
           is that the heads measurably disagree, which is the only
           reason to want them.

Nothing here is trained. Weights come from a seeded initialiser, so head
disagreement below is the disagreement of random projections, and is a
lower bound on what training produces, not a claim about learned roles.

Determinism: every random draw comes from an explicitly seeded
random.Random. Two runs on any machine produce byte-identical output.

Run:      python3 experiments/week-03/attention_heads.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about three seconds.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.attention import (  # noqa: E402
    MultiHeadSelfAttention,
    causal_mask,
    scaled_dot_product_attention,
)
from lib.linalg import shape, softmax_rows  # noqa: E402

HEAD_WIDTHS = (8, 16, 32, 64, 128, 256, 512)
SCORE_SAMPLES = 20000
SOFTMAX_ROWS = 2000
ROW_LENGTH = 16

SWEEP_D_MODEL = 64
SWEEP_HEAD_COUNTS = (1, 2, 4, 8, 16)
SWEEP_SEQUENCE = 12
SWEEP_SEED = 20260908

VARIANCE_SEED = 11
SOFTMAX_SEED = 12
SEQUENCE_SEED = 13


def dot(left, right):
    """Return the dot product of two equal-length sequences."""
    if len(left) != len(right):
        raise ValueError(f"cannot dot length {len(left)} with length {len(right)}")
    return sum(a * b for a, b in zip(left, right))


def variance(samples):
    """Return the population variance of a non-empty sample list."""
    if not samples:
        raise ValueError("variance needs at least one sample")
    mean = sum(samples) / len(samples)
    return sum((value - mean) ** 2 for value in samples) / len(samples)


def entropy(distribution):
    """Return Shannon entropy in nats. Zero-probability entries contribute 0."""
    total = 0.0
    for probability in distribution:
        if probability > 0.0:
            total -= probability * math.log(probability)
    return total


def measure_score_variance(d_k, rng):
    """Sample SCORE_SAMPLES raw dot products of unit-variance vectors.

    Args:
        d_k: head width, the number of terms in each dot product.
        rng: seeded random.Random.

    Returns:
        The measured population variance of the raw (unscaled) scores.

    Complexity: O(SCORE_SAMPLES * d_k) multiply-adds.
    """
    if d_k <= 0:
        raise ValueError(f"d_k must be positive, got {d_k}")
    scores = []
    for _ in range(SCORE_SAMPLES):
        query = [rng.gauss(0.0, 1.0) for _ in range(d_k)]
        key = [rng.gauss(0.0, 1.0) for _ in range(d_k)]
        scores.append(dot(query, key))
    return variance(scores)


def measure_softmax_shape(d_k, rng):
    """Measure what scaling does to the softmax of realistic score rows.

    Builds SOFTMAX_ROWS rows of ROW_LENGTH raw dot products at width d_k,
    then softmaxes each row twice: once raw, once divided by sqrt(d_k).

    Returns:
        (raw_max, raw_entropy, scaled_max, scaled_entropy), each a mean
        over rows. Entropy is in nats; log(ROW_LENGTH) is the maximum.
    """
    raw_rows = []
    for _ in range(SOFTMAX_ROWS):
        query = [rng.gauss(0.0, 1.0) for _ in range(d_k)]
        row = []
        for _ in range(ROW_LENGTH):
            key = [rng.gauss(0.0, 1.0) for _ in range(d_k)]
            row.append(dot(query, key))
        raw_rows.append(row)

    divisor = math.sqrt(d_k)
    scaled_rows = [[value / divisor for value in row] for row in raw_rows]
    raw_weights = softmax_rows(raw_rows)
    scaled_weights = softmax_rows(scaled_rows)
    return (
        sum(max(row) for row in raw_weights) / SOFTMAX_ROWS,
        sum(entropy(row) for row in raw_weights) / SOFTMAX_ROWS,
        sum(max(row) for row in scaled_weights) / SOFTMAX_ROWS,
        sum(entropy(row) for row in scaled_weights) / SOFTMAX_ROWS,
    )


def blend(weights, values):
    """Return the weighted sum of value rows: one convex combination."""
    if len(weights) != len(values):
        raise ValueError(
            f"{len(weights)} weights cannot combine {len(values)} value rows"
        )
    width = len(values[0])
    combined = [0.0] * width
    for weight, row in zip(weights, values):
        if len(row) != width:
            raise ValueError("value rows must all have the same width")
        for index in range(width):
            combined[index] += weight * row[index]
    return combined


def l2_distance(left, right):
    """Return the Euclidean distance between two equal-length vectors."""
    if len(left) != len(right):
        raise ValueError(f"cannot compare length {len(left)} with {len(right)}")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def collision_demo():
    """Show one head collapsing two distinct value sets to one output.

    DISTINCT holds two positions carrying orthogonal signals. AVERAGED
    holds two positions that both carry the average of those signals. A
    single head attending 0.5 / 0.5 produces the same output for both,
    because a convex combination of equals is that value. Two heads, one
    attending entirely to each position, keep them apart.

    Returns:
        (single_distance, double_distance): the L2 gap between the two
        value sets under one head and under two heads.
    """
    distinct = [[1.0, 0.0], [0.0, 1.0]]
    averaged = [[0.5, 0.5], [0.5, 0.5]]

    single = [0.5, 0.5]
    single_distance = l2_distance(blend(single, distinct), blend(single, averaged))

    head_a, head_b = [1.0, 0.0], [0.0, 1.0]
    double_distinct = blend(head_a, distinct) + blend(head_b, distinct)
    double_averaged = blend(head_a, averaged) + blend(head_b, averaged)
    double_distance = l2_distance(double_distinct, double_averaged)
    return single_distance, double_distance


def total_variation(left, right):
    """Return total variation distance between two distributions over the same support."""
    if len(left) != len(right):
        raise ValueError(f"cannot compare length {len(left)} with {len(right)}")
    return 0.5 * sum(abs(a - b) for a, b in zip(left, right))


def mean_head_disagreement(weights_per_head):
    """Mean total variation distance between every pair of heads, over all rows.

    A single head has no pairs, so it disagrees with nothing and scores
    0.0 by definition. That zero is the point of the measurement.
    """
    head_count = len(weights_per_head)
    if head_count < 2:
        return 0.0
    rows = len(weights_per_head[0])
    total, comparisons = 0.0, 0
    for first in range(head_count):
        for second in range(first + 1, head_count):
            for row in range(rows):
                total += total_variation(
                    weights_per_head[first][row], weights_per_head[second][row]
                )
                comparisons += 1
    return total / comparisons


def parameter_count(attention):
    """Count every float the module holds, by walking its actual matrices."""
    total = 0
    for head in attention.heads:
        for matrix in (head.w_query, head.w_key, head.w_value):
            rows, cols = shape(matrix)
            total += rows * cols
    rows, cols = shape(attention.w_output)
    return total + rows * cols


def run_variance_table(rng):
    """Print and return the measured raw score variance at each head width."""
    print("CLAIM 1  raw dot-product score variance grows with head width")
    print(f"         {SCORE_SAMPLES} sampled dot products per width\n")
    print(f"  {'d_k':>5}  {'measured var':>13}  {'var / d_k':>10}  {'scaled var':>11}")
    print("  " + "-" * 45)
    ratios = {}
    for d_k in HEAD_WIDTHS:
        measured = measure_score_variance(d_k, rng)
        ratio = measured / d_k
        ratios[d_k] = ratio
        print(f"  {d_k:>5}  {measured:>13.2f}  {ratio:>10.3f}  {measured / d_k:>11.3f}")
    print("\n  scaled var is measured var divided by (sqrt(d_k))^2, the")
    print("  divisor lib/attention.py applies on line 126.")
    return ratios


def run_softmax_table(rng):
    """Print and return what scaling does to softmax sharpness at each width."""
    print(f"\n\nCLAIM 2  unscaled scores collapse the distribution as width grows")
    print(f"         {SOFTMAX_ROWS} rows of {ROW_LENGTH} scores per width;")
    print(f"         a flat row over {ROW_LENGTH} entries has entropy "
          f"{math.log(ROW_LENGTH):.3f} nats and max weight "
          f"{1.0 / ROW_LENGTH:.3f}\n")
    print(f"  {'d_k':>5}  {'raw max w':>10}  {'raw entropy':>12}"
          f"  {'scaled max w':>13}  {'scaled entropy':>15}")
    print("  " + "-" * 62)
    table = {}
    for d_k in HEAD_WIDTHS:
        raw_max, raw_ent, scaled_max, scaled_ent = measure_softmax_shape(d_k, rng)
        table[d_k] = (raw_max, raw_ent, scaled_max, scaled_ent)
        print(f"  {d_k:>5}  {raw_max:>10.3f}  {raw_ent:>12.3f}"
              f"  {scaled_max:>13.3f}  {scaled_ent:>15.3f}")
    return table


def run_collision():
    """Print the one-head collision and the two-head separation."""
    single_distance, double_distance = collision_demo()
    print("\n\nCLAIM 3  one head maps two different value sets to one output")
    print("\n  position 0 = [1.0, 0.0], position 1 = [0.0, 1.0]   (DISTINCT)")
    print("  position 0 = [0.5, 0.5], position 1 = [0.5, 0.5]   (AVERAGED)")
    print("\n  one head attending 0.5 / 0.5:")
    print(f"    DISTINCT -> {blend([0.5, 0.5], [[1.0, 0.0], [0.0, 1.0]])}")
    print(f"    AVERAGED -> {blend([0.5, 0.5], [[0.5, 0.5], [0.5, 0.5]])}")
    print(f"    L2 gap between them: {single_distance:.6f}")
    print("\n  two heads, one attending to each position, concatenated:")
    print(f"    DISTINCT -> {blend([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]]) + blend([0.0, 1.0], [[1.0, 0.0], [0.0, 1.0]])}")
    print(f"    AVERAGED -> {blend([1.0, 0.0], [[0.5, 0.5], [0.5, 0.5]]) + blend([0.0, 1.0], [[0.5, 0.5], [0.5, 0.5]])}")
    print(f"    L2 gap between them: {double_distance:.6f}")
    return single_distance, double_distance


def run_head_sweep():
    """Print and return the head-count sweep: parameters, width, disagreement."""
    rng = random.Random(SEQUENCE_SEED)
    sequence = [
        [rng.uniform(-1.0, 1.0) for _ in range(SWEEP_D_MODEL)]
        for _ in range(SWEEP_SEQUENCE)
    ]
    mask = causal_mask(SWEEP_SEQUENCE)

    print(f"\n\nCLAIM 4  more heads cost no parameters and do disagree")
    print(f"         d_model {SWEEP_D_MODEL}, {SWEEP_SEQUENCE} positions, "
          f"causal mask, seed {SWEEP_SEED}\n")
    print(f"  {'heads':>6}  {'d_head':>7}  {'parameters':>11}"
          f"  {'mean pairwise TV':>17}")
    print("  " + "-" * 48)
    rows = {}
    for head_count in SWEEP_HEAD_COUNTS:
        attention = MultiHeadSelfAttention(SWEEP_D_MODEL, head_count, SWEEP_SEED)
        output, weights_per_head = attention.forward(sequence, mask)
        if shape(output) != (SWEEP_SEQUENCE, SWEEP_D_MODEL):
            raise ValueError(f"output shape {shape(output)} is not the input shape")
        disagreement = mean_head_disagreement(weights_per_head)
        params = parameter_count(attention)
        rows[head_count] = (attention.d_head, params, disagreement)
        print(f"  {head_count:>6}  {attention.d_head:>7}  {params:>11}"
              f"  {disagreement:>17.4f}")
    print(f"\n  4 * d_model^2 = {4 * SWEEP_D_MODEL ** 2}")
    print("  TV distance is 0 for identical distributions, 1 for disjoint.")
    return rows


def check_claims(ratios, softmax_table, collision, sweep):
    """Assert every claim this script exists to support.

    Raises:
        AssertionError: naming the claim and the measurement that broke it.
    """
    for d_k, ratio in ratios.items():
        assert 0.9 <= ratio <= 1.1, (
            f"CLAIM 1: at d_k {d_k} the score variance was {ratio:.3f} times "
            "d_k, outside the 0.9 to 1.1 band the sqrt(d_k) argument predicts"
        )

    narrowest, widest = HEAD_WIDTHS[0], HEAD_WIDTHS[-1]
    raw_narrow, ent_narrow = softmax_table[narrowest][0], softmax_table[narrowest][1]
    raw_wide, ent_wide = softmax_table[widest][0], softmax_table[widest][1]
    assert raw_wide > raw_narrow, (
        f"CLAIM 2: unscaled max weight did not rise with width, "
        f"{raw_narrow:.3f} at d_k {narrowest} to {raw_wide:.3f} at d_k {widest}"
    )
    assert ent_wide < ent_narrow, (
        f"CLAIM 2: unscaled entropy did not fall with width, "
        f"{ent_narrow:.3f} at d_k {narrowest} to {ent_wide:.3f} at d_k {widest}"
    )
    scaled_maxes = [softmax_table[d_k][2] for d_k in HEAD_WIDTHS]
    assert max(scaled_maxes) - min(scaled_maxes) < 0.05, (
        f"CLAIM 2: scaled max weight was supposed to be flat across widths, "
        f"but it ranged over {max(scaled_maxes) - min(scaled_maxes):.4f}"
    )

    single_distance, double_distance = collision
    assert single_distance == 0.0, (
        f"CLAIM 3: the single-head collision is meant to be exact, "
        f"but the outputs differed by {single_distance}"
    )
    assert double_distance > 0.5, (
        f"CLAIM 3: two heads were supposed to separate the value sets, "
        f"but they differed by only {double_distance:.6f}"
    )

    counts = {params for _, params, _ in sweep.values()}
    assert len(counts) == 1, (
        f"CLAIM 4: parameter count was supposed to be invariant in head count, "
        f"but the sweep produced {sorted(counts)}"
    )
    assert counts.pop() == 4 * SWEEP_D_MODEL ** 2, (
        f"CLAIM 4: parameter count is not 4 * d_model^2"
    )
    assert sweep[1][2] == 0.0, "CLAIM 4: one head cannot disagree with itself"
    for head_count, (_, _, disagreement) in sweep.items():
        if head_count > 1:
            assert disagreement > 0.05, (
                f"CLAIM 4: {head_count} heads agreed to within "
                f"{disagreement:.4f} total variation, so they are redundant"
            )


def sanity_check_module():
    """Verify the imported attention still behaves before measuring with it."""
    queries = [[1.0, 0.0], [0.0, 1.0]]
    output, weights = scaled_dot_product_attention(queries, queries, queries)
    for index, row in enumerate(weights):
        total = sum(row)
        if abs(total - 1.0) > 1e-12:
            raise ValueError(f"attention weight row {index} summed to {total}")
    if shape(output) != (2, 2):
        raise ValueError(f"expected a (2, 2) output, got {shape(output)}")


def main():
    """Run all four measurements, then assert every claim. Returns an exit code."""
    sanity_check_module()
    print("Attention head measurements, lib/attention.py")
    print("=" * 66)
    print()

    ratios = run_variance_table(random.Random(VARIANCE_SEED))
    softmax_table = run_softmax_table(random.Random(SOFTMAX_SEED))
    collision = run_collision()
    sweep = run_head_sweep()

    try:
        check_claims(ratios, softmax_table, collision, sweep)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
