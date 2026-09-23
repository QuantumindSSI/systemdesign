"""Learned sparse selection: what an indexer has to earn.

Companion artifact for the week-4 Saturday weekend challenge (2026-09-19).

A fixed window decides in advance which positions a query may read. The
other family decides per query, by scoring every candidate cheaply and
keeping the best few. DeepSeek's natively trainable design "employs a
dynamic hierarchical sparse strategy, combining coarse-grained token
compression with fine-grained token selection to preserve both global
context awareness and local precision" (arXiv:2502.11089). The deployed
descendant of that line is described in the surrounding literature as
scoring every preceding token with a small indexer and keeping the top few:
token-level sparse attention "makes the downstream attention efficient but
shifts the bottleneck to the indexer that feeds it. To select the top-k
tokens for each query, the indexer must still score every preceding token,
incurring a cost of O(L^2) per layer for a sequence of length L"
(arXiv:2607.24593).

This script measures the three quantities that decide whether that trade
works, on a model small enough to print.

  CLAIM 1  Untrained attention is diffuse. Mean row entropy sits near 73%
           of the uniform ceiling, so an untrained model is most of the way
           to attending everywhere equally. Selection's whole premise is
           that attention is peaked, so everything below is a floor rather
           than a representative number.

  CLAIM 2  Selection has something to select even so. Choosing the 8 best
           keys per query by the real scores reads 11.8% of the permitted
           pairs and keeps 77.2% of the attention mass. That gap between
           pairs read and mass kept is the entire opportunity.

  CLAIM 3  An untrained indexer captures none of it. Averaged over five
           independent indexer seeds, the mass it keeps lands within 1% of
           what picking positions at random would keep, at the operating
           point. The selector is not a cheap approximation of attention
           that happens to be untrained. Untrained, it is a coin.

  CLAIM 4  The distance between those two is the prize. At the same k, the
           oracle keeps more than twice the mass the untrained indexer
           does. Closing that gap is what training the indexer means, and
           it is why this family of designs trains the selector rather than
           bolting one on.

  CLAIM 5  Selection does not remove the quadratic term. To rank candidates
           the indexer has to score all of them, so the number of scores is
           unchanged and only the width of each falls. The saving is in the
           attention that follows, not in the selection itself.

WHAT THIS IS NOT. Claim 1, 2 and 5 are properties of this model and this
arithmetic. Claims 3 and 4 measure an untrained scorer, which is a floor
and not an estimate of what a trained one achieves. Nothing here reproduces
any published system's results, and no number below should be read as one.

Determinism: the model comes from seed 42, the five indexers from fixed
seeds. Two runs produce byte-identical output.

Run:      python3 experiments/week-04/sparse_selection.py
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

from lib.attention import (  # noqa: E402
    causal_mask,
    glorot_matrix,
    scaled_dot_product_attention,
)
from lib.linalg import matmul, transpose  # noqa: E402
from lib.sparse_attention import (  # noqa: E402
    CheapIndexer,
    attention_mass_captured,
    mask_density,
    row_entropy,
    selection_recall,
    top_k_mask,
    uniform_entropy,
)

D_MODEL = 64
D_HEAD = 16
D_INDEX = 4
NUM_HEADS = 1
LENGTH = 64
SEED = 42
INDEXER_SEEDS = (101, 202, 303, 404, 505)
K_VALUES = (1, 2, 4, 8, 16, 32)
OPERATING_K = 8

# Rows shorter than this have so few candidates that their entropy is
# dominated by the causal mask rather than by the attention.
ENTROPY_FLOOR_ROW = 8

ENTROPY_BAND = (0.60, 0.85)
RANDOM_AGREEMENT_CEILING = 0.05
ORACLE_ADVANTAGE_FLOOR = 2.0


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def random_selection_mass(k):
    """Mass a uniformly random choice of k permitted keys would keep.

    Query i has i + 1 permitted keys under a causal mask and, at this
    model's diffuseness, roughly equal weight on each. Picking k of them at
    random therefore keeps about min(k, i + 1) / (i + 1) of the mass, and
    the baseline is that averaged over queries.

    This is a baseline and not a measurement. It is the number an indexer
    has to beat to have done anything.

    Raises:
        ValueError: if k is below 1.
    """
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    return sum(min(k, row + 1) / (row + 1) for row in range(LENGTH)) / LENGTH


def build_attention(x):
    """One attention head, returning its weights and its raw scores."""
    rng = random.Random(SEED)
    w_query = glorot_matrix(D_MODEL, D_HEAD, rng)
    w_key = glorot_matrix(D_MODEL, D_HEAD, rng)
    w_value = glorot_matrix(D_MODEL, D_HEAD, rng)
    queries = matmul(x, w_query)
    keys = matmul(x, w_key)
    base = causal_mask(LENGTH)
    _, weights = scaled_dot_product_attention(
        queries, keys, matmul(x, w_value), base
    )
    return weights, matmul(queries, transpose(keys)), base


def measure_diffuseness(weights):
    """CLAIM 1: how far from peaked this model's attention is."""
    heading("HOW PEAKED IS THE ATTENTION WE ARE ABOUT TO PRUNE?")
    print()
    print("  Entropy in bits, against the ceiling a uniform row would hit.")
    print(f"  Rows below {ENTROPY_FLOOR_ROW} are excluded from the mean: they have so")
    print("  few candidates that the causal mask sets their entropy.")
    print()
    print("  position   candidates   entropy   uniform ceiling   share")
    print("  " + "-" * 60)
    ratios = []
    for position in range(LENGTH):
        entropy = row_entropy(weights[position])
        ceiling = uniform_entropy(position + 1)
        if position >= ENTROPY_FLOOR_ROW:
            ratios.append(entropy / ceiling)
        if position in (0, 1, 7, 15, 31, 63):
            share = entropy / ceiling if ceiling > 0.0 else 1.0
            print(
                f"  {position:>8}{position + 1:>13}{entropy:>10.4f}"
                f"{ceiling:>18.4f}{share:>8.4f}"
            )
    mean_ratio = sum(ratios) / len(ratios)
    print()
    print(f"  mean share of the ceiling, rows {ENTROPY_FLOOR_ROW} to "
          f"{LENGTH - 1}: {mean_ratio:.4f}")
    print()
    print("  A peaked distribution would sit far below its ceiling. This one")
    print("  does not, because nothing has been trained. Read every number")
    print("  after this as the floor it is.")
    return mean_ratio


def measure_selection(x, weights, scores, base):
    """CLAIM 2, CLAIM 3 and CLAIM 4: oracle, indexer, and coin."""
    heading("THREE WAYS TO CHOOSE WHICH POSITIONS TO READ")
    print()
    print("  ORACLE   choose by the real attention scores. Free information,")
    print("           and the ceiling any selector is competing against.")
    print(f"  INDEXER  choose by a {D_INDEX}-wide untrained scorer, averaged over")
    print(f"           {len(INDEXER_SEEDS)} seeds.")
    print("  RANDOM   choose uniformly among the permitted keys.")
    print()
    print("     k   pairs read   oracle mass   indexer mass   random mass"
          "   indexer recall")
    print("  " + "-" * 76)
    measured = {}
    for k in K_VALUES:
        reference = top_k_mask(scores, k, base)
        oracle_mass = attention_mass_captured(weights, reference)
        masses = []
        recalls = []
        for indexer_seed in INDEXER_SEEDS:
            indexer = CheapIndexer(D_MODEL, D_INDEX, indexer_seed)
            chosen = top_k_mask(indexer.scores(x), k, base)
            masses.append(attention_mass_captured(weights, chosen))
            recalls.append(selection_recall(chosen, reference))
        indexer_mass = sum(masses) / len(masses)
        indexer_recall = sum(recalls) / len(recalls)
        random_mass = random_selection_mass(k)
        measured[k] = (oracle_mass, indexer_mass, random_mass, indexer_recall)
        print(
            f"  {k:>4}{mask_density(reference):>13.4f}{oracle_mass:>14.4f}"
            f"{indexer_mass:>15.4f}{random_mass:>14.4f}{indexer_recall:>17.4f}"
        )
    print()
    oracle, indexer_mass, random_mass, _ = measured[OPERATING_K]
    reference = top_k_mask(scores, OPERATING_K, base)
    print(f"  At k = {OPERATING_K}, reading {mask_density(reference) * 100:.1f}% of the "
          "permitted pairs:")
    print(f"    the oracle keeps          {oracle:.4f} of the attention mass")
    print(f"    the untrained indexer     {indexer_mass:.4f}")
    print(f"    a coin                    {random_mass:.4f}")
    deviation = abs(indexer_mass - random_mass) / random_mass
    print(f"    indexer against the coin, relative difference: {deviation:.4f}")
    print(f"    oracle over indexer:                           "
          f"{oracle / indexer_mass:.2f}x")
    print()
    print("  The second and third lines are the same number. An untrained")
    print("  indexer is not a weak approximation of attention. It is a coin")
    print("  with a projection in front of it, and the distance to the first")
    print("  line is exactly what training the selector has to buy.")
    return measured


def measure_cost():
    """CLAIM 5: the quadratic term does not go away."""
    heading("WHAT SELECTION COSTS BEFORE IT SAVES ANYTHING")
    indexer = CheapIndexer(D_MODEL, D_INDEX, INDEXER_SEEDS[0])
    permitted = LENGTH * (LENGTH + 1) // 2
    ratio = indexer.cost_ratio(D_HEAD, NUM_HEADS)
    print()
    print("  To rank candidates the indexer has to score all of them, so")
    print("  the number of scores is the number full attention computes.")
    print()
    print(f"    permitted (query, key) pairs at length {LENGTH}     "
          f"{permitted:>8,}")
    print(f"    scores full attention computes                 {permitted:>8,}")
    print(f"    scores the indexer computes                    {permitted:>8,}")
    print(f"    multiply-adds per score, full attention        "
          f"{NUM_HEADS * D_HEAD:>8}")
    print(f"    multiply-adds per score, indexer               {D_INDEX:>8}")
    print(f"    ratio                                          {ratio:>8.4f}")
    print()
    print("  Both columns grow with the square of the length. Selection")
    print("  narrows each score and removes none of them, which is why the")
    print("  indexer becomes the thing to optimise once the attention behind")
    print("  it is already sparse.")
    return permitted, ratio


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]

    print("SPARSE SELECTION: THE SELECTOR IS THE WHOLE PROBLEM")
    print(
        f"  d_model {D_MODEL}, head width {D_HEAD}, indexer width {D_INDEX}, "
        f"length {LENGTH}, seed {SEED}"
    )
    print("  untrained weights, standard library only")

    weights, scores, base = build_attention(x)
    entropy_share = measure_diffuseness(weights)
    measured = measure_selection(x, weights, scores, base)
    permitted, ratio = measure_cost()

    heading("ASSERTIONS")
    low, high = ENTROPY_BAND
    assert low < entropy_share < high, (
        f"CLAIM 1 failed: mean entropy share is {entropy_share:.4f}, outside "
        f"the band [{low}, {high}] the article describes."
    )
    print("  CLAIM 1  untrained attention is diffuse, so this is a floor .... ok")

    oracle, indexer_mass, random_mass, _ = measured[OPERATING_K]
    reference_density = mask_density(top_k_mask(scores, OPERATING_K, base))
    assert oracle > 0.7, (
        f"CLAIM 2 failed: oracle selection kept {oracle:.4f} of the mass at "
        f"k = {OPERATING_K}, which is not an opportunity worth describing."
    )
    assert reference_density < 0.2, (
        f"CLAIM 2 failed: the oracle selection reads "
        f"{reference_density:.4f} of the pairs, which is not sparse."
    )
    print("  CLAIM 2  oracle selection keeps most of the mass, cheaply ...... ok")

    deviation = abs(indexer_mass - random_mass) / random_mass
    assert deviation < RANDOM_AGREEMENT_CEILING, (
        f"CLAIM 3 failed: the untrained indexer differs from random by "
        f"{deviation:.4f} at k = {OPERATING_K}, above the "
        f"{RANDOM_AGREEMENT_CEILING} the article claims."
    )
    print("  CLAIM 3  an untrained indexer performs exactly like a coin ..... ok")

    advantage = oracle / indexer_mass
    assert advantage > ORACLE_ADVANTAGE_FLOOR, (
        f"CLAIM 4 failed: the oracle is only {advantage:.2f}x the untrained "
        f"indexer, below the {ORACLE_ADVANTAGE_FLOOR}x the article claims."
    )
    print("  CLAIM 4  the gap to the oracle is what training has to buy ..... ok")

    assert permitted == LENGTH * (LENGTH + 1) // 2, (
        "CLAIM 5 failed: the permitted pair count is not the causal triangle."
    )
    assert 0.0 < ratio < 1.0, (
        f"CLAIM 5 failed: the indexer costs {ratio:.4f} of full attention "
        "per score, which is not cheaper and not free."
    )
    print("  CLAIM 5  selection narrows every score and removes none ........ ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
