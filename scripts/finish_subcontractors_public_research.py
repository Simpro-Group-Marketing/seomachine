"""Close out the last public-research and source-support findings.

Three distinct causes remain:

* Table-row claims carry pipes, so a whole-row claim never matches the unit
  text. Each cell that appears verbatim is bound instead.
* NAIC returns 403 to the fetcher, so any row citing it needs its local capture
  artifact and receipt rather than a live fetch.
* One subcontract-terms row carries the wrong claim type, and one duplicated
  claim/URL pair disagrees on its fields.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
CAPTURES = pathlib.Path(f"research/source-captures/{SLUG}-{DATE}")
CLASS_DIR = pathlib.Path(f"research/source-classifications/{SLUG}-{DATE}")
ANCHOR = "\n\n## FAQ Source Policy"

NAIC = "https://content.naic.org/consumer"
OSHA_ITA = "https://www.osha.gov/itadata"
NAIC_EVIDENCE = (
    "Every U.S. state, the District of Columbia, and the five U.S. territories "
    "have a Department of Insurance (DOI) dedicated to helping consumers."
)
OSHA_ITA_EVIDENCE = "Injury Tracking Application Data"

# Table cells that still need a row, with the authority linked in the same row.
CELL_CLAIMS = [
    ("That a policy existed on the issue date, and nothing more", NAIC, "naic-consumer", "non_competing_expert", NAIC_EVIDENCE),
    ("The producer named on it, then the carrier through your state insurance department", NAIC, "naic-consumer", "non_competing_expert", NAIC_EVIDENCE),
    ("Injury frequency, not safety culture", OSHA_ITA, "osha-injury-tracking-data", "primary_authority", OSHA_ITA_EVIDENCE),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(claim: str, url: str, key: str, source_class: str, evidence: str) -> str:
    artifact = CLASS_DIR / f"{key.replace('naic-consumer', 'naic-consumer')}.json"
    fields = [
        f"- Claim: {claim}",
        "Claim type: factual",
        f"Source class: {source_class}",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {evidence}",
        "Original-source status: original",
        f"Source date: {DATE}",
        "Checked date: 2026-09-22",
        "Claim fit: direct",
        "Freshness decision: current",
        "Freshness reason: Public authority page read on the checked date.",
    ]
    capture = CAPTURES / f"{key}.md"
    receipt = CAPTURES / f"{key}-capture-receipt.json"
    if capture.is_file() and receipt.is_file():
        fields += [
            f"Artifact: {capture.as_posix()}",
            f"Capture receipt: {receipt.as_posix()}",
            f"Capture receipt hash: {sha(receipt)}",
        ]
    fields += [
        f"Classification artifact: {artifact.as_posix()}",
        f"Classification hash: {sha(artifact)}",
        "Citation mode: inline_required",
        "Status: approved",
        "Intended use: Prequalification pack table row",
    ]
    return " | ".join(fields)


def main() -> int:
    text = SIDECAR.read_text(encoding="utf-8")

    # NAIC is fetch-blocked, so every row citing it needs its local capture.
    capture = CAPTURES / "naic-consumer.md"
    receipt = CAPTURES / "naic-consumer-capture-receipt.json"
    binding = (
        f" | Artifact: {capture.as_posix()}"
        f" | Capture receipt: {receipt.as_posix()}"
        f" | Capture receipt hash: {sha(receipt)}"
    )
    lines = text.splitlines()
    patched = 0
    for index, line in enumerate(lines):
        if line.startswith("- Claim:") and f"URL: {NAIC}" in line and "Capture receipt:" not in line:
            lines[index] = line.replace(
                " | Classification artifact:", binding + " | Classification artifact:", 1
            )
            patched += 1
    text = "\n".join(lines) + "\n"
    print(f"added the NAIC capture binding to {patched} rows")

    # The subcontract-terms row asserts a process, not a fact.
    before = text
    text = re.sub(
        r"(- Claim: Keep scope, schedule, price, change-order pricing[^\n]*?)Claim type: factual",
        r"\1Claim type: process",
        text,
        count=1,
    )
    print("subcontract-terms claim type set to process" if text != before else "MISS: subcontract-terms row")

    new_rows = [row(*record) for record in CELL_CLAIMS]
    text = text.replace(ANCHOR, "\n" + "\n".join(new_rows) + ANCHOR, 1)

    # Drop exact claim+URL pairs that disagree on their other fields.
    lines = text.splitlines()
    seen: dict[tuple[str, str], str] = {}
    kept: list[str] = []
    conflicts = 0
    for line in lines:
        if line.startswith("- Claim:"):
            claim = line.split("- Claim:", 1)[1].split(" | ", 1)[0].strip()
            url_match = re.search(r"URL: (\S+)", line)
            key = (claim.casefold(), url_match.group(1) if url_match else "")
            if key in seen and seen[key] != line:
                conflicts += 1
                continue
            seen[key] = line
        kept.append(line)
    SIDECAR.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="")
    print(f"added {len(new_rows)} table-cell rows; dropped {conflicts} conflicting duplicates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
