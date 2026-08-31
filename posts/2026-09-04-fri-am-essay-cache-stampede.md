# Week 2 · Fri 2026-09-04 · Long-form: The Lock Works. It Is Just Not the Problem You Have.

> Calendar row: W2 Fri AM, 09:00 (CSV row `32:2`). Format: contrarian take.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/ashishps1/awesome-system-design-resources.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: state the conventional
> wisdom fairly and steelman it in two lines | show the specific context where
> it fails and the evidence | give the replacement heuristic and its own limits.
> Committed CTA: "Save this for your next design review."
>
> **Two theses were discarded before this one, and both were mine.** The
> intended contrarian angle was "locks make tail latency worse." I encoded it
> as an assertion in the model and it failed: the blocking lock measured a
> 195.1 ms p99 against 200.0 ms for no protection at all, so the lock is
> marginally *better*. The fallback angle was "locks cost you in-service
> concurrency." That failed too, because no protection occupies exactly the
> same 771 slots. What survived contact with the measurements is narrower and
> is what the post now argues. The failed assertions are quoted in the body
> rather than deleted.
>
> **Source honesty note.** As with Tuesday, the CSV source repo is a curated
> index. `ashishps1/awesome-system-design-resources` (GitHub API today: 41,063
> stars, last push 2026-02-16, not archived) lists caching fundamentals at
> README lines 55 to 59 and read-through versus write-through at line 92, all
> of them links out to algomaster.io articles. It is credited as an index. The
> evidence in this post comes from a paper, two RFCs, and a model in this
> repository.
>
> Artifact: `prep/week-02/code/stampede_strategies.py`, written for this post,
> committed here, 247 lines, standard library only, seed 42, exit code 0 with
> "All assertions passed". Every figure below is from today's run.
>
> Week-2 scope fences: eviction policy was Thu 09-03 and is referenced only as
> the reason a key can vanish before its TTL. Cache-aside and write-through
> were Wed 09-02 and are assumed, with the necessary definitions restated
> inline because no post in this sequence has reached readers.
>
> Sources verified 2026-09-04:
> - Nishtala et al., "Scaling Memcache at Facebook", NSDI'13. Lease mechanism,
>   the 64-bit token, the default of one token per key per 10 seconds, the
>   "wait a short amount of time" notification, and the measured 17K/s to
>   1.3K/s peak database query rate, all quoted from the open-access PDF text
>   extracted on 2026-09-02.
> - RFC 9111 (HTTP Caching), Section 4, for request collapsing and its stated
>   caveat about introducing additional latency.
> - RFC 5861 (stale-while-revalidate and stale-if-error, May 2010), Section 1,
>   for both extension definitions.
>
> Adversarial review record (2026-09-04):
> - The lock is not strawmanned. It is measured doing exactly what it claims,
>   at a 771x reduction in origin queries, and the post says so before it says
>   anything critical ✓
> - The memcache result is reported as a 13x reduction to 1.3K/s, explicitly
>   not to zero, because the paper's number is not zero ✓
> - Scenario B jitter figures (50,000 to 460 peak regenerations per second,
>   spanning 1 second versus 120) are arithmetic over a stated distribution,
>   not a claim about any production system ✓
> - The replacement heuristic's limits are stated at the same length as its
>   benefits, including the case where serve-stale has nothing to serve ✓
> - No invented incident, engineer, company, or benchmark ✓
> - Zero em dashes.

---

**Topic:** Why the standard lock-based answer to cache stampedes is correct, insufficient, and usually aimed at the wrong one of two different problems

**Subtitle:** Measured: the lock cuts concurrent origin queries from 771 to 1 and leaves your thread pool exactly as exhausted as it was, while the failure most teams actually hit is one a lock cannot touch at all.

Happy Friday. I want to start by admitting that I set out to write a different essay than this one.

The plan was to tell you that lock-based stampede protection is a latency tax dressed up as a safety feature. I built a model, wrote the claim into an assertion so the program would fail if I was wrong, and ran it.

```
AssertionError: the lock must make tail latency worse
```

It is not a latency tax. The blocking lock measured a 195.1 ms p99 against 200.0 ms with no protection at all, which is slightly better. So I tried the next objection, that the lock costs you concurrency inside your own service, and wrote that assertion instead. That failed too, because doing nothing occupies exactly the same slots.

What is left after two of my own theses died is narrower and, I think, more useful than either. The lock is fine. The lock is genuinely good at what it does. The problem is what it is asked to do.

## The conventional wisdom, at its strongest

Let me state it as well as I can, because it deserves that.

**A popular key expires. Every request that was already in flight for it misses at the same instant, and all of them go to the database at once, which is precisely when the database can least afford it. So put a lock around the regeneration: the first caller recomputes, everyone else waits for that one result.**

That is two lines, it is correct, and the mechanism is sound. This is not folk wisdom. RFC 9111 explicitly permits an HTTP cache to do it, describing how a cache can "collapse requests," combining multiple incoming requests into a single forward request on a miss, "thereby reducing load on the origin server and network."

And it works. Here is my own model, 2,000 requests for one key that has just expired, arriving over 500 ms, with a regeneration that costs 200 ms:

```
strategy                   origin qrys peak concur   p99 ms  app waiters   stale
--------------------------------------------------------------------------------
no protection                      771         771    200.0          771       0
blocking lock                        1           1    195.1          771       0
lease + retry                        1           1    201.0          771       0
serve stale + revalidate             1           1      1.0            0     771
```

771 concurrent database queries collapse to 1. That is not a marginal win, that is the difference between a database that is fine and a database that is on fire. Anyone telling you locks are pointless has not looked at that column.

## Where it fails, part one: it rescues the wrong tenant

Look at the second-to-last column, and compare the first two rows.

No protection: 771 requests occupy a request-handling slot. Blocking lock: 771 requests occupy a request-handling slot.

**Unchanged.** The lock moved zero of your own concurrency. Every one of those requests is still sitting in your service holding a thread, a connection, a goroutine, whatever your unit is, for essentially the same 200 ms.

If your pool is 200, as it is in this model, you are 3.9 times oversubscribed either way. And here is the part that turns a latency problem into an outage: those slots are not reserved for this key. Requests for entirely unrelated endpoints now queue behind a stampede on one cache key they have nothing to do with.

So the honest framing of the lock is this. **It rescues your database and leaves your service exactly where it was.** That is a good trade when the database is the fragile thing, which it often is. It is not a solution to the stampede, it is a solution to one participant's experience of the stampede, and if your actual constraint is your own concurrency limit, you have built machinery that did not address it.

Now look at the last row.

Serve the stale value immediately and let one caller revalidate behind it: 1 origin query, a 1.0 ms p99, and **zero** slots held. It beats the lock on every axis the lock was chosen for, by two orders of magnitude on tail latency.

This is not exotic. RFC 5861 standardized it in 2010. The `stale-while-revalidate` extension "allows a cache to immediately return a stale response while it revalidates it in the background, thereby hiding latency (both in the network and on the server) from clients." Its sibling `stale-if-error` does the same when the origin is broken rather than slow.

The cost is in the final column: 771 responses were briefly stale. That is a real cost. It is also a **product decision**, not an engineering defect, and it is one that most teams never get asked because the lock got installed first.

## Where it fails, part two: it is not the stampede you are having

This is the bigger one, and it is the reason I would push back on the standard advice even where the lock is working perfectly.

Two completely different failures share the name "cache stampede."

**Many readers, one key.** A hot key expires and everyone wants it. This is what the lock solves, and everything above applies.

**Many keys, one moment.** You did a bulk import, or a deploy warmed the cache, or a migration wrote a few hundred thousand entries in one pass. Every one of those keys got the same TTL, because you set the TTL to a constant, because everybody sets the TTL to a constant. Ten minutes later they all expire together.

Here is that second scenario, 50,000 keys written at the same moment with a 600 second TTL:

```
TTL policy                   peak regens/s   seconds spanned
----------------------------------------------------------
identical TTL                       50,000                 1
TTL +/- 10% jitter                     460               120
```

Fifty thousand regenerations, all due inside the same second.

**A per-key lock does nothing here.** Not "less than you hoped," nothing. Each of those 50,000 keys legitimately needs exactly one regeneration, which is what the lock would give it. The lock's job is to reduce N regenerations of one key down to one. There is already only one per key. The problem is that 50,000 different ones are due simultaneously, and a mutex on each has no opinion about that.

What fixes it is a single line: multiply the TTL by a small random factor when you set it. Ten percent jitter spread the same work over 120 seconds and cut the peak by 109 times.

This is the part of the advice I would actually call wrong. Not the lock itself, but the fact that "cache stampede protection" has come to mean "locking" in most write-ups, when the failure mode that takes down more systems is correlated expiry, and its fix is boring, free, and mentioned nowhere near as often.

Think about a restaurant. When fifty people order the same dish, the kitchen cooking one large batch is exactly right, and that is your lock. But if the problem is that you booked every table for 7pm, batching does not save you. You needed staggered reservations. Locks batch the orders. Jitter staggers the reservations. They are answers to different questions and only one of them is famous.

## What production actually does

The most useful data point I know comes from Facebook's memcache paper, because they measured the thing rather than reasoning about it.

They did not build a blocking lock. They built **leases**. On a miss, memcached hands the client a 64-bit token bound to that key, and the client presents the token when it writes the value back. Crucially, the server rate-limits token issuance: by default it returns a token only once every 10 seconds per key. Other clients arriving in that window get "a special notification telling the client to wait a short amount of time," and the paper notes that the lease holder typically has the data set "within a few milliseconds."

That is a meaningfully different design from a mutex. Nobody holds a lock. The server rations permits and tells everyone else to come back shortly.

And the measurement, over a week of real traffic on keys they identified as susceptible:

> Without leases, all of the cache misses resulted in a peak database query rate of 17K/s. With leases, the peak database query rate was 1.3K/s.

Thirteen times better. Notice what that number is not. It is **not zero**. Even with a purpose-built mechanism at that scale, the peak did not go away, it got smaller. Anyone promising you elimination is selling something the largest published deployment did not achieve.

RFC 9111 adds its own quiet warning about collapsing, which almost nobody quotes: if the cache cannot use the returned response for some or all of the collapsed requests, it will have to forward them anyway, "potentially introducing additional latency." Collapsing has a failure mode where you paid the wait and still have to do the work.

## The replacement heuristic

Here is what I would do instead, in this order, because the order is the whole point.

**One: jitter every TTL, today.** It is one multiplication. It costs nothing, it needs no new dependency, and it addresses the failure that locking cannot touch. If you do only one thing from this week, do this one.

**Two: decide whether you can serve stale.** If yes, `stale-while-revalidate` dominates the lock on origin protection, tail latency, and pool occupancy. Add `stale-if-error` while you are there, so a broken origin degrades into slightly old data rather than an error page.

**Three: if you cannot serve stale, ration permits rather than blocking.** Issue one regeneration permit per key per interval, and tell the others to retry shortly. That is what memcache does, and it bounds origin load without an object anybody has to hold.

**Four: reach for a blocking lock last**, and give it a timeout strictly shorter than your request budget.

## And the limits of my own advice

I would be doing exactly what I criticized if I stopped there.

**Serve-stale needs something stale to serve.** On a genuinely cold key, one that was never cached or that eviction discarded before its TTL, there is nothing in the cache and no amount of `stale-while-revalidate` will invent it. This is not a corner case: eviction can remove a key long before it expires, so "the TTL has not run out" does not mean "the value is there." For that cold path you are back to permits or a lock.

**Jitter does nothing for a single genuinely hot key.** It solves correlation, not popularity. If your problem is one key and a million readers, jitter is irrelevant and you need the mechanisms in steps two and three.

**Leases need cache-server support you may not have.** If your cache cannot issue permits, you are implementing this in your application against a shared store, which is a distributed lock with extra steps and all of its failure modes.

**And none of it goes to zero.** 17K/s to 1.3K/s is the published result from a team with every possible resource. Plan for a reduced peak, provision for it, and do not design as though the spike is gone.

So the sentence I would take into a design review is not "add a lock." It is: **which stampede am I having, is my regeneration expensive enough to be worth machinery, and can I serve stale?** Three questions. The answers pick the mechanism, and quite often the answer is a one-line change to a TTL rather than a new component on your critical path.

Save this for your next design review.

---

*Today, 17:00: two senior engineers argue the opposite sides of this, and both have the measurements to back it up.*

*Tomorrow, 09:00: the Week 2 recap and three quiz questions, no lookups allowed.*
