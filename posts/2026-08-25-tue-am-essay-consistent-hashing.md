# Week 1 · Tue 2026-08-25 · Long-form: The Mental Model for Consistent Hashing, Before the 79 Lines

> Calendar row: W1 Tue AM, 09:00. Format: long-form Substack essay, spine =
> concept deep-dive. Pillar: System Design Fundamentals. Pass: Foundations.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, Structurally Decisive,
> Adversarial Review) + QSSI research persona (Laws I-VI) + Amendment 1.
>
> Realignment note (2026-08-26): Tuesday now runs concept in the morning,
> code in the evening. This essay builds the mental model (the failure, the
> ring, what it can't do); the line-by-line walk of the 79-line file moved
> to this afternoon's 17:00 follow-up
> (`posts/2026-08-25-tue-pm-followup-code-walkthrough.md`). Same underlying
> example across both slots.
>
> Adversarial review record (numbers audit, this session, 2026-08-26):
> - Ten keys, MD5 mod 5 vs mod 4: eight of ten `key0`-`key9` change server
>   when dropping five servers to four; the two that do not are `key4` and
>   `key7`. Computed directly this session (`hashlib.md5`), correcting an
>   earlier draft that named `key3`/`key9` as the stable pair — those two
>   both move; the stable pair is `key4`/`key7` ✓
> - 6.88x (one position per server) and 1.12x (100 positions per server)
>   load imbalance, and 79.9% vs 19.1% keys remapped on a single-node
>   removal: measured by the seeded demo in this repo
>   (`experiments/week-01/consistent_hashing_vnodes_snippet.py` and
>   `lb_algorithms_demo.py`, seed 42), reproduced exactly this session ✓
> - The S2 / S5 / S6 / S5 outcome trace: the source file's own bundled
>   example, executed this session (`python3 consistent-hashing.py`); output
>   is deterministic (MD5, no randomness) and reproduced exactly ✓
> - MD5-over-a-128-bit-space and the Dynamo preview: detailed with
>   primary-source citation in tomorrow's case study
>   (`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`), not re-derived
>   from memory here ✓

---

Consistent hashing solves one specific problem: when you add or remove a server from a pool, you want only the keys near that one server to move, not almost every key in the system. Here is that problem made concrete — the failure mode, the ring that fixes it, and what the fix still doesn't cover. This evening, at 17:00, we open the 79 lines of Python that implement it and trace them start to finish, hash value by hash value. This morning is for the mental model; the code review is worth far more once that model is already load-bearing.

## The Circle Comes Last, Not First

Most system design writeups describe consistent hashing with a picture of a circle and a wave of the hand at "and then the servers go around it." That picture isn't wrong, but it's usually introduced before the reader has a reason to want it. The circle is a description of what a particular data structure does under the hood. It is not itself the thing you need to understand first. What you need first is the failure it's fixing.

## The Problem in Two Lines

Before the ring, the naive approach: pick a server for a key with `hash(key) % N`, where N is the number of servers. This works fine right up until N changes. Add or remove one server, and the remainder of that division changes for almost every key in the system, because a modulo operation has no concept of "close" or "far." Shifting N by one reshuffles the whole table, not a proportional slice of it. A cache that just lost one node out of five does not lose a fifth of its entries; under plain mod-N hashing, it loses close to all of them, because nearly every key's remainder changes when the divisor does. That is the failure consistent hashing exists to prevent, and it is worth holding in mind for everything that follows — every design decision in the ring is answering this one failure.

Ten keys make the point concretely, computed directly rather than asserted: hash ten strings, `key0` through `key9`, with MD5, then take each hash mod 5 and mod 4. Dropping from five servers to four changes the assignment for eight of those ten keys, not two. Only `key4` and `key7` happen to land on the same server under both divisors; the other eight get reshuffled to a completely different server, most of which had nothing to do with the one server that actually left. That is what "no concept of close or far" means in practice: a key's new owner under mod-N depends on the exact arithmetic remainder, which has no relationship to which physical server was removed.

## What the Ring Actually Is, Conceptually

The fix is to stop hashing servers into a fixed-size table and instead hash both keys and servers into the same enormous space — the same range of possible outputs a hash function produces — and give each server a small number of positions scattered across it. A key belongs to whichever server owns the nearest position going in one direction. Add a server, and it only steals a slice of the range immediately around its own new positions; every other server's territory is untouched. Remove a server, and its neighbors on either side simply absorb its slice; nobody else's assignments move.

Three things have to be true for that to work, and each one maps to a piece of the eventual implementation, which is exactly what this evening's code walkthrough traces line by line:

- The hash used to place both keys and servers has to be stable: the same input has to produce the same output on every machine, in every process, forever. This rules out anything with per-process randomization baked in, which is a sharper constraint than it sounds, and worth its own paragraph when we get to the code.

- The positions have to be kept in a structure that supports fast "find the nearest one" lookups, not a linear scan. This is where the sorted-list-plus-binary-search shape comes from.

- Each server needs *multiple* positions, not one, or the slices end up wildly uneven in size. This is the single most important design decision in the whole scheme, and it deserves more space than a code comment gives it.

## Watching It Work, at the Level of Outcomes

The behavior is worth seeing before the mechanism, because the mechanism only matters in service of this outcome. Six servers, S0 through S5, get added to a ring. A lookup for one key, call it UserA, returns S2. A lookup for another, UserB, returns S5. Add a seventh server, S6, and ask for UserA again: it now returns S6. UserA moved. Ask for UserB again: it still returns S5, unchanged. Now remove S2 entirely and ask for UserB once more: still S5.

That is the entire point, demonstrated rather than argued for. Adding S6 moved UserA because one of S6's new positions happened to land in the gap UserA's hash falls into. It didn't move UserB, because none of S6's new positions fell in *that* gap. Removing S2 didn't touch UserB either, for the same reason in reverse: UserB's neighbor on the ring was S5, not S2, so S2 leaving cost UserB nothing. Two structural changes to the server pool, and exactly one of two tracked keys moved, exactly once. This evening we pull the actual 128-bit integers apart and show precisely which gap each key sits in and why — checkable arithmetic, not a coincidence, and worth seeing once you already believe the outcome is correct.

## Virtual Nodes: The One Decision Worth Understanding Before the Code

Without multiple positions per server, each physical server claims exactly one slice of the range, and slices produced by hashing a single string per server are not evenly sized: it is pure chance where each hash lands. Some servers get a wide slice and take a disproportionate share of traffic; others get a sliver. This is the part of the scheme that is easy to nod along to and easy to get wrong in practice, so the numbers matter more than the intuition here.

With one position per physical server, five servers splitting 100,000 simulated requests split unevenly enough that the busiest server handles 6.88 times the traffic of the quietest one. Raise the number of positions per server to 100 — same five servers, same requests — and watch that ratio drop to 1.12x, close enough to even that nobody would notice in production. Nothing about the servers changed. Nothing about the requests changed. The only variable that moved was how many positions each physical server claims.

The same measurement shows up a second way, on removal rather than distribution. Take those same five servers, simulate 50,000 client keys, then remove one server. Under plain `hash(key) % N`, 79.9% of all 50,000 keys land on a different server than before — almost exactly the theoretical (N-1)/N figure for five servers losing one, since nearly every remainder shifts when the divisor drops. Run the identical removal against a ring with 100 positions per server, and only 19.1% of keys move — close to the theoretical 1/N figure, the fraction of the ring the removed server actually owned. That is the entire value proposition made numeric: not "better" hashing in a vague sense, but roughly a four-times reduction, measured, in how much of a cache goes cold every time the pool scales in or loses a node.

None of that is free: more positions per server means more entries in whatever structure holds them, and there is a real memory and lookup-cost tradeoff buried in that tension. That tradeoff, and the specific data-structure choices it forces, is exactly where this evening's code walkthrough picks up.

## What the Ring Doesn't Do

Held purely as a concept, this scheme answers one question: given a key and a set of servers, which server owns it, and how much does that answer change when the set of servers changes. It says nothing about replication, nothing about what happens when the server it names is unreachable, and nothing about giving a bigger server more of the ring than a smaller one beyond uniformly raising how many positions everyone gets.

The unreachable-server gap is the sharpest one. A lookup returns exactly one server name. If that server happens to be down, there is no built-in concept of "here are the next two after that one, in case the first is unavailable." Real distributed stores close that gap by asking the ring for N distinct owners of a key, not one — walking past the first hit to collect the next N-1 unique servers — and reading or writing from several of them instead of exactly one. That single change, from "return one owner" to "return the next N owners," is what turns a routing table into a replication scheme.

The capacity gap is smaller in surface area but just as real in consequence. Giving every server the same number of ring positions assumes every physical machine can handle an equal share of traffic. A cluster with one machine twice the size of the others has no built-in way to express that, short of deliberately giving that one server more positions than everyone else — a workaround the basic scheme doesn't prevent but doesn't suggest either.

Those two gaps — no failure handling, no heterogeneous capacity — aren't oversights in a teaching-sized version of this idea; they are exactly the problems a production system built on this same ring has to solve next. That is also roughly the shape of what Amazon's Dynamo paper did with this identical scheme: the same hash-and-scatter idea, the same virtual-node trick, built up into replication, quorum reads and writes, and heterogeneous node capacity, at a scale where "1/N of the keyspace moves" needed to hold for values of N in the thousands, not five.

---

*This evening, 17:00: we open the file itself and read all 79 lines — why
MD5 beats Python's own `hash()` here, what the sorted list actually buys
over a real circle, and the exact 128-bit arithmetic behind why UserA moved
and UserB didn't, down to the one line in `remove_server` that is an honest
tradeoff, not a bug. Tomorrow, 09:00: this same ring at Amazon's scale.*
