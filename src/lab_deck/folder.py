"""The deck folder: what `new` writes, and what every other command reads back.

The layout, all of it content and none of it build code::

    brief.toml       the audience brief
    plan.html        the slide plan, approved before any slide is built
    deck.toml        the title, the built file's name, and the slides in order
    theme.toml       the font and the accent colour
    slides/<id>.js   one source file per slide; the file name is the slide's id
    pictures/        pictures, each with the prompt that made it beside it
    notes/<id>.md    speaker notes, one file per slide, named as the slide is
    <output>.pptx    the built deck

A slide's id is a name, never a number, so inserting a slide renames nothing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ORDER = "deck.toml"
BRIEF = "brief.toml"
THEME = "theme.toml"

# Body size and the floor for anything the audience must read, in points, by room.
ROOMS = {"meeting room": {"body": 24, "floor": 20}, "hall": {"body": 28, "floor": 24}}
# How the deck is used. A deck read alone may carry its own sentences.
PRESENTED = "presented"
READ_ALONE = "read alone"
USES = (PRESENTED, READ_ALONE)
# The level the talk reports at. High-level is what was built, how the work proceeds and why
# it matters; technical detail then belongs in the notes.
HIGH_LEVEL = "high-level"
LEVELS = (HIGH_LEVEL, "technical")
# One plain font, and the blue of the Okabe-Ito palette, which colour-blind viewers can tell
# from its other colours.
FONT = "Arial"
ACCENT = "0072B2"

# A slide's id: a name, which is also the name of its source file.
SLIDE_NAME = re.compile(r"[\w][\w.-]*")

# Path parts that mean a sync client owns the folder. A match only warns: the sync client and
# git both rewrite files, and the member decides whether that matters.
SYNCED = re.compile(
    r"^(CloudStorage|Mobile Documents|My Drive|iCloud Drive|Google ?Drive.*|Dropbox.*|OneDrive.*|Box)$"
)

BRIEF_TEXT = """\
# The audience brief. The build and every check read it. An empty line is not agreed yet.
audience = ""            # who will listen
knows = ""               # what they already know
# minutes =              # the length of the talk, as a number
language = ""            # the language of the slides, such as "en" or "zh"
known_terms = []         # terms and abbreviations they need no help with
room = "meeting room"    # or "hall"
use = "presented"        # or "read alone"
level = "high-level"     # or "technical": the level the talk reports at
"""

ORDER_TEXT = """\
# The deck: its title, the file the build writes, and the slides in the order shown.
# Each name is a file, slides/<name>.js. To insert a slide, add a name; rename nothing.
title = {title}
output = {output}
slides = ["title"]
"""

THEME_TEXT = f"""\
# The theme changes these two things only.
font = "{FONT}"
accent = "{ACCENT}"      # one accent colour, as six hex digits
"""

SLIDE_TEXT = """\
// One slide. The file name is the slide's id; deck.toml puts it in order.
// `slide` is the PptxGenJS slide. `deck` carries the theme, the sizes and a few helpers:
//   deck.title(slide, text)            the slide's conclusion, in one short sentence
//   deck.lines(slide, [..], box)       phrases, one per line; an item is a string or
//                                      { text, accent: true, bold: true }; a box of
//                                      { sentence: true } marks a sentence as intended
//   deck.table(slide, rows, box)       a table; the first row is its header
//   deck.citation(slide, text)         the one citation line, at 12 pt
//   deck.picture(name)                 the path of a file in pictures/
//   deck.group(slide, name, draw)      what draw() draws becomes one group
//   deck.section(slide, name, draw)    what draw() draws shows and hides together
//   deck.click(slide, { appear, disappear })   one click; each names sections
//   deck.pres, deck.W, deck.H, deck.margin, deck.font, deck.accent, deck.size
module.exports = (slide, deck) => {
  deck.title(slide, {title});
};
"""

IGNORE_TEXT = """\
# PowerPoint's owner file while the deck is open, and the build's scratch folder.
~$*
.lab-deck-*
.DS_Store
"""


class Refusal(Exception):  # noqa: N818 - a refusal is an answer, not an error; as in edison_cli
    """A command that stops without doing its work, with the reason as its message."""


@dataclass(frozen=True)
class Folder:
    """A deck folder, read and checked."""

    path: Path
    title: str
    output: Path
    slides: tuple[str, ...]
    room: str
    font: str
    accent: str
    use: str = PRESENTED
    """`presented` or `read alone`, from the audience brief."""
    known_terms: tuple[str, ...] = ()
    """The terms and abbreviations the brief says the audience needs no help with."""
    level: str = HIGH_LEVEL
    """`high-level` or `technical`, from the audience brief: the level the talk reports at."""

    def source(self, slide: str) -> Path:
        """Return the source file of the slide with this id."""
        return self.path / "slides" / f"{slide}.js"


def synced(path: Path) -> str | None:
    """Name the path part that puts this folder inside a synced cloud folder, if one does."""
    return next((part for part in path.absolute().parts if SYNCED.match(part)), None)


def _quoted(text: str) -> str:
    """Spell a string as TOML and JavaScript both read it."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def new(path: Path, title: str | None = None) -> Folder:
    """Write a new deck folder at `path` and start its git history.

    Raises
    ------
    Refusal
        When `path` already holds something, or git is missing or fails.
    """
    path = path.absolute()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise Refusal(f"{path} is not empty; `new` only makes a new deck folder.")
    git = shutil.which("git")
    if git is None:
        raise Refusal("git is not installed, and a deck folder keeps its history in git.")
    title = title or path.name
    for name in ("slides", "pictures", "notes"):
        (path / name).mkdir(parents=True, exist_ok=True)
    for name in ("pictures", "notes"):
        (path / name / ".gitkeep").touch()
    files = {
        BRIEF: BRIEF_TEXT,
        ORDER: ORDER_TEXT.format(title=_quoted(title), output=_quoted(f"{path.name}.pptx")),
        THEME: THEME_TEXT,
        "slides/title.js": SLIDE_TEXT.replace("{title}", _quoted(title)),
        ".gitignore": IGNORE_TEXT,
    }
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    done = subprocess.run([git, "init", "--quiet"], cwd=path, capture_output=True, text=True)
    if done.returncode != 0:
        raise Refusal(f"git init failed in {path}: {done.stderr.strip()}")
    return read(path)


def _table(path: Path, required: bool = False) -> dict[str, Any]:
    """Read one TOML file of the deck folder; a missing optional file is empty."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            raise Refusal(
                f"{path.parent} has no {path.name}, so it is not a deck folder. "
                "Make one with `lab-deck new`."
            ) from None
        return {}
    except tomllib.TOMLDecodeError as error:
        raise Refusal(f"{path} is not valid TOML: {error}") from None


def read(path: Path) -> Folder:
    """Read the deck folder at `path`.

    Raises
    ------
    Refusal
        When it is not a deck folder, or one of its files says something the build cannot use.
    """
    path = path.absolute()
    order = _table(path / ORDER, required=True)
    brief = _table(path / BRIEF)
    theme = _table(path / THEME)

    slides = order.get("slides")
    if not isinstance(slides, list) or not slides or not all(isinstance(s, str) for s in slides):
        raise Refusal(f"{ORDER}: `slides` must list at least one slide name.")
    for slide in slides:
        if not SLIDE_NAME.fullmatch(slide):
            raise Refusal(f"{ORDER}: {slide!r} is not a slide name; use letters, digits, - and _.")
    if len(set(slides)) != len(slides):
        raise Refusal(f"{ORDER}: a slide is listed twice.")
    output = order.get("output")
    if not isinstance(output, str) or Path(output).name != output or not output.endswith(".pptx"):
        raise Refusal(f"{ORDER}: `output` must be a .pptx file name, with no folder.")
    # A missing room means a meeting room.
    room = brief.get("room") or "meeting room"
    if room not in ROOMS:
        raise Refusal(f"{BRIEF}: `room` is {room!r}; it must be one of {', '.join(ROOMS)}.")
    # A missing use means presented.
    use = brief.get("use") or PRESENTED
    if use not in USES:
        raise Refusal(f"{BRIEF}: `use` is {use!r}; it must be one of {', '.join(USES)}.")
    # A missing level means high-level.
    level = brief.get("level") or HIGH_LEVEL
    if level not in LEVELS:
        raise Refusal(f"{BRIEF}: `level` is {level!r}; it must be one of {', '.join(LEVELS)}.")
    known = brief.get("known_terms") or []
    if not isinstance(known, list) or not all(isinstance(term, str) for term in known):
        raise Refusal(f"{BRIEF}: `known_terms` must be a list of terms, each in quotes.")
    other = sorted(set(theme) - {"font", "accent"})
    if other:
        raise Refusal(
            f"{THEME}: {', '.join(other)} cannot be set; a theme changes `font` and `accent` only."
        )
    accent = str(theme.get("accent") or ACCENT).lstrip("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", accent):
        raise Refusal(f"{THEME}: `accent` must be six hex digits, such as {ACCENT}.")
    folder = Folder(
        path=path,
        title=str(order.get("title") or path.name),
        output=path / output,
        slides=tuple(slides),
        room=room,
        font=str(theme.get("font") or FONT),
        accent=accent,
        use=use,
        known_terms=tuple(known),
        level=level,
    )
    for slide in folder.slides:
        if not folder.source(slide).is_file():
            raise Refusal(f"{ORDER} lists {slide!r}, but there is no slides/{slide}.js.")
    return folder
