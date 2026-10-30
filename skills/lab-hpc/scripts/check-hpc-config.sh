#!/usr/bin/env bash
# Preflight: is THIS machine configured for the lab HPC clusters?
#
# Checks that the lab's conventional ssh aliases resolve via the user's own
# ssh config (`ssh -G`; honors Include). Contains no hostnames, usernames,
# or keys — it only verifies that the user has configured their own.
#
# Usage: check-hpc-config.sh [--live] [-F <ssh_config>]
#   --live   additionally try a BatchMode connection to each login alias
#   -F file  use an alternate ssh config (for testing this script)
#
# Output: one line per cluster: "<cluster>: CONFIGURED" or
#         "<cluster>: NOT CONFIGURED (missing: ...)" (+ live results), or
#         only "config dir: OLD LOCATION" and the move, if ~/.claude/compute
#         still exists. An "ssh: ADVISORY" line names compute-node aliases
#         without connection reuse (ControlMaster); it never changes the exit.
# Exit:   0 if at least one cluster is fully configured, 1 otherwise.

set -u

LIVE=false
SSHCFG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --live) LIVE=true ;;
    -F) shift; SSHCFG="$1" ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

# The per-user directory moved when the plugin was renamed from lab-compute
# to lab. While the old one exists, refuse and print the move — never perform
# it, since the directory also holds the Edison key file.
if [ -e "$HOME/.claude/compute" ]; then
  echo "config dir: OLD LOCATION (~/.claude/compute — the plugin is lab now and reads ~/.claude/lab)"
  if [ -e "$HOME/.claude/lab" ]; then
    echo "  both exist: move what you still need into ~/.claude/lab, then remove ~/.claude/compute"
  else
    echo "  fix: mv ~/.claude/compute ~/.claude/lab"
  fi
  exit 1
fi

sshg() { # ssh wrapper honoring the optional -F override (bash-3.2 safe)
  if [ -n "$SSHCFG" ]; then ssh -F "$SSHCFG" "$@"; else ssh "$@"; fi
}

# An alias counts as configured when the user's ssh config actually defines
# it: resolved hostname differs from the alias, or a proxyjump/remotecommand
# is attached (compute-node aliases keep hostname == alias via ProxyJump).
alias_configured() {
  local a="$1" out host pj rc
  out=$(sshg -G "$a" 2>/dev/null) || return 1
  host=$(printf '%s\n' "$out" | awk '$1=="hostname"{print $2; exit}')
  pj=$(printf '%s\n' "$out" | awk '$1=="proxyjump"{print $2; exit}')
  rc=$(printf '%s\n' "$out" | awk '$1=="remotecommand"{print $2; exit}')
  [ "$host" != "$a" ] || [ -n "$pj" ] || [ -n "$rc" ]
}

check_cluster() {
  local name="$1" login="$2"; shift 2
  local missing=()
  local a
  for a in "$@"; do
    alias_configured "$a" || missing+=("$a")
  done
  if [ ${#missing[@]} -eq 0 ]; then
    echo "$name: CONFIGURED"
    if $LIVE; then
      if sshg -o BatchMode=yes -o ConnectTimeout=8 "$login" true 2>/dev/null; then
        echo "$name: LIVE OK ($login reachable)"
      else
        if [ "$name" = "ircbc_hpc" ]; then
          echo "$name: LIVE FAIL ($login unreachable — VPN likely down; stop and tell the user)"
        else
          echo "$name: LIVE FAIL ($login unreachable)"
        fi
      fi
    fi
    return 0
  else
    echo "$name: NOT CONFIGURED (missing: ${missing[*]})"
    return 1
  fi
}

ok=1
if check_cluster arc_hpc arc \
  arc chimera-login chimera-transfer chimera-gpu chimera-cpu; then
  ok=0
  # Warn-only: lab-jupyter tunnels also need per-node aliases (GPU****/
  # CPU****-style names, usually one wildcard Host block). Probe a shaped
  # name; explicit per-node entries may not match the probe, so never fail.
  alias_configured GPU0001 || alias_configured CPU0001 || \
    echo "arc_hpc: WARNING (no GPU****/CPU****-style node aliases found — lab-jupyter tunnels need them)"
fi
check_cluster ircbc_hpc ircbc \
  ircbc ircbc-transfer cpu01 cpu02 cpu03 cpu04 cpu05 cpu06 cpu07 cpu08 && ok=0

# Advisory only, never changes the exit code: compute-node aliases without
# connection reuse open a fresh login-node hop per ssh call, and many agents
# probing nodes at once overload that login node.
reuses_connection() {
  local out cm cp
  out=$(sshg -G "$1" 2>/dev/null) || return 1
  cm=$(printf '%s\n' "$out" | awk '$1=="controlmaster"{print $2; exit}')
  cp=$(printf '%s\n' "$out" | awk '$1=="controlpath"{print $2; exit}')
  case "$cm" in false|no|"") return 1 ;; esac
  case "$cp" in none|"") return 1 ;; esac
}
no_reuse=()
for a in chimera-gpu chimera-cpu cpu01 cpu02 cpu03 cpu04 cpu05 cpu06 cpu07 cpu08; do
  if alias_configured "$a" && ! reuses_connection "$a"; then no_reuse+=("$a"); fi
done
if [ ${#no_reuse[@]} -gt 0 ]; then
  echo "ssh: ADVISORY (no connection reuse for: ${no_reuse[*]} — add the README's ControlMaster stanza)"
fi

exit $ok
