# Week 1 · Mon 2026-08-24 · 17:00 · Follow-up: the CAP theorem in one diagram (foundations)

> Calendar row: W1 Mon PM, 17:00. Format: annotated diagram (this follow-up's
> structural spine, per the three-artifact-per-day model in
> `content_calendar_overview.md`). Pillar: System Design Fundamentals.
> Pass: Foundations. Source: github.com/ByteByteGoHq/system-design-101
> (same repo cited in this morning's essay; verification stands, GitHub API
> 2026-08-24: 87,468 stars, last push 2025-04-04, not archived).
> Standards: persona-constitution (Laws I-IV, Structurally Decisive, Adversarial
> Review) + QSSI research persona (Laws I-VI) + Amendment 1.
>
> Format-pivot note (2026-08-24): renamed from
> `2026-08-24-mon-pm-cap-theorem-diagram.md` to match the new
> `{date}-{day}-pm-followup-{slug}.md` convention. Body content is unchanged
> from the original draft; only this header was updated to reference the
> essay's current filename and drop the old LinkedIn-specific posting
> constraint (platform is Substack, not LinkedIn, under the current model).
> The superseded `.publish.md` cut of this post was moved to
> `posts/_archive/` since the old canonical/publish-cut convention is
> retired in favor of the teaser-bundle approach documented in
> `content_calendar_overview.md`.
>
> Adversarial review record (numbers audit):
> - No new numeric claims in this post; it re-diagrams the morning essay's
>   inventory example, already audited in that essay's header ✓
> - Diagram is original to this post (ASCII, text-only, no image asset), drawn
>   to match the mechanism described in the morning essay exactly: two nodes,
>   one async replication link, one read request arriving after the link
>   breaks ✓
> - Word count: 541 words in the reader-facing body (added one closing
>   paragraph linking explicitly to the essay's PACELC section during the
>   format-pivot pass), within the 500-700 word PM follow-up target
>   (verified 2026-08-24) ✓
>
> Companion reference: `posts/2026-08-24-mon-am-essay-cap-theorem.md` is this
> morning's essay; this follow-up assumes the reader has already read it and
> does not re-derive PACELC or the named-system classifications.

---

If you cannot draw the CAP theorem, you do not understand it yet. You can recite "consistency, availability, partition tolerance, pick two" without being able to say which two nodes are talking, what they are trying to agree on, or which exact step fails when the network drops. Here is the drawing that closes that gap, built from this morning's inventory example: one item in stock, two servers, one broken link.

```
                         incoming requests
                    ______________|______________
                   |                              |
             write: buy item              read: buy item
             (west coast)                 (east coast)
                   |                              |
                   v                              v
           +---------------+              +---------------+
           |    NODE B     |              |    NODE A     |
           |   us-west     |              |   us-east     |
           |   qty: 1 -> 0 |              |   qty: 1      |
           +-------+-------+              +-------+-------+
                   |                              |
                   |     async replication link    |
                   |______________X_______________|
                          [FAILS HERE]
                    link drops before B's update
                    ("qty: 0") reaches A

           Node A's read request arrives *after* the link
           fails and *before* it has ever heard qty is 0.
```

Three things to annotate before this diagram means anything.

First, the components and the data flow. Two nodes, each the sole source of truth for its own local copy, connected by one replication link that carries writes from one side to the other after the fact, not before. Requests do not go through a coordinator that checks both nodes first; each node answers from what it already has. That single design fact, replication happens after the write, not as part of it, is what makes a partition dangerous instead of merely inconvenient.

Second, the step where the interesting work happens. It is not the write on Node B, and it is not the broken link by itself. It is the moment Node A receives the read request and has to decide what to return, holding a count it knows might be stale and unable to check. That decision point, one node, one incoming request, one piece of missing information, is the entire CAP theorem compressed into a single instant. Every "AP vs CP" argument you have ever seen is an argument about what Node A should do at exactly that line.

Third, the failure point, marked where the link crosses out in the diagram above. It fails there and not somewhere else because that is the one link carrying the one fact, B's write, that would let A answer correctly. Break any other connection in this system and nothing interesting happens: a client retries, a load balancer reroutes. Break this one specific link, at this one specific moment, and A is forced into the choice this whole week has been building toward: answer now with a number that might be wrong, or refuse to answer until the number can be trusted again.

Save this drawing. The next time someone hands you a database with an "AP" or "CP" sticker on it, you should be able to point to the exact line in your own architecture where that label starts to matter, and the exact line where it stops.

One line this diagram cannot show: everything that happens on a day with no failed link at all. This morning's essay covers that separately, under PACELC, because a healthy network still forces a choice between latency and freshness on every single request, sticker or no sticker.

---

*Tuesday, 09:00: inside a real repository, the code that makes one of these tradeoffs concrete, read line by line.*
