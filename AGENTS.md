# AGENTS.md

How any agent works on this repo. `CLAUDE.md` is a symlink to this file, so edit this one.

The repo is the Liu Lab's public set of Agent Skills, shipped as one Claude Code plugin: the
repo root is plugin `lab` in marketplace `liulab`, with one skill per `skills/<name>/`. Every
file is public, and the whole tree ships to every lab machine, so every merged change is a
release.

## Hard rules

- **No connection details, anywhere.** No IP literals other than `0.0.0.0` and `127.0.0.1`,
  and no usernames, hostnames, key names, key material or passwords: not in a file, a commit,
  an issue or a PR body. Name a host only by its lab ssh alias. A skill reads everything else
  from `~/.ssh/config` and `~/.claude/lab/personal.md` when it runs.
- **Run the gate before every commit.** The no-secrets sweep looks for the usernames and hosts in
  your own ssh config, so CI's run of it is half-blind and yours is the real one.
- **A tracked skill's upstream text only gains lines.** A lab edit adds; it never cuts,
  rewords or renames, even to pass the gate. The tracked skills are the `items` in
  `upstream/mattpocock/pin.json`.

## Checks

| Lane | Command | What it proves |
| --- | --- | --- |
| Gate | `pixi run check` | Every static check, unit test and `tests/lint.sh`; what CI runs on each PR. All failures print in one run, so read to the bottom |
| Docs | `pixi run docs-build` | The site builds strictly. CI runs it too |
| Preflight | `bash tests/preflight.sh [--live]` | This machine is set up for the clusters. Local only |
| Evals | `bash tests/eval.sh --agent <agent> --only <case>` | A skill's behaviour, in a real headless session against the *installed* plugin: the runner installs and verifies a private snapshot first. Costs tokens: ask the user before `--all` or `--live` |

Use the development agent for evals. Manage only its installation. Carry authorization
through review, release and cleanup; batch routine steps and reuse approved prefixes.
Request only sandbox permissions the environment requires.

## Release

Every merged change is a release, a test-only change included:

1. In one commit, bump `version` in `.claude-plugin/plugin.json` (CalVer, `YYYY.M.PATCH`) and
   add a `CHANGELOG.md` entry, which is the release notes.
2. Once it merges, tag `main` as `v<version>` and `git push origin main --tags`. No GitHub
   Release.

## Read next

| When | Read |
| --- | --- |
| Before any change | `GLOSSARY.md`, then the `docs/adr/` records on that area |
| Writing anything | `docs/agents/writing.md` |
| Adding or editing a skill | `docs/agents/skills.md` |
| Placing a fact, a term or a decision | `docs/agents/domain.md` |
| An adopted skill, or an upstream sync | `upstream/README.md` |
| A test or an eval case | `tests/README.md`. A new gate step goes in the `check-static` task in `pyproject.toml`, which CI calls by name |
| Filing, labelling or working an issue | The lab defaults: `skills/lab-setup/references/defaults.md` |
