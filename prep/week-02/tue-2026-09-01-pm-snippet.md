# Prep · Week 2 · Tue 2026-09-01 · 17:00 · Snippet / config tip

> Calendar row: W2 Tue PM. Committed title: "A working snippet for DNS
> resolution paths (foundations)". Committed outline: minimal runnable snippet |
> the two lines people get wrong | expected output for self-verification.

## The snippet

Committed, runnable, verified live 2026-08-22:
`experiments/week-02/dns_path_tracer.py` (187 lines, stdlib only, needs
outbound UDP/53). An iterative resolver in the open: raw DNS packets built
with `struct`, RD=0, root -> TLD -> authoritative, every hop printed with
its RTT. It is the cold-cache path from the morning's Dropbox diagram,
performed by hand.

## Verified run (this machine, 2026-08-22 - RTTs and answer IPs WILL differ per vantage point and time; say so in the post)

```
tracing resolution path for 'dropbox.com' (iterative, RD=0)

  [hop 1] a.root-servers.net (root) 198.41.0.4    37.1ms  -> referral to 'com' (13 NS, 6 glue)
  [hop 2] l.gtld-servers.net 192.41.162.30        64.4ms  -> referral to 'dropbox.com' (4 NS, 1 glue)
  [hop 3] ns-564.awsdns-06.net 205.251.194.52     54.8ms  -> ANSWER
           dropbox.com A 162.125.248.18 (ttl 60)
```

Self-verification for readers: any domain should resolve in 3-4 hops ending
in an `ANSWER` line; `example.com` is a good second test. A 60-second TTL on
dropbox.com is itself a talking point: short TTLs are what make DNS-based
load balancing (the AM post) steerable.

## The two lines people get wrong

1. `header = struct.pack(..., 0x0000, ...)` - flags = 0 means **RD=0**, no
   recursion desired. Set RD=1 and any resolver will happily do the whole walk
   for you, and you will have measured nothing but your ISP's cache.
2. The compression pointer branch in `parse_name` (`length & 0xC0`): DNS
   packets reference earlier names by offset. Skip this and your parser works
   on toy queries and explodes on real gTLD referrals (13 NS records arrive
   heavily compressed).

## Post skeleton

Hook (committed): one copy-pasteable block that makes DNS resolution paths
concrete. Show the run, the two lines, then the operational punchline: your
resolver walks this path once per TTL expiry and hides it the rest of the
time - which is why "DNS is slow" bugs are really "cold cache plus long
path" bugs. Invite readers to run it against their own domain and post hop
counts.

CTA (committed): "Follow along - this series runs all week."

## Numbers audit

- Hop RTTs / IPs / TTL 60 - measured on this machine 2026-08-22, flagged as
  vantage-point-dependent in the copy ✓
- "13 root servers" implied by root referral output ("13 NS") - measured in
  the same run; the script itself ships 4 root addresses from IANA root hints ✓
- No third-party performance claims ✓
