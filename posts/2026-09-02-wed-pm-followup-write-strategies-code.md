# Week 2 · Wed 2026-09-02 · 17:00 · Follow-up: The Reorder, Executable, Plus the Measurement That Proved Me Wrong

> Calendar row: W2 Wed PM, 17:00 (CSV row `29:2`). Format: code deep-dive.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: build a minimal runnable
> model of cache-aside vs write-through from the morning's case study |
> annotate the two lines people get wrong | state the expected output so
> readers can self-verify.
> Committed CTA: "Bookmark this; you will need it at 3am someday."
>
> Artifact: `experiments/week-02/cache_write_strategies.py`, written today,
> committed in this repository, 393 lines, Python 3.8+ standard library only,
> no third-party imports, seed 42, runs in under one second. The load-bearing
> excerpts are inline below and are copied from that file unmodified. Following
> the W1 Wed convention (commit f5f8dd8), the code that carries the claims
> lives in the article; the printing harness stays in the file.
>
> Week-2 scope fences:
> - `demo_remaining_race()` exists specifically to prove that delete-on-write
>   does NOT close the reader/writer race, so that Friday's stampede and lease
>   material is set up rather than pre-spent. The mechanism that closes it is
>   named and deferred.
> - The cache in the model evicts FIFO on purpose, and the code says so in its
>   own docstring, because eviction policy is Thu 09-03 and no result here
>   should be an artifact of a clever policy.
>
> Verification performed 2026-09-02:
> - Script run to completion, exit code 0, "All assertions passed" printed.
> - Determinism confirmed by running twice and comparing an md5 of stdout:
>   identical (44c0180cb0fcb8ed6d5a678489495cec, before the docstring edit
>   below; re-checked after).
> - Every number quoted in the prose is copied from the pasted stdout, which
>   is today's actual run, not a transcription.
>
> Adversarial review record (2026-09-02):
> - The failed assertion described in the body genuinely happened during
>   development today. The original assertion was
>   `assert aside_cold["hit_rate"] > through_cold["hit_rate"]` and it failed
>   with the message "cache-aside must recover better from an empty node".
>   It is reported because it was wrong, not as a narrative device ✓
> - The replacement assertions are stated in the body and are of two kinds:
>   structural ones true for any workload (`through_ro == 0.0`,
>   `aside_ro > 0.0`) and one determinism lock pinned to this seeded workload
>   (`round(aside_ro, 1) == 28.2`). The distinction is drawn explicitly so no
>   reader mistakes a seed-specific figure for a law ✓
> - 28.2% is explained rather than presented as impressive: "read but never
>   written" selects the cold tail of a zipfian distribution, and capacity 150
>   over keyspace 500 evicts those keys between infrequent reads ✓
> - The negative-caching limitation in `read_cache_aside` is documented in the
>   function's own docstring in the committed file and repeated here. It is a
>   stated scope boundary of a teaching model, not an undisclosed defect ✓
> - No timing or throughput claim is made beyond "under one second" ✓
> - **Publication-gap remediation (2026-09-04).** No post in this week's
>   sequence reached readers, so every backward reference to a sibling post
>   was a dangling reference to material nobody had seen. The body now
>   carries the referenced substance inline instead of pointing at it:
>   the identity and scale of the NSDI'13 paper, and one-line definitions of
>   cache-aside and write-through, so the code lands without the morning post. Written so it reads as a reminder to a sequential reader and as
>   sufficient context to a cold one ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-02-wed-am-essay-cache-aside-vs-write-through.md`
> is this morning's case study. This follow-up assumes the memcache decision
> and the primer's definitions and does not re-derive them.

---

**Topic:** A deterministic model of cache-aside and write-through, including the interleaving that makes update-on-write permanently wrong

**Subtitle:** You will run the two-writer reorder yourself, watch delete-on-write survive it, and see a measurement that contradicted my own prediction about cold cache nodes.

Good evening. This morning we read a sentence from a 2013 paper:

> We choose to delete cached data instead of updating it because deletes are idempotent.

That is the kind of sentence you nod at. Tonight you get to run it.

Context in case you did not catch the morning piece. The paper is "Scaling Memcache at Facebook," presented at NSDI in 2013, describing a memcached tier in front of sharded MySQL that handled, in its own abstract's words, "billions of requests per second" holding "trillions of items." They ran **cache-aside**, which means the application reads the cache first, falls back to the database on a miss, and puts the result in the cache itself. On a write they send SQL to the database and then delete the cached key rather than overwriting it with the new value.

The two patterns in play tonight, in one line each. **Cache-aside**: the application owns the cache, reads populate it, writes invalidate it, and the cache is never authoritative. **Write-through**: the application writes to the cache and the cache writes synchronously to the database, so the cache is never stale but it is now standing on the correctness path. Nearly every guide will tell you write-through has the better consistency story, which makes it worth asking why the largest documented deployment of either picked the other one.

One design decision before the code. Real concurrency is nondeterministic, which makes it worthless as evidence. If I spawned threads and told you "see, a race," you would be entitled to ask whether it reproduces, and about one time in fifty it would not. So the interleaving here is **written down** as an explicit schedule. It reproduces byte for byte on your machine, on mine, and on a colleague's laptop you are trying to convince.

## The four functions the whole argument rests on

```python
def read_cache_aside(cache, db, key):
    """Look-aside read: cache first, fill from the database on a miss."""
    value = cache.get(key)
    if value is None:
        value = db.get(key)
        if value is not None:
            cache.set(key, value)
    return value


def write_cache_aside_delete(cache, db, key, value):
    """Facebook's choice: write the database, then INVALIDATE the key."""
    db.set(key, value)
    cache.delete(key)


def write_cache_aside_update(cache, db, key, value):
    """The tempting alternative: write the database, then OVERWRITE the key."""
    db.set(key, value)
    cache.set(key, value)


def write_write_through(cache, db, key, value):
    """Write both, synchronously, every time. The cache is never stale."""
    db.set(key, value)
    cache.set(key, value)
```

Look at `write_cache_aside_update` and `write_write_through`. They are line for line identical. That is not sloppiness, it is the actual situation: the difference between "cache-aside with update-on-write" and "write-through" is not in the write path at all, it is in whether reads populate the cache. Two patterns that most guides draw as opposites share their entire write implementation, and I think that is worth noticing before we go further.

## Part one: the reorder, in four steps

```python
def demo_writer_reorder():
    """Part 1: two writers, one reordered cache operation, two outcomes.

    Schedule (identical for both strategies, applied step by step):
        1. writer A commits x=A to the database
        2. writer B commits x=B to the database   (B is the later truth)
        3. writer B's CACHE operation lands
        4. writer A's CACHE operation lands       (arrives out of order)
    """
    results = []
    for cache_op in ("update", "delete"):
        db, cache = Database(), Cache(CACHE_CAPACITY)
        db.seed(["x"], lambda key: "v0")
        cache.set("x", "v0")

        db.set("x", "A")                       # step 1
        db.set("x", "B")                       # step 2
        if cache_op == "update":
            cache.set("x", "B")                # step 3
            cache.set("x", "A")                # step 4, reordered
        else:
            cache.delete("x")                  # step 3
            cache.delete("x")                  # step 4, reordered, harmless
        results.append((cache.get("x"), db.data["x"]))
    return results[0], results[1]
```

Nothing exotic happens here. Two writers commit in one order and their cache operations land in the other, which is an entirely ordinary thing for two processes on two machines talking to two services to do.

The result:

```
  update-on-write  cache='A'    database='B'     DISAGREE
  delete-on-write  cache=None   database='B'     AGREE (empty)
```

The database says `B`, because `B` was committed last and the database is the authority. The update-on-write cache says `A`, confidently, and will keep saying `A` to every reader until something expires it or overwrites it. Nothing in the system is aware anything is wrong.

The delete-on-write cache says nothing at all, which is the correct amount to say. The next read goes to the database and gets `B`.

That is idempotence earning its keep. Two deletes in either order are one delete. Two writes in either order are whichever one arrived last, and nobody chose which that was.

## The two lines people get wrong

**Line one: the order of the two statements inside the write.**

```python
db.set(key, value)      # database first
cache.delete(key)       # cache second
```

Swap those and you have introduced a window. Delete the cached key first, and any reader that misses in that instant will go to the database, read the **old** value, and put it back in the cache, all before your write lands. Now you have a freshly repopulated cache holding a value your write was about to replace.

Database first, then invalidate, keeps that window as small as the code can make it. This is one of those orderings that looks arbitrary until you draw the interleaving once, and then it never looks arbitrary again.

**Line two: using `None` to mean two different things.**

```python
value = cache.get(key)
if value is None:
    value = db.get(key)
```

In this model, `None` means "not in the cache." But `db.get` also returns `None` when there is no such row. The moment you have a key that legitimately has no value, the cache can never store that fact, so every request for it goes to the database. Forever.

That is the negative-caching bug, and it is the most common way a working cache-aside implementation quietly stops being a cache for exactly the keys that are being hammered by something abusive. The fix is a distinct sentinel object for "cached, and the answer is nothing."

I left the conflation in the model deliberately, because the model never stores a `None` and so cannot trip it, and adding a sentinel would put an extra concept in front of the thing we are here to see. But the committed file says so in the function's own docstring rather than letting you discover it, and if you take this shape into production, that is the first line to change.

## The race that delete-on-write does not fix

I want to be careful not to oversell the pattern I just praised.

```python
def demo_remaining_race():
    """The race delete-on-write does NOT fix, shown rather than hidden.

    Schedule:
        1. reader misses the cache and reads v0 from the database
        2. a writer commits v1 and deletes the (already absent) key
        3. the reader's delayed fill writes its stale v0 into the cache
    """
    db, cache = Database(), Cache(CACHE_CAPACITY)
    db.seed(["y"], lambda key: "v0")

    assert cache.get("y") is None, "precondition: key must start uncached"
    in_flight = db.get("y")                          # step 1, reader holds v0
    write_cache_aside_delete(cache, db, "y", "v1")   # step 2
    cache.set("y", in_flight)                        # step 3, late fill wins
    return cache.get("y"), db.data["y"]
```

Output:

```
  late read-fill   cache='v0'   database='v1'    DISAGREE
```

A slow reader, holding a value it fetched before your write existed, arrives after your invalidation and helpfully caches it. The delete happened. It deleted nothing, because the key was not there yet. Then the stale fill landed.

Delete-on-write fixes writer against writer. It does not fix reader against writer. Closing that one requires the cache to know that a fill is in flight and to refuse the stale one, which is exactly what memcached leases do, and leases are Friday's post. I am not going to pretend tonight solved it.

## Part three, where I was wrong

Here is the part I would normally quietly delete.

I predicted that a cache node coming back empty would hurt write-through more than cache-aside, because write-through only repopulates on writes while cache-aside repopulates on reads. The primer says as much at line 1271: "the new node will not cache entries until the entry is updated in the database."

So I wrote the assertion that encoded my prediction:

```python
assert aside_cold["hit_rate"] > through_cold["hit_rate"], \
    "cache-aside must recover better from an empty node"
```

It failed.

```
  cache-aside (delete)        71.2%       5,172       1,997
  write-through               73.2%       4,543       1,997
```

Write-through recovered **better**, by two points. My mental model was incomplete in an obvious way once the number is in front of you: cache-aside spends the whole run deleting its own entries on every write, and write-through never does. That self-inflicted miss rate outweighed the cold start.

The right response to a failed assertion is not to loosen it until it passes. It is to work out what question the aggregate was failing to ask.

So Part 3 now separates the reads after the node replacement into keys that got written again, and keys that were only ever read:

```python
    def read_only_hit_rate(self):
        """Hit rate over reads of keys never written after the replacement."""
        hits = misses = 0
        for key, (key_hits, key_misses) in self.reads.items():
            if key not in self.written:
                hits += key_hits
                misses += key_misses
        total = hits + misses
        return (0.0 if total == 0 else 100.0 * hits / total), total
```

And there the primer's claim shows up perfectly:

```
    cache-aside (delete)    28.2% over 1,067 reads
    write-through            0.0% over 1,067 reads
    gap: +28.2 points
```

Zero. Not low, not degraded. Exactly zero, over more than a thousand reads, because a write-through cache has no mechanism whatsoever by which a read can populate it, so a key nobody writes is a key that will never be cached again on that node.

The lesson is not really about caching. It is that the aggregate hid a total failure. Write-through's cold-node penalty is 100% severe on the affected keys and invisible in the average, because the affected keys are by definition the ones with the least traffic. If you were watching a hit-rate dashboard during that node replacement, you would have seen a healthy number and a slow tail you could not explain.

The assertions I replaced mine with are of two kinds, and the difference matters:

```python
    # Structural claims, true for any workload:
    assert through_ro == 0.0
    assert aside_ro > 0.0
    # Determinism lock on this specific workload:
    assert round(aside_ro, 1) == 28.2
```

The first two are laws. The third is a regression check on a seed, and 28.2% is modest for a reason worth saying out loud: "read but never written" selects the cold tail of a skewed distribution, and a capacity of 150 over a keyspace of 500 evicts those keys between their infrequent reads. Low is the honest answer for that tail. Zero is the structural one.

## Expected output, so you can self-verify

```
python3 experiments/week-02/cache_write_strategies.py
```

The last line should read:

```
All assertions passed. Numbers reproduce with seed 42.
```

And these six figures should match exactly:

| check | expected |
|---|---|
| update-on-write reorder | cache `'A'`, database `'B'`, DISAGREE |
| delete-on-write reorder | cache `None`, database `'B'` |
| steady state hit rate, cache-aside | 71.5% |
| steady state hit rate, write-through | 76.5% |
| read-only keys after node replacement, cache-aside | 28.2% |
| read-only keys after node replacement, write-through | 0.0% |

If any of those differ, the run is not deterministic on your machine and I want to know, because the whole point of writing the interleaving down was that it should not be.

Change one thing and re-run, if you want the real value out of this. Set `READ_RATIO` to `0.5` and watch the steady-state gap between the two strategies move, because that gap is a function of how often you invalidate.

Bookmark this. You will need it at 3am someday.

---

*Tomorrow, 09:00: the cache is full and something has to go. Three eviction policies across three workloads, and the policy that wins twice before finishing last at 18.4%.*
