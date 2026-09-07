# AI Engineering from Scratch

A hundred weeks of engineering writing, two posts a day, every day, published
here on the day they go out.

Every implementation the series discusses is written into this repository,
tested, and then read line by line in an article. Nothing is borrowed from
another repository and summarised. Everything runs on the Python standard
library, so you can clone this and execute any artifact with no install step.

```
python3 -m unittest discover -s tests -t .     # the library's test suite
python3 tools/publication_gate.py              # the rules this repo runs under
```

| Tree | What it holds |
|---|---|
| `posts/` | The articles, published on their day and not before |
| `lib/` | Reference implementations the articles walk through |
| `tests/` | The test suite behind `lib/` |
| `experiments/` | Runnable measurements quoted in specific articles |
| `data/` | Frozen corpora, so a quoted number stays reproducible |
| `tools/` | The gates that keep this repository honest |

Articles are listed below as they publish. Posts written ahead of their day
are deliberately absent: they are not committed until the morning they go out.

## Week 3

- **2026-09-06 AM** [Theme kickoff: LLM Internals and Pretraining, Foundations part 1](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-06-sun-am-theme-kickoff.md)
- **2026-09-06 PM** [Poll: Where are you with LLM internals?](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-06-sun-pm-poll.md)

## Week 2

- **2026-08-31 AM** [Long-form: A CDN Is a Shared Cache, Not a Map](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-31-mon-am-essay-cdn-architecture.md)
- **2026-08-31 PM** [Follow-up: CDN architecture in one diagram (foundations)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-31-mon-pm-followup-cdn-diagram.md)
- **2026-09-01 AM** [Long-form: Your DNS Load Balancer Is Steering a Resolver, Not a User](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-01-tue-am-essay-dns-resolution-paths.md)
- **2026-09-01 PM** [Follow-up: Reading the Resolution Path in Raw Bytes](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-01-tue-pm-followup-dns-tracer-walkthrough.md)
- **2026-09-02 AM** [Long-form: Facebook Chose to Delete, Not Update, and Built a Pipeline to Prove It](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-02-wed-am-essay-cache-aside-vs-write-through.md)
- **2026-09-02 PM** [Follow-up: The Reorder, Executable, Plus the Measurement That Proved Me Wrong](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-02-wed-pm-followup-write-strategies-code.md)
- **2026-09-03 AM** [Hands-on: Build Three Eviction Policies and Watch the Winner Lose](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-03-thu-am-tutorial-cache-eviction.md)
- **2026-09-03 PM** [Follow-up: Five Checks Before You Trust Your Eviction Policy](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-03-thu-pm-followup-eviction-mistakes-checklist.md)
- **2026-09-04 AM** [Long-form: The Lock Works. It Just Solves One Kind of Stampede.](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-04-fri-am-essay-cache-stampede.md)
- **2026-09-04 PM** [Follow-up: Necessary, or a Component You Will Regret at 3am?](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-04-fri-pm-followup-stampede-debate.md)
- **2026-09-05 AM** [Recap and Quiz: Five Things That Decide Whether a Cache Helps You](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-05-sat-am-recap-quiz.md)
- **2026-09-05 PM** [Weekend Challenge: Make a Query Plan Change Its Mind](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-09-05-sat-pm-weekend-challenge-indexing.md)

## Week 1

- **2026-08-23 AM** [Theme kickoff: System Design Fundamentals (v1, constitution-compliant)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-23-sun-am-theme-kickoff.md)
- **2026-08-23 PM** [Poll: System Design Fundamentals (v1, constitution + research persona)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-23-sun-pm-poll.md)
- **2026-08-24 AM** [Long-form: Understanding the CAP Theorem Through the Moment It Actually Bites](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-24-mon-am-essay-cap-theorem.md)
- **2026-08-24 PM** [Follow-up: the CAP theorem in one diagram (foundations)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-24-mon-pm-followup-cap-theorem-diagram.md)
- **2026-08-25 AM** [Long-form: The Mental Model for Consistent Hashing, Before the 79 Lines](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-25-tue-am-essay-consistent-hashing.md)
- **2026-08-25 PM** [Evening deep-dive: Tracing the 53 Lines That Implement Consistent Hashing](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-25-tue-pm-followup-code-walkthrough.md)
- **2026-08-26 AM** [Long-form: Case Study, Consistent Hashing in Production](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-26-wed-am-essay-dynamo-case-study.md)
- **2026-08-26 PM** [Evening deep-dive: Dynamo's Preference Lists and Quorums](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-26-wed-pm-followup-dynamo-quorum-code.md)
- **2026-08-27 AM** [Long-form: Hands-On, Load Balancing Algorithms in Under an Hour](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-27-thu-am-tutorial-load-balancing.md)
- **2026-08-27 PM** [Short follow-up: The Load Balancing Mistakes Checklist](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-27-thu-pm-followup-load-balancing-mistakes.md)
- **2026-08-28 AM** [Long-form: L4 vs L7 Is a Trust-Boundary Decision, Not a Speed Test](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-28-fri-am-essay-l4-l7-load-balancing.md)
- **2026-08-28 PM** [Short follow-up: Who Should Be Allowed to Read the Request?](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-28-fri-pm-followup-l4-l7-debate.md)

## Week 0

- **2026-08-20 AM** [Series announcement (v4, constitution-compliant)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-20-thu-am-series-announcement.md)
- **2026-08-20 PM** [Poll (v4, constitution + research persona)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-20-thu-pm-poll.md)
- **2026-08-22 AM** [How-it-works guide (v2, constitution + research persona)](https://github.com/QuantumindSSI/systemdesign/blob/main/posts/2026-08-22-sat-am-how-it-works.md)


---

Generated by `tools/build_index.py`. Regenerate after staging each day's posts.
