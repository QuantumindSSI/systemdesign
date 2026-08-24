# Week 0 · Thu poll · 17:00 · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-20-thu-pm-poll.md` (v4, committed). This file is the
> platform-ready cut only — no editorial changes. Every limit below was measured, not
> estimated (Python `len()`, 2026-08-21).
>
> Deltas from the committed v4 copy, in full:
> 1. Audit header and H1 removed — repo artifacts, not post copy.
> 2. `**bold**` markers stripped — LinkedIn renders raw text, not markdown.
> 3. "Vote with a single letter in the comments, or in the poll widget where the
>    platform provides one." → "Vote in the poll, or with a single letter in the
>    comments." The widget exists on this platform; the conditional clause is dead
>    weight here.
> 4. Closing italic line kept as a plain final line.
> 5. "This morning I promised you a poll" → "Earlier today I promised you a poll" —
>    day 1 is running a day late and the announcement posts after the morning slot;
>    "earlier today" is true at 17:00 regardless of the AM posting hour.
> 6. "before the first post went out this morning" → "before the first post went out
>    today" — same truth-preservation; the calendar was committed 20 Aug 21:45, before
>    any posting today.
> 7. Everything else verbatim.

---

## 1 · Poll widget (attach to the post)

| Field | Value | Measured | Limit |
|---|---|---|---|
| Question | Over the next 100 weeks, where should this series go deepest? | 61 | 140 |
| Option 1 | A: Harness, loop & graph | 24 | 30 |
| Option 2 | B: Inference & edge deployment | 30 | 30 |
| Option 3 | C: System design fundamentals | 29 | 30 |
| Option 4 | D: Career & forward-deployed | 28 | 30 |
| Duration | 2 weeks | — | max offered |

- Option 2 sits exactly at the 30-character limit. If LinkedIn's composer rejects it
  (their counting has been known to drift), the pre-approved fallback is
  `B: Inference & edge deploym.` — do not improvise a different one.
- Options carry the A–D letters so widget votes and comment votes tally into the same
  four buckets; write-ins live in the comments by design.
- Duration rationale: the tally is not needed until pass two is planned (week 20+),
  so the longest window LinkedIn offers maximizes the sample. Overlap with the week 1
  Sunday poll is fine — separate posts, separate questions.

## 2 · Post body (paste exactly, 2,857 / 3,000 chars)

```text
Earlier today I promised you a poll, and I promised that before you voted I would tell you exactly what I believe. A stated prior can be tested. An unstated one quietly becomes a bias. Here is mine, stated properly: with its confidence, its sample, and its limits.

I believe most of you need the evaluation and harness layers most, because that is where the production systems I have inspected actually failed. I believe most of you want the career layer most, because that is where the effort pays its bills. Those are two different claims about the same audience. I hold each at roughly seventy percent — a personal credence, not a measurement, formed from the agent projects and the hiring processes I have personally been part of. The sample is small, it is enterprise-shaped, and it has never included you. That last part is the point. This poll is the instrument that measures what I have only been assuming, and its boundary is honest too: it measures this audience, not the field.

One vote. Over the next one hundred weeks, where should this series go deepest?

Option A — harness, loop, and graph engineering. Everything you build around the model: the tools, the verifiers, the stop conditions, and the multi-agent topologies that no job title fully owns yet.

Option B — inference and edge deployment. Serving engines, quantization, latency budgets, and the bill that arrives whether or not you understood it.

Option C — system design fundamentals. The classical layer of caching, consistency, and failure handling that quietly decides whether anything built above it works at all.

Option D — career and forward-deployed engineering. Converting the entire stack into interviews passed, offers signed, and a role that survives the next hype cycle.

Vote in the poll, or with a single letter in the comments. If your honest answer is not on this list, write it in. The most informative failure of any poll is the option it forgot to offer, and a write-in is the strongest form of disagreement you can hand me. Disagreement is not noise here. It is the input this system is designed to run on.

Two commitments, so this is measurement and not engagement theatre. The first pass of this series was committed to version control before the first post went out today, so your vote cannot flatter me into rewriting history. When the second pass is planned, the full tally will be published beside the re-weighted calendar, so you can check precisely how far your vote bent it — and if the result says my seventy percent was misplaced, you will watch it get corrected in public. Strong beliefs, held with stated confidence, updated on contact with evidence. That is the discipline this series teaches. It may as well be governed by it.

Sunday, 09:00: week one begins — system design fundamentals, starting with the CAP theorem, from first principles.
```

## 3 · Posting checklist

1. Start a new post → add a poll → enter the question and the four options in the
   A–D order above → set duration to 2 weeks.
2. Paste the body from the fenced block. Nothing outside the fence goes in.
3. Confirm the fold: the preview must cut inside "Here is mine, stated properly" —
   the promise-and-prior hook is the above-the-fold content.
4. No hashtags, no @-mentions, no edits after publish. The post's own text claims
   pre-registration; the published copy must match this file.
