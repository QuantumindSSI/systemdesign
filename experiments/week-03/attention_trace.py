"""Every intermediate value of one attention computation, printed.

Companion artifact for the week-3 Tuesday evening walkthrough (2026-09-08).

`experiments/week-03/attention_heads.py` measures claims across many
samples. This script does the opposite: one tiny example, four positions
and four numbers per position, with every matrix printed at every step,
so that a reader can check the walkthrough's arithmetic by hand instead
of trusting it.

It prints, in order:

  PART 1  the input sequence, and the three projections of it that one
          head performs (lib/attention.py lines 187 to 189).
  PART 2  the four steps of scaled dot-product attention with the matrix
          after each one (lines 125, 126, 133, 134, 135), so the effect
          of the sqrt(d_k) divisor and of the causal mask are both
          visible as before-and-after tables rather than described.
  PART 3  the same row of the same input as seen by two different heads,
          with the total variation distance between them.
  PART 4  the assembly: per-head outputs, the concatenation, the output
          projection, and the shape at each stage.
  PART 5  wall-clock cost at five head counts, which is the measurement
          behind the claim that splitting into heads is cost-neutral and
          that this implementation buys none of the available parallelism.
  PART 6  every error path in lib/attention.py and lib/linalg.py that a
          caller can reach, triggered on purpose, with the real message.

Determinism: the input sequence comes from random.Random(SEQUENCE_SEED)
and is rounded to four decimal places before use, and the model weights
come from MultiHeadSelfAttention's own seed. Two runs on any machine
produce identical numbers. PART 5 is wall-clock and will differ.

Run:      python3 experiments/week-03/attention_trace.py
Depends:  Python 3.8+ standard library only, plus this repository.
Runtime:  about four seconds, almost all of it in PART 5.
Exit:     0 and "All assertions passed", or non-zero with the reason.
"""

import math
import os
import random
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.attention import (  # noqa: E402
    MultiHeadSelfAttention,
    causal_mask,
    scaled_dot_product_attention,
)
from lib.linalg import (  # noqa: E402
    add,
    hstack,
    matmul,
    scale,
    shape,
    softmax_rows,
    transpose,
)

SEQUENCE_SEED = 13
MODEL_SEED = 20260908
TRACE_POSITIONS = 4
TRACE_D_MODEL = 4
TRACE_HEADS = 2
TRACE_ROW = 3

TIMING_D_MODEL = 128
TIMING_POSITIONS = 64
TIMING_HEAD_COUNTS = (1, 2, 4, 8, 16)
TIMING_REPEATS = 3

DECIMALS = 4
WEIGHT_SUM_TOLERANCE = 1e-12


def cell(value):
    """Render one matrix entry, keeping -inf readable rather than numeric."""
    if value == float("-inf"):
        return "    -inf"
    return f"{value:8.4f}"


def show(label, matrix):
    """Print a labelled matrix, one row per line, aligned."""
    rows, cols = shape(matrix)
    print(f"  {label}   ({rows} x {cols})")
    for row in matrix:
        print("    [" + " ".join(cell(value) for value in row) + " ]")
    print()


def build_sequence():
    """Return the rounded input sequence the walkthrough quotes."""
    rng = random.Random(SEQUENCE_SEED)
    return [
        [round(rng.uniform(-1.0, 1.0), DECIMALS) for _ in range(TRACE_D_MODEL)]
        for _ in range(TRACE_POSITIONS)
    ]


def part_one(sequence, head):
    """Print the input and the head's three projections of it."""
    print("PART 1  one input, projected three ways")
    print("        lib/attention.py lines 187 to 189\n")
    show("x", sequence)
    show("W_q", head.w_query)
    queries = matmul(sequence, head.w_query)
    keys = matmul(sequence, head.w_key)
    values = matmul(sequence, head.w_value)
    show("Q = x W_q", queries)
    show("K = x W_k", keys)
    show("V = x W_v", values)
    return queries, keys, values


def part_two(queries, keys, values, mask):
    """Print each of the four attention steps and the matrix it produces."""
    print("\nPART 2  the four steps, one matrix at a time")
    print("        lib/attention.py lines 125, 126, 133, 134, 135\n")
    _, d_k = shape(queries)

    raw = matmul(queries, transpose(keys))
    show("1. scores = Q K^T   (line 125)", raw)

    scaled = scale(raw, 1.0 / math.sqrt(d_k))
    print(f"  dividing by sqrt(d_k) = sqrt({d_k}) = {math.sqrt(d_k):.6f}\n")
    show("2. scores / sqrt(d_k)   (line 126)", scaled)

    masked = add(scaled, mask)
    show("3a. + causal mask   (line 133)", masked)

    weights = softmax_rows(masked)
    show("3b. softmax per row   (line 134)", weights)
    for index, row in enumerate(weights):
        total = sum(row)
        print(f"    row {index} sums to {total!r}")
    print()

    output = matmul(weights, values)
    show("4. output = weights V   (line 135)", output)
    return weights, output


def part_three(attention, sequence, mask):
    """Print one row as two different heads see it, and their distance."""
    print("\nPART 3  the same row, as seen by two heads\n")
    rows = []
    for index, head in enumerate(attention.heads):
        _, weights = head.forward(sequence, mask)
        row = weights[TRACE_ROW]
        rows.append(row)
        rendered = " ".join(f"{value:.4f}" for value in row)
        print(f"  head {index} row {TRACE_ROW}:  [{rendered} ]")
    distance = 0.5 * sum(abs(a - b) for a, b in zip(rows[0], rows[1]))
    print(f"\n  total variation distance: {distance:.4f}")
    print("  0 would mean the second head is redundant on this row.\n")
    return distance


def part_four(attention, sequence, mask):
    """Print the assembly: per-head outputs, concatenation, projection."""
    print("\nPART 4  assembling the heads")
    print("        lib/attention.py lines 249 to 254\n")
    per_head = []
    for index, head in enumerate(attention.heads):
        head_output, _ = head.forward(sequence, mask)
        per_head.append(head_output)
        show(f"head {index} output", head_output)
    concatenated = hstack(per_head)
    show("concatenated   (line 253)", concatenated)
    show("W_o", attention.w_output)
    final, _ = attention.forward(sequence, mask)
    show("final = concat W_o   (line 254)", final)
    print(f"  input was {shape(sequence)}, output is {shape(final)}: "
          "attention preserves the shape it was given.\n")
    return final


def part_five():
    """Time the forward pass at five head counts and print the table."""
    print("\nPART 5  what splitting into heads costs")
    print(f"        d_model {TIMING_D_MODEL}, {TIMING_POSITIONS} positions, "
          f"causal mask, mean of {TIMING_REPEATS} runs\n")
    rng = random.Random(SEQUENCE_SEED)
    sequence = [
        [rng.uniform(-1.0, 1.0) for _ in range(TIMING_D_MODEL)]
        for _ in range(TIMING_POSITIONS)
    ]
    mask = causal_mask(TIMING_POSITIONS)
    print(f"  {'heads':>6}  {'d_head':>7}  {'seconds':>9}  {'vs 1 head':>10}")
    print("  " + "-" * 38)
    baseline, ratios = None, {}
    for head_count in TIMING_HEAD_COUNTS:
        attention = MultiHeadSelfAttention(TIMING_D_MODEL, head_count, MODEL_SEED)
        start = time.perf_counter()
        for _ in range(TIMING_REPEATS):
            attention.forward(sequence, mask)
        elapsed = (time.perf_counter() - start) / TIMING_REPEATS
        if baseline is None:
            baseline = elapsed
        ratios[head_count] = elapsed / baseline
        print(f"  {head_count:>6}  {attention.d_head:>7}  {elapsed:>9.4f}"
              f"  {ratios[head_count]:>9.2f}x")
    print("\n  The multiply-adds are identical at every row: n * n * d_model")
    print("  for the scores, however the width is partitioned. Any rise is")
    print("  interpreter overhead from running the heads one after another.\n")
    return ratios


def error_cases():
    """Return every reachable error path as (label, zero-argument callable)."""
    return (
        ("query and key widths disagree",
         lambda: scaled_dot_product_attention([[1.0, 2.0]], [[1.0, 2.0, 3.0]], [[1.0]])),
        ("more keys than values",
         lambda: scaled_dot_product_attention(
             [[1.0, 2.0]], [[1.0, 2.0], [3.0, 4.0]], [[1.0]])),
        ("mask does not match the score matrix",
         lambda: scaled_dot_product_attention(
             [[1.0, 2.0]], [[1.0, 2.0]], [[1.0]], [[0.0, 0.0]])),
        ("head count does not divide d_model",
         lambda: MultiHeadSelfAttention(64, 5, MODEL_SEED)),
        ("input is not as wide as the model",
         lambda: MultiHeadSelfAttention(4, 2, MODEL_SEED).forward([[1.0, 2.0]])),
        ("every position in a row is masked",
         lambda: softmax_rows([[float("-inf"), float("-inf")]])),
        ("a ragged matrix",
         lambda: shape([[1.0, 2.0], [3.0]])),
    )


def part_six():
    """Trigger every error path and print the message the caller receives."""
    print("\nPART 6  every error path, triggered on purpose\n")
    messages = {}
    for label, trigger in error_cases():
        try:
            trigger()
        except ValueError as exc:
            messages[label] = str(exc)
            print(f"  {label}")
            print(f"    ValueError: {exc}\n")
        else:
            raise AssertionError(f"{label!r} was supposed to raise and did not")
    return messages


def check_claims(weights, final, sequence, distance, ratios, messages):
    """Assert everything the walkthrough asserts in prose.

    Raises:
        AssertionError: naming the claim and the measurement that broke it.
    """
    for index, row in enumerate(weights):
        total = sum(row)
        assert abs(total - 1.0) <= WEIGHT_SUM_TOLERANCE, (
            f"attention weight row {index} summed to {total}, not 1.0: the "
            "budget argument in the morning essay depends on this"
        )
    for index, row in enumerate(weights):
        for column in range(index + 1, len(row)):
            assert row[column] == 0.0, (
                f"causal mask leaked: row {index} gave weight {row[column]} "
                f"to future position {column}"
            )
    assert shape(final) == shape(sequence), (
        f"attention changed the shape from {shape(sequence)} to {shape(final)}"
    )
    assert distance > 0.0, (
        "the two heads produced identical weights on the traced row, so the "
        "walkthrough's claim that they differ is false"
    )
    assert ratios[1] == 1.0, "the baseline ratio must be exactly 1.0"
    assert max(ratios.values()) < 2.0, (
        f"cost was supposed to be roughly flat in head count, but 16 heads "
        f"cost {max(ratios.values()):.2f} times one head"
    )
    assert len(messages) == len(error_cases()), (
        "an error path did not raise, so the code guesses where it should stop"
    )
    for label, message in messages.items():
        assert message.strip(), f"{label!r} raised with an empty message"


def main():
    """Print all six parts, then assert every claim. Returns an exit code."""
    print("One attention computation, every intermediate value")
    print("=" * 66)
    print()

    sequence = build_sequence()
    attention = MultiHeadSelfAttention(TRACE_D_MODEL, TRACE_HEADS, MODEL_SEED)
    mask = causal_mask(TRACE_POSITIONS)
    print(f"  d_model {TRACE_D_MODEL}, {TRACE_HEADS} heads, so d_head is "
          f"{attention.d_head}; {TRACE_POSITIONS} positions; seed {MODEL_SEED}\n")

    queries, keys, values = part_one(sequence, attention.heads[0])
    weights, _ = part_two(queries, keys, values, mask)
    distance = part_three(attention, sequence, mask)
    final = part_four(attention, sequence, mask)
    ratios = part_five()
    messages = part_six()

    try:
        check_claims(weights, final, sequence, distance, ratios, messages)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1

    print("All assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
