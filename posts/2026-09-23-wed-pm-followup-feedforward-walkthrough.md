# Week 4 · Wed 2026-09-23 · 17:00 · Tracing the code that implements feed-forward blocks

> Calendar row: W4 Wed PM, 17:00 (CSV row `55:4`). Format: repo walkthrough.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 2.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + human-first voice + prose style
> rules 1 through 7.
>
> **Canonical source rule, and what it changes about this format.** The
> committed CSV hook for this row names an external repository and says the
> walkthrough will read its implementation "line by line". Per `AGENTS.md`,
> the repo walkthrough format means **our** repository: 100 calendar rows use
> this format and each one walks an implementation committed here. The
> external string is an internal routing hint and appears nowhere below. The
> file walked is `lib/feedforward.py`, written in this repository, pushed
> before this article.
>
> Committed calendar beats, all three present: point to the exact file and
> read every line of the relevant implementation | trace one path through the
> code end to end, recomputing the real values | name the one line that is an
> honest tradeoff rather than a bug.
> Committed CTA: "Repost this so your team sees it."
>
> Every value traced below is from `experiments/week-04/feedforward_lab.py`,
> run 2026-09-15, exit 0, stdout md5 `2aea2a2f7af00f3f26d3e3300d5e4321`.
>
> Adversarial review record (2026-09-15):
> - Every line quoted is copied verbatim from the committed file, and the
>   traced values are from the committed script's stdout ✓
> - The "honest tradeoff" line is a real design decision with both sides
>   stated, rather than a manufactured flaw ✓
> - The traced numbers are labelled as untrained-weight values ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 1,170 words. Above the 500 to 700-word evening band,
>   because a walkthrough has to carry the code it walks. Consistent with the
>   deviation recorded for this format on 2026-09-01 and 2026-09-09 ✓
>
> **Reader-facing repository pointer (convention adopted 2026-09-14).** Every
> 17:00 post carries a short block naming the public repository directly, so a
> reader who arrives at the evening post can reach the articles, the code and
> the issue tracker in one hop. The URL is written as `Technologues` rather
> than as a `systemdesign` URL, because `tools/publish_public.py` rewrites only
> `.../systemdesign/blob/main/` file links; a bare source-repository root URL
> would survive unrewritten and its own verifier would flag it as a foreign
> repository. The block is an addition to the committed beats, not a
> substitution for any of them.
> - Zero em dashes. No sentence opens with a conjunction. No collapsed
>   contrastive framing. Verified by `tools/prose_gate.py` ✓

---

**Topic:** Reading the feed-forward implementation in this repository, one path end to end

**Subtitle:** Three short functions, one traced position, and one line that looks like a shortcut and is a deliberate decision with a cost on both sides.

Good evening. This morning's argument was that a feed-forward block's output is a weighted sum of fixed directions. Here is the code that does it, in [`lib/feedforward.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/feedforward.py), and one position traced all the way through.

## The forward pass, in two functions

```python
    def hidden(self, rows):
        """Return the post-activation hidden layer, (n, d_hidden)."""
        _, width = shape(rows)
        if width != self.d_model:
            raise ValueError(
                f"input is {width} wide but this network expects {self.d_model}"
            )
        projected = matmul(rows, self.w_in)
        return [[self.activation(value) for value in row] for row in projected]

    def forward(self, rows):
        """Project up, activate, project back down."""
        return matmul(self.hidden(rows), self.w_out)
```

`forward` is one line of work. The reason the hidden layer is a separate public method rather than a local variable is the whole point of the module: the hidden layer is the interesting object. It is the set of weights in the key-value reading, its zero fraction is the sparsity an inference kernel would want to exploit, and if it is buried inside `forward` then measuring any of that means reimplementing the first half of the function somewhere else and hoping the two stay in step.

Notice what `hidden` checks. A width mismatch raises with **both** widths named. A wrong-width input in a matrix pipeline produces either a crash three functions later or, worse, a plausible-looking answer, so the check happens at the boundary where the information to explain it still exists.

## The decomposition, which is the module's reason to exist

```python
def decompose_output(hidden_row, w_out):
    """Return each hidden unit's contribution to one output row, separately."""
    rows, _ = shape(w_out)
    if len(hidden_row) != rows:
        raise ValueError(
            f"hidden row is {len(hidden_row)} wide but w_out has {rows} rows"
        )
    return [
        [weight * value for value in w_out[index]]
        for index, weight in enumerate(hidden_row)
    ]
```

Four lines of substance. For each hidden unit, scale that unit's row of `W_out` by that unit's activation. Sum the results and you have the output, which is what `matmul` computes in one go.

Writing it out costs `d_hidden` times `d_model` multiplications, exactly what the matrix multiply costs, so this is not slower. What you get for the same arithmetic is the terms, separately, and the terms are what let you ask which units did the work.

## One path, end to end

Position 0, `d_model` 64, `d_hidden` 256, ReLU, seed 42.

**Step 1. Project up.** The 64-wide input row meets `w_in`, which is 64 by 256, giving 256 pre-activation numbers.

**Step 2. Activate.** ReLU clips everything below zero. Of the 256 units, **124 survive** and 132 become exactly 0.0. Across the whole 32-position input the zero fraction is 0.5012, which is what a symmetric random projection gives.

**Step 3. Decompose.** Take those 124 live activations and scale each unit's output row. Rank the terms by length:

```
    unit  204   activation   1.2385   contribution 0.7757
    unit  162   activation   1.3319   contribution 0.7606
    unit  104   activation   1.2541   contribution 0.7420
    unit  224   activation   1.0239   contribution 0.6804
    unit  113   activation   0.9970   contribution 0.6741
```

Unit 162 fires hardest and finishes second, because unit 204's output direction is a little longer. That inversion is the reason `dominant_units` ranks by term length rather than by activation, and there is a test named for exactly that case.

**Step 4. Sum.** Add the 256 terms, 132 of which are identically zero. Compare against the matrix multiply:

```
  largest disagreement with the matrix multiply, over all 32 positions
  and all 64 output dimensions: 0.0e+00
```

Twenty-eight of the 124 live units carry half the total length. Seventy-eight carry ninety percent. All of this is on untrained weights, so read it as the floor rather than as a fact about any model you use.

## The line that is a tradeoff rather than a bug

This one:

```python
def equivalent_gated_hidden(d_hidden):
    exact = 2 * d_hidden / 3
    rounded = int(exact // 8) * 8
    return max(8, rounded)
```

Look at `//8` then `*8`. Two-thirds of 2048 is 1365.33, and this returns 1360, throwing away 5.33 units of width. A reader could reasonably call that a bug: the parameter-matched answer is 1365, and 1360 misses parity by 0.39%.

Both sides, stated fairly.

**For rounding.** Hardware wants aligned shapes. A hidden width that is not a multiple of the tile size a kernel uses produces a ragged final tile, and the ragged tile costs more than the 5 units of width are worth. Every released configuration I have looked at rounds, which is why hidden widths in real models are always tidy numbers and never exactly two-thirds of anything.

**Against rounding.** The function is now lossy and the loss is silent. It returns 1360 and says nothing about the 5.33 it discarded, so a caller who believes they are parameter-matched is 0.39% under.

The decision I made is to round down rather than to the nearest multiple, so the error always has the same sign. A gated block built this way is never accidentally **larger** than the ungated one it claims to match, which means a parameter comparison built on it can be quoted as an upper bound. A test asserts exactly that, at three different widths, and asserts the result stays within 1% so the rounding cannot quietly become a real gap.

That is the shape of the tradeoff. The function is imprecise on purpose, the imprecision has a chosen direction, and the direction is chosen so the resulting claim is still safe to make.

## Run it

```
python3 experiments/week-04/feedforward_lab.py
python3 -m unittest tests.test_feedforward
```

Under a second for the first, 52 tests for the second.

## The code, and where to take it apart

Everything in this post lives in one repository, the articles and the implementations together:

**https://github.com/QuantumindSSI/Technologues**

```bash
git clone https://github.com/QuantumindSSI/Technologues.git
cd Technologues
python3 experiments/week-04/feedforward_lab.py
python3 -m unittest discover -s tests -t .
```

Python 3.8 or newer, standard library only, so there is no install step and no requirements file. The README there indexes every article published so far, and each one names the file its numbers came from. The suite runs 460 tests.

The repository is generated, so a pull request against an article will not stick. Raise an issue instead, and if a number in this post does not reproduce on your machine, that is exactly the kind of issue I want.

Repost this so your team sees it, especially if somebody there is about to write a pruning or quantisation proposal that assumes a hidden layer's activations are the right thing to rank by.

---

*Tomorrow, 09:00: a case study on grouped-query attention. The memory saving is exactly linear and everybody quotes it. The measurement I did not expect is what it does to the number of directions of the residual stream that the routing can read, and what happens to a position moved along one of the directions it cannot.*
