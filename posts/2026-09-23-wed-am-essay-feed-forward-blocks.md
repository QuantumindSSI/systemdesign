# Week 4 · Wed 2026-09-23 · 09:00 · The mental model for feed-forward blocks, before the code

> Calendar row: W4 Wed AM, 09:00 (CSV row `54:4`). Format: concept deep-dive.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 2.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + human-first voice + prose style
> rules 1 through 7.
>
> **Canonical source rule.** The CSV `source` column names an external
> repository. Per `AGENTS.md` that string is an internal routing hint and
> appears nowhere below.
>
> Committed calendar beats, all three present: define the failure the
> feed-forward block fixes, in two lines with a concrete example | build the
> mechanism conceptually, at the level of outcomes rather than code | state
> what it still does not do, the gaps the code inherits.
> Committed CTA: "Tag someone who is debugging this right now."
>
> Artifacts, committed before this article was written:
> - `lib/feedforward.py`, 433 lines, standard library only.
> - `tests/test_feedforward.py`, 52 tests, all passing.
> - `experiments/week-04/feedforward_lab.py`, six asserted claims.
>
> Verification 2026-09-15: exit 0, "All assertions passed", stdout md5
> `2aea2a2f7af00f3f26d3e3300d5e4321`, byte-identical across two runs, 0.5 s.
> Every number below is copied from that stdout or is arithmetic on two
> figures from one named paper.
>
> **One assertion fired before publication and is recorded.** The script first
> claimed half the output length would need under a quarter of the live hidden
> units, and checked two positions. Position 7 measured 0.2623 and the
> assertion failed. Checking all 32 positions gives a range of 0.2132 to
> 0.2698, so the sample had been too small to reveal that the threshold was
> wrong. The claim now asserts over every position with a ceiling of 0.33,
> above the measured maximum rather than inside it, and the failure is in the
> script's docstring.
>
> Non-repository sources, all permitted under the canonical source rule:
> - Geva, Schuster, Berant and Levy, "Transformer Feed-Forward Layers Are
>   Key-Value Memories", arXiv:2012.14913. Abstract read 2026-09-13. Quoted:
>   "Feed-forward layers constitute two-thirds of a transformer model's
>   parameters, yet their role in the network remains under-explored"; they
>   "operate as key-value memories, where each key correlates with textual
>   patterns in the training examples, and each value induces a distribution
>   over the output vocabulary"; "lower layers tend to capture shallow
>   patterns, while upper layers learn more semantic ones"; "the output of a
>   feed-forward layer is a composition of its memories".
> - Shazeer, "GLU Variants Improve Transformer", arXiv:2002.05202. Abstract
>   read 2026-09-13. Quoted: gated linear units "consist of the component-wise
>   product of two linear projections, one of which is first passed through a
>   sigmoid function"; some variants "yield quality improvements over the
>   typically-used ReLU or GELU activations".
> - Vaswani et al., arXiv:1706.03762. Used for the base configuration,
>   d_model 512 and d_ff 2048, quoted in the W3 Sun kickoff from the same
>   reading on 2026-09-06.
>
> Adversarial review record (2026-09-15):
> - The two-thirds figure is computed from stated widths and shown to be
>   exact for that configuration, rather than quoted as a general fact about
>   all transformers. The body says which configuration makes it exact ✓
> - The key-value memory reading is presented as an identity we verify and as
>   an interpretation the cited paper argues for, and those two are kept
>   apart ✓
> - Sparsity and concentration figures are labelled as untrained-weight
>   measurements at every point of use ✓
> - Geva et al.'s layer-depth finding is quoted as their empirical result on
>   trained models and is explicitly not reproduced here ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,506 words, within the committed 2,500 to 3,500-word
>   09:00 range ✓
> - Zero em dashes. No sentence opens with a conjunction. No collapsed
>   contrastive framing. Verified by `tools/prose_gate.py` ✓

---

**Topic:** Feed-forward blocks: the two-thirds of a transformer that gets one sentence in most explanations

**Subtitle:** Its output is exactly a weighted sum of fixed directions, one per hidden unit, and once you can see the sum you can see what the block is actually storing.

Good morning.

Every so often I look at the electricity bill for a flat and find that the thing using most of the power is not any of the things I think about. The laptop, the lights, the kettle, all the appliances with buttons and opinions. Meanwhile the fridge has been running the entire time, has no interface, makes no decisions I am aware of, and is quietly the largest line item.

The feed-forward block is the fridge.

Nine days ago we established that a transformer stack is a running total and that every block writes to it twice. One of those writes comes from attention, which gets the diagrams, the interview questions and the blog posts. The other comes from two matrix multiplies with a nonlinearity in between, applied to each position separately, which usually gets a sentence. Geva et al. open their paper by naming the imbalance: "Feed-forward layers constitute two-thirds of a transformer model's parameters, yet their role in the network remains under-explored" (arXiv:2012.14913).

## The failure it fixes, in two lines

Attention moves information between positions and does almost nothing to it on the way. Strip the block down and the operation is a weighted average of value vectors, which is a linear combination, and a stack of linear combinations is still a linear combination.

**Concrete version.** Take the sentence "the invoice was paid". Attention can let "paid" pull in whatever "invoice" is carrying. What it cannot do is take the mixture it just built and turn it into something that was not a blend of its inputs. Every output vector lives in the span of the value vectors that went in.

The feed-forward block is where a position gets to do something to itself that is not a mixture of other positions. That is the failure it fixes, and it is why the two sublayers alternate rather than one of them being enough.

## The arithmetic, which is more exact than I expected

Count the matrices in one block. Attention has four projections of size d_model by d_model: queries, keys, values, output. That is 4 times d_model squared. The feed-forward block has two matrices of size d_model by d_ff, which is 2 times d_model times d_ff.

The original paper uses d_ff equal to four times d_model. Substitute:

```
  attention      4 * d^2
  feed-forward   2 * d * 4d  =  8 * d^2
```

The feed-forward block is exactly twice attention, so it is exactly two-thirds of the block. Not approximately two-thirds. The width cancels out completely, so it holds at every size:

```
  d_model     d_ff    attention  feed-forward   ff share
  -------------------------------------------------------
       64      256       16,384        32,768   0.666667
      256     1024      262,144       524,288   0.666667
      512     2048    1,048,576     2,097,152   0.666667
      768     3072    2,359,296     4,718,592   0.666667
     1024     4096    4,194,304     8,388,608   0.666667
     4096    16384   67,108,864   134,217,728   0.666667

  furthest any row sits from two-thirds: 0.0e+00
```

That last line is the assertion, and it reports zero because the ratio has no width left in it once you substitute.

Two caveats, both of which matter if you are going to quote this. The count excludes biases, layer-norm gains and the embedding table, which are real parameters and are small next to these. The exactness also depends entirely on the four-times convention. A model with d_ff at 2.5 times d_model has a different split, and plenty of recent models do exactly that, which is the next paragraph.

## What gating changes, and the arithmetic nobody explains

There is a variant with three matrices instead of two. Two projections are computed, one is passed through a nonlinearity, and they are multiplied together element by element before the result goes through the third matrix. Shazeer describes the family: gated linear units "consist of the component-wise product of two linear projections, one of which is first passed through a sigmoid function", and reports that some variants "yield quality improvements over the typically-used ReLU or GELU activations" (arXiv:2002.05202).

Three matrices at the same hidden width is 1.5 times the parameters. Which raises the question everyone skips: if you want the same budget, how wide should the hidden layer be?

Two-thirds as wide. Three matrices at two-thirds the width is the same count as two matrices at full width. Two-thirds of 2048 is 1365.33, and real configurations round to a multiple of 8:

```
    three matrices, so the hidden width drops to 1360
    2 * 2048 / 3 = 1365.33, rounded down to a multiple of 8
    gated feed-forward     2,088,960
    ungated, for comparison 2,097,152
    ratio 0.9961, which is 0.39% under parity
```

This is why you see hidden widths in released models that look arbitrary. A number like 11008 next to a model width of 4096 looks like somebody's lucky guess. It is 2.6875 times the width, which is two-thirds of four, rounded to land on a convenient multiple. The apparently random number is the parameter-matching arithmetic, done once and then frozen into a config file.

## The reading that makes the block legible

Here is the part that changed how I think about this sublayer. Write the second matrix multiply out by hand instead of calling it a matrix multiply:

```
    out_row  =  sum over j of   hidden[j] * W_out[j]
```

`W_out[j]` is row j of the output matrix, which is a fixed vector in model space that does not depend on the input at all. `hidden[j]` is one number, the activation of hidden unit j at this position.

The output of a feed-forward block is therefore a **weighted sum of fixed directions**, and the only thing the input decides is the weights. Each hidden unit owns one direction permanently and votes on how loudly to contribute it.

That is an identity rather than an analogy, and we check it:

```
  largest disagreement with the matrix multiply, over all 32 positions
  and all 64 output dimensions: 0.0e+00
```

Exactly zero, across every position and every output dimension, because summing the terms and doing the matrix multiply are the same additions.

Geva et al. build an interpretation on top of that structure, arguing feed-forward layers "operate as key-value memories, where each key correlates with textual patterns in the training examples, and each value induces a distribution over the output vocabulary", and that "the output of a feed-forward layer is a composition of its memories". The first matrix holds the keys, one per hidden unit, and asks "does this position look like my pattern". The second matrix holds the values, one per hidden unit, and says "if so, contribute this".

Keep the two things separate in your head. The decomposition is arithmetic and holds for any weights including random ones. The claim that the keys correspond to interpretable textual patterns is their empirical finding on trained models, and it is not something this repository can check. What our identity buys is that the interpretation is at least **well-typed**: there really are per-unit directions to be interpreted, and asking what unit 3,421 does is a question with a referent.

## How many units are actually talking

Given that reading, two questions become measurable. How many units are on, and how evenly do they share the work?

The first depends entirely on the activation, and the difference is sharper than the usual "ReLU versus GELU" discussion suggests:

```
  activation   exact zeros   below 1e-3   smallest |value|
  ----------------------------------------------------------
  relu              0.5012       0.5022           0.00e+00
  gelu              0.0000       0.0027           2.09e-05
  silu              0.0000       0.0027           2.09e-05
```

ReLU zeroes 50.12% of the hidden layer exactly. GELU and SiLU zero **nothing**, exactly, and their smallest value across the whole layer is 2.09e-05.

That distinction is not aesthetic. A term multiplied by exactly 0.0 contributes exactly nothing and a kernel may skip it. A term multiplied by 2.09e-05 contributes almost nothing and a kernel may not skip it, because "almost" is not a thing arithmetic knows about. Every proposal to exploit feed-forward sparsity at inference time runs into that line, and the choice of activation decides whether the sparsity is there to exploit.

The 50.12% figure is a measurement on untrained weights, where a symmetric random projection puts half its outputs below zero by construction. What a trained network does is an empirical question about that network.

While we are on activations, there is a practical trap here that has cost people afternoons. The standard smooth activation has an exact definition involving the Gaussian error function, and most frameworks ship a tanh-based approximation of it instead. The two are close and they are not the same function:

```
      x      exact GELU    tanh GELU    difference
  --------------------------------------------------
   -3.00      -0.004050    -0.003637     -0.000412
   -2.70      -0.009361    -0.008888     -0.000473
   -1.00      -0.158655    -0.158808     +0.000153
    0.00       0.000000     0.000000     +0.000000
    1.00       0.841345     0.841192     +0.000153
    2.70       2.690639     2.691112     -0.000473
    3.00       2.995950     2.996363     -0.000412

  largest gap over x in [-6, 6]: 4.73e-04 at x = 2.70
```

Under half a thousandth at its worst, and zero at the origin, which is exactly the shape that makes it invisible in a two-point sanity check and visible when you port a model between two runtimes and compare logits. Both implementations are correct. Neither is a bug. If you have ever chased a small unexplained divergence between two frameworks running the same weights, this is on the list of places to look, and it takes one line to test.

The second question is how evenly the live units share the work. Ranking each unit by the length of its contribution:

```
  position   live units   half the length in   90% in   share of live
  ----------------------------------------------------------------------
         0          124                   28       78          0.2258
         7          122                   32       82          0.2623

  across all 32 positions: min 0.2132, max 0.2698, mean 0.2416
```

At position 0, 124 of 256 units are live, and 28 of them carry half the total contribution length. A flat distribution would need half the live units. The measured answer is around a quarter, at every position.

That figure is where my own assertion fired, and the correction is instructive. I originally wrote "under a quarter" and checked two positions. Position 7 came in at 0.2623 and the test failed. Checking all 32 gives 0.2132 to 0.2698, so my sample had been too small to notice the threshold was wrong. The claim now runs over every position with a ceiling above the measured maximum, which is the only honest place for a threshold to sit.

Here is what the top of that ranking looks like at one position, and it is worth a look because it shows the two factors that decide a unit's contribution:

```
  the five loudest units at position 0
    unit  204   activation   1.2385   contribution 0.7757
    unit  162   activation   1.3319   contribution 0.7606
    unit  104   activation   1.2541   contribution 0.7420
    unit  224   activation   1.0239   contribution 0.6804
    unit  113   activation   0.9970   contribution 0.6741
```

Unit 162 has the largest activation of the five and is second in contribution, because unit 204's output direction is slightly longer. Ranking hidden units by activation alone is therefore the wrong ranking, and it is the one people reach for because the activation is the number that is easy to get. The contribution is the activation times the length of that unit's fixed direction, and both factors are free to vary. In a trained model the second factor is something the training chose, so a unit with a modest activation and a long output row can matter more than a loud one with a short row.

## What it still does not do

Three gaps, stated plainly, because the code inherits all of them.

**It sees one position at a time.** The feed-forward block has no access to any other position. Run it on the whole sequence and run it on one row alone, and that row's output is identical to twelve decimal places, which is checked directly in `tests/test_feedforward.py`. Whatever cross-position work needs doing was done by attention before this block ran, and anything attention failed to bring across is not recoverable here.

That independence has a consequence worth pausing on, and it shows up in the ledger from the 14th. Across eight blocks, the feed-forward writes measured 0.5134 to 0.5952, a spread of about 16%. The attention writes over the same blocks measured 0.5166 to 0.9137, a spread of 77%. Attention's contribution varies with what the sequence happens to contain, because its output is a mixture whose weights depend on the whole sequence. The feed-forward block's contribution is a function of one row, so it has far less to vary with. Both figures are from untrained weights and the spread of them would look different after training. The structural reason for the asymmetry would not.

**It has no memory between calls.** The block is a pure function of its input row. The key-value memory framing is about what the weights have stored during training. At inference there is no state, no cache, and nothing that changes between the first token and the ten-thousandth.

**Its width is a fixed budget, spent on everything.** The same hidden layer serves every token in every context. Geva et al. find that "lower layers tend to capture shallow patterns, while upper layers learn more semantic ones", which is their empirical result on trained models and is worth knowing precisely because it is the sort of specialisation nothing in the architecture requires. The block has no mechanism that reserves capacity for anything.

That third gap is where mixture-of-experts enters, by making the hidden layer conditional so that different tokens use different slices of it. Two of this week's papers use it. It gets its own week, and I am not going to summarise it in a paragraph.

## The thing to carry

Run it:

```
python3 experiments/week-04/feedforward_lab.py
```

Under a second, six asserted claims, and it prints every table above. The module is [`lib/feedforward.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/feedforward.py) and the measurements are in [`experiments/week-04/feedforward_lab.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-04/feedforward_lab.py).

Here is what I would keep. When you look at a model config and see `hidden_size` and `intermediate_size`, you are looking at the two numbers that decide where two-thirds of the parameters go, and their ratio tells you which family the model is in. Four to one is the ungated original. Something near 2.7 to one is a gated block that has been parameter-matched against it. That is a fifteen-second read of a config file that tells you a real thing about the architecture, and it is available to anybody who has done the arithmetic once.

The fridge is the largest line item on the bill. It is worth knowing which one it is before you start unplugging lamps.

Tag someone who is debugging this right now, particularly if they are staring at an `intermediate_size` wondering where the number came from.

---

*This evening, 17:00: the same block read line by line in this repository, including the decomposition that turns the second matrix multiply into a ledger of per-unit contributions, and the one line in it that is an honest tradeoff rather than a bug.*
