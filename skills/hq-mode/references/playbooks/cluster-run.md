# Cluster run

**You own the run's correctness and the cluster's goodwill.** `lab-hpc` owns every cluster
fact; read it first.

## Design long data work before coding

Require correctness, robustness, resumability and efficient resource use. Put these
requirements in implementer briefs, with the planned units and how each is verified.

- Divide long work into bounded units that can restart independently. Apply
  [`make-operations-idempotent`](../principles/make-operations-idempotent.md) for atomic
  outputs, validated completion and safe reuse after interruption or changed inputs.
- Derive indexes or intermediate data once, then reuse them for selections and downstream
  builds. Avoid a full snapshot scan on every rerun. Stream large inputs and bound chunk
  sizes and buffers so each worker fits its memory budget.
- Split at valid record boundaries. Check whether the format and compression permit
  independent reads before splitting byte ranges. Consider parallel parsing or
  decompression where the measured cost warrants it, without requiring a framework.

## Plan and run

1. `lab-hpc` step 0. Work happens on a compute node, never the login node, and the host rule
   goes into every subagent brief.
2. Check for prepared inputs: registered genomes and indexes, the shared data root, the lab's
   data packages. Don't re-download what is there.
3. Write the sbatch scripts: one unit as a pilot (one sample, one chromosome, a small
   subsample), then the full set. Outputs and logs go to scratch or the project's output root,
   never the home directory and never the reference data root.
4. Show the exact scripts and wait for the user's yes before any `sbatch` or `srun`, the pilot's
   included. "Land it" and "going to bed" don't change this: prepare everything else, then end
   the turn on the question.
5. Run the pilot. Time each phase, observe CPU use and I/O, and identify the dominant cost
   with [`explain-the-number`](../principles/explain-the-number.md). Use those measurements
   to choose what to parallelize. Keep fast steps simple. Give the user the full-run
   estimate and resource plan before scaling.
6. Before starting long work, compare expected workers and threads with allocated CPUs,
   memory and current free capacity from Slurm. A pass taking more than a few minutes on
   one core in a multicore allocation needs a measured justification or a revised plan.
   Budget workers times threads per worker, memory per worker and shared I/O. Consider
   parallel code within a job and independent jobs across eligible nodes or partitions,
   within scheduler limits. Choose a partition using resumability, capacity and cost from
   the cluster's Slurm reference. Free capacity requires an allocation before use.
   Fan out separate units as jobs or an array, with concurrency bounded by those budgets.
   Check each unit as it finishes. If I/O or another measured limit favors serial work,
   record that reason and size the allocation accordingly.
7. On a misbehaving job, name the symptom and propose the workaround (exclude a node, resubmit
   one unit), and wait for a yes. Never `scancel` a job you didn't start.
8. Verify outputs, not exit codes: sizes, counts, a spot check against the pilot.

**Reply:** what ran where, the pilot's numbers and the extrapolation, per-unit status as a
checklist, outputs and their location, anything left queued.
