"""A stand-in for LibreOffice: `soffice --convert-to pdf --outdir <folder> <deck>`.

It writes a PDF with one page per slide that is not hidden, as LibreOffice does. A page
draws one box per shape on its slide, in a grey that follows the slide's text, so two slides
that differ give two different pictures and the same slide gives the same picture.

`STAND_IN_FAILS` in the environment makes it abort, as LibreOffice does inside a sandbox.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path


def pdf(pages: list[bytes]) -> bytes:
    """Write a PDF whose pages hold these drawing commands."""
    kids = " ".join(f"{3 + 2 * n} 0 R" for n in range(len(pages)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
    ]
    for n, content in enumerate(pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 960 540] "
            f"/Contents {4 + 2 * n} 0 R >>".encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n%b\nendstream" % (len(content), content))
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%b\nendobj\n" % (number, body)
    start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        start,
    )
    return out


def page(slide: str) -> bytes:
    """Draw one slide: a box per shape, in a grey its text decides."""
    words = "".join(re.findall(r"<a:t>([^<]*)</a:t>", slide))
    grey = hashlib.sha256(words.encode()).digest()[0] / 255
    boxes = [
        f"{grey:.3f} g {40 + 60 * (int(ident) % 14)} {60 + 50 * (int(ident) // 14 % 9)} 50 40 re f"
        for ident in re.findall(r'<p:cNvPr id="(\d+)"', slide)[1:]
    ]
    return "\n".join(boxes).encode()


def main() -> int:
    """Convert the deck named last on the command line."""
    if os.environ.get("STAND_IN_FAILS"):
        print("stand-in: Abort trap: 6", file=sys.stderr)
        return 134
    args = sys.argv[1:]
    deck = Path(args[-1])
    out = Path(args[args.index("--outdir") + 1])
    with zipfile.ZipFile(deck) as archive:
        listed = re.findall(r"<p:sldId [^>]*/>", archive.read("ppt/presentation.xml").decode())
        slides = [
            archive.read(f"ppt/slides/slide{n}.xml").decode() for n in range(1, len(listed) + 1)
        ]
    shown = [slide for slide in slides if not re.search(r'<p:sld\b[^>]*\sshow="0"', slide)]
    (out / f"{deck.stem}.pdf").write_bytes(pdf([page(slide) for slide in shown]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
