# Week 3 · Tue 2026-09-08 · 09:00 · Long-form: One Head Has One Budget, and That Is the Whole Problem

> Calendar row: W3 Tue AM, 09:00 (CSV row `40:3`). Format: concept deep-dive.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every implementation and
> every measurement quoted below was written in this repository.
>
> Committed calendar beats, all three present below: define the failure
> multi-head attention fixes, in two lines with a concrete example | build the
> mechanism conceptually, at the level of outcomes, not code | state what
> multi-head attention still does not do, the gaps the code inherits.
> Committed CTA: "Comment your take - I read every reply."
>
> Format note: per the day-split recorded in `prep/README.md` (2026-08-26),
> Tuesday runs concept in the morning and code in the evening. This post is
> deliberately code-free. The line-by-line reading of `lib/attention.py`,
> including the real 128-position arithmetic, is tonight's 17:00 follow-up,
> `posts/2026-09-08-tue-pm-followup-attention-code-walkthrough.md`.
>
> **Publication-gap note, flagged rather than papered over.** The tracked
> sequence has no Mon 2026-09-07 posts. The calendar assigned single-head
> self-attention to that day, and Sunday's kickoff promised Saturday's quiz
> answers there. Neither reached a reader. This post therefore does not refer
> backward to Monday at all, and carries the single-head mechanism inline as
> primary material, in the section "What one head actually is". A reader who
> has seen nothing since Sunday loses nothing here. Same remediation pattern
> recorded for week 2 in `posts/2026-09-01-tue-am-essay-dns-resolution-paths.md`.
>
> Artifact written for this post, committed here, and linked from the body:
> - `experiments/week-03/attention_heads.py`, 419 lines, Python 3.8+ standard
>   library only. Four claims, each asserted, exit code 0 with "All assertions
>   passed", about three seconds of runtime. It exists partly because
>   `lib/attention.py:25` promised that `experiments/week-03/` measured the
>   score-variance growth and no such measurement had been written. That
>   docstring is now true.
>
> Measured today (2026-09-08) by `experiments/week-03/attention_heads.py`:
> - raw score variance 8.04 / 15.98 / 32.34 / 64.61 / 125.91 / 254.88 / 506.50
>   at d_k 8 / 16 / 32 / 64 / 128 / 256 / 512, so variance over d_k stays
>   inside 0.984 to 1.011 across a 64-fold width range
> - unscaled mean largest softmax weight rises 0.560 to 0.947 over that range,
>   entropy falls 1.319 to 0.134 nats; scaled, the same quantities hold at
>   0.238 to 0.248 and 2.353 to 2.378 nats. A flat row over 16 entries is
>   2.773 nats and 0.062
> - the single-head collision is exact: L2 gap 0.000000 between two different
>   value sets, 1.000000 once two heads carry them
> - parameter count is 16,384 at head counts 1, 2, 4, 8 and 16 with d_model 64,
>   which is 4 * d_model^2 every time; mean pairwise total variation between
>   heads is 0.0000 / 0.1794 / 0.2099 / 0.2631 / 0.2673
>
> Non-repository source, permitted under the canonical source rule:
> - Vaswani et al., "Attention Is All You Need", arXiv:1706.03762. Quoted: the
>   scaled dot-product motivation including the hedge "we suspect"; h = 8 with
>   d_k = d_v = d_model / h = 64 at d_model = 512; and the paper's own
>   statement that the reduced per-head dimension makes the total cost similar
>   to single-head attention at full dimensionality.
>
> Adversarial review record (2026-09-08):
> - Every number in the body is from our own committed artifact, run today,
>   and the seeds are named so a reader reproduces them exactly ✓
> - Head disagreement is reported as the disagreement of RANDOM projections
>   and is explicitly not offered as evidence of learned specialisation. No
>   head is described as "the syntax head" or given any semantic role, because
>   nothing here is trained and that claim would be unsupported ✓
> - The paper's scaling argument is quoted with its hedge intact. Our
>   measurement is presented as confirming the variance arithmetic, not as
>   confirming the gradient claim, which this artifact does not test because
>   there is no backward pass ✓
> - The claim that multi-head is cost-neutral is derived arithmetically and
>   labelled as cost-neutral, never as cost-reducing. The quadratic term is
>   named as untouched ✓
> - The collision example is labelled as constructed, not sampled ✓
> - Reader-facing body: 2,793 words, measured 2026-09-08 by whitespace split
>   over everything below the `---` marker. Within the committed 2,500 to
>   3,500-word 09:00 range ✓
> - Zero em dashes.

---

**Topic:** The mental model for multi-head attention, before you read a line of code

**Subtitle:** A single attention head has exactly one unit of attention to spend per position, and that budget is why one head is not enough. Here is the failure, measured to six decimal places, and the shape of the fix.

Good morning.

Here is a small annoyance that I think about more than is reasonable. A restaurant has two reviews. One person gave it five stars and wrote that the food was extraordinary. The other gave it one star and wrote that they waited ninety minutes for it. The app shows you three stars.

Three stars is also what the app shows when two people each gave it three stars, because it was fine, and neither of them felt strongly.

Those are completely different restaurants. The number cannot tell you which one you are looking at, and no amount of staring at the three will recover the difference, because the difference was destroyed at the moment of averaging. You do not need a better average. You need the app to stop collapsing two opinions into one number.

That is the entire problem multi-head attention exists to solve. I am going to spend the rest of this piece making that sentence precise, and this evening at 17:00 we open the implementation and read it line by line. This morning is only the model.

## The failure, in two lines

A single attention head produces, for every position in the sequence, exactly one probability distribution over the other positions. Probability distributions sum to one, so the head has one unit of attention to spend per position, and every unit spent on one position is a unit not spent on another.

That is the failure. If a position needs information from two places for two different reasons, one head has to trade them off against each other, and whatever comes out is a blend that cannot be un-blended.

I want that to be arithmetic rather than assertion, so here is the concrete example, constructed rather than sampled, and checked by [`experiments/week-03/attention_heads.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/attention_heads.py) in this repository.

Two positions carry information. In the first case they carry different things: position zero holds `[1.0, 0.0]` and position one holds `[0.0, 1.0]`. In the second case they carry the same averaged mush: both hold `[0.5, 0.5]`. Now let one head look at both positions evenly, half its budget on each.

```
  one head attending 0.5 / 0.5:
    DISTINCT -> [0.5, 0.5]
    AVERAGED -> [0.5, 0.5]
    L2 gap between them: 0.000000
```

Zero. Not small. Zero. The head's output for two genuinely different inputs is the same pair of numbers, and every layer downstream receives that pair with no way to recover which situation produced it. This is the three-star restaurant, expressed in the actual arithmetic of the actual mechanism.

Now give the same information to two heads and let each one look at one position:

```
  two heads, one attending to each position, concatenated:
    DISTINCT -> [1.0, 0.0, 0.0, 1.0]
    AVERAGED -> [0.5, 0.5, 0.5, 0.5]
    L2 gap between them: 1.000000
```

The two cases are now distinguishable, and nothing clever happened. Nobody trained anything. The only change is that two separate budgets were spent separately instead of one budget being split.

## What one head actually is

Before going further I owe you the mechanism itself, because the budget argument only lands if you can see where the budget comes from. This section is self-contained, so if the phrase "queries, keys and values" makes you tense slightly, you are in the right place and you are about to stop needing to.

Start with the data. A sequence of n positions is a table with n rows. Each row is a list of d_model numbers describing that position. For a language model, one row is roughly "everything the model currently believes about this one token". Nothing more mystical than that.

Attention answers one question, once per row: given what this position is looking for, which other rows should contribute to its output, and by how much?

To answer it, the same input row gets projected three times, into three different spaces, by three different learned matrices. That sounds like machinery, but the reason is human. Ask yourself three questions about a word in a sentence:

- What am I looking for? That is the **query**.
- What do I offer, if somebody is looking? That is the **key**.
- If somebody does choose me, what do they actually receive? That is the **value**.

These are three genuinely different questions, and nothing forces one representation to serve all three. A word can be a poor match for what you are hunting and still carry the payload you need once you find it. Splitting into query, key and value is just refusing to pretend those are the same thing.

With the three projections in hand, the head does four things, in this order:

1. Compare every query against every key, by dot product. High number means good match. This produces an n by n table of scores.
2. Divide every score by the square root of the head's width. Hold that thought; it is the section after next, and it is the step people skip.
3. Softmax each row. This turns each row of raw scores into a set of weights that are all positive and sum to exactly 1.0.
4. Take the weighted average of the value rows using those weights. That average is the output for that position.

Step three is where the budget appears, and it is not a design choice anybody made lightly. Softmax exists to turn arbitrary scores into something you can average with. To average with weights, the weights have to sum to one, or the output drifts in magnitude depending on how many things you looked at. So the sum-to-one constraint is load-bearing.

It is also, unavoidably, the three-star problem. The constraint that makes the averaging well-behaved is the same constraint that makes it lossy.

## The fix, at the level of outcomes

Here is what I find genuinely elegant about the fix, and it is not the part usually emphasised.

You might expect that giving the model more attention budget means giving it more room: wider projections, more numbers, more parameters. That is not what happens. The heads **divide** the width that already exists rather than adding to it. With d_model of 512 and eight heads, each head is 64 wide, and 8 times 64 is 512. Vaswani and colleagues state this directly: the reduced dimension per head makes the total computational cost similar to single-head attention at full dimensionality.

Which means multi-head attention is not a bigger model. It is the same model, reorganised.

I did not want to take that on trust either, so the artifact counts the actual floats held in the actual matrices, at five different head counts, with d_model fixed at 64:

```
   heads   d_head   parameters   mean pairwise TV
  ------------------------------------------------
       1       64        16384             0.0000
       2       32        16384             0.1794
       4       16        16384             0.2099
       8        8        16384             0.2631
      16        4        16384             0.2673
```

Sixteen thousand three hundred and eighty four, sixteen times over, at every head count. That is 4 times d_model squared, and the four is three projection matrices per head plus one output projection at the end. Going from one head to sixteen changes nothing about the size of the thing. It only changes how the same numbers are partitioned.

The right-hand column is the part that matters. Total variation distance measures how far apart two probability distributions are: zero if identical, one if they have no overlap at all. One head scores 0.0000 because a head cannot disagree with itself, and that zero is the honest baseline. Add a second head and the two of them place their attention differently enough to score 0.1794, and it climbs from there.

I want to be careful here, because this is exactly the point where writing about attention usually goes soft. **Nothing in this measurement is trained.** There is no backward pass and no optimiser anywhere in this repository's attention code. The weights come from a seeded initialiser. So that 0.2631 is what you get from random projections that simply happen to differ, and it is a floor, not a finding. I cannot tell you that head three learned to track pronouns, because head three learned nothing at all. What I can tell you is that the architecture hands training eight separate budgets to work with instead of one, and that they start out already distinct.

The last step is the one that makes it a single mechanism again. Each head produces its own narrow output. Those outputs are laid side by side into one row again, and a final learned matrix projects that row back to full width. That projection is where the model gets to decide how much each head's opinion counts. The heads never negotiate; they report, and something downstream weighs them.

Back to the restaurant. Multi-head attention is the app showing you both reviews and letting you decide, rather than showing you a three.

## The divisor that decides whether any of this works

There is a step two, and it is the step that most explanations mention in half a sentence and move past. It is worth more than that, because if you get it wrong nothing else in this article happens.

The scores in step one are dot products. A dot product over d_k terms is a sum of d_k products, and sums of many independent things spread out. If the components of the query and the key are independent with mean zero and variance one, the variance of their dot product is d_k. Not roughly d_k. Exactly d_k, and it grows without limit as heads get wider.

The paper flags this and is admirably honest about its confidence level, saying it suspects that for large values of d_k the dot products grow large in magnitude, pushing softmax into regions with extremely small gradients. That hedge is in the original text and I am keeping it.

The arithmetic half of the claim is testable without any training, so the artifact tests it. Twenty thousand sampled dot products at each of seven widths:

```
    d_k   measured var   var / d_k
  --------------------------------
      8           8.04       1.005
     16          15.98       0.999
     32          32.34       1.011
     64          64.61       1.009
    128         125.91       0.984
    256         254.88       0.996
    512         506.50       0.989
```

Across a 64-fold range of widths, the ratio never leaves the band 0.984 to 1.011. The variance really is d_k.

Now the consequence, which is the part you can feel. Take two thousand rows of sixteen scores each and softmax them, once raw and once after dividing by the square root of d_k. A perfectly flat row over sixteen entries has entropy 2.773 nats and a largest weight of 0.062.

```
    d_k   raw max w   raw entropy   scaled max w   scaled entropy
  --------------------------------------------------------------
      8       0.560         1.319          0.238            2.378
     64       0.849         0.400          0.247            2.355
    512       0.947         0.134          0.248            2.353
```

Read the raw column and watch the mechanism die. At width 512, the average largest weight is 0.947. The head is putting ninety five percent of its budget on a single position, chosen essentially by which random dot product happened to come out biggest. Entropy has collapsed from 1.319 to 0.134 nats. That is not attention. That is an argmax with extra steps, and it happened without anyone changing the model, purely because the head got wider.

The scaled columns do not move. 0.238 to 0.248 across the whole range, entropy pinned near 2.35 nats. One division by a constant, and head width stops being a variable that silently changes behaviour.

This is my favourite kind of engineering detail, and I say that as somebody who has shipped the opposite. It is a single line, it looks like a normalisation nicety, and removing it does not throw an error, produce a NaN, or fail a shape check. It just quietly turns a soft lookup into a hard one, and you find out much later when the model will not learn and the loss curve looks fine for the first hour.

## What it still does not do

Every mechanism has a boundary, and the gaps here are inherited by every line of code we read this evening. Four of them are worth naming.

**Nothing assigns the heads roles.** This is the big one, and it is the claim I see stated with the most confidence and the least support. There is nothing in the architecture and nothing in the loss that says head one handles syntax and head two handles long-range reference. The heads are structurally identical. They differ at initialisation because random numbers differ, and they may differentiate further under training, or they may end up substantially redundant. The architecture provides the capacity for specialisation. It does not provide specialisation, and a diagram with helpfully labelled heads is describing somebody's interpretation of a trained model, not a property of the mechanism.

**It does not make attention cheaper.** This one gets misread constantly, I think because "parallel heads" sounds like a speedup. Each head compares every position against every position, which is n squared work at the head's own width. Sum that over h heads and the widths add back up to d_model, so the total is n squared times d_model, exactly what one full-width head would cost. Multi-head attention is cost-neutral. It is not cost-reducing, and the quadratic term, the one that decides what happens to your latency and your memory when the context gets long, is completely untouched by it. Every long-context technique you have heard of exists because this paragraph is true.

**Heads cannot consult each other while attending.** They run independently and meet only at the concatenation, after every softmax has already committed its budget. If some relationship in your data requires two heads' evidence considered jointly before deciding where to look, attention cannot form it in this layer. It has to be assembled afterwards, by the output projection or by a later layer entirely. The division into heads buys separation at the cost of coordination, and that is a real trade, not a free win.

**Dividing has a floor.** Look at the sweep table again. At d_model 64, sixteen heads means each head is four numbers wide, and the gain in disagreement from eight heads to sixteen is 0.2631 to 0.2673, which is nearly nothing. Each head's query and key space eventually becomes too small to express a useful distinction. More heads is not monotonically better, and the correct number is an empirical question about your width, not a constant.

There is a fifth gap, and it is large enough that it gets its own day rather than a paragraph here: nothing in this mechanism knows where anything is. Shuffle the rows of the input and, absent a mask, the outputs shuffle identically. Attention as described has no concept of order at all. Position has to be injected from outside, and how you do that is one of the genuinely unsettled parts of this stack.

## The part you can actually use

If you take one thing from this morning, make it the budget. When a model does something inexplicable with a long input, when it fixates on one part of a document and appears blind to another, when adding context makes an answer worse rather than better, the shape of the explanation is very often that something had one unit of attention to spend and spent it somewhere you did not expect. Not a bug. Not a missing feature. A constraint doing exactly what it says.

And when you next read a system that averages several signals into one number before making a decision, in your own code, nowhere near a model, notice that you have built the three-star restaurant. Sometimes that is fine and the average is what you wanted. Sometimes you have just deleted the difference between "extraordinary" and "ninety minutes", and you will spend a week next quarter wondering why the downstream logic cannot tell them apart.

Comment your take. I read every reply, and I am especially interested if you have hit the long-context version of this in production, because the quadratic paragraph above is where most of those stories end up.

---

*This evening, 17:00: we open the implementation and read every line of it, with real numbers. What the four steps look like when you print the actual matrices, why a causal mask is a matrix of negative infinity rather than an `if` statement, the exact arithmetic behind two heads disagreeing by 0.1286 on one row, and the five error paths the code refuses to guess its way past.*
