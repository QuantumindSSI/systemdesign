# Week 3 · Fri 2026-09-11 · 17:00 · Follow-up: Two of RoPE's Three Promises Are Algebra, and Everybody Quotes the Third

> Calendar row: consolidation of two committed rows. W3 Fri AM, 09:00 (CSV row
> `46:3`, contrarian take) and W3 Fri PM, 17:00 (CSV row `47:3`, debate
> prompt), merged into one longer evening piece. The morning slot was
> reassigned to discharge the two Monday 2026-09-07 rows that never reached
> readers; both committed Friday topics survive here intact. Editorial
> decision recorded 2026-09-09.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for both rows names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every line of code below was
> written in this repository.
>
> Committed calendar beats, all six present below. From `46:3`: state the
> conventional wisdom fairly, steelman it in two lines | show the specific
> context where it fails and the evidence | give the replacement heuristic and
> its own limits. From `47:3`: present position A with its strongest
> supporting scenario, argued from first principles | present position B with
> its strongest supporting scenario | ask readers to reply with their context,
> team size, scale, stakes.
> Committed CTAs: "Comment your take - I read every reply." (`46:3`) and
> "Bookmark this; you will need it at 3am someday." (`47:3`). Both appear.
>
> Artifacts written for this post, committed here, and linked from the body:
> - `lib/rope.py`, 198 lines, Python 3.8+ standard library only. Rotary
>   position embedding with no parameters at all: given the head width and the
>   base, every angle is determined.
> - `tests/test_rope.py`, 27 tests, including two that encode the contrarian
>   claim directly, `test_energy_in_the_slowest_pair_barely_decays` and
>   `test_energy_in_the_fastest_pair_swings_wildly`.
> - `experiments/week-03/rope_properties.py`, 398 lines. Six claims, each
>   asserted, exit code 0 with "All assertions passed", about eight seconds.
> Whole suite after these: 270 tests, all passing.
>
> Verification performed 2026-09-09, the day this post was prepared:
> - Script run to completion, exit code 0, "All assertions passed" printed.
> - Determinism confirmed by running twice and comparing an md5 of stdout:
>   identical, dd346762e3ace54bbf078fec78ad67e5.
> - Every number quoted in the prose is copied from that stdout.
>
> **A claim the assertions killed before publication.** The script originally
> asserted that averaged self-similarity at distance 512 would be below 0.10.
> It measured 0.1854 and failed. Investigating the failure produced the better
> result: the expectation over standard normal vectors has a closed form, the
> mean over pairs of cos(distance * theta_i), and the sampled average tracks it
> to within 0.004. The claim was rewritten against the closed form, which is
> what made the non-monotonicity visible, and that is now the strongest thing
> in the post. The original threshold was an assumption dressed as a
> prediction.
>
> **Standing rule, not yet discharged.** `prep/README.md` requires every
> script re-run on posting day. Prepared 2026-09-09 for a 2026-09-11 slot, so
> that re-run is outstanding. The md5 above is the expected value.
>
> Non-repository sources, permitted under the canonical source rule, all
> fetched and read 2026-09-09:
> - Su, Lu, Pan, Murtadha, Wen and Liu, "RoFormer", arXiv:2104.09864v5.
>   Quoted verbatim: RoPE "encodes the absolute position with a rotation
>   matrix and meanwhile incorporates the explicit relative position
>   dependency in self-attention formulation", and the three properties, "the
>   flexibility of sequence length, decaying inter-token dependency with
>   increasing relative distances, and the capability of equipping the linear
>   self-attention with relative position encoding".
> - Press, Smith and Lewis, "Train Short, Test Long", arXiv:2108.12409v2.
>   Quoted verbatim: "how does a model achieve extrapolation at inference time
>   for sequences that are longer than it saw during training?", and "we find
>   that current methods do not allow for efficient extrapolation". Also the
>   1.3B model trained at length 1024 extrapolating to 2048 at the same
>   perplexity as a sinusoidal model trained at 2048, "training 11% faster and
>   using 11% less memory".
> - Chen, Wong, Chen and Tian, "Extending Context Window of Large Language
>   Models via Positional Interpolation", arXiv:2306.15595v2. Quoted verbatim:
>   interpolation is used "rather than extrapolating beyond the trained
>   context length which may lead to catastrophically high attention scores
>   that completely ruin the self-attention mechanism", and "the upper bound
>   of interpolation is at least ~600x smaller than that of extrapolation".
>   Also: RoPE-based models extended "to up to 32768 with minimal fine-tuning
>   (within 1000 steps)".
>
> Adversarial review record (2026-09-09, prepared two days ahead):
> - The steelman is genuinely a steelman. Two of the paper's three properties
>   are confirmed exact by our own measurement and the body leads with that
>   before criticising anything ✓
> - The criticism is aimed at how the third property is repeated, not at the
>   paper. Su et al. say "decaying inter-token dependency with increasing
>   relative distances" and the body quotes them precisely rather than
>   attacking a stronger claim they did not make ✓
> - The closed form is derived in the artifact's docstring and validated
>   against 4,000 samples before being used. It is not asserted ✓
> - The non-monotone distances are a property of the closed form, which has no
>   randomness in it, so they are not a sampling artifact. Stated ✓
> - Nothing here is trained. The slowest-pair counterexample is described as a
>   vector a model is FREE to learn, never as one that models do learn, since
>   this repository has no trained model to check ✓
> - Press et al. is from 2021 and Chen et al. from 2023. Neither is presented
>   as the current state of the art in context extension, and the body says
>   the field moved on ✓
> - Both debate positions are argued at their strongest. Position B is not a
>   strawman: it gets the KV-cache argument, which is the strongest practical
>   case for RoPE and is one our own measurement confirms ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,782 words, measured 2026-09-09 by whitespace split
>   over everything below the `---` marker ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-11-fri-am-essay-self-attention-foundations.md`
> is this morning's mechanism post and its order-blindness measurement. This
> follow-up assumes both and does not re-derive them.

---

**Topic:** What rotary position embedding actually guarantees, what it only tends to do, and why the difference decides whether your long-context plan works

**Subtitle:** Two of its three advertised properties are exact algebra that I verified to twelve decimal places. The third is a statistical tendency that is not even monotone, and it is the one the folklore is built on.

Good evening.

This morning ended on a hole. Attention has no idea what order anything is in, measured at 1.5 parts in a quadrillion, and something has to put position back in from outside.

Rotary position embedding is the currently fashionable answer, and it is a genuinely lovely piece of work. It is also surrounded by a layer of received wisdom that is considerably more confident than the paper it came from, and separating those two things is worth an evening.

I want to be straight about the shape of this piece. Tonight is the contrarian take and the debate together, because the calendar's Friday morning slot went to the mechanism that should have run on Monday. Nothing has been dropped; it is all here, and it runs long.

## What it does, in one paragraph

Take a vector of even width and read it as a list of two-dimensional pairs. Dimensions 0 and 1 are one pair, 2 and 3 the next, and so on. Each pair is a point on a plane, and a point on a plane can be rotated. RoPE rotates pair *i* by an angle proportional to the position, with a per-pair rate that falls off geometrically:

```
    theta_i = base ** (-2i / d)        base is usually 10000
    angle for pair i at position m = m * theta_i
```

Pair 0 turns fast, a full revolution every few positions. The last pair turns so slowly it barely moves across an entire context. The fast pairs therefore carry fine local offset and the slow pairs carry coarse absolute location, and one vector holds both.

It is applied to the queries and the keys, never to the values, because the point is to make the **score** position-aware rather than to rewrite what a position contributes once it has been chosen.

The implementation is [`lib/rope.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/rope.py) and it has **no parameters at all**. Given the head width and the base, every angle is determined. That is unusual enough to be worth a second: a positional scheme that learns nothing.

## The steelman

Here is the conventional wisdom, stated as strongly and as fairly as I can.

**RoPE gives you relative position for free. The score between two tokens depends only on how far apart they are, so the same learned behaviour works anywhere in the sequence, which means the model is not tied to the lengths it saw in training and long context becomes a matter of turning the number up.**

That is the version you meet in practice, and the first sentence of it is completely true. The paper's own framing is precise and modest: RoPE "encodes the absolute position with a rotation matrix and meanwhile incorporates the explicit relative position dependency in self-attention formulation", and it lists three properties, "the flexibility of sequence length, decaying inter-token dependency with increasing relative distances, and the capability of equipping the linear self-attention with relative position encoding" (arXiv:2104.09864).

Three properties. They are not the same kind of claim, and that turns out to be the whole argument.

## Two of them are exact, and I checked

Not going to criticise something before establishing what is genuinely true about it. Everything below is from [`experiments/week-03/rope_properties.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/rope_properties.py).

**The relative-position identity holds, exactly.** For any query, any key, any two positions, the score depends only on the difference. Four thousand random pairs, six offsets ranging over four thousand positions, six distances:

```
PROPERTY 1: does the score depend only on the distance?
  4000 random query/key pairs, width 64, seed 42
  offsets tested           (0, 1, 17, 256, 1024, 4096)
  distances tested         (0, 1, 2, 9, 64, 512)
  largest violation        2.189e-12
```

2.189e-12 is floating point noise from evaluating thirty two sines and cosines. This is not approximately true or true on average. It is algebra, and it holds at position 4,096 exactly as well as at position 1.

**Rotation preserves length, exactly.** RoPE cannot amplify or attenuate anything, ever:

```
PROPERTY 2: does rotation change any vector's length?
  largest relative change  7.827e-16
```

**And shifting a whole window changes nothing inside it.** This is the property that pays rent every single day in production:

```
PROPERTY 3: does moving the window move the scores inside it?
  window of 6, shifted by 4096 positions
  largest score change     1.640e-12
```

That is what makes a KV cache work. A key computed and cached thousands of tokens ago keeps its correct relationship to a query that arrives much later, with no recomputation. If you have ever wondered why RoPE won on engineering grounds rather than benchmark grounds, this is a large part of the answer, and it deserves to be said clearly before anything critical.

So: two exact properties and one enormous practical benefit, all confirmed. That is the steelman, and it is strong.

## The third one is a different kind of claim

"Decaying inter-token dependency with increasing relative distances."

The folklore turns this into "attention naturally falls off with distance, so the mechanism degrades gracefully at long range". Let me measure it.

Self-similarity, meaning the score of a vector against itself at some distance, normalised by its value at distance zero. Averaged over 4,000 random vectors of width 64.

While measuring it I found that the expectation has a closed form. For a standard normal vector, every pair carries the same expected share of the total energy, so the weights average out and what is left is just the unweighted mean of the cosines:

```
    E[self-similarity at distance d] = mean over pairs of cos(d * theta_i)
```

No randomness in it at all. Here it is beside the sampled average, which tracks it to within 0.004:

```
   distance   sampled  closed form  slowest pair  fastest pair
  ------------------------------------------------------------
          0    1.0000       1.0000        1.0000        1.0000
          1    0.9661       0.9662        1.0000        0.5403
          2    0.8843       0.8845        1.0000       -0.4161
          4    0.7472       0.7479        1.0000       -0.6536
          8    0.6987       0.7004        1.0000       -0.1455
         16    0.6042       0.6054        1.0000       -0.9577
         32    0.6102       0.6111        1.0000        0.8342
         64    0.4318       0.4346        1.0000        0.3919
        128    0.2804       0.2839        0.9999       -0.6929
        256    0.3494       0.3537        0.9994       -0.0398
        512    0.1820       0.1854        0.9977       -0.9968
       1024    0.2641       0.2629        0.9907        0.9874
       2048   -0.0401      -0.0397        0.9629        0.9497
```

Read the closed-form column downward. It trends down. The paper's property is real.

Now read it more carefully.

```
  where moving further apart RAISES the expected dependency:
    distance   16 to   32: +0.6054 rises to +0.6111
    distance  128 to  256: +0.2839 rises to +0.3537
    distance  512 to 1024: +0.1854 rises to +0.2629
```

**Expected dependency at distance 1024 is higher than at distance 512.** By a lot: 0.2629 against 0.1854, about forty percent more.

That is not sampling noise. The closed form has no randomness in it. It is a mean of cosines at geometrically spaced frequencies, which oscillates on its way down, and the oscillation is a permanent feature of the scheme rather than an artifact of anything.

The phrase "decaying inter-token dependency with increasing relative distances" is true as a trend over the whole range and false as a statement about any particular pair of distances. Su et al. wrote the careful version. The folklore uses the strong version, and the strong version is measurably wrong.

**And it is not a property of any individual vector either.** Look at the "slowest pair" column: a vector with all its energy in the slowest-rotating pair keeps 0.9977 of its self-similarity at distance 512, where the average has fallen to 0.1854. Five and a half times more.

```
  at distance 512:
    closed-form average    +0.1854
    slowest pair           +0.9977
    slowest pair rate      1.333521e-04 radians per position
    total turn over 512    0.0683 radians (3.91 degrees)
```

Over five hundred and twelve positions, that pair turns **3.91 degrees**. It has not moved.

Nothing about that vector is exotic. It is an ordinary point in the space, and there is nothing in the architecture, the initialisation or the loss that forbids a model from putting a query there. If a head wants to attend at long range regardless of distance, the slow pairs are exactly where it would learn to live.

I should be careful here, because this is where I could overclaim in the other direction. This repository has no trained model, so I cannot tell you that real heads do this. What I can tell you is that the decay is not a constraint. It is an average over vectors, and a trained model does not sample its queries at random.

## Where the advice fails, and the evidence

The practical form of the folklore is "RoPE handles long context, so just increase the number".

Press, Smith and Lewis asked the question directly in 2021 and answered it: "how does a model achieve extrapolation at inference time for sequences that are longer than it saw during training?" Their finding, before proposing their own alternative: "we find that current methods do not allow for efficient extrapolation" (arXiv:2108.12409). Rotary is among the current methods they measured.

Two years later, Chen, Wong, Chen and Tian went at the same problem from the other side and were blunter about what happens when you try. Their Position Interpolation work down-scales position indices to fit the original window "rather than extrapolating beyond the trained context length which may lead to catastrophically high attention scores that completely ruin the self-attention mechanism" (arXiv:2306.15595).

Catastrophically high attention scores that completely ruin the self-attention mechanism. That is not degradation. That is the thing not working.

They quantify the gap: "the upper bound of interpolation is at least ~600x smaller than that of extrapolation". The fix is also not free. Extending RoPE-based models to 32,768 required fine-tuning, which they emphasise is minimal, "within 1000 steps", but a thousand steps of fine-tuning is not what "just turn the number up" means to anybody.

Here is the thing to sit with. **The relative-position identity is exact at position 4,096, and I measured that at the top of this post. Models built on it nonetheless fail when you run them past their training length.** Both are true, and holding both is the entire skill.

The identity guarantees that the *arithmetic* is position-independent. It guarantees nothing whatsoever about whether the *learned weights* have ever encountered that arithmetic. A rotation of 8,000 positions is perfectly well defined and completely unfamiliar, and the model's response to it was fitted on things it saw. RoPE removes the mechanism's excuse for failing at long range. It does not do the learning.

## The replacement heuristic, and its own limits

Here is what I would put in place of the folklore.

**Treat RoPE as buying you position-invariant arithmetic and a working KV cache, and treat your usable context as an empirical property of your training run rather than a property of your position encoding.**

Concretely, three things follow. Your effective context is the length you trained on, until measured otherwise. If you want more, the honest options are training longer, interpolating with fine-tuning, or a scheme designed for extrapolation, and all three cost something. A "supports 128k context" line in a model card is a claim about what the code accepts, not about where quality holds; the number that matters is where your own evaluation falls off, on your own inputs.

Now the limits of my own heuristic, because a replacement rule with no stated limits is just new folklore.

It is conservative, and conservative advice has a cost. Models do often work somewhat past their training length, and treating the training length as a hard wall will make you spend money on fine-tuning you might not have needed. Measure before you conclude either way.

My measurement is untrained. Every number above describes the geometry of the scheme, not the behaviour of a fitted model, and the geometry is the floor rather than the outcome.

The papers are also from 2021 and 2023. Context extension has been an extremely active area since, and there are schemes now that do considerably better than what Press et al. measured. Do not read "current methods do not allow for efficient extrapolation" as a statement about 2026. Read it as the origin of a problem that a great deal of subsequent work exists to address, which is itself the strongest evidence that the problem was real.

## The debate

Two positions. I have argued both of these in real rooms and I am not going to pretend one is obviously correct.

**Position A: RoPE is the right default and the criticism is misplaced.**

The strongest scenario for A is the one our own measurement handed it. You are serving a model with a KV cache, which is to say you are serving a model. Keys are computed once and reused across thousands of subsequent queries. RoPE makes that correct by construction: shift the window by 4,096 positions and every score inside it changes by 1.640e-12. With learned absolute position embeddings, a cached key carries a specific absolute slot, and the moment you want to slide a window, or drop a prefix, or reuse a cached system prompt in a different position, you are recomputing or you are wrong.

Add that it has no parameters, that it composes with essentially any attention implementation, and that its cost is a handful of sines and cosines. Position A says: the extrapolation complaint is a complaint about training length wearing a costume, absolute embeddings do not extrapolate either, and you would not trade a working cache for a marginally better story about lengths you did not train on.

**Position B: RoPE is a local optimum that the field over-fitted to.**

The strongest scenario for B is a team that actually needs long inputs and does not have a pretraining budget. You have a model trained at 4k and documents that are 40k. Position B observes that Press et al. built ALiBi precisely because the existing methods, rotary included, did not extrapolate, and their 1.3B model trained at 1024 reached the same perplexity at 2048 as a sinusoidal model trained at 2048, while "training 11% faster and using 11% less memory". Getting extrapolation by biasing scores with a distance penalty, rather than by rotating vectors and hoping the decay works out, is a simpler mechanism that does the thing directly.

Position B's sharpest point is the one this post measured: RoPE's decay, the property most often cited as why it handles long range, is not monotone. Expected dependency at 1024 exceeds that at 512. A scheme whose distance behaviour oscillates is a strange foundation for reasoning about distance, and Position B argues we chose it for the cache and then invented the long-context justification afterwards.

**Where I actually land**, since a debate where the writer hides is not worth reading. I use Position A's answer and I hold Position B's objection. RoPE is what I would ship, the cache argument is decisive for anything serving real traffic, and I would not let anybody tell me the context window is a configuration value. The oscillating decay does not change my default; it changes how much I trust any claim about long-range behaviour that is not backed by an evaluation on the actual lengths.

## Now yours

Reply with your **context**, because that is what decides this and generic answers are worthless here.

**Team size**, because interpolation with fine-tuning needs somebody who can run and evaluate a fine-tune, and if that person does not exist then the honest option set is one item long.

**Scale**, because the KV-cache argument in Position A is close to decisive when you are serving real traffic and close to irrelevant when you are running batch jobs overnight.

**Stakes**, because "somewhat degraded at 20k" is fine for a summariser and unacceptable for anything where a missed clause is a legal problem.

If you have measured where your own quality actually falls off, against input length, on your own data: post the number. That number is worth more than this entire post, and almost nobody has it.

Comment your take. I read every reply.

Bookmark this, you will need it at 3am someday, probably the night somebody raises the context window in a config file and cannot work out why the evaluation got worse.

---

*Tomorrow, 09:00: the week 3 recap and quiz. Six mechanisms in a line each, three new questions, and the answers to the three from Saturday 09-05 that were promised for Monday morning and never arrived. I have not forgotten them.*
