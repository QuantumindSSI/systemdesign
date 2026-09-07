# Week 1 · Tue 2026-08-25 · Evening deep-dive: Tracing the 53 Lines That Implement Consistent Hashing

> Calendar row: W1 Tue PM, 17:00. Format: the evening code deep-dive of the
> concept-AM/code-PM split; structural spine follows the calendar's "repo
> walkthrough" format for this date. Pillar: System Design Fundamentals.
> Pass: Foundations. Source:
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, Structurally Decisive,
> Adversarial Review) + QSSI research persona (Laws I-VI) + Amendment 1.
>
> Realignment note (2026-08-26): Tuesday runs concept in the morning, code
> in the evening. This is the evening deep-dive; it assumes the reader has
> read this morning's concept essay
> (`posts/2026-08-25-tue-am-essay-consistent-hashing.md`), which built the
> mental model (the mod-N failure, the ring, the outcome-level UserA/UserB
> trace, the virtual-node numbers) and promised this line-by-line read. The
> calendar's originally committed brief paired this repo with PACELC, which
> appears nowhere in the repository (grep over the full clone, 2026-08-22);
> that quorum snippet is retained in the prep pack
> (`experiments/week-01/pacelc_quorum_snippet.py`) and now finds its home in
> Wednesday's Dynamo code evening.
>
> **Rewritten 2026-09-06 under the canonical source rule.** This post
> originally walked a file in an external repository. It now walks
> `lib/consistent_hashing.py`, written into this repository for the purpose,
> covered by `tests/test_consistent_hashing.py`. The mechanism is the same
> scheme, so every hash value and every routing result below reproduces
> exactly; the file identity, the method names, and the default replica count
> changed, and one factual error was corrected.
>
> Adversarial review record (numbers audit, re-measured 2026-09-06):
> - File size: 156 lines total, 53 executable code lines, counted by AST
>   against `lib/consistent_hashing.py` rather than estimated ✓
> - `get_server("UserA")` and `get_server("UserB")` on a six-server ring at
>   `replicas=3`, then adding S6 and removing S2: executed today, output is
>   deterministic because MD5 has no randomness, reproduced exactly as
>   S2, S5, S6, S5 ✓
> - Every truncated hash value quoted in the trace section was recomputed
>   today from `hash_to_ring` and matches character for character ✓
> - **Correction.** The original version claimed `key3` and `key9` keep their
>   server when the divisor moves from 5 to 4. Recomputing the ten remainders
>   shows the two that stay are `key4` and `key7`. The count, eight of ten
>   moving, was right; the two names were wrong and are now fixed ✓
> - Distribution figures 9.04x / 2.54x / 1.12x at replicas 1 / 10 / 100, and
>   402 of 2,000 keys moving on removal with all 402 having lived on the
>   removed server: measured today by `ConsistentHashRing.distribution` over
>   keys `user-0` to `user-1999` ✓
> - The 6.88x figure quoted in the previous version came from a different
>   artifact with a different key population and is no longer cited here ✓
> - No claim is made about docstrings describing the mod-N problem; the
>   "hash(key) mod N reshuffles everything" framing is this essay's own
>   explanation ✓
> - Dynamo's use of MD5 over a 128-bit space is previewed here and detailed
>   with primary-source citation in tomorrow's case study
>   (`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`) ✓
> - Zero em dashes ✓

---

This morning's essay built the mental model: the failure `hash(key) % N` causes, the ring that fixes it, and an outcome-level trace of one key moving while another stayed put. This is the evening deep-dive it promised: the 53 lines of Python that implement that ring, read start to finish, hash value by hash value.

## The File

Open [`lib/consistent_hashing.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/consistent_hashing.py) in this repository. It is 156 lines, of which 53 are executable code and the rest are docstrings explaining why each decision is what it is. No dependencies beyond the Python standard library: `hashlib` and `bisect`. One module-level function, `hash_to_ring`, and one class, `ConsistentHashRing`, with five methods. That is the entire implementation, and by the end of this essay you will have read every line of it.

Most system design writeups describe consistent hashing with a picture of a circle and a wave of the hand at "and then the servers go around it." This file has no circle drawn anywhere. It has a sorted list and a dictionary, and the circle is a description of what that sorted list does, not a data structure the code itself needs to build. Run `python3 -m unittest tests.test_consistent_hashing` before you read on; every claim below is asserted somewhere in that file.

## The Problem in Two Lines

Before the ring, the naive approach: pick a server for a key with `hash(key) % N`, where N is the number of servers. This works fine right up until N changes. Add or remove one server, and N changes, and the remainder of that division changes for almost every key in the system, because a modulo operation has no concept of "close" or "far": shifting N by one reshuffles the whole table, not a proportional slice of it. A cache that just lost one node out of five does not lose a fifth of its entries; under plain mod-N hashing, it loses close to all of them, because nearly every key's remainder changes when the divisor does. That is the failure consistent hashing exists to prevent, and it is worth holding that failure mode in mind for every line that follows, because every design decision in this file is answering it.

Ten keys make the point concretely, computed directly rather than asserted: hash ten strings, `key0` through `key9`, with MD5, then take each hash mod 5 and mod 4. Dropping from five servers to four changes the assignment for eight of those ten keys, not two. Only `key4` and `key7` happen to land on the same server under both divisors; the other eight get reshuffled to a completely different server, most of which had nothing to do with the one server that actually left. That is what "no concept of close or far" means in practice: a key's new owner under mod-N depends on the exact arithmetic remainder, which has no relationship to which physical server was removed.

## Tracing the Ring, Line by Line

Start with `hash_to_ring`, whose body is one line: `int(hashlib.md5(value.encode("utf-8")).hexdigest(), 16)`. MD5 here is not doing anything security-related, and the file does not pretend otherwise. It is doing exactly one job: turning an arbitrary string into a big, well-spread integer, 128 bits of it, so that similar-looking keys ("user-1", "user-2") land in unrelated positions rather than clustering together. Any hash function with good spread would work; MD5 is fast, available in the standard library, and nobody in this pipeline is trying to prevent an adversary from choosing inputs, so its known cryptographic weaknesses are irrelevant to this specific use.

MD5 is also doing a second, quieter job: staying identical across runs and across processes. Python's own built-in `hash()` would have been the shorter line of code, but it is the wrong tool here, and the difference is checkable in two terminal commands rather than taken on faith. Running `hash("UserA")` under `PYTHONHASHSEED=1` prints `-8862622622771628609`; the same call under `PYTHONHASHSEED=2` prints `2238764853229878977`, a completely different number, because CPython randomizes the hash of `str` and `bytes` objects per process by default, specifically to prevent hash-flooding denial-of-service attacks against dictionaries keyed by untrusted strings. That randomization is the right default for a dictionary living inside one process. It is fatal for a hash ring, where two different servers, or the same server restarted, need to agree on which node owns `"UserA"` without talking to each other first. MD5 has no such randomization: hashing `"UserA"` prints the identical 128-bit integer every time, on every machine, in every process, which is the actual property this file needs and the actual reason `hashlib.md5` appears here instead of the shorter `hash()`. The module docstring says exactly this, so nobody later mistakes the choice for a security claim.

Next, `add_server`, the method that actually builds the ring. For a server named, say, `"S3"`, running with `replicas=3`, `_virtual_positions` computes `hash_to_ring("S3-0")`, `hash_to_ring("S3-1")`, `hash_to_ring("S3-2")`, three distinct 128-bit integers, and `add_server` maps each one to `"S3"` in a dictionary called `self._owner`. Each of those three hash values is also inserted into `self._positions`, a plain Python list, via `bisect.insort`, which keeps the list sorted as it grows instead of requiring a separate sort pass afterward. Three lines of loop body, and one physical server has just claimed three separate positions scattered across the hash space, not one.

There is one branch in that loop that looks like paranoia and is not. If a computed position is already claimed, it is skipped. Two MD5 outputs colliding in a 128-bit space is not something you will see, but the alternative to checking is silently overwriting another server's entry in `self._owner` while leaving its position in `self._positions`, which would corrupt routing in a way that is extremely hard to reproduce. Skipping costs that server one virtual node out of a hundred and nothing else.

`remove_server` undoes exactly that: it recomputes the positions that server claimed, keeps only the ones it still owns, then deletes each from `self._owner` and from `self._positions`. Recomputing rather than storing the positions is deliberate. `_virtual_positions` is a pure function of the server name, so the removal path cannot drift out of sync with the insertion path, which is the usual way a ring implementation develops a slow leak of orphaned positions.

Then `get_server`, the method every request actually calls: hash the incoming key, then `bisect_right(self._positions, position)` to find where that hash would be inserted in the sorted list, and read off the server sitting at that index. `bisect_right` finds the insertion point for a value in a sorted sequence in O(log n) time, binary search under the hood, so this lookup does not scan the whole ring on every request. The next two lines are the ones that turn a straight line back into a circle: if the index has run off the end of the list, meaning the key's hash is larger than every position currently on the ring, it is reset to zero and the key is assigned to whichever server owns the first position. That single wrap is the entire "ring" in "hash ring." There is no circular data structure anywhere in this file, only a sorted list and one wraparound at the point of lookup.

The method's first line is the one I would defend hardest in review. An empty ring raises `LookupError` rather than returning `None`. A `None` here would travel: it would be passed to a connection pool, or formatted into a log line, and the eventual failure would name a component several layers away from the ring that had no servers in it.

## Watching It Run

Six lines in a Python shell, and it is worth running rather than reading, because MD5 has no randomness in it: every run on every machine produces the identical sequence. Build `ConsistentHashRing(["S0", ..., "S5"], replicas=3)`. `ring.get_server("UserA")` returns `S2`. `ring.get_server("UserB")` returns `S5`. Then a seventh server, `S6`, gets added, and `ring.get_server("UserA")` is asked again: this time it returns `S6`. `UserA` moved. Then `S2` gets removed, and `ring.get_server("UserB")` is asked one more time: it still returns `S5`, unchanged.

That last line is the entire point of this file, demonstrated rather than argued for. Adding `S6` moved `UserA`, because one of `S6`'s three ring positions happened to land between `UserA`'s hash and whatever server used to own that arc. It did not move `UserB`, because none of `S6`'s new positions fell between `UserB`'s hash and `S5`. Removing `S2` did not touch `UserB` either, for the same reason in reverse: `UserB`'s neighbor on the ring was `S5`, not `S2`, so `S2` leaving cost `UserB` nothing. Two structural changes to the server pool, and exactly one of two tracked keys moved, exactly once. That is consistent hashing working, not described, run.

The "one of `S6`'s three positions happened to land between" claim is checkable against the actual numbers, so here they are, recomputed directly against this file's own logic and truncated to twelve hex digits for readability. `UserA` hashes to `3e44cfa1656d...`. Before `S6` exists, the ring's sorted positions running past that point read `3e443b11ad1f... (S4)`, then `59c354dfa3bf... (S2)`. `UserA`'s hash sits in the gap between those two, and `bisect.bisect` finds the next position clockwise, `S2`'s, which is why the file returns `S2`. Adding `S6` inserts three new positions, one of which, `46e176de18f1...`, lands inside that exact gap, between `S4`'s position and `S2`'s. `UserA`'s hash, `3e44cfa1656d...`, now reaches that new `S6` position before it reaches `S2`'s, so the next-clockwise lookup returns `S6` instead. `UserB` hashes to `bb9d2b016b17...`, sitting in a completely different gap, between `S3`'s position `b30e9cde12c2...` and `S5`'s position `c1d73b8ccd03...`. None of `S6`'s three new positions, `a5ca1cf50bcf...`, `46e176de18f1...`, `5fd3d18d0013...`, fall inside that particular gap; all three sort before it. `UserB`'s owner does not change because the arc it lives on was never touched. That is the whole mechanism, at the level of the actual 128-bit integers involved, not a metaphor about a circle.

## Virtual Nodes: The One Design Decision Worth Stealing

The one line in this file worth remembering longer than any other is the loop inside `_virtual_positions`: `for index in range(self.replicas)`. Without it, each physical server would claim exactly one position on the ring, and one position means one arc, and arcs produced by hashing a single string per server are not evenly sized. Some servers get a wide arc and take a disproportionate share of traffic. Others get a sliver.

The measured version of that claim, from this file's own `distribution` method over 2,000 keys named `user-0` through `user-1999`, re-measured 2026-09-06: with one virtual node per physical server, five servers split those keys 95, 104, 467, 475, 859. The busiest server holds 9.04 times the load of the quietest. Raise `replicas` to 10 and the split becomes 228, 301, 354, 539, 578, a ratio of 2.54. Raise it to 100 and the constructor's default takes over: 372, 399, 402, 412, 415, a ratio of 1.12, close enough to even that nobody would notice in production. Nothing about the servers changed. Nothing about the keys changed. The only variable that moved was how many positions each physical server claims on the ring.

The same measurement shows up a second way, on the removal side rather than the distribution side. Take those same five servers and 2,000 keys, then remove one. Under a hash ring with 200 virtual nodes per server, 402 of the 2,000 keys move, which is 20.1%, and the count of keys that had been living on the removed server is also exactly 402. Every key that moved had to move; not one other key was disturbed. Compare that to plain `hash(key) % N`: switching the divisor from five to four moves more than 70% of the same keys, and the ones that move have no relationship to the server that left. That is the entire value proposition of these 53 lines made numeric, and [`tests/test_consistent_hashing.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/tests/test_consistent_hashing.py) asserts both halves of it, so the claim fails loudly if the implementation ever stops being true.

None of that comes free, and the constructor's `replicas=100` default is where the bill is set: every virtual node is a full second entry in `self._owner` and `self._positions`, not a cheap flag on an existing one. Building this exact ring for 1,000 physical servers at 100 virtual nodes each means 100,000 dictionary entries and a 100,000-element sorted list, on the order of tens of megabytes. That is a trivial number for a single service holding its own ring in memory, and a very different number the moment that ring needs to be replicated to every client that wants to route without a network hop to a coordinator, which is exactly the shape of problem a gossip-based membership protocol has to solve. A hundred virtual nodes per server is this file's default precisely because it sits past the point of diminishing returns on balance, since 1.12x imbalance is already close to the theoretical floor, without pushing the ring's memory and gossip cost into territory where the fix costs more than the mod-N problem it solves.

## The Wart Worth Naming

Nothing in this file is presented as production-hardened, and it should not be read that way. `remove_server` finds each position with a binary search, which is O(log n), and then deletes it from a Python list, which is O(n) because every later element shifts down. Removing one server at `replicas=100` therefore costs 100 list deletions, each proportional to the size of the ring. Lookup stays logarithmic; removal does not. That is a fine tradeoff for a file whose job is to be readable in one sitting, and a real bottleneck in a system with frequent scale-in events on a ring holding hundreds of thousands of virtual nodes.

The other limitation is that `replicas` is fixed at construction. A ring cannot be re-balanced by raising the replica count later without rebuilding it, because `_virtual_positions` derives positions from the current `self.replicas` and a changed value would no longer match what was inserted. That constraint is not enforced by the type system; it is enforced by the fact that `replicas` is never reassigned anywhere in the file. If you copy this into a service that wants to tune replica counts at runtime, that is the first thing you have to change, and the removal path is where it will break if you forget.

The first limitation has a standard fix: swap the plain Python `list` for a structure with logarithmic insertion and removal, not just logarithmic lookup. A balanced tree, or a production system's own membership ring structure, buys back the O(n) removal cost this file accepts in exchange for staying dependency-free and readable in one sitting. That tradeoff, dependency-free and O(n) versus an extra dependency and O(log n), is a legitimate engineering decision rather than a bug, and the right answer depends entirely on how large the ring gets and how often servers actually leave it.

## What This File Doesn't Do

Read on its own, this file answers exactly one question: given a key and a set of servers, which server owns it, and how much does that answer change when the set of servers changes. It says nothing about replication, nothing about what happens when the server `get_server` returns is unreachable, and nothing about giving a bigger server more of the ring than a smaller one beyond bluntly raising `replicas` for everyone uniformly.

Take the unreachable-server gap first, because it is the sharpest one. `get_server("UserA")` returns exactly one name, `S2` or whichever server owns that arc, and the file has no concept of "and here are the next two servers after that one, in case the first one is down." A cache that calls this exact function and gets `S2` back, only to find `S2` unreachable, has nowhere else to go without a second lookup and its own retry logic layered on top, logic this file does not contain. Real distributed stores answer that gap by asking the ring for N distinct owners of a key, not one, walking clockwise past the first hit to collect the next N-1 unique servers, and writing (or reading) from several of them instead of exactly one. That single change, from "return one owner" to "return the next N owners walking clockwise," is what turns a routing table into a replication scheme, and it is a change this file's four methods do not make.

The capacity gap is smaller in code but just as real in consequence. `add_server(name)` takes no weight argument; every server gets the same `replicas`, meaning a ring built from this file assumes every physical machine can handle an equal share of traffic. A cluster with one machine twice the size of the others has no way to tell this ring that. The honest fix is a per-server replica count, which is a two-line change to `_virtual_positions` and a considerably longer conversation about how you decide the weights.

Those three gaps, no replication, no failure handling, no heterogeneous capacity, are not oversights; they are exactly the three problems a production system built on this same ring has to solve next, and they are the subject of tomorrow's case study: how Amazon's Dynamo paper took this identical scheme, MD5 hash, ring, virtual nodes, and built replication, quorum reads and writes, and heterogeneous node capacity on top of it, at a scale where "1/N of the keyspace moves" needed to be true for values of N in the thousands, not five.

---

*That was the morning's mental model made literal, one method at a time.
Tomorrow, 09:00: this exact ring at Amazon's scale, with replication, quorum
reads and writes, and heterogeneous capacity built on top of it. Tomorrow
evening turns the "return the next N owners" change above into a runnable
preference list and quorum.*
