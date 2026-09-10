"""Token and position embedding, the layer that turns ids into vectors.

Standard library only, built on `lib/linalg.py`. This is the layer that
sits between `lib/bpe.py`, which turns text into integers, and
`lib/attention.py`, which needs rows of floats.

An embedding layer is a table. It holds one row of d_model numbers for
every token id, and "embedding" a token means reading its row. That is
genuinely all it is, and the whole reason it deserves a module rather
than a dictionary is that three facts about it are easy to get wrong and
expensive to get wrong late.

FIRST: A LOOKUP IS A MATRIX MULTIPLICATION. Reading row i of a table E is
exactly one_hot(i) @ E, where one_hot(i) is a row of zeros with a single
1.0 in position i. The two produce identical numbers, which
`embed_by_matmul` and `EmbeddingTable.lookup` both compute so the claim
can be checked rather than asserted. This matters because it is why an
embedding table is trainable at all: a lookup looks like an array index,
which has no derivative, but the multiplication it is equivalent to has
one, and the gradient it receives lands on exactly the rows that were
looked up.

SECOND: POSITION IS NOT IN THE TOKEN. Attention, as implemented in
`lib/attention.py`, is order-blind: permute the input rows and the output
rows permute identically. The token table cannot fix this, because it is
indexed by id and knows nothing about where the token sat. So a second
table, indexed by position, is added to the first. `forward` adds them,
and the test suite checks that the same token at two different positions
comes out as two different rows.

THIRD: THE TABLE IS USUALLY THE LARGEST SINGLE PARAMETER IN A SMALL
MODEL. It holds vocab_size times d_model floats, and vocab_size is tens
of thousands. `parameter_report` computes that share for a stated
configuration, because "just a lookup" is how a third of a small model's
parameters get treated as a rounding error.

Nothing here is trained. Weights come from a seeded generator so that a
reader reproduces every number exactly. An untrained embedding carries no
meaning whatsoever, and any structure you find by comparing two of these
rows is a property of the seed.
"""

import math
import random
from typing import Dict, List, Sequence

from lib.linalg import Matrix, add, matmul, shape, transpose

# Standard deviation of the seeded Gaussian used to fill a fresh table.
# Small on purpose: rows start close to the origin and close to each
# other, which is the honest starting point for something untrained. It
# is a choice made here, not a figure taken from any paper.
DEFAULT_INIT_STD = 0.02


def gaussian_matrix(rows: int, cols: int, rng: random.Random, std: float) -> Matrix:
    """Return a rows by cols matrix of independent N(0, std^2) samples.

    Args:
        rows: number of table entries.
        cols: width of each entry.
        rng: a seeded random.Random, so results are reproducible.
        std: standard deviation, must be positive.

    Returns:
        A fresh matrix. No row is shared with any other.

    Raises:
        ValueError: if a dimension is not positive or std is not positive.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError(f"gaussian_matrix needs positive dims, got ({rows}, {cols})")
    if std <= 0.0:
        raise ValueError(f"gaussian_matrix needs a positive std, got {std}")
    return [[rng.gauss(0.0, std) for _ in range(cols)] for _ in range(rows)]


def one_hot(index: int, width: int) -> List[float]:
    """Return a row of `width` zeros with 1.0 at `index`.

    Args:
        index: the position to set, in [0, width).
        width: the length of the row, must be positive.

    Raises:
        ValueError: if width is not positive.
        IndexError: if index is outside [0, width). Raising here rather
            than wrapping is deliberate: Python's negative indexing would
            turn id -1 into the last row of the vocabulary and return a
            plausible vector for an impossible token.
    """
    if width <= 0:
        raise ValueError(f"one_hot needs a positive width, got {width}")
    if not 0 <= index < width:
        raise IndexError(f"index {index} is outside [0, {width})")
    row = [0.0] * width
    row[index] = 1.0
    return row


def embed_by_matmul(table: Sequence[Sequence[float]], ids: Sequence[int]) -> Matrix:
    """Embed ids the slow, explicit way: one-hot rows times the table.

    This exists to be compared against `EmbeddingTable.lookup`, which is
    what anybody would actually run. Identical outputs are the point.

    Complexity: O(len(ids) * num_entries * d_model), which is why nobody
    does this in production. The lookup is O(len(ids) * d_model).

    Raises:
        IndexError: if any id is outside the table.
        ValueError: if the table is empty or ragged.
    """
    num_entries, _ = shape(table)
    hot = [one_hot(token_id, num_entries) for token_id in ids]
    return matmul(hot, table)


class EmbeddingTable:
    """A table of `num_entries` rows, each `d_model` numbers wide.

    Attributes:
        num_entries: how many distinct things can be embedded.
        d_model: the width of every row.
        weight: the table itself, a list of `num_entries` rows.
    """

    def __init__(
        self,
        num_entries: int,
        d_model: int,
        rng: random.Random,
        std: float = DEFAULT_INIT_STD,
    ):
        """Allocate and fill a table.

        Args:
            num_entries: vocabulary size, or number of positions.
            d_model: width of each row.
            rng: a seeded random.Random.
            std: initialisation standard deviation.

        Raises:
            ValueError: if a dimension or std is not positive.
        """
        self.weight: Matrix = gaussian_matrix(num_entries, d_model, rng, std)
        self.num_entries = num_entries
        self.d_model = d_model

    @property
    def parameter_count(self) -> int:
        """Number of floats held: num_entries times d_model, exactly."""
        return self.num_entries * self.d_model

    def lookup(self, ids: Sequence[int]) -> Matrix:
        """Return one row per id, in the order given.

        Args:
            ids: token ids or positions, each in [0, num_entries).

        Returns:
            A len(ids) by d_model matrix. Rows are copies, so mutating the
            result never corrupts the table.

        Raises:
            IndexError: if any id is outside [0, num_entries), naming the
                offending id and the table size.
            TypeError: if any id is not an int.

        Complexity: O(len(ids) * d_model).
        """
        rows: Matrix = []
        for position, token_id in enumerate(ids):
            if not isinstance(token_id, int) or isinstance(token_id, bool):
                raise TypeError(
                    f"id at position {position} is {type(token_id).__name__}, "
                    "not int"
                )
            if not 0 <= token_id < self.num_entries:
                raise IndexError(
                    f"id {token_id} at position {position} is outside "
                    f"[0, {self.num_entries}). A tokenizer that grew special "
                    "tokens after this table was sized produces exactly this."
                )
            rows.append(list(self.weight[token_id]))
        return rows


class TokenAndPositionEmbedding:
    """Token embedding plus learned absolute position embedding.

    The forward pass is one addition: row for the token, plus row for
    where the token is. Both tables are ordinary `EmbeddingTable`s, which
    is the point. Position is not special machinery, it is a second
    lookup, and the model learns what each slot means.

    Attributes:
        tokens: the vocab_size by d_model table.
        positions: the max_positions by d_model table.
        vocab_size, max_positions, d_model: the sizing, kept for report.
    """

    def __init__(
        self,
        vocab_size: int,
        max_positions: int,
        d_model: int,
        seed: int,
        std: float = DEFAULT_INIT_STD,
    ):
        """Allocate both tables from one seed.

        Args:
            vocab_size: number of token ids the tokenizer can emit.
            max_positions: the longest sequence this layer accepts. A
                sequence longer than this cannot be embedded, and that is
                a hard limit, not a soft one.
            d_model: width of the model.
            seed: seeds a random.Random so every weight is reproducible.
            std: initialisation standard deviation.

        Raises:
            ValueError: if any dimension or std is not positive.
        """
        rng = random.Random(seed)
        self.tokens = EmbeddingTable(vocab_size, d_model, rng, std)
        self.positions = EmbeddingTable(max_positions, d_model, rng, std)
        self.vocab_size = vocab_size
        self.max_positions = max_positions
        self.d_model = d_model

    @property
    def parameter_count(self) -> int:
        """Floats in both tables: (vocab_size + max_positions) * d_model."""
        return self.tokens.parameter_count + self.positions.parameter_count

    def forward(self, token_ids: Sequence[int]) -> Matrix:
        """Embed a sequence: token row plus position row, per position.

        Args:
            token_ids: ids from a tokenizer, length 1 to max_positions.

        Returns:
            A len(token_ids) by d_model matrix, ready for attention.

        Raises:
            ValueError: if the sequence is empty or longer than
                max_positions, naming both lengths.
            IndexError: if any id is outside the vocabulary.
            TypeError: if any id is not an int.

        Complexity: O(len(token_ids) * d_model).
        """
        length = len(token_ids)
        if length == 0:
            raise ValueError("cannot embed an empty sequence")
        if length > self.max_positions:
            raise ValueError(
                f"sequence of {length} exceeds max_positions "
                f"{self.max_positions}. Truncating here would be silent data "
                "loss, so it is refused instead."
            )
        token_rows = self.tokens.lookup(token_ids)
        position_rows = self.positions.lookup(list(range(length)))
        return add(token_rows, position_rows)

    def tied_logits(self, hidden: Sequence[Sequence[float]]) -> Matrix:
        """Score every token id against every row, reusing the token table.

        Weight tying: instead of a separate vocab_size by d_model output
        matrix, the transpose of the input table is used. It halves the
        embedding parameter cost, and it is why a model's reported
        parameter count can be smaller than the sum of the layers you
        counted.

        Args:
            hidden: an n by d_model matrix, the model's output rows.

        Returns:
            An n by vocab_size matrix of scores.

        Raises:
            ValueError: if hidden's width is not d_model.

        Complexity: O(n * d_model * vocab_size), the dominant matmul in a
        small model's forward pass.
        """
        _, width = shape(hidden)
        if width != self.d_model:
            raise ValueError(
                f"hidden is {width} wide, expected d_model {self.d_model}"
            )
        return matmul(hidden, transpose(self.tokens.weight))


def parameter_report(
    vocab_size: int, max_positions: int, d_model: int, total_parameters: int
) -> Dict[str, float]:
    """Size the embedding tables against a model's whole parameter budget.

    Args:
        vocab_size: number of token ids.
        max_positions: length of the position table.
        d_model: model width.
        total_parameters: the whole model's parameter count, from whatever
            source you trust. This function does not estimate it.

    Returns:
        A dict with token_parameters, position_parameters,
        embedding_parameters, embedding_share (a fraction of
        total_parameters), and tying_saving (the floats a tied output
        projection does not have to hold).

    Raises:
        ValueError: if any argument is not positive.
    """
    for name, value in (
        ("vocab_size", vocab_size),
        ("max_positions", max_positions),
        ("d_model", d_model),
        ("total_parameters", total_parameters),
    ):
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
    token_parameters = vocab_size * d_model
    position_parameters = max_positions * d_model
    embedding_parameters = token_parameters + position_parameters
    return {
        "token_parameters": token_parameters,
        "position_parameters": position_parameters,
        "embedding_parameters": embedding_parameters,
        "embedding_share": embedding_parameters / total_parameters,
        "tying_saving": token_parameters,
    }


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine of the angle between two vectors, in [-1, 1].

    Provided so that the claim "untrained embeddings carry no meaning"
    can be measured instead of asserted: run it over a fresh table and
    watch every pair sit near zero.

    Raises:
        ValueError: if the lengths differ or either vector is all zeros.
    """
    if len(left) != len(right):
        raise ValueError(
            f"cannot compare vectors of length {len(left)} and {len(right)}"
        )
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise ValueError("cosine similarity is undefined for a zero vector")
    return dot / (left_norm * right_norm)
