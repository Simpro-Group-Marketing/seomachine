"""Re-emit the AGC capture receipt against the percent-encoded cited URL.

The article links the survey with its parentheses percent-encoded so the
Markdown link parses, and the capture receipt has to bind that exact string.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

sys.path.insert(0, ".")

from data_sources.modules.source_support.persistence import write_source_capture_receipt

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ROOT = pathlib.Path(".").resolve()
CAPTURES = pathlib.Path(f"research/source-captures/{SLUG}-{DATE}")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
KEY = "agc-2026-workforce-survey"
CITED_URL = (
    "https://www.agc.org/sites/default/files/users/user21902/"
    "2026%20Workforce%20Survey%20Analysis%20%284%29.pdf"
)


def main() -> int:
    receipt = CAPTURES / f"{KEY}-capture-receipt.json"
    write_source_capture_receipt(
        receipt,
        source_url=CITED_URL,
        source_content_path=CAPTURES / f"{KEY}.pdf",
        artifact_path=CAPTURES / f"{KEY}.md",
        artifact_reference=(CAPTURES / f"{KEY}.md").as_posix(),
        method="pdf_text",
        workspace_root=ROOT,
    )
    digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
    text = SIDECAR.read_text(encoding="utf-8")
    text, count = re.subn(
        rf"(Capture receipt: {re.escape(receipt.as_posix())} \| Capture receipt hash: )[0-9a-f]{{64}}",
        rf"\g<1>{digest}",
        text,
    )
    SIDECAR.write_text(text, encoding="utf-8", newline="")
    print(f"AGC receipt rebound to the cited URL; {count} sidecar hashes updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
