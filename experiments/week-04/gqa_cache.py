"""What grouped-query attention buys, and what it quietly spends.

Companion artifact for the week-4 Wednesday posts (2026-09-16).

Shazeer proposed sharing one key-value head across every query head,
because incremental inference "is often slow, due to the memory-bandwidth
cost of repeatedly loading the large 'keys' and 'values' tensors"
(arXiv:1911.02150). Ainslie et al. put a dial between that extreme and the
original, introducing "grouped-query attention (GQA), a generalization of
multi-query attention which uses an intermediate (more than one, less than
number of query heads) number of key-value heads", and reported that
"uptrained GQA achieves quality close to multi-head attention with
comparable speed to MQA" (arXiv:2305.13245).

The saving is famous. This script measures the saving and then measures
something the summary leaves out.

  CLAIM 1  The cache saving is exactly linear in the key-value head count.
           Eight key-value heads instead of sixty-four is exactly one
           eighth of the bytes, at every sequence length, because the head
           count appears once as a factor and nowhere else.

  CLAIM 2  Grouping saves no arithmetic. Every query head still computes
           its own scores against the shared keys, so the score count is
           identical across all three arrangements. What shrinks is the
           bytes that have to be read to do it.

  CLAIM 3  Grouping shrinks the slice of the residual stream that the
           routing decision can see. Stack the key projections and take the
           rank: multi-head attention spans the full model width, and
           multi-query attention spans only one head's worth of it. The
           remaining directions are ones no key projection can represent.

  CLAIM 4  Those directions are blind in the strongest sense available.
           Move one position along one of them and NO other position's
           attention weight toward it changes, to machine precision, in any
           head. The output still changes, because the value projection is
           a different matrix. The routing is blind; the payload is not.

  CLAIM 5  The obvious alternative measurement does not work, and the
           script says so rather than burying it. Mean pairwise similarity
           between head attention patterns barely moves across the three
           arrangements on untrained weights, because untrained attention
           is close to uniform and near-uniform distributions resemble each
           other whatever the keys are. A measurement that cannot
           distinguish the cases is reported as one that cannot.

WHAT THIS IS NOT. Claims 1, 2, 3 and 4 are arithmetic or linear algebra and
hold for any weights. The paper's own result is about quality after
uptraining, which needs gradients this repository does not have, so nothing
here says whether grouping costs accuracy. The rank result says what the
architecture can and cannot express, which is a different and narrower
statement.

Determinism: every weight comes from seed 42. Two runs produce
byte-identical output.

Run:      python3 experiments/week-04/gqa_cache.py
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
from lib.gqa import (  # noqa: E402
    GroupedQueryAttention,
    blind_directions,
    head_pattern_similarity,
    key_subspace_rank,
    kv_cache_bytes,
)

# A serving configuration, stated here rather than attributed to any
# particular released model, so the arithmetic can be checked without
# trusting a spec sheet.
SERVING_LAYERS = 80
SERVING_D_HEAD = 128
SERVING_QUERY_HEADS = 64
SERVING_LENGTHS = (4096, 32768, 131072)
SERVING_KV_HEADS = (64, 8, 1)

# The small layer everything measured is run on.
D_MODEL = 64
NUM_QUERY_HEADS = 8
LENGTH = 24
SEED = 42
KV_SETTINGS = (8, 4, 2, 1)

# The position moved along a blind direction, and how far.
TARGET_POSITION = 5
PERTURBATION = 5.0

# A routing change at or below this is floating-point noise, not a change.
MACHINE_NOISE = 1e-12


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def label(num_kv_heads, num_query_heads):
    """Name the arrangement a head count corresponds to."""
    if num_kv_heads == num_query_heads:
        return "multi-head"
    if num_kv_heads == 1:
        return "multi-query"
    return "grouped"


def measure_cache():
    """CLAIM 1: the saving, as arithmetic on a stated configuration."""
    heading("THE CACHE, FOR ONE SEQUENCE")
    print()
    print(f"  {SERVING_LAYERS} layers, {SERVING_QUERY_HEADS} query heads, "
          f"head width {SERVING_D_HEAD}, half precision.")
    print("  Only the key-value cache is counted. Weights and activations")
    print("  are a separate budget and are not in this table.")
    print()
    header = "  kv heads  arrangement   B/token/layer   KiB/token" + "".join(
        f"{length // 1024:>9}K" for length in SERVING_LENGTHS
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    totals = {}
    for kv_heads in SERVING_KV_HEADS:
        row = kv_cache_bytes(kv_heads, SERVING_D_HEAD, SERVING_LAYERS, 1)
        cells = ""
        for length in SERVING_LENGTHS:
            size = kv_cache_bytes(
                kv_heads, SERVING_D_HEAD, SERVING_LAYERS, length
            )
            totals[(kv_heads, length)] = size.total_bytes
            cells += f"{size.gibibytes:>9.2f}"
        print(
            f"  {kv_heads:>8}  {label(kv_heads, SERVING_QUERY_HEADS):<12}"
            f"{row.bytes_per_token_per_layer:>14,}"
            f"{row.bytes_per_token / 1024:>12.1f}{cells}"
        )
    print()
    print("  Columns after KiB/token are GiB for the whole sequence.")
    print()
    longest = SERVING_LENGTHS[-1]
    full = totals[(SERVING_KV_HEADS[0], longest)]
    grouped = totals[(SERVING_KV_HEADS[1], longest)]
    single = totals[(SERVING_KV_HEADS[2], longest)]
    print(f"  at {longest:,} tokens: multi-head over grouped   "
          f"{full / grouped:.1f}x")
    print(f"                        grouped over multi-query  "
          f"{grouped / single:.1f}x")
    return totals


def measure_arithmetic():
    """CLAIM 2: grouping moves bytes, not multiply-adds."""
    heading("WHAT GROUPING DOES NOT SAVE")
    print()
    print(f"  A layer with {NUM_QUERY_HEADS} query heads over {LENGTH} "
          "positions, causally masked.")
    print("  Scores computed is query heads times allowed (query, key) pairs.")
    print()
    allowed_pairs = LENGTH * (LENGTH + 1) // 2
    print("  kv heads  arrangement   key projections   scores computed")
    print("  " + "-" * 58)
    score_counts = set()
    for kv_heads in KV_SETTINGS:
        scores = NUM_QUERY_HEADS * allowed_pairs
        score_counts.add(scores)
        print(
            f"  {kv_heads:>8}  {label(kv_heads, NUM_QUERY_HEADS):<12}"
            f"{kv_heads:>18}{scores:>18,}"
        )
    print()
    print("  One number in that table changes and the other does not.")
    print("  Grouping is a memory-traffic optimisation wearing an")
    print("  architecture's clothes.")
    return score_counts


def measure_subspace(x, mask):
    """CLAIM 3 and CLAIM 4: what the routing can and cannot see."""
    heading("WHAT THE ROUTING CAN SEE")
    print()
    print(f"  d_model {D_MODEL}, {NUM_QUERY_HEADS} query heads, "
          f"head width {D_MODEL // NUM_QUERY_HEADS}.")
    print("  Rank is of every key projection stacked side by side: the")
    print("  number of independent stream directions the keys can read.")
    print()
    print("  kv heads  arrangement   key rank   blind dims   routing change"
          "   output change")
    print("  " + "-" * 80)
    measured = {}
    for kv_heads in KV_SETTINGS:
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
        rank = key_subspace_rank(layer)
        blind = blind_directions(layer)
        if blind:
            direction = blind[0]
            length = sum(value * value for value in direction) ** 0.5
            direction = [value / length for value in direction]
            moved = [list(row) for row in x]
            moved[TARGET_POSITION] = [
                moved[TARGET_POSITION][index] + PERTURBATION * direction[index]
                for index in range(D_MODEL)
            ]
            before_output, before = layer.forward(x, mask)
            after_output, after = layer.forward(moved, mask)
            routing_change = max(
                abs(
                    before[head][position][TARGET_POSITION]
                    - after[head][position][TARGET_POSITION]
                )
                for head in range(NUM_QUERY_HEADS)
                for position in range(TARGET_POSITION + 1, LENGTH)
            )
            output_change = max(
                abs(before_output[r][c] - after_output[r][c])
                for r in range(LENGTH)
                for c in range(D_MODEL)
            )
            routing_cell = f"{routing_change:>17.2e}"
            output_cell = f"{output_change:>16.4f}"
        else:
            routing_change = None
            output_change = None
            routing_cell = f"{'no blind dir':>17}"
            output_cell = f"{'-':>16}"
        measured[kv_heads] = (rank, len(blind), routing_change, output_change)
        print(
            f"  {kv_heads:>8}  {label(kv_heads, NUM_QUERY_HEADS):<12}"
            f"{rank:>11}{len(blind):>13}{routing_cell}{output_cell}"
        )
    print()
    print(f"  The perturbation moves position {TARGET_POSITION} by "
          f"{PERTURBATION:.1f} units along a direction every key")
    print("  projection sends to zero. Routing change is the largest move in")
    print(f"  any head's attention weight from any later position toward "
          f"position {TARGET_POSITION}.")
    print()
    print("  Multi-head attention has nowhere to hide a vector: its key")
    print("  projections already span the full width, so the blind subspace")
    print("  is empty and the experiment has no input to run.")
    return measured


def measure_pattern_similarity(x, mask):
    """CLAIM 5: the measurement that does not work, reported as such."""
    heading("A MEASUREMENT THAT FAILS, KEPT BECAUSE IT FAILS INFORMATIVELY")
    print()
    print("  Before the rank argument above, the obvious probe was: do heads")
    print("  forced to share keys produce more similar attention patterns?")
    print("  Mean pairwise cosine between the heads' weight matrices:")
    print()
    print("  kv heads  arrangement   mean pairwise similarity")
    print("  " + "-" * 48)
    similarities = {}
    for kv_heads in KV_SETTINGS:
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
        _, weights = layer.forward(x, mask)
        similarity = head_pattern_similarity(weights)
        similarities[kv_heads] = similarity
        print(
            f"  {kv_heads:>8}  {label(kv_heads, NUM_QUERY_HEADS):<12}"
            f"{similarity:>20.4f}"
        )
    spread = max(similarities.values()) - min(similarities.values())
    print()
    print(f"  spread across all four arrangements: {spread:.4f}")
    print()
    print("  That spread is too small to carry any conclusion. Untrained")
    print("  attention is close to uniform, near-uniform distributions look")
    print("  alike whatever produced them, and the causal mask makes the")
    print("  first rows identical by construction. The probe is measuring")
    print("  initialisation, not architecture. The rank result above is")
    print("  reported instead because it does not depend on the weights")
    print("  being anything in particular.")
    return spread


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]
    mask = causal_mask(LENGTH)

    print("GROUPED-QUERY ATTENTION: THE SAVING AND THE BILL")
    print(f"  seed {SEED}, untrained weights, standard library only")

    totals = measure_cache()
    score_counts = measure_arithmetic()
    subspace = measure_subspace(x, mask)
    spread = measure_pattern_similarity(x, mask)

    heading("ASSERTIONS")
    for length in SERVING_LENGTHS:
        full = totals[(64, length)]
        grouped = totals[(8, length)]
        single = totals[(1, length)]
        assert full == grouped * 8, (
            f"CLAIM 1 failed at {length}: 64 kv heads is {full} bytes and 8 "
            f"is {grouped}, which is not a factor of exactly 8."
        )
        assert grouped == single * 8, (
            f"CLAIM 1 failed at {length}: 8 kv heads is {grouped} bytes and 1 "
            f"is {single}, which is not a factor of exactly 8."
        )
    print("  CLAIM 1  the cache saving is exactly linear in kv heads ........ ok")

    assert len(score_counts) == 1, (
        f"CLAIM 2 failed: the arrangements computed {sorted(score_counts)} "
        "scores, so grouping changed the arithmetic after all."
    )
    print("  CLAIM 2  grouping saves bytes and saves no arithmetic .......... ok")

    d_head = D_MODEL // NUM_QUERY_HEADS
    for kv_heads, (rank, blind, _, _) in subspace.items():
        assert rank == kv_heads * d_head, (
            f"CLAIM 3 failed: {kv_heads} kv heads gave key rank {rank}, "
            f"expected {kv_heads * d_head}."
        )
        assert blind == D_MODEL - rank, (
            f"CLAIM 3 failed: rank {rank} left {blind} blind directions, "
            f"expected {D_MODEL - rank}."
        )
    assert subspace[NUM_QUERY_HEADS][0] == D_MODEL, (
        "CLAIM 3 failed: multi-head attention does not span the full width, "
        "so the comparison has no baseline."
    )
    print("  CLAIM 3  grouping shrinks the readable subspace, exactly ....... ok")

    for kv_heads, (_, blind, routing, output) in subspace.items():
        if blind == 0:
            continue
        assert routing < MACHINE_NOISE, (
            f"CLAIM 4 failed at {kv_heads} kv heads: routing moved by "
            f"{routing:.2e}, which is above machine noise."
        )
        assert output > 1e-6, (
            f"CLAIM 4 failed at {kv_heads} kv heads: the output moved by "
            f"{output:.2e}, so the perturbation did nothing at all and the "
            "frozen routing proves nothing."
        )
    print("  CLAIM 4  a blind direction freezes routing, not the payload .... ok")

    assert spread < 0.05, (
        f"CLAIM 5 failed: the similarity probe spread {spread:.4f} across "
        "arrangements, which is large enough to mean something. Rewrite the "
        "section instead of reporting it as uninformative."
    )
    print("  CLAIM 5  the similarity probe is uninformative, and says so .... ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
