"""`lab-deck build` on a deck folder with many slides: order, page numbers, theme, merge."""

from __future__ import annotations

import base64
import re
from pathlib import Path

from tests.lab_deck.conftest import PLAIN, Deck, lab_deck, write

# PptxGenJS's own table, between two text boxes: the case whose shape ids it gets wrong.
TABLE = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  deck.table(slide, [["Sample", "Reads"], ["A", "12 M"], ["B", "9 M"]]);
  deck.lines(slide, ["Below the table"], { y: 5.5, h: 1 });
  slide.addTable([["x", "y"]], {
    x: 8, y: 5.5, w: 4, fontSize: deck.size.floor, objectName: "Second table",
  });
};
"""

PICTURE = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  slide.addImage({ path: deck.picture("dot.png"), x: 1, y: 2, w: 1, h: 1 });
};
"""

# A 1 by 1 pixel PNG.
DOT = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def built(folder: Path) -> Deck:
    """Build the deck folder and read the deck it wrote."""
    done = lab_deck("build", folder)
    assert done.returncode == 0, done.stdout + done.stderr
    return Deck(folder / "talk.pptx")


FOUR = {"title": PLAIN, "question": PLAIN, "data": TABLE, "summary": PLAIN}


def test_the_slides_come_out_in_the_order_the_deck_folder_gives(folder: Path) -> None:
    """The order is `deck.toml`'s, not the alphabet's and not the files' ages."""
    write(folder, FOUR)

    deck = built(folder)

    assert deck.ids == ["title", "question", "data", "summary"]
    assert [deck.text(n)[0] for n in range(1, 5)] == [
        "About title",
        "About question",
        "About data",
        "About summary",
    ]


def test_every_slide_but_the_title_carries_its_page_number(folder: Path) -> None:
    """The number is the slide's place in the deck, so "slide 3" is the third slide."""
    write(folder, FOUR)

    deck = built(folder)

    assert [deck.page(n) for n in range(1, 5)] == [None, "2", "3", "4"]


def test_the_page_number_is_plain_text_not_powerpoints_field(folder: Path) -> None:
    """PptxGenJS gives its slide-number field one shape id on every slide; a text box has none."""
    write(folder, FOUR)

    deck = built(folder)

    for slide in deck.slides:
        assert "<a:fld" not in slide
        assert "Slide Number Placeholder" not in slide


def test_a_table_keeps_every_shape_id_on_its_slide_unique(folder: Path) -> None:
    """PptxGenJS numbers a table's frame apart from the other shapes, and the two collide."""
    write(folder, FOUR)

    deck = built(folder)

    assert "<a:tbl>" in deck.slides[2]
    for number in range(1, 5):
        ids = [ident for ident, _ in deck.shapes(number)]
        assert len(ids) == len(set(ids)), deck.shapes(number)
    # Each object's id is its place in the drawing order, a table's included.
    assert deck.shapes(3) == [
        ("2", "Slide title"),
        ("3", "Table"),
        ("4", "Text 1"),
        ("5", "Second table"),
        ("6", "Page number"),
    ]


def test_a_table_is_drawn_at_the_body_size_of_the_room(folder: Path) -> None:
    """24 pt in a meeting room, as the body text is: the floor is a limit, not a default."""
    write(folder, FOUR)

    deck = built(folder)

    table = re.search(r"<a:tbl>.*?</a:tbl>", deck.slides[2], flags=re.S)
    assert table is not None
    assert set(re.findall(r'sz="(\d+)"', table[0])) == {"2400"}


def test_inserting_a_slide_in_the_middle_changes_no_other_slide(folder: Path) -> None:
    """One new name in the order and one new file: no rename, no new shape id elsewhere."""
    write(folder, FOUR)
    before = built(folder)
    sources = {p.name: p.read_bytes() for p in (folder / "slides").iterdir()}

    write(
        folder,
        {"title": PLAIN, "question": PLAIN, "method": PLAIN, "data": TABLE, "summary": PLAIN},
    )
    after = built(folder)

    assert after.ids == ["title", "question", "method", "data", "summary"]
    for name, source in sources.items():
        assert (folder / "slides" / name).read_bytes() == source
    # The slides before the new one are the same bytes.
    assert after.slides[:2] == before.slides[:2]
    # The slides after it keep every shape, id and word; only the page number moved on.
    assert [after.page(n) for n in (4, 5)] == ["4", "5"]
    for old, new in ((3, 4), (4, 5)):
        assert after.shapes(new) == before.shapes(old)
        assert after.text(new)[:-1] == before.text(old)[:-1]


def test_the_default_theme_is_white_one_font_black_text_one_accent(folder: Path) -> None:
    """The look every deck starts from, read out of the written file."""
    write(folder, FOUR)

    deck = built(folder)

    theme = deck.parts["ppt/theme/theme1.xml"]
    assert re.findall(r'<a:latin typeface="([^"]*)"', theme)[:2] == ["Arial", "Arial"]
    for slide in deck.slides:
        assert '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/>' in slide
        assert set(re.findall(r'<a:latin typeface="([^"]*)"', slide)) == {"Arial"}
        # Black text and the one accent; a table's hairlines are black too.
        assert set(re.findall(r'<a:srgbClr val="([0-9A-F]{6})"', slide)) <= {
            "FFFFFF",
            "000000",
            "0072B2",
        }
    assert 'srgbClr val="0072B2"' in deck.slides[1]


def test_the_theme_file_changes_the_font_and_the_accent_of_every_slide(folder: Path) -> None:
    """The table and the page number follow the theme as the title does."""
    write(folder, FOUR)
    (folder / "theme.toml").write_text('font = "Verdana"\naccent = "D55E00"\n', encoding="utf-8")

    deck = built(folder)

    theme = deck.parts["ppt/theme/theme1.xml"]
    assert re.findall(r'<a:latin typeface="([^"]*)"', theme)[:2] == ["Verdana", "Verdana"]
    for slide in deck.slides:
        assert set(re.findall(r'<a:latin typeface="([^"]*)"', slide)) == {"Verdana"}
        assert "0072B2" not in slide
    assert 'srgbClr val="D55E00"' in deck.slides[1]


def test_a_theme_file_that_sets_anything_else_is_refused(folder: Path) -> None:
    """The theme may change the font and the accent only."""
    (folder / "theme.toml").write_text(
        'font = "Verdana"\nbackground = "000000"\n', encoding="utf-8"
    )

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert "background" in done.stderr
    assert not (folder / "talk.pptx").exists()


def test_a_picture_used_on_two_slides_is_stored_once(folder: Path) -> None:
    """Each slide builds alone with its own copy; the merge keeps one and points both at it."""
    (folder / "pictures" / "dot.png").write_bytes(DOT)
    write(folder, {"title": PLAIN, "first": PICTURE, "second": PICTURE})

    deck = built(folder)

    assert list(deck.media.values()) == [DOT]
    (name,) = deck.media
    for number in (2, 3):
        rels = deck.parts[f"ppt/slides/_rels/slide{number}.xml.rels"]
        assert f'Target="../media/{Path(name).name}"' in rels


def test_no_path_of_this_machine_is_in_the_built_deck(folder: Path) -> None:
    """PptxGenJS writes a picture's whole path as its alt text; the build writes its name."""
    (folder / "pictures" / "dot.png").write_bytes(DOT)
    described = PICTURE.replace("x: 1,", 'altText: "A dot", x: 1,')
    write(folder, {"title": PLAIN, "first": PICTURE, "second": described})

    deck = built(folder)

    assert 'descr="dot.png"' in deck.slides[1]
    assert 'descr="A dot"' in deck.slides[2]
    for name, part in deck.parts.items():
        assert str(folder.parent) not in part, name
        assert str(Path.home()) not in part, name
        assert not re.search(r'(descr|name|title)="(/|[A-Za-z]:\\)', part), name


def test_every_part_the_deck_names_is_in_the_file(folder: Path) -> None:
    """PowerPoint offers to repair a deck whose list of parts and whose parts disagree."""
    (folder / "pictures" / "dot.png").write_bytes(DOT)
    write(folder, {**FOUR, "picture": PICTURE})

    deck = built(folder)

    assert len(deck.names) == len(set(deck.names))
    types = deck.parts["[Content_Types].xml"]
    for number in range(1, 6):
        assert f'PartName="/ppt/slides/slide{number}.xml"' in types
        assert f'PartName="/ppt/notesSlides/notesSlide{number}.xml"' in types
        assert f"ppt/slides/slide{number}.xml" in deck.names
        assert f"ppt/notesSlides/notesSlide{number}.xml" in deck.names
    assert 'PartName="/ppt/slides/slide6.xml"' not in types
    assert "<Slides>5</Slides>" in deck.parts["docProps/app.xml"]
    assert len(set(re.findall(r'<p:sldId id="(\d+)"', deck.parts["ppt/presentation.xml"]))) == 5


def test_building_twice_writes_the_same_bytes(folder: Path) -> None:
    """A rebuild that changes nothing shows no change in the deck folder's git history."""
    write(folder, FOUR)
    built(folder)
    first = (folder / "talk.pptx").read_bytes()

    built(folder)

    assert (folder / "talk.pptx").read_bytes() == first


def test_a_chart_is_refused_because_the_merge_does_not_carry_it(folder: Path) -> None:
    """A chart brings parts of its own; a deck that lost them would open broken."""
    write(folder, FOUR)
    built(folder)
    before = (folder / "talk.pptx").read_bytes()
    (folder / "slides" / "data.js").write_text(
        "module.exports = (slide, deck) => {\n"
        '  slide.addChart(deck.pres.ChartType.bar, [{ name: "n", labels: ["a"], values: [1] }]);\n'
        "};\n",
        encoding="utf-8",
    )

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert "chart" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before


def test_a_later_slide_that_fails_is_named_and_the_old_deck_stays(folder: Path) -> None:
    """One bad slide among good ones stops the whole build."""
    write(folder, FOUR)
    built(folder)
    before = (folder / "talk.pptx").read_bytes()
    (folder / "slides" / "data.js").write_text(
        'module.exports = () => { throw new Error("no such column"); };\n', encoding="utf-8"
    )

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert "slides/data.js" in done.stderr
    assert "no such column" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    assert sorted(p.name for p in folder.iterdir() if p.name.startswith(".lab-deck")) == []
