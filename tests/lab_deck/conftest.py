"""Run `lab-deck` as a member would, and read the deck it wrote."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


def lab_deck(*args: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run `lab-deck` with these arguments through the module the PATH wrapper execs."""
    return subprocess.run(
        [sys.executable, "-m", "lab_deck", *map(str, args)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


class Deck:
    """A built deck, read straight from the file."""

    def __init__(self, path: Path) -> None:
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            self.parts = {name: archive.read(name).decode("utf-8") for name in archive.namelist()}

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


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """Make a new deck folder with `lab-deck new`, holding the one starter slide."""
    path = tmp_path / "talk"
    made = lab_deck("new", path)
    assert made.returncode == 0, made.stdout + made.stderr
    return path
