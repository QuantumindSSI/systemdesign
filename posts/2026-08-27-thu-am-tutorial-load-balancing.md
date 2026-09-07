# Week 1 · Thu 2026-08-27 · Long-form: Hands-On, Load Balancing Algorithms in Under an Hour

> Calendar row: W1 Thu AM, 09:00. Format: long-form Substack essay,
> "hands-on tutorial" spine (define the end state, numbered steps with
> code, a verification step). Pillar: System Design Fundamentals. Pass:
> Foundations. Companion file:
> `experiments/week-01/lb_algorithms_demo.py` (277 lines, stdlib only, seed
> 42). Reference implementations:
> **Canonical source rule (retrofitted 2026-09-06).** The CSV `source` column
> for this row names an external repository. Per `AGENTS.md` that string is an
> internal routing hint only and is not reproduced here or in the body.
> Standards: persona-constitution (Laws I-IV, Structurally Decisive,
> Adversarial Review) + QSSI research persona (Laws I-VI) + Amendment 1.
>
> Adversarial review record (this session, 2026-08-27):
> - Every scenario number below (20,000 each; 1.12x/6.88x spread; the
>   within-1-request weighted share; 9.99/1.66 queue depth; 79.9%/19.1%
>   remap) is copied directly from a fresh run of `lb_algorithms_demo.py`
>   this session, not carried over from the 2026-08-22 prep pass unverified.
> - Naive-burst-WRR output (`Server1` x5, then `Server2`, `Server3`) is
>   copied from a direct run of the reference repo's own
>   `weighted_round_robin.py`, this session, not asserted from memory.
> - `round_robin.py.py`'s actual on-disk filename (double extension) is
>   reproduced exactly as it exists in the cloned repo, not corrected or
>   treated as a typo of this essay's own.
> - This file replaces the week-0-era plan of a standalone YouTube video
>   for this slot; the video, if produced, is a separate, non-essay
>   artifact (see `posts/2026-08-27-thu-video-production-plan.md`), not a
>   substitute for this post under the 2026-08-24 publishing-format pivot.

---

Five load balancing algorithms, one file, no dependencies past the Python standard library. By the end of this essay you will have run all five, watched two of them fail in specific, measurable ways, and have a decision table you can apply to a real system instead of a rule of thumb you half-remember.

Most explanations of load balancing stop at the definition: round robin cycles, weighted round robin cycles with a bias, least connections routes to whoever's least busy, hashing keeps a client on the same backend. All true, all useless for deciding which one to run in a specific system, because the definitions don't say what happens when a backend degrades, when the pool changes size, or when a naive implementation of the "obviously correct" idea turns out to behave nothing like its own description. This tutorial exists to close that gap with numbers instead of adjectives: four scenarios, each one built to expose exactly where an algorithm's real behavior diverges from its one-sentence pitch.

## The End State

When you're done, `python3 lb_algorithms_demo.py` will print four scenarios and end with the line "All assertions passed." That is the actual proof this tutorial works, not a claim about it: the file contains its own assertions, and if any number drifts from what's documented here, the script itself fails loudly instead of printing something quietly wrong. 277 lines, five classes, four scenarios, one shared backend pool. Nothing here talks to a network; every "backend" is a string label and every "request" is a simulated arrival, which is what makes the whole thing deterministic and runnable in under five seconds on a laptop.

## Step 1: Get the File Running

The file needs nothing beyond Python 3.8, no `pip install`, no config. `hashlib`, `heapq`, `random`, `bisect`, `collections.Counter`, all standard library. Run it once before reading further, because every number in this essay is something you can watch happen on your own terminal:

```
python3 lb_algorithms_demo.py
```

Five backends, named `b0` through `b4`, are shared across all four scenarios, along with a fixed weight assignment, `{"b0": 5, "b1": 4, "b2": 3, "b3": 2, "b4": 1}`, used only where weights matter. Seed 42 throughout, so the numbers below are not "approximately what you'll see." They are exactly what you'll see, on any machine, every time.

## Step 2: Round Robin, and the Trap Hiding Inside "Exact"

`RoundRobin` is the smallest class in the file: an index that increments and wraps, `self.backends[self.i % len(self.backends)]`. Nothing else. There is no clever version of round robin hiding somewhere; fifteen lines is the whole idea, and every implementation of it you will ever read is this same counter.

Scenario 1a runs 100,000 requests through it across five equal backends. The result: exactly 20,000 requests to each backend, 20.0% apiece, zero variance. The file asserts this directly, `max(rr_counts.values()) - min(rr_counts.values()) == 0`, because with five backends and a number of requests divisible by five, round robin cannot produce anything else. It is not statistically even. It is exactly even, by construction, every time.

That exactness is the trap. Round robin's guarantee is about the count of requests it sends to each backend, not about how expensive each request turns out to be once it gets there. Hold that thought; scenario 3 is built specifically to break it.

The entire `pick()` method is three lines:

```python
def pick(self, _key=None):
    backend = self.backends[self.i % len(self.backends)]
    self.i += 1
    return backend
```

No branching, no state beyond a single counter, cyclomatic complexity of one. That simplicity is precisely why round robin is the right default when there is genuinely nothing to adapt to: a bug in this method would have to be a bug in modular arithmetic itself. The moment a system needs the balancer to react to anything, capacity, health, load, that same simplicity becomes the limitation, because there is nothing here for a reaction to hook into.

## Step 3: Weighted Round Robin, Done Right and Done Wrong

Not every backend deserves an equal share. `WEIGHTS = {"b0": 5, "b1": 4, "b2": 3, "b3": 2, "b4": 1}` says `b0` should get five times `b4`'s traffic. The naive way to implement that is to burst: give `b0` five requests in a row, then one to `b1`, one to `b2`, and so on. The bursting version is the one people write first, and against weights `[5, 1, 1]` for three servers it produces exactly this sequence: `Server1, Server1, Server1, Server1, Server1, Server2, Server3`. Five requests land on the same server back to back before anything else gets a turn.

That is correct on average and disastrous in the short term. If `Server1` is momentarily slow, five consecutive requests all pay for it before the rotation ever reaches another server. `SmoothWeightedRoundRobin`, the class in this week's demo file, fixes this with an nginx-style scoring loop instead of a burst counter: every pick, every backend's running score increases by its own weight, whichever backend has the highest score wins that pick, and the winner's score is reduced by the total weight of all backends. Four lines of logic, and the sequence it produces interleaves instead of bursting: heavier backends appear more often, but never five times consecutively when a lighter backend is due a turn soon.

Scenario 2 runs 100,000 requests through the smooth version with weights 5:4:3:2:1 and checks the result against the exact expected share for each backend, `NUM_REQUESTS * weight / total_weight`. Every single backend lands within 1 request of its theoretical share: `b0` at 33,333 (expected 33,333.3), `b1` at 26,667 (expected 26,666.7), down to `b4` at 6,667 (expected 6,666.7). Same weights as the naive version, same eventual ratio, and a completely different request-by-request experience for whichever backend would have suffered from five-in-a-row bursts.

The scoring loop is small enough to trace by hand. Two backends, `a` weighted 5 and `b` weighted 1, total weight 6. Running the actual class for six picks produces this exact sequence, scores shown after each pick:

```
pick 1: a   scores after: {'a': -1, 'b': 1}
pick 2: a   scores after: {'a': -2, 'b': 2}
pick 3: a   scores after: {'a': -3, 'b': 3}
pick 4: b   scores after: {'a': 2,  'b': -2}
pick 5: a   scores after: {'a': 1,  'b': -1}
pick 6: a   scores after: {'a': 0,  'b': 0}
```

`a` still wins five of the six picks, the same 5:1 ratio the burst version delivers, but `b` gets its turn on pick 4, in the middle of the sequence, instead of being forced to wait for `a` to exhaust all five of its requests first. Every pick, both scores grow by their own weight, `a` by 5 and `b` by 1; whichever score is currently highest wins and immediately drops by the total weight, 6. After six picks the scores return exactly to zero, which is what guarantees the long-run ratio converges to the input weights instead of drifting.

## Step 4: Least Connections, and the Price of Knowing

Round robin and weighted round robin both decide who gets the next request without looking at what's currently happening on any backend. `LeastConnections` is the first class in the file that looks: it tracks an `active` count per backend, sends the next request to whichever backend has the fewest in-flight requests right now, and requires the caller to call `release()` when a request finishes. That `release()` call is not optional bookkeeping. It is the entire mechanism. Skip it, even on one code path, an error handler that doesn't decrement the counter, a timeout that doesn't clean up, and the balancer's view of "least loaded" silently drifts away from reality, permanently favoring whichever backend happens to have had its counts undercounted.

Scenario 3 is where this pays off, measurably. One backend, `b2`, gets a service time ten times longer than the others: 100ms instead of 10ms, everything else unchanged, 20,000 simulated requests arriving one every 2ms. Round robin has no way to know `b2` is slow, so it keeps sending it a full, equal share of traffic regardless, and the simulated queue in front of `b2` backs up: mean queue depth 9.99, against 1.00 for every other backend, a request sitting in `b2`'s queue essentially the entire time on average. Least connections, watching the same degraded backend, sheds load off it automatically the moment its in-flight count climbs relative to the others: mean queue depth on `b2` drops to 1.66, against 1.20-1.21 on the healthy backends, a gap that is still visible but nowhere near the pileup round robin produces. The file's own assertion states the size of the effect directly: least-connections' queue depth on the slow backend must be less than half of round robin's, and the measured 1.66 against 9.99 clears that bar by a wide margin. That is the operational cost of the algorithm made concrete: least connections only works if every request that starts also gets marked finished, on every code path, without exception.

### What "Least" Actually Measures

Connection count is one proxy for load. Response time is another, and the reference repo's `least_response_time.py` implements that second version: instead of counting in-flight requests, it tracks the last observed response time per backend and routes to whichever one was fastest last time. The tradeoff is a cold start the demo file's `LeastConnections` doesn't have. `LeastResponseTime` initializes `response_times = [0] * len(servers)`, and its selection line, `self.response_times.index(min(self.response_times))`, calls Python's `list.index()`, which always returns the first matching position. Before a single response time has been recorded, every backend ties at zero, and `index()` always breaks that tie the same way: running `get_next_server()` three times against a fresh instance, with no calls to `update_response_time()` in between, returns `Server1` all three times. Not a random backend, not a rotating one, the same one every time, because index-based tie-breaking is deterministic and the demo file's `LeastConnections` deliberately isn't: it breaks ties with `self.rng.choice(candidates)`, spreading the cold-start load across every backend that's currently tied instead of concentrating it on whichever one happens to sit first in a list. A response-time-based balancer is a legitimate design, arguably a better proxy for "which backend is actually struggling" than a raw connection count, but it needs either a randomized tie-break or a brief warm-up period before it's trusted with production traffic, and the reference file, being a teaching example rather than a production balancer, has neither.

## Step 5: Hashing, Sticky Sessions, and the Ring Underneath It

The last two classes both hash a client identifier to pick a backend, and they answer two different questions. `IPHash` is the naive version: `hash(client) % len(backends)`, sticky by accident, because the same client always maps to the same remainder as long as the backend count doesn't change. `ConsistentHash` is Tuesday and Wednesday's ring, unchanged: MD5 into a 128-bit space, sorted ring positions, virtual nodes, `bisect` for the lookup.

The reference repo's `ip_hash.py` is eighteen lines and makes the mechanism, and its blind spot, easy to see directly. Running its own example against four client IPs and three servers:

```
Client 192.168.0.1 -> Server3
Client 192.168.0.2 -> Server3
Client 192.168.0.3 -> Server1
Client 192.168.0.4 -> Server3
```

Three of the four clients land on `Server3`. That's not a bug, it's what "hash mod N" looks like with a tiny, arbitrary sample: MD5 doesn't know or care that these four IPs are meant to represent a spread of traffic, it just produces whatever remainder each one produces, and small samples routinely clump. The property that actually matters, stickiness, still holds: `192.168.0.1` maps to `Server3` every single time this code runs, which is the entire feature. What it doesn't hold is even distribution at small N, which is exactly why the demo file's scenario 1 measures the same class of algorithm at 100,000 requests instead of four, where the law of large numbers, not the hash function's good intentions, is what actually produces the near-even split.

Scenario 1 runs the ring at two different virtual-node counts against the identical 100,000 simulated requests used for round robin, and the gap is the same one measured on Tuesday: with 100 virtual nodes per backend, the busiest backend (`b1`, 21.1%) handles 1.12 times the traffic of the quietest (`b2`, 18.9%). Drop to a single virtual node per backend and the spread becomes actually severe: the busiest backend, `b1` again, jumps to 45.6% of all traffic, while the quietest, `b4`, gets only 6.6%, a 6.88x gap between them, an imbalance nobody would accept in production traffic routing.

Scenario 4 removes one backend, `b2`, from a pool of five and asks the same question Tuesday's file answered with two tracked users: how many of 50,000 simulated clients change backends? Under plain `hash(client) % N`, the answer is 39,948, 79.9% of all clients, reassigned to a new backend even though only one backend actually left. Under the consistent-hash ring, the answer is 9,542, 19.1%, close to the theoretical 1/N a five-node ring predicts for losing exactly one of its members. Same removal, same client set, a four-times difference in how much of the system reshuffles, purely a function of which hashing scheme was routing traffic.

## Verification: Prove It Ran, Don't Just Trust It

The script's last line is the actual proof this tutorial's numbers are real, not narrated: `All assertions passed. Every number above reproduces with seed 42.` Six separate `assert` statements are embedded directly in the four scenario functions, checking exactly the claims made above, that round robin's spread has zero variance, that more virtual nodes produce a tighter spread than fewer, that weighted round robin lands within one request of its target share for every backend, that round robin piles up more than five times the queue depth on a degraded backend compared to its healthy peers, that least connections cuts that pileup by more than half, and that mod-N hashing remaps more than 70% of clients on a single removal while the ring remaps less than 30%. If you change anything, the weights, the seed, the number of requests, and one of those assertions fails, the script tells you exactly which claim broke, on which line, instead of leaving you to eyeball a table of numbers and guess whether something drifted.

## The Decision Table

Five algorithms, five different situations they're actually built for, not five interchangeable ways to spread load evenly:

- **Stateless backends, genuinely equal cost per request:** round robin. Its exactness is a feature here, because there is nothing to adapt to.
- **Backends with known, stable capacity differences:** weighted round robin, the smooth variety specifically. A naive burst implementation, the kind measured above producing five requests in a row to the same server, defeats the entire purpose of spreading load evenly over time.
- **Requests with genuinely variable cost, or backends that can silently degrade:** least connections, accepting the operational obligation that every `pick()` needs a matching `release()` on every exit path, including errors and timeouts.
- **Session affinity or cache locality, small and stable backend count:** IP hash, accepting that its cost is `79.9%`-scale reshuffling the day a backend actually needs to leave the pool.
- **Session affinity or cache locality at a scale where nodes come and go regularly:** the consistent-hash ring, paying a small, measured, ongoing imbalance (1.12x with enough virtual nodes) to avoid the much larger one-time cost IP hash pays on every scaling event.

None of these five is strictly better than the others; each one is a bet about what stays true in your specific system, whether requests are equal cost, whether capacity differences are known in advance, whether the backend pool changes size often, and the wrong bet shows up exactly the way it showed up in the scenarios above: as a specific, measurable number, a queue depth of 9.99 or a remap rate of 79.9%, not a vague sense that something feels off.

---

*This afternoon, 17:00: five yes/no checks that catch the mistakes hiding
inside today's numbers before they ship. Tomorrow, 09:00: the hot take this
week has been building toward, on why most advice about L4 vs L7 load
balancing gets the tradeoff backwards.*
