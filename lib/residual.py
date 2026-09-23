"""The residual stream: a transformer block stack read as writes to a bus.

Standard library only, built on `lib/linalg.py`, `lib/attention.py` and
`lib/layernorm.py`.

A transformer block is usually drawn as a pipeline: attention, then a
feed-forward network, then the next block. That drawing hides the
property that makes the architecture work. In the pre-norm arrangement,
every block reads the running vector, computes something, and adds the
result back. Nothing overwrites. So for a stack of L blocks the value
arriving at the top is exactly

    x_L = x_0 + sum of every branch output written along the way

with equality in the arithmetic, not as an approximation. He et al.
introduced the idea for image networks, reformulating layers "as learning
residual functions with reference to the layer inputs, instead of learning
unreferenced functions" (arXiv:1512.03385), and it is the same identity
here.

That identity is the whole reason this module exists. It means a stack is
a sum of contributions rather than a chain of transformations, and a sum
can be taken apart term by term. `ResidualRecorder` runs a stack and keeps
every term, so an article can show the decomposition instead of asserting
it. `experiments/week-04/residual_stream.py` then checks the reconstruction
to machine precision, and checks that the post-norm arrangement breaks it,
which is the point: post-norm renormalises the running vector at the end of
every block, so the running vector stops being a sum of what was written.

TWO FACTS THE RECORDER MAKES MEASURABLE.

  Writes are nearly orthogonal to the stream they land in, at least at
  initialization. With d dimensions and no training, a fresh branch output
  points in an essentially arbitrary direction relative to the accumulated
  stream, so the lengths add in quadrature rather than linearly:

      rms_after ** 2 ~= rms_before ** 2 + delta_rms ** 2

  That is why a pre-norm residual stream grows roughly with the square
  root of depth instead of linearly.

  Each write is small next to the stream it lands in. The recorder reports
  a write fraction, delta_rms over rms_after, so "small" is a number rather
  than an impression.

Nothing here is trained. Weights come from a seed, so every figure in an
article that quotes this module is reproducible by running the script.
"""

import math
from typing import List, NamedTuple, Optional, Sequence, Tuple

from lib.layernorm import LayerNorm, TransformerBlock, root_mean_square
from lib.linalg import Matrix, add, scale, shape


class StreamWrite(NamedTuple):
    """One component's contribution to the residual stream.

    Attributes:
        depth: index of the block that produced the write, 0 nearest input.
        component: "attention" or "feed_forward".
        delta: the (n, d_model) matrix that was added to the stream.
        stream_before: root mean square of the stream before the write.
        stream_after: root mean square of the stream after the write.
        cosine: cosine of the angle between the write and the stream it
            landed in, both flattened to one vector. Near 0.0 means the
            write is orthogonal to what was already there.
    """

    depth: int
    component: str
    delta: Matrix
    stream_before: float
    stream_after: float
    cosine: float

    @property
    def delta_rms(self) -> float:
        """Root mean square of the write itself."""
        return root_mean_square(self.delta)

    @property
    def write_fraction(self) -> float:
        """Size of the write relative to the stream it produced.

        Returns:
            delta_rms / stream_after, which answers "what share of the
            outgoing stream did this component contribute" in a way that
            does not depend on the absolute scale of the stream.

        Raises:
            ValueError: if the outgoing stream has zero size, which would
                mean the whole stack collapsed to zero.
        """
        if self.stream_after <= 0.0:
            raise ValueError(
                f"stream at depth {self.depth} after {self.component} has "
                "size 0, so a write fraction is undefined"
            )
        return self.delta_rms / self.stream_after

    @property
    def quadrature_prediction(self) -> float:
        """Stream size predicted if this write were exactly orthogonal.

        sqrt(stream_before ** 2 + delta_rms ** 2). Compare it against
        `stream_after` to see how close to orthogonal the write really was.
        """
        return math.sqrt(self.stream_before ** 2 + self.delta_rms ** 2)


def flatten(matrix: Sequence[Sequence[float]]) -> List[float]:
    """Read a matrix as one long vector, row-major.

    Raises:
        ValueError: if the matrix is empty or ragged.
    """
    shape(matrix)
    return [float(value) for row in matrix for value in row]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine of the angle between two vectors of equal length.

    Args:
        left: a non-empty sequence.
        right: a sequence of the same length.

    Returns:
        A value in [-1.0, 1.0]. Returns 0.0 when either vector has zero
        length, because an angle to the zero vector is undefined and 0.0
        is the answer that will not silently poison a mean.

    Raises:
        ValueError: if the lengths differ or either is empty.

    Complexity: O(n).
    """
    if not left or not right:
        raise ValueError("cosine_similarity needs two non-empty vectors")
    if len(left) != len(right):
        raise ValueError(
            f"cannot compare lengths {len(left)} and {len(right)}"
        )
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def subtract(
    left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
) -> Matrix:
    """Element-wise difference of two matrices of identical shape.

    Raises:
        ValueError: if the shapes differ.
    """
    return add(left, scale(right, -1.0))


def max_abs_difference(
    left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
) -> float:
    """Largest absolute element-wise difference between two matrices.

    This is the quantity a reconstruction check reports: how far the sum of
    the recorded writes is from the stream the stack actually produced.

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


class ResidualRecorder:
    """Run a stack of blocks and keep every write into the residual stream.

    The recorder re-implements the two block arrangements rather than
    calling `TransformerBlock.forward`, because the point is to intercept
    each branch output before it is added. Both paths are kept in step with
    `lib/layernorm.py` by `tests/test_residual.py`, which asserts that the
    recorder's final stream equals that module's forward pass exactly.

    Attributes:
        blocks: the blocks to run, in order, block 0 nearest the input.
        norm_first: True for pre-norm, False for post-norm. Taken from the
            first block, and every block must agree.
    """

    def __init__(self, blocks: Sequence[TransformerBlock]):
        """Take a sequence of blocks that all use the same arrangement.

        Raises:
            ValueError: if the sequence is empty or the blocks disagree
                about `norm_first`, since a mixed stack has no single
                decomposition to report.
        """
        if not blocks:
            raise ValueError("ResidualRecorder needs at least one block")
        arrangements = {block.norm_first for block in blocks}
        if len(arrangements) != 1:
            raise ValueError(
                "every block must share one arrangement, got both "
                "norm_first=True and norm_first=False"
            )
        self.blocks = list(blocks)
        self.norm_first = self.blocks[0].norm_first

    def run(
        self,
        x: Sequence[Sequence[float]],
        mask: Optional[Sequence[Sequence[float]]] = None,
        silence: Optional[Sequence[Tuple[int, str]]] = None,
    ) -> Tuple[Matrix, List[StreamWrite]]:
        """Run every block and return the final stream plus every write.

        Args:
            x: an (n, d_model) input, the value written by the embedding.
            mask: optional additive attention mask shared by every block.
            silence: optional (depth, component) pairs whose write is
                replaced by zeros. This is a true ablation: the component
                still runs, its output is discarded, and every later block
                reads the reduced stream, so the effect compounds through
                the rest of the stack. Compare with `ablate`, which removes
                a term from the finished sum and changes nothing downstream.

        Returns:
            (stream, writes). In the pre-norm arrangement the sum of every
            write's delta plus the input reconstructs the stream exactly.
            In the post-norm arrangement each block ends with a LayerNorm
            applied to the running vector; that is recorded as its own
            write, so the deltas still sum correctly while showing exactly
            where the overwrite happened.

        Raises:
            ValueError: if x is not as wide as the blocks expect, or if
                `silence` names a component this arrangement never writes.

        Complexity: the stack's own cost plus O(L * n * d_model) for the
        bookkeeping, so the recording is free next to the matmuls.
        """
        silenced = self._validate_silence(silence)
        stream: Matrix = [[float(value) for value in row] for row in x]
        writes: List[StreamWrite] = []
        for depth, block in enumerate(self.blocks):
            if self.norm_first:
                stream = self._pre_norm_block(
                    depth, block, stream, mask, writes, silenced
                )
            else:
                stream = self._post_norm_block(
                    depth, block, stream, mask, writes, silenced
                )
        return stream, writes

    def _validate_silence(
        self, silence: Optional[Sequence[Tuple[int, str]]]
    ) -> set:
        """Reject an ablation request this stack could never honour.

        A typo in a component name would otherwise produce a run that looks
        ablated, is not, and reports an effect of exactly zero.
        """
        if not silence:
            return set()
        allowed = (
            {"attention", "feed_forward"}
            if self.norm_first
            else {
                "attention",
                "feed_forward",
                "norm_attention",
                "norm_feed_forward",
            }
        )
        requested = set()
        for depth, component in silence:
            if not 0 <= depth < len(self.blocks):
                raise ValueError(
                    f"cannot silence depth {depth}: this stack has "
                    f"{len(self.blocks)} blocks"
                )
            if component not in allowed:
                raise ValueError(
                    f"cannot silence {component!r}: this arrangement writes "
                    f"{sorted(allowed)}"
                )
            requested.add((depth, component))
        return requested

    def _pre_norm_block(
        self,
        depth: int,
        block: TransformerBlock,
        stream: Matrix,
        mask: Optional[Sequence[Sequence[float]]],
        writes: List[StreamWrite],
        silenced: set,
    ) -> Matrix:
        """One pre-norm block: normalise the branch, add the result."""
        attended, _ = block.attention.forward(
            block.norm_attention.forward(stream), mask
        )
        stream = self._record(
            depth, "attention", stream, attended, writes, silenced
        )
        branch = block.feed_forward.forward(
            block.norm_feed_forward.forward(stream)
        )
        return self._record(
            depth, "feed_forward", stream, branch, writes, silenced
        )

    def _post_norm_block(
        self,
        depth: int,
        block: TransformerBlock,
        stream: Matrix,
        mask: Optional[Sequence[Sequence[float]]],
        writes: List[StreamWrite],
        silenced: set,
    ) -> Matrix:
        """One post-norm block, with each renormalisation recorded as a write.

        A LayerNorm applied to the running vector is not an addition, so to
        keep the deltas summing to the stream it is recorded as the delta it
        is equivalent to: normalised minus current. That makes the overwrite
        visible as a write whose size is comparable to the stream itself,
        which is exactly what distinguishes this arrangement.
        """
        attended, _ = block.attention.forward(stream, mask)
        stream = self._record(
            depth, "attention", stream, attended, writes, silenced
        )
        stream = self._record_norm(
            depth, "norm_attention", stream, block.norm_attention, writes,
            silenced,
        )
        branch = block.feed_forward.forward(stream)
        stream = self._record(
            depth, "feed_forward", stream, branch, writes, silenced
        )
        return self._record_norm(
            depth, "norm_feed_forward", stream, block.norm_feed_forward, writes,
            silenced,
        )

    def _record_norm(
        self,
        depth: int,
        component: str,
        stream: Matrix,
        norm: LayerNorm,
        writes: List[StreamWrite],
        silenced: set,
    ) -> Matrix:
        """Record a renormalisation as the equivalent additive delta."""
        normalised = norm.forward(stream)
        delta = subtract(normalised, stream)
        return self._record(depth, component, stream, delta, writes, silenced)

    @staticmethod
    def _record(
        depth: int,
        component: str,
        stream: Matrix,
        delta: Matrix,
        writes: List[StreamWrite],
        silenced: set,
    ) -> Matrix:
        """Add `delta` to `stream`, append the bookkeeping, return the sum."""
        if (depth, component) in silenced:
            delta = [[0.0] * len(row) for row in delta]
        before = root_mean_square(stream)
        updated = add(stream, delta)
        writes.append(
            StreamWrite(
                depth=depth,
                component=component,
                delta=[list(row) for row in delta],
                stream_before=before,
                stream_after=root_mean_square(updated),
                cosine=cosine_similarity(flatten(delta), flatten(stream)),
            )
        )
        return updated


def reconstruct(
    x: Sequence[Sequence[float]], writes: Sequence[StreamWrite]
) -> Matrix:
    """Rebuild the final stream from the input plus every recorded write.

    This is the identity the whole module is about, written out as code so
    it can be compared against the stack's own output rather than believed.

    Args:
        x: the (n, d_model) input.
        writes: every write, in the order they were made.

    Returns:
        The (n, d_model) sum.

    Raises:
        ValueError: if any delta's shape disagrees with the input's.
    """
    total: Matrix = [[float(value) for value in row] for row in x]
    for write in writes:
        total = add(total, write.delta)
    return total


def writes_at_depth(
    writes: Sequence[StreamWrite], depth: int
) -> List[StreamWrite]:
    """Every write made by one block, in order."""
    return [write for write in writes if write.depth == depth]


def ablate(
    x: Sequence[Sequence[float]],
    writes: Sequence[StreamWrite],
    depth: int,
    component: str,
) -> Matrix:
    """Rebuild the stream with one component's write removed.

    This is the cheapest possible ablation and it is exact for the pre-norm
    arrangement only in a restricted sense: it removes the contribution
    without recomputing everything downstream, so it answers "how much did
    this component put into the final sum", not "what would the model have
    done without it". The distinction matters and
    `experiments/week-04/residual_stream.py` states it at the point of use.

    Args:
        x: the original input.
        writes: every recorded write.
        depth: which block's write to drop.
        component: which component within that block.

    Returns:
        The (n, d_model) sum with that one term missing.

    Raises:
        ValueError: if no write matches, since silently returning the full
            sum would look like an ablation with no effect.
    """
    matched = [
        write
        for write in writes
        if write.depth == depth and write.component == component
    ]
    if not matched:
        raise ValueError(
            f"no write recorded for depth {depth} component {component!r}"
        )
    kept = [
        write
        for write in writes
        if not (write.depth == depth and write.component == component)
    ]
    return reconstruct(x, kept)
