# Week 2 · Mon 2026-08-31 · Long-form: A CDN Is a Shared Cache, Not a Map

> Calendar row: W2 Mon AM, 09:00 (CSV row `24:2`). Format: concept deep-dive.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/karanpratapsingh/system-design.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: define CDN architecture in
> two sentences with no jargon | walk the core mechanism step by step with one
> concrete example | state the one misconception that causes the most damage.
> Committed CTA: "Tag someone who is debugging this right now."
>
> Week-2 scope fences (deliberate, to avoid cannibalizing the rest of the week):
> - How a client reaches a particular point of presence is **Tue 09-01**
>   (DNS resolution paths). This essay names the deferral and does not trace
>   resolution, anycast, or GeoDNS.
> - Population strategy in general, cache-aside versus write-through, is
>   **Wed 09-02**. Push versus pull CDNs are mentioned only as the source
>   repo's taxonomy, with the general treatment deferred.
> - Which object gets discarded when edge storage is full is **Thu 09-03**
>   (eviction policies). This essay establishes only that residency and
>   freshness are different properties, and defers the policy mechanics.
> - Coordinating concurrent misses is **Fri 09-04** (stampede protection).
>   RFC 9111's request-collapsing language is cited once as an existence
>   proof and explicitly handed to Friday.
>
> Sources verified 2026-08-31:
> - `github.com/karanpratapsingh/system-design`, GitHub API: 45,880 stars,
>   last push 2026-07-08T00:36:51Z, not archived. CDN chapter read in a fresh
>   `--depth 1` clone at `repos/system-design/README.md`, lines 674-723
>   (definition L676, why L682, how L688-694, push/pull L700-710,
>   disadvantages L714-718).
> - RFC 9111 (HTTP Caching, June 2022), fetched from rfc-editor.org: shared
>   versus private cache (Section 1.1/2), cache key composition (Section 2),
>   reuse preconditions and the mandatory Age header (Section 4), Vary
>   matching including the `*` rule (Section 4.1), freshness lifetime
>   precedence (Section 4.2.1), heuristic freshness (Section 4.2.2), Age
>   accumulation across caches (Section 4.2.3), request collapsing (Section 4).
> - RFC 9110 (HTTP Semantics, June 2022): heuristically cacheable status codes
>   including 404 (Section 15.1), caching semantics defined for GET, HEAD and
>   POST with most implementations supporting only GET and HEAD (Section 9.2.3).
> - RFC 8446 (TLS 1.3, August 2018): Figure 1, full handshake completes in one
>   round trip before the client's first application data (Section 2).
> - Cloudflare, "Cache keys" (developers.cloudflare.com, page dateModified
>   2026-08-28): default cache key contents, the cache-sharding warning on
>   custom keys, the restricted-header list, and the device_type/geo/lang
>   user features.
> - AWS, "Understand the cache key" (CloudFront Developer Guide): default key
>   is distribution domain name plus URL path, the two-request hit example,
>   the Accept-Language variation list, the User-Agent cardinality warning,
>   and origin request policies.
> - Cloudflare, "Tiered Cache" (page dateModified 2026-08-14): lower-tier and
>   upper-tier hierarchy, only the upper tier may contact the origin, and
>   connection concentration.
>
> Adversarial review record (2026-08-31):
> - Propagation numbers are computed, not remembered. Great-circle distance by
>   haversine on WGS84 mean radius 6371.0088 km; London (51.5074, -0.1278) to
>   Ashburn (39.0438, -77.4874) = 5,917.3 km; London to Paris (48.8566, 2.3522)
>   = 343.6 km. Signal speed taken as c/n with c = 299,792.458 km/s and silica
>   fiber group index n = 1.4682, giving 204,190 km/s. Resulting one-way 28.98
>   ms, RTT 57.96 ms, three RTTs 173.87 ms; London to Paris RTT 3.37 ms. These
>   are propagation floors only. They exclude queueing, serialization, routing
>   detours and server time, and the essay says so in the body ✓
> - The Cloudflare-versus-CloudFront default cache key contrast is quoted from
>   each vendor's current documentation, not from memory, and both defaults are
>   stated as defaults rather than as fixed behavior ✓
> - "Age: 41", `shop.example.com`, and the two campaign-parameter logo URLs are
>   illustrative constructions, framed as an example on first use. No invented
>   benchmark, customer, incident, hit-ratio percentage, or production war story
>   appears anywhere. The essay's advice to inspect hit ratio per route
>   deliberately carries no example percentages, because any figure there would
>   be fabricated ✓
> - First-person statements in the body are authorial framing ("the sentence I
>   would put in your next design review", "the cleanest example I know"). None
>   of them asserts a personal incident, a client, or an observed measurement ✓
> - No vendor point-of-presence counts or traffic-share percentages are cited.
>   Those figures change continuously and were not verifiable to a primary
>   source today, so the essay makes its scale argument structurally instead ✓
> - The source repo is steelmanned before it is extended. Its definition is
>   quoted accurately and its geography framing is called incomplete rather
>   than wrong ✓
> - Zero em dashes.
>
> Known continuity gap (flagged, not papered over): the Sat 2026-08-29 recap
> and quiz was never published, and its committed hook promised "Answers in
> Monday's post." This essay therefore does not open with quiz answers, because
> there is no published quiz to answer. Friday's PM follow-up also closes with a
> pointer to that unpublished Saturday pair. Both gaps need an editorial
> decision separately from this post.

---

**Topic:** CDN architecture as a distributed shared cache whose behavior is decided by the cache key, the freshness lifetime, and edge residency

**Subtitle:** You will learn why proximity only pays on a hit, why two major CDNs disagree about whether your query string is a new file, and which three settings actually move traffic off your origin.

Good morning. Let me start with a meeting you have probably sat in.

Someone says the site feels slow for users in Europe. Someone else says, reasonably, that we should put a CDN in front of it. Everybody nods, because everybody knows what a CDN is: servers around the world, closer to users, faster pages. A ticket gets written. A month later the pages are not much faster, the origin is still busy, and there is a new line on the bill.

Nothing in that story is anyone's fault. The one-line explanation of a CDN is genuinely true, and it is also missing the half that decides whether the other half ever pays off.

So today, the mechanics. Not the marketing diagram with the glowing globe, but the actual sequence of decisions a caching server makes in the few hundred microseconds after your user's request lands on it.

## The two sentences, with no jargon in them

A CDN is a large set of caching servers, run by someone else, placed inside many networks around the world, each one holding copies of responses your servers already produced. When a request arrives at one of them, that server checks whether it is already holding a stored response that it is allowed to use for this exact request, and it contacts your servers only when the answer is no.

Read that second sentence again, because it has two clauses and the industry only talks about one of them.

"Allowed to use" is doing enormous work. And "this exact request" is doing even more, because the definition of *exact* is not obvious, is not universal, and is very often something you configured by accident.

## Give the standard explanation its best version first

Today's calendar source is `github.com/karanpratapsingh/system-design`, one of the better free system design references. I re-checked it this morning through the GitHub API: 45,880 stars, last pushed 2026-07-08, not archived. Its CDN chapter opens like this:

> A content delivery network (CDN) is a geographically distributed group of servers that work together to provide fast delivery of internet content.

And it explains the mechanism this way: to minimize the distance between visitors and the website's server, a CDN stores a cached version of its content in multiple geographical locations known as edge locations, so a visitor in the UK is served from London rather than making a full trip to a server in the USA.

That is correct, and the physics behind it is real enough that we should put a number on it rather than waving at it.

Take a UK reader and an origin server in Ashburn, Virginia. The great-circle distance from London to Ashburn is 5,917 km. Light in a silica fiber travels at roughly c divided by the fiber's group index, about 204,000 km per second, so one crossing costs about 29 ms and a round trip costs about 58 ms.

Now count the round trips a browser needs before it can even see the first byte of an image on a connection it has not used before. One for the TCP handshake. One for the TLS 1.3 handshake, which RFC 8446 shows completing in a single round trip before the client sends application data. One more for the request to go out and the response to come back. That is three round trips, about 174 ms, spent entirely on the speed of light before any server anywhere has done a single unit of useful work.

Now serve that reader from somewhere in Europe instead. London to Paris is 344 km, a round trip floor of about 3.4 ms, and a London reader reaching a London facility is nearer than that. The distance term has effectively gone away.

Those numbers are propagation floors and nothing more. Real paths are not straight lines, real networks queue, real servers think. But the gap is not subtle, and it is why CDNs exist at all. Proximity is worth about 170 ms per cold connection in this example, repeated for every asset that needs a new connection.

Here is the part the standard explanation leaves out. Every millisecond of that saving is conditional on the edge server already having the answer. If it does not, it makes the same 174 ms trip that your user would have made, and your user waits for that trip *plus* the extra hop into the CDN. On a miss, a CDN is slower than no CDN.

The source repo lists three disadvantages of CDNs: extra charges, geographic blocking, and having no servers near your audience. All three are real. Notice that all three are about cost and geography, and none of them is about the thing that actually determines whether you get hits.

## The mechanism, one request at a time

Let us follow a single request through, using one concrete example the whole way.

A reader in London opens your shop's newsletter link and their browser asks for:

```
GET /logo.jpg?utm_source=newsletter HTTP/1.1
Host: shop.example.com
```

**Step one: the request lands at a point of presence.** A point of presence, usually shortened to PoP, is one of those facilities full of caching servers. How this reader's request found the London PoP rather than the Frankfurt one is genuinely interesting and it is tomorrow morning's post, so I am going to skip it deliberately rather than hand-wave it. For today, assume the request arrived somewhere sensible.

**Step two: the edge builds a cache key.** This is the step that decides everything, and almost nobody draws it.

A cache key is the identifier the cache uses to decide whether it already has this thing. RFC 9111, the current HTTP caching specification, defines it as being composed from at minimum the request method and the target URI, and notes that many caches in common use only cache GET responses and therefore key on the URI alone.

Think of a coat check. You hand over a coat and get a numbered ticket. The coat is safe, the ticket is how you get it back, and if the number on your ticket does not match the number on the hook, the coat is unreachable even though it is hanging four feet in front of you. A cache key is that ticket number. The object can be sitting on the edge server, warm and fresh and paid for, and if your request computes a different key, the edge will tell your origin it has never heard of it.

Now, the part that surprises people. Two of the most widely deployed CDNs disagree about what goes on the ticket.

Cloudflare's default cache key, per their cache keys documentation, includes the full URL: scheme, host, and **the URI including its query string**. Their own example in that page is literally `/logo.jpg?utm_source=newsletter`. The default also folds in the `Origin` request header for CORS correctness, plus the method-override and forwarded-host header families.

Amazon CloudFront's default cache key, per the CloudFront developer guide, includes the distribution domain name and the URL path, and that is it. Query strings, headers and cookies are excluded by default. Their documentation walks through two requests with different query strings, different `User-Agent`, different `Referer` and different session cookies, and states plainly that the second one is a cache hit.

So take our reader's request, and a second reader in the same city who clicked the same logo from a different campaign:

```
/logo.jpg?utm_source=newsletter
/logo.jpg?utm_source=twitter
```

Same file. Same bytes. Same city. On a CloudFront distribution with default settings, one cache entry and one origin fetch. On a Cloudflare zone with default settings, two cache entries and two origin fetches. Neither vendor is wrong. They made different defaults for defensible reasons. But "I put a CDN in front of it" does not tell you which of those two worlds you are living in, and your marketing team generates query-string variants faster than your cache can warm up.

**Step three: the lookup.** With a key in hand, the edge checks whether it may reuse what it has. RFC 9111 lists the conditions, and all of them must hold: the target URI matches, the stored response's method allows this use, any request header fields nominated by the stored response's `Vary` field match the ones presented, the stored response does not carry `no-cache` unless it is revalidated, and the response is either fresh, or explicitly allowed to be served stale, or successfully validated.

That `Vary` clause is worth its own sentence, because it is a second, quieter way to fragment a key. `Vary` lets the origin tell the cache "this response depends on these request headers, so key on them too." `Vary: Accept-Encoding` is fine and normal. `Vary: User-Agent` is a small catastrophe, because AWS's own guidance points out that the `User-Agent` header has thousands of unique variations, and each one becomes its own copy in the cache. And `Vary: *`, which occasionally shows up in a framework's default headers, is defined by RFC 9111 to *always* fail to match. Not usually. Always. It is a guaranteed permanent miss, and it looks like a perfectly innocent line in a response.

**Step four: a hit.** If the checks pass, the edge serves the stored copy without contacting you, and it is required to add an `Age` header giving its estimate of how many seconds have passed since your origin generated or validated that response.

That header is free instrumentation and hardly anyone reads it. `Age: 41` means this copy has been sitting in caches for 41 seconds. RFC 9111 defines the value as the sum of the time the response spent resident in every cache along the path plus its transit time, which means on a tiered setup it accumulates across tiers. If you are ever unsure whether you are actually getting cached responses, curl the asset a few times and watch whether `Age` climbs. If it is missing or stuck at zero, you are not caching, whatever the dashboard says.

**Step five: a miss.** The edge has to go get it. On a flat CDN, that means every PoP that sees this object for the first time makes its own trip to your origin. Cloudflare's tiered cache documentation describes the alternative: split the network into lower tiers and upper tiers, let a lower tier ask an upper tier first, and permit only upper tiers to contact the origin. That both raises the hit ratio and concentrates origin connections into a handful of locations instead of the whole network.

Notice what tiered caching is really admitting. It exists because "put a copy near every user" and "do not hammer the origin" are in tension, and the naive topology loses that tension badly.

There is one more thing that happens on a miss when several requests for the same missing key arrive at once. RFC 9111 explicitly permits a cache to collapse them into a single forward request. That mechanism is Friday's post, along with the ways it goes wrong. Today I only want you to know the door exists.

**Step six: store, maybe.** The edge stores the response for next time, subject to freshness, which brings us to the second lever.

## Freshness is a permission you grant, with a precedence order

A response is fresh while its age has not exceeded its freshness lifetime. Fresh means reusable without asking you. Stale means it needs revalidation before it can be reused, or explicit permission to be served anyway.

RFC 9111 defines exactly how a cache computes that lifetime, using the first rule that matches:

1. If the cache is shared, and `s-maxage` is present, use it.
2. Otherwise, if `max-age` is present, use it.
3. Otherwise, if `Expires` is present, use `Expires` minus `Date`.
4. Otherwise, no explicit expiration exists, and the cache may invent one.

A CDN is a shared cache in the specification's own vocabulary: a cache that stores responses for reuse by more than one user, usually deployed as part of an intermediary. Your browser is a private cache. That distinction is not academic trivia. It is what makes rule one useful, because `s-maxage` is a dial that only the CDN turns.

```
Cache-Control: public, max-age=60, s-maxage=86400
```

That header tells browsers to hold the response for a minute and tells the CDN to hold it for a day. Your origin traffic drops, your users' browsers stay responsive to changes, and you did it with one header. Setting `max-age` on its own is the far more common configuration, and it leaves the shared-cache dial at whatever the general value happened to be.

Rule four is the one that bites. If you send no explicit expiration, the specification permits a cache to assign a heuristic lifetime it estimated on its own, typically from `Last-Modified`. And RFC 9110 defines a list of status codes that are heuristically cacheable, which includes 200 and 301, and also includes **404**.

Sit with that for a second. If a deploy briefly serves a 404 for an asset that has not finished uploading, and that 404 carries no cache-control headers, an edge is within specification to store it and keep answering with it after your deploy has finished and the asset exists. The file is there. Your origin is healthy. Your users get 404s from a cache that is behaving exactly as designed. Nothing there is a malfunction. It follows directly from rule four plus one missing header, and the fix is boring: send explicit cache-control on your error responses too, not only on your successful ones.

## Residency is a third thing, and nobody sets it

Here is the distinction that is easiest to miss, and the one I would most like you to leave with.

Freshness lifetime says how long a stored response *may* be reused. It says nothing whatsoever about whether the response is still stored.

Edge storage is finite. A PoP holds a working set, not your entire catalog, and when it needs room it discards things. Your one-year `max-age` on a product image is a permission, not a reservation. The copy can vanish in minutes if nobody asks for it, and the next request pays full price to your origin.

Which object gets discarded, and why the answer is harder than "the oldest one", is Thursday's post, so I will leave the policy alone. What matters today is the structural consequence, and it is the one that quietly breaks the mental model of a CDN as a map.

On a flat network, an object has to be fetched from your origin roughly once per PoP that ever serves it, and again every time it falls out of one. The more locations you have, the more times your origin gets asked for the same bytes. Popular objects survive this easily, because they are re-requested faster than they age out. Long-tail objects never do. They are cold nearly everywhere, nearly always, and the CDN in front of them is an extra hop with a bill attached.

Distribution is not free. It multiplies your miss cost by the number of places you distributed to, and tiered caching exists to buy that cost back.

## The misconception that does the most damage

It is this: **a CDN makes your site faster because it is closer to your users.**

That sentence is not false. It is a description of the payoff, presented as if it were the mechanism, and the substitution is expensive, because it points every subsequent decision at the wrong variable.

If proximity is the mechanism, then the way to improve a CDN is to add locations, and the way to evaluate one is to compare coverage maps. If keyed lookup is the mechanism, then the way to improve a CDN is to raise the fraction of requests that can be answered without asking you, and the way to evaluate one is to look at hit ratio per route.

The vendors are unusually direct about this once you go past the landing page. CloudFront's own documentation says you get better performance when you have a higher cache hit ratio, and that one way to improve that ratio is to include only the minimum necessary values in the cache key. Cloudflare's cache key documentation warns in plain language that custom cache keys give you more control but may reduce your cache hit rate and result in cache sharding.

Cache sharding is the honest name for the failure. One logical object, scattered across dozens of keys, each shard cold, each shard fetched separately, each shard occupying storage that would otherwise be holding something someone wants.

And it is almost always self-inflicted. AWS's guidance gives the cleanest example I know: a site that keys on `Accept-Language` in order to serve localized content will happily create separate cache entries for `en-US,en`, `en,en-US`, `en-US, en` and `en-US`, four keys and four origin fetches for four browsers that all said the same thing. Their recommended fix is not a smarter cache. It is to stop encoding the variation in a header and put it in the path instead, as `/en-US/content/...`, so that the key is something you chose rather than something a browser vendor chose for you.

The same logic explains why Cloudflare ships a `device_type` cache key feature that classifies a request as mobile, desktop or tablet. It exists because the honest version, keying on the raw `User-Agent`, would shard your cache into thousands of pieces. Three buckets is a deliberate act of cardinality control.

There is also a clean way to keep the data you need without paying for it in hit ratio. If your origin wants to see the campaign parameter for analytics but returns identical bytes regardless, CloudFront's origin request policies let you forward the value to the origin without including it in the cache key. Two different questions, two different mechanisms: what the origin gets to see, and what counts as a different object.

So the reframe I would offer, and the sentence I would put in your next design review, is this. **A CDN's job is to answer without asking you. Everything in its architecture either raises or lowers the probability that it can. Proximity is what you win when it does.**

## What to look at this week

You do not need a new dashboard to check this. You need four things you probably already have access to.

**Your cache status header.** Every major CDN sets one. Look at it per route rather than in aggregate, because a healthy overall hit ratio can hide a dismal one on the single route that costs you the most, and the aggregate is exactly the number the dashboard shows you first.

**The `Age` header.** Curl an asset several times. If `Age` climbs, you are caching. If it is absent or always zero, you are not, no matter what the configuration page says.

**Your key composition.** Go and read the actual default for the CDN you actually bought. If query strings are in the key, find out how many distinct query strings your real traffic produces for your most-requested paths. That number is often the whole story.

**Your `Vary` headers.** Especially any that a framework set for you. If you find `Vary: *` or `Vary: User-Agent` on a cacheable route, you found something worth fixing today.

The reason I would spend an hour on this rather than on adding another region is that the geography is already bought. You are paying for those locations whether or not your keys let them help. Most of the improvement available to you this week is sitting in a header, not on a map.

If you have ever stared at a CDN dashboard showing a green globe while your origin CPU graph refused to come down, this was probably why. The copies were near your users. They just were not the copies your users were asking for.

Tag someone who is debugging this right now.

---

*Today, 17:00: the same request as one annotated diagram, with the exact line where a cache key goes wrong marked on it.*

*Tomorrow, 09:00: how a request finds a point of presence in the first place. The DNS resolution path, traced hop by hop.*
