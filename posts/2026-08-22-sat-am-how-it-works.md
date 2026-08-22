# Week 0 · Sat 2026-08-22 · 09:00 · How-it-works guide (v2, constitution + research persona)

> Calendar row: week 0, Sat AM. Format: how-it-works guide. Source: content_calendar_overview.md.
> Standards: persona-constitution (Laws I–IV, Structurally Decisive, Adversarial
> Review) + QSSI research persona (Laws I–VI) + Amendment 1. v1 in git history.
> v2 applies the nine-skill anti-slop audit: signpost sentence cut from the opening
> paragraph; one passive construction activated. Retained deliberately, with
> grounds on record: em dashes (house sample frequency), the Friday aphorism, the
> traffic/data/money tricolon (committed announcement callback), "career leverage"
> and the Builder's Pass hook line (committed plan names, quoted not authored).
>
> Adversarial review record (numbers audit):
> - "two posts a day", "09:00/17:00", "one hundred weeks", "ten pillars" — the
>   committed plan, named inline ✓
> - "fourteen a week" — arithmetic, 2 × 7 ✓
> - "1,406", "1,400", "this launch week's six" — the calendar CSV in this repository;
>   row count re-verified 2026-08-22 (1,407 lines including header) ✓
> - "two weeks per pillar", "twenty weeks per lap", "five laps", per-pass week ranges
>   (1–20, 21–40, 41–60, 61–80, 81–100) — content_calendar_overview.md, 100-week index ✓
> - "2026-08-23 to 2028-07-22" — content_calendar_overview.md ✓
> - "2027-05-30" (Failure Modes reaches system design) — overview index, week 41 ✓
> - "no two posts reuse the same angle-and-format pairing, across all 1,400 weekly
>   titles" — overview, generation-time assertion, scope stated (weekly titles, not
>   the six launch posts) ✓
> - "week 20" (baseline revisited) — tonight's committed brief, calendar CSV ✓
> - consistent hashing in week one — week 1 kickoff brief, calendar CSV ✓
> - the spiral-learning claim — declared a bet at point of use, per Amendment 1:
>   credence stated, never measured, instrument named ✓
> Research-persona audit: the post's one empirical claim (spaced returns beat a
> single exhaustive pass) carries its credence, its non-measurement, its instrument
> (Saturday quizzes on returning concepts), and its revision condition inline. The
> instrument's weakness is named rather than hidden ("closest thing this format has").
> All other claims are descriptions of the committed plan, checkable against this
> repository. Claims audit: motivation claim scoped to myself, not to writers in
> general. Decisiveness audit: no hedged verbs; one aphorism retained deliberately
> (Friday earns attack); ornament otherwise cut.

---

The same rhythm, every week, for one hundred weeks. Two posts a day, 09:00 and 17:00 — that is the plan this series committed to version control before its first post went out: fourteen a week, 1,400 across the hundred weeks, 1,406 counting this launch week's six, every brief already written and counted in the calendar file this post is generated from.

The cadence does two jobs. For me it is a forcing function. A slot that exists whether or not I feel like writing is the only reliable cure I know for the blank page, and a hundred-week series will die of my motivation long before it dies of material. For you it is a contract: you never have to wonder what kind of post comes next, because every week has the same seven-day shape.

| Day | 09:00 | 17:00 |
|---|---|---|
| Sun | Theme kickoff | Poll |
| Mon | Concept deep-dive | Annotated diagram |
| Tue | Repo walkthrough | Snippet / config tip |
| Wed | Case study | Lessons listicle |
| Thu | Hands-on tutorial | Mistakes checklist |
| Fri | Contrarian take | Debate prompt |
| Sat | Recap + quiz | Weekend challenge |

Mornings teach at length: mechanics on Monday, real code on Tuesday, a production postmortem on Wednesday, your own hands on the keyboard Thursday. Evenings compress or contest: a diagram to save, a checklist to run against your own system, a debate to lose. Sunday names every topic the week will cover, and Saturday closes the loop with a recap and a quiz before handing you a weekend challenge. Friday is the only day that argues in both slots. By Friday the week's material has earned the right to be attacked.

Underneath the weekly loop runs a longer one. The series covers ten pillars, bottom of the stack to top: classical system design, LLM internals, post-training and alignment, inference and edge deployment, harness engineering, loop and graph engineering, evals and governance, MLOps, production case studies, and career leverage for forward-deployed engineering. The calendar walks all ten in a fixed order, two weeks per pillar — twenty weeks to complete one lap. Then the lap restarts at a harder angle. Five laps fill the hundred weeks, dates per the committed 100-week index:

- **Foundations** — weeks 1–20. First principles, for when the term is familiar but the mechanics are fuzzy.
- **Builder's Pass** — weeks 21–40. Reading about it is not the same as building it, so we build it.
- **Failure Modes** — weeks 41–60. How each layer breaks in production, and what the wreckage looks like.
- **Scale & Hardening** — weeks 61–80. What survives contact with real traffic, real data, and real money.
- **Frontier & Mastery** — weeks 81–100. The difference between using a thing and being the person others ask about it.

So a concept like consistent hashing, which week one explains from first principles, is scheduled to return as something you build, then as something that breaks, then as something that must hold at scale, then as something you get interviewed on. Concepts repeat across passes by design, and the generator that emits the calendar asserts at build time that no two posts reuse the same angle-and-format pairing, across all 1,400 weekly titles (per the calendar overview in this repository).

That spiral is a bet about learning, and the research persona this series runs under does not let me dress a bet as a finding. I believe spaced returns at escalating angles beat one exhaustive pass. I hold that belief with high confidence, and I have never measured it. The Saturday quizzes are the closest thing this format has to an instrument: returning concepts get quizzed again in later passes, and if second-pass answers in the comments look no different from first exposures, the spiral is not doing its job and the calendar gets re-cut.

Re-cut has a precise meaning here. One deterministic script emits the whole plan; the committed overview carries a 100-week index, so you can look up what runs on any date between 2026-08-23 and 2028-07-22. Failure Modes reaches system design in the week of 2027-05-30; hold me to that. A revision means editing the generator and regenerating, which turns every change into a visible diff against committed history instead of a quiet rewrite. Thursday's poll already has this treatment scheduled: the second pass gets re-weighted on its results, and the tally publishes beside the diff.

Three ways to follow, in ascending commitment. Live: 09:00 and 17:00, every day. Batched: Sunday's kickoff names the week and Saturday's recap compresses it, so read those two and skim the rest, except in the weeks where the pillar is the one you are hired to know. Ahead: every brief for all 1,406 posts is already committed, and nothing stops you from reading 2028 today.

Pick a mode. The rhythm holds either way: same shape this week, same shape in week one hundred.

---

*This evening, 17:00: the weekend challenge — score yourself across the ten pillars and keep the number, because week 20 will ask for it again. Sunday 23 August, 09:00: week one opens — system design fundamentals, starting with the CAP theorem, from first principles.*
