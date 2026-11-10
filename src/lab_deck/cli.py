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
from lab_deck import powerpoint
from lab_deck import preflight as preflighter
from lab_deck import render as renderer
from lab_deck.folder import Refusal

CLOSED = "the user has saved and closed the deck; believe it when PowerPoint cannot be asked"

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
    closed: Annotated[bool, typer.Option("--closed", help=CLOSED)] = False,
) -> None:
    """Build the deck folder into its PowerPoint file, replacing the last build in one step.

    A deck open in PowerPoint is closed for the build and reopened at the same slide.
    """
    held = None
    try:
        read = folders.read(folder)
        held = powerpoint.close_for_build(read.output, closed)
        report = builder.build(read)
    except Refusal as error:
        if held is not None:
            # The build failed after the close: show the last built deck again.
            print(powerpoint.reopen(held))
        raise _refuse(error) from None
    count = len(read.slides)
    print(f"built {read.output}: {count} slide{'' if count == 1 else 's'}")
    if report.warnings:
        # A warning stops no build, and none passes in silence.
        print(linter.render(report, read.output.name))
    if held is not None:
        print(powerpoint.reopen(held, count))


@app.command()
def lint(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
) -> None:
    """Check the built deck in plain code, with no model. Exit 1 on a blocking failure.

    A warning is printed and leaves the exit at 0.
    """
    try:
        read = folders.read(folder)
        report = linter.lint(read.output, read.room, read.use, read.known_terms)
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
    closed: Annotated[bool, typer.Option("--closed", help=CLOSED)] = False,
) -> None:
    """List the hand edits in the deck since its last build. Reports only.

    It writes no file itself. A deck open in PowerPoint with unsaved changes is saved there
    first, so that the report reads them.
    """
    try:
        read = folders.read(folder)
        saved = powerpoint.save_if_unsaved(read.output, closed)
        report = comparer.compare(read, since)
    except Refusal as error:
        raise _refuse(error) from None
    if saved is not None:
        print(saved + "\n")
    print(comparer.render(report, read.output.name))


@app.command()
def render(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
) -> None:
    """Render every click state of the built deck to a picture, and list the changed ones."""
    try:
        report = renderer.render(folders.read(folder))
    except Refusal as error:
        raise _refuse(error) from None
    print(renderer.text(report))
    for slide in report.unshown:
        print(
            f"lab-deck: warning: slide {slide} has an effect other than Appear and Disappear. "
            "The pictures show the slide without it.",
            file=sys.stderr,
        )


@app.command()
def preflight(
    folder: Annotated[Path, typer.Argument(help="the deck folder (default: this one)")] = Path(),
) -> None:
    """Report LibreOffice, Poppler and the theme's font, each as present or missing."""
    try:
        # Outside a deck folder, check the font a new deck would have.
        inside = (folder / folders.ORDER).is_file()
        font = folders.read(folder).font if inside else folders.FONT
    except Refusal as error:
        raise _refuse(error) from None
    found = preflighter.checks(font)
    print(preflighter.text(found))
    if any(check.found is None for check in found):
        raise typer.Exit(1)


def main() -> None:
    """Run the command line. `prog_name` is pinned so every way in prints the same name."""
    app(prog_name="lab-deck")
