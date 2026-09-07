# Prep · Week 1 · Thu 2026-08-27 · 09:00 · Hands-on tutorial (YouTube video)

> Calendar row: W1 Thu AM. Committed title: "Hands-on: load balancing
> algorithms in under an hour (foundations)". Delivery: YouTube video + LinkedIn
> post pointing at it. Committed outline: define the end state | 4-6 numbered
> steps | verification step. CSV source: github.com/binhnguyennus/awesome-scalability
> (verified 2026-08-22: 73,458 stars, push 2026-01-04).

## Demo artifact (committed, runnable, verified)

`experiments/week-01/lb_algorithms_demo.py` - 277 lines, stdlib only, seed 42,
runs in <5s. Five algorithms (RR, smooth WRR, least-connections, IP-hash,
consistent-hash ring with vnodes), four measured scenarios, all assertions
passing. Reference implementations of the same algorithms exist in
`ashishps1/awesome-system-design-resources` `implementations/python/
load_balancing_algorithms/` - shown on screen Tuesday, measured today.

Measured results to quote (seed 42, reproduce before recording):

| Scenario | Result |
|---|---|
| RR, 5 equal backends, 100k req | exact 20,000 each |
| Ring, 100 vnodes | max/min imbalance 1.12x |
| Ring, 1 vnode | max/min imbalance 6.88x |
| Smooth WRR 5:4:3:2:1 | within 1 request of exact shares |
| b2 degrades 10x: mean queue depth | RR: 9.99 on b2 · least-conn: 1.66 |
| Remove 1 of 5 backends | mod-N remaps 79.9% · ring remaps 19.1% |

## Video script outline (target 22-28 min)

1. **Cold open (0:00-1:30).** "Five load balancing algorithms. One of them
   quietly forwards 10x traffic to your slowest server, and one of them
   reshuffles 80% of your users when a node dies. By the end you will have
   measured both on your laptop." Show the final scenario-4 table.
2. **Setup (1:30-3:00).** One file, no dependencies, `python3
   lb_algorithms_demo.py`. Clone or copy; Python 3.8+.
3. **Round robin + the exactness trap (3:00-7:00).** Code tour of `RoundRobin`;
   run scenario 1a. Exact spread - and why exact spread is the wrong goal when
   requests are not identical (foreshadow scenario 3).
4. **Weighted RR done right (7:00-11:00).** `SmoothWeightedRoundRobin` - the
   nginx-style score loop; contrast against naive burst WRR; run scenario 2.
5. **Least connections and the price of state (11:00-15:00).** `pick`/`release`
   pair; run scenario 3: queue depth 9.99 vs 1.66 on the degraded backend. The
   operational cost: the balancer must observe request completion.
6. **Hashing: sticky vs survivable (15:00-21:00).** `IPHash` vs
   `ConsistentHash`; vnodes = 1 vs 100 (6.88x vs 1.12x); kill b2 live:
   79.9% vs 19.1% remap. Callback to Tuesday's repo file and Wednesday's
   Dynamo numbers.
7. **Wrap + homework (21:00-end).** The decision table: stateless+equal -> RR;
   known capacity skew -> WRR; variable request cost -> least-conn; session
   affinity or cache locality -> ring. Homework: add `least_response_time.py`
   from the ashishps1 repo to the harness and measure it against least-conn.

## Recording checklist

- [ ] Re-run the demo same-day; confirm "All assertions passed" before hitting record
- [ ] Terminal: 120x32, font >= 18pt, dark theme, `PS1` shortened, no personal paths visible
- [ ] Screen capture 1080p minimum; mic check; close notification sources
- [ ] Two takes per scenario run max; cuts at scenario boundaries
- [ ] End card: repo URL + "tomorrow 09:00: contrarian take" teaser

## Publish block

- Title options: "I measured 5 load balancing algorithms (one is a trap)" /
  "Load balancing algorithms: measured, not explained"
- Description: link to `github.com/QuantumindSSI/systemdesign` prep code, the
  ashishps1 implementations folder, and the Dynamo paper; timestamps from the
  script sections; no hashtag stacks.
- LinkedIn AM post: 4-6 numbered steps (mirror script sections 2-6), the
  scenario-4 table as the hook image or text block, link to the video.
  End state per the committed brief: "all four scenarios run on your machine
  and every assertion passes."

## PM slot (17:00 mistakes checklist) - five yes/no checks

1. Does your health check measure the work, not the port? (ping-alive !=
   serving; scenario 3 is what ping-alive looks like)
2. Is connection state released on every path - timeouts and errors included?
   (leaked `release()` = least-conn drifts into a static list)
3. Do weights track measured capacity, or the hardware invoice?
4. Can you say what fraction of sessions remap when you scale in? (mod-N: ~
   (N-1)/N; ring: ~1/N - measured 79.9% vs 19.1%)
5. Do sticky sessions survive a node loss by design, or by luck?
Symptom line for each drawn from the scenario outputs; screenshot-able card.

## Numbers audit

All performance numbers above are measured outputs of the seeded demo in this
repo (re-run day-of). Repo stars/dates: GitHub API 2026-08-22, re-check day-of.
No external performance claims used.
