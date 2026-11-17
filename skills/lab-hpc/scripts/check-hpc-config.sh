#!/usr/bin/env bash
# Preflight: is THIS machine configured for the lab HPC clusters?
#
# Checks that the lab's conventional ssh aliases resolve via the user's own
# ssh config (`ssh -G`; honors Include). Contains no hostnames, usernames,
# or keys — it only verifies that the user has configured their own.
#
# Usage: check-hpc-config.sh [--live [--node <alias>]] [-F <ssh_config>]
#   --live   additionally try a BatchMode connection to each login alias
#   --node   with --live, check that pixi runs on the compute node you hold
#   -F file  use an alternate ssh config (for testing this script)
#
# Output: one line per cluster: "<cluster>: CONFIGURED" or
#         "<cluster>: NOT CONFIGURED (missing: ...)" (+ live results), or
#         only "config dir: OLD LOCATION" and the move, if ~/.claude/compute
#         still exists. An "ssh: ADVISORY" line names compute-node aliases
#         without connection reuse (ControlMaster); it never changes the exit.
#         With --node, "node <alias>: PIXI OK", "PIXI FAIL" and its fix, or
#         "UNREACHABLE"; these never change the exit either.
#         Nor does a "lab plugin: WARNING" line: auto-update off, or an installed
#         lab plugin older than the marketplace clone (/lab-setup's check).
# Exit:   0 if at least one cluster is fully configured, 1 otherwise.

set -u

LIVE=false
SSHCFG=""
NODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --live) LIVE=true ;;
    --node) shift; NODE="${1:-}" ;;
    -F) shift; SSHCFG="$1" ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done
if [ -n "$NODE" ] && ! $LIVE; then echo "--node needs --live" >&2; exit 2; fi

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

# Compute-node aliases: checked as cluster aliases below, and for connection reuse.
arc_nodes=(chimera-gpu chimera-cpu)
ircbc_nodes=(cpu01 cpu02 cpu03 cpu04 cpu05 cpu06 cpu07 cpu08)

ok=1
if check_cluster arc_hpc arc \
  arc chimera-login chimera-transfer "${arc_nodes[@]}"; then
  ok=0
  # Warn-only: lab-jupyter tunnels also need per-node aliases (GPU****/
  # CPU****-style names, usually one wildcard Host block). Probe a shaped
  # name; explicit per-node entries may not match the probe, so never fail.
  alias_configured GPU0001 || alias_configured CPU0001 || \
    echo "arc_hpc: WARNING (no GPU****/CPU****-style node aliases found — lab-jupyter tunnels need them)"
fi
check_cluster ircbc_hpc ircbc \
  ircbc ircbc-transfer "${ircbc_nodes[@]}" && ok=0

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
for a in "${arc_nodes[@]}" "${ircbc_nodes[@]}"; do
  if alias_configured "$a" && ! reuses_connection "$a"; then no_reuse+=("$a"); fi
done
if [ ${#no_reuse[@]} -gt 0 ]; then
  echo "ssh: ADVISORY (no connection reuse for: ${no_reuse[*]} — add the README's ControlMaster stanza)"
fi

# A login shell on an arc node may not find pixi, so the skill calls it by its
# full path. Check that path on the node held now; report only.
if [ -n "$NODE" ]; then
  # shellcheck disable=SC2016 # $HOME expands on the node
  out=$(sshg -o BatchMode=yes -o ConnectTimeout=8 "$NODE" '"$HOME/.pixi/bin/pixi" --version' 2>/dev/null)
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "node $NODE: PIXI OK ($out)"
  elif [ $rc -eq 255 ]; then
    echo "node $NODE: UNREACHABLE (do you hold a job there?)"
  else
    echo "node $NODE: PIXI FAIL (\$HOME/.pixi/bin/pixi does not run there)"
    # shellcheck disable=SC2016 # the fix names $HOME literally
    echo '  fix: install pixi on the node (curl -fsSL https://pixi.sh/install.sh | bash), then call $HOME/.pixi/bin/pixi by its full path'
  fi
fi

# Warn-only, never changes the exit code: a lab plugin that stopped updating runs old rules.
# /lab-setup's script holds the check (its claude and plugin steps) and reads local files only.
lab_setup="$(dirname "$0")/../../lab-setup/scripts/lab_setup.py"
if [ -d "$HOME/.claude/plugins/marketplaces/liulab" ] && [ -f "$lab_setup" ]; then
  py=""
  for p in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$p" >/dev/null 2>&1 &&
      "$p" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
      py=$p; break
    fi
  done
  if [ -z "$py" ]; then
    echo "lab plugin: NOT CHECKED (no Python 3.11 or newer on PATH)"
  else
    # A report line is "<status> <step> <detail>", padded to columns. Strip the known status
    # word and step name, not a column offset, so a wider column cannot cut the detail.
    "$py" "$lab_setup" --home "$HOME" --dry-run --only claude --only plugin 2>/dev/null |
      while IFS= read -r line; do
        for status in "would change" stale failed ""; do
          case "$line" in "$status "*) break ;; esac
        done
        [ -n "$status" ] || continue
        rest=${line#"$status"}
        rest=${rest#"${rest%%[! ]*}"}
        for step in claude plugin ""; do
          case "$rest" in "$step "*) break ;; esac
        done
        [ -n "$step" ] || continue
        rest=${rest#"$step"}
        rest=${rest#"${rest%%[! ]*}"}
        if [ "$status" = "would change" ]; then
          echo "lab plugin: WARNING (auto-update is off; /lab-setup will $rest)"
        else
          echo "lab plugin: WARNING ($rest)"
        fi
      done
  fi
fi

exit $ok
