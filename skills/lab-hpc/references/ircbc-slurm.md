# ircbc Slurm — partitions and submitting

Which partition to ask for, and how to submit. Hosts, network, toolchain and the image store are in
`ircbc-hpc.md`; the rule about where commands run is `SKILL.md`'s.

## The Slurm client runs on the compute node (verified 2026-09-04)

Slurm is **18.08**, and the whole client — `squeue`, `sbatch`, `scancel`, `sinfo`, `scontrol`, `srun`,
`salloc` — is installed and working on `cpu0X`, where `scontrol ping` reports the controller UP. Managing the
queue is never a reason to ssh to the login node.

Two dialect notes for 18.08. `squeue --me` does not exist (`unrecognized option`) — use `squeue -u $USER`, and
expect other recent flags to be missing too. And `sbatch --test-only` does **not** submit, confirmed from both
login and compute: it prints the would-be job id and start node while the queue stays empty. That is the dry
run that pairs with the rule to show a script before submitting it.

If `sacct` reports `Problem talking to the database`, the accounting database is down or slow. That is
expected: fall back to `squeue -u $USER` for live jobs and `scontrol show job <jobid>` for one job's state.

## Partitions

No accounting or QOS caps are exposed (`sacctmgr` returns nothing), so no `--account` is needed. The
`compute_cpu` row was verified 2026-09-04, the other two 2026-07-04.

| Partition | Nodes | Per node | Limits |
| --- | --- | --- | --- |
| `compute_cpu` (default) | `cpu01`–`cpu08`, 448 CPUs | 56 CPUs, 125 GB | **`MaxNodes=2` per job**, `MaxTime=UNLIMITED`, **`DefaultTime=NONE`** |
| `compute_fat` | 2 fat nodes | 160 CPUs, ~1–2 TB RAM | Big-memory jobs |
| `compute_gpu_2080` | 2 nodes | 4× RTX 2080 | Habitually **drained** — treat ircbc as CPU-only unless `sinfo` says otherwise |

`DefaultTime=NONE` means a job submitted without `-t` has no walltime to fall back on, so **always pass `-t`**.
Nodes are shared and some are usually drained, so read `sinfo -p compute_cpu` for what is free right now
rather than assuming a node is idle.

Before long data work, apply the [`cluster-run` resource checks](../../hq-mode/references/playbooks/cluster-run.md).
Compare planned workers and threads with `scontrol show job` and current `sinfo` capacity.
Use this cluster's partitions and node limits above, not arc's preemptible tiers. Independent
jobs can use eligible free nodes after allocation, with concurrency bounded by CPU, memory
and shared I/O budgets.

## Submitting

Never submit outside an approved run plan (`SKILL.md`). Read-only probes —
`squeue`, `sinfo`, `sbatch --test-only` — need no permission.

```bash
sbatch --test-only -p compute_cpu -t 01:00:00 -c 8 job.sh   # dry run; prints the would-be job id and node
sbatch -p compute_cpu -t 01:00:00 -c 8 job.sh               # only after the user confirms the script
squeue -u $USER                                             # works from cpu0X; no --me on 18.08
srun -p compute_cpu -t 10 hostname                          # smoke test, when you hold nothing yet
```

## Running real work: `module load singularity`

Singularity is not on PATH; it is an OpenHPC module, on login and compute alike. A plain non-interactive ssh
command is enough — no login-shell wrapper needed:

```bash
ssh cpu02 'module load singularity/3.2.1 && singularity --version'
```

It is an old 3.x, so very new image features may not work. Modern binaries will not run on the host's
glibc 2.17, so anything real runs in a container, from an image already built into `$LIU_LAB_PACKAGES` —
compute nodes cannot pull. The pull, build and run recipes, including the required pixi-env activation and
bind mounts, are the **`lab-containers`** skill's, not this file's.
