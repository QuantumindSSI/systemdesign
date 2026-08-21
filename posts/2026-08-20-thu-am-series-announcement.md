# Week 0 · Thu 2026-08-20 · 09:00 · Series announcement (v4, constitution-compliant)

> Calendar row: week 0, AM. Format: series announcement. Source: curriculum.md.
> Standards: persona-constitution (Laws I–IV, Structurally Decisive, Adversarial
> Review) + QSSI research persona (Laws I–VI) + Amendment 1. v1–v3 in git history.
>
> Adversarial review record (numbers audit):
> - "ninety-five percent" — flagged unaudited folklore at point of use ✓
> - "two posts every day for one hundred weeks" — the committed plan, named inline ✓
> - "1,406 planned posts" — source: this repository's calendar, named inline ✓
> - "twenty-nine repositories" — source: GitHub API verification 2026-08-20, named inline ✓
> - "ten pillars" — source: the committed plan, named inline ✓
> - v3's "half of its context window", "two years", "six months" — removed: no source existed.
> Claims audit: all experiential claims scoped to personal observation; no borrowed
> authority. Decisiveness audit: subordinate-clause chains broken; ornament removed.
> Research-persona audit (Laws I, II): core claims carry sample characteristics and
> boundary conditions inline; the central thesis names the condition under which it
> does not apply; pre-registration and sunset protocol named in the commitments.

---

The models keep getting better, and the agents built on them keep dying in prototype. The failures are quiet, because failed prototypes do not get postmortems. They get renamed, deprioritised, and forgotten.

There is a number that gets passed around for this: ninety-five percent of enterprise agent projects never reach production. I did not collect that number. I cannot trace its sample or its method, and I will not launder it into a fact. Treat it as folklore with a suspicious amount of agreement behind it. What I can defend is what I have seen in the projects I have personally been close to, and it is consistent: the model is almost never the cause of death. My sample is small and specific — enterprise deployments I could inspect myself — and the claim carries that boundary. I assert it for systems of that shape. I make no claim about research prototypes or consumer products I have never audited. The cause of death is everything around the model. Nobody designed the tools, so the agent burns its context guessing at them. Nobody versioned the prompts, so nobody can say which change broke the behaviour. Nobody decided when a human gets to veto an irreversible action, so either everything requires approval and the reviewer stops reading, or nothing does and the first bad day becomes an incident. Nobody wrote an evaluation, so nobody can tell a regression from bad luck. The project runs on hope and a demonstration dataset until the hope runs out.

The skills that prevent this death are not a menu. They are a dependency graph, and the graph has an order. You cannot debug an agent loop that refuses to terminate if you cannot read the inference bill, because a runaway loop is a cost problem before it is a logic problem. You cannot read the bill if you do not know what the key-value cache — the memory structure that makes a language model fast — is doing to your hardware. It is one stack, from silicon to strategy. Most engineers walk it backwards: deep on transformer mathematics, which is now table stakes, and improvising at the layers where projects actually die. This ordering claim has a boundary of its own, and I will state it rather than hide it: if your work never has to leave the notebook, you can ignore the order entirely. The moment your system must survive other people's traffic, other people's data, and other people's money, the order stops being a preference and becomes the difference between shipping and dying.

I am going to walk the entire graph, in order, in public. Starting this Sunday I will publish two posts every day for one hundred weeks. The morning post teaches. The evening post argues. The plan covers ten pillars, bottom to top: classical system design, the internals of large language models, post-training and alignment, inference and edge deployment, harness engineering, loop and graph engineering, evaluation and governance, the operational substrate, production case studies, and career leverage for forward-deployed engineering. The weekly rhythm is fixed: kickoff on Sunday, a deep explanation on Monday, real code on Tuesday, a case study on Wednesday, a hands-on exercise on Thursday, a deliberate argument on Friday — the opposing position stated fairly before it is attacked — and a recap with a quiz on Saturday.

A series about engineering discipline must survive its own standards, so this one runs under five commitments. First: everything is pre-registered. All one thousand four hundred and six planned posts sit in version control, committed before this first one went out. If I rewrite the plan to look wiser in hindsight, the history will contradict me. Second: nothing is cited unverified. The twenty-nine repositories backing this series were checked against the GitHub API on the twentieth of August — alive, maintained, and saying what people claim they say. One had been removed from GitHub under a copyright takedown. It was retired with a note, not silently replaced. Dead sources get burials, not cover-ups. Third: every number names its source in the sentence that uses it, or admits that it cannot. You watched that rule applied to my own favourite statistic two paragraphs ago. Fourth: corrections are content. When something I teach turns out wrong, the correction is published as its own post. Fifth: the plan updates on evidence — which brings me to this evening.

At five o'clock today I publish the first poll of this series, and I want you to see it coming. In it I will state, openly, what I believe you need most from these hundred weeks. I formed that belief from the projects and the hiring I have personally watched, and I have never measured it. The poll is the instrument that measures it. The second pass of this series will be re-weighted on the results, and the tally will be published beside the revised calendar so you can verify how far your vote moved it. A belief you refuse to measure is a belief you are protecting. This evening you get to break one of mine.

Week one opens Sunday morning: system design fundamentals, beginning with the CAP theorem, from first principles. Follow along or do not. But if your agent dies in prototype next quarter, you will know which layer it died in.

---

*This evening, 17:00: the poll. Tomorrow, 09:00: the seven-layer map — why most engineers study the wrong layers.*
