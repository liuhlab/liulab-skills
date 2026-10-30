#!/usr/bin/env bash
# Agent-aware entrypoint. The shared case catalogue remains usable without a runner.
set -eu
cd "$(dirname "$0")/.."
if [[ " $* " == *' --dump '* ]]; then
  exec bash tests/eval_cases.sh "$@"
fi
exec python3 tests/eval_runner.py "$@"
