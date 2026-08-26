"""Consistent hashing: what virtual nodes actually buy you, measured.

Supporting (unpublished) artifact for the week-1 Tuesday concept essay
(2026-08-25), section "Virtual Nodes": it produces the 6.88x -> 1.12x
figure that essay cites. Retained after the concept-AM / code-PM day split
retired the standalone virtual-nodes follow-up post; kept here for reuse.

Isolates the virtual-node knob with a minimal, runnable measurement. Same
ring as the essay: an MD5 hash, a sorted list of positions, one modulo at
lookup that turns the line into a circle. The only variable that moves
between the two runs below is num_replicas: how many positions each physical
server claims on the ring.

Numbers reproduce the concept essay's 6.88x / 1.12x figures because this
uses the identical scheme as prep/week-01/code/lb_algorithms_demo.py
(scenario 1), extracted here to the single knob.

Run:      python3 consistent_hashing_vnodes_snippet.py
Depends:  Python 3.8+ standard library only. Deterministic (seed 42).
Runtime:  about a second on a laptop.
"""

import hashlib
import random
from bisect import bisect, insort
from collections import Counter

SEED = 42
NUM_REQUESTS = 100_000
SERVERS = ["b0", "b1", "b2", "b3", "b4"]


class HashRing:
    """The essay's ring, minus everything not about virtual nodes."""

    def __init__(self, servers, num_replicas):
        self.ring = {}
        self.sorted_keys = []
        for server in servers:
            for i in range(num_replicas):            # <-- the whole mechanism
                h = self._hash(f"{server}#{i}")      # hash server + i, never the bare name
                self.ring[h] = server
                insort(self.sorted_keys, h)

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get(self, key):
        h = self._hash(key)
        idx = bisect(self.sorted_keys, h) % len(self.sorted_keys)  # <-- % wraps line into ring
        return self.ring[self.sorted_keys[idx]]


def imbalance(num_replicas, clients):
    counts = Counter(HashRing(SERVERS, num_replicas).get(c) for c in clients)
    return counts, max(counts.values()) / min(counts.values())


def main():
    rng = random.Random(SEED)
    clients = [f"client-{rng.randrange(10_000)}" for _ in range(NUM_REQUESTS)]

    print(f"consistent hashing, {len(SERVERS)} servers, {NUM_REQUESTS:,} keys, seed {SEED}\n")
    ratios = {}
    for num_replicas in (1, 100):
        counts, ratio = imbalance(num_replicas, clients)
        ratios[num_replicas] = ratio
        print(f"num_replicas={num_replicas:>3}:  busiest/quietest = {ratio:.2f}x")
        for server in sorted(counts):
            share = counts[server] / NUM_REQUESTS * 100
            print(f"    {server}: {counts[server]:>6,}  {share:4.1f}%")
        print()

    assert ratios[100] < ratios[1], "more virtual nodes must tighten the spread"
    print(f"one number changed (num_replicas 1 -> 100): "
          f"{ratios[1]:.2f}x imbalance -> {ratios[100]:.2f}x")


if __name__ == "__main__":
    main()
