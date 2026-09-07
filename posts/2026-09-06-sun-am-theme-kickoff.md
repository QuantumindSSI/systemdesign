# Week 3 · Sun 2026-09-06 · 09:00 · Theme kickoff: LLM Internals and Pretraining, Foundations part 1

> Calendar row: W3 Sun AM, 09:00 (CSV row `36:3`). Format: theme kickoff.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule applied (effective today).** This repository is the
> only code repository this article references. The CSV `source` column for
> this row names an external repository; per `AGENTS.md` that string is an
> internal routing hint and does not appear below in any form. Every
> implementation this week needs was written here first.
>
> Artifacts written for this post and committed here:
> - `lib/linalg.py`, `lib/bpe.py`, `lib/attention.py`: standard library only,
>   no third-party numeric stack, so every artifact runs with no install step.
> - `tests/test_linalg.py`, `tests/test_bpe.py`, `tests/test_attention.py`:
>   81 tests, all passing on today's run
>   (`python3 -m unittest discover -s tests -t .`).
> - `data/week-03/tokenizer_corpus.txt`: 260,242 bytes of our own prose, frozen.
>   Provenance and known bias in `data/week-03/README.md`.
> - `experiments/week-03/vocab_vs_tokens.py`: the measurement quoted below,
>   three assertions, exit code 0 with "All assertions passed", about one
>   minute of runtime.
>
> **Two defects the tests caught before publication, recorded because the
> series claims tests do this.** First, training was asserted to reach the
> requested vocabulary size; on a low-variety corpus it stops early instead,
> so the contract is documented as an upper bound and the test was rewritten
> to the real behaviour. Second, the fast indexed trainer disagreed with the
> naive trainer on tie-breaking: heap decrements were never pushed back, so a
> pair whose count dropped could vanish from consideration. The oracle test
> `test_indexed_strategy_matches_the_naive_oracle` failed, the bug was fixed,
> and both strategies now produce identical merges.
>
> Measured today by `experiments/week-03/vocab_vs_tokens.py`:
> - corpus 260,242 bytes; token counts 260,242 / 121,888 / 90,188 / 70,669 /
>   57,580 at vocabulary 256 / 512 / 1,024 / 2,048 / 4,096
> - each doubling removes 53.2%, then 26.0%, then 21.6%, then 18.5% of the
>   remaining tokens
> - bytes per token rises 1.00, 2.14, 2.89, 3.68, 4.52
> - held-out segmentation at vocabulary 4,096: 7 tokens for an in-domain
>   sentence, 17 for the same shape of sentence containing 1234567, 21 for
>   `order_id=8f3a91c4 status=PENDING`
> - `1234567` becomes `['12', '3', '4', '5', '6', '7']`
>
> Non-repository sources fetched and read today (2026-09-06), all permitted
> under the canonical source rule:
> - Vaswani et al., "Attention Is All You Need", arXiv:1706.03762v7. Quoted:
>   the scaled dot-product motivation including the word "suspect", the
>   multi-head motivation, Table 1's self-attention row, h = 8 with
>   d_k = d_v = d_model / h = 64, d_model = 512, N = 6, 8 NVIDIA P100 GPUs,
>   100,000 steps or 12 hours for base, 300,000 steps or 3.5 days for big, and
>   the big configuration's 28.4 BLEU on WMT 2014 English to German with 41.8
>   on English to French.
> - Sennrich, Haddow and Birch, arXiv:1508.07909v5. Quoted: BPE adapted from
>   Gage (1994), "a compression algorithm", and the up to 1.1 and 1.3 BLEU
>   result over a back-off dictionary baseline on WMT 15 English to German and
>   English to Russian.
> - Su et al., "RoFormer", arXiv:2104.09864v5. Quoted: absolute position via a
>   rotation matrix with explicit relative position dependency, and the three
>   claimed properties.
> - Xiong et al., arXiv:2002.04745v2. Quoted: Post-LN's large expected
>   output-layer gradients at initialization, Pre-LN's well-behaved gradients.
> - Radford et al., "Language Models are Unsupervised Multitask Learners"
>   (GPT-2), PDF fetched and text-extracted today. Quoted: "The vocabulary is
>   expanded to 50,257" and Table 2's smallest configuration, 117M parameters,
>   12 layers, d_model 768. The 38,597,376 figure is arithmetic on 50,257 and
>   768, and the one-third share is that figure over the paper's rounded 117M.
>
> **Continuity note (flagged, not papered over).** The tracked sequence has no
> Sun 2026-08-30 kickoff and no Sat 2026-08-29 recap, so this is the first
> theme kickoff since Sun 2026-08-23. Saturday's three quiz questions were
> promised answers on Monday 2026-09-07; this post withholds them.
>
> Adversarial review record (2026-09-06):
> - Every measurement is from our own committed artifact on our own committed
>   corpus, and the corpus bias is stated in the body, not only in its README ✓
> - The compression curve is presented as the shape of a result on a small
>   single-domain corpus, explicitly not as a general-purpose tokenizer
>   benchmark ✓
> - The 2017 training figures are labeled as that paper's translation
>   experiments, with 28.4 and 41.8 attributed to the big configuration ✓
> - Vaswani et al.'s scaling explanation is quoted with its hedge, "suspect" ✓
> - Xiong et al.'s result is stated as a claim about warm-up and gradients at
>   initialization, not as "pre-norm is better" ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,895 words, measured 2026-09-06 by whitespace split
>   over everything below the `---` marker. Within the committed 2,500 to
>   3,500-word 09:00 range ✓
> - Zero em dashes.

---

**Topic:** Week 3 kickoff: what actually happens inside a language model, from the tokenizer to where you put the layer norm

**Subtitle:** Six mechanisms, one per day, each one written from scratch in this repository so you can run it. It starts with a measurement showing the same sentence costing 7 tokens or 21, depending on what is in it.

Good morning, and welcome to a new pillar.

For two weeks we lived on the outside of systems. Cache keys, DNS paths, write strategies, eviction, stampedes. All of it was about the space between components: what one machine assumes about another, and what happens when the assumption stops holding. That work is not finished, but it is paused. This week we go inside the model.

Here is the everyday version of why. Most of us have owned an appliance we could operate perfectly and could not diagnose at all. The microwave is my favourite example. You know every button. Then one evening the food comes out scalding at the edges and cold in the middle, and no button fixes it, because the fix requires knowing that the thing heats water unevenly and that stirring halfway through is physics rather than folklore. You did not need the mechanism until the day the appliance behaved in a way the buttons could not explain.

That is roughly where a lot of very good engineers are with language models right now. We can prompt them, stream them, retry them, cache them, and put a queue in front of them. Then something strange happens. A model that reasons fine about a paragraph mangles a seven-digit invoice number. A prompt that works at 2,000 tokens degrades at 30,000. A model that reads a document beautifully cannot reliably say what the third bullet point was. The buttons do not help, because the behaviour comes from the mechanism.

**The single reason this pillar matters at this angle right now: more engineers are shipping model-backed features than can explain what the model does to their input before the first matrix multiply, and almost every "the model is being weird" bug lives in that gap.**

So this is the foundations pass. Not research, not a survey of the frontier. Six mechanisms, one per day, each one written from scratch in this repository, in plain Python with no numeric library underneath, so that nothing is hidden inside a call you cannot read.

## One minute that makes the week concrete

Before any theory, a measurement. Everything below comes from code in this repository, run today.

I trained our own byte-level tokenizer ([`lib/bpe.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/bpe.py)) on our own corpus ([`data/week-03/tokenizer_corpus.txt`](https://github.com/QuantumindSSI/systemdesign/blob/main/data/week-03/tokenizer_corpus.txt), which is 260,242 bytes of the prose from the first two weeks of this series) at five vocabulary sizes, and counted the tokens:

```
  vocab  merges    tokens  bytes/token  cut vs previous
-------------------------------------------------------
    256       0    260242         1.00         baseline
    512     256    121888         2.14            53.2%
   1024     768     90188         2.89            26.0%
   2048    1792     70669         3.68            21.6%
   4096    3840     57580         4.52            18.5%
```

Read the last column downward. The first 256 merges cut the token count by more than half. The next 512 merges cut what remained by 26.0%. The next 1,024 by 21.6%. The next 2,048 by 18.5%.

Every step doubles the vocabulary. Every step buys less. You are paying twice as much for a smaller and smaller share of what is left, and the curve does not straighten out later; it keeps flattening. That is the honest shape of the tradeoff, and it is why "just use a bigger vocabulary" is a decision with an argument on both sides rather than a free improvement.

Now the part I found more useful. Here is how the largest of those tokenizers cuts up four strings it never saw in training:

```
    7 tokens  ['the', ' cache', ' expired', ' before', ' the', ' request', ' arrived']
   17 tokens  ['the', ' inv', 'o', 'ice', ' total', ' was', ' 12', '3', '4', '5', '6', '7', ' d', 'ol', 'l', 'ar', 's']
   21 tokens  ['ord', 'er', '_', 'id', '=', '8', 'f', '3', 'a', '9', '1', 'c', '4', ' status', '=', 'P', 'E', 'N', 'D', 'IN', 'G']
    4 tokens  ['un', 'h', 'app', 'iest']
```

The first sentence costs 7 tokens, one per word, because the corpus was two weeks of writing about caches and the tokenizer learned "cache", "expired" and "request" as single symbols. The second sentence is the same shape of English and costs 17, because "invoice" was rare enough to shatter into three pieces and the number shattered into six. The third is an ordinary log line and costs 21 tokens for 32 characters.

The number is worth sitting with on its own. At a vocabulary of 4,096, `1234567` becomes `['12', '3', '4', '5', '6', '7']`. Not "one million two hundred thousand". Not even seven digits. One arbitrary two-digit fragment and five loose digits, because merges are learned by frequency and an arbitrary seven-digit number is not frequent in anybody's corpus.

That is the mechanism behind a bug you may have met. **The model never receives your number.** It receives the pieces that frequency happened to leave, and if you then ask it to do arithmetic, it is doing arithmetic on that. No amount of rewording the prompt changes what the tokenizer did before the prompt arrived.

Now the caveat, because this measurement has a real limit. Our corpus is small, single-domain, and single-author. That is exactly why in-domain prose does so well and a log line does so badly, and a general-purpose tokenizer trained on a web-scale corpus would flatten that gap considerably. So do not carry these absolute numbers anywhere. Carry the shape: vocabulary growth has diminishing returns, and what fragments is whatever your training corpus did not see often.

There is a habit hiding in that, and it is worth adopting this week regardless of what else you take from the series. Most of us estimate token counts using tidy example sentences, because tidy example sentences are what appear in documentation. Your production traffic is not tidy. Take twenty real strings out of your own logs, run them through the tokenizer your model actually uses, and look at the boundaries rather than only the totals. It takes ten minutes and it tends to change at least one assumption about cost, truncation, or why a particular field keeps getting garbled.

## The six mechanisms, in order

The order is not arbitrary. Each day's topic is the thing you need in order for the next day's topic to be explainable rather than memorable.

**Monday: self-attention mechanics.** The whole week rests here. We will build the mechanism from the question it answers, which is how a position in a sequence decides which other positions matter to it, working through [`lib/attention.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/attention.py) line by line. The scaling factor is a good example of why the details earn their place. Vaswani et al. do not divide by the square root of the key dimension for decoration. They write that they "suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients" (arXiv:1706.03762), and they back the suspicion with a footnote about how the variance of a dot product grows with dimension. Note the word "suspect": a stated hypothesis with an argument attached, not a theorem. Monday measures it rather than repeating it.

The same paper contains the table I would put on the wall. For a sequence of length n and representation dimension d, self-attention costs O(n squared times d) per layer, but needs only O(1) sequential operations and has a maximum path length of O(1) between any two positions, against O(n) for both in a recurrent layer.

That middle column deserves a plain-language translation, because it is the reason the architecture won. "Maximum path length O(1)" means a word at position 3 and a word at position 30,000 are one step apart inside a layer. In the recurrent designs that came before, information had to be carried through every intervening position, so those two words were 30,000 steps of a chain apart, and long-range relationships had to survive that whole journey. Attention replaced a relay race with a room where everyone can address everyone. The gain is enormous, and the bill arrives in the first column, because a room where everyone addresses everyone grows with the square of the number of people in it.

**Tuesday: multi-head attention, twice.** In the morning, the mechanism at the level of outcomes. The original justification is one sentence and worth quoting exactly: multi-head attention "allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this." The base model in that paper uses h = 8 heads with d_k = d_v = d_model / h = 64, and since d_model is 512, the heads split the same width rather than adding to it, which is why the paper can say the total computational cost is similar to single-head attention at full dimension. Adding heads does not add width; it divides the width you already had into more, narrower questions.

In the evening, the code: a line-by-line walk of `MultiHeadSelfAttention` in [`lib/attention.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/attention.py), tracing one path through it with real numbers you can reproduce, because the weights are initialised from a seed rather than trained.

**Wednesday: BPE tokenization, as a case study and then as runnable code.** This is the mechanism behind this morning's measurement. The subword idea solved a specific, dated, very concrete problem: fixed vocabularies against an open-vocabulary task. Sennrich, Haddow and Birch adapted byte pair encoding from Gage (1994), described in their own words as "a compression algorithm", to word segmentation, and reported improvements of up to 1.1 and 1.3 BLEU over a back-off dictionary baseline on WMT 15 English to German and English to Russian (arXiv:1508.07909). Two things are worth noticing already. The gains were real and they were roughly one BLEU point, not a miracle. And the technique came from compression, which is exactly why token boundaries follow frequency rather than meaning.

Wednesday evening walks [`lib/bpe.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/bpe.py), including the part I would normally hide: it contains two trainers, a naive one that recounts everything on every round, and a fast one with a pair index and a heap. The fast one had a real bug, the naive one is the oracle that caught it, and that is a better lesson than either implementation alone.

**Thursday: embedding layers, hands-on.** An embedding layer is the least mysterious component in the model and the one most likely to be sized wrong, so it gets the tutorial slot. One number sets up the whole hour. The GPT-2 paper states that "the vocabulary is expanded to 50,257", and its Table 2 gives the smallest configuration as 117M parameters, 12 layers, and a width of 768. So the token embedding table alone holds 50,257 times 768, which is 38,597,376 parameters. That is arithmetic on two numbers from one paper, not a benchmark, and it is enough to make the point: a table you might describe as "just a lookup" is roughly a third of that model's parameters, before a single transformer block exists.

**Friday: rotary positional encodings, and an argument.** Attention as defined on Monday has no idea what order anything is in, which means position has to be injected. RoPE is one widely used answer and the one Friday takes on. Su et al. describe it as encoding "the absolute position with a rotation matrix" while incorporating "the explicit relative position dependency in self-attention formulation", and claim three properties from that: flexibility of sequence length, decaying inter-token dependency as relative distance grows, and compatibility with linear self-attention (arXiv:2104.09864). Friday morning is a contrarian take on how that gets repeated in practice; the evening is a debate prompt.

**Saturday: pre-norm versus post-norm layer normalization.** The week closes on the smallest-looking decision with the largest training consequences: where the layer norm goes relative to the residual connection. Xiong et al. proved with mean field theory that at initialization, in the original Post-LN arrangement, "the expected gradients of the parameters near the output layer are large", which makes a large learning rate unstable and is why the warm-up stage exists. Move the normalization inside the residual block and "the gradients are well-behaved at initialization", which motivated removing warm-up entirely (arXiv:2002.04745).

## What you will be able to do by Saturday

Concretely, and I would rather under-promise here.

You will be able to explain self-attention to another engineer without a diagram, including why the dot products are scaled and what the quadratic term actually costs you. You will be able to read a multi-head attention implementation and say what every projection is for. You will be able to look at a tokenizer's output for your own data and predict where it will fragment badly, which is a real debugging skill the moment your inputs contain identifiers, numbers, code, or a language the merge table saw little of. You will be able to size an embedding table and name the mistakes that make one silently wrong. You will be able to say what positional information is for, why absolute and relative encodings differ, and what RoPE is claimed to buy. And you will be able to explain why the position of a layer norm changes whether you need a warm-up schedule.

You will not be able to pretrain a competitive model, and nothing this week will suggest otherwise. Pretraining at scale is a distributed systems problem, an infrastructure problem, and a data problem, and those have their own weeks later in the calendar.

## What this week deliberately leaves out

Scope fences, stated up front so nobody waits for something that is not coming.

Serving and inference optimization, including KV caching and batching, belongs to the Inference and Edge Deployment weeks. Post-training, instruction tuning and alignment belong to their own pillar. Training infrastructure, checkpointing and cluster economics belong to the MLOps weeks. Retrieval, tool use and agent loops belong to Harness and Loop Engineering. When something this week touches one of those, I will name the connection and then leave it alone.

There is also a limit worth naming about the sources. Two of the four papers above are from 2017 and 2015 by their arXiv posting dates. They are foundational and they are old, and a well-known architecture detail from 2017 is not automatically what a 2026 production system does. Where a paper's number is specific to its own experiment, I will say so. The 2017 translation models were trained on one machine with 8 NVIDIA P100 GPUs: 100,000 steps or about 12 hours for the base configuration, and 300,000 steps or 3.5 days for the big one, which is the configuration that reached 28.4 BLEU on WMT 2014 English to German and 41.8 on English to French. Those figures describe that experiment, and they are a useful anchor for how small the original public demonstration was.

## How to follow along

One prerequisite: comfort reading Python, plus enough linear algebra to be unbothered by a matrix multiply. If you can read a `for` loop and you know what it means to multiply a 4 by 8 matrix by an 8 by 2 matrix, you have enough.

Everything this week runs from this repository with no install step, because none of it depends on a third-party numeric stack. Reproduce this morning's measurement with:

```
python3 experiments/week-03/vocab_vs_tokens.py
python3 -m unittest discover -s tests -t .
```

The first takes about a minute and prints the table above followed by "All assertions passed". The second runs the 81 tests behind `lib/`. If either one fails on your machine, that is a bug report I want.

If you are arriving at this pillar boundary for the first time, the rhythm is two posts a day. The 09:00 post is the long one and carries the argument. The 17:00 post is shorter, stays on the same example, and reinforces one piece of it: a diagram on Monday, the code on Tuesday, a runnable model on Wednesday, a mistakes checklist on Thursday, a debate on Friday. Reading only the mornings works. Reading only the evenings does not, because each one assumes the morning.

Housekeeping, and a promise I owe you. Yesterday's recap ended with three questions, one recall, one application, one design tradeoff about a cache in front of a database. The answers were promised for Monday morning and they are still coming Monday morning, at the top of the self-attention post. If you have not answered them yet, today is the day, because the answer to the third one is a judgement call and I want to see yours before I publish mine.

So here is where I would leave you this Sunday. Think about the last time a model did something you could not explain: the number it got wrong, the instruction it dropped halfway through a long document, the output that changed when you moved a paragraph. You probably fixed it by rewording something. That works often enough to become a habit, and it is the reason the mechanism stays invisible. This week is about turning one of those episodes from a mystery you worked around into a component you can name.

Tag someone who is debugging this right now.

---

*Tomorrow, 09:00: self-attention from first principles, plus the answers to Saturday's three questions.*
