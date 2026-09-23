"""Tests for lib/feedforward.py.

Three things are worth locking down. The activations must be the functions
they claim to be, checked against values computable by hand. The parameter
arithmetic must be arithmetic, so an article can quote it. And the
decomposition must reproduce the matrix multiply exactly, because the
articles use it to argue that a feed-forward output is a sum of per-unit
contributions, and an argument that is only approximately true is a
different argument.
"""

import math
import random
import unittest

from lib.feedforward import (
    ACTIVATIONS,
    FeedForward,
    GatedFeedForward,
    ParameterCount,
    decompose_output,
    dominant_units,
    equivalent_gated_hidden,
    gelu,
    gelu_tanh,
    parameter_count,
    relu,
    resolve_activation,
    silu,
    sparsity,
)
from lib.linalg import shape

D_MODEL = 8
D_HIDDEN = 32
LENGTH = 6
SEED = 42


def sample_input(seed=SEED, length=LENGTH, width=D_MODEL):
    """A reproducible input sequence."""
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(width)] for _ in range(length)]


class TestActivations(unittest.TestCase):
    def test_relu_clips_at_zero(self):
        self.assertEqual(relu(-3.5), 0.0)
        self.assertEqual(relu(0.0), 0.0)
        self.assertEqual(relu(2.25), 2.25)

    def test_gelu_is_zero_at_the_origin(self):
        self.assertEqual(gelu(0.0), 0.0)

    def test_gelu_halves_nothing_and_passes_large_values(self):
        """Far right it is the identity, far left it is nearly zero."""
        self.assertAlmostEqual(gelu(8.0), 8.0, places=10)
        self.assertAlmostEqual(gelu(-8.0), 0.0, places=10)

    def test_gelu_is_never_exactly_zero_for_a_finite_negative(self):
        self.assertNotEqual(gelu(-1.0), 0.0)
        self.assertLess(gelu(-1.0), 0.0)

    def test_gelu_tanh_approximates_the_exact_function(self):
        for value in (-2.0, -0.5, 0.0, 0.5, 2.0):
            self.assertLess(abs(gelu(value) - gelu_tanh(value)), 0.005)

    def test_gelu_tanh_is_not_the_exact_function(self):
        """If these agreed exactly there would be no reason to ship both."""
        worst = max(
            abs(gelu(value / 10.0) - gelu_tanh(value / 10.0))
            for value in range(-40, 41)
        )
        self.assertGreater(worst, 1e-6)

    def test_silu_matches_its_definition(self):
        for value in (-3.0, -0.25, 0.0, 0.25, 3.0):
            expected = value / (1.0 + math.exp(-value))
            self.assertAlmostEqual(silu(value), expected, places=12)

    def test_silu_survives_a_large_negative_input(self):
        """The naive form overflows exp(-value) here; this one must not."""
        self.assertAlmostEqual(silu(-800.0), 0.0, places=12)

    def test_silu_survives_a_large_positive_input(self):
        self.assertAlmostEqual(silu(800.0), 800.0, places=9)

    def test_resolve_activation_finds_every_advertised_name(self):
        for name in ACTIVATIONS:
            self.assertTrue(callable(resolve_activation(name)))

    def test_resolve_activation_rejects_an_unknown_name(self):
        with self.assertRaises(ValueError):
            resolve_activation("mish")


class TestParameterCount(unittest.TestCase):
    def test_attention_is_four_square_projections(self):
        counted = parameter_count(512, 2048)
        self.assertEqual(counted.attention, 4 * 512 * 512)

    def test_ungated_feed_forward_is_two_matrices(self):
        counted = parameter_count(512, 2048)
        self.assertEqual(counted.feed_forward, 2 * 512 * 2048)

    def test_gated_feed_forward_is_three_matrices(self):
        counted = parameter_count(512, 2048, gated=True)
        self.assertEqual(counted.feed_forward, 3 * 512 * 2048)

    def test_the_original_configuration_is_exactly_two_thirds(self):
        """d_ff = 4 * d_model makes the feed-forward share exactly 2/3."""
        counted = parameter_count(512, 2048)
        self.assertEqual(counted.feed_forward, 2 * counted.attention)
        self.assertAlmostEqual(counted.feed_forward_share, 2.0 / 3.0, places=12)

    def test_two_thirds_holds_at_any_width_when_d_ff_is_four_d_model(self):
        for width in (64, 768, 1024, 4096):
            counted = parameter_count(width, 4 * width)
            self.assertAlmostEqual(
                counted.feed_forward_share, 2.0 / 3.0, places=12
            )

    def test_total_is_both_sublayers(self):
        counted = ParameterCount(attention=10, feed_forward=20)
        self.assertEqual(counted.total, 30)
        self.assertAlmostEqual(counted.feed_forward_share, 2.0 / 3.0)

    def test_rejects_non_positive_widths(self):
        with self.assertRaises(ValueError):
            parameter_count(0, 16)
        with self.assertRaises(ValueError):
            parameter_count(16, -1)


class TestEquivalentGatedHidden(unittest.TestCase):
    def test_two_thirds_rounded_down_to_a_multiple_of_eight(self):
        self.assertEqual(equivalent_gated_hidden(2048), 1360)

    def test_result_keeps_the_gated_block_at_or_under_parity(self):
        for d_model, d_hidden in ((512, 2048), (768, 3072), (4096, 16384)):
            gated_hidden = equivalent_gated_hidden(d_hidden)
            ungated = parameter_count(d_model, d_hidden).feed_forward
            gated = parameter_count(d_model, gated_hidden, gated=True)
            self.assertLessEqual(gated.feed_forward, ungated)
            self.assertGreater(gated.feed_forward, 0.99 * ungated)

    def test_result_is_a_multiple_of_eight(self):
        for d_hidden in (2048, 3072, 11008, 16384):
            self.assertEqual(equivalent_gated_hidden(d_hidden) % 8, 0)

    def test_never_returns_below_eight(self):
        self.assertEqual(equivalent_gated_hidden(1), 8)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            equivalent_gated_hidden(0)


class TestSparsity(unittest.TestCase):
    def test_counts_exact_zeros_only(self):
        self.assertAlmostEqual(sparsity([[0.0, 1.0], [0.0, -1e-18]]), 0.5)

    def test_all_zero_matrix(self):
        self.assertEqual(sparsity([[0.0, 0.0]]), 1.0)

    def test_no_zero_matrix(self):
        self.assertEqual(sparsity([[1.0, -2.0]]), 0.0)

    def test_rejects_ragged(self):
        with self.assertRaises(ValueError):
            sparsity([[0.0], [0.0, 1.0]])


class TestFeedForward(unittest.TestCase):
    def test_output_shape(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(shape(network.forward(sample_input())), (LENGTH, D_MODEL))

    def test_hidden_shape(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(shape(network.hidden(sample_input())), (LENGTH, D_HIDDEN))

    def test_relu_hidden_has_exact_zeros(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "relu")
        self.assertGreater(sparsity(network.hidden(sample_input())), 0.0)

    def test_gelu_hidden_has_no_exact_zeros(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "gelu")
        self.assertEqual(sparsity(network.hidden(sample_input())), 0.0)

    def test_positions_are_independent(self):
        """Row i's output must not depend on row j. That is what position-wise means."""
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        rows = sample_input()
        together = network.forward(rows)
        alone = network.forward([rows[2]])
        for index, value in enumerate(alone[0]):
            self.assertAlmostEqual(value, together[2][index], places=12)

    def test_rejects_wrong_input_width(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        with self.assertRaises(ValueError):
            network.forward([[1.0, 2.0]])

    def test_rejects_non_positive_dims(self):
        with self.assertRaises(ValueError):
            FeedForward(0, D_HIDDEN, random.Random(SEED))

    def test_rejects_unknown_activation(self):
        with self.assertRaises(ValueError):
            FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "sigmoid")

    def test_same_seed_gives_the_same_network(self):
        left = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        right = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(left.forward(sample_input()), right.forward(sample_input()))

    def test_parameters_reports_the_ungated_count(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(network.parameters().feed_forward, 2 * D_MODEL * D_HIDDEN)


class TestGatedFeedForward(unittest.TestCase):
    def test_output_shape(self):
        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(shape(network.forward(sample_input())), (LENGTH, D_MODEL))

    def test_hidden_shape(self):
        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(shape(network.hidden(sample_input())), (LENGTH, D_HIDDEN))

    def test_gating_is_elementwise_product_of_two_projections(self):
        from lib.linalg import matmul

        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "silu")
        rows = sample_input()
        gate = matmul(rows, network.w_gate)
        value = matmul(rows, network.w_in)
        hidden = network.hidden(rows)
        for r in range(LENGTH):
            for c in range(D_HIDDEN):
                self.assertAlmostEqual(
                    hidden[r][c], silu(gate[r][c]) * value[r][c], places=12
                )

    def test_positions_are_independent(self):
        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        rows = sample_input()
        together = network.forward(rows)
        alone = network.forward([rows[4]])
        for index, value in enumerate(alone[0]):
            self.assertAlmostEqual(value, together[4][index], places=12)

    def test_parameters_reports_the_gated_count(self):
        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        self.assertEqual(network.parameters().feed_forward, 3 * D_MODEL * D_HIDDEN)

    def test_rejects_wrong_input_width(self):
        network = GatedFeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        with self.assertRaises(ValueError):
            network.forward([[1.0]])

    def test_rejects_non_positive_dims(self):
        with self.assertRaises(ValueError):
            GatedFeedForward(D_MODEL, 0, random.Random(SEED))


class TestDecomposition(unittest.TestCase):
    """The identity the Tuesday articles rest on."""

    def test_terms_sum_to_the_matrix_multiply(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        rows = sample_input()
        hidden = network.hidden(rows)
        output = network.forward(rows)
        for position in range(LENGTH):
            terms = decompose_output(hidden[position], network.w_out)
            summed = [
                sum(term[dim] for term in terms) for dim in range(D_MODEL)
            ]
            for dim in range(D_MODEL):
                self.assertAlmostEqual(summed[dim], output[position][dim], places=10)

    def test_term_shape(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        hidden = network.hidden(sample_input())
        terms = decompose_output(hidden[0], network.w_out)
        self.assertEqual(shape(terms), (D_HIDDEN, D_MODEL))

    def test_a_zero_activation_contributes_a_zero_term(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED), "relu")
        hidden = network.hidden(sample_input())
        terms = decompose_output(hidden[0], network.w_out)
        for index, weight in enumerate(hidden[0]):
            if weight == 0.0:
                self.assertEqual(terms[index], [0.0] * D_MODEL)

    def test_rejects_width_mismatch(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        with self.assertRaises(ValueError):
            decompose_output([1.0, 2.0], network.w_out)


class TestDominantUnits(unittest.TestCase):
    def test_returns_the_requested_count_sorted_descending(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        hidden = network.hidden(sample_input())
        top = dominant_units(hidden[0], network.w_out, 5)
        self.assertEqual(len(top), 5)
        lengths = [length for _, length in top]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_ranks_by_term_length_not_by_activation(self):
        """A large activation on a short output row must not win."""
        hidden_row = [10.0, 1.0]
        w_out = [[0.001, 0.0], [0.0, 100.0]]
        top = dominant_units(hidden_row, w_out, 1)
        self.assertEqual(top[0][0], 1)

    def test_ties_break_on_index(self):
        top = dominant_units([1.0, 1.0], [[1.0, 0.0], [0.0, 1.0]], 2)
        self.assertEqual([index for index, _ in top], [0, 1])

    def test_rejects_a_count_out_of_range(self):
        network = FeedForward(D_MODEL, D_HIDDEN, random.Random(SEED))
        hidden = network.hidden(sample_input())
        with self.assertRaises(ValueError):
            dominant_units(hidden[0], network.w_out, 0)
        with self.assertRaises(ValueError):
            dominant_units(hidden[0], network.w_out, D_HIDDEN + 1)


if __name__ == "__main__":
    unittest.main()
