"""The lint checks that warn: one slide per warning, in one deck that still builds.

The deck is built once for the whole file, because a build runs Node. Each example is one
slide of it that breaks one warning check and nothing else. The tests read the report of that
one build, and lint the built deck again under another brief.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from lab_deck import lint
from tests.lab_deck.conftest import Deck, build_once, copy_deck, lab_deck
from tests.lab_deck.test_lint import deck_with, failures

SLIDE = """\
module.exports = (slide, deck) => {
  deck.title(slide, "TITLE");
  BODY
};
"""
# 105 words in one paragraph, with no sentence in it.
WORDS = 'deck.lines(slide, [Array(105).fill("word").join(" ")], { fontSize: 20 });'
# 102 Chinese characters, with no space between them.
CHINESE = 'deck.lines(slide, ["细胞".repeat(51)], { fontSize: 20 });'
SENTENCES = """deck.lines(slide, [
    "We found that trimming the reads improved the rate",
    "Trimming the reads improved the alignment rate.",
    "Trimmed reads: higher alignment rate",
  ]);"""
QUOTE = 'deck.lines(slide, ["We choose to go to the moon."], { sentence: true });'
# A title of three lines, in a box tall enough to hold them, so that nothing overflows.
LONG_TITLE = """\
module.exports = (slide, deck) => {
  slide.addText(Array(12).fill("conclusion").join(" "), {
    x: deck.margin, y: 0.4, w: deck.W - 2 * deck.margin, h: 2.5, margin: 0, valign: "top",
    fontFace: deck.font, fontSize: deck.size.title, bold: true, objectName: "Slide title",
  });
};
"""
ABBREVIATIONS = """deck.lines(slide, [
    "Deep learning on DNA",
    "Adeno-associated virus (AAV) vectors",
    "RNA-seq depth",
  ]);"""
LATER = 'deck.lines(slide, ["AAVs and DNA again", "CpG sites"]);'
COLOURS = """deck.lines(slide, [{ text: "The point", accent: true }, "The rest"], { h: 1.5 });
  slide.addText("A second colour", {
    x: 1, y: 4, w: 6, h: 0.6, fontFace: deck.font, fontSize: deck.size.body, color: "D55E00",
  });"""

SLIDES = {
    "words": SLIDE.replace("BODY", WORDS),
    "chinese": SLIDE.replace("BODY", CHINESE),
    "sentence": SLIDE.replace("BODY", SENTENCES),
    "quote": SLIDE.replace("BODY", QUOTE),
    "longtitle": LONG_TITLE,
    "abbr": SLIDE.replace("BODY", ABBREVIATIONS),
    "later": SLIDE.replace("BODY", LATER),
    "colours": SLIDE.replace("BODY", COLOURS),
}
WARNINGS = [
    ("words", "3", "slide", "slide-words", "1"),
    ("chinese", "4", "slide", "slide-words", "1"),
    ("sentence", "5", "Text 1", "body-sentence", "1"),
    ("sentence", "5", "Text 1", "body-sentence", "1"),
    ("longtitle", "7", "Slide title", "title-lines", "2"),
    ("abbr", "8", "Text 1", "unknown-abbreviation", "4"),
    ("later", "9", "Text 1", "unknown-abbreviation", "4"),
    ("colours", "10", "Text 2", "accent-colours", "9"),
]


def set_brief(folder: Path, field: str, value: str) -> None:
    """Replace one line of the brief."""
    brief = folder / "brief.toml"
    text, done = re.subn(
        rf"^{field} = .*$", f"{field} = {value}", brief.read_text("utf-8"), flags=re.M
    )
    assert done == 1
    brief.write_text(text, encoding="utf-8")


@pytest.fixture(scope="module")
def built(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    """Build the deck of warning slides once: its folder, and what the build said."""

    def build(folder: Path) -> list[object]:
        made = lab_deck("new", folder)
        assert made.returncode == 0, made.stdout + made.stderr
        deck_with(folder)
        for name, source in SLIDES.items():
            (folder / "slides" / f"{name}.js").write_text(
                source.replace("TITLE", f"About {name}"), encoding="utf-8"
            )
        order = folder / "deck.toml"
        listed = ", ".join(f'"{name}"' for name in ("title", "full", *SLIDES))
        order.write_text(
            re.sub(r"slides = \[.*\]", f"slides = [{listed}]", order.read_text("utf-8")), "utf-8"
        )
        set_brief(folder, "known_terms", '["RNA-seq"]')
        done = lab_deck("build", folder)
        return [done.args, done.returncode, done.stdout, done.stderr]

    folder, said = build_once(tmp_path_factory, "warnings", build)
    assert isinstance(said, list)
    return folder, subprocess.CompletedProcess(*said)


@pytest.fixture
def copy(built: tuple[Path, subprocess.CompletedProcess[str]], tmp_path: Path) -> Path:
    """Give a test its own copy of the built deck folder, to change the brief of."""
    return copy_deck(built[0], tmp_path / "talk")


def test_a_warning_stops_no_build_and_the_build_prints_each_one(
    built: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    """One slide per warning check; the deck is written, and the build lists every warning."""
    folder, done = built

    assert done.returncode == 0, done.stdout + done.stderr
    assert (folder / "talk.pptx").is_file()
    assert "built " in done.stdout
    assert "talk.pptx: 8 warnings (meeting room, 20 pt floor)" in done.stdout
    assert "blocking" not in done.stdout
    assert failures(done.stdout) == WARNINGS


def test_lint_reports_the_same_warnings_and_exits_0(
    built: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    """`lab-deck lint` fails on a blocking failure only."""
    linted = lab_deck("lint", built[0])

    assert linted.returncode == 0, linted.stdout + linted.stderr
    assert failures(linted.stdout) == WARNINGS


def test_each_warning_says_what_it_found(
    built: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    """The words counted, the sentence and why, the lines, the abbreviation and the colours."""
    said = built[1].stdout

    assert "the slide carries 105 words beside its title, and the limit is 100" in said
    # A Chinese character counts as one word.
    assert "the slide carries 102 words beside its title" in said
    assert "reads as a full sentence: it opens with a subject, We" in said
    assert "reads as a full sentence: it ends as a sentence does" in said
    assert "Trimmed reads: higher" not in said
    assert "the title takes about 3 lines (an estimate from font widths)" in said
    assert "DNA is first used here" in said
    assert "CpG is first used here" in said
    assert "2 accent colours (0072B2, D55E00)" in said


def test_a_sentence_marked_as_intended_does_not_warn(
    built: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    """`{ sentence: true }` names the text box in the built deck, and the lint reads the name."""
    folder, done = built

    assert "quote" not in [slide for slide, *_ in failures(done.stdout)]
    assert ("3", "Intended sentence") in [
        (ident, name) for ident, name in Deck(folder / "talk.pptx").shapes(6)
    ]
    # The same sentence in a box with no mark warns.
    assert lint.sentence("We choose to go to the moon.") is not None


def test_an_abbreviation_spelled_out_or_known_does_not_warn(
    built: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    """AAV is spelled out at first use, RNA is in the brief's known terms, DNA warns once."""
    said = built[1].stdout

    assert "AAV" not in said
    assert "RNA" not in said
    assert said.count("DNA is first used here") == 1


def test_a_brief_with_no_known_terms_warns_for_each_abbreviation(copy: Path) -> None:
    """The known terms come from the brief: without `RNA-seq` there, RNA warns too."""
    set_brief(copy, "known_terms", "[]")

    linted = lab_deck("lint", copy)

    assert linted.returncode == 0, linted.stdout + linted.stderr
    assert "RNA is first used here" in linted.stdout


def test_a_read_alone_brief_drops_the_word_and_sentence_warnings(copy: Path) -> None:
    """A deck read alone may carry its own sentences; the other warnings stay."""
    set_brief(copy, "use", '"read alone"')

    linted = lab_deck("lint", copy)

    assert linted.returncode == 0, linted.stdout + linted.stderr
    assert failures(linted.stdout) == [
        one for one in WARNINGS if one[3] not in ("slide-words", "body-sentence")
    ]


def test_a_brief_with_another_use_is_refused(copy: Path) -> None:
    """The use is `presented` or `read alone`."""
    set_brief(copy, "use", '"handout"')

    linted = lab_deck("lint", copy)

    assert linted.returncode == 1
    assert "`use` is 'handout'; it must be one of presented, read alone" in linted.stderr


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("Trimmed reads: higher alignment rate", 5),
        ("甲基化区分细胞类型", 9),
        ("DNA 甲基化，区分细胞类型。", 10),  # noqa: RUF001 - Chinese punctuation is the case under test
        ("About 80% of reads - 12 M", 6),
        ("", 0),
    ],
)
def test_a_chinese_character_counts_as_one_word(text: str, words: int) -> None:
    """A word holds a letter or a digit; Chinese punctuation is no word."""
    assert lint.count_words(text) == words


@pytest.mark.parametrize(
    "text",
    [
        "Trimming the reads improved the rate.",
        "Does trimming raise the rate?",
        "Reads were trimmed. The rate rose",
        "It raises the alignment rate",
        "修剪读段提高了比对率。",
        "修剪读段。比对率提高",
    ],
)
def test_a_full_sentence_is_found(text: str) -> None:
    """By its end, by an end inside it, or by the subject it opens with."""
    assert lint.sentence(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "Trimmed reads: higher alignment rate",
        "Higher rate.",
        "Reads vs. rate in every sample",
        "Three steps: trim, align, count, etc.",
        "e.g. Trimmed reads from every sample",
        "修剪读段：比对率更高",  # noqa: RUF001 - Chinese punctuation is the case under test
    ],
)
def test_a_phrase_is_not_a_sentence(text: str) -> None:
    """A phrase, a line under four words, and a short form's full stop all pass."""
    assert lint.sentence(text) is None


def test_abbreviations_are_words_mostly_in_capitals() -> None:
    """A plural loses its s; a Roman numeral, a name and a heading in capitals are none."""
    assert lint.abbreviations("mRNA and CpG in AAVs, phase II, PowerPoint, 3D") == [
        "mRNA",
        "CpG",
        "AAV",
    ]
    assert lint.abbreviations("BACKGROUND\nTHE OPEN QUESTION\nUse PCR") == ["PCR"]
    # A long word in capitals is a heading only when it is all letters.
    assert lint.abbreviations("OVERVIEW of HEK293T cells") == ["HEK293T"]
    assert lint.spelled_out("polymerase chain reaction (PCR); AAV (a virus); DNA") == {
        "PCR",
        "AAV",
    }
    assert lint.spelled_out("聚合酶链式反应（PCR）") == {"PCR"}  # noqa: RUF001 - Chinese punctuation is the case under test


def test_the_slide_rules_give_the_limits_the_lint_uses() -> None:
    """The limits are written in the slide rules, and the lint holds the same ones."""
    page = Path(__file__).parents[2] / "skills/lab-presentation/references/slide-rules.md"
    text = " ".join(page.read_text("utf-8").split())
    rules, limits = text.split("## Warning limits", 1)

    assert f"{lint.WORDS} words" in rules
    assert f"{lint.WORDS} words" in limits
    assert {1: "one line", 2: "two lines"}[lint.TITLE_LINES] in limits
    assert "One Chinese character counts as one word" in text
    for check in lint.CHECKS:
        if check.severity == lint.WARNING:
            assert f"`{check.name}`" in text
