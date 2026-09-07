# Week 2 · Fri 2026-09-04 · Long-form: The Lock Works. It Just Solves One Kind of Stampede.

> Calendar row: W2 Fri AM, 09:00 (CSV row `32:2`). Format: contrarian take.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
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
> marginally *better*. The fallback angle was "locks add in-service
> concurrency." That failed too, because no protection occupies exactly the
> same 771 slots. What survived contact with the measurements is narrower and
> is what the post now argues. The failed assertions are quoted in the body
> rather than deleted.
>
> **Source honesty note (revised 2026-09-06).** As with Tuesday, the CSV
> source row points at a curated link index rather than a codebase, and under
> the canonical source rule it is not named. Nothing from it is quoted. The
> evidence in this post comes from a paper, two RFCs, and a model in this
> repository.
>
> Artifact: `experiments/week-02/stampede_strategies.py`, written for this post,
> committed here, 287 lines, standard library only, seed 42, exit code 0 with
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
> - Reader-facing body: 3,479 words, measured 2026-09-04. Within the committed
>   2,500 to 3,500-word long-form range ✓
> - No invented incident, engineer, company, or benchmark ✓
> - Zero em dashes.

---

**Topic:** Cache stampedes: why a lock solves only half the problem

**Subtitle:** In a deterministic model, the lock cuts concurrent origin queries from 771 to 1, yet leaves your request pool exactly as exhausted as it was and cannot prevent thousands of keys from expiring together.

Happy Friday. I want to start by admitting that I set out to write a different essay than this one.

The plan was to tell you that lock-based stampede protection is a latency tax dressed up as a safety feature. I built a model, wrote the claim into an assertion so the program would fail if I was wrong, and ran it.

```
AssertionError: the lock must make tail latency worse
```

It is not a latency tax. The blocking lock measured a 195.1 ms p99 against 200.0 ms with no protection at all, which is slightly better. So I tried the next objection, that the lock creates extra concurrency pressure inside your own service, and wrote that assertion instead. That failed too, because doing nothing occupies exactly the same slots.

What is left after two of my own theses died is narrower and, I think, more useful than either. The lock is fine. The lock is genuinely good at what it does. The problem is what it is asked to do.

That distinction matters to me because "add a lock" is the sort of sentence that can end a design conversation too early. It sounds decisive. There is a named failure, there is a familiar component, and the boxes on the whiteboard now connect neatly. I have learned to become suspicious at exactly that moment. A tidy diagram can hide an unanswered question: **which resource are we trying to save?**

So I am not going to ask you to distrust locks. I am going to ask you to slow the conversation down by one minute. We will separate two failures that share a name, follow the waiting requests instead of only counting database calls, and then choose the least complicated mechanism that protects the resource we actually care about.

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

Picture a crowded coffee shop when the card reader briefly stops working. Without coordination, every barista walks to the back office to report the same fault. The queue at the counter is now unattended, the office is full of people repeating one message, and the reader is no closer to working. A lock appoints one barista to report the fault while the others stay out of the office. That is exactly the right move if the back office is the resource you are protecting.

In cache terms, the first miss becomes the regenerator. It acquires the per-key lock, reads or computes the missing value, stores it, and releases the lock. Requests that arrive during those 200 ms do not issue their own origin query. They wait, then read the value produced by the winner. One expensive operation replaces hundreds of duplicates.

I am spelling that out because it is easy to criticize a vague caricature of locking. The real mechanism has a clear invariant: at most one regeneration for this key may be active. In the measured scenario, it keeps that promise perfectly.

## Where it fails, part one: it rescues the wrong tenant

Look at the second-to-last column, and compare the first two rows.

No protection: 771 requests occupy a request-handling slot. Blocking lock: 771 requests occupy a request-handling slot.

**Unchanged.** The lock moved zero of your own concurrency. Every one of those requests is still sitting in your service holding a thread, a connection, a goroutine, whatever your unit is, for essentially the same 200 ms.

This is the column I used to skip. I would look at origin queries, see 771 become 1, and mentally mark the incident resolved. But requests do not disappear when they stop querying the database. They remain admitted to the service. Each still has a socket, request state, a deadline, memory, and some place in a scheduler or execution pool. An asynchronous server may avoid dedicating an operating-system thread to every waiter, but it does not make those waiters free. They still consume bounded capacity and still count against whatever concurrency limit protects the process.

If your pool is 200, as it is in this model, you are 3.9 times oversubscribed either way. And here is the part that turns a latency problem into an outage: those slots are not reserved for this key. Requests for entirely unrelated endpoints now queue behind a stampede on one cache key they have nothing to do with.

Think of a doctor's waiting room with 200 chairs. The lock lets one of 771 patients knock on the consultation-room door instead of all of them knocking at once, which certainly helps the doctor. It does not create another chair. Demand for the waiting room is still far beyond capacity, and someone who arrived for an unrelated prescription renewal cannot get through the entrance. Protecting the consultation room and protecting the waiting room are different jobs.

That is why the phrase "the database is safe" is not yet an incident outcome. I also want to know how many requests are admitted, how long they remain resident, what happens when the request deadline arrives before the lock does, and whether unrelated traffic has a separate concurrency budget. Those questions turn a component choice into a system design.

So the honest framing of the lock is this. **It rescues your database and leaves your service exactly where it was.** That is a good trade when the database is the fragile thing, which it often is. It is not a solution to the stampede, it is a solution to one participant's experience of the stampede, and if your actual constraint is your own concurrency limit, you have built machinery that did not address it.

Now look at the last row.

Serve the stale value immediately and let one caller revalidate behind it: 1 origin query, a 1.0 ms p99, and **zero** slots held. It beats the lock on every axis the lock was chosen for, by two orders of magnitude on tail latency.

This is not exotic. RFC 5861 standardized it in 2010. The `stale-while-revalidate` extension "allows a cache to immediately return a stale response while it revalidates it in the background, thereby hiding latency (both in the network and on the server) from clients." Its sibling `stale-if-error` permits a stale response when the origin returns an error.

The cost is in the final column: 771 responses were briefly stale. That is a real cost. It is also a **product decision**, not an engineering defect, and it is one that most teams never get asked because the lock got installed first.

"Stale" can sound irresponsible until we attach it to a real screen. A profile photo that is ten seconds old is usually harmless. A product description that still shows the previous sentence while a background refresh runs may be harmless too. A bank balance, a revoked permission, an available seat on the last flight, or the result of a just-completed payment can be very different. The mechanism cannot make that judgment for us.

When I ask whether stale data is acceptable, I do not mean "does the company like fresh data?" Every company likes fresh data. I mean: **what concrete harm can happen if this field is old for this many seconds?** Once the question is that specific, teams can often divide one endpoint into parts. The expensive recommendation panel may be served stale while the account balance beside it is fetched fresh. We do not have to give the whole page one freshness policy simply because it arrives in one HTTP response today.

## Where it fails, part two: it is not the stampede you are having

This is the bigger one, and it is the reason I would push back on the standard advice even where the lock is working perfectly.

Two completely different failures share the name "cache stampede."

**Many readers, one key.** A hot key expires and everyone wants it. This is what the lock solves, and everything above applies.

**Many keys, one moment.** You did a bulk import, or a deploy warmed the cache, or a migration wrote a few hundred thousand entries in one pass. Every one of those keys got the same TTL, because you set the TTL to a constant, because everybody sets the TTL to a constant. Ten minutes later they all expire together.

This second shape is less dramatic in a single request trace. No key looks especially hot. Each trace shows one ordinary miss and one ordinary regeneration. The failure only becomes visible when you step back and put all the traces on the same timeline. Then the vertical line at exactly ten minutes is impossible to miss.

It is the server equivalent of setting every alarm clock in a hotel to ring at 6am. Inspect any one room and the alarm is behaving correctly. Add a lock to each door and you have changed nothing, because no two guests are fighting over the same room. The problem is the shared schedule.

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

This is the part of the advice I would actually call wrong. Not the lock itself, but the habit of using "cache stampede protection" as shorthand for "locking." Correlated expiry is a different failure, its fix is boring and cheap, and it deserves to be part of the first conversation rather than an appendix.

Think about a restaurant. When fifty people order the same dish, the kitchen cooking one large batch is exactly right, and that is your lock. But if the problem is that you booked every table for 7pm, batching does not save you. You needed staggered reservations. Locks batch the orders. Jitter staggers the reservations. They are answers to different questions and only one of them is famous.

## What production actually does

The most useful data point I know comes from Facebook's memcache paper, because they measured the thing rather than reasoning about it.

They did not build a blocking lock. They built **leases**. On a miss, memcached hands the client a 64-bit token bound to that key, and the client presents the token when it writes the value back. Crucially, the server rate-limits token issuance: by default it returns a token only once every 10 seconds per key. Other clients arriving in that window get "a special notification telling the client to wait a short amount of time," and the paper notes that the lease holder typically has the data set "within a few milliseconds."

That is a meaningfully different design from a mutex. Nobody holds a lock. The server rations permits and tells everyone else to come back shortly.

I find a numbered bakery ticket a better mental model than a locked door. One customer receives the ticket that authorizes an order. Everyone else is told that an order is already in progress and to check the display again shortly. If the ticket holder vanishes, there is no forgotten key physically trapped in a door. The permission expires and another client can eventually receive one. The hard distributed-systems questions do not vanish, but the protocol makes ownership and time explicit.

And the measurement, over a week of real traffic on keys they identified as susceptible:

> Without leases, all of the cache misses resulted in a peak database query rate of 17K/s. With leases, the peak database query rate was 1.3K/s.

Thirteen times better. Notice what that number is not. It is **not zero**. Even with a purpose-built mechanism at Facebook's scale, the peak did not go away, it got smaller. Anyone promising elimination is claiming more than this production measurement demonstrates.

RFC 9111 adds its own quiet warning about collapsing, which almost nobody quotes: if the cache cannot use the returned response for some or all of the collapsed requests, it will have to forward them anyway, "potentially introducing additional latency." Collapsing has a failure mode where you paid the wait and still have to do the work.

## The replacement heuristic

Here is what I would do instead, in this order, because the order is the whole point.

**One: jitter every cache TTL that can tolerate a bounded spread.** It is one multiplication, it needs no new service, and it addresses the failure that locking cannot touch. If you do only one thing from this week, do this one.

If the nominal TTL is 600 seconds and the allowed jitter is 10%, choose a value between 540 and 660 seconds when writing each entry. Do not add the randomness when reading, because by then the expiry schedule is already set. Do not reuse one random value for the whole batch, because that merely moves the synchronized spike to a different second. Each key needs its own draw.

**Two: decide whether you can serve stale.** If yes, `stale-while-revalidate` dominates the lock on origin protection, tail latency, and pool occupancy. Add `stale-if-error` while you are there, so a broken origin degrades into slightly old data rather than an error page.

Write the freshness budget down in product language. "Recommendations may be 60 seconds old" can be reviewed. "Use stale caching where appropriate" cannot. Also decide what the user sees after that budget expires. Serving yesterday's weather during a short outage may be better than an empty screen, while serving an old authorization decision may be unacceptable at any age.

**Three: if you cannot serve stale, ration permits rather than blocking.** Issue one regeneration permit per key per interval, and tell the others to retry shortly. That is what memcache does, and it bounds origin load without an object anybody has to hold.

The retry needs a limit and a deadline. A client should never wait indefinitely for a value whose regenerator may have crashed. Keep the retry delay bounded, stop before the request's own deadline, and expose a metric for denied permits so the mechanism cannot become invisible during the exact event it was built to control.

**Four: reach for a blocking lock last**, and give it a timeout strictly shorter than your request budget.

If the request has 500 ms left, a 500 ms lock timeout is already too long because the request still needs time to read the newly cached value and send a response. The timeout must leave room for the work after the wait. I would also split concurrency by endpoint or workload where practical, so one hot catalog key cannot consume the capacity reserved for login or checkout. The lock protects the origin; isolation protects the neighbors.

Here is how that order changes three ordinary decisions. For a news homepage, I would jitter the TTL and serve the previous page while one refresh runs. For a payment status immediately after checkout, I would jitter any cache entry but avoid serving stale, then use a bounded permit or single-flight mechanism because the user needs the current state. For a key that has never existed in the cache, I would plan an explicit cold-miss path, because there is no stale copy to rescue me.

## And the limits of my own advice

I would be doing exactly what I criticized if I stopped there.

**Serve-stale needs something stale to serve.** On a genuinely cold key, one that was never cached or that eviction discarded before its TTL, there is nothing in the cache and no amount of `stale-while-revalidate` will invent it. This is not a corner case: eviction can remove a key long before it expires, so "the TTL has not run out" does not mean "the value is there." For that cold path you are back to permits or a lock.

**Jitter does nothing for a single genuinely hot key.** It solves correlation, not popularity. If your problem is one key and a million readers, jitter is irrelevant and you need the mechanisms in steps two and three.

**Jitter must not move a policy deadline.** A cache freshness window can often slide by 10%. A session expiry, authorization deadline, or retention boundary may not. If the TTL carries a correctness or security promise rather than a caching preference, keep that deadline exact and stagger the refresh work another way.

**Leases need cache-server support you may not have.** If your cache cannot issue permits, you are implementing this in your application against a shared store, which is a distributed lock with extra steps and all of its failure modes.

**And none of it goes to zero.** 17K/s to 1.3K/s is the published result from a team with every possible resource. Plan for a reduced peak, provision for it, and do not design as though the spike is gone.

There is one more limit I keep in view: this model is deliberately small. It isolates the mechanism so we can see what each strategy changes. It does not model network jitter, partial failures, lock-server failover, retries from upstream clients, or a database whose latency rises under load. Those effects usually make overload harder, not easier, but I will not pretend a deterministic script is a production benchmark. Its job is to test the argument's arithmetic, and the production paper gives us a separate measured result from a real deployment.

So the sentence I would take into a design review is not "add a lock." It is: **which stampede am I having, is my regeneration expensive enough to be worth machinery, and can I serve stale?** Three questions. The answers pick the mechanism, and quite often the answer is a one-line change to a TTL rather than a new component on your critical path.

That is also where writing this changed my own view. I began with a verdict about a component. The measurements forced me back to the shape of the workload and the resource under pressure. I trust that version of the argument more because it survived being wrong twice.

The next time a dashboard lights up after a popular key expires, follow the requests all the way through the system. Count the origin calls, but also count the waiters. Look across keys, not only within one key. Ask what may safely be stale. A lock may still be the right answer. If it is, you will know exactly which failure it is containing and which ones remain yours to solve.

Save this for your next design review.

---

*Today, 17:00: the strongest engineering case from each side, with measurements behind both.*

*Tomorrow, 09:00: the Week 2 recap and three quiz questions, no lookups allowed.*
