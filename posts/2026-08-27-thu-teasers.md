# Week 1 · Thu 2026-08-27 · Teaser bundle (Twitter/X, LinkedIn, Reddit, Quora)

> Calendar row: W1 Thu, both slots. Per `content_calendar_overview.md`
> ("Teasers, one file, four platforms"), this file replaces the old
> full-repost publish cut: every platform below gets a hook and a link
> back to Substack, never the full essay text. Two sections follow, one
> for the 09:00 essay and one for the 17:00 follow-up.
>
> Source posts: `posts/2026-08-27-thu-am-tutorial-load-balancing.md`
> (essay), `posts/2026-08-27-thu-pm-followup-load-balancing-mistakes.md`
> (follow-up). Standards: persona-constitution (Laws I-IV) + QSSI research
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
>   plausibly have already asked ("Which load balancing algorithm should
>   I actually use...").
>
> Adversarial review record: no new numeric claims in this file; every
> figure below (9.99/1.66, 79.9%/19.1%, 6.88x/1.12x, within-1-request WRR
> share, cold-start `Server1` x3) is restated from the two source posts'
> own already-audited numbers, not introduced fresh here. Character counts
> for both Twitter/X posts verified below.

---

## 09:00 essay: "Hands-On, Load Balancing Algorithms in Under an Hour"

### Twitter/X

Ran 5 load balancing algorithms in one seeded Python file. Degrade one backend 10x: round robin's queue depth hits 9.99, least-connections holds it to 1.66. Remove one backend: mod-N reshuffles 79.9% of clients, a hash ring reshuffles 19.1%. {substack-url}

### LinkedIn

Stopped explaining load balancing algorithms by definition and just measured all five in one file instead.

Degrade one backend to 10x its normal latency: round robin's mean queue depth on it hits 9.99, because it has no way to know anything changed. Least connections, watching the same backend, holds it to 1.66.

Remove one backend from a pool of five: naive hash-mod-N reassigns 79.9% of clients to a new backend. A consistent-hash ring reassigns 19.1%, close to the theoretical 1/N for losing one node.

Every number is reproducible, seed 42, five seconds on a laptop, script included.

{substack-url}

### Reddit

Got tired of load balancing explainers that stop at the definition, so I built one file that measures all five algorithms instead of just describing them: round robin, smooth weighted round robin, least connections, IP hash, and a consistent-hash ring, 100k simulated requests per scenario, seeded for reproducibility. The two numbers that actually matter: degrade one backend to 10x latency and round robin's mean queue depth on it hits 9.99 while least-connections holds it to 1.66; remove one backend from a pool of five and naive hash-mod-N reshuffles 79.9% of clients while the ring reshuffles 19.1%. Also caught a real cold-start bug in a popular reference repo's least-response-time implementation, first three requests all land on the same server every time, deterministically, before any response time has been recorded. Full walkthrough with the code: {substack-url}

### Quora

**Which load balancing algorithm should I actually use, round robin, weighted round robin, least connections, or hashing?**

Depends entirely on what stays true in your system, and I measured all five to make the tradeoffs concrete instead of abstract. Round robin is exact but blind to backend health, degrade one backend to 10x latency and its queue depth on that backend hits 9.99. Least connections adapts, holding the same scenario to 1.66, at the cost of needing every request to report when it finishes. Hashing (IP hash or a consistent-hash ring) buys session stickiness, but plain hash-mod-N reshuffles 79.9% of clients when one backend leaves the pool versus 19.1% for a properly built ring. Full measured breakdown with runnable code: {substack-url}

---

## 17:00 follow-up: "The Load Balancing Mistakes Checklist"

### Twitter/X

5 yes/no checks that catch most load balancing mistakes before they ship: matching release() calls, smooth vs. burst weighted RR, vnode count, tested node-removal behavior, and randomized vs. deterministic tie-breaking. {substack-url}

### LinkedIn

Five checks, each a yes/no question, each tied to a number from this morning's measurements:

Does every pick() have a matching release()? A naive weighted round robin bursts five requests onto one backend, does yours? Are you running 100 virtual nodes or 1, a 1.12x vs. 6.88x difference? Have you actually tested what happens when a backend is removed, 79.9% reshuffled vs. 19.1%? Does your tie-breaking default to the same backend every time on cold start?

{substack-url}

### Reddit

Follow-up to this morning's load balancing measurements: turned the numbers into five yes/no checks you can actually run against your own setup. Covers the release()-call bug that silently breaks least connections, the difference between smooth and burst weighted round robin (verified against a popular reference repo's actual output), the vnode-count gap that turns a 1.12x imbalance into 6.88x, the node-removal test most teams never run (79.9% vs 19.1% reshuffle), and a real cold-start bug where a response-time-based balancer sends its first requests to the same backend every time, deterministically, not randomly. {substack-url}

### Quora

**What are the most common load balancing mistakes and how do I check for them?**

Five checks, each a yes/no question tied to a measured number from a runnable demo: unreleased connections silently break least connections' load tracking; naive weighted round robin bursts requests instead of interleaving them; too few virtual nodes turns a 1.12x load imbalance into 6.88x; untested node-removal behavior hides a 79.9%-vs-19.1% difference in how much of your system reshuffles; and deterministic tie-breaking on a response-time-based balancer sends early traffic to the same backend every time instead of spreading it. Full checklist with the reasoning behind each check: {substack-url}

---

*Tomorrow, 09:00: the hot take on why most advice about L4 vs L7 load
balancing gets the tradeoff backwards.*
