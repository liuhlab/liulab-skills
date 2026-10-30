#!/usr/bin/env bash
# Watch one Slurm job until it ends or its output stops growing. Run it in the
# background; it replaces `sleep` polling loops.
#
# Each check is ONE ssh call: the job's state (squeue, then scontrol show job,
# then sacct, so a down accounting database is not fatal) and, when a file is
# given, its size. Contains no hostnames, usernames, or keys — the alias
# resolves through the user's own ssh config.
#
# Usage: watch-job.sh [-i seconds] [-n checks] <alias> <jobid> [file]
#   alias       lab ssh alias of a node that runs the Slurm client
#   jobid       the job to watch
#   file        optional: a file on the remote (absolute, or relative to the
#               remote home) that a running job should keep growing
#   -i seconds  time between checks (default 60)
#   -n checks   checks in a row that end the watch: a running job whose file
#               did not grow, or no answer (default 5)
#
# Output: one line per check, "<time> state=<STATE> size=<bytes>" (size -1:
#         no such file), then a final line naming the outcome.
# Exit:   0 DONE       the job completed
#         1 FAILED     the job ended any other way (failed, cancelled,
#                      timeout, out of memory, node failure, preempted)
#         2            usage error
#         3 NO GROWTH  the job is running but the file did not grow for
#                      <checks> checks in a row
#         4 NO ANSWER  ssh failed, or no Slurm command knew the job, for
#                      <checks> checks in a row

set -u

usage() { sed -n '/^# Usage:/,/^$/s/^# \{0,1\}//p' "$0" >&2; exit 2; }

INTERVAL=60
CHECKS=5
while [ $# -gt 0 ]; do
  case "$1" in
    -i) [ $# -ge 2 ] || usage; INTERVAL="$2"; shift 2 ;;
    -n) [ $# -ge 2 ] || usage; CHECKS="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown arg: $1" >&2; usage ;;
    *) break ;;
  esac
done
[ $# -ge 2 ] && [ $# -le 3 ] || usage
ALIAS="$1" JOB="$2" FILE="${3:-}"

printf '%s' "$INTERVAL" | grep -Eq '^[0-9]+(\.[0-9]+)?$' && [ "$INTERVAL" != 0 ] \
  || { echo "-i needs a positive number of seconds" >&2; exit 2; }
printf '%s' "$CHECKS" | grep -Eq '^[1-9][0-9]*$' \
  || { echo "-n needs a whole number of checks, 1 or more" >&2; exit 2; }
printf '%s' "$JOB" | grep -Eq '^[0-9]+(_[0-9]+)?$' \
  || { echo "jobid must be a Slurm job id, got: $JOB" >&2; exit 2; }
case "$ALIAS" in -*|*[[:space:]]*|'') echo "bad alias: $ALIAS" >&2; exit 2 ;; esac

# The remote side is plain POSIX sh, so it runs under whatever login shell the
# user has on the cluster.
REMOTE="s=\$(squeue -h -j $JOB -o %T 2>/dev/null | head -n 1)
[ -n \"\$s\" ] || s=\$(scontrol show job $JOB 2>/dev/null | sed -n 's/.*JobState=\\([A-Z_]*\\).*/\\1/p' | head -n 1)
[ -n \"\$s\" ] || s=\$(sacct -n -X -j $JOB -o State 2>/dev/null | awk 'NF{print \$1; exit}')
echo \"state=\${s:-UNKNOWN}\""
if [ -n "$FILE" ]; then
  q="'$(printf '%s' "$FILE" | sed "s/'/'\\\\''/g")'"
  REMOTE="$REMOTE
if [ -e $q ]; then echo \"size=\$(wc -c < $q | tr -d ' ')\"; else echo size=-1; fi"
fi

prev=""
stalled=0
silent=0
while :; do
  out=$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$ALIAS" "$REMOTE" 2>/dev/null)
  rc=$?
  state=$(printf '%s\n' "$out" | sed -n 's/^state=//p' | head -n 1)
  size=$(printf '%s\n' "$out" | sed -n 's/^size=//p' | head -n 1)
  [ $rc -eq 0 ] || state="NO-SSH(exit $rc)"
  echo "$(date '+%H:%M:%S') state=${state:-UNKNOWN} size=${size:--}"

  case "$state" in
    COMPLETED)
      echo "DONE: job $JOB completed"; exit 0 ;;
    FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED)
      echo "FAILED: job $JOB ended $state"; exit 1 ;;
    ''|UNKNOWN|NO-SSH*)
      silent=$((silent + 1))
      if [ "$silent" -ge "$CHECKS" ]; then
        echo "NO ANSWER: $CHECKS checks in a row without the job's state (ssh down, VPN, or a wrong job id)"
        exit 4
      fi ;;
    *)
      silent=0
      if [ -n "$FILE" ] && [ "$state" = RUNNING ]; then
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
