# Week 3 · Wed 2026-09-09 · 09:00 · Long-form: The Vocabulary Filled Up With Punctuation, and Somebody Had to Notice

> Calendar row: W3 Wed AM, 09:00 (CSV row `42:3`). Format: case study.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every implementation and
> every measurement quoted below was written in this repository.
>
> Committed calendar beats, all three present below: set the scene, company
> scale, constraint, and why this concept was on the critical path | walk the
> decision, the implementation, and the number that moved | close with the
> transferable rule about BPE tokenization.
> Committed CTA: "Tag someone who is debugging this right now."
>
> Format note: per the day-split recorded in `prep/README.md` (2026-08-26),
> Wednesday runs the case study in the morning and the runnable code in the
> evening. This post is deliberately code-free. The line-by-line reading of
> `lib/bpe.py`, the traced merge table and the two implementation traps are
> tonight's 17:00 follow-up.
>
> **Case-study honesty.** No company was invented for this piece. The scene,
> the constraint, the decision and the two design choices are all quoted from
> one published paper by the team that made them. What this repository
> contributes is the counterfactual: the paper states its problem and its fix
> but publishes no number for either, so the cost and the benefit of the fix
> were measured here, on our own corpus, with our own implementation. Those
> numbers describe our corpus. They are not a reproduction of anybody's
> result, and the body says so.
>
> **Publication-gap note, carried forward from Tue 2026-09-08.** The tracked
> sequence still has no Mon 2026-09-07 posts, so a reader may have seen
> nothing between Sunday's kickoff and Tuesday. This post therefore does not
> depend on Monday, and it restates the one thing from Sunday it needs, the
> shape of the compression curve, inline.
>
> Artifacts written for this post, committed here, and linked from the body:
> - `lib/bpe.py` gained three alternative pre-tokenizers,
>   `pre_tokenize_lines`, `pre_tokenize_categories` and
>   `pre_tokenize_category_runs`, plus `char_category`. The default is
>   unchanged: `pre_tokenize` is still the whitespace rule, every function
>   that takes a boundary rule defaults to it, and
>   `experiments/week-03/vocab_vs_tokens.py` re-run today still prints the
>   token counts quoted in Sunday's kickoff, 53.2% / 26.0% / 21.6% / 18.5%.
> - `experiments/week-03/pretoken_boundary.py`, 331 lines, Python 3.8+
>   standard library only. Four claims, each asserted, exit code 0 with "All
>   assertions passed", 31 seconds of runtime.
> - `tests/test_bpe.py` grew from 25 to 47 tests covering the new rules.
>   Whole suite: 214 tests, all passing today.
>
> Measured today (2026-09-09) by `experiments/week-03/pretoken_boundary.py`,
> vocabulary 1,024 throughout, which is 768 learned merges:
> - on a 40,032-byte prefix, the permissive rule spent 306 of its 768 merges
>   on tokens that mix character categories, 68 of which span a word boundary,
>   and still finished with worse compression than the whitespace rule,
>   3.020 against 3.200 bytes per token
> - on the whole 260,242-byte corpus, the whitespace rule spent 35 slots on
>   mixed-category tokens and the category rule spent 0
> - the category boundary costs +1.29% tokens against whitespace
> - dropping the space exception costs +38.21% tokens, 126,257 against 91,351
> - determinism confirmed: two runs, identical md5 of stdout,
>   d4dd969b1f118a5a18496c1c6b4a0c7b
>
> Non-repository sources, permitted under the canonical source rule, fetched
> and read today:
> - Radford et al., "Language Models are Unsupervised Multitask Learners"
>   (GPT-2). PDF fetched from cdn.openai.com and text-extracted locally today.
>   Section 2.2 "Input Representation" quoted verbatim: the "practical middle
>   ground" framing, the base vocabulary of "over 130,000", the "32,000 to
>   64,000 token vocabularies often used with BPE", "a byte-level version of
>   BPE only requires a base vocabulary of size 256", the "sub-optimal merges"
>   observation with the `dog. dog! dog?` example, "we prevent BPE from
>   merging across character categories for any byte sequence", and the space
>   exception sentence. Scale figures from section 2.1 and Table 2: 40 GB of
>   text, vocabulary 50,257, context raised from 512 to 1,024, and the four
>   sizes 117M/345M/762M/1542M.
> - Sennrich, Haddow and Birch, arXiv:1508.07909. Quoted: BPE as an adaptation
>   of a compression algorithm, and the up to 1.1 and 1.3 BLEU improvement.
>   Already quoted in Sunday's kickoff and repeated here because this post
>   does not assume Monday reached anyone.
> - Petrov, La Malfa, Torr and Bibi, "Language Model Tokenizers Introduce
>   Unfairness Between Languages", arXiv:2305.15425, NeurIPS 2023. Abstract
>   fetched and read today. Quoted: tokenization length differences "up to 15
>   times in some cases", and "over 4 times" for character-level and
>   byte-level models.
>
> Adversarial review record (2026-09-09):
> - Every number attributed to the paper is quoted from today's extraction of
>   the paper. Every other number is from our own artifact, run today, on our
>   own corpus, and is labelled as such at the point of use ✓
> - The 306, the +1.29% and the +38.21% are explicitly NOT presented as
>   reproductions of anyone's published result. The paper publishes no
>   equivalent figure. They are our counterfactual on our corpus ✓
> - `pre_tokenize_categories` is described as our implementation of the rule
>   the paper states, never as GPT-2's tokenizer. The real one has more
>   special cases than four character categories ✓
> - The corpus bias recorded in `data/week-03/README.md` is restated in the
>   body, not buried in a README ✓
> - The claim that the boundary is free is refused. It costs 1.29% and the
>   body leads with that ✓
> - Petrov et al. is cited for the disparity it measures and is not used to
>   claim anything about our own corpus, which is monolingual English ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 3,293 words, measured 2026-09-09 by whitespace split
>   over everything below the `---` marker. Within the committed 2,500 to
>   3,500-word 09:00 range ✓
> - Zero em dashes.

---

**Topic:** How the GPT-2 team found their tokenizer wasting vocabulary on punctuation, what they did about it, and what that fix costs when you measure it

**Subtitle:** The fix is one sentence in a paper and nobody publishes its price, so I implemented both sides and measured: it buys back real vocabulary and it costs 1.29% of your compression, and the exception they bolted onto it is worth 38%.

Good morning.

Let me start with the thing on your phone that learns how you type.

You have used it for years. It watches what you write, notices what you write often, and quietly builds a private dictionary so it can finish your sentences. It is a good feature. It is also, if you have ever looked closely at it, a slightly unnerving one, because it has a fixed amount of room and it decides what goes in there entirely by counting.

Counting has no opinions. So if you write "thanks" a lot, and you write "thanks!" a lot, and you write "thanks." a lot, a system that allocates purely by frequency will happily spend three of its slots on one word. Each entry works perfectly. Nothing is broken. You have simply paid three times for something you needed once, and the thing you did not get instead is invisible, because it is the entry that never made it in.

That is not a metaphor for what happened to a language model tokenizer in 2019. That is the same problem, and somebody caught it, wrote down what they saw in one paragraph, and changed the design.

This morning is that paragraph, what was around it, and what the fix actually costs when you build both sides and run them. Tonight at 17:00 we open the implementation and read it line by line. This morning is the decision.

## The scene

The team is at OpenAI. The artifact is GPT-2, described in Radford et al., "Language Models are Unsupervised Multitask Learners". The scale, from the paper: a scraped corpus they call WebText, 40 GB of text, and four models trained on it, at 117M, 345M, 762M and 1542M parameters. The context window was raised from 512 tokens to 1,024.

Now the constraint, because the constraint is the whole reason tokenization was on the critical path rather than being a preprocessing detail somebody handled on a Tuesday.

The paper's claim is about zero-shot transfer: that a model trained only to predict the next token can be evaluated on tasks it was never trained for, on datasets it has never seen. That claim only holds if the model can actually consume those datasets. And here is the sentence that puts the tokenizer on the critical path, in their own words:

> A general language model (LM) should be able to compute the probability of (and also generate) any string.

Any string. Not any string in your training distribution. Not any string after you have lowercased it and stripped the accents and replaced the unfamiliar words with a special unknown token. Any string, including the ones with emoji in them, and the ones in a language you did not plan for, and the ones that are mostly punctuation.

They are explicit that this is exactly what standard practice was throwing away:

> Current large scale LMs include pre-processing steps such as lower-casing, tokenization, and out-of-vocabulary tokens which restrict the space of model-able strings.

If your pipeline has an unknown token, there exist strings your model cannot represent, which means there exist benchmarks you cannot honestly run. The zero-shot argument would have a hole in it, and the hole would be in the tokenizer.

So the tokenizer stopped being plumbing and became load-bearing.

## The decision

There are two decisions here, and they are usually collapsed into one. Keeping them apart is most of the value of reading the section carefully.

**Decision one: start from bytes, not characters.** They reach for byte pair encoding, which Sennrich, Haddow and Birch had brought to language from compression four years earlier, adapting an algorithm of Gage's from 1994 (arXiv:1508.07909). Their framing of why it fits:

> Byte Pair Encoding (BPE) (Sennrich et al., 2015) is a practical middle ground between character and word level language modeling which effectively interpolates between word level inputs for frequent symbol sequences and character level inputs for infrequent symbol sequences.

That is a genuinely elegant sentence and it is the reason the technique won. Frequent things get short. Rare things get spelled out. You do not choose in advance which is which; the corpus chooses.

But then there is a wrinkle, and it is the kind of wrinkle that only shows up when you actually try to build the thing:

> Despite its name, reference BPE implementations often operate on Unicode code points and not byte sequences.

If your starting alphabet is Unicode code points, and you want to represent every string, your alphabet is every code point. The paper does the arithmetic out loud: that "would result in a base vocabulary of over 130,000 before any multi-symbol tokens are added. This is prohibitively large compared to the 32,000 to 64,000 token vocabularies often used with BPE."

Read that again, because it is a lovely piece of engineering reasoning. The base vocabulary, before you have learned a single thing, would be twice the size of the entire vocabulary people normally ship. You would have spent your whole budget on the alphabet and had nothing left for words.

The alternative is one line: "In contrast, a byte-level version of BPE only requires a base vocabulary of size 256."

Two hundred and fifty six. Every possible byte. Every string on earth encodes to bytes, so there is no unknown token, ever, and there never can be. The cost is that anything outside ASCII starts life as two to four separate symbols and only gets cheaper if the corpus contained it often enough to earn merges. Hold onto that cost. It comes back at the end and it is bigger than it looks.

**Decision two, and this is the one the case study is really about: draw a boundary.**

Having chosen bytes, they ran it, and it did not work properly. Here is the observation, and I want to quote it in full because the specificity is the point:

> However, directly applying BPE to the byte sequence results in sub-optimal merges due to BPE using a greedy frequency based heuristic for building the token vocabulary. We observed BPE including many versions of common words like dog since they occur in many variations such as dog. dog! dog? . This results in a sub-optimal allocation of limited vocabulary slots and model capacity.

There it is. That is the phone keyboard spending three slots on "thanks".

And notice what kind of statement this is. It is not a theoretical objection. It is "we observed". Somebody trained a tokenizer, went and looked at the vocabulary it produced, read the actual entries, and noticed that a distressing number of them were the same word wearing different punctuation. That is a person doing the unglamorous part of the job, and the paragraph exists because they did.

The fix is one sentence, plus a second sentence that turns out to matter as much:

> To avoid this, we prevent BPE from merging across character categories for any byte sequence. We add an exception for spaces which significantly improves the compression efficiency while adding only minimal fragmentation of words across multiple vocab tokens.

Letters may merge with letters. Digits with digits. Punctuation with punctuation. A letter may never merge with a full stop, so `dog` and `dog.` cannot both exist as learned tokens, because `dog.` cannot be learned at all. And then the exception: a space is allowed to attach to the thing after it, so ` dog` is a legal token, which is why so many tokens in every modern tokenizer look like a word with a space glued to its front.

## What the paper does not tell you

Here is the gap I want to close this morning, and it is the reason this piece exists rather than being a summary of somebody else's paragraph.

The paper states a problem and states a fix. It publishes no number for either. How much vocabulary was actually being wasted? What does the fix cost? "Significantly improves the compression efficiency" is a claim with no figure attached to it, and I have shipped enough things described as significant improvements to want to see the number.

So I built both sides.

`lib/bpe.py` in this repository already trained byte-level BPE with a whitespace boundary, which is the obvious choice and the one I made back on Sunday without thinking about it very hard. Today it gained three more boundary rules so they can be run against each other:

- **lines**, the permissive baseline: merges may cross spaces, so a phrase like "of the" is a mergeable pair like any other. This is what you get if you do not think about boundaries at all.
- **whitespace**, the shipped default: merges stop at whitespace, so a token can be a word but never two words.
- **categories**, our implementation of the paper's rule: merges also stop at letter, digit and punctuation transitions, with the space exception.
- **category-runs**, the paper's rule with the space exception removed, so the exception can be priced rather than assumed.

One caution before the numbers, and it is not a small one. `pre_tokenize_categories` is our implementation of the rule the paper describes in that sentence. It is not GPT-2's tokenizer. The real one has more special cases than four character categories, and I am not going to pretend otherwise. What is being measured here is the rule as stated, on our corpus, with our code.

And the corpus deserves its own warning, which is recorded in [`data/week-03/README.md`](https://github.com/QuantumindSSI/systemdesign/blob/main/data/week-03/README.md) and which I am repeating in the body because burying it in a README would be a way of not really saying it. Our corpus is 260,242 bytes of the prose from the first two weeks of this series. It is small, it is one domain, and it is one author. Every absolute number below is a fact about that. The shape is what transfers.

## The number that moved

Everything below is at a vocabulary of 1,024, which is 768 learned merges, from [`experiments/week-03/pretoken_boundary.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/pretoken_boundary.py), run today. The first table uses a 40,032-byte prefix, because the permissive rule is slow enough on the whole corpus that nobody would run it.

```
 boundary rule  merges   tokens  bytes/token  phrase  mixed  variant
--------------------------------------------------------------------
         lines     768    13255        3.020      68    306       66
    whitespace     768    12509        3.200       0     25        4
    categories     768    12640        3.167       0      0        0
 category-runs     768    18335        2.183       0      0        0
```

The three right-hand columns are the ones to read. **phrase** counts learned tokens that cover the end of one word and the start of the next. **mixed** counts learned tokens whose text spans more than one character category. **variant** counts the slots consumed beyond the first by families that share a letter core, which is the `dog. dog!` phenomenon made countable.

Start at the top row. With no word boundary at all, **306 of 768 merges produced a token that mixes character categories**, and 68 of those glue two words together. Here is what it actually spent them on:

```
  ['. Th', ', and ', '. I', '. The ', '. A', ', the ', 'in the ', ' and the ']
```

Forty percent of the budget, gone on fragments of English that only ever match in one context. That is the phone keyboard, at scale, in a system nobody was looking at closely.

Now the part I did not expect, and it is the reason I am glad the script asserts things rather than just printing them. **The permissive rule compresses worse.** 3.020 bytes per token against the whitespace rule's 3.200. It is allowed to merge strictly more pairs than the whitespace rule. It can do everything the whitespace rule can do and more. And it ends up ahead on nothing.

I had assumed, before running it, that removing the boundary would buy some compression and the argument would be about whether the compression was worth the vocabulary damage. It does not. At this vocabulary size the phrases it learns are so specific that they pay for themselves in too few places, while the budget they consumed would have bought common words that appear everywhere. The boundary is not a tax on compression. It is what stops the merge budget being spent on things that are almost never useful.

Now the whole corpus, and the three rules that are fast enough to run on it:

```
 boundary rule  merges   tokens  bytes/token  phrase  mixed  variant
--------------------------------------------------------------------
    whitespace     768    90188        2.886       0     35        9
    categories     768    91351        2.849       0      0        0
 category-runs     768   126257        2.061       0      0        0
```

Two things worth sitting with.

**First, our own default has the paper's problem.** The whitespace rule spends 35 of its 768 slots on mixed-category tokens, and here are four of the families it built:

```
  'ed': ['ed,', 'ed.']
  'es': ['es,', 'es.']
  'ing': ['ing,', 'ing.']
   's': ['s,', 's.']
```

That is `dog. dog!`, in our tokenizer, on our corpus. Not a hypothetical. I wrote the whitespace boundary on Sunday, thought it was sufficient, and it produced the exact failure the paper describes, at a smaller scale, and I would not have known if I had not gone and counted. Which is the same thing that happened to them, and it is why the sentence in the paper starts with "we observed".

**Second, the fix is not free, and the price is smaller than the argument about it.** Moving from whitespace to the category boundary costs **+1.29% more tokens**. That is the whole bill. You give up 1.29% of your compression and you get back every slot that was being spent on punctuation variants, permanently, by construction, in a way that cannot regress when the corpus changes.

And then the exception, which is the number that genuinely surprised me. Take the space exception away, keep everything else, and the same corpus costs **126,257 tokens instead of 91,351**. That is **+38.21%**. The paper says the exception "significantly improves the compression efficiency" and declines to elaborate. On our corpus, significant means the difference between a working tokenizer and one that burns a token on every space between every pair of words for the rest of its life.

One line in a paper. Thirty eight percent.

## What it still does not fix

Every fix has a boundary of its own, and this one is narrower than it first appears. Three gaps, and the third is the largest thing in this article.

**It does not help identifiers.** Here is the same held-out string under all three rules, and the category boundary buys you exactly one token:

```
     whitespace   26 tokens  ['t', 'he', ' cache', ' exp', 'ire', 'd', '.', ' the', ' cache', ' exp', 'ire', 'd', '!', ' ord', 'er', '_', 'id', '=', '8', 'f', '3', 'a', '9', '1', 'c', '4']
     categories   25 tokens  ['t', 'he', ' cache', ' exp', 'ire', 'd', '.', ' the', ' cache', ' exp', 'ire', 'd', '!', ' order', '_', 'id', '=', '8', 'f', '3', 'a', '9', '1', 'c', '4']
```

`8f3a91c4` shatters into eight tokens either way, because it is a hex identifier and the category rule splits letters from digits on principle. If your production traffic is full of correlation ids and order numbers, the vocabulary hygiene fix does nothing for you, and the fragmentation you are paying for is structural.

**It does not make a small corpus into a big one.** Everything above is measured on two weeks of one person writing about caches. A general-purpose tokenizer trained on web-scale text would flatten most of these gaps. Carry the direction of each number, not its value.

**And it does not touch who pays.** This is the gap that outlives the paper. The whole scheme allocates vocabulary by frequency in the training corpus, so whatever the corpus underrepresents stays expensive forever. Petrov, La Malfa, Torr and Bibi measured this across deployed tokenizers and found that the same text, translated into different languages, has tokenization lengths differing "up to 15 times in some cases" (arXiv:2305.15425, NeurIPS 2023), and that even character-level and byte-level models show "over 4 times the difference in the encoding length for some language pairs".

Sit with what a 15x token count means in practice, because it is not an abstraction. It is 15 times the cost per API call. It is a fifteenth of the usable context window. It is latency, on the same request, for the same meaning. A decision made about vocabulary slots, for reasons of compression efficiency, turns into a bill that some people pay and others do not.

That is not a bug in byte pair encoding. It is byte pair encoding working exactly as designed, on a corpus, and the corpus deciding.

## The transferable rule

If you take one thing from this morning, take this:

**Byte pair encoding is a compression algorithm, and compression has no idea what a word is. Every boundary you do not draw, frequency will cross.**

That is the whole case study in one line. The team found their vocabulary filling with `dog.` and `dog!` because nothing had told the algorithm that a full stop is not part of a word, and nothing was ever going to, because frequency does not carry that information. They drew a boundary. It cost them a little compression, and it cost one carefully placed exception to keep from costing a lot, and it bought back capacity that would otherwise have leaked away invisibly forever.

The reason I think this generalises well past tokenizers is that the failure mode has a signature you can learn to spot. Somewhere in your system, something allocates a limited resource automatically, by counting. Cache keys. Feature flags. Index shards. Metric label cardinality. Sampled traces. In every one of those, the thing doing the counting has no model of what the units mean, and it will cheerfully spend your budget on three variants of one thing while the thing you actually needed never gets in.

And you will not get an error. That is the part that makes it worth a Wednesday. Nothing throws. Every entry it created is individually correct. The cost is entirely in the entries that do not exist, and absence does not page anybody.

So here is the small, concrete version, and it takes twenty minutes. Go and print the actual entries in whatever automatically-populated table your system depends on. Not the size of it. Not the hit rate. The entries. Read a hundred of them with your own eyes and ask how many are variants of each other. That is precisely what somebody did in 2019, and it is the only reason that paragraph exists.

Tag someone who is debugging this right now.

---

*This evening, 17:00: the code behind all of it. We train byte pair encoding on a corpus small enough to check by hand, print every merge as it is learned, and then walk into the two traps. One is a tie-break that makes your tokenizer depend on the order you happened to read your corpus in. The other is an encoder that round trips perfectly, never crashes, and is a different algorithm from the one that trained your merge table.*

*Tomorrow, 09:00: the layer that receives all these token ids. Embedding tables, hands-on, in under an hour, including the arithmetic that shows a third of a small model is a lookup table and the measurement that shows an untrained one knows nothing at all.*
