"""What every test folder shares: the stub programs a test puts on PATH, written once a run.

A Mac's malware check reads a program the first time it runs, one program at a time for the
whole machine. A stub that each test wrote for itself was a new program every time, so each
such test waited its turn, and under `pytest -n auto` the queue pushed tests past the 2 s
limit. `program` writes each distinct stub once for the run and gives a test a link to it,
under the name it needs, in a folder of its own. Running the link runs a program the check
has already read. Linux has no such check, so there the link only saves a write.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path

import pytest

#: The run's folder of stubs, set by `_programs` before any test runs.
STORE: list[Path] = []


@pytest.fixture(autouse=True, scope="session")
def _programs(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Make the folder `program` keeps its stubs in, one for every worker of the run."""
    base = tmp_path_factory.getbasetemp()
    # Under xdist each worker's base folder sits inside the run's; with one process it is the run's.
    store = (base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base) / "programs"
    store.mkdir(exist_ok=True)
    STORE[:] = [store]


def program(folder: Path, name: str, text: str) -> Path:
    """Put the program `text` in `folder` as `name`, a link to the run's one copy of it.

    The copy is read-only, so a test that writes to the link fails rather than changing the
    program under every other test. To give one test another program, write another text.
    """
    (store,) = STORE
    kept = store / hashlib.sha256(text.encode()).hexdigest()[:16]
    if not kept.exists():
        draft = store / f"{kept.name}.{os.getpid()}"
        draft.write_text(text, encoding="utf-8")
        draft.chmod(0o555)
        # A link, not a rename: the first worker's copy stays, so no worker runs a second one.
        with contextlib.suppress(FileExistsError):
            kept.hardlink_to(draft)
        draft.unlink()
    link = folder / name
    link.symlink_to(kept)
    return link
