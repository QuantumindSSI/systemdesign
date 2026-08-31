# Week 2 · Sat 2026-09-05 · Recap and Quiz: Five Things That Decide Whether a Cache Helps You

> Calendar row: W2 Sat AM, 09:00 (CSV row `34:2`). Format: recap + quiz.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/karanpratapsingh/system-design (GitHub API today:
> 45,880 stars, last push 2026-07-08, not archived).
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: recap in one line each
> across CDN architecture, DNS resolution paths, cache-aside versus
> write-through, cache eviction policies, cache stampede protection | three
> quiz questions, one recall, one application, one design tradeoff | invite
> answers in the comments with no lookups.
> Committed CTA: "Comment your take - I read every reply."
>
> **Standing promise honored forward, not backward.** The committed hook is
> "Answers in Monday's post." That points at Mon 2026-09-07, which is week 3
> and is not yet written. The promise is restated in the body so it is a debt
> on the record. Note separately that the equivalent Sat 2026-08-29 recap for
> week 1 was never written, so this is the series' first published quiz and
> carries no inherited answer debt.
>
> **Publication-gap remediation (2026-09-04).** This format is naturally
> self-contained, which is useful given that none of the week's posts reached
> readers. Every recap line states its mechanism and its number rather than
> referring to the day it came from, so a reader arriving here first loses
> nothing. The quiz is answerable from this page alone.
>
> Numbers re-verified against their originating posts and artifacts today.
> Every figure below appears earlier this week with its own citation:
> - 5,917 km, 58 ms, 174 ms: computed, Mon 08-31 essay.
> - 300 to 400 ms Vladivostok p75, 10-15% p75/p95 improvement: Shirokov,
>   dropbox.tech, 2020-01-08, re-fetched 2026-09-01.
> - "deletes are idempotent", 4% effective deletes, hours instead of days:
>   Nishtala et al., NSDI'13, PDF text extracted 2026-09-02.
> - 61.6% versus 18.4%: `prep/week-02/code/cache_eviction_demo.py`, seed 42.
> - 0.0% on read-only keys: `prep/week-02/code/cache_write_strategies.py`.
> - 771 to 1, 50,000 to 460: `prep/week-02/code/stampede_strategies.py`.
>
> Adversarial review record (2026-09-05):
> - No new claims. This post introduces no figure that was not measured or
>   cited earlier in the week ✓
> - Quiz answers are deliberately not included, per the committed format. The
>   three questions are checked to be answerable from the recap section above
>   them, so the exercise is fair rather than a memory test of unpublished
>   material ✓
> - Question 3 has no single correct answer and is labeled as such, because
>   presenting a tradeoff question as having one would be dishonest ✓
> - Zero em dashes.

---

**Topic:** A one-line recap of the five caching mechanisms covered this week, followed by three questions that test whether they actually landed

**Subtitle:** If you can answer the third one without hedging, you understand caching better than most people who have run a cache in production.

Good morning. Slower post today, on purpose.

We covered a lot of caching this week, and there is a difference between having read something and being able to use it in a design review on a Tuesday. So: five one-line summaries, then three questions. No lookups. The honor system is doing a lot of work here and I trust you.

## The week in five lines

**1. A CDN is a shared cache, not a map.** Its behavior is decided by the cache key it builds from your request, not by geography, and proximity only pays off on a hit. The stakes are physical: London to Ashburn is 5,917 km, which is a 58 ms round trip floor, and a cold HTTPS connection needs three of them, so roughly 174 ms of pure physics is saved on every hit and paid on every miss. Cloudflare's default cache key includes your query string; CloudFront's does not. Same file, same city, different number of origin fetches.

**2. DNS-based traffic steering routes a resolver, not a user.** The authoritative server never sees the client's IP address, only the resolver's, so every routing decision is made about the whole crowd behind that resolver. Dropbox sent users in Vladivostok to Tokyo because a map said it was close, and their traffic went Vladivostok, Moscow, across the Atlantic, across America, across the Pacific, at a 300 to 400 ms 75th percentile. Routing on measured latency instead of distance bought 10 to 15% at p75 and p95, and almost all the real value was in the tail.

**3. Cache-aside and write-through are not competing features, they are competing answers to who owns correctness.** Facebook chose cache-aside and delete on write rather than update, and stated why in one sentence: deletes are idempotent, so two of them arriving out of order cannot lie, while two updates can. They paid for that choice with an invalidation daemon on every database, a batching tier in front of it, and a 96% rate of deletes that hit nothing.

**4. Every eviction policy is a prediction about the future, and it is only as good as the assumption it encodes.** LRU predicts recent means soon. LFU predicts often means again. Measured on identical traffic where the popular keys move, LRU held 61.6% and LFU collapsed to 18.4%, because frequency is memory and memory can be wrong. This is why Redis ships LFU with a decay period, and why `lfu-decay-time 0` is a trap.

**5. There are two failures called "cache stampede" and the famous fix only addresses one.** A lock cuts concurrent origin queries from 771 to 1, which is real, and leaves your own request pool exactly as occupied as it was. Meanwhile the more common production failure is many keys expiring in the same second because a bulk write gave them all the same TTL: 50,000 at once, which 10% jitter spread to a peak of 460. No lock touches that.

## Three questions

**Question 1, recall.** Two edge servers in the same city receive requests for the same image file, one URL carrying `?utm_source=newsletter` and the other `?utm_source=twitter`. On one major CDN this produces one cached object and one origin fetch. On another it produces two of each. Which is which, and what exactly is the mechanism that differs?

**Question 2, application.** You run a product catalog. A nightly job walks every product to rebuild a search index, touching each record exactly once. Your cache hit rate is healthy on the daily average but your morning latency is bad, and it has been for months. Name the interaction between that job and your eviction policy, say which policy family you are probably running, and give the one change you would make first.

**Question 3, design tradeoff.** This one has no single right answer, and that is the point.

Your service has a cache in front of a database. A regeneration costs about 200 ms. You can serve data up to 30 seconds stale without anyone in the business objecting. Your request pool is 200 slots and your database comfortably handles 50 concurrent queries.

Your busiest key expires and 800 requests arrive for it inside half a second.

Argue for one of: a blocking lock, permit rationing with retry, serve-stale with background revalidation, or doing nothing at all. Then name the specific condition that would flip your answer to a different option.

The condition is worth more than the choice. Anyone can pick an option. Knowing what would change your mind is the part that transfers.

## How to play

Answer in the comments before you scroll back up. Partial answers are welcome and more useful to everyone else than confident wrong ones, so say which part you are unsure about.

Answers go out in Monday's post, along with the start of week three.

And if you only take one line from this week into next, take the fourth one. Every caching mechanism we looked at is a prediction: a cache key predicts that these two requests want the same bytes, a TTL predicts how long an answer stays true, an eviction policy predicts what you will want next, and a stampede lock predicts that the expensive thing is the database rather than your own concurrency. Caching is not hard because the data structures are hard. It is hard because you are betting on the future, in four places at once, and the system does not tell you when a bet stops paying.

Comment your take, I read every reply.

---

*Today, 17:00: the weekend challenge. Ninety minutes, one SQLite file, and the difference between a query plan that says SCAN and one that says SEARCH.*
