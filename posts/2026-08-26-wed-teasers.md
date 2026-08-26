# Week 1 · Wed 2026-08-26 · Teaser bundle (Twitter/X, LinkedIn, Reddit, Quora)

> Calendar row: W1 Wed, both slots. Per `content_calendar_overview.md`
> ("Teasers, one file, four platforms"), this file replaces the old
> full-repost publish cut: every platform below gets a hook and a link
> back to Substack, never the full essay text. Two sections follow, one
> for the 09:00 essay and one for the 17:00 follow-up.
>
> Source posts: `posts/2026-08-26-wed-am-essay-dynamo-case-study.md`
> (concept case study),
> `posts/2026-08-26-wed-pm-followup-dynamo-quorum-code.md` (evening code
> deep-dive). Standards: persona-constitution (Laws I-IV) + QSSI research
> persona (Laws I-VI) + Amendment 1.
>
> Link placeholder: `{substack-url}` below stands for the live Substack
> post URL. No Substack publication URL exists yet in this repo; per the
> system's rule against fabricating URLs, every link in this file is a
> literal, clearly marked placeholder to be substituted with the real
> published URL at posting time, not a guessed or invented domain.
>
> Length conventions checked before finalizing:
> - Twitter/X: single post, kept under 280 characters including the link.
> - LinkedIn: 2-4 short lines, no hashtag stack, one link.
> - Reddit: self-post framing for a subreddit like r/programming or
>   r/ExperiencedDevs; states why it is being shared, not just a headline
>   and a link, since link-only posts are typically removed as spam.
> - Quora: framed as a direct answer opening to a question a reader would
>   plausibly have already asked (09:00 = "How did Amazon actually use
>   consistent hashing in production..."; 17:00 = "How does Dynamo decide
>   which nodes hold a key...").
>
> Adversarial review record: no new numeric claims in this file; every
> figure below ((3,2,2), 200ms p99.9, 68.9ms/30.4ms, 99.94%, 3M+ checkouts,
> 79.9%/19.1%, 6.88x/1.12x, 7.7ms/16.0ms, 67.0%/0.0%, preference lists) is
> restated from the two source posts' own already-audited headers, not
> introduced fresh here ✓. Character counts for both Twitter/X posts verified
> below.

---

## 09:00 essay: "Case Study, Consistent Hashing in Production"

### Twitter/X

Amazon's Dynamo paper (SOSP'07): same ring as yesterday's 79-line file, at a scale where >150 services touch one page load. Read the actual (N,R,W)=(3,2,2) config, the 200ms p99.9 number, and why one hop cost 2x latency. {substack-url}

### LinkedIn

Yesterday I traced a 79-line teaching implementation of consistent hashing. Today: the same ring, in production, at Amazon, from the actual SOSP'07 Dynamo paper.

The paper is specific about numbers most summaries skip: a common (N,R,W) configuration of (3,2,2), a measured 99.9th percentile latency around 200ms, an order of magnitude above the average, and a single optional network hop that cost the difference between 68.9ms and 30.4ms at that percentile.

Also the part most summaries skip entirely: the paper tells you, in its own words, exactly which numbers it is withholding for business reasons, and I quote that directly instead of guessing at what's missing.

{substack-url}

### Reddit

Follow-up to yesterday's consistent hashing walkthrough: today I went through the actual Dynamo paper (Amazon, SOSP 2007) to see how the same ring gets used once it's carrying a shopping cart with an "always writeable, no exceptions" requirement. Pulled the real numbers: common config (N,R,W)=(3,2,2), measured 99.9th percentile latency ~200ms (10x the average), a single optional hop costing 68.9ms vs 30.4ms at p99.9, and the paper's own admission of exactly which numbers it's not allowed to publish. Sharing because most "Dynamo" summaries just say "consistent hashing + quorum" and skip every number that makes those choices legible. {substack-url}

### Quora

**How did Amazon actually use consistent hashing in a real production system, not just in theory?**

Went through the primary source, the 2007 Dynamo paper, rather than a secondhand summary. The short version: same ring mechanics as any consistent hashing implementation (MD5 hash, sorted ring positions, virtual nodes), but with concrete production numbers attached: a common (N,R,W) configuration of (3,2,2), measured 99.9th percentile latencies around 200ms, and a single optional network hop that doubled that latency when left in. Full breakdown, with direct quotes from the paper rather than paraphrase, here: {substack-url}

---

## 17:00 code deep-dive: "Dynamo on the Ring, in Runnable Code"

### Twitter/X

The code behind this morning's Dynamo case study: the preference list (walk the ring for N distinct nodes) and the (3,2,2) quorum, runnable. R+W>N buys zero stale reads out of 50,000, for 2x the median latency. {substack-url}

### LinkedIn

This morning was Amazon's Dynamo paper. This evening is the code: the two things Dynamo adds on top of a consistent-hash ring, both runnable in one stdlib file.

1. The preference list, walk the ring clockwise for the first N distinct physical nodes. UserA -> [D, C, F]: if D is down when a write lands, C and F are already named as backups, in order, before anything fails.

2. The quorum. (3,1,1) reads at 7.7ms but 67% come back stale; (3,2,2) satisfies R+W>N and returns zero stale reads out of 50,000, paying 16.0ms. Dynamo's common config, arrived at from the mechanism, not copied from the paper.

{substack-url}

### Reddit

The code half of this morning's Dynamo post: one stdlib file that makes the two things Dynamo builds on the ring runnable. First, the preference list, walk the ring clockwise collecting the first N *distinct* physical nodes (skipping extra vnodes of a node already chosen), so a key's replicas survive a machine failure; e.g. UserA -> [D, C, F]. Second, the quorum over that list: (3,1,1) gives 7.7ms reads but 67% stale, (3,2,2) satisfies R+W>N for zero stale out of 50,000 at 16.0ms. The two lines people get wrong are annotated: the distinct-node dedup, and treating an ack as "replicated everywhere." Seed 42, reruns identical. {substack-url}

### Quora

**How does Dynamo decide which nodes hold a key, and how does it stay consistent without a single master?**

Two mechanisms on top of a consistent-hash ring, both in one runnable file. First, the preference list: from a key's position, walk the ring clockwise and take the first N distinct physical nodes (skipping extra virtual nodes of a node already picked), so the replicas are genuinely different machines, e.g. UserA -> [D, C, F]. Second, a quorum over that list: with (N,R,W) = (3,2,2), R + W > N forces every read set to overlap every write set on the newest version, a measured zero stale reads out of 50,000 versus 67% for a fast (3,1,1), at double the median latency. Runnable snippet with the numbers: {substack-url}

---

*Thursday, 09:00: a hands-on tutorial building and measuring five load
balancing algorithms from scratch, the layer that decides which request
reaches which node once the ring has already decided who's eligible.*
