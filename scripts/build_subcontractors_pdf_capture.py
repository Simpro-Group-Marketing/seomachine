"""Emit local text proof artifacts and capture receipts for the two PDF sources.

`source_support_guard` requires a local extracted-text artifact plus an attested
capture receipt for any PDF source. Both PDFs are downloaded fresh here so the
receipt binds the exact bytes the text was extracted from.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
OUT_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SOURCES = [
    (
        "agc-2026-workforce-survey",
        "https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20(4).pdf",
    ),
    (
        "ncci-abcs-of-experience-rating",
        "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf",
    ),
]


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    pages = PdfReader(str(path)).pages
    text = "\n".join((page.extract_text() or "") for page in pages)
    # Normalise curly punctuation and collapse the PDF's hard line wrapping so a
    # sentence-level evidence snippet in the sidecar matches the artifact text.
    for curly, plain in (
        ("’", "'"),
        ("‘", "'"),
        ("“", '"'),
        ("”", '"'),
        ("–", "-"),
        ("—", "-"),
    ):
        text = text.replace(curly, plain)
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, url in SOURCES:
        pdf_path = OUT_DIR / f"{key}.pdf"
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=60) as response:
            pdf_path.write_bytes(response.read())

        text_path = OUT_DIR / f"{key}.md"
        text_path.write_text(extract_pdf_text(pdf_path), encoding="utf-8")

        receipt_path = OUT_DIR / f"{key}-capture-receipt.json"
        write_source_capture_receipt(
            receipt_path,
            source_url=url,
            source_content_path=pdf_path,
            artifact_path=text_path,
            artifact_reference=text_path.relative_to(ROOT).as_posix(),
            method="pdf_text",
            workspace_root=ROOT,
        )
        import hashlib

        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        print(f"{key}")
        print(f"  artifact        : {text_path.relative_to(ROOT).as_posix()}")
        print(f"  capture receipt : {receipt_path.relative_to(ROOT).as_posix()}")
        print(f"  receipt sha256  : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
