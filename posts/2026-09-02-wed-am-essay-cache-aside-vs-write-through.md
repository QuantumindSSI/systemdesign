# Week 2 · Wed 2026-09-02 · Long-form: Facebook Chose to Delete, Not Update, and Built a Pipeline to Prove It

> Calendar row: W2 Wed AM, 09:00 (CSV row `28:2`). Format: case study.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: set the scene, company
> scale, constraint, and why this concept was on the critical path | walk the
> decision, the implementation, and the number that moved | close with the
> transferable rule. Committed CTA: "Comment your take - I read every reply."
>
> **Prep debt cleared.** `prep/week-02/wed-2026-09-02-case-study.md:55-60`
> instructed: "pull the PDF from the USENIX page for the mechanism details you
> want to quote ... this prep verified the page, abstract and summary, not the
> full PDF text. Do not cite body-level numbers until read directly." The PDF
> was downloaded and its text extracted today, and every body-level figure
> below (4%, 18x, the two-second hold-off, hours instead of days) is quoted
> from that extraction. The prep's own caveat is therefore discharged, not
> inherited.
>
> Week-2 scope fences:
> - Leases, the 10-second token interval, and the 17K/s to 1.3K/s thundering
>   herd result are in this same paper and are deliberately NOT used here.
>   They are stampede protection, which is Fri 09-04. This post names the
>   remaining race and hands it to Friday.
> - Eviction policy is Thu 09-03. This post treats "memcache may evict" as a
>   property it is allowed to have, and does not discuss which item goes.
> - The runnable model is tonight, `posts/2026-09-02-wed-pm-followup-write-strategies-code.md`.
>
> Sources verified 2026-09-02:
> - Nishtala, Fugal, Grimm, Kwiatkowski, Lee, Li, McElroy, Paleczny, Peek,
>   Saab, Stafford, Tung, Venkataramani, "Scaling Memcache at Facebook",
>   NSDI'13, pp. 385-398. Open-access PDF downloaded from usenix.org today and
>   converted to text locally. Quotations below are from that text.
>   last push 2026-03-20, not archived. README fetched today. Cache-aside
>   section at line 1203, its disadvantages at 1233 to 1236; write-through at
>   1239, its summary at 1267, its disadvantages at 1271 to 1272. The prep
>   recorded the same line numbers on 2026-08-22 and they have not drifted.
>
> Adversarial review record (2026-09-02):
> - Verbatim paper quotations, each checked against the extracted text:
>   "demand-filled look-aside cache"; "We choose to delete cached data instead
>   of updating it because deletes are idempotent"; "Memcache is not the
>   authoritative source of the data and is therefore allowed to evict cached
>   data"; "It was the best choice given limited engineering resources and
>   time"; "only 4% of all deletes issued result in the actual invalidation of
>   cached data"; "The batching results in an 18x improvement"; "back to full
>   capacity in a few hours instead of a few days"; "that item will be
>   indefinitely inconsistent in the cold cluster"; "all deletes to the cold
>   cluster are issued with a two second hold-off". Abstract figures: "billions
>   of requests per second", "trillions of items", "over a billion users" ✓
> - Verbatim primer quotations: "Each cache miss results in three trips";
>   "Data can become stale if it is updated in the database"; "Write-through is
>   a slow overall operation due to the write operation"; "the new node will not
>   cache entries until the entry is updated in the database"; "Most data
>   written might never be read" ✓
> - The paper is from 2013 and describes the system as it was then. The post
>   says so and makes no claim about Facebook's current architecture ✓
> - No invented incident, engineer, quote, or number. The one interpretive
>   claim (that 96% wasted deletes is a deliberate trade) is marked as my
>   reading of their published figure, not as their statement ✓
> - Zero em dashes.

---

**Topic:** How Facebook's memcache deployment answered the cache-aside versus write-through question, and what the answer cost them in machinery

**Subtitle:** They picked the pattern with the worse consistency story and then spent years building the infrastructure to make it correct, which tells you something useful about what these two patterns are actually choosing between.

Good morning. Let me start with a small domestic argument, because it is the whole paper in miniature.

You keep a whiteboard in the kitchen with the milk situation on it. Somebody drinks the last of the milk. There are two things they can do. They can rub out "milk: full" and write "milk: empty," or they can just cross the line out entirely so the next person has to go and look in the fridge.

Writing the new value is more helpful. It saves a trip. It is also the option that goes wrong when two people do it at once and their handwriting lands in the wrong order, because now the board confidently states something false and nobody has any reason to doubt it.

Crossing it out is less helpful and cannot lie. Two people crossing out the same line, in either order, produces the same board.

That is the decision at the center of today's case study, made at a scale where the whiteboard has trillions of lines on it.

## The scene

The paper is "Scaling Memcache at Facebook," presented at NSDI in 2013 by Rajesh Nishtala and twelve colleagues. It is one of the most useful systems papers ever written, partly because it is unusually honest about the unglamorous parts.

The scale, from its abstract: a distributed key-value store built out of memcached that "handles billions of requests per second and holds trillions of items to deliver a rich experience for over a billion users around the world."

One important caveat before we go further. This describes the system as it existed in 2013. I am not telling you what Facebook runs today, and neither is the paper. What survives is the reasoning, which is why we are reading it thirteen years later.

The constraint that put caching on the critical path is stated plainly: they needed to lighten the read load on their MySQL databases. A social graph makes this brutal in a specific way the paper calls out, that a single web page routinely fetches thousands of key-value pairs, so every page view fans out into an enormous number of small lookups.

And the reason they reached for memcached rather than something more principled is refreshingly unpretentious:

> While there are several ways to address excessive read traffic on MySQL databases, we chose to use memcache. It was the best choice given limited engineering resources and time.

Then the sentence that actually matters architecturally:

> Additionally, separating our caching layer from our persistence layer allows us to adjust each layer independently as our workload changes.

Hold onto that one. It is the real argument for cache-aside, and it is not about performance at all.

## The decision

Here is how the primer, today's calendar source, frames the two options.

**Cache-aside**, at line 1203 of its README, puts the application in charge: look for the entry in the cache, miss, load from the database, add to the cache, return. It notes this is also called lazy loading, and that only requested data gets cached, which keeps the cache from filling up with things nobody wants. It lists the costs honestly, including that "Each cache miss results in three trips, which can cause a noticeable delay" and that "Data can become stale if it is updated in the database."

**Write-through**, at line 1239, inverts it: the application writes to the cache, and the cache synchronously writes to the database. The primer's summary is that write-through "is a slow overall operation due to the write operation, but subsequent reads of just written data are fast," and then the line that matters most, "Data in the cache is not stale."

So one pattern has a staleness problem and the other does not. You would think that settles it.

Facebook chose the one with the staleness problem. The paper says exactly what they built:

> In particular, we use memcache as a demand-filled look-aside cache

Look-aside is cache-aside. Demand-filled means nothing enters the cache until somebody asks for it. And then the write path:

> For write requests, the web server issues SQL statements to the database and then sends a delete request to memcache that invalidates any stale data.

A delete. Not an update. And they explain why in one sentence that is worth memorizing:

> We choose to delete cached data instead of updating it because deletes are idempotent.

That is the whiteboard. Two writers updating the same cached key can have their cache operations arrive in the opposite order to their database commits, and the cache is then left holding an older value with total confidence. Two writers deleting the same cached key produce an absent key regardless of order, and the next reader goes and looks in the fridge.

There is a second half to the reasoning, and it is the thing that makes the whole design legal:

> Memcache is not the authoritative source of the data and is therefore allowed to evict cached data.

Once you have said that out loud, a great deal follows. A cache that is permitted to be empty at any moment can be made simple, can be replaced, can be restarted, and can lose a machine without anybody losing data. Write-through quietly gives that property away, because if the cache is the write path, then the cache is on the correctness path.

## What the decision actually cost

Now the part that the pattern comparison in every system design guide leaves out. Choosing cache-aside did not make the consistency problem go away. It moved it into infrastructure they then had to build.

**Somebody has to send all those deletes.** The web server that made the write can delete the key it knows about, but Facebook runs many frontend clusters, and every one of them has its own memcache tier holding its own copy. So they built an invalidation pipeline. SQL statements that modify authoritative state are amended to carry the memcache keys that need invalidating once the transaction commits. A daemon called **mcsqueal** runs on every database, inspects the statements its database commits, extracts the deletes, and broadcasts them to the memcache deployment in every frontend cluster in the region.

Read that again as an operational reality rather than a diagram. There is a process sitting on your database, reading your commit stream, to keep a cache honest.

**And most of that work is wasted, deliberately.** This is my favorite number in the paper:

> We recognize that most invalidations do not delete data; indeed, only 4% of all deletes issued result in the actual invalidation of cached data.

Ninety-six percent of the invalidation traffic hits keys that were not cached. They know. They kept doing it, because the alternative is knowing which keys are cached where, and that is a harder distributed problem than sending a lot of cheap messages. That reading of the trade is mine, not theirs, but the number is theirs and it is hard to read any other way.

**And the volume forced another layer.** Sending those deletes directly from backend databases to every memcached server produced an unacceptable packet rate, so the daemons batch deletes into fewer packets, send them to dedicated mcrouter instances in each frontend cluster, and let those unpack and route the individual invalidations locally. The paper reports that "The batching results in an 18x improvement" in the packet rate.

So the honest tally for choosing cache-aside at this scale is: an amended SQL layer, a daemon on every database, a routing tier in every cluster, and a 96% waste rate accepted as the cost of not tracking cache contents.

That is not an argument against the choice. It is what the choice actually is.

## The number that moved, and the one that nearly did not

The primer warns about write-through that "the new node will not cache entries until the entry is updated in the database," and that "Most data written might never be read." Both are real. But cache-aside has the mirror problem, which the primer also lists: when a node fails and is replaced by an empty one, latency rises, because the new node knows nothing.

Facebook hit this at cluster scale, and their fix is the clearest measured result in this part of the paper.

When a new cluster comes online, or an existing one fails, or maintenance happens, the caches are empty and the backend gets the full weight of the traffic. They built **Cold Cluster Warmup**, which lets clients in the cold cluster fetch data from a warm cluster's cache rather than from persistent storage. The result:

> With this system cold clusters can be brought back to full capacity in a few hours instead of a few days.

Days to hours. That is the number that moved.

But the failure mode they had to solve to get it is more instructive than the speedup, so let me spend a paragraph on it, because it is exactly the kind of thing that bites at 3am.

A client in the cold cluster writes to the database and deletes its local cached key. A moment later, another client in the cold cluster misses and, under the warmup scheme, fills from the **warm** cluster. If the warm cluster has not yet received the invalidation, the cold cluster has just carefully copied a stale value into itself. Nothing will ever correct it, because from the cold cluster's point of view it now has a valid cached entry. The paper's phrase is that the item "will be indefinitely inconsistent in the cold cluster."

The fix is small and very specific: memcached deletes support a hold-off time that rejects add operations for a period afterwards, and "By default, all deletes to the cold cluster are issued with a two second hold-off."

Two seconds. A tiny constant, chosen because it is comfortably longer than an invalidation takes to propagate, protecting against a race that would otherwise produce silent permanent corruption in a system serving a billion people.

That is what caching consistency work actually looks like. Not a pattern name. A two second hold-off, in a specific direction, on a specific path, because somebody drew the interleaving.

## The transferable rule

If you take one thing from this, take this framing rather than a preference.

**Cache-aside and write-through are not competing features. They are competing answers to the question of who owns correctness.**

Cache-aside says the application owns it. The cache is disposable, can be empty, can lose a node, and is never the source of truth. You pay for that in staleness windows and in whatever invalidation machinery your scale demands. Facebook paid in mcsqueal, mcrouter batching, 96% wasted deletes, and a two second hold-off.

Write-through says the write path owns it. Freshness is structural, because nothing reaches the database without going through the cache. You pay for it in write latency, in caching data nobody will read, and in the fact that your cache is now standing on the correctness path, which means an empty one is not merely slow.

Notice that neither option removed the complexity. Both relocated it. Cache-aside pushes it into invalidation. Write-through pushes it into the write path and the failure model. The question worth asking in a design review is not "which pattern is better," it is **which of those two kinds of complexity does my team actually want to own at 3am**, given what we are good at and what our traffic looks like.

And one closing observation, since the paper hands it to us. Facebook's own summary of what caching became for them is that separating the caching layer from the persistence layer let them scale each independently. That is the benefit that survived every other tradeoff. Not the hit rate. The seam.

Tonight I am going to make all of this executable. A small deterministic model where you can watch two writers reorder, watch update-on-write produce a permanently wrong cache, watch delete-on-write refuse to, and see the exact cost of the cold node the primer warns about. There is one result in it that contradicted my own expectation, and I left the failed assertion in the write-up.

Comment your take, I read every reply.

---

*Today, 17:00: the runnable version. Two writers, one reordered operation, and the measurement that proved me wrong about cold nodes.*

*Tomorrow, 09:00: what happens when the cache is full. Eviction policies, measured across three workloads, where the winner of two rounds finishes last in the third.*
