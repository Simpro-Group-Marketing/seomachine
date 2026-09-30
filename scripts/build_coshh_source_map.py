"""Derive claim-bound Source Map rows for the COSHH rewrite from the live sources.

For every source_support claim candidate in the article, pick the authority URL
the claim relies on, fetch that page with the guard's own retrieval, and select
the source sentence with the highest significant-word overlap. A row is emitted
only when the overlap meets the guard's claim-fit threshold, so the Evidence is
a verbatim, visible snippet that directly carries the claim. Candidates that no
source sentence supports well enough are printed for rewording, never forced.

Writes research/source-map-rows-coshh-regulations-2026-09-24.json, which the
sidecar builder renders. Also writes local capture artifacts and receipts for
each fetched authority page so a transient network timeout falls back to the
captured text.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.proof_link_policy import analyze_proof_links
from data_sources.modules.source_support import orchestration as orch
from data_sources.modules.source_support.persistence import write_source_capture_receipt
from data_sources.modules.source_support.retrieval import fetch_source_text
from data_sources.modules.source_support.claim_matching import _evidence_contradicts_claim
from data_sources.modules.source_support.text_matching import _contains_evidence, _significant_words

SLUG = "coshh-regulations"
DATE = "2026-09-24"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-{DATE}.md"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
OUT = ROOT / "research" / f"source-map-rows-{SLUG}-{DATE}.json"
CAPTURE_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"
L = "https://www.legislation.gov.uk/uksi/2002/2677/"
OWNED_OR_PROOF_HOSTS = ("bigchange.com", "capterra.co.uk", "youtube.com")

# Extra authority pages to try for a claim, keyed by a phrase in the claim.
# The paragraph's own authority links are always tried first.
EXTRA_URLS = (
    ("Control of Substances Hazardous to Health Regulations 2002", [L + "regulation/7", L + "contents"]),
    ("apply to every employer", ["https://www.hse.gov.uk/coshh/law.htm"]),
    ("Regulation | Duty", [L + "contents"]),
    ("Question it answers", [L + "contents"]),
    ("Which controls fit", [L + "regulation/7"]),
    ("Which hazards face", [L + "regulation/6"]),
    ("real task", [L + "regulation/6"]),
    ("weighs the level", [L + "regulation/6"]),
    ("5 or more employees", [L + "regulation/6", "https://www.hse.gov.uk/coshh/basics/assessment.htm"]),
    ("Every employee makes full", [L + "regulation/8"]),
    ("every employee makes full", [L + "regulation/8"]),
)
PROOF_LINK_HOSTS = ("bigchange.com/success-stories", "capterra.co.uk")


def plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "")
    return re.sub(r"\s+", " ", text).strip().strip("|").strip()


def fetch(url: str, cache: dict[str, str]) -> str:
    if url not in cache:
        for attempt in range(4):
            try:
                cache[url] = fetch_source_text(url)
                break
            except Exception as error:  # noqa: BLE001 - retry transient network errors
                print(f"retry {attempt + 1} {url}: {type(error).__name__}")
                time.sleep(4)
        else:
            raise RuntimeError(f"could not fetch {url}")
    return cache[url]


def numeric_tokens(text: str) -> frozenset[str]:
    from data_sources.modules.source_support.common import (
        _claim_text_for_detection, _extract_numeric_tokens, _normalize_numeric_token,
    )
    return frozenset(_normalize_numeric_token(t) for t in _extract_numeric_tokens(_claim_text_for_detection(text)))


def best_window(claim: str, source_text: str, needed_numbers: frozenset[str]) -> tuple[str, int, int]:
    """Return the shortest source window meeting the claim-fit threshold."""
    claim_words = _significant_words(claim)
    needed = max(3, math.ceil(len(claim_words) * 0.5))
    spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", source_text)]
    word_sig = [_significant_words(source_text[a:b]) for a, b in spans]
    best, best_key = "", None
    best_overlap = -1
    for i in range(len(spans)):
        if not (word_sig[i] & claim_words):
            continue
        seen: set[str] = set()
        for j in range(i, len(spans)):
            if spans[j][1] - spans[i][0] > 1200:
                break
            seen |= word_sig[j] & claim_words
            overlap = len(seen)
            best_overlap = max(best_overlap, overlap)
            if overlap < needed:
                continue
            window = source_text[spans[i][0]:spans[j][1]]
            if needed_numbers and not needed_numbers <= numeric_tokens(window):
                continue
            if _evidence_contradicts_claim(claim, window):
                continue
            key = (len(window), -overlap)
            if best_key is None or key < best_key:
                best, best_key = window, key
            break
    return best, (needed if best else best_overlap), needed


def capture(url: str, text: str) -> tuple[str, str]:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    key = "authority-" + re.sub(r"[^a-z0-9]+", "-", url.lower().split("://", 1)[1]).strip("-")[:90]
    src = CAPTURE_DIR / f"{key}.fetched.txt"
    art = CAPTURE_DIR / f"{key}.md"
    src.write_bytes(text.encode("utf-8"))
    art.write_bytes(text.encode("utf-8"))
    rec = CAPTURE_DIR / f"{key}-capture-receipt.json"
    write_source_capture_receipt(
        rec, source_url=url, source_content_path=src, artifact_path=art,
        artifact_reference=art.relative_to(ROOT).as_posix(), method="html_visible_text",
        workspace_root=ROOT,
    )
    return art.relative_to(ROOT).as_posix(), rec.relative_to(ROOT).as_posix()


def _is_risk_bearing(sentence: str) -> bool:
    from data_sources.modules.proof_link_policy import INFERRED_HIGH_RISK_RE, STRICT_PUBLIC_RISK_RE
    return bool(INFERRED_HIGH_RISK_RE.search(sentence) or STRICT_PUBLIC_RISK_RE.search(sentence) or re.search(r"\d", sentence))


def _full_sentence(fragment: str, line_text: str) -> str:
    """Map a residual fragment back to the full article sentence that contains it."""
    if "|" in line_text:
        return fragment
    sentences = re.split(r"(?<=[.!?])\s+", plain(line_text))
    return next((f.strip() for f in sentences if fragment.rstrip(".") in f), fragment)


def expand_candidates(candidates, lines: list[str]) -> list[tuple[object, str]]:
    expanded = []
    for cand in candidates:
        text = plain(cand.text)
        if cand.claim_type:
            expanded.append((cand, text))
            continue
        # Policy residuals can span a whole paragraph: map each risk-bearing sentence.
        pieces = text.split("|") if "|" in text else re.split(r"(?<=[.!?])\s+", text)
        for sentence in (p.strip() for p in pieces):
            if not sentence or re.fullmatch(r"(?:Reg|Schedule) \w+", sentence):
                continue  # a bare table label carries no claim
            if _is_risk_bearing(sentence):
                expanded.append((cand, _full_sentence(sentence, lines[cand.line - 1]).rstrip(".")))
    return expanded


def authority_urls(claim: str, line_text: str) -> list[str]:
    urls = [u for u in re.findall(r"\]\((https?://[^)]+)\)", line_text) if not any(h in u for h in OWNED_OR_PROOF_HOSTS)]
    for phrase, extra in EXTRA_URLS:
        if phrase in claim or phrase in line_text:
            urls.extend(u for u in extra if u not in urls)
    return urls


def select_evidence(claim: str, urls: list[str], cache: dict[str, str]) -> tuple[tuple[str, str] | None, str]:
    """Return (url, window) from the first URL that supports the claim, else a miss note."""
    needed_numbers = numeric_tokens(claim)
    note = ""
    for url in urls:  # the paragraph's own authority link first
        source_text = fetch(url, cache)
        window, overlap, needed = best_window(claim, source_text, needed_numbers)
        if window and "|" not in window and overlap >= needed and _contains_evidence(source_text, window):
            return (url, window), ""
        note = f"best overlap {overlap}/{needed} at {url}: {window[:140]}"
    return None, note


def drop_nested(rows: list[dict]) -> list[dict]:
    # A row whose claim sits inside a longer row on the same line would be subtracted
    # first by the proof-link policy and strand the rest of the sentence.
    return [
        r for r in rows
        if not any(o is not r and o["line"] == r["line"] and r["claim"] in o["claim"] and len(o["claim"]) > len(r["claim"]) for o in rows)
    ]


def build_rows(expanded, lines: list[str], cache: dict[str, str]) -> tuple[list[dict], list[tuple]]:
    rows, unsupported = [], []
    seen_claims: set[str] = set()
    for cand, claim in expanded:
        line_text = lines[cand.line - 1]
        if any(h in line_text for h in PROOF_LINK_HOSTS):
            continue  # customer and review proof rows are authored by hand
        urls = authority_urls(claim, line_text)
        if not urls:
            unsupported.append((cand.line, cand.claim_type, claim, "no authority URL"))
            continue
        if claim in seen_claims:
            continue
        best, note = select_evidence(claim, urls, cache)
        if best is None:
            unsupported.append((cand.line, cand.claim_type, claim, note))
            continue
        seen_claims.add(claim)
        rows.append({
            "line": cand.line, "claim": claim, "claim_type": cand.claim_type or "factual",
            "url": best[0], "evidence": best[1], "numeric": sorted(numeric_tokens(claim)),
        })
    return drop_nested(rows), unsupported


def main() -> int:
    article = ARTICLE.read_bytes().decode("utf-8")
    sidecar = SIDECAR.read_bytes().decode("utf-8")
    proof_source = orch.compose_with_sidecar(article, sidecar)
    entries = orch._extract_proof_entries(proof_source)
    policy = analyze_proof_links(article, proof_source)
    candidates = orch._extract_claim_candidates(article, orch._known_customer_names(entries))
    candidates = orch._policy_aligned_candidates(candidates, policy)
    lines = article.splitlines()

    cache: dict[str, str] = {}
    rows, unsupported = build_rows(expand_candidates(candidates, lines), lines, cache)
    captures = {url: capture(url, text) for url, text in cache.items()}
    for row in rows:
        row["artifact"], row["receipt"] = captures[row["url"]]
    OUT.write_bytes(json.dumps({"rows": rows, "unsupported": unsupported}, indent=1, ensure_ascii=False).encode("utf-8"))
    print(f"rows={len(rows)} unsupported={len(unsupported)} -> {OUT.relative_to(ROOT).as_posix()}")
    for item in unsupported:
        print("UNSUPPORTED", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
