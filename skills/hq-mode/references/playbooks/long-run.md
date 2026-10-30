# Long run

**You own the exit condition.**

1. State done as a checkable predicate before the first step.
2. Wake on events, not guesses: the end of a Slurm job, a merge, CI. A long heartbeat is the
   fallback.
3. Each step makes the smallest change the evidence justifies, checks it against the predicate,
   and keeps or reverts it.
4. Log every step per `references/show-me-your-work.md`.
5. Mid-run problems are yours: fix them in their own change. Surface only an always-pause item,
   a real preference call, or a dead end.
6. Pausing: a `wip:` commit and a handoff note written by following the
   [`handoff`](../../../handoff/SKILL.md) skill's file, then stop. A subagent pauses after
   each unit, and when the orchestrator asks it to wrap up at its deadline or around half its
   context. Picking up: read the trail and redo nothing.

**Reply:** the predicate, steps run, what landed, what was reverted, the final state.
