# Week 3 · Fri 2026-09-11 · 09:00 · Long-form: The Mechanism We Skipped, and the Hole in It That Needs Filling Tonight

> Calendar row: consolidation. This slot's committed row is W3 Fri AM, 09:00
> (CSV row `46:3`), format contrarian take, topic rotary positional encodings.
> That row has been moved to this evening and merged with the 17:00 debate
> prompt. This morning instead discharges the two W3 Mon 2026-09-07 rows (CSV
> `38:3` concept deep-dive, `39:3` annotated diagram) that never reached
> readers. Editorial decision recorded 2026-09-09.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for the rows being
> discharged names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
>
> **Why this slot moved, in full, because it changes a published promise.**
> `posts/2026-09-06-sun-am-theme-kickoff.md` is pushed and tells readers
> "Monday: self-attention mechanics. The whole week rests here." Monday never
> published. Tuesday's multi-head post had to carry the single-head mechanism
> inline to stay readable, and Wednesday and Thursday both leaned on a
> foundation that no reader had been given. The same kickoff promises "Friday:
> rotary positional encodings, and an argument", with a contrarian take in the
> morning and a debate in the evening.
>
> Both promises are kept, not one at the expense of the other. The RoPE
> argument is a response to a gap in self-attention, so it needs the mechanism
> stated first. This morning states it and ends on exactly that gap; this
> evening runs the contrarian take and the debate together in one longer
> piece. No committed topic is dropped and no correction is owed.
>
> Committed calendar beats for the two Monday rows, all six present below.
> From `38:3`: define self-attention mechanics in two sentences, no jargon |
> walk the core mechanism step by step with one concrete example | state the
> one misconception that causes the most damage. From `39:3`: draw the
> components and the data flow between them | annotate the step where the
> interesting work happens | mark the failure point and say why it fails
> there.
> Committed CTA for `38:3`: "Save this for your next design review."
>
> **Not a reprint.** Tuesday 2026-09-08 already carried the single-head
> mechanism and the sqrt(d_k) argument, and this post does not repeat either
> at length. What is genuinely new here and appears nowhere else in the
> tracked sequence: the annotated diagram the `39:3` row asked for, and a
> measurement of order-blindness that Tuesday asserted in prose and never
> checked. Tuesday's exact words were "Shuffle the rows of the input and,
> absent a mask, the outputs shuffle identically". That sentence was published
> without evidence. This post supplies it.
>
> Artifact written for this post, committed here, and linked from the body:
> - `experiments/week-03/permutation_equivariance.py`, 333 lines, Python 3.8+
>   standard library only. Four claims, each asserted, exit code 0 with "All
>   assertions passed", under two seconds of runtime.
>
> Measured 2026-09-09 by `experiments/week-03/permutation_equivariance.py`,
> d_model 32, 4 heads, attention seed 42, embedding seed 42:
> - unmasked: largest gap between attention(Px) and P attention(x) is
>   1.041e-17, which is 1.543e-15 of the mean output magnitude
> - with a causal mask: the gap is 8.216e-02, which is 7.409 times the mean
>   output magnitude, and the outputs are no longer the same multiset of rows
> - token rows only, two orderings of the same 11 ids: same multiset of output
>   rows, True
> - token rows plus position rows: same multiset, False, gap 4.842e-05, which
>   is 7.179e-03 of the mean output magnitude
> - determinism confirmed: two runs, identical md5 of stdout,
>   da5e41c82094fe585cf9759c0420272e
>
> Non-repository sources, permitted under the canonical source rule:
> - Vaswani et al., "Attention Is All You Need", arXiv:1706.03762. Quoted: the
>   scaled dot-product motivation with its hedge "we suspect", and Table 1's
>   self-attention row, O(n^2 * d) complexity per layer with O(1) sequential
>   operations and O(1) maximum path length, against O(n) for both in a
>   recurrent layer.
>
> Adversarial review record (2026-09-09, prepared two days ahead):
> - The mask result is reported as measured and is NOT presented as the mask
>   making the model order-aware. The distinction between constraining who may
>   be looked at and knowing where the looker sits is stated in the body ✓
> - The position-embedding effect is 0.7% of output magnitude, which is small,
>   and the body says so rather than implying position dominates at
>   initialisation. It is contrasted against the unmasked case's 1e-15, which
>   is the honest comparison ✓
> - Nothing is trained, and the body repeats that where it matters ✓
> - The diagram is ASCII in a fenced block so it survives any renderer, and
>   every element in it maps to a named function in `lib/attention.py` ✓
> - No claim that this post's material is new to the week where it is not.
>   The overlap with Tuesday is stated in the opening ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,670 words, measured 2026-09-09 by whitespace split
>   over everything below the `---` marker. Within the committed 2,500 to
>   3,500-word 09:00 range ✓
> - Zero em dashes.

---

**Topic:** The self-attention mechanism drawn in full, and the measurement proving it has no idea what order your words are in

**Subtitle:** This is the post that should have run on Monday. It ends on a hole big enough that the entire evening is about how to fill it, and the hole is not a bug.

Good morning.

Owed you this one. It should have arrived on Monday, the kickoff said the whole week rested on it, and it did not run. Tuesday carried enough of the mechanism inline to stay standing, but "enough to stay standing" is not the same as the thing itself, and three days of posts have now been built on a foundation nobody was shown.

This morning is therefore the foundation, drawn properly, plus the piece nobody has seen anywhere: the diagram, and a measurement of the mechanism's single largest blind spot. That blind spot is the reason this evening exists, which makes this the setup rather than a detour to catch up.

If you read Tuesday, you have met some of the first half. Skim it and slow down at the diagram.

## Two sentences, no jargon

Here is the whole thing.

**Self-attention lets every position in a sequence look at every other position and pull in a weighted mixture of what it finds. The weights are computed from the content of the positions themselves, so what gets looked at is decided by the data rather than fixed in advance.**

That is it. Everything below is those two sentences at higher resolution.

The reason it was a big deal is worth one paragraph, because it makes the design choices legible instead of arbitrary. Before this, sequence models passed information along a chain: to get something from position 3 to position 30,000, it had to be carried through every position in between, surviving each handoff. Vaswani et al.'s Table 1 puts the difference in one row. Self-attention has a maximum path length of O(1) between any two positions and needs O(1) sequential operations, against O(n) for both in a recurrent layer.

O(1) path length means position 3 and position 30,000 are one step apart. One step, at any distance in the sequence.

The bill for that arrives in the same table: O(n squared times d) work per layer. You replaced a relay race with a room where everyone can address everyone directly, and a room like that grows with the square of the number of people in it. Every long-context technique you have ever heard of exists because of that trade.

## The mechanism, one step at a time

Start with the data, because the shape of it explains most of the rest.

A sequence of n positions is a table with n rows. Each row is a list of d_model numbers describing that position. For a language model, one row is roughly "everything the model currently believes about this one token". Nothing more mystical than that.

Now, the same input row gets projected three times, into three different spaces, by three different learned matrices. That sounds like machinery for its own sake. The reason is human. Ask three questions about a word in a sentence:

- What am I looking for? That is the **query**.
- What do I offer, if somebody is looking? That is the **key**.
- If somebody does choose me, what do they actually receive? That is the **value**.

These are genuinely different questions and nothing forces one set of numbers to answer all three. A word can be a poor match for what you are hunting and still carry exactly the payload you need once you have found it. Splitting into query, key and value is just refusing to pretend those are the same thing.

With the three projections in hand, four steps:

1. **Compare** every query against every key by dot product. High number means good match. This produces an n by n table of scores.
2. **Divide** every score by the square root of the head's width.
3. **Softmax** each row, turning raw scores into weights that are all positive and sum to exactly 1.0.
4. **Average** the value rows using those weights. That average is the output for that position.

Step 2 is the one that gets a half-sentence in most explanations and deserves better. The scores in step 1 are dot products over d_k terms, and a sum of d_k independent products has variance d_k exactly, as an identity rather than an approximation. The scores therefore spread out as heads get wider, and wide enough scores push softmax into a corner where one weight is nearly 1 and the rest are nearly 0. The paper is admirably careful about its confidence here, writing that it suspects that for large values of d_k the dot products grow large in magnitude, pushing softmax into regions with extremely small gradients. That hedge is in the original and I am keeping it. Tuesday measured the arithmetic half and found variance over d_k pinned between 0.984 and 1.011 across a 64-fold range of widths.

## The diagram

The `39:3` row asked for the components, the data flow, the step where the interesting work happens, and the failure point. Here they are. This is ASCII so it survives any renderer, and every box maps to a real function in [`lib/attention.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/attention.py).

```
   INPUT  x : (n, d_model)          one row per position
     |
     |  the SAME rows go three ways. this is the whole
     |  "three different questions" idea, made concrete
     |
     +----------------+----------------+
     |                |                |
   x @ W_q          x @ W_k          x @ W_v
     |                |                |
     v                v                v
  Q (n,d_k)        K (n,d_k)        V (n,d_v)
     |                |                |
     +------> Q @ K^T <-----+          |
              |                        |
              v                        |
      scores (n, n)   <-- EVERY position scored against
              |           EVERY position. this is the
              |           n-squared term. it is the whole
              |           bill for the architecture
              |
              |  [STEP 2]  / sqrt(d_k)
              |     one division by a constant. leave it
              |     out and nothing raises, nothing NaNs,
              |     no shape check fails. the model just
              |     quietly stops learning
              v
      scaled scores (n, n)
              |
              |  [optional] + mask     0.0 allows, -inf forbids
              |                        exp(-inf) = 0, so a forbidden
              |                        weight is exactly 0, not small
              v
              |  [STEP 3]  softmax, row by row
              |
              v
      weights (n, n)  <== THIS IS WHERE THE WORK HAPPENS
              |            each row is a probability distribution.
              |            it sums to exactly 1.0, which means each
              |            position has ONE UNIT of attention to
              |            spend and spending it here is not
              |            spending it there
              |
              +-------> weights @ V
                            |
                            v
                     OUTPUT (n, d_v)


   *** THE FAILURE POINT ***

   Nothing in the diagram above reads a position index.
   Not one box. Permute the rows of x and every box
   produces the same values in permuted order, so the
   OUTPUT is permuted the same way and is otherwise
   unchanged.

   "the cache expired before the request arrived"
   "arrived request the before expired cache the"

   Same bag of rows in. Same bag of rows out.
```

## The step where the interesting work happens

The `weights` box, and specifically the fact that each row sums to 1.0.

Softmax is there because you cannot take a weighted average with weights that do not sum to one; the output would drift in magnitude depending on how many things you looked at. The constraint is therefore load-bearing and not negotiable.

It is also, unavoidably, a budget. Each position gets exactly one unit of attention, and every unit spent on one place is a unit not spent on another. When a model does something inexplicable with a long input, when it fixates on one part of a document and appears blind to another, the shape of the explanation is very often that something had one unit to spend and spent it somewhere you did not expect. That is a constraint doing exactly what it says on the tin.

The mask deserves its half-sentence too, because the implementation detail is the explanation. A causal mask is not an `if` statement. It is a matrix you **add** to the scores, holding 0.0 where attending is allowed and negative infinity where it is not. After exponentiation, `exp(-inf)` is exactly 0.0, so a forbidden position receives weight exactly zero rather than a small number that might leak. The mask is arithmetic, which is why it costs nothing and vectorises perfectly.

## The misconception that causes the most damage

There are several available. The one that costs the most, in my experience of watching people reason about these systems, is this:

**That attention weights tell you what the model is using.**

They do not. They tell you what the model is mixing, which is a different claim, and the gap between the two is where a great deal of confident nonsense lives.

Three reasons the gap is real. The weights describe one head in one layer, and a model has dozens of layers each with several heads, so any single map is one slice of a very deep stack. The weights multiply the **values**, so a position with a large weight and a small value vector contributes less than a position with a modest weight and a large one; the weight alone does not tell you the size of the contribution. Residual connections then route information around the attention computation entirely, so a position can matter enormously to the final answer while attention barely looked at it.

The practical version: an attention heatmap is a picture of where the mixing happened, and it is genuinely useful for that. It is not a picture of the model's reasoning, it is not an explanation, and a diagram with helpfully labelled heads is showing you somebody's interpretation of a trained model rather than a property of the mechanism.

Save that one for the next time somebody puts an attention map on a slide as evidence.

## Now the hole, measured

Look at the diagram again. Not one box reads a position index. Query, key, value, scores, softmax, weighted sum, and at no point does anything ask "where am I".

Tuesday asserted the consequence in one sentence and gave you no evidence, which I should not have done, so here is the evidence. [`experiments/week-03/permutation_equivariance.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/permutation_equivariance.py) takes a real sentence through our own tokenizer, embeds it, runs it through real multi-head attention, then shuffles the input rows with a fixed permutation and runs it again.

```
UNMASKED: is attention permutation equivariant?
  sequence length          11
  permutation              (4, 0, 6, 2, 9, 1, 7, 3, 10, 5, 8)
  mean |output value|      0.006745   (the scale to read gaps against)
  largest gap between attention(P x) and P attention(x): 1.041e-17
  gap as a share of scale  1.543e-15
  same multiset of rows    True
```

Shuffling the input and then attending gives the same answer as attending and then shuffling, to 1.041e-17. Against a mean output magnitude of 0.006745 that is a relative gap of about 1.5 parts in a quadrillion, which is another way of writing zero.

The consequence, on real token ids:

```
TOKEN ROWS ONLY: two orderings of the same tokens
  ids in order             [116, 258, 427, 861, 522, 100, 663, 263, 410, 920, 881]
  ids shuffled             [522, 116, 663, 427, 920, 258, 263, 861, 881, 100, 410]
  same multiset of output rows: True
```

Two orderings of the same eleven tokens. Identical bag of outputs. To this mechanism they are the same input, and no amount of depth fixes it, because stacking a permutation-blind layer on a permutation-blind layer gives you a permutation-blind stack.

## The two ways out, and a result I did not expect

**The causal mask.** A decoder mask forbids attending to later positions, and it is itself indexed by position, so it does break the symmetry:

```
CAUSAL MASK: does forbidding the future restore order awareness?
  mean |output value|      0.011089
  largest gap between attention(P x) and P attention(x): 8.216e-02
  gap as a share of scale  7.409e+00
  same multiset of rows    False
```

That gap is 7.4 times the mean output magnitude. Enormous.

Be careful with what it means, though, because this is the point where it is easy to overclaim. The mask constrains **who** each position may look at. It does not tell a position **where it sits** among the places it is allowed to look. It is real positional information, and it is the reason a decoder-only model is not completely lost without anything else, and it is not the same thing as knowing you are the fourth word.

**Position embedding**, which Thursday built. Add a row for where the token is to the row for what the token is, before attention runs at all:

```
TOKEN ROWS PLUS POSITION ROWS: the same two orderings
  same multiset of output rows: False
  mean |output value|      0.006745
  largest gap after undoing the shuffle: 4.842e-05
  gap as a share of scale  7.179e-03
```

The collision is gone. The two orderings are now distinguishable.

Here is the bit I did not expect and am not going to bury. The position effect is **0.7% of the output magnitude**, while the causal mask's was **740%**. At initialisation, on this toy, the mask changes the computation about a thousand times more than the position table does.

I want to be careful about what that is and is not evidence for. Nothing here is trained: the position table is a fresh seeded initialisation with a standard deviation of 0.02, and training is exactly the process that would make those rows matter. This is therefore a measurement of the starting point rather than a verdict that position embeddings are useless, and the honest reading is that at initialisation a decoder gets far more of its order information from the mask than from the position table, and the table has to earn its influence.

The comparison that settles the argument puts 0.7% against **1.5e-15**, which matters far more than 0.7% against 740%. Position moved the output by twelve orders of magnitude more than numerical noise. The symmetry is broken. Everything after that is a question of degree, and degree is what training is for.

## What to take into the evening

Two things.

**One.** Attention is a room where everyone can address everyone, everyone has exactly one unit of attention to spend, and nobody knows where they are standing. The first part is why it won. The second is why long inputs behave strangely. The third is the hole.

**Two, and this is the one for your next design review.** Notice how much of this mechanism is a consequence rather than a choice. The n-squared cost is a consequence of everyone addressing everyone. The budget is a consequence of needing weights that sum to one. The order-blindness is a consequence of computing weights purely from content. Nobody sat down and decided the model should not know word order. It fell out, and then somebody had to go and put position back in from outside.

That is the normal shape of an engineering artifact, and it is worth recognising, because when you meet a system property that seems obviously wrong, the useful question is usually not "why did they choose that" but "what is this the price of".

Tonight, what we do about the hole. Position has to be injected from outside, there is more than one way to do it, and the currently fashionable answer has a set of claims attached to it that are repeated far more confidently than the paper that introduced them ever put it.

Save this for your next design review.

---

*This evening, 17:00, running long: the contrarian take and the debate together. Rotary position embedding makes two promises that are exact algebra and one that is a statistical tendency, and the third one is the one everybody quotes. I implemented it, measured all three, and found three specific distances where moving tokens further apart increases the expected dependency between them.*

*Tomorrow, 09:00: the week 3 recap and quiz, plus the answers to the three questions from Saturday 09-05 that were promised for Monday and never arrived.*
