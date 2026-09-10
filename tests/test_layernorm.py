"""Tests for lib/layernorm.py: normalisation, both arrangements, errors."""

import random
import unittest

from lib.layernorm import (
    DEFAULT_EPSILON,
    FeedForward,
    LayerNorm,
    TransformerBlock,
    TransformerStack,
    layer_norm,
    root_mean_square,
)

SEED = 42
D_MODEL = 8
NUM_HEADS = 2
D_HIDDEN = 16
LENGTH = 5

TOLERANCE = 1e-9
# Normalisation cannot be exact when epsilon is added to the variance, so
# a normalised row's standard deviation lands just below 1.
NORM_TOLERANCE = 1e-3


def sample_rows(rng, rows=LENGTH, width=D_MODEL):
    """A reproducible input sequence with a deliberately non-zero mean."""
    return [[rng.gauss(3.0, 2.0) for _ in range(width)] for _ in range(rows)]


class TestLayerNorm(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)
        self.rows = sample_rows(self.rng)
        self.gain = [1.0] * D_MODEL
        self.bias = [0.0] * D_MODEL

    def test_each_row_is_centred(self):
        for row in layer_norm(self.rows, self.gain, self.bias):
            self.assertAlmostEqual(sum(row) / len(row), 0.0, delta=TOLERANCE)

    def test_each_row_has_unit_variance(self):
        for row in layer_norm(self.rows, self.gain, self.bias):
            mean = sum(row) / len(row)
            variance = sum((value - mean) ** 2 for value in row) / len(row)
            self.assertAlmostEqual(variance, 1.0, delta=NORM_TOLERANCE)

    def test_rows_are_normalised_independently(self):
        # Changing row 0 must not move row 1 by anything at all.
        first = layer_norm(self.rows, self.gain, self.bias)
        changed = [list(row) for row in self.rows]
        changed[0] = [value * 100.0 for value in changed[0]]
        second = layer_norm(changed, self.gain, self.bias)
        self.assertEqual(first[1], second[1])

    def test_gain_and_bias_are_applied(self):
        gain = [2.0] * D_MODEL
        bias = [5.0] * D_MODEL
        plain = layer_norm(self.rows, self.gain, self.bias)
        scaled = layer_norm(self.rows, gain, bias)
        for plain_row, scaled_row in zip(plain, scaled):
            for base, moved in zip(plain_row, scaled_row):
                self.assertAlmostEqual(moved, base * 2.0 + 5.0, delta=TOLERANCE)

    def test_a_constant_row_does_not_divide_by_zero(self):
        result = layer_norm([[4.0] * D_MODEL], self.gain, self.bias)
        for value in result[0]:
            self.assertAlmostEqual(value, 0.0, delta=TOLERANCE)

    def test_scaling_the_input_barely_changes_the_output(self):
        # Normalisation removes scale, which is the point, but only
        # approximately: epsilon is added to the variance and does not
        # scale with the input, so (x - mu) / sqrt(var + eps) under
        # x -> 7x becomes (x - mu) / sqrt(var + eps / 49). The residual
        # difference is the epsilon term and nothing else, which is why
        # the tolerance here is 1e-4 and not machine precision.
        plain = layer_norm(self.rows, self.gain, self.bias)
        scaled_input = [[value * 7.0 for value in row] for row in self.rows]
        scaled = layer_norm(scaled_input, self.gain, self.bias)
        for left_row, right_row in zip(plain, scaled):
            for left, right in zip(left_row, right_row):
                self.assertAlmostEqual(left, right, delta=1e-4)

    def test_scale_invariance_becomes_exact_as_epsilon_shrinks(self):
        # Confirms the previous test's explanation rather than assuming it.
        rows = self.rows
        scaled_input = [[value * 7.0 for value in row] for row in rows]
        gaps = []
        for epsilon in (1e-5, 1e-9, 1e-13):
            plain = layer_norm(rows, self.gain, self.bias, epsilon)
            scaled = layer_norm(scaled_input, self.gain, self.bias, epsilon)
            gaps.append(
                max(
                    abs(left - right)
                    for left_row, right_row in zip(plain, scaled)
                    for left, right in zip(left_row, right_row)
                )
            )
        for larger, smaller in zip(gaps, gaps[1:]):
            self.assertLess(smaller, larger)

    def test_rejects_wrong_gain_or_bias_length(self):
        with self.assertRaises(ValueError):
            layer_norm(self.rows, [1.0] * (D_MODEL + 1), self.bias)
        with self.assertRaises(ValueError):
            layer_norm(self.rows, self.gain, [0.0] * (D_MODEL - 1))

    def test_rejects_non_positive_epsilon(self):
        with self.assertRaises(ValueError):
            layer_norm(self.rows, self.gain, self.bias, epsilon=0.0)


class TestLayerNormClass(unittest.TestCase):
    def test_fresh_gain_and_bias_are_identity_like(self):
        norm = LayerNorm(D_MODEL)
        self.assertEqual(norm.gain, [1.0] * D_MODEL)
        self.assertEqual(norm.bias, [0.0] * D_MODEL)

    def test_forward_matches_the_function(self):
        rng = random.Random(SEED)
        rows = sample_rows(rng)
        norm = LayerNorm(D_MODEL)
        self.assertEqual(
            norm.forward(rows),
            layer_norm(rows, norm.gain, norm.bias, DEFAULT_EPSILON),
        )

    def test_rejects_non_positive_width(self):
        with self.assertRaises(ValueError):
            LayerNorm(0)


class TestFeedForward(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)
        self.network = FeedForward(D_MODEL, D_HIDDEN, self.rng)

    def test_shape_is_preserved(self):
        rows = sample_rows(self.rng)
        out = self.network.forward(rows)
        self.assertEqual(len(out), LENGTH)
        self.assertEqual(len(out[0]), D_MODEL)

    def test_rows_are_processed_independently(self):
        rows = sample_rows(self.rng)
        first = self.network.forward(rows)
        changed = [list(row) for row in rows]
        changed[0] = [value + 50.0 for value in changed[0]]
        second = self.network.forward(changed)
        for left, right in zip(first[1], second[1]):
            self.assertAlmostEqual(left, right, delta=TOLERANCE)

    def test_rejects_wrong_width(self):
        with self.assertRaises(ValueError):
            self.network.forward([[0.0] * (D_MODEL + 1)])

    def test_rejects_non_positive_dims(self):
        with self.assertRaises(ValueError):
            FeedForward(0, D_HIDDEN, self.rng)


class TestArrangementsDiffer(unittest.TestCase):
    """The two placements are not two spellings of one thing."""

    def setUp(self):
        self.rng = random.Random(SEED)
        self.rows = sample_rows(self.rng)

    def build(self, norm_first):
        return TransformerBlock(D_MODEL, NUM_HEADS, D_HIDDEN, SEED, norm_first)

    def test_identical_weights_produce_different_outputs(self):
        pre = self.build(True).forward(self.rows)
        post = self.build(False).forward(self.rows)
        self.assertNotEqual(pre, post)

    def test_post_norm_output_rows_are_normalised(self):
        # Post-LN ends on a LayerNorm, so every row leaving the block has
        # zero mean by construction. This is the property that keeps the
        # residual stream from growing.
        for row in self.build(False).forward(self.rows):
            self.assertAlmostEqual(sum(row) / len(row), 0.0, delta=TOLERANCE)

    def test_pre_norm_output_rows_are_not_normalised(self):
        means = [
            abs(sum(row) / len(row)) for row in self.build(True).forward(self.rows)
        ]
        self.assertGreater(max(means), TOLERANCE)

    def test_shape_is_preserved_by_both(self):
        for norm_first in (True, False):
            out = self.build(norm_first).forward(self.rows)
            self.assertEqual(len(out), LENGTH)
            self.assertEqual(len(out[0]), D_MODEL)

    def test_rejects_wrong_width(self):
        with self.assertRaises(ValueError):
            self.build(True).forward([[0.0] * (D_MODEL + 1)])


class TestTransformerStack(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)
        self.rows = sample_rows(self.rng)

    def build(self, norm_first, layers=4):
        return TransformerStack(
            D_MODEL, NUM_HEADS, D_HIDDEN, layers, SEED, norm_first
        )

    def test_both_arrangements_hold_identical_weights(self):
        # Any measured difference must be the arrangement, not the seed.
        pre = self.build(True)
        post = self.build(False)
        for pre_block, post_block in zip(pre.blocks, post.blocks):
            self.assertEqual(
                pre_block.attention.w_output, post_block.attention.w_output
            )
            self.assertEqual(
                pre_block.feed_forward.w_in, post_block.feed_forward.w_in
            )

    def test_activations_has_one_entry_per_block_plus_the_input(self):
        trace = self.build(True).activations(self.rows)
        self.assertEqual(len(trace), 5)
        self.assertEqual(trace[0], [list(row) for row in self.rows])

    def test_activations_are_copies(self):
        trace = self.build(True).activations(self.rows)
        trace[0][0][0] = 999.0
        self.assertNotEqual(self.rows[0][0], 999.0)

    def test_post_norm_residual_stream_stays_bounded(self):
        trace = self.build(False, layers=6).activations(self.rows)
        sizes = [root_mean_square(step) for step in trace[1:]]
        self.assertLess(max(sizes) / min(sizes), 2.0)

    def test_pre_norm_residual_stream_grows_with_depth(self):
        trace = self.build(True, layers=6).activations(self.rows)
        sizes = [root_mean_square(step) for step in trace]
        self.assertGreater(sizes[-1], sizes[0])

    def test_rejects_zero_layers(self):
        with self.assertRaises(ValueError):
            self.build(True, layers=0)


class TestRootMeanSquare(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(root_mean_square([[3.0, 4.0]]), 3.5355339, places=6)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            root_mean_square([])


if __name__ == "__main__":
    unittest.main()
