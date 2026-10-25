# liulab-skills

Liu Lab's shared [Agent Skills](https://agentskills.io), packaged as a Claude
Code **plugin marketplace** (marketplace `liulab`, plugin `lab`; call a skill by
its own name, such as `/lab-hpc`). Codex and Kimi Code read the same
skills — SKILL.md follows the open Agent Skills standard.

**Docs:** <https://liuhlab.github.io/liulab-skills/> — human-readable
guide (what this is, install, usage, one page per skill).

Current skills:

- **`lab-hpc`** — the two lab clusters (arc/chimera GPU, ircbc CPU), the
  local → GitHub → remote workflow, Slurm usage (partitions, cost/queue
  guidance), safety rules, and a config preflight
  (`scripts/check-hpc-config.sh`) that makes agents refuse HPC requests on
  machines whose `~/.ssh/config` isn't set up.
- **`lab-jupyter`** — start or reuse a Jupyter Lab job on either cluster and
  tunnel it to `http://localhost:<port>` on the local machine: arc/chimera
  natively (`zhoulab_gpu_priority` job + `ssh -L`), ircbc inside the lab's
  Singularity image (via `lab-containers`).
- **`lab-containers`** — version-check, pull/build/update, and use the lab's
  Singularity images (`liulab-runtime` envs) on ircbc, where compute nodes
  have no internet: digest-sidecar update checks, crane pull on the login
  node → sbatch build from docker-archive, and running commands, pixi-env
  shells, or Jupyter inside the containers.
- **`lab-edison`** — the Edison research platform, which Edison Scientific
  runs: cited literature answers, precedent, molecules, and analysis of a
  dataset you upload. It goes through `edison-cli`, a command that ships
  with the plugin. No cluster involved. You invoke it yourself
  (`disable-model-invocation`), it refuses until your key file
  `~/.claude/lab/edison.env` is in place (`edison-cli preflight`), it
  shows the job and the query before it spends, and it never transmits the
  key. Kosmos is a chat session that fans out into many tasks, and the skill
  will not start one unless you ask for that run.
- **`lab-setup`** — type it once per machine, after installing. It sets
  `autoUpdate` on the `liulab` marketplace in Claude Code, installs the
  plugin in Codex, points Kimi Code's `extra_skill_dirs` at Claude Code's
  marketplace clone, links `edison-cli` onto your PATH, and lists any skill
  of yours that takes a name the plugin ships. It asks before each change and
  removes nothing; its script (`scripts/lab_setup.py`) is safe to rerun.
- **`hq-mode`** — type `/hq-mode` with a task to have the agent work the lab's
  way: it reads one page of working rules, then follows the playbook that
  fits (an analysis, a cluster run, a figure, a paper or grant section, a
  talk, landing tickets, and more). Its always-pause list, which outranks "land it"
  and "going to bed", keeps it from submitting Slurm work, spending Edison
  credits or merging an unreviewed pull request without your yes.

- **`lab-unslop-zh`** — the last pass over Chinese writing. An agent asked for
  Chinese tends to translate word by word and keep the English shape; this makes
  it read the passage, work out the meaning, and write it as a Chinese writer
  would. It carries a list of things it must *not* change, so your long
  sentences, your way of addressing the reader and your facts all survive the
  edit. It loads only when what you are making is Chinese.

- **`lab-unslop-chinese-kimi`** is a Kimi candidate for Chinese writing and strict
  technical translation. It routes by the deliverable's language and writes directly
  in Chinese. Translations keep every detail, term and degree qualifier. Mixed
  documents change only authorized Chinese text, leaving code and English intact.

Skills taken from other projects keep their own names. These come from
[mattpocock/skills](https://github.com/mattpocock/skills). Most are
unchanged. A few carry a lab edit, which only adds what science work needs,
and the changelog names each one:

- **Plan:** `grilling`, `grill-me`, `grill-with-docs`, `wayfinder`, `to-spec`,
  `to-tickets`, `to-questionnaire`, `triage`.
- **Build:** `implement`, `implement-spec`, `tdd`, `prototype`,
  `diagnosing-bugs`, `codebase-design`, `improve-codebase-architecture`,
  `domain-modeling`.
- **Review and hand over:** `code-review`, `pr`, `retro`, `handoff`.
- **Learn and write:** `research`, `teach`, `writing-for-agents`, `wait-what`.
- **Set up a repo:** `setup-matt-pocock-skills`.

These four come from [pstack](https://github.com/cursor/plugins/tree/main/pstack),
three of them changed for lab work:

- **`unslop`** takes the tells of AI writing out of a draft. It leaves science
  words such as vector, locus and modality alone, and keeps a paper or a grant
  in its field's style.
- **`technical-writing`** sets the standard for docs, protocols, pull requests
  and commit messages. Papers and grants keep their own style, and a protocol
  gives every amount its unit.
- **`ketchup`**: type `/ketchup` to hear what happened since your last
  message, and what waits on you.
- **`bro`**, as pstack wrote it: type `/bro` after a dense reply to hear it
  again in plain words.

Each project's MIT license is in `upstream/<project>/LICENSE`.

## Security policy (hard rule)

This repo is **public**; what makes that safe is that it must **never**
contain connection details or secrets of any kind: no IP addresses or
hostnames, no usernames, no SSH keys or key filenames, no tokens, no
passwords, no VPN credentials. Skills refer to hosts only by the lab's
conventional **ssh alias names** and resolve everything else from each
user's own `~/.ssh/config` at run time (`tests/lint.sh` enforces this).

Setting up SSH access (hosts, keys, accounts, VPN) is **out of scope** for
this repo — get it from a lab admin through a secure channel.

## Setup (two commands, then `/lab-setup`)

```bash
claude plugin marketplace add liuhlab/liulab-skills
claude plugin install lab@liulab
```

Then start Claude Code and type `/lab-setup`. From then on Claude Code,
Codex and Kimi Code all follow the plugin and update on their own, and
`edison-cli` works in all three. All three also read the lab's defaults: where
issues go, which labels to use, and the safety rules for the clusters. Its
[page](https://liuhlab.github.io/liulab-skills/skills/lab-setup/) has the
details.

`lab-edison` also wants [pixi](https://pixi.sh) on your PATH, and
`/lab-setup` uses it where the machine's Python is older than 3.11.

## Per-user config (once per machine)

1. Make sure your `~/.ssh/config` defines the lab's conventional aliases
   (`arc` / `chimera-login`, `chimera-transfer`, `chimera-gpu`, `chimera-cpu`,
   per-node compute aliases, `ircbc`, `ircbc-transfer`, `cpu01`…`cpu08`) with
   your own usernames and keys. Ask a lab member for a working example —
   this repo intentionally does not ship one.
2. Copy [templates/personal.md](templates/personal.md) to
   `~/.claude/lab/personal.md` and fill in your usernames/directories.
   Never commit it anywhere.
3. Only if you use `lab-edison`: install [pixi](https://pixi.sh) if you do
   not have it, then copy [templates/edison.env](templates/edison.env) to
   `~/.claude/lab/edison.env`, replace the placeholder with your own
   Edison key, and `chmod 600` it. It goes *beside* `personal.md`, never
   inside it — skills read `personal.md` into context. Never commit it.
   Nothing else has to be installed. The first Edison command builds the
   environment it runs in before anything is sent, so it can look hung. It
   is not. A plugin update lands in a fresh folder, so the build runs once
   more per release, quicker because the downloads are already on disk. The
   [lab-edison page](https://liuhlab.github.io/liulab-skills/skills/lab-edison/)
   has the rest.

## Codex and Kimi Code

`/lab-setup` sets both up from Claude Code (ADR 0014). Codex installs the same
plugin from `.claude-plugin/` and upgrades it at every startup. Kimi Code reads
the skills live from Claude Code's marketplace clone through `extra_skill_dirs`,
so it follows every Claude Code update. No other agent tool is supported.

A user-invoked skill, such as `lab-edison` or `lab-setup`, loads only when you
type its name. Claude Code and Kimi Code read that from
`disable-model-invocation: true` in its frontmatter. Codex ignores that key and
reads the opt-out file beside the skill instead, `agents/openai.yaml`, which
sets `allow_implicit_invocation: false`.

## Updating

Nothing to run once `/lab-setup` has: a release reaches each agent on its own,
and Claude Code loads it at its next launch. To update by hand:

```bash
claude plugin marketplace update liulab
claude plugin update lab@liulab
```

Claude Code loads plugins when it starts, so restart your session before the
updated skills are there.

### Moving from `lab-compute`

Until `2026.10.1` this repo was `liulab-compute-skills` and the plugin was
`lab-compute`. A plain update does not cross a rename, so do it by hand once:

```bash
claude plugin uninstall lab-compute@liulab
claude plugin marketplace remove liulab
claude plugin marketplace add liuhlab/liulab-skills
claude plugin install lab@liulab
mv ~/.claude/compute ~/.claude/lab
```

The last line moves your per-user files to where the skills now read them.
Every skill refuses to run while `~/.claude/compute` is still there.
If you installed by cloning this repo instead, use the two commands under
Setup. `/lab-setup` then lists the links your old install left, for you to
remove.

## Testing

Three layers under [tests/](tests/) — see [tests/README.md](tests/README.md):

```bash
pixi run check                          # the gate: linters + tests/lint.sh, all at once, every failure reported
bash tests/lint.sh                      # static: manifests, frontmatter, naming, no-secrets sweep
bash tests/preflight.sh --live          # this machine's ssh config + login-node reachability
bash tests/eval.sh [--live] [--only <case>]  # headless claude -p behavior evals (costs tokens; --live submits a real job on arc)
```

`pixi run check` is what CI runs on every pull request. The other two layers
are local-only: one reads your ssh config, the other spends API tokens. The
no-secrets sweep's username and hostname checks only see *your* machine's ssh
config, so they stay a pre-push control — run the gate locally before you push.

## Adding a new skill

1. Create `skills/<new-skill>/SKILL.md` — frontmatter with `name` +
   `description` (open-standard core); keep the body lean and put long
   detail in `references/`. Add `disable-model-invocation: true` only when
   a skill must never load on its own, as `lab-edison` does, and copy its
   `agents/openai.yaml` for Codex. Put the words that should trigger the
   skill in the first 247 characters of its description, which is all Kimi
   Code shows, and list them in `tests/lint.sh`.
2. Name a skill you write `lab-*`, not `liulab-*`. A skill taken from another
   project keeps its own name and is recorded in `upstream/` (see
   `upstream/README.md`). Respect the security policy above:
   no IPs, usernames, keys, or passwords — resolve per-user detail from
   `~/.ssh/config` / `~/.claude/lab/personal.md`.
3. Run `pixi run check`; bump `version` (CalVer `YYYY.M.PATCH`) in
   `.claude-plugin/plugin.json` and add a `CHANGELOG.md` entry in the same
   commit; tag that commit `v<version>`; push with `git push origin main
   --tags`. Installed machines pick it up on their own at their next launch.
