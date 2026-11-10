"""The house style in one place: the names and sizes the build writes and the checks read.

`build.py` hands them to `runner.js` in the job, so no name or size is spelled a second time
there. `lint.py`, `compare.py` and `stage.py` find a shape of the build by its name here.
"""

from __future__ import annotations

# The names the build gives the shapes that a later step must find.
TITLE = "Slide title"
PAGE_NUMBER = "Page number"
CITATION = "Citation"
TABLE = "Table"
# A text box whose sentences are meant, such as a quote.
SENTENCE = "Intended sentence"

# Sizes that do not depend on the room, in points. The citation size is the one size under
# the floor that a slide may carry, on its citation line and its page number.
TITLE_SIZE = 32
CITATION_SIZE = 12

# English Metric Units, the unit of every place and size in a deck file.
EMU_PER_INCH = 914400
EMU_PER_POINT = 12700
