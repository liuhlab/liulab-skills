"""Render every click state of a built deck to a picture, and say which pictures changed.

LibreOffice plays no animation when it converts a deck, so a slide with clicks would show
every section at once. `expand` therefore writes a copy of the deck with one plain slide per
click state: what a later click brings is cut out, what an earlier click took away is cut
out, the timing is dropped and a hidden slide is shown. LibreOffice turns the copy into a PDF
and Poppler's `pdftoppm` turns each page into a PNG. The deck itself is only ever read.

The pictures live in `renders/` inside the deck folder, which git ignores. A picture is named
by its slide's id and its click state, never by a page number, so an inserted slide leaves
the pictures of every other slide as they were. A picture has changed when its bytes differ
from the one the last render left there.

LibreOffice is the system's app. `to_pdf` is the one place that runs it; a test names a
stand-in program in `LAB_DECK_SOFFICE`.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from xml.parsers import expat
from zipfile import ZipFile

from lab_deck import stage
from lab_deck.folder import Folder, Refusal
from lab_deck.merge import SLIDE_TYPE, P, R, write

RENDERS = "renders"
# The environment variable that names the LibreOffice program, for a test's stand-in or a
# LibreOffice in an unusual place.
SOFFICE = "LAB_DECK_SOFFICE"
# Where the app keeps its program on a Mac; it is not on PATH there.
MAC_SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
# The longest LibreOffice may take over one deck, in seconds.
PATIENCE = 600
# The width of a picture, in pixels: enough to read a 12 pt citation on a 13.333 inch slide.
WIDTH = 1600

# The objects a click can show or hide, at any depth of the shape tree.
OBJECTS = {f"{P} {kind}" for kind in ("sp", "pic", "grpSp", "graphicFrame", "cxnSp")}
RELATION = re.compile(rb"<Relationship [^>]*/>")
OVERRIDE = re.compile(rb'<Override [^>]*PartName="/ppt/slides/[^"]*"[^>]*/>')


@dataclass(frozen=True)
class State:
    """One click state of one slide: one page of the copy, and one picture."""

    slide: str
    """The slide's id."""
    page: int
    """The slide's place in the deck, from 1."""
    clicks: int
    """How many clicks have been made: 0 is the slide as it opens."""
    hidden: bool
    """Whether the slide is hidden in the deck."""

    @property
    def picture(self) -> str:
        """The picture's file name: the slide's id and the click state, no page number."""
        return f"{self.slide}.click{self.clicks}.png"

    @property
    def label(self) -> str:
        """Say which click state this is, in words."""
        after = "as it opens" if self.clicks == 0 else f"after click {self.clicks}"
        return f"slide {self.slide} (page {self.page}{', hidden' if self.hidden else ''}), {after}"


@dataclass(frozen=True)
class Report:
    """What one render did."""

    folder: Path
    """The folder the pictures are in."""
    states: list[State]
    """Every click state rendered, in deck order."""
    new: list[State]
    """The click states that had no picture before."""
    changed: list[State]
    """The click states whose picture differs from the last render's."""
    gone: list[str]
    """Pictures of the last render that no click state has any more, now deleted."""
    unshown: list[str]
    """Slides with an effect other than Appear and Disappear, which no picture shows."""


def soffice() -> str | None:
    """Find the LibreOffice program: the one named in the environment, on PATH, or the Mac app."""
    named = os.environ.get(SOFFICE)
    if named:
        return named if Path(named).is_file() else None
    found = shutil.which("soffice")
    if found is None and MAC_SOFFICE.is_file():
        found = str(MAC_SOFFICE)
    return found


def tool(name: str) -> str | None:
    """Find a program of this pixi environment, or the one on PATH."""
    beside = Path(sys.prefix) / "bin" / name
    return str(beside) if beside.is_file() else shutil.which(name)


def to_pdf(deck: Path, out: Path) -> Path:
    """Convert the deck at `deck` to a PDF in the folder `out`, with LibreOffice.

    This is the one place LibreOffice runs. It runs headless, with a profile of its own in
    `out`, so it opens no window and leaves an open LibreOffice session alone.

    Raises
    ------
    Refusal
        When LibreOffice is missing, fails, takes too long or writes no PDF.
    """
    program = soffice()
    if program is None:
        raise Refusal("LibreOffice was not found. Run `lab-deck preflight` for how to get it.")
    command = [
        program,
        "-env:UserInstallation=" + (out / "profile").as_uri(),
        "--headless",
        "--invisible",
        "--norestore",
        "--nologo",
        "--nolockcheck",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out),
        str(deck),
    ]
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=PATIENCE
        )
    except subprocess.TimeoutExpired:
        raise Refusal(f"LibreOffice did not finish in {PATIENCE} seconds.") from None
    pdf = out / f"{deck.stem}.pdf"
    if done.returncode != 0 or not pdf.is_file():
        said = (done.stderr.strip() or done.stdout.strip() or "it said nothing")[-2000:]
        raise Refusal(
            f"LibreOffice wrote no PDF (exit {done.returncode}): {said}\n"
            "Inside a command sandbox LibreOffice aborts on a Mac. "
            "Run `lab-deck render` outside the sandbox."
        )
    return pdf


def to_pictures(pdf: Path, out: Path) -> list[Path]:
    """Turn each page of `pdf` into a PNG in `out`, with Poppler, and list them in page order.

    Raises
    ------
    Refusal
        When `pdftoppm` is missing or fails.
    """
    program = tool("pdftoppm")
    if program is None:
        raise Refusal(
            "Poppler's pdftoppm was not found. Run `lab-deck preflight` for how to get it."
        )
    done = subprocess.run(
        [program, "-scale-to", str(WIDTH), "-png", str(pdf), str(out / "page")],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise Refusal(f"pdftoppm failed (exit {done.returncode}): {done.stderr.strip()}")
    # pdftoppm pads the page number to the width of the last one, so names sort in page order.
    return sorted(out.glob("page-*.png"))


def _spans(data: bytes) -> dict[str, list[tuple[int, int]]]:
    """Find the bytes of every object in a slide's shape tree, by shape id."""
    parser = expat.ParserCreate(namespace_separator=" ")
    # Each open element: its start byte, and its shape id once its own `cNvPr` is read.
    open_: list[list[int | str | None]] = []
    spans: dict[str, list[tuple[int, int]]] = {}

    def start(tag: str, attrs: dict[str, str]) -> None:
        if tag == f"{P} cNvPr" and len(open_) > 1 and open_[-2][1] is None:
            open_[-2][1] = attrs.get("id", "")
        open_.append([parser.CurrentByteIndex, "" if tag not in OBJECTS else None])

    def end(tag: str) -> None:
        begin, ident = open_.pop()
        if tag not in OBJECTS or not ident:
            return
        index = parser.CurrentByteIndex
        # An element with children ends at its closing tag; an empty one is a single tag.
        closing = data[index : index + 2] == b"</"
        stop = data.index(b">", index) + 1 if closing else data.index(b"/>", index) + 2
        assert isinstance(begin, int)
        spans.setdefault(str(ident), []).append((begin, stop))

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(data, True)
    return spans


def _without(data: bytes, spans: list[tuple[int, int]]) -> bytes:
    """Cut these runs of bytes out of `data`; a run inside another goes with it."""
    kept: list[tuple[int, int]] = []
    for begin, stop in sorted(spans):
        if kept and begin < kept[-1][1]:
            continue
        kept.append((begin, stop))
    for begin, stop in reversed(kept):
        data = data[:begin] + data[stop:]
    return data


def _plain(data: bytes) -> bytes:
    """Drop a slide's timing and show it if it is hidden."""
    data = re.sub(rb"<p:timing\b.*?</p:timing>|<p:timing\b[^>]*/>", b"", data, flags=re.S)
    return re.sub(rb'(<p:sld\b[^>]*?)\s+show="(?:0|false)"', rb"\1", data, count=1)


def _order(parts: dict[str, bytes]) -> list[str]:
    """List the deck's slide parts in the order the deck shows them."""
    targets = {}
    for found in RELATION.findall(parts["ppt/_rels/presentation.xml.rels"]):
        node = ET.fromstring(found)
        targets[node.get("Id")] = posixpath.normpath(
            posixpath.join("ppt", node.get("Target", "").lstrip("/").removeprefix("ppt/"))
        )
    listing = ET.fromstring(parts["ppt/presentation.xml"]).find(f"{{{P}}}sldIdLst")
    return [] if listing is None else [targets[node.get(f"{{{R}}}id")] for node in listing]


def expand(deck: Path, copy: Path) -> tuple[list[State], list[str]]:
    """Write `copy`: the deck at `deck` with one plain slide per click state.

    Returns the click states, one per slide of the copy in order, and the ids of the slides
    that have an effect other than Appear and Disappear. Such an effect changes nothing in
    the pictures. `deck` is only read.
    """
    with ZipFile(deck) as archive:
        parts = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    order = _order(parts)
    result = {
        name: data
        for name, data in parts.items()
        if not name.startswith(("ppt/slides/slide", "ppt/slides/_rels/"))
    }
    states: list[State] = []
    unshown: list[str] = []
    listed: list[bytes] = []
    relations: list[bytes] = []
    overrides: list[bytes] = []
    taken: set[str] = set()
    for page, part in enumerate(order, 1):
        data = parts[part]
        root = ET.fromstring(data)
        sld = root.find(f"{{{P}}}cSld")
        name = (sld.get("name") if sld is not None else None) or f"slide{page}"
        # A slide copied by hand in PowerPoint keeps its name; no two pictures may share one.
        ident = name if name not in taken else f"{name}~{page}"
        taken.add(ident)
        hidden = root.get("show") in ("0", "false")
        clicks = stage.click_states(data)
        if any(change.effect == "other" for click in clicks for change in click):
            unshown.append(ident)
        spans = _spans(data)
        # A shape whose first effect is Appear is not there when the slide opens.
        shown: dict[str, bool] = {}
        for click in clicks:
            for change in click:
                if change.effect != "other":
                    shown.setdefault(change.shape, change.effect != "appear")
        rels = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
        for made in range(len(clicks) + 1):
            for change in clicks[made - 1] if made else []:
                if change.effect != "other":
                    shown[change.shape] = change.effect == "appear"
            cut = [span for shape, up in shown.items() if not up for span in spans.get(shape, [])]
            number = len(states) + 1
            result[f"ppt/slides/slide{number}.xml"] = _plain(_without(data, cut))
            if rels in parts:
                result[f"ppt/slides/_rels/slide{number}.xml.rels"] = parts[rels]
            listed.append(f'<p:sldId id="{255 + number}" r:id="rIdState{number}"/>'.encode())
            relations.append(
                f'<Relationship Id="rIdState{number}" Type="{R}/slide" '
                f'Target="slides/slide{number}.xml"/>'.encode()
            )
            overrides.append(
                f'<Override PartName="/ppt/slides/slide{number}.xml" '
                f'ContentType="{SLIDE_TYPE}"/>'.encode()
            )
            states.append(State(ident, page, made, hidden))

    presentation = parts["ppt/presentation.xml"]
    presentation, swapped = re.subn(
        rb"<p:sldIdLst>.*?</p:sldIdLst>",
        lambda _: b"<p:sldIdLst>" + b"".join(listed) + b"</p:sldIdLst>",
        presentation,
        count=1,
        flags=re.S,
    )
    if swapped != 1:
        raise Refusal(f"{deck.name} lists no slides, so there is nothing to render.")
    # A custom show names slides by the relations dropped below.
    presentation = re.sub(rb"<p:custShowLst>.*?</p:custShowLst>", b"", presentation, flags=re.S)
    result["ppt/presentation.xml"] = presentation
    name = "ppt/_rels/presentation.xml.rels"
    kept = RELATION.sub(
        lambda found: b"" if ET.fromstring(found[0]).get("Type") == f"{R}/slide" else found[0],
        parts[name],
    )
    result[name] = kept.replace(b"</Relationships>", b"".join(relations) + b"</Relationships>")
    name = "[Content_Types].xml"
    result[name] = OVERRIDE.sub(b"", parts[name]).replace(
        b"</Types>", b"".join(overrides) + b"</Types>"
    )
    write(copy, result)
    return states, unshown


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(folder: Folder) -> Report:
    """Render every click state of the deck of `folder` into its `renders/` folder.

    Nothing in `renders/` changes until every picture is made, and the deck is only read.

    Raises
    ------
    Refusal
        When there is no built deck, or LibreOffice or Poppler is missing or fails.
    """
    deck = folder.output
    if not deck.is_file():
        raise Refusal(f"there is no {deck.name} to render; run `lab-deck build` first.")
    out = folder.path / RENDERS
    with tempfile.TemporaryDirectory(prefix=".lab-deck-", dir=folder.path) as scratch:
        work = Path(scratch)
        copy = work / "click-states.pptx"
        states, unshown = expand(deck, copy)
        pages = to_pictures(to_pdf(copy, work), work)
        if len(pages) != len(states):
            raise Refusal(
                f"the deck has {len(states)} click states, but LibreOffice wrote "
                f"{len(pages)} pages, so no picture can be named. {out.name}/ was left as it was."
            )
        out.mkdir(exist_ok=True)
        # The folder ignores itself, so a deck folder made before this command needs no edit.
        (out / ".gitignore").write_text("*\n", encoding="utf-8")
        new, changed = [], []
        for state, page in zip(states, pages, strict=True):
            last = out / state.picture
            if not last.is_file():
                new.append(state)
            elif _digest(last) != _digest(page):
                changed.append(state)
            else:
                continue
            page.replace(last)
        names = {state.picture for state in states}
        gone = sorted(old.name for old in out.glob("*.png") if old.name not in names)
        for name in gone:
            (out / name).unlink()
    return Report(out, states, new, changed, gone, unshown)


def text(report: Report) -> str:
    """Spell a render's report: the count, then each picture to look at."""
    slides = len({state.slide for state in report.states})
    count = len(report.states)
    where = f"{report.folder.name}/"
    lines = [
        f"rendered {count} click state{'' if count == 1 else 's'} of {slides} "
        f"slide{'' if slides == 1 else 's'} into {where}"
    ]
    for word, states in (("new", report.new), ("changed", report.changed)):
        lines += [f"{word}: {where}{state.picture}  {state.label}" for state in states]
    lines += [f"gone: {where}{name}  no slide has this click state now" for name in report.gone]
    if not (report.new or report.changed or report.gone):
        lines.append("no picture changed since the last render")
    else:
        same = count - len(report.new) - len(report.changed)
        lines.append(f"{same} picture{'' if same == 1 else 's'} did not change")
    return "\n".join(lines)
