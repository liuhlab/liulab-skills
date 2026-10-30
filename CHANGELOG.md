# Changelog

Versions track `version` in `.claude-plugin/plugin.json`. Bump the version
and add an entry here in the same commit. Versioning is CalVer
`YYYY.M.PATCH` (month unpadded; patch counts releases within the month) —
adopted at `2026.7.0`; earlier `0.x` releases predate the switch.

## 2026.10.19 — 2026-10-30

### Fixed

- Eval runs now select the development agent explicitly, install a private plugin snapshot,
  and verify its content before launch. Codex runs no longer change other agents' installs.
- Failed setup, failed runners and missing answers cannot pass through matching output.
- The planning eval accepts an explicit equation that bounds total threads by the allocation.
- Review and development guidance now checks eval evidence and carries authorization through
  release and cleanup without weakening sandbox controls.

## 2026.10.18 — 2026-10-30

### Changed

- Large data jobs now require a plan for safe restarts and useful parallel work.
  Agents measure the slow step, match workers to available cores and memory, and reuse
  derived data instead of scanning the same snapshot for every build.
- Cluster guidance connects that plan to each cluster's limits. The arc priority queue
  also allows preemption, so a held node does not guarantee an uninterrupted run.

### Added

- A focused eval checks planning for a slow snapshot scan on a multicore allocation.

## 2026.10.17 — 2026-10-30

Real evals caught three false failures in the Chinese assertions. The skill is unchanged.

### Fixed

- **The rewrite eval accepts the source's own rhetoric.** Natural use of 「这意味着」 may stay,
  alongside the existing protection for 「之一」. Its passing fixture now covers both.
- **The routing evals distinguish present and future work.** They reject choosing `unslop-zh`
  for an English deliverable without rejecting a valid exception for later Chinese or mixed
  prose. New and updated fixtures reproduce the observed correct answers.

## 2026.10.16 — 2026-10-30

The two Chinese skills are now one `unslop-zh`.

### Changed

- **Combined `lab-unslop-zh` and `lab-unslop-zh-kimi` into `unslop-zh`.** It covers Chinese
  originals, source-based writing, strict translation, polishing and mixed documents. The
  merged workflow keeps task-specific limits, two-pass review and protected content, then
  applies the translationese and AI-tell checks without stacking `unslop` on Chinese prose.
- **Reduced seven reference pages to five.** Yu Guangzhong's retained examples stay unchanged.
  The three self-check questions join the diagnosis page, technical examples move to the
  technical Chinese page, and general rules no longer repeat across pages. Grammar terms and
  formatting rules are consistent.
- **Added a second lab-owned naming exception.** `unslop-zh` pairs with `unslop`; ADR 0016
  records the decision and its shadowing cost. Naming lint and trigger checks recognize the
  exception without admitting other unrecorded bare names.
- **Updated the Chinese evals and fixtures for the merged name.** The rewrite case no longer
  treats natural use of 「之一」 as translationese, so the source's non-unique meaning can stay.

## 2026.10.15 — 2026-10-25

The Kimi Chinese candidate now polishes Chinese with fewer unnecessary edits.

### Added

- **Low-edit Chinese polishing in `lab-unslop-zh-kimi`.** It changes only actual
  faults inside the authorized scope and returns already-natural text unchanged. It
  preserves the author's voice, facts, judgments, actors, conditions, scope, negation,
  modality, degree, quotations and terms. Simplified and Traditional Chinese, regional
  wording and register follow the source and project. Examples cover technical, chat,
  marketing and literary contexts without banning sentence forms.
- **Two polishing eval cases** cover a fault that needs a safe repair and natural
  Traditional Chinese that needs no change. Synthetic passing and failing transcripts
  reject unchanged faulty text, rewritten natural text, changed protected meaning and
  leaked review notes. Transcript review and a frozen manual comparison check Chinese
  quality separately from keyword assertions.

### Fixed

- **The English-deliverable eval accepts a valid mixed-document caveat.** It no longer
  fails a correct answer that names the Chinese candidate only for a future bilingual
  section. It still rejects choosing that candidate for English prose. Its regression
  fixture uses bare skill names.
- **Kimi routing evals observe real Skill calls.** Chinese original and source-based cases
  require automatic invocation. English, Japanese and pure-code deliveries forbid it, as
  does a Chinese request for English. Text checks read the final answer, not the loaded
  skill instructions.
- **Mixed-content and polishing evals catch narrower faults.** Protected lines are anchored
  and case-sensitive. The EDIT check keeps v2.4.0 and 3 in place. Safe repairs may retain
  「关于重试行为」 and 「关于输入校验」; the weak-verb faults still fail.

## 2026.10.14 — 2026-10-25

The Kimi Chinese candidate now handles strict technical translation and mixed documents.

### Added

- **Strict technical translation in `lab-unslop-zh-kimi`.** It reads the whole
  source and writes Chinese by paragraph and meaning group. It preserves facts, logic,
  document structure, terminology and degree qualifiers. Sentence splits, merges and
  reordering are allowed, but source-based-writing omissions and restructuring are not.
  Review reads the Chinese alone first, then checks it against the source.
- **Two translation references.** One distills Yu Guangzhong's three essays on Chinese
  westernization into contextual judgments, repairs, exceptions and modern technical
  examples. The other covers terminology priority, established English, consistency,
  technical register, hedging, punctuation and protected mixed content.
- **Two eval cases** cover strict translation and mixed documents. Synthetic passing and
  failing transcripts check fact and term fidelity, a specific translationese repair,
  and exact protected strings in the existing static gate.

## 2026.10.13 — 2026-10-25

A Kimi candidate for natural Chinese originals and source-based Chinese composition.

### Added

- **`lab-unslop-zh-kimi`** loads automatically for Chinese deliverables and can
  also be called by name. It writes directly in Chinese, defaults to simplified Chinese,
  follows specified regional and project conventions, and keeps source facts and
  structure unless the task allows changes.
- **A natural Chinese reference** covers collocations, subject-predicate relations,
  reference, measure words, aspect markers, sentence structures and rhythm. Each rule
  has conditions, examples and exceptions.
- **Three eval cases** cover a Chinese original, an English request for Chinese
  composition from source material, and an English deliverable that must not select the
  candidate. Synthetic passing and failing transcripts run in the existing static gate.

## 2026.10.12 — 2026-10-25

A Chinese prose pass, `lab-unslop-zh`, and the length cap that makes a Chinese page
measurable.

### Added

- **`lab-unslop-zh`**, the last pass over Chinese prose. It replaces `unslop` when the
  deliverable is Chinese and stays out of the way otherwise. Its one instruction is to write
  Chinese from meaning rather than translate it, which covers writing, editing and rewriting
  English source alike. Behind it are three reference pages digesting 余光中's essays on
  欧化中文: `ouhua-diagnosis.md` finds the fault by word class, `ouhua-repair.md` holds the
  rewrites and the test for when to leave a borrowing alone, and `ouhua-self-check.md` counts
  the 虚字 that give a translation away. A fourth page, `ai-tells.md`, covers the other half:
  the set phrases, dashes and lead-in colons that mark machine writing rather than
  translation. Every rule carries a **保留** case, a sentence with the same surface pattern
  that must not be touched, so the rules cannot collapse into a word blacklist. The skill
  also carries a table of features that are **not** a reason to edit, because over-editing is
  the failure this pass guards against.
- **Chinese length caps**, counted in `tests/lint.sh`: 1000 characters for a Chinese
  `SKILL.md`, 2000 for a Chinese page under `references/`. Vale's word counter reads a run of
  Chinese between two full-width commas as one word, so it passes a Chinese page at about ten
  times the English budget. `.vale.ini` is unchanged
  (`docs/adr/0015-chinese-caps-are-counted-in-lint.md`).
- **Two eval cases.** `unslop-zh-rewrite` checks an English passage comes back written rather
  than translated; `unslop-zh-not-chinese` checks the skill does not fire on an English
  deliverable that merely mentions Chinese.

### Changed

- **`hq-mode` routes Chinese prose** to `lab-unslop-zh` and everything else to `unslop`.

### Fixed

- **Node belongs to the environment, not the machine.** `markdownlint-cli2` is an ES module
  and `pyright` runs on node too, so both took whatever `node` the PATH offered. On a machine
  whose system node predates ES modules, markdownlint, typecheck and the side-page test all
  died at load with `ERR_REQUIRE_ESM`, and the gate reported a repo problem that was really a
  laptop problem. `nodejs` is now a pixi dependency. The same move fixes the four
  `tests/lint.sh` edison-preflight steps, which were failing because the system `python3` was
  older than `str.removesuffix`.

## 2026.10.11 — 2026-10-13

The guide an agent reads on every turn in this repo is now a short page of pointers. The
rules that serve one kind of task moved to the page that task reads.

### Changed

- **`AGENTS.md` is a short page of pointers.** It keeps what every task needs: what the repo
  is, the hard rules, the checks, the release steps and a table of where to read next. It is
  about a fifth of its old length.
- **The skill rules have a page of their own**, `docs/agents/skills.md`. It covers the shape of
  a skill, its name, the rules every lab skill keeps, and what `lab-hpc`, `lab-jupyter`,
  `lab-containers` and `lab-edison` must keep true.
- **The rules for writing down a fact moved to `docs/agents/domain.md`.** A fact is checked
  and dated, and a page records settings, never measurements.
- **`AGENTS.md` has its own word cap of 300**, so it stays short. Vale does not count table
  text, so the cap limits prose and the pointer rows can grow.
- **The list of eval cases lives in `tests/eval.sh` and `tests/README.md` only.** Lint checks
  those two.
- **The release tag goes on `main` after the merge**, where the recent tags already sit.
- **`tests/README.md` names both commands to run before an eval:**
  `claude plugin marketplace update liulab`, then `claude plugin update lab@liulab`.

## 2026.10.10 — 2026-10-13

`/hq-mode`'s improve-a-metric playbook gives its table of attempts its own name.

### Fixed

- **An attempt log, not a decision log.** The improve-a-metric playbook keeps a table with
  one row per attempt, on every run. It called that table a decision log, the same name as
  the log of choices that the agent keeps only when you step away. So the playbook seemed to
  ask for that log on every run, with its own columns. The table is now the attempt log, and
  it keeps its columns. (#125)

## 2026.10.9 — 2026-10-13

`/hq-mode` gets a playbook for docs pages, and five of its rules that did not fit a docs task
now do.

### Added

- **A docs page playbook in `/hq-mode`**, for a page on a repo's docs site. The agent names
  the reader and checks every claim against a file in the repo. It draws diagrams as text, so
  a diagram changes in the same edit as the words around it. Then it builds the site
  strictly and looks at every changed page in the light and the dark theme. The figure
  playbook now sends a docs diagram here, not to image generation.

### Changed

- **Steps without a to-do list.** An agent with no to-do tool lists the playbook's steps in
  its first reply. Its last reply says which steps it did and which it skipped.
- **Helpers take checks and side-by-side work.** The agent keeps the work whose sources it
  has already read. It hands helpers the pieces that can run at the same time, and the
  checks that need fresh eyes, such as a fact-check.
- **The decision log is for work you leave.** The agent keeps a log of its choices, and has
  a helper review it, only when you step away. Before, it did so on every task that no
  playbook fit.
- **Principles are read before they are named.** The agent names a working principle in its
  reply only after reading that principle's page.

## 2026.10.8 — 2026-10-13

`/bro` comes from pstack, three skills move back toward the text their authors wrote, and
`/tdd` warns against tests that slow the checks or prove nothing new.

### Added

- **`/bro`**, as pstack wrote it. Type it after a dense reply, and the agent says the same
  thing again in plain words. It runs only when you type it, in every agent.
- **`/tdd` watches what a test costs.** Two mistakes join its list. The first is writing
  more tests than the plan agreed on, such as one per helper or one that proves what
  another test already proves. Every test is code someone has to keep up, so no new test is
  better than one that adds nothing. The second is a test that slows the checks you run on
  every change. The agent uses the smallest input that shows the behavior, or moves the
  test to a slower set of checks that the repo lists. It times the checks before and after
  its change, and tells you when they got slower and by how much. The `/hq-mode` page on
  checks now says a check must be worth its cost.
- **A rule for changing upstream text.** Every edit to a skill taken from mattpocock/skills
  or pstack now has to name a failure seen in a lab session or an eval. A guess that the
  agent might miss something is not enough. Older edits stand, and going back to upstream's
  text needs no reason. `upstream/README.md` has the rule.

### Changed

- **`/ketchup` talks like `/bro` again**, as pstack's does. It still checks Slurm jobs and
  Edison runs.
- **`unslop` is closer to pstack's.** It takes pstack's short description and makes one
  pass, so a reply no longer ends with a report on a second one. It keeps two lab rules. A
  paper or a grant keeps its field's style, and a science word used in its real sense, such
  as a viral vector or a genetic locus, stays. Its own exceptions for citations,
  statistics, units and number ranges are gone. In a paper or a grant, the style rule keeps
  them. Your agent can still use it without being asked.
- **`to-tickets` is upstream's text again.** The lab's line that a data pipeline's stages
  are its layers is gone. A review of every lab edit to upstream text found no session that
  needed it.

## 2026.10.7 — 2026-10-13

A Developers section on the docs site, after Skills.

### Added

- **Pages for people who change the repo.** Three pages, mostly diagrams. How the repo is
  laid out and how a change ships. How the skills from mattpocock/skills and pstack arrive,
  change and keep their names, and what `hq-mode` took from each. The design choices behind
  the layout, each linked to the decision record that argues it.
- **Mermaid diagrams on the site.** `mkdocs.yml` turns on the `mermaid` code fence, so a
  diagram is text that changes in the same diff as the prose around it.

## 2026.10.6 — 2026-10-12

`edison-cli` now runs on Intel Macs, and `/hq-mode` is clearer about two of its pauses.

### Fixed

- **`edison-cli` runs on Intel Macs.** The lab's pixi setup listed only Apple-chip Macs and
  Linux. So on an Intel Mac, `edison-cli` stopped with an "unsupported platform" error
  before it did anything. Intel Macs are now on the list. (#110)
- **`/hq-mode` leaves an issue open while its fix waits for review.** Asked to close an
  issue whose fix sits in a pull request nobody has reviewed, the agent now leaves the issue
  open and asks you. Before a Slurm job, it puts the exact script in its reply, not a link
  to the file. The `hq-pause-merge` eval now also fails an answer that closes the issue.
  One eval case can now hold more than one fixture of a kind. (#109)

### Changed

- **Evals stay in `eval.sh`.** Claude Code's own eval tool runs only Claude Code, and the
  lab also uses Codex and Kimi Code. The plan to move the evals to it is dropped.
  `.out-of-scope/claude-plugin-eval.md` says why. (#87)

## 2026.10.5 — 2026-10-12

No skill changed. Four evals in the 2026.10.4 acceptance run failed on correct answers.
The tests were wrong, not the skills. (#105)

### Fixed

- **Evals read a plan saved under `~`.** A session can save its plan as
  `~/.claude/plans/x.md` and print only that path. The eval script looked only for paths
  that start with `/`, so it never read the plan, and `edison-kosmos` and `hq-pause-sbatch`
  failed. It now reads both kinds of path. A new unit test checks this with a fake `claude`,
  so it costs nothing.
- **`edison-recover` accepts `task list`.** The skill now finds a lost run with
  `edison-cli task list`, and the eval only knew the older words for it.
- **`hq-pause-merge` lets the agent show the merge command.** It used to fail any answer
  that wrote out `gh pr merge`. That includes the right one: show the exact command, then
  wait for a yes. It now fails only an answer that says the pull request was merged.

## 2026.10.4 — 2026-10-11

The lab plugin now ships the whole skill set: the skills from mattpocock/skills under their
own names, three skills from pstack, `/hq-mode` and `/lab-setup`.

### Added

- **`/grilling`**, the first skill from mattpocock/skills. It ships exactly as upstream
  wrote it, under its own name. Its MIT license is in `upstream/mattpocock/LICENSE`.
- **The other 24 skills from mattpocock/skills**, such as `/tdd`, `/wayfinder` and
  `/code-review`. Each ships as upstream wrote it, under its own name, and the README lists
  them all. The ones you start yourself carry the file Codex reads, so Codex never starts
  them unasked. Upstream's `wizard` stays out, and its `ask-matt` becomes part of `/hq-mode`.
- **`upstream/`**, where the repo records what it takes from outside. Each upstream has a
  pin there: the commit last merged or read, and which lab file each upstream skill feeds.
  A skill the lab changes for good gets an attribution record instead.
  `upstream/README.md` gives both formats.
- **`unslop` and `technical-writing`**, two writing skills from pstack, now owned and
  changed by the lab. Your agent can use them without being asked. `unslop` takes the tells
  of AI writing out of a draft. It no longer rewrites science words such as vector,
  locus, modality and scaffold, and it keeps citations, statistics, units and
  number ranges. It does the job `avoid-ai-writing` did, so you can remove that skill if you
  installed it. `technical-writing` keeps papers and grants in their own style, asks for
  quantities with units, and uses spaces, not tabs, in code.
- **`/ketchup`**, pstack's catch-up: what happened since your last message, and what waits
  on you. It now checks Slurm jobs and Edison runs too, in plain words. It runs only when
  you type it, in every agent.
- **pstack's pin.** The lab reads pstack and never merges it. `upstream/pstack/pin.json`
  records the last pstack commit read, `978ca6e` (v0.15.17), and the lab file each item
  feeds, the items taken only as ideas included. pstack's MIT license is in
  `upstream/pstack/LICENSE`. Like the lab's own skills, each of the three starts its
  description with its triggers, and the tests now check that for every skill the lab
  forks.
- **`/lab-setup`.** Type it once in Claude Code after the two install commands. It turns on
  updates for the `liulab` marketplace, installs the plugin in Codex, points Kimi Code at the
  copy Claude Code keeps current, and links `edison-cli` into a folder on your PATH. It asks
  before each change, removes nothing, and is safe to run again. It also lists any skill of
  yours that takes a name the plugin ships, because that copy wins over the plugin's without
  a word.
- **`/prototype` handles analysis and works outside JavaScript.** Upstream knew two kinds of
  prototype, a web page to click through and a set of screen designs. It now has a third for
  an analysis or a figure: a short script or notebook on part of the data that shows 2 or 3
  versions side by side. For an analysis, it fixes how to judge them before they run and
  reports all of them, so the pick does not follow the result. In a Python or R repo, the
  logic is now written in that language and run from a script or notebook, because logic
  written for a web page can't move into Python or R code. The page is built only when
  someone who doesn't code must click through it.
- **`/diagnosing-bugs` keeps going when one run takes minutes.** Upstream wants a test loop
  that runs in seconds, which a bug that shows only on the full dataset can never meet, so
  the agent stalled. Now it shrinks the input while the bug still shows, restarts from the
  last good saved file, or takes a batch job as the loop.
- **An eval case for each of those two changes.** `prototype-language` and
  `diagnosing-bugs-slow-loop` check that the agent still takes the lab's path. A later
  upstream rewording could undo either change without a merge conflict, so the upstream
  sync reruns the case when upstream touches that skill. Both changes only add lines to
  upstream's text.
- **The monthly upstream sync, for the maintainer.** `/lab-upstream-sync` brings upstream's
  changes into the skills the lab takes from mattpocock/skills, and ends in one pull request.
  The new version is tagged on `main` once that pull request merges. Its script merges each
  file from the pin to upstream's latest commit and keeps the lab's own lines. It lists
  conflicts, removed skills and new ones. The skill lives in this repo's `.claude/commands/`,
  so the plugin never ships it. The check for leaked secrets now reads that folder too.
- **The sync reports what a clean merge hides.** It lists each line the lab added that the
  merge lost, and each lab page that still uses a name upstream dropped, such as an old file
  name. It runs both checks again once the conflicts are fixed, since that is where a line
  most often goes missing. It also says what is new in both upstreams: changes to the
  skills the lab took and now owns, and a line for each pstack item. A change that only saves
  tokens or moves the default model is marked low priority. pstack's pin moves in the same
  pull request. When upstream changes `prototype` or `diagnosing-bugs`, the sync names that
  skill's eval case and asks before it runs, since each case costs tokens.
- **`/hq-mode`**, the lab's way of working through a whole task. Type it with your request.
  The agent reads one page of working rules first, then follows one of 17 playbooks, such as
  an analysis, a cluster run, a paper or grant section, or a talk. Some steps always wait for
  your yes, and that list wins over "land it" and "going to bed": a Slurm job, an Edison
  credit, merging a pull request nobody reviewed, and a few more. It runs only when you type
  it, in every agent. Its [page](https://liuhlab.github.io/liulab-skills/skills/hq-mode/) has
  the playbooks and the full list.
- **Tests for `/hq-mode`.** Two new eval cases check the two pauses above: a cluster run left
  overnight, and "close the issue" with a pull request nobody reviewed. The first also checks
  that the agent shows you the Slurm script it waits on, not only that it waits. The tests
  also fail when the mode names a playbook with no page, or a page it doesn't name, and when
  its list of always-paused steps loses one.
- **`/hq-mode`'s principles, from pstack.** The mode reads one of 22 short pages when that
  principle applies, and an index says when each one does. Six were changed for science
  work. Before it trusts a cell count, it rules out data leaking between splits, batch
  effects, repeated samples and a filter that changed what the count is out of. It tries one
  sample of a job array before it runs the rest. A step that reruns after a crash writes to
  a new name and then renames it, so a half-written file never counts as done. The tests fail
  when the index names a principle with no page, or a page it doesn't name.
- **Three more pages for `/hq-mode`.** pstack's benchmark checklist now pins both sides of a
  timing to one kind of node and records the job ID. pstack's decision log, for work you
  leave running, reads this agent's own session log, not Cursor's. A new page says how the
  agent finds the checks a task rests on before you step away: an agent that can check its
  own work can be trusted with more. Each page records its pstack source in `upstream/`,
  and the tests fail when pstack's pin points at a file that isn't there.
- **The lab defaults.** `/lab-setup` now adds one short block to each agent's own notes file:
  `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and `~/.kimi-code/AGENTS.md`. The block points
  at one page in the plugin, `skills/lab-setup/references/defaults.md`. That page says where
  a repo's issues go, which labels to use, where its glossary lives, and the safety rules for
  the clusters. So a new repo needs no setup, and Codex and Kimi Code get the same rules as
  Claude Code. A change to the page reaches every machine with the next update. Text outside
  the block is yours, and a second run replaces only the block. A repo's own page under
  `docs/agents/` replaces only the default it covers. (#101)

### Changed

- **Updates arrive on their own.** After `/lab-setup`, a release reaches Claude Code, Codex
  and Kimi Code with no command, and loads the next time each one starts. To update by
  hand, run `claude plugin marketplace update liulab`, then `claude plugin update
  lab@liulab`. Releasing is now just pushing. (#77)
- **The install pages** give the two commands, then `/lab-setup`. They no longer tell you to
  link skills into other agents with `skills/install.py`. If you installed that way,
  `/lab-setup` lists the links it left, for you to remove.
- **`templates/CLAUDE-stub.md` is gone**, and so is the install step that told you to paste it
  into `~/.claude/CLAUDE.md`. The defaults page carries its three rules now. (#101)
- **This repo's own issue and label pages are gone** from `docs/agents/`. They said what the
  defaults page says. Its domain page stays, because its table of what goes where is this
  repo's own. (#101)
- **Each lab skill's description now starts with its triggers.** Kimi Code shows only the
  first 247 characters of a description, so the words that should load a skill now come
  first. The tests list those words for every lab skill and fail when one falls past that
  point. (#79)
- **Naming.** A `lab-*` name now marks a skill the lab wrote. Lint accepts any other name
  only if `upstream/` records the skill, or if it is `hq-mode`. The error says how to
  record it.
- **The writing checks take upstream text as it is.** vale and markdownlint each skip the
  rules upstream text breaks, for the skills `upstream/` records and no others. Lab pages
  beside a skill body and in playbook folders now carry the 1200-word cap.
- **The glossary is now `GLOSSARY.md`.** It was `CONTEXT.md`. The skills from
  mattpocock/skills read and write `GLOSSARY.md` and nothing else, so under the old name they
  would miss it and start a second one. The entries are unchanged. The repo checks are the lab
  template's new copy: they fail a repo still on `CONTEXT.md`, and a repo skill that takes
  any name the plugin ships.
- **Lab edits to six skills from mattpocock/skills.** Each one adds what science work
  needs and removes no line of upstream text. A longer one sits in its own page beside the
  skill, named `*.lab.md`, and the writing checks hold that page to the lab's rules.
  - `code-review` also looks for science smells, such as a random step with no seed, rows
    dropped with no count, or a threshold with no source. Its fixed smell list is about
    objects, so a review of analysis code missed the faults that change a result.
  - `research` keeps what a paper reports apart from how well it is established, and takes
    a review as the source for where consensus stands. Before, it could pass on one
    preprint's claim as fact.
  - `tdd` takes a frozen golden output as a known-good value, with a rule for tolerance:
    compare bytes first, then mask fields that change between runs, then use
    `pytest.approx` with a stated reason. Most analysis outputs have no other known-good
    value, so the agent turned such tests down or wrote empty ones.
  - `implement` runs `pixi run check` plus the steps `AGENTS.md` lists outside it. With no
    test suite, it reruns on the fixture and compares with the saved result. Upstream
    assumes a type checker and a test suite, so without them the agent made up commands
    or skipped the check.
  - `to-spec` gains an analysis plan: the question, the data and where it came from,
    methods, outputs, checks and controls, and what is out of scope. An analysis has no
    users, so the user stories the usual template asks for were made up.
  - `to-tickets` treats a pipeline's stages as its layers, so a ticket takes one sample
    through every stage to a figure. Upstream names web layers, and the easy misreading
    was one ticket per stage.

### Fixed

- **`edison-cli` works through a link.** `/lab-setup` links `edison-cli` into a folder on
  your PATH, so Codex and Kimi Code can run it too. Run through that link, it used to look
  for its project next to the link and fail. Now it follows the link back to the plugin, and
  the setup check prints the short `edison-cli` form there too. The note at the top of the
  file no longer says Codex and Kimi Code install a plugin by symlink. (#78)
- **Codex no longer starts `lab-edison` unasked.** Codex ignores the setting that keeps the
  skill waiting for you, so it could spend your Edison credits without being asked. The skill
  now ships the small file Codex reads instead, `agents/openai.yaml`. The tests fail any skill
  that has the setting without the file, or the file without the setting. (#75)
- **The docs said every other agent ignores that setting.** Claude Code and Kimi Code honour
  it; only Codex needs the file. The README, the glossary, the `lab-edison` page and decision
  records 0007 and 0010 now say so.

### Upgrading

If you installed skills from mattpocock/skills with `npx skills`, remove those copies once on
each machine. The plugin now ships the same skills under the same names. A copy on your
machine wins over the plugin's without a word, so you would keep running the old one.

`npx skills` puts its copies in `~/.agents/skills` and links them into `~/.claude/skills`. For
each skill the README lists from mattpocock/skills, delete the copy and its link. If nothing
else on the machine came from `npx skills`, delete its list too, `~/.agents/.skill-lock.json`.

If you pasted `templates/CLAUDE-stub.md` into `~/.claude/CLAUDE.md`, delete that section once
`/lab-setup` has run. The defaults page carries the same rules, so the copy only repeats them.

## 2026.10.3 — 2026-10-11

No skill changed. This release writes down how the lab will take in skills from outside,
ahead of the release that does it.

### Added

- **Three decision records.** Skills taken from mattpocock/skills will be merged from a
  recorded commit, and pstack will only be read for ideas (ADR 0012). Those skills keep their
  own names, such as `/grilling` (ADR 0013). Installed copies will update on their own in
  Claude Code, Codex and Kimi Code, once a new setup skill turns that on (ADR 0014). That
  replaces the half of ADR 0004 that kept updates manual.
- **New glossary terms** in `CONTEXT.md` for the same work: upstream, tracked and forked
  skills, the pin, the mode and its playbooks, and the lab defaults.

## 2026.10.2 — 2026-10-10

You now call a skill by its own name, `/lab-edison`, with no `lab:` in front.

### Changed

- **Short names.** The README, the docs and the tests now write a skill as `/lab-hpc` or
  `/lab-edison`. Your agent still shows `lab:` in front of each skill, but you don't need to
  type it. The short name works as long as nothing else on your machine has the same name.

## 2026.10.1 — 2026-10-10

The repo is now `liulab-skills` and the plugin is `lab`, because this is where every lab
skill goes from here on, not only the compute ones. You call a skill as `/lab:lab-edison`.

### Changed

- **New names.** The repo moved from `liuhlab/liulab-compute-skills` to
  `liuhlab/liulab-skills`, the plugin from `lab-compute` to `lab`, and the docs site to
  <https://liuhlab.github.io/liulab-skills/>. The marketplace is still `liulab`.
- **Your per-user files moved too**, from `~/.claude/compute/` to `~/.claude/lab/`. While the
  old folder exists, the `lab-hpc` and `lab-edison` setup checks refuse and print the `mv`
  to run. They never move it for you, because it holds your Edison key.

### Upgrading

A plain update does not cross a rename. Run this once on each machine:

```bash
claude plugin uninstall lab-compute@liulab
claude plugin marketplace remove liulab
claude plugin marketplace add liuhlab/liulab-skills
claude plugin install lab@liulab
mv ~/.claude/compute ~/.claude/lab
```

Entries below this one keep the old names, because those releases shipped under them.

## 2026.10.0 — 2026-10-10

The setup pages no longer say how long the first Edison command takes.

### Changed

- **No build timings on the setup pages.** The README, the usage page and the `lab-edison`
  page each said how long the first Edison command spends building its environment. Nothing
  re-measured those figures, and the three copies had already drifted apart. Each page now
  says what the figure was for: the first command builds before anything is sent, so it can
  look hung and is not, and it builds once more after each update. (#47)
