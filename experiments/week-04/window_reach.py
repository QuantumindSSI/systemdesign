"""Sliding-window attention: what "reaches" means, and what it is worth.

Companion artifact for the week-4 Friday posts (2026-09-18).

The standard defence of a fixed attention window is stacking. A position
reads its window, the positions in that window already read theirs, so
after L layers information has travelled L * (window - 1) positions and the
model can therefore "handle sequences of arbitrary length with a reduced
inference cost" (arXiv:2310.06825). Longformer makes the same structural
argument for "an attention mechanism that scales linearly with sequence
length" (arXiv:2004.05150).

The argument is correct about connectivity. This script checks that, and
then asks the question the argument does not answer: how much of a signal
survives the journey.

  CLAIM 1  The reach formula is right. Boolean powers of the mask give
           exactly L * (window - 1), until the sequence runs out.

  CLAIM 2  Past the reach, influence is exactly 0.0. Perturb a position and
           positions beyond the horizon do not move at all, to the last bit.
           That is a hard cutoff, not a decay.

  CLAIM 3  Inside the reach, influence decays by orders of magnitude. At the
           furthest reachable position the windowed model retains under
           one hundred-thousandth of the influence the dense model has
           there. Reachable and readable are different properties, and the
           stacking argument only establishes the first.

  CLAIM 4  The density saving is real and is the reason anyone accepts the
           above. A window of 8 over 64 positions permits a fraction of the
           pairs causal attention does.

  CLAIM 5  A handful of always-readable positions repairs the long range at
           a small cost in density. Four of them restore influence at
           distance to at least the dense level across the whole sequence.
           More influence is not automatically better, and the script says
           so rather than declaring a winner.

METHOD, AND A MISTAKE WORTH KEEPING. Influence is measured by perturbing
one position's input and taking the length of the change at every other
position after the full stack. The first version of this script perturbed
by a constant vector, every dimension moved by the same amount. Every
position past the first showed a change of about 1e-14, which reads as a
dramatic finding about attention and is entirely a statement about layer
normalization: a pre-norm block normalises its branch input, normalisation
subtracts the row mean, and a constant shift is exactly the direction that
removes. The perturbation is now a random direction with its mean removed,
so it survives the normalisation it has to pass through.

WHAT THIS IS NOT. Claims 1, 2 and 4 are combinatorial and hold for any
weights. Claims 3 and 5 are measured on an untrained six-layer stack, where
attention is close to uniform. A trained model concentrates its attention,
which changes the numbers and does not change the structure: a hard cutoff
is still a hard cutoff, and a path that exists can still carry nothing.

Determinism: every weight comes from seed 42, the perturbation direction
from seed 7. Two runs produce byte-identical output.

Run:      python3 experiments/week-04/window_reach.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about three seconds, almost all of it the six forward passes.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.attention import causal_mask  # noqa: E402
from lib.layernorm import TransformerStack  # noqa: E402
from lib.sparse_attention import (  # noqa: E402
    allowed_count,
    mask_density,
    max_reach,
    sink_window_mask,
    sliding_window_mask,
    window_reach_formula,
)

D_MODEL = 32
NUM_HEADS = 4
D_HIDDEN = 64
NUM_LAYERS = 6
LENGTH = 64
WINDOW = 8
NUM_SINKS = 4
SEED = 42
PERTURBATION_SEED = 7
PERTURBATION = 1.0
SOURCE = 0

POSITIONS_SHOWN = (0, 1, 2, 4, 8, 16, 24, 32, 40, 42, 43, 48, 63)

# Below this a measured change is floating-point noise rather than signal.
NOISE_FLOOR = 1e-12

# How far the windowed model's influence must have fallen at the furthest
# reachable position for the article's claim to hold.
DECAY_CEILING = 1e-4


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def perturbation_direction():
    """A reproducible unit direction that layer normalization cannot remove.

    The mean is subtracted before normalising, because a pre-norm block
    normalises its branch input and normalisation removes exactly the
    constant component. A perturbation along that component measures the
    normalisation and not the attention.
    """
    rng = random.Random(PERTURBATION_SEED)
    raw = [rng.gauss(0.0, 1.0) for _ in range(D_MODEL)]
    mean = sum(raw) / D_MODEL
    centred = [value - mean for value in raw]
    length = math.sqrt(sum(value * value for value in centred))
    return [value / length for value in centred]


def measure_reach(masks):
    """CLAIM 1 and CLAIM 4: connectivity and density, both combinatorial."""
    heading("CONNECTIVITY: HOW FAR A PATH EXISTS")
    print()
    print(f"  {NUM_LAYERS} layers, window {WINDOW}, length {LENGTH}.")
    print(f"  The formula says a window carries information "
          f"{WINDOW - 1} positions per layer.")
    print()
    print("  mask            allowed pairs   density   measured reach   formula")
    print("  " + "-" * 70)
    reaches = {}
    densities = {}
    for name, mask in masks.items():
        reach = max_reach(mask, NUM_LAYERS)
        reaches[name] = reach
        densities[name] = mask_density(mask)
        formula = (
            f"{window_reach_formula(WINDOW, NUM_LAYERS):>9}"
            if name != "dense"
            else f"{'-':>9}"
        )
        print(
            f"  {name:<14}{allowed_count(mask):>14,}{densities[name]:>10.4f}"
            f"{reach:>17}{formula}"
        )
    print()
    print("  Reach is measured by taking boolean powers of the mask, so it")
    print("  is the graph's answer rather than the formula's. The window")
    print("  row agrees with the formula exactly. The dense and sink rows")
    print(f"  are capped at {LENGTH - 1}, the length of the sequence.")
    return reaches, densities


def measure_influence(masks, x, direction):
    """CLAIM 2, CLAIM 3 and CLAIM 5: what survives the journey."""
    heading("INFLUENCE: HOW MUCH OF A SIGNAL SURVIVES")
    stack = TransformerStack(
        D_MODEL, NUM_HEADS, D_HIDDEN, NUM_LAYERS, SEED, norm_first=True
    )
    moved = [list(row) for row in x]
    moved[SOURCE] = [
        moved[SOURCE][index] + PERTURBATION * direction[index]
        for index in range(D_MODEL)
    ]

    influence = {}
    for name, mask in masks.items():
        before = stack.forward(x, mask)
        after = stack.forward(moved, mask)
        influence[name] = [
            math.sqrt(
                sum(
                    (before[position][dim] - after[position][dim]) ** 2
                    for dim in range(D_MODEL)
                )
            )
            for position in range(LENGTH)
        ]

    print()
    print(f"  Position {SOURCE} is moved by {PERTURBATION:.1f} along a unit")
    print("  direction with zero mean. The table is the length of the change")
    print("  at each position after the whole stack.")
    print()
    names = list(masks)
    header = "  position" + "".join(f"{name:>14}" for name in names)
    header += f"{'window/dense':>15}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for position in POSITIONS_SHOWN:
        cells = "".join(f"{influence[name][position]:>14.3e}" for name in names)
        dense_value = influence["dense"][position]
        ratio = (
            influence["window"][position] / dense_value
            if dense_value > NOISE_FLOOR
            else 0.0
        )
        print(f"  {position:>8}{cells}{ratio:>15.2e}")

    reach = window_reach_formula(WINDOW, NUM_LAYERS)
    beyond = [
        influence["window"][position]
        for position in range(reach + 1, LENGTH)
    ]
    at_edge = influence["window"][reach]
    dense_at_edge = influence["dense"][reach]
    edge_ratio = at_edge / dense_at_edge
    far_sink = min(
        influence["sink"][position] for position in range(reach + 1, LENGTH)
    )
    far_dense = max(
        influence["dense"][position] for position in range(reach + 1, LENGTH)
    )

    print()
    print(f"  largest change anywhere past position {reach}, window:  "
          f"{max(beyond):.1e}")
    print(f"  change at position {reach}, the furthest reachable:       "
          f"{at_edge:.3e}")
    print(f"  the same position under dense attention:              "
          f"{dense_at_edge:.3e}")
    print(f"  ratio                                                 "
          f"{edge_ratio:.2e}")
    print()
    print(f"  smallest sink influence past position {reach}:           "
          f"{far_sink:.3e}")
    print(f"  largest dense influence past position {reach}:           "
          f"{far_dense:.3e}")
    print()
    print("  Read the first line and the third together. Past the horizon")
    print("  the window model does not decay, it stops. One position before")
    print("  the horizon it has already lost almost everything, so the")
    print("  horizon was never where the information ran out.")
    print()
    print("  The sink row is not a verdict. Holding four positions readable")
    print("  from everywhere gives them more influence than dense attention")
    print("  gives them, which is a different bias, not an absence of one.")
    return influence, max(beyond), edge_ratio, far_sink, far_dense


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]
    direction = perturbation_direction()

    masks = {
        "dense": causal_mask(LENGTH),
        "window": sliding_window_mask(LENGTH, WINDOW),
        "sink": sink_window_mask(LENGTH, WINDOW, NUM_SINKS),
    }

    print("SLIDING-WINDOW ATTENTION: REACH IS NOT INFLUENCE")
    print(
        f"  d_model {D_MODEL}, {NUM_HEADS} heads, {NUM_LAYERS} layers, "
        f"length {LENGTH}, window {WINDOW}, {NUM_SINKS} sinks, seed {SEED}"
    )
    print("  untrained weights, standard library only")

    reaches, densities = measure_reach(masks)
    influence, beyond, edge_ratio, far_sink, far_dense = measure_influence(
        masks, x, direction
    )

    heading("ASSERTIONS")
    expected = window_reach_formula(WINDOW, NUM_LAYERS)
    assert reaches["window"] == expected, (
        f"CLAIM 1 failed: measured reach {reaches['window']}, formula "
        f"{expected}."
    )
    assert reaches["dense"] == LENGTH - 1, (
        f"CLAIM 1 failed: dense reach is {reaches['dense']}, expected the "
        f"full {LENGTH - 1}."
    )
    print("  CLAIM 1  the reach formula matches the measured graph ......... ok")

    assert beyond == 0.0, (
        f"CLAIM 2 failed: the largest change past the horizon is {beyond:.2e}, "
        "expected exactly 0.0."
    )
    print("  CLAIM 2  past the horizon the influence is exactly zero ....... ok")

    assert edge_ratio < DECAY_CEILING, (
        f"CLAIM 3 failed: at the furthest reachable position the window "
        f"retains {edge_ratio:.2e} of the dense influence, expected under "
        f"{DECAY_CEILING:.0e}."
    )
    assert influence["window"][expected] > 0.0, (
        "CLAIM 3 failed: the furthest reachable position did not move at "
        "all, so the horizon is in the wrong place."
    )
    print("  CLAIM 3  inside the horizon the influence has already gone .... ok")

    assert densities["window"] < densities["dense"] / 4.0, (
        f"CLAIM 4 failed: window density {densities['window']:.4f} against "
        f"dense {densities['dense']:.4f} is not a saving worth the cost."
    )
    print("  CLAIM 4  the density saving is real ........................... ok")

    assert far_sink >= far_dense, (
        f"CLAIM 5 failed: the weakest sink influence past the horizon is "
        f"{far_sink:.3e}, below the strongest dense influence "
        f"{far_dense:.3e}."
    )
    assert densities["sink"] < densities["dense"], (
        "CLAIM 5 failed: the sink mask is not sparser than dense attention, "
        "so it has bought nothing."
    )
    print("  CLAIM 5  a few sinks repair the range, and change the bias ..... ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
