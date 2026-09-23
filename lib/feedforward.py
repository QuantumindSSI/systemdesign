"""Feed-forward blocks: the two-thirds of a transformer nobody draws.

Standard library only, built on `lib/linalg.py` and `lib/attention.py`.

Every transformer block has two sublayers. Attention gets the diagrams, the
blog posts and the interview questions. The other one is two matrix
multiplies with a nonlinearity between them, applied to each position
independently, and it holds most of the parameters. Geva et al. open with
the count: "Feed-forward layers constitute two-thirds of a transformer
model's parameters, yet their role in the network remains under-explored"
(arXiv:2012.14913). `experiments/week-04/feedforward_lab.py` checks that
fraction as arithmetic on a stated configuration rather than repeating it.

THE SHAPE. For a block of width d_model with hidden width d_hidden:

    ungated   h = act(x W_in)           then  out = h W_out
    gated     h = act(x W_gate) * x W_in  then  out = h W_out

The ungated form is the original (arXiv:1706.03762), where d_hidden is four
times d_model. The gated form adds a third matrix and multiplies two
projections together element-wise; Shazeer tested several such variants in
the feed-forward sublayers and found "that some of them yield quality
improvements over the typically-used ReLU or GELU activations"
(arXiv:2002.05202). Three matrices at the same hidden width is 1.5 times
the parameters, which is why gated designs shrink d_hidden to two-thirds of
what the ungated design would use. `parameter_count` does that arithmetic.

THE READING THAT MAKES IT CLICK. Write the second multiply out by hand:

    out_row = sum over j of  h[j] * W_out[j]

The output of a feed-forward block is a weighted sum of the ROWS of W_out,
and the weights are the hidden activations. So each hidden unit owns one
fixed output direction and decides how loudly to contribute it. Geva et al.
name this structure directly, arguing feed-forward layers "operate as
key-value memories, where each key correlates with textual patterns in the
training examples, and each value induces a distribution over the output
vocabulary", and that "the output of a feed-forward layer is a composition
of its memories". `decompose_output` computes that composition term by term
so an article can show the identity holding exactly rather than describe it.

Under a ReLU the weights are also mostly zero, so the sum runs over a
subset. `sparsity` measures how large that subset is.

Nothing here is trained. Weights come from a seed.
"""

import math
import random
from typing import Callable, List, NamedTuple, Sequence, Tuple

from lib.attention import glorot_matrix
from lib.linalg import Matrix, matmul, shape

Activation = Callable[[float], float]


def relu(value: float) -> float:
    """max(0, value). The original transformer's choice.

    Exactly zero below the origin, which is what makes hidden activations
    genuinely sparse rather than merely small.
    """
    return value if value > 0.0 else 0.0


def gelu(value: float) -> float:
    """The Gaussian error linear unit, computed exactly.

    value * Phi(value), where Phi is the standard normal cumulative
    distribution function, evaluated through math.erf so this is the exact
    function and not the tanh approximation that appears in many
    implementations. `gelu_tanh` is the approximation, kept beside it so
    the difference can be measured.

    Never exactly zero for a finite negative input, which is the property
    that matters here: a GELU network has no true activation sparsity.
    """
    return value * 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def gelu_tanh(value: float) -> float:
    """The tanh approximation to GELU that most frameworks ship.

    Present so that `experiments/week-04/feedforward_lab.py` can measure how
    far it sits from the exact function instead of assuming they agree.
    """
    inner = math.sqrt(2.0 / math.pi) * (value + 0.044715 * value ** 3)
    return 0.5 * value * (1.0 + math.tanh(inner))


def silu(value: float) -> float:
    """value * sigmoid(value), also called Swish.

    Written to avoid overflowing exp on large negative inputs, because a
    hidden pre-activation is not guaranteed to be small.
    """
    if value >= 0.0:
        return value / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return value * exponential / (1.0 + exponential)


ACTIVATIONS = {
    "relu": relu,
    "gelu": gelu,
    "gelu_tanh": gelu_tanh,
    "silu": silu,
}


def resolve_activation(name: str) -> Activation:
    """Look up an activation by name.

    Raises:
        ValueError: naming every available option, because a silently
            wrong activation produces plausible numbers.
    """
    if name not in ACTIVATIONS:
        raise ValueError(
            f"unknown activation {name!r}, expected one of "
            f"{sorted(ACTIVATIONS)}"
        )
    return ACTIVATIONS[name]


class ParameterCount(NamedTuple):
    """Where the parameters in one transformer block live.

    Attributes:
        attention: the four d_model by d_model projections, Q, K, V and O.
        feed_forward: every matrix in the feed-forward sublayer.
    """

    attention: int
    feed_forward: int

    @property
    def total(self) -> int:
        """Both sublayers together. Biases and norms are excluded."""
        return self.attention + self.feed_forward

    @property
    def feed_forward_share(self) -> float:
        """Feed-forward parameters as a fraction of the block."""
        return self.feed_forward / self.total


def parameter_count(
    d_model: int, d_hidden: int, gated: bool = False
) -> ParameterCount:
    """Count the weight matrices in one transformer block.

    Args:
        d_model: model width.
        d_hidden: feed-forward hidden width.
        gated: True for the three-matrix gated form, False for two.

    Returns:
        A ParameterCount. Attention is 4 * d_model^2, being Q, K, V and the
        output projection. Feed-forward is 2 * d_model * d_hidden ungated
        and 3 * d_model * d_hidden gated.

        Biases, layer-norm gains and the embedding table are excluded. They
        are real parameters and they are tiny next to these, so leaving
        them out keeps the ratio honest and the arithmetic checkable.

    Raises:
        ValueError: if either width is not positive.
    """
    if d_model <= 0 or d_hidden <= 0:
        raise ValueError(
            f"parameter_count needs positive widths, got "
            f"({d_model}, {d_hidden})"
        )
    matrices = 3 if gated else 2
    return ParameterCount(
        attention=4 * d_model * d_model,
        feed_forward=matrices * d_model * d_hidden,
    )


def equivalent_gated_hidden(d_hidden: int) -> int:
    """Hidden width a gated block needs to match an ungated one's parameters.

    Three matrices instead of two, so two-thirds of the width holds the
    same count. The result is rounded down to the nearest multiple of 8,
    the way real configurations round, and the rounding is why a gated
    block is usually a little under parameter-matched rather than exactly.

    Args:
        d_hidden: the ungated hidden width to match.

    Returns:
        The rounded gated hidden width, at least 8.

    Raises:
        ValueError: if d_hidden is not positive.
    """
    if d_hidden <= 0:
        raise ValueError(f"d_hidden must be positive, got {d_hidden}")
    exact = 2 * d_hidden / 3
    rounded = int(exact // 8) * 8
    return max(8, rounded)


def sparsity(hidden: Sequence[Sequence[float]]) -> float:
    """Fraction of hidden activations that are exactly zero.

    Exactly, not approximately. A ReLU network has genuine zeros and the
    products they multiply can be skipped; a GELU network has small values
    that cannot. Measuring the exact-zero fraction is what separates the
    two claims.

    Raises:
        ValueError: if the matrix is empty or ragged.
    """
    rows, cols = shape(hidden)
    zeros = sum(
        1 for row in hidden for value in row if value == 0.0
    )
    return zeros / (rows * cols)


class FeedForward:
    """The two-matrix position-wise network, with a chosen activation.

    Attributes:
        w_in: (d_model, d_hidden), the "keys" in the key-value reading.
        w_out: (d_hidden, d_model), whose ROWS are the "values".
        activation_name: which nonlinearity sits between them.
    """

    def __init__(
        self,
        d_model: int,
        d_hidden: int,
        rng: random.Random,
        activation: str = "relu",
    ):
        """Allocate both projections deterministically from `rng`.

        Raises:
            ValueError: if either width is not positive, or the activation
                name is not recognised.
        """
        if d_model <= 0 or d_hidden <= 0:
            raise ValueError(
                f"FeedForward needs positive dims, got ({d_model}, {d_hidden})"
            )
        self.d_model = d_model
        self.d_hidden = d_hidden
        self.activation_name = activation
        self.activation = resolve_activation(activation)
        self.w_in = glorot_matrix(d_model, d_hidden, rng)
        self.w_out = glorot_matrix(d_hidden, d_model, rng)

    def hidden(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Return the post-activation hidden layer, (n, d_hidden).

        Exposed because the hidden layer is the interesting object: it is
        the set of weights in the key-value reading, and its zero fraction
        is the sparsity an inference kernel would exploit.

        Raises:
            ValueError: if rows are not d_model wide.
        """
        _, width = shape(rows)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this network expects {self.d_model}"
            )
        projected = matmul(rows, self.w_in)
        return [[self.activation(value) for value in row] for row in projected]

    def forward(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Project up, activate, project back down.

        Raises:
            ValueError: if rows are not d_model wide.

        Complexity: O(n * d_model * d_hidden) multiply-adds, twice.
        """
        return matmul(self.hidden(rows), self.w_out)

    def parameters(self) -> ParameterCount:
        """Parameter count for a block using this network."""
        return parameter_count(self.d_model, self.d_hidden, gated=False)


class GatedFeedForward:
    """The three-matrix gated network: two projections multiplied together.

    h = activation(x W_gate) * (x W_in), element-wise, then h W_out. With
    `silu` as the activation this is the SwiGLU arrangement; with `gelu` it
    is GeGLU. The activation applies to the gate only, which is what makes
    the other projection a value the gate scales rather than a second
    nonlinear feature.

    Attributes:
        w_gate: (d_model, d_hidden), the projection the activation sees.
        w_in: (d_model, d_hidden), the projection the gate scales.
        w_out: (d_hidden, d_model), whose rows are the output directions.
    """

    def __init__(
        self,
        d_model: int,
        d_hidden: int,
        rng: random.Random,
        activation: str = "silu",
    ):
        """Allocate all three projections deterministically from `rng`.

        Raises:
            ValueError: if either width is not positive, or the activation
                name is not recognised.
        """
        if d_model <= 0 or d_hidden <= 0:
            raise ValueError(
                f"GatedFeedForward needs positive dims, got "
                f"({d_model}, {d_hidden})"
            )
        self.d_model = d_model
        self.d_hidden = d_hidden
        self.activation_name = activation
        self.activation = resolve_activation(activation)
        self.w_gate = glorot_matrix(d_model, d_hidden, rng)
        self.w_in = glorot_matrix(d_model, d_hidden, rng)
        self.w_out = glorot_matrix(d_hidden, d_model, rng)

    def hidden(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Return the gated hidden layer, (n, d_hidden).

        Raises:
            ValueError: if rows are not d_model wide.
        """
        _, width = shape(rows)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this network expects {self.d_model}"
            )
        gate = matmul(rows, self.w_gate)
        value = matmul(rows, self.w_in)
        return [
            [self.activation(gate[r][c]) * value[r][c] for c in range(self.d_hidden)]
            for r in range(len(rows))
        ]

    def forward(self, rows: Sequence[Sequence[float]]) -> Matrix:
        """Gate, multiply, project back down.

        Raises:
            ValueError: if rows are not d_model wide.

        Complexity: O(n * d_model * d_hidden) multiply-adds, three times.
        """
        return matmul(self.hidden(rows), self.w_out)

    def parameters(self) -> ParameterCount:
        """Parameter count for a block using this network."""
        return parameter_count(self.d_model, self.d_hidden, gated=True)


def decompose_output(
    hidden_row: Sequence[float], w_out: Sequence[Sequence[float]]
) -> Matrix:
    """Return each hidden unit's contribution to one output row, separately.

    The feed-forward output for a position is a weighted sum of the rows of
    W_out. This returns the terms of that sum, one per hidden unit, so the
    sum can be checked against the matrix multiply and the largest terms can
    be named.

    Args:
        hidden_row: length d_hidden, one position's post-activation values.
        w_out: (d_hidden, d_model).

    Returns:
        A (d_hidden, d_model) matrix whose row j is hidden_row[j] times
        row j of w_out. Summing its rows gives the output for that position.

    Raises:
        ValueError: if the hidden width does not match w_out's row count.

    Complexity: O(d_hidden * d_model).
    """
    rows, _ = shape(w_out)
    if len(hidden_row) != rows:
        raise ValueError(
            f"hidden row is {len(hidden_row)} wide but w_out has {rows} rows"
        )
    return [
        [weight * value for value in w_out[index]]
        for index, weight in enumerate(hidden_row)
    ]


def dominant_units(
    hidden_row: Sequence[float], w_out: Sequence[Sequence[float]], count: int
) -> List[Tuple[int, float]]:
    """The `count` hidden units contributing most to one output row.

    Contribution is measured as the Euclidean length of that unit's term in
    the decomposition, which is the activation times the length of its
    output row. Ranking by activation alone would be wrong whenever the
    output rows differ in length.

    Args:
        hidden_row: one position's post-activation values.
        w_out: (d_hidden, d_model).
        count: how many to return, at least 1.

    Returns:
        A list of (unit index, contribution length), largest first.

    Raises:
        ValueError: if count is below 1 or exceeds the hidden width, or if
            the widths disagree.

    Complexity: O(d_hidden * d_model + d_hidden log d_hidden).
    """
    terms = decompose_output(hidden_row, w_out)
    if not 1 <= count <= len(terms):
        raise ValueError(
            f"count must be between 1 and {len(terms)}, got {count}"
        )
    lengths = [
        (index, math.sqrt(sum(value * value for value in term)))
        for index, term in enumerate(terms)
    ]
    lengths.sort(key=lambda pair: (-pair[1], pair[0]))
    return lengths[:count]
