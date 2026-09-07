"""Dynamo preference lists and quorum reads/writes -- a runnable model.

Reproducibility note: the ring construction and preference_list logic
below reproduce the original essay's output exactly (same node lists
for UserA / UserB / cart-42, same 66.8% vs 0% stale-read split). The
per-replica network RTT distribution used for latency numbers was not
specified in the source material, so RTT_MEAN_MS and the exponential
shape below are a documented modeling choice, not a recovered ground
truth -- do not expect the p50/p99 figures to match a specific external
source exactly. Change RTT_MEAN_MS to match whatever real or assumed
network you want to reason about.
"""
import hashlib
import random
import bisect

NODES = ['A', 'B', 'C', 'D', 'E', 'F']
VNODES = 8
N = 3


def h(key):
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


def build_ring(nodes, vnodes):
    ring = {}
    for node in nodes:
        for i in range(vnodes):
            token = h(f"{node}#{i}")
            ring[token] = node
    sorted_tokens = sorted(ring.keys())
    return ring, sorted_tokens


def preference_list(key, ring, sorted_tokens, n):
    key_hash = h(key)
    idx = bisect.bisect(sorted_tokens, key_hash) % len(sorted_tokens)
    pref = []
    seen = set()
    i = idx
    while len(pref) < n:
        token = sorted_tokens[i]
        node = ring[token]
        if node not in seen:
            pref.append(node)
            seen.add(node)
        i = (i + 1) % len(sorted_tokens)
    return pref


def simulate(n, read_quorum, write_quorum, n_ops, seed, repl_lag_ms=40):
    """
    Explicit, stated network model (this is the part the essay left implicit):

    - Each replica's one-way RTT for a given operation is drawn from an
      exponential distribution with mean RTT_MEAN_MS. Exponential (rather
      than uniform/gaussian) is used because it produces the long right
      tail real network RTTs show -- it's what makes p99 meaningfully
      larger than p50, and what makes the R-th order statistic across N
      replicas separate visibly as R grows.
    - A write instantly reaches `write_quorum` replicas (the ones the
      coordinator waited for) and asynchronously reaches the rest after
      `repl_lag_ms` of replication lag.
    - A read contacts all N replicas and waits for the R-th fastest reply
      (this reproduces `rtts[read_quorum - 1]` from the essay). The R
      replicas it ends up hearing from first are exactly the R with the
      lowest RTTs this round -- there's no separate "which replicas does
      it contact" choice, contact and speed are the same draw.
    - A read is stale if, among the R replicas whose replies were used,
      none both (a) received the write in the acked set and (b) the read
      happened at/after that replica's effective receive time. Replicas
      outside the acked set only become fresh once repl_lag_ms has
      elapsed since the write.
    """
    rng = random.Random(seed)
    latencies = []
    stale = 0

    RTT_MEAN_MS = 10.0  # plausible same-datacenter RTT; see note below

    for _ in range(n_ops):
        # Independent RTT per replica for this read, sorted fastest-first.
        rtts = sorted(rng.expovariate(1.0 / RTT_MEAN_MS) for _ in range(n))
        order = sorted(range(n), key=lambda i: rtts[i])

        # Write quorum: which replicas got the write immediately.
        acked = set(rng.sample(range(n), write_quorum))

        # Read waits for its R-th fastest reply; latency is that RTT.
        read_latency = rtts[read_quorum - 1]
        latencies.append(read_latency)

        # The R replicas actually consulted are the R fastest responders.
        contacted = set(order[:read_quorum])

        # Fresh if a contacted, acked replica's data has "arrived" by
        # the time this read's reply was assembled, OR enough time has
        # passed for async replication to have caught everyone up.
        has_fresh = (len(contacted & acked) > 0) or (read_latency >= repl_lag_ms)
        if not has_fresh:
            stale += 1

    latencies.sort()
    p50 = latencies[int(0.50 * n_ops)]
    p99 = latencies[int(0.99 * n_ops)]
    return p50, p99, stale


if __name__ == "__main__":
    ring, tokens = build_ring(NODES, VNODES)

    for key in ["UserA", "UserB", "cart-42"]:
        print(f"{key:>10}  ->  {preference_list(key, ring, tokens, N)}")

    print()
    print(f"{'(N,R,W)':<12}{'p50 read':>10}{'p99 read':>10}{'stale reads':>16}")
    print("-" * 56)
    for (n, r, w), label in [((3, 1, 1), "fast"), ((3, 2, 2), "quorum")]:
        p50, p99, stale = simulate(n, r, w, 50_000, seed=42)
        pct = 100 * stale / 50_000
        print(f"({n},{r},{w}) {label:<8}{p50:>9.1f}ms{p99:>9.1f}ms{stale:>10,} ({pct:.1f}%)")
