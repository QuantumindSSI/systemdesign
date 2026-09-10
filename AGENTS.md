# Repository instructions

## Canonical source rule (effective 2026-09-06, binding, no exceptions)

This repository, `github.com/QuantumindSSI/systemdesign`, is the only code
repository any article may reference.

- **No external code repository may appear in any file under `posts/`.** Not as
  a link, not as a bare `github.com/owner/name` string, not as a clone command,
  not as "adapted from", and not inside an editorial audit header that a reader
  could see if the header were ever published.
- **Material is authored here first.** When an article needs an implementation,
  a dataset, a diagram source, or a measurement, that artifact is written into
  this repository, committed, and then referenced by its path here. An article
  may not reference an artifact that does not yet exist in this repository at
  the time the article is written.
- **Reference by repository path**, for example `lib/bpe.py` or
  `experiments/week-03/vocab_vs_tokens.py`. Paths must resolve.
- **Primary non-repository sources remain citable and are still required**:
  peer-reviewed and preprint papers (arXiv, ACM, USENIX), standards documents
  (RFCs), and first-party vendor documentation. The numerical grounding rule is
  unchanged: every number names its source inline, is flagged unaudited at the
  point of use, or is cut.
- **The CSV `source` column is an internal routing hint, never a citation.**
  `content_calendar.csv` names an external repository for most of its 1,406
  rows. Those strings exist to indicate the topic area for brief generation.
  They must never be reproduced in an article.
- **The `repo walkthrough` format means our repository.** 100 calendar rows use
  it. Each one walks an implementation committed here, line by line, not
  somebody else's code.
- **`prep/` verification logs are internal working notes.** They may record that
  an external repository was inspected while researching. Nothing in `prep/` is
  a citable source for an article.

Third-party *packages* installed as tooling are not "source repositories" and
are not banned by this rule, but prefer the Python standard library so readers
can run artifacts with no install step.

## The two repositories (effective 2026-09-10, binding)

`QuantumindSSI/systemdesign` is the working repository. It holds everything:
posts with their editorial audit headers, `prep/` working notes, `tools/`,
`AGENTS.md`, and the content calendar. It is where articles are written and
where the gates run.

`QuantumindSSI/Technologues` is the reader-facing repository. Readers are given
this one and only this one. It carries the articles as reader-facing copy plus
the code needed to run them, which means `posts/`, `lib/`, `tests/`, `data/`,
and `experiments/`. It never carries `AGENTS.md`, `prep/`, `tools/`, or
`content_calendar.csv`.

It is built by `tools/publish_public.py`, never edited by hand, because hand
edits would drift from the working repository and could not be verified. The
script performs three transformations and refuses to finish if any check fails:

- Each post is cut to its reader-facing copy. The level-one heading survives as
  the article title, the editorial audit block below it is discarded, and
  everything below the first `---` marker is kept verbatim. Discarding the
  audit block is also what removes every `prep/` reference, so those references
  stay legal in the working repository.
- Every embedded `systemdesign` URL is rewritten to `Technologues`, so a link a
  reader clicks resolves inside the repository they are already reading.
- `README.md` is regenerated as the public index.

The published tree is then verified: no excluded path present, no excluded
string surviving in published text, no unrewritten source URL, and every
embedded link resolving to a file that exists. A failure exits non-zero and
nothing is pushed.

Publishing starts at 2026-09-10. Earlier posts and earlier weeks of
`experiments/` are consolidated into the public repository as a separate,
deliberate decision, by widening `--since` and `EXPERIMENT_WEEKS`.

Writing continues to target the working repository. An article still embeds
`systemdesign` URLs, and the publisher rewrites them on the way out, so the
canonical source rule above is unchanged.

## Publication rules (effective 2026-09-06, binding, no exceptions)

Enforced mechanically by `tools/publication_gate.py`. Run it before every push.
It exits 0 only when all four rules pass.

**Artifacts are pushed during prep, and the article embeds the pushed link.**
While preparing a post, its public-facing artifacts are written, tested, and
pushed to this repository first. The article then embeds the resolvable URL,
never a bare path:

```
[`lib/bpe.py`](https://github.com/QuantumindSSI/systemdesign/blob/main/lib/bpe.py)
```

A link in a published article that 404s is worse than no link, so the gate
checks that every embedded URL resolves to a path that exists (R2).

**Public artifact trees**, safe to push, are what articles may link:
`lib/`, `tests/`, `data/`, `experiments/`, `tools/`.
**Internal trees**, never citable from an article: `prep/` (working notes).

**No post is available ahead of its post day.** A file under `posts/` dated
later than today must not be tracked by git, because tracked means pushed and
pushed means public. Write it, leave it unstaged, stage it on its day (R1).

**This repository is where readers read the series.** `README.md` is the front
door and is generated by `tools/build_index.py` from the files themselves, so
it cannot drift. It lists only articles whose day has arrived. Regenerate it
after staging each day's posts; `--check` fails if it is stale.

**Nothing invites a reader to read ahead.** Reader-facing copy, meaning
everything below the editorial `---` marker, must not contain a read-ahead
invitation and must not point at a post that has not published yet.

Pointing a reader at an **already published** article of ours is the intended
use of this repository and is encouraged: embed it as a resolvable URL, the
same form used for artifacts. "Already published" means dated strictly earlier
than the referring post. A same-date reference counts as forward, because the
09:00 post precedes the 17:00 post and a filename carries no time; refer to the
same day's other slot in prose ("This evening, 17:00: ..."). Audit headers
above the marker are internal and may reference any post by path (R3).

This applies retroactively and going forward. Forward teasers naming the next
post's topic are fine; anything pointing at where to obtain it early is not.

**What the external repositories in `content_calendar.csv` are.** They are the
research backing that informed a topic, and they stay exactly as they are. They
are never rewritten, and they are never shown to a reader. If a reader needs to
see an implementation, we write it here.

## Human-first article voice

Apply this rule to every reader-facing article and follow-up under `posts/`:

- Immediately below the editorial `---` marker, include a Substack-style
  title block with exactly `**Topic:** <clear subject>` and `**Subtitle:**
  <one-sentence reader promise>`. The topic should be specific and scannable;
  the subtitle should add the human stakes, concrete outcome, or useful tension
  instead of restating the topic.
- Write as a thoughtful person speaking with the reader, not as a detached
  technical reference.
- Open with a natural greeting, check-in, or familiar everyday moment.
- Carry the relationship through every major section with reader-facing
  transitions and concrete daily analogies. A friendly introduction alone is
  not enough.
- Follow each relatable frame with the precise technical mechanism. Never
  weaken citations, measurements, caveats, or numerical rigor for tone.
- Close by reconnecting the lesson to a decision, problem, or experience the
  reader is likely to recognize.
- Keep the warmth natural. Do not invent personal stories, force slang, or
  repeat the same greeting mechanically. The writer-POV rule below governs the
  one narrow case where a first-person memory is permitted.

Preserve the editorial audit header above the `---` marker. The topic,
subtitle, and human-first voice belong to the reader-facing copy below it.

## Prose style rules (binding on every article and follow-up)

These seven rules apply automatically to every reader-facing rewrite and every
new article. They are not restated per request.

**1. Human-centred narrative voice.** Frame a technical explainer as prose told
through a person's experience of the mechanism, rather than as a systems-design
brief describing the mechanism in the abstract.

**2. Writer-POV analogies, author-supplied only.** Thread the author's own
first-person memories through the piece, mapped onto the technical concepts, in
place of generic or hypothetical comparisons. Each analogy earns its place at
the exact point its matching concept appears, and the frame both opens and
closes the piece.

The agent may extend, re-apply, or find new mappings for a memory the author
has already supplied or approved. The agent may never fabricate a memory, nor
invent the specifics of one it knows only by label. Where a piece needs a frame
and no approved memory fits, propose candidates and wait. This is the single
exception to "do not invent personal stories" above, and it is an exception
only for memories that came from the author.

Approved memories, with the post that uses each:
- wedding seating card: `posts/2026-09-10-thu-am-tutorial-embedding-layers.md`,
  `posts/2026-09-10-thu-pm-followup-embedding-mistakes-checklist.md`

**3. No em dashes.** Zero, anywhere, in any piece. This restates C-08 of the
persona constitution and carries the same zero tolerance.

**4. No sentence begins with a conjunction.** "And", "But", "So", "Or",
"Because", "Yet", and "Nor" never open a sentence, headings included. Rewrite so
the sentence leads with its own subject.

**5. No "not X, it's Y" antithesis.** Collapsed contrastive framing such as "not
small, zero" or "not a bug, a constraint" is rewritten as a direct
single-direction statement, so the reasoning reads as one continuous thought
rather than a sequence of self-corrections.

**6. Cognitive-flow punctuation.** Plain commas and periods carry the logic in
sequence, cause then effect then cost. Dashes and staged reversals do not do
that work.

**7. Technical content is preserved exactly.** Code blocks, data tables, exact
figures, and cited claims stay verbatim, or are paraphrased only lightly for
flow. They are never altered and never invented, because they are the evidence
the piece rests on. A style rewrite that changes a number is a failed rewrite.

Rules 3, 4, and 5 are mechanically checkable and should be verified by grep over
the reader-facing copy before any post is staged.
