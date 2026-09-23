# Week 4 · Mon 2026-09-14 · 09:00 · Residual streams, explained from first principles

> Calendar row: W4 Mon AM, 09:00 (CSV row `52:4`). Format: concept deep-dive.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 2.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + human-first voice + prose style
> rules 1 through 7.
>
> **Canonical source rule.** The CSV `source` column names an external
> repository. Per `AGENTS.md` that string is an internal routing hint and
> appears nowhere below. Every line of code quoted here was written in this
> repository.
>
> Committed calendar beats, all three present: define residual streams in two
> sentences with no jargon | walk the core mechanism step by step with one
> concrete example | state the one misconception that causes the most damage.
> Committed CTA: "Comment your take - I read every reply."
>
> Artifacts, committed before this article was written:
> - `lib/residual.py`, 473 lines, standard library only, built on
>   `lib/linalg.py`, `lib/attention.py` and `lib/layernorm.py`.
> - `tests/test_residual.py`, 46 tests, all passing.
> - `experiments/week-04/residual_stream.py`, five asserted claims.
>
> Verification performed 2026-09-13 and re-run 2026-09-14: exit 0, "All
> assertions passed", stdout md5 `490e464df6f75a098056e1a719f414a3`,
> byte-identical across two runs, 0.6 s. Every number below is copied from
> that stdout.
>
> **One assertion fired before publication and is recorded.** The script first
> claimed the last attention write would be under a quarter of its outgoing
> stream. It measured 0.3537 and the assertion failed. The threshold had been
> guessed rather than measured, and the real effect is a trend across depth,
> so the claim was rewritten as the ratio of the lower half's mean write share
> to the upper half's, which measures 1.509. The body reports the trend rather
> than the guessed number, and the failure is written into the script's
> docstring.
>
> Non-repository source, permitted under the canonical source rule:
> - He, Zhang, Ren and Sun, "Deep Residual Learning for Image Recognition",
>   arXiv:1512.03385. Abstract fetched and read 2026-09-13. Quoted:
>   reformulating layers "as learning residual functions with reference to the
>   layer inputs, instead of learning unreferenced functions"; "residual nets
>   with a depth of up to 152 layers"; "3.57% error on the ImageNet test set".
>
> Adversarial review record (2026-09-14):
> - The reconstruction identity is presented as an algebraic property that
>   holds for any weights, and the growth and share results are labelled as
>   measurements on untrained weights ✓
> - The arithmetic ablation is explicitly distinguished from rerunning without
>   the component, and both numbers are given rather than the flattering one ✓
> - The 2015 image-network result is attributed to that paper's own
>   experiments and is not presented as a claim about language models ✓
> - The misconception section quantifies the misconception rather than
>   asserting it ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,716 words, within the committed 2,500 to 3,500-word
>   09:00 range ✓
> - Zero em dashes. No sentence opens with a conjunction. No collapsed
>   contrastive framing. Verified by `tools/prose_gate.py` ✓

---

**Topic:** The residual stream: why a transformer stack is a sum of contributions rather than a chain of transformations

**Subtitle:** The input plus every recorded write reconstructs the output with an error of exactly zero, and once you have seen that, the question "what did layer 14 compute" stops making sense.

Good morning.

Yesterday I described the noticeboard in a building hallway: cork, drawing pins, and one unwritten rule where you add your notice and never remove anyone else's. Today that noticeboard is the whole post, because it is the most accurate picture of a transformer I know, and almost nobody draws it.

Housekeeping first. Saturday's three quiz questions were answered in yesterday's 09:00 post, one day earlier than that Saturday post's own wording promised. If you came looking for them here, they are one post back.

## Two sentences, no jargon

**A residual stream is a running total that every part of the model adds to and nothing removes from.** A transformer block reads that total, computes something from it, and adds the result back, so the value arriving at the top of the stack is the starting vector plus every contribution written along the way.

That is the whole idea. The rest of this post is about why it is not a metaphor.

## The step-by-step, with one concrete example

Here is one pre-norm block, written out. Everything in this series uses the arrangement where normalization sits on the branch rather than on the main path, which is the one we measured on Saturday 2026-09-12.

```
    x  ->  x + Attention(LayerNorm(x))
    x  ->  x + FeedForward(LayerNorm(x))
```

Look at where `x` appears. On the right-hand side it appears twice: once inside a function, and once on its own as the first term of a sum. The copy inside the function is read. The copy outside is carried. Nothing in that line writes over `x`.

Stack eight of those and the top of the stack holds the input plus sixteen additions, and you can list them. I built exactly that in [`lib/residual.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/residual.py) and recorded every write. The recorder intercepts each branch output before it is added, so that instead of a black box you get a ledger:

```
  depth  component      write   stream in  stream out   share   cos
  ------------------------------------------------------------------
      0  attention     0.7181      0.9124      1.2238  0.5867 +0.114
      0  feed_forward  0.5439      1.2238      1.2387  0.4391 -0.195
      1  attention     0.8736      1.2387      1.5663  0.5577 +0.072
      1  feed_forward  0.5449      1.5663      1.6088  0.3387 -0.095
      2  attention     0.8788      1.6088      1.6388  0.5363 -0.239
      2  feed_forward  0.5312      1.6388      1.6808  0.3160 -0.082
      3  attention     0.5166      1.6808      1.7728  0.2914 +0.029
      3  feed_forward  0.5952      1.7728      1.8736  0.3177 +0.006
      4  attention     0.8154      1.8736      1.9237  0.4239 -0.155
      4  feed_forward  0.5144      1.9237      2.1015  0.2448 +0.228
      5  attention     0.7157      2.1015      2.4095  0.2970 +0.292
      5  feed_forward  0.5134      2.4095      2.4503  0.2095 -0.026
      6  attention     0.7430      2.4503      2.4589  0.3022 -0.140
      6  feed_forward  0.5324      2.4589      2.6036  0.2045 +0.172
      7  attention     0.9137      2.6036      2.5829  0.3537 -0.198
      7  feed_forward  0.5457      2.5829      2.6472  0.2062 +0.014
```

Eight blocks, two writes each. Read it three ways.

**First, the "write" column, which does not grow.** Every block contributes something between 0.51 and 0.91, regardless of where it sits. Block 7's attention writes 0.9137, the largest write in the table, and block 0's writes 0.7181. There is no trend. Each block is doing roughly the same amount of work.

**Second, the "stream out" column, which does grow.** The board starts at 0.9124 and finishes at 2.6472.

**Third, the "share" column, which is the first two divided.** Block 0's attention is 58.7% of the stream leaving it. Block 7's feed-forward is 20.6% of the stream leaving it. Same-sized notice, much fuller board. Averaged over the lower four blocks the share is 0.4230, and over the upper four it is 0.2802, a ratio of **1.509**.

That last number is the one I got wrong the first time, and it is worth a sentence because the correction is the useful part. My original claim was that the last attention write would be under a quarter of its stream. It measured 0.3537 and the assertion fired. The threshold had been guessed. The effect is real and it is a trend across depth rather than a small number at the top, so the claim now measures the trend, and the failed version is in the script's docstring where anyone can see what I had assumed.

## The part that makes this more than a diagram

Everything above is descriptive. Here is the load-bearing claim:

**The input plus every recorded write reconstructs the final stream with a largest element-wise difference of exactly 0.0.**

```
    PRE-LN,  all 16 writes            0.0e+00
```

Floating point usually leaves a residue somewhere around 1e-15 when two computations agree. Here there is no residue at all, because the recorder and the stack perform the same additions in the same order, and addition of the same numbers in the same order is the same operation. The identity is not approximately true. It is what the arithmetic does.

That matters because a sum can be taken apart and a chain of transformations cannot. If layer 5 produced its output by transforming layer 4's output, there is no meaningful way to ask what layer 5 contributed; the question dissolves into the composition. In a residual stack you can point at layer 5's term, remove it, and look at what is left, because it was only ever a term.

Here is the part of the recorder that makes the ledger, and it is deliberately boring:

```python
    def _pre_norm_block(self, depth, block, stream, mask, writes, silenced):
        """One pre-norm block: normalise the branch, add the result."""
        attended, _ = block.attention.forward(
            block.norm_attention.forward(stream), mask
        )
        stream = self._record(
            depth, "attention", stream, attended, writes, silenced
        )
        branch = block.feed_forward.forward(
            block.norm_feed_forward.forward(stream)
        )
        return self._record(
            depth, "feed_forward", stream, branch, writes, silenced
        )
```

`_record` does the addition and keeps a copy of what was added. That is the entire instrumentation. There is no gradient hook, no tracing framework, and no clever machinery, because in an additive stack the thing you want to record is already sitting on the right-hand side of a plus sign, waiting to be picked up. Compare what it would take to answer the same question about a stack where each layer overwrote its input, and the difference is the whole argument for the architecture.

One observation from the ledger that I will state and then immediately hedge. Attention writes in this toy run from 0.5166 to 0.9137 and feed-forward writes from 0.5134 to 0.5952, so attention is the noisier contributor and the feed-forward is remarkably consistent. That is a fact about untrained Glorot-initialised weights with these widths and it should not be carried anywhere. The reason to point at it is procedural: the ledger gives you a per-component distribution to look at, and the first thing worth doing with any new instrument is checking whether it says something you can already explain.

## How the total grows, which is not how you would guess

The writes are each around 0.5 to 0.9 and there are sixteen of them plus a starting vector of 0.9124. A reasonable first guess is that they add up. They do not:

```
    input                              0.9124
    measured output                    2.6472
    predicted, sum of squares          2.8378   off by 7.2%
    predicted, plain sum              11.4083   off by 331%
```

Adding the sizes predicts 11.4083 and the truth is 2.6472. Taking the square root of the sum of squares predicts 2.8378, off by 7.2%.

The second prediction works because the writes point in nearly unrelated directions. In a space of 16 dimensions, two arbitrary vectors are close to perpendicular, and perpendicular things combine by Pythagoras rather than by addition. The "cos" column in the big table is exactly this: the cosine between each write and the stream it lands in, and it sits between -0.24 and +0.29 with a mean of -0.0127.

Now the honest caveat, because this one has a real limit. Vectors with no structure at all in this many dimensions would give a mean absolute cosine of 0.0576. Ours is 0.1286, more than twice that. The writes are close to perpendicular and they are measurably **more aligned than chance**, which is why quadrature comes within 7.2% rather than landing exactly. This is an untrained model. A trained one has every reason to arrange its writes deliberately, and nothing here says what that arrangement looks like.

Carry the shape and leave the numbers: **a residual stream grows roughly with the square root of the number of writes, so depth buys you a bigger total slowly.** That is why a pre-norm model with 96 blocks does not arrive at the top with an astronomically large vector, and it is also why real pre-norm architectures put one final normalization after the last block anyway.

## The misconception that does the most damage

There is one, it is extremely common, and it is quantified in the table above.

**The misconception: that the output of block k is what block k computed.**

It is not. The output of block k is the entire running total at that point, and most of it was written by something else. At block 7, the feed-forward write is 20.6% of the outgoing stream. The other **79.4%** was put there by the fifteen writes below it and by the embedding.

This has teeth. If you take activations from layer 20 of a model, run them through the unembedding, and read off what the model "thinks" at layer 20, you are reading the accumulated total, and you are attributing all of it to layer 20. That technique is genuinely useful and the interpretation of it is where people get hurt. The honest description of what you measured is the state of the noticeboard after twenty floors, not what the twentieth floor posted.

The second form of the same error is subtler and it cost me a measurement. There are two different experiments you can call "ablating a component", and they give very different answers:

```
  depth  component      arithmetic     rerun    rerun / arithmetic
  --------------------------------------------------------------
      0  attention         0.7181    2.2283             3.103
      0  feed_forward      0.5439    2.2546             4.145
      1  attention         0.8736    2.6075             2.985
      2  attention         0.8788    2.0194             2.298
      3  attention         0.5166    0.9587             1.856
      4  attention         0.8154    1.2968             1.590
      5  attention         0.7157    0.7509             1.049
      6  attention         0.7430    0.8298             1.117
      7  attention         0.9137    0.9894             1.083
      7  feed_forward      0.5457    0.5457             1.000
```

The "arithmetic" column deletes that block's term from the finished sum and changes nothing else. The "rerun" column writes zeros in its place and lets every later block read the reduced stream.

At block 0's attention the rerun effect is **3.103 times** the arithmetic one. At block 0's feed-forward it is 4.145 times. At the top block's feed-forward the two are equal to the last decimal place, **1.000**, because there is nothing above it to react.

Read that column downward and you are watching compounding. An early write is not just its own 0.7181. It is that, plus its influence on every read above it, plus the influence of those changes on everything above those. The deeper a component sits, the more of its effect lives in what other components did differently because of it, and no single-layer analysis can see any of that.

## Where the identity breaks, and why that is the point

Everything above assumed pre-norm. Run the same recorder on the original post-norm arrangement, where normalization sits on the main path, and the branch writes stop adding up:

```
    POST-LN, all 32 writes           0.0e+00
    POST-LN, 16 branch writes only  6.0868
```

The first line is exact because the recorder also logs each renormalisation as the delta it is equivalent to. The second line is what happens if you count only the attention and feed-forward writes, the way you legitimately can in pre-norm. It misses by 6.0868, against a final stream whose size is 1.0000.

That is not a rounding difference. It means the post-norm stack is genuinely not a sum of its branch outputs, because something is overwriting the total at the end of every block. The largest single renormalisation delta measures 0.7501, which is 75% of the stream it lands in.

Which connects to the layer-norm placement result from two days ago. The reason pre-norm won is usually told as a story about gradients and warm-up, and that story is correct. The residual stream gives you the other half of it: pre-norm preserves a clean additive channel from the input to the output, and post-norm does not. Every interpretability technique that treats a stack as a sum is quietly relying on that choice.

## Why this is Monday's topic rather than a footnote

The four mechanisms later this week are all rules about reading from this stream, and each of them is only describable once the stream exists as an object.

Grouped-query attention, on Wednesday, forces several query heads to share one set of keys. The interesting way to state what that costs is in terms of the stream: a layer's key projections can only read a certain number of independent directions out of it, and sharing keys shrinks that number. In our toy, the full arrangement reads all 64 dimensions and the fully shared one reads 8, leaving 56 directions that are invisible to the routing decision no matter what is written along them.

Multi-head latent attention, on Thursday, compresses what gets cached between positions. What is being compressed is a projection of the stream, and the whole question is whether the compression can be undone for free.

Sliding windows and learned selection, on Friday and Saturday, restrict which earlier positions a query may read at all. Since every position's contribution lives in its own stream, restricting the read is restricting which noticeboards you are allowed to walk past.

None of those four sentences can be said clearly without today's picture, which is why today's picture comes first.

## What this is for

The framing came from image networks. He et al. reformulated layers "as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions", and trained "residual nets with a depth of up to 152 layers", reaching "3.57% error on the ImageNet test set" (arXiv:1512.03385). Those figures describe their own vision experiments in 2015 and I am not transferring them anywhere. What transferred is the structural idea, and it transferred completely.

Three things to take into your week.

**When you are reading activations, ask what was added rather than what was computed.** The difference between those two questions is 79.4% of the vector at block 7 in our toy, and a larger fraction in anything deeper.

**When you ablate, say which ablation you ran.** Deleting a term from a sum and rerunning without the component are different experiments with a factor of three between them at the bottom of the stack. Both are legitimate. Reporting one and describing the other is not.

**When something in a stack looks like housekeeping, check whether it is on the residual path.** A component on the branch adds. A component on the main path can overwrite, and an overwrite is the one operation that destroys the property everything else depends on.

Run it yourself:

```
python3 experiments/week-04/residual_stream.py
```

Under a second. It prints every table above and ends with "All assertions passed". The five claims it checks are in [`experiments/week-04/residual_stream.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-04/residual_stream.py), and if one of them fails on your machine, this post is wrong and I want to know.

Here is the thing I keep coming back to. That hallway noticeboard is unreadable as a document and perfectly readable as a history. Nobody curated it, so everything anyone ever posted is still there, layered and jostling. A transformer works the same way and for the same reason: the refusal to overwrite is what lets a hundred blocks each contribute a little without the early contributions being erased by the late ones. The cost is a channel that gets more crowded with every floor, which is exactly what the share column was showing you.

Comment your take. I read every reply, and if you have ever read a layer's activations and described them as what that layer computed, I would genuinely like to know whether the distinction above changes anything for you.

---

*This evening, 17:00: the same mechanism as one diagram you can draw from memory, with the failure point marked and named.*
