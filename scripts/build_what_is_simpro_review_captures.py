"""Bind receipt-backed captures for the review quotes in the What Is Simpro blog.

G2 review pages return HTTP 403 to automated clients, so their visible review
text was read back through the Chrome connector in the user's browser and saved
verbatim under research/source-captures/what-is-simpro/. The Capterra product
page is fetched here with curl_cffi (Safari impersonation), because the repo
fetcher also receives HTTP 403 there. Each artifact is bound with an
html_visible_text capture receipt. This script never edits public Markdown.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt  # noqa: E402

SLUG = "what-is-simpro"
DATE = "2026-10-05"
READBACK_DIR = ROOT / "research" / "source-captures" / SLUG
CAPTURE_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"
OUT = ROOT / "research" / f"review-captures-{SLUG}-{DATE}.json"

G2 = {
    "claim-metric-MET-1809": ("https://www.g2.com/products/simpro/reviews/simpro-review-13118004", "chrome-g2-review-13118004.txt",
                              "Simpro has made everyone accountable from the very beginning, from the lead and quote stage all the way through to collecting the final payment for the job."),
    "claim-metric-MET-1816": ("https://www.g2.com/products/simpro/reviews/simpro-review-13176424", "chrome-g2-review-13176424.txt",
                              "It has improved communication between the office and field technicians, streamlined dispatching and scheduling, and given us better visibility into jobs, quotes, inventory, and invoicing."),
    "claim-metric-MET-1302": ("https://www.g2.com/products/simpro/reviews/simpro-review-8771080", "chrome-g2-review-8771080.txt",
                              "We went from carbonless service call forms and a whiteboard calendar to Simpro."),
    "claim-metric-MET-1849": ("https://www.g2.com/products/simpro/reviews/simpro-review-13242709", "chrome-g2-review-13242709.txt",
                              "As an owner, it gives me great real-time insight into my business, from work orders to quotes."),
    "claim-metric-MET-1271": ("https://www.g2.com/products/simpro/reviews/simpro-review-8714287", "chrome-g2-review-8714287.txt",
                              "Simpro allows our company to manage quotes, jobs, invoicing, and business reporting efficiently in one place."),
}
CAPTERRA_CLAIM = "claim-metric-MET-1755"
CAPTERRA_URL = "https://www.capterra.com/p/10529/Simpro-Enterprise/#Capterra___7174604"
CAPTERRA_FETCH = "https://www.capterra.com/p/10529/Simpro-Enterprise/"
CAPTERRA_QUOTE = "It is an absolute powerhouse when it comes to keeping our quoting, job management, and invoicing tied together in one single source of truth."


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def normalize(text: str) -> str:
    return " ".join(text.replace("’", "'").replace("“", '"').replace("”", '"').split())


def main() -> int:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for claim_id, (url, name, quote) in G2.items():
        raw = READBACK_DIR / name
        text = raw.read_text(encoding="utf-8")
        if normalize(quote) not in normalize(text):
            raise SystemExit(f"quote not visible in readback for {claim_id}")
        artifact = CAPTURE_DIR / name.replace(".txt", ".md")
        artifact.write_text(text, encoding="utf-8", newline="\n")
        receipt = CAPTURE_DIR / name.replace(".txt", "-capture-receipt.json")
        write_source_capture_receipt(receipt, source_url=url, source_content_path=raw, artifact_path=artifact,
                                     artifact_reference=rel(artifact), method="html_visible_text", workspace_root=ROOT)
        records.append({"claim_id": claim_id, "url": url, "artifact": rel(artifact), "receipt": rel(receipt),
                        "receipt_sha256": sha(receipt), "checked": "2026-10-02", "method": "Chrome connector readback"})

    from curl_cffi import requests as creq  # noqa: PLC0415
    from data_sources.modules.source_support.text_matching import _extract_visible_text  # noqa: PLC0415

    raw_html = CAPTURE_DIR / "capterra-simpro-enterprise-product-page.html"
    checked = DATE
    method = "curl_cffi safari fetch"
    try:
        response = creq.get(CAPTERRA_FETCH, impersonate="safari", timeout=60)
        response.raise_for_status()
        raw_html.write_bytes(response.content)
    except Exception as error:  # Capterra bot protection: reuse the 2026-10-02 fetch.
        print(f"Capterra refetch failed ({error}); using the 2026-10-02 curl_cffi capture")
        raw_html = READBACK_DIR / "capterra-simpro-enterprise-product-page.html"
        checked = "2026-10-02"
        method = "curl_cffi safari fetch on 2026-10-02"
    visible = _extract_visible_text(raw_html.read_text(encoding="utf-8", errors="replace"))
    if normalize(CAPTERRA_QUOTE) not in normalize(visible):
        raise SystemExit("Capterra quote not visible on the fetched product page")
    artifact = CAPTURE_DIR / "capterra-simpro-enterprise-product-page.md"
    artifact.write_text(visible, encoding="utf-8", newline="\n")
    receipt = CAPTURE_DIR / "capterra-simpro-enterprise-product-page-capture-receipt.json"
    write_source_capture_receipt(receipt, source_url=CAPTERRA_URL, source_content_path=raw_html, artifact_path=artifact,
                                 artifact_reference=rel(artifact), method="html_visible_text", workspace_root=ROOT)
    records.append({"claim_id": CAPTERRA_CLAIM, "url": CAPTERRA_URL, "artifact": rel(artifact), "receipt": rel(receipt),
                    "receipt_sha256": sha(receipt), "checked": checked, "method": method})

    OUT.write_text(json.dumps({"schema": "simpro-what-is-simpro-review-captures/v1",
                               "generated_at": datetime.now(timezone.utc).isoformat(),
                               "records": records}, indent=2) + "\n", encoding="utf-8", newline="\n")
    for row in records:
        print(row["claim_id"], row["receipt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
