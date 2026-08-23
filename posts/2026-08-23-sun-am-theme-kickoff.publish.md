# Week 1 · Day 1 AM · Theme kickoff · Publish cut (LinkedIn)

> Source of truth: `posts/2026-08-23-sun-am-theme-kickoff.md` (v1). That body is
> 2,959 chars; well under LinkedIn's 3,000 limit. This cut is 2,958 chars, measured
> (`len()`, 2026-08-23, sha256 to be filled at publish). The repo md stays canonical.
>
> Deltas from the committed v1 copy, in full:
> 1. Audit header and H1 stripped: repo artifacts, not post copy.
> 2. `**bold**` markers stripped: LinkedIn renders raw text, not markdown.
> 3. All em dashes replaced with periods or commas (Constitution edict: zero
>    em dashes in any writing, including metadata, posts, READMEs, and site copy).
> 4. Monday–Thursday preview kept as a single paragraph: the canonical's line
>    breaks were for readability in source, not formatting; LinkedIn auto-wraps.
> 5. Repo link added as the closing line (house pattern). REQUIREMENT: the repo
>    must be public before this posts.
> 6. Week-0 poll callout moved to a single sentence from two: "housekeeping"
>    and "pinned" framing cut. The W0 poll being open is a fact; the reader
>    does not need a labelled section for it.
>
> Timing: calendar slot is Sun 23 Aug, 09:00. No slip to resolve: this is the
> first scheduled post of Week 1 and it runs on its calendar date. The week-0
> slip is closed.

---

## 1 · Posting checklist

1. Confirm github.com/QuantumindSSI/systemdesign is public. The post links it.
2. Text post, no poll widget, no hashtags, no @-mentions, no image.
3. Post at 09:00. The PM poll cut references "this morning": both must be
   live before 17:00 for the reference to hold.
4. Confirm the fold: the preview must end inside "…caching decision nobody
   made" territory, before the Monday–Thursday calendar block starts.
5. No edits after publish.

## 2 · Post body (paste exactly, 2,958 / 3,000 chars)

```text
The layer most engineers skip is the one that kills them. When a distributed system fails under load, the postmortem rarely names a clever algorithm someone got wrong. It names a caching decision nobody made, a consistency assumption nobody wrote down, and a partition nobody planned for because the design review focused on the models instead. System design fundamentals are not the most interesting layer in the stack. They are the load-bearing one. Everything above them, the harnesses, the agent loops, the serving graphs, inherits their failure modes without knowing it. A harness with a four-second timeout is not a harness problem. It is a partitioning problem wearing a tooling hat.

This week opens the twenty-week foundations pass of this series. The concept is classical system design: the constraints that govern any system whose state lives in more than one place. Caching. Consistency. Partitioning. Load distribution. The language is old. CAP was formalised in 2000, the Dynamo paper shipped in 2007, consistent hashing is a 1997 idea by Karger et al. That longevity is the point. These are not frameworks that go stale when a new serving engine ships. They are the physics. The physics does not care which LLM you are orchestrating.

The week: Monday, a deep-dive on the CAP theorem and PACELC, the single diagram that organises every consistency tradeoff you will ever make, and the one most engineers can name but cannot apply. Tuesday, inside a real repository, open-source implementations of consistent hashing and load balancing you can read in under eighty lines, paired with a runnable snippet that makes quorum tradeoffs concrete. Wednesday, Dynamo at Amazon, the case study that moved consistent hashing from a research idea to production infrastructure at a scale that matters, with the exact numbers the paper reports and the ones it explicitly withheld. Thursday, a hands-on video, five load balancing algorithms measured on your laptop, with the trap that separates textbook correctness from production survival. Friday the argument flips: what if most of what you learned this week is right on paper and wrong in deployment? Saturday closes the loop with a quiz that doubles as the instrument. If the concepts stuck, the answers will show it.

The week does not assume you have read the Dynamo paper or written a distributed hash ring. It assumes you have built or maintained something that talked to more than one server, and it starts from there. If you have not, Thursday's exercise gives you the running code. Monday and Tuesday give you the mental model to read it.

The week-zero poll on where this series should go deepest is still open, voting runs through the end of next week. Your vote weights the second pass of the calendar.

Monday, 09:00: the CAP theorem and PACELC, the diagram that organises every consistency tradeoff you will ever make, and the one most engineers misapply.

Plan and audit trail: github.com/QuantumindSSI/systemdesign
```