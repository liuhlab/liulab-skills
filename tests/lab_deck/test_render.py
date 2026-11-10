"""`lab-deck render` and `lab-deck preflight`, with a stand-in for LibreOffice.

Poppler is the real one, from the pixi environment. The stand-in writes a PDF with one page
per slide that is not hidden, so the page count and the pictures are the render's own work.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from lab_deck import preflight, render
from lab_deck.merge import write as write_zip
from tests.lab_deck.conftest import Deck, lab_deck
from tests.lab_deck.test_clicks import BOTH, STAGED
from tests.lab_deck.test_deck import PLAIN, built, write

STAND_IN = Path(__file__).with_name("stand_in_soffice.py")
PNG = b"\x89PNG\r\n\x1a\n"
THREE = {"title": PLAIN, "staged": STAGED, "signal": BOTH}


@pytest.fixture(autouse=True)
def soffice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put the stand-in where `lab-deck` looks for LibreOffice."""
    program = tmp_path / "soffice"
    program.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(STAND_IN))} "$@"\n',
        encoding="utf-8",
    )
    program.chmod(0o755)
    monkeypatch.setenv(render.SOFFICE, str(program))
    return program


def rendered(folder: Path) -> str:
    """Render the deck folder and return what the command printed."""
    done = lab_deck("render", folder)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def pictures(folder: Path) -> list[str]:
    """Name the pictures in the deck folder's render folder."""
    return sorted(path.name for path in (folder / "renders").glob("*.png"))


def hide(deck: Path, number: int) -> None:
    """Hide one slide of a built deck, as a hand edit in PowerPoint does."""
    with zipfile.ZipFile(deck) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    name = f"ppt/slides/slide{number}.xml"
    parts[name], count = re.subn(rb"<p:sld ", b'<p:sld show="0" ', parts[name], count=1)
    assert count == 1
    write_zip(deck, parts)


def test_every_click_state_of_every_slide_becomes_a_picture(folder: Path) -> None:
    """A slide with n clicks gives n + 1 pictures, named by its id and the clicks made."""
    write(folder, THREE)
    built(folder)

    said = rendered(folder)

    assert pictures(folder) == [
        "signal.click0.png",
        "signal.click1.png",
        "staged.click0.png",
        "staged.click1.png",
        "staged.click2.png",
        "title.click0.png",
    ]
    for name in pictures(folder):
        assert (folder / "renders" / name).read_bytes().startswith(PNG)
    assert "rendered 6 click states of 3 slides into renders/" in said
    assert "new: renders/staged.click2.png  slide staged (page 2), after click 2" in said


def test_a_click_state_holds_what_the_audience_sees(folder: Path, tmp_path: Path) -> None:
    """What a later click brings is not there yet; what an earlier click took away is gone."""
    write(folder, {"title": PLAIN, "staged": STAGED})
    built(folder)
    copy = tmp_path / "copy.pptx"

    states, unshown = render.expand(folder / "talk.pptx", copy)

    assert [(state.slide, state.clicks) for state in states] == [
        ("title", 0),
        ("staged", 0),
        ("staged", 1),
        ("staged", 2),
    ]
    assert unshown == []
    deck = Deck(copy)
    seen = [[name for _, name in deck.shapes(n)] for n in range(2, 5)]
    assert seen[0] == ["Slide title", "Question", "Page number"]
    assert seen[1] == ["Slide title", "Question", "Method", "Method detail", "Page number"]
    assert seen[2] == ["Slide title", "Method", "Method detail", "Result", "Page number"]
    assert all("<p:timing" not in slide for slide in deck.slides)


def test_a_group_shows_and_hides_as_one(folder: Path, tmp_path: Path) -> None:
    """A grouped drawing a click brings is cut out whole before the click."""
    write(folder, {"title": PLAIN, "signal": BOTH})
    built(folder)
    copy = tmp_path / "copy.pptx"

    render.expand(folder / "talk.pptx", copy)

    deck = Deck(copy)
    assert [name for _, name in deck.shapes(2)] == ["Slide title", "Page number"]
    assert {"Track", "bar", "peak", "Label"} <= {name for _, name in deck.shapes(3)}


def test_a_hidden_slide_is_rendered_too(folder: Path) -> None:
    """LibreOffice leaves a hidden slide out of a PDF; the render shows it first."""
    write(folder, THREE)
    built(folder)
    hide(folder / "talk.pptx", 2)

    said = rendered(folder)

    assert len(pictures(folder)) == 6
    assert "slide staged (page 2, hidden), as it opens" in said


def test_a_second_render_lists_only_the_pictures_that_changed(folder: Path) -> None:
    """A picture has changed when it differs from the one the last render left."""
    write(folder, THREE)
    built(folder)
    rendered(folder)
    assert "no picture changed since the last render" in rendered(folder)

    source = folder / "slides" / "signal.js"
    source.write_text(source.read_text().replace('"Signal"', '"A new label"'), encoding="utf-8")
    built(folder)
    said = rendered(folder)

    # The label is in the section the click brings, so the slide as it opens is as it was.
    assert re.findall(r"^(?:new|changed|gone): .*", said, flags=re.M) == [
        "changed: renders/signal.click1.png  slide signal (page 3), after click 1"
    ]
    assert "5 pictures did not change" in said


def test_a_new_slide_and_a_dropped_slide_touch_no_other_picture(folder: Path) -> None:
    """Pictures are named by slide id, so each is compared with its own last picture."""
    write(folder, THREE)
    built(folder)
    rendered(folder)

    write(folder, {"title": PLAIN, "signal": BOTH, "last": PLAIN})
    built(folder)
    said = rendered(folder)

    lines = re.findall(r"^(?:new|changed|gone): \S+", said, flags=re.M)
    # `signal` moved from page 3 to page 2, so the page number drawn on it changed.
    assert lines == [
        "new: renders/last.click0.png",
        "changed: renders/signal.click0.png",
        "changed: renders/signal.click1.png",
        "gone: renders/staged.click0.png",
        "gone: renders/staged.click1.png",
        "gone: renders/staged.click2.png",
    ]
    assert pictures(folder) == [
        "last.click0.png",
        "signal.click0.png",
        "signal.click1.png",
        "title.click0.png",
    ]


def test_rendering_never_modifies_the_deck_and_git_ignores_the_pictures(folder: Path) -> None:
    """The deck's bytes and time are as they were, and git sees nothing new."""
    write(folder, THREE)
    built(folder)
    deck = folder / "talk.pptx"
    before = (deck.read_bytes(), deck.stat().st_mtime_ns)
    subprocess.run(["git", "add", "-A"], cwd=folder, check=True)

    rendered(folder)

    assert (deck.read_bytes(), deck.stat().st_mtime_ns) == before
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=folder,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "??" not in status.stdout, status.stdout
    assert not list(folder.glob(".lab-deck-*"))


def test_a_libreoffice_that_aborts_is_a_refusal_that_names_the_sandbox(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The last render's pictures stay, and the message says where to run the command."""
    write(folder, THREE)
    built(folder)
    rendered(folder)
    before = {name: (folder / "renders" / name).read_bytes() for name in pictures(folder)}
    monkeypatch.setenv("STAND_IN_FAILS", "1")

    done = lab_deck("render", folder)

    assert done.returncode == 1
    assert "exit 134" in done.stderr
    assert "outside the sandbox" in done.stderr
    assert {name: (folder / "renders" / name).read_bytes() for name in pictures(folder)} == before


def test_render_refuses_a_folder_with_no_built_deck(folder: Path) -> None:
    """There is nothing to render before the first build."""
    done = lab_deck("render", folder)

    assert done.returncode == 1
    assert "run `lab-deck build` first" in done.stderr


def test_render_without_libreoffice_points_to_preflight(
    folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing LibreOffice is a refusal, not a traceback."""
    built(folder)
    monkeypatch.setenv(render.SOFFICE, str(tmp_path / "nothing-here"))

    done = lab_deck("render", folder)

    assert done.returncode == 1
    assert "LibreOffice was not found" in done.stderr
    assert "lab-deck preflight" in done.stderr


def test_preflight_reports_each_tool_and_the_font_as_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With all three there, each line says present."""
    monkeypatch.setattr(preflight, "fonts", lambda: {"arial"})

    found = preflight.checks("Arial")

    assert [check.name for check in found] == ["LibreOffice", "Poppler", "font Arial"]
    assert all(check.found is not None for check in found)
    assert preflight.text(found).count("present: ") == 3


def test_preflight_says_how_to_get_each_missing_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing tool or font comes with the way to get it."""
    monkeypatch.setattr(render, "soffice", lambda: None)
    monkeypatch.setattr(render, "tool", lambda name: None)
    monkeypatch.setattr(preflight, "fonts", lambda: {"arial"})

    said = preflight.text(preflight.checks("Cambria")).splitlines()

    assert said[0].startswith("missing: LibreOffice. To get it: install it from https://")
    assert said[1].startswith("missing: Poppler. To get it: ")
    assert "pixi install" in said[1]
    assert said[2].startswith("missing: font Cambria. To get it: install the font")
    assert "theme.toml" in said[2]


def test_preflight_reads_the_font_from_the_theme_and_exits_1_when_it_is_missing(
    folder: Path,
) -> None:
    """The font checked is the deck folder's own."""
    (folder / "theme.toml").write_text('font = "No Such Font 4821"\n', encoding="utf-8")

    done = lab_deck("preflight", folder)

    assert done.returncode == 1, done.stdout + done.stderr
    assert "present: LibreOffice" in done.stdout
    assert "present: Poppler" in done.stdout
    assert "missing: font No Such Font 4821" in done.stdout
