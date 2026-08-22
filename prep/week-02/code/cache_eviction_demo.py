"""Cache eviction policies, measured, in one file.

Companion demo for the week-2 Thursday tutorial (2026-09-03, YouTube):
"Hands-on: cache eviction policies in under an hour".

Implements FIFO, LRU and LFU behind one interface and measures hit rate
on three workloads that decide real caching arguments:
  1. zipfian traffic (what production key popularity actually looks like),
  2. a sequential scan flood (the workload that famously destroys LRU),
  3. a shifting hot set (where LFU's long memory becomes a liability).

Run:      python3 cache_eviction_demo.py
Depends:  Python 3.8+ standard library only. Deterministic (seeded).
Runtime:  under ten seconds on a laptop.
"""

import random
from collections import Counter, OrderedDict, defaultdict

SEED = 42
CAPACITY = 100
KEYSPACE = 2_000
REQUESTS = 200_000


# ------------------------------------------------------------------ caches


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


class LRUCache:
    """Evicts the least recently used key. OrderedDict as the classic recency list."""

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


# --------------------------------------------------------------- workloads


def zipf_keys(rng, n, keyspace, s=1.1):
    """Zipfian sample: key k drawn with probability proportional to 1/k^s."""
    population = list(range(keyspace))
    weights = [1.0 / (k + 1) ** s for k in range(keyspace)]
    return rng.choices(population, weights=weights, k=n)


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


# ----------------------------------------------------------------- harness


def run(cache_cls, keys):
    cache = cache_cls(CAPACITY)
    hits = 0
    for key in keys:
        if cache.get(key) is None:
            cache.put(key, key)  # cache-aside fill on miss
        else:
            hits += 1
    return hits / len(keys) * 100


def main():
    print("=" * 68)
    print(f"Cache eviction shoot-out: capacity={CAPACITY}, keyspace={KEYSPACE}")
    print(f"seed={SEED}; hit rate in % of requests, higher is better")
    print("=" * 68)

    workloads = [
        ("zipfian steady state", workload_zipf),
        ("zipfian + scan floods", workload_scan_flood),
        ("shifting hot set", workload_shifting_hotset),
    ]
    policies = [("FIFO", FIFOCache), ("LRU", LRUCache), ("LFU", LFUCache)]
    results = {}

    header = f"\n{'workload':<24}" + "".join(f"{name:>8}" for name, _ in policies)
    print(header)
    print("-" * len(header))
    for wl_name, wl_fn in workloads:
        keys = wl_fn(random.Random(SEED))
        assert len(keys) >= 100_000, "workload too small to be meaningful"
        row = {}
        for p_name, p_cls in policies:
            row[p_name] = run(p_cls, keys)
        results[wl_name] = row
        print(f"{wl_name:<24}" + "".join(f"{row[name]:>7.1f}%" for name, _ in policies))

    # The three claims the video makes, held up by assertions:
    z, s, h = (results[w] for w, _ in workloads)
    assert z["LRU"] > z["FIFO"], "recency must beat pure age on zipfian traffic"
    assert z["LFU"] >= z["LRU"], "frequency must at least match recency on a stable hot set"
    assert s["LFU"] - s["LRU"] >= 5.0, "scan flood must hurt LRU far more than LFU"
    assert h["LRU"] > h["LFU"], "a moving hot set must punish LFU's long memory"

    print("\nReadings:")
    print("  1. stable zipf: LFU's frequency memory wins; FIFO pays for ignoring patterns")
    print("  2. scan floods evict LRU's whole hot set; LFU barely notices")
    print("  3. when popularity shifts, LFU clings to stale frequency and loses")
    print("  no single winner: the workload picks the policy, and Redis ships")
    print("  approximations (allkeys-lru / allkeys-lfu) for exactly this reason")
    print("\nAll assertions passed. Numbers reproduce with seed 42.")


if __name__ == "__main__":
    main()
