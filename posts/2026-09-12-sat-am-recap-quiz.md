# Week 3 · Sat 2026-09-12 · 09:00 · Recap and Quiz: Six Mechanisms, Three Answers I Owed You, and One Map

> Calendar row: W3 Sat AM, 09:00 (CSV row `48:3`). Format: recap + quiz.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body.
>
> Committed calendar beats, all three present below: recap in one line each
> across the week's mechanisms | three quiz questions, one recall, one
> application, one design tradeoff | invite answers with no lookups.
> Committed CTA: "Comment your take - I read every reply."
>
> **Editorial debt discharged here, in full.** This slot absorbs material from
> three rows that never reached readers, per the consolidation decision
> recorded 2026-09-09:
> - The quiz answers promised in `posts/2026-09-05-sat-am-recap-quiz.md`. That
>   post ended with three questions and said answers would come Monday
>   2026-09-07. `posts/2026-09-06-sun-am-theme-kickoff.md` repeated the
>   promise in the body and again in its teaser, and
>   `posts/2026-09-06-sun-pm-poll.md` repeated it a third time. Monday never
>   published. The answers are below, eight days late, with the delay stated
>   in the reader-facing copy rather than glossed.
> - W1 Sat 2026-08-29 AM, recap + quiz for week 1 (CSV row `18:1`), absent
>   from the tracked sequence. Its recap function is served by the
>   "Week 1, the recap that also never ran" section below, five lines with
>   figures re-quoted from the week-1 posts. Its quiz is not resurrected: a
>   quiz on material three weeks stale would be a memory test.
> - W0 Fri 2026-08-21 AM, "The 7-layer map" (CSV row `4:0`), absent. The map
>   is restored below as the closing section, because a reader three weeks in
>   has still never been shown where any of this sits.
>
> **Slots that are NOT resurrected, and why. Recorded so the decision is not
> quietly reversed later.**
> - W0 Fri 2026-08-21 PM, resource roundup of external repositories (CSV row
>   `5:0`). **Dead permanently.** The canonical source rule of 2026-09-06
>   forbids naming an external code repository in any post. This row cannot be
>   written in any form and should be treated as retired.
> - W0 Sat 2026-08-22 PM, "baseline yourself before week 1" (CSV `7:0`).
>   Superseded. Three weeks in, a pre-week-1 baseline has no audience.
> - W1 Sat 2026-08-29 PM, weekend challenge on reverse proxies (CSV `19:1`).
>   Deferred, not written. It is System Design Fundamentals material and
>   putting it in an LLM-internals week would serve the calendar rather than
>   the reader. The pillar recurs later in the 100-week plan.
> - W2 Sun 2026-08-30 AM and PM, week-2 kickoff and poll (CSV `20:2`,
>   `21:2`). Superseded. Week 2 ran and was recapped on 2026-09-05.
> Full inventory in `prep/README.md`.
>
> Numbers re-verified against their originating artifacts, all re-run
> 2026-09-09, all exiting 0 with "All assertions passed":
> - 90,188 tokens at vocabulary 1,024, +1.29% and +38.21%:
>   `experiments/week-03/pretoken_boundary.py`, md5
>   d4dd969b1f118a5a18496c1c6b4a0c7b.
> - 933 disagreements, +3.14%: `experiments/week-03/bpe_trace.py`, md5
>   33236832cc519bee4ed0e83b77c32e8b.
> - 33.7% and 5.3% share, 0.1003 against 0.0997:
>   `experiments/week-03/embedding_lab.py`, md5
>   36c23c8fab0535cbf8b49e3454e526e7.
> - 1.041e-17 and 8.216e-02: `experiments/week-03/permutation_equivariance.py`,
>   md5 da5e41c82094fe585cf9759c0420272e.
> - 2.189e-12, 0.1854 and 0.9977: `experiments/week-03/rope_properties.py`,
>   md5 dd346762e3ace54bbf078fec78ad67e5.
> - 8.04 to 506.50 score variance, 16,384 parameters at every head count:
>   `experiments/week-03/attention_heads.py`, from 2026-09-08.
> - Whole suite: 270 tests, all passing 2026-09-09.
>
> Week-2 figures quoted in the answer section are re-quoted from
> `posts/2026-09-05-sat-am-recap-quiz.md` and its cited artifacts, not
> re-measured today. Stated at the point of use.
>
> **Standing rule, not yet discharged.** Prepared 2026-09-09 for a 2026-09-12
> slot. `prep/README.md` requires a re-run on posting day; the md5s above are
> the expected values.
>
> Adversarial review record (2026-09-09, prepared three days ahead):
> - Question 3 of the week-2 quiz had no single right answer and was labelled
>   that way when asked. The answer below is presented as one defensible
>   choice with its assumptions named, not as the correct one ✓
> - The eight-day delay on those answers is stated in reader-facing copy, not
>   only in this header ✓
> - The 7-layer map is presented as this series' organising scheme, not as an
>   industry standard, because it is ours ✓
> - Every week-3 figure names its artifact. Week-2 figures are marked as
>   re-quoted rather than re-measured ✓
> - The three new questions are answerable from the recap section above them,
>   so the quiz is fair rather than a memory test ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,575 words, measured 2026-09-09 by whitespace split
>   over everything below the `---` marker. Within the committed 2,500 to
>   3,500-word 09:00 range ✓
> - Zero em dashes.

---

**Topic:** The week's six mechanisms in one line each, the three answers owed since 2026-09-05, and the map showing where all of this sits

**Subtitle:** Debts first, because I have been promising these answers for eight days, and a series that carries a promise that long should pay it before it recaps anything.

Good morning.

Before the recap, a debt.

On Saturday the 5th I ended the week-2 recap with three questions and said the answers were coming Monday. On Sunday I said it again, in the body and in the teaser. On Sunday evening I said it a third time. Then Monday's post did not run, and Tuesday through Friday were all built on material that came after it.

That is eight days. If you answered those questions and have been waiting, thank you for the patience, and it should not have taken this long. The answers therefore go first, before anything else, and then we do the week.

## The three answers, eight days late

These figures come from the week-2 posts and their artifacts and are re-quoted rather than re-measured this morning.

**Question 1, recall.** Two sequential GETs, same host, same path, same everything except `utm_source`. Empty edge cache, no upper tier, response cacheable and still fresh. One major CDN produces one cached object and one origin fetch; another produces two of each. Which is which, and what mechanism differs?

The mechanism is **whether the query string is part of the cache key by default**.

One vendor's documented default excludes the query string from the key, so `utm_source` changes nothing about identity: request two is a hit on the object stored by request one, and the origin is contacted once. The other vendor's documented default includes the full query string, so the two URLs are two distinct keys, two objects, two fetches.

The thing worth carrying is not which vendor does which. It is that **a cache key is a policy decision with a default, and the default is where your marketing team's tracking parameters turn into a cache-hit-rate incident**. Anything appended to a URL for a reason unrelated to content is a candidate to fragment your cache, and the fix is to normalise the key deliberately rather than discovering the default at the wrong moment.

**Question 2, application.** Product catalog larger than the cache. A nightly job walks every product exactly once, through the same LRU as customer traffic, inserting on every miss. Daily hit rate looks fine, morning latency is consistently bad. Explain the interaction, then name the first mitigation you would test.

The interaction is **cache pollution by a scan**, and LRU is maximally vulnerable to it by design.

LRU's entire premise is that recently used means soon used again. A scan violates that premise on every single access: each product is touched exactly once and will not be touched again by the job. Every one of those touches is recent, so the scan's entries occupy the front of the LRU ordering and evict the genuinely hot working set built up during the day. By morning the cache is full of things nobody will request and empty of things everybody will.

The hit rate hides it because it is a daily average dominated by daytime traffic, and the damage is concentrated in the hours right after the job.

The first mitigation I would test is **keeping the scan out of the customer cache entirely**: give the job its own connection, its own cache, or no cache. It is the cheapest change, it is the most reversible, and it addresses the cause rather than the symptom. Only if that is impossible would I move to scan-resistant admission, which is more machinery and more ways to be subtly wrong.

Week 2's measurement is the evidence that this class of failure is not theoretical. Across three workloads, LFU won two and then collapsed to **18.4%** on a shifting hot set where LRU held **61.6%**, because LFU's long memory is its own version of the same mistake.

**Question 3, design tradeoff.** No single right answer, which was the point. Regeneration about 200 ms, staleness tolerance 30 seconds, 200 request slots, database comfortable to 50 concurrent queries. Busiest key expires, 800 requests arrive in half a second. Name the missing fact you would resolve first, choose a strategy, reject the others under stated assumptions, and name what would flip you.

**The missing fact I would resolve first: does the cache retain the expired bytes.**

I picked that one over the arrival distribution and over the queueing behaviour because it is the only one that changes the option set rather than the parameters. If the expired value is still in memory, serve-stale is available and the entire problem becomes easy, since 200 ms of staleness sits comfortably inside a 30-second tolerance. If the bytes are gone, serve-stale is off the table no matter what else is true, and I am choosing among ways to make 800 requests wait.

**Assuming the bytes are retained, I would choose serve-stale with background revalidation.** One request triggers regeneration, every other request gets the slightly old value immediately, nothing queues, the database sees one query rather than 800, and the worst case a customer experiences is data 200 ms past its expiry against a permitted 30 seconds.

Rejecting the others under that assumption. A **blocking lock** makes 799 requests wait 200 ms while holding request slots; at that arrival rate the pool is the binding constraint before the database is. A **bounded permit with retry** protects the database properly but the denied requests still have to do something, and unless a denied permit returns immediately and frees its slot, it is the blocking lock with extra steps. **No protection** sends 800 requests at a database comfortable with 50, which is a sixteen-fold overshoot.

**What flips me:** if the bytes are not retained, I go to a bounded permit with immediate rejection and a client-side retry, and I accept visible errors for a fraction of a second in exchange for not losing the database. If the staleness tolerance were 30 milliseconds instead of 30 seconds, serve-stale would be wrong regardless of what the cache retains.

If your answer differed, I would genuinely like to read it. The third question is the one where the reasoning is worth more than the conclusion.

## Week 1, the recap that also never ran

While I am paying debts: the week-1 recap was scheduled for Saturday 2026-08-29 and did not run either, so week 1 has never been closed off. Five lines, one per topic. These figures come from the week-1 posts and their artifacts, re-quoted rather than re-measured this morning.

**CAP.** The choice only exists during a partition, and outside one you are choosing between consistency and latency instead, which is the part people skip. Before the network splits, CAP has no opinion about your system at all.

**Consistent hashing.** Hash servers and keys onto the same ring so adding or removing a server moves only the keys between two adjacent points instead of rehashing everything. The catch is that random placement is uneven: with one virtual node per server, the busiest server held **6.88 times** the load of the quietest. A hundred virtual nodes per server brought that to **1.12 times**.

**Dynamo.** The same ring at production scale, and the honest part is that virtual nodes did not fully fix the imbalance. Running with 30 tokens per node, the paper reports imbalance "as high as 20%" at low load and "close to 10%" at high load, against a fairness bar of 15% deviation from average. The quorum tradeoff was measured too: a non-quorum (3,1,1) configuration read at 2.3 ms median with **66.8% stale reads**; the (3,2,2) quorum removed staleness entirely at 6.9 ms, roughly triple. Divergent versions were rare but real: "99.94% of requests saw exactly one version", leaving a remainder that vector clocks and read repair exist to handle.

**Load balancing algorithms.** Round robin, least connections and weighted variants are each a prediction about what makes a server slow, and they fail when the prediction stops matching your traffic. Same shape as the eviction result from week 2, and the same lesson.

**L4 against L7.** Not a choice between fast and smart. It is a choice about where the trust boundary sits: who terminates TLS, who can see client identity, who owns retries, and therefore which team can safely operate the failure.

The thread running through all five, and worth carrying into any week: **every one of them is a default that somebody chose, and the default is where the incident comes from**. Random ring placement, a quorum setting, a load-balancing algorithm, a TLS termination point. None of them announce themselves.

## Week 3, six mechanisms in a line each

Now this week. Everything below has a runnable artifact behind it in this repository.

**1. Self-attention.** Every position looks at every other position and pulls in a weighted mixture, with the weights computed from content rather than fixed in advance. Cost: O(n squared times d) per layer, in exchange for a maximum path length of O(1) between any two positions. The budget is the thing to remember: softmax makes each row sum to 1.0, so every position has exactly one unit of attention and spending it here is not spending it there.

**2. The scaling factor.** Dot products over d_k terms have variance d_k, so scores spread as heads widen, and wide enough scores turn softmax into an argmax. Measured across a 64-fold range of widths, variance over d_k stayed between 0.984 and 1.011. Unscaled, the mean largest weight climbed from 0.560 to 0.947; scaled, it held between 0.238 and 0.248.

**3. Multi-head attention.** One head produces one distribution per position, so two different reasons to look in two places get blended into one number that cannot be un-blended. Heads **divide** the existing width rather than adding to it: 16,384 parameters at 1, 2, 4, 8 and 16 heads with d_model 64, identical every time. It is cost-neutral, not cost-reducing, and the quadratic term is untouched.

**4. BPE tokenization.** A compression algorithm applied to language, which means token boundaries follow frequency and frequency has no idea what a word is. Every boundary you do not draw, frequency will cross: with no word boundary, 306 of 768 merges went to tokens mixing character categories, and compression got *worse*, not better. The category boundary costs +1.29% tokens; removing the space exception costs +38.21%.

**5. Embedding layers.** A table, one row per token id, where reading a row is exactly multiplying by a one-hot vector, which is the entire reason the table is trainable. At the smallest published GPT-2 configuration it holds 33.7% of the parameters, falling to 5.3% at the largest. An untrained one knows nothing: mean absolute cosine similarity 0.1003 against the 0.0997 that vectors with no structure produce.

**6. Position.** Attention is order-blind, measured at 1.041e-17, so two orderings of the same tokens are the same input. Position gets injected from outside, and rotary embedding does it by rotating dimension pairs at geometrically spaced rates. Its relative-position identity is exact, 2.189e-12 across a 4,096-position sweep. Its decay property is a statistical tendency that is not even monotone: expected dependency at distance 1024 is 0.2629, higher than the 0.1854 at distance 512.

## The map, three weeks late

The very first Friday of this series was supposed to carry a map of the layers, and it never ran. Three weeks in, that is the thing most likely to be missing, so here it is. This is **our** organising scheme for the 100 weeks, not an industry standard.

```
  LAYER 6   Strategy, economics, org design
            what to build, what to buy, what it costs to run

  LAYER 5   MLOps, infrastructure, serving
            training clusters, deployment, cost, reliability

  LAYER 4   Evaluation and governance
            does it work, how do you know, who is accountable

  LAYER 3   Agentic development environments
            the tools around the loop: IDEs, sandboxes, review

  LAYER 2   The agent stack
            harnesses, loops, graphs, tools, memory, retrieval

  LAYER 1   Model lifecycle
            pretraining, post-training, adaptation, distillation

  LAYER 0   Foundations
            distributed systems, caching, networking, storage,
            and the internals of the model itself
```

The argument the missing post was going to make, and which three weeks of writing has only made me more confident about: **almost everyone studies Layer 0 and Layer 6, and the failures happen in Layers 2 through 4.**

Layer 0 is table stakes and it is where the tutorials are, so it gets studied. Layer 6 is where the interesting conversations are, so it gets talked about. Layers 2 through 4 are where an agent that demoed beautifully dies in production, and they are underserved because they are new, unglamorous, and hard to write tutorials about.

Weeks 1 and 2 were Layer 0, the systems half: consistent hashing, CAP, load balancing, CDNs, DNS, caching, eviction, stampedes. This week was Layer 0, the model half: attention, tokenization, embeddings, position. All of it is foundation, all of it is prerequisite, and none of it is where your agent will fail.

That is not a reason to skip it. It is the reason to get through it deliberately rather than indefinitely.

## Three questions, no lookups

Same shape as before: one recall, one application, one tradeoff. Everything you need is above.

**Question 1, recall.** A tokenizer is trained with byte-level BPE and a whitespace-only pre-token boundary, so merges may join letters to punctuation but never cross a space. Name the specific way its vocabulary gets wasted, give a concrete example of two tokens it would learn that one boundary rule would collapse into one, and say what the fix costs.

**Question 2, application.** You are handed a model checkpoint with no documentation. You compute the mean absolute cosine similarity between 300 randomly chosen rows of its token embedding table, at width 512, and get 0.0353. Should you be reassured or alarmed, and what exactly does that number tell you? Show the arithmetic you used to decide.

**Question 3, design tradeoff.** No single right answer, and that is the point.

You serve a RoPE-based model trained on 8k context. Product wants 32k. You have one engineer who can run a fine-tune, a four-week window, and an evaluation set of 200 hand-labelled examples, none longer than 6k tokens.

Name the fact you would establish first. Then choose among fine-tuning with position interpolation, swapping to a scheme designed for extrapolation, chunking the input and keeping the 8k model, or shipping at 32k with no change and monitoring. Make your assumptions explicit, reject the other three under those assumptions, and name the condition that flips you.

I will note one thing about the third question, because it is the trap I would fall into: read the evaluation set description again before you answer.

Answers on Monday morning, at the top of the first post of week 4. That is a promise I have now broken once and do not intend to break twice.

Comment your take. I read every reply, and for question 3 the reasoning is the whole answer.

---

*This evening, 17:00: the weekend challenge. Ninety minutes, one file, and the smallest-looking decision in the transformer. Where you put the layer norm changes whether the residual stream grows fourfold with depth and which end of the stack your gradients pile up at, and you will measure both by hand because this repository has no autodiff.*
