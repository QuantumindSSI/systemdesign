# Week 0 · Thu 2026-08-20 · 09:00 · Series announcement (v2, persona-grounded)

> Calendar row: week 0, AM. Format: series announcement. Source: curriculum.md.
> Voice/standards: QSSI research persona (Laws I–VI applied conversationally — calibrated
> uncertainty, pre-registration, sunset protocols, adversarial review). v1 in git history.
> Platform notes: post as-is on LinkedIn; for X, split at the horizontal rules into a thread.

---

The models keep getting better. The agents keep dying in prototype.

The number everyone quotes is 95% — ninety-five out of a hundred enterprise agent projects never survive contact with production. I've repeated that number myself, so let me hold it to the standard I'm about to hold everything else to: I can't fully audit it. What I *can* audit is the pattern behind it, because I've watched these projects die up close, and the autopsy is almost never the model. It's everything around the model. Nobody designed the tools. Nobody versioned the prompts. Nobody decided when a human gets to veto. Nobody wrote a single eval. The whole thing ran on hope and a demo dataset, right up until it didn't.

Here's what took me embarrassingly long to see: these skills stack in a specific order. You can't debug an agent loop if you can't read an inference bill. You can't read an inference bill if you don't know what a KV cache is doing to your memory. There's a dependency graph under this field, and most engineers walk it backwards — six months grinding transformer math (table stakes now), then winging the layer where projects actually die.

So I'm walking the whole graph, in order, in public. Starting Sunday: 100 weeks, 2 posts a day, every day.

And because "trust me" is exactly the disease this series is against, it runs under five rules:

1. **Everything is pre-registered.** All 1,400+ posts were planned and committed to version control before this one went out. If I quietly rewrite the plan to look smarter later, git will tattle.
2. **Nothing gets cited unverified.** Every repo backing this series — 29 of them this week — gets checked: alive, active, and actually saying what people claim it says. One had already been DMCA'd off GitHub. It was retired with a note, not silently swapped.
3. **Claims carry their uncertainty.** When I know, I'll say how. When I'm guessing, the post will say "I'm guessing." You just watched me do it to my own favorite statistic.
4. **Corrections are content.** When something I taught turns out wrong, the correction gets its own post — dead ideas get a burial, not a stealth edit.
5. **The plan updates on evidence.** Your comments and polls are data. Pass two of this series gets re-weighted on them, and I'll show the numbers when it does.

The ten pillars, bottom to top: system design fundamentals (boring, load-bearing) → LLM internals & pretraining → post-training & alignment → inference & edge → harness engineering → loop & graph engineering → evals, observability & governance (the skipped layer — see: 95%) → MLOps & infrastructure → production case studies → career & FDE.

The rhythm never changes: kickoff Sunday, deep-dive Monday, real code Tuesday, case study Wednesday, hands-on Thursday, a fight on Friday — steelman first, then attack — and a quiz Saturday. Morning teaches. Evening argues.

Week 1 opens Sunday with system design fundamentals, from first principles. Follow along, or don't — but if your agent dies in prototype next quarter, at least you'll know which layer it died in.

---

*Tomorrow, 09:00: the 7-layer map — why most engineers study the wrong layers.*
