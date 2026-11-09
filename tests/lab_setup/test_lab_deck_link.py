"""`lab-deck` as a bare command in every agent: the same PATH link `edison-cli` gets."""

from __future__ import annotations

from tests.lab_setup.conftest import FakeMachine


def test_the_deck_launcher_is_linked_beside_the_edison_one(machine: FakeMachine) -> None:
    """One user bin folder holds both links, each into the marketplace clone."""
    result = machine.run()

    link = machine.bin_dir / "lab-deck"
    assert link.is_symlink()
    assert link.readlink() == machine.clone / "bin" / "lab-deck"
    assert (machine.bin_dir / "edison-cli").is_symlink()
    assert result.returncode == 0, result.stdout + result.stderr


def test_another_lab_deck_already_there_is_left_alone(machine: FakeMachine) -> None:
    """The script removes nothing, so someone else's command keeps its name."""
    theirs = machine.bin_dir / "lab-deck"
    theirs.write_text("#!/bin/sh\necho mine\n")

    result = machine.run("--only", "lab-deck")

    assert not theirs.is_symlink()
    assert "~/.local/bin/lab-deck" in result.stdout


def test_a_clone_from_before_lab_deck_skips_the_step(machine: FakeMachine) -> None:
    """An older clone has no launcher yet; the next update brings it."""
    (machine.clone / "bin" / "lab-deck").unlink()

    result = machine.run("--only", "lab-deck")

    assert not (machine.bin_dir / "lab-deck").exists()
    assert "skipped" in result.stdout
    assert result.returncode == 0, result.stdout + result.stderr
