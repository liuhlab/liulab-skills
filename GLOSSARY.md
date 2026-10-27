# Glossary

The words this repo uses, and nothing else. How the clusters actually work is in
`skills/lab-hpc/references/`; why the repo is shaped the way it is is in `docs/adr/`.

## Glossary

### Adopted skill

A skill that came from an upstream rather than being written here. It keeps its upstream
name, typed bare, and is either tracked or forked. Its upstream's MIT license and attribution
travel with it. Contrast a derived skill, which the lab owns from the start. See
`docs/adr/0013-adopted-skills-keep-upstream-names.md`.

### Agent-facing document

A document written for a machine that has to act on it: `AGENTS.md`, `GLOSSARY.md`, the
pages under `docs/agents/` and `docs/adr/`, and the skill bodies. Capped in words, exempt
from the jargon and reading-grade rules, and kept out of the site navigation. Its opposite
is a human-facing page — `README.md`, `CHANGELOG.md`, and the browsable `docs/` pages —
which is checked for jargon and reading grade and carries no cap. A file is one or the
other; if you cannot tell which, it is human-facing. See `docs/agents/writing.md`.

### Agent Skill

A directory under `skills/` holding a `SKILL.md` whose frontmatter carries `name` and
`description` — the open Agent Skills standard — plus optional `references/` and
`scripts/`. The description is the trigger signal an agent matches a request against; the
body is what it reads once triggered. A user-invoked skill, such as `lab-edison`, also sets
`disable-model-invocation: true`, a key beyond the standard. Claude Code and Kimi Code
honour it. Codex ignores it and needs the opt-out file instead: `agents/openai.yaml` beside
the `SKILL.md`, setting `policy.allow_implicit_invocation: false`. The gate fails a skill
that has one without the other. See `docs/adr/0007-edison-key-file-and-never-transmit.md`.

### Alias

The name a lab host is called by in this repo: `arc`, `ircbc`, `chimera-transfer`,
`cpu01`. An alias resolves to a real hostname and username only in the user's own
`~/.ssh/config`, on their own machine, at run time. This repo never records what one
resolves to, and the no-secrets sweep fails a commit that does.

### Always-pause list

The actions the mode never takes without the user's yes: submitting or cancelling Slurm
work, spending Edison credits, force-pushing, deleting data, merging a pull request nobody
reviewed, making private material public, and the rest, written once on the working-style
page. It outranks every session override ("headless", "land it", "going to bed") and every
principle. A lab safety rule lives here or in a lab-owned skill, and never inside upstream
text.

### Attribution record

The record that a forked item came from an upstream: the item's lab path, the upstream item
and commit it was taken from, and optionally what the lab changed. Records live in
`upstream/attribution.json`, and lint reads one as proof that a forked skill is adopted. The
upstream's license sits in `upstream/<upstream>/LICENSE`. A tracked skill needs no record,
because its pin maps it. Format: `upstream/README.md`.

### CalVer

The versioning scheme of `.claude-plugin/plugin.json`: `YYYY.M.PATCH` — year, month with
no leading zero, then a counter that increments per release within the month and resets
when the month changes. See `docs/adr/0004-calver-and-manual-updates.md`.

### Compute node

A cluster node that runs real work, inside a Slurm job. It is reachable by ssh only while
the user holds a job on it, and it is the only correct place for anything heavier than
light Slurm control.

### Conformance rule

One named check in the conformance checker, `scripts/conformance.py`, which holds this
repo to the lab template's rules. A rule passes, fails with a list of problems, or reports
that it did not run. Rules are waived by name, never per file.

### Core skill

`lab-hpc`: the skill holding the repo's foundational cluster facts — which cluster is
which, the safety rules, and the per-cluster reference pages. Every other skill builds on
it and none repeats it. Contrast a task-recipe skill; see
`docs/adr/0002-facts-vs-recipes.md`.

### Credit

The Edison platform's unit of spend. A submitted task is charged in credits against the
balance the key belongs to, so a wasted run costs the person whose key it is. The tiers are
what a skill routes by, never the numbers: literature, precedent and molecules are the
ordinary tier; high-reasoning literature and analysis cost more and run longer; a batch
multiplies whichever was picked; a Kosmos run pays for every task it fans out to. No figure appears
anywhere in this repo. The platform's own billing page is the only current source, and a
price written into a skill goes stale in silence — so send the user to their balance
instead of quoting one.

### Derived skill

A skill the lab owns from the start but built from upstream skills or ideas, carrying their
attribution. It takes a `lab-*` name, except the mode. Contrast a forked skill, which began
as an adopted copy and keeps its upstream name.

### Description budget

Room for the trigger text an agent reads when it decides which skill to load. Two limits
are easily confused. One skill's frontmatter `description` is capped at 1536 characters —
the platform's limit on a single entry in the skill listing — and the gate fails a
description longer than that. The other is the share of the model's context window the
listing occupies: genuinely shared, but across every skill installed on a machine rather
than the ones in this repo, so no count taken here measures it. The gate prints the total
of this repo's descriptions as information and fails nothing on it. Other agents cut each
entry sooner: Codex at 1024 characters, Kimi Code at 250, of which it shows 247 and an
ellipsis. So a lab-owned skill puts its triggers first, and the gate fails one whose
recorded triggers fall past Kimi's cut. A tracked skill is exempt, its description being
upstream text. Keeping each one keyword-dense is still the point.

### Digest sidecar

A file named `<image>.sif.digest` beside a built SIF, holding the registry digest the image
was built from. A version check compares it against the registry, so it is written only
after the build succeeds — an image that failed its smoke test must not have one.

### Edison

The Edison research platform, run by **Edison Scientific** — FutureHouse's commercial
spinout, which the platform transitioned to — and reached from a lab machine through
`edison-cli` and the `edison-client` package: cited answers over the published literature,
precedent searches, chemistry, and a data-analysis agent that runs code on a dataset the user
uploads. It is a cloud API, and the one thing this repo teaches that has no cluster in it
at all. `lab-edison` is the skill that drives it — user-invoked only, and in the same
plugin as the rest. See `docs/adr/0006-edison-one-skill-in-the-lab-plugin.md`.

This entry is the **single authority** on who runs the platform. Every other page — the
skill body, its trigger description, `README.md`, the published page — names Edison
Scientific in its own register and carries none of the lineage above, because no one
sentence passes every register's checks. The platform's own job names still read
`job-futurehouse-…` and its persona picker still offers `@FutureHouse/…`: naming residue
of the spinout, not evidence of who runs it. They are live API values, so never "correct"
one or argue from one back to a vendor. The gate fails a commit re-attributing the
platform, and exempts those strings.

### Edison key file

`~/.claude/lab/edison.env` on the user's own machine, at owner-only permissions: one
exported assignment of the variable the client reads, and nothing else. The preflight owns
those constants — the name, the placeholder, the location and which modes pass — and prints
them on request, so nothing else in the tree may restate one. It sits beside the per-user
config and never inside it, because a skill reads that file into context and a key placed
there would land in every transcript. `templates/edison.env` is the blank copy; a filled-in one never
lands here, and the no-secrets sweep fails a commit that brings one. A skill sources the
file into the process that needs it and never transmits, prints or asks for its contents.
See `docs/adr/0007-edison-key-file-and-never-transmit.md`.

### Eval case

One named scenario in `tests/eval.sh` — `trigger`, `containers`, `reuse-job`, and the
rest. Each is a full headless agent session run against the *installed* plugin. As the case
requires, assertions use loose key phrases, exact anchored text, case-sensitive protected
text, or observed Skill tool calls. Evals test behavior; lint checks files and exercises
those assertions against synthetic transcripts.

### Forked skill

An adopted item the lab now owns: a skill or a reference page. It keeps its upstream name
and attribution, leaves the pin, and may change freely. Upstream changes to its original
reach it only as ideas in the upstream sync's summary, ported by hand. Every pstack item is
forked from day one; a mattpocock skill is forked when merging it costs more than it saves.
Contrast a tracked skill. See `docs/adr/0012-upstream-skills-merge-from-a-pin.md`.

### Gate

`pixi run check`: the one command that must be green before a commit, and what CI runs on
every pull request. The steps start together and every failure is reported in one run, so
read to the bottom. A cap or rule inside the gate is a dial, not a law — raise one
deliberately, in its own commit, with the reason in the message.

### Idle interactive job

A Slurm job the user already holds that is not currently computing — usually a long-lived
Jupyter or reservation job. It is the default place to run work: reuse it before queueing
anything new, and never run work through `ssh` to a login alias.

### Kosmos

The Edison platform's heavyweight agent. Not a job you submit but a **chat session on a
project**, which fans one objective out into many ordinary tasks over several rounds. That
is why `JobNames` has no member for it — the enum lists the one-shot jobs `create_task`
takes, while Kosmos sits on the chat surface under the job name
`job-futurehouse-data-analysis-aries`. A run is billed for each of the tasks it fans out to,
so its cost is the sum of the ones it actually calls and there is no flat per-run price. It
is also unbounded before the run starts, which is why a skill never starts one unless the
user asks for that run in those words; drafting the objective, checking the dataset and
reading a run that already exists are free, and are usually what was wanted.

### Lab defaults

The issue tracker, triage labels and domain layout every lab machine provides, so a repo
needs no setup for them. They live on one lab-owned page in the marketplace clone, which
`/lab-setup` points each agent's user-level instructions file at, so an update reaches it
with no rerun: `skills/lab-setup/references/defaults.md`. The page indexes upstream's own
seed pages and adds a few lab lines, among them the always-on cluster rules members once
appended to `~/.claude/CLAUDE.md` by hand, and the line that turns on the working-style page.
A repo's own `docs/agents/<page>` overrides that one default and no other.

### Lab edit

A capability added to the upstream text of a tracked skill: a template, a branch, a loop
path. Never a safety rule, which lives on the always-pause list or in a lab-owned skill, and
never a rename. A whole new section goes in a lab-only side page with a one-line pointer from
the upstream file; a branch or a loop path goes in place. Its only record is the diff against
the pin, with its reason in the commit message and the changelog.

### `lab-*` name

The mark of a skill the lab wrote, such as `lab-hpc` or `lab-setup`, or derived. An adopted
skill never takes one, tracked or forked. The mode is the one exception: `hq-mode`. Lint
admits any other name only when the repo records the skill as adopted. See
`docs/adr/0013-adopted-skills-keep-upstream-names.md`.

### liulab-runtime

The lab's environment repo: pixi environments (`default`, `ml`, `align-rna`, and others)
published as container images. On arc they run natively under pixi; on ircbc they are
pulled and built into SIFs. This repo teaches how to consume them and does not define them.

### Login node

The shared node an ssh login alias lands on. Light commands only — file browsing, Slurm
control, small transfers, non-bulk `git`. On ircbc it is also the only node with a route
out to the internet, so staging downloads belong there.

### Marketplace clone

Claude Code's git clone of the `liulab` marketplace, under `~/.claude/plugins/marketplaces/`,
which its update pass keeps on `main`. Kimi Code reads its skills from it, and the
`edison-cli` link on the user's PATH points into it. It is the catalogue, not the installed
plugin, so for a while after an update the two can differ. See
`docs/adr/0014-installed-copies-update-on-their-own.md`.

### Mode

`hq-mode`: a user-invoked router over playbooks, with a working-style page that every session
reads first. Its name follows pstack's `<handle>-mode` convention, and it is the one derived
skill without a `lab-*` name. Its text says "the user", so any lab member who types
`/hq-mode` gets that way of working applied to their own work.

### Name cache

`~/.claude/lab/edison-cli-names.json` on the user's own machine, at owner-only
permissions: what `edison-cli` remembers of the persona and project names it has already
resolved, so `--project` and `--persona` can take a name where the platform wants a UUID. It
holds names and ids and nothing else — never the key, and never one byte of the key file — and
it sits beside the Edison key file rather than inside the plugin directory, which a plugin
update wipes. It is a convenience and never the truth: `--no-cache` refreshes it, every command
that spends or destroys ignores it and resolves live, and a cache that cannot be read or written
is simply not used rather than being an error.

### No-secrets sweep

The part of `tests/lint.sh` that greps the whole publishable tree for connection details:
IP literals (`0.0.0.0` and `127.0.0.1` excepted), key material, an Edison key set to
anything but the shipped placeholder, and the usernames and dotted hostnames it reads out
of the local machine's `~/.ssh/config` at run time. Those last two are blind on a CI runner
that has no ssh config, which is why the sweep stays a local pre-push control.

### Partition

A named Slurm queue with its own hardware, limits and cost. `zhoulab_gpu_priority` on arc,
`compute_cpu` on ircbc; arc's preemptible partitions cost nothing and requeue.

### Per-user config

`~/.claude/lab/personal.md` on the user's own machine: their per-cluster usernames,
code directories, ports and reservation notes. A skill reads it at run time and it takes
precedence over any default in this repo. `templates/personal.md` is the blank copy; a
filled-in one never lands here. A credential never goes in it — reading it at run time
means reading it into context, which is why the Edison key file sits beside it. Until the
plugin was renamed it lived in `~/.claude/compute/`; while that directory exists, both
preflights refuse and print the move rather than read either copy.

### Pin

Per upstream, the commit last synced (mattpocock/skills) or reviewed (pstack), plus a map
from each upstream item to the lab file it feeds. The repo stores only the pin, never a copy
of upstream: a sync fetches upstream and reads both ends from that one clone. Moving a pin
forward goes in the sync's pull request. It lives at `upstream/<upstream>/pin.json`, in the
format `upstream/README.md` gives. See `docs/adr/0012-upstream-skills-merge-from-a-pin.md`.

### Playbook

The mode's step list for one kind of task, such as an analysis, a cluster run or a paper
section, at `references/playbooks/<name>.md` inside `hq-mode`.

### Plugin marketplace

This repo, `liulab-skills`: the home of every Liu Lab agent skill, whether or not it touches
a cluster. `.claude-plugin/marketplace.json` declares `source: "./"`, so the repo root is
the plugin: marketplace `liulab`, plugin `lab`, every skill inside that one plugin and
invoked by its bare name, such as `/lab-edison`. See `docs/adr/0001-repo-root-is-the-plugin.md`.

### Preflight

Step 0 of a skill: a check reporting, condition by condition, whether this machine holds
what the task needs. The two are no longer the same kind of thing. `lab-hpc` runs a bash
script, `scripts/check-hpc-config.sh`, which says per cluster whether `~/.ssh/config`
carries the aliases. `lab-edison` runs `edison-cli preflight`, a subcommand of the package
that spends, which says whether the key file exists, is non-empty, is no longer the
placeholder and is owner-only — never the key itself. That module imports only the standard
library, so the no-secrets sweep can read its constants without a hundred packages
resolving. On a machine that is not configured the skill refuses the request rather than
improvising around it. Each takes a flag naming an alternative file, so the gate can drive
it against fixtures.

### Provenance block

The two lines at the head of every `lab-edison` reference page: where the page's facts came
from, the date they were checked, and the tier that holds unless a claim says otherwise.
Three tiers, and only three — **verified**, we ran it and saw the result; **read**, taken
from the package source or a vendor page and not run; **unverified**, inferred or assumed
with nothing checked. A claim at another tier is tagged where it is made, so the exceptions
are visible and the page still declares one default. Package or vendor page is a matter for
the Source line and never the tier: the skill already ranks those two ("believe the package
over any vendor page"), and encoding the ranking twice would let tier and source contradict
each other with nothing to catch it. `tests/lint.sh` fails a reference page carrying no block
and a block whose date will not parse; no check can tell whether a date is honest. See
`docs/adr/0009-facts-carry-their-provenance.md`.

### Reference page

A page under a skill's `references/`, read by path when the skill body points at it and never
triggered on its own. `lab-hpc`'s cluster pages and `lab-edison`'s vendor pages are reference
pages, and so is most of what pstack contributes to the mode: its principles,
`show-me-your-work` and `benchmark-checklist`. Reading by path works in all three agents and
costs no place in the skill listing.

### Reservation job

A long-lived Slurm job a user keeps to hold a node on a reserved partition. Never cancel
one you did not start, and never cancel someone else's to make room.

### Shared package store

`$LIU_LAB_PACKAGES` on ircbc: the group-writable directory holding the lab's SIF images,
their digest sidecars, job logs and helper binaries. Everything in it is shared lab
property — never delete or overwrite another person's image without asking.

### SIF

A Singularity image file: one file holding a whole environment. On ircbc every real job
runs inside one, because the host OS is far too old to run modern binaries; on arc the same
environments run natively under pixi.

### Task-recipe skill

`lab-jupyter`, `lab-containers` and `lab-edison`: a skill holding one repeatable procedure
and its own trigger vocabulary. The first two build on the core skill and point at its
references instead of repeating a cluster fact. `lab-edison` has no cluster to defer to, so
it carries its own facts in its own `references/`. See
`docs/adr/0002-facts-vs-recipes.md`.

### Tracked skill

An adopted skill merged from its upstream on every upstream sync. Its upstream text changes
only by a lab edit. Every mattpocock skill starts tracked, and no pstack item ever is.
Contrast a forked skill. See `docs/adr/0012-upstream-skills-merge-from-a-pin.md`.

### Transfer node

The alias for a cluster's data-mover host — `chimera-transfer`, `ircbc-transfer`. Use it
for bulk copies instead of the login node. On ircbc it does not mount the same storage the
login node does, so a file landed there has to be copied onward.

### Upstream

A repo the lab takes skills from and keeps following: mattpocock/skills, whose skills are
tracked or forked, and cursor/plugins' `pstack`, whose items are all forked and only
reviewed. No third one is followed. Any other skill installed on a machine is not an
upstream: it stays on its own channel or retires.

### Upstream sync

One run of `/lab-upstream-sync`, the maintainer-only skill in this repo's `.claude/commands/`,
which is not shipped, started by hand about monthly. Its script, `scripts/upstream_sync.py`,
merges every tracked skill from its pin to upstream's tip, and reports conflicts, deletions,
stale words (a token upstream removed that lab text still uses) and dropped edits (a line the
lab added that the merge lost). The skill summarises what is new in both upstreams and opens
one pull request, so one version under `docs/adr/0008-version-identifies-the-content.md`.

### Waiver

A conformance rule this repo declines, recorded by rule name in `pyproject.toml` with the
reason beside it. Waivers are per rule and never per file, they do not expire, and every
conformance run prints them — so the reason is where a reader meets it.

### Working-style page

`hq-mode`'s `references/working-style.md`: the rules every session reads first. Asking,
autonomy and the always-pause list, delegation, the reply, the user's documents. The lab
defaults turn it on for any non-trivial task. A repo's own `AGENTS.md` wins over it.
