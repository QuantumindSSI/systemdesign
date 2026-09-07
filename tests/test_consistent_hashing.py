"""Tests for lib/consistent_hashing.py, including the property it exists for."""

import unittest

from lib.consistent_hashing import HASH_SPACE, ConsistentHashRing, hash_to_ring

KEYS = [f"user-{index}" for index in range(2000)]


class TestHashToRing(unittest.TestCase):
    def test_is_stable(self):
        self.assertEqual(hash_to_ring("UserA"), hash_to_ring("UserA"))

    def test_is_in_range(self):
        for key in ("", "a", "UserA", "\u4f60\u597d"):
            value = hash_to_ring(key)
            self.assertGreaterEqual(value, 0)
            self.assertLess(value, HASH_SPACE)

    def test_similar_keys_land_far_apart(self):
        # The point of hashing: "user-1" and "user-2" must not be neighbours.
        first = hash_to_ring("user-1")
        second = hash_to_ring("user-2")
        self.assertGreater(abs(first - second), HASH_SPACE // 1000)

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            hash_to_ring(42)


class TestRingBasics(unittest.TestCase):
    def test_empty_ring_refuses_to_route(self):
        with self.assertRaises(LookupError):
            ConsistentHashRing().get_server("anything")

    def test_single_server_owns_everything(self):
        ring = ConsistentHashRing(["only"], replicas=4)
        for key in KEYS[:100]:
            self.assertEqual(ring.get_server(key), "only")

    def test_routing_is_deterministic(self):
        first = ConsistentHashRing(["a", "b", "c"], replicas=8)
        second = ConsistentHashRing(["a", "b", "c"], replicas=8)
        for key in KEYS[:200]:
            self.assertEqual(first.get_server(key), second.get_server(key))

    def test_insertion_order_does_not_matter(self):
        forward = ConsistentHashRing(["a", "b", "c"], replicas=8)
        backward = ConsistentHashRing(["c", "b", "a"], replicas=8)
        for key in KEYS[:200]:
            self.assertEqual(forward.get_server(key), backward.get_server(key))

    def test_servers_property(self):
        ring = ConsistentHashRing(["b", "a"], replicas=3)
        self.assertEqual(ring.servers, ["a", "b"])

    def test_duplicate_server_rejected(self):
        ring = ConsistentHashRing(["a"], replicas=3)
        with self.assertRaises(ValueError):
            ring.add_server("a")

    def test_removing_absent_server_raises(self):
        ring = ConsistentHashRing(["a"], replicas=3)
        with self.assertRaises(KeyError):
            ring.remove_server("ghost")

    def test_replicas_below_one_rejected(self):
        with self.assertRaises(ValueError):
            ConsistentHashRing(["a"], replicas=0)

    def test_add_then_remove_restores_routing(self):
        ring = ConsistentHashRing(["a", "b", "c"], replicas=16)
        before = [ring.get_server(key) for key in KEYS[:300]]
        ring.add_server("d")
        ring.remove_server("d")
        after = [ring.get_server(key) for key in KEYS[:300]]
        self.assertEqual(before, after)


class TestTheWholePoint(unittest.TestCase):
    """The property consistent hashing exists to provide."""

    def test_removing_one_of_five_moves_roughly_a_fifth(self):
        ring = ConsistentHashRing(["s0", "s1", "s2", "s3", "s4"], replicas=200)
        before = {key: ring.get_server(key) for key in KEYS}
        ring.remove_server("s2")
        moved = sum(1 for key in KEYS if ring.get_server(key) != before[key])
        fraction = moved / len(KEYS)
        # Every key that was on s2 must move; ideally nothing else does.
        self.assertGreater(fraction, 0.10)
        self.assertLess(fraction, 0.35)

    def test_keys_not_on_the_removed_server_stay_put(self):
        ring = ConsistentHashRing(["s0", "s1", "s2"], replicas=200)
        before = {key: ring.get_server(key) for key in KEYS}
        ring.remove_server("s1")
        for key in KEYS:
            if before[key] != "s1":
                self.assertEqual(ring.get_server(key), before[key])

    def test_modulo_hashing_moves_almost_everything(self):
        # The baseline consistent hashing is measured against.
        before = [hash_to_ring(key) % 5 for key in KEYS]
        after = [hash_to_ring(key) % 4 for key in KEYS]
        moved = sum(1 for a, b in zip(before, after) if a != b)
        self.assertGreater(moved / len(KEYS), 0.70)

    def test_adding_a_server_only_takes_from_others(self):
        ring = ConsistentHashRing(["s0", "s1", "s2"], replicas=200)
        before = {key: ring.get_server(key) for key in KEYS}
        ring.add_server("s3")
        for key in KEYS:
            current = ring.get_server(key)
            if current != before[key]:
                self.assertEqual(current, "s3")


class TestVirtualNodes(unittest.TestCase):
    def test_more_replicas_balance_better(self):
        def spread(replicas):
            ring = ConsistentHashRing(["s0", "s1", "s2", "s3", "s4"], replicas=replicas)
            counts = list(ring.distribution(KEYS).values())
            return max(counts) / min(counts)

        self.assertGreater(spread(1), spread(200))

    def test_distribution_counts_every_server(self):
        ring = ConsistentHashRing(["s0", "s1", "s2"], replicas=50)
        counts = ring.distribution(KEYS)
        self.assertEqual(sorted(counts), ["s0", "s1", "s2"])
        self.assertEqual(sum(counts.values()), len(KEYS))

    def test_single_replica_ring_still_routes(self):
        ring = ConsistentHashRing(["a", "b"], replicas=1)
        self.assertIn(ring.get_server("some-key"), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
