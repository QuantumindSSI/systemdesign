# Week 0 · Day 1 AM · Series announcement · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-20-thu-am-series-announcement.md` (v4 + provenance
> commit e48e1b5). That text is 6,697 chars; LinkedIn's post limit is 3,000. This cut
> is 2,994 chars, measured (`len()`, 2026-08-21), sha256 e815b622fde16ce9. The repo md
> stays canonical and the post links it, so nothing is lost — only compressed.
>
> Deltas from the committed v4 copy, in full:
> 1. Condensed 6,697 → 2,994. Every number kept its source in-sentence: NANDA (title +
>    52/153/300 methodology + no-P&L-impact finding + direct-verification/press-coverage
>    custody split), Iris.ai 88% as reported, base-rate pushback, personal-sample
>    boundary, 1,406 → version control, 29 repos → GitHub API 20 Aug, takedown retired
>    with a note. 21 content gates asserted programmatically before this file was written.
> 2. Audit header, H1, and markdown markers stripped — LinkedIn renders raw text.
> 3. Spelled-out numbers rendered as digits (feed compression; Amendment 1 governs
>    sourcing, not spelling).
> 4. Weekly-cadence sentence cut — Saturday's how-it-works post owns that material.
> 5. Repo link added as the closing line. The post claims pre-registration is checkable;
>    the link is what makes it checkable. REQUIREMENT: the repo must be public before
>    this posts.
> 6. "which brings me to this evening" → "tonight"; footer reduced to the
>    seven-layer-map teaser (the poll teaser already lives in the body).
>
> Timing (day 1 is running one day late — calendar said Thu 20 Aug, posting Fri 21 Aug):
> - All in-copy time references are relative and hold if this posts today BEFORE 17:00:
>   "At 17:00 today: the first poll" requires the poll to go out at 17:00 the same day
>   (its publish cut is ready and time-neutral). "Starting Sunday" and "Week one opens
>   Sunday" = 23 Aug, per the calendar — true regardless of the slip.
> - "Tomorrow, 09:00: the seven-layer map" is true only if Friday's calendar content
>   (seven-layer map + repo roundup) runs Saturday 22 Aug.
> - OPEN DECISION (not made here): sliding Friday→Saturday displaces Saturday's
>   how-it-works + weekend challenge into Sunday 23 Aug, which collides with the week 1
>   kickoff + week 1 poll. Either compress four posts into Saturday, or re-slot the two
>   Saturday pieces; the calendar CSV must then be regenerated to match what actually ran.

---

## 1 · Posting checklist

1. Confirm github.com/QuantumindSSI/systemdesign is public. The post links it as
   the plan and audit trail only, never as somewhere to read unpublished posts. It
   stakes its credibility on inspection.
2. Text post, no poll widget, no hashtags, no @-mentions, no image.
3. Post before 17:00 today, then publish the poll cut at 17:00 sharp.
4. Confirm the fold: the preview must end inside the hook — "…renamed, deprioritised,
   and forgotten." territory, before the NANDA material starts.
5. No edits after publish. The copy claims pre-registration; the published text must
   match this file exactly.

## 2 · Post body (paste exactly, 2,994 / 3,000 chars)

```text
The models keep getting better, and the agents built on them keep dying in prototype. The failures are quiet: failed prototypes do not get postmortems. They get renamed, deprioritised, and forgotten.

A number gets passed around for this; the retelling flattened it. Source: MIT's Project NANDA, "The GenAI Divide: State of AI in Business 2025" — reported methodology: 52 executive interviews, 153 leaders surveyed, 300 deployments. Its finding: 95% of enterprise GenAI pilots produced no measurable P&L impact. Dying before production is a different stat: 88%, per Iris.ai's 2026 analysis, as reported. Two failure modes wear one headline. Fair pushback: pilots are supposed to fail; attrition is normal for enterprise tech. Custody: NANDA verified directly at MIT's Media Lab; findings cited via press coverage. What I can defend without a survey: in deployments I inspected, the model was almost never the cause of death. Small enterprise sample; the claim carries that boundary.

The skills that prevent this death are not a menu. They are a dependency graph with an order. You cannot debug a runaway agent loop if you cannot read the inference bill: it is a cost problem before it is a logic problem. One stack, silicon to strategy. Most engineers walk it backwards: deep on transformer math, improvising where projects die. If your work never leaves the notebook, ignore the order. If it must survive other people's traffic, data, and money, the order decides whether you ship.

I will walk the whole graph, in order, in public: two posts a day for 100 weeks, starting Sunday. Mornings teach. Evenings argue. Ten pillars, bottom to top: system design, LLM internals, post-training, inference and edge, harnesses, loops and graphs, evals and governance, MLOps, case studies, career and FDE.

A series about discipline must survive its own standards. Five commitments: Pre-registration — all 1,406 planned posts were committed to version control before this first one went out. Verified citations — the 29 repos behind the series were checked against the GitHub API on 20 August; one, removed by a copyright takedown, was retired with a note. Every number names its source inline or admits it cannot — you just watched it dissect this headline. Corrections are content: their own posts. The plan updates on evidence — which brings me to tonight.

At 17:00 today: the first poll. I state what I believe you need most from these hundred weeks — formed from projects and hiring I watched, never measured. The poll measures it. Pass two is re-weighted on the results, tally published beside the revised calendar. A belief you refuse to measure is a belief you are protecting. Tonight you break one of mine.

Week one opens Sunday: system design fundamentals, starting with the CAP theorem from first principles. If your agent dies in prototype next quarter, you will know which layer it died in.

Plan and audit trail: github.com/QuantumindSSI/systemdesign
Tomorrow, 09:00: the seven-layer map.
```
