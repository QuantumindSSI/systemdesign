"""Where the layer norm goes, and what it does to the gradients.

Companion artifact for the week-3 Saturday weekend challenge (2026-09-12).

Two arrangements of the same block, differing by the position of one
function call:

    POST-LN, the original    x -> LayerNorm(x + Sublayer(x))
    PRE-LN                   x -> x + Sublayer(LayerNorm(x))

Xiong et al. (arXiv:2002.04745) analyse both with mean field theory and
report that at initialization, with Post-LN, "the expected gradients of
the parameters near the output layer are large", which makes a large
learning rate unstable and is the reason the original recipe needs a
warm-up stage. With Pre-LN, they report, "the gradients are well-behaved
at initialization", which motivated removing warm-up.

This script measures two consequences on a model small enough to
differentiate by hand.

  FORWARD: how big the residual stream gets with depth. Post-LN
  renormalises the stream at every block, so it cannot grow. Pre-LN
  leaves the residual path untouched and every block adds to it, so it
  does grow, and the growth is measured rather than argued.

  BACKWARD: the gradient magnitude of each block's attention output
  projection, by central finite differences on the forward pass, because
  there is no autodiff in this repository. Central differences are exact
  to O(h^2), and the step is chosen and then verified by halving it and
  confirming the answer barely moves.

WHAT THIS IS NOT. Six layers at width 16 is not the regime the paper's
proof concerns, and a finite-difference gradient on an untrained toy is
not a training run. The honest question this answers is narrow: on a toy,
in the direction the theory predicts, does anything move at all? The
article says so at the point of use, and a reader who wants the real
claim is pointed at the paper.

RAW GRADIENT MAGNITUDES ARE NOT COMPARABLE ACROSS THE TWO, and getting
that wrong is the easiest mistake available here. Pre-LN's residual stream
is several times larger by the top of the stack, so its outputs sit
further from the target and every gradient in it is larger for a reason
that has nothing to do with the pathology under discussion. The comparable
quantity is the SHAPE of the gradient profile with depth, measured within
each arrangement against its own average. That is what the tilt below is.

Five claims are asserted at the end. Each one can fail, and if it fails
the article that quotes it is wrong and has to change.

  CLAIM 1  Both arrangements hold numerically identical weights, so every
           difference measured is the arrangement and nothing else.

  CLAIM 2  Post-LN holds the residual stream flat with depth. Pre-LN lets
           it grow, and the growth is monotone across the stack.

  CLAIM 3  The finite-difference step is small enough to be trustworthy:
           halving it changes the measured gradient norm by under 1%.

  CLAIM 4  The forward scales differ enough that raw gradient magnitudes
           must not be compared between arrangements. Asserted, rather
           than assumed, so that a future run where the scales happen to
           match cannot quietly leave the caveat in the article.

  CLAIM 5  Scale-free, the two tilt in opposite directions. Post-LN puts
           more gradient in the half of the stack nearest the output than
           in the half nearest the input. Pre-LN does the reverse. That is
           the direction Xiong et al.'s analysis predicts, reproduced on a
           toy far outside the regime their proof concerns.

Determinism: every weight comes from seed 42. Two runs produce
byte-identical output.

Run:      python3 experiments/week-03/norm_placement.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about six seconds, almost all of it finite differences.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.layernorm import TransformerStack, root_mean_square  # noqa: E402

D_MODEL = 8
NUM_HEADS = 2
D_HIDDEN = 16
NUM_LAYERS = 6
LENGTH = 6
SEED = 42
TARGET_SEED = 7

# Central difference step, and the halved step used to check it.
STEP = 1e-4
CHECK_STEP = 5e-5
STEP_AGREEMENT = 0.01

# Below this the residual stream counts as flat across the stack.
FLAT_RATIO = 2.0


def sample_input(rng):
    """A reproducible input sequence."""
    return [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]


def build(norm_first):
    """Build a stack. Both arrangements share the seed, so also the weights."""
    return TransformerStack(
        D_MODEL, NUM_HEADS, D_HIDDEN, NUM_LAYERS, SEED, norm_first
    )


def fixed_target(rng):
    """A frozen target the loss is measured against."""
    return [[rng.gauss(0.0, 1.0) for _ in range(D_MODEL)] for _ in range(LENGTH)]


def loss(stack, x, target):
    """Mean squared error between the stack's output and a fixed target.

    THE OBVIOUS LOSS DOES NOT WORK HERE, and the reason is worth stating
    because it is a trap anyone repeating this will fall into. The first
    version of this script used the mean squared VALUE of the output, with
    no target. Under Post-LN the last operation in the stack is a
    LayerNorm, so every output row has mean 0 and variance 1 by
    construction, so that loss is pinned at 1.0 no matter what any weight
    does. Its gradient measured as 1e-5, which looks like a dramatic
    finding about Post-LN and is actually a statement about the loss.

    Measuring against a fixed target removes the degeneracy: normalisation
    fixes each row's length but not its direction, and the direction is
    what the target term sees.
    """
    output = stack.forward(x)
    total = 0.0
    count = 0
    for row, target_row in zip(output, target):
        for value, wanted in zip(row, target_row):
            total += (value - wanted) ** 2
            count += 1
    return total / count


def weights_are_identical(pre, post):
    """True if two stacks hold the same numbers in every measured matrix."""
    for pre_block, post_block in zip(pre.blocks, post.blocks):
        if pre_block.attention.w_output != post_block.attention.w_output:
            return False
        if pre_block.feed_forward.w_in != post_block.feed_forward.w_in:
            return False
        if pre_block.feed_forward.w_out != post_block.feed_forward.w_out:
            return False
        for pre_head, post_head in zip(
            pre_block.attention.heads, post_block.attention.heads
        ):
            if pre_head.w_query != post_head.w_query:
                return False
    return True


def gradient_norm(stack, x, target, matrix, step):
    """L2 norm of the gradient of `loss` with respect to `matrix`.

    Central differences: for each entry w, perturb by plus and minus
    `step`, and take (f(w + h) - f(w - h)) / (2h). The entry is restored
    before moving on, so the stack is left exactly as it was found.

    Complexity: two forward passes per entry, so 2 * rows * cols passes.

    Raises:
        ValueError: if step is not positive.
    """
    if step <= 0.0:
        raise ValueError(f"step must be positive, got {step}")
    total = 0.0
    for row in range(len(matrix)):
        for column in range(len(matrix[row])):
            original = matrix[row][column]
            matrix[row][column] = original + step
            up = loss(stack, x, target)
            matrix[row][column] = original - step
            down = loss(stack, x, target)
            matrix[row][column] = original
            derivative = (up - down) / (2.0 * step)
            total += derivative * derivative
    return math.sqrt(total)


def residual_profile(stack, x):
    """Root mean square of the stream entering and leaving every block."""
    return [root_mean_square(step) for step in stack.activations(x)]


def print_residual(pre_profile, post_profile):
    """Print the forward residual-stream table."""
    print("FORWARD: how large is the residual stream at each depth?")
    print(f"  root mean square over all values, {NUM_LAYERS} layers, "
          f"d_model {D_MODEL}, seed {SEED}")
    print()
    header = f"{'depth':>7} {'Post-LN':>10} {'Pre-LN':>10}"
    print(f"  {header}")
    print("  " + "-" * len(header))
    for depth, (post, pre) in enumerate(zip(post_profile, pre_profile)):
        label = "input" if depth == 0 else str(depth)
        print(f"  {label:>7} {post:>10.4f} {pre:>10.4f}")
    post_ratio = max(post_profile[1:]) / min(post_profile[1:])
    pre_ratio = pre_profile[-1] / pre_profile[0]
    print()
    print(f"  Post-LN largest / smallest across blocks: {post_ratio:.3f}")
    print(f"  Pre-LN  output / input:                   {pre_ratio:.3f}")
    return post_ratio, pre_ratio


def gradient_profile(stack, x, target, step):
    """Gradient norm of every block's attention output projection."""
    return [
        gradient_norm(stack, x, target, block.attention.w_output, step)
        for block in stack.blocks
    ]


def tilt(gradients):
    """Mean gradient of the output half divided by that of the input half.

    Above 1 means gradient concentrates toward the output, which is the
    Post-LN pathology Xiong et al. describe. Below 1 means it does not.
    Dividing two means from the same arrangement cancels that
    arrangement's overall scale, which is exactly what has to be removed
    before the two can be compared.

    Raises:
        ValueError: if there are fewer than two blocks to split.
    """
    if len(gradients) < 2:
        raise ValueError("tilt needs at least two blocks")
    half = len(gradients) // 2
    bottom = sum(gradients[:half]) / half
    top = sum(gradients[half:]) / (len(gradients) - half)
    if bottom <= 0.0:
        raise ValueError("the input half has no gradient to divide by")
    return top / bottom


def print_gradients(post_grads, pre_grads):
    """Print the per-block gradient table, raw and scale-free."""
    print()
    print("BACKWARD: gradient norm of each block's attention output projection")
    print(f"  central differences, step {STEP:.0e}, "
          f"{D_MODEL * D_MODEL} entries per block")
    print("  block 0 is nearest the input, "
          f"block {NUM_LAYERS - 1} is nearest the output")
    print()
    post_mean = sum(post_grads) / len(post_grads)
    pre_mean = sum(pre_grads) / len(pre_grads)
    header = (
        f"{'block':>7} {'Post-LN':>11} {'/ its mean':>11} "
        f"{'Pre-LN':>11} {'/ its mean':>11}"
    )
    print(f"  {header}")
    print("  " + "-" * len(header))
    for index, (post, pre) in enumerate(zip(post_grads, pre_grads)):
        print(
            f"  {index:>7} {post:>11.6f} {post / post_mean:>11.2f} "
            f"{pre:>11.6f} {pre / pre_mean:>11.2f}"
        )
    print()
    print("  raw columns are NOT comparable across arrangements: Pre-LN's")
    print("  residual stream is larger by the top of the stack, so its")
    print("  outputs sit further from the target for reasons unrelated to")
    print("  gradient behaviour. The '/ its mean' columns remove that.")
    print()
    post_tilt = tilt(post_grads)
    pre_tilt = tilt(pre_grads)
    print(f"  Post-LN tilt, output half over input half: {post_tilt:.3f}")
    print(f"  Pre-LN  tilt, output half over input half: {pre_tilt:.3f}")
    print(f"  Post-LN tilts {post_tilt / pre_tilt:.2f} times further toward "
          "the output")
    return post_tilt, pre_tilt


def check_claims(identical, ratios, step_check, tilts):
    """Assert the five claims the article makes. Raises AssertionError."""
    assert identical, (
        "CLAIM 1 died: the two stacks do not hold identical weights, so any "
        "difference measured below is not attributable to the arrangement"
    )

    post_ratio, pre_ratio, pre_monotone = ratios
    assert post_ratio < FLAT_RATIO, (
        f"CLAIM 2 died: Post-LN's residual stream varied by a factor of "
        f"{post_ratio:.3f} across the stack, which is not flat"
    )
    assert pre_ratio > FLAT_RATIO, (
        f"CLAIM 2 died: Pre-LN's residual stream grew only {pre_ratio:.3f} "
        "times from input to output, so there is no growth to report"
    )
    assert pre_monotone, (
        "CLAIM 2 died: Pre-LN's residual stream did not grow at every block, "
        "so the growth is not monotone and the article must not say it is"
    )

    coarse, fine = step_check
    relative = abs(coarse - fine) / coarse
    assert relative < STEP_AGREEMENT, (
        f"CLAIM 3 died: halving the finite-difference step moved the gradient "
        f"norm from {coarse:.6f} to {fine:.6f}, a relative {relative:.2%}, "
        f"above {STEP_AGREEMENT:.0%}. The step is too large to trust"
    )

    assert pre_ratio > 2.0, (
        f"CLAIM 4 died: Pre-LN's residual stream grew only {pre_ratio:.3f} "
        "times, so the forward scales are close enough that raw gradient "
        "magnitudes might be comparable after all. The article's caveat "
        "about not comparing them would then be unearned and must be redone"
    )

    post_tilt, pre_tilt = tilts
    assert post_tilt > 1.0, (
        f"CLAIM 5 died: Post-LN's gradient tilt is {post_tilt:.3f}, so it "
        "does NOT concentrate gradient toward the output on this run, and "
        "the direction Xiong et al. describe does not appear here. The "
        "article must report that instead of the prediction"
    )
    assert pre_tilt < 1.0, (
        f"CLAIM 5 died: Pre-LN's gradient tilt is {pre_tilt:.3f}, which also "
        "concentrates toward the output, so the two arrangements do not "
        "differ in the way the article claims"
    )


def main():
    """Measure forward and backward for both arrangements, then verify."""
    rng = random.Random(SEED)
    x = sample_input(rng)
    target = fixed_target(random.Random(TARGET_SEED))
    post = build(norm_first=False)
    pre = build(norm_first=True)

    identical = weights_are_identical(pre, post)
    print(f"both stacks hold identical weights: {identical}")
    print()

    post_profile = residual_profile(post, x)
    pre_profile = residual_profile(pre, x)
    post_ratio, pre_ratio = print_residual(pre_profile, post_profile)
    pre_monotone = all(
        later > earlier for earlier, later in zip(pre_profile, pre_profile[1:])
    )
    print(f"  Pre-LN grows at every block:              {pre_monotone}")

    post_grads = gradient_profile(post, x, target, STEP)
    pre_grads = gradient_profile(pre, x, target, STEP)
    tilts = print_gradients(post_grads, pre_grads)

    coarse = post_grads[-1]
    fine = gradient_norm(
        post, x, target, post.blocks[-1].attention.w_output, CHECK_STEP
    )
    print()
    print("STEP CHECK: is the finite-difference step small enough?")
    print(f"  step {STEP:.0e}   gradient norm {coarse:.6f}")
    print(f"  step {CHECK_STEP:.0e}   gradient norm {fine:.6f}")
    print(f"  relative change  {abs(coarse - fine) / coarse:.2%}")

    try:
        check_claims(
            identical,
            (post_ratio, pre_ratio, pre_monotone),
            (coarse, fine),
            tilts,
        )
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nAll assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
