"""Multi-head latent attention: the fold, and the thing that breaks it.

Companion artifact for the week-4 Thursday posts (2026-09-17).

DeepSeek-V2 reports that "MLA guarantees efficient inference through
significantly compressing the Key-Value (KV) cache into a latent vector",
with a 93.3% reduction in that cache against their previous model
(arXiv:2405.04434). Compressing a cache is easy. Compressing it without
paying the decompression back in arithmetic is the part worth an hour.

This script builds the layer, verifies the identity that makes the
compression free, breaks it, and repairs it.

  CLAIM 1  The cached latent is narrower than the cache it replaces, and
           the reduction is exact arithmetic on stated widths.

  CLAIM 2  Folding the key up-projection into the query projection
           reproduces the explicit scores to better than 1e-10. That
           equality is the design: it means the keys never have to be
           rebuilt from the latent at inference time, so the memory saving
           does not become an arithmetic cost.

  CLAIM 3  The same fold works on the value side, because attention is a
           linear combination of values. Attending over the latents and
           up-projecting once at the end gives the same output as
           up-projecting every value first.

  CLAIM 4  Rotating whole head vectors by their position destroys the fold.
           A single absorbed matrix produces scores whose error is larger
           than the scores themselves, while still being exactly right on
           the diagonal, which is the worst possible failure mode for a
           bug: correct where a spot check would look.

  CLAIM 5  The rotated scores can be rebuilt exactly, at the cost of one
           absorbed matrix per relative distance instead of one per head.
           A decoupled positional channel avoids that by keeping the
           rotation out of the folded product, and the full forward passes
           still agree to better than 1e-10 with it switched on.

WHAT THIS IS NOT. Every claim here is linear algebra and holds for any
weights, trained or not. None of it says whether latent attention costs
model quality; that is an empirical question about trained models and this
repository has no gradients. The published reduction figure is quoted as
that paper's measurement of that model, not reproduced.

Determinism: every weight comes from seed 42. Two runs produce
byte-identical output.

Run:      python3 experiments/week-04/mla_absorption.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  under a second.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.attention import causal_mask  # noqa: E402
from lib.mla import (  # noqa: E402
    MultiHeadLatentAttention,
    cache_comparison,
    max_abs_difference,
    rotary_offsets_needed,
)

D_MODEL = 64
NUM_HEADS = 8
D_HEAD = 8
D_LATENT = 16
D_ROPE = 8
LENGTH = 12
SEED = 42
HEAD_SHOWN = 0

# A serving-scale configuration for the cache table, stated here rather
# than attributed to a released model.
SERVING_HEADS = 64
SERVING_D_HEAD = 128
SERVING_LATENTS = (512, 1024, 2048)
SERVING_D_ROPE = 64

EXACT_ENOUGH = 1e-10


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def measure_cache():
    """CLAIM 1: what the cache costs before and after."""
    heading("THE CACHE, PER TOKEN PER LAYER")
    print()
    print(f"  {SERVING_HEADS} heads of width {SERVING_D_HEAD}, half precision.")
    print("  Standard attention stores a key and a value for every head.")
    print("  Latent attention stores one latent, shared across every head,")
    print(f"  plus a {SERVING_D_ROPE}-wide positional channel, also shared.")
    print()
    print("  d_latent   standard B   latent B   reduction   factor")
    print("  " + "-" * 54)
    comparisons = {}
    for d_latent in SERVING_LATENTS:
        comparison = cache_comparison(
            SERVING_HEADS, SERVING_D_HEAD, d_latent, SERVING_D_ROPE
        )
        comparisons[d_latent] = comparison
        print(
            f"  {d_latent:>8}{comparison.standard_bytes:>13,}"
            f"{comparison.latent_bytes:>11,}"
            f"{comparison.reduction * 100:>11.1f}%{comparison.factor:>9.1f}x"
        )
    print()
    print("  The standard column does not depend on d_latent, which is the")
    print("  point: one number is a property of the head count and the other")
    print("  is a design choice.")
    return comparisons


def measure_absorption(x, mask):
    """CLAIM 2 and CLAIM 3: the fold reproduces the slow path exactly."""
    heading("THE FOLD: SCORING AGAINST THE LATENT WITH NO KEY AT ALL")
    layer = MultiHeadLatentAttention(D_MODEL, NUM_HEADS, D_HEAD, D_LATENT, SEED)
    print()
    print("    q_i . k_j  =  (x_i W_q) . (c_j W_uk)  =  (x_i W_q W_uk^T) . c_j")
    print()
    print("  The bracket depends on the head and on nothing else, so it is")
    print("  computed once. After that a score is a dot product between a")
    print("  projected query and the cached latent.")
    print()
    print("  head   explicit vs folded, largest score difference")
    print("  " + "-" * 52)
    worst_scores = 0.0
    for head in range(NUM_HEADS):
        explicit = layer.content_scores_explicit(x, head)
        folded = layer.content_scores_absorbed(x, head)
        difference = max_abs_difference(explicit, folded)
        worst_scores = max(worst_scores, difference)
        print(f"  {head:>4}{difference:>44.2e}")

    explicit_output, explicit_weights = layer.forward_explicit(x, mask)
    absorbed_output, absorbed_weights = layer.forward_absorbed(x, mask)
    output_difference = max_abs_difference(explicit_output, absorbed_output)
    weight_difference = max(
        max_abs_difference(explicit_weights[head], absorbed_weights[head])
        for head in range(NUM_HEADS)
    )
    standard, latent = layer.cache_widths()
    print()
    print("  FULL FORWARD PASS, BOTH WAYS")
    print(f"    attention weights, largest difference   {weight_difference:.2e}")
    print(f"    layer output, largest difference        {output_difference:.2e}")
    print()
    print("  The value side folds too, because attention is a weighted sum")
    print("  of values and a weighted sum commutes with a linear map:")
    print()
    print("    sum_j w_ij (c_j W_uv)  =  (sum_j w_ij c_j) W_uv")
    print()
    print(f"  cached per token per layer: {standard} values standard, "
          f"{latent} latent")
    return worst_scores, output_difference, weight_difference


def measure_rotation_break(x):
    """CLAIM 4 and CLAIM 5: what position does to the fold, and the repair."""
    heading("WHAT ROTARY POSITION DOES TO THE FOLD")
    layer = MultiHeadLatentAttention(D_MODEL, NUM_HEADS, D_HEAD, D_LATENT, SEED)
    rotated = layer.content_scores_explicit(x, HEAD_SHOWN, rotate_heads=True)
    single = layer.content_scores_absorbed(x, HEAD_SHOWN, offset=0)
    rebuilt = layer.content_scores_absorbed_per_offset(x, HEAD_SHOWN)

    largest = max(abs(value) for row in rotated for value in row)
    single_error = max_abs_difference(rotated, single)
    band_error = max(
        abs(rotated[i][j] - rebuilt[i][j])
        for i in range(LENGTH)
        for j in range(i + 1)
    )
    diagonal_error = max(
        abs(rotated[position][position] - single[position][position])
        for position in range(LENGTH)
    )

    print()
    print("    rot(q_i, i) . rot(k_j, j)  =  x_i  W_q R_(i-j) W_uk^T  c_j")
    print()
    print("  A rotation now sits inside the bracket, and it depends on the")
    print("  distance between the two positions, so the folded matrix is no")
    print("  longer one matrix.")
    print()
    print(f"  largest rotated score, any pair                 {largest:>10.4f}")
    print(f"  error from using ONE fold for everything        {single_error:>10.4f}")
    print(f"  error on the diagonal, where i - j is 0         {diagonal_error:>10.2e}")
    print(f"  error from one fold PER relative distance       {band_error:>10.2e}")
    print()
    print("  Read the middle two lines together. A single fold is exactly")
    print("  right where a position looks at itself and wrong everywhere")
    print("  else, by more than the scores are worth. A spot check of the")
    print("  diagonal would pass.")

    print()
    print("  THE COST OF BEING CORRECT THE OBVIOUS WAY")
    for length in (LENGTH, 4096, 131072):
        print(f"    sequence length {length:>7,}: "
              f"{rotary_offsets_needed(length):>7,} folded matrices per head")
    print()
    print("  THE REPAIR: KEEP THE ROTATION OUT OF THE FOLD")
    print(f"    a shared {D_ROPE}-wide channel carries position, cached once")
    print("    per token for every head, and is never folded")
    print()
    decoupled = MultiHeadLatentAttention(
        D_MODEL, NUM_HEADS, D_HEAD, D_LATENT, SEED, d_rope=D_ROPE
    )
    mask = causal_mask(LENGTH)
    explicit, _ = decoupled.forward_explicit(x, mask)
    absorbed, _ = decoupled.forward_absorbed(x, mask)
    repaired = max_abs_difference(explicit, absorbed)
    unpositioned, _ = MultiHeadLatentAttention(
        D_MODEL, NUM_HEADS, D_HEAD, D_LATENT, SEED
    ).forward_explicit(x, mask)
    position_effect = max_abs_difference(unpositioned, explicit)
    standard, latent = decoupled.cache_widths()
    print(f"    explicit vs folded, with the channel on     {repaired:>10.2e}")
    print(f"    output change caused by the channel         {position_effect:>10.4f}")
    print(f"    cached per token per layer                  "
          f"{latent:>4} values, against {standard} standard")
    print()
    print("  The second line matters. If the channel changed nothing, the")
    print("  first line would prove only that position was ignored.")
    return single_error, largest, diagonal_error, band_error, repaired, position_effect


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]
    mask = causal_mask(LENGTH)

    print("MULTI-HEAD LATENT ATTENTION: THE FOLD AND ITS ONE ENEMY")
    print(
        f"  d_model {D_MODEL}, {NUM_HEADS} heads of width {D_HEAD}, "
        f"latent {D_LATENT}, length {LENGTH}, seed {SEED}"
    )
    print("  untrained weights, standard library only")

    comparisons = measure_cache()
    score_error, output_error, weight_error = measure_absorption(x, mask)
    (
        single_error,
        largest_score,
        diagonal_error,
        band_error,
        repaired_error,
        position_effect,
    ) = measure_rotation_break(x)

    heading("ASSERTIONS")
    for d_latent, comparison in comparisons.items():
        expected_standard = 2 * SERVING_HEADS * SERVING_D_HEAD * 2
        expected_latent = (d_latent + SERVING_D_ROPE) * 2
        assert comparison.standard_bytes == expected_standard, (
            f"CLAIM 1 failed: standard cache is {comparison.standard_bytes}, "
            f"expected {expected_standard}."
        )
        assert comparison.latent_bytes == expected_latent, (
            f"CLAIM 1 failed at d_latent {d_latent}: latent cache is "
            f"{comparison.latent_bytes}, expected {expected_latent}."
        )
        assert comparison.reduction > 0.0, (
            f"CLAIM 1 failed at d_latent {d_latent}: the latent cache is not "
            "smaller, so there is no compression to report."
        )
    print("  CLAIM 1  the latent cache is smaller, by stated arithmetic ..... ok")

    assert score_error < EXACT_ENOUGH, (
        f"CLAIM 2 failed: folded scores differ from explicit ones by "
        f"{score_error:.2e}, expected under {EXACT_ENOUGH:.0e}."
    )
    assert weight_error < EXACT_ENOUGH, (
        f"CLAIM 2 failed: attention weights differ by {weight_error:.2e}."
    )
    print("  CLAIM 2  the key fold reproduces the explicit scores ........... ok")

    assert output_error < EXACT_ENOUGH, (
        f"CLAIM 3 failed: layer outputs differ by {output_error:.2e}, so the "
        "value side of the fold is not equivalent."
    )
    print("  CLAIM 3  the value fold reproduces the explicit output ......... ok")

    assert single_error > largest_score * 0.5, (
        f"CLAIM 4 failed: a single fold under rotation was off by only "
        f"{single_error:.4f} against scores reaching {largest_score:.4f}. "
        "The break is not as decisive as the article says."
    )
    assert diagonal_error < 1e-8, (
        f"CLAIM 4 failed: the diagonal is off by {diagonal_error:.2e}, so the "
        "claim that a spot check would pass is wrong."
    )
    print("  CLAIM 4  rotation breaks the fold, and hides on the diagonal ... ok")

    assert band_error < 1e-8, (
        f"CLAIM 5 failed: one fold per offset still misses by "
        f"{band_error:.2e}, so the rebuild is not exact."
    )
    assert repaired_error < EXACT_ENOUGH, (
        f"CLAIM 5 failed: with the decoupled channel the two paths differ by "
        f"{repaired_error:.2e}."
    )
    assert position_effect > 1e-6, (
        "CLAIM 5 failed: the decoupled channel changed nothing, so the "
        "agreement above proves only that position was ignored."
    )
    print("  CLAIM 5  a decoupled channel restores the fold, and matters .... ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
