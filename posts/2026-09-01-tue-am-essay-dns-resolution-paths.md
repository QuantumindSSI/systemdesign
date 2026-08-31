# Week 2 · Tue 2026-09-01 · Long-form: Your DNS Load Balancer Is Steering a Resolver, Not a User

> Calendar row: W2 Tue AM, 09:00 (CSV row `26:2`). Format: concept deep-dive.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/binhnguyennus/awesome-scalability.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: define the failure DNS
> resolution paths fixes, in two lines with a concrete example | build the
> mechanism conceptually, at the level of outcomes, not code | state what DNS
> resolution paths still does not do, the gaps the code inherits.
> Committed CTA: "Save this for your next design review."
>
> Format note: per the day-split recorded in `prep/README.md` (2026-08-26),
> Tuesday runs concept in the morning and code in the evening. This post is
> deliberately code-free. The raw-packet tracer, the awesome-scalability
> section map, and the line-by-line reading are tonight's follow-up,
> `posts/2026-09-01-tue-pm-followup-dns-tracer-walkthrough.md`.
>
> Week-2 scope fences:
> - Monday's essay deferred "how a request finds a PoP" to this post. That
>   debt is paid here. This post does not re-derive cache keys, freshness, or
>   residency, and links back for them instead.
> - Cache population strategy is Wed 09-02, eviction is Thu 09-03, stampede
>   protection is Fri 09-04. None of them is pre-spent here.
> - Anycast is named as the alternative steering mechanism and explicitly not
>   developed, because it is a routing-layer topic and this week is caching.
>
> Sources verified 2026-09-01:
> - `github.com/binhnguyennus/awesome-scalability`, GitHub API: 73,628 stars,
>   last push 2026-01-04, not archived. Its DNS cluster sits under the
>   `## Availability` heading (README.md line 515) inside the Load Balancing
>   list, lines 551 to 556: LinkedIn RUM DNS, Dropbox edge network, Dropbox
>   intelligent DNS, Stripe DNS monitoring, Monday multi-DNS, Hulu dynamic
>   anycast. Line numbers re-grepped today and still accurate; the public copy
>   cites section names anyway, per the standing rule in `prep/README.md:73`.
> - Nikita Shirokov, "Intelligent DNS based load balancing at Dropbox",
>   dropbox.tech, 2020-01-08. Full text re-fetched today. Every Dropbox figure
>   below is quoted from that fetch, not from the 2026-08-22 prep notes.
> - RFC 7871 (Client Subnet in DNS Queries, informational, May 2016) is the
>   ECS specification the Dropbox post links to.
> - Live measurement: `prep/week-02/code/dns_path_tracer.py` run on this
>   machine today. Output is used in tonight's post; the TTL figure quoted
>   here comes from that run.
>
> Adversarial review record (2026-09-01):
> - Every Dropbox number below appears verbatim in the re-fetched post:
>   "more than 20 edge clusters"; Vladivostok p75 RTT "around 300-400 ms"
>   falling to "roughly 150" after rerouting to Frankfurt; "around 10-15%
>   latency improvement ... both for 75th and 95th percentile, with no
>   negative effects at higher percentiles"; "around 10% of our user saw 2 ms
>   improvements, 1% got around 20 ms improvements and long tail saw up to
>   200 ms and above"; Iceland Oslo to Amsterdam "by 10-15%"; Egypt Milan to
>   Paris "a 10% benefit"; "over half a billion" users; peering "in more than
>   30 locations"; anycast used "for apex record of dropbox.com" ✓
> - The TXL loop `TXL->FRA->TXL->FRA->TXL` and the Vladivostok path
>   "Vladivostok->Moscow->Atlantic Ocean->USA->Pacific Ocean->Tokyo" are the
>   post's own illustrations, reproduced as such ✓
> - "the authoritative DNS server does not see the end user's IP address, but
>   the IP address of the user's DNS resolver" and ECS being "still not widely
>   used" with Google and OpenDNS named as the notable providers: same source,
>   appendix C ✓
> - The 60-second TTL on dropbox.com is measured, not quoted, and is labeled
>   as a reading taken from one vantage point today ✓
> - No invented engineer, incident, customer, or benchmark. The Dropbox work
>   is attributed to Dropbox and NS1, who did it ✓
> - The honest reading of the results section (median gain small, tail gain
>   large) is my interpretation of the published distribution and is presented
>   as interpretation, not as a claim from the source ✓
> - **Publication-gap remediation (2026-09-04).** No post in this week's
>   sequence reached readers, so every backward reference to a sibling post
>   was a dangling reference to material nobody had seen. The body now
>   carries the referenced substance inline instead of pointing at it:
>   the HTTP freshness precedence order (s-maxage, then max-age, then
>   Expires minus Date, then heuristic) stated in full beside the DNS TTL,
>   rather than referring to Monday's essay for it. Written so it reads as a reminder to a sequential reader and as
>   sufficient context to a cold one ✓
> - Zero em dashes.

---

**Topic:** Why DNS-based traffic steering is a decision about resolvers and measured latency rather than about users and geographic distance

**Subtitle:** You will learn why the server answering your DNS query has never seen your IP address, why that single fact sent users in Vladivostok most of the way around the planet, and what it costs to fix.

Good morning. I owe you an answer from yesterday.

Monday's essay followed a request from a reader in London into a London point of presence, and right at the first step I put up a hand and said the interesting question, how that request found the London PoP rather than the Frankfurt one, was Tuesday's problem. It is Tuesday.

Here is the thing that makes this harder than it looks. You can build the most beautiful edge network in the world, and the mechanism you use to send people to it is a protocol from 1987 that was never designed to know who is asking.

## The failure, in two lines

You have edge locations in many places, and the only lever most systems have for deciding which one a user reaches is DNS. DNS never sees the user, so the routing decision has to be made about somebody else entirely, and the usual stand-in for a user's network position is a dot on a map that has nothing to do with how their traffic actually travels.

Now the concrete version, and it is a good one because the numbers are published.

Dropbox ran geolocation-based load balancing across what their traffic team describes as more than 20 edge clusters. Send the user to the nearest PoP. Users in Vladivostok were therefore sent to Tokyo, which is the obvious answer if you are looking at a map, because Tokyo is close.

It was the wrong answer by an enormous margin. Most Russian ISPs have no presence in Tokyo, and most Russian transit connections happen in the west of the country. So traffic from Vladivostok to a server geographically nearby went, in Dropbox's own description of the path, Vladivostok to Moscow, across the Atlantic Ocean, across the United States, across the Pacific Ocean, and into Tokyo. The 75th percentile round trip time between those users and a Dropbox frontend server was around 300 to 400 ms.

The map said neighbors. The network said almost all the way around the world and back.

## The receptionist who makes the call for you

To understand why the fix is awkward, you have to be honest about who is actually talking to whom during a DNS lookup.

Think about calling a company through a receptionist. You ring the front desk, you say who you want, and the receptionist places the call on your behalf. The person who eventually picks up sees the front desk's number on their display. They have never seen yours. If they want to do something clever based on where the caller is, everything they know is about the receptionist.

That is DNS. The Dropbox post lays the sequence out in four steps, and it is worth walking slowly because every conclusion in this piece falls out of it:

1. The user's browser or desktop client needs an IP address for a hostname, so it sends a query to whichever resolver it has been configured with, usually the ISP's.
2. That recursive resolver, assuming it has nothing cached, works its way to the authoritative DNS server for the zone.
3. The authoritative server replies with an IP address.
4. The recursive resolver passes that address back to the user.

Read step two and three again. The conversation that decides which of your edge locations the user will connect to happens between the resolver and your authoritative server. The user is not in it.

The Dropbox post states the consequence plainly: the authoritative DNS server does not see the end user's IP address, it sees the IP address of the user's DNS resolver.

So when a vendor sells you "geo DNS," what they are actually selling is geo-location of resolvers. Every user behind a given resolver receives the same answer, because from the authoritative server's seat they are indistinguishable. They are one caller with one phone number.

## Distance is a proxy for topology, and the proxy breaks

Once you accept that you are steering resolvers, the second problem shows up: even if you knew exactly where a user was standing, distance would still be the wrong input.

Dropbox's clearest small example is Berlin. Imagine a user whose ISP is in Berlin, and Dropbox has a PoP in Berlin. Geographically this is a solved problem. But Dropbox has no private network interconnection with that ISP in Berlin, so the ISP has to reach them through a transit provider, and that transit connection happens in Frankfurt. The traffic does not go Berlin to Frankfurt and stop. It goes out to Frankfurt, back to Berlin, out to Frankfurt again, and back to Berlin, because each leg is following its own routing, not the straight line you drew.

That is the whole problem in one shape. Geographic distance is a proxy for network distance. It is usually a decent proxy, which is exactly why it survives so long in production. It fails precisely where peering relationships do not follow the map, and those failures are not evenly distributed. They concentrate in the places where you have the fewest users and the least visibility, which is why they persist.

Dropbox is direct about the limits of chasing these one at a time. They run an open peering policy and peer publicly in more than 30 locations, and they still say that tracking down every one of these cases is unrealistic.

## The shape of the fix, at the level of outcomes

The fix is one sentence: stop routing on where people are, and start routing on what you measured.

Then the sentence turns into a real engineering problem, because you cannot measure what you cannot join. You need to connect three things:

- which subnet a user is on
- which resolver that subnet uses
- how long it actually takes that user to reach each of your PoPs

The third one Dropbox already had, because their desktop client can run latency tests against every edge cluster. The first one they had in aggregate. The second one is the hard one, and it is hard for exactly the reason we have been circling: your authoritative server sees the resolver, and your client sees the user, and nothing naturally sees both.

The trick they used is the part of this story I would most want you to remember, because it is a genuinely clever piece of instrumentation and you can steal the shape of it for other problems.

They had the desktop client issue DNS queries for **random subdomains** of their own domain. Because the names are random, no resolver anywhere has them cached, so every one of those queries is forced all the way through to Dropbox's authoritative servers. On the authoritative side they log which unique name arrived from which resolver IP. On the client side, the client reports which unique names it issued. Join those two logs on the random name, and you have learned which resolver that client's subnet uses, without ever needing the resolver to tell you.

They are explicit that this is aggregated by subnet and that individual user IP addresses are not logged, and they credit prior art for the technique.

With the join in hand, the rest is arithmetic. For every resolver, look at the population of clients behind it, take the 75th percentile of their measured latency to each PoP, and pick the winner.

Then comes the design decision that I think is the actual lesson of the piece, and it has nothing to do with DNS.

They did not encode the result as configuration. They encoded it as **data**: a JSON document mapping subnets to PoP labels, tagged with IATA airport codes, uploaded to their DNS provider through an API as the last step of a pipeline. Regenerate the telemetry, regenerate the map, upload the map.

That is the difference between a routing policy a human maintains and a routing policy a measurement maintains. One of them drifts the moment the internet changes shape. The other one notices.

## What it still does not do

This is the beat where most write-ups stop, and it is the beat that decides whether you can actually run this. Here are the gaps, and they are inherited by any implementation you build.

**You are still steering a crowd, not a person.** Every user behind a resolver gets the same answer. A resolver serving a geographically diverse subscriber base gets one label, and the users at the edges of that population get an answer optimized for somebody else. The p75 aggregation is an admission of this: you are explicitly choosing to serve three quarters of the crowd well.

**The obvious fix is not widely deployed.** EDNS Client Subnet, specified in RFC 7871, exists exactly for this. It lets a recursive resolver pass along a truncated version of the client's subnet so the authoritative server can answer for the actual user. Dropbox's appendix says plainly that it is still not very common, and names Google and OpenDNS as the notable providers that do it. So you build the resolver-based map anyway, and treat ECS as a bonus when it happens to be present.

**Your steering decision is only as fresh as your TTL.** Once a resolver has your answer, it keeps handing that answer out until the record expires, and nothing you change in the meantime reaches those users.

This is the same arithmetic that governs an HTTP cache, wearing different clothes, so it is worth stating both halves side by side. In HTTP, a cached response is reusable without asking the origin until its age exceeds its freshness lifetime, and a shared cache computes that lifetime from `s-maxage` if present, otherwise `max-age`, otherwise `Expires` minus `Date`, otherwise a value it invents heuristically. In DNS, a cached record is reusable until its TTL runs out, and there is no heuristic branch because the TTL is mandatory. Both are the same trade: a longer lifetime means fewer requests reaching you and less control over what your users see, and a shorter one inverts both.

I traced `dropbox.com` from this machine this morning and the authoritative answer came back with a 60-second TTL. Sixty seconds is a deliberate choice, and it is the price of steerability: short TTLs mean more queries and more load on your authoritative tier, and they buy you the ability to move traffic quickly. Tonight's post shows that measurement, alongside `example.com` answering with a 300-second TTL, which is what a name that is not being actively steered looks like.

**The first version is not the smart version.** Dropbox says the initial map considers no BGP policy, so it cannot prefer a location where they have direct peering, and they name that as the top priority for the next iteration. They also say PoP weights were static, with load-based feedback still to come. A latency map with no load awareness will happily route everyone to your best-performing PoP right up until that PoP is the reason performance degrades.

**There is a completely different answer available.** Anycast announces the same address from many locations and lets BGP decide, which moves the steering decision out of DNS and into routing. Dropbox uses it for the apex record of dropbox.com. It has its own tradeoffs and it is a routing topic rather than a caching one, so I am naming it and leaving it, rather than pretending this week covered it.

## What actually moved, read honestly

Dropbox reported roughly a 10 to 15% latency improvement at both the 75th and 95th percentile when they deployed the latency map against the geo map, with no negative effects at higher percentiles.

But the distribution is the interesting part, and I want to read it carefully rather than just repeating the headline. They published it: around 10% of users saw a 2 ms improvement, 1% got around 20 ms, and the long tail saw up to 200 ms and above.

Sit with those three numbers, because they describe almost every latency project I have ever seen argued about. For most people the change is invisible. Two milliseconds is nothing. You could not detect it in a user study if you tried.

The value is entirely in the tail. Vladivostok went from 300 to 400 ms down to roughly 150 by being routed to Frankfurt instead of Tokyo, because Frankfurt is one of the major places Russian ISPs exchange traffic. Iceland moved from Oslo to Amsterdam for a 10 to 15% gain, because there is no direct submarine cable from Iceland to Norway and the cables go to Denmark instead. Egypt moved from Milan to Paris for about 10%, because that is where the cables go.

Notice what all three have in common. None of them was fixed by being closer. They were fixed by following the cables instead of the coastline.

So if you ever have to defend this kind of work to someone holding an average, the honest pitch is not "everything gets faster." It is "a small number of your users are having a catastrophically bad time for a structural reason, the average will never show it to you, and this is how you find them."

## The question to take into your next design review

If you run anything in more than one location, there is one question worth asking out loud this week.

**What is the input to our traffic steering decision, and when did we last check it against a measurement?**

If the answer is a geo database, you now know its precise failure mode: it is right until peering disagrees with geography, and it will not tell you when that happens.

If the answer is a latency map, the follow-up is when it was last regenerated, because a stale measurement is just geography with extra steps.

And whichever it is, find out your TTL. That number is your reaction time. It is how long a bad decision stays deployed after you have already fixed it.

Save this for your next design review.

---

*Today, 17:00: the same resolution path, performed by hand. Raw DNS packets, recursion turned off, every hop and its round trip time printed, with the two lines people get wrong.*

*Tomorrow, 09:00: the other half of caching. What Facebook's memcache deployment chose on the write path, and why they delete instead of update.*
