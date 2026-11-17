"""Claude Code's installed `lab` plugin: reported when it lags the marketplace clone.

The clone is Claude Code's checkout of the marketplace, and its `.claude-plugin/plugin.json`
names the newest release it has fetched. `~/.claude/plugins/installed_plugins.json` names the
release the sessions load. A machine whose plugin stopped updating runs old rules without a
word, so the `plugin` step says so, and the HPC preflight every cluster session runs repeats it.
"""

from __future__ import annotations

import json
import subprocess
import sys

from tests.conftest import program
from tests.lab_setup.conftest import REPO, FakeMachine

PREFLIGHT = REPO / "skills" / "lab-hpc" / "scripts" / "check-hpc-config.sh"


def releases(machine: FakeMachine, installed: str, cloned: str) -> None:
    """Make the clone hold release `cloned` and Claude Code's install record `installed`."""
    manifest = machine.clone / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "lab", "version": cloned}))
    cache = machine.home / ".claude" / "plugins" / "cache" / "liulab" / "lab" / installed
    record = {
        "version": 2,
        "plugins": {
            "lab@liulab": [
                {
                    "scope": "user",
                    "installPath": str(cache),
                    "version": installed,
                    "installedAt": "2026-10-31T09:00:00.000Z",
                    "lastUpdated": "2026-10-31T09:00:00.000Z",
                }
            ]
        },
    }
    path = machine.home / ".claude" / "plugins" / "installed_plugins.json"
    path.write_text(json.dumps(record))


def preflight(machine: FakeMachine) -> subprocess.CompletedProcess[str]:
    """Run `lab-hpc`'s preflight on the fake home with no ssh config, a 3.11+ `python3` first."""
    program(machine.stubs, "python3", f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    return subprocess.run(
        ["bash", str(PREFLIGHT), "-F", "/dev/null"],
        env={"HOME": str(machine.home), "PATH": f"{machine.stubs}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_hpc_preflight_warns_of_a_plugin_that_stopped_updating_and_still_answers(
    machine: FakeMachine,
) -> None:
    """Auto-update off and an old install: two warnings, each with the step's whole detail.

    Releases compare as numbers: 2026.9.40 is older than 2026.11.2, though not as text.
    """
    releases(machine, installed="2026.9.40", cloned="2026.11.2")
    before = machine.snapshot()

    result = preflight(machine)

    warnings = [line for line in result.stdout.splitlines() if line.startswith("lab plugin:")]
    assert len(warnings) == 2, result.stdout
    assert warnings[0].startswith(
        "lab plugin: WARNING (auto-update is off; /lab-setup will turn on auto-update for "
    ), warnings[0]
    assert warnings[1].startswith(
        "lab plugin: WARNING (lab@liulab 2026.9.40 is older than the marketplace clone's 2026.11.2;"
    ), warnings[1]
    assert "claude plugin update lab@liulab" in warnings[1]
    assert "arc_hpc: NOT CONFIGURED" in result.stdout
    assert result.returncode == 1
    assert machine.snapshot() == before


def test_the_hpc_preflight_says_nothing_of_a_plugin_that_is_up_to_date(
    machine: FakeMachine,
) -> None:
    """Auto-update on and the install at the clone's release: no line about the plugin."""
    releases(machine, installed="2026.11.15", cloned="2026.11.15")
    settings = {"extraKnownMarketplaces": {"liulab": {"autoUpdate": True}}}
    (machine.home / ".claude" / "settings.json").write_text(json.dumps(settings))

    result = preflight(machine)

    assert "lab plugin" not in result.stdout
    assert "arc_hpc: NOT CONFIGURED" in result.stdout
