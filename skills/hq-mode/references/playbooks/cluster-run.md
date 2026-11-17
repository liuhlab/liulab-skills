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
  builds. Stream large inputs and bound chunk sizes and buffers so each worker fits its
  memory budget.
- Split at valid record boundaries. Check whether the format and compression permit
  independent reads before splitting byte ranges. Consider parallel parsing or
  decompression where the measured cost warrants it, without requiring a framework.
- Size every pass to the change: a rerun, check or copy touches only new or changed units,
  and a whole-store pass needs the user's yes
  ([verification](../verification.md#size-the-work-to-the-change)).

## Plan and run

1. [Develop on a small example](../small-example.md) first.
2. `lab-hpc` step 0. Work happens on a compute node, never the login node, and the host rule
   goes into every subagent brief.
3. Agree the target before building anything: the measure that counts (items fetched per
   hour, wall time to the full set, cost per sample) and its acceptable range. Ask the user
   when no source settles it.
4. Ask for one [work folder](#work-folder) for the run, suggesting one under the project's
   output root. Every script, log, temp file and output of the run lives there, never in the
   home directory or the reference data root.
5. Check for prepared inputs: registered genomes and indexes, the shared data root, the lab's
   data packages. Don't re-download what is there.
6. Write the sbatch scripts: one unit as a pilot (see [Pilot design](#pilot-design)), then
   the full set. Ask Slurm for generous memory when `sinfo` shows the nodes have it free: a
   job that fails on a tight request costs more than idle headroom.
7. Propose the run plan, with the exact scripts in the reply, and wait for the user's yes
   before any `sbatch` or `srun`, the pilot's included. The plan states the work folder, the
   partitions, the most CPU, memory and wall time per job, the most jobs at once, and the
   target measure with its acceptable range. Size it for the full run, so one yes covers the
   pilot and every round. Post the approved plan on the run's issue, or in the work folder's
   README when there is no issue, and quote it word for word in every subagent brief. Inside
   it, submit and cancel the plan's own jobs without asking. The plan does not cover a write
   to shared data or the shared package store. A job past any limit, a pilot estimate past
   one, cancelling a job the plan did not start, or such a write goes back to the user: a
   revised plan, or a yes for that step. The plan ends with the run. With no plan, "land it"
   and "going to bed" change nothing: prepare everything else, then end the turn on the
   question.
8. Run the pilot. Time each phase, observe CPU use and I/O, and identify the dominant cost
   with [`explain-the-number`](../principles/explain-the-number.md). If one step dominates,
   ask whether the run needs it before making it faster. Use those measurements to choose
   what to parallelize. Keep fast steps simple. Report the full-run estimate to the user and
   scale within the plan.
9. Before starting long work, compare expected workers and threads with allocated CPUs,
   memory and current free capacity from Slurm. A pass taking more than a few minutes on
   one core in a multicore allocation needs a measured justification or a revised plan.
   Budget workers times threads per worker, memory per worker and shared I/O. Consider
   parallel code within a job and independent jobs across eligible nodes or partitions,
   within scheduler limits. Choose a partition using resumability, capacity and cost from
   the cluster's Slurm reference. Free capacity requires an allocation before use. Fan out
   separate units as jobs or an array, with concurrency bounded by those budgets. Check each
   unit as it finishes. If I/O or another measured limit favors serial work, record that
   reason and size the allocation accordingly.
10. Scale up in rounds sized to the question. See [Rounds](#rounds).
11. Check each new job in its first minutes: state, node, the first output lines and the rate
    against the pilot's. Then the main session watches it in the background with `lab-hpc`'s
    `scripts/watch-job.sh`, one per job. A job slower than the pilot predicts gets its cause
    found at once, before it burns its time budget.
    [Unattended jobs](../unattended-jobs.md) covers a job that outlives the session.
12. On a misbehaving job, name the symptom and propose the workaround (exclude a node, resubmit
    one unit), and wait for a yes unless the plan covers it.
13. Verify outputs, not exit codes: sizes, counts, a
    [sampled check](../verification.md#a-check-over-many-records) against the pilot.

## Pilot design

A pilot answers one question: what the full run will cost and where it will break.

- **Agree the pilot's time budget first,** with the user, before choosing its size. A pilot
  that runs for hours is a round, not a pilot.
- **Use the smallest sample that answers the question.** Nest the samples: each step's sample
  contains the last one's, and the same items are used across steps, so steps compare.
- **Network or I/O pilots:** read the server's documented limits first (requests per second,
  concurrent connections, daily quota). Measure batch size and concurrency against those
  limits, stepping up until throughput stops rising or errors start. Count retries, back-off
  waits, throttling responses and timeouts beside the throughput: a fast number that hides
  throttling is wrong. The [benchmark checklist](../benchmark-checklist.md) applies to every
  number the pilot reports.
- **Don't over-test.** Stop once the question is answered. One more setting that cannot
  change the plan is not worth its time.

## Rounds

Whether to run intermediate rounds, and how big, is a judgement, not a rule. Size each
round to what is still unknown at the next scale: a rate limit that shows only under
sustained load, the spread of file sizes, memory at scale, a node type the pilot missed. A
cheap, well-understood job can go from the pilot straight to the full run. 1% → 10% → 100%
is an example, not a default.

- Each round skips the items already done, and checks speed, errors and load against the
  last round before the next one starts.
- A fresh subagent runs each round, reports its job IDs, hands off a summary in the per-round
  report format below and stops.
- The final report names the rounds chosen and why.

## Work folder

Clean the folder as the run goes: delete temp files and superseded logs once a round is
verified. Anything kept long term gets a short `README.md` saying what each part holds, which
run made it and how.

## Per-round report

- **Progress:** items done, failed and left, per phase.
- **Estimate:** the best full-run estimate per phase, with what it is measured from.
- **What would change it:** the open unknowns, such as a rate limit not yet hit or a large
  file tail not yet reached.

**Final reply:** what ran where, the pilot's numbers and the extrapolation, the rounds chosen
and why, per-unit status as a checklist, outputs and their location, anything left queued.
