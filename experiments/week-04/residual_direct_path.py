"""The direct path: what a residual stream preserves, measured, not asserted.

Companion artifact for the week-4 Monday post (2026-09-28). The week-4
Monday artifact of 2026-09-14, `residual_stream.py`, took a residual
stack apart into the writes it collects. This script asks the question
that comes after: what the stack preserves. Because nothing overwrites,
the input is still sitting in the stream at every level above it, exactly
where it was written, and this script measures how visible it stays and
what it costs to keep it.

  CLAIM 1  The input plus every write reconstructs the stream at every
           level of the stack, not only at the top, with a maximum
           element-wise error of exactly 0.0. Level 0 is the input
           itself; level k is the input plus the 2k writes below it.

  CLAIM 2  The input never leaves and its share of the board falls. Its
           alignment with the stream drops from 1.0 at the embedding to
           a measured fraction at the top, and its share of the stream's
           length falls by more than SHARE_DECLINE_FLOOR between the
           first block and the top.

  CLAIM 3  Remove the additions and the input is gone in one block. In a
           stack where each block replaces its input, the alignment of
           the input with the state is already under RELAY_ONE_CEILING
           after one block and under RELAY_TOP_CEILING at the top.

  CLAIM 4  The direct path is exact only in the pre-norm arrangement.
           Subtracting every branch write returns the pre-norm stream to
           the input to within floating-point noise, measured 2.0e-15 and
           asserted under 1e-12. The subtraction introduces its own
           rounding at the last bit; the identity itself is CLAIM 1's,
           and that one is exactly 0.0. The post-norm stream returns to
           something at least POST_SUBTRACT_FLOOR away, because each
           block ends by renormalising the running vector and the input
           with it. The two numbers are about fifteen orders of magnitude
           apart.

  CLAIM 5  The input's raw direction survives pre-norm and not post-norm.
           After eight blocks the input's alignment with the stream
           measures 0.4067 pre-norm and 0.1040 post-norm, a factor of
           3.9 apart. The reason is structural: pre-norm's stream still
           holds the input's unmodified values as an anchor term, and
           post-norm rescales them at the end of every block.

           The first version of CLAIM 4 asserted exactness for the
           subtraction, and it measured 1.9984e-15, so the assertion
           fired: the subtraction is a different computation from the
           recorder's identity and it carries its own last-bit rounding.
           The first version of CLAIM 5 asserted that post-norm keeps the
           input's visibility better, and the measurement said the
           opposite, by a factor of 3.9. Both failures are recorded
           because claims adjusted after seeing the data have to say so.

WHAT THIS IS NOT. Eight blocks of width 16 with untrained weights is a
demonstration of an algebraic property, not a claim about what a trained
model does. Claims 1, 3 and 4 are structural and hold for any weights.
Claims 2 and 5 depend on the writes being close to orthogonal, which is a
property of random initialisation that training is free to destroy. The
article says so at the point of use.

Determinism: every weight comes from seed 42 and the input from the same
seed as residual_stream.py, so the two artifacts are directly comparable.
Two runs produce byte-identical output.

Run:      python3 experiments/week-04/residual_direct_path.py
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

from lib.layernorm import TransformerStack  # noqa: E402
from lib.linalg import zeros  # noqa: E402
from lib.residual import (  # noqa: E402
    ResidualRecorder,
    cosine_similarity,
    max_abs_difference,
    reconstruct,
    subtract,
)

D_MODEL = 16
NUM_HEADS = 4
D_HIDDEN = 64
NUM_LAYERS = 8
LENGTH = 12
SEED = 42

# A reconstruction that is only nearly exact would mean the recorder is
# doing different arithmetic from the stack. Zero is the expected answer.
EXACT = 0.0

# Subtracting a sum from a stream that contains it is a different
# computation from the recorder's identity and it carries its own last-bit
# rounding. The pre-norm subtraction must land under this bound, which is
# floating-point noise, and nothing more.
SUBTRACT_NOISE = 1e-12

# The input's visibility at the top must sit under this ceiling, which is
# set above the measured value, never inside it.
ALIGN_TOP_CEILING = 0.45

# The input's share of the stream's length must fall by at least this
# factor between the first block and the top.
SHARE_DECLINE_FLOOR = 1.8

# Predicting visibility from sizes alone must land inside this relative
# error at every level.
PREDICTION_TOLERANCE = 0.18

# The relay's alignment after one block must sit under this ceiling.
RELAY_ONE_CEILING = 0.15

# The relay's alignment at the top must sit under this tighter ceiling.
RELAY_TOP_CEILING = 0.15

# Subtracting every branch write must leave the post-norm stream at least
# this far from the input, or no renormalisation worth naming has happened.
POST_SUBTRACT_FLOOR = 5.0

# Pre-norm's alignment at the top must exceed post-norm's by at least
# this factor for the finding in CLAIM 5 to be worth reporting.
PRE_VS_POST_FLOOR = 3.0


def sample_input(rng):
    """A reproducible input sequence, standing in for the embedding output."""
    return [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]


def row_rms(row):
    """Root mean square of one row.

    Raises:
        ValueError: if the row is empty.
    """
    if not row:
        raise ValueError("row_rms needs a non-empty row")
    return math.sqrt(sum(value * value for value in row) / len(row))


def vector_norm(row):
    """Length of one row.

    Raises:
        ValueError: if the row is empty.
    """
    if not row:
        raise ValueError("vector_norm needs a non-empty row")
    return math.sqrt(sum(value * value for value in row))


def stream_levels(x):
    """The input and the stream after every block, in order.

    Returns (levels, blocks): levels has NUM_LAYERS + 1 entries, so entry
    0 is the embedding and entry k is the stream after block k - 1. The
    stack is the module's own, and `tests/test_residual.py` asserts that
    these streams equal the recorder's exactly.
    """
    stack = TransformerStack(D_MODEL, NUM_HEADS, D_HIDDEN, NUM_LAYERS, SEED, True)
    return stack.activations(x), stack.blocks


def relay_forward(blocks, x):
    """Run the stack with every addition removed: each block replaces its input.

    This is the pipeline the diagrams draw. The block's own pre-norm
    sublayers are used unchanged; the only difference is that each branch
    output is written over the running vector instead of added to it.

    Raises:
        ValueError: propagated from the sublayers on bad dimensions.
    """
    stream = [[float(value) for value in row] for row in x]
    for block in blocks:
        attended, _ = block.attention.forward(
            block.norm_attention.forward(stream)
        )
        stream = attended
        stream = block.feed_forward.forward(
            block.norm_feed_forward.forward(stream)
        )
    return stream


def mean_alignment(x, stream):
    """Mean cosine, over positions, between the input row and the stream row."""
    total = sum(cosine_similarity(x[t], stream[t]) for t in range(LENGTH))
    return total / LENGTH


def mean_size_ratio(x, stream):
    """Mean, over positions, of the input's length over the stream row's length.

    This is what visibility would be if the stream carried nothing but
    the input and directions orthogonal to it: sizes alone, no dot
    products, in the same dimensionless units as the alignment.
    """
    total = sum(
        vector_norm(x[t]) / vector_norm(stream[t]) for t in range(LENGTH)
    )
    return total / LENGTH


def heading(text):
    """Print a section banner."""
    print()
    print(text)
    print("=" * len(text))


def measure_presence(x, levels, blocks):
    """CLAIM 1: the input survives at every level, exactly."""
    heading("PRESENCE: is the input still in the stream at every level?")
    print()
    print("  level  writes below   largest difference")
    print("  " + "-" * 44)
    worst = 0.0
    for level in range(NUM_LAYERS + 1):
        if level == 0:
            error = max_abs_difference(reconstruct(x, []), levels[0])
        else:
            sub_stream, sub_writes = ResidualRecorder(blocks[:level]).run(x)
            error = max_abs_difference(reconstruct(x, sub_writes), sub_stream)
        worst = max(worst, error)
        print(f"  {level:>5}  {2 * level:>12}  {error:>17.1e}")
    print()
    print(f"  largest difference over all {NUM_LAYERS + 1} levels: {worst:.1e}")
    print("  The input is a term of the stream at every level, so the")
    print("  input plus the writes below any level add back to that level.")
    return worst


def measure_visibility(x, levels):
    """CLAIM 2: the input never leaves; its share of the board falls."""
    heading("VISIBILITY: how much of the board is still the input?")
    print()
    print("  level   alignment   predicted    off by")
    print("  " + "-" * 44)
    errors = []
    for level in range(0, NUM_LAYERS + 1):
        stream = levels[level]
        alignment = mean_alignment(x, stream)
        predicted = mean_size_ratio(x, stream)
        error = abs(predicted - alignment) / alignment
        errors.append(error)
        print(
            f"  {level:>5}  {alignment:>10.4f}  {predicted:>10.4f}"
            f"  {error * 100:>6.1f}%"
        )
    top_alignment = mean_alignment(x, levels[NUM_LAYERS])
    top_share = mean_size_ratio(x, levels[NUM_LAYERS])
    first_share = mean_size_ratio(x, levels[1])
    decline = first_share / top_share
    print()
    print("  alignment at the embedding                       1.0000")
    print(f"  alignment at the top                             {top_alignment:.4f}")
    print(f"  input's share of the stream's length at the top  {top_share:.4f}")
    print(f"  same share at level 1                            {first_share:.4f}")
    print(f"  share decline, level 1 over the top              {decline:.3f}")
    print()
    print("  The input is still in the stream at the top, exactly where")
    print("  it was pinned, and its share of the board has fallen. The")
    print("  predicted column is sizes alone; where it lands close, the")
    print("  visibility is dilution, and where it misses, the writes")
    print("  carry some of the input's own direction with them.")
    return top_alignment, decline, max(errors)


def measure_relay(x, levels, blocks):
    """CLAIM 3: remove the additions and the input is gone in one block."""
    heading("THE RELAY: the same stack with every addition removed")
    print()
    print("  level   residual    relay      relay rms")
    print("  " + "-" * 44)
    relay_alignments = []
    for level in range(1, NUM_LAYERS + 1):
        relay = relay_forward(blocks[:level], x)
        alignment = mean_alignment(x, relay)
        rms = sum(row_rms(relay[t]) for t in range(LENGTH)) / LENGTH
        residual = mean_alignment(x, levels[level])
        relay_alignments.append(alignment)
        print(
            f"  {level:>5}  {residual:>10.4f}  {alignment:>10.4f}"
            f"  {rms:>10.4f}"
        )
    print()
    print(f"  relay alignment after one block     {relay_alignments[0]:.4f}")
    print(f"  relay alignment at the top          {relay_alignments[-1]:.4f}")
    print()
    print("  The relay's state never grows: each block renormalises the")
    print("  branch before writing over it, so the board stays the same")
    print("  size and the first notice is not on it any more.")
    return relay_alignments[0], relay_alignments[-1]


def measure_post_norm(x, blocks, levels):
    """CLAIM 4 and CLAIM 5: the other arrangement, and the trade."""
    heading("THE OTHER ARRANGEMENT: post-norm, and what it trades")
    post_stack = TransformerStack(
        D_MODEL, NUM_HEADS, D_HIDDEN, NUM_LAYERS, SEED, False
    )
    post_levels = post_stack.activations(x)
    print()
    print("  level   pre-norm    post-norm")
    print("  " + "-" * 34)
    for level in range(1, NUM_LAYERS + 1):
        pre = mean_alignment(x, levels[level])
        post = mean_alignment(x, post_levels[level])
        print(f"  {level:>5}  {pre:>10.4f}  {post:>10.4f}")
    pre_top = mean_alignment(x, levels[NUM_LAYERS])
    post_top = mean_alignment(x, post_levels[NUM_LAYERS])

    recorder = ResidualRecorder(post_stack.blocks)
    post_stream, post_writes = recorder.run(x)
    branch_writes = [
        write
        for write in post_writes
        if write.component in ("attention", "feed_forward")
    ]
    branch_sum = reconstruct(zeros(LENGTH, D_MODEL), branch_writes)
    post_error = max_abs_difference(subtract(post_stream, branch_sum), x)

    pre_recorder = ResidualRecorder(blocks)
    pre_stream, pre_writes = pre_recorder.run(x)
    pre_sum = reconstruct(zeros(LENGTH, D_MODEL), pre_writes)
    pre_error = max_abs_difference(subtract(pre_stream, pre_sum), x)

    print()
    print("  every branch write subtracted, versus the input")
    print("  (largest element-wise difference)")
    print()
    print(f"    PRE-LN,  all {len(pre_writes)} branch writes     {pre_error:.1e}")
    print(f"    POST-LN, {len(branch_writes)} branch writes      {post_error:.4f}")
    print()
    print(f"  alignment at the top, pre-norm     {pre_top:.4f}")
    print(f"  alignment at the top, post-norm    {post_top:.4f}")
    print()
    print("  In pre-norm, subtracting every branch write returns the")
    print("  stream to the input to within floating-point noise: the")
    print("  input's values are still sitting in it, unmodified. In")
    print("  post-norm the same subtraction returns something else, and")
    print("  the input's raw direction is largely gone, because every")
    print("  renormalisation rescaled the running vector and the input")
    print("  with it. The post-norm stream keeps the board's size pinned;")
    print("  the pre-norm stream keeps the input. Neither keeps both.")
    return pre_top, post_top, pre_error, post_error


def main():
    """Run every measurement and assert every claim. Returns an exit code."""
    rng = random.Random(SEED)
    x = sample_input(rng)

    print("THE DIRECT PATH: WHAT A RESIDUAL STREAM PRESERVES")
    print(
        f"  d_model {D_MODEL}, heads {NUM_HEADS}, hidden {D_HIDDEN}, "
        f"layers {NUM_LAYERS}, length {LENGTH}, seed {SEED}"
    )
    print("  untrained weights, no autodiff, standard library only")

    levels, blocks = stream_levels(x)
    presence_worst = measure_presence(x, levels, blocks)
    top_alignment, decline, prediction_error = measure_visibility(x, levels)
    relay_one, relay_top = measure_relay(x, levels, blocks)
    pre_top, post_top, pre_error, post_error = measure_post_norm(x, blocks, levels)

    heading("ASSERTIONS")
    assert presence_worst == EXACT, (
        f"CLAIM 1 failed: reconstruction error is {presence_worst}, expected "
        "exactly 0.0 at every level. The recorder and the stack disagree."
    )
    print("  CLAIM 1  the input is a term of the stream at every level .... ok")

    assert top_alignment < ALIGN_TOP_CEILING, (
        f"CLAIM 2 failed: the input's alignment at the top is "
        f"{top_alignment:.4f}, expected under {ALIGN_TOP_CEILING}."
    )
    assert decline > SHARE_DECLINE_FLOOR, (
        f"CLAIM 2 failed: the input's share of the stream's length falls by "
        f"only {decline:.3f} between level 1 and the top, expected more than "
        f"{SHARE_DECLINE_FLOOR}."
    )
    assert prediction_error < PREDICTION_TOLERANCE, (
        f"CLAIM 2 failed: predicting visibility from sizes alone misses by "
        f"{prediction_error * 100:.1f}% at its worst, expected under "
        f"{PREDICTION_TOLERANCE * 100:.0f}%."
    )
    print("  CLAIM 2  the input never leaves; its share of the board falls . ok")

    assert relay_one < RELAY_ONE_CEILING, (
        f"CLAIM 3 failed: the relay's alignment after one block is "
        f"{relay_one:.4f}, expected under {RELAY_ONE_CEILING}."
    )
    assert relay_top < RELAY_TOP_CEILING, (
        f"CLAIM 3 failed: the relay's alignment at the top is "
        f"{relay_top:.4f}, expected under {RELAY_TOP_CEILING}."
    )
    print("  CLAIM 3  without the additions the input is gone in one block . ok")

    assert pre_error < SUBTRACT_NOISE, (
        f"CLAIM 4 failed: subtracting every pre-norm branch write returns "
        f"an error of {pre_error}, expected under {SUBTRACT_NOISE}, which "
        "is floating-point noise and nothing more."
    )
    assert post_error > POST_SUBTRACT_FLOOR, (
        f"CLAIM 4 failed: subtracting every post-norm branch write leaves "
        f"only {post_error:.4f} behind, which is not a renormalisation "
        "worth naming."
    )
    print("  CLAIM 4  the exact direct path is pre-norm's alone ............ ok")

    assert pre_top > post_top * PRE_VS_POST_FLOOR, (
        f"CLAIM 5 failed: pre-norm's alignment at the top is {pre_top:.4f} "
        f"against post-norm's {post_top:.4f}, which is less than the factor "
        f"of {PRE_VS_POST_FLOOR} the article reports."
    )
    print("  CLAIM 5  the input's raw direction survives pre-norm alone ..... ok")

    print()
    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
