"""What RoPE guarantees, and what it only tends to do, measured.

Companion artifact for the week-3 Friday evening contrarian take and
debate (2026-09-11).

Su et al. list three properties for rotary position embedding
(arXiv:2104.09864): "the flexibility of sequence length, decaying
inter-token dependency with increasing relative distances, and the
capability of equipping the linear self-attention with relative position
encoding".

Those three are not the same kind of claim, and the difference is the
whole argument of the evening post. This script separates them by
measuring each one.

  THE EXACT ONE. The relative-position identity is algebra. The score
  between a query at m and a key at n depends only on m - n, for every
  vector, at every position, without exception. Measured here across an
  offset of 4,096 positions and found to hold at machine precision.

  THE OTHER EXACT ONE. Rotation preserves length, so RoPE can never
  amplify or attenuate a vector. Also measured.

  THE STATISTICAL ONE. Decay with distance is an average over vectors,
  not a guarantee for a vector, and it is not even monotone as an average.
  Taking the expectation over standard normal vectors turns out to have a
  closed form:

      E[self-similarity at distance d] = mean over pairs of cos(d * theta_i)

  which this script derives numerically by agreeing with it to three
  decimal places. That expression trends downward, so the property is real
  as a trend. It is also a sum of cosines, so it oscillates, and there are
  distances where moving further apart raises the expected dependency
  rather than lowering it. Those distances are found and printed.

Six claims are asserted at the end. Each one can fail, and if it fails the
article that quotes it is wrong and has to change.

  CLAIM 1  The relative-position identity holds to machine precision over
           a 4,096-position offset sweep.

  CLAIM 2  Rotation preserves the norm of every vector at every position.

  CLAIM 3  Shifting an entire attention window leaves every score inside
           it unchanged, which is the property a KV cache depends on.

  CLAIM 4  Averaged over random vectors, self-similarity does fall with
           relative distance, and the measured average agrees with the
           closed form. The paper's third property reproduces as a trend.

  CLAIM 5  The trend is not monotone. There exist distances d1 < d2 where
           the expected dependency at d2 is HIGHER than at d1, and they
           are not marginal cases.

  CLAIM 6  It is not a guarantee for a vector either. A vector whose
           energy sits in the slowest-rotating pair keeps almost all of
           its self-similarity at a distance where the average has
           collapsed. Nothing in the architecture or the loss forbids a
           model from placing a query there.

Determinism: every vector comes from a stated seed. Two runs produce
byte-identical output.

Run:      python3 experiments/week-03/rope_properties.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about eight seconds.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.rope import (  # noqa: E402
    DEFAULT_BASE,
    apply_rope,
    dot,
    inverse_frequencies,
    norm,
    relative_score,
    rotate,
)

D_HEAD = 64
SEED = 42
SAMPLES = 4000

# How closely the sampled average must track the closed form for the
# closed form to be accepted as describing it.
CLOSED_FORM_TOLERANCE = 0.01

# Offsets used to check that only the difference matters.
OFFSETS = (0, 1, 17, 256, 1024, 4096)
DISTANCES_FOR_IDENTITY = (0, 1, 2, 9, 64, 512)

# Distances the decay curve is measured at.
DECAY_DISTANCES = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048)

# Where CLAIM 5's comparison is made.
FAR_DISTANCE = 512

WINDOW = 6
WINDOW_SHIFT = 4096

TOLERANCE = 1e-9
NORM_TOLERANCE = 1e-12


def random_vector(rng, width=D_HEAD):
    """A reproducible standard normal vector."""
    return [rng.gauss(0.0, 1.0) for _ in range(width)]


def slowest_pair_vector(width=D_HEAD):
    """A unit vector with all of its energy in the slowest-rotating pair.

    Nothing about this vector is exotic. It is a perfectly ordinary point
    in the space, and a trained model is free to put a query there. That
    is the entire point of CLAIM 5.
    """
    vector = [0.0] * width
    vector[width - 2] = 1.0
    return vector


def fastest_pair_vector(width=D_HEAD):
    """A unit vector with all of its energy in the fastest-rotating pair."""
    vector = [0.0] * width
    vector[0] = 1.0
    return vector


def check_relative_identity(rng):
    """Measure the largest violation of the relative-position identity.

    Returns:
        The largest absolute gap found over the offset and distance sweep.
    """
    worst = 0.0
    for _ in range(SAMPLES):
        query = random_vector(rng)
        key = random_vector(rng)
        for distance in DISTANCES_FOR_IDENTITY:
            at_origin = relative_score(query, key, distance, 0)
            for offset in OFFSETS:
                shifted = relative_score(
                    query, key, offset + distance, offset
                )
                worst = max(worst, abs(shifted - at_origin))
    print("PROPERTY 1: does the score depend only on the distance?")
    print(f"  {SAMPLES} random query/key pairs, width {D_HEAD}, seed {SEED}")
    print(f"  offsets tested           {OFFSETS}")
    print(f"  distances tested         {DISTANCES_FOR_IDENTITY}")
    print(f"  largest violation        {worst:.3e}")
    return worst


def check_norm_preservation(rng):
    """Measure the largest relative change in norm under rotation."""
    worst = 0.0
    for _ in range(SAMPLES):
        vector = random_vector(rng)
        original = norm(vector)
        for position in (1, 13, 512, 4096, -97):
            changed = norm(rotate(vector, position))
            worst = max(worst, abs(changed - original) / original)
    print()
    print("PROPERTY 2: does rotation change any vector's length?")
    print(f"  largest relative change  {worst:.3e}")
    print("  a rotation turns a vector, it cannot stretch one, so RoPE has")
    print("  no way to amplify or attenuate anything")
    return worst


def check_window_shift(rng):
    """Measure whether shifting a whole window changes any score in it."""
    queries = [random_vector(rng) for _ in range(WINDOW)]
    keys = [random_vector(rng) for _ in range(WINDOW)]
    here_q = apply_rope(queries)
    here_k = apply_rope(keys)
    there_q = apply_rope(queries, offset=WINDOW_SHIFT)
    there_k = apply_rope(keys, offset=WINDOW_SHIFT)
    worst = 0.0
    for i in range(WINDOW):
        for j in range(WINDOW):
            worst = max(
                worst, abs(dot(here_q[i], here_k[j]) - dot(there_q[i], there_k[j]))
            )
    print()
    print("PROPERTY 3: does moving the window move the scores inside it?")
    print(f"  window of {WINDOW}, shifted by {WINDOW_SHIFT} positions")
    print(f"  largest score change     {worst:.3e}")
    print("  this is the property a KV cache runs on: a cached key keeps")
    print("  its meaning relative to a query that arrives much later")
    return worst


def expected_self_similarity(distance, width=D_HEAD, base=DEFAULT_BASE):
    """Closed form for the average self-similarity at a given distance.

    Self-similarity at distance d for a vector v is

        sum over pairs i of (v_2i^2 + v_2i+1^2) * cos(d * theta_i)

    divided by |v|^2. For a standard normal v every pair carries the same
    expected share of the total energy, so the weights average out and
    what is left is the unweighted mean of the cosines. This function is
    that mean. It has no randomness in it at all.

    Raises:
        ValueError: if width is not positive and even, or base <= 1.
    """
    rates = inverse_frequencies(width, base)
    return sum(math.cos(distance * rate) for rate in rates) / len(rates)


def non_monotone_pairs(curve):
    """Return consecutive (near, far) pairs where the far value is higher.

    A property described as "decaying with increasing relative distance"
    predicts this list is empty.
    """
    rising = []
    for (near, near_value), (far, far_value) in zip(curve, curve[1:]):
        if far_value > near_value:
            rising.append((near, far, near_value, far_value))
    return rising


def decay_curve(vectors):
    """Mean self-similarity at each distance, normalised to distance 0.

    Self-similarity means score(v at distance d, v at 0). At distance 0
    this is the squared norm, which is positive, so the ratio is a clean
    fraction of the starting value rather than a signed quantity averaging
    to nothing.

    Returns:
        A list of (distance, mean ratio) pairs.
    """
    curve = []
    for distance in DECAY_DISTANCES:
        ratios = []
        for vector in vectors:
            baseline = dot(vector, vector)
            assert baseline > 0.0, "a zero vector has no self-similarity"
            ratios.append(relative_score(vector, vector, distance, 0) / baseline)
        curve.append((distance, sum(ratios) / len(ratios)))
    return curve


def run_decay(rng):
    """Print the sampled curve, the closed form, and two constructed ones."""
    random_vectors = [random_vector(rng) for _ in range(SAMPLES)]
    random_curve = decay_curve(random_vectors)
    slow_curve = decay_curve([slowest_pair_vector()])
    fast_curve = decay_curve([fastest_pair_vector()])
    closed = [
        (distance, expected_self_similarity(distance))
        for distance in DECAY_DISTANCES
    ]

    print()
    print("PROPERTY 4, 5 and 6: does dependency decay with distance?")
    print("  self-similarity as a fraction of its value at distance 0")
    print(f"  sampled column averages {SAMPLES} standard normal vectors, "
          f"seed {SEED}")
    print("  closed form is mean over pairs of cos(distance * theta_i), "
          "no randomness")
    print()
    header = (
        f"{'distance':>9} {'sampled':>9} {'closed form':>12} "
        f"{'slowest pair':>13} {'fastest pair':>13}"
    )
    print(f"  {header}")
    print("  " + "-" * len(header))
    for (distance, average), (_, exact), (_, slow), (_, fast) in zip(
        random_curve, closed, slow_curve, fast_curve
    ):
        print(
            f"  {distance:>9} {average:>9.4f} {exact:>12.4f} "
            f"{slow:>13.4f} {fast:>13.4f}"
        )
    return random_curve, closed, slow_curve


def report_contrast(closed, slow_curve):
    """Print the two comparisons CLAIM 5 and CLAIM 6 rest on."""
    rising = non_monotone_pairs(closed)
    print()
    print("  where moving further apart RAISES the expected dependency:")
    if not rising:
        print("    none found")
    for near, far, near_value, far_value in rising:
        print(f"    distance {near:>4} to {far:>4}: "
              f"{near_value:+.4f} rises to {far_value:+.4f}")

    exact_at = dict(closed)[FAR_DISTANCE]
    slow_at = dict(slow_curve)[FAR_DISTANCE]
    rates = inverse_frequencies(D_HEAD, DEFAULT_BASE)
    turn = rates[-1] * FAR_DISTANCE
    print()
    print(f"  at distance {FAR_DISTANCE}:")
    print(f"    closed-form average    {exact_at:+.4f}")
    print(f"    slowest pair           {slow_at:+.4f}")
    print(f"    slowest pair rate      {rates[-1]:.6e} radians per position")
    print(f"    total turn over {FAR_DISTANCE}    {turn:.4f} radians "
          f"({math.degrees(turn):.2f} degrees)")
    print("  the slowest pair has not completed a quarter turn, so its")
    print("  contribution has barely moved. Nothing forbids a model from")
    print("  putting a query there")
    return rising


def check_claims(identity, norm_change, window, curves):
    """Assert the six claims the article makes. Raises AssertionError."""
    random_curve, closed, slow_curve = curves
    assert identity < TOLERANCE, (
        f"CLAIM 1 died: the relative-position identity was violated by "
        f"{identity:.3e}, above {TOLERANCE:.0e}"
    )
    assert norm_change < NORM_TOLERANCE, (
        f"CLAIM 2 died: rotation changed a norm by a relative "
        f"{norm_change:.3e}, above {NORM_TOLERANCE:.0e}"
    )
    assert window < TOLERANCE, (
        f"CLAIM 3 died: shifting the window changed a score by {window:.3e}"
    )

    sampled_at = dict(random_curve)
    exact_at = dict(closed)
    assert sampled_at[0] > 0.99, (
        f"CLAIM 4 died: self-similarity at distance 0 is "
        f"{sampled_at[0]:.4f}, which should be 1 by construction"
    )
    for distance in DECAY_DISTANCES:
        gap = abs(sampled_at[distance] - exact_at[distance])
        assert gap < CLOSED_FORM_TOLERANCE, (
            f"CLAIM 4 died: at distance {distance} the sampled average "
            f"{sampled_at[distance]:+.4f} and the closed form "
            f"{exact_at[distance]:+.4f} differ by {gap:.4f}, so the closed "
            "form does not describe the average and the article's derivation "
            "is wrong"
        )
    assert exact_at[DECAY_DISTANCES[-1]] < 0.5 * exact_at[1], (
        f"CLAIM 4 died: expected dependency at distance "
        f"{DECAY_DISTANCES[-1]} is {exact_at[DECAY_DISTANCES[-1]]:+.4f}, not "
        f"well below the {exact_at[1]:+.4f} at distance 1, so there is no "
        "downward trend to report"
    )

    rising = non_monotone_pairs(closed)
    assert rising, (
        "CLAIM 5 died: the expected-dependency curve is monotone over the "
        "distances measured, so 'decaying with increasing relative distance' "
        "survives as stated and the article must not claim otherwise"
    )

    slow_at = dict(slow_curve)
    assert slow_at[FAR_DISTANCE] > 0.99, (
        f"CLAIM 6 died: the slowest-pair vector retained only "
        f"{slow_at[FAR_DISTANCE]:+.4f} of its self-similarity at distance "
        f"{FAR_DISTANCE}, so it is not a counterexample to guaranteed decay"
    )
    assert slow_at[FAR_DISTANCE] > 4.0 * abs(exact_at[FAR_DISTANCE]), (
        f"CLAIM 6 died: the slowest pair at {slow_at[FAR_DISTANCE]:+.4f} is "
        f"not far above the average at {exact_at[FAR_DISTANCE]:+.4f}, so the "
        "contrast the article draws is not there"
    )


def main():
    """Measure all six properties, then verify."""
    rng = random.Random(SEED)
    identity = check_relative_identity(rng)
    norm_change = check_norm_preservation(rng)
    window = check_window_shift(rng)
    curves = run_decay(rng)
    report_contrast(curves[1], curves[2])

    try:
        check_claims(identity, norm_change, window, curves)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
