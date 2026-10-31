# hq-mode: work through a whole task the lab's way

Type it at the start of a task, followed by what you want:

```text
/hq-mode analyse the new run and tell me if the batch effect is gone
```

It never starts on its own. You turn it on, in Claude Code, Codex or Kimi Code.

## What it does

First the agent reads one page of working rules. They cover when to ask you and when to
find the answer itself, what it may do without asking, how it splits work between helpers,
and how it writes its reply. A rule in your repo's own `AGENTS.md` wins over that page.

Then it picks the playbook that fits your task and copies its steps into its to-do list, so
you can see what it will do and how far it has got. An agent with no to-do list puts the steps
in its first reply instead. The playbooks:

| Kind | Playbooks |
| --- | --- |
| Science | analysis, cluster run, method research, experiment plan, figure |
| Writing | paper section, grant section, talk, review a document, message, docs page |
| Code | land the tickets, improve a metric, refactor analysis code, investigation |
| Any task | long run, close the session |

When none fits, it designs one for the task, writes the steps down, and works through them.

It also follows a set of working principles. Each is a short page it reads when that
principle applies, such as "check the real output, not a sign of it". A few were changed for
science work. For example, before it trusts a cell count, it rules out data leaking between
splits, batch effects, repeated samples and a filter that changed what the count is out of.

It also knows which skill to reach for along the way: the lab cluster skills before any
ssh, `unslop` before you read its prose, and the planning skills such as `/grill-with-docs`
and `/to-spec` for a new idea. A skill you start by typing its name stays yours to start. The
agent suggests it rather than running it.

## What it always asks first

Some steps wait for your yes, every time:

- submitting or running a Slurm job outside a run plan you approved, or cancelling a job the
  plan did not start. A run plan covers one cluster run: its work folder, partitions, the
  most CPU, memory and wall time per job,
  the most jobs at once, and the target. You approve it once, before the pilot, after the
  agent shows you the exact scripts. Inside it, jobs go in without asking. A job past a limit
  comes back to you as a revised plan;
- spending Edison credits;
- writing to or deleting from the lab's shared package store;
- force-pushing, or deleting data;
- merging a pull request nobody reviewed, unless you told it to land it;
- anything on a live service;
- making private work public;
- wet-lab steps;
- editing your own document beyond what you asked for.

This list wins over everything else you say in the session. "I'm going to bed, land it" lets
the agent keep going on its own. It still stops at a Slurm job and waits for you, and you
find the script ready in the morning. "Close the issue" is not "merge it": while the fix is
not merged, the agent leaves the issue open and asks you.

## Where the rules came from

They are the lab's way of working, drawn from many real sessions and written as "the user",
so they apply to whoever types `/hq-mode`. Several playbooks build on
[pstack](https://github.com/cursor/plugins/tree/main/pstack)'s `poteto-mode`, the principles
come from pstack too, and the planning flow follows
[mattpocock/skills](https://github.com/mattpocock/skills). Both are MIT licensed.
