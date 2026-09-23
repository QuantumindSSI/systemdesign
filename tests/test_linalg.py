"""Tests for lib/linalg.py: happy paths, boundaries, and error paths."""

import math
import unittest

from lib.linalg import (
    add,
    hstack,
    matmul,
    matrix_rank,
    null_space_basis,
    reduced_row_echelon,
    scale,
    shape,
    softmax_rows,
    transpose,
    zeros,
)


class TestShape(unittest.TestCase):
    def test_rectangular(self):
        self.assertEqual(shape([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), (2, 3))

    def test_single_element(self):
        self.assertEqual(shape([[7.0]]), (1, 1))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            shape([])

    def test_zero_width_raises(self):
        with self.assertRaises(ValueError):
            shape([[]])

    def test_ragged_raises(self):
        with self.assertRaises(ValueError) as ctx:
            shape([[1.0, 2.0], [3.0]])
        self.assertIn("ragged", str(ctx.exception))


class TestMatmul(unittest.TestCase):
    def test_known_product(self):
        # [[1,2],[3,4]] @ [[5,6],[7,8]] = [[19,22],[43,50]]
        product = matmul([[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]])
        self.assertEqual(product, [[19.0, 22.0], [43.0, 50.0]])

    def test_non_square(self):
        # (2,3) @ (3,1) -> (2,1)
        product = matmul(
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], [[1.0], [1.0], [1.0]]
        )
        self.assertEqual(product, [[6.0], [15.0]])

    def test_identity_is_neutral(self):
        a = [[2.0, -1.0], [0.5, 3.0]]
        identity = [[1.0, 0.0], [0.0, 1.0]]
        self.assertEqual(matmul(a, identity), a)

    def test_inner_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError) as ctx:
            matmul([[1.0, 2.0]], [[1.0, 2.0]])
        self.assertIn("inner dimensions", str(ctx.exception))


class TestTransposeAddScale(unittest.TestCase):
    def test_transpose_roundtrip(self):
        a = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        self.assertEqual(transpose(transpose(a)), a)

    def test_transpose_shape(self):
        self.assertEqual(shape(transpose(zeros(2, 5))), (5, 2))

    def test_add(self):
        self.assertEqual(add([[1.0, 2.0]], [[3.0, 4.0]]), [[4.0, 6.0]])

    def test_add_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            add([[1.0, 2.0]], [[1.0]])

    def test_scale(self):
        self.assertEqual(scale([[1.0, -2.0]], 3.0), [[3.0, -6.0]])

    def test_zeros_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            zeros(0, 3)


class TestHstack(unittest.TestCase):
    def test_concatenates_columns(self):
        left = [[1.0], [2.0]]
        right = [[3.0, 4.0], [5.0, 6.0]]
        self.assertEqual(hstack([left, right]), [[1.0, 3.0, 4.0], [2.0, 5.0, 6.0]])

    def test_row_count_mismatch_raises(self):
        with self.assertRaises(ValueError):
            hstack([[[1.0]], [[1.0], [2.0]]])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            hstack([])


class TestSoftmaxRows(unittest.TestCase):
    def test_rows_sum_to_one(self):
        result = softmax_rows([[1.0, 2.0, 3.0], [-5.0, 0.0, 5.0]])
        for row in result:
            self.assertAlmostEqual(sum(row), 1.0, places=12)

    def test_uniform_input_gives_uniform_output(self):
        result = softmax_rows([[2.0, 2.0, 2.0, 2.0]])
        for value in result[0]:
            self.assertAlmostEqual(value, 0.25, places=12)

    def test_monotonic(self):
        row = softmax_rows([[1.0, 2.0, 3.0]])[0]
        self.assertLess(row[0], row[1])
        self.assertLess(row[1], row[2])

    def test_large_values_do_not_overflow(self):
        # Without the max subtraction, exp(1000) overflows to inf.
        result = softmax_rows([[1000.0, 1000.0, 999.0]])
        self.assertAlmostEqual(sum(result[0]), 1.0, places=12)
        self.assertTrue(all(math.isfinite(v) for v in result[0]))

    def test_shift_invariance(self):
        base = softmax_rows([[1.0, 2.0, 3.0]])[0]
        shifted = softmax_rows([[101.0, 102.0, 103.0]])[0]
        for a, b in zip(base, shifted):
            self.assertAlmostEqual(a, b, places=12)

    def test_masked_entry_gets_zero_weight(self):
        result = softmax_rows([[1.0, float("-inf"), 1.0]])[0]
        self.assertEqual(result[1], 0.0)
        self.assertAlmostEqual(result[0], 0.5, places=12)

    def test_fully_masked_row_raises(self):
        with self.assertRaises(ValueError) as ctx:
            softmax_rows([[float("-inf"), float("-inf")]])
        self.assertIn("entirely masked", str(ctx.exception))


class TestReducedRowEchelon(unittest.TestCase):
    def test_identity_is_already_reduced(self):
        echelon, pivots = reduced_row_echelon([[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(echelon, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(pivots, [0, 1])

    def test_dependent_rows_produce_a_zero_row(self):
        echelon, pivots = reduced_row_echelon([[1.0, 2.0], [2.0, 4.0]])
        self.assertEqual(pivots, [0])
        self.assertEqual(echelon[1], [0.0, 0.0])

    def test_free_column_is_skipped(self):
        _, pivots = reduced_row_echelon([[0.0, 1.0], [0.0, 0.0]])
        self.assertEqual(pivots, [1])

    def test_partial_pivoting_survives_a_tiny_leading_entry(self):
        """Without pivoting this divides by 1e-18 and loses every digit."""
        echelon, pivots = reduced_row_echelon([[1e-18, 1.0], [1.0, 1.0]])
        self.assertEqual(pivots, [0, 1])
        self.assertAlmostEqual(echelon[0][0], 1.0, places=12)
        self.assertAlmostEqual(echelon[0][1], 0.0, places=12)

    def test_rejects_non_positive_tolerance(self):
        with self.assertRaises(ValueError):
            reduced_row_echelon([[1.0]], tolerance=0.0)

    def test_rejects_ragged(self):
        with self.assertRaises(ValueError):
            reduced_row_echelon([[1.0, 2.0], [3.0]])


class TestMatrixRank(unittest.TestCase):
    def test_full_rank_identity(self):
        self.assertEqual(matrix_rank([[1.0, 0.0], [0.0, 1.0]]), 2)

    def test_rank_one(self):
        self.assertEqual(matrix_rank([[1.0, 2.0], [3.0, 6.0]]), 1)

    def test_zero_matrix_has_rank_zero(self):
        self.assertEqual(matrix_rank([[0.0, 0.0], [0.0, 0.0]]), 0)

    def test_rank_is_capped_by_the_smaller_dimension(self):
        self.assertEqual(matrix_rank([[1.0, 2.0, 3.0]]), 1)
        self.assertEqual(matrix_rank([[1.0], [2.0], [3.0]]), 1)

    def test_rank_matches_transpose(self):
        matrix = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        self.assertEqual(matrix_rank(matrix), matrix_rank(transpose(matrix)))

    def test_tolerance_decides_a_near_singular_case(self):
        nearly = [[1.0, 0.0], [0.0, 1e-12]]
        self.assertEqual(matrix_rank(nearly, tolerance=1e-15), 2)
        self.assertEqual(matrix_rank(nearly, tolerance=1e-9), 1)


class TestNullSpaceBasis(unittest.TestCase):
    def test_full_row_rank_annihilates_nothing(self):
        self.assertEqual(null_space_basis([[1.0, 0.0], [0.0, 1.0]]), [])

    def test_basis_size_is_rows_minus_rank(self):
        matrix = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]]
        self.assertEqual(len(null_space_basis(matrix)), 3 - matrix_rank(matrix))

    def test_every_basis_vector_is_annihilated_from_the_left(self):
        matrix = [[1.0, 2.0], [2.0, 4.0], [0.0, 1.0]]
        for vector in null_space_basis(matrix):
            product = matmul([vector], matrix)[0]
            for value in product:
                self.assertAlmostEqual(value, 0.0, places=12)

    def test_a_tall_random_matrix_has_the_expected_null_dimension(self):
        import random as _random

        rng = _random.Random(7)
        matrix = [[rng.gauss(0.0, 1.0) for _ in range(4)] for _ in range(11)]
        self.assertEqual(matrix_rank(matrix), 4)
        self.assertEqual(len(null_space_basis(matrix)), 7)

    def test_basis_vectors_are_independent(self):
        matrix = [[1.0], [1.0], [1.0], [1.0]]
        basis = null_space_basis(matrix)
        self.assertEqual(len(basis), 3)
        self.assertEqual(matrix_rank(basis), 3)

    def test_rejects_ragged(self):
        with self.assertRaises(ValueError):
            null_space_basis([[1.0, 2.0], [3.0]])


if __name__ == "__main__":
    unittest.main()
