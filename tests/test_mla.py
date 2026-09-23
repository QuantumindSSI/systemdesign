"""Tests for lib/mla.py.

The load-bearing claim is that folding the key up-projection into the query
projection changes nothing about the answer. If that equality is only
approximate in a way that grows, the design does not work and the articles
that describe it are wrong, so it is asserted directly at several shapes.

The second claim is the negative one: rotating whole head vectors breaks
the fold. A test that only checked the happy path would pass on an
implementation that silently ignored position.
"""

import random
import unittest

from lib.attention import causal_mask
from lib.linalg import matmul, shape
from lib.mla import (
    MultiHeadLatentAttention,
    cache_comparison,
    max_abs_difference,
    rotary_offsets_needed,
    rotate_rows,
    rope_base,
)

D_MODEL = 32
NUM_HEADS = 4
D_HEAD = 8
D_LATENT = 16
D_ROPE = 8
LENGTH = 10
SEED = 42

EXACT_ENOUGH = 1e-10


def sample_input(seed=SEED, length=LENGTH, width=D_MODEL):
    """A reproducible input sequence."""
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(width)] for _ in range(length)]


def build(d_rope=0, **overrides):
    """A layer with the module defaults, overridable per test."""
    settings = {
        "d_model": D_MODEL,
        "num_heads": NUM_HEADS,
        "d_head": D_HEAD,
        "d_latent": D_LATENT,
        "seed": SEED,
        "d_rope": d_rope,
    }
    settings.update(overrides)
    return MultiHeadLatentAttention(**settings)


class TestConstruction(unittest.TestCase):
    def test_projection_shapes(self):
        layer = build()
        self.assertEqual(shape(layer.w_down_kv), (D_MODEL, D_LATENT))
        self.assertEqual(shape(layer.w_up_key[0]), (D_LATENT, D_HEAD))
        self.assertEqual(shape(layer.w_up_value[0]), (D_LATENT, D_HEAD))
        self.assertEqual(shape(layer.w_query[0]), (D_MODEL, D_HEAD))
        self.assertEqual(shape(layer.w_output), (NUM_HEADS * D_HEAD, D_MODEL))

    def test_no_positional_projections_when_d_rope_is_zero(self):
        layer = build()
        self.assertEqual(layer.w_query_rope, [])
        self.assertEqual(layer.w_key_rope, [])

    def test_positional_key_projection_is_shared_across_heads(self):
        """One matrix, not one per head. That is what makes it cheap to cache."""
        layer = build(d_rope=D_ROPE)
        self.assertEqual(shape(layer.w_key_rope), (D_MODEL, D_ROPE))
        self.assertEqual(len(layer.w_query_rope), NUM_HEADS)

    def test_scale_includes_the_positional_width(self):
        import math

        layer = build(d_rope=D_ROPE)
        self.assertAlmostEqual(layer.scale, 1.0 / math.sqrt(D_HEAD + D_ROPE))

    def test_rejects_non_positive_widths(self):
        for bad in ("d_model", "num_heads", "d_head", "d_latent"):
            with self.assertRaises(ValueError):
                build(**{bad: 0})

    def test_rejects_negative_or_odd_rope_width(self):
        with self.assertRaises(ValueError):
            build(d_rope=-2)
        with self.assertRaises(ValueError):
            build(d_rope=7)

    def test_rejects_an_out_of_range_head(self):
        layer = build()
        with self.assertRaises(ValueError):
            layer.absorbed_matrix(NUM_HEADS)
        with self.assertRaises(ValueError):
            layer.absorbed_matrix(-1)


class TestCacheAccounting(unittest.TestCase):
    def test_standard_cache_counts_a_key_and_a_value_per_head(self):
        comparison = cache_comparison(NUM_HEADS, D_HEAD, D_LATENT)
        self.assertEqual(comparison.standard_bytes, 2 * NUM_HEADS * D_HEAD * 2)

    def test_latent_cache_counts_the_latent_and_the_shared_channel(self):
        comparison = cache_comparison(NUM_HEADS, D_HEAD, D_LATENT, D_ROPE)
        self.assertEqual(comparison.latent_bytes, (D_LATENT + D_ROPE) * 2)

    def test_reduction_and_factor_agree(self):
        comparison = cache_comparison(64, 128, 512, 64)
        self.assertAlmostEqual(
            comparison.reduction, 1.0 - 1.0 / comparison.factor, places=12
        )

    def test_cache_widths_match_the_standalone_helper(self):
        layer = build(d_rope=D_ROPE)
        standard, latent = layer.cache_widths()
        comparison = cache_comparison(NUM_HEADS, D_HEAD, D_LATENT, D_ROPE)
        self.assertEqual(standard * 2, comparison.standard_bytes)
        self.assertEqual(latent * 2, comparison.latent_bytes)

    def test_a_latent_wider_than_the_standard_cache_is_not_a_saving(self):
        """The function must not pretend a bad configuration compresses."""
        comparison = cache_comparison(2, 4, 64)
        self.assertLess(comparison.reduction, 0.0)

    def test_rejects_bad_widths(self):
        with self.assertRaises(ValueError):
            cache_comparison(0, 8, 16)
        with self.assertRaises(ValueError):
            cache_comparison(4, 8, 16, d_rope=3)


class TestRotateRows(unittest.TestCase):
    def test_zero_position_is_the_identity(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        rotated = rotate_rows(matrix, 0)
        for r in range(2):
            for c in range(2):
                self.assertAlmostEqual(rotated[r][c], matrix[r][c], places=12)

    def test_every_row_gets_the_same_angle(self):
        """Unlike apply_rope, which gives row j the angle for position j."""
        matrix = [[1.0, 0.0], [1.0, 0.0]]
        rotated = rotate_rows(matrix, 3)
        self.assertAlmostEqual(rotated[0][0], rotated[1][0], places=12)
        self.assertAlmostEqual(rotated[0][1], rotated[1][1], places=12)

    def test_length_is_preserved(self):
        matrix = [[3.0, 4.0]]
        rotated = rotate_rows(matrix, 7)
        self.assertAlmostEqual(
            sum(value * value for value in rotated[0]), 25.0, places=10
        )

    def test_rejects_odd_width(self):
        with self.assertRaises(ValueError):
            rotate_rows([[1.0, 2.0, 3.0]], 1)


class TestAbsorption(unittest.TestCase):
    """The identity the whole design rests on."""

    def test_absorbed_matrix_shape(self):
        layer = build()
        self.assertEqual(shape(layer.absorbed_matrix(0)), (D_MODEL, D_LATENT))

    def test_folded_scores_match_the_explicit_ones(self):
        layer = build()
        x = sample_input()
        for head in range(NUM_HEADS):
            explicit = layer.content_scores_explicit(x, head)
            folded = layer.content_scores_absorbed(x, head)
            self.assertLess(max_abs_difference(explicit, folded), EXACT_ENOUGH)

    def test_the_fold_holds_at_several_shapes(self):
        for d_model, heads, d_head, d_latent in (
            (16, 2, 4, 8),
            (32, 4, 8, 4),
            (48, 6, 8, 24),
        ):
            layer = MultiHeadLatentAttention(
                d_model, heads, d_head, d_latent, SEED
            )
            x = sample_input(width=d_model)
            explicit = layer.content_scores_explicit(x, 0)
            folded = layer.content_scores_absorbed(x, 0)
            self.assertLess(max_abs_difference(explicit, folded), EXACT_ENOUGH)

    def test_full_forward_passes_agree_without_position(self):
        layer = build()
        x = sample_input()
        mask = causal_mask(LENGTH)
        explicit, explicit_weights = layer.forward_explicit(x, mask)
        absorbed, absorbed_weights = layer.forward_absorbed(x, mask)
        self.assertLess(max_abs_difference(explicit, absorbed), EXACT_ENOUGH)
        for head in range(NUM_HEADS):
            self.assertLess(
                max_abs_difference(explicit_weights[head], absorbed_weights[head]),
                EXACT_ENOUGH,
            )

    def test_full_forward_passes_agree_with_a_decoupled_channel(self):
        layer = build(d_rope=D_ROPE)
        x = sample_input()
        mask = causal_mask(LENGTH)
        explicit, _ = layer.forward_explicit(x, mask)
        absorbed, _ = layer.forward_absorbed(x, mask)
        self.assertLess(max_abs_difference(explicit, absorbed), EXACT_ENOUGH)

    def test_the_decoupled_channel_actually_changes_the_answer(self):
        """Otherwise the previous test would pass on a no-op implementation."""
        x = sample_input()
        mask = causal_mask(LENGTH)
        without, _ = build().forward_explicit(x, mask)
        with_position, _ = build(d_rope=D_ROPE).forward_explicit(x, mask)
        self.assertGreater(max_abs_difference(without, with_position), 1e-6)

    def test_no_key_matrix_is_built_by_the_absorbed_path(self):
        """A structural check: the fold consumes the latent, not a key."""
        layer = build()
        x = sample_input()
        folded = matmul(x, layer.absorbed_matrix(0))
        self.assertEqual(shape(folded), (LENGTH, D_LATENT))


class TestRotationBreaksTheFold(unittest.TestCase):
    """The negative result, which is the reason the decoupled channel exists."""

    def test_a_single_fold_is_wrong_once_heads_are_rotated(self):
        layer = build()
        x = sample_input()
        rotated = layer.content_scores_explicit(x, 0, rotate_heads=True)
        single = layer.content_scores_absorbed(x, 0, offset=0)
        largest = max(abs(value) for row in rotated for value in row)
        self.assertGreater(max_abs_difference(rotated, single), largest * 0.5)

    def test_the_offset_zero_diagonal_is_still_right(self):
        """The single fold is not wrong everywhere, which is the trap."""
        layer = build()
        x = sample_input()
        rotated = layer.content_scores_explicit(x, 0, rotate_heads=True)
        single = layer.content_scores_absorbed(x, 0, offset=0)
        for position in range(LENGTH):
            self.assertAlmostEqual(
                rotated[position][position], single[position][position], places=8
            )

    def test_one_fold_per_offset_reproduces_the_rotated_scores(self):
        layer = build()
        x = sample_input()
        rotated = layer.content_scores_explicit(x, 0, rotate_heads=True)
        rebuilt = layer.content_scores_absorbed_per_offset(x, 0)
        for i in range(LENGTH):
            for j in range(i + 1):
                self.assertAlmostEqual(rotated[i][j], rebuilt[i][j], places=8)

    def test_folds_for_different_offsets_are_different_matrices(self):
        layer = build()
        near = layer.rotated_absorbed_matrix(0, 0)
        far = layer.rotated_absorbed_matrix(0, 1)
        self.assertGreater(max_abs_difference(near, far), 1e-6)

    def test_offset_zero_fold_is_the_plain_fold(self):
        layer = build()
        self.assertLess(
            max_abs_difference(
                layer.rotated_absorbed_matrix(0, 0), layer.absorbed_matrix(0)
            ),
            EXACT_ENOUGH,
        )

    def test_rotating_an_odd_head_is_refused_rather_than_silently_wrong(self):
        layer = MultiHeadLatentAttention(D_MODEL, 1, 7, D_LATENT, SEED)
        with self.assertRaises(ValueError):
            layer.content_scores_explicit(sample_input(), 0, rotate_heads=True)

    def test_offsets_needed_is_the_sequence_length(self):
        self.assertEqual(rotary_offsets_needed(4096), 4096)
        with self.assertRaises(ValueError):
            rotary_offsets_needed(0)


class TestForwardBehaviour(unittest.TestCase):
    def test_output_shape(self):
        layer = build(d_rope=D_ROPE)
        output, weights = layer.forward_absorbed(sample_input())
        self.assertEqual(shape(output), (LENGTH, D_MODEL))
        self.assertEqual(len(weights), NUM_HEADS)

    def test_weight_rows_sum_to_one(self):
        layer = build(d_rope=D_ROPE)
        _, weights = layer.forward_absorbed(sample_input(), causal_mask(LENGTH))
        for head in weights:
            for row in head:
                self.assertAlmostEqual(sum(row), 1.0, places=10)

    def test_mask_is_honoured_in_both_paths(self):
        layer = build(d_rope=D_ROPE)
        mask = causal_mask(LENGTH)
        for weights in (
            layer.forward_explicit(sample_input(), mask)[1],
            layer.forward_absorbed(sample_input(), mask)[1],
        ):
            for head in weights:
                for row_index, row in enumerate(head):
                    for col_index, value in enumerate(row):
                        if col_index > row_index:
                            self.assertEqual(value, 0.0)

    def test_rejects_a_mask_of_the_wrong_shape(self):
        layer = build()
        with self.assertRaises(ValueError):
            layer.forward_absorbed(sample_input(), [[0.0]])

    def test_rejects_an_input_of_the_wrong_width(self):
        layer = build()
        with self.assertRaises(ValueError):
            layer.forward_explicit([[1.0, 2.0]])

    def test_positional_keys_are_empty_without_a_channel(self):
        self.assertEqual(build().positional_keys(sample_input()), [])

    def test_positional_keys_shift_with_the_offset(self):
        layer = build(d_rope=D_ROPE)
        x = sample_input()
        here = layer.positional_keys(x, offset=0)
        there = layer.positional_keys(x, offset=3)
        self.assertGreater(max_abs_difference(here, there), 1e-6)

    def test_rope_base_is_the_shared_constant(self):
        self.assertEqual(rope_base(), 10000.0)


if __name__ == "__main__":
    unittest.main()
