"""Report the hand edits in a deck: the deck file as it is now against its last build.

A member edits the built deck in PowerPoint and hands it back. `compare` reads the deck file
in the deck folder and the same file in the last commit that holds a build, and lists what
differs, slide by slide and shape by shape. It writes nothing: the agent copies each edit into
the slide source by hand, and a rebuild then keeps it.

PowerPoint rewrites every part when it saves: attributes change order, defaults are spelled
out, runs of text are split. So two decks are compared by what a shape means, never by their
XML: the words, the place and size, and the few properties of style listed in `SEEN`.

- A slide is matched by its id, the `name` of its `<p:cSld>`, which the build sets and
  PowerPoint keeps. Its place in the deck is free to change.
- A shape is matched by its shape id, which PowerPoint keeps. A shape inside a group is read
  at its place on the slide, so grouping two shapes moves neither.
- A build is told from a saved deck by the fixed time the build writes into the file.
"""

from __future__ import annotations

import difflib
import hashlib
import io
import json
import posixpath
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from zipfile import BadZipFile, ZipFile

from lab_deck.folder import Folder, Refusal
from lab_deck.merge import CORE_TIME, A, P, R

MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"

EMU = 914400  # in one inch
POINT = 12700  # EMU in one point
# A place or size must move by more than this to count: a quarter of a point.
SLACK = POINT / 4
# How far back to look for a commit that holds a build.
DEPTH = 200

# The page number is the slide's place in the deck, and the build writes it again.
PAGE = "Page number"
# A word, or the gap between two words: the unit two texts are lined up by.
WORD = re.compile(r"\s+|\S+")

SEEN = (
    "the words of a text box and of a table cell",
    "position, size, rotation and flips",
    "font, size, bold, italic, underline and colour of text",
    "alignment, bullet and level of a paragraph, and the vertical anchor of a text box",
    "fill, outline and preset geometry of a shape",
    "the file and the crop of a picture",
    "the rows, columns and column widths of a table",
    "the name of a shape",
    "added and deleted shapes and slides, and the order of the slides",
    "a slide hidden or shown again",
)
UNSEEN = (
    "animations and slide transitions",
    "speaker notes",
    "the order shapes are drawn in, front to back",
    "the slide background, the master, the layouts and the theme",
    "the height of a table and of its rows, and the borders and fills of its cells",
    "shadows and other effects, transparency, gradient stops and arrowheads",
    "text insets, autofit, line spacing and paragraph spacing",
    "hyperlinks and alt text",
    "the picture adjustments: brightness, recolour, compression",
    "the points of a freeform shape, and what is inside a chart or a SmartArt",
)
IGNORED = (
    "the order and spelling of the XML, and the ids PowerPoint gives new parts",
    "how PowerPoint splits one line of text into runs",
    "the language, spelling and revision marks on text",
    "the file's properties, thumbnail, view settings and saved times",
    "the digits of a page number, which the build writes again",
    "the height PowerPoint gives a table's rows when it lays the table out",
)

KINDS = {
    f"{{{P}}}sp": "shape",
    f"{{{P}}}pic": "picture",
    f"{{{P}}}graphicFrame": "object",
    f"{{{P}}}cxnSp": "line",
    f"{{{P}}}grpSp": "group",
}
ALIGN = {"l": "left", "ctr": "centre", "r": "right", "just": "justified"}
ANCHOR = {"t": "top", "ctr": "middle", "b": "bottom"}

# The style of one character: (field, value) pairs, in the order of `_run` and `_paragraph`.
Style = tuple[tuple[str, object], ...]
Box = tuple[float, float, float, float]
# A scale and a shift for x and for y: where a group puts what is inside it.
Frame = tuple[float, float, float, float]


@dataclass(frozen=True)
class Text:
    """The words of one text body, with the style of each character.

    Paragraphs are joined by a newline and a line break inside a paragraph is a vertical tab,
    so the same words read the same however PowerPoint split them into runs.
    """

    chars: str = ""
    styles: tuple[Style | None, ...] = ()


@dataclass
class Shape:
    """One shape on a slide, as far as `compare` reads it."""

    ident: str
    name: str
    kind: str
    box: Box | None
    turn: tuple[float, bool, bool]
    parent: str | None
    # The text bodies: "" for the shape's own, "row 2, column 1" for a table cell.
    texts: dict[str, Text] = field(default_factory=dict)
    # Whatever else is compared, by the name it is reported under.
    look: dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """Name the shape as the report does."""
        return f'shape {self.ident} "{self.name}" ({self.kind})'


@dataclass
class Slide:
    """One slide: its id, its place in the deck counted from 1, and its shapes."""

    ident: str
    page: int
    shapes: list[Shape]
    hidden: bool = False
    """Whether the slide is hidden in the deck: `show="0"` on the slide."""


@dataclass
class Deck:
    """A deck file, read. `built` says the build wrote it and nothing has saved it since."""

    slides: list[Slide]
    built: bool


@dataclass
class Edit:
    """One edit: what it was made to, its kind, and the lines that describe it."""

    subject: str
    kind: str
    detail: list[str] = field(default_factory=list)


@dataclass
class Report:
    """What `compare` found: the commit compared with, and the edits under each heading."""

    commit: str
    sections: list[tuple[str, list[Edit]]]

    @property
    def count(self) -> int:
        """Count the edits."""
        return sum(len(edits) for _, edits in self.sections)


# ---- reading a deck ----


def _inches(*values: float) -> str:
    return ", ".join(f"{value / EMU:.2f}" for value in values)


def _colour(fill: ET.Element) -> str:
    """Spell the colour of a solid fill: six hex digits, or the theme colour's name."""
    for node in fill:
        local = node.tag.rsplit("}", 1)[-1]
        value = node.get("val", "")
        if local == "srgbClr":
            return value.upper()
        if local == "schemeClr":
            return f"theme colour {value}"
        if local == "sysClr":
            return (node.get("lastClr") or value).upper()
        return local
    return "none"


def _fill(node: ET.Element | None) -> str:
    """Spell the fill set on a shape or a line. A shape of the build with none set has none."""
    kinds = {"gradFill": "a gradient", "pattFill": "a pattern", "blipFill": "a picture"}
    for child in () if node is None else node:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "solidFill":
            return _colour(child)
        if local in kinds:
            return kinds[local]
    return "none"


def _outline(node: ET.Element | None) -> str:
    """Spell a shape's outline: its colour, width and dash, or none."""
    line = None if node is None else node.find(f"{{{A}}}ln")
    colour = _fill(line)
    if line is None or colour == "none":
        return "none"
    dash = line.find(f"{{{A}}}prstDash")
    kind = "solid" if dash is None else dash.get("val", "solid")
    width = int(line.get("w") or 9525) / POINT
    return f"{colour}, {width:g} pt" + ("" if kind == "solid" else f", {kind}")


def _run(props: ET.Element | None) -> Style:
    """Read the style a run of text sets on itself."""
    if props is None:
        return (
            ("font", None),
            ("size", None),
            ("bold", False),
            ("italic", False),
            ("underline", False),
            ("colour", None),
        )
    latin = props.find(f"{{{A}}}latin")
    fill = props.find(f"{{{A}}}solidFill")
    size = props.get("sz")
    return (
        ("font", None if latin is None else latin.get("typeface")),
        ("size", None if size is None else int(size) / 100),
        ("bold", props.get("b") in ("1", "true")),
        ("italic", props.get("i") in ("1", "true")),
        ("underline", props.get("u", "none") != "none"),
        ("colour", None if fill is None else _colour(fill)),
    )


def _paragraph(props: ET.Element | None) -> Style:
    """Read the alignment, bullet and level of a paragraph."""
    bullet = "none"
    for child in () if props is None else props:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "buChar":
            bullet = child.get("char", "a bullet")
        elif local == "buAutoNum":
            bullet = "numbered"
        elif local == "buBlip":
            bullet = "a picture"
    get = (lambda _name, default: default) if props is None else props.get
    return (
        ("alignment", ALIGN.get(get("algn", "l"), get("algn", "l"))),
        ("bullet", bullet),
        ("level", int(get("lvl", "0"))),
    )


def _text(body: ET.Element | None) -> Text:
    """Read one text body, character by character."""
    chars: list[str] = []
    styles: list[Style | None] = []
    for place, paragraph in enumerate(() if body is None else body.findall(f"{{{A}}}p")):
        if place:
            chars.append("\n")
            styles.append(None)
        whole = _paragraph(paragraph.find(f"{{{A}}}pPr"))
        for node in paragraph:
            if node.tag in (f"{{{A}}}r", f"{{{A}}}fld"):
                words = node.findtext(f"{{{A}}}t") or ""
                chars.extend(words)
                styles.extend([_run(node.find(f"{{{A}}}rPr")) + whole] * len(words))
            elif node.tag == f"{{{A}}}br":
                chars.append("\v")
                styles.append(None)
    # PowerPoint adds and drops empty paragraphs at the end as the cursor leaves the box.
    while chars and chars[-1] == "\n":
        chars.pop()
        styles.pop()
    return Text("".join(chars), tuple(styles))


def _table(table: ET.Element, shape: Shape) -> None:
    """Read a table into `shape`: its grid, its column widths and the words of each cell."""
    widths = [int(col.get("w", "0")) for col in table.iter(f"{{{A}}}gridCol")]
    rows = table.findall(f"{{{A}}}tr")
    shape.look["table"] = f"{len(rows)} rows by {len(widths)} columns"
    shape.look["column widths"] = _inches(*widths) + " in"
    for r, row in enumerate(rows, 1):
        for c, cell in enumerate(row.findall(f"{{{A}}}tc"), 1):
            shape.texts[f"row {r}, column {c}"] = _text(cell.find(f"{{{A}}}txBody"))


def _number(node: ET.Element | None, name: str) -> float:
    return 0.0 if node is None else float(node.get(name) or 0)


def _walk(
    tree: ET.Element,
    frame: Frame,
    parent: str | None,
    picture: Callable[[str | None], str],
) -> Iterator[Shape]:
    """Yield every shape under `tree` in drawing order, the shapes inside a group included."""
    sx, sy, tx, ty = frame
    for node in tree:
        if node.tag == f"{{{MC}}}AlternateContent":
            # What PowerPoint itself shows; the fallback is for programs that cannot.
            choice = node.find(f"{{{MC}}}Choice")
            if choice is not None:
                yield from _walk(choice, frame, parent, picture)
            continue
        kind = KINDS.get(node.tag)
        named = node.find(f"*/{{{P}}}cNvPr")
        if kind is None or named is None:
            continue
        own = node.find(f"{{{P}}}spPr")
        if kind == "group":
            own = node.find(f"{{{P}}}grpSpPr")
        placed = node.find(f"{{{P}}}xfrm") if kind == "object" else None
        if placed is None and own is not None:
            placed = own.find(f"{{{A}}}xfrm")
        box = None
        turn = (0.0, False, False)
        if placed is not None:
            off, ext = placed.find(f"{{{A}}}off"), placed.find(f"{{{A}}}ext")
            x, y = _number(off, "x"), _number(off, "y")
            w, h = _number(ext, "cx"), _number(ext, "cy")
            box = (tx + sx * x, ty + sy * y, sx * w, sy * h)
            turn = (
                int(placed.get("rot") or 0) / 60000,
                placed.get("flipH") in ("1", "true"),
                placed.get("flipV") in ("1", "true"),
            )
        shape = Shape(named.get("id", ""), named.get("name", ""), kind, box, turn, parent)
        if kind == "group":
            yield shape
            inner = frame
            if placed is not None and box is not None:
                at, size = placed.find(f"{{{A}}}chOff"), placed.find(f"{{{A}}}chExt")
                cx, cy = _number(at, "x"), _number(at, "y")
                cw, ch = _number(size, "cx"), _number(size, "cy")
                kx = box[2] / cw if cw else sx
                ky = box[3] / ch if ch else sy
                inner = (kx, ky, box[0] - kx * cx, box[1] - ky * cy)
            yield from _walk(node, inner, shape.ident, picture)
            continue
        if kind in ("shape", "line", "picture"):
            shape.look["fill"] = _fill(own)
            shape.look["outline"] = _outline(own)
            geometry = None if own is None else own.find(f"{{{A}}}prstGeom")
            shape.look["geometry"] = "custom" if geometry is None else geometry.get("prst", "")
        if kind == "shape":
            body = node.find(f"{{{P}}}txBody")
            shape.texts[""] = _text(body)
            props = None if body is None else body.find(f"{{{A}}}bodyPr")
            anchor = "t" if props is None else props.get("anchor", "t")
            shape.look["vertical anchor"] = ANCHOR.get(anchor, anchor)
        if kind == "picture":
            blip = node.find(f"{{{P}}}blipFill/{{{A}}}blip")
            shape.look["picture file"] = picture(
                None if blip is None else blip.get(f"{{{R}}}embed")
            )
            crop = node.find(f"{{{P}}}blipFill/{{{A}}}srcRect")
            sides = [int(_number(crop, side)) / 1000 for side in "ltrb"]
            shape.look["crop"] = (
                "none"
                if not any(sides)
                else ("left {:g}%, top {:g}%, right {:g}%, bottom {:g}%".format(*sides))
            )
            del shape.look["fill"]
        if kind == "object":
            table = node.find(f".//{{{A}}}tbl")
            if table is not None:
                shape.kind = "table"
                _table(table, shape)
        yield shape


def _targets(archive: ZipFile, owner: str) -> dict[str, str]:
    """Map each relationship id of the part `owner` to the part it points at."""
    rels = posixpath.join(posixpath.dirname(owner), "_rels", posixpath.basename(owner) + ".rels")
    if rels not in archive.namelist():
        return {}
    found = {}
    for relation in ET.fromstring(archive.read(rels)):
        if relation.get("TargetMode") == "External":
            continue
        target = relation.get("Target", "")
        if not target.startswith("/"):
            target = posixpath.join(posixpath.dirname(owner), target)
        found[relation.get("Id", "")] = posixpath.normpath(target).lstrip("/")
    return found


def read(payload: bytes, what: str = "the deck") -> Deck:
    """Read the bytes of a deck file.

    Raises
    ------
    Refusal
        When the bytes are not a PowerPoint file.
    """
    try:
        archive = ZipFile(io.BytesIO(payload))
    except BadZipFile:
        raise Refusal(f"{what} is not a PowerPoint file.") from None
    with archive:
        names = archive.namelist()
        if "ppt/presentation.xml" not in names:
            raise Refusal(f"{what} is not a PowerPoint file.")
        parts = _targets(archive, "ppt/presentation.xml")
        slides = []
        listed = ET.fromstring(archive.read("ppt/presentation.xml")).iter(f"{{{P}}}sldId")
        for page, entry in enumerate(listed, 1):
            part = parts.get(entry.get(f"{{{R}}}id", ""), "")
            if part not in names:
                raise Refusal(f"{what} lists a slide that is not in the file.")
            media = _targets(archive, part)

            def picture(rid: str | None, media: dict[str, str] = media) -> str:
                # A picture is its bytes: PowerPoint renames the file and keeps them.
                part = media.get(rid or "", "")
                if part not in names:
                    return "missing"
                return hashlib.sha256(archive.read(part)).hexdigest()[:12]

            root = ET.fromstring(archive.read(part))
            inside = root.find(f"{{{P}}}cSld")
            tree = None if inside is None else inside.find(f"{{{P}}}spTree")
            shapes = [] if tree is None else list(_walk(tree, (1, 1, 0, 0), None, picture))
            ident = "" if inside is None else inside.get("name", "")
            slides.append(Slide(ident, page, shapes, root.get("show") in ("0", "false")))
        core = archive.read("docProps/core.xml") if "docProps/core.xml" in names else b""
    return Deck(slides, f">{CORE_TIME}</dcterms:modified>".encode() in core)


# ---- comparing two decks ----


def _show(words: str) -> str:
    """Spell text as a slide source would: quoted, with a line end as an escape."""
    return json.dumps(words.replace("\v", "\n"), ensure_ascii=False)


def _value(name: str, value: object) -> str:
    if value is None:
        return "the default"
    if isinstance(value, bool):
        return "on" if value else "off"
    return f"{value:g} pt" if name == "size" else str(value)


def _change(was: Style, now: Style) -> str:
    """Spell how one style became another, field by field."""
    return "; ".join(
        f"{name} {_value(name, a)} -> {_value(name, b)}"
        for (name, a), (_, b) in zip(was, now, strict=True)
        if a != b
    )


def _one(text: Text) -> Style | None:
    """Give the one style all of a text is set in, or None when it holds several or no words."""
    styles = {style for style in text.styles if style is not None}
    return next(iter(styles)) if len(styles) == 1 else None


def _styles(old: Text, new: Text) -> list[str]:
    """Describe where the style differs on words that both texts hold.

    The two texts are lined up word by word, never letter by letter: a letter that new words
    happen to share with the old ones was not restyled. When the words changed and each text
    is in one style, the change is told once, for the whole text. When most of the words are
    new and the styles are mixed, there is no stretch to pin a change on, and none is told.
    """
    changed = old.chars != new.chars
    if changed and (was := _one(old)) and (now := _one(new)):
        return [] if was == now else [f"{_change(was, now)}, on the whole text"]
    # Words and the gaps between them, each with the place of its first character.
    a, b = (
        [(found[0], found.start()) for found in WORD.finditer(text.chars)] for text in (old, new)
    )
    matcher = difflib.SequenceMatcher(
        None, [word for word, _ in a], [word for word, _ in b], autojunk=False
    )
    spans: list[tuple[str, str]] = []
    kept = 0
    start, change = 0, None

    def close(stop: int) -> None:
        words = new.chars[start:stop].strip()
        if change is not None and words:
            spans.append((words, change))

    for i, j, size in matcher.get_matching_blocks():
        for k in range(size):
            word, at = b[j + k]
            kept += 0 if word.isspace() else len(word)
            for n in range(len(word)):
                was, now = old.styles[a[i + k][1] + n], new.styles[at + n]
                here = None
                if was is not None and now is not None and was != now:
                    here = _change(was, now)
                if here != change:
                    close(at + n)
                    start, change = at + n, here
        # A stretch never runs on across words that are new.
        if size:
            word, at = b[j + size - 1]
            close(at + len(word))
            change = None
    if changed and kept * 2 < sum(not char.isspace() for char in new.chars):
        return []
    # One line per change, naming every stretch of words it was made to.
    lines: dict[str, list[str]] = {}
    for words, what in spans:
        lines.setdefault(what, []).append(_show(words))
    return [f"{what}, on {', '.join(where)}" for what, where in lines.items()]


def _moved(old: Shape, new: Shape, groups: dict[str, tuple[Shape, Shape]]) -> tuple[bool, bool]:
    """Say whether a shape was moved, and whether it was resized, by hand.

    A shape inside a group that was itself moved or resized went with the group: the group is
    the edit, and the shape is reported only if it also moved inside the group.
    """
    if old.box is None or new.box is None:
        return (old.box is not None or new.box is not None), False
    was = old.box
    pair = groups.get(old.parent or "")
    if pair and new.parent == pair[1].ident and pair[0].box and pair[1].box:
        (gx, gy, gw, gh), (hx, hy, hw, hh) = pair[0].box, pair[1].box
        kx, ky = (hw / gw if gw else 1), (hh / gh if gh else 1)
        was = (hx + (was[0] - gx) * kx, hy + (was[1] - gy) * ky, was[2] * kx, was[3] * ky)
    gap = [abs(a - b) > SLACK for a, b in zip(was, new.box, strict=True)]
    # PowerPoint sets a table's height from its rows when it lays the table out.
    return gap[0] or gap[1], gap[2] or (gap[3] and new.kind != "table")


def _describe(shape: Shape) -> list[str]:
    """Describe a shape in full, for one that has no counterpart to compare with."""
    lines = []
    if shape.box is not None:
        x, y, w, h = shape.box
        lines.append(f"at {_inches(x, y)} in, {_inches(w)} by {_inches(h)} in")
    for where, text in shape.texts.items():
        if not text.chars:
            continue
        lines.append(f"text{' of ' + where if where else ''}: {_show(text.chars)}")
        first = next((style for style in text.styles if style is not None), ())
        lines.append(
            "  "
            + ", ".join(
                f"{name} {_value(name, value)}"
                for name, value in first
                if value not in (None, False)
            )
        )
    lines.extend(f"{name}: {value}" for name, value in shape.look.items())
    return lines


def _pairs(
    old: list[Shape], new: list[Shape]
) -> tuple[list[tuple[Shape, Shape]], list[Shape], list[Shape]]:
    """Match the shapes of one slide in two decks; give the pairs, the deleted, the added."""
    now = {shape.ident: shape for shape in new}
    pairs = [
        (shape, now.pop(shape.ident))
        for shape in old
        if shape.ident in now and now[shape.ident].kind == shape.kind
    ]
    paired = {a.ident for a, _ in pairs}
    deleted = [shape for shape in old if shape.ident not in paired]
    added = list(now.values())
    # A shape whose id changed, but whose name and kind are still its own on both sides.
    for shape in list(deleted):
        same = [other for other in added if (other.name, other.kind) == (shape.name, shape.kind)]
        twin = [other for other in deleted if (other.name, other.kind) == (shape.name, shape.kind)]
        if len(same) == 1 and len(twin) == 1 and shape.name:
            pairs.append((shape, same[0]))
            deleted.remove(shape)
            added.remove(same[0])
    return pairs, deleted, added


def _slide(old: Slide, new: Slide) -> list[Edit]:
    """List the edits made to one slide."""
    edits: list[Edit] = []
    pairs, deleted, added = _pairs(old.shapes, new.shapes)
    groups = {a.ident: (a, b) for a, b in pairs if a.kind == "group"}
    for was, now in pairs:
        if was.name != now.name:
            edits.append(Edit(now.label, "renamed", [f'"{was.name}" -> "{now.name}"']))
        moved, resized = _moved(was, now, groups)
        if moved and was.box and now.box:
            edits.append(
                Edit(
                    now.label,
                    "moved",
                    [f"{_inches(*was.box[:2])} in -> {_inches(*now.box[:2])} in"],
                )
            )
        elif moved:
            edits.append(Edit(now.label, "moved", ["its place is no longer the layout's"]))
        if resized and was.box and now.box:
            (_, _, w, h), (_, _, v, g) = was.box, now.box
            edits.append(
                Edit(
                    now.label,
                    "resized",
                    [f"{_inches(w)} by {_inches(h)} in -> {_inches(v)} by {_inches(g)} in"],
                )
            )
        if was.turn != now.turn:
            detail = []
            if was.turn[0] != now.turn[0]:
                detail.append(f"{was.turn[0]:g} -> {now.turn[0]:g} degrees")
            for at, name in ((1, "flipped left to right"), (2, "flipped top to bottom")):
                if was.turn[at] != now.turn[at]:
                    detail.append(
                        f"{name}: {_value('', was.turn[at])} -> {_value('', now.turn[at])}"
                    )
            edits.append(Edit(now.label, "rotated", detail))
        words: list[str] = []
        style: list[str] = []
        for where in dict.fromkeys([*was.texts, *now.texts]):
            a, b = was.texts.get(where, Text()), now.texts.get(where, Text())
            of = f"{where}: " if where else ""
            if a.chars != b.chars and now.name != PAGE:
                words += [f"{of}was {_show(a.chars)}", f"{of}now {_show(b.chars)}"]
            style += [of + line for line in _styles(a, b)]
        for name in dict.fromkeys([*was.look, *now.look]):
            a_look, b_look = was.look.get(name, "none"), now.look.get(name, "none")
            if a_look != b_look:
                style.append(f"{name} {a_look} -> {b_look}")
        if words:
            edits.append(Edit(now.label, "text changed", words))
        if style:
            edits.append(Edit(now.label, "style changed", style))
    for shape in deleted:
        inside = [
            s.ident
            for s in new.shapes
            if s.ident in {o.ident for o in old.shapes if o.parent == shape.ident}
        ]
        detail = _describe(shape)
        if shape.kind == "group" and inside:
            detail = [f"ungrouped: shapes {', '.join(inside)} are still on the slide"]
        edits.append(Edit(shape.label, "deleted", detail))
    for shape in added:
        detail = _describe(shape)
        if shape.kind == "group":
            inside = [s.ident for s in new.shapes if s.parent == shape.ident]
            detail.append(f"holds shapes {', '.join(inside)}")
        edits.append(Edit(shape.label, "added", detail))
    return edits


def diff(old: Deck, new: Deck, commit: str = "") -> Report:
    """Compare the last build `old` with the deck as it is now, `new`."""
    built = {slide.ident: slide for slide in reversed(old.slides) if slide.ident}
    sections: list[tuple[str, list[Edit]]] = []
    seen: list[str] = []
    for slide in new.slides:
        was = built.get(slide.ident)
        if was is None or slide.ident in seen:
            copy = f", a copy of slide {slide.ident}" if slide.ident in seen else ""
            edits = [Edit("the slide", f"added by hand{copy}")]
            edits += [Edit(shape.label, "added", _describe(shape)) for shape in slide.shapes]
            sections.append((f"slide with no source (page {slide.page})", edits))
            continue
        seen.append(slide.ident)
        edits = _slide(was, slide)
        if was.hidden != slide.hidden:
            edits.insert(0, Edit("the slide", "hidden" if slide.hidden else "shown again"))
        if edits:
            sections.append((f"slide {slide.ident} (page {slide.page})", edits))
    for slide in old.slides:
        if slide.ident not in seen:
            sections.append(
                (
                    f"slide {slide.ident} (page {slide.page} in the build)",
                    [Edit("the slide", "deleted")],
                )
            )
    before = [slide.ident for slide in old.slides if slide.ident in seen]
    if before != seen:
        sections.append(
            (
                "the deck",
                [
                    Edit(
                        "the slides",
                        "reordered",
                        [f"was {', '.join(before)}", f"now {', '.join(seen)}"],
                    )
                ],
            )
        )
    return Report(commit, sections)


# ---- the deck folder ----


def _git(folder: Folder, *args: str) -> subprocess.CompletedProcess[bytes]:
    git = shutil.which("git")
    if git is None:
        raise Refusal(
            "git is not installed, and the last build is read from the deck folder's git."
        )
    return subprocess.run([git, *args], cwd=folder.path, capture_output=True, check=False)


def last_build(folder: Folder, since: str | None = None) -> tuple[str, bytes]:
    """Find the deck file of the last commit that holds a build: the commit and the bytes.

    With `since`, that commit is taken as it is. Without, the newest commit whose deck file
    was written by the build, with nothing saving it since, is the one.

    Raises
    ------
    Refusal
        When the folder has no git history of the deck, or no commit holds a build.
    """
    name = folder.output.name
    if since is not None:
        found = _git(folder, "rev-parse", "--short", "--verify", f"{since}^{{commit}}")
        shown = _git(folder, "show", f"{since}:./{name}")
        if found.returncode != 0 or shown.returncode != 0:
            raise Refusal(f"the commit {since} holds no {name}.")
        return found.stdout.decode().strip(), shown.stdout
    log = _git(folder, "log", f"--max-count={DEPTH}", "--format=%h", "--", name)
    commits = log.stdout.decode().split() if log.returncode == 0 else []
    if not commits:
        raise Refusal(
            f"no commit in {folder.path} holds {name}, so there is no last build to compare "
            "with. Commit after every build."
        )
    for commit in commits:
        shown = _git(folder, "show", f"{commit}:./{name}")
        if shown.returncode == 0 and read(shown.stdout, f"{name} in commit {commit}").built:
            return commit, shown.stdout
    raise Refusal(
        f"no commit holds a build of {name}: each one holds a deck saved by hand. "
        "Name the commit of the last build with --since."
    )


def _is_build(payload: bytes) -> bool:
    """Tell whether these bytes are a deck the build wrote, with nothing saving it since."""
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            core = archive.read("docProps/core.xml")
    except (BadZipFile, KeyError):
        return False
    return f">{CORE_TIME}</dcterms:modified>".encode() in core


def hand_edits(folder: Folder) -> str | None:
    """Before a build replaces the deck file: find hand edits in it that the build would lose.

    Returns None when there is no deck file or the build wrote it. Returns the commit that
    holds the file when it was saved by hand and is committed as it is: the edits are safe in
    history, and the build may go on.

    Raises
    ------
    Refusal
        When the deck was saved by hand and its bytes are in no commit: untracked, or changed
        since the last commit.
    """
    deck = folder.output
    if not deck.is_file() or _is_build(deck.read_bytes()):
        return None
    name = deck.name
    tracked = _git(folder, "ls-files", "--error-unmatch", "--", name).returncode == 0
    if tracked and _git(folder, "diff", "--quiet", "HEAD", "--", name).returncode == 0:
        found = _git(folder, "log", "--max-count=1", "--format=%h", "--", name)
        commit = found.stdout.decode().strip()
        if found.returncode == 0 and commit:
            return commit
    raise Refusal(
        f"{name} holds hand edits: it was saved outside the build, and the file as it is now "
        "is not committed, so a build would lose them.\nNothing was written. Commit the deck, "
        "then run `lab-deck compare` and copy the edits into the slide sources."
    )


def compare(folder: Folder, since: str | None = None) -> Report:
    """Compare the deck file of `folder` as it is now with its last build. Writes nothing.

    Raises
    ------
    Refusal
        When there is no deck file, no last build, or one of the two cannot be read.
    """
    if not folder.output.is_file():
        raise Refusal(f"{folder.output} does not exist; there is no deck to compare.")
    commit, payload = last_build(folder, since)
    now = folder.output.read_bytes()
    old = read(payload, f"{folder.output.name} in commit {commit}")
    return diff(old, old if now == payload else read(now, folder.output.name), commit)


def render(report: Report, name: str) -> str:
    """Write the report as the text the command prints."""
    lines = [f"compared {name} as it is now with its last build, commit {report.commit}", ""]
    for heading, edits in report.sections:
        lines.append(heading)
        for edit in edits:
            lines.append(f"  {edit.subject}: {edit.kind}")
            lines.extend(f"      {line}" for line in edit.detail)
        lines.append("")
    slides = sum(heading.startswith("slide") for heading, _ in report.sections)
    count = report.count
    lines.append(
        "no hand edits found."
        if not count
        else f"{count} edit{'' if count == 1 else 's'} on {slides} slide{'' if slides == 1 else 's'}."
    )
    lines.append("Nothing was copied into the slide sources.")
    lines.append("")
    lines.append("compare cannot see yet, so check these by eye:")
    lines.extend(f"  - {item}" for item in UNSEEN)
    lines.append("compare ignores, as PowerPoint's own rewriting:")
    lines.extend(f"  - {item}" for item in IGNORED)
    return "\n".join(lines)
