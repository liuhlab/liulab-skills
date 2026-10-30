---
search:
  exclude: true
---

# Skills

Read this before you add or edit a skill. `GLOSSARY.md` defines the kinds of skill it names.

## The shape of a skill

A skill is `skills/<name>/SKILL.md`, with `name` and `description` front matter (the open
Agent Skills standard), and the pages it needs beside it.

- **The description is the trigger.** An agent loads the skill when a request matches it, so
  keep it keyword-dense. Lint fails a single description over 1536 characters, the platform's
  cap on one listing; the total over all skills is information only. Kimi Code shows only the
  first 247 characters, so put the trigger words there. Every lab-owned skill records them in
  `LAB_TRIGGERS` in `tests/lint.sh`.
- **The body is the interface:** what must be true before the first tool call, under its
  600-word cap (`writing.md`). Long detail goes in `references/`, and executable checks in
  `scripts/`.
- **A user-invoked skill never triggers on its own.** It carries
  `disable-model-invocation: true` in its front matter, which Claude Code and Kimi Code
  honour, and an `agents/openai.yaml` that turns off implicit invocation for Codex. Lint
  checks the pair.

## Names

A skill the lab wrote or derived is `lab-*`; `liulab` names only the repo, the GitHub org and
the marketplace. `hq-mode` and `unslop-zh` are the two exceptions. An adopted skill keeps its
upstream name and is recorded in `upstream/`. Lint admits no other bare name
(`docs/adr/0013-adopted-skills-keep-upstream-names.md`,
`docs/adr/0016-unslop-zh-is-a-naming-exception.md`).

## Rules every lab skill keeps

- **Show the job first.** A skill never submits `sbatch` or `srun` work for the user outside
  a run plan the user approved after seeing the exact scripts (`lab-hpc`'s hard rules,
  `docs/adr/0017-slurm-approval-is-per-run-plan.md`).
- **A change in behaviour is tested with `tests/eval.sh`**, using the development agent via `--agent`, not only with lint, which proves
  just that the files are well-formed. Run an eval for a behaviour change you need to verify,
  never as a routine check.
- **`templates/` is documentation.** It holds the per-user files a member copies to their
  machine (`personal.md`, `edison.env`), and the plugin never loads them. A filled-in copy
  never lands in the repo, and lint fails a real Edison key.
- **SSH setup is out of scope** for this repo.

## Per-skill invariants

### `lab-hpc`

The core skill. Its preflight, `scripts/check-hpc-config.sh`, refuses an HPC request on an
unconfigured machine. Each cluster fact lives in one place: hosts, network, toolchain and
storage in `arc-hpc.md` or `ircbc-hpc.md`; partitions, choosing one and submitting in
`arc-slurm.md` or `ircbc-slurm.md`. The two clusters differ sharply, so read a cluster's
reference pages before you write a command for it.

### `lab-jupyter` and `lab-containers`

For Jupyter on ircbc, `lab-jupyter` owns the session lifecycle and `lab-containers` owns the
container commands, the ircbc Jupyter `sbatch` command among them. Neither repeats the other's
half (`docs/adr/0003-jupyter-containers-ownership-split.md`).

### `lab-edison`

The one skill with no cluster in it: the Edison cloud platform. It is user-invoked, so it never
triggers on its own and never spends a credit unprompted
(`docs/adr/0006-edison-one-skill-in-the-lab-plugin.md`).

- The spend path is the `src/edison_cli/` package, run through pixi and typed as the bare
  `edison-cli`, because Claude Code puts `bin/` on PATH. Its preflight, `edison-cli preflight`,
  refuses on a machine with no key (`docs/adr/0011-the-spend-path-became-a-package.md`).
- The Edison key file sits beside the per-user config, never inside it. Its contents are never
  sent, printed or asked for (`docs/adr/0007-edison-key-file-and-never-transmit.md`).
- Each of its reference pages carries a provenance block (`domain.md`).
