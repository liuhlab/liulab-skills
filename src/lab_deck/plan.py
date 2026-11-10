"""Lint the slide plan page in plain code: no model, no tokens, no build.

The slide plan is `plan.html` in the deck folder: one HTML page the user approves before any
slide is built. Each slide of it is a `section` of class `plan-slide`, named by `data-slide`
with the id the slide will have in the deck. Inside it:

- `on-slide` holds the mock-up: only what will be on the slide.
- `slide-title`, inside the mock-up, holds the slide's title.
- `slide-figure`, inside the mock-up, marks where the picture goes. Its label is counted
  with the mock-up's other words, so it stays a few words long.
- `planned-picture`, in the side panel, says what the picture is, or `text only`.

Everything else in the section is the side panel, which the audience never sees and the
lint never counts. The word check uses the deck lint's own counter and limit, so the plan
cannot promise more text than the built slide may carry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from lab_deck import lint as linter
from lab_deck.folder import PRESENTED, READ_ALONE, SLIDE_NAME, Refusal
from lab_deck.lint import BLOCKING, WARNING

PAGE = "plan.html"

SLIDE = "plan-slide"
ON_SLIDE = "on-slide"
TITLE = "slide-title"
FIGURE = "slide-figure"
PICTURE = "planned-picture"

# Elements with no end tag, which never hold text.
VOID = frozenset(
    (
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    )
)
# Elements that sit inside a word or a phrase: a tag of one starts no new word.
INLINE = frozenset(
    ("a", "abbr", "b", "code", "em", "i", "mark", "s", "small", "span", "strong", "sub", "sup", "u")
)
# Elements whose text is code, not words on the page.
UNREAD = frozenset(("script", "style", "template"))

# Lists: an open list item is closed by the next item of the same list, not of a list inside it.
LISTS = frozenset(("ul", "ol"))


@dataclass
class Planned:
    """One slide of the plan, as the checks read it."""

    place: int
    """Its place on the page, counted from 1."""
    ident: str
    title: str = ""
    body: str = ""
    """The mock-up's words beside its title."""
    picture: str = ""


@dataclass(frozen=True)
class Finding:
    """One failure of one check on one planned slide."""

    check: str
    severity: str
    rule: int | None
    slide: str
    message: str


@dataclass(frozen=True)
class Report:
    """What the lint found in one plan page."""

    slides: int
    findings: tuple[Finding, ...]

    @property
    def blocking(self) -> tuple[Finding, ...]:
        """The findings the user cannot approve the plan over."""
        return tuple(one for one in self.findings if one.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        """The findings that are reported and stop nothing."""
        return tuple(one for one in self.findings if one.severity == WARNING)


@dataclass
class _Reader(HTMLParser):
    """Read a plan page into its planned slides."""

    slides: list[Planned] = field(default_factory=list)
    open: list[tuple[str, frozenset[str]]] = field(default_factory=list)
    """Every element now open, outermost first: its tag and its classes."""

    def __post_init__(self) -> None:
        super().__init__(convert_charrefs=True)

    def _inside(self, name: str) -> bool:
        return any(name in classes for _, classes in self.open)

    def _add(self, text: str) -> None:
        if not self._inside(SLIDE) or any(tag in UNREAD for tag, _ in self.open):
            return
        slide = self.slides[-1]
        if self._inside(PICTURE):
            slide.picture += text
        if not self._inside(ON_SLIDE):
            return
        if self._inside(TITLE):
            slide.title += text
        else:
            slide.body += text

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in INLINE:
            self._add(" ")
        if tag in VOID:
            return
        given = dict(attrs)
        classes = frozenset((given.get("class") or "").split())
        self._imply(tag)
        if SLIDE in classes:
            # A slide never holds a slide: one whose end tag was left out ends here.
            at = next((at for at, (_, held) in enumerate(self.open) if SLIDE in held), None)
            if at is not None:
                del self.open[at:]
            ident = (given.get("data-slide") or "").strip()
            self.slides.append(Planned(len(self.slides) + 1, ident))
        self.open.append((tag, classes))

    def _close(self, tag: str) -> None:
        """Close the innermost open element of this tag, and everything inside it."""
        for at in range(len(self.open) - 1, -1, -1):
            if self.open[at][0] == tag:
                del self.open[at:]
                break

    def _imply(self, tag: str) -> None:
        """Close what HTML lets a writer leave open: a paragraph, or the list item before."""
        tags = [held for held, _ in self.open]
        if tag not in INLINE and "p" in tags:
            # A paragraph holds phrases only, so any other element ends it.
            self._close("p")
        elif tag == "li" and "li" in tags:
            item = len(tags) - 1 - tags[::-1].index("li")
            if not LISTS & set(tags[item:]):
                self._close("li")

    def handle_endtag(self, tag: str) -> None:
        self._close(tag)
        if tag not in INLINE:
            self._add(" ")

    def handle_data(self, data: str) -> None:
        self._add(data)


def read(page: Path) -> list[Planned]:
    """Read the planned slides of the plan page at `page`, in the order shown.

    Raises
    ------
    Refusal
        When the page is missing, or holds no planned slide.
    """
    try:
        text = page.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Refusal(
            f"{page.parent} has no {page.name}. Write the slide plan from the template in "
            "the `lab-presentation` skill."
        ) from None
    reader = _Reader()
    reader.feed(text)
    reader.close()
    if not reader.slides:
        raise Refusal(
            f'{page.name} holds no planned slide: each is a <section class="{SLIDE}" '
            'data-slide="<slide id>">.'
        )
    for slide in reader.slides:
        slide.title, slide.body = " ".join(slide.title.split()), " ".join(slide.body.split())
        slide.picture = " ".join(slide.picture.split())
    return reader.slides


def lint(page: Path, use: str = PRESENTED) -> Report:
    """Run every check on the plan page at `page`, for the use the brief gives.

    Raises
    ------
    Refusal
        When the page is missing, or holds no planned slide.
    """
    slides = read(page)
    findings: list[Finding] = []
    seen: set[str] = set()
    for slide in slides:
        name = slide.ident or f"{slide.place} (no id)"

        def found(
            check: str, severity: str, rule: int | None, message: str, name: str = name
        ) -> None:
            findings.append(Finding(check, severity, rule, name, message))

        if not slide.ident:
            found(
                "plan-id",
                BLOCKING,
                None,
                "the slide has no id; name it with data-slide, as its source file will be named",
            )
        elif not SLIDE_NAME.fullmatch(slide.ident):
            found(
                "plan-id",
                BLOCKING,
                None,
                "the id is not a slide name; use letters, digits, - and _, as deck.toml does",
            )
        elif slide.ident in seen:
            found("plan-id", BLOCKING, None, "another slide of the plan has the same id")
        seen.add(slide.ident)
        if not slide.title:
            found(
                "plan-title",
                BLOCKING,
                2,
                f'the mock-up has no title; put the conclusion in its "{TITLE}" element',
            )
        if not slide.picture:
            found(
                "plan-picture",
                BLOCKING,
                None,
                f'the slide names no picture; say what it shows in its "{PICTURE}" element, '
                'or write "text only"',
            )
        words = linter.count_words(slide.body)
        # The limit is read from the deck lint at each run: one number for the plan and the deck.
        if use != READ_ALONE and words > linter.WORDS:
            found(
                "plan-words",
                WARNING,
                1,
                f"the mock-up carries {words} words beside its title, and the limit is "
                f"{linter.WORDS} (a Chinese character counts as one word)",
            )
    return Report(len(slides), tuple(findings))


def render(report: Report, name: str) -> str:
    """Spell the report as text, under the plan page's file name."""

    def listed(findings: tuple[Finding, ...]) -> list[str]:
        return [
            f"  slide {one.slide}: {one.check}"
            + ("" if one.rule is None else f" (rule {one.rule})")
            + f": {one.message}"
            for one in findings
        ]

    def count(number: int, what: str) -> str:
        return f"{number} {what}{'' if number == 1 else 's'}"

    if not report.findings:
        return f"{name}: the plan lint passed on {count(report.slides, 'planned slide')}."
    lines = []
    if report.blocking:
        lines.append(f"{name}: {count(len(report.blocking), 'blocking failure')}")
        lines += listed(report.blocking)
    if report.warnings:
        lines.append(f"{name}: {count(len(report.warnings), 'warning')}")
        lines += listed(report.warnings)
    return "\n".join(lines)
