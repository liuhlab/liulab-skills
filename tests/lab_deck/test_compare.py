"""`lab-deck compare`: one known hand edit to a built deck, and the report of that edit alone.

There is no PowerPoint here. Each test edits the XML of a built deck as a save in PowerPoint
would leave it, and stamps the file with a new saved time, which is how a saved deck is told
from a build.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.lab_deck.conftest import lab_deck
from tests.lab_deck.test_deck import DOT, PLAIN, TABLE, write

SHAPES = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  slide.addImage({ path: deck.picture("dot.png"), x: 1, y: 2.2, w: 2, h: 2 });
  slide.addShape(deck.pres.ShapeType.rect, {
    x: 4, y: 2.2, w: 3, h: 2, fill: { color: deck.accent }, objectName: "Blue box",
  });
  slide.addShape(deck.pres.ShapeType.rect, {
    x: 8, y: 2.2, w: 2, h: 2, fill: { color: "D55E00" }, objectName: "Orange box",
  });
};
"""

OPEN = ("<p:sp>", "<p:pic>", "<p:graphicFrame>")
SAVED = "2026-11-09T08:00:00Z"


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


@pytest.fixture(scope="module")
def committed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a deck of five slides once, and commit the build."""
    path = tmp_path_factory.mktemp("compare") / "talk"
    assert lab_deck("new", path).returncode == 0
    (path / "pictures" / "dot.png").write_bytes(DOT)
    write(path, {"title": PLAIN, "question": PLAIN, "data": TABLE, "shapes": SHAPES, "end": PLAIN})
    done = lab_deck("build", path)
    assert done.returncode == 0, done.stdout + done.stderr
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "Build")
    return path


@pytest.fixture
def folder(committed: Path, tmp_path: Path) -> Path:
    """Give each test its own copy of the built, committed deck folder."""
    return Path(shutil.copytree(committed, tmp_path / "talk"))


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


def report(folder: Path, *args: str) -> str:
    """Run `lab-deck compare` and give what it printed."""
    done = lab_deck("compare", folder, *args)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def found(text: str) -> list[str]:
    """List the report's headings and edits, down to the summary line."""
    body = text.split("\n\n", 1)[1].split("\nNothing was copied")[0]
    return [line.strip() for line in body.splitlines() if line.strip()]


def test_a_deck_nobody_edited_reports_no_edit(folder: Path) -> None:
    """The build compared with itself."""
    assert found(report(folder)) == ["no hand edits found."]


def test_a_deck_saved_with_no_edit_reports_no_edit(folder: Path) -> None:
    """What PowerPoint rewrites on a save is not an edit: runs, marks, order, row heights."""

    def rewrite(text: dict[str, str]) -> None:
        for name in [n for n in text if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]:
            xml = text[name]
            # One run split in two, as a spelling mark does.
            xml = xml.replace(
                "<a:t>First phrase</a:t></a:r>",
                '<a:t>First </a:t></a:r><a:r><a:rPr lang="en-GB" sz="2400" dirty="0" err="1">'
                '<a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:latin typeface="Arial"/>'
                "</a:rPr><a:t>phrase</a:t></a:r>",
            )
            # Attributes in another order, a default spelled out, a new language.
            xml = xml.replace(
                'lang="en-US" sz="3200" b="1" dirty="0"', 'b="1" i="0" sz="3200" lang="zh-CN"'
            )
            # The row heights and the frame height PowerPoint lays a table out with.
            xml = xml.replace('<a:tr h="0">', '<a:tr h="370840">')
            xml = re.sub(
                r'(<p:xfrm><a:off x="\d+" y="\d+"/><a:ext cx="\d+" cy=")\d+', r"\g<1>1112520", xml
            )
            # An empty paragraph at the end of a box, and an extension list.
            xml = xml.replace(
                "</a:p></p:txBody>", '</a:p><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody>'
            )
            xml = xml.replace(
                "</p:sld>",
                '<p:extLst><p:ext uri="{00000000-0000-0000-0000-000000000000}"/></p:extLst></p:sld>',
            )
            text[name] = xml

    save(folder, rewrite)

    assert found(report(folder)) == ["no hand edits found."]


def test_changed_words_are_reported_with_the_slide_id_and_page(folder: Path) -> None:
    """The slide is named by its id and its page; the shape by its id and name."""
    save(folder, on("question", "First phrase", swap("First phrase", "A better phrase")))

    assert found(report(folder)) == [
        "slide question (page 2)",
        'shape 3 "Text 1" (shape): text changed',
        'was "First phrase\\nSecond phrase"',
        'now "A better phrase\\nSecond phrase"',
        "1 edit on 1 slide.",
    ]


def test_a_changed_table_cell_is_named_by_row_and_column(folder: Path) -> None:
    """A table's words are compared cell by cell."""
    save(folder, on("data", "<a:tbl>", swap("<a:t>12 M</a:t>", "<a:t>15 M</a:t>")))

    assert found(report(folder)) == [
        "slide data (page 3)",
        'shape 3 "Table" (table): text changed',
        'row 2, column 2: was "12 M"',
        'row 2, column 2: now "15 M"',
        "1 edit on 1 slide.",
    ]


def test_a_moved_shape_is_reported_in_inches(folder: Path) -> None:
    """Inches, as a slide source places a shape."""
    save(
        folder,
        on(
            "shapes",
            "Blue box",
            swap('<a:off x="3657600" y="2011680"/>', '<a:off x="4572000" y="2011680"/>'),
        ),
    )

    assert found(report(folder)) == [
        "slide shapes (page 4)",
        'shape 4 "Blue box" (shape): moved',
        "4.00, 2.20 in -> 5.00, 2.20 in",
        "1 edit on 1 slide.",
    ]


def test_a_resized_shape_is_reported(folder: Path) -> None:
    """A drag of the bottom right handle changes the size and not the place."""
    save(
        folder,
        on(
            "shapes",
            "Blue box",
            swap('<a:ext cx="2743200" cy="1828800"/>', '<a:ext cx="3657600" cy="914400"/>'),
        ),
    )

    assert found(report(folder)) == [
        "slide shapes (page 4)",
        'shape 4 "Blue box" (shape): resized',
        "3.00 by 2.00 in -> 4.00 by 1.00 in",
        "1 edit on 1 slide.",
    ]


def test_a_recoloured_and_bolded_phrase_is_reported_with_its_words(folder: Path) -> None:
    """A change of text style names the words it was made to."""

    def restyle(xml: str) -> str:
        head, tail = xml.split("<a:t>Second phrase", 1)
        at = head.rindex("<a:rPr")
        run = (
            head[at:].replace('val="0072B2"', 'val="D55E00"').replace("<a:rPr ", '<a:rPr b="1" ', 1)
        )
        return head[:at] + run + "<a:t>Second phrase" + tail

    save(folder, on("question", "First phrase", restyle))

    assert found(report(folder)) == [
        "slide question (page 2)",
        'shape 3 "Text 1" (shape): style changed',
        'bold off -> on; colour 0072B2 -> D55E00, on "Second phrase"',
        "1 edit on 1 slide.",
    ]


def test_a_changed_fill_is_reported(folder: Path) -> None:
    """The fill of a shape is style too."""
    save(
        folder,
        on("shapes", "Blue box", swap('<a:srgbClr val="0072B2"/>', '<a:srgbClr val="009E73"/>')),
    )

    assert found(report(folder)) == [
        "slide shapes (page 4)",
        'shape 4 "Blue box" (shape): style changed',
        "fill 0072B2 -> 009E73",
        "1 edit on 1 slide.",
    ]


def test_an_added_shape_is_described_in_full(folder: Path) -> None:
    """A shape with no counterpart in the build: its place, words and look, to write it from."""
    box = (
        '<p:sp><p:nvSpPr><p:cNvPr id="9" name="TextBox 8"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="914400" y="4572000"/><a:ext cx="1828800" cy="457200"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="2000"/>'
        "<a:t>A note</a:t></a:r></a:p></p:txBody></p:sp>"
    )

    def add(text: dict[str, str]) -> None:
        name = part(text, "shapes")
        text[name] = text[name].replace("</p:spTree>", box + "</p:spTree>")

    save(folder, add)

    assert found(report(folder)) == [
        "slide shapes (page 4)",
        'shape 9 "TextBox 8" (shape): added',
        "at 1.00, 5.00 in, 2.00 by 0.50 in",
        'text: "A note"',
        "size 20 pt, alignment left, bullet none",
        "fill: none",
        "outline: none",
        "geometry: rect",
        "vertical anchor: top",
        "1 edit on 1 slide.",
    ]


def test_a_deleted_shape_is_reported(folder: Path) -> None:
    """A shape of the build that is gone."""
    save(folder, on("shapes", "Orange box", lambda xml: ""))

    lines = found(report(folder))

    assert lines[:2] == ["slide shapes (page 4)", 'shape 5 "Orange box" (shape): deleted']
    assert lines[-1] == "1 edit on 1 slide."
    assert sum(": " in line and line.startswith("shape ") for line in lines) == 1


def test_reordered_slides_are_reported_and_no_shape_with_them(folder: Path) -> None:
    """A slide is matched by its id, so a slide that moved has no other edit."""

    def reorder(text: dict[str, str]) -> None:
        xml = text["ppt/presentation.xml"]
        entries = re.findall(r"<p:sldId [^>]*/>", xml)
        moved = [entries[0], entries[2], entries[1], *entries[3:]]
        text["ppt/presentation.xml"] = xml.replace("".join(entries), "".join(moved))

    save(folder, reorder)

    assert found(report(folder)) == [
        "the deck",
        "the slides: reordered",
        "was title, question, data, shapes, end",
        "now title, data, question, shapes, end",
        "1 edit on 0 slides.",
    ]


def test_a_deleted_slide_is_reported_by_its_id(folder: Path) -> None:
    """The slides after it keep their ids, so none of them is reported."""

    def drop(text: dict[str, str]) -> None:
        xml = text["ppt/presentation.xml"]
        entries = re.findall(r"<p:sldId [^>]*/>", xml)
        text["ppt/presentation.xml"] = xml.replace(entries[1], "")

    save(folder, drop)

    assert found(report(folder)) == [
        "slide question (page 2 in the build)",
        "the slide: deleted",
        "1 edit on 1 slide.",
    ]


def test_grouping_shapes_reports_the_group_and_moves_none_of_them(folder: Path) -> None:
    """A shape inside a group is read at its place on the slide, whatever the group's scale."""

    def group(text: dict[str, str]) -> None:
        name = part(text, "shapes")
        xml = text[name]
        start = xml.index("<p:sp>", xml.index("</p:pic>"))
        end = xml.rindex("</p:sp>") + len("</p:sp>")
        # The group's own space is half the slide's, so each shape inside is spelled at half.
        inside = re.sub(
            r'(x|y|cx|cy)="(\d+)"', lambda m: f'{m[1]}="{int(m[2]) // 2}"', xml[start:end]
        )
        text[name] = (
            xml[:start]
            + '<p:grpSp><p:nvGrpSpPr><p:cNvPr id="9" name="Group 8"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="3657600" y="2011680"/><a:ext cx="5486400" cy="1828800"/>'
            '<a:chOff x="1828800" y="1005840"/><a:chExt cx="2743200" cy="914400"/></a:xfrm></p:grpSpPr>'
            + inside
            + "</p:grpSp>"
            + xml[end:]
        )

    save(folder, group)

    assert found(report(folder)) == [
        "slide shapes (page 4)",
        'shape 9 "Group 8" (group): added',
        "at 4.00, 2.20 in, 6.00 by 2.00 in",
        "holds shapes 4, 5, 6",
        "1 edit on 1 slide.",
    ]


def test_the_build_is_found_behind_a_commit_of_the_hand_edited_deck(folder: Path) -> None:
    """The agent commits the member's deck before it touches it; the build is one commit back."""
    save(folder, on("question", "First phrase", swap("First phrase", "A better phrase")))
    git(folder, "commit", "-q", "-am", "The deck as edited by hand")
    build = git(folder, "rev-parse", "--short", "HEAD~1").strip()

    text = report(folder)

    assert f"commit {build}" in text.splitlines()[0]
    assert "1 edit on 1 slide." in text


def test_compare_changes_no_file(folder: Path) -> None:
    """It reports only: the slide sources, the deck and git are as they were."""
    save(folder, on("question", "First phrase", swap("First phrase", "A better phrase")))
    before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file() and ".git" not in p.parts}
    status = git(folder, "status", "--porcelain")

    report(folder)

    after = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert after == before
    assert git(folder, "status", "--porcelain") == status


def test_the_report_says_what_it_cannot_see(folder: Path) -> None:
    """An edit `compare` is blind to must not pass for no edit."""
    text = report(folder)

    assert "compare cannot see yet" in text
    assert "animations and slide transitions" in text
    assert "compare ignores, as PowerPoint's own rewriting" in text


def test_a_deck_with_no_committed_build_is_refused(folder: Path) -> None:
    """Without a build in history there is nothing to compare with."""
    shutil.rmtree(folder / ".git")
    git(folder, "init", "-q")

    done = lab_deck("compare", folder)

    assert done.returncode == 1
    assert "Commit after every build" in done.stderr
