---
search:
  exclude: true
---

# Writing rules

Three rules. Two are checked by `vale` inside `pixi run check`; the third is on you.

## 1. Be concise

Shorter beats longer — in documents, issues, commit messages, replies, and skills. If a
sentence survives deletion without loss, delete it. The caps below are ceilings, not
targets.

## 2. Agent-facing documents have word caps

| Files | Cap |
| --- | --- |
| `AGENTS.md` | 300 (`Lab.LengthAgents`) |
| `docs/agents/*`, `upstream/README.md`, `skills/*/references/*`, other pages beside a skill body, `skills/*/playbooks/*` | 1200 (`Lab.LengthDoc`) |
| `skills/*/SKILL.md`, the maintainer-only skill in `.claude/commands/` | 600 (`Lab.LengthSkill`) |
| An adopted skill's pages | none — upstream text passes unchanged (`upstream/README.md`); a lab side page beside them, `*.lab.md`, takes the 1200 cap |
| `docs/adr/*` | 400 (`Lab.LengthAdr`) |
| `GLOSSARY.md` | 200 words per glossary entry, checked by conformance |
| `docs/research/*` | none — a research note is long by nature |

A skill body and the pages behind it are capped apart, because they are different things. The
body is an interface — what must be true before the first tool call — so it gets 600, and a
body that outgrows that is detail belonging in `references/`. The reference pages are this
repo's densest agent-facing prose and keep the document cap; the lab template's
`skills/*/SKILL.md` glob does not reach them at all.

`AGENTS.md` has the tightest cap because every word of it is in context on every turn of
every session. It holds what every task needs and points at the rest. Vale skips table
text, so the cap limits its prose and leaves the read-next rows free to grow.

`GLOSSARY.md` has no file cap. A glossary grows one term at a time and never shrinks, so a
file-level count measures how big the domain is, not how well the entries are written — a
cap set for twenty terms fires again at twenty-five. The per-entry cap is the unit that
matches how the file grows, and it is the only one.

**A Chinese file is capped in characters, not words, and `tests/lint.sh` counts it.** Vale's
`words` counter reads a run of characters between two full-width commas as one word, so a
Chinese page passes the word caps at roughly ten times the English budget. A file whose CJK
codepoints outnumber its ASCII letters takes 1000 characters for a `SKILL.md` and 2000 for a
page under `references/`. Nothing in `.vale.ini` changes; its caps just never fire there. See
`docs/adr/0015-chinese-caps-are-counted-in-lint.md`.

**Measure with the gate, not with `wc`.** `wc -w` counts table pipes, link targets and
shell flags as words; vale does not, and vale is what enforces the cap. The gap scales with
markup — from about 10% on plain prose to 65% on a page that is mostly a table — so `wc`
will tell you a reference page is near a cap it is nowhere near. Run `pixi run vale` and
believe it.

The caps are dials with tight defaults. Raising one is a one-line diff in `styles/Lab/` —
do it deliberately, and say why in the commit message. Do not raise a cap because a
document ran long; that is the cap working.

## 3. Human-facing prose avoids jargon and stays readable

`README.md`, `CHANGELOG.md` and every `docs/` page a person browses: no terms from the lab
jargon list (`Lab.Jargon` — architecture-speak and needlessly Latinate verbs), and reading
grade 11 or below (`Lab.Readability`). No length cap — a tutorial is as long as the task.

**When `Lab.Readability` fails, match a passing exemplar — do not attack the number.** The
grade is a ratio over structure, so shaving words inside sentences you already committed to
moves it by hundredths. Find text that passes — an older section, a sibling page — and
rewrite toward how that text is segmented.

**This rule also covers what you say, not only what you write.** Nothing checks a chat
reply, so it is on you: when a person asks, answer in plain language and explain the term
you would otherwise reach for.

## How `.vale.ini` is arranged

**Every rule is named in every section.** Vale's `*` matches `/`, so the sections overlap
and their settings accumulate, the later section winning. A rule left out of a section
inherits whatever an earlier one said rather than defaulting off, which once left the
decision records checked by nothing on a green gate. Broad section first, narrowest last.

**Every declared file class names its section.** Each key in `[tool.liulab.agent-docs]` is
paired to a section by conformance rule 3, which looks for the key inside a section header
and wants exactly one match. So a new cap is a new section plus a key that no other header
spells — check both directions before you commit, because a key matching two headers fails
the gate and a key matching none is a file class checked by nothing.

## Which is which

Agent-facing means written for a machine that has to act: capped, exempt from the jargon
and readability rules, kept out of the site navigation with both `search: exclude: true`
front matter and absence from `nav:`. Human-facing means written for a person reading the
published site: checked for jargon and reading grade, uncapped. A file is one or the other
— if you are adding a document and cannot tell, it is human-facing.

Neither is exempt from the no-secrets policy. Agent-facing pages under `docs/` are still
built and still reachable by URL; unlisted is not private.
