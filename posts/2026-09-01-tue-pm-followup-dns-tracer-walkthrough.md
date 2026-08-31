# Week 2 · Tue 2026-09-01 · 17:00 · Follow-up: Reading the Resolution Path in Raw Bytes

> Calendar row: W2 Tue PM, 17:00 (CSV row `27:2`). Format: repo walkthrough.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/binhnguyennus/awesome-scalability.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: point to the exact file
> in the source repo that implements DNS resolution paths and read every line |
> trace one path through the code end to end, recomputing the real values |
> name the one line that is an honest tradeoff, not a bug.
> Committed CTA: "Follow along - this series runs all week."
>
> **Format honesty note, carried forward from `prep/week-02/tue-2026-09-01-repo-walkthrough.md`.**
> The committed CSV row asks for a file in `binhnguyennus/awesome-scalability`
> that implements DNS resolution. No such file exists. That repository is a
> curated index of engineering write-ups, not a codebase, and pretending
> otherwise would be the exact failure this series is supposed to avoid. The
> post therefore does two honest things instead of one dishonest one: it reads
> the index as an index and says what that is worth, then walks a real
> implementation that is committed in *this* repository at
> `prep/week-02/code/dns_path_tracer.py`. The same resolution applies here
> that `prep/README.md` recorded for the W1 Tuesday source mismatch.
>
> Sources verified 2026-09-01:
> - `github.com/binhnguyennus/awesome-scalability`, GitHub API: 73,628 stars,
>   last push 2026-01-04, not archived. README fetched today; DNS entries
>   confirmed at lines 551 to 556 under the `## Availability` heading
>   (line 515), inside the Load Balancing list.
> - `prep/week-02/code/dns_path_tracer.py`, 187 lines, committed in this
>   repository, Python 3.8+ standard library only, no third-party imports.
>   Every excerpt below is copied from that file unmodified.
> - Two live runs on this machine today, both reproduced in full below.
> - Root server addresses in the script are IANA root hints. `a.root-servers.net`
>   at 198.41.0.4 answered both runs.
>
> Adversarial review record (2026-09-01):
> - The measured hop tables are today's actual stdout, pasted, not retyped.
>   Both runs are labeled as vantage-point-dependent, because RTTs and answer
>   addresses vary by location and by time. A reader in another country will
>   get different numbers and the post says so before showing them ✓
> - The 2026-08-22 prep run recorded 37.1 / 64.4 / 54.8 ms for the same three
>   hops. Today's run recorded 32.2 / 18.6 / 26.8 ms. The prep numbers are not
>   reused anywhere; they are cited only as evidence that RTT is unstable ✓
> - `example.com` resolving to Cloudflare nameservers with two A records and a
>   300 second TTL is today's measurement, not a claim about how example.com
>   is permanently configured ✓
> - The named tradeoff (`resolve_ns_address` falling back to the OS resolver)
>   is argued as a deliberate simplification with its consequence stated, not
>   excused ✓
> - No performance claim is made about the script beyond its measured runtime
>   and its stated bounds (12 hops, 3 second timeout, 3 candidates per hop) ✓
> - **Publication-gap remediation (2026-09-04).** No post in this week's
>   sequence reached readers, so every backward reference to a sibling post
>   was a dangling reference to material nobody had seen. The body now
>   carries the referenced substance inline instead of pointing at it:
>   the four resolution steps enumerated, the resolver-not-user fact stated,
>   and the Vladivostok 300-400 ms example reproduced, rather than alluded to. Written so it reads as a reminder to a sequential reader and as
>   sufficient context to a cold one ✓
> - Zero em dashes.
>
> Companion reference: `posts/2026-09-01-tue-am-essay-dns-resolution-paths.md`
> is this morning's essay. This follow-up assumes the four-step resolution
> path and the resolver-versus-user distinction and does not re-derive them.

---

**Topic:** Performing a DNS resolution path by hand in raw UDP packets, and reading the one deliberate compromise in the implementation

**Subtitle:** Your resolver hides three network round trips behind a single function call, and doing them yourself in 187 lines of standard library changes what you believe about "DNS is slow."

Good evening. This morning we talked about the resolution path as a diagram, and tonight we perform it by hand. If you did not read the morning piece, the diagram is four steps and one uncomfortable fact, and here they are.

1. Your browser needs an IP address for a hostname, so it asks whichever resolver it was configured with, usually your ISP's.
2. That recursive resolver, if it has nothing cached, works its way to the authoritative servers for the zone.
3. The authoritative server answers with an IP address.
4. The resolver hands that address back to you.

The uncomfortable fact is in steps two and three. The conversation that decides which of a company's edge locations you will connect to happens between **your resolver and their server**. You are not in it. The authoritative server never sees your IP address, only your resolver's, which is why every DNS-based traffic steering decision is really a decision about a resolver and the entire crowd of users sitting behind it. Dropbox's engineering blog states this plainly, and this morning's essay traced what it cost them: users in Vladivostok routed to Tokyo because Tokyo is geographically close, with a 75th percentile round trip time of 300 to 400 ms, because their traffic was actually travelling Vladivostok to Moscow, across the Atlantic, across the United States, across the Pacific, and into Japan.

Diagrams are easy to nod along to. So tonight we do it by hand.

## First, an honest word about tonight's repository

The calendar has me pointing you at the exact file in `binhnguyennus/awesome-scalability` that implements DNS resolution, and reading it line by line.

There is no such file. That repository, 73,628 stars as of this morning and last pushed in January, is a curated index. It is a very good one. It is not a codebase, and if I dressed one of its markdown lists up as an implementation to satisfy a calendar row, you should stop reading this series.

So let me tell you what an index like that is actually for, because it is worth something specific.

Under its `## Availability` heading, inside the load balancing list, it collects six DNS entries in a row: traffic steering with RUM DNS at LinkedIn, two Dropbox posts on their edge network and their intelligent DNS balancing, DNS monitoring at Stripe, a three-part multi-DNS migration at Monday, and dynamic anycast DNS at Hulu.

That is not a tutorial and it does not want to be. It is six teams who ran this in production writing down what happened, sitting next to each other so you can see the shape of the problem across all of them. This morning's essay came out of one of those six. An index that reliably points at primary engineering sources is more useful than a hundred summaries of them, and the correct way to use it is to leave it immediately for the thing it pointed at.

The code, then, has to come from somewhere else. It comes from this repository, and it is 187 lines.

## What we are building and why it is not a wrapper

`prep/week-02/code/dns_path_tracer.py` does the resolution walk in the open. No DNS library. Raw packets built with `struct`, sent over UDP to port 53, parsed by hand, with recursion explicitly turned off so that no resolver anywhere will do the work on our behalf.

That last part is the whole point. If you call `socket.gethostbyname` you learn one thing: how long your ISP's cache took to answer. The path this morning's essay described is invisible to you, because hiding it is precisely what a recursive resolver is for.

Standard library only, Python 3.8 or newer. It needs outbound UDP on port 53, which some corporate networks block, and it is bounded on purpose: a maximum of 12 hops, a 3 second timeout per query, and at most 3 candidate servers tried per hop.

## Reading it, in the order the packet is built

**Encoding the name.** DNS does not send `dropbox.com` as a string. It sends length-prefixed labels.

```python
def encode_name(name):
    """example.com -> b'\x07example\x03com\x00'"""
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode()
        assert 0 < len(raw) < 64, f"invalid label: {label!r}"
        out += bytes([len(raw)]) + raw
    return out + b"\x00"
```

Seven, then `example`. Three, then `com`. Then a zero byte meaning the name is over. The assertion is not decoration: a label longer than 63 bytes cannot be represented, because the top two bits of that length byte are reserved, and you are about to see what they are reserved for.

**Building the query.** Twelve bytes of header, then the name, then the type and class.

```python
def build_query(name, qtype, txid):
    header = struct.pack(">HHHHHH", txid, 0x0000, 1, 0, 0, 0)  # RD=0: iterative
    return header + encode_name(name) + struct.pack(">HH", qtype, 1)
```

**This is the first line people get wrong.** That `0x0000` is the flags field, and the bit that matters is Recursion Desired. Setting it to zero is what makes this an iterative walk. Flip it to 1, point the script at your ISP's resolver, and it will cheerfully hand you an answer in one hop, and you will have measured nothing except a cache lookup. Every DNS tracing tool that produces suspiciously fast, suspiciously boring output has this bit set.

**Parsing names back out, including the trick.**

```python
def parse_name(msg, offset):
    """Decompress a DNS name; returns (name, next_offset). Pointer-safe."""
    labels, jumps, next_offset = [], 0, None
    while True:
        assert offset < len(msg), "name parse ran past message end"
        length = msg[offset]
        if length & 0xC0 == 0xC0:  # compression pointer
            if next_offset is None:
                next_offset = offset + 2
            pointer = struct.unpack(">H", msg[offset:offset + 2])[0] & 0x3FFF
            offset = pointer
            jumps += 1
            assert jumps <= 20, "compression pointer loop"
            continue
        if length == 0:
            if next_offset is None:
                next_offset = offset + 1
            return ".".join(labels), next_offset
        offset += 1
        labels.append(msg[offset:offset + length].decode("ascii", "replace"))
        offset += length
```

**This is the second line people get wrong**, and it is the `length & 0xC0` branch.

DNS messages compress repeated names by pointing backwards. If a response mentions `.com` thirteen times, it writes it once and then refers to that offset. Those two reserved bits in the length byte are the flag: both set means the next fourteen bits are an offset into the message rather than a label length.

Here is why it matters practically. A parser that skips this works perfectly on the toy query you tested with, and then explodes the first time it meets a real response from a gTLD server, because those referrals arrive with thirteen name server records that are heavily compressed. The `jumps <= 20` assertion is there because a malicious or broken packet can point a name at itself, and an unbounded follow is an infinite loop in your parser.

Note also that the function tracks `next_offset` separately from `offset`. Once you have jumped, where you continue reading is not where you ended up. Getting that wrong produces a parser that appears to work and silently misreads every record after the first compressed name.

**One query, timed.**

```python
def query(server_ip, name, qtype, rng):
    txid = rng.randrange(0x10000)
    packet = build_query(name, qtype, txid)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT_S)
        start = time.perf_counter()
        sock.sendto(packet, (server_ip, 53))
        data, _ = sock.recvfrom(4096)
        rtt_ms = (time.perf_counter() - start) * 1000
    return parse_response(data, txid), rtt_ms
```

The transaction ID is random, and `parse_response` asserts that the reply carries the same one back. That check is the only thing standing between this script and accepting a forged UDP packet from anyone who can guess what we asked. It is also, historically, the thin thread that DNS cache poisoning attacks were built around pulling. Sixteen bits is not very many.

**The loop.** Start at the roots. Ask. If the answer contains an A record, we are done. If it contains a CNAME, restart from the roots with the new name. Otherwise, read the referral out of the authority section, find addresses for those name servers in the additional section, and go again.

That additional section has a name worth knowing: **glue**. When `com`'s servers tell you that `dropbox.com` is handled by `ns-564.awsdns-06.net`, you now need an address for that name, which is itself a DNS lookup, which would need a lookup. Glue is the referral shipping the addresses alongside the names so the recursion terminates.

## The run, tonight, on this machine

Numbers first, then the warning. Your output will differ. Round trip times depend on where you are sitting, and the answer addresses depend on where you are sitting and when you asked. That variability is the subject, not a defect.

```
tracing resolution path for 'dropbox.com' (iterative, RD=0)

  [hop 1] a.root-servers.net (root) 198.41.0.4    32.2ms  -> referral to 'com' (13 NS, 6 glue)
  [hop 2] l.gtld-servers.net 192.41.162.30    18.6ms  -> referral to 'dropbox.com' (4 NS, 1 glue)
  [hop 3] ns-564.awsdns-06.net 205.251.194.52    26.8ms  -> ANSWER
           dropbox.com A 162.125.248.18 (ttl 60)

done in 3 authoritative hops - this is the path your
resolver walks on a cold cache, then hides behind its TTLs
```

Three hops, about 78 ms of network time, to answer a question your browser appears to answer instantly.

Read the referral counts. Hop one returned 13 name server records for `com` with 6 glue addresses. Hop two returned 4 name servers for `dropbox.com` with 1 glue address. Those are not round numbers someone chose for a diagram, they are what the internet actually handed back at 11:54 this morning.

And look at the last line, because this is where tonight meets this morning: **ttl 60**.

Sixty seconds. That is the number I promised you in the essay. Dropbox steers traffic by handing different users different IP addresses, and that steering only works if resolvers come back and ask again. A 60 second TTL is them buying reaction time and paying for it in query volume at their authoritative tier. Every DNS-based load balancing scheme in existence is making some version of that trade.

Now a second domain, so you have something to check your own setup against:

```
tracing resolution path for 'example.com' (iterative, RD=0)

  [hop 1] a.root-servers.net (root) 198.41.0.4    25.8ms  -> referral to 'com' (13 NS, 6 glue)
  [hop 2] l.gtld-servers.net 192.41.162.30    19.4ms  -> referral to 'example.com' (2 NS, 2 glue)
  [hop 3] hera.ns.cloudflare.com 173.245.58.162    16.4ms  -> ANSWER
           example.com A 172.66.147.243 (ttl 300)
           example.com A 104.20.23.154 (ttl 300)
```

Same shape, different everything else. Two name servers instead of four. Two A records instead of one, which is the oldest load balancing mechanism there is, round robin at the record level. And a 300 second TTL rather than 60, which tells you this name is not being actively steered.

**Self-verification for you:** any domain should finish in three or four hops with an `ANSWER` line. If you get zero hops and a timeout, your network blocks outbound UDP on port 53, which is common on corporate wifi and is itself worth knowing about your own environment.

One more thing worth comparing. The prep notes for this post recorded a run on 2026-08-22 with hop times of 37.1, 64.4 and 54.8 ms. Tonight the same three hops took 32.2, 18.6 and 26.8. Same code, same domain, same machine, less than half the total. Nothing was optimized. That is just what the internet was doing this morning versus that morning, and it is a useful inoculation against anyone who quotes you a single latency measurement as a fact about a system.

## The one line that is an honest tradeoff, not a bug

Here it is:

```python
def resolve_ns_address(ns_name, rng):
    """Glue missing: fall back to the OS resolver for the NS host itself."""
    try:
        return socket.getaddrinfo(ns_name, 53, socket.AF_INET)[0][4][0]
    except socket.gaierror:
        _ = rng
        return None
```

That `getaddrinfo` call is the script quietly using the very thing it exists to avoid.

The situation it handles is real. A referral gives you name server *names*, and glue records give you their addresses, but glue is not always complete. Hop two above returned 4 name servers and only 1 glue address. When we need one of the other three, we have a name and no way to reach it.

A real iterative resolver handles this by resolving that name server's name iteratively too, from the roots, as a nested walk. That is correct, and it introduces a genuinely hard problem: the nested walk can itself hit a missing-glue referral, and now you need cycle detection and a depth budget or you have written a program that can be made to loop forever by a hostile zone.

This script takes the shortcut and asks the operating system. Here is what that costs, stated plainly rather than buried:

- Those particular lookups are **not** measured. They do not appear as hops. So if a trace ever depends on this path, the printed round trip times understate the real work.
- It reintroduces cache dependence at exactly one point. The OS resolver may answer that sub-lookup from cache.

Why is that a tradeoff and not a bug? Because the script's purpose is to make the *primary* delegation chain visible and measurable, and it does that with complete honesty on every hop it prints. Adding full nested resolution would roughly double the code and add the one class of bug, unbounded recursion on hostile input, that a teaching artifact should not be quietly shipping. The compromise is scoped, it is documented in the function's own docstring, and its effect is a possible undercount rather than a wrong answer.

That is the distinction I would ask you to carry into code review generally. A bug is behavior nobody chose. A tradeoff is a cost someone chose, wrote down, and bounded. The line above is the second thing. The way you tell them apart is whether the consequence is stated anywhere.

## Run it against something you own

The whole file is committed at `prep/week-02/code/dns_path_tracer.py`. Point it at a hostname you are responsible for:

```
python3 dns_path_tracer.py your-domain.example
```

Then read three things off the output. How many hops. How many name servers and how much glue your delegation actually returns. And your TTL, because after this morning you know that number is your traffic steering reaction time, and after tonight you have watched the packet that carries it.

Follow along, this series runs all week.

---

*Tomorrow, 09:00: the write path. What Facebook's memcache deployment chose between cache-aside and write-through, why they delete cached data instead of updating it, and what that decision cost them in machinery.*
