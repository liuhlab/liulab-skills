# Develop on a small example

Before code meets a large input or a slow job, get it working on a small one. A full run
measures working code; it is not the place to find a path bug.

1. Before the first run, pick or make the smallest concrete example that exercises the code:
   an existing test fixture first, otherwise a seeded sample of the real data.
2. Write the first version, every fix and every update against it, until the code runs clean
   and the outputs look right. One loop takes seconds to minutes.
3. Name what only the full data can answer: scale limits, run time, memory, rare records. Run
   the full data for that, once.
4. When comparing options on the full data, test them on one slice first and drop the losers.

On a cluster, this loop comes before the [`cluster-run`](playbooks/cluster-run.md) pilot and
rounds, which measure code that already works. That playbook's rules hold for the small
example too: no login node, and no new `sbatch` or `srun` outside a run plan.
