"""`lab-deck build`: a one-slide deck folder becomes a 16:9 PowerPoint file."""

from __future__ import annotations

from pathlib import Path

from tests.lab_deck.conftest import Deck, lab_deck

# 13.333 by 7.5 inches, PowerPoint's own widescreen size, in EMU (914400 to the inch).
WIDESCREEN = (12192000, 6858000)

SLIDE = """\
module.exports = (slide, deck) => {
  deck.title(slide, "Methylation separates the cell types");
  deck.lines(slide, ["Two clusters", "One marker gene"]);
};
"""


def test_build_writes_a_one_slide_widescreen_deck(folder: Path) -> None:
    """The starter folder builds as it is, into the file the slide order names."""
    built = lab_deck("build", folder)

    assert built.returncode == 0, built.stdout + built.stderr
    deck = Deck(folder / "talk.pptx")
    assert deck.size == WIDESCREEN
    assert len(deck.slides) == 1
    assert "talk.pptx" in built.stdout
    assert sorted(p.name for p in folder.iterdir() if p.name.startswith(".lab-deck")) == []


def test_build_without_a_folder_builds_the_one_it_is_run_in(folder: Path) -> None:
    """A member inside the deck folder types `lab-deck build` and nothing else."""
    built = lab_deck("build", cwd=folder)

    assert built.returncode == 0, built.stdout + built.stderr
    assert (folder / "talk.pptx").is_file()


def test_the_slide_source_decides_what_the_slide_says(folder: Path) -> None:
    """The words in the source are the words on the slide, in order."""
    (folder / "slides" / "title.js").write_text(SLIDE, encoding="utf-8")

    built = lab_deck("build", folder)

    assert built.returncode == 0, built.stdout + built.stderr
    assert Deck(folder / "talk.pptx").text(1) == [
        "Methylation separates the cell types",
        "Two clusters",
        "One marker gene",
    ]


def test_the_theme_sets_the_font_and_the_accent_colour(folder: Path) -> None:
    """A deck matches an event by its theme file, with no change to a slide source."""
    (folder / "slides" / "title.js").write_text(
        SLIDE.replace('"Two clusters"', '{ text: "Two clusters", accent: true }'),
        encoding="utf-8",
    )
    (folder / "theme.toml").write_text('font = "Verdana"\naccent = "D55E00"\n', encoding="utf-8")

    lab_deck("build", folder)

    slide = Deck(folder / "talk.pptx").slides[0]
    assert 'typeface="Verdana"' in slide
    assert 'typeface="Arial"' not in slide
    assert 'srgbClr val="D55E00"' in slide


def test_a_hall_brief_makes_the_body_text_larger(folder: Path) -> None:
    """24 pt in a meeting room, 28 pt in a hall; the file counts in hundredths of a point."""
    (folder / "slides" / "title.js").write_text(SLIDE, encoding="utf-8")
    lab_deck("build", folder)
    assert 'sz="2400"' in Deck(folder / "talk.pptx").slides[0]

    brief = folder / "brief.toml"
    text = brief.read_text(encoding="utf-8")
    assert 'room = "meeting room"' in text
    brief.write_text(text.replace('room = "meeting room"', 'room = "hall"'), encoding="utf-8")
    lab_deck("build", folder)

    slide = Deck(folder / "talk.pptx").slides[0]
    assert 'sz="2800"' in slide
    assert 'sz="2400"' not in slide


def test_a_slide_source_that_fails_leaves_the_last_built_deck_alone(folder: Path) -> None:
    """The deck is replaced in one step, or not at all."""
    lab_deck("build", folder)
    before = (folder / "talk.pptx").read_bytes()
    (folder / "slides" / "title.js").write_text(
        'module.exports = () => { throw new Error("no such helper"); };\n', encoding="utf-8"
    )

    built = lab_deck("build", folder)

    assert built.returncode == 1
    assert "title" in built.stderr
    assert "no such helper" in built.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    assert sorted(p.name for p in folder.iterdir() if p.name.startswith(".lab-deck")) == []


def test_a_slide_in_the_order_with_no_source_is_named(folder: Path) -> None:
    """The order is the one list of slides, so a name with no file is a mistake to report."""
    order = folder / "deck.toml"
    order.write_text(
        order.read_text(encoding="utf-8").replace('["title"]', '["results"]'), encoding="utf-8"
    )

    built = lab_deck("build", folder)

    assert built.returncode == 1
    assert "slides/results.js" in built.stderr
    assert not (folder / "talk.pptx").exists()


def test_a_folder_that_is_not_a_deck_folder_is_refused(tmp_path: Path) -> None:
    """Nothing is written into a folder `lab-deck new` did not make."""
    built = lab_deck("build", tmp_path)

    assert built.returncode == 1
    assert "deck.toml" in built.stderr
    assert list(tmp_path.iterdir()) == []
