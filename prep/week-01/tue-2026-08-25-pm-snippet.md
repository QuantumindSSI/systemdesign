# Prep · Week 1 · Tue 2026-08-25 · 17:00 · (SUPERSEDED) Snippet / config tip

> SUPERSEDED 2026-08-26: the Tue 17:00 slot is now the **code walkthrough**
> (concept-AM / code-PM day split); its prep lives in
> `tue-2026-08-25-repo-walkthrough.md`. This doc is retained only to document
> the vnode snippet below, now an unpublished supporting artifact for the AM
> concept essay's virtual-node section, not its own post.
>
> Original calendar row: W1 Tue PM. Prior title (regenerated 2026-08-25): "A
> working snippet for consistent hashing's virtual nodes (foundations)".
> Prior outline: minimal runnable snippet | annotate the two lines people get
> wrong | state expected output for self-verification.
>
> Realignment (2026-08-25): the original committed brief was "A working
> snippet for PACELC tradeoffs," inherited from the AM slot's wrong PACELC
> pairing. The AM essay now walks the repo's real consistent-hashing code,
> so this follow-up reinforces the AM essay's virtual-node section instead
> of introducing quorums as a new topic (follow-up rule in
> `content_calendar_overview.md`: same underlying example, no new topic).
> The PACELC quorum snippet and its prep are retained at the bottom of this
> file for reference, unpublished in this slot.

## The snippet

Committed, runnable, verified 2026-08-25:
`prep/week-01/code/consistent_hashing_vnodes_snippet.py` (stdlib only,
seeded, finishes in ~1s). Same ring as the AM essay (MD5 hash, sorted list,
`% len` wraparound), reduced to the single knob `num_replicas`. Same scheme
and seed as `lb_algorithms_demo.py` scenario 1, so its numbers match the AM
essay's cited 6.88x / 1.12x exactly.

What it does: five servers, 100,000 keys, no partition, no failure. Two runs
of the same ring, changing only how many positions each server claims:

- **num_replicas=1** - each server hashed once, one arc each
- **num_replicas=100** - each server hashed 100 times, many small arcs

## Measured output (seed 42 - reproduces exactly; put this in the post as the self-verification block)

```
num_replicas=  1:  busiest/quietest = 6.88x
    b0: 11,439  11.4%
    b1: 45,550  45.6%
    b2: 14,562  14.6%
    b3: 21,826  21.8%
    b4:  6,623   6.6%

num_replicas=100:  busiest/quietest = 1.12x
    b0: 19,566  19.6%
    b1: 21,131  21.1%
    b2: 18,894  18.9%
    b3: 19,762  19.8%
    b4: 20,647  20.6%
```

Framing per Amendment 1: these are simulation outputs under the stated
parameters (5 servers, 100,000 keys, seed 42), not field measurements. The
qualitative claim is the point: one arc per server is wildly uneven, many
arcs per server average out. The 6.88x / 1.12x figures are properties of
these parameters; readers changing `num_replicas` or `SERVERS` watch them
move, which is the exercise.

## The two lines people get wrong (annotate these)

1. `h = self._hash(f"{server}#{i}")` - virtual nodes require hashing
   `server + i`, not the bare `server`. Raising a replica count while still
   hashing the plain name puts every replica on the identical position: the
   ring is secretly back to one node per server, stuck at 6.88x.
2. `idx = bisect(self.sorted_keys, h) % len(self.sorted_keys)` - the trailing
   `% len` is the wraparound that closes the ring. Drop it and any key past
   the last position raises IndexError instead of wrapping to the first
   server.

## Post skeleton

Hook (regenerated): "One copy-pasteable block and one knob: watch virtual
nodes turn a 6.88x load imbalance into 1.12x." Then: the table, the two
lines, the invitation to change `num_replicas` (or add a sixth server) and
re-run. Close on the AM essay's thesis - the ring's evenness is a number you
choose, not a property of consistent hashing itself.

CTA (committed): "Repost this so your team sees it."

## Numbers audit

- 6.88x / 1.12x and the per-server share tables - measured, seeded script in
  this repo (`consistent_hashing_vnodes_snippet.py`), parameters inline;
  identical to `lb_algorithms_demo.py` scenario 1 by construction ✓
- `num_replicas=3` source-file default - read directly from
  `consistent-hashing.py` in the clone, re-check day-of ✓

## Retained, unpublished: PACELC quorum snippet

The originally committed PACELC snippet stays in the pack for possible reuse
(PACELC is a recurring pillar topic, e.g. week 62), just not in this slot:
`prep/week-01/code/pacelc_quorum_snippet.py` (110 lines, stdlib, seed 42),
measured output W=1/R=1 -> 7.7ms p50 / 67.0% stale, W=2/R=2 -> 16.0ms p50 /
0 stale. It defines and measures PACELC's ELC half; the Monday CAP essay
already covers PACELC in prose, so the concept is not lost from the week.
