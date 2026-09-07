"""Tests for lib/linalg.py: happy paths, boundaries, and error paths."""

import math
import unittest

from lib.linalg import (
    add,
    hstack,
    matmul,
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


if __name__ == "__main__":
    unittest.main()
