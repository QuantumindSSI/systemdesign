"""Trace a DNS resolution path by hand: root -> TLD -> authoritative.

Companion snippet for the week-2 Tuesday PM post (2026-09-01, 17:00):
"A working snippet for DNS resolution paths".

Your stub resolver hides three network round trips behind one call.
This script performs them in the open, with no DNS library: raw DNS
packets over UDP, built and parsed with struct. It queries a root
server, follows the referral to the TLD servers, follows that to the
domain's authoritative servers, and prints every hop with its RTT.
This is the resolution path your recursive resolver walks on a cold
cache (the same path drawn in Dropbox's DNS load balancing post).

Run:      python3 dns_path_tracer.py [hostname]   (default: dropbox.com)
Depends:  Python 3.8+ standard library. Needs outbound UDP port 53.
Bounds:   max 12 hops, 3s timeout per query, 3 server candidates per hop.
"""

import random
import socket
import struct
import sys
import time

ROOT_SERVERS = [  # 4 of the 13 root server addresses (IANA root hints)
    ("a.root-servers.net", "198.41.0.4"),
    ("b.root-servers.net", "170.247.170.2"),
    ("c.root-servers.net", "192.33.4.12"),
    ("d.root-servers.net", "199.7.91.13"),
]
QTYPE_A, QTYPE_NS, QTYPE_CNAME = 1, 2, 5
MAX_HOPS = 12
TIMEOUT_S = 3.0


def encode_name(name):
    """example.com -> b'\\x07example\\x03com\\x00'"""
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode()
        assert 0 < len(raw) < 64, f"invalid label: {label!r}"
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def build_query(name, qtype, txid):
    header = struct.pack(">HHHHHH", txid, 0x0000, 1, 0, 0, 0)  # RD=0: iterative
    return header + encode_name(name) + struct.pack(">HH", qtype, 1)


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


def parse_records(msg, offset, count):
    records = []
    for _ in range(count):
        name, offset = parse_name(msg, offset)
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", msg[offset:offset + 10])
        offset += 10
        rdata_raw = msg[offset:offset + rdlen]
        if rtype == QTYPE_A and rdlen == 4:
            rdata = ".".join(str(b) for b in rdata_raw)
        elif rtype in (QTYPE_NS, QTYPE_CNAME):
            rdata, _ = parse_name(msg, offset)
        else:
            rdata = rdata_raw.hex()
        offset += rdlen
        records.append({"name": name, "type": rtype, "ttl": ttl, "data": rdata})
    return records, offset


def parse_response(msg, expected_txid):
    txid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", msg[:12])
    assert txid == expected_txid, "transaction id mismatch"
    rcode = flags & 0x000F
    offset = 12
    for _ in range(qd):  # skip question section
        _, offset = parse_name(msg, offset)
        offset += 4
    answers, offset = parse_records(msg, offset, an)
    authority, offset = parse_records(msg, offset, ns)
    additional, _ = parse_records(msg, offset, ar)
    return {"rcode": rcode, "answers": answers, "authority": authority,
            "additional": additional}


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


def resolve_ns_address(ns_name, rng):
    """Glue missing: fall back to the OS resolver for the NS host itself."""
    try:
        return socket.getaddrinfo(ns_name, 53, socket.AF_INET)[0][4][0]
    except socket.gaierror:
        _ = rng
        return None


def trace(hostname):
    rng = random.Random()  # txids must NOT be predictable; system entropy
    print(f"tracing resolution path for {hostname!r} (iterative, RD=0)\n")
    candidates = [(f"{n} (root)", ip) for n, ip in ROOT_SERVERS]
    for hop in range(1, MAX_HOPS + 1):
        response = None
        for label, ip in candidates[:3]:
            try:
                response, rtt = query(ip, hostname, QTYPE_A, rng)
                break
            except (socket.timeout, AssertionError, OSError) as exc:
                print(f"  [hop {hop}] {label} {ip} failed ({exc}); trying next")
        if response is None:
            print("all candidate servers failed; check UDP/53 egress")
            return 1
        if response["rcode"] == 3:
            print(f"  [hop {hop}] NXDOMAIN from {label} - name does not exist")
            return 1

        a_answers = [r for r in response["answers"] if r["type"] == QTYPE_A]
        cnames = [r for r in response["answers"] if r["type"] == QTYPE_CNAME]
        if a_answers:
            print(f"  [hop {hop}] {label} {ip}  {rtt:6.1f}ms  -> ANSWER")
            for r in a_answers:
                print(f"           {r['name']} A {r['data']} (ttl {r['ttl']})")
            print(f"\ndone in {hop} authoritative hops - this is the path your")
            print("resolver walks on a cold cache, then hides behind its TTLs")
            return 0
        if cnames:
            target = cnames[0]["data"]
            print(f"  [hop {hop}] {label} {ip}  {rtt:6.1f}ms  -> CNAME {target}")
            hostname = target
            candidates = [(f"{n} (root)", ipaddr) for n, ipaddr in ROOT_SERVERS]
            continue

        ns_records = [r for r in response["authority"] if r["type"] == QTYPE_NS]
        if not ns_records:
            print(f"  [hop {hop}] {label} {ip}: no answer and no referral; stopping")
            return 1
        zone = ns_records[0]["name"] or "."
        glue = {r["name"]: r["data"] for r in response["additional"]
                if r["type"] == QTYPE_A}
        print(f"  [hop {hop}] {label} {ip}  {rtt:6.1f}ms  -> referral to "
              f"{zone!r} ({len(ns_records)} NS, {len(glue)} glue)")
        next_candidates = []
        for record in ns_records:
            ns_name = record["data"]
            ip_addr = glue.get(ns_name) or resolve_ns_address(ns_name, rng)
            if ip_addr:
                next_candidates.append((ns_name, ip_addr))
        if not next_candidates:
            print("  referral had no resolvable NS addresses; stopping")
            return 1
        candidates = next_candidates
    print(f"exceeded {MAX_HOPS} hops without an answer; stopping")
    return 1


if __name__ == "__main__":
    sys.exit(trace(sys.argv[1] if len(sys.argv) > 1 else "dropbox.com"))
