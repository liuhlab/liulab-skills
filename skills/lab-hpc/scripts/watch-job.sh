#!/usr/bin/env bash
# Watch one Slurm job until it ends, or with -r until it starts running. Run it
# in the background, one watcher per job; it replaces `sleep` polling loops.
#
# Each check is ONE ssh call: the job's state and node (squeue, then scontrol
# show job, then sacct, so a down accounting database is not fatal) and, when
# a file is given, its size. Contains no hostnames, usernames, or keys — the
# alias resolves through the user's own ssh config.
#
# Usage: watch-job.sh [-r] [-g] [-i seconds] [-n checks] <alias> <jobid> [file]
#   alias       lab ssh alias of a node that runs the Slurm client
#   jobid       the job to watch
#   file        optional: a file on the remote (absolute, or relative to the
#               remote home) whose size each check prints
#   -r          return once the job runs, naming its node (exit 0)
#   -g          the file must grow: a running job whose file did not grow for
#               <checks> checks in a row ends the watch. Leave it off for a log
#               that may go quiet, such as during a copy step
#   -i seconds  time between checks (default 60)
#   -n checks   checks in a row that end the watch: no growth (with -g), ssh
#               failures, or a job no Slurm command knows (default 5)
#
# Output: one line per check, "<time> state=<STATE> size=<bytes>" (size -1:
#         no such file) or "<time> ssh failed (...)", then a final line naming
#         the outcome.
# Exit:   0 DONE       the job completed
#           RUNNING    with -r: the job runs; the line names its node
#         1 FAILED     the job ended any other way (failed, cancelled,
#                      timeout, out of memory, node failure, preempted)
#         2            usage error
#         3 NO GROWTH  with -g: the job runs but the file did not grow for
#                      <checks> checks in a row
#         4 NO SSH     ssh failed or came back empty for <checks> checks in a
#                      row. The job's state is unknown, NOT ended: ask
#                      squeue on another node you hold
#         5 NO JOB     ssh worked, but no Slurm command knew the job for
#                      <checks> checks in a row (a wrong job id, or it ended
#                      while the accounting database was down)

set -u

usage() { sed -n '/^# Usage:/,/^$/s/^# \{0,1\}//p' "$0" >&2; exit 2; }

INTERVAL=60
CHECKS=5
UNTIL_RUNNING=false
MUST_GROW=false
while [ $# -gt 0 ]; do
  case "$1" in
    -r) UNTIL_RUNNING=true; shift ;;
    -g) MUST_GROW=true; shift ;;
    -i) [ $# -ge 2 ] || usage; INTERVAL="$2"; shift 2 ;;
    -n) [ $# -ge 2 ] || usage; CHECKS="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown arg: $1" >&2; usage ;;
    *) break ;;
  esac
done
[ $# -ge 2 ] && [ $# -le 3 ] || usage
ALIAS="$1" JOB="$2" FILE="${3:-}"
if $MUST_GROW && [ -z "$FILE" ]; then echo "-g needs a file" >&2; exit 2; fi

printf '%s' "$INTERVAL" | grep -Eq '^[0-9]+(\.[0-9]+)?$' && [ "$INTERVAL" != 0 ] \
  || { echo "-i needs a positive number of seconds" >&2; exit 2; }
printf '%s' "$CHECKS" | grep -Eq '^[1-9][0-9]*$' \
  || { echo "-n needs a whole number of checks, 1 or more" >&2; exit 2; }
printf '%s' "$JOB" | grep -Eq '^[0-9]+(_[0-9]+)?$' \
  || { echo "jobid must be a Slurm job id, got: $JOB" >&2; exit 2; }
case "$ALIAS" in -*|*[[:space:]]*|'') echo "bad alias: $ALIAS" >&2; exit 2 ;; esac

# The remote side is plain POSIX sh run by ssh's non-interactive shell: the
# Slurm client commands are system-installed, so no login shell is needed.
# squeue's %N is the job's node list, empty while it pends. sacct -P prints
# the whole state: a fixed-width column would cut OUT_OF_MEMORY to
# OUT_OF_ME+, and the first word of "CANCELLED by <uid>" is the state.
q="'$(printf '%s' "$FILE" | sed "s/'/'\\\\''/g")'"
REMOTE="j=$JOB f=$q
$(cat <<'EOF'
r=$(squeue -h -j "$j" -o '%T %N' 2>/dev/null | head -n 1)
s=${r%% *}
n=${r#"$s"}
[ -n "$s" ] || s=$(scontrol show job "$j" 2>/dev/null | sed -n 's/.*JobState=\([A-Z_]*\).*/\1/p' | head -n 1)
[ -n "$s" ] || s=$(sacct -n -P -X -j "$j" -o State 2>/dev/null | awk 'NF{print $1; exit}')
echo "state=${s:-UNKNOWN}"
echo "node=${n# }"
if [ -z "$f" ]; then :; elif [ -e "$f" ]; then echo "size=$(wc -c < "$f" | tr -d ' ')"; else echo size=-1; fi
EOF
)"

prev=""
stalled=0
nossh=0
nojob=0
while :; do
  # stderr joins the reply, so a failed check can name ssh's own error. The
  # keepalives end a connection that dies mid-check instead of hanging on it.
  out=$(ssh -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=4 "$ALIAS" "$REMOTE" 2>&1)
  rc=$?
  state=$(printf '%s\n' "$out" | sed -n 's/^state=//p' | head -n 1)
  size=$(printf '%s\n' "$out" | sed -n 's/^size=//p' | head -n 1)
  node=$(printf '%s\n' "$out" | sed -n 's/^node=//p' | head -n 1)

  # ssh's own failures exit 255. No state line means the remote command never
  # ran or its reply was lost. Either way the job's fate is unknown, so this
  # never counts as the job ending.
  if [ $rc -eq 255 ] || [ -z "$state" ]; then
    why=$(printf '%s\n' "$out" | grep -v '^\(state\|node\|size\)=' | grep . | tail -n 1)
    [ -n "$why" ] || why="empty reply"
    echo "$(date '+%H:%M:%S') ssh failed (exit $rc: $why)"
    nossh=$((nossh + 1))
    if [ "$nossh" -ge "$CHECKS" ]; then
      echo "NO SSH: $CHECKS checks in a row could not reach $ALIAS; job $JOB may still run (last: $why)"
      exit 4
    fi
    sleep "$INTERVAL"
    continue
  fi
  nossh=0
  echo "$(date '+%H:%M:%S') state=$state size=${size:--}"

  case "$state" in
    COMPLETED)
      echo "DONE: job $JOB completed"; exit 0 ;;
    FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED)
      echo "FAILED: job $JOB ended $state"; exit 1 ;;
    UNKNOWN)
      nojob=$((nojob + 1))
      if [ "$nojob" -ge "$CHECKS" ]; then
        echo "NO JOB: ssh worked, but no Slurm command knew job $JOB for $CHECKS checks (a wrong job id, or it ended while accounting was down)"
        exit 5
      fi ;;
    *)
      nojob=0
      if $UNTIL_RUNNING && [ "$state" = RUNNING ]; then
        echo "RUNNING: job $JOB runs on ${node:-an unnamed node}"; exit 0
      fi
      if $MUST_GROW && [ "$state" = RUNNING ]; then
        if [ -n "$prev" ] && [ "$size" -le "$prev" ] 2>/dev/null; then
          stalled=$((stalled + 1))
        else
          stalled=0
        fi
        prev="$size"
        if [ "$stalled" -ge "$CHECKS" ]; then
          echo "NO GROWTH: $FILE stayed at $size bytes for $CHECKS checks while job $JOB ran"
          exit 3
        fi
      fi ;;
  esac
  sleep "$INTERVAL"
done
