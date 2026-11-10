"""`lab-deck build` on slides with clicks, grouped drawings and notes, read from the deck."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lab_deck import stage
from tests.lab_deck.conftest import PLAIN, Deck, lab_deck, write
from tests.lab_deck.test_deck import built

# A slide in three sections. The first is up when the slide opens; a click brings the second,
# and the next click brings the third and takes the first away.
STAGED = """\
module.exports = (slide, deck) => {
  const box = (name, y) => slide.addText(name, {
    x: 1, y, w: 4, h: 0.5, fontFace: deck.font, fontSize: deck.size.body, objectName: name,
  });
  deck.title(slide, "TITLE");
  deck.section(slide, "question", () => {
    box("Question", 2);
  });
  // MOVE
  deck.section(slide, "method", () => {
    box("Method", 3);
    box("Method detail", 3.6);
  });
  deck.section(slide, "result", () => {
    box("Result", 5);
  });
  deck.click(slide, { appear: "method" });
  deck.click(slide, { appear: "result", disappear: "question" });
};
"""

# A drawing of four shapes, between two text boxes.
DRAWING = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  DRAW
  deck.lines(slide, ["Below the drawing"], { y: 5.5, h: 1 });
};
"""
BARS = """\
for (let n = 0; n < 3; n++) {
    slide.addShape(deck.pres.ShapeType.rect, {
      x: 2 + n, y: 4 - n * 0.5, w: 0.8, h: 0.5 + n * 0.5,
      fill: { color: deck.accent }, objectName: `bar ${n + 1}`,
    });
  }
  slide.addShape(deck.pres.ShapeType.line, {
    x: 2, y: 4.5, w: 3, h: 0, line: { color: deck.text, width: 0.75 }, objectName: "baseline",
  });"""
GROUPED = DRAWING.replace("DRAW", f'deck.group(slide, "Track", () => {{\n  {BARS}\n  }});')
LOOSE = DRAWING.replace("DRAW", BARS)

# A grouped drawing inside a section: one click brings the whole drawing and its label.
BOTH = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.section(slide, "signal", () => {
    deck.group(slide, "Track", () => {
      slide.addShape(deck.pres.ShapeType.rect, { x: 2, y: 3, w: 1, h: 1, objectName: "bar" });
      slide.addShape(deck.pres.ShapeType.rect, { x: 3, y: 2, w: 1, h: 2, objectName: "peak" });
    });
    slide.addText("Signal", {
      x: 2, y: 5, w: 3, h: 0.5, fontFace: deck.font, fontSize: deck.size.body, objectName: "Label",
    });
  });
  deck.click(slide, { appear: "signal" });
};
"""


def refused(folder: Path, source: str) -> str:
    """Build a deck whose second slide is `source`, and return what the refusal said."""
    write(folder, {"title": PLAIN, "bad": source})
    done = lab_deck("build", folder)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "slides/bad.js" in done.stderr
    assert not (folder / "talk.pptx").exists()
    return done.stderr


def test_a_click_shows_or_hides_every_shape_of_the_sections_it_names(folder: Path) -> None:
    """One click is one step: the whole section comes, and another may go, at once."""
    write(folder, {"title": PLAIN, "staged": STAGED})

    deck = built(folder)

    assert deck.clicks(1) == []
    assert deck.clicks(2) == [
        [("Method", "entr"), ("Method detail", "entr")],
        [("Result", "entr"), ("Question", "exit")],
    ]


def test_the_only_effects_written_are_appear_and_disappear(folder: Path) -> None:
    """PowerPoint's Appear and Disappear are preset 1: one switch of visibility, no motion."""
    write(folder, {"title": PLAIN, "staged": STAGED})

    slide = built(folder).slides[1]

    assert set(re.findall(r'presetID="(\d+)"', slide)) == {"1"}
    assert set(re.findall(r'presetClass="(\w+)"', slide)) == {"entr", "exit"}
    assert set(re.findall(r"<p:attrName>([^<]*)</p:attrName>", slide)) == {"style.visibility"}
    for other in ("<p:anim ", "<p:animEffect", "<p:animMotion", "<p:animScale", "<p:transition"):
        assert other not in slide
    # One effect starts on the click, and the rest of that click's effects start with it.
    assert re.findall(r'nodeType="(clickEffect|withEffect)"', slide) == [
        "clickEffect",
        "withEffect",
        "clickEffect",
        "withEffect",
    ]
    ids = re.findall(r'<p:cTn id="(\d+)"', slide)
    assert len(ids) == len(set(ids))


def test_a_drawing_call_that_moves_keeps_every_click_right(folder: Path) -> None:
    """A click names a section, not a shape id, so a new shape before it breaks nothing."""
    write(folder, {"title": PLAIN, "staged": STAGED})
    before = built(folder)
    moved = STAGED.replace("// MOVE", 'box("Aside", 6);')

    write(folder, {"title": PLAIN, "staged": moved})
    after = built(folder)

    # Every shape drawn after the new one has a new id, and the clicks still follow them.
    assert dict(after.shapes(2))["4"] == "Aside"
    assert dict(before.shapes(2))["4"] == "Method"
    assert after.clicks(2) == before.clicks(2)
    for click in stage.read(folder / "talk.pptx")["staged"]:
        for change in click:
            assert (change.shape, change.name) in after.shapes(2)


def test_a_shape_drawn_inside_a_section_comes_and_goes_with_it(folder: Path) -> None:
    """Moving a drawing call into a section is the whole edit: no list of ids to update."""
    inside = STAGED.replace('box("Result", 5);', 'box("Result", 5);\n    box("Caveat", 6);')
    write(folder, {"title": PLAIN, "staged": inside})

    deck = built(folder)

    assert deck.clicks(2)[1] == [("Result", "entr"), ("Caveat", "entr"), ("Question", "exit")]


def test_a_drawing_of_many_shapes_is_one_group(folder: Path) -> None:
    """The shapes move and reveal as one, and stay where the source drew them."""
    write(folder, {"title": PLAIN, "grouped": GROUPED})
    grouped = built(folder)
    write(folder, {"title": PLAIN, "grouped": LOOSE})
    loose = built(folder)

    assert grouped.top(2) == [
        ("2", "Slide title", []),
        ("9", "Track", ["bar 1", "bar 2", "bar 3", "baseline"]),
        ("7", "Text 5", []),
        ("8", "Page number", []),
    ]
    # Every shape keeps its id, its place in the drawing order and its XML: without the
    # group's own tags the slide is the one the loose shapes build to.
    slide = grouped.slides[1]
    assert len(set(grouped.shapes(2))) == len(grouped.shapes(2))
    unwrapped = re.sub(r"<p:grpSp>.*?</p:grpSpPr>|</p:grpSp>", "", slide, flags=re.S)
    assert unwrapped == loose.slides[1]
    # The group's box is the box around its shapes, and its children's frame is the same box.
    box = re.search(
        r'<p:grpSpPr><a:xfrm><a:off x="(\d+)" y="(\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>'
        r'<a:chOff x="(\d+)" y="(\d+)"/><a:chExt cx="(\d+)" cy="(\d+)"/>',
        slide[slide.index('name="Track"') :],
    )
    assert box is not None
    inch = 914400
    assert [int(n) for n in box.groups()] == [2 * inch, 3 * inch, 3 * inch, int(1.5 * inch)] * 2


def test_a_group_inside_a_section_is_one_object_of_the_click(folder: Path) -> None:
    """The click targets the group, never one of its shapes."""
    write(folder, {"title": PLAIN, "both": BOTH})

    deck = built(folder)

    assert deck.top(2)[1][1:] == ("Track", ["bar", "peak"])
    assert deck.clicks(2) == [[("Track", "entr"), ("Label", "entr")]]


def test_a_click_can_name_a_group_drawn_outside_any_section(folder: Path) -> None:
    """A group at the top of the slide is a section of one object."""
    source = GROUPED.replace("\n};", '\n  deck.click(slide, { disappear: ["Track"] });\n};')
    write(folder, {"title": PLAIN, "grouped": source})

    deck = built(folder)

    assert deck.clicks(2) == [[("Track", "exit")]]


def test_notes_come_from_the_deck_folder_one_file_per_slide(folder: Path) -> None:
    """`notes/<id>.md` is the slide's notes, with a `[Click]` cue where each click falls."""
    write(folder, {"title": PLAIN, "staged": STAGED, "plain": PLAIN})
    text = "Ask the question.\n\n[Click] Say how.\n\n[Click] Give the result & stop.\n"
    (folder / "notes" / "staged.md").write_text(text, encoding="utf-8")

    deck = built(folder)

    notes = deck.notes(2)
    assert notes.replace("\r\n", "\n") == text.strip()
    assert notes.count("[Click]") == len(deck.clicks(2)) == 2
    assert deck.notes(1) == deck.notes(3) == ""
    # The notes take no shape's place: the slide is the one built with no notes.
    (folder / "notes" / "staged.md").unlink()
    assert built(folder).slides[1] == deck.slides[1]


def test_the_built_deck_tells_each_slides_clicks(folder: Path) -> None:
    """A check reads the clicks from the deck alone: n clicks are n + 1 click states."""
    write(folder, {"title": PLAIN, "staged": STAGED, "both": BOTH})
    built(folder)

    clicks = stage.read(folder / "talk.pptx")

    assert list(clicks) == ["title", "staged", "both"]
    assert [len(found) for found in clicks.values()] == [0, 2, 1]
    assert [[(c.name, c.effect) for c in click] for click in clicks["staged"]] == [
        [("Method", "appear"), ("Method detail", "appear")],
        [("Result", "appear"), ("Question", "disappear")],
    ]


def test_an_effect_powerpoint_added_by_hand_reads_as_other(folder: Path) -> None:
    """A deck edited in PowerPoint may hold a fade; the reader names it and does not guess."""
    write(folder, {"title": PLAIN, "staged": STAGED})
    slide = built(folder).slides[1].replace('presetID="1"', 'presetID="10"', 1)

    clicks = stage.click_states(slide.encode("utf-8"))

    assert [c.effect for c in clicks[0]] == ["other", "appear"]


def test_building_twice_with_clicks_groups_and_notes_writes_the_same_bytes(folder: Path) -> None:
    """Groups, clicks and notes add nothing that changes from one build to the next."""
    write(folder, {"title": PLAIN, "staged": STAGED, "both": BOTH, "grouped": GROUPED})
    (folder / "notes" / "both.md").write_text("[Click] The signal.\n", encoding="utf-8")
    built(folder)
    first = (folder / "talk.pptx").read_bytes()

    built(folder)

    assert (folder / "talk.pptx").read_bytes() == first


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (('appear: "method"', 'appear: "methods"'), "no section or group of that name"),
        (('disappear: "question"', 'disappear: "method"'), "one effect per section"),
        (('"result", () =>', '"method", () =>'), 'the name "method" is used twice'),
        (('box("Result", 5);', ""), 'section "result" draws nothing'),
        (('box("Result", 5);', 'deck.section(slide, "more", () => box("More", 6));'), "inside"),
        (('appear: "method" }', 'appear: "method", fade: "result" }'), "fade is not an effect"),
        (("// MOVE", 'slide.addNotes("Say this.");'), "notes/bad.md"),
        (('deck.title(slide, "TITLE");\n', ""), "TITLE"),
    ],
)
def test_a_click_the_build_cannot_place_stops_it_with_the_reason(
    folder: Path, change: tuple[str, str], said: str
) -> None:
    """A click that names nothing, or names a thing twice, never builds to a wrong deck."""
    source = STAGED.replace(*change)
    if said == "TITLE":
        # The title drawn inside a section that a click hides.
        source = source.replace('box("Question", 2);', 'deck.title(slide, "Title");')
        said = "The title stays up"
    assert source != STAGED

    assert said in refused(folder, source)


def test_a_click_that_names_a_group_inside_a_section_is_refused(folder: Path) -> None:
    """Only a whole section comes or goes, so half a section cannot be left behind."""
    source = BOTH.replace('appear: "signal"', 'appear: "Track"')

    assert 'a group inside section "signal"' in refused(folder, source)


def test_a_failed_click_leaves_the_last_built_deck_as_it_was(folder: Path) -> None:
    """The refusal comes before anything is moved over the deck."""
    write(folder, {"title": PLAIN, "staged": STAGED})
    built(folder)
    before = (folder / "talk.pptx").read_bytes()
    write(folder, {"title": PLAIN, "staged": STAGED.replace('appear: "result"', 'appear: "x"')})

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert 'click 2 names "x"' in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    assert isinstance(Deck(folder / "talk.pptx").clicks(2), list)
