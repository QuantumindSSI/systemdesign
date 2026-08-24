# Content Calendar - System Overview

**1406 posts** - a 6-post launch block (week 0: Thu 2026-08-20 to Sat), then 2/day (09:00 + 17:00), Sun-Sat, for 100 weeks: 2026-08-23 to 2028-07-22.

Full calendar: `content_calendar.csv` (one complete brief per post: title, hook, 3-bullet outline, CTA, source). Regenerate or re-date by editing `generate_calendar.py` (set `START_DATE`) and rerunning - output is deterministic.

## How the system works

- **10 pillars** drawn from `curriculum.md` (Layers 0-6) and `files.md` (28 verified repos).
- **5 editorial passes x 20 weeks**: Foundations -> Builder's Pass -> Failure Modes -> Scale & Hardening -> Frontier & Mastery. Every pillar gets 2 weeks per pass.
- **Concepts recur across passes by design** (pillar-cluster model) but never with the same angle + format; all 1,400 titles are asserted unique at generation time.
- **Fixed daily cadence** so production becomes routine:

| Day | 09:00 | 17:00 |
|---|---|---|
| Sun | Theme kickoff | Poll |
| Mon | Concept deep-dive | Annotated diagram |
| Tue | Repo walkthrough | Snippet / config tip |
| Wed | Case study | Lessons listicle |
| Thu | Hands-on tutorial | Mistakes checklist |
| Fri | Contrarian take | Debate prompt |
| Sat | Recap + quiz | Weekend challenge |

## Publishing format (effective 2026-08-24, week 1 onward)

Platform is Substack, not LinkedIn. Each calendar day produces three artifacts,
not one post per slot:

- **09:00 - the essay.** A full long-form Substack essay, 2,500-3,500 words.
  The day's `format` column (concept deep-dive, repo walkthrough, case study,
  etc.) is not a separate short post; it is the essay's spine, the structural
  backbone the essay is organized around. A "concept deep-dive" essay leads
  with a plain-language definition, walks the mechanism with a concrete
  example, and closes on the load-bearing misconception. A "case study" essay
  leads with the scene, walks the decision and the numbers, and closes on the
  transferable rule. The outline column in the CSV names the spine's beats;
  the essay fills each beat out to full depth rather than one sentence.
- **17:00 - the follow-up.** A short 500-700 word post that buttresses the
  morning essay: same day, same underlying example, does not introduce a new
  topic. It is built around that day's PM `format` column exactly as before
  (annotated diagram, snippet, listicle, and so on), just short instead of a
  standalone LinkedIn post. It assumes the reader has read the 09:00 essay
  and reinforces one piece of it (a diagram, a runnable snippet, a checklist)
  rather than repeating the whole argument.
- **Teasers, one file, four platforms.** A short comment-length teaser for
  Twitter/X, LinkedIn, Reddit, and Quora, each in that platform's native
  voice and length convention, each linking back to the Substack essay. These
  replace the old full-repost "publish cut": the essay lives on Substack,
  the other platforms only ever get a hook and a link, never the full text.

File naming for each day: `posts/{date}-{day}-am-essay-{slug}.md` (the
essay), `posts/{date}-{day}-pm-followup-{slug}.md` (the buttressing
follow-up), `posts/{date}-{day}-teasers.md` (the four-platform bundle). Each
essay and follow-up file carries an editorial audit header (source
verification, numbers audit) above a `---` marker; only the content below
that marker is the reader-facing publish copy.

## Working the calendar

1. Batch-write one week (14 briefs) in a single sitting; the briefs are complete outlines.
2. The CSV imports directly into Notion, Google Sheets, Airtable, or Buffer/Hypefury.
3. Swap any concept by editing its pillar bank in the generator and rerunning.
4. Numerical grounding rule: every number in a published post must name its source inline, be explicitly flagged as unaudited at the point of use, or be cut (QSSI research persona, Amendment 1).

## 100-week index

| Week | Dates | Pillar | Pass |
|---|---|---|---|
| 0 | 2026-08-20 - 2026-08-22 | Series Launch | Launch |
| 1 | 2026-08-23 - 2026-08-29 | System Design Fundamentals | Foundations |
| 2 | 2026-08-30 - 2026-09-05 | System Design Fundamentals | Foundations |
| 3 | 2026-09-06 - 2026-09-12 | LLM Internals & Pretraining | Foundations |
| 4 | 2026-09-13 - 2026-09-19 | LLM Internals & Pretraining | Foundations |
| 5 | 2026-09-20 - 2026-09-26 | Post-training & Alignment | Foundations |
| 6 | 2026-09-27 - 2026-10-03 | Post-training & Alignment | Foundations |
| 7 | 2026-10-04 - 2026-10-10 | Inference & Edge Deployment | Foundations |
| 8 | 2026-10-11 - 2026-10-17 | Inference & Edge Deployment | Foundations |
| 9 | 2026-10-18 - 2026-10-24 | Harness Engineering | Foundations |
| 10 | 2026-10-25 - 2026-10-31 | Harness Engineering | Foundations |
| 11 | 2026-11-01 - 2026-11-07 | Loop & Graph Engineering | Foundations |
| 12 | 2026-11-08 - 2026-11-14 | Loop & Graph Engineering | Foundations |
| 13 | 2026-11-15 - 2026-11-21 | Evals, Observability & Governance | Foundations |
| 14 | 2026-11-22 - 2026-11-28 | Evals, Observability & Governance | Foundations |
| 15 | 2026-11-29 - 2026-12-05 | MLOps & Infrastructure | Foundations |
| 16 | 2026-12-06 - 2026-12-12 | MLOps & Infrastructure | Foundations |
| 17 | 2026-12-13 - 2026-12-19 | Production Case Studies | Foundations |
| 18 | 2026-12-20 - 2026-12-26 | Production Case Studies | Foundations |
| 19 | 2026-12-27 - 2027-01-02 | Career, FDE & Interviews | Foundations |
| 20 | 2027-01-03 - 2027-01-09 | Career, FDE & Interviews | Foundations |
| 21 | 2027-01-10 - 2027-01-16 | System Design Fundamentals | Builder's Pass |
| 22 | 2027-01-17 - 2027-01-23 | System Design Fundamentals | Builder's Pass |
| 23 | 2027-01-24 - 2027-01-30 | LLM Internals & Pretraining | Builder's Pass |
| 24 | 2027-01-31 - 2027-02-06 | LLM Internals & Pretraining | Builder's Pass |
| 25 | 2027-02-07 - 2027-02-13 | Post-training & Alignment | Builder's Pass |
| 26 | 2027-02-14 - 2027-02-20 | Post-training & Alignment | Builder's Pass |
| 27 | 2027-02-21 - 2027-02-27 | Inference & Edge Deployment | Builder's Pass |
| 28 | 2027-02-28 - 2027-03-06 | Inference & Edge Deployment | Builder's Pass |
| 29 | 2027-03-07 - 2027-03-13 | Harness Engineering | Builder's Pass |
| 30 | 2027-03-14 - 2027-03-20 | Harness Engineering | Builder's Pass |
| 31 | 2027-03-21 - 2027-03-27 | Loop & Graph Engineering | Builder's Pass |
| 32 | 2027-03-28 - 2027-04-03 | Loop & Graph Engineering | Builder's Pass |
| 33 | 2027-04-04 - 2027-04-10 | Evals, Observability & Governance | Builder's Pass |
| 34 | 2027-04-11 - 2027-04-17 | Evals, Observability & Governance | Builder's Pass |
| 35 | 2027-04-18 - 2027-04-24 | MLOps & Infrastructure | Builder's Pass |
| 36 | 2027-04-25 - 2027-05-01 | MLOps & Infrastructure | Builder's Pass |
| 37 | 2027-05-02 - 2027-05-08 | Production Case Studies | Builder's Pass |
| 38 | 2027-05-09 - 2027-05-15 | Production Case Studies | Builder's Pass |
| 39 | 2027-05-16 - 2027-05-22 | Career, FDE & Interviews | Builder's Pass |
| 40 | 2027-05-23 - 2027-05-29 | Career, FDE & Interviews | Builder's Pass |
| 41 | 2027-05-30 - 2027-06-05 | System Design Fundamentals | Failure Modes |
| 42 | 2027-06-06 - 2027-06-12 | System Design Fundamentals | Failure Modes |
| 43 | 2027-06-13 - 2027-06-19 | LLM Internals & Pretraining | Failure Modes |
| 44 | 2027-06-20 - 2027-06-26 | LLM Internals & Pretraining | Failure Modes |
| 45 | 2027-06-27 - 2027-07-03 | Post-training & Alignment | Failure Modes |
| 46 | 2027-07-04 - 2027-07-10 | Post-training & Alignment | Failure Modes |
| 47 | 2027-07-11 - 2027-07-17 | Inference & Edge Deployment | Failure Modes |
| 48 | 2027-07-18 - 2027-07-24 | Inference & Edge Deployment | Failure Modes |
| 49 | 2027-07-25 - 2027-07-31 | Harness Engineering | Failure Modes |
| 50 | 2027-08-01 - 2027-08-07 | Harness Engineering | Failure Modes |
| 51 | 2027-08-08 - 2027-08-14 | Loop & Graph Engineering | Failure Modes |
| 52 | 2027-08-15 - 2027-08-21 | Loop & Graph Engineering | Failure Modes |
| 53 | 2027-08-22 - 2027-08-28 | Evals, Observability & Governance | Failure Modes |
| 54 | 2027-08-29 - 2027-09-04 | Evals, Observability & Governance | Failure Modes |
| 55 | 2027-09-05 - 2027-09-11 | MLOps & Infrastructure | Failure Modes |
| 56 | 2027-09-12 - 2027-09-18 | MLOps & Infrastructure | Failure Modes |
| 57 | 2027-09-19 - 2027-09-25 | Production Case Studies | Failure Modes |
| 58 | 2027-09-26 - 2027-10-02 | Production Case Studies | Failure Modes |
| 59 | 2027-10-03 - 2027-10-09 | Career, FDE & Interviews | Failure Modes |
| 60 | 2027-10-10 - 2027-10-16 | Career, FDE & Interviews | Failure Modes |
| 61 | 2027-10-17 - 2027-10-23 | System Design Fundamentals | Scale & Hardening |
| 62 | 2027-10-24 - 2027-10-30 | System Design Fundamentals | Scale & Hardening |
| 63 | 2027-10-31 - 2027-11-06 | LLM Internals & Pretraining | Scale & Hardening |
| 64 | 2027-11-07 - 2027-11-13 | LLM Internals & Pretraining | Scale & Hardening |
| 65 | 2027-11-14 - 2027-11-20 | Post-training & Alignment | Scale & Hardening |
| 66 | 2027-11-21 - 2027-11-27 | Post-training & Alignment | Scale & Hardening |
| 67 | 2027-11-28 - 2027-12-04 | Inference & Edge Deployment | Scale & Hardening |
| 68 | 2027-12-05 - 2027-12-11 | Inference & Edge Deployment | Scale & Hardening |
| 69 | 2027-12-12 - 2027-12-18 | Harness Engineering | Scale & Hardening |
| 70 | 2027-12-19 - 2027-12-25 | Harness Engineering | Scale & Hardening |
| 71 | 2027-12-26 - 2028-01-01 | Loop & Graph Engineering | Scale & Hardening |
| 72 | 2028-01-02 - 2028-01-08 | Loop & Graph Engineering | Scale & Hardening |
| 73 | 2028-01-09 - 2028-01-15 | Evals, Observability & Governance | Scale & Hardening |
| 74 | 2028-01-16 - 2028-01-22 | Evals, Observability & Governance | Scale & Hardening |
| 75 | 2028-01-23 - 2028-01-29 | MLOps & Infrastructure | Scale & Hardening |
| 76 | 2028-01-30 - 2028-02-05 | MLOps & Infrastructure | Scale & Hardening |
| 77 | 2028-02-06 - 2028-02-12 | Production Case Studies | Scale & Hardening |
| 78 | 2028-02-13 - 2028-02-19 | Production Case Studies | Scale & Hardening |
| 79 | 2028-02-20 - 2028-02-26 | Career, FDE & Interviews | Scale & Hardening |
| 80 | 2028-02-27 - 2028-03-04 | Career, FDE & Interviews | Scale & Hardening |
| 81 | 2028-03-05 - 2028-03-11 | System Design Fundamentals | Frontier & Mastery |
| 82 | 2028-03-12 - 2028-03-18 | System Design Fundamentals | Frontier & Mastery |
| 83 | 2028-03-19 - 2028-03-25 | LLM Internals & Pretraining | Frontier & Mastery |
| 84 | 2028-03-26 - 2028-04-01 | LLM Internals & Pretraining | Frontier & Mastery |
| 85 | 2028-04-02 - 2028-04-08 | Post-training & Alignment | Frontier & Mastery |
| 86 | 2028-04-09 - 2028-04-15 | Post-training & Alignment | Frontier & Mastery |
| 87 | 2028-04-16 - 2028-04-22 | Inference & Edge Deployment | Frontier & Mastery |
| 88 | 2028-04-23 - 2028-04-29 | Inference & Edge Deployment | Frontier & Mastery |
| 89 | 2028-04-30 - 2028-05-06 | Harness Engineering | Frontier & Mastery |
| 90 | 2028-05-07 - 2028-05-13 | Harness Engineering | Frontier & Mastery |
| 91 | 2028-05-14 - 2028-05-20 | Loop & Graph Engineering | Frontier & Mastery |
| 92 | 2028-05-21 - 2028-05-27 | Loop & Graph Engineering | Frontier & Mastery |
| 93 | 2028-05-28 - 2028-06-03 | Evals, Observability & Governance | Frontier & Mastery |
| 94 | 2028-06-04 - 2028-06-10 | Evals, Observability & Governance | Frontier & Mastery |
| 95 | 2028-06-11 - 2028-06-17 | MLOps & Infrastructure | Frontier & Mastery |
| 96 | 2028-06-18 - 2028-06-24 | MLOps & Infrastructure | Frontier & Mastery |
| 97 | 2028-06-25 - 2028-07-01 | Production Case Studies | Frontier & Mastery |
| 98 | 2028-07-02 - 2028-07-08 | Production Case Studies | Frontier & Mastery |
| 99 | 2028-07-09 - 2028-07-15 | Career, FDE & Interviews | Frontier & Mastery |
| 100 | 2028-07-16 - 2028-07-22 | Career, FDE & Interviews | Frontier & Mastery |
