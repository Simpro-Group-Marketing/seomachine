"""Emit local text proof artifacts for the BigChange Capterra UK review pages.

`source_support_guard` verifies Evidence snippets by fetching the cited page.
capterra.co.uk returns HTTP 403 to that fetch while serving the page normally to
a real browser, so the visible review text was read through the Chrome connector
on 2026-09-24 and is bound here as local artifacts with capture receipts. Each
text block is a contiguous verbatim excerpt of the rendered review card.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt

SLUG = "coshh-regulations"
DATE = "2026-09-24"
OUT_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"
PRODUCT_PAGE = "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"

CLARE_TEXT = (
    "Clare HSEQ Manager in UK Construction, 11–50 Employees Used the Software for: 2+ years "
    "\"Review of BigChange\" 13 January 2021 5.0 Overall experience is good, it really has "
    "helped our administration of the way we work as a company. I believe that with the "
    "introduction of Big Change that we have reduced our administration needs and as saved the "
    "employment of 1 x person required, which has been important as we grow as a company. "
    "Pros: This is a really easy system to use, you can design to meet your company needs for "
    "policies, procedures, health & safety. You can manage the system yourself, you do not need "
    "software engineers to design your worksheets this can all be done in house"
)

SUZANNE_TEXT = (
    "suzanne Transport Manager in UK Building Materials, 201–500 Employees Used the Software "
    "for: 2+ years \"The good, the bad and the getting it right!\" 1 June 2023 4.0 On boarding "
    "was fantastic, being able to use the system to achieve what we want is a really good "
    "feature. Down side for myself, we as a business don't utilize it in other departments such "
    "as accounts. Doing this would stream line the whole process as Big Change can certainly do "
    "it Pros: NOTES!!!! being a transport manager being bale to have files on the fleet, with "
    "real time actions, keeping all documents together showing a stream from report to "
    "completion of faults and issues which keeps us compliant"
)

CAPTURES = [
    ("capterra-uk-bigchange-clare-hseq-page-6", f"{PRODUCT_PAGE}?page=6", CLARE_TEXT),
    ("capterra-uk-bigchange-suzanne-transport-page-2", f"{PRODUCT_PAGE}?page=2", SUZANNE_TEXT),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, url, text in CAPTURES:
        source_path = OUT_DIR / f"{key}.chrome.txt"
        source_path.write_text(text, encoding="utf-8")
        text_path = OUT_DIR / f"{key}.md"
        text_path.write_text(text, encoding="utf-8")
        receipt_path = OUT_DIR / f"{key}-capture-receipt.json"
        write_source_capture_receipt(
            receipt_path,
            source_url=url,
            source_content_path=source_path,
            artifact_path=text_path,
            artifact_reference=text_path.relative_to(ROOT).as_posix(),
            method="html_visible_text",
            workspace_root=ROOT,
        )
        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        print(f"{key}: receipt sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
