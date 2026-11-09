"""The run as a whole: safe to repeat, removes nothing, and asks before it changes.

A member reruns `/lab-setup` to repair a half-set-up machine, so on a set-up one a run has to
be a no-op down to the byte. The skill confirms each change first, which takes a run that
only reports (`--dry-run`) and a run of the steps the member agreed to (`--only`).
"""

from __future__ import annotations

import json
import subprocess
import sys

from tests.lab_setup.conftest import SCRIPT, FakeMachine, skill


def lived_in(machine: FakeMachine) -> None:
    """Give the fake home the member's own files, which every run must keep."""
    home = machine.home
    (home / ".claude" / "settings.json").write_text(json.dumps({"model": "opus"}, indent=4))
    (home / ".claude" / "CLAUDE.md").write_text("# Mine\n\nAnswer in English.\n")
    (home / ".kimi-code" / "config.toml").write_text(
        '# mine\nextra_skill_dirs = ["~/team-skills"]\n\n[thinking]\nenabled = true\n'
    )
    skill(home / ".agents" / "skills", "grilling")
    skill(home / ".claude" / "skills", "my-analysis")
    (home / "notes.txt").write_text("keep me\n")


def test_a_second_run_leaves_every_file_byte_identical(machine: FakeMachine) -> None:
    """The first run sets the machine up; the second finds it so, and writes nothing."""
    lived_in(machine)
    machine.run()
    after_first = machine.snapshot()
    calls = machine.codex_calls()

    result = machine.run()

    assert machine.snapshot() == after_first
    assert machine.codex_calls() == calls
    assert "changed" not in result.stdout
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_run_removes_nothing(machine: FakeMachine) -> None:
    """Every file that was there is still there; only the files the steps write differ."""
    lived_in(machine)
    before = machine.snapshot()

    machine.run()

    after = machine.snapshot()
    assert set(before) <= set(after)
    changed = {path for path in before if before[path] != after[path]}
    assert changed == {".claude/settings.json", ".claude/CLAUDE.md", ".kimi-code/config.toml"}


def test_a_dry_run_reports_each_change_and_makes_none(machine: FakeMachine) -> None:
    """What the skill shows the member before asking: one line per change, nothing done."""
    lived_in(machine)
    before = machine.snapshot()

    result = machine.run("--dry-run")

    assert machine.snapshot() == before
    assert machine.codex_calls() == []
    for step in ("claude", "codex", "kimi", "defaults", "edison-cli", "lab-deck"):
        assert any(
            line.startswith("would change") and step in line for line in result.stdout.splitlines()
        ), step
    assert "~/.agents/skills/grilling" in result.stdout


def test_only_runs_the_steps_it_names(machine: FakeMachine) -> None:
    """The member said yes to Kimi and no to the rest."""
    machine.run("--only", "kimi")

    assert (machine.home / ".kimi-code" / "config.toml").exists()
    assert not (machine.home / ".claude" / "settings.json").exists()
    assert not (machine.bin_dir / "edison-cli").exists()
    assert machine.codex_calls() == []


def test_the_home_is_never_guessed(machine: FakeMachine) -> None:
    """Without `--home` the script refuses rather than reach for the one in the environment."""
    before = machine.snapshot()

    refused = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={"HOME": str(machine.home), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert refused.returncode == 2
    assert "--home" in refused.stderr
    assert machine.snapshot() == before
