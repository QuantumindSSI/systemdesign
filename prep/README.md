# Prep pack · Weeks 1-2 (2026-08-23 → 2026-09-05)

Production materials for the Tuesday repo walkthroughs, Wednesday case
studies and Thursday YouTube tutorials of the first two calendar weeks
(pillar: System Design Fundamentals, pass: Foundations). Prepared
2026-08-22. Every number in these documents is either verified against a
named source on a stated date, or measured by a seeded script committed in
this directory.

## Index

| Slot | Prep document | Code artifact (runnable, verified) |
|---|---|---|
| W1 Tue 08-25 AM · walkthrough | `week-01/tue-2026-08-25-repo-walkthrough.md` | - |
| W1 Tue 08-25 PM · snippet | `week-01/tue-2026-08-25-pm-snippet.md` | `week-01/code/pacelc_quorum_snippet.py` |
| W1 Wed 08-26 AM · case study (+PM listicle) | `week-01/wed-2026-08-26-case-study.md` | - |
| W1 Thu 08-27 AM · YouTube tutorial (+PM checklist) | `week-01/thu-2026-08-27-youtube-tutorial.md` | `week-01/code/lb_algorithms_demo.py` |
| W2 Tue 09-01 AM · walkthrough | `week-02/tue-2026-09-01-repo-walkthrough.md` | - |
| W2 Tue 09-01 PM · snippet | `week-02/tue-2026-09-01-pm-snippet.md` | `week-02/code/dns_path_tracer.py` |
| W2 Wed 09-02 AM · case study (+PM listicle) | `week-02/wed-2026-09-02-case-study.md` | - |
| W2 Thu 09-03 AM · YouTube tutorial (+PM checklist) | `week-02/thu-2026-09-03-youtube-tutorial.md` | `week-02/code/cache_eviction_demo.py` |

All four scripts: Python 3.8+ stdlib only, deterministic where applicable
(seed 42), assertions encode each post's claims. Run them; if an assertion
fails, the post's claim died and the post must change.

## Repo verification log (GitHub API, 2026-08-22 - re-check day-of)

| Repo | Stars | Last push | Archived |
|---|---|---|---|
| ashishps1/awesome-system-design-resources | 40,837 | 2026-02-16 | no |
| binhnguyennus/awesome-scalability | 73,458 | 2026-01-04 | no |
| karanpratapsingh/system-design | 45,711 | 2026-07-08 | no |
| donnemartin/system-design-primer | 365,438 | 2026-03-20 | no |
| ByteByteGoHq/system-design-101 | 87,418 | 2025-04-04 | no |

Local shallow clones live in `repos/` (gitignored). Re-clone with:
`git clone --depth 1 https://github.com/<owner>/<repo>.git repos/<repo>`

## External source verification log (2026-08-22)

| Source | Status | Used for |
|---|---|---|
| allthingsdistributed.com/2007/10/amazons_dynamo.html (Dynamo, SOSP'07) | verified, full text fetched | W1 Wed case study |
| usenix.org NSDI'13 nishtala page (Scaling Memcache at Facebook) | verified: abstract, BibTeX, open-access PDF link, Piatek summary | W2 Wed case study (paper BODY not yet read - pull PDF before quoting body numbers) |
| dropbox.tech "Intelligent DNS based load balancing" (Shirokov, 2020-01-08) | verified, full text fetched | W2 Tue walkthrough trace |
| medium.com Vimeo bounded-load consistent hashing | HTTP 403 on fetch | EXCLUDED - not cited anywhere |

## Open editorial decision (blocks W1 Tue AM copy)

The committed W1 Tue brief pairs PACELC with
`ashishps1/awesome-system-design-resources`, and PACELC appears nowhere in
that repo (grep over full clone, 2026-08-22). The walkthrough prep doc
carries both resolutions - Option A (recommended): walk the repo's real
`implementations/` code (consistent hashing), which chains into Wednesday's
Dynamo case study and Thursday's measurements; Option B: keep PACELC and
swap the source to karanpratapsingh/system-design (chapter verified at
README L1586). Whichever runs, regenerate/edit the calendar row afterward,
same discipline as the launch-week slip.

## Standing rules for writing from this pack

1. Re-verify repos (API) and re-run every script on posting day; measured
   numbers must be regenerated, not remembered.
2. Line numbers into cloned repos drift - re-grep before citing; prefer
   section names in public copy.
3. Nothing from the EXCLUDED row appears in any post under any framing.
4. Thursday videos: record only after the same-day demo run prints
   "All assertions passed".
