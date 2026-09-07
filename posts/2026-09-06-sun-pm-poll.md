# Week 3 · Sun 2026-09-06 · 17:00 · Poll: Where are you with LLM internals?

> Calendar row: W3 Sun PM, 17:00 (CSV row `37:3`). Format: poll.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 1.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + QSSI research persona (prior stated with credence, sample
> characteristics, update condition, boundary condition) + AGENTS.md canonical
> source rule + AGENTS.md human-first voice.
>
> **Canonical source rule applied (effective today).** No external code
> repository is named, linked, or implied. The CSV `source` column for this row
> names one; per `AGENTS.md` that string is an internal routing hint only.
>
> Committed calendar beats, all four options present below: A learning the
> vocabulary | B built it once in a side project | C run it in production |
> D debugged it during an incident.
> Committed CTA: "Repost this so your team sees it."
>
> **Publication-gap remediation (carried forward from 2026-09-04).** No post in
> this sequence has reached readers, so the reference to this morning's kickoff
> restates its substance inline. A reader arriving here first can still vote.
>
> Numbers used below, all from this repository, measured today by
> `experiments/week-03/vocab_vs_tokens.py` against
> `data/week-03/tokenizer_corpus.txt` (exit code 0, "All assertions passed"):
> - 7 tokens for the in-domain sentence, 21 for
>   `order_id=8f3a91c4 status=PENDING`, both at vocabulary 4,096
> - `1234567` becomes `['12', '3', '4', '5', '6', '7']`
> - each doubling of the vocabulary removes 53.2%, then 26.0%, then 21.6%,
>   then 18.5% of the remaining tokens
> - the corpus is small, single-domain and single-author, and the body says so
>
> Adversarial review record (2026-09-06):
> - The four options are vantage points, not a ranking. The post says so
>   explicitly, because presenting D as the expert answer would bias the
>   instrument it is trying to read ✓
> - The update condition is defined before any votes exist, so the poll cannot
>   be retrofitted to whatever result arrives ✓
> - The prior carries its credence, its sample, and its boundary inline, and is
>   labeled personal observation rather than a survey ✓
> - The tokenizer figures carry their corpus caveat at the point of use, not
>   only in this unpublished header ✓
> - No claim is made about the status of the week 0 or week 1 polls, since
>   neither has a verified current state in this repository ✓
> - Reader-facing body: 942 words, measured 2026-09-06 by whitespace split over
>   everything below the `---` marker. Above the 500 to 700-word evening band,
>   because a poll has to carry a stated prior, four described options, and the
>   update condition. Deliberate, and consistent with the Fri 2026-09-04 debate
>   post, which recorded the same deviation for the same structural reason ✓
> - Zero em dashes.

---

**Topic:** A pulse check on where you actually stand with the inside of a language model

**Subtitle:** Four honest positions, none of them better than the others, and a prior of mine that this poll exists to correct.

Good evening. Before the deep dives start tomorrow, one question, and I would like the unflattering answer rather than the impressive one.

This morning I opened the week on what happens inside a language model: self-attention, multi-head attention, BPE tokenization, embedding layers, rotary positional encodings, and where the layer norm goes. The concrete piece was a tokenizer we wrote and trained ourselves, on our own two weeks of writing about caching. Trained that way, it turns "the cache expired before the request arrived" into 7 tokens, one per word. It turns the log line `order_id=8f3a91c4 status=PENDING` into 21 tokens for 32 characters. And it turns `1234567` into `['12', '3', '4', '5', '6', '7']`.

That last one is the whole reason the week exists. If you ask a model to add up a number, the number it receives is not a number. It is one arbitrary two-digit fragment and five loose digits, because token boundaries follow frequency and nobody's corpus contains your invoice ID often enough to earn a merge. The corpus we trained on is small and one-domain, so those exact counts are ours and not a general benchmark, but the mechanism transfers to every tokenizer there is.

So: how visible is that mechanism for you right now?

I want to state my prior before you vote, because an unstated prior stops being a hypothesis and quietly becomes a bias. **I expect most of you to land in B, and I hold that at roughly fifty-five percent.** That is a personal credence formed from the engineers I have worked with, hired, and interviewed over the last few years, not a measurement of anything. The sample is small, it skews toward people building applications on top of models rather than training them, and it has never included you. That last part is why this poll exists.

One vote. Which of these describes your relationship with the internals of a language model?

**Option A: learning the vocabulary.** You know the words. Attention, embeddings, tokens, heads. You can follow a conversation about them and you would not want to be asked to draw the data flow on a whiteboard.

**Option B: built it once in a side project.** You have written or closely read an implementation, probably a small GPT, probably on a weekend. You got it working. Some of it you understood, and some of it you copied because it worked and you moved on.

**Option C: run it in production.** Your job involves a model serving real traffic. You have opinions about token counts because they appear on an invoice, and about context length because it has broken something you own.

**Option D: debugged it during an incident.** At some point the thing failed in a way that only made sense from the inside, and you had to go in. Truncation, degradation over long inputs, a tokenizer mangling a field, a fine-tune that would not converge. You did not choose this knowledge; it was issued to you at an unpleasant hour.

These are vantage points, not a ladder, and I want to be clear about that because it changes what the answers are worth. D is not the expert option. Someone who once spent a night on a tokenizer bug may know one mechanism in painful detail and nothing about the other five. Someone in A who has read carefully may hold a cleaner mental model than someone in C who has only ever tuned parameters. Vote for where you are, not where the phrasing sounds strongest.

Here is what I will do with the result, decided now, before any votes exist. If A and B dominate, tomorrow's essay keeps every mechanism anchored to a worked numeric example and I slow down at the projections. If C and D dominate, the week keeps the same six topics but spends more of its weight on the operational consequences: where these mechanisms show up in a bill, a latency graph, or a corrupted field, and less on rebuilding intuition you already have. Either way the six topics stay fixed, because the calendar for this pass is committed and I am not going to pretend otherwise. What moves is the depth allocation inside each day.

And the boundary, stated honestly: this measures this audience on this Sunday, not the field. A poll on a post about model internals selects for people who clicked on a post about model internals. If the result comes back overwhelmingly D, the correct conclusion is that this audience skews experienced, not that most engineers have debugged an attention bug.

If none of the four fits, write yours in. The most informative failure of any poll is the option it forgot to offer, and a write-in tells me more than a vote for the least wrong box. If your honest answer is "I use these models daily and have never once thought about what happens before the first matrix multiply," that is a real position and it is worth saying out loud, because it is more common than the confident phrasing on this platform suggests.

This is a different question from the one week 1 asked. That poll asked where your gap was inside a topic. This one asks what altitude you are flying at, so I know how far down to start.

Repost this so your team sees it.

---

*Tomorrow, 09:00: self-attention from first principles, plus the answers to Saturday's three questions.*
