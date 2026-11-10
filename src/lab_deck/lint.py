"""Lint a built deck in plain code: no model, no tokens, about a second.

The lint reads the deck file and nothing else. The room, which sets the size floor, the
use and the known terms come from the audience brief through the caller. `build` runs the
lint on the deck it is about to write and refuses to replace the last built deck when a
blocking check fails.

A check is one entry of `CHECKS`: a name, a severity, the slide rule it enforces and a
function that reads one slide. A `blocking` check stops a build. A `warning` check is
reported and stops nothing. To add a check, write its function and add its entry.

Whether text fits its box is an estimate. The lint sums glyph widths from the font's file,
read with fontTools, and wraps lines as PowerPoint does. When the file is not on this
machine it uses the widths of Helvetica, which Arial copies. It knows no kerning and none of
PowerPoint's own line breaking, so the report calls the result an estimate.
"""

from __future__ import annotations

import posixpath
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from functools import cache
from itertools import pairwise
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fontTools.ttLib import TTFont, TTLibError

from lab_deck import stage
from lab_deck.folder import PRESENTED, READ_ALONE, ROOMS, Refusal
from lab_deck.house import CITATION, CITATION_SIZE, PAGE_NUMBER, SENTENCE, TITLE
from lab_deck.house import EMU_PER_POINT as POINT
from lab_deck.merge import A, P, R

NS = {"p": P, "a": A}
BLOCKING = "blocking"
WARNING = "warning"

# What DrawingML gives a run that states no size, and a text box that states no inset.
DEFAULT_SIZE = 18.0
INSET_X = 91440
INSET_Y = 45720
# A line of text is this many times its font size tall, as PowerPoint sets single spacing.
LINE = 1.2
# How far past its box the estimate must run before the lint calls it an overflow.
SLACK = 1.05
# The share of regular width a bold face adds, for a font with no bold file to read.
BOLD = 1.07
CUE = re.compile(r"\[Click\]")

# The limits of the warning checks. The slide-rules page says how each was chosen.
# The most words a slide carries beside its title, its citation and its page number.
WORDS = 100
# The most lines a title takes.
TITLE_LINES = 2
# The fewest words a line holds before the lint reads it as a sentence.
SENTENCE_WORDS = 4
# A line that opens with one of these has a subject, and is a sentence with no full stop.
SUBJECT = re.compile(r"(We|I|It|They|There|He|She|You)\s")
# A short form whose full stop ends no sentence.
SHORT_FORM = re.compile(r"\b(e\.g|i\.e|etc|et al|vs|cf|Fig|approx)\.")
# The longest word of capital letters alone the lint reads as an abbreviation.
ABBREVIATION = 6
# A word of letters and digits, and a Roman numeral, which is no abbreviation.
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
ROMAN = re.compile(r"[IVX]+")
# Chinese and typographic punctuation, read as its plain form. NFKC first turns full-width
# brackets, question marks and exclamation marks into their plain forms.
PLAIN = str.maketrans("。”\u2019」』", '."\'""')

# Advance widths of Helvetica, in thousandths of the font size, for the characters from the
# space to the tilde. Arial has the same widths. Used when the font's file is not found.
HELVETICA = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
)  # fmt: skip
OTHER = 556


@dataclass(frozen=True)
class Run:
    """A run of text in one size and weight. A forced line break is a run of one newline."""

    text: str
    size: float
    bold: bool
    font: str | None
    color: str | None = None
    """The colour the run states, as six hex digits or a theme colour's name."""


@dataclass(frozen=True)
class Paragraph:
    """One paragraph: its runs, its alignment and its spacing in points."""

    runs: tuple[Run, ...]
    align: str = "l"
    before: float = 0.0
    after: float = 0.0
    spacing: float | None = None
    """Line height as a multiple of single spacing, when the paragraph sets one."""
    exact: float | None = None
    """Line height in points, when the paragraph sets one."""

    @property
    def text(self) -> str:
        """The paragraph's words."""
        return "".join(run.text for run in self.runs)


@dataclass(frozen=True)
class Shape:
    """One object of a slide, with its box in EMU on the slide and the text it holds."""

    ident: str
    name: str
    kind: str
    """`sp` a shape or text box, `pic` a picture, `graphicFrame` a table, `grpSp` a group."""
    x: float
    y: float
    w: float
    h: float
    owners: tuple[str, ...]
    """Its own shape id and the id of every group around it: a click on any of them moves it."""
    paragraphs: tuple[Paragraph, ...] = ()
    insets: tuple[float, float, float, float] = (INSET_X, INSET_Y, INSET_X, INSET_Y)
    """Left, top, right, bottom, in EMU."""
    anchor: str = "t"
    wrap: bool = True

    @property
    def text(self) -> str:
        """The shape's words, one paragraph to a line."""
        return "\n".join(paragraph.text for paragraph in self.paragraphs).strip()


@dataclass(frozen=True)
class Slide:
    """One slide of the deck, as the checks read it."""

    ident: str
    page: int
    shapes: tuple[Shape, ...]
    """Every object in drawing order, a group before the shapes inside it."""
    clicks: tuple[tuple[stage.Change, ...], ...]
    notes: str


@dataclass(frozen=True)
class Setup:
    """What the checks need beside the slide: the brief's lines and the font widths."""

    floor: int
    fonts: Fonts
    use: str = PRESENTED
    """`presented` or `read alone`. A deck read alone may carry sentences and more words."""
    known: frozenset[str] = frozenset()
    """The brief's known terms and each word of them, in lower case."""
    first: dict[str, int] = field(default_factory=dict)
    """The page each abbreviation of the deck is first used on."""
    spelled: dict[str, int] = field(default_factory=dict)
    """The page each abbreviation is first spelled out on, for those that are."""


@dataclass(frozen=True)
class Check:
    """One lint check."""

    name: str
    severity: str
    """`blocking` stops a build; `warning` is reported and stops nothing."""
    rule: int
    """The id of the slide rule it enforces, in the skill's slide-rules page."""
    run: Callable[[Slide, Setup], Iterable[tuple[str, str]]]
    """Reads one slide and gives a (shape name, message) for each failure."""


@dataclass(frozen=True)
class Finding:
    """One failure of one check on one shape."""

    check: str
    severity: str
    rule: int
    slide: str
    page: int
    shape: str
    message: str


@dataclass(frozen=True)
class Report:
    """What the lint found in one deck."""

    room: str
    floor: int
    slides: int
    findings: tuple[Finding, ...]
    measured: str
    """How text widths were found, in words for the report."""

    @property
    def blocking(self) -> tuple[Finding, ...]:
        """The findings that stop a build."""
        return tuple(one for one in self.findings if one.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        """The findings that are reported and stop nothing."""
        return tuple(one for one in self.findings if one.severity == WARNING)


# ------------------------------ font widths ------------------------------


def _font_folders() -> list[Path]:
    """List the folders this machine keeps fonts in."""
    home = Path.home()
    return [
        home / "Library" / "Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
        Path("/System/Library/Fonts"),
        home / ".fonts",
        home / ".local" / "share" / "fonts",
        Path("/usr/local/share/fonts"),
        Path("/usr/share/fonts"),
        Path(sys.prefix) / "fonts",
    ]


def _plain(name: str) -> str:
    """Spell a font name as its letters and digits only, in lower case."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@cache
def _faces(family: str) -> dict[bool, tuple[dict[int, int], int]]:
    """Read the widths of a font family from its files: by bold, (width by character, em).

    Empty when no file of the family is on this machine.
    """
    wanted = _plain(family)
    found: dict[bool, tuple[dict[int, int], int]] = {}
    if not wanted:
        return found
    for folder in _font_folders():
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            # The file name is a cheap first look; the name table inside decides.
            if not _plain(path.stem).startswith(wanted):
                continue
            for number in range(16 if path.suffix.lower() == ".ttc" else 1):
                try:
                    font = TTFont(path, fontNumber=number, lazy=True)
                except (TTLibError, OSError, IndexError):
                    break
                names = font["name"]
                if _plain(names.getBestFamilyName() or "") != wanted:
                    continue
                style = _plain(names.getBestSubFamilyName() or "")
                if style not in ("regular", "bold") or (style == "bold") in found:
                    continue
                cmap = font.getBestCmap() or {}
                advance = font["hmtx"].metrics
                widths = {code: advance[glyph][0] for code, glyph in cmap.items()}
                found[style == "bold"] = (widths, getattr(font["head"], "unitsPerEm", 1000))
            if len(found) == 2:
                return found
    return found


@dataclass
class Fonts:
    """Text widths, from each font's file where it is found and from a table where not."""

    family: str
    """The font a run that names none is measured in."""
    missing: set[str] = field(default_factory=set)
    used: set[str] = field(default_factory=set)

    def width(self, text: str, size: float, bold: bool, font: str | None = None) -> float:
        """Estimate the width of `text` on one line, in points."""
        family = font or self.family
        faces = _faces(family)
        (self.used if faces else self.missing).add(family)
        widths, em = faces.get(bold) or faces.get(False) or ({}, 1000)
        scale = BOLD if bold and bold not in faces else 1.0
        total = 0.0
        for char in text:
            code = ord(char)
            if unicodedata.east_asian_width(char) in ("W", "F"):
                # A full-width character, Chinese among them, fills a square of the font size.
                total += 1.0
            elif code in widths:
                total += widths[code] / em * scale
            elif 32 <= code <= 126:
                total += HELVETICA[code - 32] / 1000 * scale
            else:
                total += OTHER / 1000 * scale
        return total * size

    @property
    def how(self) -> str:
        """Say how the widths were found."""
        if self.missing:
            names = ", ".join(sorted(self.missing))
            return (
                f"Text widths are an estimate from Helvetica's widths: no font file for {names} "
                "was found on this machine."
            )
        if self.used:
            return (
                f"Text widths are an estimate from the font file of {', '.join(sorted(self.used))}."
            )
        return "Text widths are an estimate from font widths."


# ------------------------------ reading the deck ------------------------------


def _points(node: ET.Element | None, path: str) -> float:
    """Read a spacing given in points, in hundredths, or 0."""
    found = None if node is None else node.find(path, NS)
    return 0.0 if found is None else int(found.get("val", 0)) / 100


def _paragraphs(body: ET.Element) -> list[Paragraph]:
    """Read the paragraphs of one text body."""
    paragraphs = []
    for para in body.findall("a:p", NS):
        props = para.find("a:pPr", NS)
        end = para.find("a:endParaRPr", NS)
        size = DEFAULT_SIZE if end is None or not end.get("sz") else int(end.get("sz", 0)) / 100
        runs = []
        for node in para:
            kind = node.tag.rsplit("}", 1)[-1]
            if kind == "br":
                runs.append(Run("\n", size, False, None))
            if kind not in ("r", "fld"):
                continue
            look = node.find("a:rPr", NS)
            if look is not None and look.get("sz"):
                size = int(look.get("sz", 0)) / 100
            latin = None if look is None else look.find("a:latin", NS)
            fill = None if look is None else look.find("a:solidFill", NS)
            color = None if fill is None or not len(fill) else fill[0].get("val")
            runs.append(
                Run(
                    node.findtext("a:t", "", NS),
                    size,
                    look is not None and look.get("b") in ("1", "true"),
                    None if latin is None else latin.get("typeface"),
                    color,
                )
            )
        percent = None if props is None else props.find("a:lnSpc/a:spcPct", NS)
        exact = _points(props, "a:lnSpc/a:spcPts")
        paragraphs.append(
            Paragraph(
                tuple(runs),
                align="l" if props is None else props.get("algn", "l"),
                before=_points(props, "a:spcBef/a:spcPts"),
                after=_points(props, "a:spcAft/a:spcPts"),
                spacing=None if percent is None else int(percent.get("val", 100000)) / 100000,
                exact=exact or None,
            )
        )
    return paragraphs


def _shapes(
    tree: ET.Element,
    place: Callable[[float, float, float, float], tuple[float, ...]],
    owners: tuple[str, ...],
) -> Iterator[Shape]:
    """Walk one shape tree in drawing order. `place` turns a box in the tree into the slide's."""
    for child in tree:
        kind = child.tag.rsplit("}", 1)[-1]
        if kind in ("nvGrpSpPr", "grpSpPr"):
            continue
        named = next(child.iter(f"{{{P}}}cNvPr"), None)
        if named is None:
            continue
        ident, name = named.get("id", ""), named.get("name", "")
        xfrm = child.find("p:grpSpPr/a:xfrm" if kind == "grpSp" else "p:spPr/a:xfrm", NS)
        if xfrm is None:
            xfrm = child.find("p:xfrm", NS)
        off = None if xfrm is None else xfrm.find("a:off", NS)
        ext = None if xfrm is None else xfrm.find("a:ext", NS)
        raw = (
            float(off.get("x", 0)) if off is not None else 0.0,
            float(off.get("y", 0)) if off is not None else 0.0,
            float(ext.get("cx", 0)) if ext is not None else 0.0,
            float(ext.get("cy", 0)) if ext is not None else 0.0,
        )
        x, y, w, h = place(*raw)
        mine = (*owners, ident)
        if kind == "grpSp":
            yield Shape(ident, name, kind, x, y, w, h, mine)
            inner_off = None if xfrm is None else xfrm.find("a:chOff", NS)
            inner_ext = None if xfrm is None else xfrm.find("a:chExt", NS)
            cx = float(inner_ext.get("cx", 0)) if inner_ext is not None else 0.0
            cy = float(inner_ext.get("cy", 0)) if inner_ext is not None else 0.0
            ox = float(inner_off.get("x", 0)) if inner_off is not None else raw[0]
            oy = float(inner_off.get("y", 0)) if inner_off is not None else raw[1]
            sx = raw[2] / cx if cx else 1.0
            sy = raw[3] / cy if cy else 1.0

            def inside(
                a: float,
                b: float,
                c: float,
                d: float,
                box: tuple[float, ...] = (raw[0], raw[1], ox, oy, sx, sy),
                outer: Callable[[float, float, float, float], tuple[float, ...]] = place,
            ) -> tuple[float, ...]:
                gx, gy, kx, ky, zx, zy = box
                return outer(gx + (a - kx) * zx, gy + (b - ky) * zy, c * zx, d * zy)

            yield from _shapes(child, inside, mine)
            continue
        paragraphs: list[Paragraph] = []
        left, top, right, bottom = float(INSET_X), float(INSET_Y), float(INSET_X), float(INSET_Y)
        anchor, wrap = "t", True
        body = child.find("p:txBody", NS)
        if body is not None:
            paragraphs = _paragraphs(body)
            props = body.find("a:bodyPr", NS)
            if props is not None:
                left = float(props.get("lIns", left))
                top = float(props.get("tIns", top))
                right = float(props.get("rIns", right))
                bottom = float(props.get("bIns", bottom))
                anchor = props.get("anchor", "t")
                wrap = props.get("wrap", "square") != "none"
        elif kind == "graphicFrame":
            for cell in child.iter(f"{{{A}}}txBody"):
                paragraphs += _paragraphs(cell)
        insets = (left, top, right, bottom)
        yield Shape(ident, name, kind, x, y, w, h, mine, tuple(paragraphs), insets, anchor, wrap)


def _same(x: float, y: float, w: float, h: float) -> tuple[float, ...]:
    return (x, y, w, h)


def _target(owner: str, target: str) -> str:
    """Name the part a relationship of `owner` points at."""
    return posixpath.normpath(posixpath.join(posixpath.dirname(owner), target)).lstrip("/")


def _relations(parts: dict[str, bytes], owner: str) -> list[ET.Element]:
    """List the relationships of one part."""
    name = posixpath.join(posixpath.dirname(owner), "_rels", posixpath.basename(owner) + ".rels")
    return list(ET.fromstring(parts[name])) if name in parts else []


def read(deck: Path) -> list[Slide]:
    """Read every slide of a deck, in the order shown.

    Raises
    ------
    Refusal
        When the file is missing or is not a PowerPoint deck.
    """
    try:
        with ZipFile(deck) as archive:
            parts = {
                name: archive.read(name)
                for name in archive.namelist()
                if name.endswith((".xml", ".rels"))
            }
        owner = "ppt/presentation.xml"
        targets = {one.get("Id"): one.get("Target", "") for one in _relations(parts, owner)}
        order = [
            _target(owner, targets[node.get(f"{{{R}}}id")])
            for node in ET.fromstring(parts[owner]).iter(f"{{{P}}}sldId")
        ]
        slides = []
        for page, name in enumerate(order, 1):
            data = parts[name]
            root = ET.fromstring(data)
            sld = root.find("p:cSld", NS)
            tree = None if sld is None else sld.find("p:spTree", NS)
            if sld is None or tree is None:
                raise KeyError(name)
            notes = ""
            for relation in _relations(parts, name):
                if relation.get("Type", "").endswith("/notesSlide"):
                    notes = _notes(parts[_target(name, relation.get("Target", ""))])
            slides.append(
                Slide(
                    ident=sld.get("name") or str(page),
                    page=page,
                    shapes=tuple(_shapes(tree, _same, ())),
                    clicks=tuple(tuple(click) for click in stage.click_states(data)),
                    notes=notes,
                )
            )
    except FileNotFoundError:
        raise Refusal(f"{deck.name} is not built yet; run `lab-deck build` first.") from None
    except (BadZipFile, KeyError, ET.ParseError, ValueError):
        raise Refusal(f"{deck.name} is not a PowerPoint deck the lint can read.") from None
    return slides


def _notes(data: bytes) -> str:
    """Read the speaker notes of one notes slide: the text of its body placeholder."""
    lines = []
    for shape in ET.fromstring(data).iter(f"{{{P}}}sp"):
        if shape.find("p:nvSpPr/p:nvPr/p:ph[@type='body']", NS) is None:
            continue
        for para in shape.iter(f"{{{A}}}p"):
            lines.append("".join(node.text or "" for node in para.iter(f"{{{A}}}t")))
    return "\n".join(lines)


# ------------------------------ laying text out ------------------------------


@dataclass(frozen=True)
class Block:
    """The estimated extent of a shape's text, in points."""

    lines: int
    width: float
    height: float


def _breaks(char: str) -> bool:
    """Say whether a line may break on either side of this character, as in Chinese text."""
    return unicodedata.east_asian_width(char) in ("W", "F")


def _wrap(atoms: list[tuple[str, float]], room: float) -> list[float]:
    """Wrap one forced line of (character, width) into lines, and give each line's width.

    A line breaks after a space and beside a full-width character. A word wider than the
    line breaks inside itself, as PowerPoint breaks it.
    """
    words: list[list[tuple[str, float]]] = [[]]
    for char, width in atoms:
        if _breaks(char) and words[-1]:
            words.append([])
        words[-1].append((char, width))
        if char == " " or _breaks(char):
            words.append([])
    lines = [0.0]
    pending = 0.0  # the spaces that end the line so far; they count only if a word follows
    for word in words:
        inked = sum(width for char, width in word if char != " ")
        spaces = sum(width for char, width in word if char == " ")
        if not word:
            continue
        if lines[-1] and lines[-1] + pending + inked > room:
            lines.append(0.0)
            pending = 0.0
        if inked > room:
            for _, width in word:
                if lines[-1] and lines[-1] + width > room:
                    lines.append(0.0)
                lines[-1] += width
            pending = 0.0
            continue
        lines[-1] += pending + inked
        pending = spaces
    return lines


def layout(shape: Shape, fonts: Fonts) -> Block:
    """Estimate how many lines the shape's text takes, and how wide and tall they are."""
    room = (shape.w - shape.insets[0] - shape.insets[2]) / POINT if shape.wrap else float("inf")
    room = max(room, 1.0)
    count, widest, height = 0, 0.0, 0.0
    last = len(shape.paragraphs) - 1
    for place, para in enumerate(shape.paragraphs):
        size = max((run.size for run in para.runs if run.text.strip()), default=None)
        if size is None:
            size = para.runs[0].size if para.runs else DEFAULT_SIZE
        forced: list[list[tuple[str, float]]] = [[]]
        for run in para.runs:
            for char in run.text:
                if char == "\n":
                    forced.append([])
                else:
                    forced[-1].append((char, fonts.width(char, run.size, run.bold, run.font)))
        lines = [width for atoms in forced for width in _wrap(atoms, room)]
        tall = para.exact if para.exact is not None else LINE * size * (para.spacing or 1.0)
        count += len(lines)
        widest = max(widest, *lines)
        height += tall * len(lines)
        # Space above the first paragraph and below the last is not drawn.
        height += (para.before if place else 0.0) + (para.after if place < last else 0.0)
    return Block(count, widest, height)


def _text_box(shape: Shape, fonts: Fonts) -> tuple[float, float, float, float]:
    """Estimate where the shape's text sits on the slide: left, top, right, bottom, in EMU."""
    if shape.kind != "sp":
        return (shape.x, shape.y, shape.x + shape.w, shape.y + shape.h)
    block = layout(shape, fonts)
    left, top, right, bottom = shape.insets
    wide, tall = block.width * POINT, block.height * POINT
    inner_w = shape.w - left - right
    inner_h = shape.h - top - bottom
    align = shape.paragraphs[0].align if shape.paragraphs else "l"
    x = shape.x + left + {"ctr": (inner_w - wide) / 2, "r": inner_w - wide}.get(align, 0.0)
    y = shape.y + top + {"ctr": (inner_h - tall) / 2, "b": inner_h - tall}.get(shape.anchor, 0.0)
    return (x, y, x + wide, y + tall)


# ------------------------------ the checks ------------------------------


def _quote(text: str, most: int = 40) -> str:
    """Quote the start of some text, on one line."""
    flat = " ".join(text.split())
    return f'"{flat if len(flat) <= most else flat[: most - 1] + "…"}"'


def _size(size: float) -> str:
    return f"{size:g} pt"


def size_floor(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find text under the size floor. The page number is exempt; one citation may be 12 pt."""
    citations = 0
    for shape in slide.shapes:
        if not shape.text or shape.name == PAGE_NUMBER:
            continue
        floor = float(setup.floor)
        if shape.name == CITATION:
            citations += 1
            if citations > 1:
                yield (
                    shape.name,
                    f"a second citation line; a slide may carry one line under the "
                    f"{_size(setup.floor)} floor",
                )
                continue
            floor = float(CITATION_SIZE)
            lines = layout(shape, setup.fonts).lines
            if lines > 1:
                yield (
                    shape.name,
                    f"the citation takes about {lines} lines (an estimate from font widths); "
                    f"one line at {_size(CITATION_SIZE)} is allowed",
                )
        small = [
            run
            for paragraph in shape.paragraphs
            for run in paragraph.runs
            if run.text.strip() and run.size < floor
        ]
        if small:
            run = min(small, key=lambda one: one.size)
            yield (
                shape.name,
                f"{_quote(run.text)} is {_size(run.size)}, under the {_size(floor)} floor",
            )


def text_overflow(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find text that takes more height than its box has, by an estimate from font widths."""
    for shape in slide.shapes:
        # A table grows its rows to hold its text, so its frame says nothing about a fit.
        # A box of negative size is the `negative-size` check's to report, not this one's.
        if shape.kind != "sp" or not shape.text or shape.w < 0 or shape.h < 0:
            continue
        block = layout(shape, setup.fonts)
        room = (shape.h - shape.insets[1] - shape.insets[3]) / POINT
        if block.height > room * SLACK:
            yield (
                shape.name,
                f"{_quote(shape.text)} takes about {block.lines} lines and {block.height:.0f} pt "
                f"of height, and its box has {max(room, 0):.0f} pt (an estimate from font widths)",
            )


def _hidden(slide: Slide) -> list[set[str]]:
    """List, for each click state of the slide, the shape ids hidden in it."""
    first: dict[str, str] = {}
    for click in slide.clicks:
        for change in click:
            first.setdefault(change.shape, change.effect)
    hidden = {shape for shape, effect in first.items() if effect == "appear"}
    states = [set(hidden)]
    for click in slide.clicks:
        for change in click:
            if change.effect == "appear":
                hidden.discard(change.shape)
            elif change.effect == "disappear":
                hidden.add(change.shape)
        states.append(set(hidden))
    return states


def picture_over_text(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a picture drawn over text, in a click state that shows both."""
    states = _hidden(slide)
    texts: list[tuple[Shape, tuple[float, float, float, float]]] = []
    for shape in slide.shapes:
        if shape.kind == "pic":
            for under, (left, top, right, bottom) in texts:
                # A point of slack on every side: an edge that only touches covers nothing.
                covers = (
                    shape.x < right - POINT
                    and shape.x + shape.w > left + POINT
                    and shape.y < bottom - POINT
                    and shape.y + shape.h > top + POINT
                )
                together = any(
                    not hidden.intersection(shape.owners) and not hidden.intersection(under.owners)
                    for hidden in states
                )
                if covers and together:
                    yield (
                        shape.name,
                        f'the picture covers the text {_quote(under.text)} of "{under.name}" '
                        "(the text's place is an estimate from font widths)",
                    )
        elif shape.text and shape.w >= 0 and shape.h >= 0:
            texts.append((shape, _text_box(shape, setup.fonts)))


def negative_size(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a shape whose width or height is under zero."""
    for shape in slide.shapes:
        for side, value in (("width", shape.w), ("height", shape.h)):
            if value < 0:
                yield (shape.name, f"its {side} is negative ({value / POINT:.0f} pt)")


def click_cues(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find notes whose `[Click]` cues are not one per click. Empty notes are not checked."""
    if not slide.notes.strip():
        return
    cues, clicks = len(CUE.findall(slide.notes)), len(slide.clicks)
    if cues != clicks:
        yield (
            "notes",
            f"the notes carry {cues} [Click] cue{'' if cues == 1 else 's'}, and the slide has "
            f"{clicks} click{'' if clicks == 1 else 's'} ({clicks + 1} click states)",
        )


def _plain_marks(text: str) -> str:
    """Spell Chinese and typographic punctuation as its plain form."""
    return unicodedata.normalize("NFKC", text).translate(PLAIN)


def _wide_letter(char: str) -> bool:
    """Say whether this is a full-width letter, such as a Chinese character: not punctuation."""
    return unicodedata.east_asian_width(char) in ("W", "F") and unicodedata.category(char) == "Lo"


def count_words(text: str) -> int:
    """Count the words of some text. A Chinese character counts as one word.

    A word is a run of characters between spaces that holds a letter or a digit. A full-width
    letter, such as a Chinese character or a kana, is a word by itself.
    """
    rest = "".join(" " if _wide_letter(char) else char for char in text)
    wide = sum(1 for char in text if _wide_letter(char))
    return wide + sum(1 for word in rest.split() if any(char.isalnum() for char in word))


def _body(slide: Slide) -> Iterator[Shape]:
    """Give the shapes whose text is the slide's body: not its title, citation or page number."""
    for shape in slide.shapes:
        if shape.text and shape.name not in (TITLE, CITATION, PAGE_NUMBER):
            yield shape


def slide_words(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a slide that carries more words than the limit. A deck read alone is not checked."""
    if setup.use == READ_ALONE:
        return
    words = sum(count_words(shape.text) for shape in _body(slide))
    if words > WORDS:
        yield (
            "slide",
            f"the slide carries {words} words beside its title, and the limit is {WORDS} "
            "(a Chinese character counts as one word)",
        )


def sentence(text: str) -> str | None:
    """Say why a line reads as a full sentence, or None when it reads as a phrase.

    A guess from the line's punctuation and its first word: the lint parses no grammar.
    """
    flat = SHORT_FORM.sub(r"\1", " ".join(_plain_marks(text).split()))
    if count_words(flat) < SENTENCE_WORDS:
        return None
    bare = flat.rstrip("\"') ")
    if bare.endswith((".", "!", "?")) and not bare.endswith(".."):
        return "it ends as a sentence does"
    if re.search(r"[a-z)][.!?] +[A-Z]", bare) or any(
        end in ".!?" and _wide_letter(after) for end, after in pairwise(bare)
    ):
        return "it holds the end of a sentence"
    if SUBJECT.match(flat):
        return f"it opens with a subject, {flat.split()[0]}"
    return None


def body_sentence(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a full sentence below the title. An intended sentence and a deck read alone pass."""
    if setup.use == READ_ALONE:
        return
    for shape in _body(slide):
        if shape.name.startswith(SENTENCE):
            continue
        for paragraph in shape.paragraphs:
            why = sentence(paragraph.text)
            if why is not None:
                yield (shape.name, f"{_quote(paragraph.text)} reads as a full sentence: {why}")


def title_lines(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a title that takes more than two lines, by an estimate from font widths."""
    for shape in slide.shapes:
        if shape.name != TITLE or not shape.text or shape.w < 0:
            continue
        lines = layout(shape, setup.fonts).lines
        if lines > TITLE_LINES:
            yield (
                shape.name,
                f"the title takes about {lines} lines (an estimate from font widths), "
                f"and the limit is {TITLE_LINES}",
            )


def _capitals(line: str) -> bool:
    """Say whether a line is a heading set in capitals: two words or more, no small letter."""
    words = [word for word in line.split() if any(char.isalpha() for char in word)]
    return len(words) > 1 and not any(char.islower() for char in line)


def abbreviations(text: str) -> list[str]:
    """List the abbreviations in some text, each once, in the order met.

    An abbreviation is a word with two capitals or more, where at least half of its letters
    are capitals: DNA, mRNA, CpG. A plural loses its s. A Roman numeral is not one. Nor is
    a word of a heading set in capitals: a word of capital letters only that is longer than
    six characters, or any word of a line of two words or more that is all in capitals. A
    word with a digit in it, such as the name of a cell line, is an abbreviation at any
    length.
    """
    found: list[str] = []
    lines = [line for line in text.splitlines() if not _capitals(line)]
    for word in TOKEN.findall("\n".join(lines)):
        if word.isalpha() and word.isupper() and len(word) > ABBREVIATION:
            continue
        if len(word) > 3 and word.endswith("s") and word[-2].isupper():
            word = word[:-1]
        capitals = sum(1 for char in word if char.isupper())
        letters = sum(1 for char in word if char.isalpha())
        if capitals < 2 or capitals * 2 < letters or ROMAN.fullmatch(word):
            continue
        if word not in found:
            found.append(word)
    return found


def spelled_out(text: str) -> set[str]:
    """Find the abbreviations some text spells out: `long name (DNA)` or `DNA (long name)`."""
    found = set()
    for word in abbreviations(text):
        name = re.escape(word)
        if re.search(rf"\(\s*{name}s?\s*\)|\b{name}s?\s*\(\s*[^\s)]", _plain_marks(text)):
            found.add(word)
    return found


def _read(slide: Slide) -> Iterator[Shape]:
    """Give the shapes the abbreviation check reads: the title and the body, not the citation."""
    for shape in slide.shapes:
        if shape.text and shape.name not in (CITATION, PAGE_NUMBER):
            yield shape


def unknown_abbreviation(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find an abbreviation at its first use, unless it is known or spelled out by then."""
    seen: set[str] = set()
    for shape in _read(slide):
        for word in abbreviations(shape.text):
            if word in seen or setup.first.get(word) != slide.page:
                continue
            seen.add(word)
            if word.lower() in setup.known or setup.spelled.get(word, slide.page + 1) <= slide.page:
                continue
            yield (
                shape.name,
                f"{word} is first used here, is not spelled out on this slide or an earlier "
                "one, and is not in the brief's known terms",
            )


def _accent(color: str) -> bool:
    """Say whether a text colour is an accent: not black, white or a grey."""
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        # A theme colour: its text and background colours are plain, the others accents.
        return color.startswith(("accent", "hlink", "folHlink"))
    return not color[0:2].lower() == color[2:4].lower() == color[4:6].lower()


def accent_colours(slide: Slide, setup: Setup) -> Iterator[tuple[str, str]]:
    """Find a slide whose text is in more than one accent colour."""
    found: dict[str, str] = {}
    for shape in slide.shapes:
        for paragraph in shape.paragraphs:
            for run in paragraph.runs:
                if run.text.strip() and run.color and _accent(run.color):
                    found.setdefault(run.color.upper(), shape.name)
    if len(found) > 1:
        colours = list(found)
        yield (
            found[colours[1]],
            f"the slide's text is in {len(colours)} accent colours ({', '.join(colours)}); "
            "one accent colour marks what the slide is about",
        )


# Every check the lint runs, in the order reported. The rule ids are those of the slide-rules
# page of the `lab-presentation` skill, which names each check beside its rule.
CHECKS: tuple[Check, ...] = (
    Check("size-floor", BLOCKING, 8, size_floor),
    Check("text-overflow", BLOCKING, 8, text_overflow),
    Check("picture-over-text", BLOCKING, 16, picture_over_text),
    Check("negative-size", BLOCKING, 17, negative_size),
    Check("click-cues", BLOCKING, 18, click_cues),
    Check("slide-words", WARNING, 1, slide_words),
    Check("body-sentence", WARNING, 1, body_sentence),
    Check("title-lines", WARNING, 2, title_lines),
    Check("unknown-abbreviation", WARNING, 4, unknown_abbreviation),
    Check("accent-colours", WARNING, 9, accent_colours),
)


def _family(slides: list[Slide]) -> str:
    """Name the font most runs of the deck are set in: the theme's font."""
    counts: dict[str, int] = {}
    for slide in slides:
        for shape in slide.shapes:
            for paragraph in shape.paragraphs:
                for run in paragraph.runs:
                    if run.font:
                        counts[run.font] = counts.get(run.font, 0) + len(run.text)
    return max(counts, key=lambda name: counts[name]) if counts else "Arial"


def lint(deck: Path, room: str, use: str = PRESENTED, known_terms: Iterable[str] = ()) -> Report:
    """Run every check on the deck at `deck`, for the room, use and known terms of the brief.

    Raises
    ------
    Refusal
        When the deck is missing or cannot be read.
    """
    slides = read(deck)
    floor = ROOMS[room]["floor"]
    terms = list(known_terms)
    known = {term.strip().lower() for term in terms}
    known |= {word.lower() for term in terms for word in TOKEN.findall(term)}
    first: dict[str, int] = {}
    spelled: dict[str, int] = {}
    for slide in slides:
        for shape in _read(slide):
            for word in abbreviations(shape.text):
                first.setdefault(word, slide.page)
            for word in spelled_out(shape.text):
                spelled.setdefault(word, slide.page)
    setup = Setup(floor, Fonts(_family(slides)), use, frozenset(known), first, spelled)
    findings = [
        Finding(check.name, check.severity, check.rule, slide.ident, slide.page, shape, message)
        for slide in slides
        for check in CHECKS
        for shape, message in check.run(slide, setup)
    ]
    return Report(room, floor, len(slides), tuple(findings), setup.fonts.how)


def render(report: Report, name: str) -> str:
    """Spell the report as text, under the deck's file name."""

    def listed(findings: tuple[Finding, ...]) -> list[str]:
        return [
            f'  slide {one.slide} (page {one.page}), shape "{one.shape}": '
            f"{one.check} (rule {one.rule}): {one.message}"
            for one in findings
        ]

    def count(number: int, what: str) -> str:
        return f"{number} {what}{'' if number == 1 else 's'}"

    setting = f"{report.room}, {report.floor} pt floor"
    if not report.findings:
        return (
            f"{name}: the lint passed on {count(report.slides, 'slide')} ({setting}). "
            f"{report.measured}"
        )
    lines = []
    if report.blocking:
        lines.append(f"{name}: {count(len(report.blocking), 'blocking failure')} ({setting})")
        lines += listed(report.blocking)
    if report.warnings:
        lines.append(f"{name}: {count(len(report.warnings), 'warning')} ({setting})")
        lines += listed(report.warnings)
    lines.append(report.measured)
    return "\n".join(lines)
