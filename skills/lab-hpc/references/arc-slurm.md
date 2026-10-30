# arc Slurm — partitions and submitting

Which partition to ask for, and how to submit. Hosts, network, toolchain and storage are in
`arc-hpc.md`; the rule about where commands run is `SKILL.md`'s.

## The Slurm client runs on the compute node (verified 2026-09-04)

Slurm is modern (**25.x**), and the whole client — `squeue`, `sbatch`, `salloc`, `scancel`, `sinfo`,
`sacct`, `scontrol`, `sstat`, `srun` — is in `/usr/bin` on the compute nodes and works there, so
managing the queue is never a reason to ssh to the login node. `sbatch --test-only` runs there too,
reporting when a job *would* start without submitting — a safe dry run.

## Partitions (verified 2026-07-04)

Lab members submit under account `zhoulab` (QOS `normal`), so you rarely need `--account`.
`DefaultTime` is 12 h on every partition, so **always set `--time`**. Jobs are single-node
(`MaxNodes=1`) except on the priority partition; `PreemptMode=REQUEUE` on the preemptible tiers.

| Partition | Wall limit | Purpose / limits |
| --- | --- | --- |
| `cpu` (default) | 5 d | Interactive CPU. QOS `cpu_interact`: ≤ 64 CPUs, **≤ 2 running jobs per user**, ≤ 4 GB per CPU. |
| `cpu_batch` | 14 d | CPU batch. QOS `cpu_batch`: ≤ 20 running / 200 queued per user. |
| `gpu` | 1 d | Interactive GPU; ≤ 32 CPUs per node per job; ≤ 10 GB per CPU. |
| `gpu_batch` | 14 d | GPU batch. |
| `*_high_mem` | 14 d | The same tiers on the ~2 TB nodes. |
| `preemptible` | 14 d | Big fan-outs, **GPU available**; requeued at any time. QOS `preempt`: ≤ 100 running / 512 queued. |
| `cpu_preemptible` | 14 d | The same, but **CPU-only**. QOS `preempt`. |
| `quick_preemptible` | 2 h | Short tests and smoke jobs (**GPU available**). QOS `quick_preempt`: ≤ 4 running / 8 queued. |
| `zhoulab_gpu_priority` | 14 d | **Lab-reserved**, account `zhoulab` only: one node, ≤ 176 CPUs, 4 GPUs, `MaxMemPerCPU=4096`, `PriorityTier=1000`, `PreemptMode=REQUEUE` (verified 2026-09-04). Long-lived reservations live here. |

Free: `zhoulab_gpu_priority` and the preemptible tiers; the other GPU partitions are billed extra, so
default to the free ones. For GPU work try **`zhoulab_gpu_priority` first** — the lab's own node starts
work far sooner than the contended shared queues; confirm with `sbatch --test-only`, which prints the
projected start time. Jobs there are preemptible, so a foothold can vanish mid-task — re-submit and
land again rather than drifting back to the login node.
Requeue-tolerant fan-outs: `preemptible` (GPU) or `cpu_preemptible`; smoke tests `quick_preemptible`.

Before long data work, apply the [`cluster-run` resource checks](../../hq-mode/references/playbooks/cluster-run.md).
Compare eligible partitions with `sinfo` and inspect the held allocation with `scontrol show job`.
The priority row's `PreemptMode=REQUEUE` means neither that partition nor a held node guarantees
an uninterrupted pass. Make such passes resumable, or justify the bounded work that would
repeat after interruption.

## Submitting

`sh_gpu [1-4] [srun opts]` and `sh_dev [srun opts]` wrap an interactive `srun`; `sh_gpu` asks for 1 GPU +
8 cores + 80 GB by default. Both default to the shared, contended partitions (`sh_gpu` to `gpu`), so pass
`--partition zhoulab_gpu_priority` to land on the lab node. They exist on compute nodes too, so a held
node can seed a second one.

**Don't reach for `ssh chimera-gpu` / `chimera-cpu` as an agent.** They `RequestTTY` and `RemoteCommand`
the wrappers on the login host: you queue on a contended partition and hold an interactive TTY that dies
with the ssh connection. Fine for a human at a keyboard, wrong for an agent.

```bash
sbatch --partition=quick_preemptible --time=00:05:00 --wrap=hostname  # cheap smoke test
squeue --me                                            # then scancel <jobid> if still queued
mkdir -p sbatch                                        # the log paths below need it
sbatch --job-name=reserve --partition=zhoulab_gpu_priority --time=5-00:00:00 --cpus-per-task=24 \
  --mem-per-cpu=6G --gpus=1 --output=sbatch/gpu.%j.output.log --error=sbatch/gpu.%j.error.log \
  --wrap 'sleep infinity'
```

`sbatch` inherits the submitting shell's environment, so whatever the payload calls must be on PATH
*there* — otherwise give an absolute path (see `~/.claude/lab/personal.md`).
