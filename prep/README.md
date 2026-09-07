# Prep pack · Weeks 1-3 (2026-08-23 → 2026-09-12)

> **Internal working notes. Not a citable source (AGENTS.md, 2026-09-06).**
> The tables below record that external repositories and pages were inspected
> while researching. Under the canonical source rule, no article may name,
> link, or quote an external code repository. These logs exist so that a claim
> made in an article can be traced back to what was actually read; they are
> not a licence to cite any of it. Papers, RFCs and first-party vendor
> documentation listed here remain citable in articles. External repositories
> listed here do not.

Production materials for the Tuesday repo walkthroughs, Wednesday case
studies and Thursday YouTube tutorials of the first two calendar weeks
(pillar: System Design Fundamentals, pass: Foundations). Prepared
2026-08-22. Every number in these documents is either verified against a
named source on a stated date, or measured by a seeded script committed in
this directory.

## Index

| Slot | Prep document | Code artifact (runnable, verified) |
|---|---|---|
| W1 Tue 08-25 AM · concept essay | `week-01/tue-2026-08-25-repo-walkthrough.md` (concept beats) | - |
| W1 Tue 08-25 PM · code walkthrough | `week-01/tue-2026-08-25-repo-walkthrough.md` | `consistent-hashing.py` (in clone); retained: `consistent_hashing_vnodes_snippet.py` |
| W1 Wed 08-26 AM · case study (concept) + PM code | `week-01/wed-2026-08-26-case-study.md` | `week-01/code/dynamo_quorum_snippet.py` |
| W1 Thu 08-27 AM · YouTube tutorial (+PM checklist) | `week-01/thu-2026-08-27-youtube-tutorial.md` | `week-01/code/lb_algorithms_demo.py` |
| W2 Tue 09-01 AM · walkthrough | `week-02/tue-2026-09-01-repo-walkthrough.md` | - |
| W2 Tue 09-01 PM · snippet | `week-02/tue-2026-09-01-pm-snippet.md` | `week-02/code/dns_path_tracer.py` |
| W2 Wed 09-02 AM · case study (+PM listicle) | `week-02/wed-2026-09-02-case-study.md` | - |
| W2 Thu 09-03 AM · YouTube tutorial (+PM checklist) | `week-02/thu-2026-09-03-youtube-tutorial.md` | `week-02/code/cache_eviction_demo.py` |
| W3 Sun 09-06 AM · theme kickoff | (written direct to `posts/`) | `experiments/week-03/vocab_vs_tokens.py` |

The week-1 and week-2 scripts: Python 3.8+ stdlib only, deterministic where
applicable (seed 42), assertions encode each post's claims. Run them; if an
assertion fails, the post's claim died and the post must change.

From week 3 the artifacts live outside `prep/`, because they are now published
material rather than working notes: reusable code in `lib/`, its tests in
`tests/`, frozen data in `data/`, and one-off measurements in `experiments/`.
Everything is standard library only, so a reader runs it with no install step.
`experiments/week-03/vocab_vs_tokens.py` exits 0 with "All assertions passed"
and takes about a minute; `python3 -m unittest discover -s tests -t .` runs 101
tests. Both were green on 2026-09-06.

## Repo verification log (GitHub API, 2026-08-22 - re-check day-of)

| Repo | Stars | Last push | Archived |
|---|---|---|---|
| ashishps1/awesome-system-design-resources | 40,837 | 2026-02-16 | no |
| binhnguyennus/awesome-scalability | 73,458 | 2026-01-04 | no |
| karanpratapsingh/system-design | 45,711 | 2026-07-08 | no |
| donnemartin/system-design-primer | 365,438 | 2026-03-20 | no |
| ByteByteGoHq/system-design-101 | 87,418 | 2025-04-04 | no |

Week-3 repos: **none**. As of 2026-09-06 the canonical source rule replaced
external repository sourcing entirely. Week 3's code spine is this repository:
`lib/linalg.py`, `lib/bpe.py`, `lib/attention.py` and
`lib/consistent_hashing.py`, covered by `tests/`, with the corpus in
`data/week-03/` and the measurement in `experiments/week-03/`.

Local shallow clones live in `repos/` (gitignored). Re-clone with:
`git clone --depth 1 https://github.com/<owner>/<repo>.git repos/<repo>`

## External source verification log (2026-08-22)

| Source | Status | Used for |
|---|---|---|
| allthingsdistributed.com/2007/10/amazons_dynamo.html (Dynamo, SOSP'07) | verified, full text fetched | W1 Wed case study |
| usenix.org NSDI'13 nishtala page (Scaling Memcache at Facebook) | verified: abstract, BibTeX, open-access PDF link, Piatek summary | W2 Wed case study (paper BODY not yet read - pull PDF before quoting body numbers) |
| dropbox.tech "Intelligent DNS based load balancing" (Shirokov, 2020-01-08) | verified, full text fetched | W2 Tue walkthrough trace |
| medium.com Vimeo bounded-load consistent hashing | HTTP 403 on fetch | EXCLUDED - not cited anywhere |

## External source verification log (2026-09-06, week 3)

| Source | Status | Used for |
|---|---|---|
| arXiv:1706.03762v7 "Attention Is All You Need" | verified, full text read | W3 Sun kickoff, Mon self-attention, Tue multi-head |
| arXiv:1508.07909v5 Sennrich et al., subword units | verified, full text read | W3 Sun kickoff, Wed BPE |
| arXiv:2104.09864v5 Su et al., RoFormer / RoPE | verified, abstract and intro read | W3 Sun kickoff, Fri RoPE |
| arXiv:2002.04745v2 Xiong et al., layer normalization | verified, abstract read | W3 Sun kickoff, Sat weekend challenge |
| huggingface.co/openai-community/gpt2 `config.json` | verified, fetched: vocab_size 50257, n_embd 768, n_layer 12, n_head 12, n_positions 1024 | W3 Sun kickoff, Thu embeddings |

## Resolved editorial decision (W1 Tue + Wed day split)

The committed W1 Tue brief paired PACELC with
`ashishps1/awesome-system-design-resources`, and PACELC appears nowhere in
that repo (grep over full clone, 2026-08-22). **Resolved Option A**
(2026-08-23): keep the repo, walk its real `implementations/`
consistent-hashing code. **Day split** (2026-08-26): Tuesday and Wednesday
both run concept in the morning, code in the evening. Tue AM = the ring's
mental model (code-free); Tue PM = the 79-line code walkthrough; Wed AM = the
Dynamo case study (concept); Wed PM = a runnable preference-list + quorum
snippet. Calendar rows 12-15 (titles/hooks/formats) were edited to match. The
rejected Option B was to keep PACELC and swap the AM source to
karanpratapsingh/system-design (chapter verified at README L1586).

The PACELC quorum snippet (`week-01/code/pacelc_quorum_snippet.py`) is no
longer orphaned: its quorum mechanism (R + W > N) is exactly Dynamo's
(3,2,2), so it feeds Wednesday's code evening (`dynamo_quorum_snippet.py`).
PACELC itself remains a recurring pillar topic (e.g. week 62) and is covered
in prose by Monday's CAP essay.

## Standing rules for writing from this pack

1. Re-verify repos (API) and re-run every script on posting day; measured
   numbers must be regenerated, not remembered.
2. Line numbers into cloned repos drift - re-grep before citing; prefer
   section names in public copy.
3. Nothing from the EXCLUDED row appears in any post under any framing, and
   from 2026-09-06 no external repository appears in any post either.
4. Thursday videos: record only after the same-day demo run prints
   "All assertions passed".
