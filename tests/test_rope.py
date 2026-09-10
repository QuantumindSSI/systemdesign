"""Tests for lib/rope.py: the relative identity, length, and error paths."""

import math
import random
import unittest

from lib.rope import (
    DEFAULT_BASE,
    apply_rope,
    dot,
    inverse_frequencies,
    norm,
    relative_score,
    rotate,
)

SEED = 42
WIDTH = 8

# The identity is exact in real arithmetic, so the only gap is floating
# point accumulated over WIDTH / 2 sine and cosine evaluations.
TOLERANCE = 1e-9


def random_vector(rng, width=WIDTH):
    """A reproducible vector for the property tests."""
    return [rng.gauss(0.0, 1.0) for _ in range(width)]


class TestInverseFrequencies(unittest.TestCase):
    def test_one_rate_per_pair(self):
        self.assertEqual(len(inverse_frequencies(8)), 4)

    def test_first_rate_is_one_and_rates_descend(self):
        rates = inverse_frequencies(16)
        self.assertAlmostEqual(rates[0], 1.0)
        for earlier, later in zip(rates, rates[1:]):
            self.assertLess(later, earlier)

    def test_last_rate_is_base_to_the_minus_one_plus_two_over_d(self):
        rates = inverse_frequencies(8, DEFAULT_BASE)
        self.assertAlmostEqual(rates[-1], DEFAULT_BASE ** (-6.0 / 8.0))

    def test_rejects_odd_or_non_positive_width(self):
        for width in (0, -2, 7):
            with self.assertRaises(ValueError):
                inverse_frequencies(width)

    def test_rejects_base_at_or_below_one(self):
        for base in (1.0, 0.5, -3.0):
            with self.assertRaises(ValueError):
                inverse_frequencies(8, base)


class TestRotate(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def test_position_zero_is_the_identity(self):
        vector = random_vector(self.rng)
        for value, rotated in zip(vector, rotate(vector, 0)):
            self.assertAlmostEqual(value, rotated, delta=TOLERANCE)

    def test_length_is_preserved(self):
        # A rotation cannot lengthen or shorten anything, which is why
        # RoPE can never amplify or attenuate a vector.
        vector = random_vector(self.rng)
        original = norm(vector)
        for position in (1, 5, 97, 4096, -13):
            self.assertAlmostEqual(
                norm(rotate(vector, position)), original, delta=TOLERANCE
            )

    def test_rotations_compose_additively(self):
        vector = random_vector(self.rng)
        twice = rotate(rotate(vector, 3), 5)
        once = rotate(vector, 8)
        for left, right in zip(twice, once):
            self.assertAlmostEqual(left, right, delta=TOLERANCE)

    def test_input_is_not_modified(self):
        vector = random_vector(self.rng)
        copy = list(vector)
        rotate(vector, 7)
        self.assertEqual(vector, copy)

    def test_rejects_odd_width(self):
        with self.assertRaises(ValueError):
            rotate([1.0, 2.0, 3.0], 1)

    def test_rejects_empty_vector(self):
        with self.assertRaises(ValueError):
            rotate([], 1)


class TestRelativePositionIdentity(unittest.TestCase):
    """The property the whole scheme exists for."""

    def setUp(self):
        self.rng = random.Random(SEED)

    def test_score_depends_only_on_the_difference(self):
        query = random_vector(self.rng)
        key = random_vector(self.rng)
        for offset in (0, 1, 7, 100, 1000):
            for distance in (0, 1, 2, 13, 64):
                shifted = relative_score(
                    query, key, offset + distance, offset
                )
                at_origin = relative_score(query, key, distance, 0)
                self.assertAlmostEqual(shifted, at_origin, delta=TOLERANCE)

    def test_the_identity_holds_for_negative_distances_too(self):
        query = random_vector(self.rng)
        key = random_vector(self.rng)
        self.assertAlmostEqual(
            relative_score(query, key, 10, 17),
            relative_score(query, key, -7, 0),
            delta=TOLERANCE,
        )

    def test_distance_zero_is_the_unrotated_dot_product(self):
        query = random_vector(self.rng)
        key = random_vector(self.rng)
        self.assertAlmostEqual(
            relative_score(query, key, 42, 42), dot(query, key), delta=TOLERANCE
        )

    def test_rejects_mismatched_widths(self):
        with self.assertRaises(ValueError):
            relative_score([1.0, 2.0], [1.0, 2.0, 3.0, 4.0], 1, 0)


class TestApplyRope(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)
        self.rows = [random_vector(self.rng) for _ in range(5)]

    def test_shape_is_unchanged(self):
        rotated = apply_rope(self.rows)
        self.assertEqual(len(rotated), len(self.rows))
        self.assertEqual(len(rotated[0]), WIDTH)

    def test_row_j_is_rotated_by_j(self):
        rotated = apply_rope(self.rows)
        for index, row in enumerate(self.rows):
            for produced, expected in zip(rotated[index], rotate(row, index)):
                self.assertAlmostEqual(produced, expected, delta=TOLERANCE)

    def test_offset_shifts_every_position(self):
        # This is what a KV cache needs: row 0 of a continuation is not
        # position 0 of the sequence.
        rotated = apply_rope(self.rows, offset=100)
        for index, row in enumerate(self.rows):
            expected = rotate(row, 100 + index)
            for produced, want in zip(rotated[index], expected):
                self.assertAlmostEqual(produced, want, delta=TOLERANCE)

    def test_offset_preserves_relative_scores(self):
        # Shifting the whole window must not change any score inside it.
        keys = [random_vector(self.rng) for _ in range(5)]
        plain_q = apply_rope(self.rows)
        plain_k = apply_rope(keys)
        shifted_q = apply_rope(self.rows, offset=500)
        shifted_k = apply_rope(keys, offset=500)
        for i in range(5):
            for j in range(5):
                self.assertAlmostEqual(
                    dot(plain_q[i], plain_k[j]),
                    dot(shifted_q[i], shifted_k[j]),
                    delta=1e-6,
                )

    def test_rejects_odd_width(self):
        with self.assertRaises(ValueError):
            apply_rope([[1.0, 2.0, 3.0]])

    def test_rejects_ragged_input(self):
        with self.assertRaises(ValueError):
            apply_rope([[1.0, 2.0], [3.0]])


class TestVectorHelpers(unittest.TestCase):
    def test_norm(self):
        self.assertAlmostEqual(norm([3.0, 4.0]), 5.0)

    def test_norm_rejects_empty(self):
        with self.assertRaises(ValueError):
            norm([])

    def test_dot(self):
        self.assertAlmostEqual(dot([1.0, 2.0], [3.0, 4.0]), 11.0)

    def test_dot_rejects_length_mismatch(self):
        with self.assertRaises(ValueError):
            dot([1.0], [1.0, 2.0])


class TestDecayIsNotGuaranteed(unittest.TestCase):
    """The claim the Friday evening post is built on.

    Su et al. list "decaying inter-token dependency with increasing
    relative distances" as a property. It is a tendency over vectors in
    general, not a guarantee for every vector, and a test is the honest
    place to record the difference.
    """

    def test_energy_in_the_slowest_pair_barely_decays(self):
        width = 64
        rates = inverse_frequencies(width)
        slow = [0.0] * width
        slow[width - 2] = 1.0
        at_zero = relative_score(slow, slow, 0, 0)
        far = relative_score(slow, slow, 512, 0)
        # The slowest pair turns by rate * distance radians in total.
        self.assertLess(rates[-1] * 512, math.pi / 2)
        self.assertGreater(far, 0.5 * at_zero)

    def test_energy_in_the_fastest_pair_swings_wildly(self):
        width = 64
        fast = [0.0] * width
        fast[0] = 1.0
        scores = [relative_score(fast, fast, distance, 0)
                  for distance in range(0, 8)]
        self.assertAlmostEqual(scores[0], 1.0, delta=TOLERANCE)
        self.assertLess(min(scores), 0.0)


if __name__ == "__main__":
    unittest.main()
