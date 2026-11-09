"""Put one-slide decks together into one deck, without changing a slide.

`runner.js` writes each slide as a deck of its own. Three steps turn them into the deck:

- `repair` fixes what PptxGenJS gets wrong inside one slide, and names the slide.
- `merge` copies every slide, its notes and its pictures into one file. A slide's XML goes in
  byte for byte, so a shape id set before the merge is the shape id after it.
- `check` reads the merged file back and refuses a deck PowerPoint would offer to repair.

The merged file depends on the slides alone: the times inside it are fixed, so the same deck
folder builds to the same bytes.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from lab_deck.folder import Refusal

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SLIDE_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
NOTES_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"

SLIDE = "ppt/slides/slide1.xml"
NOTES = "ppt/notesSlides/notesSlide1.xml"
# The parts each slide owns. Every other part is the same in every one-slide deck.
OWN = ("ppt/slides/", "ppt/notesSlides/", "ppt/media/")
# Parts that may differ between one-slide decks: the time of writing, and the list of file
# types, which grows with the pictures a slide uses.
VARY = ("docProps/core.xml", "[Content_Types].xml")

# The time on every part and in the deck's properties: the earliest a zip file can hold.
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
CORE_TIME = "1980-01-01T00:00:00Z"
MODE = 0o644 << 16

# How PptxGenJS opens a table's frame. A chart's frame is spelled otherwise and keeps its id.
FRAME = re.compile(r'(<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id=")\d+(")')


def _owner(rels: str) -> str:
    """Name the part a `.rels` file belongs to."""
    return posixpath.join(posixpath.dirname(posixpath.dirname(rels)), posixpath.basename(rels)[:-5])


def _shape_ids(slide: bytes) -> list[str]:
    """List the id of every shape on a slide, in the order drawn."""
    return [node.get("id", "") for node in ET.fromstring(slide).iter(f"{{{P}}}cNvPr")]


def _write(path: Path, parts: dict[str, bytes]) -> None:
    """Write a zip file whose bytes depend on its parts alone."""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, payload in parts.items():
            info = ZipInfo(name, ZIP_TIME)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = MODE
            archive.writestr(info, payload)


def repair(path: Path, slide: str) -> None:
    """Fix the one-slide deck at `path` in place, and give its slide the name `slide`.

    PptxGenJS numbers a shape by its place in the drawing order, plus 2, but numbers a table's
    frame by a count of tables. On a one-slide deck the first table gets id 2, the id of the
    first shape. Here a table's frame gets the id its place gives it, as every other shape has,
    so no other id moves.

    Raises
    ------
    Refusal
        When two shapes on the slide still share an id.
    """
    with ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    text = parts[SLIDE].decode("utf-8")
    tree = ET.fromstring(text).find(f"{{{P}}}cSld/{{{P}}}spTree")
    assert tree is not None
    # The tree's first two children are its own properties; the shapes follow, so a shape's
    # index among the children is the id PptxGenJS means it to have.
    places = [
        index
        for index, child in enumerate(tree)
        if child.tag == f"{{{P}}}graphicFrame" and child.find(f".//{{{A}}}tbl") is not None
    ]
    assert len(places) == len(FRAME.findall(text)), "a table's frame was not found"
    place = iter(places)
    text = FRAME.sub(lambda found: f"{found[1]}{next(place)}{found[2]}", text)
    text, named = re.subn(r'<p:cSld name="[^"]*">', f'<p:cSld name="{slide}">', text, count=1)
    assert named == 1, "the slide has no name to set"
    parts[SLIDE] = text.encode("utf-8")
    ids = _shape_ids(parts[SLIDE])
    twice = sorted({ident for ident in ids if ids.count(ident) > 1}, key=int)
    if twice:
        raise Refusal(
            f"slide {slide} (slides/{slide}.js): two shapes share the id {', '.join(twice)}. "
            "PowerPoint would offer to repair the deck. PptxGenJS numbers a video or a sound "
            "apart from other shapes; draw the slide without it."
        )
    _write(path, parts)


def merge(sources: list[Path], output: Path) -> None:
    """Write the one-slide decks `sources`, in order, as one deck at `output`.

    Raises
    ------
    Refusal
        When a source holds a part the merge does not carry, such as a chart.
    """
    archives = [ZipFile(source) for source in sources]
    try:
        _merge(archives, [source.stem for source in sources], output)
    finally:
        for archive in archives:
            archive.close()


def _merge(archives: list[ZipFile], ids: list[str], output: Path) -> None:
    base = archives[0]
    count = len(archives)
    names = [[n for n in archive.namelist() if not n.endswith("/")] for archive in archives]
    shared = [n for n in names[0] if not n.startswith(OWN)]
    for number, (archive, own) in enumerate(zip(archives, names, strict=True), 1):
        assert [n for n in own if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)] == [SLIDE]
        # A part that only some slides hold belongs to the slide that brought it.
        alone = [n for n in own if not n.startswith(OWN) and any(n not in other for other in names)]
        if alone:
            raise Refusal(
                f"slide {ids[number - 1]} cannot be merged: it holds {', '.join(alone[:3])}, which the "
                "merge does not carry. A chart and a slide master bring such parts; show a "
                "chart as a picture."
            )
        differs = [n for n in shared if n not in VARY and archive.read(n) != base.read(n)]
        if differs:
            raise Refusal(
                f"slide {ids[number - 1]} cannot be merged: its {', '.join(differs[:3])} differs from "
                "the first slide's. Set nothing on `deck.pres` in a slide source."
            )

    out = {name: base.read(name) for name in shared}
    media: dict[tuple[str, str], str] = {}
    for number, archive in enumerate(archives, 1):
        moved = {
            SLIDE: f"ppt/slides/slide{number}.xml",
            "ppt/slides/_rels/slide1.xml.rels": f"ppt/slides/_rels/slide{number}.xml.rels",
            NOTES: f"ppt/notesSlides/notesSlide{number}.xml",
            "ppt/notesSlides/_rels/notesSlide1.xml.rels": (
                f"ppt/notesSlides/_rels/notesSlide{number}.xml.rels"
            ),
        }
        pictures: dict[str, str] = {}
        # The same picture on two slides is stored once; its bytes are not touched.
        for name in names[number - 1]:
            if name.startswith("ppt/media/"):
                payload = archive.read(name)
                key = (hashlib.sha256(payload).hexdigest(), PurePosixPath(name).suffix)
                if key not in media:
                    media[key] = f"ppt/media/image{len(media) + 1}{key[1]}"
                    out[media[key]] = payload
                pictures[name] = media[key]
        for old, new in moved.items():
            payload = archive.read(old)
            if old.endswith(".rels"):
                payload = _retarget(payload, _owner(old), _owner(new), {**moved, **pictures})
            out[new] = payload

    # The first slide keeps the relationship PptxGenJS gave it; the others take new ones.
    rels = base.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
    free = max(int(n) for n in re.findall(r'Id="rId(\d+)"', rels)) + 1
    rids = ["rId2"] + [f"rId{free + n}" for n in range(count - 1)]
    added = "".join(
        f'<Relationship Id="{rid}" Type="{R}/slide" Target="slides/slide{number}.xml"/>'
        for number, rid in enumerate(rids[1:], 2)
    )
    out["ppt/_rels/presentation.xml.rels"] = rels.replace(
        "</Relationships>", added + "</Relationships>"
    ).encode("utf-8")
    listed = "".join(
        f'<p:sldId id="{255 + number}" r:id="{rid}"/>' for number, rid in enumerate(rids, 1)
    )
    out["ppt/presentation.xml"] = re.sub(
        r"<p:sldIdLst>.*?</p:sldIdLst>",
        f"<p:sldIdLst>{listed}</p:sldIdLst>",
        base.read("ppt/presentation.xml").decode("utf-8"),
        flags=re.S,
    ).encode("utf-8")

    types = base.read("[Content_Types].xml").decode("utf-8")
    default = re.compile(r'<Default Extension="([^"]+)"[^>]*/>')
    known = set(default.findall(types))
    for archive in archives[1:]:
        for found in default.finditer(archive.read("[Content_Types].xml").decode("utf-8")):
            if found[1] not in known:
                known.add(found[1])
                types = types.replace("<Override", found[0] + "<Override", 1)
    overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{n}.xml" ContentType="{SLIDE_TYPE}"/>'
        f'<Override PartName="/ppt/notesSlides/notesSlide{n}.xml" ContentType="{NOTES_TYPE}"/>'
        for n in range(2, count + 1)
    )
    out["[Content_Types].xml"] = types.replace("</Types>", overrides + "</Types>").encode("utf-8")

    app = base.read("docProps/app.xml").decode("utf-8")
    app = app.replace("<Slides>1</Slides>", f"<Slides>{count}</Slides>")
    app = app.replace("<Notes>1</Notes>", f"<Notes>{count}</Notes>")
    app = re.sub(
        r"(<vt:lpstr>Slide Titles</vt:lpstr></vt:variant>\s*<vt:variant><vt:i4>)1",
        rf"\g<1>{count}",
        app,
    )
    titles = "".join(f"<vt:lpstr>Slide {n}</vt:lpstr>" for n in range(2, count + 1))
    app = app.replace("<vt:lpstr>Slide 1</vt:lpstr>", "<vt:lpstr>Slide 1</vt:lpstr>" + titles)
    app = re.sub(
        r'(<TitlesOfParts>\s*<vt:vector size=")(\d+)',
        lambda found: f"{found[1]}{int(found[2]) + count - 1}",
        app,
    )
    out["docProps/app.xml"] = app.encode("utf-8")
    out["docProps/core.xml"] = re.sub(
        r"(<dcterms:(?:created|modified)[^>]*>)[^<]+",
        lambda found: found[1] + CORE_TIME,
        base.read("docProps/core.xml").decode("utf-8"),
    ).encode("utf-8")

    for number, archive in enumerate(archives, 1):
        assert out[f"ppt/slides/slide{number}.xml"] == archive.read(SLIDE)
        assert out[f"ppt/notesSlides/notesSlide{number}.xml"] == archive.read(NOTES)
    _write(output, out)


def _retarget(payload: bytes, owner: str, owner_now: str, moved: dict[str, str]) -> bytes:
    """Point one `.rels` file at where its targets went, keeping every id and their order."""
    here = posixpath.dirname(owner)
    now = posixpath.dirname(owner_now)

    def target(found: re.Match[str]) -> str:
        if 'TargetMode="External"' in found[0]:
            return found[0]
        absolute = posixpath.normpath(posixpath.join(here, found[2]))
        there = posixpath.relpath(moved.get(absolute, absolute), now)
        return f'{found[1]}Target="{there}"{found[3]}'

    text = re.sub(
        r'(<Relationship\b[^>]*?)Target="([^"]+)"([^>]*>)', target, payload.decode("utf-8")
    )
    return text.encode("utf-8")


def check(path: Path, count: int) -> None:
    """Read the merged deck back, and refuse one that PowerPoint would offer to repair.

    Raises
    ------
    Refusal
        When a part is missing, listed twice or of no declared type, the slides are out of
        order, two shapes on a slide share an id, or a shape has a negative size.
    """
    with ZipFile(path) as archive:
        names = archive.namelist()
        parts = {name: archive.read(name) for name in names}
        bad = archive.testzip()
    problems: list[str] = []
    if bad is not None or len(set(names)) != len(names):
        problems.append("the file holds a damaged or repeated part")
    slides = [f"ppt/slides/slide{n}.xml" for n in range(1, count + 1)]
    notes = [f"ppt/notesSlides/notesSlide{n}.xml" for n in range(1, count + 1)]
    for kind, wanted in (("slides", slides), ("notesSlides", notes)):
        found = sorted(n for n in names if re.fullmatch(rf"ppt/{kind}/[a-zA-Z]+\d+\.xml", n))
        if found != sorted(wanted):
            problems.append(f"ppt/{kind} holds {len(found)} parts, not {count}")
    for name, payload in parts.items():
        if not name.endswith((".xml", ".rels")):
            continue
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as error:
            problems.append(f"{name} is not XML: {error}")
            continue
        if name in slides:
            ids = _shape_ids(payload)
            if len(ids) != len(set(ids)):
                problems.append(f"{name}: two shapes share an id")
            if re.search(rb'\bc[xy]="-', payload):
                problems.append(f"{name}: a shape has a negative size")
        if name.endswith(".rels"):
            owner = "" if name == "_rels/.rels" else _owner(name)
            seen: set[str] = set()
            for relation in root:
                if relation.get("Id") in seen:
                    problems.append(f"{name}: the id {relation.get('Id')} is used twice")
                seen.add(relation.get("Id", ""))
                if relation.get("TargetMode") == "External":
                    continue
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(owner), relation.get("Target", ""))
                ).lstrip("/")
                if target not in parts:
                    problems.append(f"{name} points at {target}, which is not in the file")
    if not problems:
        presentation = ET.fromstring(parts["ppt/presentation.xml"])
        targets = {
            r.get("Id"): r.get("Target")
            for r in ET.fromstring(parts["ppt/_rels/presentation.xml.rels"])
        }
        order = [targets.get(node.get(f"{{{R}}}id")) for node in presentation.iter(f"{{{P}}}sldId")]
        if order != [f"slides/slide{n}.xml" for n in range(1, count + 1)]:
            problems.append("the slides are not listed in order")
        types = ET.fromstring(parts["[Content_Types].xml"])
        defaults = {node.get("Extension") for node in types if node.tag.endswith("Default")}
        overrides = {
            (node.get("PartName") or "").lstrip("/")
            for node in types
            if node.tag.endswith("Override")
        }
        for name in names:
            if name == "[Content_Types].xml" or name.endswith("/"):
                continue
            if name not in overrides and name.rsplit(".", 1)[-1] not in defaults:
                problems.append(f"{name} has no declared type")
    if problems:
        raise Refusal("the merged deck is not sound:\n" + "\n".join(problems))
