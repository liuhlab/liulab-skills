"""`lab-deck lint`, and the lint inside `lab-deck build`: one deck per check, and one that passes.

Each failing deck is the passing deck plus one slide, `bad`, that breaks one check. The test
reads the report a member would: the slide by id and page, the shape, the check and its rule.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import pytest

from lab_deck import lint
from lab_deck.merge import write as write_deck
from tests.lab_deck.conftest import PLAIN, lab_deck, write
from tests.lab_deck.test_deck import DOT

# A slide that uses everything the lint reads and breaks none of it: a table, a picture
# beside the text, Chinese text, the one citation line, and two clicks with their cues.
FULL = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.section(slide, "question", () => {
    deck.lines(slide, ["Trimmed reads: higher rate", "甲基化区分细胞类型"], { w: 6, h: 1.5 });
  });
  deck.section(slide, "data", () => {
    deck.table(slide, [["Sample", "Reads"], ["A", "12 M"]], { y: 3.6, w: 6 });
  });
  deck.section(slide, "figure", () => {
    slide.addImage({ path: deck.picture("dot.png"), x: 8, y: 2, w: 4, h: 4 });
  });
  deck.citation(slide, "Author, Journal, 2020");
  deck.click(slide, { appear: "data" });
  deck.click(slide, { appear: "figure", disappear: "question" });
};
"""
CUES = "Ask the question.\n\n[Click] Show the table.\n\n[Click] Show the picture.\n"

SMALL = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.lines(slide, ["Readable", "Too small"], { fontSize: SIZE });
};
"""
CHINESE = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.lines(slide, [TEXT], { w: 4, h: 0.6, fontSize: SIZE });
};
"""
OVERFLOW = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.lines(slide, [
    "The first of four long phrases that each fill most of a line of this narrow box",
    "The second of four long phrases", "The third", "The fourth",
  ], { w: 5, h: 1.2 });
};
"""
COVERED = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  FIRST
  SECOND
};
"""
WORDS = 'deck.lines(slide, ["Words under the picture"], { h: 1 });'
IMAGE = 'slide.addImage({ path: deck.picture("dot.png"), x: 0.5, y: 1.8, w: 3, h: 1 });'
CITED = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  CITE
};
"""
CLICKED = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.section(slide, "result", () => {
    deck.lines(slide, ["The result"], { h: 1 });
  });
  deck.click(slide, { appear: "result" });
};
"""


def deck_with(folder: Path, bad: str | None = None) -> None:
    """Write the passing deck into the folder, and after it the slide `bad` when given."""
    slides = {"title": PLAIN, "full": FULL}
    if bad is not None:
        slides["bad"] = bad
    write(folder, slides)
    (folder / "pictures" / "dot.png").write_bytes(DOT)
    (folder / "notes" / "full.md").write_text(CUES, encoding="utf-8")


def failures(text: str) -> list[tuple[str, str, str, str, str]]:
    """Read a report's failures: (slide id, page, shape, check, rule) of each."""
    return re.findall(
        r'slide (\S+) \(page (\d+)\), shape "([^"]*)": ([a-z-]+) \(rule (\d+)\)', text
    )


@pytest.fixture(scope="module")
def passing(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the passing deck once."""
    path = tmp_path_factory.mktemp("lint") / "talk"
    assert lab_deck("new", path).returncode == 0
    deck_with(path)
    first = lab_deck("build", path)
    assert first.returncode == 0, first.stdout + first.stderr
    return path


@pytest.fixture
def folder(passing: Path, tmp_path: Path) -> Path:
    """Give each test its own copy of the deck folder, with the passing deck built in it."""
    return Path(shutil.copytree(passing, tmp_path / "talk"))


def refused(folder: Path, bad: str) -> str:
    """Build the deck with `bad` over a built deck, and return what the build said.

    The build must be refused, and must leave the deck the last build wrote as it was.
    """
    before = (folder / "talk.pptx").read_bytes()
    deck_with(folder, bad)

    done = lab_deck("build", folder)

    assert done.returncode == 1, done.stdout + done.stderr
    assert "talk.pptx was left as it was" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    return done.stderr


def passes(folder: Path, bad: str) -> None:
    """Build the passing deck with one more slide, which must break nothing."""
    deck_with(folder, bad)
    done = lab_deck("build", folder)
    assert done.returncode == 0, done.stdout + done.stderr


def set_room(folder: Path, line: str) -> None:
    """Replace the brief's room line."""
    brief = folder / "brief.toml"
    text = brief.read_text(encoding="utf-8")
    assert 'room = "meeting room"' in text
    brief.write_text(re.sub(r"^room = .*$", line, text, flags=re.M), encoding="utf-8")


def test_a_deck_that_breaks_no_check_builds_and_lints_clean(folder: Path) -> None:
    """The passing deck: a table, a picture, Chinese, a citation, a page number, clicks, notes."""
    deck_with(folder)

    built = lab_deck("build", folder)
    linted = lab_deck("lint", folder)

    assert built.returncode == 0, built.stdout + built.stderr
    assert linted.returncode == 0, linted.stdout + linted.stderr
    assert "the lint passed on 2 slides (meeting room, 20 pt floor)" in linted.stdout
    assert failures(linted.stdout) == []
    # The page number and the citation are 12 pt, and neither is a failure.
    assert lint.lint(folder / "talk.pptx", "meeting room").findings == ()


def test_lint_says_its_widths_are_an_estimate(folder: Path) -> None:
    """Whether text fits is estimated from font widths, and every report says so."""
    deck_with(folder)
    lab_deck("build", folder)

    assert "an estimate from" in lab_deck("lint", folder).stdout


def test_text_under_the_floor_stops_the_build(folder: Path) -> None:
    """The failure names the slide by id and page, the shape, the check and the rule."""
    said = refused(folder, SMALL.replace("SIZE", "16"))

    assert failures(said) == [("bad", "3", "Text 1", "size-floor", "8")]
    assert "is 16 pt, under the 20 pt floor" in said


def test_the_floor_is_20_pt_in_a_meeting_room_and_24_pt_in_a_hall(folder: Path) -> None:
    """The room in the audience brief sets the floor."""
    passes(folder, SMALL.replace("SIZE", "22"))
    set_room(folder, 'room = "hall"')

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert ("bad", "3", "Text 1", "size-floor", "8") in failures(done.stderr)
    assert "is 22 pt, under the 24 pt floor" in done.stderr
    assert "hall, 24 pt floor" in done.stderr


def test_a_brief_with_no_room_takes_the_meeting_room_floor(folder: Path) -> None:
    """A missing room means a meeting room: 20 pt passes and 18 pt does not."""
    set_room(folder, "")
    passes(folder, SMALL.replace("SIZE", "20"))

    said = refused(folder, SMALL.replace("SIZE", "18"))

    assert failures(said) == [("bad", "3", "Text 1", "size-floor", "8")]
    assert "meeting room, 20 pt floor" in said


def test_one_citation_line_at_12_pt_is_allowed(folder: Path) -> None:
    """`deck.citation` draws it; the lint knows it by its name, `Citation`."""
    passes(folder, CITED.replace("CITE", 'deck.citation(slide, "Author, Journal, 2020");'))


def test_a_second_citation_line_stops_the_build(folder: Path) -> None:
    """One line under the floor per slide, not two."""
    two = (
        'deck.citation(slide, "Author, Journal, 2020");\n'
        '  deck.citation(slide, "Other, Journal, 2021", { y: 6.6 });'
    )

    said = refused(folder, CITED.replace("CITE", two))

    assert failures(said) == [("bad", "3", "Citation", "size-floor", "8")]
    assert "a second citation line" in said


def test_a_citation_of_two_lines_stops_the_build(folder: Path) -> None:
    """The allowance is one line; a citation that wraps is body text at 12 pt."""
    long = ", ".join(["Author, Journal, 2020"] * 12)

    said = refused(folder, CITED.replace("CITE", f'deck.citation(slide, "{long}", {{ h: 1 }});'))

    assert failures(said) == [("bad", "3", "Citation", "size-floor", "8")]
    assert "one line at 12 pt is allowed" in said


def test_12_pt_text_that_is_not_the_citation_stops_the_build(folder: Path) -> None:
    """Only the shape named `Citation` gets the allowance."""
    raw = (
        'slide.addText("A caption", '
        "{ x: 1, y: 3, w: 4, h: 0.5, fontFace: deck.font, fontSize: 12 });"
    )

    said = refused(folder, CITED.replace("CITE", raw))

    assert failures(said) == [("bad", "3", "Text 1", "size-floor", "8")]


def test_chinese_text_keeps_the_same_floor(folder: Path) -> None:
    """Chinese under the floor fails as Latin does."""
    said = refused(folder, CHINESE.replace("TEXT", '"甲基化"').replace("SIZE", "16"))

    assert failures(said) == [("bad", "3", "Text 1", "size-floor", "8")]
    assert "甲基化" in said


def test_text_that_overflows_its_box_stops_the_build(folder: Path) -> None:
    """Four phrases in a box with room for two lines; the report calls it an estimate."""
    said = refused(folder, OVERFLOW)

    assert failures(said) == [("bad", "3", "Text 1", "text-overflow", "8")]
    assert "an estimate from font widths" in said


def test_chinese_text_wraps_between_characters_and_can_overflow(folder: Path) -> None:
    """A full-width character is as wide as the font size, and a line breaks beside any one.

    The box is 4 inches wide and one line tall. Nine characters at 24 pt fit; twenty-seven need
    three lines.
    """
    passes(folder, CHINESE.replace("TEXT", '"甲基化区分细胞类型"').replace("SIZE", "24"))

    said = refused(
        folder, CHINESE.replace("TEXT", f'"{"甲基化区分细胞类型" * 3}"').replace("SIZE", "24")
    )

    assert failures(said) == [("bad", "3", "Text 1", "text-overflow", "8")]
    assert "about 3 lines" in said


def test_a_picture_over_text_stops_the_build(folder: Path) -> None:
    """A picture drawn after the text, where the text's words are."""
    said = refused(folder, COVERED.replace("FIRST", WORDS).replace("SECOND", IMAGE))

    assert failures(said) == [("bad", "3", "Image 0", "picture-over-text", "16")]
    assert '"Text 1"' in said


def test_text_drawn_over_a_picture_is_a_label_and_passes(folder: Path) -> None:
    """Text above a picture can be read; only a picture above text hides it."""
    passes(folder, COVERED.replace("FIRST", IMAGE).replace("SECOND", WORDS))


def test_a_picture_and_text_that_no_click_state_shows_together_pass(folder: Path) -> None:
    """A click takes the words away as it brings the picture to their place."""
    swapped = COVERED.replace(
        "FIRST", f'deck.section(slide, "words", () => {{ {WORDS} }});'
    ).replace(
        "SECOND",
        f'deck.section(slide, "figure", () => {{ {IMAGE} }});\n'
        '  deck.click(slide, { appear: "figure", disappear: "words" });',
    )

    passes(folder, swapped)


def test_a_shape_with_a_negative_size_fails_the_lint(folder: Path) -> None:
    """No slide source can write one past the build, so the built deck is edited as by hand."""
    deck_with(folder)
    lab_deck("build", folder)
    path = folder / "talk.pptx"
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    slide = parts["ppt/slides/slide2.xml"].decode("utf-8")
    box = re.search(r'name="Slide title".*?<a:ext cx="(\d+)"', slide, flags=re.S)
    assert box is not None
    edited = slide[: box.start(1)] + "-" + slide[box.start(1) :]
    parts["ppt/slides/slide2.xml"] = edited.encode("utf-8")
    write_deck(path, parts)

    linted = lab_deck("lint", folder)

    assert linted.returncode == 1
    assert failures(linted.stdout) == [("full", "2", "Slide title", "negative-size", "17")]
    assert "its width is negative" in linted.stdout


@pytest.mark.parametrize(
    ("notes", "cues"),
    [("Say it.\n\n[Click] Then this.\n\n[Click] And this.\n", 2), ("Say it, with no cue.\n", 0)],
)
def test_click_cues_that_do_not_match_the_clicks_stop_the_build(
    folder: Path, notes: str, cues: int
) -> None:
    """One `[Click]` cue per click: a slide with one click and two cues, or none, is refused."""
    (folder / "notes" / "bad.md").write_text(notes, encoding="utf-8")

    said = refused(folder, CLICKED)

    assert failures(said) == [("bad", "3", "notes", "click-cues", "18")]
    assert f"{cues} [Click] cue" in said
    assert "1 click (2 click states)" in said


def test_a_slide_with_clicks_and_no_notes_passes(folder: Path) -> None:
    """Notes are written last, and only for some decks, so missing notes break nothing."""
    passes(folder, CLICKED)


def test_lint_refuses_a_folder_whose_deck_is_not_built(folder: Path) -> None:
    """The lint reads the built deck, so there must be one."""
    (folder / "talk.pptx").unlink()

    linted = lab_deck("lint", folder)

    assert linted.returncode == 1
    assert "not built yet" in linted.stderr


def test_every_blocking_check_names_a_rule_of_the_slide_rules_page() -> None:
    """The slide rules name each lint check beside the rule it enforces."""
    page = Path(__file__).parents[2] / "skills/lab-presentation/references/slide-rules.md"
    rules = dict(
        re.findall(r"^(\d+)\. (.*?)(?=^\d+\. |\Z)", page.read_text("utf-8"), flags=re.M | re.S)
    )

    for check in lint.CHECKS:
        assert check.severity in (lint.BLOCKING, lint.WARNING)
        assert f"`{check.name}`" in rules[str(check.rule)], check.name


def test_a_font_with_no_file_is_measured_by_the_built_in_widths() -> None:
    """Helvetica's widths stand in, and the report says which font was not found."""
    fonts = lint.Fonts("No Such Font")

    # H 722, e 556, l 222, l 222, o 556: 2278 thousandths of 100 pt.
    assert fonts.width("Hello", 100, False) == pytest.approx(227.8)
    # A full-width character is a square of the font size.
    assert fonts.width("中文", 20, False) == pytest.approx(40)
    assert "no font file for No Such Font" in fonts.how
