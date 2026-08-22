# Prep · Week 2 · Thu 2026-09-03 · 09:00 · Hands-on tutorial (YouTube video)

> Calendar row: W2 Thu AM. Committed title: "Hands-on: cache eviction policies
> in under an hour (foundations)". Delivery: YouTube video + LinkedIn post.
> Committed outline: define the end state | 4-6 numbered steps | verification
> step. CSV source: github.com/ByteByteGoHq/system-design-101 (verified
> 2026-08-22: 87,418 stars, push 2025-04-04; its cache-eviction entries are
> two external ByteByteGo guides - our demo supplies the runnable material).

## Demo artifact (committed, runnable, verified)

`prep/week-02/code/cache_eviction_demo.py` - 216 lines, stdlib only, seed 42,
runs in <10s. FIFO, LRU (OrderedDict) and O(1) LFU (frequency buckets +
min-freq pointer) behind one interface; three workloads; assertions encode
the video's claims.

Measured hit rates (seed 42, capacity 100, keyspace 2,000, 200k requests -
reproduce before recording):

| workload | FIFO | LRU | LFU |
|---|---|---|---|
| zipfian steady state | 56.1% | 61.7% | 69.7% |
| zipfian + scan floods | 48.2% | 52.9% | 59.8% |
| shifting hot set | 56.1% | 61.6% | **18.4%** |

The story is the third row: LFU wins two workloads then collapses to 18.4%
when popularity shifts, because frequency is memory and memory can be wrong.

## Video script outline (target 20-25 min)

1. **Cold open (0:00-1:30).** Show the table. "Same cache size, same keys,
   three eviction policies - and the winner of two rounds finishes last in
   the third at 18%. Eviction is workload physics, and today you measure it."
2. **Setup (1:30-3:00).** One file, `python3 cache_eviction_demo.py`,
   Python 3.8+, nothing to install.
3. **FIFO, the honest baseline (3:00-6:00).** Insertion order only; the
   `put` on existing key deliberately does NOT reorder - that single line is
   the entire FIFO/LRU difference.
4. **LRU in 20 lines (6:00-10:00).** OrderedDict + `move_to_end` on get;
   run workload 1: recency beats age (61.7 vs 56.1).
5. **LFU without the heap (10:00-15:00).** Frequency buckets + floating
   min_freq = O(1) evictions; LRU order inside a bucket breaks ties. Run
   workload 1 again: 69.7%.
6. **Breaking them (15:00-20:00).** Workload 2, scan floods: one-touch keys
   flush LRU's hot set (52.9) while LFU barely notices (59.8). Workload 3,
   the hot set moves: LFU clings to stale frequencies and craters to 18.4
   while LRU adapts at 61.6. Name the fixes the real world uses: windowed/
   decayed LFU, scan-resistant hybrids (ARC/2Q-family), and Redis shipping
   approximated `allkeys-lru` / `allkeys-lfu` sampling instead of perfect
   bookkeeping.
7. **Wrap + homework (20:00-end).** Decision rule: stable popularity -> LFU
   family; shifting popularity or scans -> LRU family or hybrid; measure
   before believing. Homework: add TTL expiry to any one cache class and
   watch which workload it rescues.

## Recording checklist

- [ ] Re-run demo same-day: "All assertions passed" before recording
- [ ] Terminal 120x32, >=18pt font, dark theme, clean prompt
- [ ] 1080p capture minimum; cuts at workload boundaries
- [ ] On-screen callout when the 18.4% row prints - that is the thumbnail moment
- [ ] End card: repo URL + Friday contrarian-take teaser

## Publish block

- Title options: "The best cache eviction policy loses 51 points overnight" /
  "FIFO vs LRU vs LFU: measured, not vibes"
- Description: repo prep link, Redis eviction-policy docs link, NSDI memcache
  paper link (ties to Wednesday), timestamps per section.
- LinkedIn AM post: the table as hook, steps 2-6 numbered, video link. End
  state per the committed brief: "the table reproduces on your machine, seed
  42, every assertion passes."

## PM slot (17:00 mistakes checklist) - five yes/no checks

1. Do you know your workload's shape (stable, scanning, shifting) from data,
   not intuition? (The whole table above is this question.)
2. Is your hit rate monitored per key-class, not just globally? (A scan can
   halve hot-set hits while the global average barely moves.)
3. Does anything batch-scan through your cache tier on a schedule? (Workload
   2 is your nightly export job.)
4. When popularity shifts (deploy, trend, failover), how long until your
   policy forgets? (LFU without decay: never - the 18.4% row.)
5. Are you using your store's real policy names? (Redis `allkeys-lru` vs
   `volatile-lru` confusion ships outages; verify config against docs.)
Symptom per check drawn from the measured rows; screenshot-able card.

## Numbers audit

- All hit rates - measured outputs of the seeded demo in this repo,
  parameters stated (capacity 100, keyspace 2,000, 200k requests, seed 42),
  re-run day-of ✓
- Redis policy names - Redis documentation, re-verify exact names day-of
  before quoting ✓
- Repo stars/dates - GitHub API 2026-08-22, re-check day-of ✓
