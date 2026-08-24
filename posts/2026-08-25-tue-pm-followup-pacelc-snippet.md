# Week 1 · Tue 2026-08-25 · Follow-up: A Working Snippet for PACELC Tradeoffs

> Calendar row: W1 Tue PM, 17:00. Format: short follow-up, 500-700 words.
> Pillar: System Design Fundamentals. Standalone snippet, does not depend
> on the morning's repo. Verified this session: `pacelc_quorum_snippet.py`
> (110 lines, stdlib only, seed 42) re-run directly; every number below is
> copied from that run's actual stdout, not recalled from memory.

---

CAP gets argued about because it only applies during a network partition, and most systems spend nearly all their time not partitioned. PACELC, a term Daniel Abadi coined, adds the half of the tradeoff that applies the rest of the time: Else, meaning no partition at all, you still choose between Latency and Consistency, on every single request. This snippet, 110 lines of stdlib Python, makes that second half measurable instead of asserted.

Three replicas, one coordinator per operation, a fixed 40ms replication lag standing in for the time it takes an async copy to reach a replica that wasn't part of the write quorum. Two configurations, run back to back against the identical seeded traffic, 50,000 interleaved writes and reads:

```
config                  p50 read  p99 read   stale reads
--------------------------------------------------------
A: W=1, R=1 (fast)         7.7ms    24.0ms   26,810 (67.0%)
B: W=2, R=2 (quorum)      16.0ms    28.4ms        0 ( 0.0%)
```

Config A writes to one replica and reads from one replica. It is over twice as fast at the median, 7.7ms against 16.0ms, and 67.0% of its reads, two out of every three, return a version older than the most recent write. Config B writes to two replicas and reads from two, satisfying R + W > N with N=3, and that overlap guarantees the read quorum always intersects the write quorum on at least one replica holding the newest value. Zero stale reads, out of 50,000, not approximately zero. In exchange, the median read pays more than double, and read latency here is not the fastest replica's response, it's the R-th fastest, so a quorum of two waits for the second-fastest replica to answer, not the first.

That single design choice, one line inside `simulate()`, `latencies.append(rtts[read_quorum - 1])`, is the whole mechanism. A quorum read cannot be faster than its slowest required participant, so raising R to buy consistency always costs you the response time of whichever replica in that quorum is slowest, every time, not occasionally.

The other line worth reading twice is `acked = rng.sample(range(N), write_quorum)`. An ack means exactly those sampled replicas hold the new version immediately; everyone else gets it roughly 40ms later, appended to a `pending` list and applied only once the virtual clock passes its scheduled time. That queued-and-applied-later mechanic is the entire source of staleness in config A: with W=1, two of three replicas are still behind for 40ms after every write, and R=1 has a two-in-three chance of asking one of them.

Nothing here is about a partition. All three replicas are reachable the whole time; this is 50,000 fully successful operations. The tradeoff is purely about how many replicas you wait for before answering, and the snippet turns "consistency costs latency" from a slogan into two numbers you can read off a terminal: 8.3ms more at the median, 4.4ms more at p99, in exchange for going from 67.0% stale reads to zero.

Run it yourself: `python3 pacelc_quorum_snippet.py`, seed 42, no dependencies past the standard library, identical output on every machine. Change `REPLICATION_LAG_MS` or `OPS` and the stale-read percentage in config A moves accordingly, a good way to build intuition for how lag and traffic volume interact with quorum size, without touching a single real network.

---

*Tomorrow, 09:00: the system that made W=2, R=2-style quorums famous at
scale, Amazon's Dynamo, in
`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`.*
