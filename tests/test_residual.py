"""Tests for lib/residual.py.

The contract that matters is the reconstruction identity: input plus every
recorded write equals the stream the stack produced. Everything else in
this file exists to stop that identity from being true by accident, for
instance because the recorder quietly reimplemented the block wrong and
both sides agree on a wrong answer. So the recorder is also checked
against `lib/layernorm.py`'s own forward pass, which was written first and
is covered by its own tests.
"""

import math
import random
import unittest

from lib.layernorm import TransformerBlock, root_mean_square
from lib.linalg import shape
from lib.residual import (
    ResidualRecorder,
    StreamWrite,
    ablate,
    cosine_similarity,
    flatten,
    max_abs_difference,
    reconstruct,
    subtract,
    writes_at_depth,
)

D_MODEL = 8
NUM_HEADS = 2
D_HIDDEN = 16
NUM_LAYERS = 4
LENGTH = 5
SEED = 42


def build_blocks(norm_first, num_layers=NUM_LAYERS):
    """Blocks seeded exactly the way TransformerStack seeds them."""
    return [
        TransformerBlock(
            D_MODEL, NUM_HEADS, D_HIDDEN, SEED + 100 * index, norm_first
        )
        for index in range(num_layers)
    ]


def sample_input(seed=SEED, length=LENGTH, width=D_MODEL):
    """A reproducible input sequence."""
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(width)] for _ in range(length)]


class TestFlatten(unittest.TestCase):
    def test_reads_row_major(self):
        self.assertEqual(flatten([[1.0, 2.0], [3.0, 4.0]]), [1.0, 2.0, 3.0, 4.0])

    def test_rejects_ragged(self):
        with self.assertRaises(ValueError):
            flatten([[1.0, 2.0], [3.0]])

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            flatten([])


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_give_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0], [1.0, 2.0]), 1.0)

    def test_opposite_vectors_give_minus_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0], [-1.0, -2.0]), -1.0)

    def test_orthogonal_vectors_give_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 3.0]), 0.0)

    def test_scale_invariant(self):
        left = [0.3, -1.2, 4.0]
        right = [2.0, 0.5, -1.0]
        self.assertAlmostEqual(
            cosine_similarity(left, right),
            cosine_similarity([value * 7.5 for value in left], right),
        )

    def test_zero_vector_returns_zero_rather_than_nan(self):
        self.assertEqual(cosine_similarity([0.0, 0.0], [1.0, 2.0]), 0.0)

    def test_rejects_length_mismatch(self):
        with self.assertRaises(ValueError):
            cosine_similarity([1.0, 2.0], [1.0])

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            cosine_similarity([], [])


class TestMatrixHelpers(unittest.TestCase):
    def test_subtract(self):
        self.assertEqual(
            subtract([[5.0, 1.0]], [[2.0, 4.0]]), [[3.0, -3.0]]
        )

    def test_subtract_rejects_shape_mismatch(self):
        with self.assertRaises(ValueError):
            subtract([[1.0, 2.0]], [[1.0]])

    def test_max_abs_difference(self):
        self.assertAlmostEqual(
            max_abs_difference([[1.0, 2.0], [3.0, 4.0]], [[1.0, 2.5], [3.0, 4.0]]),
            0.5,
        )

    def test_max_abs_difference_rejects_shape_mismatch(self):
        with self.assertRaises(ValueError):
            max_abs_difference([[1.0]], [[1.0, 2.0]])


class TestRecorderConstruction(unittest.TestCase):
    def test_rejects_empty_stack(self):
        with self.assertRaises(ValueError):
            ResidualRecorder([])

    def test_rejects_mixed_arrangements(self):
        blocks = [
            TransformerBlock(D_MODEL, NUM_HEADS, D_HIDDEN, SEED, True),
            TransformerBlock(D_MODEL, NUM_HEADS, D_HIDDEN, SEED + 100, False),
        ]
        with self.assertRaises(ValueError):
            ResidualRecorder(blocks)

    def test_takes_arrangement_from_the_blocks(self):
        self.assertTrue(ResidualRecorder(build_blocks(True)).norm_first)
        self.assertFalse(ResidualRecorder(build_blocks(False)).norm_first)


class TestRecorderMatchesTheBlockItself(unittest.TestCase):
    """The recorder must not be a second, subtly different implementation."""

    def test_pre_norm_final_stream_matches_forward(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        stream, _ = ResidualRecorder(blocks).run(x)
        expected = x
        for block in blocks:
            expected = block.forward(expected)
        self.assertLess(max_abs_difference(stream, expected), 1e-12)

    def test_post_norm_final_stream_matches_forward(self):
        blocks = build_blocks(norm_first=False)
        x = sample_input()
        stream, _ = ResidualRecorder(blocks).run(x)
        expected = x
        for block in blocks:
            expected = block.forward(expected)
        self.assertLess(max_abs_difference(stream, expected), 1e-12)

    def test_mask_is_threaded_through(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        mask = [
            [0.0 if col <= row else float("-inf") for col in range(LENGTH)]
            for row in range(LENGTH)
        ]
        masked, _ = ResidualRecorder(blocks).run(x, mask)
        unmasked, _ = ResidualRecorder(blocks).run(x)
        self.assertGreater(max_abs_difference(masked, unmasked), 1e-6)


class TestReconstruction(unittest.TestCase):
    """The identity the module exists for."""

    def test_pre_norm_writes_sum_to_the_stream(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        stream, writes = ResidualRecorder(blocks).run(x)
        self.assertLess(max_abs_difference(reconstruct(x, writes), stream), 1e-12)

    def test_post_norm_writes_also_sum_because_norms_are_recorded(self):
        blocks = build_blocks(norm_first=False)
        x = sample_input()
        stream, writes = ResidualRecorder(blocks).run(x)
        self.assertLess(max_abs_difference(reconstruct(x, writes), stream), 1e-12)

    def test_pre_norm_records_two_writes_per_block(self):
        blocks = build_blocks(norm_first=True)
        _, writes = ResidualRecorder(blocks).run(sample_input())
        self.assertEqual(len(writes), 2 * NUM_LAYERS)
        self.assertEqual(
            [write.component for write in writes_at_depth(writes, 0)],
            ["attention", "feed_forward"],
        )

    def test_post_norm_records_four_writes_per_block(self):
        blocks = build_blocks(norm_first=False)
        _, writes = ResidualRecorder(blocks).run(sample_input())
        self.assertEqual(len(writes), 4 * NUM_LAYERS)
        self.assertEqual(
            [write.component for write in writes_at_depth(writes, 1)],
            ["attention", "norm_attention", "feed_forward", "norm_feed_forward"],
        )

    def test_dropping_the_norm_writes_breaks_post_norm_reconstruction(self):
        """Post-norm is not a sum of its branch outputs, and this shows it."""
        blocks = build_blocks(norm_first=False)
        x = sample_input()
        stream, writes = ResidualRecorder(blocks).run(x)
        branches_only = [
            write
            for write in writes
            if write.component in ("attention", "feed_forward")
        ]
        self.assertGreater(
            max_abs_difference(reconstruct(x, branches_only), stream), 0.1
        )

    def test_every_delta_has_the_stream_shape(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x)
        for write in writes:
            self.assertEqual(shape(write.delta), (LENGTH, D_MODEL))


class TestStreamWriteStatistics(unittest.TestCase):
    def test_stream_after_is_the_rms_of_the_sum(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        stream, writes = ResidualRecorder(blocks).run(x)
        self.assertAlmostEqual(writes[-1].stream_after, root_mean_square(stream))

    def test_first_write_starts_from_the_input_size(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x)
        self.assertAlmostEqual(writes[0].stream_before, root_mean_square(x))

    def test_write_fraction_is_delta_over_outgoing_stream(self):
        write = StreamWrite(
            depth=0,
            component="attention",
            delta=[[3.0, 4.0]],
            stream_before=1.0,
            stream_after=5.0,
            cosine=0.0,
        )
        self.assertAlmostEqual(write.delta_rms, math.sqrt(12.5))
        self.assertAlmostEqual(write.write_fraction, math.sqrt(12.5) / 5.0)

    def test_write_fraction_refuses_a_collapsed_stream(self):
        write = StreamWrite(
            depth=2,
            component="feed_forward",
            delta=[[0.0]],
            stream_before=0.0,
            stream_after=0.0,
            cosine=0.0,
        )
        with self.assertRaises(ValueError):
            write.write_fraction

    def test_quadrature_prediction_is_exact_for_an_orthogonal_write(self):
        """Two orthogonal vectors: the prediction must be the true answer."""
        stream = [[3.0, 0.0]]
        delta = [[0.0, 4.0]]
        write = StreamWrite(
            depth=0,
            component="attention",
            delta=delta,
            stream_before=root_mean_square(stream),
            stream_after=root_mean_square([[3.0, 4.0]]),
            cosine=0.0,
        )
        self.assertAlmostEqual(write.quadrature_prediction, write.stream_after)

    def test_quadrature_prediction_is_wrong_for_a_parallel_write(self):
        stream = [[3.0, 0.0]]
        delta = [[3.0, 0.0]]
        write = StreamWrite(
            depth=0,
            component="attention",
            delta=delta,
            stream_before=root_mean_square(stream),
            stream_after=root_mean_square([[6.0, 0.0]]),
            cosine=1.0,
        )
        self.assertGreater(
            abs(write.quadrature_prediction - write.stream_after), 1.0
        )

    def test_cosines_are_within_range(self):
        blocks = build_blocks(norm_first=True)
        _, writes = ResidualRecorder(blocks).run(sample_input())
        for write in writes:
            self.assertGreaterEqual(write.cosine, -1.0)
            self.assertLessEqual(write.cosine, 1.0)


class TestSilencing(unittest.TestCase):
    """The true ablation: discard a write and let the rest of the stack react."""

    def test_silenced_component_writes_zeros(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x, silence=[(1, "attention")])
        silenced = [
            write
            for write in writes
            if write.depth == 1 and write.component == "attention"
        ][0]
        self.assertEqual(silenced.delta_rms, 0.0)

    def test_silencing_changes_later_writes_too(self):
        """A term removed from the finished sum cannot do this; a real one can."""
        blocks = build_blocks(norm_first=True, num_layers=6)
        x = sample_input()
        _, full = ResidualRecorder(blocks).run(x)
        _, cut = ResidualRecorder(blocks).run(x, silence=[(1, "attention")])
        later_full = [w for w in full if w.depth == 4][0]
        later_cut = [w for w in cut if w.depth == 4][0]
        self.assertGreater(
            max_abs_difference(later_full.delta, later_cut.delta), 1e-6
        )

    def test_silencing_differs_from_arithmetic_removal(self):
        blocks = build_blocks(norm_first=True, num_layers=6)
        x = sample_input()
        _, full = ResidualRecorder(blocks).run(x)
        rerun, _ = ResidualRecorder(blocks).run(x, silence=[(2, "feed_forward")])
        arithmetic = ablate(x, full, depth=2, component="feed_forward")
        self.assertGreater(max_abs_difference(rerun, arithmetic), 1e-6)

    def test_silencing_nothing_matches_a_plain_run(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        plain, _ = ResidualRecorder(blocks).run(x)
        empty, _ = ResidualRecorder(blocks).run(x, silence=[])
        self.assertEqual(max_abs_difference(plain, empty), 0.0)

    def test_rejects_unknown_component(self):
        blocks = build_blocks(norm_first=True)
        with self.assertRaises(ValueError):
            ResidualRecorder(blocks).run(sample_input(), silence=[(0, "mlp")])

    def test_rejects_a_norm_component_in_the_pre_norm_arrangement(self):
        """Pre-norm never writes a norm delta, so silencing one is a typo."""
        blocks = build_blocks(norm_first=True)
        with self.assertRaises(ValueError):
            ResidualRecorder(blocks).run(
                sample_input(), silence=[(0, "norm_attention")]
            )

    def test_accepts_a_norm_component_in_the_post_norm_arrangement(self):
        blocks = build_blocks(norm_first=False)
        stream, _ = ResidualRecorder(blocks).run(
            sample_input(), silence=[(0, "norm_attention")]
        )
        self.assertEqual(shape(stream), (LENGTH, D_MODEL))

    def test_rejects_out_of_range_depth(self):
        blocks = build_blocks(norm_first=True)
        with self.assertRaises(ValueError):
            ResidualRecorder(blocks).run(
                sample_input(), silence=[(NUM_LAYERS, "attention")]
            )


class TestAblation(unittest.TestCase):
    def test_removing_a_write_changes_the_sum_by_exactly_that_write(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        stream, writes = ResidualRecorder(blocks).run(x)
        without = ablate(x, writes, depth=1, component="attention")
        removed = [
            write
            for write in writes
            if write.depth == 1 and write.component == "attention"
        ][0]
        self.assertLess(
            max_abs_difference(subtract(stream, without), removed.delta), 1e-12
        )

    def test_unknown_component_raises_rather_than_no_opping(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x)
        with self.assertRaises(ValueError):
            ablate(x, writes, depth=1, component="mlp")

    def test_out_of_range_depth_raises(self):
        blocks = build_blocks(norm_first=True)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x)
        with self.assertRaises(ValueError):
            ablate(x, writes, depth=NUM_LAYERS, component="attention")


class TestGrowthShape(unittest.TestCase):
    """The measured behaviour an article is allowed to quote."""

    def test_pre_norm_stream_grows_with_depth(self):
        blocks = build_blocks(norm_first=True, num_layers=6)
        x = sample_input()
        _, writes = ResidualRecorder(blocks).run(x)
        self.assertGreater(writes[-1].stream_after, writes[0].stream_before)

    def test_post_norm_stream_ends_at_unit_size(self):
        blocks = build_blocks(norm_first=False, num_layers=6)
        stream, _ = ResidualRecorder(blocks).run(sample_input())
        self.assertAlmostEqual(root_mean_square(stream), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
