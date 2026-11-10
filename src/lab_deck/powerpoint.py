"""Ask PowerPoint about the deck file: is it open, is it saved; save it, close it, reopen it.

A deck left open in PowerPoint is a trap in both directions. PowerPoint may hold edits the
file on disk lacks, so reading the file misses them; and PowerPoint keeps showing the old
slides after a build writes the file, so the user sees a stale deck and may save it back.

This module is the only place that talks to PowerPoint, and `run` is its one call to the
outside: `osascript` for every question and order, and `open` to show the deck again. A test
replaces those two programs with a stand-in. Control is for a Mac only. Anywhere else, and
whenever PowerPoint does not answer, the deck cannot be shown to be closed, and the command
stops with a message to save and close it.

What the scripts may and may not do was measured on PowerPoint 16 for Mac:

- A deck is addressed by its name every time. A reference kept in a variable goes stale.
- Open decks are listed with `full name of every presentation`, and the paths are compared
  resolved, because PowerPoint may spell the same folder through a different link.
- PowerPoint saves in place only, and is never told to open a file or to save under a new
  name: either raises a "Grant File Access" dialog that blocks the script. The reopen goes
  through `open -a` from the shell, which raises none.
- Every command has a timeout, because any dialog in PowerPoint blocks a script.
- `application … is running` asks macOS, not PowerPoint, so it starts nothing. Every other
  script would start PowerPoint, and is sent only after that answer was yes.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from lab_deck.folder import Refusal

APP = "Microsoft PowerPoint"
# Seconds PowerPoint gets to answer one command, and to show a deck after `open`.
WAIT = 30
# Seconds between two looks for the reopened deck.
PAUSE = 0.5


def _tell(*lines: str) -> str:
    """Wrap AppleScript lines for PowerPoint in a timeout; `argv` holds the arguments."""
    body = "\n".join(f"\t\t\t{line}" for line in lines)
    return (
        "on run argv\n"
        f'\ttell application "{APP}"\n'
        f"\t\twith timeout of {WAIT} seconds\n"
        f"{body}\n"
        "\t\tend timeout\n"
        "\tend tell\n"
        "end run"
    )


# Each script is fixed text. The deck's name travels as an argument, never inside the script,
# so no file name can change what a script does.
RUNNING = f'application "{APP}" is running'
# With no deck open the list is `missing value`, so the count is asked first.
LIST = _tell(
    'if (count of presentations) is 0 then return ""',
    "set AppleScript's text item delimiters to linefeed",
    "return (full name of every presentation) as text",
)
SAVED = _tell("return saved of presentation (item 1 of argv)")
SAVE = _tell("save presentation (item 1 of argv)")
SLIDE = _tell(
    "return slide index of slide of view of document window 1 of presentation (item 1 of argv)"
)
CLOSE = _tell("close presentation (item 1 of argv) saving no")
GOTO = _tell(
    "go to slide (view of document window 1 of presentation (item 1 of argv)) "
    "number ((item 2 of argv) as integer)"
)


class Refused(Exception):  # noqa: N818 - an answer from PowerPoint, as `Refusal` is one to the user
    """PowerPoint could not be asked, or did not do what it was asked."""


@dataclass(frozen=True)
class Held:
    """A deck that was closed for a build: the file, its name in PowerPoint, the slide shown."""

    deck: Path
    name: str
    slide: int


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one program that reaches PowerPoint. The only outside call of this module."""
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=WAIT + 10)


def _do(program: str, *args: str) -> str:
    """Run `osascript` or `open`, and give what it printed.

    Raises
    ------
    Refused
        When the program is absent, runs out of time, or exits with anything but 0.
    """
    found = shutil.which(program)
    if found is None:
        raise Refused(f"there is no `{program}` here, so this is not a Mac")
    try:
        done = run([found, *args])
    except subprocess.TimeoutExpired:
        raise Refused(f"PowerPoint did not answer in {WAIT} seconds") from None
    if done.returncode != 0:
        said = done.stderr.strip().splitlines()
        raise Refused(said[-1] if said else f"`{program}` failed")
    return done.stdout.strip()


def _ask(script: str, *args: str) -> str:
    """Send one script to PowerPoint and give its answer."""
    return _do("osascript", "-e", script, *args)


def _same(spelled: str, deck: Path) -> bool:
    """Tell whether a path as PowerPoint spells it is the deck file."""
    try:
        return Path(spelled).resolve() == deck
    except (OSError, ValueError):
        return False


def name_if_open(deck: Path) -> str | None:
    """Give the name PowerPoint has the deck open under, or None when it is not open.

    PowerPoint that is not running has no deck open, and is not started to be asked.

    Raises
    ------
    Refused
        When PowerPoint cannot be asked, or two open decks share the deck's name, so that
        the name does not say which one is meant.
    """
    if _ask(RUNNING) != "true":
        return None
    listed = [line for line in _ask(LIST).splitlines() if line.strip()]
    deck = deck.resolve()
    if not any(_same(line, deck) for line in listed):
        return None
    if sum(Path(line).name == deck.name for line in listed) > 1:
        raise Refused(
            f"two decks named {deck.name} are open, and PowerPoint tells them apart by name"
        )
    return deck.name


def _stop(deck: Path, why: Refused) -> Refusal:
    """Word the stop for a deck that cannot be shown to be closed."""
    return Refusal(
        f"{deck.name} may be open in PowerPoint, and PowerPoint could not be asked: {why}.\n"
        "Nothing was read or written. Ask the user to save the deck and close it in "
        "PowerPoint, then run this again with --closed."
    )


def _open_name(deck: Path, closed: bool) -> str | None:
    """Find the deck in PowerPoint, or stop. `closed` is the user's word that it is closed."""
    try:
        return name_if_open(deck)
    except Refused as why:
        if closed:
            return None
        raise _stop(deck, why) from None


def save_if_unsaved(deck: Path, closed: bool = False) -> str | None:
    """Before the deck file is read: have PowerPoint save it when it holds unsaved changes.

    Returns the sentence that tells the user what was done, or None when nothing was.

    Raises
    ------
    Refusal
        When the deck cannot be shown to be closed and `closed` is false, or PowerPoint has
        it open and does not say whether it is saved, or does not save it.
    """
    if not deck.is_file():
        return None
    name = _open_name(deck, closed)
    if name is None:
        return None
    try:
        if _ask(SAVED, name) == "true":
            return None
        _ask(SAVE, name)
        if _ask(SAVED, name) != "true":
            raise Refused("the deck still has unsaved changes after the save")
    except Refused as why:
        raise Refusal(
            f"{deck.name} is open in PowerPoint and could not be saved from here: {why}.\n"
            "Nothing was read. Ask the user to save the deck in PowerPoint, then run this again."
        ) from None
    return (
        f"saved {deck.name} in PowerPoint: it was open with unsaved changes. Tell the user, "
        "and commit the saved deck before you change anything."
    )


def close_for_build(deck: Path, closed: bool = False) -> Held | None:
    """Before the deck file is written: close it in PowerPoint, and remember the slide shown.

    Returns what `reopen` needs, or None when the deck was not open.

    Raises
    ------
    Refusal
        When the deck is open with unsaved changes, which a build would lose; when it cannot
        be shown to be closed and `closed` is false; or when PowerPoint does not close it.
    """
    if not deck.is_file():
        return None
    name = _open_name(deck, closed)
    if name is None:
        return None
    try:
        if _ask(SAVED, name) != "true":
            raise Refusal(
                f"{deck.name} is open in PowerPoint with unsaved changes, and a build would "
                "lose them.\nNothing was written. Run `lab-deck compare` first: it saves the "
                "deck and lists the hand edits to copy into the slide sources."
            )
        shown = _ask(SLIDE, name)
        slide = int(shown) if shown.isdigit() else 1
        _ask(CLOSE, name)
        if name_if_open(deck) is not None:
            raise Refused("the deck is still open after the close")
    except Refused as why:
        raise _stop(deck, why) from None
    return Held(deck.resolve(), name, slide)


def reopen(held: Held, slides: int | None = None) -> str:
    """After the build: show the deck again at the slide it was on, and say so.

    `slides` is how many slides the deck now has; a slide past the end becomes the last one.
    Nothing here raises: the deck is already written, so a failure is told, not refused.
    """
    slide = held.slide if slides is None else max(1, min(held.slide, slides))
    try:
        _do("open", "-a", APP, str(held.deck))
        ends = time.monotonic() + WAIT
        while name_if_open(held.deck) is None:
            if time.monotonic() > ends:
                raise Refused(f"PowerPoint did not show the deck in {WAIT} seconds")
            time.sleep(PAUSE)
    except Refused as why:
        return (
            f"closed {held.name} in PowerPoint for the build, and could not reopen it: {why}. "
            "Tell the user to open it again."
        )
    try:
        _ask(GOTO, held.name, str(slide))
    except Refused as why:
        return (
            f"closed {held.name} in PowerPoint for the build and reopened it, but not at "
            f"slide {slide}: {why}. Tell the user."
        )
    return (
        f"closed {held.name} in PowerPoint for the build, and reopened it at slide {slide}. "
        "Tell the user."
    )
