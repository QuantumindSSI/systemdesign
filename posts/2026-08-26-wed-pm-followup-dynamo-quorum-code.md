# Week 1 · Wed 2026-08-26 · Evening deep-dive: Dynamo on the Ring, in Runnable Code

> Calendar row: W1 Wed PM, 17:00. Format: the evening code deep-dive of the
> concept-AM/code-PM day split (the morning was the Dynamo case study; this
> is its code). Pillar: System Design Fundamentals. Pass: Foundations.
> Verified this session: `prep/week-01/code/dynamo_quorum_snippet.py`
> (stdlib only, seed 42) re-run directly; every number below is copied from
> that run's actual stdout, not recalled from memory.
>
> Realignment note (2026-08-26): Wednesday's 17:00 slot was a lessons
> listicle; under the day split it is now the code evening for the morning's
> Dynamo case study (`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`).
> The quorum simulation reused here is the one retired from Tuesday's PACELC
> slot (`prep/week-01/code/pacelc_quorum_snippet.py`): its R + W > N mechanism
> is exactly Dynamo's (3,2,2), so it finds its home here. The five lessons the
> old listicle drew are folded into this week's essays already.
>
> Adversarial review record (numbers audit, this session, 2026-08-26):
> - Preference lists (UserA -> D,C,F; UserB -> A,C,F; cart-42 -> E,D,A):
>   deterministic MD5 ring walk over 6 nodes x 8 vnodes, computed this
>   session; each is three distinct physical nodes (asserted) ✓
> - (3,1,1) reads 7.7ms p50 / 24.0ms p99 / 67.0% stale, and (3,2,2) reads
>   16.0ms p50 / 28.4ms p99 / 0 stale: reproduced this session; identical to
>   Tuesday's retired quorum sim by construction (same constants, same seeded
>   RNG order) and to the figures this morning's essay cites ✓
> - (3,2,2) as Dynamo's "common (N,R,W)": quoted from the Dynamo paper in
>   this morning's case study, not asserted here ✓
> - Simulation, not a field measurement (Amendment 1): parameters are stated
>   inline (N=3, 40ms lag, 50,000 ops, seed 42); no partition is modeled ✓

---

**Topic:** Dynamo's Preference Lists and Quorums

**Subtitle:** A runnable Python model of who keeps each copy, how many replicas must answer, and why stronger confidence costs latency.

Hello again—how is your day going? If you read this morning's case study with a cup of coffee, this is the evening where we roll up our sleeves and make the idea move. No new grand theory, just the two questions hiding underneath every reliable shopping cart: **who keeps a copy, and how many replies are enough?**

Dynamo answers those questions with a preference list, which decides which nodes hold a key, and a quorum, which decides how many of them we wait for. Here they both are, runnable in one standard-library Python file. You can read along first or run the code beside the article; either way, we will take it one small step at a time.

## First, Who Keeps a Copy?

A ring answers exactly one question—who owns this key? That is useful, but it is a little like leaving the only spare key to your home with one friend. If that friend is away, the plan stops being a plan. Dynamo's fix is to keep walking around the ring. From the key's position, collect the first N *distinct* physical nodes and skip any virtual node belonging to a machine already on the list. That ordered group is the preference list, and the whole replication story fits in one function:

```
     UserA  ->  ['D', 'C', 'F']
     UserB  ->  ['A', 'C', 'F']
   cart-42  ->  ['E', 'D', 'A']
```

Three keys, three distinct-node lists, from a six-node ring with eight virtual nodes each. `UserA` lives on D, C, and F. If D is unreachable when a write arrives, C and F have already been named as backups, in order, before anything goes wrong. We are not trying to invent a rescue plan during the outage; we wrote the contact list while everyone was still available.

That small change—return the next N owners instead of one—is what this morning's essay called the move that "turns a routing table into a replication scheme." In the code, it is only nine lines of `preference_list`. In a real service, it is the difference between one failed machine becoming an inconvenience and becoming an outage.

## Then, How Many Replies Are Enough?

Once a key has N holders, `(N, R, W)` decides durability and freshness. A write is acknowledged once W of them have it; a read consults R. Think about sending an important change to three people who share a household shopping list. One quick reply feels fast, but two replies give you more confidence that the new list will still be found if one person's phone is offline.

Our simulation turns that everyday tradeoff into numbers. It runs three replicas with a 40ms asynchronous replication lag and no network partition, performs 50,000 operations, and compares a fast configuration with Dynamo's common one:

```
(N,R,W)                 p50 read  p99 read   stale reads
--------------------------------------------------------
(3,1,1) fast               7.7ms    24.0ms   26,810 (67.0%)
(3,2,2) quorum            16.0ms    28.4ms        0 ( 0.0%)
```

Here is the catch. `(3,1,1)` writes to one replica and reads from one, so it is the fastest possible choice, but two out of every three reads come back stale while the 40ms lag window is open. It is the digital equivalent of checking the one phone that has not received the updated list yet.

`(3,2,2)` satisfies R + W > N—2 + 2 > 3—which forces the two-replica read set to overlap the two-replica write set on at least one node holding the newest version. The result is zero stale reads out of 50,000, paid for with a median latency that more than doubles. A two-replica read must wait for the *second*-fastest replica, not the first. There is no free lunch here: we wait a little longer because we asked for stronger evidence. This is the same `(3,2,2)` configuration the paper reports as "common," arrived at here from the mechanism rather than copied from the paper.

## Two Small Lines With Big Consequences

These are the two lines I would circle if we were reading the file together.

1. `if node not in pref` inside `preference_list`. Drop that deduplication and your "three replicas" can quietly be three virtual nodes of the *same* physical machine. It is like making three copies of your house key and leaving all three in the same locked drawer. The count says three; the protection is still one. The preference list must contain distinct physical nodes, which is why walking the ring means more than taking the next three positions.

2. `acked = rng.sample(range(N), write_quorum)` paired with `latencies.append(rtts[read_quorum - 1])`. The first says an acknowledgement means *those* replicas have the version now and everyone else converges about 40ms later; treating "acknowledged" as "replicated everywhere" is the classic bug. The second says a quorum read is as slow as its R-th fastest member. Together they show, in code, why R + W > N buys consistency and charges latency for it.

## Where This Small Model Stops

Let's be honest about the boundary. This is a simulation under stated parameters, not a production measurement. It deliberately stops where this morning's concepts get harder: there is no partition, and sloppy quorum, hinted handoff, vector clocks, and Merkle-tree anti-entropy—the machinery the essay walks through for the rare divergent-version case—are not in these lines. What it does show is the load-bearing half you can run in a second: the ring names the holders, and the quorum sets the price of reading them consistently.

If you have five spare minutes, run `python3 prep/week-01/code/dynamo_quorum_snippet.py`. It uses seed 42, needs nothing beyond the Python standard library, and produces identical output on every machine. Then change `NODES`, `VNODES`, or the `(N, R, W)` pairs and watch the preference lists and stale-read percentage move together.

You do not need to memorize every line tonight. Keep the two human questions: **who has a copy, and how many answers will make us confident?** The ring answers the first. The quorum answers the second. Everything else is the cost of keeping that promise when a real person taps **Add to cart**.

---

*Tomorrow, 09:00: a hands-on tutorial building and measuring five load
balancing algorithms, the layer that decides which request reaches which
node once the ring has already decided who is eligible, in
`posts/2026-08-27-thu-am-tutorial-load-balancing.md`.*
