# Week 1 · Wed 2026-08-26 · Evening deep-dive: Dynamo's Preference Lists and Quorums

> Calendar row: W1 Wed PM, 17:00. Format: the evening code deep-dive of the
> concept-AM/code-PM day split (the morning was the Dynamo case study; this
> is its code). Pillar: System Design Fundamentals. Pass: Foundations.
> Verified this session: `experiments/week-01/dynamo_quorum_snippet.py`
> (stdlib only, seed 42) re-run directly; every number below is copied from
> that run's actual stdout, not recalled from memory. The complete model is
> also embedded inline under "The Runnable Model" so the article is
> self-contained.
>
> Realignment note (2026-08-26): Wednesday's 17:00 slot was a lessons
> listicle; under the day split it is now the code evening for the morning's
> Dynamo case study (`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`).
> The quorum simulation reuses the R + W > N mechanism from Tuesday's retired
> PACELC slot (`experiments/week-01/pacelc_quorum_snippet.py`), but its network
> RTT model is now explicit and documented: an exponential distribution with
> mean RTT_MEAN_MS = 10.0ms (a plausible same-datacenter round trip), which
> the retired uniform model replaced. The five lessons the old listicle drew
> are folded into this week's essays already.
>
> Adversarial review record (numbers audit, this session, 2026-08-26):
> - Preference lists (UserA -> D,C,F; UserB -> A,C,F; cart-42 -> E,D,A):
>   deterministic MD5 ring walk over 6 nodes x 8 vnodes, computed this
>   session; each is three distinct physical nodes (asserted) ✓
> - (3,1,1) reads 2.3ms p50 / 15.4ms p99 / 66.8% stale, and (3,2,2) reads
>   6.9ms p50 / 28.7ms p99 / 0 stale: reproduced this session from the
>   embedded exponential-RTT model (RTT_MEAN_MS=10, seed 42, 50,000 ops);
>   the stale split (66.8% vs 0%) is the load-bearing result and is
>   independent of the exact RTT shape ✓
> - (3,2,2) as Dynamo's "common (N,R,W)": quoted from the Dynamo paper in
>   this morning's case study, not asserted here ✓
> - Simulation, not a field measurement (Amendment 1): parameters are stated
>   inline (N=3, 40ms lag, 50,000 ops, seed 42, RTT_MEAN_MS=10); no
>   partition is modeled ✓

---

**Topic:** Dynamo's Preference Lists and Quorums

**Subtitle:** A runnable Python model of who keeps each copy, how many replicas must answer, and why stronger confidence costs latency.

Hello again—how is your day going? If you read this morning's case study with a cup of coffee, this is the evening where we roll up our sleeves and make the idea move. No new grand theory, just the two questions hiding underneath every reliable shopping cart: who keeps a copy, and how many replies are enough?

Dynamo answers those questions with a preference list, which decides which nodes hold a key, and a quorum, which decides how many of them we wait for. Here they both are, runnable in one standard-library Python file. You can read along first or run the code beside the article; either way, we will take it one small step at a time.

## The Runnable Model

```python
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
```

## First, Who Keeps a Copy?

A ring answers exactly one question—who owns this key? That is useful, but it is a little like leaving the only spare key to your home with one friend. If that friend is away, the plan stops being a plan. Dynamo's fix is to keep walking around the ring. From the key's position, collect the first N distinct physical nodes and skip any virtual node belonging to a machine already on the list. That ordered group is the preference list, and the whole replication story fits in one function:

```
     UserA  ->  ['D', 'C', 'F']
     UserB  ->  ['A', 'C', 'F']
   cart-42  ->  ['E', 'D', 'A']
```

Three keys, three distinct-node lists, from a six-node ring with eight virtual nodes each. `UserA` lives on D, C, and F. If D is unreachable when a write arrives, C and F have already been named as backups, in order, before anything goes wrong. We are not trying to invent a rescue plan during the outage; we wrote the contact list while everyone was still available.

That small change—return the next N owners instead of one—is what this morning's essay called the move that "turns a routing table into a replication scheme." In the code, it is only nine lines of `preference_list`. In a real service, it is the difference between one failed machine becoming an inconvenience and becoming an outage.

## Then, How Many Replies Are Enough?

Once a key has N holders, `(N, R, W)` decides durability and freshness. A write is acknowledged once W of them have it; a read consults R. Sending an important change to three people who share a household shopping list, one quick reply feels fast, but two replies make it far less likely the new list will go unseen if one person's phone is offline — not a certainty, but a deliberately engineered improvement in the odds.

Our simulation turns that everyday tradeoff into numbers. It runs three replicas with a 40ms asynchronous replication lag and no network partition, performs 50,000 operations, and compares a fast configuration with Dynamo's common one:

```
(N,R,W)                 p50 read  p99 read   stale reads
--------------------------------------------------------
(3,1,1) fast               2.3ms    15.4ms   33,417 (66.8%)
(3,2,2) quorum              6.9ms    28.7ms        0 ( 0.0%)
```

Here is the catch. `(3,1,1)` writes to one replica and reads from one, so it is the fastest possible choice, but two out of every three reads come back stale while the 40ms lag window is open. It is the digital equivalent of checking the one phone that has not received the updated list yet.

`(3,2,2)` satisfies R + W > N—2 + 2 > 3—which guarantees the two-replica read set overlaps the two-replica write set on at least one node holding the newest version, so long as no partition splits the replicas from each other. The result is zero stale reads out of 50,000, paid for with a median latency that roughly triples. A two-replica read must wait for the second-fastest replica, not the first. There is no free lunch here: we wait a little longer because we asked for stronger evidence. This is the same `(3,2,2)` configuration the paper reports as common — and, as it turns out, it's also the smallest (R, W) pair for N=3 that satisfies R + W > N, so "arrived at from the mechanism" and "the paper's choice" are really the same answer seen from two directions.

## Two Small Lines With Big Consequences

These are the two lines I would circle if we were reading the file together.

1. `if node not in seen` inside `preference_list`. Drop that deduplication and your "three replicas" can quietly be three virtual nodes of the same physical machine. It is like making three copies of your house key and leaving all three in the same locked drawer. The count says three; the protection is still one. The preference list must contain distinct physical nodes, which is why walking the ring means more than taking the next three positions.

2. `acked = set(rng.sample(range(n), write_quorum))` paired with `read_latency = rtts[read_quorum - 1]`. The first says an acknowledgement means those replicas have the version now and everyone else converges about 40ms later; treating "acknowledged" as "replicated everywhere" is the classic bug. The second says a quorum read is as slow as its R-th fastest member. Together they show, in code, why R + W > N buys consistency and charges latency for it.

## Where This Small Model Stops

Let's be honest about the boundary. This is a simulation under stated parameters, not a production measurement. It deliberately stops where this morning's concepts get harder: there is no partition, and sloppy quorum, hinted handoff, vector clocks, and Merkle-tree anti-entropy — the machinery the essay walks through for the rare divergent-version case — are not in these lines. What it does show is the load-bearing half you can run in a second: the ring names the holders, and the quorum sets the price of reading them consistently.

One more honest note: the per-replica network latency used to produce the p50/p99 numbers above is a modeled choice (an exponential distribution with a 10ms mean round trip), not a measurement of any real network. The preference lists and the stale-read percentages are exact — those follow directly from the ring and quorum logic. The millisecond figures will shift if you change that latency model, and that's the point: they're there to make the shape of the tradeoff tangible, not to stand in as a benchmark.

If you have five spare minutes, run the model above — or `python3 experiments/week-01/dynamo_quorum_snippet.py`. It uses seed 42, needs nothing beyond the Python standard library, and produces identical output on every machine. Then change `NODES`, `VNODES`, `RTT_MEAN_MS`, or the `(N, R, W)` pairs and watch the preference lists and stale-read percentage move together.

You do not need to memorize every line tonight. Keep the two human questions: **who has a copy, and how many answers will make us confident?** The ring answers the first. The quorum answers the second. Everything else is the cost of keeping that promise when a real person taps **Add to cart**.

---

*Tomorrow, 09:00: a hands-on tutorial building and measuring five load
balancing algorithms, the layer that decides which request reaches which
node once the ring has already decided who is eligible.*
