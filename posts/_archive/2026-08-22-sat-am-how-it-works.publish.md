# Week 0 · Sat AM · How-it-works guide · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-22-sat-am-how-it-works.md` (v2). That body is
> 4,818 chars; LinkedIn's post limit is 3,000. This cut is 2,999 chars, measured
> (`len()`, 2026-08-22), sha256 44eecc0290369d08. The repo md stays canonical,
> so nothing is lost — only compressed. The two v2 canonical edits (signpost
> sentence cut, passive construction activated) fall outside this cut, which
> never contained either line: the paste body is byte-identical to the v1 cut,
> re-verified against the recorded sha256.
>
> Deltas from the committed v2 copy, in full:
> 1. Condensed 4,945 → 2,999. Every number kept its source or flag in-sentence:
>    post counts → the committed calendar ("all pre-registered"); pass ranges, run
>    dates, and 2027-05-30 → the committed index; the spiral-learning claim →
>    declared a bet, held with high confidence, never measured, instrument named.
>    10 content gates asserted programmatically before this file was written.
> 2. Audit header, H1, and markdown stripped — LinkedIn renders raw text. The
>    seven-day table flattened to seven plain lines; pass bullets to a numbered list.
> 3. Spelled-out numbers rendered as digits (feed compression; Amendment 1 governs
>    sourcing, not spelling).
> 4. Ten-pillar enumeration cut from the pillar paragraph: the day-1 announcement
>    cut already published the full list, and tonight's challenge post re-enumerates
>    it as the thing being scored.
> 5. Repo link added as the closing line (the canonical stays linkless, per house
>    pattern). REQUIREMENT: the repo must be public before this posts.
> 6. Canonical footer's week-20 baseline callback dropped from the teaser — tonight's
>    challenge post owns that material.
>
> Timing (inherits the day-1 slip; see the announcement publish cut):
> - Calendar slot: Sat 22 Aug, 09:00. The day-1 cut recorded a one-day slip and an
>   OPEN DECISION on Friday's content (seven-layer map + repo roundup), which has no
>   committed post files as of this writing. That decision is not resolved here.
> - This copy is slip-proof except one pairing: "Tonight, 17:00" requires the
>   weekend-challenge cut to run the same evening as this post, whichever day that
>   turns out to be. "Sunday 23 August" and "week one opens" are date-anchored and
>   hold regardless of the slip.
> - This post cannot slide to Sunday: 09:00 Sun belongs to the week-1 kickoff. If it
>   cannot run Saturday, the collision options in the day-1 cut apply, and the
>   calendar CSV must be regenerated to match what actually ran.

---

## 1 · Posting checklist

1. Resolve the day-0 timing decision first. This cut assumes it runs Saturday
   22 Aug at 09:00, with the weekend-challenge cut at 17:00 the same day.
2. Confirm github.com/QuantumindSSI/systemdesign is public. The post links it as
   the plan and audit trail. It must not invite anyone to consume a post before
   that post's own day; the embargo in `tools/publication_gate.py` enforces that
   no unpublished post is reachable there.
3. Text post, no poll widget, no hashtags, no @-mentions, no image.
4. Confirm the fold: the preview must end inside the hook — "…1,406 counting this
   launch week's six, all pre-registered." territory, before the table starts.
5. No edits after publish. The copy claims pre-registration; the published text
   must match this file exactly.

## 2 · Post body (paste exactly, 2,999 / 3,000 chars)

```text
Same rhythm, every week, for 100 weeks. Two posts a day, 09:00 and 17:00 — the plan this series committed to version control before its first post went out: 14 a week, 1,400 across the run, 1,406 counting this launch week's six, all pre-registered.

The cadence does two jobs. For me it is a forcing function: a slot that exists whether or not I feel like writing, because a 100-week series will die of my motivation long before it dies of material. For you it is a contract: every week has the same seven-day shape.

Sun: theme kickoff · poll
Mon: concept deep-dive · annotated diagram
Tue: repo walkthrough · snippet / config tip
Wed: case study · lessons listicle
Thu: hands-on tutorial · mistakes checklist
Fri: contrarian take · debate prompt
Sat: recap + quiz · weekend challenge

Mornings teach at length. Evenings compress or contest: a diagram to save, a checklist to run, a debate to lose. Sunday names every topic the week covers; Saturday closes the loop. Friday argues in both slots — by Friday the material has earned the right to be attacked.

Underneath runs a longer loop. Ten pillars, bottom of the stack to top, 2 weeks per pillar: 20 weeks per lap. Then the lap restarts at a harder angle. Five laps fill the 100 weeks:

1. Foundations (weeks 1–20): first principles, for when the mechanics are fuzzy.
2. Builder's Pass (21–40): reading about it is not the same as building it, so we build it.
3. Failure Modes (41–60): how each layer breaks in production.
4. Scale & Hardening (61–80): what survives real traffic, real data, real money.
5. Frontier & Mastery (81–100): being the person others ask.

So consistent hashing, explained in week one, is scheduled to return as something you build, then something that breaks, then something that must hold at scale, then something you get interviewed on. Concepts repeat by design, but no two posts reuse the same angle-and-format pairing (asserted at generation, all 1,400 titles).

The spiral is a bet about learning, and this series does not dress bets as findings: I believe spaced returns at escalating angles beat one exhaustive pass; I hold it with high confidence; I have never measured it. The Saturday quizzes are the instrument. If second-pass answers look no different from first exposures, the calendar gets re-cut — as a visible diff against committed history, never a quiet rewrite. Look up any date between 2026-08-23 and 2028-07-22. Failure Modes reaches system design the week of 2027-05-30; hold me to that.

Three ways to follow. Live: 09:00 and 17:00 daily. Batched: Sunday's kickoff names the week, Saturday's recap compresses it; read those two, and go deep when the pillar is the one you are hired to know. Ahead: all 1,406 briefs are committed; nothing stops you from reading 2028 today.

Tonight, 17:00: the weekend challenge — baseline yourself before week one. Sunday 23 August, 09:00: week one opens with the CAP theorem, from first principles.

Plan and audit trail: github.com/QuantumindSSI/systemdesign
```
