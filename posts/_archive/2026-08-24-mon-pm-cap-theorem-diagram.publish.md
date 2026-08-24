# Week 1 · Day 2 PM · Annotated diagram · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-24-mon-pm-cap-theorem-diagram.md` (v1).
> That body (prose + diagram) is 3,373 chars, over LinkedIn's 3,000 limit.
> This cut compresses the ASCII diagram (fewer box-drawing characters, same
> nodes, same failure point) and tightens prose; measured at 2,378 chars
> (`len()`, 2026-08-24). No claim or annotation dropped, only compressed.
>
> Deltas from the committed v1 copy, in full:
> 1. Audit header and H1 stripped: repo artifacts, not post copy.
> 2. Diagram redrawn smaller: same two nodes, same replication link, same
>    failure point label, fewer border characters. The full-size version
>    stays canonical in the repo.
> 3. Three annotation paragraphs tightened for length; each still names its
>    one claim (components, decision step, failure point) verbatim in
>    substance.
> 4. All em dashes replaced with periods or commas (Constitution C-08).
> 5. Repo link added as the closing line (house pattern).
> 6. A monospace note added before the diagram: LinkedIn does not guarantee
>    a fixed-width font, so the diagram may not align on every device. This
>    is disclosed rather than silently risked.

---

## 1 · Posting checklist

1. Confirm github.com/QuantumindSSI/systemdesign is public. The post links it.
2. Text post, no poll widget, no hashtags, no @-mentions, no image.
3. Post at 17:00, after the 09:00 CAP deep-dive: this post re-diagrams that
   exact inventory example and assumes the reader has seen it.
4. Preview the rendered post on both desktop and mobile before publishing.
   LinkedIn's line-wrap can break ASCII diagrams differently per device;
   if the diagram reads as garbled on mobile, fall back to the three
   annotation paragraphs alone and drop the diagram block.
5. No edits after publish.

## 2 · Post body (paste exactly, 2,378 / 3,000 chars)

```text
If you cannot draw the CAP theorem, you do not understand it yet. You can recite "consistency, availability, partition tolerance, pick two" without being able to say which two nodes are talking, what they are trying to agree on, or which exact step fails when the network drops. Here is the drawing that closes that gap, built from this morning's inventory example: one item in stock, two servers, one broken link.

(Diagram below is plain text; it may not stay perfectly aligned on every device.)

  write: qty 1->0              read: qty?
       |                            |
       v                            v
  [ NODE B, us-west ]          [ NODE A, us-east ]
  local qty: 0                 local qty: 1 (stale)
       |____________X_______________|
         replication link, FAILS HERE
     (B's write never reached A before this read arrived)

Three things to annotate before this means anything.

First, the components and the data flow. Two nodes, each the sole source of truth for its own copy, connected by one link that carries writes from one side to the other after the fact, not as part of the write itself. Each node answers from what it already has. That single fact, replication happens after the write, is what turns a broken link into a real problem instead of a minor delay.

Second, the step where the interesting work happens. Not the write on B, not the broken link alone. It is the instant Node A receives the read and must decide what to return, holding a count it knows might be stale and cannot verify. One node, one request, one missing fact: that instant is the entire CAP theorem, compressed.

Third, the failure point, marked where the link crosses out above. It fails there because that is the one link carrying the one fact, B's write, that would let A answer correctly. Break this link at this moment and A is forced into the choice the whole week has built toward: answer now with a number that might be wrong, or refuse until the number can be trusted again.

Save this drawing. Next time a database ships with an "AP" or "CP" sticker, you should be able to point to the exact line in your own architecture where that label starts to matter, and where it stops.

Tuesday, 09:00: inside a real repository, the code that makes one of these tradeoffs concrete, read line by line.

Plan and audit trail: github.com/QuantumindSSI/systemdesign
```
