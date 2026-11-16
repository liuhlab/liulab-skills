"""Codex: the `lab` plugin installed from the `liulab` marketplace.

Codex reads this repo's `.claude-plugin/` files and upgrades its git marketplaces at startup,
so installing once is all it needs. The script runs Codex's own two commands, against the
Codex home inside `--home`, and only for what `config.toml` does not already record.
"""

from __future__ import annotations

from tests.conftest import program
from tests.lab_setup.conftest import FakeMachine


def test_codex_gets_the_marketplace_and_the_plugin_in_its_own_home(
    machine: FakeMachine,
) -> None:
    """Both commands run, in order, with `CODEX_HOME` inside the fake home."""
    result = machine.run()

    codex_home = machine.home / ".codex"
    assert machine.codex_calls() == [
        f"{codex_home}|plugin marketplace add liuhlab/liulab-skills",
        f"{codex_home}|plugin add lab@liulab",
    ]
    assert result.returncode == 0, result.stdout + result.stderr


def test_codex_with_the_plugin_already_installed_is_not_run(machine: FakeMachine) -> None:
    """`config.toml` already records both: nothing to run, nothing to change."""
    config = machine.home / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text(
        'model = "o5"\n\n[marketplaces.liulab]\nsource_type = "git"\n'
        'source = "liuhlab/liulab-skills"\n\n[plugins."lab@liulab"]\nenabled = true\n'
    )

    result = machine.run()

    assert machine.codex_calls() == []
    assert "lab@liulab" in result.stdout


def test_a_machine_without_codex_is_told_so_and_the_run_still_succeeds(
    machine: FakeMachine,
) -> None:
    """No `codex` on PATH is an odd machine, not an error: the other agents still get set up."""
    result = machine.run(path=[machine.bin_dir])

    assert "codex" in result.stdout
    assert "skipped" in result.stdout
    assert not (machine.home / ".codex").exists()
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_failing_codex_command_fails_the_run_and_says_what_it_printed(
    machine: FakeMachine,
) -> None:
    """A refused install has to reach the member, with Codex's own reason."""
    (machine.stubs / "codex").unlink()
    program(machine.stubs, "codex", "#!/bin/sh\necho 'marketplace unreachable' >&2\nexit 3\n")

    result = machine.run()

    assert result.returncode == 1
    assert "marketplace unreachable" in result.stdout
