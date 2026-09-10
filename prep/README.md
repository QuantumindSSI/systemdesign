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
| W3 Tue 09-08 AM+PM · attention | (written direct to `posts/`) | `experiments/week-03/attention_heads.py`, `attention_trace.py` |
| W3 Wed 09-09 AM · case study | (written direct to `posts/`) | `experiments/week-03/pretoken_boundary.py` |
| W3 Wed 09-09 PM · code deep-dive | (written direct to `posts/`) | `experiments/week-03/bpe_trace.py` |
| W3 Thu 09-10 AM+PM · embeddings | (written direct to `posts/`) | `lib/embedding.py`, `experiments/week-03/embedding_lab.py` |
| W3 Fri 09-11 AM · consolidation | (written direct to `posts/`) | `experiments/week-03/permutation_equivariance.py` |
| W3 Fri 09-11 PM · RoPE, merged | (written direct to `posts/`) | `lib/rope.py`, `experiments/week-03/rope_properties.py` |
| W3 Sat 09-12 AM · recap + quiz | (written direct to `posts/`) | re-quotes week-1 to week-3 artifacts, no new code |
| W3 Sat 09-12 PM · weekend challenge | (written direct to `posts/`) | `lib/layernorm.py`, `experiments/week-03/norm_placement.py` |

The week-1 and week-2 scripts: Python 3.8+ stdlib only, deterministic where
applicable (seed 42), assertions encode each post's claims. Run them; if an
assertion fails, the post's claim died and the post must change.

From week 3 the artifacts live outside `prep/`, because they are now published
material rather than working notes: reusable code in `lib/`, its tests in
`tests/`, frozen data in `data/`, and one-off measurements in `experiments/`.
Everything is standard library only, so a reader runs it with no install step.

Week-3 run log, all on 2026-09-09 unless stated, all exiting 0 with "All
assertions passed", all byte-identical across two runs:

| Artifact | Runtime | stdout md5 |
|---|---|---|
| `experiments/week-03/vocab_vs_tokens.py` | ~1 min | (not captured; token counts unchanged from 2026-09-06) |
| `experiments/week-03/pretoken_boundary.py` | 31 s | `d4dd969b1f118a5a18496c1c6b4a0c7b` |
| `experiments/week-03/bpe_trace.py` | 3 s | `33236832cc519bee4ed0e83b77c32e8b` |
| `experiments/week-03/embedding_lab.py` | <2 s | `36c23c8fab0535cbf8b49e3454e526e7` |
| `experiments/week-03/permutation_equivariance.py` | <2 s | `da5e41c82094fe585cf9759c0420272e` |
| `experiments/week-03/rope_properties.py` | 8 s | `dd346762e3ace54bbf078fec78ad67e5` |
| `experiments/week-03/norm_placement.py` | 4 s | `703197248266bafa4b5323f2d82fd4df` |

`python3 -m unittest discover -s tests -t .` runs 270 tests, green on
2026-09-09. It was 101 on 2026-09-06, 160 before the Wednesday work, and 214
after Thursday's embedding module.

## Publication-gap inventory and disposition (decided 2026-09-09)

Thirteen calendar slots from 2026-08-20 to 2026-09-12 were never written. Four
of those are the Fri 09-11 and Sat 09-12 slots, now written. The remaining
nine are disposed of as follows, and this table is the record so the decision
is not silently reversed.

| Slot | CSV | Disposition |
|---|---|---|
| W3 Mon 09-07 AM, self-attention concept | `38:3` | **Discharged** in Fri 09-11 AM |
| W3 Mon 09-07 PM, self-attention diagram | `39:3` | **Discharged** in Fri 09-11 AM |
| W2 Sat 09-05 quiz answers (owed, not a slot) | - | **Discharged** in Sat 09-12 AM |
| W1 Sat 08-29 AM, week-1 recap | `18:1` | **Recap discharged** in Sat 09-12 AM; its quiz not resurrected, three weeks stale |
| W0 Fri 08-21 AM, the 7-layer map | `4:0` | **Discharged** in Sat 09-12 AM as the closing section |
| W0 Fri 08-21 PM, 28-repo resource roundup | `5:0` | **DEAD PERMANENTLY.** The canonical source rule of 2026-09-06 forbids naming an external code repository in any post. This row cannot be written in any form. Retire it from the calendar rather than rescheduling it. |
| W0 Sat 08-22 PM, baseline before week 1 | `7:0` | Superseded. A pre-week-1 baseline has no audience three weeks in. |
| W1 Sat 08-29 PM, reverse proxies challenge | `19:1` | Deferred, not written. System Design Fundamentals material; placing it in an LLM-internals week would serve the calendar rather than the reader. The pillar recurs later in the 100-week plan. |
| W2 Sun 08-30 AM+PM, week-2 kickoff and poll | `20:2`, `21:2` | Superseded. Week 2 ran and was recapped on 2026-09-05. |

**Slot reassignment, recorded because it changes a pushed promise.** The
committed W3 Fri AM row (`46:3`, contrarian take on RoPE) was moved to the
evening and merged with the W3 Fri PM debate row (`47:3`). The vacated morning
slot carries the two Monday rows. Both topics the pushed Sunday kickoff
promised readers, RoPE on Friday and layer-norm placement on Saturday, are
delivered, so no correction is owed to readers.

**Backward-compatibility note (2026-09-09).** `lib/bpe.py` gained three
alternative pre-tokenizers and a `pre_tokenizer` parameter threaded through
`word_counts`, `train`, `BPETokenizer.__init__` and `encode`. Every default is
unchanged, and `vocab_vs_tokens.py` was re-run to confirm it still prints the
token counts and percentage cuts quoted in the Sunday kickoff. Any future
change to the default boundary rule invalidates that post and must re-measure
it in the same commit.

**Assertions that fired before publication (2026-09-09), kept as evidence the
gate works.** `embedding_lab.py` asserted mean absolute cosine similarity
between untrained rows would be below 0.10; it measured 0.1003 and failed. The
threshold was wrong: random vectors in d dimensions have mean absolute cosine
sqrt(2 / (pi * d)) = 0.0997 at d_model 64, so the claim was rewritten against
that prediction. The same script's related-pair probe originally compared
" cache" with " caches", which share a first token id, so it was scoring a row
against itself at 1.0000; it now refuses to run unless both words are single
tokens with different ids.

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

## External source verification log (2026-09-09, week 3 midweek)

| Source | Status | Used for |
|---|---|---|
| Radford et al., GPT-2, `cdn.openai.com/better-language-models/...pdf` | verified, PDF downloaded and text-extracted with `pdftotext -layout`. Section 2.2 read in full | W3 Wed case study (byte-level base 256 vs "over 130,000"; the `dog. dog! dog?` observation; "prevent BPE from merging across character categories"; the space exception), W3 Thu tutorial (Table 2's four rows, vocabulary 50,257, context 512 to 1,024) |
| arXiv:2305.15425 Petrov, La Malfa, Torr, Bibi, tokenizer unfairness (NeurIPS 2023) | verified, abstract fetched and read | W3 Wed case study, "up to 15 times" and "over 4 times" |

Not used, and the reason recorded so it is not quietly reconsidered: the
paper's `dog. dog! dog?` observation has no published magnitude attached to
it, so no figure was attributed to the paper. The counterfactual in the
Wednesday post is our own measurement on our own corpus and is labelled that
way at every point of use.

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
