---
name: lab-hpc
description: >-
  Lab HPC clusters (arc/chimera GPU, ircbc CPU) and remote compute on them. Use whenever a task
  involves ssh to a lab server, Slurm jobs (sbatch, srun, squeue, salloc), compute or login nodes,
  running code remotely, or moving files to a cluster. Read it BEFORE the first ssh of a session:
  it decides where every command runs. Covers the zhoulab_gpu_priority partition, syncing code
  local -> GitHub -> remote, host aliases, choosing a cluster, per-user config, and the rule that
  work belongs on a compute node, never on the shared login node.
---

# Lab HPC clusters & remote-compute workflow

Detail is in `references/`: `*-hpc.md` for hosts, network and storage; `*-slurm.md` for
partitions and submitting; `remote-processes.md` for processes, waits and the Mac shell;
`browser-login.md` for a tool's browser login.

Before designing a large-data pipeline or starting a long data job, read and apply
[`cluster-run`](../hq-mode/references/playbooks/cluster-run.md), including on a held node.

## Step 0 — before the first ssh

1. Run `bash scripts/check-hpc-config.sh` (`--live` also tests ssh). If the cluster the task needs
   is `NOT CONFIGURED`, **refuse**: name the missing aliases, point at the README's "Per-user
   config", never improvise with raw addresses or keys, and resolve hosts from `~/.ssh/config` only.
   `config dir: OLD LOCATION` → **refuse** too, and relay the printed fix for the user to run.
   Once you know your node, `--live --node <alias>` checks that pixi runs there.
2. Read `~/.claude/lab/personal.md` — usernames, code dirs, the standing job, sbatch
   defaults. It **overrides** this skill. Say so if it is absent.
3. Ask which cluster unless context pins it down. Then develop locally, push to GitHub,
   and `git pull` on the remote — code reaches a cluster through git, not scp.

## Shell and environment

- **The Mac shell is zsh,** with no `timeout` and maybe `rm -i`: see `remote-processes.md`.
- **Run project code through pixi,** not the system `python3`; on arc by its full path,
  `$HOME/.pixi/bin/pixi`, since `bash -lc` does not find it. Other tools in your arc home
  (uv, conda, mamba) need a login shell (`arc-hpc.md`).

## Work on a compute node, not the login node

A login node is one shared machine per cluster, and a fan-out of "small" agent commands takes it
down. Even a one-liner belongs on the compute node, where the whole Slurm client runs.
Only **three uses** justify a login node:

1. **You hold no job:** only a login node can submit the first one.
2. **The compute node lacks what you need:** on ircbc, internet, `git` and a route to arc
   (`ircbc-hpc.md`). On **arc, nothing**: its compute nodes have internet and a full toolchain,
   so once you hold one, never leave.
3. **Finding the node you hold:** one read-only `squeue --me` (ircbc: `squeue -u $USER`).

## SOP — take a foothold, then keep it

1. **Find your node live.** Unless your brief names it, use the `squeue` in
   `remote-processes.md`; never sweep node aliases. Name the node in every brief.
2. **Land and stay.** Put each probe's commands into one ssh call: every call is a connection
   through the login node. If ssh hangs after a network drop, clear the stale shared connection
   with `ssh -O exit <alias>`, then retry once.
3. **No node anywhere?** Only then use the login node, and only to fix that: show the exact
   sbatch/salloc, get confirmation, submit, poll to RUNNING, ssh in, and leave. If a foothold
   is preempted, repeat this step.

## Watching a job

The main session owns every wait, one watcher per job; a subagent reports its job IDs and never
waits. Run `bash scripts/watch-job.sh <alias> <jobid> [file]` in the background, never `sleep`,
locally or on the node. `-h` lists its modes and exits; `remote-processes.md` says where to point it.

## Hard rules

- **Work on a compute node; the login node has exactly the three uses above.**
- **No sbatch/srun outside an approved run plan.** Approved before the pilot, sized for the
  full run, scripts shown: work folder, partitions, most CPU, memory and wall time per job,
  most jobs at once, target measure and range. Inside it, submit and cancel its own jobs
  unasked. A job or pilot estimate past a limit needs a revised plan. Cancelling a job the
  plan did not start, and writes to shared data or the shared package store, need a yes.
  Post it on the run's issue (or work folder README); quote it verbatim in subagent briefs.
  It ends with the run. No plan: a yes per script. Probes like `squeue` need none.
- **Reachable never means permitted.** ircbc lets you ssh to a node you hold no job on; working
  there steals from the scheduler. Hold an allocation.
- **Never `pkill -f`;** stop only your own process group.
- If ssh to `ircbc` hangs, **stop and tell the user to check the VPN**. arc is not behind it.
  Never retry in a loop.
