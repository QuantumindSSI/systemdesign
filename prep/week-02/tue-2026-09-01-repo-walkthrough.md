# Prep · Week 2 · Tue 2026-09-01 · 09:00 · Repo walkthrough

> Calendar row: W2 Tue AM. Committed title: "Inside awesome-scalability: DNS
> resolution paths in real code (foundations)". Source repo:
> github.com/binhnguyennus/awesome-scalability.
> Repo verified via GitHub API 2026-08-22: 73,458 stars, last push 2026-01-04,
> not archived. Local clone at `repos/awesome-scalability` (gitignored).

## Honesty note on the format

This repo is a curated index, not a codebase - "where DNS resolution actually
lives" here means the engineering write-ups it curates. The committed outline
already allows this ("files/sections that implement **or document**"). The
walkthrough: map the section, then trace ONE entry end to end. The PM snippet
supplies the actual code (our own raw-packet tracer).

## Section map (verified in clone, README.md, 2026-08-22)

DNS entries live in the Traffic/Infrastructure listings around lines 551-556:

- L551: Traffic Steering using RUM DNS at LinkedIn (USENIX SRECon17 talk)
- L553: **Intelligent DNS based load balancing at Dropbox** (dropbox.tech) <- trace this
- L554: Monitor DNS systems at Stripe ("secret life of DNS")
- L555: Multi-DNS architecture at Monday (3 parts, Cloudflare -> multi-DNS)
- L556: Dynamic Anycast DNS infrastructure at Hulu
- (L160: Deliveroo CDN A/B testing - adjacent, skip)

Line numbers drift as the repo updates - re-grep `rg -n "DNS" README.md`
on post day and cite section names, not line numbers, in the public post.

## The end-to-end trace: Dropbox's intelligent DNS load balancing

Source verified 2026-08-22 (full text fetched): Nikita Shirokov,
"Intelligent DNS based load balancing at Dropbox", dropbox.tech, 2020-01-08.

The resolution path (the post draws exactly this, four steps):
user -> ISP's recursive resolver -> authoritative DNS (NS1 for dropbox.com)
-> IP answer -> back through the resolver. The authoritative server never
sees the user's IP - only the resolver's (ECS exists but "still not widely
used" per the post). Every DNS-based routing decision is therefore made
about the resolver, not the user. That is the design constraint the whole
system dances around.

What Dropbox built on that constraint (all verified in the fetched text):

1. Geo-routing v1: send users to the geographically nearest of "more than 20
   edge clusters". Failure mode shown: Vladivostok users routed to Tokyo at
   **300-400ms p75 RTT** because Russian ISPs interconnect in western Russia.
2. Discovery trick worth stealing: the desktop client queries **random
   subdomains** of dropbox.com, forcing cache-miss lookups, which lets Dropbox
   join (client subnet <-> resolver <-> measured latency per PoP).
3. The map: subnet -> PoP labels serialized as JSON, uploaded to NS1 per
   record; latency-based instead of geography-based.
4. Measured outcome: **10-15% p75/p95 latency improvement** overall;
   Vladivostok **300-400ms -> ~150ms** (rerouted to Frankfurt); Iceland
   10-15% (Oslo -> Amsterdam, submarine cable topology); Egypt ~10%
   (Milan -> Paris). Distribution: ~10% of users gained ~2ms, 1% gained
   ~20ms, the long tail 200ms+.

The one design decision worth stealing (committed outline item 3): route on
measured latency, not geographic distance - and ship the routing table as
data (a JSON map regenerated from telemetry), not as config someone edits.

## Post skeleton

Hook (committed): theory posts everywhere; today where it actually lives.
Beat 1: the section map (what a good curated index gives you: primary
engineering sources, not summaries). Beat 2: the Dropbox trace. Beat 3: the
stolen decision. Close: tonight's snippet walks the same resolution path
with raw packets on your own machine.

CTA (committed): "Save this for your next design review."

## Numbers audit

- 73,458 stars / push date - GitHub API 2026-08-22, re-check day-of ✓
- 20+ edge clusters, 300-400ms -> ~150ms, 10-15% p75/p95, 2ms/20ms/200ms
  distribution, Iceland/Egypt reroutes - Dropbox post, verified 2026-08-22 ✓
- "authoritative never sees the user IP; ECS not widely used" - same source ✓
