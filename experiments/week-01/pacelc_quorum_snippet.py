"""PACELC in 90 lines: pay latency or read stale - measure both.

Companion snippet for the week-1 Tuesday PM post (2026-08-25, 17:00):
"A working snippet for PACELC tradeoffs".

PACELC (Abadi): under Partition choose Availability or Consistency,
Else - during normal operation - choose Latency or Consistency.
This snippet makes the "ELC" half measurable. Three replicas, no
partition, replication lag in play:

  config A (W=1, R=1): fastest writes and reads, stale reads possible
  config B (W=2, R=2): quorum overlap (R + W > N), zero stale reads,
                       every operation pays the second-fastest replica

Virtual clock, no sleeping. Deterministic (seeded).
Run:      python3 pacelc_quorum_snippet.py
Depends:  Python 3.8+ standard library only.
"""

import random

SEED = 42
N = 3                    # replicas
OPS = 50_000             # interleaved writes and reads
REPLICATION_LAG_MS = 40  # async copy delay to non-coordinator replicas
NODE_RTT_MS = (2.0, 30.0)  # per-request per-replica latency range


class Replica:
    def __init__(self):
        self.version = 0          # latest version fully applied here
        self.pending = []         # (apply_at_ms, version) not yet applied

    def apply_pending(self, now_ms):
        for apply_at, version in self.pending:
            if apply_at <= now_ms:
                self.version = max(self.version, version)
        self.pending = [(t, v) for t, v in self.pending if t > now_ms]

    def read_version(self, now_ms):
        self.apply_pending(now_ms)
        return self.version


def simulate(write_quorum, read_quorum, rng):
    """Returns (read latencies ms, stale read count, freshest version log)."""
    assert 1 <= write_quorum <= N and 1 <= read_quorum <= N
    replicas = [Replica() for _ in range(N)]
    latest_written = 0
    now = 0.0
    latencies, stale = [], 0

    for op in range(OPS):
        now += rng.uniform(1.0, 5.0)  # steady request arrivals
        rtts = sorted(rng.uniform(*NODE_RTT_MS) for _ in range(N))
        if op % 5 == 0:  # one write per four reads
            latest_written += 1
            # W fastest replicas ack synchronously: they hold the version now
            acked = rng.sample(range(N), write_quorum)
            for i, replica in enumerate(replicas):
                if i in acked:
                    replica.apply_pending(now)
                    replica.version = max(replica.version, latest_written)
                else:
                    replica.pending.append((now + REPLICATION_LAG_MS, latest_written))
        else:
            # R replicas answer; the response is the max version among them,
            # and the client waits for the R-th fastest response.
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
    print(f"PACELC, the ELC half: N={N}, lag={REPLICATION_LAG_MS}ms, {OPS:,} ops, seed={SEED}\n")
    print(f"{'config':<22}{'p50 read':>10}{'p99 read':>10}{'stale reads':>14}")
    print("-" * 56)
    results = {}
    for name, w, r in [("A: W=1, R=1 (fast)", 1, 1), ("B: W=2, R=2 (quorum)", 2, 2)]:
        latencies, stale = simulate(w, r, random.Random(SEED))
        stale_pct = stale / len(latencies) * 100
        results[name] = (pct(latencies, 0.50), pct(latencies, 0.99), stale_pct)
        print(f"{name:<22}{results[name][0]:>8.1f}ms{results[name][1]:>8.1f}ms"
              f"{stale:>9,} ({stale_pct:4.1f}%)")

    a, b = results["A: W=1, R=1 (fast)"], results["B: W=2, R=2 (quorum)"]
    assert b[2] == 0.0, "R+W>N must guarantee overlap with the newest write"
    assert a[2] > 0.0, "R=W=1 with async lag must produce stale reads"
    assert b[0] > a[0], "quorum reads must cost latency at the median"

    print("\nThe two lines people get wrong:")
    print("  1. 'acked = rng.sample(range(N), write_quorum)' - an ack means THOSE")
    print("     replicas have it now; everyone else gets it ~lag ms later.")
    print("  2. 'latencies.append(rtts[read_quorum - 1])' - a quorum read is as")
    print("     slow as the R-th fastest replica, not the fastest.")
    print("\nSame system, no partition anywhere: you chose latency or you chose")
    print("consistency. That is the second half of PACELC, and it is the half")
    print("you pay for every single day.")


if __name__ == "__main__":
    main()
