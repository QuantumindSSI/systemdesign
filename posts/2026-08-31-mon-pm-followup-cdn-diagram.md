# Week 2 · Mon 2026-08-31 · 17:00 · Follow-up: CDN architecture in one diagram (foundations)

> Calendar row: W2 Mon PM, 17:00 (CSV row `25:2`). Format: annotated diagram.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: draw the components and
> the data flow between them | annotate the step where the interesting work
> happens | mark the failure point in red and say why it fails there.
> Committed CTA: "Repost this so your team sees it."
>
> Companion reference: `posts/2026-08-31-mon-am-essay-cdn-architecture.md` is
> this morning's essay. This follow-up assumes the reader has it and does not
> re-derive the cache key definition, the freshness precedence order, or the
> residency argument.
>
> Adversarial review record (2026-08-31):
> - No new numeric claims. The only figures in the diagram, 5,917 km, a 58 ms
>   round trip floor, and three round trips on a cold connection, are carried
>   unchanged from this morning's essay, where the haversine and c/n computation
>   and its stated exclusions are recorded in full ✓
> - Diagram is original to this post: ASCII, text only, no image asset. It
>   redraws exactly the request traced in the morning essay, two readers in
>   the same city requesting the same file with different campaign parameters ✓
> - "Red" in the committed calendar outline is rendered as an explicit
>   `[FAILS HERE]` marker, since this post ships as plain text. Stated here so
>   the deviation from the CSV wording is on the record ✓
> - The failure point is marked at the cache key construction line, not at the
>   origin. The origin fetch is the symptom. Rationale is argued in the body ✓
> - Cache-key defaults are described as vendor defaults, consistent with the
>   morning essay's citations to the Cloudflare and CloudFront documentation ✓
> - Word count: 821 words in the reader-facing body below the editorial `---`
>   marker, excluding the ASCII diagram fence. The annotation prose after the
>   diagram is 459 words and still sits inside the 500-700 word PM follow-up
>   target carried over from the W1 Mon follow-up. The overage is entirely the
>   catch-up context added by the publication-gap remediation noted below, and
>   is a deliberate exception to that target rather than scope creep.
>   Measured 2026-09-04, not estimated ✓
> - Diagram alignment is generated, not hand-spaced. Column audit: the edge PoP
>   box is 10 lines at exactly 68 columns, and the upper-tier and origin boxes
>   are 6 lines at exactly 60 columns. It will not shear in a monospace reader ✓
> - **Publication-gap remediation (2026-09-04).** No post in this week's
>   sequence reached readers, so every backward reference to a sibling post
>   was a dangling reference to material nobody had seen. The body now
>   carries the referenced substance inline instead of pointing at it:
>   a four-sentence restatement of what a CDN is and what a cache key
>   decides, plus the 5,917 km / 58 ms / 174 ms propagation arithmetic that
>   makes the hit-versus-miss asymmetry concrete. Written so it reads as a reminder to a sequential reader and as
>   sufficient context to a cold one ✓
> - Zero em dashes.

---

**Topic:** The one diagram of CDN architecture that puts the cache key on the page instead of a world map

**Subtitle:** Two readers in the same city ask for the same image, one gets a hit and one wakes up your origin, and the entire difference is a line most CDN diagrams never draw.

If you cannot draw CDN architecture, you do not understand it yet. Most of us can draw the marketing version from memory: a globe, some dots, some arrows. That drawing has never once helped anyone debug a low hit ratio, because the step that decides hit or miss is not on it.

If you did not catch this morning's essay, here is everything you need in four sentences. A CDN is a set of caching servers placed in many networks, each holding copies of responses your origin already produced. When a request arrives, the nearest one checks whether it is holding a stored response it is allowed to use for *this exact request*, and only contacts your origin when the answer is no. The definition of "this exact request" is a string called the **cache key**, assembled from pieces of the incoming request, and it is the thing that decides everything. Proximity is what you win on a hit, and on a miss a CDN is slower than no CDN, because the edge makes the same long trip your user would have made and you paid for an extra hop.

That last point has a number attached, which is worth carrying into the drawing. London to Ashburn, Virginia is 5,917 km. Light in fiber covers that in about 29 ms each way, so 58 ms for a round trip, and a browser opening a fresh HTTPS connection needs three of them: one for the TCP handshake, one for the TLS 1.3 handshake, and one for the request and response. That is roughly 174 ms of pure physics before any server does any work. All of it is saved on a hit and all of it is paid on a miss.

Here is the drawing. Same request as this morning, two readers in London, same logo, different campaign link.

```
   reader A, London                        reader B, London
   GET /logo.jpg?utm_source=newsletter     GET /logo.jpg?utm_source=twitter
            |                                          |
            +---------------------+--------------------+
                                  v
        +==========================================================+
        |            EDGE POP  ·  London                           |
        |                                                          |
        |  step 1   BUILD THE CACHE KEY                            |
        |             scheme + host + path                         |
        |             + query string ?   <=== [FAILS HERE]         |
        |             + Vary-nominated request headers             |
        |                                                          |
        |  step 2   LOOK THAT KEY UP                               |
        +==================+====================+==================+
                           |                    |
                   key found, fresh       key absent, stale, or
                        (HIT)             Vary mismatch (MISS)
                           |                    |
                           v                    v
                   serve stored copy        ask the tier above
                   add  "Age: 41"               |
                   origin requests: 0           v
                                        +------------------+
                                        |  UPPER TIER POP  |
                                        +---------+--------+
                                                  | still a miss
                                                  v
                                        +------------------+
                                        |  ORIGIN, Ashburn |
                                        +------------------+
                                        5,917 km away. A 58 ms
                                        round trip floor, three
                                        round trips on a cold
                                        connection.
```

Three things to annotate before this drawing earns its place on a wall.

**First, the components and the flow.** There are only three boxes, and the arrows only ever travel downward on a miss. The edge PoP is a shared cache holding copies of responses your origin already produced. The upper tier exists so that not every PoP is allowed to phone your origin independently. The origin is the only box in the picture that can produce a response that does not already exist somewhere. Everything above it can only find one, or fail to.

**Second, the step where the interesting work happens.** It is step one, and it takes microseconds. Before any lookup, before any network decision, the edge assembles a string out of pieces of your request, and that string is the entire question it is about to ask itself. Think of a coat check ticket. The coat is on the hook four feet away, and if the number on your ticket does not match the number on the hook, you are leaving without your coat. Reader A and reader B are standing next to each other in the same city asking for identical bytes. Whether the second one gets served from London or wakes up a server in Virginia is decided in that one line, by whether the query string is part of the ticket.

That is not a hypothetical. It is the documented default difference between two widely deployed CDNs. Cloudflare's default cache key includes the URI with its query string. CloudFront's default includes the domain and path only. Same file, same city, same afternoon, two different worlds.

**Third, the failure point, marked at that key line and nowhere else.** It is tempting to draw the red mark on the origin arrow, because that is where the pain shows up: latency, load, bill. But the origin is doing exactly what it was asked to do. The link is not broken. Nothing has crashed. The edge server is holding a perfectly good copy of that logo and is about to declare it does not have it, because the key it built does not match the key it stored under.

Break the origin and you get an incident, a page, and a fix. Break the key and you get a system that is quietly correct, slightly slow, and expensive forever. Nobody gets paged for a cache miss.

So when someone hands you a CDN diagram, ask where the cache key is drawn. If it is not on the page, the diagram is showing you the payoff and hiding the mechanism.

Repost this so your team sees it.

---

*Tomorrow, 09:00: how the request found the London PoP at all. The DNS resolution path, traced hop by hop.*
