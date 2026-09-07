# Week 2 · Fri 2026-09-04 · 17:00 · Follow-up: Necessary, or a Component You Will Regret at 3am?

> Calendar row: W2 Fri PM, 17:00 (CSV row `33:2`). Format: debate prompt.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: present position A with
> its strongest supporting scenario argued from first principles | present
> position B with its strongest supporting scenario | ask readers to reply with
> their context, team size, scale, stakes.
> Committed CTA: "Follow along - this series runs all week."
>
> **Deviation from the committed hook, on the record.** The CSV hook reads
> "Two senior engineers, opposite positions on cache stampede protection, both
> with production scars." There are no two engineers and there are no scars.
> Inventing them would be fabrication, and the W1 Friday debate post set the
> precedent for this substitution: the positions below are stated as explicit
> engineering archetypes, each grounded in a measurement or a cited document.
> The hook's framing is honored in structure, not in fiction.
>
> **Publication-gap remediation (2026-09-04).** No post in this sequence has
> reached readers, so both positions restate the mechanism and the numbers they
> rest on rather than referring back to this morning's essay.
>
> Sources verified 2026-09-04 (same set as this morning's essay):
> - Nishtala et al., "Scaling Memcache at Facebook", NSDI'13: leases, the
>   10-second default token interval, and the 17K/s to 1.3K/s result.
> - RFC 9111 Section 4 (request collapsing and its added-latency caveat).
> - RFC 5861 (stale-while-revalidate, stale-if-error).
> - `experiments/week-02/stampede_strategies.py`, today's run: 771 to 1 origin
>   queries, 771 app slots unchanged against a pool of 200, serve-stale at a
>   1.0 ms p99 holding zero slots, and 50,000 to 460 peak regenerations per
>   second under 10% TTL jitter.
>
> Adversarial review record (2026-09-04):
> - Both positions are argued at their strongest. Position B is not a
>   scarecrow: its central claim, that the lock leaves in-service concurrency
>   untouched, is the measured result that killed one of my own theses ✓
> - Neither position is declared the winner. The closing section names the
>   conditions under which each is right ✓
> - Word count: 920 words in the reader-facing body below the editorial `---`
>   marker, measured 2026-09-04, not estimated. Above the 500-700 band used for
>   the diagram and checklist follow-ups, because the debate format has to
>   carry two full arguments plus the publication-gap restatement of their
>   supporting numbers. Deliberate, not drift ✓
> - Zero em dashes.

---

**Topic:** A structured argument over whether dedicated cache stampede protection earns its place on the critical path

**Subtitle:** One side has a 13x measured reduction in peak database load. The other has the fact that the mechanism rescues your database and leaves your thread pool exactly as exhausted as it was.

Good evening. This morning I argued that lock-based stampede protection works, is aimed at the wrong problem more often than not, and is usually beaten by a one-line TTL change.

That is my read. It is not the only defensible one. So here are the two strongest versions of the disagreement, and neither is a straw man.

The shared setup: a read-heavy service, a cache in front of a database, and a regeneration that costs about 200 ms. When a popular key expires, every concurrent request for it misses at once.

## Position A: build the protection, the arithmetic is not close

The platform team's case starts with what peak load costs.

You do not provision a database for average load, you provision it for peak. So a mechanism that cuts peak matters far more than one that cuts average. In a model of 2,000 requests arriving for one expired key, an unprotected cache sent **771 concurrent queries** at the origin. With a single-regeneration mechanism in front, that becomes **1**. Not 1 on average. One.

The production version of this is measured rather than modeled. Facebook's memcache deployment issues a lease on a miss, a 64-bit token bound to the key, rate-limited by default to one token per key per 10 seconds, with other callers told to wait briefly and retry. Over a week of real traffic on keys they knew were susceptible, peak database query rate went from 17,000 per second without leases to 1,300 with them.

Then the argument that actually settles it for this side: **a stampede is a positive feedback loop.** The database slows down under the concurrent load. A slower database means regeneration takes longer. A longer regeneration means a wider window in which new arrivals also miss. More arrivals mean more load. Nothing in that loop is self-correcting, which is why stampedes present as a cliff rather than a slope. Single-flight regeneration is the thing that breaks the loop, and jitter cannot break it, because jitter is applied before the fact and this is happening now.

The risk this side accepts: a new mechanism on the miss path, which is a path that runs when things are already going badly.

## Position B: this is a component you will be paged for

The service team's case starts with what the mechanism does not do.

Measure the resource that actually runs out. In the same model, an unprotected cache had **771 requests occupying a request-handling slot**. With a blocking lock in front: still **771**. Identical. The lock rescued the database and moved not one unit of your own concurrency, so against a pool of 200 you are 3.9 times oversubscribed either way, and requests for unrelated endpoints now queue behind one key they have nothing to do with.

Meanwhile, serving the stale value while one caller revalidates behind it, which RFC 5861 standardized in 2010, got the same single origin query with a **1.0 ms p99 and zero slots held**. Same protection, two orders of magnitude better tail, no lock to operate. The only cost is briefly stale data, which is a question for the product owner, not the platform team.

And the failure this side is most afraid of: a distributed lock is a dependency that can be down. When it is, every cache miss in the system is blocked on it, which converts a cache performance problem into a total outage. A lock held by a process that just crashed stalls every waiter until a timeout somebody set once and never revisited. RFC 9111 even warns that collapsing can end in the worst of both, forwarding the requests anyway after everyone has already waited, "potentially introducing additional latency."

Their closing point is about diagnosis. The more common production stampede is not many readers on one key, it is many keys expiring in the same second because a bulk write gave them all the same TTL. In that shape, 50,000 keys came due in one second, and 10% TTL jitter spread them over 120 seconds and cut the peak to 460. A per-key lock changes neither number. Build the complicated thing and the actual outage still happens.

## Where each one is right

Position A is right when regeneration is genuinely expensive, staleness is genuinely unacceptable, and you have a cache tier that can ration permits without you operating a lock. That combination is real, and at sufficient scale the peak-provisioning arithmetic wins on its own.

Position B is right when you can serve stale, when your constraint is your own concurrency rather than your database's, or when nobody on the team wants to own a lock service at 3am. Which is to say, most of the time.

Your turn. Reply with three things: your regeneration cost, whether your product can tolerate data a few seconds old, and which resource hits its limit first, your database or your request pool. Then say which mistake you would rather make, over-engineering a stampede that never comes, or discovering during one that your fix addressed a different problem.

Follow along, this series runs all week.

---

*Tomorrow, 09:00: the Week 2 recap, five topics in one line each, and three quiz questions with no lookups allowed.*
