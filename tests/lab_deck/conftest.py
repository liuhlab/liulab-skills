"""Run `lab-deck` as a member would, and read the deck it wrote."""

from __future__ import annotations

import atexit
import functools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

STANDIN = Path(__file__).with_name("standin.py")


@functools.cache
def programs(mac: bool = True) -> str:
    """Make the PATH `lab-deck` runs with: the stand-in for PowerPoint first, or no Mac at all.

    On a Mac the folder holds `osascript` and `open`, each running the stand-in, before
    everything else on PATH. Off a Mac it holds git and nothing else, so neither is found.
    """
    path = Path(tempfile.mkdtemp(prefix="lab-deck-programs-"))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    if not mac:
        git = shutil.which("git")
        assert git, "the tests need git"
        (path / "git").symlink_to(git)
        return str(path)
    python, standin = shlex.quote(sys.executable), shlex.quote(str(STANDIN))
    for name in ("osascript", "open"):
        program = path / name
        program.write_text(f'#!/bin/sh\nexec {python} {standin} {name} "$@"\n', encoding="utf-8")
        program.chmod(0o755)
    return f"{path}{os.pathsep}{os.environ['PATH']}"


def lab_deck(
    *args: str | Path, cwd: Path | None = None, mac: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run `lab-deck` with these arguments through the module the PATH wrapper execs.

    Every run has the stand-in for PowerPoint on its PATH, whatever fixture started it, so
    no test reaches the real one. `mac=False` runs it where there is no `osascript`.
    """
    return subprocess.run(
        [sys.executable, "-m", "lab_deck", *map(str, args)],
        cwd=cwd,
        env={**os.environ, "PATH": programs(mac)},
        capture_output=True,
        text=True,
        check=False,
    )


class Deck:
    """A built deck, read straight from the file."""

    def __init__(self, path: Path) -> None:
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            self.names = archive.namelist()
            # The XML parts as text. A picture stays out: it is bytes, read with `media`.
            self.parts = {
                name: archive.read(name).decode("utf-8")
                for name in self.names
                if name.endswith((".xml", ".rels"))
            }
            self.media = {
                name: archive.read(name) for name in self.names if name.startswith("ppt/media/")
            }

    @property
    def size(self) -> tuple[int, int]:
        """The slide size in EMU, as `ppt/presentation.xml` declares it."""
        found = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', self.parts["ppt/presentation.xml"])
        assert found, "the deck declares no slide size"
        return int(found[1]), int(found[2])

    @property
    def slides(self) -> list[str]:
        """Each slide's XML, in the order the deck shows them."""
        listed = re.findall(r"<p:sldId [^>]*/>", self.parts["ppt/presentation.xml"])
        return [self.parts[f"ppt/slides/slide{n}.xml"] for n in range(1, len(listed) + 1)]

    def text(self, slide: int) -> list[str]:
        """Every run of text on one slide, counted from 1."""
        return re.findall(r"<a:t>([^<]*)</a:t>", self.slides[slide - 1])

    @property
    def ids(self) -> list[str]:
        """Each slide's id, the name of its source file, in the order the deck shows them."""
        return [re.search(r'<p:cSld name="([^"]*)"', slide)[1] for slide in self.slides]  # type: ignore[index]

    def shapes(self, slide: int) -> list[tuple[str, str]]:
        """List the (shape id, name) of every object on one slide, in drawing order."""
        return re.findall(r'<p:cNvPr id="(\d+)" name="([^"]*)"', self.slides[slide - 1])[1:]

    def page(self, slide: int) -> str | None:
        """Read the page number drawn on one slide, or None when it has none."""
        box = re.search(
            r'<p:sp><p:nvSpPr><p:cNvPr id="\d+" name="Page number".*?</p:sp>',
            self.slides[slide - 1],
            flags=re.S,
        )
        return None if box is None else "".join(re.findall(r"<a:t>([^<]*)</a:t>", box[0]))


class PowerPoint:
    """The stand-in's state, as a test sets it and reads it back."""

    def __init__(self, kept: Path) -> None:
        self.kept = kept

    def start(self, *decks: dict[str, object], refuse: tuple[str, ...] = ()) -> None:
        """Have PowerPoint running, with these decks open and these commands refused."""
        state = {"running": True, "decks": list(decks), "refuse": list(refuse), "log": []}
        self.kept.write_text(json.dumps(state), encoding="utf-8")

    @property
    def state(self) -> dict[str, list[dict[str, object]]]:
        """Read what PowerPoint holds now."""
        return json.loads(self.kept.read_text(encoding="utf-8"))

    @property
    def log(self) -> list[list[str]]:
        """List every command PowerPoint got after the running check, in order."""
        return self.state["log"] if self.kept.is_file() else []  # type: ignore[return-value]

    @property
    def commands(self) -> list[str]:
        """Name the commands PowerPoint got, in order."""
        return [entry[0] for entry in self.log]


@pytest.fixture(autouse=True)
def powerpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PowerPoint:
    """Give each test a PowerPoint of its own, which the stand-in on PATH answers for.

    Until a test calls `start`, PowerPoint is not running, as on a machine with no deck open.
    """
    kept = tmp_path / "powerpoint.json"
    monkeypatch.setenv("LAB_DECK_STANDIN", str(kept))
    return PowerPoint(kept)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """Make a new deck folder with `lab-deck new`, holding the one starter slide."""
    path = tmp_path / "talk"
    made = lab_deck("new", path)
    assert made.returncode == 0, made.stdout + made.stderr
    return path
