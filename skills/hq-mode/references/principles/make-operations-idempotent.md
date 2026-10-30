# Make Operations Idempotent

Design operations so they converge to the correct state regardless of how many times they run or where they start from. Every state-mutating operation should answer: "What happens if this runs twice? What happens if the previous run crashed halfway?"

**Why:** Commands, lifecycle operations, and processing loops run where crashes, restarts, and retries are normal. If partial state changes the next run's outcome, every restart becomes a debugging session.

**The pattern:**

- Convergent startup: scan for existing state, clean stale artifacts, adopt live sessions
- Content-based cleanup: compare by content equivalence, not creation order
- Self-healing locks: use PID-based stale lock detection
- Locks on a shared filesystem: a PID means something on one node only, so a live lock held by a job on another node looks stale and gets stolen. A lock names its host and job. Prefer per-job outputs, which need no lock.
- Atomic outputs: write to a temporary name, then rename. Skip an output only if it exists and validates, never because it exists: a requeued job otherwise counts a half-written file as done.
- Reusable data: record the input identity and relevant code and configuration with each completed unit or derived index. Reuse only when those match and the output validates. Rebuild affected units when they change, and restart interrupted units without treating temporary files as finished work.
- Idempotent scheduling: failed work respawns cleanly, fresh input regenerated after each cycle

**The test:**

1. What happens if this runs twice in a row?
2. What happens if the previous run crashed at every possible point?
3. Does re-execution converge to the same end state?

If any answer is "it depends on what state was left behind," the operation needs a reconciliation step.
