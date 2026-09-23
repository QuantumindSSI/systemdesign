"""Tests for lib/sparse_attention.py.

Masks are easy to get subtly wrong in ways that look right: off by one at
the window edge, leaking a future position, or forbidding everything for
the first query. Each of those is checked against a hand-written expected
mask at a small size, because a mask compared only against itself proves
nothing.

The reachability code exists to check a formula, so it is checked against
hand-computed reach at sizes small enough to verify by eye.
"""

import math
import random
import unittest

from lib.attention import causal_mask, scaled_dot_product_attention
from lib.linalg import matmul, shape
from lib.sparse_attention import (
    NEG_INF,
    CheapIndexer,
    allowed_count,
    attention_mass_captured,
    mask_density,
    max_reach,
    reachability,
    recall_and_mass,
    row_entropy,
    selected_indices,
    selection_recall,
    sink_window_mask,
    sliding_window_mask,
    top_k_mask,
    uniform_entropy,
    window_reach_formula,
)

D_MODEL = 32
LENGTH = 12
SEED = 42


def sample_input(seed=SEED, length=LENGTH, width=D_MODEL):
    """A reproducible input sequence."""
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(width)] for _ in range(length)]


def pattern(mask):
    """Render a mask as strings, for comparison against a hand-written one."""
    return [
        "".join("." if value != NEG_INF else "x" for value in row)
        for row in mask
    ]


class TestSlidingWindowMask(unittest.TestCase):
    def test_window_of_three_at_length_five(self):
        self.assertEqual(
            pattern(sliding_window_mask(5, 3)),
            [
                ".xxxx",
                "..xxx",
                "...xx",
                "x...x",
                "xx...",
            ],
        )

    def test_window_of_one_reads_only_itself(self):
        self.assertEqual(
            pattern(sliding_window_mask(4, 1)),
            [".xxx", "x.xx", "xx.x", "xxx."],
        )

    def test_window_at_full_length_is_ordinary_causal_attention(self):
        self.assertEqual(sliding_window_mask(6, 6), causal_mask(6))

    def test_window_wider_than_the_sequence_is_still_causal(self):
        self.assertEqual(sliding_window_mask(4, 99), causal_mask(4))

    def test_no_query_ever_reads_the_future(self):
        mask = sliding_window_mask(9, 4)
        for row in range(9):
            for col in range(row + 1, 9):
                self.assertEqual(mask[row][col], NEG_INF)

    def test_every_query_can_read_at_least_itself(self):
        mask = sliding_window_mask(9, 2)
        for row in range(9):
            self.assertEqual(mask[row][row], 0.0)

    def test_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            sliding_window_mask(0, 3)
        with self.assertRaises(ValueError):
            sliding_window_mask(5, 0)


class TestSinkWindowMask(unittest.TestCase):
    def test_two_sinks_stay_readable_from_everywhere(self):
        """Window 2 means {i-1, i}; sinks add 0 and 1 to every row.

        Row 3 reads {2, 3} locally plus {0, 1}, which is everything so far,
        so its row looks dense. Row 4 reads {3, 4} plus {0, 1} and the gap
        at position 2 is the first place the window's limit is visible.
        """
        self.assertEqual(
            pattern(sink_window_mask(6, 2, 2)),
            [
                ".xxxxx",
                "..xxxx",
                "...xxx",
                "....xx",
                "..x..x",
                "..xx..",
            ],
        )

    def test_zero_sinks_is_a_plain_window(self):
        self.assertEqual(
            sink_window_mask(7, 3, 0), sliding_window_mask(7, 3)
        )

    def test_sinks_never_leak_the_future(self):
        mask = sink_window_mask(6, 2, 4)
        for row in range(6):
            for col in range(row + 1, 6):
                self.assertEqual(mask[row][col], NEG_INF)

    def test_rejects_bad_sink_counts(self):
        with self.assertRaises(ValueError):
            sink_window_mask(5, 2, -1)
        with self.assertRaises(ValueError):
            sink_window_mask(5, 2, 6)


class TestCounting(unittest.TestCase):
    def test_causal_allows_the_triangle(self):
        self.assertEqual(allowed_count(causal_mask(5)), 15)

    def test_window_allows_fewer(self):
        self.assertEqual(allowed_count(sliding_window_mask(5, 3)), 12)

    def test_density_is_against_the_full_square(self):
        self.assertAlmostEqual(mask_density(causal_mask(4)), 10.0 / 16.0)

    def test_window_density_falls_with_length(self):
        narrow = mask_density(sliding_window_mask(64, 4))
        wide = mask_density(sliding_window_mask(256, 4))
        self.assertLess(wide, narrow)


class TestReachability(unittest.TestCase):
    def test_one_layer_is_the_mask_itself(self):
        mask = sliding_window_mask(6, 3)
        reached = reachability(mask, 1)
        for row in range(6):
            for col in range(6):
                self.assertEqual(reached[row][col], mask[row][col] != NEG_INF)

    def test_two_layers_doubles_the_window_reach(self):
        self.assertEqual(max_reach(sliding_window_mask(16, 3), 1), 2)
        self.assertEqual(max_reach(sliding_window_mask(16, 3), 2), 4)
        self.assertEqual(max_reach(sliding_window_mask(16, 3), 3), 6)

    def test_measured_reach_matches_the_formula_until_the_sequence_runs_out(self):
        window, length = 4, 64
        mask = sliding_window_mask(length, window)
        for layers in (1, 2, 4, 8):
            self.assertEqual(
                max_reach(mask, layers), window_reach_formula(window, layers)
            )

    def test_reach_is_capped_by_the_sequence(self):
        """The formula keeps growing; the sequence does not."""
        mask = sliding_window_mask(8, 4)
        self.assertGreater(window_reach_formula(4, 10), 7)
        self.assertEqual(max_reach(mask, 10), 7)

    def test_a_sink_gives_full_reach_in_one_layer(self):
        self.assertEqual(max_reach(sink_window_mask(16, 2, 1), 1), 15)

    def test_rejects_a_non_square_mask(self):
        with self.assertRaises(ValueError):
            reachability([[0.0, 0.0, 0.0]], 1)

    def test_rejects_non_positive_layers(self):
        with self.assertRaises(ValueError):
            reachability(causal_mask(3), 0)

    def test_formula_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            window_reach_formula(0, 1)
        with self.assertRaises(ValueError):
            window_reach_formula(4, 0)


class TestTopKMask(unittest.TestCase):
    def test_keeps_the_highest_scoring_keys(self):
        scores = [[1.0, 5.0, 3.0, 2.0]]
        self.assertEqual(selected_indices(top_k_mask(scores, 2), 0), {1, 2})

    def test_respects_the_base_mask(self):
        """Without this, a causal model would select a future position."""
        scores = [[1.0, 9.0], [1.0, 9.0]]
        selected = top_k_mask(scores, 1, causal_mask(2))
        self.assertEqual(selected_indices(selected, 0), {0})
        self.assertEqual(selected_indices(selected, 1), {1})

    def test_keeps_everything_when_k_exceeds_the_permitted_count(self):
        selected = top_k_mask([[1.0, 2.0], [3.0, 4.0]], 5, causal_mask(2))
        self.assertEqual(selected_indices(selected, 0), {0})
        self.assertEqual(selected_indices(selected, 1), {0, 1})

    def test_ties_break_on_the_lower_index(self):
        self.assertEqual(
            selected_indices(top_k_mask([[2.0, 2.0, 1.0]], 1), 0), {0}
        )

    def test_never_produces_a_fully_masked_row(self):
        selected = top_k_mask(
            [[0.0] * LENGTH for _ in range(LENGTH)], 3, causal_mask(LENGTH)
        )
        for row in range(LENGTH):
            self.assertGreater(len(selected_indices(selected, row)), 0)

    def test_rejects_k_below_one(self):
        with self.assertRaises(ValueError):
            top_k_mask([[1.0]], 0)

    def test_rejects_a_mismatched_base_mask(self):
        with self.assertRaises(ValueError):
            top_k_mask([[1.0, 2.0]], 1, [[0.0]])

    def test_rejects_a_query_with_no_permitted_key(self):
        blocked = [[NEG_INF, NEG_INF]]
        with self.assertRaises(ValueError):
            top_k_mask([[1.0, 2.0]], 1, blocked)

    def test_selected_indices_rejects_a_bad_row(self):
        with self.assertRaises(ValueError):
            selected_indices(causal_mask(3), 3)


class TestSelectionQuality(unittest.TestCase):
    def test_identical_selections_recall_everything(self):
        reference = top_k_mask([[1.0, 2.0, 3.0]], 2)
        self.assertAlmostEqual(selection_recall(reference, reference), 1.0)

    def test_disjoint_selections_recall_nothing(self):
        reference = top_k_mask([[3.0, 2.0, 1.0]], 1)
        other = top_k_mask([[1.0, 2.0, 3.0]], 1)
        self.assertAlmostEqual(selection_recall(other, reference), 0.0)

    def test_half_overlap_recalls_half(self):
        reference = top_k_mask([[4.0, 3.0, 2.0, 1.0]], 2)
        other = top_k_mask([[4.0, 1.0, 2.0, 3.0]], 2)
        self.assertAlmostEqual(selection_recall(other, reference), 0.5)

    def test_recall_averages_over_queries(self):
        reference = top_k_mask([[3.0, 1.0], [3.0, 1.0]], 1)
        other = top_k_mask([[3.0, 1.0], [1.0, 3.0]], 1)
        self.assertAlmostEqual(selection_recall(other, reference), 0.5)

    def test_recall_rejects_shape_mismatch(self):
        with self.assertRaises(ValueError):
            selection_recall([[0.0]], [[0.0, 0.0]])

    def test_mass_of_a_full_selection_is_one(self):
        weights = [[0.5, 0.3, 0.2]]
        self.assertAlmostEqual(
            attention_mass_captured(weights, [[0.0, 0.0, 0.0]]), 1.0
        )

    def test_mass_counts_weight_not_positions(self):
        weights = [[0.9, 0.05, 0.05]]
        self.assertAlmostEqual(
            attention_mass_captured(weights, [[0.0, NEG_INF, NEG_INF]]), 0.9
        )

    def test_mass_rejects_shape_mismatch(self):
        with self.assertRaises(ValueError):
            attention_mass_captured([[1.0]], [[0.0, 0.0]])


class TestEntropy(unittest.TestCase):
    def test_uniform_row_hits_the_ceiling(self):
        row = [0.25] * 4
        self.assertAlmostEqual(row_entropy(row), uniform_entropy(4))
        self.assertAlmostEqual(uniform_entropy(4), 2.0)

    def test_one_hot_row_has_zero_entropy(self):
        self.assertAlmostEqual(row_entropy([1.0, 0.0, 0.0]), 0.0)

    def test_zeros_do_not_raise(self):
        self.assertAlmostEqual(row_entropy([0.5, 0.5, 0.0]), 1.0)

    def test_rejects_an_unnormalised_row(self):
        with self.assertRaises(ValueError):
            row_entropy([0.5, 0.2])

    def test_rejects_an_empty_row(self):
        with self.assertRaises(ValueError):
            row_entropy([])

    def test_uniform_entropy_rejects_non_positive_support(self):
        with self.assertRaises(ValueError):
            uniform_entropy(0)


class TestCheapIndexer(unittest.TestCase):
    def test_score_shape(self):
        indexer = CheapIndexer(D_MODEL, 4, SEED)
        self.assertEqual(shape(indexer.scores(sample_input())), (LENGTH, LENGTH))

    def test_cost_ratio_is_the_width_ratio(self):
        indexer = CheapIndexer(D_MODEL, 4, SEED)
        self.assertAlmostEqual(indexer.cost_ratio(8, 8), 4.0 / 64.0)

    def test_scores_are_a_bilinear_form_of_the_input(self):
        indexer = CheapIndexer(D_MODEL, 4, SEED)
        x = sample_input()
        scores = indexer.scores(x)
        queries = matmul(x, indexer.w_query)
        keys = matmul(x, indexer.w_key)
        for i in range(LENGTH):
            for j in range(LENGTH):
                expected = sum(a * b for a, b in zip(queries[i], keys[j]))
                self.assertAlmostEqual(scores[i][j], expected, places=10)

    def test_rejects_wrong_input_width(self):
        indexer = CheapIndexer(D_MODEL, 4, SEED)
        with self.assertRaises(ValueError):
            indexer.scores([[1.0, 2.0]])

    def test_rejects_bad_dimensions(self):
        with self.assertRaises(ValueError):
            CheapIndexer(0, 4, SEED)
        with self.assertRaises(ValueError):
            CheapIndexer(D_MODEL, 0, SEED)

    def test_cost_ratio_rejects_bad_dimensions(self):
        indexer = CheapIndexer(D_MODEL, 4, SEED)
        with self.assertRaises(ValueError):
            indexer.cost_ratio(0, 8)


class TestRecallAndMass(unittest.TestCase):
    def test_returns_three_values_in_range(self):
        x = sample_input()
        rng = random.Random(SEED)
        from lib.attention import glorot_matrix

        w_query = glorot_matrix(D_MODEL, 8, rng)
        w_key = glorot_matrix(D_MODEL, 8, rng)
        w_value = glorot_matrix(D_MODEL, 8, rng)
        base = causal_mask(LENGTH)
        _, weights = scaled_dot_product_attention(
            matmul(x, w_query), matmul(x, w_key), matmul(x, w_value), base
        )
        scores = matmul(matmul(x, w_query), [list(row) for row in
                                             zip(*matmul(x, w_key))])
        indexer = CheapIndexer(D_MODEL, 4, SEED + 1)
        recall, cheap, oracle = recall_and_mass(
            x, weights, scores, indexer, 4, base
        )
        for value in (recall, cheap, oracle):
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0 + 1e-12)

    def test_the_oracle_never_loses_to_the_cheap_selection_on_its_own_scores(self):
        """Selecting by the real scores must capture at least as much mass."""
        x = sample_input()
        rng = random.Random(SEED)
        from lib.attention import glorot_matrix

        w_query = glorot_matrix(D_MODEL, 8, rng)
        w_key = glorot_matrix(D_MODEL, 8, rng)
        w_value = glorot_matrix(D_MODEL, 8, rng)
        base = causal_mask(LENGTH)
        queries = matmul(x, w_query)
        keys = matmul(x, w_key)
        _, weights = scaled_dot_product_attention(
            queries, keys, matmul(x, w_value), base
        )
        scores = matmul(queries, [list(row) for row in zip(*keys)])
        indexer = CheapIndexer(D_MODEL, 4, SEED + 1)
        _, cheap, oracle = recall_and_mass(x, weights, scores, indexer, 4, base)
        self.assertGreaterEqual(oracle + 1e-12, cheap)


if __name__ == "__main__":
    unittest.main()
