"""The fake machine every `/lab-setup` test runs the setup script against.

A home in `tmp_path` that holds what a member's machine holds after the two install
commands: Claude Code's marketplace clone, with a few skills and the `edison-cli` launcher,
a user bin directory on PATH, and a Kimi Code home. `codex` is a stub that appends to its
config what the real command would, and writes down every call, so no test reaches the
network. `HOME` is the fake home too, so a script that forgot `--home` would still miss the
real one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "lab-setup" / "scripts" / "lab_setup.py"
# What the fake clone ships. A real clone ships more; these three are enough to clash with.
SHIPPED = ("grilling", "lab-hpc", "lab-setup")

# Records `CODEX_HOME|args` per call, then writes the tables the real `codex` writes, so a
# second run finds Codex set up exactly as it would on a real machine.
CODEX_STUB = """#!/bin/sh
printf '%s|%s\\n' "$CODEX_HOME" "$*" >> "$CODEX_LOG"
mkdir -p "$CODEX_HOME"
case "$1 $2" in
  "plugin marketplace")
    printf '[marketplaces.liulab]\\nsource_type = "git"\\nsource = "%s"\\n' "$4" \\
      >> "$CODEX_HOME/config.toml" ;;
  "plugin add")
    printf '[plugins."%s"]\\nenabled = true\\n' "$3" >> "$CODEX_HOME/config.toml" ;;
esac
"""


def skill(folder: Path, name: str) -> Path:
    """Write a minimal skill called `name` into `folder` and return its directory."""
    path = folder / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A skill.\n---\n")
    return path


@dataclass
class FakeMachine:
    """A fake home plus the stubs around it, and the one way to run the script on it."""

    root: Path

    @property
    def home(self) -> Path:
        """The home directory the script is told to act on."""
        return self.root / "home"

    @property
    def clone(self) -> Path:
        """Claude Code's marketplace clone inside the fake home."""
        return self.home / ".claude" / "plugins" / "marketplaces" / "liulab"

    @property
    def bin_dir(self) -> Path:
        """The user bin directory that is on PATH."""
        return self.home / ".local" / "bin"

    @property
    def stubs(self) -> Path:
        """Where the stub `codex` lives, outside the home."""
        return self.root / "stubs"

    @property
    def codex_log(self) -> Path:
        """Every call the stub `codex` received, outside the home."""
        return self.root / "codex.log"

    def run(self, *args: str, path: list[Path] | None = None) -> subprocess.CompletedProcess[str]:
        """Run the script on the fake home, with `path` (default: stubs, user bin) on PATH."""
        dirs = [self.stubs, self.bin_dir] if path is None else path
        env = {
            "HOME": str(self.home),
            "PATH": os.pathsep.join([*map(str, dirs), "/usr/bin", "/bin"]),
            "CODEX_LOG": str(self.codex_log),
        }
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(self.home), *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def codex_calls(self) -> list[str]:
        """List the stub's calls, one `CODEX_HOME|args` line each."""
        if not self.codex_log.exists():
            return []
        return self.codex_log.read_text().splitlines()

    def snapshot(self) -> dict[str, bytes | str]:
        """Every file's bytes and every link's target under the home, keyed by path."""
        found: dict[str, bytes | str] = {}
        for path in sorted(self.home.rglob("*")):
            key = str(path.relative_to(self.home))
            if path.is_symlink():
                found[key] = f"-> {path.readlink()}"
            elif path.is_file():
                found[key] = path.read_bytes()
        return found


@pytest.fixture
def machine(tmp_path: Path) -> FakeMachine:
    """Build a machine after `claude plugin marketplace add` and `install`, with Kimi and Codex."""
    fake = FakeMachine(tmp_path)
    for name in SHIPPED:
        skill(fake.clone / "skills", name)
    (fake.clone / "bin").mkdir(parents=True)
    for name in ("edison-cli", "lab-deck"):
        launcher = fake.clone / "bin" / name
        launcher.write_text("#!/bin/sh\necho launcher\n")
        launcher.chmod(0o755)
    fake.bin_dir.mkdir(parents=True)
    (fake.home / ".kimi-code").mkdir()
    fake.stubs.mkdir()
    codex = fake.stubs / "codex"
    codex.write_text(CODEX_STUB)
    codex.chmod(0o755)
    return fake
