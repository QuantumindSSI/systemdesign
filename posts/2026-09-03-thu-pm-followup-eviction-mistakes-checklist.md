# Week 2 · Thu 2026-09-03 · 17:00 · Follow-up: Five Checks Before You Trust Your Eviction Policy

> Calendar row: W2 Thu PM, 17:00 (CSV row `31:2`). Format: common mistakes
> checklist. Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: five yes/no checks
> phrased so "no" means stop and fix | for each, the symptom you will see in
> production if it is skipped | make it screenshot-able as a single card.
> Committed CTA: "Repost this so your team sees it."
>
> Sources verified 2026-09-03 (same fetch as this morning's tutorial):
> - Redis, "Key eviction" (redis.io/docs/latest/develop/reference/eviction/).
>   Check 1 quotes "The `volatile-xxx` policies behave like `noeviction` if no
>   keys have an associated expiration." Check 2 quotes the decay description
>   and the `lfu-decay-time` special value of 0 meaning never decay. Check 4
>   uses the documented `keyspace_hits` / `keyspace_misses` formula. Check 5
>   uses the documented `evicted_keys` and `expired_keys` diagnostic reasoning
>   and the `noeviction` error behavior.
> - Measured rows referenced in checks 2 and 3 are from
>   `experiments/week-02/cache_eviction_demo.py`, re-run today, all assertions
>   passing, figures identical to this morning's post.
>
> Adversarial review record (2026-09-03):
> - Every check is falsifiable by the reader against their own configuration
>   and metrics. No check depends on taking my word for anything ✓
> - The "90%" in the committed CSV hook is the calendar's marketing language
>   and is deliberately not repeated as a measured claim in the body. There is
>   no evidence for a 90% figure and inventing one would be fabrication ✓
> - Redis is named as the concrete example because its documentation is public
>   and quotable. The underlying checks are stated so they transfer to other
>   caches, and the post says which parts are Redis-specific ✓
> - No invented incident or postmortem. Symptoms are derived from the
>   documented mechanism or from the measured demo, and are phrased as what you
>   would observe, not as something that happened to someone ✓
> - **Publication-gap remediation (2026-09-04).** No post in this week's
>   sequence reached readers, so every backward reference to a sibling post
>   was a dangling reference to material nobody had seen. The body now
>   carries the referenced substance inline instead of pointing at it:
>   check 4's example expanded to explain what write-through is and why it
>   structurally cannot repopulate on a read, rather than citing 'yesterday'. Written so it reads as a reminder to a sequential reader and as
>   sufficient context to a cold one ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-03-thu-am-tutorial-cache-eviction.md`.
> This follow-up assumes the FIFO/LRU/LFU table and does not re-derive it.

---

**Topic:** Five verifiable checks on a cache eviction configuration, each with the production symptom you get for skipping it

**Subtitle:** Including the Redis setting that quietly turns eviction off completely while your dashboard shows a perfectly healthy cache.

Good evening. This morning we measured three eviction policies and found that the best one in two tests collapsed to 18.4% in the third.

That is a useful thing to know and a slightly uncomfortable one, because most of us are not going to rerun that experiment against production traffic this week. So here is the shorter version: five questions you can answer today, from a config file and a metrics page.

Every one is phrased so that **"no" means stop and fix**.

## The card

**1. If your policy starts with `volatile-`, do most of your keys actually have a TTL?**

This is the one that ruins evenings. Redis's documentation states it directly: the `volatile-xxx` policies behave like `noeviction` if no keys have an associated expiration.

Read that again. You configured `volatile-lru` believing you had chosen an eviction policy. If your keys have no TTL set, you have chosen **no eviction at all**.

*Symptom:* memory climbs to `maxmemory` and stays pinned there. Writes begin failing with out-of-memory errors while reads keep working perfectly, because `noeviction` rejects commands that add data and leaves reads alone. Your hit rate looks fine right up until the moment your application cannot write.

**2. If you are using LFU, is decay switched on?**

Redis approximates LFU with a probabilistic counter plus, in their words, "a decay period so that the counter is reduced over time ... so that the algorithm can adapt to a shift in the access pattern." The control is `lfu-decay-time`, defaulting to 1 minute, and a value of `0` means never decay.

*Symptom:* this morning's third row. Hit rate falls off a cliff after a deploy, a trending story, or a region failover, and does not recover on its own. Keys that were popular last week sit in your cache defended by history while the keys people want now are evicted on arrival. In our measurement that was 61.6% for LRU against 18.4% for undecayed LFU on identical traffic.

**3. Can you say, from data, whether anything walks your whole keyspace on a schedule?**

Nightly exports, analytics jobs, search crawlers, backfills, cache warmers. Each touches many keys exactly once.

*Symptom:* a recurring dip in hit rate on a timetable, usually overnight, usually attributed to "less traffic at night." An LRU-family cache treats every scanned key as the most recently used thing it owns, so a single pass can push your genuinely hot set toward eviction. In the demo this cost LRU 8.8 points while LFU lost only 9.9 from a much higher base.

If the honest answer is "I do not know what runs at 3am," that is a **no**.

**4. Is hit rate broken out per key class, or do you only have one number?**

Redis gives you `keyspace_hits` and `keyspace_misses` in `INFO stats`, and the ratio is `keyspace_hits / (keyspace_hits + keyspace_misses) * 100`. That is one number for your entire keyspace.

*Symptom:* the failure is invisible. Here is a measured example, from a simulation I ran yesterday comparing two ways of populating a cache. Under **write-through**, where entries only ever enter the cache on a write, a replaced cache node came back empty, and its hit rate on keys that were read but never rewritten was exactly **0.0%** over more than a thousand reads. Nothing was broken. Write-through simply has no mechanism by which a read can populate the cache, so a key nobody writes is a key that will never be cached again on that node. The aggregate hit rate over the same run still looked two points *better* than the alternative.

That is the shape to watch for. A total failure on a subset of keys can hide inside a healthy average, and it will hide there specifically for your low-traffic keys, which is exactly where your slowest requests already live.

**5. Have you compared `evicted_keys` against `expired_keys` before blaming the policy?**

Redis documents the diagnostic, and it is worth stealing regardless of what cache you run. If hits are lower than expected and `evicted_keys` is high, the wrong keys are probably being evicted, and the policy is the suspect. If `evicted_keys` is low but `expired_keys` is high, nothing is being evicted at all, your TTLs are simply too short, and changing the eviction policy will achieve nothing.

*Symptom:* a week spent tuning `maxmemory-policy` and `maxmemory-samples` on a problem that was a TTL the whole time. These two numbers tell you which conversation you are actually in, and they take thirty seconds to read.

## What is Redis-specific and what is not

Checks 1, 2 and 5 quote Redis configuration names, because Redis publishes its behavior clearly enough to quote. The questions underneath them are not Redis-specific at all:

- Does my eviction policy have a precondition I have not met?
- Does my frequency-based policy have a way to forget?
- Am I looking at eviction pressure or expiry pressure?

Ask those of Memcached, of a CDN's edge storage, of an in-process LRU in your own service. The config key changes. The mistake does not.

And if you take one line from today, take the one from this morning that made all five of these necessary. **Every eviction policy is a prediction about the future, and it is only as good as the assumption it encodes.** These five checks are just asking whether your system is still the kind of system your policy was predicting.

Repost this so your team sees it.

---

*Tomorrow, 09:00: a contrarian take. The standard advice on cache stampede protection optimizes for the demo, not the system you actually run, and there is a 2013 paper with the numbers to show it.*
