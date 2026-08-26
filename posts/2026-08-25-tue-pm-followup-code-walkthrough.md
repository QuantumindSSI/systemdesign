# Week 1 · Tue 2026-08-25 · Evening deep-dive: Tracing the 79 Lines That Implement Consistent Hashing

> Calendar row: W1 Tue PM, 17:00. Format: the evening code deep-dive of the
> concept-AM/code-PM split; structural spine follows the calendar's "repo
> walkthrough" format for this date. Pillar: System Design Fundamentals.
> Pass: Foundations. Source:
> github.com/ashishps1/awesome-system-design-resources, file
> `implementations/python/consistent_hashing/consistent-hashing.py`.
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
> (`prep/week-01/code/pacelc_quorum_snippet.py`) and now finds its home in
> Wednesday's Dynamo code evening.
>
> Adversarial review record (numbers audit, this session, 2026-08-25):
> - "40,884 stars, last push 2026-02-16, not archived": GitHub API, live
>   query this session (2026-08-25) ✓
> - File line count: 79 lines, counted directly against the cloned file
>   this session (`wc -l`), correcting the prep pack's hedged "~75 lines"
>   estimate ✓
> - `get_server("UserA")`, `get_server("UserB")`, and the add/remove-server
>   trace: the file's own bundled usage example, executed directly this
>   session (`python3 consistent-hashing.py`); output is deterministic
>   (MD5, no randomness) and reproduced exactly: S2, S5, S6, S5, in that
>   order ✓
> - 6.88x / 1.12x vnode-imbalance ratio and 79.9% / 19.1% remap-on-removal
>   figures: measured by the seeded demo in this repo
>   (`prep/week-01/code/lb_algorithms_demo.py`, seed 42), re-run and
>   reproduced exactly this session ✓
> - No claim is made about this file's docstrings describing the mod-N
>   problem; the file has no top-of-file docstring, and the "hash(key) mod
>   N reshuffles everything" framing below is this essay's own explanation
>   of the general problem, not a quote from the source file ✓
> - Dynamo's use of MD5 over a 128-bit space is previewed here and detailed
>   with primary-source citation in tomorrow's case study
>   (`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`); not re-derived
>   from memory in this essay ✓

---

This morning's essay built the mental model: the failure `hash(key) % N` causes, the ring that fixes it, and an outcome-level trace of one key moving while another stayed put. This is the evening deep-dive it promised — the 79 lines of Python that implement that ring, read start to finish, hash value by hash value.

## The File

Open `github.com/ashishps1/awesome-system-design-resources`, a repository sitting at 40,884 stars at the last repo check, last pushed 2026-02-16, not archived. Inside `implementations/python/consistent_hashing/` is a single file, `consistent-hashing.py`, 79 lines including its own usage example at the bottom. No dependencies beyond the Python standard library: `hashlib` and `bisect`. One class, `ConsistentHashing`, four methods. That is the entire implementation, and by the end of this essay you will have read every line of it.

Most system design writeups describe consistent hashing with a picture of a circle and a wave of the hand at "and then the servers go around it." This file has no circle drawn anywhere. It has a sorted list and a dictionary, and the circle is a description of what that sorted list does, not a data structure the code itself needs to build.

## The Problem in Two Lines

Before the ring, the naive approach: pick a server for a key with `hash(key) % N`, where N is the number of servers. This works fine right up until N changes. Add or remove one server, and N changes, and the remainder of that division changes for almost every key in the system, because a modulo operation has no concept of "close" or "far": shifting N by one reshuffles the whole table, not a proportional slice of it. A cache that just lost one node out of five does not lose a fifth of its entries; under plain mod-N hashing, it loses close to all of them, because nearly every key's remainder changes when the divisor does. That is the failure consistent hashing exists to prevent, and it is worth holding that failure mode in mind for every line that follows, because every design decision in this file is answering it.

Ten keys make the point concretely, computed directly rather than asserted: hash ten strings, `key0` through `key9`, with MD5, then take each hash mod 5 and mod 4. Dropping from five servers to four changes the assignment for eight of those ten keys, not two. Only `key3` and `key9` happen to land on the same server under both divisors; the other eight get reshuffled to a completely different server, most of which had nothing to do with the one server that actually left. That is what "no concept of close or far" means in practice: a key's new owner under mod-N depends on the exact arithmetic remainder, which has no relationship to which physical server was removed.

## Tracing the Ring, Line by Line

Start with `_hash`, four lines: `int(hashlib.md5(key.encode()).hexdigest(), 16)`. MD5 here is not doing anything security-related, and the file does not pretend otherwise. It is doing exactly one job: turning an arbitrary string into a big, well-spread integer, 128 bits of it, so that similar-looking keys ("user-1", "user-2") land in unrelated positions rather than clustering together. Any hash function with good spread would work; MD5 is fast, available in the standard library, and nobody in this pipeline is trying to prevent an adversary from choosing inputs, so its known cryptographic weaknesses are irrelevant to this specific use.

MD5 is also doing a second, quieter job: staying identical across runs and across processes. Python's own built-in `hash()` would have been the shorter line of code, but it is the wrong tool here, and the difference is checkable in two terminal commands rather than taken on faith. Running `hash("UserA")` under `PYTHONHASHSEED=1` prints `-8862622622771628609`; the same call under `PYTHONHASHSEED=2` prints `2238764853229878977`, a completely different number, because CPython randomizes the hash of `str` and `bytes` objects per process by default, specifically to prevent hash-flooding denial-of-service attacks against dictionaries keyed by untrusted strings. That randomization is the right default for a dictionary living inside one process. It is fatal for a hash ring, where two different servers, or the same server restarted, need to agree on which node owns `"UserA"` without talking to each other first. MD5 has no such randomization: hashing `"UserA"` prints the identical 128-bit integer every time, on every machine, in every process, which is the actual property this file needs and the actual reason `hashlib.md5` appears here instead of the shorter `hash()`.

Next, `add_server`, the method that actually builds the ring. For a server named, say, `"S3"`, with the default `num_replicas=3`, it computes `_hash("S3-0")`, `_hash("S3-1")`, `_hash("S3-2")`, three distinct 128-bit integers, and maps each one to `"S3"` in a dictionary called `self.ring`. Each of those three hash values is also inserted into `self.sorted_keys`, a plain Python list, via `bisect.insort`, which keeps the list sorted as it grows instead of requiring a separate sort pass afterward. Three lines of code, and one physical server has just claimed three separate positions scattered across the hash space, not one.

`remove_server` undoes exactly that: for each of the `num_replicas` positions a server claimed, delete the entry from `self.ring` and remove the matching hash from `self.sorted_keys`.

Then `get_server`, the method every request actually calls: hash the incoming key, then `bisect.bisect(self.sorted_keys, hash_val) % len(self.sorted_keys)` to find the position in the sorted list where that hash would be inserted, and read off the server sitting at that index. `bisect.bisect` finds the insertion point for a value in a sorted sequence in O(log n) time, binary search under the hood, so this lookup does not scan the whole ring on every request. The `% len(self.sorted_keys)` at the end is the one line that turns a straight line back into a circle: if the key's hash is larger than every position currently on the ring, the index wraps back around to zero, meaning it gets assigned to whichever server owns the first position. That single modulo is the entire "ring" in "hash ring." There is no circular data structure anywhere in this file, only a sorted list and one wraparound calculation at the point of lookup.

## Watching It Run

The file ends with its own worked example, six lines, and it is worth running rather than reading, because MD5 has no randomness in it: every run on every machine produces the identical sequence. Six servers, `S0` through `S5`, get added first. `ch.get_server("UserA")` returns `S2`. `ch.get_server("UserB")` returns `S5`. Then a seventh server, `S6`, gets added, and `ch.get_server("UserA")` is asked again: this time it returns `S6`. `UserA` moved. Then `S2` gets removed, and `ch.get_server("UserB")` is asked one more time: it still returns `S5`, unchanged.

That last line is the entire point of this file, demonstrated rather than argued for. Adding `S6` moved `UserA`, because one of `S6`'s three ring positions happened to land between `UserA`'s hash and whatever server used to own that arc. It did not move `UserB`, because none of `S6`'s new positions fell between `UserB`'s hash and `S5`. Removing `S2` did not touch `UserB` either, for the same reason in reverse: `UserB`'s neighbor on the ring was `S5`, not `S2`, so `S2` leaving cost `UserB` nothing. Two structural changes to the server pool, and exactly one of two tracked keys moved, exactly once. That is consistent hashing working, not described, run.

The "one of `S6`'s three positions happened to land between" claim is checkable against the actual numbers, so here they are, recomputed directly against this file's own logic and truncated to twelve hex digits for readability. `UserA` hashes to `3e44cfa1656d...`. Before `S6` exists, the ring's sorted positions running past that point read `3e443b11ad1f... (S4)`, then `59c354dfa3bf... (S2)`. `UserA`'s hash sits in the gap between those two, and `bisect.bisect` finds the next position clockwise, `S2`'s, which is why the file returns `S2`. Adding `S6` inserts three new positions, one of which, `46e176de18f1...`, lands inside that exact gap, between `S4`'s position and `S2`'s. `UserA`'s hash, `3e44cfa1656d...`, is now closer to that new `S6` position than to `S2`'s, so the next-clockwise lookup returns `S6` instead. `UserB` hashes to `bb9d2b016b17...`, sitting in a completely different gap, between `S3`'s position `b30e9cde12c2...` and `S5`'s position `c1d73b8ccd03...`. None of `S6`'s three new positions, `a5ca1cf50bcf...`, `46e176de18f1...`, `5fd3d18d0013...`, fall inside that particular gap; all three sort before it. `UserB`'s owner does not change because the arc it lives on was never touched. That is the whole mechanism, at the level of the actual 128-bit integers involved, not a metaphor about a circle.

## Virtual Nodes: The One Design Decision Worth Stealing

The one line in this file worth remembering longer than any other is the loop inside `add_server`: `for i in range(self.num_replicas)`. Without it, each physical server would claim exactly one position on the ring, and one position means one arc, and arcs produced by hashing a single string per server are not evenly sized. Some servers get a wide arc and take a disproportionate share of traffic. Others get a sliver.

The measured version of that claim, from the seeded demo in this repo's prep pack (`prep/week-01/code/lb_algorithms_demo.py`, seed 42, reproduced this session): with one virtual node per physical server, five servers split 100,000 simulated requests unevenly enough that the busiest server handles 6.88 times the traffic of the quietest one. Raise `num_replicas` to 100, the same five servers, the same requests, and that ratio drops to 1.12x, close enough to even that nobody would notice in production. Nothing about the servers changed. Nothing about the requests changed. The only variable that moved was how many positions each physical server claims on the ring, which is exactly the `num_replicas` parameter sitting in this file's constructor with a default value of 3, a number chosen for readability in a teaching example, not for production load distribution.

The same measurement shows up a second way, on the removal side rather than the distribution side. Take those same five servers and simulate 50,000 client keys, then remove one server. Under plain `hash(key) % N`, 79.9% of all 50,000 keys land on a different server than before, almost exactly the theoretical (N-1)/N figure for five servers losing one, because nearly every remainder shifts when the divisor drops from five to four. Run the identical removal against a hash ring with 100 virtual nodes per server, and only 19.1% of keys move, close to the theoretical 1/N figure: the fraction of the ring that the removed server actually owned. That is the entire value proposition of this 79-line file made numeric: not "better" hashing in some vague sense, but a four-times reduction, measured, in how much of your cache goes cold every time you scale in or lose a node.

None of that comes free, and this file's default of 3 is one honest way of admitting it: every virtual node is a full second entry in `self.ring` and `self.sorted_keys`, not a cheap flag on an existing one. Building this exact ring for 1,000 physical servers at 100 virtual nodes each, 100,000 total entries, measured directly against this process's own resident memory this session (`resource.getrusage`, macOS), costs roughly 15 MB. That is a trivial number for a single service holding its own ring in memory, and a very different number the moment that ring needs to be replicated to every client that wants to route without a network hop to a coordinator, which is exactly the shape of problem a gossip-based membership protocol has to solve. A hundred virtual nodes per server is a good default precisely because it sits past the point of diminishing returns on balance, 1.12x imbalance is already close to the theoretical floor, without pushing the ring's memory and gossip cost into territory where the fix costs more than the mod-N problem it solves.

## The Wart Worth Naming

Nothing in this file is presented as production-hardened, and it should not be read that way. `remove_server` calls `self.sorted_keys.remove(hash_val)` once per replica, and `list.remove` in Python is an O(n) linear scan for each call, meaning removing a server with a large `num_replicas` on a ring with many entries costs real time proportional to the ring's size, not the logarithmic cost `get_server`'s `bisect.bisect` enjoys on lookup. A production ring typically keeps a balanced tree or batches removals instead of calling `.remove()` in a loop. It is a fine tradeoff for a file whose entire job is to be readable in one sitting, and a real bottleneck if this exact code shipped into a system with frequent scale-in events on a ring holding thousands of virtual nodes.

The other limitation is the constructor default itself: `num_replicas=3`. The measurement above used 100 virtual nodes to get an even distribution; three is enough to demonstrate that the mechanism works, and nowhere near enough to demonstrate that it works well. Anyone copying this file into a real service needs to raise that number, and needs to know why, which is the whole reason this essay measured the difference rather than asserting it.

Both limitations have the same shape: swap the plain Python `list` for a structure with logarithmic insertion and removal, not just logarithmic lookup. A sorted balanced tree, or the `sortedcontainers` package's `SortedList` on the Python side, or a real production system's own membership ring data structure, all buy back the `O(n)` removal cost this file accepts in exchange for staying dependency-free and readable in one sitting. That tradeoff, dependency-free and O(n) versus one extra import and O(log n), is a legitimate engineering decision, not a bug, and the right answer depends entirely on how large the ring gets and how often servers actually leave it, which is a question this file correctly leaves for whoever adopts it to answer for their own system.

## What This File Doesn't Do

Read on its own, this file answers exactly one question: given a key and a set of servers, which server owns it, and how much does that answer change when the set of servers changes. It says nothing about replication, nothing about what happens when the server `get_server` returns is unreachable, and nothing about giving a bigger server more of the ring than a smaller one beyond bluntly raising `num_replicas` for everyone uniformly.

Take the unreachable-server gap first, because it is the sharpest one. `get_server("UserA")` returns exactly one name, `S2` or whichever server owns that arc, and the file has no concept of "and here are the next two servers after that one, in case the first one is down." A cache that calls this exact function and gets `S2` back, only to find `S2` unreachable, has nowhere else to go without a second lookup and its own retry logic layered on top, logic this file does not contain. Real distributed stores answer that gap by asking the ring for N distinct owners of a key, not one, walking clockwise past the first hit to collect the next N-1 unique servers, and writing (or reading) from several of them instead of exactly one. That single change, from "return one owner" to "return the next N owners walking clockwise," is what turns a routing table into a replication scheme, and it is a change this file's four methods do not make.

The capacity gap is smaller in code but just as real in consequence. `add_server(name)` takes no weight argument; every server gets the same `num_replicas`, meaning a ring built from this file assumes every physical machine can handle an equal share of traffic. A cluster with one machine twice the size of the others has no way to tell this ring that, short of calling `add_server` for that machine with a different `num_replicas` than everyone else, a workaround the file's signature does not prevent but does not suggest either.

Those three gaps, no replication, no failure handling, no heterogeneous capacity, are not oversights in a teaching file; they are exactly the three problems a production system built on this same ring has to solve next, and they are the subject of tomorrow's case study: how Amazon's Dynamo paper took this identical scheme, MD5 hash, ring, virtual nodes, and built replication, quorum reads and writes, and heterogeneous node capacity on top of it, at a scale where "1/N of the keyspace moves" needed to be true for values of N in the thousands, not five.

---

*That was the morning's mental model made literal, one method at a time.
Tomorrow, 09:00: this exact ring at Amazon's scale — replication, quorum
reads and writes, and heterogeneous capacity built on top of it — in
`posts/2026-08-26-wed-am-essay-dynamo-case-study.md`. And this evening's
companion in that story is Wednesday's own code deep-dive, where the "return
the next N owners" change above becomes a runnable preference list and
quorum.*
