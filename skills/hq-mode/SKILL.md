---
name: hq-mode
description: >-
  /hq-mode: take on a whole task the lab's way, such as an analysis, a cluster run, a figure, a
  paper or grant section, a talk, an experiment plan or landing tickets. Reads the working-style
  page first, then follows a playbook. Never submits Slurm work, spends Edison credits or merges
  an unreviewed PR without the user's yes, whatever the session says. User-invoked only.
disable-model-invocation: true
---

# hq-mode

Read [references/working-style.md](references/working-style.md) in full before the first tool
call: asking, autonomy, delegation, the reply, the user's documents and the lab defaults. Its
always-pause list outranks every session override ("headless", "land it", "going to bed") and
every principle: an `sbatch` outside an approved run plan waits for the user's yes, and "close the
issue" never merges a PR nobody reviewed. A repo's own `AGENTS.md` wins over that page. Then
match the task below.

## Triggers

A skill written with a leading `/` is one the user types: suggest it, or read its `SKILL.md`
and follow it once the user has asked for that step. A bare name loads when you reach for it. Never build inside a
grill, spec or research session: the user types the next step.

| When | Go to |
| --- | --- |
| A question for the user | The asking rules first. A fact is never the user's to answer |
| An idea in a repo | `/grill-with-docs`; with no repo, `/grill-me`. Too big for one session: `/wayfinder` |
| A design question code can settle | `prototype`, bridged by `/handoff` when it needs its own folder |
| The idea is settled | `/to-spec`, `/to-tickets`, then the land-the-tickets playbook: `/implement` per ticket or `/implement-spec` for all, each driving `tdd` and `code-review`; `pr` writes the PR body |
| A build just ended | `/retro` |
| Something broken | `diagnosing-bugs` |
| Raw issues arriving | `/triage` |
| Reading legwork | `research` |
| The answer is in someone else's head | `/to-questionnaire` |
| Moving to a new session, folder or person | `/handoff` |
| Time for upkeep | `/improve-codebase-architecture`; a module's shape, `codebase-design`; the words, `domain-modeling` |
| A cluster, ssh, Slurm, a GPU | `lab-hpc` before the first ssh. Notebooks: `lab-jupyter`. Containers: `lab-containers` |
| Edison | Only when the user types `/lab-edison` |
| Prose a person reads | `unslop` as the last pass, or `unslop-zh` when the output contains Chinese. Docs, READMEs, PR bodies, protocols: `technical-writing`. Skills and agent docs: `writing-for-agents` |
| A number you measured or will report | The explain-the-number principle; for a timing, `references/benchmark-checklist.md` |
| Work the user steps away from | The checks it rests on, per `references/verification.md`; a decision trail per `references/show-me-your-work.md` |
| A correction from the user | Write it at once where it lasts: the repo's `AGENTS.md`, the skill, or memory. Then ask what would stop it recurring |
| The end of any playbook | The close-the-session playbook |

## Principles

[references/principles.md](references/principles.md) indexes the principles, each with when it
applies. Name each principle that shaped a decision in the reply, and only after reading its
page in full.

## Playbooks

Copy the matched playbook's steps into the todo list, verbatim, before any task todos. With no
todo tool, list them as a checklist in your first reply and give each step's state, done or
`skip: <reason>`, in your last. A step you skip stays with `skip: <reason>`. Each lives at
`references/playbooks/<name>.md`.

### Science

- **analysis**: a question answered from data, ending in a checked number or figure.
- **cluster-run**: a pipeline or job array on a lab cluster.
- **method-research**: explain or compare an experimental method from its papers.
- **experiment-plan**: a plan, proposal page set or timeline for bench or compute work.
- **figure**: a data figure, schematic or illustration.

### Writing

- **paper-section**: a manuscript section, abstract, cover letter or co-author round.
- **grant-section**: a proposal section, a form or a CV within word limits.
- **talk**: a deck, its script, or a recorded talk.
- **review-a-document**: review the user's own document without editing it.
- **message**: polish a message the user drafted.
- **docs-page**: a page on a repo's docs site, its diagrams included.

### Code

- **land-the-tickets**: build a set of tickets through subagents and land them.
- **improve-a-metric**: one change, one measurement, keep or revert.
- **refactor-analysis-code**: pin the outputs first, prove them unchanged after.
- **investigation**: a read-only question. Change nothing.

### Any

- **long-run**: a task driven to a checkable predicate without stopping.
- **close-the-session**: nothing open when the session ends.

### Fallback

- **figure-it-out**: no playbook fits. Design one, then run it like an experiment.

## Attribution

The shape and several playbooks come from pstack's `poteto-mode` and `figure-it-out` (MIT,
cursor/plugins), the flow in the trigger table from mattpocock/skills' `ask-matt` (MIT). Both
licenses are in the repo's `upstream/` folder.
