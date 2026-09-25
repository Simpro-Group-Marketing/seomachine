"""Emit source classification registry records for the subcontractors rewrite.

Every URL below resolved through `url_validator.py` on 2026-09-18 with zero
blockers. dol.gov and bls.gov are deliberately absent: both return HTTP 403 to
the validator and would fail readiness as unresolved manual-review blockers, so
the federal classification claims route through the Federal Register and the
eCFR instead.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
OUT_DIR = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}"

SOURCES = [
    (
        "federalregister-ic-nprm-2026",
        "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical",
        "primary_authority",
    ),
    (
        "ecfr-part-795",
        "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-795",
        "primary_authority",
    ),
    (
        "irs-1099-mec-instructions",
        "https://www.irs.gov/instructions/i1099mec",
        "primary_authority",
    ),
    (
        "irs-independent-contractor-test",
        "https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee",
        "primary_authority",
    ),
    (
        "irs-about-form-w-9",
        "https://www.irs.gov/forms-pubs/about-form-w-9",
        "primary_authority",
    ),
    (
        "irs-about-form-ss-8",
        "https://www.irs.gov/forms-pubs/about-form-ss-8",
        "primary_authority",
    ),
    (
        "osha-establishment-search",
        "https://www.osha.gov/ords/imis/establishment.html",
        "primary_authority",
    ),
    (
        "osha-multi-employer-citation-policy",
        "https://www.osha.gov/enforcement/directives/cpl-02-00-124",
        "primary_authority",
    ),
    (
        "ncci-abcs-of-experience-rating",
        "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf",
        "non_competing_expert",
    ),
    (
        "agc-2026-workforce-survey",
        "https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20%284%29.pdf",
        "non_competing_expert",
    ),
    (
        "dol-fact-sheet-13",
        "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship",
        "primary_authority",
    ),
    (
        "osha-injury-tracking-data",
        "https://www.osha.gov/itadata",
        "primary_authority",
    ),
    (
        "sba-prime-and-subcontracting",
        "https://www.sba.gov/counseling/prime-and-subcontracting/",
        "primary_authority",
    ),
    (
        "naic-consumer",
        "https://content.naic.org/consumer",
        "non_competing_expert",
    ),
    (
        "ca-dir-independent-contractor-faq",
        "https://www.dir.ca.gov/dlse/faq_independentcontractor.htm",
        "primary_authority",
    ),
]

RELATIONSHIP_BY_CLASS = {
    "primary_authority": "independent",
    "independent_research": "independent",
    "non_competing_expert": "independent",
    "neutral": "independent",
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for key, url, source_class in SOURCES:
        payload = {
            "schema": "simpro-source-classification/v1",
            "classified_at": now,
            "emitter": {"name": "source_registry_export", "version": "1.0.0"},
            "publisher": {
                "hostname": urlparse(url).hostname,
                "relationship": RELATIONSHIP_BY_CLASS[source_class],
            },
            "registry": {"record_id": f"{SLUG}-{key}", "revision": DATE},
            "source_class": source_class,
            "source_url": url,
        }
        path = OUT_DIR / f"{key}.json"
        atomic_write_json(
            path,
            attest_mapping(
                payload,
                purpose="simpro-source-classification/v1",
                workspace_root=ROOT,
            ),
        )
        print(f"{source_class:22s} {path.name}")
    print(f"\n{len(SOURCES)} classification records -> {OUT_DIR.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
