"""Sparse attention: fixed windows, attention sinks, and learned selection.

Standard library only, built on `lib/linalg.py` and `lib/attention.py`.

Full causal attention lets every position read every earlier position, and
costs a number of scores that grows with the square of the sequence. Two
families of answer exist, and they fail in different ways.

FIXED PATTERNS decide in advance which pairs are allowed. Longformer
introduced "an attention mechanism that scales linearly with sequence
length", combining "a local windowed attention with a task motivated global
attention" (arXiv:2004.05150). Mistral 7B pairs the same idea with grouped
queries, using "sliding window attention (SWA) to effectively handle
sequences of arbitrary length with a reduced inference cost"
(arXiv:2310.06825).

The claim that a window handles arbitrary length rests on stacking: a
position reads its window, and the positions in that window have already
read theirs, so information travels one window per layer. `max_reach`
computes how far that actually gets by taking boolean powers of the mask
rather than by trusting the formula, and `window_reach_formula` gives the
formula so the two can be compared. Reachability is a statement about the
connectivity graph, and `experiments/week-04/window_reach.py` measures what
survives the journey, which is a different question with a different answer.

LEARNED SELECTION decides per query which positions are worth reading.
DeepSeek's own natively trainable design "employs a dynamic hierarchical
sparse strategy, combining coarse-grained token compression with
fine-grained token selection" (arXiv:2502.11089). The deployed descendant
of that line is described in the surrounding literature as scoring every
preceding token with a cheap indexer and keeping the best few: token-level
sparse attention "makes the downstream attention efficient but shifts the
bottleneck to the indexer that feeds it. To select the top-k tokens for
each query, the indexer must still score every preceding token, incurring a
cost of O(L^2) per layer for a sequence of length L" (arXiv:2607.24593).
Another treatment puts the same point as the indexer scoring "every prefix
token", using "many query heads (for example, 64 on DeepSeek-V3.2) that
share the same selected token set", which is "precisely what makes the
indexer the dominant cost on long contexts" (arXiv:2605.07363).

`CheapIndexer` is a small, deliberately weak scorer in that spirit, and
`selection_recall` and `attention_mass_captured` measure the two things
that decide whether selection works: does the cheap scorer pick the same
positions the real scores would, and does the set it picks hold most of
the attention mass.

Nothing here is trained. Weights come from a seed.
"""

import math
import random
from typing import List, Optional, Sequence, Set, Tuple

from lib.attention import glorot_matrix
from lib.linalg import Matrix, matmul, shape, transpose

NEG_INF = float("-inf")


def sliding_window_mask(length: int, window: int) -> Matrix:
    """Additive mask for causal attention inside a window of `window`.

    Position i may read positions i - window + 1 through i inclusive, so a
    window of 1 lets a position read only itself and a window of `length`
    is ordinary causal attention.

    Args:
        length: sequence length.
        window: how many positions a query may read, including itself.

    Returns:
        A (length, length) matrix of 0.0 where reading is allowed and -inf
        where it is not.

    Raises:
        ValueError: if length or window is not positive.
    """
    if length <= 0:
        raise ValueError(f"length must be positive, got {length}")
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    return [
        [
            0.0 if row - window < col <= row else NEG_INF
            for col in range(length)
        ]
        for row in range(length)
    ]


def sink_window_mask(length: int, window: int, num_sinks: int) -> Matrix:
    """A sliding window plus a few positions every query may always read.

    The always-readable positions are the first `num_sinks` of the
    sequence. Longformer's global attention is the same structural idea,
    "a local windowed attention with a task motivated global attention"
    (arXiv:2004.05150), with the global set chosen by the task rather than
    fixed at the front.

    Args:
        length: sequence length.
        window: local window size, including the query itself.
        num_sinks: how many leading positions stay readable from everywhere.

    Returns:
        A (length, length) additive mask.

    Raises:
        ValueError: if any argument is invalid, or num_sinks exceeds length.
    """
    if num_sinks < 0:
        raise ValueError(f"num_sinks cannot be negative, got {num_sinks}")
    if num_sinks > length:
        raise ValueError(
            f"num_sinks {num_sinks} exceeds length {length}"
        )
    mask = sliding_window_mask(length, window)
    for row in range(length):
        for col in range(min(num_sinks, row + 1)):
            mask[row][col] = 0.0
    return mask


def allowed_count(mask: Sequence[Sequence[float]]) -> int:
    """How many (query, key) pairs a mask permits.

    Raises:
        ValueError: if the mask is empty or ragged.
    """
    shape(mask)
    return sum(1 for row in mask for value in row if value != NEG_INF)


def mask_density(mask: Sequence[Sequence[float]]) -> float:
    """Permitted pairs as a fraction of all pairs in the matrix.

    Reported against the full square rather than against the causal
    triangle, because the square is what quadratic cost refers to.

    Raises:
        ValueError: if the mask is empty or ragged.
    """
    rows, cols = shape(mask)
    return allowed_count(mask) / (rows * cols)


def window_reach_formula(window: int, layers: int) -> int:
    """How far back a position can reach after `layers` windowed layers.

    Each layer moves information at most window - 1 positions, so after L
    layers the furthest reachable distance is L * (window - 1). This is the
    arithmetic everyone quotes; `max_reach` measures it instead.

    Raises:
        ValueError: if window or layers is not positive.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if layers <= 0:
        raise ValueError(f"layers must be positive, got {layers}")
    return layers * (window - 1)


def reachability(
    mask: Sequence[Sequence[float]], layers: int
) -> List[List[bool]]:
    """Which positions can influence which others through `layers` layers.

    Takes boolean powers of the mask's adjacency. Entry (i, j) is True when
    information at position j can reach position i after that many layers.
    This is pure graph connectivity: it says a path exists and says nothing
    about how much survives the trip.

    Args:
        mask: an (n, n) additive mask.
        layers: how many stacked layers, at least 1.

    Returns:
        An (n, n) boolean matrix.

    Raises:
        ValueError: if the mask is not square, or layers is not positive.

    Complexity: O(layers * n^3).
    """
    rows, cols = shape(mask)
    if rows != cols:
        raise ValueError(f"reachability needs a square mask, got ({rows}, {cols})")
    if layers <= 0:
        raise ValueError(f"layers must be positive, got {layers}")
    adjacency = [
        [mask[row][col] != NEG_INF for col in range(cols)] for row in range(rows)
    ]
    reached = [list(row) for row in adjacency]
    for _ in range(layers - 1):
        reached = [
            [
                any(reached[i][k] and adjacency[k][j] for k in range(rows))
                for j in range(cols)
            ]
            for i in range(rows)
        ]
    return reached


def max_reach(mask: Sequence[Sequence[float]], layers: int) -> int:
    """Largest backward distance any position can reach after `layers`.

    Measured from the connectivity graph rather than from the formula, so
    `window_reach_formula` can be checked rather than assumed.

    Raises:
        ValueError: propagated from `reachability`.
    """
    reached = reachability(mask, layers)
    rows = len(reached)
    best = 0
    for i in range(rows):
        for j in range(i + 1):
            if reached[i][j]:
                best = max(best, i - j)
    return best


def top_k_mask(
    scores: Sequence[Sequence[float]],
    k: int,
    base_mask: Optional[Sequence[Sequence[float]]] = None,
) -> Matrix:
    """Keep the k highest-scoring permitted keys per query, forbid the rest.

    Args:
        scores: an (n_q, n_k) matrix of selection scores. Higher is better.
        k: how many keys to keep per query. A query with fewer permitted
            keys than k keeps all of them.
        base_mask: optional additive mask applied first, so selection only
            ever chooses among positions the model was already allowed to
            read. Without it, a causal model would select from the future.

    Returns:
        An (n_q, n_k) additive mask.

    Raises:
        ValueError: if k is below 1, the shapes disagree, or a query has no
            permitted key at all, since that produces a fully masked row
            and softmax has no answer for it.

    Complexity: O(n_q * n_k log n_k).
    """
    rows, cols = shape(scores)
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    if base_mask is not None:
        base_shape = shape(base_mask)
        if base_shape != (rows, cols):
            raise ValueError(
                f"base mask is {base_shape} but scores are ({rows}, {cols})"
            )
    selected = [[NEG_INF] * cols for _ in range(rows)]
    for row in range(rows):
        candidates = [
            (scores[row][col], col)
            for col in range(cols)
            if base_mask is None or base_mask[row][col] != NEG_INF
        ]
        if not candidates:
            raise ValueError(
                f"query {row} has no permitted key, so no selection exists"
            )
        candidates.sort(key=lambda pair: (-pair[0], pair[1]))
        for _, col in candidates[:k]:
            selected[row][col] = 0.0
    return selected


def selected_indices(mask: Sequence[Sequence[float]], row: int) -> Set[int]:
    """The set of keys one query is permitted to read.

    Raises:
        ValueError: if the row index is out of range.
    """
    rows, cols = shape(mask)
    if not 0 <= row < rows:
        raise ValueError(f"row {row} is out of range for {rows} queries")
    return {col for col in range(cols) if mask[row][col] != NEG_INF}


def selection_recall(
    chosen: Sequence[Sequence[float]],
    reference: Sequence[Sequence[float]],
) -> float:
    """Share of the reference selection that a cheaper selection recovered.

    Averaged over queries. For each query, the fraction of the reference
    query's chosen keys that also appear in the cheaper selection. A recall
    of 1.0 means the cheap scorer picked every position the expensive one
    would have.

    Args:
        chosen: the cheap selection's additive mask.
        reference: the mask the expensive scores would have produced.

    Returns:
        A value in [0.0, 1.0].

    Raises:
        ValueError: if the shapes disagree, or any reference query selects
            nothing, which would make its recall undefined.
    """
    chosen_shape = shape(chosen)
    reference_shape = shape(reference)
    if chosen_shape != reference_shape:
        raise ValueError(
            f"cannot compare {chosen_shape} with {reference_shape}"
        )
    rows, _ = chosen_shape
    total = 0.0
    for row in range(rows):
        wanted = selected_indices(reference, row)
        if not wanted:
            raise ValueError(f"reference query {row} selects nothing")
        got = selected_indices(chosen, row)
        total += len(wanted & got) / len(wanted)
    return total / rows


def attention_mass_captured(
    weights: Sequence[Sequence[float]],
    selection: Sequence[Sequence[float]],
) -> float:
    """Share of the full attention distribution that a selection keeps.

    Recall counts positions. This weighs them: a selection that misses two
    positions carrying almost no weight has lost almost nothing, and a
    selection that misses the one position carrying half the weight has
    lost half. Averaged over queries.

    Args:
        weights: an (n_q, n_k) matrix of full attention weights, rows
            summing to 1.
        selection: the additive mask whose permitted entries are counted.

    Returns:
        A value in [0.0, 1.0].

    Raises:
        ValueError: if the shapes disagree.
    """
    weight_shape = shape(weights)
    selection_shape = shape(selection)
    if weight_shape != selection_shape:
        raise ValueError(
            f"cannot compare {weight_shape} with {selection_shape}"
        )
    rows, cols = weight_shape
    total = 0.0
    for row in range(rows):
        kept = sum(
            weights[row][col]
            for col in range(cols)
            if selection[row][col] != NEG_INF
        )
        total += kept
    return total / rows


def row_entropy(row: Sequence[float]) -> float:
    """Shannon entropy of one attention distribution, in bits.

    Zero weights contribute nothing, which is the correct limit of
    p log p as p goes to 0 and avoids a domain error on log(0).

    Returns:
        Entropy in bits, between 0.0 for a one-hot row and log2(n) for a
        uniform one over n positions.

    Raises:
        ValueError: if the row is empty or sums to something other than 1
            within a tolerance, since an unnormalised row has no entropy.
    """
    if not row:
        raise ValueError("row_entropy needs a non-empty row")
    total = sum(row)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"row sums to {total}, which is not a distribution"
        )
    # The trailing addition turns a negated 0.0 back into 0.0. A one-hot
    # row otherwise prints as -0.0, which reads as a bug in a table.
    return -sum(
        value * math.log2(value) for value in row if value > 0.0
    ) + 0.0


def uniform_entropy(support: int) -> float:
    """Entropy of a uniform distribution over `support` positions, in bits.

    The ceiling any attention row can reach, and the baseline against which
    a row's peakedness should be read.

    Raises:
        ValueError: if support is not positive.
    """
    if support <= 0:
        raise ValueError(f"support must be positive, got {support}")
    return math.log2(support)


class CheapIndexer:
    """A deliberately weak scorer that ranks keys without running attention.

    The published designs in this family use a small learned scorer to
    decide which positions the expensive attention should read. This is the
    same shape at toy scale: one narrow projection for queries and one for
    keys, so scoring a pair costs `d_index` multiply-adds instead of
    `d_head`, and the ranking it produces is compared against the ranking
    the real scores would give.

    It is untrained, so it has no reason to agree with anything. That is
    the point of measuring it: an untrained indexer is the floor, and the
    gap between that floor and useful selection is what training has to
    close.

    Attributes:
        d_index: width of the scoring projection, smaller than d_head.
        w_query: (d_model, d_index).
        w_key: (d_model, d_index).
    """

    def __init__(self, d_model: int, d_index: int, seed: int):
        """Build both projections deterministically from `seed`.

        Raises:
            ValueError: if either width is not positive.
        """
        if d_model <= 0 or d_index <= 0:
            raise ValueError(
                f"CheapIndexer needs positive dims, got ({d_model}, {d_index})"
            )
        self.d_model = d_model
        self.d_index = d_index
        rng = random.Random(seed)
        self.w_query = glorot_matrix(d_model, d_index, rng)
        self.w_key = glorot_matrix(d_model, d_index, rng)

    def scores(self, x: Sequence[Sequence[float]]) -> Matrix:
        """Score every (query, key) pair cheaply.

        Args:
            x: (n, d_model) input.

        Returns:
            An (n, n) matrix of scores, higher meaning more worth reading.

        Raises:
            ValueError: if x is not d_model wide.

        Complexity: O(n^2 * d_index). Quadratic in the sequence, which is
        the cost this family of designs pays to avoid a quadratic cost.
        """
        _, width = shape(x)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this indexer expects {self.d_model}"
            )
        queries = matmul(x, self.w_query)
        keys = matmul(x, self.w_key)
        return matmul(queries, transpose(keys))

    def cost_ratio(self, d_head: int, num_heads: int) -> float:
        """Indexer score cost as a fraction of full attention's score cost.

        Args:
            d_head: width of one attention head.
            num_heads: heads in the layer being replaced.

        Returns:
            d_index / (num_heads * d_head), the per-pair work ratio.

        Raises:
            ValueError: if either argument is not positive.
        """
        if d_head <= 0 or num_heads <= 0:
            raise ValueError(
                f"cost_ratio needs positive dims, got ({d_head}, {num_heads})"
            )
        return self.d_index / (num_heads * d_head)


def recall_and_mass(
    x: Sequence[Sequence[float]],
    weights: Sequence[Sequence[float]],
    scores: Sequence[Sequence[float]],
    indexer: CheapIndexer,
    k: int,
    base_mask: Sequence[Sequence[float]],
) -> Tuple[float, float, float]:
    """Compare a cheap selection against the selection real scores imply.

    Args:
        x: the (n, d_model) input the indexer scores.
        weights: the full attention weights, for the mass calculation.
        scores: the real pre-softmax scores the reference selection uses.
        indexer: the cheap scorer.
        k: how many keys each query keeps.
        base_mask: the causal or windowed mask selection must respect.

    Returns:
        (recall, cheap_mass, oracle_mass): the share of the reference
        selection recovered, the attention mass the cheap selection keeps,
        and the mass the reference selection keeps. The third is the
        ceiling the second is competing against.

    Raises:
        ValueError: propagated from the helpers on any shape disagreement.
    """
    reference = top_k_mask(scores, k, base_mask)
    cheap = top_k_mask(indexer.scores(x), k, base_mask)
    return (
        selection_recall(cheap, reference),
        attention_mass_captured(weights, cheap),
        attention_mass_captured(weights, reference),
    )
