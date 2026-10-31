---
search:
  exclude: true
---

# Slurm approval is per run plan, not per job

The user approves a run plan once, before the pilot: the run it covers, its work folder, the
partitions, the most CPU, memory and wall time per job, the most jobs at once, and the target
measure with its acceptable range. A pilot estimate past any limit means a revised plan. Inside it, the agent and its subagents
submit jobs and cancel the jobs the plan started without asking. A job outside the plan,
cancelling a job the plan did not start, and a write to shared data still pause. The
approval ends with the run.

## Why

The rule had been "show the exact script and wait for a yes before every `sbatch`". On a
two-day metadata download the user overrode it by hand in four sessions, and every pilot and
round waited on them. The user was approving the same resources again and again, not
anything new per job. What they do need to see is the envelope: how much of the shared
cluster the run can take, and for how long.

## Considered options

- **Per job, as before.** Safe, but it made the user the bottleneck of every round, and the
  user worked around it with session overrides that carried no limits at all.
- **A session override ("you may submit")**. What the user did by hand. It has no cap, so a
  bad loop can fill a partition.
- **A run plan.** Chosen: the cap is explicit, written down, and a job outside it pauses.

## Consequences

The concurrency cap is the only limit on how much of a partition a plan can take, so a plan
without one is not a plan. The `hq-pause-sbatch` eval still holds: "going to bed" with no plan
pauses.
