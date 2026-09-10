"""Rotary position embedding: rotate pairs of dimensions by position.

Standard library only, built on `lib/linalg.py`. This is the reference
implementation the series uses when it needs RoPE.

The idea, stripped of notation. Take a vector of even width and read it as
a list of two-dimensional pairs: dimensions 0 and 1 are one pair, 2 and 3
are the next, and so on. Each pair is a point on a plane, and a point on a
plane can be rotated. RoPE rotates pair i by an angle proportional to the
position, with a per-pair rate:

    theta_i = base ** (-2i / d)      for i = 0 .. d/2 - 1
    angle for pair i at position m = m * theta_i

Pair 0 rotates fast, one full turn every few positions. The last pair
rotates so slowly that across an entire context it barely moves. So the
fast pairs encode fine local offsets and the slow pairs encode coarse
absolute location, and the vector carries both at once.

WHY THIS IS MORE THAN A TRICK. Rotation by m then comparing against
rotation by n leaves a rotation by (m - n). Concretely, for any q, k and
any positions m, n:

    dot(rotate(q, m), rotate(k, n)) == dot(rotate(q, m - n), rotate(k, 0))

The attention score between two positions depends only on how far apart
they are, never on where the pair sits in the sequence. Su et al. state
this as encoding "the absolute position with a rotation matrix" while
incorporating "the explicit relative position dependency in self-attention
formulation" (arXiv:2104.09864). That identity is exact, it holds to
machine precision, and `experiments/week-03/rope_properties.py` checks it
rather than assuming it.

WHAT IT DOES NOT CHANGE. A rotation preserves length. Every vector comes
out of `rotate` with the norm it went in with, so RoPE cannot amplify or
attenuate anything. It only turns.

Applied to attention, RoPE goes on the queries and the keys and not on
the values, because the point is to make the score position-aware, not to
rewrite the payload a position contributes.

Nothing here is trained. RoPE has no parameters at all: given d_head and
the base, every angle is determined. That is unusual and worth noticing.
"""

import math
from typing import List, Sequence

from lib.linalg import Matrix, shape

# The rate constant from the paper. Larger means the slow pairs turn even
# more slowly, which is exactly the knob context-extension work adjusts.
DEFAULT_BASE = 10000.0


def inverse_frequencies(d_head: int, base: float = DEFAULT_BASE) -> List[float]:
    """Return theta_i for each of the d_head / 2 pairs.

    Args:
        d_head: head width, must be positive and even. Odd widths have a
            dimension with no partner to rotate against.
        base: the rate constant, must be greater than 1.

    Returns:
        A list of d_head / 2 angular rates, descending from 1.0.

    Raises:
        ValueError: if d_head is not positive and even, or base <= 1.
    """
    if d_head <= 0 or d_head % 2 != 0:
        raise ValueError(f"d_head must be positive and even, got {d_head}")
    if base <= 1.0:
        raise ValueError(f"base must be greater than 1, got {base}")
    pairs = d_head // 2
    return [base ** (-2.0 * index / d_head) for index in range(pairs)]


def rotate(
    vector: Sequence[float], position: int, base: float = DEFAULT_BASE
) -> List[float]:
    """Rotate each dimension pair of `vector` by position times its rate.

    Args:
        vector: a sequence of even length.
        position: the position index. May be any integer, including
            negative, which is what makes the relative-position identity
            testable directly.
        base: the rate constant.

    Returns:
        A new list of the same length. The input is not modified.

    Raises:
        ValueError: if the length is odd or zero, or base is invalid.

    Complexity: O(len(vector)).
    """
    width = len(vector)
    rates = inverse_frequencies(width, base)
    rotated = [0.0] * width
    for index, rate in enumerate(rates):
        angle = position * rate
        cosine = math.cos(angle)
        sine = math.sin(angle)
        even = vector[2 * index]
        odd = vector[2 * index + 1]
        rotated[2 * index] = even * cosine - odd * sine
        rotated[2 * index + 1] = even * sine + odd * cosine
    return rotated


def apply_rope(
    rows: Sequence[Sequence[float]], base: float = DEFAULT_BASE, offset: int = 0
) -> Matrix:
    """Rotate row j of `rows` by position (offset + j).

    Args:
        rows: an (n, d_head) matrix of queries or of keys.
        base: the rate constant.
        offset: position of the first row. Non-zero offsets are what a
            KV cache needs, since row 0 of a continuation is not position
            0 of the sequence.

    Returns:
        A new (n, d_head) matrix.

    Raises:
        ValueError: if the matrix is empty, ragged, or of odd width.

    Complexity: O(n * d_head).
    """
    _, width = shape(rows)
    if width % 2 != 0:
        raise ValueError(f"apply_rope needs an even width, got {width}")
    return [rotate(row, offset + index, base) for index, row in enumerate(rows)]


def norm(vector: Sequence[float]) -> float:
    """Euclidean length of a vector.

    Present so that the length-preservation property can be measured
    rather than asserted.

    Raises:
        ValueError: if the vector is empty.
    """
    if not vector:
        raise ValueError("norm needs a non-empty vector")
    return math.sqrt(sum(value * value for value in vector))


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    """Dot product of two vectors of equal length.

    Raises:
        ValueError: if the lengths differ.
    """
    if len(left) != len(right):
        raise ValueError(
            f"cannot take a dot product of lengths {len(left)} and {len(right)}"
        )
    return sum(a * b for a, b in zip(left, right))


def relative_score(
    query: Sequence[float],
    key: Sequence[float],
    query_position: int,
    key_position: int,
    base: float = DEFAULT_BASE,
) -> float:
    """Unscaled attention score between one query and one key under RoPE.

    This is the quantity the relative-position identity is about. Call it
    two ways with the same (query_position - key_position) and the answers
    agree to machine precision.

    Args:
        query: the query vector, even width.
        key: the key vector, same width as query.
        query_position: absolute position of the query.
        key_position: absolute position of the key.
        base: the rate constant.

    Returns:
        The dot product of the two rotated vectors. Not divided by
        sqrt(d_head): that scaling belongs to attention, not to RoPE.

    Raises:
        ValueError: if the widths differ or are odd.
    """
    if len(query) != len(key):
        raise ValueError(
            f"query is {len(query)} wide and key is {len(key)} wide"
        )
    return dot(
        rotate(query, query_position, base), rotate(key, key_position, base)
    )
