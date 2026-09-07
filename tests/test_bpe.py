"""Tests for lib/bpe.py: round trips, determinism, boundaries, errors."""

import unittest

from lib.bpe import BYTE_VOCAB_SIZE, BPETokenizer, pre_tokenize

CORPUS = (
    "the cache expired and every request went to the database. "
    "the database was not ready for every request at once. "
    "a cache that expires together is a cache that fails together. "
) * 12

# CORPUS has few distinct word types, so it runs out of mergeable pairs
# well before a large vocabulary is reached. RICH_CORPUS has hundreds of
# distinct types and is used wherever a test needs training to actually
# reach the requested size.
RICH_CORPUS = " ".join(
    f"request{i} cache{i} database{i} expired{i}" for i in range(240)
)


class TestPreTokenize(unittest.TestCase):
    def test_is_lossless(self):
        for text in ["", "a", "a b", "  leading", "trailing  ", "a\n\nb\t c"]:
            self.assertEqual("".join(pre_tokenize(text)), text)

    def test_leading_space_attaches_to_word(self):
        self.assertEqual(pre_tokenize("the cat"), ["the", " cat"])

    def test_whitespace_run_is_its_own_chunk(self):
        self.assertEqual(pre_tokenize("a\n"), ["a", "\n"])

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            pre_tokenize(b"bytes are not str")


class TestTraining(unittest.TestCase):
    def test_vocab_size_is_reached_on_a_rich_corpus(self):
        tokenizer = BPETokenizer.train(RICH_CORPUS, vocab_size=400)
        self.assertEqual(tokenizer.vocab_size, 400)
        self.assertEqual(len(tokenizer.merges), 400 - BYTE_VOCAB_SIZE)

    def test_vocab_size_is_an_upper_bound_not_a_promise(self):
        # A corpus with few distinct word types exhausts its mergeable
        # pairs early. The documented contract is a cap, not a guarantee.
        tokenizer = BPETokenizer.train(CORPUS, vocab_size=4000)
        self.assertLess(tokenizer.vocab_size, 4000)
        self.assertEqual(
            tokenizer.vocab_size, BYTE_VOCAB_SIZE + len(tokenizer.merges)
        )

    def test_base_vocabulary_requires_no_merges(self):
        tokenizer = BPETokenizer.train(CORPUS, vocab_size=BYTE_VOCAB_SIZE)
        self.assertEqual(tokenizer.merges, [])
        self.assertEqual(tokenizer.vocab_size, BYTE_VOCAB_SIZE)

    def test_below_base_vocabulary_raises(self):
        with self.assertRaises(ValueError):
            BPETokenizer.train(CORPUS, vocab_size=255)

    def test_training_is_deterministic(self):
        first = BPETokenizer.train(CORPUS, vocab_size=350)
        second = BPETokenizer.train(CORPUS, vocab_size=350)
        self.assertEqual(first.merges, second.merges)

    def test_indexed_strategy_matches_the_naive_oracle(self):
        # The fast path exists only for speed. If it ever disagrees with
        # the textbook recount, the fast path is wrong, not the oracle.
        for corpus in (CORPUS, RICH_CORPUS):
            for vocab_size in (280, 320, 450):
                fast = BPETokenizer.train(corpus, vocab_size, strategy="indexed")
                slow = BPETokenizer.train(corpus, vocab_size, strategy="naive")
                self.assertEqual(fast.merges, slow.merges)

    def test_both_strategies_encode_identically(self):
        text = "the database was not ready for every request at once"
        fast = BPETokenizer.train(RICH_CORPUS, 400, strategy="indexed")
        slow = BPETokenizer.train(RICH_CORPUS, 400, strategy="naive")
        self.assertEqual(fast.encode(text), slow.encode(text))

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError) as ctx:
            BPETokenizer.train(CORPUS, 300, strategy="magic")
        self.assertIn("indexed", str(ctx.exception))

    def test_exhausted_corpus_stops_early(self):
        # "aa" has exactly one mergeable pair, so training cannot reach 300.
        tokenizer = BPETokenizer.train("aa", vocab_size=300)
        self.assertEqual(len(tokenizer.merges), 1)
        self.assertLess(tokenizer.vocab_size, 300)

    def test_empty_corpus_produces_no_merges(self):
        tokenizer = BPETokenizer.train("", vocab_size=300)
        self.assertEqual(tokenizer.merges, [])


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tokenizer = BPETokenizer.train(CORPUS, vocab_size=400)

    def test_roundtrip_on_training_text(self):
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(CORPUS)), CORPUS)

    def test_roundtrip_on_unseen_text(self):
        unseen = "A totally unseen sentence, with punctuation!"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(unseen)), unseen)

    def test_roundtrip_on_non_ascii(self):
        # Byte level means there is no unknown token, ever.
        text = "cafe\u0301 na\u00efve \u4f60\u597d \U0001f600"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(text)), text)

    def test_roundtrip_on_whitespace_shapes(self):
        for text in ["", " ", "\n\n", "  a  b  ", "\ta\n"]:
            self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(text)), text)

    def test_empty_string_encodes_to_nothing(self):
        self.assertEqual(self.tokenizer.encode(""), [])

    def test_every_id_is_in_vocabulary(self):
        for token_id in self.tokenizer.encode(CORPUS):
            self.assertIn(token_id, self.tokenizer.vocab)


class TestCompressionBehaviour(unittest.TestCase):
    def test_more_merges_never_lengthen_the_encoding(self):
        previous = len(
            BPETokenizer.train(RICH_CORPUS, BYTE_VOCAB_SIZE).encode(RICH_CORPUS)
        )
        for vocab_size in (300, 400, 500, 600):
            current = len(
                BPETokenizer.train(RICH_CORPUS, vocab_size).encode(RICH_CORPUS)
            )
            self.assertLessEqual(current, previous)
            previous = current

    def test_untrained_tokenizer_emits_one_token_per_byte(self):
        tokenizer = BPETokenizer.train("", vocab_size=BYTE_VOCAB_SIZE)
        text = "hello"
        self.assertEqual(len(tokenizer.encode(text)), len(text.encode("utf-8")))

    def test_merges_do_not_cross_pretoken_boundaries(self):
        # "ab" repeated as two separate words must never merge into one token.
        tokenizer = BPETokenizer.train("ab ab ab ab ab ab", vocab_size=300)
        pieces = tokenizer.token_pieces("ab ab")
        self.assertEqual("".join(pieces), "ab ab")
        for piece in pieces:
            self.assertNotIn("b a", piece)


class TestErrorPaths(unittest.TestCase):
    def setUp(self):
        self.tokenizer = BPETokenizer.train(CORPUS, vocab_size=320)

    def test_encode_rejects_non_string(self):
        with self.assertRaises(TypeError):
            self.tokenizer.encode(123)

    def test_decode_rejects_unknown_id(self):
        with self.assertRaises(ValueError) as ctx:
            self.tokenizer.decode([99999])
        self.assertIn("not in a vocabulary", str(ctx.exception))

    def test_non_consecutive_merge_ids_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            BPETokenizer([((97, 98), 999)])
        self.assertIn("consecutive", str(ctx.exception))

    def test_merge_referencing_future_id_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            BPETokenizer([((256, 97), 256)])
        self.assertIn("does not exist yet", str(ctx.exception))

    def test_token_pieces_reconstruct_the_text(self):
        text = "the database was not ready"
        self.assertEqual("".join(self.tokenizer.token_pieces(text)), text)


if __name__ == "__main__":
    unittest.main()
