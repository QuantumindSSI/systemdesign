# Week 4 · Sun 2026-09-13 · 17:00 · Poll: Where are you with the parts that make attention affordable?

> Calendar row: W4 Sun PM, 17:00 (CSV row `51:4`). Format: poll.
> Pillar: LLM Internals & Pretraining. Pass: Foundations, part 2.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + QSSI research persona (prior stated with credence, sample
> characteristics, update condition, boundary condition) + AGENTS.md canonical
> source rule + AGENTS.md human-first voice + prose style rules 1 through 7.
>
> **Canonical source rule.** The CSV `source` column for this row names an
> external repository. Per `AGENTS.md` that string is an internal routing hint
> only and appears nowhere below.
>
> Committed calendar beats, all four options present: A learning the
> vocabulary | B built it once in a side project | C run it in production |
> D debugged it during an incident.
> Committed CTA: "Follow along - this series runs all week."
>
> The committed option set is generic to every week's poll. It is used
> verbatim here because it is committed, and the body reframes each option
> against this week's specific subject so a vote means something concrete
> rather than a general self-assessment.
>
> Numbers used below, all measured in this repository today by
> `experiments/week-04/gqa_cache.py` and `experiments/week-04/window_reach.py`
> (both exit 0, "All assertions passed", stdout md5
> `8e07dc410034d4711452ecfe5f91b1ae` and `b6d110a1653176c824d51c896966b909`):
> - 80 layers, 64 query heads, head width 128, half precision, 131,072 tokens:
>   320.00 GiB at 64 key-value heads, 40.00 GiB at 8, 5.00 GiB at 1
> - at d_model 64 with 8 query heads: key subspace rank 64, 32, 16, 8 for
>   64/32/16/8-wide key stacks, leaving 0, 32, 48 and 56 blind directions
> - routing change under a blind-direction perturbation: 2.78e-16 at worst,
>   against an output change of 1.5853
> - window of 8 over 6 layers, length 64: influence 1.198e-05 at position 42
>   and exactly 0.000e+00 at position 43
>
> Adversarial review record (2026-09-13):
> - The four options are vantage points and the post says so, because
>   presenting D as the expert answer would bias the instrument ✓
> - The prior carries its credence, its sample, and its boundary inline, and
>   is labeled personal observation rather than a survey ✓
> - The update condition is fixed before any vote exists, so the result cannot
>   be retrofitted ✓
> - Every quoted figure names the script that produced it, and the untrained
>   toy's status is stated at the point of use ✓
> - The generic committed option set is flagged above as generic, and the
>   reframing is disclosed rather than passed off as the committed wording ✓
> - No external code repository is named, linked, or implied ✓
> - Reader-facing body: 1,212 words, measured 2026-09-13 by whitespace split
>   below the `---` marker. Above the 500 to 700-word evening band, for the
>   same structural reason recorded on 2026-09-04 and 2026-09-06: a poll has
>   to carry a stated prior, four described options, and an update condition ✓
>
> **Reader-facing repository pointer (convention adopted 2026-09-14).** Every
> 17:00 post carries a short block naming the public repository directly, so a
> reader who arrives at the evening post can reach the articles, the code and
> the issue tracker in one hop. The URL is written as `Technologues` rather
> than as a `systemdesign` URL, because `tools/publish_public.py` rewrites only
> `.../systemdesign/blob/main/` file links; a bare source-repository root URL
> would survive unrewritten and its own verifier would flag it as a foreign
> repository. The block is an addition to the committed beats, not a
> substitution for any of them.
> - Zero em dashes. No sentence opens with a conjunction. No collapsed
>   contrastive framing. Verified by `tools/prose_gate.py` ✓

---

**Topic:** A pulse check on the four efficiency mechanisms this week is about

**Subtitle:** Four honest positions, none better than the others, plus a prior of mine that I expect this poll to correct in a specific direction.

Good evening. One question before the deep dives start, and as usual I would rather have the unflattering answer than the impressive one.

This morning I opened week 4 on the two parts of a transformer block that week 3 walked past, and then on four schemes for making attention cheaper: grouped-query attention, multi-head latent attention, sliding windows, and learned sparse selection.

Here is the concrete piece, so the question below is about something rather than about a vocabulary. Take a model of 80 layers with 64 query heads of width 128, serving one sequence of 131,072 tokens in half precision. Its key-value cache is **320 GiB**. Group the heads down to 8 and the same cache is **40 GiB**. Take it to one and it is **5 GiB**. That arithmetic is the reason every served model you use has been grouped, and it is not controversial.

The part I find more interesting is what came out when I measured what grouping costs. Stack up a layer's key projections and take the rank, and you get the number of independent directions of the residual stream that the routing decision can actually read. With one key-value head per query head, our toy layer reads all 64 dimensions of its stream. With one shared key-value head, it reads 8, which leaves **56 directions the routing is blind to**. Move a position along one of those and no other position's attention weight toward it changes by more than 2.78e-16, which is floating-point noise, while the layer's output moves by 1.59.

That is on an untrained toy and I will keep saying so. What it establishes is a property of the architecture rather than of any trained model: those directions are unreadable by construction, and no amount of training gives them back.

Which brings me to the question: how visible is any of this from where you sit?

I want to state my prior before you vote, because an unstated prior stops being a hypothesis and quietly becomes a bias. **I expect the mode to be A this week, and I hold that at roughly sixty percent**, which is higher than my usual and is itself the interesting part. Last Sunday I put B at fifty-five percent for the mechanics of a transformer. This week's four topics are further from the tutorial path: they are optimisations made by people shipping models rather than by people using them, so my guess is that most readers have heard the names and never had to reason about the mechanics. That credence comes from the engineers I have worked with, hired and interviewed, which is a small sample skewed toward people building applications on top of models. It has never included you, which is why the poll exists.

One vote. Which of these describes your relationship with the mechanisms in this week's list?

**Option A: learning the vocabulary.** You have seen "GQA" in a model card and "sliding window" in a config file. You could follow a conversation about them and you would not want to be asked to draw the data flow or to say what the cache costs.

**Option B: built it once in a side project.** You have implemented or closely read one of these. Probably grouped-query attention, probably on a weekend, probably by modifying an existing attention layer. It worked, and some of it you copied because it worked.

**Option C: run it in production.** You serve a model where one of these choices is load-bearing. You have opinions about key-value cache size because it appears on an invoice or on a capacity plan, and about window length because it has constrained something you own.

**Option D: debugged it during an incident.** At some point one of these failed in a way that only made sense from the inside. A long document silently losing its middle, a cache that would not fit at the concurrency you promised, a quality regression after a config change nobody thought was a model change. You did not choose this knowledge; it arrived at an unpleasant hour.

These are vantage points rather than a ladder, and that matters for how I read the result. D is not the expert option. Somebody who spent a night on a window-length incident may know one mechanism in painful detail and nothing about the other three. Somebody in A who has read carefully may hold a cleaner picture than somebody in C who inherited a config file and has never changed it. Vote for where you are.

Here is what I will do with the result, fixed now, before any votes exist. If A and B dominate, Wednesday through Saturday keep every mechanism anchored to a worked numeric example and I spend the extra space on the arithmetic. If C and D dominate, the six topics stay fixed and the weight shifts toward the failure modes: what each mechanism looks like when it is the cause of an incident, what shows up in a graph, and what does not show up anywhere. Either way the topics do not move, because the calendar for this pass is committed and I am not going to pretend otherwise.

The boundary, stated honestly: this measures this audience on this Sunday. A poll attached to a post about attention internals selects for people who clicked on a post about attention internals. If the result comes back heavily C and D, the right conclusion is that this audience skews toward people serving models, rather than that most engineers have debugged a key-value cache.

If none of the four fits, write yours in. The most informative failure of any poll is the option it forgot to offer. If your honest answer is "I have accepted every one of these defaults without ever asking what it cost", that is a real position, it is the one this week is written for, and it is more common than the confident phrasing on this platform suggests.

## The code, and where to take it apart

Everything in this post lives in one repository, the articles and the implementations together:

**https://github.com/QuantumindSSI/Technologues**

```bash
git clone https://github.com/QuantumindSSI/Technologues.git
cd Technologues
python3 experiments/week-04/gqa_cache.py
python3 -m unittest discover -s tests -t .
```

Python 3.8 or newer, standard library only, so there is no install step and no requirements file. The README there indexes every article published so far, and each one names the file its numbers came from. The suite runs 460 tests.

The repository is generated, so a pull request against an article will not stick. Raise an issue instead, and if a number in this post does not reproduce on your machine, that is exactly the kind of issue I want.

Follow along. This series runs all week.

---

*Tomorrow, 09:00: residual streams. Why a transformer stack is a sum rather than a pipeline, why the input plus every recorded write reconstructs the output with an error of exactly zero, and why removing an early block's contribution is three times the effect of deleting that term from the finished total.*
