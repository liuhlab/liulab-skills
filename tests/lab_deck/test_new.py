"""`lab-deck new`: a deck folder in the right shape, with its own git history."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from tests.lab_deck.conftest import lab_deck


def test_new_makes_the_deck_folder_with_a_git_repo(tmp_path: Path) -> None:
    """The brief, the slide order, one slide source, pictures, notes and the theme."""
    path = tmp_path / "group meeting"

    made = lab_deck("new", path)

    assert made.returncode == 0, made.stdout + made.stderr
    for name in ("brief.toml", "deck.toml", "theme.toml", "slides/title.js"):
        assert (path / name).is_file(), name
    for name in ("pictures", "notes"):
        assert (path / name).is_dir(), name
    order = tomllib.loads((path / "deck.toml").read_text(encoding="utf-8"))
    assert order["slides"] == ["title"]
    assert order["output"] == "group meeting.pptx"
    inside = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=path, capture_output=True, text=True
    )
    assert Path(inside.stdout.strip()).resolve() == path.resolve()
    assert "warning" not in made.stdout + made.stderr


def test_new_leaves_every_brief_line_the_agent_asks_for_empty(tmp_path: Path) -> None:
    """Only the room and the use have a default; a filled line would read as agreed."""
    path = tmp_path / "talk"
    assert lab_deck("new", path).returncode == 0

    brief = tomllib.loads((path / "brief.toml").read_text(encoding="utf-8"))

    assert brief == {
        "audience": "",
        "knows": "",
        "language": "",
        "known_terms": [],
        "room": "meeting room",
        "use": "presented",
    }
    assert "# minutes =" in (path / "brief.toml").read_text(encoding="utf-8")


def test_new_inside_a_synced_cloud_folder_warns_and_still_makes_it(tmp_path: Path) -> None:
    """The member decides whether to move it; the tool only says so."""
    path = tmp_path / "Library" / "CloudStorage" / "GoogleDrive-someone" / "My Drive" / "talk"

    made = lab_deck("new", path)

    assert made.returncode == 0, made.stdout + made.stderr
    assert "warning" in made.stderr
    assert "synced" in made.stderr
    assert (path / "deck.toml").is_file()
    assert (path / ".git").is_dir()


def test_new_refuses_a_folder_that_already_holds_something(tmp_path: Path) -> None:
    """An existing deck is never written over."""
    path = tmp_path / "talk"
    path.mkdir()
    (path / "mine.txt").write_text("keep me\n", encoding="utf-8")

    made = lab_deck("new", path)

    assert made.returncode == 1
    assert "not empty" in made.stderr
    assert sorted(p.name for p in path.iterdir()) == ["mine.txt"]
