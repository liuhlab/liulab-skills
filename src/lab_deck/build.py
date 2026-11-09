"""Build the deck: hand the folder to Node, and replace the deck file in one step.

Python reads the deck folder and writes one JSON job. `runner.js`, beside this file, runs each
slide source against PptxGenJS and writes one file per slide into a scratch folder inside the
deck folder. `merge.py` puts those files together and checks the result. Only a finished,
checked file is moved over the last built deck, so a failed build leaves that deck as it was.

PptxGenJS is a conda-forge package in the pixi environment, at `lib/node_modules` under the
environment's prefix. Node does not search that folder by itself, so `NODE_PATH` names it for
the one process this module starts. No `npm install` runs anywhere.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lab_deck import merge
from lab_deck.folder import ROOMS, Folder, Refusal

RUNNER = Path(__file__).with_name("runner.js")
# Where a conda package of a Node library lands, under the environment's prefix.
NODE_MODULES = Path(sys.prefix) / "lib" / "node_modules"
# Sizes that do not depend on the room, in points.
TITLE = 32
CITATION = 12


def node() -> str:
    """Find the Node.js of this environment, or the one on PATH.

    Raises
    ------
    Refusal
        When there is no Node.js to run.
    """
    beside = Path(sys.prefix) / "bin" / "node"
    found = str(beside) if beside.is_file() else shutil.which("node")
    if found is None:
        raise Refusal("Node.js was not found; run lab-deck through its pixi environment.")
    return found


def job(folder: Folder, scratch: Path) -> dict[str, object]:
    """Describe one build for `runner.js`: what to draw, how it looks, where to write it.

    Each slide is written to a file of its own in `scratch`. The page number is the slide's
    place in the deck; the first slide is the title and carries none.
    """
    return {
        "title": folder.title,
        "pictures": str(folder.path / "pictures"),
        "theme": {"font": folder.font, "accent": folder.accent},
        "size": {"title": TITLE, "citation": CITATION, **ROOMS[folder.room]},
        "slides": [
            {
                "id": slide,
                "source": str(folder.source(slide)),
                "output": str(scratch / f"{slide}.pptx"),
                "page": None if place == 1 else place,
            }
            for place, slide in enumerate(folder.slides, 1)
        ],
    }


def build(folder: Folder) -> Path:
    """Build the deck of `folder` and return the file written.

    Raises
    ------
    Refusal
        When a slide source fails, a slide cannot be merged, or the merged deck is not sound.
        The last built deck is untouched.
    """
    if not (NODE_MODULES / "pptxgenjs").is_dir():
        raise Refusal(f"PptxGenJS is not installed at {NODE_MODULES}; run `pixi install`.")
    # Inside the deck folder, so the final move stays on one filesystem and is one step.
    with tempfile.TemporaryDirectory(prefix=".lab-deck-", dir=folder.path) as scratch:
        work = Path(scratch)
        spec = work / "job.json"
        spec.write_text(json.dumps(job(folder, work)), encoding="utf-8")
        done = subprocess.run(
            [node(), str(RUNNER), str(spec)],
            cwd=folder.path,
            env={**os.environ, "NODE_PATH": str(NODE_MODULES)},
            capture_output=True,
            text=True,
            check=False,
        )
        slides = [work / f"{slide}.pptx" for slide in folder.slides]
        try:
            if done.returncode != 0 or not all(slide.is_file() for slide in slides):
                raise Refusal(done.stderr.strip() or done.stdout.strip() or "Node wrote no deck")
            for name, slide in zip(folder.slides, slides, strict=True):
                merge.repair(slide, name)
            # A name no slide can have, so the merged file never lands on a slide's own.
            written = work / "merged deck.pptx"
            merge.merge(slides, written)
            merge.check(written, len(slides))
        except Refusal as error:
            raise Refusal(
                f"the build failed, and {folder.output.name} was left as it was.\n{error}"
            ) from None
        written.replace(folder.output)
    return folder.output
