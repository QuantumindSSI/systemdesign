# Week 1 · Thu 2026-08-27 · Video Production Plan (companion to the AM essay)

> Internal action plan, not a publish artifact. Not part of the four
> content pieces (AM essay, PM follow-up, teaser bundle) counted against
> the daily publishing cadence in `content_calendar_overview.md`; this
> document exists because the original Thursday brief specifically called
> for a video alongside the written tutorial. If produced, this is a
> companion video pointed at from the AM essay and the teaser bundle, not
> a substitute for either. Title (committed): "Hands-on: load balancing
> algorithms in under an hour." Companion file:
> `experiments/week-01/lb_algorithms_demo.py`.
>
> Every measured number in this plan is copied from the same verified
> run of `lb_algorithms_demo.py` cited in
> `posts/2026-08-27-thu-am-tutorial-load-balancing.md`; no new figures
> are introduced here. Re-run the script the day of recording regardless,
> per the pre-production checklist below, because a script drift between
> prep and recording is exactly the kind of silent failure this whole
> content week has been about catching.

---

## 1. Pre-Production Checklist (do this before touching record)

- [ ] Re-run `python3 experiments/week-01/lb_algorithms_demo.py` same-day.
      Confirm the terminal output ends with `All assertions passed. Every
      number above reproduces with seed 42.` If any number in the output
      differs from the table below, stop and reconcile before recording,
      do not narrate a number the screen doesn't show.
- [ ] Confirm the reference repo clone at
      `repos/awesome-system-design-resources/implementations/python/
      load_balancing_algorithms/` is present and unmodified: `ip_hash.py`
      (18 lines), `least_connections.py` (27 lines), `least_response_time.py`
      (33 lines), `round_robin.py.py` (15 lines), `weighted_round_robin.py`
      (24 lines).
- [ ] Terminal setup: 120 columns x 32 rows, monospace font at 18pt or
      larger, dark theme, shortened `PS1` (no full local path, no
      username visible in prompt).
- [ ] Screen capture at 1080p minimum, 30fps or higher.
- [ ] Microphone check: record 10 seconds of silence and 10 seconds of
      speech, confirm no clipping and no background hum before the full
      take.
- [ ] Close every notification source: chat apps, email client, OS
      notification center, calendar popups.
- [ ] Have this plan and the AM essay open on a second monitor or printed,
      not on the recording screen.

## 2. Reference Numbers Table (confirm on screen before recording)

| Scenario | Result |
|---|---|
| Round robin, 5 equal backends, 100k requests | exactly 20,000 each, 20.0% |
| Ring, 100 vnodes, same 100k requests | busiest 21.1%, quietest 18.9%, 1.12x spread |
| Ring, 1 vnode, same 100k requests | busiest 45.6%, quietest 6.6%, 6.88x spread |
| Smooth WRR, weights 5:4:3:2:1 | every backend within 1 request of its exact share |
| b2 degrades to 10x service time, mean queue depth | round robin 9.99 on b2, least-connections 1.66 |
| Remove 1 of 5 backends, 50k clients | mod-N remaps 79.9%, ring remaps 19.1% |
| Naive burst WRR (reference repo, weights 5:1:1) | `Server1` x5, then `Server2`, `Server3` |
| Cold-start least-response-time (reference repo, no updates yet) | `Server1` returned 3 times in a row |

## 3. Full Script (beat by beat, target 22-28 minutes)

### Beat 1: Cold Open (0:00-1:30)

**On screen:** the scenario-4 table from the terminal, `79.9%` and `19.1%`
already visible, paused before any narration starts.

**Narration draft:** "Five load balancing algorithms. Run them side by
side and two things happen that no one-sentence definition warns you
about. Drop one backend's speed by ten times and one of these algorithms
keeps feeding it a full, equal share of traffic anyway, its queue backs up
almost tenfold. Remove one backend from a pool of five and one of these
algorithms reshuffles eighty percent of your users to a new server, even
though only one server actually left. By the end of this video you will
have measured both of those failures yourself, on your own machine, with
one file and no dependencies."

**Action:** hold on the printed terminal output for 3-4 seconds before
cutting to the file.

### Beat 2: Setup (1:30-3:00)

**On screen:** `lb_algorithms_demo.py` open in an editor, scrolled to the
top docstring and imports.

**Narration draft:** "One file, 277 lines, nothing outside the Python
standard library, `hashlib`, `heapq`, `random`, `bisect`,
`collections.Counter`. Clone the repo or copy the file, then run `python3
lb_algorithms_demo.py`. Seed 42 throughout, so every number this video
quotes is exactly what your terminal will show too, not an
approximation."

**Action:** run the command live, let the full output scroll, do not cut
it short.

### Beat 3: Round Robin and the Exactness Trap (3:00-7:00)

**On screen:** `RoundRobin` class, then the printed `[1a]` block from the
terminal (20,000 each, 20.0% each).

**Narration draft:** "Three lines: pick the next backend in a fixed
cycle, wrap the index, done. Run 100,000 requests through five equal
backends and the split is exact, 20,000 to each, zero variance, because
with an equal backend count and a request total divisible by it, round
robin cannot produce anything else. That exactness sounds like a feature.
It's about to become the trap. Round robin's guarantee is about how many
requests each backend receives, not about how expensive each request
turns out to be once it's there. Keep that in mind. We come back to it in
about eight minutes."

**Action:** highlight the three-line `pick()` method on screen while
narrating it.

### Beat 4: Weighted Round Robin, Done Right and Done Wrong (7:00-11:00)

**On screen:** split terminal, reference repo's `weighted_round_robin.py`
output on the left (`Server1` x5 burst), this week's `SmoothWeightedRoundRobin`
scenario-2 output on the right.

**Narration draft:** "Give one backend five times the weight of another,
and the naive implementation gives it five requests in a row before
anything else gets a turn. Here's that exact output from a real reference
repo: five `Server1`s back to back, then `Server2`, then `Server3`. If
`Server1` is having a bad moment, all five of those requests pay for it
before the rotation moves on. The smooth version fixes this with a
scoring loop instead of a burst counter, every pick every backend's score
grows by its own weight, the highest score wins and pays back the total.
Run it for 100,000 requests at weights five-four-three-two-one and every
single backend lands within one request of its exact theoretical share.
Same ratio. Completely different request-by-request experience."

**Action:** trace the six-pick example from the AM essay live on screen,
weights `{a: 5, b: 1}`, showing the score dictionary after each pick.

### Beat 5: Least Connections and the Price of Knowing (11:00-15:00)

**On screen:** `LeastConnections.pick` and `.release`, then the
scenario-3 table (round robin 9.99, least-connections 1.66).

**Narration draft:** "Round robin and weighted round robin both decide
blind, no idea what's actually happening on any backend right now. Least
connections looks: track an active-request count per backend, send the
next request to whichever has the fewest, and require the caller to call
`release()` when a request finishes. That release call is the entire
mechanism, not optional bookkeeping. Here's what it buys you: degrade one
backend to ten times its normal latency, and round robin's mean queue
depth on it climbs to 9.99, nearly ten requests deep, on average, at any
given moment. Least connections, watching the same degraded backend,
holds that queue to 1.66. The cost: skip `release()` on even one error
path and this entire advantage silently evaporates, because the balancer
is now tracking a number that no longer matches reality."

**Action:** point at the exact `release()` call in the simulation loop
and explain what happens if that line is deleted, without actually
deleting it on screen, describe the failure instead of demonstrating a
broken run.

### Beat 6: Hashing, Sticky Sessions, and the Ring (15:00-21:00)

**On screen:** `IPHash` and `ConsistentHash` side by side, then
scenario-1's vnode comparison (1.12x vs 6.88x), then scenario-4's removal
comparison (79.9% vs 19.1%).

**Narration draft:** "Two more algorithms, both hash a client to pick a
backend, answering two different questions. Plain hash mod N is sticky by
accident, the same client always lands on the same remainder as long as
the backend count doesn't change. A consistent-hash ring, the same one
from Tuesday's file, spreads each backend across many small virtual
arcs instead of one big one. Run both at a single virtual node per
backend and the spread is severe, one backend takes 45.6% of traffic,
another takes 6.6%, a 6.88x gap. Run the ring at 100 virtual nodes and
that gap shrinks to 1.12x. Now the real test: remove one backend from a
pool of five. Plain hash mod N reshuffles 79.9% of clients to a new
backend. The ring reshuffles 19.1%, close to the one-fifth you'd expect
from losing exactly one out of five nodes. Same removal, same client set,
four times the disruption, purely a function of which hashing scheme was
running."

**Action:** run scenario 4 live, on screen, do not pre-record this part,
let the audience watch the actual removal happen and the actual numbers
print.

### Beat 7: Wrap and Homework (21:00-24:00)

**On screen:** the decision table from the AM essay, formatted as a
five-row on-screen graphic.

**Narration draft:** "Five algorithms, five different bets about what
stays true in your system. Equal-cost stateless backends, round robin.
Known, stable capacity differences, smooth weighted round robin, not the
bursty kind. Variable request cost or backends that can silently
degrade, least connections, if you can guarantee every request reports
when it finishes. Session affinity at a small, stable scale, IP hash.
Session affinity where nodes come and go, the ring. Homework: the
reference repo also ships a least-response-time balancer that routes by
response time instead of connection count. Add it to this file's harness
and measure its cold-start behavior yourself, what does it do before a
single response time has been recorded? The answer is in this afternoon's
mistakes checklist, but measure it yourself first."

**Action:** end card: repo URL, this afternoon's checklist post title,
tomorrow's contrarian-take title.

## 4. B-Roll / On-Screen Assets Needed

- Terminal capture of the full `lb_algorithms_demo.py` run, unedited,
  timestamped for each of the four scenario blocks.
- Editor view of `RoundRobin.pick`, `SmoothWeightedRoundRobin.pick`,
  `LeastConnections.pick`/`.release`, `IPHash.pick`, `ConsistentHash.pick`,
  each isolated on screen long enough to read at normal speaking pace.
- Side-by-side terminal capture of the reference repo's
  `weighted_round_robin.py` output next to this week's smooth-WRR output.
- The five-row decision table as a single static graphic for the wrap.

## 5. Recording Checklist

- [ ] Re-run the demo same day, confirm "All assertions passed" before
      hitting record.
- [ ] Two takes per scenario run, maximum, cut at scenario boundaries,
      not mid-sentence.
- [ ] Record the cold open last, after every other beat is in the can,
      so the hook can reference exact on-screen numbers without guessing.
- [ ] Confirm no personal file paths, usernames, or unrelated terminal
      history are visible in any take.
- [ ] Save raw takes before any editing pass, do not overwrite.

## 6. Post-Production Checklist

- [ ] Trim to the beat boundaries above; target final runtime 22-28
      minutes.
- [ ] Captions: auto-generate, then hand-correct every technical term
      (`vnode`, `pick`, `release`, `IPHash`, `WRR`) and every number
      (79.9%, 19.1%, 6.88x, 1.12x, 9.99, 1.66).
- [ ] Chapter markers at each beat boundary (Cold Open, Setup, Round
      Robin, Weighted RR, Least Connections, Hashing, Wrap).
- [ ] Thumbnail: the scenario-4 table (79.9% vs 19.1%), high contrast,
      no fabricated claims in thumbnail text beyond what the video proves.

## 7. Publish Block

- Title options: "I measured 5 load balancing algorithms (one is a
  trap)" or "Load balancing algorithms: measured, not explained."
- Description: link to this repository's
  [`experiments/week-01/lb_algorithms_demo.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/experiments/week-01/lb_algorithms_demo.py) and
  [`lib/consistent_hashing.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/consistent_hashing.py), and
  the AM essay (`{substack-url}`, placeholder pending live URL). Include
  chapter timestamps matching the beats above. No hashtag stacks.
- Cross-post: link the video from the AM essay's closing line and from
  the teaser bundle's LinkedIn post, do not duplicate the video's full
  script as a caption anywhere, per the same teaser-length conventions
  used for every other platform this week.
- End card: repo URL, PM checklist title, tomorrow's contrarian-take
  title on L4 vs L7 load balancing.

## 8. Success Criteria

- [ ] Every number spoken in the final cut matches a number actually
      visible on screen at that timestamp, no narrated number without a
      corresponding on-screen source.
- [ ] The homework beat's claim (least-response-time's cold start
      defaults to the same backend) is verified against the reference
      repo's actual code before the video ships, not asserted from
      memory. Verified this session: three consecutive `get_next_server()`
      calls with no prior `update_response_time()` calls return `Server1`
      all three times.
- [ ] Final runtime falls inside the 22-28 minute target; if a beat runs
      long, cut narration, not code demonstrations, viewers came to see
      the numbers happen live.
