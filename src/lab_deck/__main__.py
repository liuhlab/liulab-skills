"""The entry point, reachable both as `lab-deck` and as `python -m lab_deck`.

`bin/lab-deck` execs the module form, for the reason `bin/edison-cli` gives.
"""

from __future__ import annotations

from lab_deck.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
