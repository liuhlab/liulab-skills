"""Say whether this machine can render a deck: LibreOffice, Poppler and the theme's font.

`lab-deck build` needs none of the three. `lab-deck render` needs the first two, and the
pictures match PowerPoint only when LibreOffice finds the font the slides name: it draws a
missing font with another, and the text then wraps at other places.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from lab_deck import render


@dataclass(frozen=True)
class Check:
    """One thing a render needs, as found on this machine."""

    name: str
    found: str | None
    """Where it is, or None when it is missing."""
    get: str
    """How to get it when it is missing."""


def fonts() -> set[str] | None:
    """Name every font family on this machine, in lower case, or None when none can be listed."""
    program = render.tool("fc-list")
    if program is None:
        return None
    done = subprocess.run(
        [program, "--format", "%{family}\n"], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        return None
    # A font with names in several languages lists them all on one line, with commas between.
    return {name.strip().lower() for line in done.stdout.splitlines() for name in line.split(",")}


def checks(font: str) -> list[Check]:
    """Check LibreOffice, Poppler and the font `font`."""
    families = fonts()
    return [
        Check(
            "LibreOffice",
            render.soffice(),
            "install it from https://www.libreoffice.org/download, or on a Mac with "
            "`brew install --cask libreoffice`. `lab-deck` looks for `soffice` on PATH, then "
            f"inside the Mac app; set {render.SOFFICE} to the program if it is elsewhere.",
        ),
        Check(
            "Poppler",
            render.tool("pdftoppm"),
            "it comes with the plugin's pixi environment: run `/lab-setup` again, or "
            "`pixi install` in the plugin folder.",
        ),
        Check(
            f"font {font}",
            "installed" if families is not None and font.lower() in families else None,
            "install the font on this machine, or set `font` in theme.toml to a font that is "
            "installed. LibreOffice draws a missing font with another one, so the pictures "
            "would not match PowerPoint."
            if families is not None
            else "the fonts could not be listed, because fontconfig's fc-list is missing: run "
            "`pixi install` in the plugin folder.",
        ),
    ]


def text(found: list[Check]) -> str:
    """Spell the checks: one line each, present or missing, and how to get a missing one."""
    lines = []
    for check in found:
        if check.found is not None:
            lines.append(f"present: {check.name} ({check.found})")
        else:
            lines.append(f"missing: {check.name}. To get it: {check.get}")
    return "\n".join(lines)
