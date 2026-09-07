"""Scaled dot-product attention and multi-head self-attention.

Standard library only, built on `lib/linalg.py`. This is the reference
implementation the series walks through when it needs attention.

A sequence of n positions is a matrix of shape (n, d_model): one row per
position, d_model numbers describing that position. Attention answers one
question for each row: given what I am looking for, which other rows
should contribute to my output, and how much?

It answers it in four steps, and every step is one line in
`scaled_dot_product_attention` below:

  1. scores = Q K^T          how well each query matches each key
  2. scores = scores / sqrt(d_k)   the scaling discussed in step 2 below
  3. weights = softmax(scores)     turn scores into a distribution per row
  4. output = weights V            a weighted average of the value rows

Step 2 is the one people skip. Vaswani et al. (arXiv:1706.03762) state it
as a suspicion with an argument: if the components of q and k are
independent with mean 0 and variance 1, their dot product over d_k terms
has variance d_k, so scores grow with the square root of the dimension.
Large scores push softmax into a region where one weight approaches 1 and
the gradients approach 0. Dividing by sqrt(d_k) holds the variance at
roughly 1 regardless of head width. `experiments/week-03/` measures that
growth rather than taking it on faith.

Nothing here is trained. There is no backward pass and no optimiser: the
weights are initialised deterministically from a seed so that a reader can
reproduce every number in an article exactly. The point of this module is
to make the forward computation legible, not to fit anything.
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

from lib.linalg import Matrix, add, hstack, matmul, scale, shape, softmax_rows, transpose

NEG_INF = float("-inf")


def glorot_matrix(rows: int, cols: int, rng: random.Random) -> Matrix:
    """Return a rows by cols matrix drawn uniformly from [-limit, limit].

    limit = sqrt(6 / (rows + cols)), the Glorot and Bengio (2010) uniform
    initialisation. The scale matters here for one reason only: it keeps
    the projected values in a range where the sqrt(d_k) discussion above
    is observable rather than swamped by an arbitrary weight magnitude.

    Args:
        rows: input width (fan in).
        cols: output width (fan out).
        rng: a seeded random.Random, so results are reproducible.

    Raises:
        ValueError: if either dimension is not positive.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError(f"glorot_matrix needs positive dims, got ({rows}, {cols})")
    limit = math.sqrt(6.0 / (rows + cols))
    return [[rng.uniform(-limit, limit) for _ in range(cols)] for _ in range(rows)]


def causal_mask(length: int) -> Matrix:
    """Return an additive mask that forbids attending to the future.

    Entry (i, j) is 0.0 when j <= i and -inf when j > i. Adding it to the
    scores before softmax drives the forbidden weights to exactly 0.0,
    because exp(-inf) is 0.

    This is the difference between a model that predicts the next token
    and a model that has already read it. Getting it wrong produces
    excellent training loss and a useless model.

    Raises:
        ValueError: if length is not positive.
    """
    if length <= 0:
        raise ValueError(f"causal_mask needs positive length, got {length}")
    return [
        [0.0 if col <= row else NEG_INF for col in range(length)]
        for row in range(length)
    ]


def scaled_dot_product_attention(
    queries: Sequence[Sequence[float]],
    keys: Sequence[Sequence[float]],
    values: Sequence[Sequence[float]],
    mask: Optional[Sequence[Sequence[float]]] = None,
) -> Tuple[Matrix, Matrix]:
    """Compute attention output and the weights that produced it.

    Args:
        queries: (n_q, d_k).
        keys: (n_k, d_k).
        values: (n_k, d_v). Must have the same row count as keys.
        mask: optional (n_q, n_k) additive mask, 0.0 to allow and -inf to
            forbid. See `causal_mask`.

    Returns:
        (output, weights) where output is (n_q, d_v) and weights is
        (n_q, n_k) with every row summing to 1.0.

    Raises:
        ValueError: on any shape disagreement, naming both shapes.

    Complexity: O(n_q * n_k * (d_k + d_v)) multiply-adds. The n_q * n_k
    term is the quadratic cost that dominates long-context work.
    """
    n_queries, d_k = shape(queries)
    n_keys, key_width = shape(keys)
    n_values, _ = shape(values)
    if key_width != d_k:
        raise ValueError(
            f"queries have width {d_k} but keys have width {key_width}"
        )
    if n_values != n_keys:
        raise ValueError(
            f"keys have {n_keys} rows but values have {n_values}: "
            "every key must have exactly one value"
        )

    scores = matmul(queries, transpose(keys))
    scores = scale(scores, 1.0 / math.sqrt(d_k))
    if mask is not None:
        mask_shape = shape(mask)
        if mask_shape != (n_queries, n_keys):
            raise ValueError(
                f"mask is {mask_shape} but scores are ({n_queries}, {n_keys})"
            )
        scores = add(scores, mask)
    weights = softmax_rows(scores)
    return matmul(weights, values), weights


class AttentionHead:
    """One attention head: three projections and one attention computation.

    The head owns W_q, W_k and W_v, each (d_model, d_head). It projects the
    same input three times into three different spaces, which is the whole
    trick: "what am I looking for", "what do I offer as a match", and "what
    do I actually contribute" are three different questions about one
    position, and nothing forces them to share a representation.
    """

    def __init__(self, d_model: int, d_head: int, rng: random.Random):
        """Initialise the three projections deterministically from `rng`.

        Raises:
            ValueError: if either dimension is not positive.
        """
        if d_model <= 0 or d_head <= 0:
            raise ValueError(
                f"AttentionHead needs positive dims, got d_model={d_model}, "
                f"d_head={d_head}"
            )
        self.d_model = d_model
        self.d_head = d_head
        self.w_query = glorot_matrix(d_model, d_head, rng)
        self.w_key = glorot_matrix(d_model, d_head, rng)
        self.w_value = glorot_matrix(d_model, d_head, rng)

    def forward(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[Matrix, Matrix]:
        """Project x three ways and attend.

        Args:
            x: (n, d_model) input sequence.
            mask: optional additive (n, n) mask.

        Returns:
            (output, weights): output is (n, d_head), weights is (n, n).

        Raises:
            ValueError: if x is not d_model wide.
        """
        _, width = shape(x)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this head expects {self.d_model}"
            )
        queries = matmul(x, self.w_query)
        keys = matmul(x, self.w_key)
        values = matmul(x, self.w_value)
        return scaled_dot_product_attention(queries, keys, values, mask)


class MultiHeadSelfAttention:
    """Several attention heads in parallel, concatenated and projected.

    The heads split d_model rather than adding to it: with d_model = 512
    and 8 heads, each head is 64 wide. This is why the original paper can
    say the total cost is similar to one head at full width. Adding heads
    does not add width; it divides the width you already had into more,
    narrower questions.
    """

    def __init__(self, d_model: int, num_heads: int, seed: int):
        """Build `num_heads` heads plus the output projection.

        Args:
            d_model: model width, must be divisible by num_heads.
            num_heads: number of parallel heads, at least 1.
            seed: seeds a random.Random so every weight is reproducible.

        Raises:
            ValueError: if num_heads is below 1 or does not divide d_model.
        """
        if num_heads < 1:
            raise ValueError(f"num_heads must be at least 1, got {num_heads}")
        if d_model % num_heads != 0:
            raise ValueError(
                f"d_model {d_model} is not divisible by num_heads {num_heads}"
            )
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_head = d_model // num_heads
        rng = random.Random(seed)
        self.heads = [
            AttentionHead(d_model, self.d_head, rng) for _ in range(num_heads)
        ]
        self.w_output = glorot_matrix(num_heads * self.d_head, d_model, rng)

    def forward(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[Matrix, List[Matrix]]:
        """Run every head on the same input, concatenate, project.

        Args:
            x: (n, d_model) input sequence.
            mask: optional additive (n, n) mask shared by all heads.

        Returns:
            (output, weights_per_head): output is (n, d_model) and
            weights_per_head has one (n, n) matrix per head, in head order.

        Raises:
            ValueError: if x is not d_model wide.
        """
        outputs: List[Matrix] = []
        weights_per_head: List[Matrix] = []
        for head in self.heads:
            head_output, head_weights = head.forward(x, mask)
            outputs.append(head_output)
            weights_per_head.append(head_weights)
        concatenated = hstack(outputs)
        return matmul(concatenated, self.w_output), weights_per_head
