"""Tests for lib/embedding.py: the lookup identity, sizing, and error paths."""

import random
import unittest

from lib.embedding import (
    DEFAULT_INIT_STD,
    EmbeddingTable,
    TokenAndPositionEmbedding,
    cosine_similarity,
    embed_by_matmul,
    gaussian_matrix,
    one_hot,
    parameter_report,
)

SEED = 42
VOCAB = 64
POSITIONS = 16
WIDTH = 8

# Tolerance for comparing two routes to the same arithmetic. The matmul
# route sums num_entries products, all but one of them exactly 0.0, so
# the two results are expected to agree to the last bit; the tolerance is
# here so a future change to the matmul does not fail on a rounding
# difference that means nothing.
TOLERANCE = 1e-12


class TestGaussianMatrix(unittest.TestCase):
    def test_shape_and_determinism(self):
        first = gaussian_matrix(4, 3, random.Random(SEED), DEFAULT_INIT_STD)
        second = gaussian_matrix(4, 3, random.Random(SEED), DEFAULT_INIT_STD)
        self.assertEqual(len(first), 4)
        self.assertEqual(len(first[0]), 3)
        self.assertEqual(first, second)

    def test_rows_are_independent_objects(self):
        table = gaussian_matrix(3, 2, random.Random(SEED), DEFAULT_INIT_STD)
        table[0][0] = 99.0
        self.assertNotEqual(table[1][0], 99.0)

    def test_rejects_bad_dimensions(self):
        for rows, cols in ((0, 2), (2, 0), (-1, 2)):
            with self.assertRaises(ValueError):
                gaussian_matrix(rows, cols, random.Random(SEED), DEFAULT_INIT_STD)

    def test_rejects_non_positive_std(self):
        for std in (0.0, -0.1):
            with self.assertRaises(ValueError):
                gaussian_matrix(2, 2, random.Random(SEED), std)


class TestOneHot(unittest.TestCase):
    def test_exactly_one_hot(self):
        row = one_hot(3, 5)
        self.assertEqual(row, [0.0, 0.0, 0.0, 1.0, 0.0])
        self.assertEqual(sum(row), 1.0)

    def test_negative_index_is_refused_not_wrapped(self):
        # Python would happily return the last row for -1. An id of -1 is
        # a bug upstream, and returning a plausible vector hides it.
        with self.assertRaises(IndexError):
            one_hot(-1, 5)

    def test_index_at_width_is_refused(self):
        with self.assertRaises(IndexError):
            one_hot(5, 5)

    def test_rejects_non_positive_width(self):
        with self.assertRaises(ValueError):
            one_hot(0, 0)


class TestLookupIsAMatrixMultiplication(unittest.TestCase):
    def setUp(self):
        self.table = EmbeddingTable(VOCAB, WIDTH, random.Random(SEED))

    def test_the_two_routes_agree(self):
        ids = [0, 7, 63, 7, 1]
        by_lookup = self.table.lookup(ids)
        by_matmul = embed_by_matmul(self.table.weight, ids)
        self.assertEqual(len(by_lookup), len(by_matmul))
        for left_row, right_row in zip(by_lookup, by_matmul):
            for left, right in zip(left_row, right_row):
                self.assertAlmostEqual(left, right, delta=TOLERANCE)

    def test_repeated_id_gives_the_same_row_twice(self):
        rows = self.table.lookup([9, 9])
        self.assertEqual(rows[0], rows[1])

    def test_result_rows_are_copies(self):
        rows = self.table.lookup([2])
        rows[0][0] = 123.0
        self.assertNotEqual(self.table.weight[2][0], 123.0)


class TestEmbeddingTableSizing(unittest.TestCase):
    def test_parameter_count_is_the_product(self):
        table = EmbeddingTable(VOCAB, WIDTH, random.Random(SEED))
        self.assertEqual(table.parameter_count, VOCAB * WIDTH)

    def test_out_of_range_id_raises_with_the_id_named(self):
        table = EmbeddingTable(VOCAB, WIDTH, random.Random(SEED))
        with self.assertRaises(IndexError) as ctx:
            table.lookup([VOCAB])
        self.assertIn(str(VOCAB), str(ctx.exception))

    def test_non_integer_id_raises(self):
        table = EmbeddingTable(VOCAB, WIDTH, random.Random(SEED))
        for bad in (1.0, "3", None, True):
            with self.assertRaises(TypeError):
                table.lookup([bad])


class TestTokenAndPositionEmbedding(unittest.TestCase):
    def setUp(self):
        self.layer = TokenAndPositionEmbedding(VOCAB, POSITIONS, WIDTH, SEED)

    def test_output_shape(self):
        rows = self.layer.forward([1, 2, 3])
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(rows[0]), WIDTH)

    def test_same_token_at_two_positions_differs(self):
        # If this fails, the layer is order-blind and attention will be too.
        rows = self.layer.forward([5, 5])
        self.assertNotEqual(rows[0], rows[1])

    def test_forward_is_token_row_plus_position_row(self):
        ids = [4, 11]
        rows = self.layer.forward(ids)
        tokens = self.layer.tokens.lookup(ids)
        positions = self.layer.positions.lookup([0, 1])
        for index, row in enumerate(rows):
            for column, value in enumerate(row):
                expected = tokens[index][column] + positions[index][column]
                self.assertAlmostEqual(value, expected, delta=TOLERANCE)

    def test_determinism_from_the_seed(self):
        twin = TokenAndPositionEmbedding(VOCAB, POSITIONS, WIDTH, SEED)
        self.assertEqual(self.layer.forward([1, 2]), twin.forward([1, 2]))

    def test_a_different_seed_gives_different_weights(self):
        other = TokenAndPositionEmbedding(VOCAB, POSITIONS, WIDTH, SEED + 1)
        self.assertNotEqual(self.layer.forward([1, 2]), other.forward([1, 2]))

    def test_parameter_count_covers_both_tables(self):
        self.assertEqual(
            self.layer.parameter_count, (VOCAB + POSITIONS) * WIDTH
        )

    def test_empty_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            self.layer.forward([])

    def test_sequence_longer_than_the_position_table_is_refused(self):
        too_long = list(range(POSITIONS + 1))
        with self.assertRaises(ValueError) as ctx:
            self.layer.forward(too_long)
        self.assertIn(str(POSITIONS), str(ctx.exception))

    def test_exactly_max_positions_is_allowed(self):
        rows = self.layer.forward([0] * POSITIONS)
        self.assertEqual(len(rows), POSITIONS)

    def test_out_of_vocabulary_id_is_refused(self):
        with self.assertRaises(IndexError):
            self.layer.forward([VOCAB + 1])


class TestWeightTying(unittest.TestCase):
    def setUp(self):
        self.layer = TokenAndPositionEmbedding(VOCAB, POSITIONS, WIDTH, SEED)

    def test_logits_shape_is_sequence_by_vocabulary(self):
        hidden = self.layer.forward([1, 2, 3])
        logits = self.layer.tied_logits(hidden)
        self.assertEqual(len(logits), 3)
        self.assertEqual(len(logits[0]), VOCAB)

    def test_a_token_row_scores_highest_against_itself(self):
        # The row for id 7, scored against every row, must match itself
        # best. This is the sanity check that tying is wired the right way
        # round rather than transposed by accident.
        row = [list(self.layer.tokens.weight[7])]
        logits = self.layer.tied_logits(row)[0]
        self.assertEqual(max(range(VOCAB), key=lambda i: logits[i]), 7)

    def test_width_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            self.layer.tied_logits([[0.0] * (WIDTH + 1)])


class TestParameterReport(unittest.TestCase):
    def test_arithmetic(self):
        report = parameter_report(50257, 1024, 768, 117_000_000)
        self.assertEqual(report["token_parameters"], 50257 * 768)
        self.assertEqual(report["position_parameters"], 1024 * 768)
        self.assertEqual(
            report["embedding_parameters"], 50257 * 768 + 1024 * 768
        )
        self.assertEqual(report["tying_saving"], 50257 * 768)
        self.assertAlmostEqual(
            report["embedding_share"],
            (50257 * 768 + 1024 * 768) / 117_000_000,
            places=12,
        )

    def test_share_falls_as_the_model_widens_faster_than_the_vocabulary(self):
        narrow = parameter_report(50257, 1024, 768, 117_000_000)
        wide = parameter_report(50257, 1024, 1600, 1_542_000_000)
        self.assertGreater(narrow["embedding_share"], wide["embedding_share"])

    def test_rejects_non_positive_arguments(self):
        for args in (
            (0, 1024, 768, 1),
            (10, 0, 768, 1),
            (10, 1024, 0, 1),
            (10, 1024, 768, 0),
        ):
            with self.assertRaises(ValueError):
                parameter_report(*args)


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0], [1.0, 2.0]), 1.0)

    def test_opposite_vectors_score_minus_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [-1.0, 0.0]), -1.0)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cosine_similarity([1.0], [1.0, 2.0])

    def test_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            cosine_similarity([0.0, 0.0], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
