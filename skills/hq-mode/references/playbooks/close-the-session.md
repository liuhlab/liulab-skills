# Close the session

**You own a session that leaves nothing open.**

1. Land your own work only: commit, PR, merge where the user asked you to land it, close the
   issues it covers. A PR nobody reviewed, with no "land it", stays open and goes in the reply.
2. Delete merged branches, local and remote. Remove your worktrees and scratch files. Keep only
   the default branch and any docs branch. Then run `hq-mode`'s
   `scripts/stale-worktrees.sh --remove` from the repo. It removes, across the folder holding
   your clones, every worktree that holds no work and has sat a day, so what a session that
   died before its own close left behind goes too. A `keep` line on your own worktree is
   unlanded work: name it in the reply.
3. On every host, delete each file and folder your subagents' reports list, such as clones,
   environments and temporary scripts, then list the parent folder to check they are gone. A
   run's outputs are data, not scratch: they stay. Stop every finished subagent and background
   shell, each process the reports list, and each `orphan` the sweep printed that your session
   started; name the other orphans in the reply.
4. Sync the local clone. Tag and release where the repo's flow says so.
5. Fix what you found in this session that found it. File a new issue only for large work or a
   decision the user must make, sized and linked to its parent.
6. Write each lesson where it lasts, as `hq-mode`'s row for a correction from the user says:
   memory holds only a personal preference.

**Reply:** "Anything left?" answered yes or no first, then what the user still has to do.
