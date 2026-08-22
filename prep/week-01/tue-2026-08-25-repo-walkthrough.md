# Prep · Week 1 · Tue 2026-08-25 · 09:00 · Repo walkthrough

> Calendar row: W1 Tue AM. Committed title: "Inside awesome-system-design-resources:
> PACELC tradeoffs in real code (foundations)". Source repo:
> github.com/ashishps1/awesome-system-design-resources.
> Repo verified via GitHub API 2026-08-22: 40,837 stars, last push 2026-02-16,
> not archived. Local clone at `repos/awesome-system-design-resources`
> (gitignored). Re-verify the repo is unchanged on post day.

## EDITORIAL DECISION REQUIRED BEFORE WRITING

The committed brief cannot run as written. Verified 2026-08-22 by grep over the
full clone: **the string "PACELC" appears nowhere in this repository.** The
generator paired the week's concept with the pillar's repo bank mechanically
and this pairing is wrong. Two honest ways out:

**Option A (recommended): keep the repo, walk its real code.**
The repo is not just a link list - it ships working implementations:

- `implementations/python/consistent_hashing/consistent-hashing.py` (~75 lines)
- `implementations/python/load_balancing_algorithms/` - five algorithms:
  `round_robin.py.py` (typo in the filename is real, verify it still exists on
  post day - it is an honest, likable detail), `weighted_round_robin.py`,
  `least_connections.py`, `least_response_time.py`, `ip_hash.py`
- `implementations/python/rate_limiting/` - five rate limiter variants
- Java mirrors of all of the above

Walk `consistent-hashing.py`. It sets up Wednesday's case study (Dynamo uses
exactly this scheme) and Thursday's video (which measures these algorithms).
The week becomes one arc: read the code Tue, see it at Amazon scale Wed, run
it yourself Thu.

**Option B: keep PACELC, swap the repo.**
PACELC genuinely lives in `karanpratapsingh/system-design` (verified in clone:
README.md line 39 TOC entry, chapter at lines 1586-1596 with the Daniel Abadi
attribution and a diagram). But that chapter is prose, not code, and the
committed format promises "real code". Weaker fit; use only if Tuesday must
stay on PACELC. Note Tuesday PM's snippet keeps PACELC alive either way.

If A is chosen, the calendar CSV row should be regenerated/edited afterward to
match what ran (same discipline as the launch-week slip).

## Walkthrough beats (Option A), file: `implementations/python/consistent_hashing/consistent-hashing.py`

1. **The problem in two lines** (file docstring context): `hash(key) mod N`
   reshuffles almost everything when N changes. The fix is a ring.
2. **`_hash`** - MD5 of the key, taken as a 128-bit integer. Not for security,
   for spread. (Dynamo does the same: MD5 to a 128-bit space - say it Wed.)
3. **`add_server`** - the design decision worth stealing: each server is
   hashed `num_replicas` times (`f"{server}-{i}"`), so one physical node owns
   many small arcs instead of one big one. Virtual nodes are what make the
   ring's distribution even.
4. **`bisect.insort` / `bisect.bisect`** - the ring is just a sorted list of
   hashes; lookup is O(log n) and the `% len` at the end is the wrap-around
   that makes the circle a circle.
5. **The wart worth naming** - `remove_server` calls `sorted_keys.remove()`
   per replica: O(n) each. Fine at demo scale, a real ring keeps a tree or
   re-sorts in batch. Also `num_replicas=3` is pedagogically low.
6. **The measured payoff** (numbers from our seeded demo,
   `prep/week-01/code/lb_algorithms_demo.py`, seed 42): with 1 vnode per node
   the busiest/quietest node ratio is 6.88x; with 100 vnodes it is 1.12x.
   Losing 1 of 5 backends remaps 79.9% of keys under `mod N` and 19.1% on the
   ring (theory: 80% vs 20%).
7. **What is missing for production** - no replication, no weights, no
   bounded loads, no health checks. That gap is exactly Wednesday's post.

## Numbers audit for the post

- 40,837 stars / push date - GitHub API, 2026-08-22, re-check day-of ✓
- 6.88x / 1.12x / 79.9% / 19.1% - measured, seeded demo in this repo ✓
- "~75 lines" - count in the clone, re-check day-of ✓
- Dynamo facts belong to Wednesday; if referenced Tue, cite
  allthingsdistributed.com/2007/10/amazons_dynamo.html (verified 2026-08-22) ✓

## PM slot pointer

17:00 snippet post prep: `tue-2026-08-25-pm-snippet.md` (PACELC quorum
simulation - keeps the committed PACELC concept concrete regardless of the
AM decision).
