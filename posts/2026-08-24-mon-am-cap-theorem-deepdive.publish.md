# Week 1 · Day 2 AM · Concept deep-dive · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-24-mon-am-cap-theorem-deepdive.md` (v1).
> That body is 3,036 chars, over LinkedIn's 3,000 limit. This cut tightens
> phrasing without changing any claim; measured at 2,918 chars
> (`len()`, 2026-08-24).
>
> Deltas from the committed v1 copy, in full:
> 1. Audit header and H1 stripped: repo artifacts, not post copy.
> 2. Opening sentence tightened ("no acronym required" replaces "no acronym
>    expansion required first") to reclaim chars, no meaning change.
> 3. Second paragraph's final clause tightened for length; the "not three,
>    exactly two moves" framing is preserved verbatim, it is the load-bearing
>    line.
> 4. All em dashes replaced with periods or commas (Constitution C-08: zero
>    em dashes in any writing).
> 5. Repo link added as the closing line (house pattern).
> 6. Teaser line kept, pointing to the 17:00 diagram post.

---

## 1 · Posting checklist

1. Confirm github.com/QuantumindSSI/systemdesign is public. The post links it.
2. Text post, no poll widget, no hashtags, no @-mentions, no image.
3. Post at 09:00. The PM diagram post at 17:00 re-diagrams this exact
   inventory example: post this one first, or the diagram references an
   example the reader has not seen yet.
4. Confirm the fold: the preview must end inside "no acronym required"
   territory, before the inventory example starts.
5. No edits after publish.

## 2 · Post body (paste exactly, 2,918 / 3,000 chars)

```text
Most explanations of the CAP theorem start with the acronym and work backward, which is exactly why so few people can apply it under pressure. Here is the definition in two sentences, no acronym required. When a distributed system keeps more than one copy of the same data and the network between those copies breaks, it cannot promise that every copy is both fully up to date and instantly reachable at the same time. During that break, each request has to pick one of those two promises to keep, and it cannot keep both.

Here is the mechanism, step by step, with one concrete example. Picture an online store with exactly one unit of an item left in stock, tracked by two servers: Node A in the eastern US, Node B in the west, each holding its own copy of the count and replicating changes to the other asynchronously. A customer on the west coast buys the last unit; the write lands on Node B, whose count drops from one to zero. Before that update replicates east, the link between the two nodes drops. A second customer, routed to Node A, tries to buy the same item, and Node A still shows a count of one, because A never received B's update and has no way to ask B right now. Node A has exactly two moves, not three. Serve the stale count and let the sale go through, keeping the system available but selling an item that does not exist. Or refuse the request until B can be reached, keeping the data consistent but turning away a customer who might have been fine to serve. There is no branch where A answers immediately and answers correctly, because the one fact that would let it do both is on the other side of a broken link.

Now the misconception that causes the most damage: treating "pick two of three" as a single, permanent decision made once, when you choose a database. Eric Brewer, who first stated CAP, wrote eleven years later that the "2 of 3" framing opens the conversation but is easy to over-read, since CAP "prohibits only a tiny part of the design space: perfect availability and consistency in the presence of partitions, which are rare" (quoted via bytebytego.com's CAP theorem guide, citing "CAP Twelve Years Later: How the Rules Have Changed"). CAP describes what happens during a partition, which most systems most of the time are not in. Teams that treat a database's "AP" or "CP" label as the whole conversation stop asking the harder question: what happens the rest of the time, when there is no partition but a slow node still has to choose between a fast, possibly-stale answer and a slower, fresher one? That question has its own theorem, and it is the one that governs your system on an average Tuesday. CAP tells you what breaks during the outage. It was never claiming to run the rest of the week.

Monday, 17:00: this same tradeoff, drawn as one diagram, with the exact line where it breaks marked and explained.

Plan and audit trail: github.com/QuantumindSSI/systemdesign
```
