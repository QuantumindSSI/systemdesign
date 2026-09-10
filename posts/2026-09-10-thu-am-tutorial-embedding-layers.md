# Week 3 · Thu 2026-09-10 · 09:00 · Hands-on: Build an Embedding Layer in an Hour and Find Out It Knows Nothing

> Calendar row: W3 Thu AM, 09:00 (CSV row `44:3`). Format: hands-on tutorial.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every line of code below was
> written in this repository and is copied from a committed file unmodified.
>
> Committed calendar beats, all three present below: define the end state,
> what exists and runs when the hour is up | give the 4 to 6 numbered steps
> with the commands or code per step | include the verification step that
> proves it worked. Committed CTA: "Save this for your next design review."
>
> Artifacts written for this post, committed in this repository:
> - `lib/embedding.py`, 356 lines, Python 3.8+ standard library only, built on
>   `lib/linalg.py`. Token table, position table, weight tying, the parameter
>   report, and the cosine helper used to show a fresh table knows nothing.
> - `tests/test_embedding.py`, 246 lines, 35 tests, all passing today.
> - `experiments/week-03/embedding_lab.py`, 414 lines, seeds 42 and 43, sample
>   seed 7. Five claims, each asserted, exit code 0 with "All assertions
>   passed", under two seconds of runtime.
> Whole suite after these three files: 214 tests, all passing.
>
> Verification performed 2026-09-09, the day this post was prepared:
> - `experiments/week-03/embedding_lab.py` run to completion, exit code 0,
>   "All assertions passed" printed.
> - Determinism confirmed by running twice and comparing an md5 of stdout:
>   identical, 36c23c8fab0535cbf8b49e3454e526e7.
> - Every number quoted in the prose is copied from that stdout.
> - `python3 -m unittest discover -s tests -t .`: 214 tests, OK.
>
> **Standing rule, discharged 2026-09-10.** `prep/README.md` requires every
> script to be re-run on posting day and measured numbers to be regenerated
> rather than remembered. Re-run performed on posting day before staging:
> `experiments/week-03/embedding_lab.py` exited 0 with "All assertions passed"
> and an stdout md5 of 36c23c8fab0535cbf8b49e3454e526e7, identical to the
> value recorded on 2026-09-09. Every figure in the body is therefore current
> and no correction was needed.
>
> **Two claims the assertions killed before publication on 2026-09-09,
> recorded because the series says tests do this.** First, the lab asserted
> that mean absolute
> cosine similarity between untrained rows would be "near zero", using 0.10 as
> the threshold. It measured 0.1003 and the assertion failed. The threshold
> was wrong, not the table: random vectors in d dimensions have mean absolute
> cosine of sqrt(2 / (pi * d)), which is 0.0997 at d_model 64. The claim was
> rewritten to compare against that prediction, which is a stronger statement
> and is what the body now makes. Second, the related-pair probe originally
> compared " cache" against " caches", which encode to `[427]` and `[427, 115]`
> respectively, so it was comparing row 427 with itself and scoring a perfect
> 1.0000. The lab now refuses to continue unless both words are single tokens
> with different ids.
>
> Week-3 scope fences:
> - Tokenization was Wednesday and is not re-derived. Step 1 uses `lib/bpe.py`
>   as a black box that turns text into ids.
> - Attention is Monday and Tuesday. Nothing here attends to anything.
> - Rotary positional encodings are tomorrow. This post covers learned
>   absolute position embeddings only, and says so at the point where the
>   distinction starts to matter.
> - There is still no backward pass in this repository. Every weight comes
>   from a seed, which is exactly what makes step 6 possible.
>
> Non-repository sources, permitted under the canonical source rule:
> - Radford et al., "Language Models are Unsupervised Multitask Learners"
>   (GPT-2). PDF fetched and text-extracted 2026-09-09. Quoted: "The
>   vocabulary is expanded to 50,257", the context size "from 512 to 1024
>   tokens", and Table 2's four rows: 117M/12/768, 345M/24/1024, 762M/36/1280,
>   1542M/48/1600. The share column in step 4 is arithmetic on those two
>   published columns and is labelled as arithmetic, not as a benchmark.
>
> Adversarial review record (2026-09-09, prepared a day ahead):
> - The parameter-share table is derived from two published columns and one
>   published vocabulary. It is not a measurement of any model, and the body
>   says which numbers are published and which are computed ✓
> - The published totals are rounded in the source (117M, not 117,000,000), so
>   the share percentages carry that rounding. Stated in the body ✓
> - Step 6 makes no claim about what trained embeddings do. It measures what
>   untrained ones do not do, and the difference is stated explicitly ✓
> - The seed-dependence demonstration uses two seeds and reports both, rather
>   than showing one nearest neighbour and implying it means something ✓
> - Learned absolute position embedding is named as one of several schemes,
>   not as how position works in general ✓
> - Six numbered steps, inside the committed 4 to 6 band ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 3,682 words, measured 2026-09-10 by whitespace split
>   over everything below the `---` marker ✓
> - Zero em dashes.

---

**Topic:** Building a token and position embedding layer from scratch, sizing it against four published model configurations, and measuring exactly how much meaning an untrained one carries

**Subtitle:** In about an hour you will have a file that proves the lookup is a matrix multiplication, that a third of a small model is a table, and that the nearest neighbour of the word "cache" in a fresh embedding is a backtick.

Good morning.

Here is a small thing that used to bother me about the seating plan at weddings.

You get a table number. That is all it is: a number. The number carries nothing about who you are, nothing about who you would enjoy sitting with, nothing about whether you are the sort of person who leaves at nine. Somebody else, holding a completely separate sheet of paper, decided what number 7 means. The number and the meaning live in different places, and the number is genuinely, completely empty until the sheet exists.

That is an embedding layer, and I mean that almost literally rather than as a loose analogy. Yesterday's tokenizer produced numbers. Today we build the sheet of paper. The part of this hour I most want you to reach is the last step, where we measure how much the sheet knows before anyone has filled it in, and the answer is a properly satisfying nothing.

An hour, one file, no installs.

## The end state

When you are done you will have run a Python file that:

- builds a **token embedding table** and proves, to the last bit, that reading row *i* is the same arithmetic as multiplying by a one-hot vector
- adds a **position table** and shows the same token at two different places comes out as two different rows, with the difference being exactly the difference between two position rows
- **sizes** the table against four published model configurations, and watches the embedding share of the parameter budget fall from about a third to about a twentieth
- **ties** the output projection to the input table and confirms the saving is exactly vocabulary times width
- **measures** what a fresh table knows, against the number that vectors with no structure at all would produce
- **asserts** all five of those, so that if one is wrong the program fails rather than this post lying to you

It needs Python 3.8 or newer, imports nothing outside the standard library, and finishes in under two seconds.

Here is the table you are aiming at, produced on my machine this morning:

```
    model  d_model  layers   token table   +positions  share of total
  -------------------------------------------------------------------
     117M      768      12    38,597,376   39,383,808          33.7%
     345M     1024      24    51,463,168   52,511,744          15.2%
     762M     1280      36    64,328,960   65,639,680           8.6%
    1542M     1600      48    80,411,200   82,049,600           5.3%
```

## Step 1: get real ids, not made-up ones

Start where yesterday ended. Train the tokenizer on our own corpus and encode a sentence, so that the vocabulary size in every calculation afterwards is a measured fact rather than a placeholder:

```python
def step_one_real_ids(corpus):
    """Train the tokenizer and encode one sentence. Returns (tokenizer, ids)."""
    tokenizer = BPETokenizer.train(corpus, TOKENIZER_VOCAB)
    ids = tokenizer.encode(SENTENCE)
```

Output:

```
STEP 1: real token ids from our own tokenizer
  corpus            260148 characters
  vocabulary        1024
  sentence          'the cache expired before the request arrived'
  ids               [116, 258, 427, 861, 522, 100, 663, 263, 410, 920, 881]
  pieces            ['t', 'he', ' cache', ' exp', 'ire', 'd', ' before', ' the', ' request', ' arri', 'ved']
```

Look at that ids list for a second before moving on, because it is the whole reason the rest of the hour is necessary. Forty three characters of ordinary English became eleven integers between 100 and 920. There is nothing else. No text, no meaning, no relationship. The number 427 has no more inherent connection to caching than table number 7 has to your cousin.

Notice too that `'the'` at the start of the sentence is `[116, 258]`, two tokens, while `' the'` in the middle is `263`, one token. Same word, different ids, because one has a space in front of it and the other is at the start of a string. That is Wednesday's boundary rule showing up in today's inputs, and it is the first thing that catches people out when they try to reason about ids by eye.

## Step 2: the lookup is a matrix multiplication

Now the table. It is a rectangle of numbers: one row per token id, each row `d_model` wide. From [`lib/embedding.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/embedding.py):

```python
    def lookup(self, ids: Sequence[int]) -> Matrix:
        rows: Matrix = []
        for position, token_id in enumerate(ids):
            if not isinstance(token_id, int) or isinstance(token_id, bool):
                raise TypeError(
                    f"id at position {position} is {type(token_id).__name__}, "
                    "not int"
                )
            if not 0 <= token_id < self.num_entries:
                raise IndexError(
                    f"id {token_id} at position {position} is outside "
                    f"[0, {self.num_entries}). A tokenizer that grew special "
                    "tokens after this table was sized produces exactly this."
                )
            rows.append(list(self.weight[token_id]))
        return rows
```

That is an embedding layer. Read the row, copy it, return it. Everything else in this post is a consequence of those four lines.

**Slow down on the two guards, because they are the whole reason this is a function rather than `weight[i]`.** The `isinstance` check rejects `True`, which Python would otherwise happily treat as 1, silently embedding a boolean as whatever token id 1 happens to be. The range check refuses negative ids instead of letting Python's negative indexing turn id -1 into the last row of the vocabulary and hand back a completely plausible vector for an impossible token.

Now the claim that makes an embedding table trainable at all. Here is the same operation written as arithmetic instead of as an index:

```python
def embed_by_matmul(table: Sequence[Sequence[float]], ids: Sequence[int]) -> Matrix:
    """Embed ids the slow, explicit way: one-hot rows times the table.

    Complexity: O(len(ids) * num_entries * d_model), which is why nobody
    does this in production. The lookup is O(len(ids) * d_model).
    """
    num_entries, _ = shape(table)
    hot = [one_hot(token_id, num_entries) for token_id in ids]
    return matmul(hot, table)
```

A one-hot row is 1,023 zeros and a single 1.0. Multiply it by the table and you get, by definition, exactly the row where the 1.0 was. Compare the two routes:

```
STEP 2: a lookup is a matrix multiplication
  table             1024 by 64, 65536 floats
  rows returned     11
  largest gap between lookup and one-hot matmul: 0.000e+00
```

Zero exactly, to the last bit, because the multiplication sums 1,024 products of which 1,023 are exactly 0.0 and one is exactly the value you wanted.

This matters far more than it looks. An array index has no derivative; you cannot differentiate "the fourth item". A matrix multiplication has a very well-behaved one. The lookup **is** a multiplication, which makes the embedding table a weight matrix like any other, and the gradient it receives lands on precisely the rows that were looked up and nowhere else. That single equivalence is why the least sophisticated component in the model gets to learn.

Think of it as the difference between fetching a book off a shelf and taking one book's worth from every shelf at once, where every shelf but one lends you nothing. Same book in your hands. Completely different thing to reason about mathematically.

## Step 3: position comes from a second table

Back to the reception for a moment. Your card carries a table number, and it carries nothing at all about when you arrived or where you stood in the queue. The seating plan was drawn before anyone walked in. Whatever the number means, it means the same thing whether you are first through the door or last.

The token table has exactly that limitation, because it is indexed by id. Attention, as built earlier this week, is order-blind: permute the input rows and the output rows permute identically. Position therefore has to come from somewhere else.

The answer is almost disappointingly plain. Another table, indexed by position instead of by id, added on:

```python
    def forward(self, token_ids: Sequence[int]) -> Matrix:
        length = len(token_ids)
        if length == 0:
            raise ValueError("cannot embed an empty sequence")
        if length > self.max_positions:
            raise ValueError(
                f"sequence of {length} exceeds max_positions "
                f"{self.max_positions}. Truncating here would be silent data "
                "loss, so it is refused instead."
            )
        token_rows = self.tokens.lookup(token_ids)
        position_rows = self.positions.lookup(list(range(length)))
        return add(token_rows, position_rows)
```

One addition. That is learned absolute position embedding in full: a row for what the token is, plus a row for where it is, added together. The model works out what each position slot should mean during training, the same way it works out what each token row should mean.

```
STEP 3: position is a second table, not a property of the token
  output shape      11 by 64
  same id at positions 0 and 5, largest difference: 0.091034
  positions 0 and 5 of the position table differ by: 0.091034
```

The two numbers are identical, and that identity is the point rather than a coincidence. Feed the same token id six times and rows 0 and 5 differ by 0.091034. The token contributed nothing to that difference, because it was the same token. All of it came from the position table. The assertion in the lab checks that the two agree to within 1e-12, so if anything other than position ever moved, the run fails.

**Two things to flag before moving on, because both bite later.**

`max_positions` is a hard wall. A sequence longer than the position table has no row to add, and the layer refuses rather than truncating, because truncating would be silent data loss dressed up as a successful call. That refusal is one of the reasons context windows are the numbers they are. A room with sixty seats seats sixty people, and the sixty first guest is a problem you solve at the door rather than by quietly leaving someone off the list.

Adding a learned table indexed by absolute position is one scheme among several, chosen here for being the plainest one that works. It has an obvious weakness: the model learns what slot 900 means only from examples that actually reached slot 900, and there are always fewer of those. Alternatives exist and tomorrow is about one of them. For today, know that this is a choice with a name.

## Step 4: find out how much of the model is a lookup table

Now the arithmetic that changes how people size things. Two numbers from the GPT-2 paper: the vocabulary is 50,257, and the context is 1,024 tokens. Table 2 of the same paper gives four configurations. Everything in this step is arithmetic on those published columns. It is not a benchmark and it is not an estimate of anything.

```python
    token_parameters = vocab_size * d_model
    position_parameters = max_positions * d_model
    embedding_parameters = token_parameters + position_parameters
    return {
        "token_parameters": token_parameters,
        "position_parameters": position_parameters,
        "embedding_parameters": embedding_parameters,
        "embedding_share": embedding_parameters / total_parameters,
        "tying_saving": token_parameters,
    }
```

```
STEP 4: how much of the model is the lookup table
  vocabulary 50257, context 1024, both as published

    model  d_model  layers   token table   +positions  share of total
  -------------------------------------------------------------------
     117M      768      12    38,597,376   39,383,808          33.7%
     345M     1024      24    51,463,168   52,511,744          15.2%
     762M     1280      36    64,328,960   65,639,680           8.6%
    1542M     1600      48    80,411,200   82,049,600           5.3%
```

**Row one is the one to keep.** At the smallest configuration, the tables hold 39.4 million of roughly 117 million parameters. **Thirty three point seven percent of that model, before a single transformer block exists, is a lookup table.** A third of the weights sit in rows you read out by index, while attention and the feed-forward stack share what is left.

I have heard an embedding layer described as "just a lookup" in more design conversations than I can count, always in the tone reserved for things that do not need to be on the slide. A third of the model.

**Row four is the one that stops it being a rule.** At 1542M the same tables are 5.3%, because `d_model` grew 2.1 times while the layer count grew 4 times, and the blocks scale with the square of the width. The table grows linearly in width. The rest grows faster. The embedding share is therefore a property of where you sit on the size curve, and it falls the whole way along it.

One honesty note on this table. The published totals are rounded, since the paper says 117M rather than 117,000,000. That rounding carries into 33.7%, so the true figure is 33.7% give or take a few tenths. It does not move the argument, and pretending to more precision than the source has would be its own kind of error.

The practical version of this step, and the reason it is in a tutorial rather than a footnote: if you are building something small, your vocabulary size is a first-class architectural decision competing directly with depth and width for the same budget. Doubling your vocabulary at `d_model` 768 costs another 38.6 million parameters, which at that scale is most of another five transformer blocks. At 1542M the same doubling barely registers. Same decision, completely different answer, purely because of where you are on the curve.

## Step 5: tie the output projection and get the table back for free

At the end of the model, something has to score every token in the vocabulary. That is a `d_model` by `vocab_size` matrix, which is the same size as the embedding table.

That matrix can also be the embedding table, transposed:

```python
    def tied_logits(self, hidden: Sequence[Sequence[float]]) -> Matrix:
        _, width = shape(hidden)
        if width != self.d_model:
            raise ValueError(
                f"hidden is {width} wide, expected d_model {self.d_model}"
            )
        return matmul(hidden, transpose(self.tokens.weight))
```

```
STEP 5: tying the output projection to the input table
  logits shape      1 by 1024
  a separate output projection would hold 65,536 more floats
  which is 88.9% of this layer's own parameters
```

Weight tying is the same table doing both jobs: read a row on the way in, score against every row on the way out. One sheet of paper, consulted at the door to find where you go, consulted again at the end of the night to work out whose coat is whose. It costs zero extra parameters.

There is a test worth stealing for this one, because tying is very easy to wire in transposed and very hard to notice when you have:

```python
    def test_a_token_row_scores_highest_against_itself(self):
        # The row for id 7, scored against every row, must match itself
        # best. This is the sanity check that tying is wired the right way
        # round rather than transposed by accident.
        row = [list(self.layer.tokens.weight[7])]
        logits = self.layer.tied_logits(row)[0]
        self.assertEqual(max(range(VOCAB), key=lambda i: logits[i]), 7)
```

If you feed in the row for token 7, the highest score has to be token 7. A transposed tie still produces a matrix of the right shape and plausible-looking numbers, and this assertion is the cheapest thing that catches it.

Tying also explains an arithmetic puzzle you may have hit: a model whose reported parameter count is smaller than the sum of the layers you counted. You counted the vocabulary matrix twice. It only exists once.

## Step 6: measure what it knows, which is nothing

This is the step I would keep if I could only keep one.

Fresh table, seed 42, nothing trained. Now the question everybody's intuition answers wrongly: how related are the rows for `' cache'` and `' database'`? They are two words from the same domain, out of a corpus entirely about that domain, sitting in adjacent regions of a space built for exactly this.

```
STEP 6: what an untrained table does not know
  44850 pairs from 300 sampled ids, sample seed 7
  mean |cosine|, measured                0.1003
  mean |cosine|, predicted for no structure  0.0997   (sqrt(2 / (pi * 64)))
  95% of arbitrary pairs sit below   0.2454
  largest |cosine|                       0.5213
  ' cache' (id 427) against ' database' (id 924): cosine +0.0063
  nearest neighbour of ' cache' at seed 42: id 96 '`' (+0.3674)
  nearest neighbour of ' cache' at seed 43: id 991 ' ed' (+0.5399)
```

Three separate ways of saying the same thing, and I want all three because each closes a different escape route.

**The mean matches the no-structure prediction.** For vectors of independent Gaussian components in *d* dimensions, the expected absolute cosine similarity is sqrt(2 / (pi * d)), which at width 64 is 0.0997. Measured over 44,850 pairs: 0.1003. Agreement to six parts in a thousand. The claim that there is no structure here rests on a number matching its prediction, which is as close to a hand-wave as arithmetic gets.

**The related pair is unremarkable.** `' cache'` against `' database'` scores +0.0063, while 95% of arbitrary pairs sit below 0.2454. Two words a human would call obviously related score lower than the vast majority of pairs picked at random.

**The nearest neighbour is a property of the seed.** At seed 42, the closest row to `' cache'` in the entire vocabulary belongs to a backtick. Change one integer, seed 43, and it becomes `' ed'`. Nothing else changed. Not the corpus, not the tokenizer, not the ids, not the architecture. One integer, and `' cache'`'s nearest neighbour in the whole vocabulary became a different token.

Sit with the backtick for a moment. If you were shown that as output, with a chart and some confident framing, you could talk yourself into a story about it. Code contexts, technical prose, markdown formatting. The story would be entirely made of nothing.

**This is why the step is here.** Untrained and randomly initialised embeddings are floating around in more places than people admit: frozen tables in a pipeline that was never fine-tuned, a component swapped out during debugging, a config where the loading path silently failed and initialised fresh. When you look at one and see structure, you are looking at the seed. This is the reception hall with the cards printed and the sheet of paper still blank: every guest has a number, every number is legible, and nobody has yet decided what any of them mean. Meaning is something training puts there, and until training has run, the only honest number is 0.0997.

While we are here, the two things this layer refuses to do quietly:

```
    out-of-range id  -> IndexError: id 1024 at position 0 is outside [0, 1024). A tokenizer that grew special tokens after this table was sized produces exactly this.
    over-long input  -> ValueError: sequence of 129 exceeds max_positions 128. Truncating here would be silent data loss, so it is refused instead.
```

Both messages name the offending value and the limit, because the version of this that returns a plausible vector for id -1, or quietly truncates your 129th token, is the version you debug at three in the morning.

## Run it and verify

```
python3 experiments/week-03/embedding_lab.py
```

Under two seconds. The last line should read:

```
All assertions passed
```

These six should match exactly, because everything is seeded:

| check | expected |
|---|---|
| largest gap, lookup against one-hot matmul | `0.000e+00` |
| same id at positions 0 and 5 | `0.091034`, equal to the position-row difference |
| embedding share, 117M configuration | `33.7%` |
| embedding share, 1542M configuration | `5.3%` |
| mean absolute cosine, measured against predicted | `0.1003` against `0.0997` |
| nearest neighbour of `' cache'`, seeds 42 and 43 | `` '`' `` and `' ed'` |

If any differ, the run is not deterministic on your machine and I would like to know.

## What to do with this today

Three things, in descending order of how much time they take.

**Go and compute your own row one.** Take the vocabulary size, the width and the total parameter count of whatever model you are actually using, and work out the share. If it comes out above a quarter, your vocabulary is an architectural decision that is probably being made by whoever picked the tokenizer, on grounds that had nothing to do with your parameter budget.

**Check your position table against your longest real input.** Use the longest one you have actually seen in production rather than the average. `max_positions` is a wall, and what happens when you hit it is a decision somebody made, possibly by accident, possibly by calling something that truncates without saying so.

**Stop reading meaning into vectors whose training you cannot account for.** If you cannot say what corpus put the structure there, the honest prior is 0.0997.

The rule underneath all three is the one I would put on a wall. **An embedding table is the emptiest component in the model and the most expensive one to size wrong, and it will never tell you that you got it wrong.** A table that is too small raises. A table that is too large just quietly eats a third of your budget. A table that was never trained returns confident, plausible, entirely meaningless numbers for as long as you care to ask.

Which brings me back to what actually bothered me about the seating plan. It was never the number on the card. It was that the number looked like information. You can hold it, read it, repeat it to somebody and feel entirely informed while carrying nothing at all, because the meaning was always on a separate sheet of paper that somebody else had to fill in. A fresh embedding table is that card, 50,257 times over, and 0.1003 is the measurement of exactly how much it is telling you.

Save this for your next design review. Specifically, save it for the moment somebody says "it is just a lookup".

---

*This evening, 17:00: the five checks. Everything above, compressed into questions you can answer today from a config file and a metrics page, including the one where the number you configured and the number your tokenizer actually emits are not the same number.*

*Tomorrow, 09:00: a contrarian take. Most advice about rotary positional encodings optimizes for the demo rather than the system you actually run, and the learned absolute table from step 3 is the baseline it has to beat.*
