# Week 2 · Sat 2026-09-05 · Recap and Quiz: Five Things That Decide Whether a Cache Helps You

> Calendar row: W2 Sat AM, 09:00 (CSV row `34:2`). Format: recap + quiz.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
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
> **Forward promise recorded, not yet fulfilled.** The committed hook is
> "Answers in Monday's post." That points at Mon 2026-09-07, which is week 3
> and is not yet written. The promise is restated in the body so the future
> answer block is an explicit editorial debt. The equivalent Sat 2026-08-29
> recap is absent from the tracked sequence, so there is no earlier quiz here
> whose answers this post must supply.
>
> **Publication-gap remediation (2026-09-04).** This format is naturally
> self-contained, which is useful given the sequence's existing editorial
> record that none of the week's posts reached readers. Every recap states its
> mechanism, evidence, and material caveat rather than relying on a backward
> reference. A reader arriving here first has enough context to attempt the
> quiz.
>
> Numbers re-verified against their originating posts and artifacts today:
> - 300 to 400 ms Vladivostok p75, 10-15% p75/p95 improvement: Shirokov,
>   dropbox.tech, 2020-01-08, re-fetched 2026-09-01.
> - "deletes are idempotent" and 4% effective deletes:
>   Nishtala et al., NSDI'13, PDF text extracted 2026-09-02.
> - 61.6% versus 18.4% on the shifting-hot-set workload:
>   `experiments/week-02/cache_eviction_demo.py`, seed 42.
> - 771 arrivals before the first fill and 771 to 1 modeled origin
>   concurrency: `experiments/week-02/stampede_strategies.py`, seed 42. The
>   script declares a 200-slot pool but does not enforce admission, queueing,
>   or rejection; the body now states that limit.
> - 50,000 to 460 scheduled expirations per one-second bucket across 120
>   occupied buckets: the same script and seed. This is an expiry histogram,
>   not a measurement of regeneration or origin traffic. Although the current
>   script labels the buckets as regenerations, its calculation only places
>   expiry timestamps into buckets; the body records that distinction.
>
> Source pages re-fetched 2026-09-05: Cloudflare Cache Keys, AWS CloudFront
> "Understand the cache key," RFC 9846 Section 2, RFC 7871, Nikita Shirokov's
> Dropbox engineering post, the USENIX page and paper for "Scaling Memcache at
> Facebook," and Redis "Key eviction."
>
> Adversarial review record (2026-09-05):
> - No unsupported new claims. Every figure is attributed again in the
>   reader-facing copy, not only in this unpublished audit header ✓
> - Quiz answers are deliberately not included, per the committed format. The
>   three questions are checked to be answerable from the recap section above
>   them, so the exercise is fair rather than a memory test of unpublished
>   material ✓
> - Question 3 has no single correct answer and is labeled as such, because
>   presenting a tradeoff question as having one would be dishonest ✓
> - Cache population and write propagation are treated as separate choices;
>   cache-aside and write-through are not presented as exclusive opposites ✓
> - The DNS recap distinguishes the resolver's source address from the client
>   prefix optionally carried by EDNS Client Subnet ✓
> - Synthetic hit rates, offered demand, origin concurrency, and expiry counts
>   are labeled as model outputs, with the artifacts' limits beside them ✓
> - Reader-facing body: 2,759 words, measured 2026-09-05. Within the committed
>   2,500 to 3,500-word 09:00 essay range ✓
> - Zero em dashes.

---

**Topic:** Five caching decisions: cache keys, DNS steering, write strategy, eviction, and stampede control

**Subtitle:** Five compact recaps and three no-lookup questions will show whether you can turn the mechanisms into a design decision.

Good morning. Before we call this week done, here is a small test: can you explain each mechanism without leaning on its label?

You know the feeling. You finish a week of reading, every term looks familiar, and then a design review asks what you would actually choose. Suddenly the definitions blur together. So today is intentionally slower: five one-line takeaways with the evidence attached, then three questions. No lookups. The honor system is doing a lot of work here, and I trust you.

Think of a neighborhood library. Directions get you to a branch. A catalog number decides whether two requests mean the same book. An update process keeps copies honest. A shelf policy decides what stays. A queueing rule handles the rush when everybody wants one missing copy. A cache makes those same five decisions, just quickly enough that we stop noticing them.

## Five lines worth keeping

**1. A CDN is a shared cache, not a map.**

Geography decides how far a request travels. It does not decide whether the nearby edge can answer. That second decision has two gates, and it helps to keep them separate.

First, the CDN turns the request into a cache key. Think of the key as the library's catalog number. Two copies can contain the same bytes, sit on the same machine, and still look unrelated if their catalog numbers differ. That is what happens when a harmless campaign parameter becomes part of the key. The edge does not compare files and notice they are identical. It looks up the exact identifier it was told to build.

Second, finding a candidate is not enough. The response must still be resident and reusable: fresh, successfully revalidated, or explicitly permitted to be served stale. A correct key can find no resident entry because the response was never stored or was evicted. Expiration makes a retained response stale; it does not necessarily remove it. A badly designed custom key can create the opposite and more dangerous failure: two requests that should receive different representations collapse onto one stored response. The key chooses the candidate. Cacheability, freshness, validation rules, and residency decide whether the edge may reuse it.

Now the map matters. On a new connection, the long-haul path contributes to TCP setup, the full one-round-trip TLS 1.3 handshake shown in the current [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html#section-2), and the request-to-first-byte trip. Reusing a connection avoids the first two, not the final network trip. An edge hit avoids an upstream fetch. An edge miss goes to the next cache tier or the origin; only a miss through every configured tier reaches the origin.

The practical trap is that sensible vendors choose different catalog numbers. [Cloudflare's documented default](https://developers.cloudflare.com/cache/how-to/cache-keys/) includes the query string. [CloudFront's documented default](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html#cache-key-default) includes the distribution domain and URL path but excludes query strings by default. Put `?utm_source=newsletter` on one request and `?utm_source=twitter` on the next. For the same cacheable file at one empty edge with no upper cache tier, one default creates two keys and two origin fetches while the other creates one of each.

So when someone says, "the CDN is close to the user," ask the next question. Which fields build the key, and how do we know the responses are actually hits? Proximity only helps after identity and reuse have both worked.

**2. Without extra client-network metadata, DNS-based traffic steering routes a resolver, not a user.**

The familiar DNS picture often skips the person making the important call. Your browser asks a recursive resolver for an address. If the answer is not already cached, that resolver asks the authoritative server. The authoritative server normally sees the resolver's source address, not yours, and the resolver may then reuse the answer for other clients until its DNS TTL expires.

It is like asking a receptionist to make a reservation for you. The restaurant sees the receptionist's number. If it chooses a branch based on that number, it is choosing for everyone who uses the same front desk, not for your actual trip across town.

[EDNS Client Subnet](https://www.rfc-editor.org/rfc/rfc7871.html#section-5) adds an important qualification. It does not replace the resolver's source address. An ECS-capable resolver can also send a truncated prefix for the originating client network. An ECS-aware authority may use that prefix to tailor its answer, and the recursive cache must scope the stored answer to the network range the authority declares. That can improve steering, but it also fragments the resolver cache and carries a privacy cost. It is an optional signal, not permission to pretend the authority sees every end user directly.

[Dropbox's published account](https://dropbox.tech/infrastructure/intelligent-dns-based-load-balancing-at-dropbox) shows what the resolver-versus-user distinction costs when geography is the routing input. Users in Vladivostok were sent to geographically nearby Tokyo. Their packets did not follow the map. Dropbox describes the route going through Moscow, across the Atlantic, across the United States, and across the Pacific before reaching Tokyo, producing a 300 to 400 ms p75 round trip.

Dropbox replaced geographic closeness with measured network latency. The reported result was about a 10 to 15% improvement at p75 and p95, with the largest individual gains in the long tail. The transferable lesson is not that every team needs Dropbox's telemetry pipeline. It is that a location database is a proxy for the thing you care about. If you steer traffic, ask whose address the decision sees, how long that answer stays cached, and when you last compared the proxy with an actual path measurement. Follow the network, not the coastline.

**3. Cache population and write propagation are separate choices, not two exclusive pattern names.**

This week's labels hide two different questions. On a read miss, who fetches the durable value and puts it in the cache? On a write, do you invalidate the cached copy, update it, route the write through the cache, or wait for expiry? A system can use cache-aside reads and synchronous cache updates on writes. Calling one design "cache-aside" does not answer its write policy.

Return to the library. A reader checks the shelf, finds no copy, retrieves one from storage, and places it on the shelf for the next person. That is cache-aside population. Now a corrected edition arrives. The librarian can replace the shelf copy immediately, remove it so the next reader fetches the new edition, or wait for the old copy's allowed lifetime to end. That is a separate decision about coherence.

Write-through synchronously updates the cache and durable store before the write is considered complete. It buys a warm, current cached value after a successful write, but it adds cache work to write latency and puts the cache on the path that must succeed. Delete-on-write keeps the cache disposable. It commits the durable value and invalidates the copy, accepting that the next read will miss and refill.

In [Facebook's NSDI 2013 memcache paper](https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala), the application used demand-filled look-aside reads and, after database writes, deleted cached entries instead of updating them. Their reason was precise: deletes are idempotent. If two post-commit deletes arrive in either order, the cache is still empty. If two cache updates arrive out of order, the older value can land last and remain confidently wrong.

That simpler operation did not produce a simple system. At regional scale, mcsqueal ran on every database, extracted invalidations from committed SQL statements, and batched them through dedicated mcrouters. The paper reports that only 4% of issued deletes found an item to invalidate. Most invalidation messages did no useful deletion, but avoiding them would require tracking which cache held which item, another distributed problem.

The cache remained disposable, and Facebook could scale persistence and caching separately. Its best-effort staleness control still depended on infrastructure it had to build and operate. In your design review, ask which store is authoritative, what happens when cache and database operations arrive out of order, and whether a cache outage should make writes fail or merely make reads slower. Those answers matter more than the pattern label.

**4. Every eviction policy is a prediction about the future.**

When a shelf is full, removing something is unavoidable. The policy is simply a guess about which item the next reader is least likely to ask for. FIFO trusts age. LRU trusts recency. LFU trusts accumulated frequency. None of those is intelligence in the abstract. Each is a compressed theory of your workload.

LRU's weakness is a one-pass scan. Imagine a nightly job touching every product once. Each throwaway read becomes the most recent thing in the cache, so genuinely hot customer entries move toward the eviction end of the list. This is cache pollution: work with no future reuse displaces work that had reuse. The first mitigation to test is often not a new global policy. It is stopping the scan from inserting into, or updating recency in, the customer-facing cache.

LFU resists that pattern because a key touched once has little frequency. Its weakness appears when yesterday's popular keys are not tomorrow's. Old keys carry large counters from a demand pattern that no longer exists, while newly popular keys enter with no history and can be evicted before they accumulate evidence.

This series' seeded model, [`experiments/week-02/cache_eviction_demo.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-02/cache_eviction_demo.py), makes that second failure concrete. In the seed-42 shifting-hot-set workload, a 100-entry cache serves 200,000 requests drawn from a Zipf distribution with exponent 1.1 over 2,000 keys. The popularity ranking shifts by 400 keys after each 40,000-request epoch. LRU reaches a 61.6% hit rate. The model's exact, undecayed LFU reaches 18.4%.

Those figures belong to that synthetic workload, not to your production cache. The model also contains a scan scenario, but its aggregate totals include 25,000 compulsory misses from unique scan keys and do not isolate a material pollution penalty, so they cannot tell you how many points your own LRU policy would lose.

[Redis's LFU design](https://redis.io/docs/latest/develop/reference/eviction/#lfu-eviction) responds to stale popularity with a decay period that lowers counters over time. Its special `lfu-decay-time` value of `0` disables decay. That might preserve useful long-term history in a stable workload, or preserve yesterday's mistake indefinitely in a shifting one. Before changing policy, separate request classes, inspect hits and evictions around batch windows and deploys, and ask what your chosen policy assumes will repeat.

**5. There are two failures called "cache stampede," and they need different controls.**

The first shape is many readers arriving for one key. One popular value expires, and requests arriving before the refill completes all see a miss. A per-key lock or single-flight mechanism lets one caller regenerate while the others wait for its result. This is like a crowded cafe sending one employee to check a broken card reader instead of sending the whole staff. It protects the back office. It does not make the queue at the counter disappear.

The exact distinction matters in this series' [`experiments/week-02/stampede_strategies.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-02/stampede_strategies.py). With seed 42, the model samples 2,000 arrival times independently and uniformly across 500 ms, and the first fill takes 200 ms. It counts 771 arrivals before that fill completes. Without coordination, the model's peak origin concurrency is 771. A blocking lock reduces that origin concurrency to 1, which is a real and large win. All 771 arrivals still need a miss-path outcome before the fill completes.

The script declares a 200-slot request pool but does not enforce admission, queueing, or rejection. It therefore measures offered demand, not 771 occupied slots in a real 200-slot pool. In a deployed service, some requests might wait upstream, some might be rejected, and some might consume in-process capacity. Those choices change latency and failure propagation, and the model does not choose among them.

That is why the alternatives are about different resources. Serving stale while one caller revalidates can remove foreground waiting if the product permits old data and the cache retains an expired value to serve. A lease or permit can bound origin work without a mutex, but it protects the request pool only if denied callers return or release their slot rather than sleeping inside the service. A blocking lock can be perfectly reasonable when stale data is unsafe and the origin is the fragile resource, provided the wait is bounded by a deadline shorter than the request budget.

The second shape is many keys reaching expiry together. Imagine every alarm in a hotel set for the same minute. A lock on each room does not stagger the alarms because nobody is competing for the same room.

The script's second calculation writes 50,000 keys together at time zero with a 600-second TTL. With identical TTLs, all 50,000 expiry timestamps land in one one-second bucket. With seed 42, independently sampling each TTL uniformly from 540 to 660 seconds produces 120 occupied one-second buckets and a maximum of 460 scheduled expirations in one bucket. Although the script's printed heading calls these regenerations, the calculation contains no post-expiry requests and no origin work. It proves the expiry distribution, not how many keys will actually be requested and regenerated.

The mechanism still transfers. A per-key lock cannot move expiry timestamps for different keys. Independent TTL jitter can. The resulting origin load depends on which expired keys are requested, so measure misses and regeneration separately rather than treating expiry as work by definition.

When a miss storm appears, ask two questions before naming a component. Are many callers contending for one key, or are many keys becoming eligible to miss together? Then ask which bounded resource needs protection: origin concurrency, request admission, latency, or freshness. The answers choose the control.

The common thread is not "use a cache." It is **name the assumption before you choose the mechanism**. The cache key assumes two requests deserve the same bytes. Resolver-based DNS steering without client-network metadata assumes the resolver egress approximates the user's path. A cache-coherence policy assumes invalidation or expiry keeps stale exposure inside its allowed budget. Eviction assumes yesterday's access pattern predicts tomorrow's. Stampede protection assumes you know which resource will run out first.

## Three questions

**Question 1, recall.** Start with an empty edge cache and no upper cache tier. Assume two sequential `GET` requests use the same host, path, and all other key-affecting fields; the response is cacheable, stored, and still fresh; only `utm_source` differs. Under the documented defaults, one major CDN produces one cached object and one origin fetch; another produces two of each. Which is which, and what exact mechanism differs?

**Question 2, application.** You run a product catalog larger than the cache. A nightly job walks every product exactly once through the same LRU cache used by customer requests, and every job miss is inserted. The daily hit rate looks healthy, but morning latency is consistently bad. Explain how the scan interacts with LRU, then name the first mitigation you would test.

**Question 3, design tradeoff.** This one has no single right answer, and that is the point.

Consider a hypothetical service with a cache in front of a database. These figures are design inputs, not benchmark results: regeneration takes about 200 ms; the product permits data up to 30 seconds stale; the request pool has 200 slots; and the database is comfortable up to 50 concurrent queries.

Your busiest key expires and 800 requests arrive within half a second. You have not yet established their arrival distribution, whether or where requests queue once the pool is full, whether the cache retains expired bytes for stale serving, or whether a denied permit returns immediately and frees its request slot.

Name the missing fact you would resolve first. Then choose among a blocking lock, a bounded permit with retry, serve-stale with background revalidation, or no dedicated protection, making your assumptions explicit. Reject the other three under those assumptions, then name the condition that would flip your choice.

That condition makes the reasoning reusable in a system with different limits.

## How to play

Answer in the comments before you scroll back up. Partial answers are welcome. Show the part of your reasoning you trust and name the part you are unsure about, because that is where the useful conversation starts.

Answers go out in Monday's self-attention post, after tomorrow's week-three kickoff.

Take those five predictions into your next cache review: which requests are equivalent, which network path is shorter, how a copy stays true, which key will be wanted next, and which resource a miss storm will exhaust. When performance changes, identify which prediction no longer matches the workload before changing the mechanism.

Comment your take - I read every reply.

---

*Today, 17:00: the weekend challenge. Ninety minutes, one SQLite file, and the difference between a query plan that says SCAN and one that says SEARCH.*
