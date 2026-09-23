"""Multi-head latent attention: cache one narrow vector, rebuild the rest.

Standard library only, built on `lib/linalg.py`, `lib/attention.py` and
`lib/rope.py`.

Grouped-query attention shrinks the key-value cache by giving several query
heads one key-value head to share. Multi-head latent attention shrinks it a
different way: keep every head distinct, and cache a single compressed
vector per position from which each head's key and value can be rebuilt.
DeepSeek-V2 introduced it, reporting that "MLA guarantees efficient
inference through significantly compressing the Key-Value (KV) cache into a
latent vector", alongside a 93.3% reduction in that cache and 5.76 times
the maximum generation throughput against their previous model
(arXiv:2405.04434). The same attention carried forward into DeepSeek-V3,
which "adopts Multi-head Latent Attention (MLA) and DeepSeekMoE
architectures, which were thoroughly validated in DeepSeek-V2"
(arXiv:2412.19437).

THE SHAPE. One down-projection produces the cached latent, and per-head
up-projections rebuild keys and values from it:

    c_j    = x_j W_dkv                     cached, d_latent wide
    k_j^h  = c_j W_uk^h                    rebuilt, never cached
    v_j^h  = c_j W_uv^h                    rebuilt, never cached
    q_i^h  = x_i W_q^h

Rebuilding on every step would trade memory for arithmetic, which is a poor
trade when the arithmetic is the thing already saturating. The move that
makes it work is that the rebuild never has to happen:

    q_i^h . k_j^h = (x_i W_q^h) . (c_j W_uk^h) = (x_i W_q^h W_uk^h^T) . c_j

The bracket on the right is a matrix that depends on the head and on
nothing else, so it can be computed once and folded into the query
projection. `absorbed_matrix` returns it. After that the score is a dot
product between a projected query and the cached latent directly, and no
key is ever materialised. The value side folds the same way, because
attention is linear in the values:

    sum_j w_ij v_j^h = sum_j w_ij (c_j W_uv^h) = (sum_j w_ij c_j) W_uv^h

`forward_explicit` rebuilds everything, `forward_absorbed` folds, and
`tests/test_mla.py` asserts they agree to machine precision. That equality
is the whole design, so it is checked rather than described.

WHERE IT BREAKS, AND THE FIX. Rotary position embedding rotates queries and
keys by their position. Put a rotation between the two halves of the
absorbed product and the head's matrix stops being position-independent:

    rot(q_i, i) . rot(k_j, j) = q_i R_(j-i) W_uk^h^T c_j

`rotated_absorbed_matrix` builds that per-offset matrix, and it is a
different matrix for every relative distance, so folding would need one per
distance instead of one per head. The published answer is a decoupled
channel: a few extra dimensions that carry position, cached once for all
heads beside the latent, kept out of the absorbed product. Set `d_rope`
above zero and this module implements that split, so the failure and the
repair can both be run.

Nothing here is trained. Weights come from a seed.
"""

import math
import random
from typing import List, NamedTuple, Optional, Sequence, Tuple

from lib.attention import glorot_matrix
from lib.linalg import Matrix, hstack, matmul, shape, softmax_rows, transpose
from lib.rope import DEFAULT_BASE, rotate

# Half precision, the usual storage format for a served cache.
DEFAULT_BYTES_PER_ELEMENT = 2


class CacheComparison(NamedTuple):
    """Per-token per-layer cache for two attention designs.

    Attributes:
        standard_bytes: multi-head attention, which stores a key and a
            value for every head.
        latent_bytes: multi-head latent attention, which stores the latent
            and, when present, the shared positional channel.
    """

    standard_bytes: int
    latent_bytes: int

    @property
    def reduction(self) -> float:
        """Fraction of the standard cache that latent attention removes."""
        return 1.0 - self.latent_bytes / self.standard_bytes

    @property
    def factor(self) -> float:
        """How many times smaller the latent cache is."""
        return self.standard_bytes / self.latent_bytes


def cache_comparison(
    num_heads: int,
    d_head: int,
    d_latent: int,
    d_rope: int = 0,
    bytes_per_element: int = DEFAULT_BYTES_PER_ELEMENT,
) -> CacheComparison:
    """Compare per-token per-layer cache for standard and latent attention.

    Args:
        num_heads: attention heads.
        d_head: width of one head.
        d_latent: width of the cached latent.
        d_rope: width of the shared positional channel, 0 if absent.
        bytes_per_element: storage width.

    Returns:
        A CacheComparison. Standard attention stores 2 * num_heads * d_head
        values; latent attention stores d_latent + d_rope, both shared
        across every head.

    Raises:
        ValueError: if any width is not positive, or d_rope is negative, or
            d_rope is odd. A rotation acts on pairs of dimensions, so an
            odd positional channel has a dimension with no partner.
    """
    for name, value in (
        ("num_heads", num_heads),
        ("d_head", d_head),
        ("d_latent", d_latent),
        ("bytes_per_element", bytes_per_element),
    ):
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
    if d_rope < 0:
        raise ValueError(f"d_rope cannot be negative, got {d_rope}")
    if d_rope % 2 != 0:
        raise ValueError(f"d_rope must be even, got {d_rope}")
    return CacheComparison(
        standard_bytes=2 * num_heads * d_head * bytes_per_element,
        latent_bytes=(d_latent + d_rope) * bytes_per_element,
    )


def rotate_rows(matrix: Sequence[Sequence[float]], position: int) -> Matrix:
    """Rotate every row of a matrix by the SAME position.

    `lib.rope.apply_rope` rotates row j by position j, which is what a
    sequence needs. Folding a rotation into a projection needs the other
    thing: one shared angle applied to every row, because the rows here are
    input dimensions rather than positions.

    Raises:
        ValueError: if the matrix is empty, ragged, or of odd width.
    """
    _, width = shape(matrix)
    if width % 2 != 0:
        raise ValueError(f"rotate_rows needs an even width, got {width}")
    return [rotate(row, position) for row in matrix]


class MultiHeadLatentAttention:
    """Attention whose cache is one latent vector per position.

    Attributes:
        d_latent: width of the cached latent.
        d_rope: width of the shared positional channel, 0 when position is
            not encoded here.
        w_down_kv: (d_model, d_latent), produces the cached latent.
        w_up_key: one (d_latent, d_head) per head.
        w_up_value: one (d_latent, d_head) per head.
        w_query: one (d_model, d_head) per head, the content query.
        w_query_rope: one (d_model, d_rope) per head, present when d_rope
            is above zero.
        w_key_rope: (d_model, d_rope), shared by every head, present when
            d_rope is above zero. Shared because its output is cached once
            per position rather than once per head.
        w_output: (num_heads * d_head, d_model).
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        d_head: int,
        d_latent: int,
        seed: int,
        d_rope: int = 0,
    ):
        """Build every projection deterministically from `seed`.

        Args:
            d_model: model width.
            num_heads: attention heads.
            d_head: width of one head's content channel.
            d_latent: width of the cached latent. Compression only happens
                when this is below 2 * num_heads * d_head.
            seed: seeds a random.Random so every weight is reproducible.
            d_rope: width of the decoupled positional channel. Zero
                disables position entirely, which is the configuration the
                absorption identity is cleanest in.

        Raises:
            ValueError: if any width is not positive, or d_rope is negative
                or odd.
        """
        for name, value in (
            ("d_model", d_model),
            ("num_heads", num_heads),
            ("d_head", d_head),
            ("d_latent", d_latent),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
        if d_rope < 0:
            raise ValueError(f"d_rope cannot be negative, got {d_rope}")
        if d_rope % 2 != 0:
            raise ValueError(f"d_rope must be even, got {d_rope}")
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_head = d_head
        self.d_latent = d_latent
        self.d_rope = d_rope
        self.scale = 1.0 / math.sqrt(d_head + d_rope)
        rng = random.Random(seed)
        self.w_down_kv = glorot_matrix(d_model, d_latent, rng)
        self.w_up_key = [
            glorot_matrix(d_latent, d_head, rng) for _ in range(num_heads)
        ]
        self.w_up_value = [
            glorot_matrix(d_latent, d_head, rng) for _ in range(num_heads)
        ]
        self.w_query = [
            glorot_matrix(d_model, d_head, rng) for _ in range(num_heads)
        ]
        if d_rope:
            self.w_query_rope = [
                glorot_matrix(d_model, d_rope, rng) for _ in range(num_heads)
            ]
            self.w_key_rope = glorot_matrix(d_model, d_rope, rng)
        else:
            self.w_query_rope = []
            self.w_key_rope = []
        self.w_output = glorot_matrix(num_heads * d_head, d_model, rng)

    def latents(self, x: Sequence[Sequence[float]]) -> Matrix:
        """Return the cached latent for every position, (n, d_latent).

        This, plus `positional_keys` when d_rope is set, is the entire
        per-position state a served model would hold. Everything else is
        rebuilt or folded away.

        Raises:
            ValueError: if x is not d_model wide.
        """
        self._check_width(x)
        return matmul(x, self.w_down_kv)

    def positional_keys(
        self, x: Sequence[Sequence[float]], offset: int = 0
    ) -> Matrix:
        """Return the shared rotated positional key for every position.

        Shared across heads, which is why it is cheap to cache: one d_rope
        vector per position rather than one per head per position.

        Args:
            x: (n, d_model) input.
            offset: position of the first row, for continuing a cache.

        Returns:
            An (n, d_rope) matrix, or an empty list when d_rope is 0.

        Raises:
            ValueError: if x is not d_model wide.
        """
        self._check_width(x)
        if not self.d_rope:
            return []
        projected = matmul(x, self.w_key_rope)
        return [
            rotate(row, offset + index) for index, row in enumerate(projected)
        ]

    def cache_widths(self) -> Tuple[int, int]:
        """(standard values per token, latent values per token), per layer.

        Returned as counts rather than bytes so the comparison does not
        depend on a storage format.
        """
        return (2 * self.num_heads * self.d_head, self.d_latent + self.d_rope)

    def absorbed_matrix(self, head: int) -> Matrix:
        """W_q^h times W_uk^h transposed: the fold that removes the key.

        Returns:
            A (d_model, d_latent) matrix. Multiply an input row by it and
            the result dots directly against a cached latent to give the
            content score, with no key ever built.

        Raises:
            ValueError: if the head index is out of range.
        """
        self._check_head(head)
        return matmul(self.w_query[head], transpose(self.w_up_key[head]))

    def rotated_absorbed_matrix(self, head: int, offset: int) -> Matrix:
        """The absorbed matrix for one relative offset, under rotation.

        Present to show why folding and rotary position embedding do not
        combine. Rotating the query by i and the key by j leaves a rotation
        by (j - i) sitting between the two halves of the fold, so the matrix
        depends on the distance between the positions and one per head is no
        longer enough.

        Args:
            head: which head.
            offset: the relative distance j - i.

        Returns:
            A (d_model, d_latent) matrix, valid only at that offset.

        Raises:
            ValueError: if the head index is out of range, or if d_head is
                odd, since a rotation acts on pairs.
        """
        self._check_head(head)
        rotated_query = rotate_rows(self.w_query[head], offset)
        return matmul(rotated_query, transpose(self.w_up_key[head]))

    def content_scores_explicit(
        self, x: Sequence[Sequence[float]], head: int, rotate_heads: bool = False
    ) -> Matrix:
        """Raw content scores for one head, built the slow way.

        Args:
            x: (n, d_model) input.
            head: which head.
            rotate_heads: when True, rotate the whole query and key by
                their positions, which is what a model does when it applies
                rotary position embedding to the head vectors rather than
                to a decoupled channel. This is the configuration that
                breaks the fold, and it exists here so the break can be
                measured.

        Returns:
            An (n, n) matrix of unscaled, unmasked scores.

        Raises:
            ValueError: if the head index is out of range, if x is the
                wrong width, or if `rotate_heads` is asked for on an odd
                head width.
        """
        self._check_head(head)
        latents = self.latents(x)
        keys = matmul(latents, self.w_up_key[head])
        queries = matmul(x, self.w_query[head])
        if rotate_heads:
            if self.d_head % 2 != 0:
                raise ValueError(
                    f"rotating a head needs an even d_head, got {self.d_head}"
                )
            queries = [rotate(row, index) for index, row in enumerate(queries)]
            keys = [rotate(row, index) for index, row in enumerate(keys)]
        return matmul(queries, transpose(keys))

    def content_scores_absorbed(
        self,
        x: Sequence[Sequence[float]],
        head: int,
        offset: Optional[int] = None,
    ) -> Matrix:
        """Raw content scores for one head, through a folded matrix.

        Args:
            x: (n, d_model) input.
            head: which head.
            offset: None uses the position-independent fold, which matches
                `content_scores_explicit(..., rotate_heads=False)` exactly.
                An integer uses the fold for that relative distance, which
                matches the rotated scores only on the diagonal band where
                i - j equals it. Supplying one offset for a whole matrix is
                the mistake this argument exists to demonstrate.

        Returns:
            An (n, n) matrix of unscaled, unmasked scores.

        Raises:
            ValueError: if the head index is out of range or x is the wrong
                width.
        """
        self._check_head(head)
        latents = self.latents(x)
        if offset is None:
            folded = matmul(x, self.absorbed_matrix(head))
        else:
            folded = matmul(x, self.rotated_absorbed_matrix(head, offset))
        return matmul(folded, transpose(latents))

    def content_scores_absorbed_per_offset(
        self, x: Sequence[Sequence[float]], head: int
    ) -> Matrix:
        """Rotated scores rebuilt correctly, one folded matrix per distance.

        This reproduces `content_scores_explicit(..., rotate_heads=True)`
        exactly, and it is the reason the decoupled channel exists: getting
        the right answer here costs one absorbed matrix per relative
        distance in the sequence, so the fold stops being a fold.

        Raises:
            ValueError: if the head index is out of range or x is the wrong
                width.

        Complexity: O(n * d_model * d_head * d_latent) for the matrices
        alone, against O(d_model * d_head * d_latent) for the single fold.
        """
        self._check_head(head)
        latents = self.latents(x)
        rows, _ = shape(x)
        folds = {
            offset: matmul(x, self.rotated_absorbed_matrix(head, offset))
            for offset in range(rows)
        }
        return [
            [
                sum(
                    folds[i - j][i][unit] * latents[j][unit]
                    for unit in range(self.d_latent)
                )
                if i >= j
                else 0.0
                for j in range(rows)
            ]
            for i in range(rows)
        ]

    def forward_explicit(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[Matrix, List[Matrix]]:
        """Rebuild every key and value from the latent, then attend normally.

        This is the reference implementation. It is what the design is
        defined to compute, and it is deliberately the slow way.

        Args:
            x: (n, d_model) input.
            mask: optional additive (n, n) mask.

        Returns:
            (output, weights_per_head).

        Raises:
            ValueError: on any shape disagreement.

        Complexity: O(n^2 * (d_head + d_rope) + n * d_latent * d_head * H).
        """
        latents = self.latents(x)
        position_keys = self.positional_keys(x)
        outputs: List[Matrix] = []
        weights_per_head: List[Matrix] = []
        for head in range(self.num_heads):
            keys = matmul(latents, self.w_up_key[head])
            values = matmul(latents, self.w_up_value[head])
            queries = matmul(x, self.w_query[head])
            if self.d_rope:
                query_rope = matmul(x, self.w_query_rope[head])
                queries = hstack(
                    [
                        queries,
                        [
                            rotate(row, index)
                            for index, row in enumerate(query_rope)
                        ],
                    ]
                )
                keys = hstack([keys, position_keys])
            scores = matmul(queries, transpose(keys))
            weights = self._weights(scores, mask)
            outputs.append(matmul(weights, values))
            weights_per_head.append(weights)
        return matmul(hstack(outputs), self.w_output), weights_per_head

    def forward_absorbed(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[Matrix, List[Matrix]]:
        """Score against the cached latent directly, building no key at all.

        The content half folds W_uk into the query projection. The value
        half attends over the latents and up-projects once at the end, which
        is valid because attention is a linear combination of the values.
        When d_rope is set, the positional half is computed separately on
        the shared channel and added to the scores.

        Args:
            x: (n, d_model) input.
            mask: optional additive (n, n) mask.

        Returns:
            (output, weights_per_head), numerically equal to
            `forward_explicit` up to floating-point reassociation.

        Raises:
            ValueError: on any shape disagreement.

        Complexity: O(n^2 * (d_latent + d_rope)) for the scores, plus the
        one-off fold. The keys never exist.
        """
        latents = self.latents(x)
        position_keys = self.positional_keys(x)
        latents_t = transpose(latents)
        outputs: List[Matrix] = []
        weights_per_head: List[Matrix] = []
        for head in range(self.num_heads):
            folded = matmul(x, self.absorbed_matrix(head))
            scores = matmul(folded, latents_t)
            if self.d_rope:
                query_rope = matmul(x, self.w_query_rope[head])
                rotated = [
                    rotate(row, index) for index, row in enumerate(query_rope)
                ]
                positional = matmul(rotated, transpose(position_keys))
                scores = [
                    [scores[r][c] + positional[r][c] for c in range(len(row))]
                    for r, row in enumerate(scores)
                ]
            weights = self._weights(scores, mask)
            pooled = matmul(weights, latents)
            outputs.append(matmul(pooled, self.w_up_value[head]))
            weights_per_head.append(weights)
        return matmul(hstack(outputs), self.w_output), weights_per_head

    def _weights(
        self,
        scores: Matrix,
        mask: Optional[Sequence[Sequence[float]]],
    ) -> Matrix:
        """Scale, mask and normalise raw scores into attention weights."""
        scaled = [[value * self.scale for value in row] for row in scores]
        if mask is not None:
            mask_shape = shape(mask)
            score_shape = shape(scaled)
            if mask_shape != score_shape:
                raise ValueError(
                    f"mask is {mask_shape} but scores are {score_shape}"
                )
            scaled = [
                [scaled[r][c] + mask[r][c] for c in range(score_shape[1])]
                for r in range(score_shape[0])
            ]
        return softmax_rows(scaled)

    def _check_width(self, x: Sequence[Sequence[float]]) -> None:
        """Reject an input of the wrong width, naming both widths."""
        _, width = shape(x)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this layer expects {self.d_model}"
            )

    def _check_head(self, head: int) -> None:
        """Reject an out-of-range head index."""
        if not 0 <= head < self.num_heads:
            raise ValueError(
                f"head {head} is out of range for {self.num_heads} heads"
            )


def rotary_offsets_needed(sequence_length: int) -> int:
    """Distinct relative offsets a causal sequence of this length contains.

    The count of absorbed matrices a folded implementation would need if
    rotation were applied to the whole head instead of to a decoupled
    channel. One per head becomes one per head per offset, which is the
    reason the decoupled design exists.

    Raises:
        ValueError: if the length is not positive.
    """
    if sequence_length <= 0:
        raise ValueError(
            f"sequence_length must be positive, got {sequence_length}"
        )
    return sequence_length


def max_abs_difference(
    left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
) -> float:
    """Largest absolute element-wise difference between two matrices.

    Raises:
        ValueError: if the shapes differ.
    """
    left_shape = shape(left)
    right_shape = shape(right)
    if left_shape != right_shape:
        raise ValueError(f"cannot compare {left_shape} with {right_shape}")
    rows, cols = left_shape
    return max(
        abs(left[r][c] - right[r][c]) for r in range(rows) for c in range(cols)
    )


def rope_base() -> float:
    """The rotation rate constant this module inherits from `lib/rope.py`."""
    return DEFAULT_BASE
