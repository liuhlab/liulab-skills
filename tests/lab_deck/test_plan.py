"""`lab-deck plan-lint`: the check of the slide plan page, before any slide is built.

Each test writes a small `plan.html` into a new deck folder and reads what the command says.
Nothing is built, so no test here starts Node.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab_deck import lint
from tests.lab_deck.conftest import lab_deck

PAGE = "<!doctype html>\n<html><body>\n<main>\nSLIDES</main>\n</body></html>\n"


def words(count: int, word: str = "word") -> str:
    """Spell `count` words."""
    return " ".join([word] * count)


def slide(
    ident: str | None = "why",
    body: str = "First phrase",
    panel: str = "What the presenter says",
    picture: str = "A bar chart of the two rates",
    title: str = "Trimming raises the alignment rate",
    figure: str = "",
) -> str:
    """Write one slide of a plan page: the mock-up and its side panel."""
    named = "" if ident is None else f' data-slide="{ident}"'
    return f"""\
<section class="plan-slide"{named}>
  <div class="on-slide">
    <h2 class="slide-title">{title}</h2>
    <ul><li>{body}</li></ul>
    <div class="slide-figure">{figure}</div>
  </div>
  <aside class="side-panel">
    <h3>Picture</h3><p class="planned-picture">{picture}</p>
    <h3>Says</h3><p>{panel}</p>
    <h3>Evidence</h3><p>Counts from the run of 2026-11-02</p>
  </aside>
</section>
"""


def plan(folder: Path, *slides: str) -> Path:
    """Give the deck folder a plan page of these slides."""
    page = folder / "plan.html"
    page.write_text(PAGE.replace("SLIDES", "".join(slides)), encoding="utf-8")
    return page


def test_a_mock_up_over_the_word_limit_warns_and_the_side_panel_does_not_count(
    folder: Path,
) -> None:
    """The limit is the deck lint's: 100 words beside the title. A warning stops nothing."""
    plan(
        folder,
        slide("fits", body=words(100), panel=words(300)),
        slide("long", body=words(101), panel="Short"),
    )

    done = lab_deck("plan-lint", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "plan.html: 1 warning" in done.stdout
    assert (
        "slide long: plan-words (rule 1): the mock-up carries 101 words beside its title, "
        "and the limit is 100" in done.stdout
    )
    assert "slide fits" not in done.stdout


def test_the_label_in_the_picture_box_counts_as_words_of_the_mock_up(folder: Path) -> None:
    """Everything inside the mock-up but its title counts, so text cannot hide in the box."""
    plan(folder, slide("box", body=words(95), figure=words(6)))

    assert "the mock-up carries 101 words" in lab_deck("plan-lint", folder).stdout


def test_the_plan_and_the_deck_share_one_word_limit(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing the deck lint's limit changes the plan's: the plan holds no number of its own."""
    plan(folder, slide("short", body=words(6)))
    assert "passed" in lab_deck("plan-lint", folder).stdout

    monkeypatch.setattr(lint, "WORDS", 5)

    assert "the mock-up carries 6 words beside its title, and the limit is 5" in (
        lab_deck("plan-lint", folder).stdout
    )


def test_a_chinese_character_of_the_mock_up_counts_as_one_word(folder: Path) -> None:
    """The counter is the deck lint's, so a Chinese plan is held to the same limit."""
    plan(folder, slide("cells", body="细胞" * 51))

    assert "the mock-up carries 102 words" in lab_deck("plan-lint", folder).stdout


def test_a_deck_read_alone_gets_no_word_warning(folder: Path) -> None:
    """As in the deck lint: a deck read alone may carry more words."""
    plan(folder, slide("long", body=words(150)))
    brief = folder / "brief.toml"
    text = brief.read_text(encoding="utf-8")
    brief.write_text(text.replace('use = "presented"', 'use = "read alone"'), encoding="utf-8")

    done = lab_deck("plan-lint", folder)

    assert done.returncode == 0
    assert "plan.html: the plan lint passed on 1 planned slide." in done.stdout


def test_a_slide_with_no_id_or_no_picture_choice_fails(folder: Path) -> None:
    """The user approves each slide by its id, with a picture or an explicit "text only"."""
    plan(
        folder,
        slide("why", picture="text only"),
        slide(None),
        slide("how", picture=""),
        slide("why"),
    )

    done = lab_deck("plan-lint", folder)

    assert done.returncode == 1
    assert "plan.html: 3 blocking failures" in done.stdout
    assert "slide 2 (no id): plan-id: the slide has no id" in done.stdout
    assert "slide how: plan-picture: the slide names no picture" in done.stdout
    assert "slide why: plan-id: another slide of the plan has the same id" in done.stdout


def test_a_deck_folder_with_no_plan_page_is_refused(folder: Path) -> None:
    """Exit 1 with the reason, as every other command refuses."""
    done = lab_deck("plan-lint", folder)

    assert done.returncode == 1
    assert "has no plan.html" in done.stderr


TEMPLATE = Path(__file__).parents[2] / "skills/lab-presentation/assets/plan.html"


def test_the_template_the_skill_ships_passes_the_plan_lint(folder: Path) -> None:
    """The agent starts from a page that is already in the shape the lint reads."""
    (folder / "plan.html").write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

    done = lab_deck("plan-lint", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "the plan lint passed" in done.stdout


def test_the_template_is_one_file_that_opens_offline_and_on_a_phone() -> None:
    """No script, stylesheet, font or picture from elsewhere, and a viewport for a phone."""
    page = TEMPLATE.read_text(encoding="utf-8")

    assert "http://" not in page
    assert "https://" not in page
    assert " src=" not in page
    assert "<link" not in page
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in page
    assert "aspect-ratio: 16 / 9" in page


def test_a_brief_with_no_level_is_read_as_high_level_and_another_word_is_refused(
    folder: Path,
) -> None:
    """A deck folder made before the level line still reads; a level nobody defined does not."""
    plan(folder, slide())
    brief = folder / "brief.toml"
    text = brief.read_text(encoding="utf-8")
    line = 'level = "high-level"'
    assert line in text

    brief.write_text(text.replace(line, "# no level"), encoding="utf-8")
    assert lab_deck("plan-lint", folder).returncode == 0

    brief.write_text(text.replace(line, 'level = "deep"'), encoding="utf-8")
    done = lab_deck("plan-lint", folder)
    assert done.returncode == 1
    assert "`level` is 'deep'; it must be one of high-level, technical" in done.stderr


def test_a_slide_whose_section_or_paragraph_is_left_open_is_still_read_alone(
    folder: Path,
) -> None:
    """HTML lets `</p>`, `</li>` and a hand-written `</section>` be left out."""
    opened = slide("first").replace("</section>", "")
    loose = slide("loose", body=words(101)).replace(
        '<h2 class="slide-title">Trimming raises the alignment rate</h2>',
        '<p class="slide-title">Trimming raises the alignment rate',
    )
    plan(folder, opened, slide(None), loose)

    done = lab_deck("plan-lint", folder)

    assert "slide 2 (no id): plan-id" in done.stdout
    assert "slide loose: plan-words (rule 1): the mock-up carries 101 words" in done.stdout
    assert "plan-title" not in done.stdout
