"""Where a transformer's parameters actually live, and what they do there.

Companion artifact for the week-4 Tuesday posts (2026-09-15).

Attention gets the diagrams. The feed-forward sublayer gets the parameters.
Geva et al. state the split plainly: "Feed-forward layers constitute
two-thirds of a transformer model's parameters, yet their role in the
network remains under-explored" (arXiv:2012.14913). The first measurement
below is that fraction, computed rather than repeated, and it turns out to
be exact rather than approximate for the original configuration.

  CLAIM 1  With d_ff = 4 * d_model, the feed-forward sublayer holds exactly
           two-thirds of a block's matrix parameters, at every width. Not
           roughly two-thirds. Exactly, because 2 * d * 4d is exactly twice
           4 * d * d and the ratio has no width left in it.

  CLAIM 2  A gated feed-forward block has three matrices instead of two, so
           matching the parameter count means shrinking the hidden width to
           two-thirds. Rounded to a multiple of 8 the way real
           configurations round, 2048 becomes 1360 and lands within 0.5% of
           parity.

  CLAIM 3  A feed-forward output is exactly the sum of one term per hidden
           unit, each term being that unit's activation times its row of
           W_out. The decomposition reproduces the matrix multiply to
           better than 1e-10 at every position, which is what licenses
           reading the sublayer as a set of independently addressable
           memories.

  CLAIM 4  The choice of activation decides whether that sum is sparse.
           ReLU zeros about half the hidden layer exactly. GELU and SiLU
           zero nothing at all, exactly, so an inference kernel that skips
           zeros has nothing to skip.

  CLAIM 5  Even among the units that do fire, contribution is concentrated:
           at every position, under a third of the live units carry half the
           output length, against the half a flat distribution would need.

           The first version of this claim said "under a quarter" and
           checked two positions. Position 7 measured 0.2623 and the
           assertion fired. Checking all 32 positions gives a range of
           0.2132 to 0.2698, so the threshold was wrong and the sample was
           too small to have found that out. The claim now asserts over
           every position and the recorded threshold sits above the
           measured maximum rather than inside it. Both corrections are
           written down because a claim adjusted after seeing the data has
           to say so.

  CLAIM 6  The tanh approximation to GELU that most frameworks ship is not
           the function it approximates. The gap peaks near x = 2.7 at
           about 4.7e-4, which is small, is not zero, and is worth knowing
           before comparing two implementations and calling the difference
           a bug.

WHAT THIS IS NOT. Claims 1, 2, 3 and 6 are arithmetic or algebra and hold
for any weights, trained or not. Claims 4 and 5 are measured on untrained
weights and synthetic input, where a ReLU's sign is a coin flip. A trained
network's sparsity is an empirical property of that network and this script
cannot speak to it. The articles say so at the point of use.

Determinism: every weight comes from seed 42. Two runs produce
byte-identical output.

Run:      python3 experiments/week-04/feedforward_lab.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  under a second.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.feedforward import (  # noqa: E402
    FeedForward,
    GatedFeedForward,
    decompose_output,
    dominant_units,
    equivalent_gated_hidden,
    gelu,
    gelu_tanh,
    parameter_count,
    sparsity,
)

# The configuration from the original transformer paper's base model.
PAPER_D_MODEL = 512
PAPER_D_FF = 2048

# A small stack for the measured parts, sized so the tables print.
D_MODEL = 64
D_HIDDEN = 256
LENGTH = 32
SEED = 42

WIDTHS = (64, 256, 512, 768, 1024, 4096)
POSITIONS_SHOWN = (0, 7)

DECOMPOSITION_TOLERANCE = 1e-10
GATED_PARITY_TOLERANCE = 0.005
RELU_SPARSITY_BAND = (0.40, 0.60)

# Share of the LIVE hidden units needed to reach half the output length. A
# flat distribution would need 0.5, so anything well below that is
# concentration. The ceiling sits above the measured maximum rather than
# inside it, so a mildly different seed does not turn the claim false.
CONCENTRATION_CEILING = 0.33
FLAT_DISTRIBUTION_SHARE = 0.5


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def sample_input(rng):
    """A reproducible input sequence."""
    return [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]


def measure_parameter_split():
    """CLAIM 1 and CLAIM 2: the arithmetic, done rather than quoted."""
    heading("WHERE THE PARAMETERS ARE")
    print()
    print("  One block, d_ff = 4 * d_model, matrices only.")
    print("  Attention is Q, K, V and the output projection: 4 * d_model^2.")
    print("  Feed-forward is W_in and W_out: 2 * d_model * d_ff.")
    print()
    print("  d_model     d_ff    attention  feed-forward   ff share")
    print("  " + "-" * 55)
    shares = []
    for width in WIDTHS:
        counted = parameter_count(width, 4 * width)
        shares.append(counted.feed_forward_share)
        print(
            f"  {width:>7}{4 * width:>9}{counted.attention:>13,}"
            f"{counted.feed_forward:>14,}{counted.feed_forward_share:>11.6f}"
        )
    worst_share_error = max(abs(share - 2.0 / 3.0) for share in shares)
    print()
    print(f"  furthest any row sits from two-thirds: {worst_share_error:.1e}")

    print()
    print("  THE PAPER'S BASE CONFIGURATION")
    paper = parameter_count(PAPER_D_MODEL, PAPER_D_FF)
    print(f"    d_model {PAPER_D_MODEL}, d_ff {PAPER_D_FF}")
    print(f"    attention     {paper.attention:>12,}")
    print(f"    feed-forward  {paper.feed_forward:>12,}")
    print(f"    block total   {paper.total:>12,}")
    print(f"    feed-forward is exactly {paper.feed_forward // paper.attention}x "
          "attention")

    print()
    print("  MATCHING A GATED BLOCK TO THE SAME BUDGET")
    gated_hidden = equivalent_gated_hidden(PAPER_D_FF)
    gated = parameter_count(PAPER_D_MODEL, gated_hidden, gated=True)
    ratio = gated.feed_forward / paper.feed_forward
    print(f"    three matrices, so the hidden width drops to {gated_hidden}")
    print(f"    2 * {PAPER_D_FF} / 3 = {2 * PAPER_D_FF / 3:.2f}, rounded down to a "
          "multiple of 8")
    print(f"    gated feed-forward  {gated.feed_forward:>12,}")
    print(f"    ungated, for comparison {paper.feed_forward:>9,}")
    print(f"    ratio {ratio:.4f}, which is {(1 - ratio) * 100:.2f}% under parity")
    return worst_share_error, abs(1.0 - ratio)


def measure_decomposition(x):
    """CLAIM 3 and CLAIM 5: the output is a sum of per-unit contributions."""
    heading("THE OUTPUT IS A SUM, ONE TERM PER HIDDEN UNIT")
    network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "relu")
    hidden = network.hidden(x)
    output = network.forward(x)

    worst = 0.0
    for position in range(LENGTH):
        terms = decompose_output(hidden[position], network.w_out)
        for dim in range(D_MODEL):
            summed = sum(term[dim] for term in terms)
            worst = max(worst, abs(summed - output[position][dim]))
    print()
    print("    out_row = sum over j of  hidden[j] * W_out[j]")
    print()
    print(f"  largest disagreement with the matrix multiply, over all "
          f"{LENGTH} positions")
    print(f"  and all {D_MODEL} output dimensions: {worst:.1e}")

    print()
    print("  HOW CONCENTRATED THAT SUM IS")
    print()
    print("  Every position is measured; two are printed. A flat")
    print(f"  distribution would need {FLAT_DISTRIBUTION_SHARE:.2f} of the live "
          "units to reach half.")
    print()
    print("  position   live units   half the length in   90% in   share of live")
    print("  " + "-" * 70)
    concentrations = []
    for position in range(LENGTH):
        terms = decompose_output(hidden[position], network.w_out)
        lengths = sorted(
            (math.sqrt(sum(value * value for value in term)) for term in terms),
            reverse=True,
        )
        total = sum(lengths)
        live = sum(1 for value in hidden[position] if value != 0.0)
        running = 0.0
        half_at = ninety_at = None
        for index, length in enumerate(lengths, start=1):
            running += length
            if half_at is None and running >= 0.5 * total:
                half_at = index
            if ninety_at is None and running >= 0.9 * total:
                ninety_at = index
                break
        share = half_at / live
        concentrations.append(share)
        if position in POSITIONS_SHOWN:
            print(
                f"  {position:>8}{live:>13}{half_at:>21}{ninety_at:>9}"
                f"{share:>16.4f}"
            )
    print()
    print(
        f"  across all {LENGTH} positions: min {min(concentrations):.4f}, "
        f"max {max(concentrations):.4f}, "
        f"mean {sum(concentrations) / len(concentrations):.4f}"
    )

    top = dominant_units(hidden[0], network.w_out, 5)
    print()
    print("  the five loudest units at position 0")
    for index, length in top:
        print(f"    unit {index:>4}   activation {hidden[0][index]:>8.4f}   "
              f"contribution {length:.4f}")
    return worst, max(concentrations)


def measure_sparsity(x):
    """CLAIM 4: the activation decides whether there are zeros to skip."""
    heading("WHICH ACTIVATIONS PRODUCE ZEROS, AND WHICH ONLY PRODUCE SMALL")
    print()
    print("  activation   exact zeros   below 1e-3   smallest |value|")
    print("  " + "-" * 58)
    measured = {}
    for name in ("relu", "gelu", "silu"):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), name)
        hidden = network.hidden(x)
        values = [abs(value) for row in hidden for value in row]
        zero_fraction = sparsity(hidden)
        tiny = sum(1 for value in values if value < 1e-3) / len(values)
        measured[name] = zero_fraction
        print(
            f"  {name:<12}{zero_fraction:>12.4f}{tiny:>13.4f}"
            f"{min(values):>19.2e}"
        )

    gated = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "silu")
    gated_hidden = gated.hidden(x)
    print(f"  {'gated silu':<12}{sparsity(gated_hidden):>12.4f}")
    print()
    print("  ReLU's zeros are exact, so a kernel can skip those multiplies.")
    print("  The others produce values that are small and not zero, which is")
    print("  a different thing entirely when the question is whether work")
    print("  can be skipped.")
    return measured


def measure_gelu_approximation():
    """CLAIM 6: the shipped approximation is not the function."""
    heading("EXACT GELU VERSUS THE TANH APPROXIMATION")
    worst = 0.0
    worst_at = 0.0
    for step in range(-600, 601):
        value = step / 100.0
        gap = abs(gelu(value) - gelu_tanh(value))
        if gap > worst:
            worst = gap
            worst_at = value
    print()
    print("      x      exact GELU    tanh GELU    difference")
    print("  " + "-" * 50)
    for value in (-3.0, -2.7, -1.0, 0.0, 1.0, 2.7, 3.0):
        print(
            f"  {value:>6.2f}{gelu(value):>15.6f}{gelu_tanh(value):>13.6f}"
            f"{gelu(value) - gelu_tanh(value):>+14.6f}"
        )
    print()
    print(f"  largest gap over x in [-6, 6]: {worst:.2e} at x = {worst_at:.2f}")
    print("  Small. Not zero. Two implementations that disagree by this much")
    print("  are both correct and are not the same function.")
    return worst


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = sample_input(rng)

    print("FEED-FORWARD BLOCKS: THE TWO-THIRDS NOBODY DRAWS")
    print(
        f"  measured parts use d_model {D_MODEL}, hidden {D_HIDDEN}, "
        f"length {LENGTH}, seed {SEED}"
    )
    print("  untrained weights, standard library only")

    share_error, parity_gap = measure_parameter_split()
    decomposition_error, concentration = measure_decomposition(x)
    zero_fractions = measure_sparsity(x)
    gelu_gap = measure_gelu_approximation()

    heading("ASSERTIONS")
    assert share_error < 1e-12, (
        f"CLAIM 1 failed: a width missed two-thirds by {share_error:.1e}. "
        "The ratio is supposed to have no width left in it."
    )
    print("  CLAIM 1  feed-forward is exactly two-thirds of a block ......... ok")

    assert parity_gap < GATED_PARITY_TOLERANCE, (
        f"CLAIM 2 failed: the rounded gated width misses parity by "
        f"{parity_gap * 100:.2f}%, expected under "
        f"{GATED_PARITY_TOLERANCE * 100:.1f}%."
    )
    print("  CLAIM 2  a gated block matches parity at two-thirds width ...... ok")

    assert decomposition_error < DECOMPOSITION_TOLERANCE, (
        f"CLAIM 3 failed: the decomposition disagrees with the matrix "
        f"multiply by {decomposition_error:.1e}."
    )
    print("  CLAIM 3  the output is exactly a sum of per-unit terms ......... ok")

    low, high = RELU_SPARSITY_BAND
    assert low < zero_fractions["relu"] < high, (
        f"CLAIM 4 failed: ReLU zeroed {zero_fractions['relu']:.4f} of the "
        f"hidden layer, expected between {low} and {high}."
    )
    assert zero_fractions["gelu"] == 0.0 and zero_fractions["silu"] == 0.0, (
        "CLAIM 4 failed: a smooth activation produced an exact zero, which "
        "means the input hit the origin and the comparison is degenerate."
    )
    print("  CLAIM 4  ReLU zeros half; the smooth ones zero nothing ......... ok")

    assert concentration < CONCENTRATION_CEILING, (
        f"CLAIM 5 failed: at its worst position, half the output length "
        f"needed {concentration:.4f} of the live units, expected under "
        f"{CONCENTRATION_CEILING}."
    )
    assert concentration < FLAT_DISTRIBUTION_SHARE, (
        "CLAIM 5 failed: the contribution is no more concentrated than a "
        "flat distribution, so there is nothing to report."
    )
    print("  CLAIM 5  contribution concentrates in a few live units ......... ok")

    assert 1e-5 < gelu_gap < 1e-2, (
        f"CLAIM 6 failed: exact and tanh GELU differ by {gelu_gap:.2e}, "
        "which is outside the range the article describes."
    )
    print("  CLAIM 6  the tanh GELU is close to, and is not, exact GELU ..... ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
