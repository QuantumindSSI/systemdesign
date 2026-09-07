"""Byte-level byte pair encoding: training, encoding, decoding.

Standard library only. This is the reference implementation the series
uses whenever a tokenizer is needed, and it is written to be read.

The algorithm is the one Sennrich, Haddow and Birch adapted from Gage's
1994 compression scheme (arXiv:1508.07909): start from a small alphabet,
repeatedly find the most frequent adjacent pair of symbols, and replace
that pair everywhere with a single new symbol. Each replacement adds one
entry to the vocabulary and shortens the sequence.

Two design choices are worth stating up front because they determine
everything the tokenizer can and cannot do.

BYTE LEVEL. The starting alphabet is the 256 possible byte values, not
the characters of some language. Any text encodes to bytes, so there is
no unknown token and no out-of-vocabulary failure, ever. The cost is that
a character outside ASCII begins life as two to four separate tokens and
only becomes cheaper if the training corpus contained it often enough to
earn merges.

MERGES NEVER CROSS A PRE-TOKEN BOUNDARY. Before training, the text is cut
into chunks by `pre_tokenize`, and merging happens inside a chunk only.
Without this, the tokenizer would happily learn a single symbol for
"the cat" and the vocabulary would fill up with phrases. This is why a
token so often looks like a word with its leading space attached.

Determinism: training is a pure function of (text, vocab_size). Ties on
pair frequency are broken by taking the numerically smallest pair, so two
runs on the same input produce identical merges. There is no seed because
there is no randomness.
"""

import heapq
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

BYTE_VOCAB_SIZE = 256

# A chunk is either a run of non-whitespace with the whitespace that
# precedes it attached, or a run of whitespace on its own. Concatenating
# every match reconstructs the input exactly, with nothing dropped.
PRETOKEN_RE = re.compile(r"\s*\S+|\s+")

Pair = Tuple[int, int]


def pre_tokenize(text: str) -> List[str]:
    """Split text into the chunks that merges are allowed to operate inside.

    Args:
        text: any string, including the empty string.

    Returns:
        A list of chunks whose concatenation is exactly `text`.

    Raises:
        TypeError: if `text` is not a str.
    """
    if not isinstance(text, str):
        raise TypeError(f"pre_tokenize needs a str, got {type(text).__name__}")
    return PRETOKEN_RE.findall(text)


def _merge_once(symbols: Sequence[int], pair: Pair, new_id: int) -> Tuple[int, ...]:
    """Replace every non-overlapping occurrence of `pair` with `new_id`.

    Scans left to right, so in "aaa" the pair (a, a) is replaced once and
    the trailing "a" is left alone. That matches the usual BPE behaviour.

    Complexity: O(len(symbols)).
    """
    merged: List[int] = []
    index = 0
    limit = len(symbols)
    while index < limit:
        if (
            index + 1 < limit
            and symbols[index] == pair[0]
            and symbols[index + 1] == pair[1]
        ):
            merged.append(new_id)
            index += 2
        else:
            merged.append(symbols[index])
            index += 1
    return tuple(merged)


def _count_pairs(word_counts: Dict[Tuple[int, ...], int]) -> Counter:
    """Count adjacent symbol pairs across all words, weighted by word frequency.

    Complexity: O(total symbols across distinct words), which is far
    smaller than the corpus length because identical words are counted
    once and weighted.
    """
    pair_counts: Counter = Counter()
    for word, frequency in word_counts.items():
        for left, right in zip(word, word[1:]):
            pair_counts[(left, right)] += frequency
    return pair_counts


def _best_pair(pair_counts: Counter) -> Optional[Pair]:
    """Return the most frequent pair, ties broken by the smallest pair.

    Returns None when no pair remains, which is how training terminates on
    a corpus that has run out of things to merge.
    """
    if not pair_counts:
        return None
    return min(pair_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def train_merges_naive(
    word_counts: Dict[Tuple[int, ...], int], vocab_size: int
) -> List[Tuple[Pair, int]]:
    """Learn merges by recounting every pair from scratch on every round.

    This is the algorithm as it is usually written down, and it is the
    definition of correct behaviour for this module. It is O(V * S) where
    V is the number of merges and S is the total symbol count across
    distinct words, which is why `train_merges_indexed` exists.

    Kept, exercised by the tests, and used as the oracle the fast path is
    checked against. If the two ever disagree, the fast path is wrong.
    """
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


def _index_pairs(
    word_counts: Dict[Tuple[int, ...], int]
) -> Tuple[Counter, Dict[Pair, Set[Tuple[int, ...]]]]:
    """Build the pair frequency table and the pair to containing-words index."""
    pair_counts: Counter = Counter()
    pair_words: Dict[Pair, Set[Tuple[int, ...]]] = defaultdict(set)
    for word, frequency in word_counts.items():
        for pair in zip(word, word[1:]):
            pair_counts[pair] += frequency
            pair_words[pair].add(word)
    return pair_counts, pair_words


def _pair_occurrences(word: Tuple[int, ...]) -> Counter:
    """Count each adjacent pair inside one word.

    Overlapping occurrences are counted the way `_count_pairs` counts
    them, so the indexed trainer and the naive trainer share one
    definition of pair frequency. In "aaa" the pair (a, a) counts twice
    even though a single merge pass replaces it once. Both trainers use
    this convention, so their ranking of pairs agrees.
    """
    occurrences: Counter = Counter()
    for pair in zip(word, word[1:]):
        occurrences[pair] += 1
    return occurrences


def _retire_word(
    word: Tuple[int, ...],
    frequency: int,
    pair_counts: Counter,
    pair_words: Dict[Pair, Set[Tuple[int, ...]]],
    heap: List[Tuple[int, Pair]],
) -> None:
    """Remove one word's contribution from the pair table and the index.

    A decrement must be pushed onto the heap just like an increment. The
    heap entry that carried the old, higher count becomes stale and is
    skipped on pop, so without pushing the new lower count the pair would
    disappear from consideration entirely even though it still occurs.
    """
    for pair, occurrences in _pair_occurrences(word).items():
        pair_counts[pair] -= frequency * occurrences
        if pair_counts[pair] <= 0:
            del pair_counts[pair]
        else:
            heapq.heappush(heap, (-pair_counts[pair], pair))
        pair_words[pair].discard(word)


def _admit_word(
    word: Tuple[int, ...],
    frequency: int,
    pair_counts: Counter,
    pair_words: Dict[Pair, Set[Tuple[int, ...]]],
    heap: List[Tuple[int, Pair]],
) -> None:
    """Add one word's contribution and push the affected pairs onto the heap."""
    for pair, occurrences in _pair_occurrences(word).items():
        pair_counts[pair] += frequency * occurrences
        pair_words[pair].add(word)
        heapq.heappush(heap, (-pair_counts[pair], pair))


def train_merges_indexed(
    word_counts: Dict[Tuple[int, ...], int], vocab_size: int
) -> List[Tuple[Pair, int]]:
    """Learn merges without recounting the whole corpus on every round.

    Two changes against `train_merges_naive`, and the complexity of both
    is the price of an artifact a reader can actually run:

    1. An index from pair to the set of words containing it, so a merge
       only touches the words that contain the merged pair instead of all
       of them.
    2. A max-heap of (negative count, pair) with lazy invalidation. The
       heap may hold stale entries; an entry is accepted only when its
       count still matches the live table, and skipped otherwise.

    The heap ordering (-count, pair) is exactly the tie-break rule used by
    `_best_pair`: highest frequency first, smallest pair on a tie. That is
    why the two implementations produce identical merges, which the test
    suite asserts directly rather than assuming.
    """
    counts = dict(word_counts)
    pair_counts, pair_words = _index_pairs(counts)
    heap: List[Tuple[int, Pair]] = [
        (-count, pair) for pair, count in pair_counts.items()
    ]
    heapq.heapify(heap)

    merges: List[Tuple[Pair, int]] = []
    for new_id in range(BYTE_VOCAB_SIZE, vocab_size):
        best = _pop_best(heap, pair_counts)
        if best is None:
            break
        merges.append((best, new_id))
        affected = list(pair_words.get(best, ()))
        for word in affected:
            frequency = counts.get(word)
            if frequency is None:
                continue
            _retire_word(word, frequency, pair_counts, pair_words, heap)
            del counts[word]
            merged = _merge_once(word, best, new_id)
            existing = counts.get(merged)
            if existing is not None:
                _retire_word(merged, existing, pair_counts, pair_words, heap)
                frequency += existing
            counts[merged] = frequency
            _admit_word(merged, frequency, pair_counts, pair_words, heap)
        pair_words.pop(best, None)
    return merges


def _pop_best(heap: List[Tuple[int, Pair]], pair_counts: Counter) -> Optional[Pair]:
    """Pop the highest-count pair, discarding entries whose count is stale.

    Terminates because every iteration removes one heap entry and the heap
    is finite.
    """
    while heap:
        negative_count, pair = heapq.heappop(heap)
        if pair_counts.get(pair, 0) == -negative_count:
            return pair
    return None


class BPETokenizer:
    """A trained byte-level BPE tokenizer.

    Construct one with `BPETokenizer.train(...)`. The constructor takes an
    already-computed merge list and is used by `train` and by tests.

    Attributes:
        merges: the learned merges in the order they were learned. Order
            is load-bearing: encoding replays them in exactly this order.
        vocab: maps every token id to the bytes it stands for.
    """

    def __init__(self, merges: Sequence[Tuple[Pair, int]]):
        """Build a tokenizer from an ordered merge list.

        Args:
            merges: ordered ((left_id, right_id), new_id) triples. The
                new ids must be consecutive starting at 256.

        Raises:
            ValueError: if the new ids are not consecutive from 256, or a
                merge references an id that does not exist yet.
        """
        self.merges: List[Tuple[Pair, int]] = [((a, b), n) for (a, b), n in merges]
        self.vocab: Dict[int, bytes] = {i: bytes([i]) for i in range(BYTE_VOCAB_SIZE)}
        expected_id = BYTE_VOCAB_SIZE
        for (left, right), new_id in self.merges:
            if new_id != expected_id:
                raise ValueError(
                    f"merge ids must be consecutive from {BYTE_VOCAB_SIZE}, "
                    f"expected {expected_id} but got {new_id}"
                )
            if left not in self.vocab or right not in self.vocab:
                raise ValueError(
                    f"merge ({left}, {right}) references an id that does not exist yet"
                )
            self.vocab[new_id] = self.vocab[left] + self.vocab[right]
            expected_id += 1
        # Rank of each merge, so encoding can ask "is this pair mergeable,
        # and how early was it learned" in constant time.
        self._merge_rank: Dict[Pair, int] = {
            pair: rank for rank, (pair, _) in enumerate(self.merges)
        }
        self._chunk_cache: Dict[str, Tuple[int, ...]] = {}

    @property
    def vocab_size(self) -> int:
        """Total number of token ids: 256 base bytes plus one per merge."""
        return BYTE_VOCAB_SIZE + len(self.merges)

    @classmethod
    def word_counts(cls, text: str) -> Counter:
        """Count how often each pre-token chunk occurs, as byte tuples.

        This is the only place the raw text is read. Everything after it
        works on word types and frequencies, which is why training cost
        scales with the vocabulary of the corpus rather than its length.
        """
        counts: Counter = Counter()
        for chunk in pre_tokenize(text):
            counts[tuple(chunk.encode("utf-8"))] += 1
        return counts

    @classmethod
    def train(
        cls, text: str, vocab_size: int, strategy: str = "indexed"
    ) -> "BPETokenizer":
        """Learn merges from `text` until the vocabulary reaches `vocab_size`.

        Args:
            text: the training corpus.
            vocab_size: target vocabulary size, at least 256. This is an
                upper bound, not a promise: a corpus with few distinct
                word types runs out of mergeable pairs and stops early.
            strategy: "indexed" (default, fast) or "naive" (the textbook
                recount, kept as the correctness oracle). Both produce
                identical merges.

        Returns:
            A trained tokenizer.

        Raises:
            ValueError: if vocab_size is below 256 or strategy is unknown.

        Termination: the loop inside either strategy runs at most
        `vocab_size - 256` times and stops early when no pair remains, so
        it always halts.
        """
        if vocab_size < BYTE_VOCAB_SIZE:
            raise ValueError(
                f"vocab_size must be at least {BYTE_VOCAB_SIZE}, got {vocab_size}"
            )
        counts = cls.word_counts(text)
        if strategy == "indexed":
            merges = train_merges_indexed(counts, vocab_size)
        elif strategy == "naive":
            merges = train_merges_naive(counts, vocab_size)
        else:
            raise ValueError(
                f"strategy must be 'indexed' or 'naive', got {strategy!r}"
            )
        return cls(merges)

    def _encode_chunk(self, chunk: str) -> Tuple[int, ...]:
        """Encode one pre-token chunk, memoised on the chunk string.

        Applies the lowest-ranked applicable merge repeatedly, rather than
        replaying the entire merge list. The two are equivalent: merge k
        produces a brand new symbol id 256+k, and the only new adjacencies
        it creates involve that new id, so it can never manufacture a pair
        belonging to an earlier merge. Nothing already passed can become
        applicable again.

        Complexity: O(len(chunk)^2) in the worst case instead of
        O(len(merges) * len(chunk)), which matters once the merge list is
        thousands long. The cache matters too, because real text repeats
        its chunks heavily.
        """
        cached = self._chunk_cache.get(chunk)
        if cached is not None:
            return cached
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
        encoded = tuple(symbols)
        self._chunk_cache[chunk] = encoded
        return encoded

    def encode(self, text: str) -> List[int]:
        """Encode text to token ids.

        Args:
            text: any string. The empty string encodes to [].

        Returns:
            A list of token ids, every one of which is in `self.vocab`.

        Raises:
            TypeError: if `text` is not a str.
        """
        if not isinstance(text, str):
            raise TypeError(f"encode needs a str, got {type(text).__name__}")
        token_ids: List[int] = []
        for chunk in pre_tokenize(text):
            token_ids.extend(self._encode_chunk(chunk))
        return token_ids

    def decode(self, token_ids: Iterable[int], errors: str = "strict") -> str:
        """Decode token ids back to text.

        Args:
            token_ids: ids produced by `encode`, or any subset of them.
            errors: passed to bytes.decode. The default "strict" raises on
                invalid UTF-8, which is what you want for a round trip.
                Use "replace" when inspecting a single token, since one
                token can hold a fragment of a multi-byte character.

        Returns:
            The decoded string.

        Raises:
            ValueError: if an id is not in the vocabulary.
            UnicodeDecodeError: if the bytes are not valid UTF-8 and
                errors="strict".
        """
        chunks: List[bytes] = []
        for token_id in token_ids:
            piece = self.vocab.get(token_id)
            if piece is None:
                raise ValueError(
                    f"token id {token_id} is not in a vocabulary of size "
                    f"{self.vocab_size}"
                )
            chunks.append(piece)
        return b"".join(chunks).decode("utf-8", errors=errors)

    def token_pieces(self, text: str) -> List[str]:
        """Return the text each token covers, for showing segmentation.

        Decoding one token at a time can split a multi-byte character, so
        this uses errors="replace" and is for display only, never for a
        round trip.
        """
        return [self.decode([token_id], errors="replace") for token_id in self.encode(text)]
