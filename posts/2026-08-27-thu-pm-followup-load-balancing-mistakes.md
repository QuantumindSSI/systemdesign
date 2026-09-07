# Week 1 · Thu 2026-08-27 · Short follow-up: The Load Balancing Mistakes Checklist

> Calendar row: W1 Thu PM, 17:00. Format: common mistakes checklist, five
> yes/no checks, screenshot-able. Pillar: System Design Fundamentals. Pass:
> Foundations. Builds directly on this morning's
> `posts/2026-08-27-thu-am-tutorial-load-balancing.md` and
> `experiments/week-01/lb_algorithms_demo.py`.
>
> Adversarial review record: every number cited below is the same,
> already-verified figure from this morning's essay (9.99, 1.66, 79.9%,
> 19.1%, 6.88x, 1.12x, cold-start `Server1` x3); no new figures are
> introduced in this follow-up.

---

Five checks. Each one is a yes/no question. If the answer is "no," stop and fix it before this goes anywhere near production traffic.

**1. Does every `pick()` have a matching `release()`, on every exit path, including errors and timeouts?**

Least connections only knows what it's told. Skip `release()` on one error-handling branch and the balancer's connection counts drift from reality, permanently, in one direction. This morning's numbers show what "working" looks like: least connections held the degraded backend's queue depth to 1.66 against round robin's 9.99, a result that depends entirely on every finished request actually reporting itself finished. A single un-released connection doesn't crash anything. It just makes the balancer quietly wrong, in a way that gets worse the longer the process runs.

**2. Is your weighted round robin the smooth kind, or the burst kind?**

The naive implementation of "weight 5 vs weight 1" gives the heavier backend five requests in a row before the lighter one gets a turn. Verified directly against the reference repo's own code this morning: weights `[5, 1, 1]` produce `Server1, Server1, Server1, Server1, Server1, Server2, Server3`. If that backend is momentarily slow, five consecutive requests pay for it before the rotation moves on. The smooth scoring version, the one this week's demo file implements, interleaves instead: the same 5:1 ratio, but no five-in-a-row bursts. Check which one your load balancer actually runs, because "weighted round robin" as a label covers both.

**3. Does your load-balancing algorithm know the difference between five virtual nodes and one hundred?**

A consistent-hash ring with too few virtual nodes per backend isn't a milder version of a well-tuned one. It's a different failure mode. Measured this morning: 100 virtual nodes per backend produced a 1.12x gap between the busiest and quietest backend. One virtual node per backend produced 6.88x, with one backend absorbing 45.6% of all traffic. If your ring config was copied from an example without checking the vnode count, you don't know which of these two you're running.

**4. Have you actually measured what happens when you remove one backend, or are you assuming it's fine?**

Plain `hash(client) % N` and a consistent-hash ring both call themselves "hashing," and they produce opposite outcomes when the pool changes size. Removing one of five backends: 79.9% of clients reassigned under mod-N, 19.1% under the ring, measured against the identical 50,000-client set this morning. If your session-affinity layer has never been tested through an actual node removal, you don't know which number you're closer to.

**5. If your balancer routes by response time instead of connection count, does it break ties randomly, or does it default to the same backend every time?**

A response-time-based balancer starts with no data, every backend tied at zero. `list.index()`-style tie-breaking resolves that tie the same way every time: the reference implementation, run cold with no prior updates, sent three consecutive requests to `Server1`, not a random backend, the same one, because index-based selection is deterministic. If your balancer's warm-up behavior has never been checked, the first wave of traffic after every restart may be landing on one backend by accident, not by design.

---

*Tomorrow, 09:00: the hot take on why most advice about L4 vs L7 load
balancing gets the tradeoff backwards.*
