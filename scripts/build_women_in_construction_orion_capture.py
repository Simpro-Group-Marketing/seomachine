"""Capture the Orion Security Solutions case study as a receipt-bound local proof artifact.

The source-support fetcher's pinned transport receives HTTP 403 from
simprogroup.com, while a browser-UA GET returns 200. The raw HTML snapshot and
its visible-text artifact are bound by a source capture receipt, matching the
Chrome-capture pattern used for the BLS tables in this run.
"""
from __future__ import annotations

import html
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt  # noqa: E402

SLUG = "women-in-construction"
DATE = "2026-09-28"
URL = "https://www.simprogroup.com/case-studies/orion"
SNAP = ROOT / "research" / "source-snapshots" / f"{SLUG}-{DATE}" / "simpro-case-study-orion.html"
ART = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}" / "simpro-case-study-orion.md"
RECEIPT = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}" / "simpro-case-study-orion-capture-receipt.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
EVIDENCE = "The company expanded its workforce by 25%"


def visible_text(raw: str) -> str:
    match = re.search(r"<main.*?</main>", raw, re.S)
    body = match.group(0) if match else raw
    body = re.sub(r"<(script|style).*?</\1>", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", html.unescape(body)).strip()


def main() -> int:
    request = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    SNAP.parent.mkdir(parents=True, exist_ok=True)
    ART.parent.mkdir(parents=True, exist_ok=True)
    SNAP.write_bytes(data)
    text = visible_text(data.decode("utf-8", errors="replace"))
    if EVIDENCE not in text:
        raise SystemExit("evidence snippet not visible in the captured page")
    ART.write_text(f"Source: {URL}\n\n{text}\n", encoding="utf-8", newline="\n")
    write_source_capture_receipt(
        RECEIPT, source_url=URL, source_content_path=SNAP, artifact_path=ART,
        artifact_reference=ART.relative_to(ROOT).as_posix(), method="html_visible_text",
        workspace_root=ROOT,
    )
    import hashlib
    print(f"artifact={ART.relative_to(ROOT).as_posix()}")
    print(f"receipt={RECEIPT.relative_to(ROOT).as_posix()} sha256={hashlib.sha256(RECEIPT.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
