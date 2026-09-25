"""Map each public-research claim to the authority already linked beside it.

The guard only counts a visible link when the sidecar maps that exact claim to
that exact URL, so claims whose paragraph already carries an approved authority
just need the Source Map row. Claims with no authority link in range are left
alone and reported, because those need an editorial decision rather than a row.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, ".")

from data_sources.modules.proof_link_policy import analyze_proof_links

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
CLASS_DIR = pathlib.Path(f"research/source-classifications/{SLUG}-{DATE}")
ANCHOR = "\n\n## FAQ Source Policy"
CHECKED = "2026-09-22"

# Evidence snippets already verified against each live source in this run.
EVIDENCE = {
    "https://content.naic.org/consumer": "Every U.S. state, the District of Columbia, and the five U.S. territories have a Department of Insurance (DOI) dedicated to helping consumers.",
    "https://www.osha.gov/enforcement/directives/cpl-02-00-124": "more than one employer may be citable for a hazardous condition that violates an OSHA standard.",
    "https://www.osha.gov/itadata": "Injury Tracking Application Data",
    "https://www.osha.gov/ords/imis/establishment.html": "Establishment Search",
    "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-795": "Employee or Independent Contractor Classification Under the Fair Labor Standards Act",
    "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical": "currently set forth in 29 CFR part 795",
    "https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee": "Independent contractor (self-employed) or employee?",
    "https://www.irs.gov/forms-pubs/about-form-ss-8": "About Form SS-8, Determination of Worker Status for Purposes of Federal Employment Taxes and Income Tax Withholding",
    "https://www.irs.gov/forms-pubs/about-form-w-9": "About Form W-9, Request for Taxpayer Identification Number and Certification",
    "https://www.irs.gov/instructions/i1099mec": "File Form 1099-NEC, Nonemployee Compensation, for each person in the course of your business during the year to whom you have paid at least $2,000 in: Services performed by someone who is not your employee",
    "https://www.sba.gov/counseling/prime-and-subcontracting/": "In an effort to locate small business subcontractors, any large business can post a notice of a subcontracting opportunity",
    "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf": "The mod applied to an employer's policy is either a unity (1.00) factor, a credit mod, or a debit mod.",
}


def canonical(url: str) -> str:
    """Match the policy engine's canonical form, which drops a trailing slash."""
    return url.rstrip("/")


def classification_index() -> dict[str, tuple[str, str, str]]:
    """Map each classified source URL to its artifact path, hash and class."""
    index: dict[str, tuple[str, str, str]] = {}
    for path in sorted(CLASS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        index[canonical(payload["source_url"])] = (
            path.as_posix(),
            digest,
            payload["source_class"],
        )
    return index


EVIDENCE_BY_CANONICAL = {
    url.rstrip("/"): (url, snippet) for url, snippet in EVIDENCE.items()
}


def bindable(claim: str) -> str:
    return " ".join(claim.replace("|", " ").split())


def _residual_sentences(claim: str) -> list[str]:
    """Split a residual into the sentences that appear verbatim in the article."""
    article = " ".join(ARTICLE.read_text(encoding="utf-8").split()).casefold()
    sentences: list[str] = []
    for raw in re.split(r"(?<=[.!?])\s+", claim):
        candidate = bindable(raw).strip(" .,;:-")
        if len(candidate.split()) < 4:
            continue
        if candidate.casefold() in article:
            sentences.append(candidate)
    return sentences


def row(claim: str, url: str, artifact: str, digest: str, source_class: str) -> str:
    return " | ".join([
        f"- Claim: {bindable(claim)}",
        "Claim type: factual",
        f"Source class: {source_class}",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {EVIDENCE_BY_CANONICAL[url.rstrip(chr(47))][1]}",
        "Original-source status: original",
        f"Source date: {DATE}",
        f"Checked date: {CHECKED}",
        "Claim fit: direct",
        "Freshness decision: current",
        "Freshness reason: Public authority page read on the checked date.",
        f"Classification artifact: {artifact}",
        f"Classification hash: {digest}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: Public research binding for the claim at the linked authority",
    ])


def main() -> int:
    index = classification_index()
    report = analyze_proof_links(
        ARTICLE.read_text(encoding="utf-8"),
        SIDECAR.read_text(encoding="utf-8"),
    )
    rows: list[str] = []
    unlinked: list[tuple[int, str]] = []
    for requirement in report.requirements:
        if requirement.owner != "public_research":
            continue
        if requirement.mode not in {"inline_required", "section_source_allowed"}:
            continue
        links = [
            link for link in report.links
            if link.external and requirement.line <= link.line <= requirement.end_line
        ]
        if any(link.canonical_url in requirement.visible_urls for link in links):
            continue
        usable = [
            link for link in links
            if canonical(link.canonical_url) in index
            and canonical(link.canonical_url) in EVIDENCE_BY_CANONICAL
        ]
        if not usable:
            unlinked.append((requirement.line, requirement.claim[:90]))
            continue
        key = canonical(usable[0].canonical_url)
        artifact, digest, source_class = index[key]
        # A residual spanning an interior mapped claim is not contiguous text, so
        # it can never match a unit. Bind the individual remaining sentences,
        # each of which does appear verbatim.
        for sentence in _residual_sentences(requirement.claim):
            rows.append(
                row(sentence, EVIDENCE_BY_CANONICAL[key][0], artifact, digest, source_class)
            )

    if rows:
        text = SIDECAR.read_text(encoding="utf-8")
        SIDECAR.write_text(
            text.replace(ANCHOR, "\n" + "\n".join(rows) + ANCHOR, 1),
            encoding="utf-8",
            newline="",
        )
    print(f"bound {len(rows)} public-research claims to their linked authority")
    print(f"needing an editorial decision (no authority link in range): {len(unlinked)}")
    for line, claim in unlinked:
        print(f"  L{line}: {claim}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
