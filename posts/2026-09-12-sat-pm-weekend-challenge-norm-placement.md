# Week 3 · Sat 2026-09-12 · 17:00 · Weekend Challenge: Move One Function Call and Watch the Gradients Move

> Calendar row: W3 Sat PM, 17:00 (CSV row `49:3`). Format: weekend challenge.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every line of code below was
> written in this repository.
>
> Committed calendar beat: a weekend-sized exercise on pre-norm versus
> post-norm layer normalization, matching the topic promised in
> `posts/2026-09-06-sun-am-theme-kickoff.md`, which told readers "Saturday:
> pre-norm versus post-norm layer normalization. The week closes on the
> smallest-looking decision with the largest training consequences."
> Committed CTA: "Bookmark this; you will need it at 3am someday."
>
> Artifacts written for this post, committed in this repository:
> - `lib/layernorm.py`, 304 lines, Python 3.8+ standard library only, built on
>   `lib/linalg.py` and `lib/attention.py`. LayerNorm, a feed-forward
>   sublayer, and a TransformerBlock whose only configuration is a
>   `norm_first` boolean.
> - `tests/test_layernorm.py`, 29 tests, all passing.
> - `experiments/week-03/norm_placement.py`, 387 lines, seeds 42 and 7. Five
>   claims, each asserted, exit code 0 with "All assertions passed", about
>   four seconds.
> Whole suite after these: 270 tests, all passing.
>
> Verification performed 2026-09-09, the day this post was prepared:
> - Script run to completion, exit code 0, "All assertions passed" printed.
> - Determinism confirmed by running twice and comparing an md5 of stdout:
>   identical, 703197248266bafa4b5323f2d82fd4df.
> - Every number quoted in the prose is copied from that stdout.
>
> **Two methodological errors caught before publication, both recorded in the
> artifact's own docstrings because they are the most useful part of it.**
>
> First, a degenerate loss. The script originally used the mean squared VALUE
> of the stack's output, with no target. Under Post-LN the last operation is a
> LayerNorm, so every output row has mean 0 and variance 1 by construction and
> that loss is pinned at 1.0 regardless of any weight. Its gradient measured
> at 1e-5, which reads as a dramatic finding about Post-LN and is entirely a
> statement about the loss. Replaced with mean squared error against a fixed
> seeded target, which normalisation does not trivialise because it fixes each
> row's length but not its direction.
>
> Second, an invalid comparison. With the loss fixed, Post-LN's raw gradient
> norms came out roughly twenty times SMALLER than Pre-LN's, the opposite of
> the predicted direction. The reason is not a finding either: Pre-LN's
> residual stream is 4.264 times larger by the top of the stack, so its
> outputs sit further from the target and every gradient in it is larger for a
> reason unrelated to the pathology under discussion. The comparable quantity
> is the SHAPE of the gradient profile with depth, measured within each
> arrangement against its own mean. Measured that way the predicted direction
> does appear. The body leads with this rather than hiding it, and CLAIM 4 now
> asserts that the forward scales differ enough to forbid the raw comparison,
> so a future run where they happen to match cannot leave a stale caveat in
> the article.
>
> **Standing rule, not yet discharged.** Prepared 2026-09-09 for a 2026-09-12
> slot. `prep/README.md` requires a re-run on posting day; the md5 above is
> the expected value.
>
> Non-repository source, permitted under the canonical source rule:
> - Xiong, Yang, He, Zheng, Zheng, Xing, Zhang, Lan, Wang and Liu, "On Layer
>   Normalization in the Transformer Architecture", arXiv:2002.04745v2.
>   Abstract read 2026-09-06, re-read 2026-09-09. Quoted: with Post-LN "the
>   expected gradients of the parameters near the output layer are large", and
>   with Pre-LN "the gradients are well-behaved at initialization".
>
> Adversarial review record (2026-09-09, prepared three days ahead):
> - The scope limit is stated in the body, not only here. Six layers at width
>   8 with a finite-difference gradient and no training is not the regime a
>   mean field theory proof concerns, and the body says the honest question is
>   narrow: does anything move in the predicted direction on a toy ✓
> - Gradients are computed by central differences because this repository has
>   no autodiff, and the step is validated by halving it rather than assumed ✓
> - The raw gradient columns are printed AND labelled as not comparable, so a
>   reader who skims the table cannot take the wrong number from it ✓
> - The tilt statistic is defined before it is used, and it is a ratio of two
>   means from the same arrangement, which is what cancels the scale ✓
> - Xiong et al.'s claim is about gradients at initialization and is quoted
>   that way. No claim is made about final quality of either arrangement ✓
> - No external code repository is named, linked, or implied ✓
> - Word count: 1,701 words in the reader-facing body below the editorial
>   `---` marker ✓
> - Zero em dashes.

---

**Topic:** Building both layer-norm arrangements, then measuring the residual stream and the gradients by hand to see what moving one function call actually does

**Subtitle:** Ninety minutes, one file, no autodiff and no installs. You will watch one arrangement hold its residual stream at exactly 1.0 while the other grows fourfold, and find the gradients piling up at opposite ends of the stack.

Good evening.

We spent a week on the parts of a transformer that clearly matter: attention, tokenization, embeddings, position. This evening, ninety minutes on the part that looks like housekeeping.

There are two ways to arrange a transformer block. They differ by where one function call goes.

```
    POST-LN, the original    x -> LayerNorm(x + Sublayer(x))
    PRE-LN                   x -> x + Sublayer(LayerNorm(x))
```

That is the entire difference. In Post-LN the normalization sits **on** the residual path, so everything handed from one block to the next has been renormalised. In Pre-LN the residual path runs from input to output untouched and normalization happens only on the branch.

Xiong et al. analysed both with mean field theory and reported that at initialization, with Post-LN, "the expected gradients of the parameters near the output layer are large", which makes a large learning rate unstable and is the reason the original recipe needs a warm-up stage. With Pre-LN, "the gradients are well-behaved at initialization" (arXiv:2002.04745).

That is a claim about gradients, and we have no autodiff in this repository. We are going to compute them by hand.

## The end state

When you are done you will have run a file that:

- builds the **same six-block stack twice**, once in each arrangement, from one seed, so the weights are numerically identical and any difference is the arrangement
- measures the **residual stream size** at every depth in both
- measures the **gradient norm** of every block's attention output projection, by central finite differences on the forward pass
- **validates the finite-difference step** by halving it
- **asserts** all of it

Python 3.8 or newer, standard library only, about four seconds.

Two honesty notes before you start, because they are the actual lesson.

**This is not the paper's regime.** Six layers at width 8, untrained, with a synthetic loss, is not what a mean field theory proof about large transformers concerns. The narrow question we can answer is whether anything moves in the predicted direction on a toy. That is worth knowing and it is not a reproduction.

**I got this measurement wrong twice before it worked**, and both mistakes are in the file's docstrings, because they are more useful than the result.

## Step 1: build the block, with one boolean

From [`lib/layernorm.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/layernorm.py):

```python
    def forward(self, x, mask=None):
        if self.norm_first:
            attended, _ = self.attention.forward(self.norm_attention.forward(x), mask)
            x = add(x, attended)
            branch = self.feed_forward.forward(self.norm_feed_forward.forward(x))
            return add(x, branch)
        attended, _ = self.attention.forward(x, mask)
        x = self.norm_attention.forward(add(x, attended))
        branch = self.feed_forward.forward(x)
        return self.norm_feed_forward.forward(add(x, branch))
```

Read the two branches side by side. In the Pre-LN branch, `x` is only ever passed to `add`. It is never normalised on its way through. In the Post-LN branch, `x` is reassigned to the output of a `LayerNorm` twice, so nothing survives a block unnormalised.

## Step 2: measure the forward stream

Run the same input through both and take the root mean square at every depth.

```
    depth    Post-LN     Pre-LN
  -----------------------------
    input     0.8030     0.8030
        1     1.0000     1.1935
        2     1.0000     1.7285
        3     1.0000     2.3051
        4     1.0000     2.7545
        5     1.0000     2.8839
        6     1.0000     3.4238

  Post-LN largest / smallest across blocks: 1.000
  Pre-LN  output / input:                   4.264
  Pre-LN grows at every block:              True
```

Post-LN reads **1.0000** at every single depth, exactly rather than approximately. The last thing each block does is normalise, so the stream leaving it has unit variance by construction, and depth cannot change that.

Pre-LN climbs from 0.8030 to 3.4238, growing at every block, a factor of **4.264** over six layers. Every block adds its branch to an untouched residual path, so the variances accumulate. Six layers is nothing; imagine ninety-six.

That growth is not automatically bad, and it is why real Pre-LN architectures put a final normalization after the last block. It is nonetheless the reason the two arrangements cannot be compared on raw magnitudes, which is exactly the trap I fell into.

## Step 3: gradients, by hand

No autodiff, so central differences. Perturb one weight up by `h`, measure the loss, perturb down by `h`, measure again, and the derivative is the difference over `2h`. Do that for all 64 entries of a block's attention output projection and take the L2 norm.

Choosing the loss is where I went wrong the first time, and it is worth your attention because it is a trap anyone repeating this will hit:

```python
    THE OBVIOUS LOSS DOES NOT WORK HERE, and the reason is worth stating
    because it is a trap anyone repeating this will fall into. The first
    version of this script used the mean squared VALUE of the output, with
    no target. Under Post-LN the last operation in the stack is a
    LayerNorm, so every output row has mean 0 and variance 1 by
    construction, so that loss is pinned at 1.0 no matter what any weight
    does. Its gradient measured as 1e-5, which looks like a dramatic
    finding about Post-LN and is actually a statement about the loss.
```

A loss that the architecture makes constant has zero gradient, and zero gradient looks exactly like a dramatic result. Measuring against a fixed target fixes it, because normalisation constrains each row's length but not its direction.

Here is the output, and read the caveat before the numbers:

```
    block     Post-LN  / its mean      Pre-LN  / its mean
  -------------------------------------------------------
        0    0.127955        0.55   10.582733        1.14
        1    0.148474        0.64   15.463770        1.67
        2    0.143173        0.62    9.801398        1.06
        3    0.191081        0.83    7.820954        0.84
        4    0.458930        1.99    5.410039        0.58
        5    0.314603        1.36    6.611628        0.71
```

**The raw columns are not comparable across arrangements.** Pre-LN's numbers are larger, and that is mostly the 4.264 from step 2: a bigger residual stream means outputs further from the target means bigger gradients everywhere, for a reason that has nothing to do with layer-norm placement. Reading "Pre-LN gradients are twenty times bigger" off this table would be wrong.

The comparable thing is the **shape**, which is what the "/ its mean" columns are. Divide each arrangement's profile by its own average and the scale cancels.

Now look again. Post-LN: 0.55, 0.64, 0.62, 0.83, **1.99, 1.36**. It starts below its average and ends well above it. Pre-LN: 1.14, 1.67, 1.06, 0.84, **0.58, 0.71**. It starts above and ends below.

```
  Post-LN tilt, output half over input half: 2.299
  Pre-LN  tilt, output half over input half: 0.554
  Post-LN tilts 4.15 times further toward the output
```

Post-LN puts **2.3 times** more gradient in the half of the stack nearest the output than in the half nearest the input. Pre-LN does the reverse, at 0.554.

That is the direction Xiong et al. describe, on a six-layer toy, measured by finite differences, with no training. I would not call it a reproduction of their proof. I would call it the smallest piece of evidence that the effect they analysed is not an artifact of their assumptions.

## Step 4: check the step

A finite-difference result you have not validated is a number, not a measurement. Halve the step and the answer should barely move:

```
STEP CHECK: is the finite-difference step small enough?
  step 1e-04   gradient norm 0.314603
  step 5e-05   gradient norm 0.314603
  relative change  0.00%
```

Six significant figures, unchanged. If that had moved by a few percent, everything above would be step-size artifact and the post would say so instead.

## Run it

```
python3 experiments/week-03/norm_placement.py
```

Four seconds. The last line reads `All assertions passed`. These should match exactly:

| check | expected |
|---|---|
| both stacks hold identical weights | `True` |
| Post-LN residual stream, every depth | `1.0000` |
| Pre-LN output over input | `4.264` |
| Post-LN tilt | `2.299` |
| Pre-LN tilt | `0.554` |
| step check, relative change | `0.00%` |

## The weekend part

Ninety minutes. Three things, in increasing order of interest.

**Change the depth.** Set `NUM_LAYERS` to 12 and re-run. Does Pre-LN's residual stream keep growing at the same rate, or does the growth per block change? Does the tilt get stronger with depth? The paper's claim is about depth, so depth is the variable that ought to matter.

**Break my measurement on purpose.** Put the degenerate loss back: replace the target term with the mean squared value of the output. Watch Post-LN's gradients collapse to around 1e-5 and see how completely convincing the wrong answer looks. That is the most valuable ninety seconds in this exercise. A measurement that produces a dramatic number is not thereby a good measurement.

**Then the one that is actually hard.** Add a final `LayerNorm` after the last Pre-LN block, which is what real Pre-LN architectures do, and work out what it does to the tilt. My prediction is that it changes the gradient profile substantially and I have deliberately not measured it, because I would rather read yours.

## The thing to keep

Every named decision in this week had a measurable consequence that nothing warns you about. Where the merge boundary goes. How big the vocabulary is. Whether the position table is long enough. Where the layer norm sits.

None of them raise. That is the pattern, and it is the week's real subject.

**A configuration that cannot fail loudly will eventually fail quietly, and the only defence is measuring the thing you assumed.** Which is what tonight was: I assumed Post-LN's gradients would be larger, measured it, got the opposite, found out my comparison was invalid, fixed the comparison, and only then had a result. The first two answers were confident and wrong.

Bookmark this. You will need it at 3am someday, and probably not for layer norm. You will need it the night a number looks dramatic and you have to decide whether you measured the system or measured your own setup.

---

*Tomorrow, 09:00: week 4 opens a new theme, and the first post carries the answers to this morning's three questions.*
