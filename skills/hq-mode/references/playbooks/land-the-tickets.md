# Land the tickets

**You own the landing. Subagents write the code; you verify, merge and clean up.**

1. Read the map or parent issue and its open tickets, blockers first. Note which tickets
   belong to another session and leave them alone.
2. One subagent per ticket, each in its own worktree. The brief: the ticket, the files, the host
   rule, "read `hq-mode`'s working-style page", and the paths of `tdd` and `code-review` to
   follow. Each commits its own work, comments and closes its ticket when it lands.
   The brief also says: one plain command per call, run from the worktree root; longer logic
   goes in a script file run as one command.
3. Decide cross-cutting choices centrally before the fan-out (names, caps, record formats).
4. Run independent tickets in parallel; serialise only on shared files.
5. Verify each subagent's claim yourself: run the gate, read the diff, check the artifact.
6. Collect into one PR unless the tickets are independent enough for one each. Merge only when
   the user has asked you to land it; otherwise the PR waits for a review.
7. Then **close-the-session**.

**Reply:** tickets landed, the PR, the gate result, and anything that became a new issue.
