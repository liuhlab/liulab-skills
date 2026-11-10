"""The command line: one typer app, one job per command.

The exit codes are 0 fine, 1 refused, 2 usage, as `edison-cli` has them. A warning goes to
stderr and changes no exit code.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from lab_deck import build as builder
from lab_deck import compare as comparer
from lab_deck import folder as folders
from lab_deck import lint as linter
from lab_deck.folder import Refusal

HELP = """\
Build a slide deck from a deck folder. The folder holds content only: the audience brief, the
slide order, one source file per slide, pictures, notes and the theme.
"""

# Plain click help, for the reason `edison-cli` gives: this lands in an agent's transcript.
app = typer.Typer(
    name="lab-deck",
    help=HELP,
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


def _refuse(error: Refusal) -> typer.Exit:
    """Print a refusal as the command's last word and give the exit that goes with it."""
    print(f"lab-deck: {error}", file=sys.stderr)
    return typer.Exit(1)


@app.command()
def new(
    folder: Annotated[Path, typer.Argument(help="the deck folder to make")],
    title: Annotated[str | None, typer.Option("--title", help="the deck's title")] = None,
) -> None:
    """Make a deck folder with one starter slide and a local git repo."""
    try:
        made = folders.new(folder, title)
    except Refusal as error:
        raise _refuse(error) from None
    print(f"made {made.path}")
    print(f"next: edit {folders.BRIEF} and slides/title.js, then run `lab-deck build`")
    part = folders.synced(made.path)
    if part is not None:
        print(
            f"lab-deck: warning: this folder is inside a synced cloud folder ({part}). "
            "A sync client and git can each rewrite the other's files. "
            "Move the folder if that matters to you; nothing was changed for it.",
            file=sys.stderr,
        )


@app.command()
def build(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
) -> None:
    """Build the deck folder into its PowerPoint file, replacing the last build in one step."""
    try:
        read = folders.read(folder)
        written = builder.build(read)
    except Refusal as error:
        raise _refuse(error) from None
    count = len(read.slides)
    print(f"built {written}: {count} slide{'' if count == 1 else 's'}")


@app.command()
def lint(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
) -> None:
    """Check the built deck in plain code, with no model. Exit 1 on a blocking failure."""
    try:
        read = folders.read(folder)
        report = linter.lint(read.output, read.room)
    except Refusal as error:
        raise _refuse(error) from None
    print(linter.render(report, read.output.name))
    if report.blocking:
        raise typer.Exit(1)


@app.command()
def compare(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
    since: Annotated[
        str | None,
        typer.Option("--since", help="the commit of the last build, when it is not found"),
    ] = None,
) -> None:
    """List the hand edits in the deck since its last build. Reports only; changes no file."""
    try:
        read = folders.read(folder)
        report = comparer.compare(read, since)
    except Refusal as error:
        raise _refuse(error) from None
    print(comparer.render(report, read.output.name))


def main() -> None:
    """Run the command line. `prog_name` is pinned so every way in prints the same name."""
    app(prog_name="lab-deck")
