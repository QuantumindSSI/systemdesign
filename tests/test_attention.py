"""Tests for lib/attention.py: shapes, invariants, masking, error paths."""

import math
import unittest

from lib.attention import (
    AttentionHead,
    MultiHeadSelfAttention,
    causal_mask,
    glorot_matrix,
    scaled_dot_product_attention,
)
from lib.linalg import shape

import random


def sequence(n_rows: int, width: int, seed: int = 7):
    """Deterministic (n_rows, width) input sequence for tests."""
    rng = random.Random(seed)
    return [[rng.uniform(-1.0, 1.0) for _ in range(width)] for _ in range(n_rows)]


class TestCausalMask(unittest.TestCase):
    def test_lower_triangle_is_open(self):
        mask = causal_mask(3)
        self.assertEqual(mask[0][0], 0.0)
        self.assertEqual(mask[2][0], 0.0)
        self.assertEqual(mask[2][2], 0.0)

    def test_upper_triangle_is_closed(self):
        mask = causal_mask(3)
        self.assertEqual(mask[0][1], float("-inf"))
        self.assertEqual(mask[0][2], float("-inf"))
        self.assertEqual(mask[1][2], float("-inf"))

    def test_shape(self):
        self.assertEqual(shape(causal_mask(5)), (5, 5))

    def test_non_positive_raises(self):
        with self.assertRaises(ValueError):
            causal_mask(0)


class TestScaledDotProductAttention(unittest.TestCase):
    def test_output_and_weight_shapes(self):
        queries = sequence(3, 4)
        keys = sequence(5, 4, seed=8)
        values = sequence(5, 2, seed=9)
        output, weights = scaled_dot_product_attention(queries, keys, values)
        self.assertEqual(shape(output), (3, 2))
        self.assertEqual(shape(weights), (3, 5))

    def test_weights_are_a_distribution(self):
        output, weights = scaled_dot_product_attention(
            sequence(4, 6), sequence(4, 6, seed=2), sequence(4, 3, seed=3)
        )
        del output
        for row in weights:
            self.assertAlmostEqual(sum(row), 1.0, places=12)
            self.assertTrue(all(0.0 <= value <= 1.0 for value in row))

    def test_identical_keys_give_uniform_attention(self):
        # If every key is the same, no query can prefer any position.
        keys = [[1.0, 1.0]] * 4
        queries = [[0.3, -0.7]]
        values = [[float(i), 0.0] for i in range(4)]
        _, weights = scaled_dot_product_attention(queries, keys, values)
        for value in weights[0]:
            self.assertAlmostEqual(value, 0.25, places=12)

    def test_output_is_a_convex_combination_of_values(self):
        # Every output coordinate must lie within the range of that value column.
        values = [[1.0], [5.0], [9.0]]
        output, _ = scaled_dot_product_attention(
            sequence(2, 3), sequence(3, 3, seed=4), values
        )
        for row in output:
            self.assertGreaterEqual(row[0], 1.0 - 1e-9)
            self.assertLessEqual(row[0], 9.0 + 1e-9)

    def test_causal_mask_zeroes_the_future(self):
        queries = sequence(4, 3)
        keys = sequence(4, 3, seed=11)
        values = sequence(4, 3, seed=12)
        _, weights = scaled_dot_product_attention(
            queries, keys, values, mask=causal_mask(4)
        )
        for row_index, row in enumerate(weights):
            for col_index, value in enumerate(row):
                if col_index > row_index:
                    self.assertEqual(value, 0.0)
            self.assertAlmostEqual(sum(row), 1.0, places=12)

    def test_first_position_under_causal_mask_attends_only_to_itself(self):
        _, weights = scaled_dot_product_attention(
            sequence(3, 2), sequence(3, 2, seed=5), sequence(3, 2, seed=6),
            mask=causal_mask(3),
        )
        self.assertAlmostEqual(weights[0][0], 1.0, places=12)

    def test_scaling_is_actually_applied(self):
        # With d_k = 4, scores are divided by 2. Build q, k so the raw
        # score is exactly 8, hence 4 after scaling, and check the softmax
        # against the value computed from the scaled score.
        queries = [[1.0, 1.0, 1.0, 1.0]]
        keys = [[2.0, 2.0, 2.0, 2.0], [0.0, 0.0, 0.0, 0.0]]
        values = [[1.0], [0.0]]
        output, weights = scaled_dot_product_attention(queries, keys, values)
        expected_hot = math.exp(4.0) / (math.exp(4.0) + math.exp(0.0))
        self.assertAlmostEqual(weights[0][0], expected_hot, places=12)
        self.assertAlmostEqual(output[0][0], expected_hot, places=12)

    def test_key_width_mismatch_raises(self):
        with self.assertRaises(ValueError):
            scaled_dot_product_attention([[1.0, 2.0]], [[1.0]], [[1.0]])

    def test_value_row_mismatch_raises(self):
        with self.assertRaises(ValueError) as ctx:
            scaled_dot_product_attention(
                [[1.0, 2.0]], [[1.0, 2.0], [3.0, 4.0]], [[1.0]]
            )
        self.assertIn("exactly one value", str(ctx.exception))

    def test_mask_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            scaled_dot_product_attention(
                sequence(2, 2), sequence(2, 2, seed=1), sequence(2, 2, seed=2),
                mask=causal_mask(3),
            )


class TestGlorotMatrix(unittest.TestCase):
    def test_shape_and_bounds(self):
        rng = random.Random(1)
        matrix = glorot_matrix(4, 6, rng)
        self.assertEqual(shape(matrix), (4, 6))
        limit = math.sqrt(6.0 / 10.0)
        for row in matrix:
            for value in row:
                self.assertLessEqual(abs(value), limit)

    def test_same_seed_same_matrix(self):
        a = glorot_matrix(3, 3, random.Random(42))
        b = glorot_matrix(3, 3, random.Random(42))
        self.assertEqual(a, b)

    def test_non_positive_raises(self):
        with self.assertRaises(ValueError):
            glorot_matrix(0, 3, random.Random(1))


class TestAttentionHead(unittest.TestCase):
    def test_output_shape_is_d_head(self):
        head = AttentionHead(d_model=8, d_head=2, rng=random.Random(3))
        output, weights = head.forward(sequence(5, 8))
        self.assertEqual(shape(output), (5, 2))
        self.assertEqual(shape(weights), (5, 5))

    def test_wrong_input_width_raises(self):
        head = AttentionHead(d_model=8, d_head=2, rng=random.Random(3))
        with self.assertRaises(ValueError) as ctx:
            head.forward(sequence(5, 7))
        self.assertIn("expects 8", str(ctx.exception))

    def test_non_positive_dims_raise(self):
        with self.assertRaises(ValueError):
            AttentionHead(d_model=0, d_head=2, rng=random.Random(3))


class TestMultiHeadSelfAttention(unittest.TestCase):
    def test_output_width_equals_d_model(self):
        attention = MultiHeadSelfAttention(d_model=12, num_heads=3, seed=42)
        output, per_head = attention.forward(sequence(6, 12))
        self.assertEqual(shape(output), (6, 12))
        self.assertEqual(len(per_head), 3)
        for weights in per_head:
            self.assertEqual(shape(weights), (6, 6))

    def test_heads_split_the_width(self):
        attention = MultiHeadSelfAttention(d_model=12, num_heads=4, seed=1)
        self.assertEqual(attention.d_head, 3)
        self.assertEqual(attention.num_heads * attention.d_head, attention.d_model)

    def test_heads_learn_different_projections(self):
        attention = MultiHeadSelfAttention(d_model=8, num_heads=2, seed=5)
        self.assertNotEqual(attention.heads[0].w_query, attention.heads[1].w_query)

    def test_same_seed_reproduces_output(self):
        x = sequence(4, 8)
        first, _ = MultiHeadSelfAttention(8, 2, seed=99).forward(x)
        second, _ = MultiHeadSelfAttention(8, 2, seed=99).forward(x)
        self.assertEqual(first, second)

    def test_causal_mask_propagates_to_every_head(self):
        attention = MultiHeadSelfAttention(d_model=8, num_heads=2, seed=7)
        _, per_head = attention.forward(sequence(4, 8), mask=causal_mask(4))
        for weights in per_head:
            self.assertEqual(weights[0][1], 0.0)
            self.assertEqual(weights[1][3], 0.0)

    def test_indivisible_width_raises(self):
        with self.assertRaises(ValueError) as ctx:
            MultiHeadSelfAttention(d_model=10, num_heads=4, seed=1)
        self.assertIn("not divisible", str(ctx.exception))

    def test_zero_heads_raises(self):
        with self.assertRaises(ValueError):
            MultiHeadSelfAttention(d_model=8, num_heads=0, seed=1)

    def test_single_head_is_permitted(self):
        attention = MultiHeadSelfAttention(d_model=4, num_heads=1, seed=2)
        output, per_head = attention.forward(sequence(3, 4))
        self.assertEqual(shape(output), (3, 4))
        self.assertEqual(len(per_head), 1)


if __name__ == "__main__":
    unittest.main()
