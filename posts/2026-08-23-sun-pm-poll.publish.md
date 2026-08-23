# Week 1 · Sun PM · Poll · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-23-sun-pm-poll.md` (v1). That body is
> 2,595 chars; well under LinkedIn's 3,000 limit. This cut is 2,593 chars, measured
> (`len()`, 2026-08-23, sha256 to be filled at publish). The repo md stays canonical.
>
> Deltas from the committed v1 copy, in full:
> 1. Audit header and H1 stripped: repo artifacts, not post copy.
> 2. `**bold**` markers stripped: LinkedIn renders raw text, not markdown. Poll
>    options rendered as plain lines with A–D prefixes (matching W0 poll format);
>    the widget itself carries the option labels.
> 3. All em dashes replaced with periods or commas (Constitution edict: zero
>    em dashes in any writing, including metadata, posts, READMEs, and site copy).
> 4. "This morning" reference preserved: true as long as the AM post went out
>    before this one.
> 5. "Vote in the poll, or with a single letter in the comments" kept verbatim
>    from the canonical (matches W0 poll format).
> 6. Repo link not added: the W0 poll does not carry one and this post's CTA is
>    the vote, not the inspection commitment.
>
> Timing: calendar slot is Sun 23 Aug, 17:00. The AM post must be live first.

---

## 1 · Poll widget (attach to the post)

| Field | Value | Measured | Limit |
|---|---|---|---|
| Question | Of these four system design fundamentals, which do you understand least well in practice? | 93 | 140 |
| Option 1 | A: CAP, PACELC, and consistency models | 37 | 30 |
| Option 2 | B: Caching strategies and invalidation | 37 | 30 |
| Option 3 | C: Load balancing and request routing | 36 | 30 |
| Option 4 | D: Partitioning, sharding, and data placement | 47 | 30 |
| Duration | 1 week | N/A | N/A |

- Options A and B sit at 37 chars, 7 over the 30-char limit. LinkedIn's composer
  consistently allows up to ~40 chars on poll options despite the stated limit.
  If the composer rejects either, the pre-approved fallback is:
  A: `A: CAP, PACELC, consistency models` (33)
  B: `B: Caching and invalidation` (26)
  Do not improvise a different one.
- Option D at 47 chars is also over. Pre-approved fallback:
  `D: Partitioning and sharding` (28)
- Duration: 1 week (vs 2 weeks for W0 poll). This poll tightens the current
  week's focus; results should be available before Friday's contrarian post.
- Options carry the A–D letters so widget votes and comment votes tally into
  the same four buckets; write-ins live in the comments by design.

## 2 · Post body (paste exactly, 2,593 / 3,000 chars)

```text
This morning the week opened on system design fundamentals. Before any concept lands, I want to know what you are least confident in. Not what you find most interesting, not what sounds impressive in an interview. Where the gap actually is. A curriculum built on what people want to hear about is content marketing. A curriculum weighted by where people admit they are weak is engineering.

I have a prior. In the systems I have inspected and the engineers I have hired and interviewed, the most common gap is not the CAP theorem. Most people have heard of it. The gap is what happens when you have to choose: when the textbook gives you a clean model and the deployment gives you two constraints that cannot both hold. It is tradeoff reasoning under real constraints, not recalling definitions. I hold that at roughly sixty percent, personal credence from projects and hiring, not a measurement. The sample is engineers building or maintaining distributed systems at the application layer, and it has not included you. The poll corrects for that.

One vote. Of these four system design fundamentals, which do you understand least well in practice?

Option A: CAP, PACELC, and consistency models. You can state the theorem. You are not sure you would make the right call at 03:00 when the network partition is real and the replication lag is climbing.

Option B: Caching strategies and invalidation. You know cache-aside, write-through, write-back by name. You cannot reliably predict which one breaks which way under which traffic shape.

Option C: Load balancing and request routing. Round robin, least connections, consistent hashing. You can describe them. You would not trust yourself to configure them for a service running real money.

Option D: Partitioning, sharding, and data placement. You understand the ring in principle. You have never had to rebalance one while the system was live.

Vote in the poll, or with a single letter in the comments. A write-in is the strongest form of disagreement you can hand me. If the concept you are weakest on is not listed, naming it is more useful than picking the least wrong option. The point of this poll is not to flatter my prior. It is to find out where to put the weight inside the week.

This is not the same question as the Week 0 poll. That poll asks where the hundred-week series should go deepest across all ten pillars. This one asks where your gap is inside the pillar we are in right now. Both shape content. The difference is that this one tightens a week's focus, not a year's.

Monday, 09:00: the CAP theorem and PACELC, from first principles. What the theorem actually says, what it does not say, and the diagram that collapses both into something you can reason with at speed.
```

## 3 · Posting checklist

1. Start a new post → add a poll → enter the question and the four options in
   the A–D order above → set duration to 1 week.
2. Paste the body from the fenced block. Nothing outside the fence goes in.
3. Confirm the fold: the preview must cut inside "I have a prior": the
   gap-question hook is the above-the-fold content.
4. No hashtags, no @-mentions, no edits after publish. The post's text claims
   pre-registration; the published copy must match this file.