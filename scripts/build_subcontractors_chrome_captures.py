"""Emit local text proof artifacts for sources that refuse automated fetching.

`source_support_guard` verifies an Evidence snippet by fetching the cited page.
dol.gov and content.naic.org return HTTP 403 to that fetch while serving the
page normally to a real browser, so the visible text is captured through the
Chrome connector and bound as a local artifact with a capture receipt. The text
below is what the connector read back on 2026-09-18.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
OUT_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"

NAIC_TEXT = (
    "Home Consumer Discover tools and resources to help you understand different types of "
    "insurance, claims processes, and practical tips to help support you through every stage "
    "of your life. How Does Insurance Work? It can cost a lot of money to recover from "
    "disasters and medical emergencies. Insurance helps you avoid paying the entire cost of "
    "treatment, services, repairs, and rebuilds on your own. Learn More About Insurance Your "
    "Insurance Department Is Here for You Every U.S. state, the District of Columbia, and the "
    "five U.S. territories have a Department of Insurance (DOI) dedicated to helping consumers. "
    "Get Insurance Help Types of Insurance Browse different insurance types to understand your "
    "options and potential risks Homeowners Learn more Life & Annuities Learn more Auto Learn "
    "more Health Learn more Flood Learn more Military Learn more Small Business Learn more "
    "Long-Term Care Learn more Sharing Economy Learn more Cybersecurity Learn more File a "
    "Complaint Having a problem with an insurer."
)

DOL_FS13_TEXT = (
    "Whether a worker is an employee or an independent contractor under the FLSA is determined "
    "by looking at the economic realities of the worker's relationship with the employer. If the "
    "economic realities show that the worker is economically dependent on the employer for work, "
    "then the worker is an employee. If the economic realities show that the worker is in business "
    "for themself, then the worker is an independent contractor. The economic realities of the "
    "entire working relationship are looked at to decide whether a worker is an employee or an "
    "independent contractor. Employment under the FLSA is not determined by technical concepts or "
    "common law standards of control; it is broader than the common law standard often applied to "
    "determine employment status under other Federal laws. What Is the Economic Reality Test? The "
    "economic reality test uses multiple factors to see if an employment relationship exists under "
    "the FLSA (29 CFR 795.110). The goal of the test is to decide if the worker is economically "
    "dependent on the employer for work."
)

CAPTURES = [
    ("naic-consumer", "https://content.naic.org/consumer", NAIC_TEXT),
    (
        "dol-fact-sheet-13",
        "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship",
        DOL_FS13_TEXT,
    ),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, url, text in CAPTURES:
        # The connector returns rendered visible text, so that text is both the
        # captured input and the extracted artifact.
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
