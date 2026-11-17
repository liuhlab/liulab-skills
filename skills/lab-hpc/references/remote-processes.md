# Remote processes, waits and the Mac shell

How to find your node, start and stop a process over ssh, and wait on a job, plus the traps in
the Mac's own shell. Each recipe replaces a failure the data runs of November 2026 repeated.
Where each command may run is `SKILL.md`'s rule.

## Find the node you hold

The node changes on every resubmit, so `personal.md` records the standing job's name, never its
node. Find the node live, with one read-only call on the login node:

```bash
ssh arc 'squeue --me -h -t R -o "%i %j %N"'    # job id, job name, node
```

On ircbc, use `squeue -u $USER` (`ircbc-slurm.md`). Once you hold a node, run `squeue` there
instead. Never sweep node aliases (`arc-hpc.md` says why). Put the node name in every brief,
so no subagent looks for it again.

For a job you just submitted, `bash scripts/watch-job.sh -r <alias> <jobid>` returns once the job
runs and prints its node.

## Start a process detached

```bash
ssh <node> 'cd <dir> && setsid nohup <cmd> > <log> 2>&1 < /dev/null & echo $!'
```

- `< /dev/null` lets ssh return at once. Without it, `nohup <cmd> > <log> 2>&1 &` holds the
  session open until the tool's time limit.
- `setsid` gives the process a session of its own, so the printed PID is also its process
  group ID. Record it in your notes or on the run's issue.
- Start a multi-step command as a script (below), not as a nested `bash -c '…'`.

## Stop a process and wait for it

```bash
ssh <node> 'kill -TERM -- -<pgid>; timeout 60 tail --pid=<pid> -f /dev/null; pgrep -a -g <pgid> || echo gone'
```

- Kill the process group, not the PID, so the children die too. Killing Snakemake by its PID
  leaves a child step running. If `pgrep` still lists processes after the wait, send
  `kill -KILL -- -<pgid>`. A step that Snakemake sent to Slurm is a job: `scancel` it under the
  run plan.
- Never `pkill -f <pattern>`. The remote shell's own command line holds the pattern, so
  `pkill -f` kills the ssh session. A `pgrep -f` wait loop matches itself the same way.
- Never a broad `pkill -x <name>`. Nodes are shared, so it can kill a peer session's
  processes. Kill only the process groups you started.
- `tail --pid` waits for one PID without matching any pattern, and `timeout` caps the wait. Both
  are on the node, not on the Mac.

## Run a script, not nested quotes

Inline scripts in `ssh <node> '…'` break on nested quotes. Write the script to a local file in
your scratch folder, then send it:

```bash
ssh <node> bash -s -- <args> < script.sh   # a short script: bash reads it from standard input
rsync script.sh <node>:<dir>/              # a detached or long one: copy it, then run it by path
```

Under `bash -s`, a command in the script that reads standard input takes the rest of the script
as its input, so give that command `< /dev/null`. Project code still reaches a cluster through
git; this is for one-off helper scripts.

## Wait without sleeping

A `sleep` in a shell call blocks the session, and the harness may refuse it. A `sleep` moved
onto the server (`ssh <node> 'sleep 1800; …'`) dies when its connection resets. Watch a job with
`scripts/watch-job.sh` in the background:

- `-r` returns once the job runs, and the last line names its node.
- A file argument prints the file's size at each check. Add `-g` only when that file must
  grow between checks, such as a progress log. A log that goes quiet during a copy step needs no
  `-g`, or the watch ends on NO GROWTH while the job is fine.
- Exit 4, NO SSH, means ssh failed or came back empty, so the job's state is unknown, not
  ended. Ask `squeue` on another node you hold. Exit 5, NO JOB,
  means ssh worked but no Slurm command knew the job.
- Point it at a node another job holds, such as the standing job's. On arc a node refuses
  you once your last job there ends (`arc-hpc.md`), so a watcher on the job's own node ends on
  NO SSH, not on DONE.
- Who runs the watchers, and how many:
  [`hq-mode`'s working style](../../hq-mode/references/working-style.md#delegation).

## The Mac's shell

- **The local shell is zsh.** Quote every URL (`?` and `*` are globs). An unquoted `$var` is not
  split into words, so use an array. End a probe that may find nothing with `|| true`, so an
  empty result doesn't hide real errors.
- **macOS has no `timeout`.** Bound ssh with `-o ConnectTimeout=10`, and put `timeout` inside
  the remote command, where the node has it.
- **`rm` and `cp` may be aliases for `rm -i` and `cp -i`,** which wait for an answer until the
  tool's limit. Call `command rm` and `command cp`.
