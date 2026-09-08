# Week 3 · Tue 2026-09-08 · 17:00 · Follow-up: Reading All 254 Lines of Our Attention

> Calendar row: W3 Tue PM, 17:00 (CSV row `41:3`). Format: repo walkthrough.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The committed CSV row for this slot asks me to
> walk a file in an external repository. Per `AGENTS.md` that string is an
> internal routing hint and is not reproduced here or in the body. The
> `repo walkthrough` format means this repository. The file walked below,
> `lib/attention.py`, was written here, is committed here, and every line
> quoted is copied from it unmodified.
>
> Committed calendar beats, all three present below: point to the exact file
> that implements multi-head attention and read every line | trace one path
> through the code end to end, recomputing the real values | name the one line
> that is an honest tradeoff, not a bug.
> Committed CTA: "Bookmark this; you will need it at 3am someday."
>
> Companion: this morning's 09:00 essay established the budget argument, the
> sum-to-one constraint, and the four steps. This post assumes them and does
> not re-derive them.
>
> **Publication-gap note.** There are no tracked Mon 2026-09-07 posts, so
> nothing below refers backward to Monday. Same handling as this morning.
>
> Artifacts written for this post, committed here, linked from the body:
> - `experiments/week-03/attention_trace.py`, 320 lines, standard library
>   only. Prints every intermediate matrix of one four-position attention
>   computation, the two-head comparison, the assembly, the timing table, and
>   all seven error paths. Nine assertions, exit code 0 with "All assertions
>   passed", about four seconds.
> - `experiments/week-03/attention_heads.py` was written for this morning and
>   is cited again here for the cost-neutrality arithmetic.
>
> Every number below is from one run of `attention_trace.py` on this machine
> today (2026-09-08). The matrices are deterministic: input from
> `random.Random(13)` rounded to four places, weights from seed 20260908, so
> a reader reproduces them exactly. PART 5 is wall clock and will not
> reproduce exactly; it is labelled as such in the body.
>
> Line numbers cited, re-checked against the working tree today: 125, 126,
> 133, 134, 135 (the four steps), 187 to 189 (the three projections), 216 to
> 219 (the divisibility check), 222, 227, 249 to 254 (assembly), and
> `lib/linalg.py` 168 to 173 (the masked-row guard and the max subtraction).
>
> Adversarial review record (2026-09-08):
> - The softmax arithmetic for row 1 is recomputed by hand in the body and
>   agrees with the printed 0.6636 / 0.3364 to four places ✓
> - The named tradeoff is argued as a deliberate legibility choice with its
>   cost stated, not excused. The claim that it forfeits parallelism is
>   separated from the claim that the FLOP count is unchanged, because only
>   the second is measured here ✓
> - The timing table is presented as one machine, one run, with the ratios
>   rather than the absolute seconds carrying the argument. An earlier run
>   today produced 1.00 / 1.07 / 1.04 / 1.07 / 1.14; the run quoted produced
>   1.00 / 1.01 / 1.03 / 1.07 / 1.13. Both are shown, because a single
>   timing run is not evidence and pretending otherwise would be the failure
>   this series is meant to avoid ✓
> - No head is given a semantic role. The 0.1286 distance is reported as two
>   random projections differing, with no claim about what either attends to ✓
> - The complexity statements are the ones in the code's own docstrings,
>   re-derived here, not new claims ✓
> - Reader-facing body: 2,640 words, measured 2026-09-08 by whitespace split
>   over everything below the `---` marker ✓
> - Zero em dashes.

---

**Topic:** Reading a complete multi-head attention implementation line by line, with every intermediate matrix printed

**Subtitle:** Four lines of code do the actual work. The other 250 exist to stop you getting plausible numbers that are wrong, and one of them is a tradeoff I would defend and you might not.

Good evening.

This morning I asked you to hold one idea: a single attention head has one unit of attention to spend per position, and that budget is why one head is not enough. Tonight we open the file and watch the budget get spent, with real numbers on the screen.

I want to say something about why this is worth an hour. Most of us have had the experience of reading code that we understood at the level of "yes, that is what that does" and still could not have written. The gap is almost never the algorithm. It is that the reading skipped the intermediate values. You saw `softmax(QK^T / sqrt(d_k))V` and nodded, and nobody ever showed you the four numbers in row two. So tonight nothing is skipped. Every matrix, at every step.

## The file, and how small it actually is

Two files, both standard library only, no numeric package underneath:

- [`lib/attention.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/attention.py), 254 lines, of which a substantial fraction is docstring.
- [`lib/linalg.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/linalg.py), 178 lines, matrices as lists of lists, no broadcasting, no dtypes, no in-place mutation.

The second file exists for one reason, and it is stated at the top of it: so that the first file can be read as mathematics rather than as array-library idiom. Every reshape you have ever squinted at in production attention code is absent here, because there is nothing to reshape.

To follow along with the exact numbers, [`experiments/week-03/attention_trace.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/attention_trace.py) prints all of it. Four positions, four numbers per position, two heads. Small enough to check by hand, which we are going to do.

## Three questions about one word

A head begins by asking the same input three different questions. Lines 187 to 189, and this is the whole of it:

```python
        queries = matmul(x, self.w_query)
        keys = matmul(x, self.w_key)
        values = matmul(x, self.w_value)
```

Same `x` three times, three different matrices. In our trace, `x` is four positions of four numbers, and each projection matrix is 4 by 2, so each of Q, K and V comes out 4 by 2.

```
  x   (4 x 4)                          Q = x W_q   (4 x 2)
    [ -0.4820   0.3705   0.3682   0.6987 ]    [ -0.1617   0.6983 ]
    [ -0.6286  -0.5389  -0.7057  -0.5497 ]    [  0.9535   0.4182 ]
    [  0.4680  -0.7396   0.0626  -0.5722 ]    [  0.3125  -1.0824 ]
    [ -0.4107  -0.1368   0.6753   0.2168 ]    [  0.1049  -0.2327 ]
```

Notice the width dropped from four to two. That is the head being a head: 2 heads, d_model 4, so d_head is 2. Line 222 is where that happens and it is one line of integer division:

```python
        self.d_head = d_model // num_heads
```

## The four lines that do the work

Here is the entire mechanism, lines 125 to 135, with the shape checks removed for a moment:

```python
    scores = matmul(queries, transpose(keys))
    scores = scale(scores, 1.0 / math.sqrt(d_k))
    if mask is not None:
        scores = add(scores, mask)
    weights = softmax_rows(scores)
    return matmul(weights, values), weights
```

Four operations. Let us watch each one.

**Line 125, every query against every key.** Q is 4 by 2 and K transposed is 2 by 4, so the product is 4 by 4: one score for every ordered pair of positions.

```
  1. scores = Q K^T
    [  0.1775  -0.1443  -0.1824   0.2749 ]
    [ -0.0093  -0.9698  -0.4894  -0.6582 ]
    [ -0.2819   0.1715   0.2603  -0.4747 ]
    [ -0.0648   0.0052   0.0423  -0.1316 ]
```

Take one entry and check it. Row 1, column 0, is position 1's query against position 0's key. Q row 1 is `[0.9535, 0.4182]`. K row 0 is `[-0.1101, 0.2286]`. So the dot product is 0.9535 times -0.1101, which is -0.10498, plus 0.4182 times 0.2286, which is 0.09560. Sum: -0.00938. The table says -0.0093. There is no step here you cannot do on paper.

This 4 by 4 is also where the quadratic cost lives. Four positions gives sixteen entries. Four thousand positions gives sixteen million, and that is the number that decides your memory bill.

**Line 126, the divisor.** d_k is 2 here, so everything gets divided by 1.414214.

```
  2. scores / sqrt(d_k)
    [  0.1255  -0.1020  -0.1290   0.1944 ]
    [ -0.0066  -0.6858  -0.3461  -0.4654 ]
```

At width two this looks pointless, and honestly at width two it nearly is. That is exactly why it is dangerous. This morning's measurement showed what the same line is doing at width 512: without it, the average largest softmax weight is 0.947 and the row has effectively collapsed to a single choice. The line looks like nothing at the scale where you would test it by eye and is load-bearing at the scale where you would ship it.

**Line 133, the mask, and why it is a matrix.** This is my favourite piece of the file, because the obvious implementation is wrong in an interesting way.

You want position 2 to be unable to see position 3. The instinct is a conditional: skip the future entries. Look at what the code does instead, lines 81 to 84:

```python
    return [
        [0.0 if col <= row else NEG_INF for col in range(length)]
        for row in range(length)
    ]
```

It builds a matrix of zeros and negative infinities, and adds it to the scores.

```
  3a. + causal mask
    [  0.1255     -inf     -inf     -inf ]
    [ -0.0066  -0.6858     -inf     -inf ]
    [ -0.1993   0.1213   0.1840     -inf ]
    [ -0.0458   0.0037   0.0299  -0.0931 ]
```

The reason is the next step. Softmax exponentiates, and e to the power of negative infinity is exactly zero, not approximately zero. So a forbidden position receives weight `0.0`, and because the denominator is the sum of the exponentials, the remaining weights renormalise among themselves automatically. An `if` statement would have needed you to remember to renormalise, and forgetting is silent. The docstring on `causal_mask` puts the stakes plainly, and it is not exaggerating: getting this wrong produces excellent training loss and a useless model, because the model has been reading the answer.

**Line 134, softmax, and the budget.**

```
  3b. softmax per row
    [  1.0000   0.0000   0.0000   0.0000 ]
    [  0.6636   0.3364   0.0000   0.0000 ]
    [  0.2601   0.3584   0.3816   0.0000 ]
    [  0.2449   0.2573   0.2642   0.2336 ]
```

Look at the shape of that. Row 0 has no choice at all: position zero can only see itself, so it gets 1.0 and the budget argument is trivially satisfied. Row 3 can see everything and spreads roughly evenly. The staircase is the causal mask made visible.

Check row 1 by hand. The two live scores are -0.0066 and -0.6858. Softmax subtracts the row maximum first, so we exponentiate 0 and -0.6792. That is 1.0 and 0.50705, summing to 1.50705. Divide: 0.66354 and 0.33645. The table says 0.6636 and 0.3364. Position 1 gave two thirds of its budget to position 0 and one third to itself, and there was never any more than one to give.

That maximum subtraction is `lib/linalg.py` line 168, and it is the other quietly important line in this stack. It cancels exactly in the ratio, so it changes no result, and without it `math.exp` overflows on large scores. Directly above it, line 169, is a guard I want to praise:

```python
        if row_max == float("-inf"):
            raise ValueError(f"row {r} is entirely masked, softmax is undefined")
```

A fully masked row has no valid target. The tempting behaviours are to return zeros or to let the division produce NaN. Both hand you a number. This raises, and it names the row.

**Line 135, spending the budget.** `matmul(weights, values)` is the weighted average, and this is the step the morning essay was about. Row 3's output is 0.2449 of position 0's value row, plus 0.2573 of position 1's, plus 0.2642 of position 2's, plus 0.2336 of position 3's. One point, blended, and the blend cannot be undone.

## Two heads, one row

Here is the same row 3, as each of our two heads sees it:

```
  head 0 row 3:  [0.2449 0.2573 0.2642 0.2336 ]
  head 1 row 3:  [0.3688 0.2540 0.1389 0.2383 ]
  total variation distance: 0.1286
```

Head 1 gives position 0 half again as much attention as head 0 does, and gives position 2 roughly half as much. Two budgets, spent differently, from the same input.

The honest caveat, repeated from this morning because it is the caveat most often dropped: nothing here is trained. These are seeded random projections. I am not telling you head 1 has learned anything, because head 1 has learned nothing. The 0.1286 is what the architecture provides before any learning happens, which is a starting point rather than a result.

## Putting them back together

Lines 249 to 254:

```python
        for head in self.heads:
            head_output, head_weights = head.forward(x, mask)
            outputs.append(head_output)
            weights_per_head.append(head_weights)
        concatenated = hstack(outputs)
        return matmul(concatenated, self.w_output), weights_per_head
```

Each head gave us a 4 by 2. `hstack` lays them side by side into a 4 by 4, which is back to d_model, because the heads divided the width rather than adding to it. Then one more matrix, `w_output`, built on line 227, projects that back to d_model.

```
  concatenated   (line 253)
    [  0.9992  -1.1058   0.1934   1.2776 ]
    [  0.6779  -0.4354   0.2876   0.8234 ]
    [ -0.2563   0.4394   0.1111  -0.1391 ]
    [ -0.0950   0.0968   0.1843   0.2847 ]

  final = concat W_o   (line 254)
    [  0.6525  -0.2160  -0.6316   1.1683 ]
    [  0.3679  -0.3027  -0.4008   0.6380 ]
    [ -0.1850  -0.1543   0.0577  -0.2983 ]
    [  0.0024  -0.2542  -0.1570   0.0521 ]
```

Input was 4 by 4. Output is 4 by 4. That shape preservation is not decoration; it is what lets you stack these layers at all.

## The one line that is an honest tradeoff, not a bug

Line 249:

```python
        for head in self.heads:
```

Every head is independent of every other head. They share the input, they share the mask, and they never look at each other. That independence is the single most exploitable property of the entire design, and in any real implementation it is exploited hard: the heads become one batched matrix multiply, computed together, and the reason multi-head attention is practical at all is that "eight heads" costs one operation rather than eight.

This line runs them one after another, in a Python loop, on one core.

I want to defend it, and then tell you exactly what it costs.

The defence is that this file's job is to be read. A batched implementation replaces the loop with a reshape from `(n, d_model)` to `(n, h, d_head)`, a transpose to put the head axis first, and a matmul that broadcasts over it. That is three lines of index gymnastics that produce the same numbers and teach nobody anything about attention. The module docstring commits to the goal of making the forward computation legible rather than fast, and this line honours that commitment.

The cost is that the code demonstrates none of the parallelism it is explaining. A reader could walk away thinking heads are inherently sequential, which is the opposite of true.

Here is what it actually costs, measured today at d_model 128 over 64 positions:

```
   heads   d_head    seconds   vs 1 head
  --------------------------------------
       1      128     0.2485       1.00x
       2       64     0.2503       1.01x
       4       32     0.2571       1.03x
       8       16     0.2664       1.07x
      16        8     0.2813       1.13x
```

Read that as ratios, not seconds. This is one machine and one run: an earlier run today gave 1.00, 1.07, 1.04, 1.07 and 1.14 for the same rows, so treat anything below about ten percent as noise.

What survives the noise is the shape. Going from one head to sixteen barely moves the clock. That is this morning's cost-neutrality claim showing up in wall time: the scores cost n times n times d_model multiply-adds no matter how you partition the width, so sixteen narrow heads do the same arithmetic as one wide one. The slow creep to 1.13x is the interpreter, paying for sixteen Python objects and sixteen loop iterations instead of one.

And notice what is missing from that table. Nothing gets faster. In a batched implementation these rows would still be roughly flat, because the work is the same, but they would all be a great deal lower than 0.2485 seconds. The loop is honest about the arithmetic and silent about the engineering, and now you know which is which.

There is a smaller tradeoff worth flagging in the same breath. `causal_mask` materialises a full n by n matrix of floats to express a rule that is just "column index is greater than row index". At four positions that is sixteen floats. At four thousand it is sixteen million, allocated to store a comparison. Production implementations do not build it. This one does, because a mask you can print is a mask you can debug, and you saw the staircase.

## Seven ways to be told no

The last thing I want to show you is the part of the file that is not the algorithm. Roughly a third of `lib/attention.py` and `lib/linalg.py` exists to refuse. Every one of these is triggered on purpose by the trace script:

```
  query and key widths disagree
    ValueError: queries have width 2 but keys have width 3

  more keys than values
    ValueError: keys have 2 rows but values have 1: every key must have exactly one value

  mask does not match the score matrix
    ValueError: mask is (1, 2) but scores are (1, 1)

  head count does not divide d_model
    ValueError: d_model 64 is not divisible by num_heads 5

  input is not as wide as the model
    ValueError: input is 2 wide but this head expects 4

  every position in a row is masked
    ValueError: row 0 is entirely masked, softmax is undefined

  a ragged matrix
    ValueError: row 1 has width 1, expected 2: matrix is ragged
```

Every message names both offending shapes. That is deliberate, and it is the difference between a two-minute fix and a two-hour one. `lib/linalg.py` says why in its own docstring: a silent shape error in attention code produces plausible-looking numbers that are wrong. Attention is unusually good at this. Multiply the wrong pair of matrices and you frequently still get a matrix, softmax still returns rows that sum to one, and the model still trains. It just trains on nonsense.

The divisibility check on lines 216 to 219 is the one I would most want in the middle of the night. Ask for five heads on a 64-wide model and you get told immediately, by name, instead of silently receiving a model that is 60 wide because integer division rounded your width down and threw four dimensions away.

## What to take home

The mechanism is four lines. The reason production attention code is thousands is partly performance, and partly that everything around those four lines is refusing to guess.

If you have been meaning to build an intuition for this, my suggestion is narrow: pull the trace script, change one thing, and look at what moves. Delete the mask and watch the staircase fill in. Remove the division on line 126 and push d_head up, and watch the softmax rows go from a spread to a spike. Ask for a head count that does not divide the width and read the error you get. Twenty minutes of that is worth more than a diagram, because the numbers argue back.

Bookmark this; you will need it at 3am someday, and probably in the form of a shape error that names two numbers you were certain were the same.

---

*Tomorrow, 09:00: the case study. What these mechanisms look like at the scale where the choices stop being aesthetic.*
