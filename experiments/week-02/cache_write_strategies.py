"""Cache-aside vs write-through: a deterministic, runnable model.

Companion artifact for the week-2 Wednesday posts (2026-09-02):
  AM  case study  - "Scaling Memcache at Facebook" (NSDI'13), look-aside
                    caching and the decision to delete rather than update.
  PM  code deep-dive - this file.

The model answers three questions with measurements rather than opinion:

  Part 1  Why does Facebook DELETE a cached key on write instead of
          UPDATING it? Because two concurrent writers whose cache
          operations arrive out of order leave an UPDATE-based cache
          permanently disagreeing with the database, while DELETE is
          idempotent and cannot be reordered into a wrong answer.

  Part 2  What does each strategy cost in backend work, and what is the
          hit rate under a read-heavy workload?

  Part 3  What happens when a cache node is replaced and comes back
          empty? Cache-aside refills from reads. Write-through refills
          only from writes, so a cold node stays cold for anything that
          is read but not written.

Concurrency is modelled as an EXPLICIT operation schedule, not threads.
Real interleavings are nondeterministic and therefore useless as
teaching evidence; here the interleaving is written down, so the result
reproduces byte for byte on every machine.

Scope note: delete-on-write removes the writer/writer reorder shown in
Part 1. It does NOT remove the reader/writer race in which a slow cache
fill overwrites a newer value. That race is what memcached leases exist
to solve, and it is the subject of the Friday 2026-09-04 posts. Part 1
demonstrates the race it does solve, and `demo_remaining_race()` proves
the other one still exists rather than pretending otherwise.

Run:      python3 cache_write_strategies.py
Depends:  Python 3.8+ standard library only.
Bounds:   fixed workload of 20,000 operations, seed 42, runs in under 1s.
"""

import random
import sys

SEED = 42
KEYSPACE = 500
OPERATIONS = 20_000
READ_RATIO = 0.9
CACHE_CAPACITY = 150
ZIPF_SKEW = 1.1


class Database:
    """Authoritative store. Counts every operation that reaches it."""

    def __init__(self):
        self.data = {}
        self.reads = 0
        self.writes = 0

    def get(self, key):
        self.reads += 1
        return self.data.get(key)

    def set(self, key, value):
        self.writes += 1
        self.data[key] = value

    def seed(self, keys, value_fn):
        """Populate without polluting the counters we are measuring."""
        for key in keys:
            self.data[key] = value_fn(key)


class Cache:
    """Bounded key-value cache with explicit hit/miss accounting.

    Eviction is first-in-first-out. That choice is deliberate and is NOT
    the subject here: eviction policy is the Thursday 2026-09-03 material.
    FIFO is used because it is the least interesting policy available, so
    no result below can be an artifact of a clever one.
    """

    def __init__(self, capacity):
        assert capacity > 0, "capacity must be positive"
        self.capacity = capacity
        self.data = {}
        self.order = []
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key):
        if key in self.data:
            self.hits += 1
            return self.data[key]
        self.misses += 1
        return None

    def set(self, key, value):
        if key not in self.data:
            if len(self.data) >= self.capacity:
                oldest = self.order.pop(0)
                del self.data[oldest]
                self.evictions += 1
            self.order.append(key)
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.order.remove(key)

    def clear(self):
        """Simulate node replacement: the process restarts empty."""
        self.data.clear()
        self.order.clear()

    def hit_rate(self):
        total = self.hits + self.misses
        return 0.0 if total == 0 else 100.0 * self.hits / total


def read_cache_aside(cache, db, key):
    """Look-aside read: cache first, fill from the database on a miss.

    KNOWN LIMITATION, stated rather than hidden: `None` is used both for
    "not in the cache" and for "no such row". This model never stores a
    None value, so the conflation cannot fire here. Production code must
    use a distinct sentinel, because otherwise a legitimately absent row
    is re-fetched from the database on every single request forever, which
    is the negative-caching bug and is the most common way a working
    cache-aside implementation quietly stops being a cache.
    """
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


def read_write_through(cache, db, key):
    """Under write-through the cache is the read path; misses still fall back."""
    value = cache.get(key)
    if value is None:
        value = db.get(key)
    return value


def write_write_through(cache, db, key, value):
    """Write both, synchronously, every time. The cache is never stale."""
    db.set(key, value)
    cache.set(key, value)


def demo_writer_reorder():
    """Part 1: two writers, one reordered cache operation, two outcomes.

    Schedule (identical for both strategies, applied step by step):
        1. writer A commits x=A to the database
        2. writer B commits x=B to the database   (B is the later truth)
        3. writer B's CACHE operation lands
        4. writer A's CACHE operation lands       (arrives out of order)

    Returns (update_result, delete_result) as (cached, stored) tuples.
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


def demo_remaining_race():
    """The race delete-on-write does NOT fix, shown rather than hidden.

    Schedule:
        1. reader misses the cache and reads v0 from the database
        2. a writer commits v1 and deletes the (already absent) key
        3. the reader's delayed fill writes its stale v0 into the cache

    Returns (cached, stored). They disagree, and that is why leases exist.
    """
    db, cache = Database(), Cache(CACHE_CAPACITY)
    db.seed(["y"], lambda key: "v0")

    assert cache.get("y") is None, "precondition: key must start uncached"
    in_flight = db.get("y")                    # step 1, reader holds v0
    write_cache_aside_delete(cache, db, "y", "v1")   # step 2
    cache.set("y", in_flight)                  # step 3, late fill wins
    return cache.get("y"), db.data["y"]


def zipf_keys(rng, count):
    """Pre-generate a skewed access sequence so every run sees the same keys."""
    weights = [1.0 / ((rank + 1) ** ZIPF_SKEW) for rank in range(KEYSPACE)]
    population = list(range(KEYSPACE))
    return rng.choices(population, weights=weights, k=count)


class PostClearStats:
    """Reads observed after a node replacement, kept per key.

    Exists to isolate the primer's specific claim about write-through:
    "the new node will not cache entries until the entry is updated in the
    database." Aggregate hit rate cannot test that, because it mixes keys
    that were rewritten (and so repopulated) with keys that were only ever
    read. This separates them.
    """

    def __init__(self):
        self.reads = {}      # key -> [hits, misses]
        self.written = set()

    def record_read(self, key, was_hit):
        bucket = self.reads.setdefault(key, [0, 0])
        bucket[0 if was_hit else 1] += 1

    def record_write(self, key):
        self.written.add(key)

    def read_only_hit_rate(self):
        """Hit rate over reads of keys never written after the replacement."""
        hits = misses = 0
        for key, (key_hits, key_misses) in self.reads.items():
            if key not in self.written:
                hits += key_hits
                misses += key_misses
        total = hits + misses
        return (0.0 if total == 0 else 100.0 * hits / total), total


def run_workload(strategy, keys, decisions, clear_at=None):
    """Drive one strategy through an identical, pre-computed operation list.

    strategy   "aside" or "through"
    keys       pre-generated key sequence, shared by all strategies
    decisions  pre-generated read/write flags, shared by all strategies
    clear_at   optional index at which the cache node is replaced (emptied)

    Returns a dict of measurements.
    """
    assert strategy in ("aside", "through"), f"unknown strategy {strategy!r}"
    db, cache = Database(), Cache(CACHE_CAPACITY)
    db.seed(range(KEYSPACE), lambda key: f"value-{key}-v0")
    if strategy == "through":
        for key in range(min(KEYSPACE, CACHE_CAPACITY)):
            cache.set(key, db.data[key])

    post, version, cleared = PostClearStats(), 0, False
    for index, (key, is_read) in enumerate(zip(keys, decisions)):
        if clear_at is not None and index == clear_at:
            cache.clear()
            cache.hits = cache.misses = 0
            cleared = True
        if is_read:
            before = cache.hits
            if strategy == "aside":
                read_cache_aside(cache, db, key)
            else:
                read_write_through(cache, db, key)
            if cleared:
                post.record_read(key, cache.hits > before)
        else:
            version += 1
            value = f"value-{key}-v{version}"
            if strategy == "aside":
                write_cache_aside_delete(cache, db, key, value)
            else:
                write_write_through(cache, db, key, value)
            if cleared:
                post.record_write(key)
    read_only_rate, read_only_ops = post.read_only_hit_rate()
    return {"hit_rate": cache.hit_rate(), "db_reads": db.reads,
            "db_writes": db.writes, "evictions": cache.evictions,
            "read_only_hit_rate": read_only_rate,
            "read_only_ops": read_only_ops}


def format_row(label, stats):
    return (f"  {label:<26}{stats['hit_rate']:6.1f}%"
            f"{stats['db_reads']:>12,}{stats['db_writes']:>12,}")


def main():
    print("=" * 68)
    print("Cache-aside vs write-through: measured, not argued")
    print(f"seed={SEED}  keyspace={KEYSPACE}  capacity={CACHE_CAPACITY}"
          f"  ops={OPERATIONS:,}  reads={READ_RATIO:.0%}")
    print("=" * 68)

    print("\nPart 1: two writers, one reordered cache operation")
    (upd_cached, upd_stored), (del_cached, del_stored) = demo_writer_reorder()
    print(f"  update-on-write  cache={upd_cached!r:6} database={upd_stored!r:6}"
          f"  {'AGREE' if upd_cached == upd_stored else 'DISAGREE'}")
    print(f"  delete-on-write  cache={del_cached!r:6} database={del_stored!r:6}"
          f"  {'AGREE' if del_cached == del_stored else 'AGREE (empty)'}")
    assert upd_cached == "A" and upd_stored == "B", "reorder demo drifted"
    assert del_cached is None and del_stored == "B", "delete demo drifted"

    print("\n  the race delete-on-write does NOT fix (see Friday):")
    race_cached, race_stored = demo_remaining_race()
    print(f"  late read-fill   cache={race_cached!r:6} database={race_stored!r:6}"
          "  DISAGREE")
    assert race_cached == "v0" and race_stored == "v1", "race demo drifted"

    rng = random.Random(SEED)
    keys = zipf_keys(rng, OPERATIONS)
    decisions = [rng.random() < READ_RATIO for _ in range(OPERATIONS)]

    print("\nPart 2: steady state cost")
    print(f"  {'strategy':<26}{'hit rate':>7}{'db reads':>12}{'db writes':>12}")
    print("  " + "-" * 55)
    aside = run_workload("aside", keys, decisions)
    through = run_workload("through", keys, decisions)
    print(format_row("cache-aside (delete)", aside))
    print(format_row("write-through", through))
    assert aside["db_writes"] == through["db_writes"], "write counts must match"
    assert through["hit_rate"] > aside["hit_rate"], "write-through should hit more"

    print("\nPart 3: a cache node is replaced halfway through and comes back empty")
    half = OPERATIONS // 2
    aside_cold = run_workload("aside", keys, decisions, clear_at=half)
    through_cold = run_workload("through", keys, decisions, clear_at=half)
    print(f"  {'strategy':<26}{'hit rate':>7}{'db reads':>12}{'db writes':>12}")
    print("  " + "-" * 55)
    print(format_row("cache-aside (delete)", aside_cold))
    print(format_row("write-through", through_cold))
    print("\n  aggregate hit rate does NOT show the cold-node problem:")
    print(f"    write-through still leads by "
          f"{through_cold['hit_rate'] - aside_cold['hit_rate']:+.1f} points,")
    print("    because never invalidating outweighs starting empty.")
    assert through_cold["hit_rate"] > aside_cold["hit_rate"], \
        "aggregate result drifted; the surprise in Part 3 is load-bearing"

    print("\n  now isolate keys that were READ but never WRITTEN after the")
    print("  replacement, which is the case the primer actually warns about:")
    aside_ro = aside_cold["read_only_hit_rate"]
    through_ro = through_cold["read_only_hit_rate"]
    print(f"    cache-aside (delete)   {aside_ro:5.1f}% over "
          f"{aside_cold['read_only_ops']:,} reads")
    print(f"    write-through          {through_ro:5.1f}% over "
          f"{through_cold['read_only_ops']:,} reads")
    print(f"    gap: {aside_ro - through_ro:+.1f} points")
    # Structural claims, true for any workload:
    assert through_ro == 0.0, \
        "write-through must never serve a read-only key from a cold node"
    assert aside_ro > 0.0, \
        "cache-aside must be able to refill a read-only key from a read"
    # Determinism lock on this specific workload. The absolute figure is
    # modest because "read but never written" selects the cold tail of a
    # zipfian distribution, and a capacity of 150 over a keyspace of 500
    # evicts those keys between their infrequent reads. Low is the honest
    # answer; zero is the structural one.
    assert round(aside_ro, 1) == 28.2, \
        f"seeded workload drifted: expected 28.2, measured {aside_ro:.1f}"

    print("\nReadings:")
    print("  1. delete is idempotent, so reordering two deletes cannot lie;")
    print("     reordering two updates can, and does, permanently")
    print("  2. write-through buys freshness and a higher steady-state hit")
    print("     rate by writing the cache on every write, read or not")
    print("  3. the cold-node penalty is real but INVISIBLE in the aggregate:")
    print("     it lands entirely on keys nobody writes, at exactly 0%")
    print("\nAll assertions passed. Numbers reproduce with seed 42.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
