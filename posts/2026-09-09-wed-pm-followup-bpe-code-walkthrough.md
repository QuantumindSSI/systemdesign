# Week 3 · Wed 2026-09-09 · 17:00 · Follow-up: Twelve Merges You Can Check by Hand, and Two Ways to Get This Wrong

> Calendar row: W3 Wed PM, 17:00 (CSV row `43:3`). Format: code deep-dive.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md canonical source rule + AGENTS.md human-first voice.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and is not reproduced here or in the body. Every line of code below was
> written in this repository and is copied from a committed file unmodified.
>
> Committed calendar beats, all three present below: build a minimal runnable
> model of BPE tokenization from the morning's case study | annotate the two
> lines people get wrong | state the expected output so readers can
> self-verify.
> Committed CTA: "Repost this so your team sees it."
>
> Artifact: `experiments/week-03/bpe_trace.py`, written today, committed in
> this repository, 421 lines, Python 3.8+ standard library only, no
> third-party imports, shuffle seed 42, runs in about three seconds. Three
> claims, each asserted, exit code 0 with "All assertions passed". Following
> the W1 Wed convention (commit f5f8dd8), the code that carries the claims
> lives in the article; the printing harness stays in the file.
>
> Reference implementation walked: `lib/bpe.py`, 687 lines after this
> morning's additions. Covered by `tests/test_bpe.py`, 312 lines and 47
> tests. Whole suite 214 tests, all passing today.
>
> Verification performed 2026-09-09:
> - `experiments/week-03/bpe_trace.py` run to completion, exit code 0, "All
>   assertions passed" printed.
> - Determinism confirmed by running twice and comparing an md5 of stdout:
>   identical, 33236832cc519bee4ed0e83b77c32e8b.
> - The traced training loop asserts its merge list equals `lib/bpe.py`'s, so
>   the trace is a trace rather than a re-derivation that might drift.
> - Every number quoted in the prose is copied from today's stdout, not
>   transcribed from memory.
> - `python3 -m unittest discover -s tests -t .`: 214 tests, OK.
>
> Week-3 scope fences:
> - The pre-token boundary and its cost were this morning's subject and are
>   not re-derived here. This post assumes the whitespace default and walks
>   what happens inside a chunk.
> - Embedding the ids these merges produce is tomorrow 09:00. Nothing below
>   turns a token into a vector.
> - There is still no backward pass anywhere in this repository. Nothing here
>   is trained in the gradient sense; BPE training is a counting procedure.
>
> Adversarial review record (2026-09-09):
> - Every code block is copied verbatim from a committed file. Line counts and
>   file paths were checked against the working tree today ✓
> - The tie-break trap is demonstrated, not asserted from theory: `max()` is
>   shown diverging at merge 27 under a stated shuffle seed, and the stable
>   rule is shown not diverging under any of the four orderings ✓
> - Trial 0 of the tie-break table shows the two rules agreeing, and the body
>   says so rather than showing only the trials that make the point ✓
> - The left-to-right encoder is described as a different algorithm that round
>   trips correctly, never as a bug that crashes, because it does not ✓
> - The heap-decrement defect is reported as the test suite catching it before
>   publication, with the date, and is not presented as a hypothetical ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 2,669 words, measured 2026-09-09 by whitespace split
>   over everything below the `---` marker ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-09-wed-am-essay-bpe-tokenization-case-study.md`
> is this morning's case study. This follow-up assumes the boundary decision
> and does not re-derive it.

---

**Topic:** Byte pair encoding traced merge by merge on a corpus you can check by hand, then the two implementations that look right and are not

**Subtitle:** You will watch twelve merges get learned, then meet a tie-break that makes your tokenizer depend on the order you read your files in, and an encoder that round trips perfectly while being a different algorithm from the one that trained it.

Good evening.

This morning we read a sentence from a 2019 paper about a team who looked inside their vocabulary and did not like what they found. Tonight you get to look inside one.

Quick context if you did not catch the morning piece, because this stands on its own. Byte pair encoding starts with an alphabet of the 256 possible byte values, finds the most frequent adjacent pair of symbols in the corpus, replaces that pair everywhere with a single new symbol, and repeats. Each repetition adds one entry to the vocabulary and makes the sequence shorter. Merges are not allowed to cross a word boundary, which is why so many tokens look like a word with a space stuck on the front. That is the entire algorithm.

It is about fifteen lines. That is worth saying out loud, because tokenizers get discussed as though they were mysterious, and the counting part genuinely is not. What is not fifteen lines is getting it right, and the interesting failures are not where you would look for them.

So: twelve merges you can check with a pencil, and then two traps.

## The whole algorithm, on a corpus you can hold in your head

Here is the training corpus. Ninety six characters, deliberately.

```python
TINY_CORPUS = (
    "the cache expired. the cache expired again. "
    "the request missed the cache and the request waited."
)
```

The first thing that happens to it is that it stops being text. `lib/bpe.py` cuts it into chunks at whitespace, encodes each chunk to bytes, and counts how often each distinct chunk occurs. From [`lib/bpe.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/bpe.py):

```python
    @classmethod
    def word_counts(
        cls, text: str, pre_tokenizer: PreTokenizer = pre_tokenize
    ) -> Counter:
        """Count how often each pre-token chunk occurs, as byte tuples.

        This is the only place the raw text is read. Everything after it
        works on word types and frequencies, which is why training cost
        scales with the vocabulary of the corpus rather than its length.
        """
        counts: Counter = Counter()
        for chunk in pre_tokenizer(text):
            counts[tuple(chunk.encode("utf-8"))] += 1
        return counts
```

Slow down on that docstring, because it is the reason this is tractable at all. After this function, the corpus does not exist. What exists is a table of distinct word types and how often each occurred. Our 96-character corpus becomes 10 word types. The full 260,242-byte corpus becomes 8,105. Training cost tracks the number of distinct words, not the number of words, which is why you can train a tokenizer on a corpus you could not fit in memory.

Then the loop. Count every adjacent pair, weighted by word frequency. Take the winner. Replace it everywhere. Repeat.

```python
def train_merges_naive(
    word_counts: Dict[Tuple[int, ...], int], vocab_size: int
) -> List[Tuple[Pair, int]]:
    counts = Counter(word_counts)
    merges: List[Tuple[Pair, int]] = []
    for new_id in range(BYTE_VOCAB_SIZE, vocab_size):
        best = _best_pair(_count_pairs(counts))
        if best is None:
            break
        merges.append((best, new_id))
        rebuilt: Counter = Counter()
        for word, frequency in counts.items():
            rebuilt[_merge_once(word, best, new_id)] += frequency
        counts = rebuilt
    return merges
```

That is it. That is byte pair encoding. `_count_pairs` counts, `_best_pair` picks, `_merge_once` replaces, and the loop runs at most `vocab_size - 256` times and stops early when nothing is left to merge, so it always halts.

Now run it and watch. This is real output from [`experiments/week-03/bpe_trace.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-03/bpe_trace.py), asking for a vocabulary of 268, which is twelve merges:

```
corpus: 96 characters, 10 distinct word types

round  new id  count  pair                     stands for
------------------------------------------------------------------------
    1     256      8  'h' + 'e'                'he'
    2     257      5  't' + 'he'               'the'
    3     258      4  ' ' + 'the'              ' the'
    4     259      4  'e' + 'd'                'ed'
    5     260      3  ' ' + 'c'                ' c'
    6     261      3  'a' + 'c'                'ac'
    7     262      3  ' c' + 'ac'              ' cac'
    8     263      3  ' cac' + 'he'            ' cache'
    9     264      2  ' ' + 'a'                ' a'
   10     265      2  ' ' + 'e'                ' e'
   11     266      2  ' ' + 'r'                ' r'
   12     267      2  'a' + 'i'                'ai'
```

Read rounds five through eight as a single story, because they are the algorithm's whole character in four lines. It does not learn " cache". It learns " c", then "ac", then glues those into " cac", and only then attaches the "he" it learned in round one. Four rounds, four vocabulary slots, to arrive at one word.

Nothing planned that. No step looked ahead. Each round asked one question, which pair is most frequent right now, and the word assembled itself out of the answers. That is what people mean when they say BPE is greedy, and the four-round climb to " cache" is what greedy costs.

Round three is worth its own moment too. The most frequent pair at that point is a space followed by "the", so the space becomes part of the token. That is not a special case anybody wrote. It falls out of the boundary rule from this morning: a chunk carries the whitespace in front of it, so the space is inside the chunk and eligible to merge like anything else.

Two runs of this produce byte-identical output. There is no seed, because there is no randomness. Or rather, there is no randomness if you get the next part right.

## The first line people get wrong

Ties. Two pairs, both occurring four times, one slot available.

Here is what `lib/bpe.py` does:

```python
def _best_pair(pair_counts: Counter) -> Optional[Pair]:
    """Return the most frequent pair, ties broken by the smallest pair.

    Returns None when no pair remains, which is how training terminates on
    a corpus that has run out of things to merge.
    """
    if not pair_counts:
        return None
    return min(pair_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
```

The key is `(-count, pair)`. Highest count first, and on a tie, the numerically smaller pair. That second component is the entire point of the line, and it is the thing that gets left out.

Because the obvious way to write this is:

```python
best = max(pair_counts, key=pair_counts.get)     # the trap
```

That is shorter, it is idiomatic, it is what I would probably type first, and it is correct in the sense that it does return a pair with the maximum count. The problem is which one. Python's `max` returns the first item it encounters holding the maximum, and for a dict that means insertion order. Insertion order here is the order the pairs were first seen, which is the order the word types were counted, which is the order your files came off disk.

So the tokenizer is a function of your directory listing.

Here is that, measured. Same corpus, same word types, same counts. The only thing that changes is the order they were inserted into the dictionary, shuffled four times with seed 42:

```
2120 word types, vocabulary 320, 4 shuffled orderings, seed 42

 ordering   smallest-pair tie-break    max() tie-break
--------------------------------------------------------
        0                 identical          identical
        1                 identical differs at merge 27
        2                 identical differs at merge 37
        3                 identical differs at merge 37
```

Look at ordering 0 first, because it is the honest part of this table. The two rules agree. If you had run this once and got that row, you would have concluded there was no problem and moved on. That is exactly how this class of bug survives: it agrees with you most of the time you look at it.

Then ordering 1 diverges at merge 27. Out of 64 merges, the first twenty seven are identical and then the tokenizers are different objects, and every merge after that compounds, because merge 28 operates on a corpus that merge 27 changed.

Now think about what a different merge list actually means downstream. Your tokenizer is a fixed component. Every embedding row is indexed by a token id from it. Retrain the tokenizer with the files in a different order and id 274 stops meaning what it meant, while every model artifact you already trained still believes it does. Nothing crashes. The text still round trips. Your embeddings are just quietly indexed against a vocabulary that no longer exists.

The fix is one tuple element. `(-count, pair)` instead of `count`. The tie is broken by something intrinsic to the pair rather than by an accident of iteration, and the tokenizer goes back to being a function of its training data.

## The second line people get wrong

Now encoding, which is where I think most people's mental model quietly parts company with the code.

Training learned merges in an order. Encoding has to replay them in that order. The obvious implementation walks the string left to right and applies the first merge that fits, and that is a different algorithm.

Here is the wrong one, written entirely against the public API, which is how you would write it:

```python
def encode_left_to_right(tokenizer, ranks, chunk):
    symbols = list(chunk.encode("utf-8"))
    budget = len(symbols)
    while budget > 0:
        budget -= 1
        applied = False
        for position in range(len(symbols) - 1):
            rank = ranks.get((symbols[position], symbols[position + 1]))
            if rank is None:
                continue
            symbols[position:position + 2] = [tokenizer.merges[rank][1]]
            applied = True
            break
        if not applied:
            return symbols
    return symbols
```

And here is the right one, from `lib/bpe.py`:

```python
        symbols: List[int] = list(chunk.encode("utf-8"))
        while len(symbols) >= 2:
            best_rank = None
            best_position = None
            for position in range(len(symbols) - 1):
                rank = self._merge_rank.get((symbols[position], symbols[position + 1]))
                if rank is not None and (best_rank is None or rank < best_rank):
                    best_rank = rank
                    best_position = position
            if best_rank is None:
                break
            symbols[best_position:best_position + 2] = [self.merges[best_rank][1]]
```

Spot the difference. The wrong one breaks out of the inner loop at the first applicable merge, wherever it is in the string. The right one scans the whole string and keeps the merge with the **lowest rank**, meaning the one that was learned earliest. Position does not matter. Only the order of learning matters, because that is the order training applied them in.

The wrong one is not broken in any way that announces itself. It terminates. It never raises. It round trips perfectly, because merges are reversible regardless of the order you apply them. It just produces different tokens.

How different? Every distinct chunk from the first 60,000 characters of the corpus, at a vocabulary of 512:

```
2809 distinct chunk types from the first 60000 characters, vocabulary 512
  disagreements            933
  tokens, replay by rank   12392
  tokens, left to right    12781
  left to right costs      +3.14%
```

A third of all chunk types encode differently. Here is one:

```
  worked example: ' Almost'
    by rank         ["' A'", "'l'", "'m'", "'ost'"]
    left to right   ["' A'", "'l'", "'m'", "'os'", "'t'"]
```

Four tokens against five, for one word. Multiply by every word in every request forever and you get the 3.14%, which is a permanent tax you pay for a bug you cannot see.

There is a small proof hiding in the correct version that is worth making explicit, because it is why the lowest-rank rule is not just a heuristic that happens to work. It is in the docstring:

```python
        Applies the lowest-ranked applicable merge repeatedly, rather than
        replaying the entire merge list. The two are equivalent: merge k
        produces a brand new symbol id 256+k, and the only new adjacencies
        it creates involve that new id, so it can never manufacture a pair
        belonging to an earlier merge. Nothing already passed can become
        applicable again.
```

Merge k mints a symbol id that did not exist before, so any pair it creates involves an id larger than any id an earlier merge knew about. An earlier merge can therefore never become applicable again. That is what makes "always take the earliest-learned applicable merge" equivalent to "replay all of them in order", and it is what turns an O(merges × length) loop into an O(length²) one, which matters once the merge list is thousands long.

## The bug the tests caught, and why it is in the article

One more, because this series claims that tests earn their keep and a claim like that should cost something to make.

`lib/bpe.py` ships two trainers. `train_merges_naive` is the textbook version above, recounting every pair every round. `train_merges_indexed` is the fast one, with a pair-to-words index and a max-heap using lazy invalidation. They must produce identical merges, and a test asserts exactly that rather than assuming it:

```python
    def test_indexed_strategy_matches_the_naive_oracle(self):
        # The fast path exists only for speed. If it ever disagrees with
        # the textbook recount, the fast path is wrong, not the oracle.
        for corpus in (CORPUS, RICH_CORPUS):
            for vocab_size in (280, 320, 450):
                fast = BPETokenizer.train(corpus, vocab_size, strategy="indexed")
                slow = BPETokenizer.train(corpus, vocab_size, strategy="naive")
                self.assertEqual(fast.merges, slow.merges)
```

On 2026-09-06 that test failed. The heap was receiving increments when a pair's count went up and nothing when it went down, so a pair whose count dropped kept only its stale, higher heap entry, that entry got rejected on pop as no longer matching the live count, and the pair vanished from consideration while still occurring in the corpus. The comment on the fix says it better than I can:

```python
    A decrement must be pushed onto the heap just like an increment. The
    heap entry that carried the old, higher count becomes stale and is
    skipped on pop, so without pushing the new lower count the pair would
    disappear from consideration entirely even though it still occurs.
```

That bug produces a working tokenizer. It trains, it encodes, it round trips, and its vocabulary is subtly wrong in a way no round-trip test would ever reveal, because round trips are preserved by any consistent merge list. The only thing that catches it is keeping the slow obviously-correct implementation around and asserting the fast one agrees with it.

Which is the actual lesson of the evening: for anything where the fast version is an optimisation of a simple version, keep the simple version, and make the test suite ask them the same question.

## Expected output, so you can self-verify

Clone or pull, then:

```
python3 experiments/week-03/bpe_trace.py
```

Three seconds. The last line should read:

```
All assertions passed
```

And these should match exactly, because there is no sampling anywhere except the stated shuffle seed:

| check | expected |
|---|---|
| merges traced on the tiny corpus | 12, identical to `lib/bpe.py`'s |
| merge 8 stands for | `' cache'` |
| word types at 40,000 characters | 2120 |
| `max()` tie-break, ordering 1 | differs at merge 27 |
| smallest-pair tie-break, all orderings | identical |
| chunk types compared | 2809 |
| encoder disagreements | 933 |
| tokens by rank / left to right | 12392 / 12781 |
| left to right costs | +3.14% |

If any of those differ, the run is not deterministic on your machine and I would like to know, because the entire argument of this post is that it should be.

Then change one thing, if you want the real value out of this. Set `SHUFFLE_TRIALS` to `12` and watch how many orderings the `max()` tie-break survives before diverging. The answer is not zero, and that is the uncomfortable part: this bug passes a code review, passes a round-trip test, and passes the first few times you look at it directly.

Repost this so your team sees it.

---

*Tomorrow, 09:00: the ids come out of the tokenizer and something has to turn them into vectors. Embedding layers, hands-on, in under an hour, with the arithmetic that shows a third of a small model is a lookup table and a measurement that shows a fresh one knows nothing at all.*
