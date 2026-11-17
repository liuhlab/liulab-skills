"""`watch-job.sh` waits for a run, tells ssh trouble from a job's end, and asks for growth.

It stops on a stalled file only when told that file must grow (`-g`). Each test runs the watcher against a stub `ssh` first on PATH. Every call replays the next line
of a scenario: the connection fails, or it runs the watcher's remote command here, against
stub `squeue`, `scontrol` and `sacct` and a real file of the given size. Nothing reaches a
host.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import program

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "lab-hpc" / "scripts" / "watch-job.sh"

SSH = """#!/bin/sh
# Stand-in ssh. Each call replays the next line of $WJ_DIR/scenario:
#   ssh <rc>                  the connection fails with exit <rc>
#   ssh empty                 the connection closes with no reply and exit 0
#   <squeue> <sacct> <size>   the node answers: squeue's state, or - once the job has left
#                             the queue; sacct's state, or - for no answer; the file's size
for remote; do :; done
n=$(( $(wc -l < "$WJ_DIR/calls") + 1 ))
echo call >> "$WJ_DIR/calls"
set -- $(sed -n "${n}p" "$WJ_DIR/scenario")
[ $# -gt 0 ] || { echo "stub ssh: no line $n in the scenario" >&2; exit 255; }
if [ "$1" = ssh ]; then
  [ "$2" = empty ] && exit 0
  echo "ssh: connect to host stub: Connection refused" >&2
  exit "$2"
fi
printf '%s\\n' "$1" > "$WJ_DIR/squeue.state"
printf '%s\\n' "$2" > "$WJ_DIR/sacct.state"
head -c "$3" /dev/zero > "$WJ_DIR/out.log"
cd "$WJ_DIR" && exec sh -c "$remote"
"""

SLURM = """#!/bin/sh
# Stand-in Slurm client, linked as squeue, scontrol and sacct. squeue answers from
# squeue.state and honours -o's %T (state) and %N (node, node-a while it runs); sacct answers
# from sacct.state; scontrol knows no job. "-" is no answer.
tool=$(basename "$0")
case "$tool" in
  squeue) s=$(cat "$WJ_DIR/squeue.state") ;;
  sacct) s=$(cat "$WJ_DIR/sacct.state") ;;
  *) exit 1 ;;
esac
[ "$s" = - ] && exit 1
if [ "$tool" = sacct ]; then printf '%s\\n' "$s"; exit 0; fi
node=
[ "$s" = RUNNING ] && node=node-a
fmt=%T
while [ $# -gt 0 ]; do [ "$1" = -o ] && fmt=$2; shift; done
printf '%s\\n' "$fmt" | sed "s/%T/$s/g; s/%N/$node/g"
"""


def watch(tmp_path: Path, scenario: list[str], *args: str) -> tuple[int, list[str], int]:
    """Run the watcher on job 123 through `scenario`; return its exit, output lines, ssh calls."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    program(bin_dir, "ssh", SSH)
    for name in ("squeue", "scontrol", "sacct"):
        program(bin_dir, name, SLURM)
    (tmp_path / "scenario").write_text("\n".join(scenario) + "\n", encoding="utf-8")
    (tmp_path / "calls").write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "WJ_DIR": str(tmp_path),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    result = subprocess.run(
        ["bash", str(SCRIPT), "-i", "0.05", "-n", "2", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    calls = len((tmp_path / "calls").read_text(encoding="utf-8").splitlines())
    return result.returncode, (result.stdout + result.stderr).splitlines(), calls


def test_until_running_returns_once_the_job_runs_and_names_its_node(tmp_path: Path) -> None:
    """`-r` ends the watch at the first check that finds the job running, and names the node."""
    rc, lines, calls = watch(
        tmp_path, ["PENDING - 0", "PENDING - 0", "RUNNING - 0", "RUNNING - 0"], "-r", "arc", "123"
    )

    assert (rc, calls) == (0, 3), lines
    assert lines[-1] == "RUNNING: job 123 runs on node-a", lines


@pytest.mark.parametrize(
    ("scenario", "want_rc", "outcome"),
    [
        (["RUNNING - 0", "ssh 255", "ssh empty"], 4, "NO SSH:"),
        (["RUNNING - 0", "- - 0", "- - 0"], 5, "NO JOB:"),
    ],
    ids=["ssh-fails", "job-unknown"],
)
def test_an_ssh_failure_is_reported_apart_from_a_job_nobody_knows(
    tmp_path: Path, scenario: list[str], want_rc: int, outcome: str
) -> None:
    """A failed or empty ssh reply ends the watch with its own exit, never as the job's end."""
    rc, lines, calls = watch(tmp_path, scenario, "arc", "123")

    assert (rc, calls) == (want_rc, 3), lines
    assert lines[-1].startswith(outcome), lines


@pytest.mark.parametrize(
    ("flags", "want_rc", "want_calls", "outcome"),
    [((), 0, 5, "DONE:"), (("-g",), 3, 3, "NO GROWTH:")],
    ids=["quiet-step", "must-grow"],
)
def test_no_growth_ends_the_watch_only_for_a_file_that_must_grow(
    tmp_path: Path, flags: tuple[str, ...], want_rc: int, want_calls: int, outcome: str
) -> None:
    """A watched file that stays the same size is reported; it stops the watch only under `-g`."""
    scenario = ["RUNNING - 10"] * 4 + ["- COMPLETED 10"]
    rc, lines, calls = watch(tmp_path, scenario, *flags, "arc", "123", "out.log")

    assert (rc, calls) == (want_rc, want_calls), lines
    assert lines[-1].startswith(outcome), lines
