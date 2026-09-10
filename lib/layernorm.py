"""Layer normalization, and the block whose only question is where it goes.

Standard library only, built on `lib/linalg.py` and `lib/attention.py`.

Layer normalization itself is three lines of arithmetic. For each row
independently: subtract the row's mean, divide by the row's standard
deviation, then scale by a learned gain and shift by a learned bias. It
looks like housekeeping.

Where you put it does not look like housekeeping once you have watched a
training run refuse to start. There are two arrangements, they differ by
the position of one function call, and they are not equivalent:

    POST-LN, the original    x -> LayerNorm(x + Sublayer(x))
    PRE-LN                   x -> x + Sublayer(LayerNorm(x))

In Post-LN the normalization sits ON the residual path, so everything
flowing from one block to the next has been renormalised. In Pre-LN the
residual path is untouched from input to output and the normalization
happens only on the branch. That single difference decides whether the
residual stream grows with depth, and Xiong et al. (arXiv:2002.04745)
argue with mean field theory that it also decides whether the gradients
at the output layer are well behaved at initialization, which is why the
original recipe needs a learning-rate warm-up stage and the other one
largely does not.

`experiments/week-03/norm_placement.py` measures both consequences on a
model small enough to differentiate by finite differences, and is explicit
that a six-layer toy is not the regime the paper's proof is about.

Nothing here is trained. Weights come from a seed. There is no autodiff in
this repository, so gradients, where they are needed, are computed by
central differences on the forward pass.
"""

import math
import random
from typing import List, Optional, Sequence

from lib.attention import MultiHeadSelfAttention, glorot_matrix
from lib.linalg import Matrix, add, matmul, shape

# Guards the division when a row is constant and its variance is 0.
DEFAULT_EPSILON = 1e-5


def layer_norm(
    rows: Sequence[Sequence[float]],
    gain: Sequence[float],
    bias: Sequence[float],
    epsilon: float = DEFAULT_EPSILON,
) -> Matrix:
    """Normalise each row to zero mean and unit variance, then scale and shift.

    Normalisation is per row and never across rows, so position i's
    statistics never depend on position j's. That is what makes it usable
    with variable sequence lengths and at inference time on a single row.

    Args:
        rows: an (n, d) matrix.
        gain: length d, the learned per-dimension scale.
        bias: length d, the learned per-dimension shift.
        epsilon: added to the variance before the square root.

    Returns:
        A new (n, d) matrix.

    Raises:
        ValueError: if gain or bias is not d long, or epsilon <= 0.

    Complexity: O(n * d).
    """
    _, width = shape(rows)
    if len(gain) != width or len(bias) != width:
        raise ValueError(
            f"gain is {len(gain)} and bias is {len(bias)}, both must be "
            f"{width} to match the row width"
        )
    if epsilon <= 0.0:
        raise ValueError(f"epsilon must be positive, got {epsilon}")
    normalised: Matrix = []
    for row in rows:
        mean = sum(row) / width
        variance = sum((value - mean) ** 2 for value in row) / width
        deviation = math.sqrt(variance + epsilon)
        normalised.append(
            [
                (value - mean) / deviation * gain[index] + bias[index]
                for index, value in enumerate(row)
            ]
        )
    return normalised


class LayerNorm:
    """Layer normalization with a learned gain and bias.

    Attributes:
        gain: initialised to all ones, so a fresh LayerNorm only
            normalises and does not additionally rescale.
        bias: initialised to all zeros.
    """

    def __init__(self, width: int, epsilon: float = DEFAULT_EPSILON):
        """Allocate gain and bias for a given row width.

        Raises:
            ValueError: if width is not positive.
        """
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")
        self.width = width
        self.epsilon = epsilon
        self.gain: List[float] = [1.0] * width
        self.bias: List[float] = [0.0] * width

    def forward(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Normalise, scale and shift every row."""
        return layer_norm(rows, self.gain, self.bias, self.epsilon)


class FeedForward:
    """The position-wise two-layer network that follows attention.

    One hidden layer with a ReLU, applied to each row independently. It is
    here because a transformer block has two sublayers and the layer-norm
    placement question is about both of them, not only attention.
    """

    def __init__(self, d_model: int, d_hidden: int, rng: random.Random):
        """Allocate both projections.

        Raises:
            ValueError: if either dimension is not positive.
        """
        if d_model <= 0 or d_hidden <= 0:
            raise ValueError(
                f"FeedForward needs positive dims, got ({d_model}, {d_hidden})"
            )
        self.d_model = d_model
        self.d_hidden = d_hidden
        self.w_in = glorot_matrix(d_model, d_hidden, rng)
        self.w_out = glorot_matrix(d_hidden, d_model, rng)

    def forward(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Project up, rectify, project back down.

        Raises:
            ValueError: if rows are not d_model wide.

        Complexity: O(n * d_model * d_hidden).
        """
        _, width = shape(rows)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this network expects {self.d_model}"
            )
        hidden = matmul(rows, self.w_in)
        rectified = [[value if value > 0.0 else 0.0 for value in row]
                     for row in hidden]
        return matmul(rectified, self.w_out)


class TransformerBlock:
    """Attention and feed-forward, with the norm before or after.

    Attributes:
        norm_first: True for Pre-LN, False for Post-LN. This single
            boolean is the entire subject of the Saturday challenge.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        d_hidden: int,
        seed: int,
        norm_first: bool,
    ):
        """Build one block in the requested arrangement.

        Args:
            d_model: model width.
            num_heads: heads in the attention sublayer.
            d_hidden: width of the feed-forward hidden layer.
            seed: seeds every weight in this block.
            norm_first: True for Pre-LN, False for Post-LN.

        Raises:
            ValueError: propagated from the sublayers on bad dimensions.
        """
        self.d_model = d_model
        self.norm_first = norm_first
        self.attention = MultiHeadSelfAttention(d_model, num_heads, seed)
        rng = random.Random(seed + 1)
        self.feed_forward = FeedForward(d_model, d_hidden, rng)
        self.norm_attention = LayerNorm(d_model)
        self.norm_feed_forward = LayerNorm(d_model)

    def forward(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Matrix:
        """Run both sublayers in the configured arrangement.

        Post-LN normalises the sum, so the value handed to the next block
        has always been renormalised. Pre-LN normalises only the branch,
        so the residual path runs from input to output untouched.

        Args:
            x: an (n, d_model) input.
            mask: optional additive attention mask.

        Returns:
            An (n, d_model) output.

        Raises:
            ValueError: if x is not d_model wide.
        """
        if self.norm_first:
            attended, _ = self.attention.forward(self.norm_attention.forward(x), mask)
            x = add(x, attended)
            branch = self.feed_forward.forward(self.norm_feed_forward.forward(x))
            return add(x, branch)
        attended, _ = self.attention.forward(x, mask)
        x = self.norm_attention.forward(add(x, attended))
        branch = self.feed_forward.forward(x)
        return self.norm_feed_forward.forward(add(x, branch))


class TransformerStack:
    """A stack of identical blocks, all in the same arrangement.

    Attributes:
        blocks: the blocks in order, block 0 nearest the input.
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        d_hidden: int,
        num_layers: int,
        seed: int,
        norm_first: bool,
    ):
        """Build `num_layers` blocks, each seeded distinctly but reproducibly.

        Both arrangements built with the same seed hold numerically
        identical weights, so any difference measured between them is the
        arrangement and nothing else.

        Raises:
            ValueError: if num_layers is below 1.
        """
        if num_layers < 1:
            raise ValueError(f"num_layers must be at least 1, got {num_layers}")
        self.d_model = d_model
        self.norm_first = norm_first
        self.blocks = [
            TransformerBlock(
                d_model, num_heads, d_hidden, seed + 100 * index, norm_first
            )
            for index in range(num_layers)
        ]

    def forward(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Matrix:
        """Run every block in order."""
        for block in self.blocks:
            x = block.forward(x, mask)
        return x

    def activations(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> List[Matrix]:
        """Return the input and the output of every block, in order.

        Returns a list of length len(blocks) + 1, so entry 0 is the input
        to block 0 and entry k is the output of block k - 1.
        """
        trace: List[Matrix] = [[list(row) for row in x]]
        for block in self.blocks:
            x = block.forward(x, mask)
            trace.append([list(row) for row in x])
        return trace


def root_mean_square(rows: Sequence[Sequence[float]]) -> float:
    """Root mean square over every element, the size of the residual stream.

    Raises:
        ValueError: if there are no values.
    """
    values = [value for row in rows for value in row]
    if not values:
        raise ValueError("root_mean_square needs at least one value")
    return math.sqrt(sum(value * value for value in values) / len(values))
