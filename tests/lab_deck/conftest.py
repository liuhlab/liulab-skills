"""Run `lab-deck` as a member would, and read the deck it wrote."""

from __future__ import annotations

import atexit
import contextlib
import fcntl
import functools
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lab_deck import cli
from lab_deck import powerpoint as powerpoint_module
from tests.lab_deck import stand_in_powerpoint

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
STANDIN = Path(__file__).with_name("stand_in_powerpoint.py")


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


def stand_in(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Answer one `osascript` or `open` call as the stand-in on PATH would, with no new Python.

    `lab-deck` still finds the program on its PATH, so "there is no `osascript` here" is
    decided as in a real run. Only the start of the program is saved: a build asks PowerPoint
    several questions, and each was a shell and a Python of its own.
    """
    said, failed = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(said), contextlib.redirect_stderr(failed):
        status = stand_in_powerpoint.answer(Path(command[0]).name, command[1:])
    return subprocess.CompletedProcess(command, status, said.getvalue(), failed.getvalue())


def lab_deck(
    *args: str | Path, cwd: Path | None = None, mac: bool = True, process: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run `lab-deck` with these arguments, and give its exit status and what it printed.

    Every run has the stand-in for PowerPoint on its PATH, whatever fixture started it, so
    no test reaches the real one. `mac=False` runs it where there is no `osascript`.

    The command runs inside the test's own process: the same typer app, arguments,
    environment and working folder, without the time a new Python takes to start. Node
    and git are still programs of their own. The stand-in for PowerPoint is found on PATH
    and then answers inside this process too (`stand_in`). `process=True` starts
    `python -m lab_deck`, the module the PATH wrapper execs, for the tests of that way in;
    there the stand-in runs as the program it is.
    """
    command = [sys.executable, "-m", "lab_deck", *map(str, args)]
    path = programs(mac)
    if process:
        return subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, "PATH": path},
            capture_output=True,
            text=True,
            check=False,
        )
    before, run = os.environ["PATH"], powerpoint_module.run
    standins = Path(path.split(os.pathsep)[0])
    os.environ["PATH"] = path
    powerpoint_module.run = lambda found: (
        stand_in(found) if Path(found[0]).parent == standins else run(found)
    )
    try:
        with contextlib.chdir(cwd or Path.cwd()):
            done = CliRunner().invoke(cli.app, command[3:], prog_name="lab-deck")
    finally:
        os.environ["PATH"], powerpoint_module.run = before, run
    if done.exception is not None and not isinstance(done.exception, SystemExit):
        # A traceback in a real run: let the test fail on it, not on an exit status.
        raise done.exception
    return subprocess.CompletedProcess(command, done.exit_code, done.stdout, done.stderr)


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

    def top(self, slide: int) -> list[tuple[str, str, list[str]]]:
        """List the objects at the top of one slide's shape tree, in drawing order.

        Each is (shape id, name, the names of the shapes inside it); only a group holds any.
        """
        tree = ET.fromstring(self.slides[slide - 1]).find("p:cSld/p:spTree", NS)
        assert tree is not None
        found = []
        for child in list(tree)[2:]:
            own, *inside = child.iter(f"{{{NS['p']}}}cNvPr")
            is_group = child.tag == f"{{{NS['p']}}}grpSp"
            members = [node.get("name", "") for node in inside] if is_group else []
            found.append((own.get("id", ""), own.get("name", ""), members))
        return found

    def clicks(self, slide: int) -> list[list[tuple[str, str]]]:
        """Read one slide's clicks from its timing: per click, each (object name, effect).

        The effect is PowerPoint's own name for it: `entr` or `exit`.
        """
        root = ET.fromstring(self.slides[slide - 1])
        names = {node.get("id"): node.get("name") for node in root.iter(f"{{{NS['p']}}}cNvPr")}
        steps = root.find(".//p:cTn[@nodeType='mainSeq']/p:childTnLst", NS)
        found = []
        for step in [] if steps is None else steps:
            effects = [node for node in step.iter(f"{{{NS['p']}}}cTn") if node.get("presetID")]
            found.append(
                [
                    (
                        names[effect.find(".//p:spTgt", NS).get("spid")],  # type: ignore[union-attr]
                        effect.get("presetClass", ""),
                    )
                    for effect in effects
                ]
            )
        return found

    def notes(self, slide: int) -> str:
        """Read the speaker notes of one slide: the text of its notes placeholder."""
        root = ET.fromstring(self.parts[f"ppt/notesSlides/notesSlide{slide}.xml"])
        body = next(
            shape
            for shape in root.iter(f"{{{NS['p']}}}sp")
            if shape.find("p:nvSpPr/p:nvPr/p:ph[@type='body']", NS) is not None
        )
        return "".join(node.text or "" for node in body.iter(f"{{{NS['a']}}}t"))


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


def build_once(
    tmp_path_factory: pytest.TempPathFactory, name: str, build: Callable[[Path], object]
) -> tuple[Path, object]:
    """Build a deck folder that many tests copy, once for the whole run; give it and its note.

    `pixi run test` runs on every core, and each worker is a process with fixtures of its
    own, so a deck "built once" was built once per worker. Here the first worker to ask
    calls `build` with the folder to make, under a file lock, and keeps what `build` returns
    as JSON beside it. Every other worker waits and reads. No test writes in the shared
    folder: each copies it.
    """
    base = tmp_path_factory.getbasetemp()
    # Under xdist each worker's base folder sits inside the run's; with one process it is the run's.
    shared = (base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base) / "built-once"
    shared.mkdir(exist_ok=True)
    folder, note = shared / name / "talk", shared / f"{name}.json"
    with (shared / f"{name}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not note.is_file():
            # A build that failed part-way leaves no note, and the next worker starts clean.
            shutil.rmtree(folder.parent, ignore_errors=True)
            folder.parent.mkdir()
            note.write_text(json.dumps(build(folder)), encoding="utf-8")
    return folder, json.loads(note.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def starter(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Make a new deck folder with `lab-deck new` once, for every test to copy."""

    def build(path: Path) -> None:
        made = lab_deck("new", path)
        assert made.returncode == 0, made.stdout + made.stderr

    return build_once(tmp_path_factory, "starter", build)[0]


def copy_deck(built: Path, to: Path) -> Path:
    """Copy a deck folder for one test to change, without git's sample hooks.

    `git init` leaves a dozen `*.sample` files in `.git/hooks`. git never runs one, and they
    are programs, which the virus scanner on a lab Mac reads on every copy: they were most of
    the time a copy took.
    """
    return Path(shutil.copytree(built, to, ignore=shutil.ignore_patterns("*.sample")))


@pytest.fixture
def folder(starter: Path, tmp_path: Path) -> Path:
    """Give each test its own new deck folder, holding the one starter slide."""
    return copy_deck(starter, tmp_path / "talk")


# What the tests of more than one file write, edit and read.

PLAIN = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.lines(slide, ["First phrase", { text: "Second phrase", accent: true }]);
};
"""

OPEN = ("<p:sp>", "<p:pic>", "<p:graphicFrame>")
SAVED = "2026-11-09T08:00:00Z"


def write(folder: Path, slides: dict[str, str]) -> None:
    """Give the deck folder these slides, in this order; each title is the slide's name."""
    for name, source in slides.items():
        (folder / "slides" / f"{name}.js").write_text(
            source.replace("TITLE", f"About {name}"), encoding="utf-8"
        )
    listed = ", ".join(f'"{name}"' for name in slides)
    order = folder / "deck.toml"
    order.write_text(
        re.sub(r"slides = \[.*\]", f"slides = [{listed}]", order.read_text(encoding="utf-8")),
        encoding="utf-8",
    )


def git(folder: Path, *args: str) -> str:
    """Run git in the deck folder, as a member with a name would."""
    done = subprocess.run(
        ["git", "-c", "user.name=Member", "-c", "user.email=member@example.invalid", *args],
        cwd=folder,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def save(folder: Path, change: Callable[[dict[str, str]], None]) -> None:
    """Change the XML parts of the deck, and save it as PowerPoint would: with a new time."""
    path = folder / "talk.pptx"
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    text = {n: p.decode("utf-8") for n, p in parts.items() if n.endswith((".xml", ".rels"))}
    change(text)
    text["docProps/core.xml"] = re.sub(
        r"(<dcterms:modified[^>]*>)[^<]+", rf"\g<1>{SAVED}", text["docProps/core.xml"]
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in parts.items():
            archive.writestr(name, text.get(name, payload))


def part(text: dict[str, str], slide: str) -> str:
    """Name the part that holds the slide with this id."""
    return next(n for n, xml in text.items() if f'<p:cSld name="{slide}">' in xml)


def on(slide: str, marker: str, change: Callable[[str], str]) -> Callable[[dict[str, str]], None]:
    """Change the one shape of `slide` whose XML holds `marker`."""

    def apply(text: dict[str, str]) -> None:
        name = part(text, slide)
        xml = text[name]
        at = xml.index(marker)
        start = max(xml.rfind(tag, 0, at) for tag in OPEN)
        close = "</" + xml[start + 1 : xml.index(">", start) + 1]
        end = xml.index(close, at) + len(close)
        changed = change(xml[start:end])
        assert changed != xml[start:end], "the edit changed nothing"
        text[name] = xml[:start] + changed + xml[end:]

    return apply


def swap(old: str, new: str, count: int = 1) -> Callable[[str], str]:
    """Replace `old` with `new` in a shape's XML."""
    return lambda xml: xml.replace(old, new, count)


def found(text: str) -> list[str]:
    """List the report's headings and edits, down to the summary line."""
    body = text.split("\n\n", 1)[1].split("\nNothing was copied")[0]
    return [line.strip() for line in body.splitlines() if line.strip()]
