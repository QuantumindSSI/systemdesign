# Week 3 · Sun 2026-09-06 · Teaser bundle (Twitter/X, LinkedIn, Reddit, Quora)

> Calendar row: W3 Sun, both slots. Per `content_calendar_overview.md`, this
> file contains platform-native hooks that send readers to Substack rather
> than reproducing either post in full.
>
> Source posts:
> - `posts/2026-09-06-sun-am-theme-kickoff.md`
> - `posts/2026-09-06-sun-pm-poll.md`
>
> Link placeholder: replace each `{substack-url}` with the corresponding live
> Substack URL at posting time. No publication URL is stored in this repo, so
> none has been guessed.
>
> **Canonical source rule applied (effective today).** No external code
> repository is named, linked, or implied in any draft below.
>
> **Cadence note.** Week 2 (2026-08-31 to 2026-09-05) shipped no teaser
> bundles, so this is the first one since Fri 2026-08-28. The omission is
> recorded rather than backfilled, since those posts' teasers would now be
> promoting a week that has ended.
>
> Editorial checks (2026-09-06):
> - Every number below is from `experiments/week-03/vocab_vs_tokens.py` on
>   today's run against `data/week-03/tokenizer_corpus.txt`: 7 tokens for the
>   in-domain sentence, 21 for the log line, `1234567` splitting into six
>   pieces, and cuts of 53.2%, 26.0%, 21.6%, 18.5% per doubling.
> - The corpus caveat travels with the numbers in the longer drafts, so no
>   platform gets the result without its limit.
> - Twitter/X drafts are under 280 characters counted with the literal
>   `{substack-url}` placeholder in place.
> - LinkedIn drafts use short paragraphs and one link, without hashtag stacks.
> - Reddit drafts explain why the link is relevant instead of dropping a bare
>   headline. Quora drafts open by answering a plausible reader question.
> - No invented engineer, incident, benchmark, or production scar appears.
> - Zero em dashes.

---

## 09:00 kickoff: "What Actually Happens Inside a Language Model"

### Twitter/X

Trained our own tokenizer today. "the cache expired before the request arrived" costs 7 tokens. The log line order_id=8f3a91c4 status=PENDING costs 21, for 32 characters. And 1234567 becomes ['12','3','4','5','6','7']. New week starts here: {substack-url}

### LinkedIn

If you have ever watched a model mangle an invoice number, here is the mechanism, measured rather than described.

I trained a byte-level tokenizer from scratch on our own corpus and fed it strings it had never seen. An in-domain sentence, "the cache expired before the request arrived", cost 7 tokens: one per word. An ordinary log line, order_id=8f3a91c4 status=PENDING, cost 21 tokens for 32 characters.

Then the number. At a vocabulary of 4,096, 1234567 came out as ['12', '3', '4', '5', '6', '7']. One arbitrary two-digit fragment and five loose digits.

The model never receives your number. It receives the pieces that frequency happened to leave, because merges are learned by how often things co-occur and nobody's corpus contains your invoice ID often enough to earn one. No amount of rewording the prompt changes what the tokenizer did before the prompt arrived.

Caveat worth stating: our corpus is small and single-domain, which is exactly why in-domain prose scores so well here. The absolute numbers are ours. The mechanism is everyone's.

This kicks off a week on the six mechanisms inside the model, one a day, all written from scratch so you can run them.

{substack-url}

### Reddit

I keep meeting engineers who ship model-backed features confidently and have never looked at what happens to their input before the first matrix multiply, and I think that gap explains a lot of "the model is being weird" bugs.

So I trained a byte-level BPE tokenizer from scratch and measured it. Two findings.

First, diminishing returns are steeper than people expect. Doubling the vocabulary from 256 to 512 cut the corpus token count by 53.2%. The next doubling cut 26.0% of what remained, then 21.6%, then 18.5%. Every step costs twice as much and buys less, and the curve keeps flattening.

Second, and more useful operationally: at a vocabulary of 4,096, an in-domain sentence cost 7 tokens while the log line order_id=8f3a91c4 status=PENDING cost 21 tokens for 32 characters, and 1234567 came out as ['12','3','4','5','6','7']. Merges follow frequency, so anything your corpus did not see often shatters.

Honest limit: the corpus is small, single-domain and single-author, which inflates the in-domain result. Take the shape, not the absolute values.

Write-up kicks off a week on attention, multi-head attention, BPE, embeddings, RoPE and layer-norm placement, with the code and its tests included so you can rerun everything: {substack-url}

### Quora

**Why do language models sometimes get numbers wrong even when the arithmetic is trivial?**

Part of the answer is that the model never sees your number. It sees the fragments a tokenizer produced, and those fragments follow frequency rather than mathematics.

I measured this on a tokenizer I trained from scratch. At a vocabulary of 4,096, the string 1234567 came out as ['12', '3', '4', '5', '6', '7']: one arbitrary two-digit chunk and five separate digits. Nothing in that sequence tells the model it is looking at one seven-digit quantity, because an arbitrary seven-digit number is not frequent enough in any training corpus to earn its own token.

The same effect explains why identifiers are expensive. In the same test, an ordinary sentence cost 7 tokens while a log line of 32 characters cost 21, purely because the tokenizer had learned the words and had never learned the identifier.

I wrote up the experiment and the week of mechanisms behind it, from attention through to layer norm placement, here: {substack-url}

---

## 17:00 poll: "Where Are You With LLM Internals?"

### Twitter/X

Quick one before the deep dives start. Where are you with the inside of a language model? A: learning the vocabulary. B: built it once in a side project. C: run it in production. D: debugged it during an incident. Not a ranking. Vote honestly: {substack-url}

### LinkedIn

Before a week of deep dives on model internals, one question, and I want the unflattering answer rather than the impressive one.

Where are you with the inside of a language model?

A: learning the vocabulary.
B: built it once in a side project.
C: run it in production.
D: debugged it during an incident.

These are vantage points, not a ladder. Someone who spent one bad night on a tokenizer bug may know that mechanism in detail and nothing about the other five. Someone still learning the vocabulary, reading carefully, may hold a cleaner mental model than someone who has only ever tuned parameters.

My prior is that most people land in B, and I hold that at about fifty-five percent. That is a personal credence from the engineers I have worked with and hired, not a measurement, and the sample has never included you. The poll is what corrects it.

{substack-url}

### Reddit

Running a pulse check before a week of posts on model internals, and I stated my prior before opening the vote so it can actually be wrong: I expect most respondents to be in the "built a small GPT once on a weekend" bucket, held at roughly fifty-five percent as a personal credence from people I have worked with and hired.

The four options are learning the vocabulary, built it once in a side project, run it in production, and debugged it during an incident. Deliberately not a ranking. I also committed in advance to what changes based on the result: if the first two dominate, every mechanism gets anchored to a worked numeric example; if the last two dominate, the same six topics stay but more weight goes to operational consequences. The topic list itself does not move, because the calendar is committed.

Vote or write in a fifth option, which is usually more informative than picking the least wrong box: {substack-url}

### Quora

**How much do I actually need to know about the internals of a language model to work with one professionally?**

It depends less on your job title than on which failure you are likely to meet. If you only assemble prompts and read responses, you can go a long way without the mechanism. The moment something fails from the inside, a field getting mangled by tokenization, quality degrading as inputs get long, a fine-tune that will not converge, the mechanism is the only thing that helps.

A useful self-assessment is to place yourself among four positions: learning the vocabulary, built a small model once, run one in production, or debugged one during an incident. None is better than the others, and most people are in different positions for different mechanisms.

I put that question to readers as a poll, along with what I will change in the week depending on the answer: {substack-url}

---

*Tomorrow, 09:00: self-attention from first principles, plus the answers to
Saturday's three quiz questions. The annotated diagram follows at 17:00.*
