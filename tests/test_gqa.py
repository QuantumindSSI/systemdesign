"""Tests for lib/gqa.py.

The cache arithmetic is the load-bearing claim, so it is checked against
numbers computed by hand rather than against the function's own output.
The grouping is checked for the property that gives it its name: two query
heads in the same group must read literally the same keys, which shows up
as a specific relationship between their attention patterns that heads in
different groups do not have.
"""

import random
import unittest

from lib.gqa import (
    DEFAULT_BYTES_PER_ELEMENT,
    GroupedQueryAttention,
    blind_directions,
    distinct_key_spaces,
    group_assignment,
    head_pattern_similarity,
    key_subspace_rank,
    kv_cache_bytes,
)
from lib.linalg import matmul, shape

D_MODEL = 32
NUM_QUERY_HEADS = 8
LENGTH = 10
SEED = 42


def sample_input(seed=SEED, length=LENGTH, width=D_MODEL):
    """A reproducible input sequence."""
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(width)] for _ in range(length)]


class TestGroupAssignment(unittest.TestCase):
    def test_multi_head_gives_every_query_head_its_own(self):
        self.assertEqual(group_assignment(8, 8), [0, 1, 2, 3, 4, 5, 6, 7])

    def test_multi_query_puts_every_head_in_one_group(self):
        self.assertEqual(group_assignment(8, 1), [0] * 8)

    def test_grouped_assigns_contiguous_blocks(self):
        self.assertEqual(group_assignment(8, 4), [0, 0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(group_assignment(8, 2), [0, 0, 0, 0, 1, 1, 1, 1])

    def test_rejects_an_uneven_split(self):
        with self.assertRaises(ValueError):
            group_assignment(8, 3)

    def test_rejects_more_kv_heads_than_query_heads(self):
        with self.assertRaises(ValueError):
            group_assignment(4, 8)

    def test_rejects_zero_heads(self):
        with self.assertRaises(ValueError):
            group_assignment(0, 1)
        with self.assertRaises(ValueError):
            group_assignment(8, 0)


class TestCacheArithmetic(unittest.TestCase):
    def test_matches_hand_arithmetic(self):
        """8 kv heads, 128 wide, 2 bytes: 2 * 8 * 128 * 2 = 4096 per layer."""
        size = kv_cache_bytes(
            num_kv_heads=8, d_head=128, num_layers=32, sequence_length=1
        )
        self.assertEqual(size.bytes_per_token_per_layer, 4096)
        self.assertEqual(size.bytes_per_token, 4096 * 32)
        self.assertEqual(size.total_bytes, 4096 * 32)

    def test_scales_linearly_in_sequence_length(self):
        one = kv_cache_bytes(8, 128, 32, 1)
        many = kv_cache_bytes(8, 128, 32, 4096)
        self.assertEqual(many.total_bytes, one.total_bytes * 4096)

    def test_scales_exactly_linearly_in_kv_heads(self):
        """This is the whole saving, so it must be exact and not approximate."""
        full = kv_cache_bytes(64, 128, 80, 32768)
        grouped = kv_cache_bytes(8, 128, 80, 32768)
        single = kv_cache_bytes(1, 128, 80, 32768)
        self.assertEqual(full.total_bytes, grouped.total_bytes * 8)
        self.assertEqual(grouped.total_bytes, single.total_bytes * 8)
        self.assertEqual(full.total_bytes, single.total_bytes * 64)

    def test_gibibytes_conversion(self):
        """4 bytes per token here: 2 tensors, 1 head, width 1, 2 bytes each."""
        size = kv_cache_bytes(1, 1, 1, 1024 ** 3 // 8)
        self.assertEqual(size.bytes_per_token_per_layer, 4)
        self.assertAlmostEqual(size.gibibytes, 0.5, places=9)

    def test_rejects_every_non_positive_argument(self):
        for kwargs in (
            {"num_kv_heads": 0},
            {"d_head": 0},
            {"num_layers": 0},
            {"sequence_length": 0},
            {"bytes_per_element": 0},
        ):
            base = {
                "num_kv_heads": 8,
                "d_head": 64,
                "num_layers": 4,
                "sequence_length": 16,
            }
            base.update(kwargs)
            with self.assertRaises(ValueError):
                kv_cache_bytes(**base)


class TestConstruction(unittest.TestCase):
    def test_multi_head_holds_one_key_projection_per_query_head(self):
        layer = GroupedQueryAttention(D_MODEL, 8, 8, SEED)
        self.assertEqual(len(layer.w_key), 8)
        self.assertEqual(distinct_key_spaces(layer), 8)

    def test_multi_query_holds_exactly_one(self):
        layer = GroupedQueryAttention(D_MODEL, 8, 1, SEED)
        self.assertEqual(len(layer.w_key), 1)
        self.assertEqual(distinct_key_spaces(layer), 1)

    def test_query_projections_never_shrink(self):
        for kv_heads in (1, 2, 4, 8):
            layer = GroupedQueryAttention(D_MODEL, 8, kv_heads, SEED)
            self.assertEqual(len(layer.w_query), 8)

    def test_query_weights_are_identical_across_arrangements(self):
        """The comparison is only about grouping if the queries match."""
        full = GroupedQueryAttention(D_MODEL, 8, 8, SEED)
        grouped = GroupedQueryAttention(D_MODEL, 8, 2, SEED)
        single = GroupedQueryAttention(D_MODEL, 8, 1, SEED)
        self.assertEqual(full.w_query, grouped.w_query)
        self.assertEqual(full.w_query, single.w_query)

    def test_first_key_projection_is_also_shared_across_arrangements(self):
        full = GroupedQueryAttention(D_MODEL, 8, 8, SEED)
        single = GroupedQueryAttention(D_MODEL, 8, 1, SEED)
        self.assertEqual(full.w_key[0], single.w_key[0])

    def test_rejects_indivisible_width(self):
        with self.assertRaises(ValueError):
            GroupedQueryAttention(30, 8, 8, SEED)

    def test_group_size_is_reported(self):
        self.assertEqual(GroupedQueryAttention(D_MODEL, 8, 2, SEED).group_size, 4)


class TestForward(unittest.TestCase):
    def test_output_width_is_unchanged_by_grouping(self):
        x = sample_input()
        for kv_heads in (1, 2, 4, 8):
            layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
            output, _ = layer.forward(x)
            self.assertEqual(shape(output), (LENGTH, D_MODEL))

    def test_one_weight_matrix_per_query_head_not_per_kv_head(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 2, SEED)
        _, weights = layer.forward(sample_input())
        self.assertEqual(len(weights), NUM_QUERY_HEADS)

    def test_every_weight_row_sums_to_one(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 2, SEED)
        _, weights = layer.forward(sample_input())
        for head in weights:
            for row in head:
                self.assertAlmostEqual(sum(row), 1.0, places=10)

    def test_heads_in_one_group_read_the_same_keys(self):
        """The defining property: shared keys, so shared key projections."""
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 2, SEED)
        self.assertEqual(layer.groups[0], layer.groups[3])
        self.assertNotEqual(layer.groups[0], layer.groups[4])

    def test_multi_query_scores_differ_only_through_the_query_projection(self):
        """With one shared key head, head h's scores are x Wq_h Wk^T x^T."""
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 1, SEED)
        x = sample_input()
        _, weights = layer.forward(x)
        keys = matmul(x, layer.w_key[0])
        for head in range(NUM_QUERY_HEADS):
            queries = matmul(x, layer.w_query[head])
            from lib.attention import scaled_dot_product_attention

            _, expected = scaled_dot_product_attention(
                queries, keys, matmul(x, layer.w_value[0])
            )
            self.assertEqual(weights[head], expected)

    def test_mask_is_honoured(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 2, SEED)
        mask = [
            [0.0 if col <= row else float("-inf") for col in range(LENGTH)]
            for row in range(LENGTH)
        ]
        _, weights = layer.forward(sample_input(), mask)
        for head in weights:
            for row_index, row in enumerate(head):
                for col_index, value in enumerate(row):
                    if col_index > row_index:
                        self.assertEqual(value, 0.0)

    def test_rejects_wrong_input_width(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 2, SEED)
        with self.assertRaises(ValueError):
            layer.forward([[1.0, 2.0]])

    def test_grouping_changes_the_output(self):
        """If these agreed, grouping would be free and the week is pointless."""
        x = sample_input()
        full, _ = GroupedQueryAttention(D_MODEL, 8, 8, SEED).forward(x)
        single, _ = GroupedQueryAttention(D_MODEL, 8, 1, SEED).forward(x)
        worst = max(
            abs(full[r][c] - single[r][c])
            for r in range(LENGTH)
            for c in range(D_MODEL)
        )
        self.assertGreater(worst, 1e-6)


class TestKeySubspace(unittest.TestCase):
    """The structural cost of grouping, separate from the memory saving."""

    def test_multi_head_keys_span_the_whole_stream(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, NUM_QUERY_HEADS, SEED)
        self.assertEqual(key_subspace_rank(layer), D_MODEL)

    def test_rank_is_kv_heads_times_head_width(self):
        for kv_heads in (1, 2, 4, 8):
            layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
            self.assertEqual(
                key_subspace_rank(layer), kv_heads * layer.d_head
            )

    def test_multi_head_has_no_blind_directions(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, NUM_QUERY_HEADS, SEED)
        self.assertEqual(blind_directions(layer), [])

    def test_blind_subspace_fills_whatever_the_keys_cannot_read(self):
        for kv_heads in (1, 2, 4):
            layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
            self.assertEqual(
                len(blind_directions(layer)),
                D_MODEL - key_subspace_rank(layer),
            )

    def test_a_blind_direction_produces_the_same_key_in_every_head(self):
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 1, SEED)
        direction = blind_directions(layer)[0]
        for projection in layer.w_key:
            projected = matmul([direction], projection)[0]
            for value in projected:
                self.assertAlmostEqual(value, 0.0, places=12)

    def test_moving_a_position_along_a_blind_direction_changes_no_routing(self):
        """The decisive experiment: attention toward that position is frozen."""
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 1, SEED)
        x = sample_input()
        target = 3
        direction = blind_directions(layer)[0]
        moved = [list(row) for row in x]
        moved[target] = [
            moved[target][index] + 5.0 * direction[index]
            for index in range(D_MODEL)
        ]
        _, before = layer.forward(x)
        _, after = layer.forward(moved)
        for head in range(NUM_QUERY_HEADS):
            for position in range(LENGTH):
                if position == target:
                    continue
                self.assertAlmostEqual(
                    before[head][position][target],
                    after[head][position][target],
                    places=12,
                )

    def test_the_same_move_still_changes_the_output(self):
        """Blind routing is not a no-op: the value that position carries moves."""
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, 1, SEED)
        x = sample_input()
        direction = blind_directions(layer)[0]
        moved = [list(row) for row in x]
        moved[3] = [
            moved[3][index] + 5.0 * direction[index] for index in range(D_MODEL)
        ]
        before, _ = layer.forward(x)
        after, _ = layer.forward(moved)
        worst = max(
            abs(before[r][c] - after[r][c])
            for r in range(LENGTH)
            for c in range(D_MODEL)
        )
        self.assertGreater(worst, 1e-6)

    def test_multi_head_routing_is_not_frozen_by_any_single_head_null_vector(self):
        """With full-rank keys there is no direction that hides from all heads."""
        layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, NUM_QUERY_HEADS, SEED)
        from lib.linalg import null_space_basis

        direction = null_space_basis(layer.w_key[0])[0]
        others = [
            max(abs(value) for value in matmul([direction], projection)[0])
            for projection in layer.w_key[1:]
        ]
        self.assertGreater(max(others), 1e-6)


class TestHeadPatternSimilarity(unittest.TestCase):
    def test_identical_heads_score_one(self):
        head = [[0.5, 0.5], [0.25, 0.75]]
        self.assertAlmostEqual(head_pattern_similarity([head, head]), 1.0)

    def test_different_heads_score_below_one(self):
        left = [[1.0, 0.0], [1.0, 0.0]]
        right = [[0.0, 1.0], [0.0, 1.0]]
        self.assertAlmostEqual(head_pattern_similarity([left, right]), 0.0)

    def test_averages_over_every_unordered_pair(self):
        a = [[1.0, 0.0]]
        b = [[1.0, 0.0]]
        c = [[0.0, 1.0]]
        self.assertAlmostEqual(head_pattern_similarity([a, b, c]), 1.0 / 3.0)

    def test_rejects_a_single_head(self):
        with self.assertRaises(ValueError):
            head_pattern_similarity([[[1.0]]])

    def test_rejects_mismatched_shapes(self):
        with self.assertRaises(ValueError):
            head_pattern_similarity([[[1.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]]])

    def test_real_layers_produce_a_value_in_range(self):
        x = sample_input()
        for kv_heads in (1, 2, 8):
            layer = GroupedQueryAttention(D_MODEL, NUM_QUERY_HEADS, kv_heads, SEED)
            _, weights = layer.forward(x)
            similarity = head_pattern_similarity(weights)
            self.assertGreater(similarity, 0.0)
            self.assertLessEqual(similarity, 1.0)


if __name__ == "__main__":
    unittest.main()
