# Testing this skill repo

Skills are prose that steers an agent, so they are tested at three layers of
increasing cost. Run layer 1 on every change, layer 2 when setting up a machine,
and layer 3 only when a skill's behaviour has changed. Two skills also ship real
code, and so does the maintainer's upstream sync. Each has unit tests of its own,
described first.

`pixi run check` runs everything cheap and safe: the static linters, the unit
tests and layer 1, all started at once, every failure reported in one run.
`.github/workflows/ci.yml` runs the same tasks on every pull request. **Only the
unit tests and layer 1 run in CI** — the other two are local-only, for the reasons
below.

## Unit tests — the Edison spend path: `tests/edison_cli/`

Free, seconds. `pixi run test`, and a step of `check-static`. Tests the **code**:
`src/edison_cli`, which is the only Python in this repo that can spend a lab
member's money.

They have their own directory because the rest of `tests/` is bash and costs
something. Every one of them answers from a fake `edison_client` the test writes
into a temporary directory and puts first on `PYTHONPATH`, and the fixture proves
the shadowing worked before any test runs. **Nothing here can reach the
platform**, which is the point: a test of the spending path has to be safe on the
day that path is broken.

What they pin, beyond the obvious: `kosmos stop` queues the halt *before* it
cancels anything, because reversing those two makes the run dispatch replacements
faster than the sweep can cancel them; the preflight module runs with neither the
client nor typer installed; the key reaches the client through the environment,
did arrive, and appears in no argument, no output and no file under `src/`; and
`project delete` removes nothing without `--yes` and a stated disposition for the
run history.

## Unit tests — the upstream sync: `tests/upstream_sync/`

Free, seconds, in the same `pixi run test`. Tests `scripts/upstream_sync.py`, the
script behind the maintainer's monthly merge of upstream skills. Each test builds a
small upstream and a lab tree as git repos in a temporary directory, runs the
script at its command line, and reads what a person would: the files it wrote, the
report it printed and its exit status. There is one case each for a clean merge, a
conflict, a deletion with and without a fork, a rename, a new skill, a forked skill
left alone, a lost pin, the moved pin and a fork. Then the reports a clean merge
hides: stale words, in a lab edit and on any lab page, the defaults page among them;
dropped edits, at the merge and again in `recheck` after a resolution; what upstream
did to a forked skill's original; the pstack section; and which eval cases to rerun.
Nothing reaches the network, and git reads none of your own settings.

## Unit tests — the setup script: `tests/lab_setup/`

Free, seconds, in the same `pixi run test`. They drive `/lab-setup`'s script,
`skills/lab-setup/scripts/lab_setup.py`, at its command line against a **fake
home** in a temporary directory, with a stub `codex` that writes what the real
one would. `HOME` points at the fake home too, so nothing can reach the real one.
They pin what a member would see: the settings, Kimi config and PATH link it
leaves, the defaults block in all three agents' instructions files with the
member's text around it kept, that it removes nothing and keeps entries it did
not write, the clash report against planted skills, the refusal without a
marketplace clone, and that a second run leaves every file byte-identical. One
test points the fake clone at this repo and follows the block to the defaults
page and on to every seed page it names, so an upstream rename fails here.

## Unit tests — lab side pages: `tests/test_side_pages.py`

Free, seconds, in the same `pixi run test`. A lab edit too long for an upstream
file sits beside it as `<topic>.lab.md`. These run vale and markdownlint with the
repo's own configuration on a copy of one adopted skill's folder, and check that
the upstream page keeps its exemption while the side page meets the lab's rules.

## Unit tests — the eval plan fold: `tests/test_eval_plans.py`

Free, seconds, in the same `pixi run test`. A plan-mode eval session may print only
the path to its plan file, so `eval.sh` adds that file to the transcript before it
checks anything. These run `eval.sh --only` against a stub `claude` and a fake home,
and check that a plan named from `~` or by its full path is added. The stub is first
on PATH, so no session starts.

## Unit tests — shared eval assertions: `tests/test_eval_assert_sh.py`

Free, seconds, in the same `pixi run test`. `tests/eval_assert.sh` is the shared
interface used by `eval.sh` and `lint.sh`. These tests check case-sensitive and
case-insensitive matching, required and forbidden Skill calls, `!` handling, and the
failure reasons against existing stream-json fixtures. No session starts.

## Layer 1 — static lint: `tests/lint.sh`

Free, seconds. Tests the **files**: manifests are valid JSON, every skill has
parseable `name`/`description` front matter, names follow the naming policy
(`lab-*`, or recorded as adopted in `upstream/`), every item a pin maps points at a
lab file that exists, each description fits the
per-skill listing limit, and a tagged version still names the tree it was tagged
on. A user-invoked skill must carry Codex's opt-out file, and every lab-owned
skill, forked ones included, lists triggers that must fit in the 247 characters
Kimi Code shows. A Chinese skill body or reference page is capped in CJK
codepoints here rather than by vale, which cannot count Chinese
(`docs/adr/0015-chinese-caps-are-counted-in-lint.md`). For `hq-mode`, the playbook index and the playbook pages must
name the same playbooks, the principles index and the principle pages the same
principles, every skill its trigger table names must ship, its text
must say "the user" and never "hq", and its always-pause list must keep every item.
It also self-tests the two preflights, the eval guard, the naming check, those
rules, and the eval assertions (below).

The Edison preflight is a Python module, `src/edison_cli/preflight.py`, and this
suite runs it as a file with a bare interpreter. That is deliberate: the no-secrets
sweep reads the key-file constants from it, so it has to answer on a tree where
nothing is installed, which is why it imports only the standard library.

The heart of it is the **no-secrets sweep**: no IP literals, no key material, no
Edison key other than the shipped placeholder, and none of the usernames or dotted
host names from *your* `~/.ssh/config` anywhere in the repo. Both lists are read
from your machine at test time, so the test itself stores neither.

**In CI that sweep is half-blind, and that is expected.** The username and host
name checks read the runner's own `~/.ssh/config`, which has no lab hosts in it.
So the leak sweep is a **local pre-push control**: a green CI run is not evidence
that no username or host name reached the tree. Run `pixi run check` on a machine
with the lab ssh config before you push.

## Layer 2 — environment preflight: `tests/preflight.sh`

Free, seconds. **Local only** — it reads a real `~/.ssh/config` that a runner does
not have. Tests the **machine**, not the repo, by running the same checks the
skills run as their own step 0. Three of them: the cluster aliases, which decide
the exit code, and then two Edison checks that are reported and never decide,
because the platform is opt-in per user. The first is the key. The second is the
environment `edison-cli` runs in — whether pixi is installed and whether the
environment is built — because the Edison spend path is a Python package now and a
key on its own is no longer enough. It reports; it never builds one. With `--live`
it also opens a connection to each login node; an ircbc timeout usually means the
VPN is down.

## Layer 3 — agent evals: `tests/eval.sh`

Costs tokens. Every case is a real headless `claude -p` session, so **there is no
default run** — a bare `eval.sh` prints the case list and exits without launching
anything. Ask for what you want by name:

```bash
bash tests/eval.sh --only edison-kosmos   # one case
bash tests/eval.sh --all                  # every non-live case
bash tests/eval.sh --all --live           # plus the cluster job and one real credit
```

`--live` on its own is refused: it is a modifier, not a request. Naming a `live-*`
case turns it on by itself. Layer 3 **never runs in CI** — on a public repo,
anyone who could open a pull request could spend that budget. Cases run
concurrently, so a suite takes about as long as its slowest case.

Evals exercise the **installed** plugin, not this working tree: push, then run
`claude plugin marketplace update liulab` and `claude plugin update lab@liulab`,
or you are testing the previous version. If you are an agent doing this for someone, prefer `--only`, and ask
before `--all` or anything live.

| Case | What it proves |
| --- | --- |
| `trigger` | An HPC prompt that never names the skill still produces a Slurm-first plan |
| `explicit` | Invoking `lab-hpc` by name states the hard safety rules |
| `reject` | Told the preflight failed, the agent refuses instead of improvising |
| `containers` | An image rebuild surfaces crane-on-login and a docker-archive build job |
| `jupyter-ircbc` | Jupyter on ircbc plans the container path, not the arc-native one |
| `reuse-job` | With a job already held, work reuses that node instead of the login node |
| `edison-refuse` | With no key, the agent refuses and never asks for the key in chat |
| `edison-molecules` | Chemistry routes to `MOLECULES`, never to the retired job that 404s |
| `edison-kosmos` | Kosmos is explained as a fan-out chat session, and nothing is substituted for it |
| `edison-recover` | A run whose id was lost is found in task history, not bought again |
| `prototype-language` | In a Python repo, `prototype` writes the logic in Python, not in an HTML page |
| `diagnosing-bugs-slow-loop` | A loop that takes minutes takes the slow-loop path instead of stalling |
| `hq-pause-sbatch` | Under `/hq-mode`, "going to bed, land it" still shows the script and waits for a yes before `sbatch` |
| `hq-pause-merge` | Under `/hq-mode`, "close the issue" never merges a pull request nobody reviewed, and never closes the issue while its fix is unmerged |
| `unslop-zh-rewrite` | An English passage asked for in Chinese comes back written, not translated: none of the markers a literal rendering would leave |
| `unslop-zh-not-chinese` | An English README about Chinese-language data takes `unslop`, not `lab-unslop-zh`. The skill's description is dense with "Chinese", so this is where it would wrongly fire |
| `unslop-zh-kimi-original` | A Chinese request automatically invokes the candidate through the Skill tool and produces an original Chinese final text without an English draft or process notes |
| `unslop-zh-kimi-source` | An English request automatically invokes the candidate and composes Chinese from source facts without adding facts or exposing process notes |
| `unslop-zh-kimi-not-chinese` | English documentation about Chinese-labelled data selects `unslop` without invoking the Chinese candidate; a future mixed-document caveat may still name that candidate |
| `unslop-zh-kimi-english-delivery` | An English editing task delivers English prose without invoking the Chinese candidate |
| `unslop-zh-kimi-zh-request-english` | A Chinese request for an English deliverable does not invoke the Chinese candidate |
| `unslop-zh-kimi-non-chinese` | A Japanese deliverable does not invoke the Chinese candidate |
| `unslop-zh-kimi-code` | A pure Python deliverable does not invoke the Chinese candidate |
| `unslop-zh-kimi-translate` | Strict technical translation preserves facts and established terms while repairing a specific English-shaped construction |
| `unslop-zh-kimi-mixed` | A mixed document repairs only the authorized Chinese sentence and preserves exact code, versions, placeholders, English and quotes |
| `unslop-zh-kimi-polish-fix` | Chinese polishing repairs a real fault and keeps the natural second line exact, including its facts, term and qualifiers |
| `unslop-zh-kimi-polish-keep` | Already-natural Traditional Chinese stays on one exact line without rewriting, script conversion or process notes |
| `live-sbatch` | Really ssh to arc, submit a tiny job to a free partition, clean it up |
| `live-edison` | One real literature call comes back with citations, for one credit |

Assertions include loose key phrases and exact anchored matches. A case can opt into
case-sensitive matching for protected text. EXPECT, ALSO and EXTRA are positive
assertions. DENY forbids a match. SKILL requires or forbids an actual Skill `tool_use`.
For stream-json cases, text assertions read the final `result`, while SKILL reads the
assistant events. A plugin listing or a skill named in prose does not count as an
invocation. `tests/lint.sh` checks all these rules against synthetic transcripts in
`fixtures/eval/`, reading the assertions from `eval.sh --dump`. Some cases still have
no fixtures; lint names them each run.

The polish cases reject an unchanged faulty line, a rewritten natural line and
changes to protected meaning. Keyword, exact-match and tool-call assertions do not
prove naturalness, so transcript review and the frozen with-skill and without-skill
comparison remain separate acceptance steps.

A failure means "read the transcript in the temp directory", not necessarily "the
skill is broken".

> Note: these cases do not move to Claude Code's native `claude plugin eval`. It
> drives Claude Code only, and the lab also runs Codex and Kimi Code. The reasons
> are in `.out-of-scope/claude-plugin-eval.md`.
