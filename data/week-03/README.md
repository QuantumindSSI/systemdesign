# Week 3 data

## `tokenizer_corpus.txt`

The training corpus for `experiments/week-03/vocab_vs_tokens.py` and for any
week-3 artifact that needs a tokenizer.

**Provenance.** Our own prose. It is a frozen snapshot of the reader-facing
bodies of the 33 posts written for weeks 0 to 2 of this series, taken on
2026-09-06: everything below the editorial `---` marker in each file, with
fenced code blocks, tables, block quotes, headings, list markers and inline
markdown removed, whitespace collapsed. No third-party text is included.

**Size.** 260,242 bytes, 43,245 whitespace-separated words, 8,105 distinct
pre-token chunk types under `lib.bpe.pre_tokenize`.

**Why frozen rather than regenerated.** The posts directory keeps growing, so
regenerating the corpus on every run would silently change every measurement
that quotes it. The file is committed and read as-is. When it is deliberately
refreshed, every article that quotes a number from it must be re-measured in
the same commit.

**Known bias, stated because it shapes the results.** This corpus is two weeks
of writing about caching and distributed systems by one author. It is small,
single-domain, and single-voice. A tokenizer trained on it learns merges for
"cache", "request" and "database" and learns nothing useful about digits,
identifiers, or any language other than English. That bias is the point in the
Sunday kickoff, which contrasts in-domain prose against a log line, but it
means no compression number measured here transfers to a general-purpose
tokenizer trained on a web-scale corpus. Treat the shape of the curve as the
finding, not the absolute values.
