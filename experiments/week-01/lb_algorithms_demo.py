"""Load balancing algorithms, measured, in one file.

Companion demo for the week-1 Thursday tutorial (2026-08-27, YouTube):
"Hands-on: load balancing algorithms in under an hour".

Implements five algorithms against a simulated backend pool and measures
the two properties marketing slides never show you:
  1. how evenly each algorithm spreads load when backends are equal,
  2. what each algorithm does when one backend degrades or disappears.

Reference implementations of the same algorithms live in
github.com/ashishps1/awesome-system-design-resources
(implementations/python/load_balancing_algorithms/). This file is
self-contained so viewers can run it with nothing but Python 3.

Run:      python3 lb_algorithms_demo.py
Depends:  Python 3.8+ standard library only. Deterministic (seeded).
Runtime:  under five seconds on a laptop.
"""

import hashlib
import heapq
import random
from bisect import bisect, insort
from collections import Counter

SEED = 42
NUM_REQUESTS = 100_000
BACKENDS = ["b0", "b1", "b2", "b3", "b4"]
WEIGHTS = {"b0": 5, "b1": 4, "b2": 3, "b3": 2, "b4": 1}


# ---------------------------------------------------------------- algorithms


class RoundRobin:
    """Next backend in a fixed cycle. O(1) per pick."""

    def __init__(self, backends):
        assert backends, "backend list must not be empty"
        self.backends = list(backends)
        self.i = 0

    def pick(self, _key=None):
        backend = self.backends[self.i % len(self.backends)]
        self.i += 1
        return backend


class SmoothWeightedRoundRobin:
    """Nginx-style smooth WRR: spreads weighted picks instead of bursting.

    Each pick: every backend's current score grows by its weight, the
    highest score wins and pays back the total weight. Sequence for
    weights {a:5, b:1} interleaves a,a,b,a,a,a rather than a,a,a,a,a,b.
    """

    def __init__(self, weights):
        assert weights and all(w > 0 for w in weights.values()), "weights must be positive"
        self.weights = dict(weights)
        self.current = {b: 0 for b in weights}
        self.total = sum(weights.values())

    def pick(self, _key=None):
        for backend, weight in self.weights.items():
            self.current[backend] += weight
        best = max(self.current, key=self.current.get)
        self.current[best] -= self.total
        return best


class LeastConnections:
    """Backend with the fewest in-flight requests; random tie-break.

    The balancer must be told when a request finishes (release), which is
    the operational cost of the algorithm: it needs connection state.
    """

    def __init__(self, backends, rng):
        assert backends, "backend list must not be empty"
        self.active = {b: 0 for b in backends}
        self.rng = rng

    def pick(self, _key=None):
        floor = min(self.active.values())
        candidates = [b for b, n in self.active.items() if n == floor]
        backend = self.rng.choice(candidates)
        self.active[backend] += 1
        return backend

    def release(self, backend):
        assert self.active[backend] > 0, "release without matching pick"
        self.active[backend] -= 1


class IPHash:
    """hash(client) mod N. Sticky sessions for free, resharding for a price."""

    def __init__(self, backends):
        assert backends, "backend list must not be empty"
        self.backends = list(backends)

    def pick(self, key):
        digest = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self.backends[digest % len(self.backends)]


class ConsistentHash:
    """Hash ring with virtual nodes; same scheme as Dynamo's partitioner.

    vnodes matters: it converts 'each backend owns one arc' into 'each
    backend owns many small arcs', which is what makes the distribution
    even. The demo measures exactly that.
    """

    def __init__(self, backends, vnodes=100):
        assert backends, "backend list must not be empty"
        assert vnodes >= 1, "vnodes must be at least 1"
        self.vnodes = vnodes
        self.ring = {}
        self.sorted_keys = []
        for backend in backends:
            self.add(backend)

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add(self, backend):
        for i in range(self.vnodes):
            h = self._hash(f"{backend}#{i}")
            self.ring[h] = backend
            insort(self.sorted_keys, h)

    def remove(self, backend):
        for i in range(self.vnodes):
            h = self._hash(f"{backend}#{i}")
            del self.ring[h]
            self.sorted_keys.remove(h)

    def pick(self, key):
        assert self.ring, "ring is empty"
        h = self._hash(key)
        idx = bisect(self.sorted_keys, h) % len(self.sorted_keys)
        return self.ring[self.sorted_keys[idx]]


# ---------------------------------------------------------------- scenarios


def show(title, counts, total):
    print(f"\n{title}")
    for backend in sorted(counts):
        share = counts[backend] / total * 100
        print(f"  {backend}: {counts[backend]:>7,}  {share:5.1f}%  {'#' * int(share // 2)}")


def scenario_1_even_spread():
    """Equal backends: RR is exact, hashing is only statistically even."""
    rng = random.Random(SEED)
    clients = [f"client-{rng.randrange(10_000)}" for _ in range(NUM_REQUESTS)]

    rr = RoundRobin(BACKENDS)
    rr_counts = Counter(rr.pick() for _ in range(NUM_REQUESTS))
    show("[1a] round robin, 5 equal backends, 100k requests", rr_counts, NUM_REQUESTS)
    assert max(rr_counts.values()) - min(rr_counts.values()) == 0, "RR must be exact"

    ch = ConsistentHash(BACKENDS, vnodes=100)
    ch_counts = Counter(ch.pick(c) for c in clients)
    show("[1b] consistent hash (100 vnodes), same requests", ch_counts, NUM_REQUESTS)

    ch1 = ConsistentHash(BACKENDS, vnodes=1)
    ch1_counts = Counter(ch1.pick(c) for c in clients)
    show("[1c] consistent hash (1 vnode) - why vnodes exist", ch1_counts, NUM_REQUESTS)

    spread_100 = max(ch_counts.values()) / min(ch_counts.values())
    spread_1 = max(ch1_counts.values()) / min(ch1_counts.values())
    assert spread_100 < spread_1, "more vnodes must mean a tighter spread"
    print(f"\n  max/min imbalance: 100 vnodes = {spread_100:.2f}x, 1 vnode = {spread_1:.2f}x")
    return spread_100, spread_1


def scenario_2_weighted():
    """Smooth WRR converges to the weight ratio."""
    wrr = SmoothWeightedRoundRobin(WEIGHTS)
    counts = Counter(wrr.pick() for _ in range(NUM_REQUESTS))
    show("[2] smooth weighted RR, weights 5:4:3:2:1", counts, NUM_REQUESTS)
    total_weight = sum(WEIGHTS.values())
    for backend, weight in WEIGHTS.items():
        expected = NUM_REQUESTS * weight / total_weight
        actual = counts[backend]
        assert abs(actual - expected) <= 1, f"{backend}: {actual} vs expected {expected}"
    print("  every backend within 1 request of its exact weighted share")


def scenario_3_slow_backend():
    """One backend gets 10x slower. RR keeps feeding it; least-conn adapts.

    Virtual-time event simulation: each request occupies its backend for
    the backend's service time; we track queue depth per backend.
    """
    service_ms = {b: 10.0 for b in BACKENDS}
    service_ms["b2"] = 100.0  # b2 degrades 10x
    arrival_gap_ms = 2.0      # one request every 2ms -> 500 rps offered

    def run(balancer, uses_release):
        rng = random.Random(SEED)
        in_flight = []  # (finish_time, backend)
        depth_samples = {b: [] for b in BACKENDS}
        now = 0.0
        for i in range(20_000):
            now = i * arrival_gap_ms
            while in_flight and in_flight[0][0] <= now:
                _, done_backend = heapq.heappop(in_flight)
                if uses_release:
                    balancer.release(done_backend)
            backend = balancer.pick(f"client-{rng.randrange(10_000)}")
            heapq.heappush(in_flight, (now + service_ms[backend], backend))
            depth = Counter(b for _, b in in_flight)
            for b in BACKENDS:
                depth_samples[b].append(depth.get(b, 0))
        return {b: sum(v) / len(v) for b, v in depth_samples.items()}

    rr_depth = run(RoundRobin(BACKENDS), uses_release=False)
    lc_depth = run(LeastConnections(BACKENDS, random.Random(SEED)), uses_release=True)

    print("\n[3] b2 degrades to 10x service time; mean queue depth per backend")
    print("      backend   round-robin   least-connections")
    for b in BACKENDS:
        print(f"      {b}       {rr_depth[b]:11.2f}   {lc_depth[b]:17.2f}")
    assert rr_depth["b2"] > 5 * max(v for b, v in rr_depth.items() if b != "b2"), \
        "RR must pile requests onto the slow backend"
    assert lc_depth["b2"] < rr_depth["b2"] / 2, \
        "least-connections must shed load off the slow backend"
    return rr_depth, lc_depth


def scenario_4_lose_a_backend():
    """Kill one backend of five: mod-N hashing reshuffles the world,
    the ring only reassigns the dead backend's share."""
    rng = random.Random(SEED)
    clients = [f"client-{n}" for n in range(50_000)]

    iph = IPHash(BACKENDS)
    before = {c: iph.pick(c) for c in clients}
    iph_after = IPHash([b for b in BACKENDS if b != "b2"])
    moved_mod = sum(1 for c in clients if before[c] != iph_after.pick(c))

    ch = ConsistentHash(BACKENDS, vnodes=100)
    before_ch = {c: ch.pick(c) for c in clients}
    ch.remove("b2")
    moved_ch = sum(1 for c in clients if before_ch[c] != ch.pick(c))

    n = len(clients)
    print("\n[4] remove b2 (1 of 5 backends): how many clients change backend?")
    print(f"      hash mod N:        {moved_mod:>6,} / {n:,}  = {moved_mod / n * 100:5.1f}%")
    print(f"      consistent hash:   {moved_ch:>6,} / {n:,}  = {moved_ch / n * 100:5.1f}%")
    print("      theory: mod-N moves ~ (N-1)/N = 80.0%; the ring moves ~ 1/N = 20.0%")
    assert moved_mod / n > 0.70, "mod-N must remap the large majority"
    assert moved_ch / n < 0.30, "the ring must remap roughly the dead node's share only"
    _ = rng  # rng reserved for future randomized client sets
    return moved_mod / n, moved_ch / n


def main():
    print("=" * 68)
    print("Load balancing algorithms: measured behaviour, not vibes")
    print(f"seed={SEED}, requests per scenario as printed")
    print("=" * 68)
    scenario_1_even_spread()
    scenario_2_weighted()
    scenario_3_slow_backend()
    scenario_4_lose_a_backend()
    print("\nAll assertions passed. Every number above reproduces with seed 42.")


if __name__ == "__main__":
    main()
