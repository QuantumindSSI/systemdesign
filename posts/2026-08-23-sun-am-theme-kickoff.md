# Week 1 · Sun 2026-08-23 · 09:00 · Theme kickoff: System Design Fundamentals (v1, constitution-compliant)

> Calendar row: W1 Sun AM. Format: theme kickoff. Pillar: System Design Fundamentals.
> Pass: Foundations. Source: curriculum.md Layer 0 + prep pack week-01.
> Standards: persona-constitution (Laws I–IV, Structurally Decisive, Adversarial
> Review) + QSSI research persona (Laws I–VI) + Amendment 1.
>
> Adversarial review record (numbers audit):
> - "twenty-week foundations pass": the committed calendar, named inline ✓
> - Repo stats cited are from the prep pack verification log (GitHub API 2026-08-22);
>   re-verify day-of per standing rule ✓
> - "Thursday" video claim references the committed demo script, re-run before posting ✓
> - No external performance claims made; all numbers traceable to verified repos or the
>   committed prep code in this repo ✓
> - Week-0 poll still open: the 2-week duration was declared in the W0 poll publish
>   cut; verifying it is still live is a day-of posting check ✓

---

The layer most engineers skip is the one that kills them. When a distributed system fails under load, the postmortem rarely names a clever algorithm someone got wrong. It names a caching decision nobody made, a consistency assumption nobody wrote down, and a partition nobody planned for because the design review focused on the models instead. System design fundamentals are not the most interesting layer in the stack. They are the load-bearing one. Everything above them, the harnesses, the agent loops, the serving graphs, inherits their failure modes without knowing it. A harness with a four-second timeout is not a harness problem. It is a partitioning problem wearing a tooling hat.

This week opens the twenty-week foundations pass of this series. The concept is classical system design: the constraints that govern any system whose state lives in more than one place. Caching. Consistency. Partitioning. Load distribution. The language is old. CAP was formalised in 2000, the Dynamo paper shipped in 2007, consistent hashing is a 1997 idea by Karger et al. That longevity is the point. These are not frameworks that go stale when a new serving engine ships. They are the physics. The physics does not care which LLM you are orchestrating.

What to expect this week. Monday: a deep-dive on the CAP theorem and PACELC, the single diagram that organises every consistency tradeoff you will ever make, and the one most engineers can name but cannot apply. Tuesday: inside a real repository, open-source implementations of consistent hashing and load balancing you can read in under eighty lines, paired with a runnable snippet that makes quorum tradeoffs concrete. Wednesday: Dynamo at Amazon, the case study that moved consistent hashing from a research idea to production infrastructure at a scale that matters, with the exact numbers the paper reports and the ones it explicitly withheld. Thursday: a hands-on video, five load balancing algorithms, measured on your laptop, with the trap that separates textbook correctness from production survival. Friday the argument flips: what if most of what you learned this week is right on paper and wrong in deployment? Saturday closes the loop with a quiz that doubles as the instrument. If the concepts stuck, the answers will show it.

The week does not assume you have read the Dynamo paper or written a distributed hash ring. It assumes you have built or maintained something that talked to more than one server, and it starts from there. If you have not, Thursday's exercise gives you the running code; Monday and Tuesday give you the mental model to read it.

One piece of housekeeping. The week-zero poll on where this series should go deepest is still open. It runs for two weeks from Thursday's launch. If you have not voted, the post is pinned. Your vote weights the second pass of the calendar. A poll with no votes is not an audience signal. It is just a prior nobody challenged.

---

*Monday, 09:00: the CAP theorem and PACELC, the diagram that organises every consistency tradeoff you will ever make, and the one most engineers misapply.*