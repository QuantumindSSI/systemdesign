# Prep · Week 1 · Tue 2026-08-25 · 17:00 · Snippet / config tip

> Calendar row: W1 Tue PM. Committed title: "A working snippet for PACELC
> tradeoffs (foundations)". Committed outline: minimal runnable snippet |
> annotate the two lines people get wrong | state expected output for
> self-verification.
>
> Context available: `posts/2026-08-24-mon-cap-theorem-longform.md` already
> defines PACELC ("if partitioned, choose availability or consistency per
> CAP; otherwise, choose latency or consistency") with a worked example
> (Singapore replica-lag case). This post's job is to make that definition
> concrete with running code and measured numbers, not to re-explain PACELC
> from scratch. Reference it rather than duplicate the definition.

## The snippet

Committed, runnable, verified 2026-08-22:
`prep/week-01/code/pacelc_quorum_snippet.py` (110 lines, stdlib only,
seeded, finishes in ~2s).

What it does: three replicas, 40ms async replication lag, no partition
anywhere. Two configs of the same system:

- **A: W=1, R=1** - write acks after 1 replica, read queries 1 replica
- **B: W=2, R=2** - quorum overlap (R + W > N)

## Measured output (seed 42 - reproduces exactly; put this in the post as the self-verification block)

```
config                  p50 read  p99 read   stale reads
--------------------------------------------------------
A: W=1, R=1 (fast)         7.7ms    24.0ms   26,810 (67.0%)
B: W=2, R=2 (quorum)      16.0ms    28.4ms        0 ( 0.0%)
```

Framing per Amendment 1: these are simulation outputs under the stated
parameters (lag 40ms, 1 write per 4 reads, RTTs 2-30ms), not field
measurements. The qualitative shape is the claim: quorum reads roughly
double median latency and eliminate staleness; single-replica reads are
fast and serve stale data while the lag window is open. The 67% figure is
a property of these parameters; readers changing `REPLICATION_LAG_MS`
will watch it move, which is the point of the exercise.

## The two lines people get wrong (already printed by the script)

1. `acked = rng.sample(range(N), write_quorum)` - a write ack means those
   specific replicas have the version now. Everyone else converges ~lag ms
   later. Treating "acked" as "replicated everywhere" is the classic bug.
2. `latencies.append(rtts[read_quorum - 1])` - a quorum read completes at
   the R-th fastest replica, not the fastest. Quorums buy consistency with
   tail latency.

## Post skeleton

Hook (committed): "One copy-pasteable block that makes PACELC tradeoffs
concrete." Then: the table, the two lines, the invitation to flip one
constant (`REPLICATION_LAG_MS`, or try W=2,R=1 - R+W=N, overlap gone) and
re-run. Close with the PACELC sentence: no partition was harmed in this
demo, and you still had to choose latency or consistency.

CTA (committed): "Repost this so your team sees it."

## Numbers audit

- 7.7 / 16.0 / 24.0 / 28.4 ms, 67.0% / 0.0% - measured, seeded script in
  this repo, parameters stated inline ✓
- "R + W > N" overlap rule - standard quorum condition, demonstrated by the
  script's assertion (`b_stale == 0`) rather than asserted from authority ✓
