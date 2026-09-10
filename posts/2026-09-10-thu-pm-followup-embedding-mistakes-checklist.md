# Week 3 · Thu 2026-09-10 · 17:00 · Follow-up: Five Checks Before You Trust Your Embedding Layer

> Calendar row: W3 Thu PM, 17:00 (CSV row `45:3`). Format: common mistakes
> checklist. Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body.
>
> Committed calendar beats, all three present below: five yes/no checks
> phrased so "no" means stop and fix, targeting mistakes made from first
> principles | for each, the symptom you will see in production if it is
> skipped | make it screenshot-able as a single card.
> Committed CTA: "Follow along - this series runs all week."
>
> Sources verified 2026-09-09, the day this post was prepared (same fetch as
> the tutorial that runs this morning):
> - Radford et al., "Language Models are Unsupervised Multitask Learners"
>   (GPT-2), PDF fetched and text-extracted 2026-09-09. Check 1 uses the
>   published vocabulary 50,257 against the byte-level base of 256 stated in
>   section 2.2. Check 2 uses the context size, raised "from 512 to 1024
>   tokens". Check 4 uses Table 2's 117M/768 and 1542M/1600 rows.
> - Measured figures in checks 3, 4 and 5 are from
>   `experiments/week-03/embedding_lab.py`, run 2026-09-09, all assertions
>   passing, stdout md5 36c23c8fab0535cbf8b49e3454e526e7, figures identical to
>   the morning post: 33.7% and 5.3% share, mean absolute cosine 0.1003
>   against a predicted 0.0997, and the two nearest neighbours at seeds 42
>   and 43.
> - Check 1's off-by-one arithmetic is from `lib/embedding.py`'s own range
>   guard, whose message is quoted verbatim.
>
> **Standing rule, not yet discharged.** `prep/README.md` requires the script
> to be re-run on posting day. This post was written on 2026-09-09 for a
> 2026-09-10 slot, so that re-run is outstanding. The md5 above is the
> expected value; a different one means these figures are stale.
>
> Adversarial review record (2026-09-09, prepared a day ahead):
> - Every check is answerable today from a config file, a metrics page or one
>   line of Python. None requires retraining anything ✓
> - Check 4 is arithmetic on published columns and is labelled as arithmetic.
>   The published totals are rounded and the check does not claim more
>   precision than they have ✓
> - Check 5 states what untrained embeddings do not do and makes no claim
>   about what trained ones do ✓
> - No vendor-specific configuration key is quoted, because no first-party
>   vendor documentation was fetched for this slot. The checks are framed
>   against the mechanism instead, which is what the committed beat asks for ✓
> - No external code repository is named, linked, or implied ✓
> - Word count: 1,537 words in the reader-facing body below the editorial `---`
>   marker ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-10-thu-am-tutorial-embedding-layers.md`.
> This follow-up assumes the parameter-share table and the cosine measurement
> and does not re-derive them.

---

**Topic:** Five verifiable checks on an embedding layer, each with the production symptom you get for skipping it

**Subtitle:** Including the one where the vocabulary size in your config and the vocabulary size your tokenizer actually emits are two different numbers, and nothing tells you until a rare input arrives.

Good evening. This morning we built an embedding layer and found that a third of a small model is a lookup table, and that a fresh one thinks the nearest neighbour of the word "cache" is a backtick.

Useful things to know. Slightly awkward things to act on, though, because most of us are not going to re-derive that against our own stack this week.

So here is the shorter version: five questions you can answer today, from a config file, a metrics page, and about one line of Python. Every one is phrased so that **"no" means stop and fix**.

**1. Does the vocabulary size your table was built with equal the vocabulary size your tokenizer actually emits?**

These come from different places and drift apart quietly. The tokenizer's size is whatever training produced, plus every special token added afterwards: padding, end of sequence, a chat template's role markers, the four sentinels somebody added last quarter for a feature that shipped. The table's size is a number in a config.

Byte-level BPE makes this worse rather than better, and it is worth understanding why. There is no unknown token, ever. Any string encodes to bytes and every byte is in the base vocabulary of 256, so the tokenizer never signals that something was out of range. It cannot. That safety property is real, and it means the only thing standing between you and an out-of-range id is that the two numbers agree.

The check is one line: encode something, take the maximum id, compare it to your table's row count. Or read the guard we wrote this morning, which names both numbers when it fires:

*Symptom:* an index error, or on a GPU a device-side assert with no useful stack, on an input shape you cannot reproduce locally. It fires on whichever request happens to contain the rare token, which means it looks like an intermittent infrastructure fault for as long as you are willing to believe that. Worse if your lookup does not range-check: id -1 becomes the last row of your vocabulary in ordinary Python indexing, and you get a perfectly plausible vector for an impossible token, forever, silently.

**2. Is your position table at least as long as your longest real input, and do you know what happens when it is not?**

Absolute position embedding has a hard wall at `max_positions`. Past it there is no row to add. That is not a soft limit that degrades, it is an operation with no defined result, and every implementation resolves it somehow: raising, truncating, or wrapping.

The two published GPT-2 numbers make the shape of this concrete. The context was raised from 512 to 1,024 tokens, and that is a table size, not a preference. Your model's context length and the height of this table are the same fact seen from two directions.

The question is not really "is it long enough". It is "which of the three behaviours did I get, and did I choose it". Truncation is the dangerous one, because it succeeds.

*Symptom:* quality that falls off a cliff at a length nobody documented, on the longest documents only, with no error anywhere. The model appears to ignore the end of long inputs because it never received the end of long inputs. Everything looks healthy: latency normal, error rate zero, and the only signal is a support ticket saying the summary missed the last section.

**3. Have you measured your embedding table's share of your parameter budget, rather than assuming it is small?**

This morning's arithmetic on published columns: at the 117M configuration, vocabulary 50,257 and width 768, the tables hold 39,383,808 parameters, which is **33.7%** of the model. At the 1542M configuration, width 1600, the same tables are **5.3%**.

Two conclusions, and the second is the one that gets missed. At small widths the table is a major architectural component competing with depth for the same budget. And the share is not a constant, it falls the whole way along the size curve, because the table grows linearly in width while the blocks grow quadratically. So the answer to "how much does vocabulary cost me" depends entirely on where you are, and advice inherited from a larger model does not transfer down.

*Symptom:* you add parameters expecting capacity and get very little, because most of what you added went into rows for tokens that appear a handful of times in your corpus. Or the reverse, and more common: you shrink the model to fit a memory budget by cutting layers, the thing you were actually measuring barely moves, and the table you never considered is still sitting there holding a third of the weights.

**4. If you tied your input and output embeddings, does your parameter count know?**

Tying reuses the transposed token table as the output projection. The saving is exactly vocabulary times width, which at 50,257 by 768 is another 38,597,376 parameters not held.

The failure here is arithmetic rather than runtime, and it goes both ways. Counting the vocabulary matrix twice in a memory estimate makes you provision for a model larger than the one you have. Counting it once when it is not tied makes you provision for one smaller. Either way the number you planned with is wrong by tens of millions of parameters, and neither version fails at startup.

There is also a wiring failure worth one test. A transposed tie produces logits of exactly the right shape, full of plausible numbers, and trains to something. The cheapest thing that catches it: feed the embedding row for token *k* into the output projection and check the highest score is token *k*. If tying is the right way round it must be. If it is not, it will not be, and nothing else will tell you.

*Symptom:* for the arithmetic version, a capacity plan that is wrong by tens of millions of parameters and a deploy that either does not fit or wastes what it reserved. For the wiring version, a model that trains, produces syntactically fine output, and never gets as good as it should, with no error at any point.

**5. Can you name the training run that put meaning into the embeddings you are reading?**

This is the one I would put first if the numbers did not need the other four to make sense.

An untrained table has no structure. Not "less structure", none. Measured this morning over 44,850 pairs at width 64: mean absolute cosine similarity **0.1003**, against **0.0997**, which is what vectors with no structure whatsoever produce, sqrt(2 / (pi * d)). The two words `' cache'` and `' database'`, from a corpus entirely about caching and databases, scored **+0.0063**, while 95% of arbitrary pairs scored higher.

And the demonstration that should end the argument: at seed 42 the nearest neighbour of `' cache'` in the whole vocabulary is a backtick. At seed 43 it is `' ed'`. One integer changed. Nothing else.

Randomly initialised embeddings turn up in more places than anybody admits. A frozen table in a pipeline nobody fine-tuned. A component swapped during debugging and never swapped back. A loading path that failed silently and initialised fresh, which is the worst one, because it looks exactly like success.

If the honest answer is "I do not know which run trained this table", that is a **no**.

*Symptom:* a similarity feature that ships and performs at chance while looking sophisticated. Nearest-neighbour output that is easy to build a story around, because human beings can build a story around anything. And the quiet version: a model that trains far slower than it should, from a table that was supposed to arrive pretrained and did not.

## What is model-specific and what is not

Checks 1 and 2 sound like they belong to a particular tokenizer and a particular context length. They do not. Underneath, they are:

- Do the two numbers that must agree actually agree, and does anything check?
- Does my hard limit fail loudly, or does it succeed and lose data?
- Am I reading structure out of something whose training I cannot account for?

Ask those of an embedding layer, of a feature store's vector column, of a cache key namespace, of any lookup table that something else populates. The config key changes. The mistake does not.

And if you take one line from today, take this morning's. **An embedding table is the emptiest component in the model and the most expensive one to size wrong, and it will never tell you that you got it wrong.** These five checks are just the ways of asking it anyway.

Follow along, this series runs all week.

---

*Tomorrow, 09:00: a contrarian take. The standard advice on rotary positional encodings optimizes for the demo rather than the system you actually run, and the plain learned table from check 2 is the baseline it has to beat.*
