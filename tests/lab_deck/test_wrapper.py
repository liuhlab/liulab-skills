"""`bin/lab-deck`: the file that makes the command a bare name in all three agents.

The same two properties `tests/edison_cli/test_wrapper.py` pins for `bin/edison-cli`: it is
committed executable, and it execs the module, never the console script that shares its name.
It is run here against a stub `pixi` that writes down its arguments, directly and through the
link `/lab-setup` puts on PATH.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WRAPPER = REPO / "bin" / "lab-deck"
ARGS = ["build", "a deck"]


def test_the_wrapper_is_executable_on_disk_and_in_the_index() -> None:
    """A plugin is installed by cloning this repo, so the mode git records is the mode shipped."""
    assert os.access(WRAPPER, os.X_OK), "bin/lab-deck is not executable"
    listed = subprocess.run(
        ["git", "ls-files", "-s", "bin/lab-deck"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert listed.startswith("100755 "), f"git has it at the wrong mode: {listed.strip()!r}"


def test_the_wrapper_execs_the_module_and_never_its_own_name() -> None:
    """The recursion guard. `lab-deck` here would mean this file, not the console script."""
    text = WRAPPER.read_text(encoding="utf-8")
    runs = [line.strip() for line in text.splitlines() if re.match(r"^\s*exec\b", line)]
    assert runs, "the wrapper execs nothing"
    for line in runs:
        assert "python -m lab_deck" in line, f"not the module entry point: {line}"
        assert not re.search(r"\blab-deck\b", line), f"this execs itself: {line}"


@pytest.mark.parametrize("how", ["direct", "linked"])
def test_the_wrapper_runs_this_project_from_any_folder(tmp_path: Path, how: str) -> None:
    """Called as Claude Code calls it, and through a link in a folder on PATH."""
    launcher = WRAPPER
    if how == "linked":
        on_path = tmp_path / "a dir on PATH"
        on_path.mkdir()
        launcher = on_path / "lab-deck"
        launcher.symlink_to(WRAPPER)
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    stub = stub_dir / "pixi"
    stub.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$PIXI_STUB_LOG"\n', encoding="utf-8")
    stub.chmod(0o755)
    log = tmp_path / "pixi-args"
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'not-this-one'\n", encoding="utf-8")

    done = subprocess.run(
        [str(launcher), *ARGS],
        cwd=tmp_path,
        env={
            "PATH": os.pathsep.join([str(stub_dir), "/usr/bin", "/bin"]),
            "PIXI_STUB_LOG": str(log),
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    manifest = str(REPO / "pyproject.toml")
    assert log.read_text(encoding="utf-8").splitlines() == [
        "run",
        "--manifest-path",
        manifest,
        "python",
        "-m",
        "lab_deck",
        *ARGS,
    ]
