"""A deck left open or unsaved in PowerPoint: what `compare` and `build` do about it.

PowerPoint here is the stand-in of `stand_in_powerpoint.py`, which `conftest.py` puts on the PATH of
every `lab-deck` run. A test sets what PowerPoint holds, runs the command as a member would,
and reads the message, the deck file and the commands PowerPoint got.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lab_deck import powerpoint as scripts
from tests.lab_deck.conftest import (
    PLAIN,
    Deck,
    PowerPoint,
    found,
    git,
    lab_deck,
    on,
    save,
    swap,
    write,
)

NAMES = ("title", "question", "method", "result", "end")


@pytest.fixture(scope="module")
def committed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a deck of five slides once, and commit the build."""
    path = tmp_path_factory.mktemp("powerpoint") / "talk"
    assert lab_deck("new", path).returncode == 0
    write(path, dict.fromkeys(NAMES, PLAIN))
    done = lab_deck("build", path)
    assert done.returncode == 0, done.stdout + done.stderr
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "Build")
    return path


@pytest.fixture
def folder(committed: Path, tmp_path: Path) -> Path:
    """Give each test its own copy of the built, committed deck folder."""
    return Path(shutil.copytree(committed, tmp_path / "talk"))


def opened(folder: Path, **more: object) -> dict[str, object]:
    """Describe the deck of `folder` as open in PowerPoint: saved, on slide 1, unless told."""
    return {"path": str(folder / "talk.pptx"), "saved": True, "slide": 1, **more}


def edit_in_powerpoint(folder: Path, tmp_path: Path) -> str:
    """Make an edit that PowerPoint holds and the file on disk lacks; give where it is kept."""
    deck = folder / "talk.pptx"
    on_disk = deck.read_bytes()
    save(folder, on("question", "First phrase", swap("First phrase", "A better phrase")))
    unsaved = tmp_path / "unsaved.pptx"
    shutil.copyfile(deck, unsaved)
    deck.write_bytes(on_disk)
    return str(unsaved)


def change_a_source(folder: Path) -> None:
    """Change one slide source, so that the next build writes a different deck."""
    source = folder / "slides" / "result.js"
    source.write_text(
        source.read_text(encoding="utf-8").replace("About result", "A new result"),
        encoding="utf-8",
    )


# Reading the hand edits.


def test_compare_saves_an_open_deck_with_unsaved_changes_and_says_so(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """The edit is in PowerPoint only; after the save through PowerPoint, the report has it."""
    powerpoint.start(opened(folder, saved=False, unsaved=edit_in_powerpoint(folder, tmp_path)))

    done = lab_deck("compare", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    told, report = done.stdout.split("\n\n", 1)
    assert told.startswith("saved talk.pptx in PowerPoint: it was open with unsaved changes.")
    assert 'now "A better phrase\\nSecond phrase"' in found(report)
    assert powerpoint.commands == ["list", "saved", "save", "saved"]
    assert powerpoint.state["decks"][0]["saved"] is True, "the deck stays open, now saved"


def test_compare_sends_no_save_to_an_open_deck_that_is_saved(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """A saved deck is the file on disk: it is read as it is, and nothing is said."""
    powerpoint.start(opened(folder))

    done = lab_deck("compare", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "PowerPoint" not in done.stdout.split("\n\n", 1)[0]
    assert powerpoint.commands == ["list", "saved"]


def test_a_deck_is_found_under_another_spelling_of_its_folder(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """PowerPoint may name the folder through a link, so the paths are compared resolved."""
    link = tmp_path / "link"
    link.symlink_to(folder, target_is_directory=True)
    kept = edit_in_powerpoint(folder, tmp_path)
    powerpoint.start(opened(folder, saved=False, unsaved=kept, spelled=str(link / "talk.pptx")))

    done = lab_deck("compare", folder)

    assert done.stdout.startswith("saved talk.pptx in PowerPoint"), done.stdout + done.stderr


def test_another_deck_open_in_powerpoint_is_left_alone(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """Only the deck of this folder matters, however many others are open and unsaved."""
    other = tmp_path / "other.pptx"
    shutil.copyfile(folder / "talk.pptx", other)
    powerpoint.start({"path": str(other), "saved": False, "slide": 2})
    change_a_source(folder)

    assert lab_deck("compare", folder).returncode == 0
    built = lab_deck("build", folder)

    assert built.returncode == 0, built.stdout + built.stderr
    assert powerpoint.commands == ["list", "list"]
    assert "PowerPoint" not in built.stdout


def test_powerpoint_that_is_not_running_is_not_started(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """Not running means not open: both commands go on, and send PowerPoint nothing."""
    powerpoint.start()
    powerpoint.kept.write_text(powerpoint.kept.read_text().replace("true", "false", 1))
    change_a_source(folder)

    assert lab_deck("compare", folder).returncode == 0
    built = lab_deck("build", folder)

    assert built.returncode == 0, built.stdout + built.stderr
    assert powerpoint.log == []


# Writing the rebuilt deck.


def test_build_closes_an_open_deck_writes_it_and_reopens_it_at_the_same_slide(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """Close, then write, then reopen: PowerPoint never holds a deck that changes under it."""
    powerpoint.start(opened(folder, slide=4))
    change_a_source(folder)

    done = lab_deck("build", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert powerpoint.commands == [
        "list",
        "saved",
        "slide",
        "close",
        "list",
        "open",
        "list",
        "goto",
    ]
    close, reopen = powerpoint.log[3], powerpoint.log[5]
    assert close[-1] != reopen[-1], "the deck was not written between the close and the reopen"
    assert "A new result" in Deck(folder / "talk.pptx").text(4)
    assert powerpoint.state["decks"] == [opened(folder.resolve(), slide=4)]
    assert "closed talk.pptx in PowerPoint for the build, and reopened it at slide 4" in done.stdout


def test_a_slide_past_the_end_of_the_new_deck_becomes_the_last_slide(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """The deck got shorter, so the slide that was showing no longer exists."""
    powerpoint.start(opened(folder, slide=5))
    write(folder, dict.fromkeys(NAMES[:3], PLAIN))

    done = lab_deck("build", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert powerpoint.state["decks"][0]["slide"] == 3
    assert "reopened it at slide 3" in done.stdout


def test_build_refuses_an_open_deck_with_unsaved_changes(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """A build over unsaved hand edits would lose them: nothing is closed, nothing written."""
    powerpoint.start(opened(folder, saved=False, unsaved=edit_in_powerpoint(folder, tmp_path)))
    before = (folder / "talk.pptx").read_bytes()
    change_a_source(folder)

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert "unsaved changes" in done.stderr
    assert "lab-deck compare" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    assert powerpoint.commands == ["list", "saved"]
    assert len(powerpoint.state["decks"]) == 1, "the deck is still open"


def test_a_build_that_fails_after_the_close_shows_the_last_built_deck_again(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """The user gets back the deck they had open, on the slide they were on."""
    powerpoint.start(opened(folder, slide=2))
    before = (folder / "talk.pptx").read_bytes()
    (folder / "slides" / "result.js").write_text("module.exports = () => { throw 1; };\n")

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert (folder / "talk.pptx").read_bytes() == before
    assert powerpoint.state["decks"][0]["slide"] == 2
    assert "reopened it at slide 2" in done.stdout


def test_a_deck_that_cannot_be_reopened_is_built_and_the_user_is_told(
    folder: Path, powerpoint: PowerPoint
) -> None:
    """The deck is written by then, so this is told, not refused."""
    powerpoint.start(opened(folder), refuse=("open",))
    change_a_source(folder)

    done = lab_deck("build", folder)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "A new result" in Deck(folder / "talk.pptx").text(4)
    assert "could not reopen it" in done.stdout


# When PowerPoint cannot be asked.


@pytest.mark.parametrize("command", ["build", "compare"])
def test_off_a_mac_the_command_stops_and_asks_to_save_and_close(
    command: str, folder: Path, powerpoint: PowerPoint
) -> None:
    """With no way to ask PowerPoint, the deck is not shown to be closed: nothing is done."""
    before = (folder / "talk.pptx").read_bytes()
    change_a_source(folder)

    done = lab_deck(command, folder, mac=False)

    assert done.returncode == 1
    assert "save the deck and close it" in done.stderr
    assert "--closed" in done.stderr
    assert done.stdout == ""
    assert (folder / "talk.pptx").read_bytes() == before
    assert powerpoint.log == []


@pytest.mark.parametrize("command", ["build", "compare"])
def test_off_a_mac_the_users_word_that_the_deck_is_closed_is_taken(
    command: str, folder: Path
) -> None:
    """`--closed` is how the command goes on once the user has saved and closed the deck."""
    change_a_source(folder)

    done = lab_deck(command, folder, "--closed", mac=False)

    assert done.returncode == 0, done.stdout + done.stderr
    if command == "build":
        assert "A new result" in Deck(folder / "talk.pptx").text(4)


def test_off_a_mac_a_first_build_has_no_deck_to_be_open(tmp_path: Path) -> None:
    """A deck file that does not exist yet is open nowhere, so nothing needs asking."""
    path = tmp_path / "fresh"
    assert lab_deck("new", path, mac=False).returncode == 0

    done = lab_deck("build", path, mac=False)

    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("command", "refused", "sent"),
    [
        ("build", "list", ["list"]),
        ("build", "saved", ["list", "saved"]),
        ("build", "slide", ["list", "saved", "slide"]),
        ("build", "close", ["list", "saved", "slide", "close"]),
        ("compare", "list", ["list"]),
        ("compare", "saved", ["list", "saved"]),
    ],
)
def test_when_powerpoint_refuses_the_command_stops_and_writes_nothing(
    command: str, refused: str, sent: list[str], folder: Path, powerpoint: PowerPoint
) -> None:
    """Permission denied, or any other refusal, at any step: the deck file is not touched."""
    powerpoint.start(opened(folder), refuse=(refused,))
    before = (folder / "talk.pptx").read_bytes()
    change_a_source(folder)

    done = lab_deck(command, folder)

    assert done.returncode == 1
    assert "Not authorized to send Apple events" in done.stderr
    assert "save the deck" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before
    assert powerpoint.commands == sent


def test_compare_stops_when_powerpoint_does_not_save(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """Unsaved edits that cannot be saved are not read around: the report would miss them."""
    kept = edit_in_powerpoint(folder, tmp_path)
    powerpoint.start(opened(folder, saved=False, unsaved=kept), refuse=("save",))

    done = lab_deck("compare", folder)

    assert done.returncode == 1
    assert "could not be saved from here" in done.stderr
    assert done.stdout == ""


def test_the_users_word_does_not_outrank_powerpoints_answer(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """`--closed` covers only a PowerPoint that cannot be asked, never one that says open."""
    powerpoint.start(opened(folder, saved=False, unsaved=edit_in_powerpoint(folder, tmp_path)))
    before = (folder / "talk.pptx").read_bytes()

    done = lab_deck("build", folder, "--closed")

    assert done.returncode == 1
    assert "unsaved changes" in done.stderr
    assert (folder / "talk.pptx").read_bytes() == before


def test_two_open_decks_of_one_name_stop_the_build(
    folder: Path, tmp_path: Path, powerpoint: PowerPoint
) -> None:
    """PowerPoint tells decks apart by name, so a second `talk.pptx` makes the name unsafe."""
    twin = tmp_path / "elsewhere" / "talk.pptx"
    twin.parent.mkdir()
    shutil.copyfile(folder / "talk.pptx", twin)
    powerpoint.start(opened(folder), {"path": str(twin), "saved": False, "slide": 1})

    done = lab_deck("build", folder)

    assert done.returncode == 1
    assert "two decks named talk.pptx" in done.stderr
    assert powerpoint.commands == ["list"]


# The scripts themselves, which no test here can send to the real PowerPoint.


SENT = (scripts.LIST, scripts.SAVED, scripts.SAVE, scripts.SLIDE, scripts.CLOSE, scripts.GOTO)


@pytest.mark.parametrize("script", SENT)
def test_every_script_has_a_timeout_and_addresses_the_deck_by_name(script: str) -> None:
    """A dialog in PowerPoint blocks a script, and a kept reference to a deck goes stale."""
    assert f"with timeout of {scripts.WAIT} seconds" in script
    assert "set p to" not in script
    if script != scripts.LIST:
        assert "presentation (item 1 of argv)" in script


@pytest.mark.parametrize("script", SENT)
def test_no_script_opens_a_file_or_saves_under_a_new_name(script: str) -> None:
    """Either raises a "Grant File Access" dialog, which blocks until the user answers."""
    lines = [line.strip() for line in script.splitlines()]
    assert not any(line.startswith("open ") for line in lines)
    assert not any(line.startswith("save ") and " in " in line for line in lines)


def test_the_running_check_does_not_address_powerpoint() -> None:
    """It asks macOS. A `tell` would start PowerPoint to ask it whether it is running."""
    assert "tell" not in scripts.RUNNING
