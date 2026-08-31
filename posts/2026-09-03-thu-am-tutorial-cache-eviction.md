# Week 2 · Thu 2026-09-03 · Hands-on: Build Three Eviction Policies and Watch the Winner Lose

> Calendar row: W2 Thu AM, 09:00 (CSV row `30:2`). Format: hands-on tutorial.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/ByteByteGoHq/system-design-101.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: define the end state,
> what exists and runs when the hour is up | give the 4 to 6 numbered steps
> with the commands or code per step | include the verification step that
> proves it worked. Committed CTA: "Tag someone who is debugging this right now."
>
> **Source honesty note.** As recorded in
> `prep/week-02/thu-2026-09-03-youtube-tutorial.md:6-8`, the CSV source repo's
> cache-eviction entries are links out to two external ByteByteGo guides, not
> runnable material. The demo in this repository supplies the code. The repo is
> credited for what it is, an index, and is not dressed up as an implementation.
>
> Companion artifact: `prep/week-02/code/cache_eviction_demo.py`, 216 lines,
> committed in this repository, Python 3.8+ standard library only, seed 42.
> A video production plan for this slot exists at
> `prep/week-02/thu-2026-09-03-youtube-tutorial.md`; this post is the written
> tutorial and stands alone.
>
> Week-2 scope fences:
> - What to do about a stampede of concurrent misses is Fri 09-04. This post
>   measures which key gets discarded, not what happens when many callers miss
>   the same key at once.
> - Cache key construction is Mon 08-31 and is referenced, not re-derived.
>
> Sources verified 2026-09-03:
> - `github.com/ByteByteGoHq/system-design-101`, GitHub API: 87,742 stars,
>   last push 2025-04-04, not archived.
> - Redis, "Key eviction" (redis.io/docs/latest/develop/reference/eviction/),
>   fetched today. All ten policy names, the approximation rationale, the
>   `maxmemory-samples` default of 5, the Morris counter and decay description,
>   the `lfu-log-factor 10` and `lfu-decay-time 1` defaults, the counter range
>   0-255, the one-million-request saturation and one-minute decay defaults,
>   and the `keyspace_hits` / `keyspace_misses` formula are quoted from that
>   page.
> - Demo re-run on this machine today: "All assertions passed" printed, runtime
>   0.8 seconds, all nine hit rates identical to the prep table recorded
>   2026-08-22.
>
> Adversarial review record (2026-09-03):
> - The nine hit rates in the table are today's stdout, pasted. The prep
>   recorded the same nine figures on 2026-08-22 and they reproduced exactly,
>   which is the point of seeding ✓
> - **Prep correction.** `prep/week-02/thu-2026-09-03-youtube-tutorial.md:49`
>   listed Redis policies as "allkeys-lru / allkeys-lfu" only. Today's fetch
>   shows Redis has since added Least Recently Modified in version 8.6, giving
>   `allkeys-lrm` and `volatile-lrm`. The standing day-of re-verification rule
>   in `prep/README.md:71` is what caught it. The post uses the current list ✓
> - No claim is made that this demo predicts any production system's hit rate.
>   Capacity, keyspace, request count, skew and seed are all stated, and the
>   closing section says explicitly that the numbers are a property of these
>   parameters ✓
> - "18.4%" is not presented as a general fact about LFU. It is the measured
>   result of one synthetic workload designed to be adversarial to LFU, and
>   the post says so before quoting it ✓
> - Zero em dashes.

---

**Topic:** Building FIFO, LRU and LFU from scratch and measuring them against three workloads that decide real caching arguments

**Subtitle:** In about an hour you will have a file that proves the best policy in two tests collapses to an 18.4% hit rate in the third, and you will know exactly why.

Good morning. Quick question before we start.

Your cache is full. A new key arrives. Something has to go. Which one?

Most of us answer that question once, early, by typing a config value we half remember, and then never think about it again. It sits there for years. It is one of the highest-leverage single lines in a caching setup and it usually gets less thought than a variable name.

Today we fix that, by measuring instead of arguing. An hour, one file, no installs.

## The end state

When you are done you will have a single Python file that:

- implements **FIFO**, **LRU** and **LFU** behind one shared interface, with LFU running in constant time rather than the naive heap version
- drives all three through **three different workloads**: steady skewed traffic, traffic interrupted by scans, and traffic whose popular keys move
- prints a nine-cell table of hit rates
- **asserts** the claims this post makes, so that if a claim is wrong, the program fails rather than the post lying

It runs in under a second, needs Python 3.8 or newer, and imports nothing outside the standard library.

Here is the table you are aiming at, produced on my machine this morning:

```
workload                    FIFO     LRU     LFU
-------------------------------------------------
zipfian steady state       56.1%   61.7%   69.7%
zipfian + scan floods      48.2%   52.9%   59.8%
shifting hot set           56.1%   61.6%   18.4%
```

Look at the bottom right. LFU wins the first two rows comfortably, then finishes at 18.4%, roughly a third of what the policy it just beat manages on the same data. That collapse is the lesson, and by the end of the hour you will be able to explain it in one sentence.

## Step 1: FIFO, the honest baseline

Start with the policy nobody recommends, because it makes the others legible.

```python
class FIFOCache:
    """Evicts the oldest inserted key. Insertion order, nothing else."""

    def __init__(self, capacity):
        assert capacity > 0, "capacity must be positive"
        self.capacity = capacity
        self.store = OrderedDict()

    def get(self, key):
        return self.store.get(key)

    def put(self, key, value):
        if key in self.store:
            self.store[key] = value  # no reordering: FIFO ignores recency
            return
        if len(self.store) >= self.capacity:
            self.store.popitem(last=False)
        self.store[key] = value
```

The whole policy is `popitem(last=False)`, which removes the oldest inserted entry.

Pay attention to the comment on the third line of `put`. When a key already present is written again, FIFO deliberately does **not** move it. That single omission is the entire difference between this class and the next one. Everything else is identical.

Think of it as a queue at a bakery counter that never lets anyone rejoin. You are served in the order you arrived, no matter how often you come back.

## Step 2: LRU, which is FIFO plus one line

```python
class LRUCache:
    """Evicts the least recently used key."""

    def __init__(self, capacity):
        assert capacity > 0, "capacity must be positive"
        self.capacity = capacity
        self.store = OrderedDict()

    def get(self, key):
        if key not in self.store:
            return None
        self.store.move_to_end(key)  # touch = most recently used
        return self.store[key]

    def put(self, key, value):
        if key in self.store:
            self.store.move_to_end(key)
            self.store[key] = value
            return
        if len(self.store) >= self.capacity:
            self.store.popitem(last=False)
        self.store[key] = value
```

`move_to_end` on every touch. That is it. LRU is FIFO that lets you rejoin the queue at the back every time you are served.

Notice the assumption baked in: **recent use predicts future use.** That is usually true and it is why LRU is the sensible default. Hold onto the word "usually," because step 5 is going to attack it.

## Step 3: LFU without the heap

Most LFU implementations you find online use a priority queue and are O(log n) per operation. You can do it in constant time with frequency buckets and a floating minimum pointer, and it is genuinely elegant.

```python
class LFUCache:
    """Evicts the least frequently used key; LRU order breaks frequency ties.

    Frequency buckets: freq -> OrderedDict of keys, plus a floating
    min_freq pointer. All operations O(1).
    """

    def __init__(self, capacity):
        assert capacity > 0, "capacity must be positive"
        self.capacity = capacity
        self.values = {}
        self.freq_of = {}
        self.bucket = defaultdict(OrderedDict)
        self.min_freq = 0

    def _touch(self, key):
        f = self.freq_of[key]
        del self.bucket[f][key]
        if not self.bucket[f]:
            del self.bucket[f]
            if self.min_freq == f:
                self.min_freq = f + 1
        self.freq_of[key] = f + 1
        self.bucket[f + 1][key] = None

    def get(self, key):
        if key not in self.values:
            return None
        self._touch(key)
        return self.values[key]

    def put(self, key, value):
        if key in self.values:
            self.values[key] = value
            self._touch(key)
            return
        if len(self.values) >= self.capacity:
            evict_key, _ = self.bucket[self.min_freq].popitem(last=False)
            if not self.bucket[self.min_freq]:
                del self.bucket[self.min_freq]
            del self.values[evict_key]
            del self.freq_of[evict_key]
        self.values[key] = value
        self.freq_of[key] = 1
        self.bucket[1][key] = None
        self.min_freq = 1
```

Two details worth slowing down for, because they are where people get this wrong.

**The `min_freq` pointer only ever moves in two places.** It increments inside `_touch`, but only when the bucket it just emptied was the minimum. And it resets to 1 in `put`, because a newly inserted key has frequency 1 and 1 is now the minimum by definition. Get either wrong and the cache still works, silently evicting the wrong key forever.

**Inside a bucket, order is LRU.** Each bucket is an `OrderedDict` and eviction takes `popitem(last=False)`. So when several keys tie on frequency, the least recently touched one goes. LFU without a tiebreaker is underspecified, and "whichever the dict happened to yield" is not a policy.

## Step 4: three workloads, because one workload is an opinion

This is the part that turns the exercise from a coding kata into something that will change a decision.

```python
def workload_zipf(rng):
    """Steady zipfian popularity - the default shape of production traffic."""
    return [f"k{k}" for k in zipf_keys(rng, REQUESTS, KEYSPACE)]


def workload_scan_flood(rng):
    """Zipfian traffic interrupted by full one-pass scans (batch jobs,
    crawlers, analytics). Each scanned key is touched once, never again."""
    keys = []
    scan_id = 0
    for chunk in range(10):
        keys += [f"k{k}" for k in zipf_keys(rng, 15_000, KEYSPACE)]
        if chunk % 2 == 1:  # a scan after every second chunk
            keys += [f"scan{scan_id}-{i}" for i in range(5_000)]
            scan_id += 1
    return keys


def workload_shifting_hotset(rng):
    """The hot set moves every 40k requests (deploys, trends, region
    failover). Old popularity stops predicting new popularity."""
    keys = []
    for epoch in range(5):
        base = epoch * 400  # shift the popular region of the keyspace
        keys += [f"k{(base + k) % KEYSPACE}" for k in zipf_keys(rng, 40_000, KEYSPACE)]
    return keys
```

Each of these is a real thing that happens to you:

- **Zipfian** is ordinary traffic. A few keys are enormously popular, most are not. This is the shape of nearly every user-facing workload.
- **Scan flood** is your nightly export, your analytics job, your search crawler. Something walks the whole keyspace once, touching each key exactly one time, and never comes back.
- **Shifting hot set** is a deploy, a trending story, a region failover. Yesterday's popular keys are not today's.

## Step 5: run it and read the table

```
python3 prep/week-02/code/cache_eviction_demo.py
```

```
====================================================================
Cache eviction shoot-out: capacity=100, keyspace=2000
seed=42; hit rate in % of requests, higher is better
====================================================================

workload                    FIFO     LRU     LFU
-------------------------------------------------
zipfian steady state       56.1%   61.7%   69.7%
zipfian + scan floods      48.2%   52.9%   59.8%
shifting hot set           56.1%   61.6%   18.4%
```

**Row one.** Everything behaves as the textbook says. Recency beats raw age, 61.7 against 56.1. Frequency beats recency, 69.7 against 61.7, because when popularity is stable, counting how often a key was wanted is simply a better predictor than remembering when it was last wanted.

**Row two, the scan flood.** Now watch LRU suffer. Every scanned key is touched once, and LRU dutifully treats each one as the most recently used thing in the cache, pushing genuinely hot keys toward eviction. Its hit rate falls 8.8 points. LFU barely notices, because a key touched once has a frequency of one and is the first thing thrown out. This is the classic argument for LFU and the table supports it.

**Row three, and this is why you did the exercise.** The hot set moves, and LFU goes to 18.4%.

Here is the one-sentence explanation. **Frequency is memory, and memory can be wrong.** Those old keys accumulated enormous counts during their popular epoch. When the traffic moves on, they are still sitting at the top of the frequency ranking, defended by history, while the keys people actually want now arrive with a frequency of 1 and get evicted immediately. LFU is not confused. It is doing precisely what it was asked to do, using evidence that has expired.

LRU has no such problem, because recency forgets automatically. That is the underrated property of LRU: not that it is smart, but that it is incapable of holding a grudge.

## Step 6: verify, and check it against what Redis actually ships

The verification step is built in. The script asserts the four claims this post makes:

```python
    assert z["LRU"] > z["FIFO"], "recency must beat pure age on zipfian traffic"
    assert z["LFU"] >= z["LRU"], "frequency must at least match recency on a stable hot set"
    assert s["LFU"] - s["LRU"] >= 5.0, "scan flood must hurt LRU far more than LFU"
    assert h["LRU"] > h["LFU"], "a moving hot set must punish LFU's long memory"
```

If the run ends with this line, everything above held:

```
All assertions passed. Numbers reproduce with seed 42.
```

If it does not, the post is wrong and I would like to know.

Now the part that makes this more than an exercise. Go and read Redis's key eviction documentation, and notice that everything you just built appears there in a slightly humbler form.

Redis does not implement true LRU. Its documentation says so plainly, and gives the reason: a true implementation costs more memory. Instead it samples a small number of keys at random and evicts the ones with the longest time since last access, with `maxmemory-samples` defaulting to 5.

LFU is approximated too, using a Morris counter, a probabilistic counter that estimates access frequency in a handful of bits, in a range of 0 to 255.

And now look at what they bolted on next to it, because it is the fix for the exact failure you just measured:

> combined with a decay period so that the counter is reduced over time. At some point we no longer want to consider keys as frequently accessed, even if they were in the past, so that the algorithm can adapt to a shift in the access pattern.

That is row three, solved. Redis defaults to saturating the counter at around one million requests and decaying it every one minute, tunable through `lfu-log-factor` (default 10) and `lfu-decay-time` (default 1 minute). And `lfu-decay-time 0` means never decay, which is to say, opt into an 18.4% row.

One more thing worth knowing, because it changed since these notes were first written. Redis's current policy list is longer than the two everyone quotes: `noeviction`, `allkeys-lru`, `allkeys-lrm`, `allkeys-lfu`, `allkeys-random`, `volatile-lru`, `volatile-lrm`, `volatile-lfu`, `volatile-random` and `volatile-ttl`. The `lrm` family is Least Recently Modified, added in Redis 8.6, which updates its timestamp on writes but not reads. My own prep notes for this post listed only the two common policies and were out of date by the time I came to write it, which is a decent argument for checking a version number before quoting a config value.

## What to do with this tomorrow

The decision rule that falls out of the table is short:

- **Stable popularity** and you can afford the bookkeeping: the LFU family, **with decay enabled**.
- **Shifting popularity, or anything that scans**: the LRU family, or a scan-resistant hybrid.
- **Genuinely uniform access**: random eviction is not a joke, and Redis ships `allkeys-random` for it.

But the rule underneath the rule is the one I would actually put on a wall. **Every eviction policy is a prediction about the future, and it is only as good as the assumption it encodes.** LRU predicts that recent means soon. LFU predicts that often means again. When your traffic stops matching the prediction, the policy does not warn you, it just quietly starts throwing away the right answers.

So: go and look at your `maxmemory-policy` today. Then find out whether anything in your system does a full scan on a schedule, and whether your popularity shifts on deploys. If you find a mismatch, you found something real, and it cost you an hour.

Tag someone who is debugging this right now.

---

*Today, 17:00: the five yes/no checks that catch most eviction mistakes before they ship, including the Redis setting that silently turns eviction off entirely.*

*Tomorrow, 09:00: a contrarian take. Most advice about cache stampede protection optimizes for the demo rather than the system you actually run.*
