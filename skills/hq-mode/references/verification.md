# Checking your own work

An agent that can check its own work can be trusted with more: a longer run, less
supervision, a bigger change. An agent that can't is trusted only as far as the user reads
every line. So before work the user steps away from, know how you will check it, and make
the check if there is none.

The lab has no verification skill and no `verify` task. Each repo's checks already exist:
`pixi run check` is the gate, and the repo's `AGENTS.md` lists every test lane outside it and
what each proves. That list is the repo's map of what can be checked.

## Before the first change

1. **Find the checks.** Read the gate and the lanes in `AGENTS.md`. Note which lane covers
   the code or the output you will change.
2. **Run them on the untouched tree.** A lane that is red before you start says nothing about
   your change. Record what was red, and leave it red unless it is your task.
3. **No lane covers it: build the smallest one first.** A small, real, subsampled fixture
   under `tests/data/`, its provenance in that directory's README, and a test that runs the
   command a user runs and compares the output with a pinned golden one. `tdd` carries the
   rule for goldens and tolerance. Add the lane to `AGENTS.md` if it sits outside the gate.
4. **A lane needs a GPU or a binary only the cluster has.** It runs inside an interactive job
   the user already holds. A new `sbatch` is on the always-pause list.

## A check worth trusting

- **It drives the real path.** The command, the pipeline entry or the function a user calls,
  never an internal helper or a test-only setter.
- **It can fail.** A test that would still pass if every call returned `None`, or if the step
  wrote an empty file, checks nothing. Assert the literal result: a known value, a pinned
  output, a row count.
- **It checks the effect, not the exit code.** Files written, rows kept, numbers in range;
  an exit code of 0 is a proxy.
- **Its evidence survives.** The command, the output path and the job ID go in the reply or
  the decision trail (`show-me-your-work.md`), and cleanup never deletes them.
- **It is worth its cost.** It proves something no other check proves, and it runs fast enough
  for its lane. Time the checks before and after your change, and give the increase in the
  reply when they grew. `tdd` carries the two anti-patterns: over-testing, and slow in the fast
  loop.

## A check over many records

A check that opens every record of a large store is never the default. A sample read in
full often tests more than a full pass that only glances at each record.

1. **List the questions first.** Before writing the check, write down what it answers.
2. **Answer each from the cheapest source that can.** Table metadata first: duplicate keys,
   counts, sizes. Then one directory listing against the table: every listed file on disk,
   no strays, sizes match. Then a random sample of records, each read in full and compared
   by checksum. A fault in the shared write code shows up in a sample.
3. **A full pass needs the user's yes,** and a stated repair or format change to justify it.
   In a session the user has left, run the sampled check and end on that question.
4. **State the expected cost before the check runs,** in the brief or the reply, and time a
   few iterations before the loop runs at full scale.
5. **Probe a long check in its first minutes,** like any job: CPU time, bytes read, the
   rate. A rate far below the estimate is a finding. Find its cause; don't wait it out.

## When a check and the code disagree

The check is stale, or the code regressed. Prove which before you change anything. Fix a
stale check and say so. Report a regression; never edit the check to make it pass. When you
add, retire or move a lane, update its line in `AGENTS.md` in the same change, so the map
stays true for the next agent.
