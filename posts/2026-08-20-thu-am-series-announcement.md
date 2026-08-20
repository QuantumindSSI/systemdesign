# Week 0 · Thu 2026-08-20 · 09:00 · Series announcement

> Calendar row: week 0, AM. Format: series announcement. Source: curriculum.md.
> Platform notes: post as-is on LinkedIn; for X, split at the horizontal rules into a thread.

---

The models keep getting better. The agents keep dying in prototype.

The number that gets passed around is 95% — ninety-five out of a hundred enterprise agent projects never survive contact with production. I believe it, because I've watched how they die. It's almost never the model. It's everything around the model: nobody designed the tools, nobody versioned the prompts, nobody decided when a human gets to veto, nobody wrote a single eval. The whole thing runs on hope and a demo dataset, right up until it doesn't.

Here's the thing that took me embarrassingly long to see: these skills stack in a specific order. You can't debug an agent loop if you can't read an inference bill. You can't read an inference bill if you don't know what a KV cache is doing to your memory. There's a dependency graph hiding under this field, and most engineers walk it in exactly the wrong order — six months grinding transformer math (which is table stakes now), then winging the layer where projects actually die.

So I'm going to walk the whole graph, in order, in public. Starting Sunday: 100 weeks, 2 posts a day. Every day.

The ten pillars, roughly bottom to top:

1. System design fundamentals — CAP, caching, sharding. Boring. Load-bearing.
2. LLM internals & pretraining — what's actually inside the thing you're renting
3. Post-training & alignment — SFT, RLHF, DPO, and why your fine-tune got dumber
4. Inference & edge — where latency, cost, and physics collect their debts
5. Harness engineering — an agent is a model plus everything you built around it
6. Loop & graph engineering — verifiers, stop rules, and multi-agent topology
7. Evals, observability & governance — the layer everyone skips. See: 95%.
8. MLOps & infrastructure — the substrate nobody tweets about
9. Production case studies — how real systems failed, and occasionally didn't
10. Career & FDE — turning all of the above into leverage

The rhythm never changes, so you always know what's coming: kickoff Sunday, deep-dive Monday, real code from a real repo Tuesday, case study Wednesday, something hands-on Thursday, a hot take Friday, a quiz Saturday. Morning post teaches. Evening post argues.

One promise about sourcing: every claim in this series traces back to a repo you can clone or a document you can read. I verified all 29 repos backing this series this week — existence, activity, whether the README actually says what people claim it says. The verification pass caught one repo that had been quietly DMCA'd off GitHub. That's the standard: checked, not vibes.

Week 1 opens Sunday with system design fundamentals, from first principles. Follow along, or don't — but if your agent dies in prototype next quarter, at least you'll know which layer it died in.

---

*Tomorrow, 09:00: the 7-layer map — why most engineers study the wrong layers.*
