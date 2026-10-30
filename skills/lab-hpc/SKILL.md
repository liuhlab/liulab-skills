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

Per-cluster detail sits in `references/`: `arc-hpc.md` and `ircbc-hpc.md` for hosts, network and storage; `arc-slurm.md` and `ircbc-slurm.md` for partitions and submitting.

Before designing a large-data pipeline or starting a long data job, read and apply
[`cluster-run`](../hq-mode/references/playbooks/cluster-run.md), including on a held node.

## Step 0 — before the first ssh

1. Run `bash scripts/check-hpc-config.sh` (`--live` also tests ssh). If the cluster the task needs
   is `NOT CONFIGURED`, **refuse**: name the missing aliases, point at the README's "Per-user
   config", never improvise with raw addresses or keys, and resolve hosts from `~/.ssh/config` only.
   `config dir: OLD LOCATION` → **refuse** too, and relay the printed fix for the user to run.
2. Read `~/.claude/lab/personal.md` — usernames, code dirs, the standing job, sbatch
   defaults. It **overrides** this skill. Say so if it is absent.
3. Ask which cluster unless context already pins it down. Then develop locally, push to GitHub,
   and `git pull` on the remote — code reaches a cluster through git, not scp.

## Work on a compute node, not the login node

Get onto a compute node and stay there. A login node is a doorway, not a workspace: one shared
machine per cluster, and a fan-out of "small" agent commands is what takes it down. `ssh arc
'<cmd>'` is the wrong reflex even for a one-liner — and rarely needed, since the whole Slurm
client (`squeue`, `sbatch`, `scancel`, `sinfo`) runs on the compute node. There are **two
reasons, and only two**, to run anything on a login node:

1. **You hold no job**, so no compute node is yours yet. Only a login node can submit that
   first one.
2. **The compute node lacks what you need.** On ircbc that means internet (its compute nodes
   are offline) and `git` (not installed there). On **arc it means nothing at all** — arc
   compute nodes have direct internet and a full toolchain, so once you hold one, never leave.

## SOP — take a foothold, then keep it

1. **Find and reuse the node you already hold.** The lab parks a long-lived idle GPU job on arc for this.
   Check `personal.md`, then probe aliases with `ssh -o BatchMode=yes -o ConnectTimeout=10
   <alias> true` — probes fail fast, so sweeping every alias is cheap. Judge by exit status, not stderr.
2. **Land and stay.** On arc, wrap commands in a login shell — `ssh <node> 'bash -lc "…"'` — or
   `pixi` and other user-installed tools are invisible.
3. **No node anywhere?** Only then use the login node, and only to fix that: show the exact
   sbatch/salloc, get confirmation, submit, poll to RUNNING, ssh in, and leave. Footholds are
   preemptible; if one dies, repeat this step.

## Watching a job

Poll a job only with `bash scripts/watch-job.sh <alias> <jobid> [file]`, run in the background,
never a `sleep` loop. Each check is one ssh call; it exits 0 done, 1 failed, 3 when the file
stops growing, 4 when it gets no answer (`-h` for flags). Every job-watching subagent's brief
names it.

## Hard rules

- **Work on a compute node; the login node has exactly the two uses above.** Nothing else.
- **Never submit sbatch/srun without showing the exact script and getting confirmation.**
  Read-only probes like `squeue` and `sbatch --test-only` need no permission.
- **Reachable never means permitted.** ircbc lets you ssh to a node you hold no job on; working
  there steals from the scheduler. Hold an allocation, and never scancel a job you didn't start.
- If ssh to `ircbc` hangs, **stop and tell the user to check the VPN** (atrust, managed by
  hand). arc is not behind it. Never retry in a loop.
