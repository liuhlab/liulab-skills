# Lab defaults

Every lab machine provides these through `/lab-setup`. They are the issue tracker, triage labels
and domain docs the engineering skills expect to be "provided to you", so a repo needs no setup
for them and `/setup-matt-pocock-skills` runs only where a repo differs. Each default is one of
upstream's own seed pages, read as written, plus the lab's lines under it. Every path here is
in the lab plugin's marketplace clone, `~/.claude/plugins/marketplaces/liulab/`.

**A repo's own `docs/agents/` page overrides only that one default.** A repo with its own
`docs/agents/issue-tracker.md` takes its tracker from there, and its labels and domain docs from
here. The always-on rules hold in every repo.

## Issue tracker

GitHub issues on the repo's own `git remote`, with PRs not a request surface:
`skills/setup-matt-pocock-skills/issue-tracker-github.md`.

- A public repo's tracker is public: no hostnames, usernames, key paths or ssh output in an
  issue or a comment. Nothing checks an issue before it posts.

## Triage labels

The five roles, each label named as its role: `skills/setup-matt-pocock-skills/triage-labels.md`.

- Create a missing label on first use, the `wayfinder:*` ones included: `gh label create <name>`.

## Domain docs

Single-context, with `GLOSSARY.md` and `docs/adr/` at the repo root:
`skills/setup-matt-pocock-skills/domain.md`.

## Always on

- Load `lab-hpc` before any ssh or Slurm step.
- Never compute on a login node: get a Slurm job first.
- If ssh to `ircbc` hangs or times out, stop and tell the user to check the VPN.
- Pass `--as user` on every `lark-cli` call. Strict mode alone does not hold: when the CLI
  cannot load the account it treats strict mode as off, and with no user login an implicit
  call runs as the bot. Login life and Drive limits: `skills/lab-setup/references/feishu.md`.
- For any non-trivial task, read `hq-mode`'s working-style page first:
  `skills/hq-mode/references/working-style.md`.
