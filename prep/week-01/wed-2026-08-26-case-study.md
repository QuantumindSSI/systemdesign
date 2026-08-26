# Prep · Week 1 · Wed 2026-08-26 · AM case study (concept) + PM code deep-dive

> Calendar rows: W1 Wed AM (case study, concept) + PM (code deep-dive). Day
> split 2026-08-26: concept in the morning, code in the evening, matching
> Tuesday. AM = this Dynamo case study; PM = a runnable preference-list +
> quorum snippet (`prep/week-01/code/dynamo_quorum_snippet.py`, seed 42;
> reproduces the AM's 7.7/16.0ms and 67.0%/0.0% quorum figures, and prints
> preference lists off the ring). The retired lessons-listicle's five points
> are already folded into this week's essays. Prior AM title: "Case study:
> consistent hashing in production (foundations)". Outline: scene | decision,
> implementation, the numbers | transferable rule. CSV source:
> github.com/karanpratapsingh/system-design (concept chapter, verified in
> clone: README.md line 1812 "# Consistent Hashing"); the case-study anchor
> below is primary-sourced separately.

## The case: Dynamo at Amazon (SOSP 2007)

**Primary source, verified 2026-08-22 (full text fetched):**
Werner Vogels' post hosting the paper -
https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html
Citation: DeCandia, Hastorun, Jampani, Kakulapati, Lakshman, Pilchin,
Sivasubramanian, Vosshall, Vogels. "Dynamo: Amazon's Highly Available
Key-value Store", SOSP'07.

### Scene (all facts verified in the fetched text)

- Amazon platform: "tens of millions customers at peak times", "tens of
  thousands of servers", hundreds of services; a page render typically calls
  ~150 services.
- The constraint that forced the design: the shopping cart must accept writes
  "even if disks are failing, network routes are flapping, or data centers are
  being destroyed by tornados" - an always-writeable store.
- SLAs measured at the **99.9th percentile**, not averages; example SLA quoted
  in the paper: 300ms response for 99.9% of requests at 500 req/s peak.

### Decision and implementation

- Partitioning: **consistent hashing on a ring** - MD5 of the key into a
  128-bit space (Tuesday's 75-line file is this exact scheme in miniature;
  same hash, same ring, same virtual nodes).
- The basic ring's two failures, named in the paper: random node positions
  give non-uniform load, and it ignores heterogeneous hardware. Fix:
  **virtual nodes** ("tokens") - each physical node owns many positions,
  capacity-proportional.
- Replication: each key stored at N successor nodes (preference list, distinct
  physical nodes, spread across data centers).
- Consistency dials: **R and W per service instance; R + W > N** gives the
  quorum overlap - the same knob the Tuesday-PM snippet measures. Sloppy
  quorum + hinted handoff keep writes flowing through failures.
- "Zero-hop DHT": every node can route any key directly, because multi-hop
  routing wrecks the 99.9th percentile.

### The number that moved

Verified in the fetched text (intro, production experience): during the
holiday shopping season Dynamo served the shopping cart through "tens of
millions" of requests resulting in **"well over 3 million checkouts in a
single day"** with no downtime, and the session-state service held "hundreds
of thousands" of concurrently active sessions. The paper explicitly withholds
absolute request rates for business reasons - say so in the post; naming what
a source refuses to say is part of the citation discipline.

### Transferable rule (close)

Consistent hashing is not a partitioning trick, it is an operability
contract: adding or removing a node touches ~1/N of the keyspace and nobody
else. Dynamo's twist is making the remaining tradeoffs (N, R, W) per-service
configuration instead of architecture - the cart chooses availability, the
catalog can choose consistency. The dial, not the default, is the design.

Optionally bridge back to the measured demo: mod-N remaps 79.9% of keys on a
5-node scale-in; the ring remaps 19.1% (seeded, `prep/week-01/code/`).

## PM slot (17:00 lessons listicle) - five lessons, each traceable

1. `mod N` is a resharding incident scheduled for later. (Demo: 79.9%.)
2. Virtual nodes are not optional at small cluster sizes. (Demo: 6.88x -> 1.12x.)
3. R and W are product decisions, not infra defaults. (Dynamo: per-instance.)
4. Sloppy quorum trades "where" for "whether": availability over placement.
   (Dynamo hinted handoff.)
5. Percentile SLAs decide architectures: zero-hop routing exists because of
   p99.9. (Dynamo.)
Earliest warning signal: a cache/storage tier whose node count appears in a
modulo anywhere in the codebase.

## Numbers audit

- 3M+ checkouts/day, tens of millions requests, ~150 services/page, 300ms @
  99.9% @ 500rps, tens of thousands of servers - Dynamo paper text, verified
  2026-08-22 ✓
- 79.9% / 19.1% / 6.88x / 1.12x - measured, seeded demo in this repo ✓
- Excluded: Vimeo/Google "bounded loads" deployment numbers - Medium returned
  403 on verification 2026-08-22; not cited anywhere ✓
