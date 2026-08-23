# Week 1 · Sun 2026-08-23 · 17:00 · Poll: System Design Fundamentals (v1, constitution + research persona)

> Calendar row: W1 Sun PM. Format: poll. Pillar: System Design Fundamentals.
> Pass: Foundations. Source: curriculum.md Layer 0.
> Standards: persona-constitution (decisive, adversarially reviewed) + QSSI research
> persona (prior stated with credence, sample characteristics, update condition,
> boundary condition) + Amendment 1.
>
> Adversarial review record (numbers audit):
> - Every prior in this post carries its own credence and sample boundary inline ✓
> - "most engineers skip": experiential, scoped to hiring and projects I have been
>   part of, not a survey; the poll itself is the measurement instrument ✓
> - The committed Week 0 poll is still live (2-week duration); this poll covers a
>   different question in a different layer, no overlap ✓
> - No external stats cited; all priors stated with source (personal observation,
>   hiring, project postmortems) ✓

---

This morning the week opened on system design fundamentals. Before any concept lands, I want to know what you are least confident in. Not what you find most interesting, not what sounds impressive in an interview. Where the gap actually is. A curriculum built on what people want to hear about is content marketing. A curriculum weighted by where people admit they are weak is engineering.

I have a prior. In the systems I have inspected and the engineers I have hired and interviewed, the most common gap is not the CAP theorem. Most people have heard of it. It is what happens when you have to choose: when the textbook gives you a clean model and the deployment gives you two constraints that cannot both hold. The gap is in tradeoff reasoning under real constraints, not in recalling definitions. I hold that at roughly sixty percent, personal credence from projects and hiring, not a measurement. The sample is engineers building or maintaining distributed systems at the application layer, and it has not included you. The poll corrects for that.

One vote. Of these four system design fundamentals, which do you understand least well in practice?

**Option A: CAP, PACELC, and consistency models.** You can state the theorem. You are not sure you would make the right call at 03:00 when the network partition is real and the replication lag is climbing.

**Option B: Caching strategies and invalidation.** You know cache-aside, write-through, write-back by name. You cannot reliably predict which one breaks which way under which traffic shape.

**Option C: Load balancing and request routing.** Round robin, least connections, consistent hashing. You can describe them. You would not trust yourself to configure them for a service running real money.

**Option D: Partitioning, sharding, and data placement.** You understand the ring in principle. You have never had to rebalance one while the system was live.

Vote in the poll, or with a single letter in the comments. A write-in is the strongest form of disagreement you can hand me. If the concept you are weakest on is not listed, naming it is more useful than picking the least wrong option. The point of this poll is not to flatter my prior. It is to find out where to put the weight inside the week.

This is not the same question as the Week 0 poll. That poll asks where the hundred-week series should go deepest across all ten pillars. This one asks where your gap is inside the pillar we are in right now. Both are open; both will shape content. The difference is that this one tightens a week's focus, not a year's.

---

*Monday, 09:00: the CAP theorem and PACELC, from first principles. What the theorem actually says, what it does not say, and the diagram that collapses both into something you can reason with at speed.*