"""Dynamo on top of the ring: the preference list and the quorum, measured.

Companion snippet for the week-1 Wednesday PM post (2026-08-26, 17:00), the
code evening of Wednesday's Dynamo case study. It makes runnable the two
things Dynamo adds on top of the consistent-hash ring Tuesday walked:

  Part 1 - the PREFERENCE LIST. A ring only answers "who owns this key."
           Dynamo replicates each key at the first N *distinct* physical
           nodes walking clockwise from the key's position (skipping extra
           virtual nodes of a node already in the list). That ordered list
           is the preference list: the N nodes that hold the key.

  Part 2 - the QUORUM over that list. With (N,R,W), a write is acked by W of
           the N and a read consults R. R + W > N forces the read set and the
           write set to overlap on at least one node holding the newest
           version. Dynamo's "common (N,R,W)" is (3,2,2). This part measures
           (3,1,1) fast-but-stale against (3,2,2) quorum, on three replicas
           with async replication lag and no partition anywhere.

Part 2 reuses the exact simulation from pacelc_quorum_snippet.py (same
constants, same seeded RNG, same order), so it reproduces the identical
numbers Wednesday's essay cites: (3,1,1) reads 7.7ms p50 / 67.0% stale;
(3,2,2) reads 16.0ms p50 / 0 stale. Part 1 is deterministic (hashing only)
and does not touch Part 2's RNG stream.

Run:      python3 dynamo_quorum_snippet.py
Depends:  Python 3.8+ standard library only. Deterministic (seed 42).
"""

import hashlib
import random
from bisect import bisect, insort

SEED = 42

# ----- Part 1: the ring and the preference list (deterministic) -------------

NODES = ["A", "B", "C", "D", "E", "F"]
VNODES = 8            # virtual nodes per physical node
N_REPLICAS = 3        # preference-list length = Dynamo's N


class HashRing:
    def __init__(self, nodes, vnodes):
        self.ring = {}
        self.sorted_keys = []
        for node in nodes:
            for i in range(vnodes):
                h = self._hash(f"{node}#{i}")
                self.ring[h] = node
                insort(self.sorted_keys, h)

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def preference_list(self, key, n):
        """First n DISTINCT physical nodes walking clockwise from key."""
        assert n <= len(set(self.ring.values())), "n exceeds physical node count"
        start = bisect(self.sorted_keys, self._hash(key))
        pref = []
        for step in range(len(self.sorted_keys)):
            node = self.ring[self.sorted_keys[(start + step) % len(self.sorted_keys)]]
            if node not in pref:          # skip extra vnodes of a node already chosen
                pref.append(node)
                if len(pref) == n:
                    break
        return pref


# ----- Part 2: quorum over the preference list (from pacelc_quorum_snippet) --

N = 3                    # replicas (= preference-list length)
OPS = 50_000
REPLICATION_LAG_MS = 40
NODE_RTT_MS = (2.0, 30.0)


class Replica:
    def __init__(self):
        self.version = 0
        self.pending = []

    def apply_pending(self, now_ms):
        for apply_at, version in self.pending:
            if apply_at <= now_ms:
                self.version = max(self.version, version)
        self.pending = [(t, v) for t, v in self.pending if t > now_ms]

    def read_version(self, now_ms):
        self.apply_pending(now_ms)
        return self.version


def simulate(write_quorum, read_quorum, rng):
    assert 1 <= write_quorum <= N and 1 <= read_quorum <= N
    replicas = [Replica() for _ in range(N)]
    latest_written = 0
    now = 0.0
    latencies, stale = [], 0
    for op in range(OPS):
        now += rng.uniform(1.0, 5.0)
        rtts = sorted(rng.uniform(*NODE_RTT_MS) for _ in range(N))
        if op % 5 == 0:
            latest_written += 1
            acked = rng.sample(range(N), write_quorum)
            for i, replica in enumerate(replicas):
                if i in acked:
                    replica.apply_pending(now)
                    replica.version = max(replica.version, latest_written)
                else:
                    replica.pending.append((now + REPLICATION_LAG_MS, latest_written))
        else:
            queried = rng.sample(range(N), read_quorum)
            got = max(replicas[i].read_version(now) for i in queried)
            latencies.append(rtts[read_quorum - 1])
            if got < latest_written:
                stale += 1
    return latencies, stale


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))]


def main():
    ring = HashRing(NODES, VNODES)
    print(f"Part 1 - preference lists (N={N_REPLICAS} distinct nodes clockwise), "
          f"{len(NODES)} nodes x {VNODES} vnodes:\n")
    for key in ["UserA", "UserB", "cart-42"]:
        print(f"  {key:>8}  ->  {ring.preference_list(key, N_REPLICAS)}")
    for key in ["UserA", "UserB", "cart-42"]:
        assert len(set(ring.preference_list(key, N_REPLICAS))) == N_REPLICAS

    print(f"\nPart 2 - quorum over a preference list of N={N}: lag="
          f"{REPLICATION_LAG_MS}ms, {OPS:,} ops, seed={SEED}\n")
    print(f"{'(N,R,W)':<22}{'p50 read':>10}{'p99 read':>10}{'stale reads':>14}")
    print("-" * 56)
    results = {}
    for name, w, r in [("(3,1,1) fast", 1, 1), ("(3,2,2) quorum", 2, 2)]:
        latencies, stale = simulate(w, r, random.Random(SEED))
        stale_pct = stale / len(latencies) * 100
        results[name] = (pct(latencies, 0.50), pct(latencies, 0.99), stale_pct)
        print(f"{name:<22}{results[name][0]:>8.1f}ms{results[name][1]:>8.1f}ms"
              f"{stale:>9,} ({stale_pct:4.1f}%)")

    a, b = results["(3,1,1) fast"], results["(3,2,2) quorum"]
    assert b[2] == 0.0, "R+W>N must guarantee overlap with the newest write"
    assert a[2] > 0.0, "R=W=1 with async lag must produce stale reads"
    assert b[0] > a[0], "quorum reads must cost latency at the median"

    print("\nThe ring picks WHO holds a key (Part 1); (N,R,W) picks how many you")
    print("wait for (Part 2). (3,2,2) is Dynamo's common config: R+W>N, so every")
    print("read quorum meets every write quorum on the newest version - zero")
    print("stale reads, paid for in latency. No partition was involved.")


if __name__ == "__main__":
    main()
