"""Grouped-query attention: one dial between multi-head and multi-query.

Standard library only, built on `lib/linalg.py` and `lib/attention.py`.

Multi-head attention gives every query head its own key and value
projection. During incremental decoding those keys and values have to be
kept for every position generated so far, and Shazeer identified the cost
that creates: incremental inference "is often slow, due to the
memory-bandwidth cost of repeatedly loading the large 'keys' and 'values'
tensors", proposing multi-query attention, "where the keys and values are
shared across all of the different attention 'heads'" (arXiv:1911.02150).
One key-value head instead of H of them.

Ainslie et al. then put a dial between the two ends, introducing
"grouped-query attention (GQA), a generalization of multi-query attention
which uses an intermediate (more than one, less than number of query heads)
number of key-value heads", and reporting that "uptrained GQA achieves
quality close to multi-head attention with comparable speed to MQA"
(arXiv:2305.13245). Mistral 7B pairs it with a sliding window, "grouped-query
attention (GQA) for faster inference, coupled with sliding window attention
(SWA)" (arXiv:2310.06825).

So this module has one class with one extra parameter. Set `num_kv_heads`
equal to `num_query_heads` and it is multi-head attention. Set it to 1 and
it is multi-query attention. Anything between is GQA, and every query head
in a group reads the same keys and the same values.

    query heads   8 8 8 8 8 8 8 8
    kv heads      \___/ \___/ \___/ \___/      num_kv_heads = 4, group = 2

WHAT CHANGES AND WHAT DOES NOT. The query projections are untouched, so
the parameter count barely moves and the output width is identical. What
shrinks is the cache: `kv_cache_bytes` is linear in `num_kv_heads`, so
going from 8 key-value heads to 1 divides the cache by 8 exactly. That
part is arithmetic and this module computes it.

What it cannot tell you is whether the model is as good afterwards. The
paper's answer to that is uptraining, which needs gradients this repository
does not have. What is measurable here without training is how much the
attention patterns of different query heads resemble each other once they
are forced to read the same keys, and `head_pattern_similarity` measures
exactly that. `experiments/week-04/gqa_cache.py` reports both and is
explicit about which is arithmetic and which is a measurement on untrained
weights.

Nothing here is trained. Weights come from a seed.
"""

import math
import random
from typing import List, NamedTuple, Optional, Sequence, Tuple

from lib.attention import glorot_matrix, scaled_dot_product_attention
from lib.linalg import (
    Matrix,
    hstack,
    matmul,
    matrix_rank,
    null_space_basis,
    shape,
)

# Two tensors are cached per position per key-value head: the key and the
# value. Nothing else in attention is per-position state.
TENSORS_CACHED = 2

# Half precision, the usual storage format for a served KV cache.
DEFAULT_BYTES_PER_ELEMENT = 2


class CacheSize(NamedTuple):
    """KV cache arithmetic for one stated configuration.

    Attributes:
        bytes_per_token_per_layer: the unit everything else is built from.
        bytes_per_token: that times the layer count.
        total_bytes: that times the sequence length.
    """

    bytes_per_token_per_layer: int
    bytes_per_token: int
    total_bytes: int

    @property
    def gibibytes(self) -> float:
        """Total cache in GiB, which is the unit a capacity limit uses."""
        return self.total_bytes / (1024 ** 3)


def kv_cache_bytes(
    num_kv_heads: int,
    d_head: int,
    num_layers: int,
    sequence_length: int,
    bytes_per_element: int = DEFAULT_BYTES_PER_ELEMENT,
) -> CacheSize:
    """Size the key-value cache for one sequence.

    Args:
        num_kv_heads: key-value heads per layer. This is the only term that
            grouping changes, which is why the saving is exactly linear.
        d_head: width of one head.
        num_layers: blocks in the model.
        sequence_length: positions held in the cache.
        bytes_per_element: storage width, 2 for half precision.

    Returns:
        A CacheSize. The arithmetic is
        2 * num_kv_heads * d_head * num_layers * sequence_length *
        bytes_per_element, where the 2 is the key and the value.

        Query projections, weights and activations are excluded. This
        counts the cache and nothing else.

    Raises:
        ValueError: if any argument is not positive.

    Complexity: O(1).
    """
    for name, value in (
        ("num_kv_heads", num_kv_heads),
        ("d_head", d_head),
        ("num_layers", num_layers),
        ("sequence_length", sequence_length),
        ("bytes_per_element", bytes_per_element),
    ):
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
    per_token_per_layer = (
        TENSORS_CACHED * num_kv_heads * d_head * bytes_per_element
    )
    per_token = per_token_per_layer * num_layers
    return CacheSize(
        bytes_per_token_per_layer=per_token_per_layer,
        bytes_per_token=per_token,
        total_bytes=per_token * sequence_length,
    )


def group_assignment(num_query_heads: int, num_kv_heads: int) -> List[int]:
    """Map each query head to the key-value head it reads.

    Query heads are assigned to groups in contiguous blocks, which is the
    arrangement the name describes: heads 0 and 1 share key-value head 0,
    heads 2 and 3 share key-value head 1, and so on.

    Args:
        num_query_heads: total query heads.
        num_kv_heads: key-value heads, must divide num_query_heads.

    Returns:
        A list of length num_query_heads whose entry h is the index of the
        key-value head that query head h reads.

    Raises:
        ValueError: if either count is below 1, or if num_kv_heads does not
            divide num_query_heads. An uneven split would give some groups
            more heads than others, which is a different architecture and
            should not be reachable by accident.
    """
    if num_query_heads < 1:
        raise ValueError(
            f"num_query_heads must be at least 1, got {num_query_heads}"
        )
    if num_kv_heads < 1:
        raise ValueError(f"num_kv_heads must be at least 1, got {num_kv_heads}")
    if num_kv_heads > num_query_heads:
        raise ValueError(
            f"num_kv_heads {num_kv_heads} exceeds num_query_heads "
            f"{num_query_heads}: there would be keys no query ever reads"
        )
    if num_query_heads % num_kv_heads != 0:
        raise ValueError(
            f"num_kv_heads {num_kv_heads} does not divide num_query_heads "
            f"{num_query_heads}: the groups would be uneven"
        )
    group_size = num_query_heads // num_kv_heads
    return [head // group_size for head in range(num_query_heads)]


class GroupedQueryAttention:
    """Attention with a configurable number of key-value heads.

    Attributes:
        num_query_heads: query heads, unchanged by grouping.
        num_kv_heads: key-value heads. Equal to num_query_heads for
            multi-head attention, 1 for multi-query attention.
        group_size: query heads per key-value head.
        groups: per-query-head index of the key-value head it reads.
        w_query: one (d_model, d_head) projection per query head.
        w_key: one (d_model, d_head) projection per key-value head.
        w_value: one (d_model, d_head) projection per key-value head.
        w_output: (num_query_heads * d_head, d_model).
    """

    def __init__(
        self,
        d_model: int,
        num_query_heads: int,
        num_kv_heads: int,
        seed: int,
    ):
        """Build the projections deterministically from `seed`.

        The query projections are drawn first and in query-head order, so
        two instances that differ only in `num_kv_heads` hold identical
        query weights. That is what makes a comparison between the three
        arrangements a comparison of the arrangement.

        Raises:
            ValueError: if d_model is not divisible by num_query_heads, or
                if the head counts are invalid. See `group_assignment`.
        """
        if d_model % num_query_heads != 0:
            raise ValueError(
                f"d_model {d_model} is not divisible by num_query_heads "
                f"{num_query_heads}"
            )
        self.groups = group_assignment(num_query_heads, num_kv_heads)
        self.d_model = d_model
        self.num_query_heads = num_query_heads
        self.num_kv_heads = num_kv_heads
        self.group_size = num_query_heads // num_kv_heads
        self.d_head = d_model // num_query_heads
        rng = random.Random(seed)
        self.w_query = [
            glorot_matrix(d_model, self.d_head, rng)
            for _ in range(num_query_heads)
        ]
        self.w_key = [
            glorot_matrix(d_model, self.d_head, rng) for _ in range(num_kv_heads)
        ]
        self.w_value = [
            glorot_matrix(d_model, self.d_head, rng) for _ in range(num_kv_heads)
        ]
        self.w_output = glorot_matrix(num_query_heads * self.d_head, d_model, rng)

    def cache_size(
        self,
        num_layers: int,
        sequence_length: int,
        bytes_per_element: int = DEFAULT_BYTES_PER_ELEMENT,
    ) -> CacheSize:
        """KV cache for a model built from blocks like this one."""
        return kv_cache_bytes(
            self.num_kv_heads,
            self.d_head,
            num_layers,
            sequence_length,
            bytes_per_element,
        )

    def forward(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[Matrix, List[Matrix]]:
        """Run every query head against its group's keys and values.

        Args:
            x: (n, d_model) input sequence.
            mask: optional additive (n, n) mask shared by every head.

        Returns:
            (output, weights_per_query_head): output is (n, d_model) and
            the weight list has one (n, n) matrix per QUERY head, not per
            key-value head, because each query head still produces its own
            distribution over positions even when the keys are shared.

        Raises:
            ValueError: if x is not d_model wide.

        Complexity: O(n^2 * d_model) for the scores, unchanged by grouping.
        Grouping saves cache bytes and the bandwidth to reload them, and
        saves no arithmetic at all in this formulation.
        """
        _, width = shape(x)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this layer expects {self.d_model}"
            )
        keys = [matmul(x, projection) for projection in self.w_key]
        values = [matmul(x, projection) for projection in self.w_value]
        outputs: List[Matrix] = []
        weights_per_head: List[Matrix] = []
        for head in range(self.num_query_heads):
            group = self.groups[head]
            queries = matmul(x, self.w_query[head])
            attended, weights = scaled_dot_product_attention(
                queries, keys[group], values[group], mask
            )
            outputs.append(attended)
            weights_per_head.append(weights)
        return matmul(hstack(outputs), self.w_output), weights_per_head


def head_pattern_similarity(weights_per_head: Sequence[Sequence[Sequence[float]]]) -> float:
    """Mean pairwise similarity of the attention patterns across heads.

    Each head produces an (n, n) matrix of distributions, one per query
    position. This flattens each head's matrix and takes the mean cosine
    over every unordered pair of heads. Attention weights are non-negative
    and each row sums to 1, so the value is always positive; what matters is
    whether forcing heads to share keys pushes it up.

    Args:
        weights_per_head: one (n, n) weight matrix per head, at least two.

    Returns:
        The mean pairwise cosine, in (0.0, 1.0].

    Raises:
        ValueError: if fewer than two heads are given, or the shapes differ.

    Complexity: O(H^2 * n^2).
    """
    if len(weights_per_head) < 2:
        raise ValueError(
            "head_pattern_similarity needs at least two heads to compare"
        )
    shapes = {shape(head) for head in weights_per_head}
    if len(shapes) != 1:
        raise ValueError(f"heads disagree on shape: {sorted(shapes)}")
    flattened = [
        [float(value) for row in head for value in row]
        for head in weights_per_head
    ]
    norms = [math.sqrt(sum(value * value for value in head)) for head in flattened]
    total = 0.0
    pairs = 0
    for left in range(len(flattened)):
        for right in range(left + 1, len(flattened)):
            if norms[left] == 0.0 or norms[right] == 0.0:
                raise ValueError(
                    f"head {left if norms[left] == 0.0 else right} has "
                    "all-zero attention weights, which softmax cannot produce"
                )
            dot = sum(
                a * b for a, b in zip(flattened[left], flattened[right])
            )
            total += dot / (norms[left] * norms[right])
            pairs += 1
    return total / pairs


def distinct_key_spaces(layer: GroupedQueryAttention) -> int:
    """How many different key projections the layer holds.

    Present so an article can state the collapse as a count rather than an
    adjective: multi-head attention has one key space per query head,
    multi-query attention has one in total.
    """
    return layer.num_kv_heads


def key_subspace_rank(layer: GroupedQueryAttention) -> int:
    """How many dimensions of the residual stream the keys can read.

    Put every key projection side by side and take the rank. A layer with
    K key-value heads of width d_head can distinguish at most K * d_head
    independent directions of the incoming stream when it decides where to
    look, capped by the stream's own width.

    This is the structural cost of grouping, and it is separate from the
    memory saving. Multi-head attention with H heads of width d_model / H
    reads the whole stream. Multi-query attention reads a d_head-wide slice
    of it, whatever the stream's width, so most of what a position carries
    is invisible to the routing decision. `blind_directions` produces the
    directions that are invisible, so the claim can be demonstrated rather
    than argued.

    Returns:
        The rank, between 1 and d_model.
    """
    return matrix_rank(hstack(layer.w_key))


def blind_directions(layer: GroupedQueryAttention) -> Matrix:
    """Residual-stream directions every key projection sends to zero.

    A position moved along one of these directions produces exactly the
    same key in every head, so no other position's decision about how much
    to attend to it changes at all. The value that position contributes
    does change, because W_v is a different matrix. The routing is blind;
    the payload is not.

    Returns:
        A basis for the blind subspace, empty when the key projections
        already span the full stream, which is the multi-head case.
    """
    return null_space_basis(hstack(layer.w_key))
