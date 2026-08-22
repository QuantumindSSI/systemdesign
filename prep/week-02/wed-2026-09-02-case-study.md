# Prep · Week 2 · Wed 2026-09-02 · 09:00 · Case study

> Calendar row: W2 Wed AM. Committed title: "Case study: cache-aside vs
> write-through caching in production (foundations)". Committed outline:
> scene | decision, implementation, the number that moved | transferable rule.
> CSV source: github.com/donnemartin/system-design-primer (pattern definitions,
> verified in clone). Case-study anchor is primary-sourced separately.

## Pattern definitions (CSV source repo, verified in clone 2026-08-22)

`repos/system-design-primer/README.md`:
- Cache-aside section starts L1203 ("lazy loading", app manages the cache);
  disadvantages block L1233-1236 - notably: "Data can become stale if it is
  updated in the database... mitigated by setting a time-to-live (TTL)... or
  by using write-through."
- Write-through section L1239; L1267: "Write-through is a slow overall
  operation due to the write operation, but subsequent reads of just written
  data are fast... Data in the cache is not stale."
- L1271: new/replacement nodes start cold under write-through until entries
  are re-written - "Cache-aside in conjunction with write through can
  mitigate this issue."
- L1290: write-behind is more complex than either.
Line numbers drift; re-grep on post day, cite section anchors publicly.

## The case: memcache at Facebook (NSDI 2013)

**Primary source, verified 2026-08-22:** USENIX page (open access) -
https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala
Citation: Nishtala, Fugal, Grimm, Kwiatkowski, Lee, Li, McElroy, Paleczny,
Peek, Saab, Stafford, Tung, Venkataramani. "Scaling Memcache at Facebook",
NSDI'13, pp. 385-398. PDF, slides and talk video are on that page.

### Scene (verified: abstract + Piatek's public summary on the USENIX page)

- Scale, from the abstract: the system "handles billions of requests per
  second and holds trillions of items" serving "over a billion users".
- Architecture shape: sharded MySQL with a memcached tier for reads - the
  canonical look-aside (cache-aside) deployment, at the largest scale
  publicly documented.
- The evolution Piatek's summary names: caches accumulate responsibility
  until "the cache becomes the primary data store, without which the service
  cannot function" - consistency, failure handling, replication and load
  balancing all get harder once that happens.

### Decision and implementation

Facebook chose **look-aside (cache-aside), demand-filled**: the web tier
reads memcache first, on miss reads MySQL and fills the cache; writes go to
MySQL and **delete** (invalidate) the cached key rather than update it.
Piatek's summary confirms the paper's scope: consistency management between
cache and DB, replication coordination, and failure handling tuned for a
billion-user system - memcached itself "may lose or evict data without
notice", and the system provides no transactional invalidation.

IMPORTANT before writing: pull the PDF from the USENIX page for the
mechanism details you want to quote (leases against thundering herds /
stale sets, regional pools, cold cluster warm-up, McSqueal invalidation
pipeline). Those are in the paper body; this prep verified the page,
abstract and summary, not the full PDF text. Do not cite body-level numbers
until read directly.

### The number that moved

From the verified abstract: **billions of requests per second** against
**trillions of items** - achieved with a cache pattern whose every miss is
two round trips and whose every write is a deliberate cache delete. If a
body-level number is wanted (e.g. lease-related load reduction), read the
PDF first and cite the section; otherwise the abstract numbers carry the post.

### Transferable rule (close)

Cache-aside and write-through are not rival features, they are different
answers to "who owns correctness?". Cache-aside puts the application in
charge: reads scale, cache loss is survivable, and staleness is the tax
(primer L1236). Write-through puts the write path in charge: freshness is
structural, write latency is the tax (primer L1267), and cold nodes are the
corner case (L1271). Facebook ran cache-aside at world scale and paid the
correctness tax in engineering (invalidation pipelines, leases) - the
pattern choice decided where the complexity lives, not whether it exists.

## PM slot (17:00 lessons listicle) - five lessons

1. Invalidate, don't update, on write - two writers updating a cached value
   race; a delete is idempotent. (Memcache's delete-on-write.)
2. Every cache-aside miss is a stampede invitation; leases/locks are not
   optional at scale. (Paper body - read PDF before citing specifics.)
3. TTLs are the price floor of staleness, not the fix. (Primer L1236.)
4. Write-through without cache-aside leaves replacement nodes cold.
   (Primer L1271.)
5. The moment the service cannot run without the cache, it is not a cache -
   design its failure like a database's. (Piatek summary.)
Earliest warning signal: cache hit rate appearing in an availability
postmortem instead of a performance dashboard.

## Numbers audit

- Billions req/s, trillions of items, 1B+ users - NSDI'13 abstract, verified
  2026-08-22 ✓
- Primer quotes - clone, line-verified 2026-08-22, re-grep day-of ✓
- Body-level paper numbers - NOT verified; instruction in prep to read the
  PDF before use ✓
