"""Write a slide's groups and clicks into its one-slide deck, and read clicks back.

PptxGenJS writes no group shape and no animation. A slide source names its groups, its
sections and its clicks through `deck`, and `runner.js` hands them over as a plan: each group
and section is a run of the things the source drew, by place in the drawing order. A click
names sections, never shape ids, so a drawing call that moves takes its place in its section
with it.

`stage` runs on a one-slide deck after `merge.repair` and before `merge.merge`:

- A group's shapes are wrapped in one group shape, where they stand. No shape's XML, id or
  place changes. The group takes the id after the slide's highest.
- A click is one step of the slide's main sequence. Its effects are PowerPoint's Appear and
  Disappear, one per object of each section it names, all starting on the click.

`click_states` reads the clicks of any slide back, so a check can count and render them.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.parsers import expat
from xml.sax.saxutils import quoteattr
from zipfile import ZipFile

from lab_deck import house
from lab_deck.folder import Refusal
from lab_deck.merge import SLIDE, A, P, write

NS = {"p": P, "a": A}
# The shapes no click may show or hide: the slide's conclusion stays up.
FIXED = (house.TITLE,)


@dataclass(frozen=True)
class Change:
    """One object that one click shows or hides."""

    shape: str
    """The object's shape id on its slide."""
    name: str
    """The object's name, as PowerPoint's selection pane lists it."""
    effect: str
    """`appear`, `disappear`, or `other` for any effect the build does not write."""


@dataclass(frozen=True)
class _Object:
    """One object at the top of a slide's shape tree: a shape, a picture, a table, a group."""

    ident: str
    name: str
    kind: str
    first: int
    last: int
    """The things drawn that it holds, as a half-open run of places in the drawing order."""


def _spans(data: bytes) -> list[tuple[str, str, str, int, int]]:
    """List the shape tree's objects in drawing order: (id, name, kind, start byte, end byte)."""
    parser = expat.ParserCreate()
    depth = 0
    tree: int | None = None
    spans: list[tuple[str, str, str, int, int]] = []
    current: list[Any] | None = None

    def start(tag: str, attrs: dict[str, str]) -> None:
        nonlocal depth, tree, current
        depth += 1
        if tag == "p:spTree":
            tree = depth
        elif tree is not None and depth == tree + 1:
            current = [None, "", parser.CurrentByteIndex]
        elif current is not None and current[0] is None and tag == "p:cNvPr":
            current[:2] = attrs["id"], attrs.get("name", "")

    def end(tag: str) -> None:
        nonlocal depth, tree, current
        if tree is not None and depth == tree + 1 and current is not None:
            index = parser.CurrentByteIndex
            assert data[index : index + 2] == b"</", f"an empty {tag} in the shape tree"
            # The tree's own properties are children too; only what was drawn counts.
            if tag not in ("p:nvGrpSpPr", "p:grpSpPr"):
                kind = tag.split(":")[1]
                spans.append((current[0], current[1], kind, current[2], index + len(tag) + 3))
            current = None
        elif tag == "p:spTree":
            tree = None
        depth -= 1

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(data, True)
    return spans


def _boxes(data: bytes) -> list[tuple[int, int, int, int]]:
    """Each drawn object's box in EMU, in drawing order: (left, top, right, bottom)."""
    tree = ET.fromstring(data).find("p:cSld/p:spTree", NS)
    assert tree is not None
    boxes = []
    for child in list(tree)[2:]:
        # A table's frame carries its box in the other namespace.
        xfrm = child.find("p:spPr/a:xfrm", NS)
        if xfrm is None:
            xfrm = child.find("p:xfrm", NS)
        assert xfrm is not None, "a drawn object has no box"
        off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
        assert off is not None, "a drawn object's box has no place"
        assert ext is not None, "a drawn object's box has no size"
        x, y = int(off.get("x", 0)), int(off.get("y", 0))
        boxes.append((x, y, x + int(ext.get("cx", 0)), y + int(ext.get("cy", 0))))
    return boxes


def _group(data: bytes, groups: list[dict[str, Any]]) -> tuple[bytes, list[_Object]]:
    """Wrap each group's shapes in a group shape, and list the slide's top-level objects."""
    spans = _spans(data)
    boxes = _boxes(data)
    ident = max(int(node.get("id", 0)) for node in ET.fromstring(data).iter(f"{{{P}}}cNvPr"))
    top: list[_Object] = []
    inserts: list[tuple[int, bytes]] = []
    place = 0
    for group in sorted(groups, key=lambda one: one["first"]):
        first, last = group["first"], group["last"]
        top += [_Object(*spans[n][:3], n, n + 1) for n in range(place, first)]
        place = last
        ident += 1
        top.append(_Object(str(ident), group["name"], "grpSp", first, last))
        inside = boxes[first:last]
        x, y = min(box[0] for box in inside), min(box[1] for box in inside)
        w, h = max(box[2] for box in inside) - x, max(box[3] for box in inside) - y
        # The children's frame is the group's own, so every shape stays where it was drawn.
        opening = (
            f'<p:grpSp><p:nvGrpSpPr><p:cNvPr id="{ident}" name={quoteattr(group["name"])}/>'
            "<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>"
            f'<a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/>'
            f'<a:chOff x="{x}" y="{y}"/><a:chExt cx="{w}" cy="{h}"/>'
            "</a:xfrm></p:grpSpPr>"
        )
        inserts.append((spans[first][3], opening.encode("utf-8")))
        inserts.append((spans[last - 1][4], b"</p:grpSp>"))
    top += [_Object(*spans[n][:3], n, n + 1) for n in range(place, len(spans))]
    # From the end backwards, so no insert moves the place of one still to come.
    for position, text in sorted(inserts, key=lambda one: one[0], reverse=True):
        data = data[:position] + text + data[position:]
    return data, top


def _timing(clicks: list[list[tuple[_Object, bool]]]) -> str:
    """Spell the clicks as the timing PowerPoint itself writes for Appear and Disappear."""
    counter = 2

    def tid() -> int:
        nonlocal counter
        counter += 1
        return counter

    steps = []
    builds: list[str] = []
    for click in clicks:
        outer, inner = tid(), tid()
        effects = []
        for place, (target, shown) in enumerate(click):
            effect, behaviour = tid(), tid()
            # PowerPoint lists a build only for a shape that can hold text, not for a picture
            # or a group.
            if shown and target.kind == "sp":
                builds.append(target.ident)
            effects.append(
                f'<p:par><p:cTn id="{effect}" presetID="1" '
                f'presetClass="{"entr" if shown else "exit"}" presetSubtype="0" fill="hold" '
                f'grpId="0" nodeType="{"clickEffect" if place == 0 else "withEffect"}">'
                '<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{behaviour}" dur="1" fill="hold">'
                '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{target.ident}"/></p:tgtEl><p:attrNameLst>'
                "<p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>"
                f'<p:to><p:strVal val="{"visible" if shown else "hidden"}"/></p:to></p:set>'
                "</p:childTnLst></p:cTn></p:par>"
            )
        steps.append(
            f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst>'
            '<p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/>'
            "</p:stCondLst><p:childTnLst>" + "".join(effects) + "</p:childTnLst></p:cTn></p:par>"
            "</p:childTnLst></p:cTn></p:par>"
        )
    listed = "".join(f'<p:bldP spid="{spid}" grpId="0"/>' for spid in sorted(builds, key=int))
    return (
        '<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" '
        'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        + "".join(steps)
        + "</p:childTnLst></p:cTn>"
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
        '</p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/>'
        "</p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>"
        + (f"<p:bldLst>{listed}</p:bldLst>" if listed else "")
        + "</p:timing>"
    )


def stage(path: Path, slide: str, plan: dict[str, Any]) -> None:
    """Write the groups and clicks of `plan` into the one-slide deck at `path`, in place.

    Raises
    ------
    Refusal
        When the file does not hold what the source drew, or a click would hide the title.
    """
    if not plan["groups"] and not plan["clicks"]:
        return
    with ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    data = parts[SLIDE]
    where = f"slide {slide} (slides/{slide}.js)"
    spans = _spans(data)
    if len(spans) != plan["objects"]:
        raise Refusal(
            f"{where}: the source drew {plan['objects']} things, but the slide holds "
            f"{len(spans)}, so its groups and clicks cannot be placed. Draw with `slide.add...` "
            "and the `deck` helpers only."
        )
    data, top = _group(data, plan["groups"])

    runs = {one["name"]: (one["first"], one["last"]) for one in plan["sections"]}
    runs.update({one.name: (one.first, one.last) for one in top if one.kind == "grpSp"})
    clicks: list[list[tuple[_Object, bool]]] = []
    for click in plan["clicks"]:
        effects: list[tuple[_Object, bool]] = []
        for shown, names in ((True, click["appear"]), (False, click["disappear"])):
            for name in names:
                first, last = runs[name]
                fixed = [span[1] for span in spans[first:last] if span[1] in FIXED]
                if fixed:
                    raise Refusal(
                        f'{where}: a click shows or hides "{name}", which holds the '
                        f"{fixed[0].lower()}. The title stays up; draw it outside the section."
                    )
                effects += [(one, shown) for one in top if first <= one.first and one.last <= last]
        clicks.append(effects)
    if clicks:
        assert b"<p:timing" not in data, "the slide already has a timing"
        assert data.count(b"</p:sld>") == 1, "the slide does not end once"
        data = data.replace(b"</p:sld>", _timing(clicks).encode("utf-8") + b"</p:sld>")

    # Read back what was written, by the reader every later check uses.
    wanted = [
        [Change(one.ident, one.name, "appear" if shown else "disappear") for one, shown in click]
        for click in clicks
    ]
    assert click_states(data) == wanted, f"{where}: the clicks written are not the clicks read"
    parts[SLIDE] = data
    write(path, parts)


def click_states(slide: bytes) -> list[list[Change]]:
    """Read the clicks of one slide's XML: for each click, in order, what it shows and hides.

    A slide with n clicks has n + 1 click states: the slide as it opens, and one more after
    each click. An object whose first effect is `appear` is hidden when the slide opens.
    """
    root = ET.fromstring(slide)
    names = {node.get("id"): node.get("name", "") for node in root.iter(f"{{{P}}}cNvPr")}
    main = next(
        (node for node in root.iter(f"{{{P}}}cTn") if node.get("nodeType") == "mainSeq"), None
    )
    steps = None if main is None else main.find("p:childTnLst", NS)
    if steps is None:
        return []
    clicks = []
    for step in steps:
        changes = []
        for effect in step.iter(f"{{{P}}}cTn"):
            if effect.get("presetID") is None:
                continue
            target = effect.find(".//p:spTgt", NS)
            shape = "" if target is None else target.get("spid", "")
            kind = {"entr": "appear", "exit": "disappear"}.get(effect.get("presetClass", ""))
            value = effect.find("p:childTnLst/p:set/p:to/p:strVal", NS)
            plain = (
                effect.get("presetID") == "1"
                and kind is not None
                and len(effect.findall("p:childTnLst/*", NS)) == 1
                and value is not None
                and value.get("val") == ("visible" if kind == "appear" else "hidden")
                and effect.findtext(".//p:attrName", None, NS) == "style.visibility"
            )
            changes.append(Change(shape, names.get(shape, ""), kind if plain and kind else "other"))
        clicks.append(changes)
    return clicks


def read(deck: Path) -> dict[str, list[list[Change]]]:
    """Read the clicks of every slide of a built deck, by slide id, in the order shown."""
    found = {}
    with ZipFile(deck) as archive:
        count = sum(1 for name in archive.namelist() if name.startswith("ppt/slides/slide"))
        for number in range(1, count + 1):
            data = archive.read(f"ppt/slides/slide{number}.xml")
            sld = ET.fromstring(data).find("p:cSld", NS)
            assert sld is not None
            found[sld.get("name", str(number))] = click_states(data)
    return found
