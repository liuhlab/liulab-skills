# Liu Lab Skills

[Agent Skills](https://agentskills.io) that teach AI coding agents how the Liu
Lab works, starting with its HPC clusters. Built for Claude Code, and they work
in any tool that reads the open skills standard.

Ask an agent to "run this on the cluster" and it needs lab knowledge it cannot
guess: which clusters exist, how a job gets submitted, what is safe to do. This
plugin holds that knowledge.

| Skill | What it covers |
| --- | --- |
| [lab-hpc](skills/lab-hpc.md) | The two clusters (arc/chimera GPU, ircbc CPU), Slurm, the safety rules, the per-machine setup check. |
| [lab-jupyter](skills/lab-jupyter.md) | Jupyter Lab on a compute node, tunnelled to your local browser. |
| [lab-containers](skills/lab-containers.md) | The lab's Singularity images on ircbc: keeping them current, running work inside them. |
| [lab-edison](skills/lab-edison.md) | The Edison platform: Kosmos for a whole research goal, cited literature answers and data analysis for a single question. No cluster. |
| [lab-setup](skills/lab-setup.md) | One step after installing: the plugin updates by itself, and Codex and Kimi Code get it too. |
| [hq-mode](skills/hq-mode.md) | A whole task done the lab's way: working rules, a playbook per kind of task, and a list of steps that always wait for your yes. |
| [lab-unslop-zh](skills/lab-unslop-zh.md) | The last pass over Chinese writing: it writes Chinese rather than translating it, and leaves your voice and your facts alone. |
| [lab-unslop-zh-kimi](skills/lab-unslop-zh-kimi.md) | A Kimi candidate for natural Chinese writing and strict technical translation, with protected mixed content. |

The three cluster skills load by themselves when your request touches remote compute.
The Chinese writing skills load when the deliverable is Chinese, and you can also call
them by name. Call lab-edison, lab-setup and hq-mode by name: lab-edison because every
run costs you money, lab-setup because you need it once per machine, and hq-mode
because you choose when a task gets it.

## What the agent will not do

It never runs compute on a login node, never submits a job you have not seen, and
never picks a cluster in silence. On a machine that is not set up it refuses and
points you at the setup below, rather than asking for an address or a password.
When ircbc stops answering it tells you to check the VPN instead of retrying in a
loop.

!!! note "No secrets in this repo"
    The skills hold no hostnames, addresses, usernames or keys. Hosts appear only
    as ssh alias names, and the rest is read from *your* `~/.ssh/config` at run
    time. That is what makes this repo safe to publish.

## Install

Two commands in your terminal:

```bash
claude plugin marketplace add liuhlab/liulab-skills
claude plugin install lab@liulab
```

Then start Claude Code and type `/lab-setup`. It turns on updates for the plugin,
and sets up Codex and Kimi Code if you have them. It also points each agent at the
lab's defaults: where issues go, which labels to use, and the safety rules for the
clusters. It asks before each change, and it removes nothing. Its
[page](skills/lab-setup.md) has the details.

Then set the machine up for the clusters once.

1. **SSH aliases.** Your `~/.ssh/config` needs the lab's usual alias names:
   `arc`, `chimera-login`, `chimera-transfer`, `chimera-gpu`, `chimera-cpu`, the
   per-node aliases, `ircbc`, `ircbc-transfer`, and `cpu01` through `cpu08`, each
   with your own username and key. Ask a lab member for a working example. This
   repo ships none.
2. **Personal config.** Copy
   [`templates/personal.md`](https://github.com/liuhlab/liulab-skills/blob/main/templates/personal.md)
   to `~/.claude/lab/personal.md` and fill in your usernames, directories and
   Jupyter defaults. Never commit it.
3. **Edison key and pixi, only for lab-edison.** That skill needs
   [pixi](https://pixi.sh) on your PATH. Then copy
   [`templates/edison.env`](https://github.com/liuhlab/liulab-skills/blob/main/templates/edison.env)
   to `~/.claude/lab/edison.env`, paste your own key over the placeholder,
   and `chmod 600` it. It sits beside `personal.md`, never inside it. Never
   commit it.

To check the result, ask Claude: *"Am I set up for the lab HPC clusters?"* The
skill runs its preflight and reports per cluster.

## Codex and Kimi Code

`/lab-setup` sets both up from Claude Code, so there is nothing to install by hand.
Codex gets the same plugin and checks for a new release each time it starts. Kimi
Code reads the skills from the copy Claude Code keeps up to date. No other agent
tool is supported.

lab-edison waits for you to type its name in all three. Claude Code and Kimi Code
read that from its settings. Codex reads it from a small opt-out file the skill
also ships, `agents/openai.yaml`.

## Updating

Once `/lab-setup` has run, there is nothing to do: each agent picks up a new
release on its own. To update by hand:

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

The last line moves your own files to where the skills now look for them. Every
skill refuses to run while `~/.claude/compute` is still there. If you installed
from a clone instead, use the two commands under Install. `/lab-setup` then lists
the links your old install left, for you to remove.
