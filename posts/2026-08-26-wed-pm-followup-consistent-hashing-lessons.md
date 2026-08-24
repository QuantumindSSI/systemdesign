# Week 1 · Wed 2026-08-26 · Follow-up: Five Lessons From This Week, Each One Traceable

> Calendar row: W1 Wed PM, 17:00. Format: short follow-up, 500-700 words.
> Pillar: System Design Fundamentals. Every lesson below cites a specific
> number already audited in this week's two prior posts
> (`posts/2026-08-25-tue-am-essay-consistent-hashing.md` and
> `posts/2026-08-26-wed-am-essay-dynamo-case-study.md`); no new figures
> are introduced in this file.

---

Three posts this week have all been circling the same ring. Here are the five lessons that fall out of it, each one pointing back to a specific number rather than a general impression.

**1. `hash(key) % N` is a resharding incident scheduled for later, not a design decision.**
Ten keys hashed with MD5, mod 5 versus mod 4: eight out of ten land on a different server the moment one server leaves. At larger scale the same mechanism produced 79.9% of 50,000 keys remapped on a single-node removal. The number is not the point; the mechanism is. Every key's new owner under mod-N depends on an arithmetic remainder that has no relationship to which physical server actually left, so nearly the whole table moves regardless of how small the change was.

**2. Virtual nodes are not optional once a cluster is small.**
One virtual node per physical server produced a 6.88x gap between the busiest and quietest server in a five-node ring. A hundred virtual nodes per server brought that down to 1.12x, and the same change dropped the remap-on-removal figure from 79.9% to 19.1%. Dynamo's own production numbers add the honest caveat: even with tokens in place, its measured imbalance ratio still ran 10% to 20% against a 15% fairness threshold. Tokens fix most of the problem, not all of it, and "most" is still the difference between a real system and a toy one.

**3. R and W are product decisions, not infrastructure defaults.**
Dynamo's common configuration, (N, R, W) = (3, 2, 2), was not chosen because 2-of-3 is a universally correct number. It was chosen because a shopping cart specifically cannot reject a write, and R + W > N with N = 3 is the smallest majority overlap that still guarantees a read sees the newest write. A service with different failure tolerance gets a different N, R, W, on the same underlying ring. The knob is the design, not a constant buried in a config file nobody revisits.

**4. Sloppy quorum trades where a replica lives for whether the write happens at all.**
A strict quorum fails the moment one of exactly N nodes is unreachable, which is the opposite of an always-writeable store. Hinted handoff routes the write to the next healthy node instead, tags it with where it was supposed to go, and forwards it once that node recovers. That single mechanism is the entire reason Dynamo can say a write is only rejected if every node in the system is down, not just the three that happened to be in one key's preference list.

**5. Percentile SLAs decide architectures; averages hide the decision that matters.**
Dynamo's own measurements: 99.9th percentile latencies around 200ms, an order of magnitude above the average. Removing one optional network hop between client and coordinator cut p99.9 latency from 68.9ms to 30.4ms, more than double, while the average moved by barely two milliseconds. A system tuned against its average would never notice that hop was expensive. A system tuned against its 99.9th percentile, because it has over 150 downstream services on a single page render and any one of them can blow the whole page's latency budget, has to notice it, and Dynamo's zero-hop routing exists specifically because it did.

The earliest warning sign that a system hasn't absorbed lesson one yet is not exotic. It is a cache or storage tier whose node count appears in a modulo operation anywhere in the codebase, waiting for the day someone scales that tier and finds out how much of it just moved.

---

*Tomorrow, 09:00: a hands-on tutorial building and measuring five load
balancing algorithms, the layer that decides which request reaches which
node once the ring has already decided who's eligible, in
`posts/2026-08-27-thu-am-tutorial-load-balancing.md`.*
