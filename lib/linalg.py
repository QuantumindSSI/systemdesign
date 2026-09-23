"""Minimal dense matrix operations, standard library only.

This module exists so that `lib/attention.py` can be read as mathematics
rather than as array-library idiom. Everything here operates on a matrix
represented as a list of equal-length lists of floats, row-major:

    [[a00, a01, a02],
     [a10, a11, a12]]

is a 2 by 3 matrix. There is no broadcasting, no dtype system, and no
in-place mutation. Every function returns a new object.

Performance is deliberately not a goal. `matmul` is the textbook triple
loop, which is O(n * m * p) and is fine for the sequence lengths used in
this series (tens of positions, not thousands). If you need speed, this
is the wrong file; if you need to see what a projection actually does,
this is the right one.

Every function validates its input shapes and raises ValueError with the
offending shapes named, because a silent shape error in attention code
produces plausible-looking numbers that are wrong.
"""

import math
from typing import List, Sequence

Matrix = List[List[float]]


def shape(matrix: Sequence[Sequence[float]]) -> tuple:
    """Return (rows, cols) and verify the matrix is rectangular.

    Raises:
        ValueError: if the matrix is empty or its rows differ in length.
    """
    if not matrix:
        raise ValueError("matrix has no rows")
    cols = len(matrix[0])
    if cols == 0:
        raise ValueError("matrix has rows of width 0")
    for index, row in enumerate(matrix):
        if len(row) != cols:
            raise ValueError(
                f"row {index} has width {len(row)}, expected {cols}: matrix is ragged"
            )
    return (len(matrix), cols)


def zeros(rows: int, cols: int) -> Matrix:
    """Return a rows by cols matrix of 0.0.

    Raises:
        ValueError: if either dimension is not positive.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError(f"zeros needs positive dimensions, got ({rows}, {cols})")
    return [[0.0] * cols for _ in range(rows)]


def transpose(matrix: Sequence[Sequence[float]]) -> Matrix:
    """Return the transpose. A p by q matrix becomes q by p."""
    rows, cols = shape(matrix)
    return [[float(matrix[r][c]) for r in range(rows)] for c in range(cols)]


def matmul(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> Matrix:
    """Multiply two matrices.

    Args:
        left: an n by m matrix.
        right: an m by p matrix.

    Returns:
        The n by p product.

    Raises:
        ValueError: if the inner dimensions disagree.

    Complexity: O(n * m * p) multiply-adds, the textbook triple loop.
    """
    n_rows, n_cols = shape(left)
    m_rows, m_cols = shape(right)
    if n_cols != m_rows:
        raise ValueError(
            f"cannot multiply ({n_rows}, {n_cols}) by ({m_rows}, {m_cols}): "
            f"inner dimensions {n_cols} and {m_rows} differ"
        )
    right_t = transpose(right)
    product = zeros(n_rows, m_cols)
    for i in range(n_rows):
        left_row = left[i]
        for j in range(m_cols):
            right_col = right_t[j]
            total = 0.0
            for k in range(n_cols):
                total += left_row[k] * right_col[k]
            product[i][j] = total
    return product


def add(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> Matrix:
    """Element-wise sum of two matrices of identical shape.

    Raises:
        ValueError: if the shapes differ.
    """
    left_shape = shape(left)
    right_shape = shape(right)
    if left_shape != right_shape:
        raise ValueError(f"cannot add {left_shape} to {right_shape}")
    rows, cols = left_shape
    return [[left[r][c] + right[r][c] for c in range(cols)] for r in range(rows)]


def scale(matrix: Sequence[Sequence[float]], factor: float) -> Matrix:
    """Multiply every element by a scalar."""
    rows, cols = shape(matrix)
    return [[matrix[r][c] * factor for c in range(cols)] for r in range(rows)]


def hstack(matrices: Sequence[Sequence[Sequence[float]]]) -> Matrix:
    """Concatenate matrices left to right. All must have the same row count.

    This is the operation that turns a list of per-head outputs, each
    n by d_head, into the single n by (num_heads * d_head) matrix that
    the output projection consumes.

    Raises:
        ValueError: if the list is empty or row counts disagree.
    """
    if not matrices:
        raise ValueError("hstack needs at least one matrix")
    row_counts = {shape(m)[0] for m in matrices}
    if len(row_counts) != 1:
        raise ValueError(f"hstack needs equal row counts, got {sorted(row_counts)}")
    rows = row_counts.pop()
    stacked = []
    for r in range(rows):
        row: List[float] = []
        for matrix in matrices:
            row.extend(float(value) for value in matrix[r])
        stacked.append(row)
    return stacked


DEFAULT_RANK_TOLERANCE = 1e-9


def reduced_row_echelon(
    matrix: Sequence[Sequence[float]],
    tolerance: float = DEFAULT_RANK_TOLERANCE,
) -> tuple:
    """Gauss-Jordan elimination with partial pivoting.

    Args:
        matrix: any rectangular matrix.
        tolerance: a candidate pivot whose absolute value is at or below
            this counts as zero. Floating point never produces an exact
            zero after elimination, so a threshold is not optional; it is
            a stated parameter so that a rank result carries its own
            assumption instead of hiding it.

    Returns:
        (echelon, pivot_columns): a new matrix in reduced row echelon form,
        and the column index of each pivot, ascending.

    Raises:
        ValueError: if the matrix is empty, ragged, or the tolerance is
            not positive.

    Complexity: O(rows^2 * cols).
    """
    rows, cols = shape(matrix)
    if tolerance <= 0.0:
        raise ValueError(f"tolerance must be positive, got {tolerance}")
    work = [[float(value) for value in row] for row in matrix]
    pivot_columns: List[int] = []
    pivot_row = 0
    for column in range(cols):
        if pivot_row >= rows:
            break
        candidate = max(
            range(pivot_row, rows), key=lambda index: abs(work[index][column])
        )
        if abs(work[candidate][column]) <= tolerance:
            continue
        work[pivot_row], work[candidate] = work[candidate], work[pivot_row]
        scale_factor = work[pivot_row][column]
        work[pivot_row] = [value / scale_factor for value in work[pivot_row]]
        for index in range(rows):
            if index == pivot_row:
                continue
            factor = work[index][column]
            if factor == 0.0:
                continue
            work[index] = [
                work[index][j] - factor * work[pivot_row][j] for j in range(cols)
            ]
        pivot_columns.append(column)
        pivot_row += 1
    return work, pivot_columns


def matrix_rank(
    matrix: Sequence[Sequence[float]],
    tolerance: float = DEFAULT_RANK_TOLERANCE,
) -> int:
    """Number of independent rows, equivalently of independent columns.

    Used in this series to answer a structural question about attention:
    how much of the residual stream can a layer's key projections actually
    read. A projection of rank r can only see an r-dimensional slice of
    what is in front of it, no matter how wide the stream is.

    Raises:
        ValueError: propagated from `reduced_row_echelon`.
    """
    return len(reduced_row_echelon(matrix, tolerance)[1])


def null_space_basis(
    matrix: Sequence[Sequence[float]],
    tolerance: float = DEFAULT_RANK_TOLERANCE,
) -> Matrix:
    """Basis for the row vectors this matrix annihilates.

    Everything in this repository multiplies a row vector on the left, so
    the useful null space is {x : x @ matrix == 0}, not {x : matrix @ x == 0}.
    This returns a basis for that set.

    Args:
        matrix: an (n, m) matrix.
        tolerance: passed to the elimination.

    Returns:
        A list of length-n basis vectors, empty when the matrix has full
        row rank and there is nothing it annihilates.

    Raises:
        ValueError: propagated from `reduced_row_echelon`.

    Complexity: O(n * m * min(n, m)).
    """
    rows, _ = shape(matrix)
    echelon, pivot_columns = reduced_row_echelon(transpose(matrix), tolerance)
    pivot_set = set(pivot_columns)
    free_columns = [index for index in range(rows) if index not in pivot_set]
    basis: Matrix = []
    for free in free_columns:
        vector = [0.0] * rows
        vector[free] = 1.0
        for row_index, pivot in enumerate(pivot_columns):
            vector[pivot] = -echelon[row_index][free]
        basis.append(vector)
    return basis


def softmax_rows(matrix: Sequence[Sequence[float]]) -> Matrix:
    """Apply softmax independently to each row.

    The maximum of each row is subtracted before exponentiating. That
    subtraction cancels exactly in the ratio, so it changes no result,
    and it is what stops exp() overflowing on large scores. Attention
    scores can be large, so this is not optional in practice.

    A row may contain float('-inf') for masked positions; those receive
    weight exactly 0.0. A row that is entirely -inf has no valid target
    and raises rather than returning NaN.

    Returns:
        A matrix of the same shape whose rows each sum to 1.0.

    Raises:
        ValueError: if any row is entirely masked.
    """
    rows, cols = shape(matrix)
    result = zeros(rows, cols)
    for r in range(rows):
        row = matrix[r]
        row_max = max(row)
        if row_max == float("-inf"):
            raise ValueError(f"row {r} is entirely masked, softmax is undefined")
        exponentials = [0.0 if value == float("-inf") else math.exp(value - row_max)
                        for value in row]
        total = sum(exponentials)
        if total <= 0.0:
            raise ValueError(f"row {r} produced a non-positive softmax denominator")
        for c in range(cols):
            result[r][c] = exponentials[c] / total
    return result
