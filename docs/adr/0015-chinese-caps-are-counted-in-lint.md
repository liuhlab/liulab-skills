---
search:
  exclude: true
---

# Chinese length caps are counted in lint, not in vale

A Chinese agent-facing file is capped in CJK codepoints by a check in `tests/lint.sh`: 1000
for a `SKILL.md`, 2000 for a page under `references/`. A file counts as Chinese when its CJK
codepoints outnumber its ASCII letters. `.vale.ini` and `styles/Lab/` are untouched, and
`[tool.liulab.agent-docs]` keeps its existing section pairing, so conformance rule 3 still
holds.

## Why not a vale rule

Vale's `words` formula cannot measure Chinese. It reads a run of characters between two
full-width commas as one word. Measured on this repo's own configuration, with the cap
lowered to force the count: 420 Chinese characters report as 40 words, 1260 as 120, 4200 as
400. A Chinese `SKILL.md` would therefore pass the 600-word cap at roughly 6000 characters,
about ten times the English budget. Worse, the ratio tracks punctuation density rather than
length, so no single adjusted number would hold across two pages.

Vale has no CJK word segmenter to swap in, and the `metric` rules it does offer count the
same broken units. So the choice was a second counter or a cap that silently does not apply.

## What it costs

- Two places now cap a file, and a reader has to know which one applies. `docs/agents/writing.md`
  says so in the same section as the word caps.
- The 1000 and 2000 figures come from the English caps scaled by a rough 1.6 characters per
  word. They are dials, set once and not measured against a corpus of Chinese skills, because
  there is one Chinese skill. Raise them the way the word caps are raised: deliberately, with
  the reason in the commit message.
- The Chinese check reads every `SKILL.md` and reference page on each run. It is standard
  library and runs in well under a second, so the gate's cost does not change.

## What this does not reverse

The word caps in `docs/agents/writing.md` stand for every English file, and still apply to a
Chinese one, where they never fire. ADR 0002's split between facts and recipes is untouched.
