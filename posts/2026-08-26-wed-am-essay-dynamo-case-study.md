# Week 1 · Wed 2026-08-26 · Long-form: Case Study, Consistent Hashing in Production

> Calendar row: W1 Wed AM, 09:00. Committed title: "Case study: consistent
> hashing in production (foundations)." Format: long-form Substack essay.
> Pillar: System Design Fundamentals. Pass: Foundations. Primary source:
> DeCandia, Hastorun, Jampani, Kakulapati, Lakshman, Pilchin,
> Sivasubramanian, Vosshall, Vogels, "Dynamo: Amazon's Highly Available
> Key-value Store," SOSP'07, hosted at
> allthingsdistributed.com/2007/10/amazons_dynamo.html.
> Standards: persona-constitution (Laws I-IV, Structurally Decisive,
> Adversarial Review) + QSSI research persona (Laws I-VI) + Amendment 1.
>
> Adversarial review record (this session, 2026-08-26):
> - Primary source re-fetched directly this session (not carried over
>   unverified from the 2026-08-22 prep pass); every quoted figure below
>   is copied from that fetch, not recalled from memory.
> - Scale figures ("tens of millions customers," "tens of thousands of
>   servers," "over 150 services" per page render): Section 1/2.2, quoted
>   verbatim below.
> - "(N,R,W) = (3,2,2)" and "a typical value of N ... is 3": Section 6
>   opening, quoted verbatim, previously absent from the prep pack and
>   added this session after a full re-read.
> - Table 2 (client-driven vs. server-driven coordination latencies):
>   Section 6.4, quoted verbatim; source HTML flattens the table into
>   run-on text, transcribed here exactly as it appears, row order
>   preserved.
> - "99.9th percentile latencies are around 200 ms": Section 6.1, quoted
>   verbatim.
> - Version-conflict percentages (99.94% / 0.00057% / 0.00047% / 0.00009%):
>   Section 6.3, quoted verbatim.
> - "well over 3 million checkouts in a single day": Section 1
>   (Introduction), quoted verbatim.
> - The paper's own stated reason for withholding absolute request rates:
>   quoted verbatim from Section 1, not paraphrased, per the citation
>   discipline of naming what a source refuses to say.
> - Tuesday's ring (`posts/2026-08-25-tue-am-essay-consistent-hashing.md`)
>   and Tuesday PM's quorum snippet
>   (`posts/2026-08-25-tue-pm-followup-pacelc-snippet.md`) are referenced
>   by their own already-audited figures, not re-derived here.

---

The shopping cart service at Amazon has one rule that overrides almost everything else in its design: a customer adding an item to a cart can never be told no. Not because the database is slow, not because a replica is unreachable, not because, in the paper's own words, "disks are failing, network routes are flapping, or data centers are being destroyed by tornados." An always-writeable store, full stop, is the constraint, and Dynamo is the system Amazon built in 2007 to satisfy it at a scale where "add a server" and "a server disappeared" both had to be routine, boring events, not incidents.

This is the same ring from yesterday, MD5 hash, sorted positions, virtual nodes, run at a scale Tuesday's 79-line teaching file was never meant to reach. Here is what changes when consistent hashing stops being an exercise and becomes the partitioning layer under a production key-value store handling, by the paper's own account, "tens of millions" of shopping-cart requests a day.

## The Scene

By 2007, Amazon's e-commerce platform served "tens of millions customers at peak times using tens of thousands of servers located in many data centers around the world," built from "hundreds of services" working together, not one monolith. The paper is specific about how deep that composition runs: "a page request to one of the e-commerce sites typically requires the rendering engine to construct its response by sending requests to over 150 services." One page load, over 150 downstream calls. At that fan-out, a single service with a slow tail doesn't cost that service a bad afternoon, it costs every page render that touches it, which by the pigeonhole principle is close to every page render on the site.

That fan-out is why the paper measures everything at the 99.9th percentile and says so explicitly: "an SLA stated in terms of mean or median response times will not address" the customers who, for instance, have long personalization histories and therefore heavier queries. An example SLA the paper offers directly: "a response within 300ms for 99.9% of its requests for a peak client load of 500 requests per second." Not "usually fast." Fast on 999 requests out of every 1,000, always, because with over 150 services on the call graph of a single page, a p99.9 promise from any one of them is what makes a p99.9 promise from the page itself possible at all.

## The Decision

Against that background, the paper states its partitioning choice in one line: "Data is partitioned and replicated using consistent hashing." Not a novel algorithm invented for Dynamo. The same mechanism Tuesday's 79-line file implements: hash the key, MD5 into a 128-bit space exactly as in that file, walk the ring clockwise, find the first node with a position larger than the key's. "The principle advantage of consistent hashing is that departure or arrival of a node only affects its immediate neighbors and other nodes remain unaffected," the paper writes, which is Tuesday's `UserA`/`UserB` trace stated as a design goal instead of demonstrated against real hash integers.

The paper also names the exact same two weaknesses Tuesday's essay measured against a plain ring: "the random position assignment of each node on the ring leads to non-uniform data and load distribution," and "the basic algorithm is oblivious to the heterogeneity in the performance of nodes." Two sentences, and both are the same failure Tuesday's seeded demo put a number on: one virtual node per server produces a 6.88x load imbalance between the busiest and quietest server; a hundred virtual nodes per server brings that down to 1.12x. Dynamo's fix is named directly, and it is the identical fix: "each node gets assigned to multiple points in the ring," called tokens, so that "the number of virtual nodes that a node is responsible for can [be] decided based on its capacity, accounting for heterogeneity in the physical infrastructure." A bigger machine simply gets assigned more tokens; Tuesday's file's flat `num_replicas=3` for every server is exactly the simplification Dynamo's token-per-capacity scheme replaces once the servers in the ring stop being identical.

Dynamo measured its own remaining imbalance rather than assuming the token fix solved the problem completely. Running an experiment at S=30 (30 total tokens per node, split across the ring) with N=3, the paper reports that "during low loads the imbalance ratio is as high as 20% and during high loads it is close to 10%," measured against an explicit fairness bar: a node counts as "in-balance" only if its request load deviates from the average by less than 15%. Tokens bring the worst-case imbalance from Tuesday's 6.88x down toward parity, but the paper's own numbers show they do not erase it entirely, a double-digit percentage gap between the busiest and average node persists even with virtual nodes in place. That residual gap is why Dynamo keeps load balancing as its own live concern in section 6 rather than treating the ring as a solved problem the moment tokens are added, and it is exactly the layer Thursday's tutorial picks up: once a ring or a hash decides which node a request could go to, something still has to decide, request by request, whether that node can take it right now.

## Replication and the Preference List

A ring by itself only answers "who owns this key." Dynamo layers replication directly on top of it: "each data item is replicated at N hosts, where N is a parameter configured 'per-instance.'" The node that owns a key on the ring, the coordinator, "replicates these keys at the N-1 clockwise successor nodes in the ring," and that ordered list of N nodes, the preference list, is deliberately spread so that its members land in distinct physical nodes across multiple data centers, so a single data center failure, not just a single machine failure, still leaves the key available somewhere.

"A typical value of N used by Dynamo's users is 3," and the paper states one further concrete number that Tuesday's file has no equivalent of at all: "the common (N,R,W) configuration used by several instances of Dynamo is (3,2,2)." Three replicas. A write is durable once 2 of them have it. A read is trusted once 2 of them agree on it. That is the R and W from the exact quorum mechanism yesterday afternoon's snippet measured directly: R + W > N, here 2 + 2 > 3, guarantees every read quorum overlaps every write quorum on at least one replica holding the newest version. Yesterday's simulation, run with its own W=2/R=2 configuration chosen independently to demonstrate the mechanism, landed on the identical pair of numbers Amazon's own paper reports as its "common" real-world configuration. That is not a coincidence built into either piece of work; it is what R + W > N with N = 3 forces, the smallest majority overlap available once you fix N at 3.

Yesterday's snippet measured what that overlap costs: a fast, non-quorum configuration read at 7.7ms median with 67.0% stale reads; a quorum configuration eliminated staleness entirely at a cost of 16.0ms median, more than double. Dynamo's own production numbers, gathered over a full month rather than a seeded simulation, show the same shape of tradeoff at the percentile that matters to them: "the 99.9th percentile latencies are around 200 ms and are an order of magnitude higher than the averages," and a separate table comparing two coordination strategies for the same quorum work puts exact numbers on how much routing choices cost at that percentile: server-driven coordination measured 68.9ms at p99.9 for reads and 68.5ms for writes, averaging 3.9ms and 4.02ms; client-driven coordination, which skips an extra network hop by letting the client library talk to the right node directly, measured 30.4ms at p99.9 for both reads and writes, averaging 1.55ms and 1.96ms. Same quorum, same N/R/W, and removing one hop from the coordination path more than halved the tail latency. At averages measured in single-digit milliseconds, that entire difference is invisible; at the 99.9th percentile the paper insists on measuring, it is the whole story.

That hop-counting discipline is not incidental; it is a named design choice the paper contrasts directly against the structured peer-to-peer systems the technique otherwise resembles. Chord and Pastry, the DHTs the paper cites as related work, route a request through multiple intermediate peers to find the node responsible for a key, a design the paper calls out by name as the wrong shape for this workload, because "multi-hop routing increases variability in response times, thereby increasing the latency at higher percentiles." Dynamo instead keeps enough routing information on every node that any node can forward a request directly to the right one in a single hop, a property the paper labels a "zero-hop DHT." Table 2's 68.9ms-versus-30.4ms gap is that same principle showing up one layer further out: even a single optional forwarding step between a client and its coordinator node costs more than double at p99.9, which is why Dynamo's client libraries are built to skip it whenever possible rather than accept it as a rounding error.

## Trading Where for Whether

A strict quorum, exactly N candidate nodes and no others, would make Dynamo unavailable the moment any node in a key's preference list is down, the opposite of the always-writeable requirement the whole design starts from. The paper's fix has a name and a mechanism: sloppy quorum. "All read and write operations are performed on the first N healthy nodes from the preference list, which may not always be the first N nodes encountered while walking the consistent hashing ring." If a node that should hold a replica is unreachable, the write goes to the next healthy node instead, tagged with a hint recording who the intended recipient actually was; once that original node recovers, the hinted replica gets forwarded to it and the temporary holder deletes its copy. Hinted handoff is what lets Dynamo say, without qualification, that "the write request is only rejected if all nodes in the system are unavailable." Sloppy quorum trades where a replica temporarily lives for whether the write happens at all, and for a shopping cart, that trade is not a tuning knob, it is the entire point of the system.

The other side of eventual consistency is that two different nodes can end up holding two different, both legitimate, versions of the same cart, and someone has to decide which one wins, or whether both need to be kept and merged. Dynamo measured how often that actually happens rather than assuming it away: over the measurement period the paper reports, "99.94% of requests saw exactly one version; 0.00057% of requests saw 2 versions; 0.00047% of requests saw 3 versions and 0.00009% of requests saw 4 versions." Divergent versions are rare, not nonexistent, and the paper builds a whole mechanism, vector clocks plus a "read repair" step that quietly patches stale replicas the moment a coordinator notices them lagging during a normal read, specifically for that rare remainder rather than pretending it away.

Hinted handoff and read repair both assume the gap between replicas gets noticed during ordinary traffic, a node that was briefly down comes back and gets its hinted data forwarded, a coordinator that spots a stale reply during a normal read quietly patches it. Neither mechanism helps if a replica goes missing for long enough, or fails permanently, that it never shows up in that ordinary traffic at all, which the paper treats as a distinct failure mode with its own fix: an anti-entropy protocol built on Merkle trees. Each node keeps a hash tree per key range it hosts, leaves are hashes of individual keys, and each parent is a hash of its children, so two replicas can compare just their root hashes first; if the roots match, the paper notes, the entire underlying data is provably identical and no further comparison is needed, and only when roots disagree do the nodes walk down the tree comparing children until the specific out-of-sync keys are isolated. That is a direct, structural answer to the same operability question Tuesday's ring answers for membership changes: don't resynchronize everything after a permanent failure, resynchronize exactly the branch of the tree that actually diverged.

## What the Paper Won't Tell You

Not every number in this design is public, and the paper says exactly why, in its own words, rather than leaving the gap unexplained: "There are a number of places in this paper where additional information may have been appropriate but where protecting Amazon's business interests require us to reduce some level of detail. For this reason, the intra- and inter-datacenter latencies in section 6, the absolute request rates in section 6.2 and outage lengths and workloads in section 6.3 are provided through aggregate measures instead of absolute details." The paper is telling you, directly, that it is withholding the exact request-rate number for the shopping cart service, and it is worth saying that plainly rather than filling the gap with a guess. What it does report, from actual holiday production traffic rather than a lab benchmark, is that the shopping cart service "served tens of millions requests that resulted in well over 3 million checkouts in a single day" with no downtime, while the separate session-management service "handled hundreds of thousands of concurrently active sessions" at the same time. Those are the numbers Amazon chose to publish; the exact requests-per-second figure behind them is the one thing in this whole design this essay will not invent an estimate for.

## The Transferable Rule

Strip away the SOSP formatting and Dynamo is one idea, applied consistently: consistent hashing is not a partitioning trick, it is an operability contract. Adding or removing a node touches roughly 1/N of the keyspace and, by the design's own stated goal, nothing else. Tuesday's essay measured that contract directly on a five-node toy ring, 19.1% of keys remapped on removal against 79.9% for plain mod-N. Dynamo's contribution is not a better hash function; it is making every knob downstream of that ring, N, R, W, how many tokens a node gets, whether a hop through a load balancer is worth its latency cost, a per-service decision instead of a fixed architecture choice. The paper says as much explicitly in its design considerations: the goal is to "let services make their own tradeoffs between functionality, performance and cost-effectiveness," not to hand every service the same defaults regardless of what it actually needs.

A shopping cart chooses availability over consistency, because a merged cart is recoverable and a rejected "add to cart" is a lost sale. A product catalog, described elsewhere in the same paper's platform, can afford to choose consistency more aggressively, because catalog data changes far less often and staleness there is a worse user experience than a moment of unavailability. Same ring underneath both. Different R, different W, different tolerance for a stale read, chosen per service because the ring makes that choice cheap to make differently in different places, instead of forcing one global answer onto every kind of data a company the size of Amazon needs to store.

The earliest warning sign that a system hasn't learned this lesson yet is not exotic: it is a cache or storage tier whose node count shows up in a modulo operation anywhere in the codebase. That single detail, `hash(key) % len(servers)`, is Tuesday's whole problem statement, still live, still waiting for the day someone adds or removes a server and finds out how much of the keyspace just moved.

---

*This afternoon, 17:00: five lessons out of this case study, each one traceable
back to a specific measured number from this week, in
`posts/2026-08-26-wed-pm-followup-consistent-hashing-lessons.md`. Tomorrow,
09:00: a hands-on tutorial building and measuring five load-balancing
algorithms, the layer that decides which request reaches which node in the
first place, in `posts/2026-08-27-thu-am-tutorial-load-balancing.md`.*
