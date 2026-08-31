"""Cache stampede protection, measured on both problems people confuse.

Companion artifact for the week-2 Friday posts (2026-09-04).

The standard advice is "put a lock around the regeneration so only one
caller recomputes." That advice is not wrong. It is an answer to ONE of
two different problems that both get called a stampede, and it makes a
measurable trade that its usual presentation leaves out.

  Scenario A  MANY READERS, ONE KEY. One hot key expires while N requests
              are in flight. Compared: no protection, a blocking lock, a
              memcached-style lease with retry, and serve-stale with
              background revalidation. The lock removes origin load and
              relocates it into concurrent waiters inside your own
              service, which is the resource that actually runs out.

  Scenario B  MANY KEYS, ONE MOMENT. A bulk write, deploy or cache warm
              gives a large set of keys the same TTL, so they expire
              together. Per-key locking cannot help: each key legitimately
              needs its one regeneration, and they are all due at once.
              TTL jitter is the mechanism that applies, and it is the one
              nobody demonstrates.

Everything is deterministic. Arrival times are generated from a fixed
seed and the simulation is closed-form arithmetic over those arrivals,
so there is no wall-clock timing and no flakiness.

Run:      python3 stampede_strategies.py
Depends:  Python 3.8+ standard library only.
Bounds:   two scenarios, 2,000 arrivals and 50,000 keys, runs in under 1s.
"""

import random
import statistics
import sys

SEED = 42

# Scenario A: many readers, one key.
READERS = 2_000
ARRIVAL_WINDOW_MS = 500     # requests for this key spread over half a second
REGEN_MS = 200              # cost of recomputing the value at the origin
CACHE_HIT_MS = 1            # cost of being served from cache
LEASE_RETRY_MS = 20         # how long a lease-denied client waits before retrying
POOL_SIZE = 200             # request-handling slots in the service

# Scenario B: many keys, one moment.
KEYS = 50_000
BASE_TTL_S = 600
JITTER_FRACTION = 0.10      # +/- 10% applied to each key's TTL
BUCKET_S = 1


def arrival_times(rng):
    """Deterministic, sorted arrival offsets in milliseconds."""
    times = sorted(rng.uniform(0.0, ARRIVAL_WINDOW_MS) for _ in range(READERS))
    assert times[0] >= 0.0, "arrivals must be non-negative"
    return times


def peak_overlap(intervals):
    """Largest number of intervals covering any single instant.

    Used for peak concurrent origin queries. Sweeps start and end events in
    time order, counting ends before starts at equal timestamps so that a
    query finishing exactly as another begins is not double counted.
    """
    events = []
    for start, end in intervals:
        events.append((start, 1))
        events.append((end, -1))
    events.sort(key=lambda e: (e[0], e[1]))
    current = peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def strategy_none(arrivals):
    """No protection: every request that misses goes to the origin."""
    first_fill = arrivals[0] + REGEN_MS
    latencies, origin_calls = [], []
    for arrive in arrivals:
        if arrive >= first_fill:
            latencies.append(CACHE_HIT_MS)
        else:
            origin_calls.append((arrive, arrive + REGEN_MS))
            latencies.append(REGEN_MS)
    return summarize("no protection", latencies, len(origin_calls), arrivals,
                     waiters_window=(arrivals[0], first_fill),
                     stale_served=0, peak_origin=peak_overlap(origin_calls))


def strategy_lock(arrivals):
    """Blocking lock: one caller regenerates, everyone else waits for it."""
    first_fill = arrivals[0] + REGEN_MS
    latencies, origin = [], 1
    for arrive in arrivals:
        if arrive >= first_fill:
            latencies.append(CACHE_HIT_MS)
        else:
            latencies.append(first_fill - arrive)   # blocked until the fill lands
    return summarize("blocking lock", latencies, origin, arrivals,
                     waiters_window=(arrivals[0], first_fill), stale_served=0,
                     peak_origin=1)


def strategy_lease(arrivals):
    """memcached-style lease: one token holder regenerates, others retry.

    Denied clients are told to wait a short time and try again, so their
    wait is rounded up to the next retry tick rather than being an open
    block on a lock. The origin cost is the same as the lock. The
    latency is slightly worse because of the retry granularity.
    """
    first_fill = arrivals[0] + REGEN_MS
    latencies, origin = [], 1
    for arrive in arrivals:
        if arrive >= first_fill:
            latencies.append(CACHE_HIT_MS)
            continue
        waited = 0.0
        while arrive + waited < first_fill:
            waited += LEASE_RETRY_MS
        latencies.append(waited + CACHE_HIT_MS)
    return summarize("lease + retry", latencies, origin, arrivals,
                     waiters_window=(arrivals[0], first_fill), stale_served=0,
                     peak_origin=1)


def strategy_serve_stale(arrivals):
    """Serve the stale value immediately; one caller revalidates behind it."""
    first_fill = arrivals[0] + REGEN_MS
    latencies, origin, stale_served = [], 1, 0
    for arrive in arrivals:
        latencies.append(CACHE_HIT_MS)
        if arrive < first_fill:
            stale_served += 1
    return summarize("serve stale + revalidate", latencies, origin, arrivals,
                     waiters_window=None, stale_served=stale_served,
                     peak_origin=1)


def summarize(name, latencies, origin, arrivals, waiters_window,
              stale_served, peak_origin):
    """Collapse one strategy's per-request results into comparable numbers.

    peak_waiters is the largest number of requests simultaneously occupying
    a request-handling slot while waiting for the regeneration. For the
    strategies that make callers wait, that is every arrival inside the
    regeneration window.
    """
    if waiters_window is None:
        peak_waiters = 0
    else:
        start, end = waiters_window
        peak_waiters = sum(1 for a in arrivals if start <= a < end)
    ordered = sorted(latencies)
    return {
        "name": name,
        "origin": origin,
        "p50": statistics.median(ordered),
        "p99": ordered[min(len(ordered) - 1, int(0.99 * len(ordered)))],
        "peak_waiters": peak_waiters,
        "stale_served": stale_served,
        "peak_origin": peak_origin,
    }


def expiry_peak(rng, jitter):
    """Scenario B: peak regenerations landing in any one-second bucket.

    Every key is written at t=0. Without jitter every TTL is identical, so
    every key expires in the same second. With jitter each TTL is scaled by
    a factor drawn from 1 +/- JITTER_FRACTION.
    """
    buckets = {}
    for _ in range(KEYS):
        ttl = BASE_TTL_S
        if jitter:
            ttl *= 1.0 + rng.uniform(-JITTER_FRACTION, JITTER_FRACTION)
        bucket = int(ttl // BUCKET_S)
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return max(buckets.values()), len(buckets)


def print_scenario_a(results):
    print("\nScenario A: many readers, one key")
    print(f"  {READERS:,} requests for one expired key over {ARRIVAL_WINDOW_MS} ms, "
          f"regeneration costs {REGEN_MS} ms")
    header = (f"  {'strategy':<26}{'origin qrys':>12}{'peak concur':>12}"
              f"{'p99 ms':>9}{'app waiters':>13}{'stale':>8}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in results:
        print(f"  {r['name']:<26}{r['origin']:>12,}{r['peak_origin']:>12,}"
              f"{r['p99']:>9.1f}{r['peak_waiters']:>13,}{r['stale_served']:>8,}")


def main():
    print("=" * 78)
    print("Cache stampede: the two problems that share one name")
    print(f"seed={SEED}  readers={READERS:,}  regen={REGEN_MS}ms  "
          f"pool={POOL_SIZE}  keys={KEYS:,}")
    print("=" * 78)

    arrivals = arrival_times(random.Random(SEED))
    none_r = strategy_none(arrivals)
    lock_r = strategy_lock(arrivals)
    lease_r = strategy_lease(arrivals)
    stale_r = strategy_serve_stale(arrivals)
    print_scenario_a([none_r, lock_r, lease_r, stale_r])

    print("\n  what the lock does, honestly:")
    print(f"    origin queries        {none_r['origin']:,} -> {lock_r['origin']:,}"
          f"  ({none_r['origin'] // lock_r['origin']}x reduction, a real win)")
    print(f"    peak concurrent origin {none_r['peak_origin']:,} -> "
          f"{lock_r['peak_origin']:,}  (the database stops drowning)")
    print(f"    p99 latency           {none_r['p99']:.1f} ms -> {lock_r['p99']:.1f} ms"
          f"  (slightly BETTER, not worse)")
    print("\n  what the lock does NOT do:")
    print(f"    app slots held        {none_r['peak_waiters']:,} -> "
          f"{lock_r['peak_waiters']:,}  (unchanged)")
    print(f"    -> {lock_r['peak_waiters']:,} requests still occupy a pool of "
          f"{POOL_SIZE}, {lock_r['peak_waiters'] / POOL_SIZE:.1f}x over.")
    print("       The database was rescued. The service was not.")
    print(f"\n  serve-stale, for comparison: {stale_r['origin']} origin query, "
          f"{stale_r['p99']:.1f} ms p99, {stale_r['peak_waiters']} slots held,")
    print(f"    at a cost of {stale_r['stale_served']:,} responses being briefly stale.")

    # The lock genuinely works on the axis it claims.
    assert none_r["origin"] > 100, "unprotected case must show a real stampede"
    assert lock_r["origin"] == 1, "the lock must collapse origin load to one query"
    assert none_r["peak_origin"] > 100, "unprotected origin must be hit concurrently"
    assert lock_r["peak_origin"] == 1, "the lock must serialise origin work"
    # The claim it is usually sold with is not the one the numbers support.
    assert lock_r["p99"] < none_r["p99"], \
        "the lock is NOT worse on tail latency; the essay must say so"
    assert lock_r["peak_waiters"] == none_r["peak_waiters"], \
        "the lock does not reduce in-service concurrency at all"
    assert lock_r["peak_waiters"] > POOL_SIZE, \
        "this workload must exhaust the pool, or the point is not demonstrated"
    # Lease matches the lock on origin load and cannot beat it on latency.
    assert lease_r["origin"] == lock_r["origin"], "lease matches lock on origin load"
    assert lease_r["p99"] >= lock_r["p99"], "retry granularity cannot beat blocking"
    # Serve-stale dominates on every axis except freshness.
    assert stale_r["origin"] == 1 and stale_r["peak_waiters"] == 0, \
        "serve-stale must protect the origin without occupying the pool"
    assert stale_r["p99"] * 100 < lock_r["p99"], \
        "serve-stale must beat the lock on tail latency by two orders of magnitude"
    assert stale_r["stale_served"] > 0, "serve-stale must actually serve stale data"

    print("\nScenario B: many keys, one moment")
    print(f"  {KEYS:,} keys written together with a {BASE_TTL_S}s TTL")
    flat_peak, flat_buckets = expiry_peak(random.Random(SEED), jitter=False)
    jit_peak, jit_buckets = expiry_peak(random.Random(SEED), jitter=True)
    print(f"  {'TTL policy':<26}{'peak regens/s':>16}{'seconds spanned':>18}")
    print("  " + "-" * 58)
    print(f"  {'identical TTL':<26}{flat_peak:>16,}{flat_buckets:>18,}")
    print(f"  {f'TTL +/- {JITTER_FRACTION:.0%} jitter':<26}{jit_peak:>16,}{jit_buckets:>18,}")
    print(f"\n  reduction in peak regenerations per second: "
          f"{flat_peak / jit_peak:.0f}x")
    print("  a per-key lock changes NEITHER number: each key needs its one")
    print("  regeneration, and identical TTLs make all of them due at once")

    assert flat_peak == KEYS, "without jitter every key must expire in one bucket"
    assert flat_buckets == 1, "without jitter there is exactly one expiry second"
    assert jit_peak < flat_peak / 50, "jitter must cut the peak by a large factor"

    print("\nReadings:")
    print("  1. the lock does exactly what it claims, and the win is large:")
    print("     concurrent origin queries collapse from hundreds to one")
    print("  2. it is NOT a latency tax. Tail latency is marginally better")
    print("     than no protection, so that common objection is wrong")
    print("  3. what it leaves untouched is your own concurrency: the same")
    print("     requests occupy the same pool slots for the same duration")
    print("  4. serve-stale gets the same origin protection with a p99 two")
    print("     orders of magnitude lower, paid for in staleness")
    print("  5. locks answer 'many readers, one key'; jitter answers 'many")
    print("     keys, one moment'. Applying the first to the second does nothing")
    print("\nAll assertions passed. Numbers reproduce with seed 42.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
