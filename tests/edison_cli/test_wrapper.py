"""`bin/edison-cli`: the file that makes the command a bare name, and the loop it must not make.

Claude Code puts `<plugin-root>/bin` on PATH, so this wrapper is what turns every command in
`skills/lab-edison/` into the short form its pages already write — and what makes a permission
rule outlive a release, since the explicit spelling carries the plugin's version in its path.

Two properties, and both are about the shipped file rather than about a function. It has to be
committed EXECUTABLE, because the plugin cache is a clone and a mode 644 wrapper is a command
nobody can run. And it must exec the MODULE and never the console script: the script inside the
pixi environment wears this same name, this file is earlier on PATH, and `pixi run … edison-cli`
would therefore re-enter this file until the machine gives up. Neither is visible in Python, so
neither is asserted anywhere else.

The wrapper is run here only against a stub `pixi` that writes down its arguments, directly and
through the link `/lab-setup` puts on PATH. A real run builds a pixi environment of hundreds of
megabytes, and `tests/preflight.sh` is where this repo asks what a real machine has.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import program

REPO = Path(__file__).resolve().parents[2]
WRAPPER = REPO / "bin" / "edison-cli"
ARGS = ["status", "--json"]


def test_the_wrapper_is_there_and_the_preflight_looks_for_it_where_it_is() -> None:
    """`preflight.command` reports the bare spelling off this path, so the two must agree."""
    from edison_cli import preflight

    assert WRAPPER.is_file(), "bin/edison-cli is the whole of issue #51"
    assert preflight.WRAPPER == WRAPPER


def test_the_wrapper_is_executable_on_disk_and_in_the_index() -> None:
    """A plugin is installed by cloning this repo, so the mode git records is the mode shipped."""
    assert os.access(WRAPPER, os.X_OK), "bin/edison-cli is not executable"
    listed = subprocess.run(
        ["git", "ls-files", "-s", "bin/edison-cli"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert listed.startswith("100755 "), f"git has it at the wrong mode: {listed.strip()!r}"


def test_the_wrapper_execs_the_module_and_never_its_own_name() -> None:
    """The recursion guard. `edison-cli` here would mean this file, not the console script."""
    text = WRAPPER.read_text(encoding="utf-8")
    runs = [line.strip() for line in text.splitlines() if re.match(r"^\s*exec\b", line)]
    assert runs, "the wrapper execs nothing"
    for line in runs:
        assert "python -m edison_cli" in line, f"not the module entry point: {line}"
        assert not re.search(r"\bedison-cli\b", line), f"this execs itself: {line}"


def test_the_command_is_spelled_bare_only_where_the_shell_can_find_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`STOP:` is pasted into the caller's own shell, so the spelling has to work there.

    Both directions, because the two failures are opposite and both are silent: a bare name
    where nothing is on PATH is a stop command that does not run, and the explicit form where
    the wrapper IS on PATH is the version-carrying spelling issue #51 exists to remove.
    """
    from edison_cli import preflight

    monkeypatch.setenv("PATH", str(WRAPPER.parent))
    assert preflight.on_path()
    assert preflight.command() == "edison-cli"

    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert not preflight.on_path()
    assert preflight.command().startswith("pixi run --manifest-path ")
    assert preflight.command().endswith("/pyproject.toml edison-cli")


def test_a_link_on_path_is_the_bare_command_and_a_namesake_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through `/lab-setup`'s link the bare name works, so the preflight must print it.

    A plain file of the same name is the pixi environment's console script, which a caller's
    own shell does not have; it must not count.
    """
    from edison_cli import preflight

    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / "edison-cli").symlink_to(WRAPPER)
    namesake = tmp_path / "namesake"
    namesake.mkdir()
    (namesake / "edison-cli").write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setenv("PATH", os.pathsep.join([str(namesake), str(linked)]))
    assert preflight.command() == "edison-cli"

    monkeypatch.setenv("PATH", str(namesake))
    assert preflight.command().startswith("pixi run --manifest-path ")


def _run_with_stub_pixi(tmp_path: Path, launcher: Path) -> list[str]:
    """Run `launcher` with a `pixi` on PATH that only writes down what it was asked to do."""
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    program(stub_dir, "pixi", '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$PIXI_STUB_LOG"\n')
    log = tmp_path / "pixi-args"
    env = {
        "PATH": os.pathsep.join([str(stub_dir), "/usr/bin", "/bin"]),
        "PIXI_STUB_LOG": str(log),
        "HOME": str(tmp_path),
    }
    done = subprocess.run(
        [str(launcher), *ARGS],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return log.read_text(encoding="utf-8").splitlines()


def _expected(manifest: Path) -> list[str]:
    return ["run", "--manifest-path", str(manifest), "python", "-m", "edison_cli", *ARGS]


@pytest.mark.parametrize("kind", ["absolute", "relative", "chained"])
def test_through_a_link_elsewhere_the_wrapper_runs_the_real_project(
    tmp_path: Path, kind: str
) -> None:
    """`/lab-setup` links this file into a directory already on PATH, for Codex and Kimi Code.

    Through that link `$0` is the link, so a root found from it is the PATH directory's parent,
    whose `pyproject.toml` is somebody else's or nothing. The space in the directory name is
    there because a home directory may have one.
    """
    on_path = tmp_path / "a dir on PATH"
    on_path.mkdir()
    link = on_path / "edison-cli"
    if kind == "absolute":
        link.symlink_to(WRAPPER)
    elif kind == "relative":
        link.symlink_to(os.path.relpath(WRAPPER, on_path.resolve()))
    else:
        middle = tmp_path / "middle"
        middle.mkdir()
        (middle / "edison-cli").symlink_to(WRAPPER)
        link.symlink_to(os.path.relpath(middle / "edison-cli", on_path.resolve()))

    assert _run_with_stub_pixi(tmp_path, link) == _expected(REPO / "pyproject.toml")


def test_the_link_is_followed_without_gnu_only_tools() -> None:
    """`readlink -f` is GNU's, and `realpath` is missing from older macOS; the wrapper is `sh`."""
    text = WRAPPER.read_text(encoding="utf-8")
    code = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    for line in code:
        assert not re.search(r"readlink\s+-\w*f|\brealpath\b", line), line


def test_the_wrapper_resolves_the_plugin_from_its_own_location(tmp_path: Path) -> None:
    """An agent harness resets the working directory between calls, so nothing may depend on it.

    Called directly, as Claude Code calls it through `<plugin-root>/bin`, from a directory with a
    project of its own. `--manifest-path` is what keeps an activated pixi environment of the
    user's from winning.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'not-this-one'\n", encoding="utf-8")
    assert _run_with_stub_pixi(tmp_path, WRAPPER) == _expected(REPO / "pyproject.toml")
