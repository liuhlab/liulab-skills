"""`check-hpc-config.sh --live --node <alias>` checks that pixi runs on the held node.

A login shell on an arc compute node may not find `pixi`; only `$HOME/.pixi/bin/pixi` is
sure to. These tests run the preflight against a stub `ssh` first on PATH: it answers every
config query with a fixture host, passes the login probe, and runs the node's command here,
in a fake node home. Nothing reaches a host.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import program

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "lab-hpc" / "scripts" / "check-hpc-config.sh"

SSH = """#!/bin/sh
# Stand-in ssh: a config query gets a fixture host, the login probe succeeds, and a
# command for a node runs here with $STUB_NODE_HOME as its home.
for remote; do
  if [ "$remote" = -G ]; then echo "hostname fixture-host"; exit 0; fi
done
[ "$remote" = true ] && exit 0
exec env -i HOME="$STUB_NODE_HOME" PATH=/usr/bin:/bin sh -c "$remote"
"""

PIXI = """#!/bin/sh
echo "pixi 0.99.0"
"""


@pytest.mark.parametrize("installed", [True, False], ids=["pixi", "no-pixi"])
def test_live_node_check_reports_pixi_and_the_fix(tmp_path: Path, installed: bool) -> None:
    """A pixi at `$HOME/.pixi/bin` gives PIXI OK and its version; none gives PIXI FAIL, a fix."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    program(bin_dir, "ssh", SSH)
    node_home = tmp_path / "node-home"
    pixi_dir = node_home / ".pixi" / "bin"
    pixi_dir.mkdir(parents=True)
    if installed:
        program(pixi_dir, "pixi", PIXI)
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "STUB_NODE_HOME": str(node_home),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }

    result = subprocess.run(
        ["bash", str(SCRIPT), "--live", "--node", "GPU0001"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    lines = result.stdout.splitlines()
    report = result.stdout + result.stderr

    assert result.returncode == 0, report
    if installed:
        assert "node GPU0001: PIXI OK (pixi 0.99.0)" in lines, report
        assert not any("fix:" in line for line in lines), report
    else:
        assert any(line.startswith("node GPU0001: PIXI FAIL") for line in lines), report
        assert any(
            line.startswith("  fix:") and "$HOME/.pixi/bin/pixi" in line for line in lines
        ), report
