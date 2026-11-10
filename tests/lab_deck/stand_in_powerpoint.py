"""A stand-in for PowerPoint: what `osascript` and `open` do in the tests of `lab-deck`.

`conftest.py` puts two small programs named `osascript` and `open` first on PATH, and each
runs this file. So no test, on a Mac or off one, ever reaches the real PowerPoint.

The stand-in keeps PowerPoint's state in the JSON file that `LAB_DECK_STANDIN` names:

- `running`: whether PowerPoint is running.
- `decks`: the open decks, each with its `path`, `saved`, the `slide` shown, optionally the
  path PowerPoint has it `spelled` as, and optionally `unsaved`, a file that holds what a
  save would write.
- `refuse`: the commands PowerPoint refuses, by the names in `SCRIPTS`, or `open`.
- `log`: every command received, in order. A close and an open record the deck's bytes.

With no such file, PowerPoint is not running. A script this file does not know, or any script
but the running check sent while PowerPoint is not running, exits with 70: the real
PowerPoint would have been started by it.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from lab_deck import powerpoint

SCRIPTS = {
    powerpoint.RUNNING: "running",
    powerpoint.LIST: "list",
    powerpoint.SAVED: "saved",
    powerpoint.SAVE: "save",
    powerpoint.SLIDE: "slide",
    powerpoint.CLOSE: "close",
    powerpoint.GOTO: "goto",
}
DENIED = "execution error: Not authorized to send Apple events to Microsoft PowerPoint. (-1743)"
ABSENT = "execution error: The object you are trying to access does not exist (-1728)"


def digest(path: str) -> str:
    """Name the bytes of a file, to tell one build of the deck from another."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fail(message: str, status: int = 1) -> int:
    """Refuse as `osascript` does: a line on stderr and a status that is not 0."""
    print(message, file=sys.stderr)
    return status


def act(state: dict, program: str, args: list[str]) -> int:
    """Do one command to the state, print PowerPoint's answer, and give the exit status."""
    decks, refuse, log = state["decks"], state["refuse"], state["log"]
    if program == "open":
        if args[:2] != ["-a", powerpoint.APP] or len(args) != 3:
            return fail(f"open: unexpected arguments {args}", 70)
        log.append(["open", args[2], digest(args[2])])
        if "open" in refuse:
            return fail("Unable to find application named 'Microsoft PowerPoint'")
        state["running"] = True
        decks.append({"path": args[2], "saved": True, "slide": 1})
        return 0
    if args[:1] != ["-e"] or args[1] not in SCRIPTS:
        return fail(f"osascript: a script the stand-in does not know: {args}", 70)
    command, rest = SCRIPTS[args[1]], args[2:]
    if command == "running":
        print(str(state["running"]).lower())
        return 0
    if not state["running"]:
        log.append(["started by", command])
        return fail(f"`{command}` would have started PowerPoint", 70)
    log.append([command, *rest])
    if command in refuse:
        return fail(DENIED)
    if command == "list":
        print("\n".join(deck.get("spelled", deck["path"]) for deck in decks))
        return 0
    named = [deck for deck in decks if Path(deck["path"]).name == rest[0]]
    if not named:
        return fail(ABSENT)
    deck = named[0]
    if command == "saved":
        print(str(deck["saved"]).lower())
    elif command == "save":
        if "unsaved" in deck:
            shutil.copyfile(deck.pop("unsaved"), deck["path"])
        deck["saved"] = True
    elif command == "slide":
        print(deck["slide"])
    elif command == "close":
        log[-1].append(digest(deck["path"]))
        decks.remove(deck)
    elif command == "goto":
        deck["slide"] = int(rest[1])
    return 0


def answer(program: str, args: list[str]) -> int:
    """Read the state, do the command, and write the state back when there is a file for it."""
    kept = Path(os.environ.get("LAB_DECK_STANDIN", ""))
    state = {"running": False, "decks": [], "refuse": [], "log": []}
    if kept.is_file():
        state |= json.loads(kept.read_text(encoding="utf-8"))
    status = act(state, program, args)
    if kept.is_file():
        kept.write_text(json.dumps(state), encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(answer(sys.argv[1], sys.argv[2:]))
