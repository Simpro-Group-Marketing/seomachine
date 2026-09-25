"""Build source rows for the women-in-construction rewrite.

Governance artifact only, modeled on build_trade_jobs_ca_source_rows.py. The
article does not exist yet, so the rows map a fixed set of PLANNED claims to
their public sources. Every planned claim string must later appear verbatim in
the article unit it supports (or the row must be regenerated from the article).

What the script does:
1. Captures every source into research/source-snapshots/women-in-construction-2026-09-26/
   (raw bytes + .meta.json, reused unless --refresh, same as the CA wage builder).
   - HTML sources the guard fetcher can read are fetched live.
   - PDFs are downloaded and text-extracted (pypdf), then bound with a
     pdf_text capture receipt under research/source-captures/<slug>-<date>/.
   - www.bls.gov and dol.gov refuse automated clients (HTTP 403), so their
     visible text was read back through the Chrome connector on 2026-09-25 and is
     stored here verbatim, then bound with an html_visible_text capture receipt.
2. Confirms every Evidence snippet is visible in the live page (guard fetcher) or
   in the bound local artifact.
3. Writes research/source-rows-<slug>-<date>.md/.json, the Metric Proof Pack
   draft, and the early-artifact stats table. It never edits public Markdown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.source_support.persistence import write_source_capture_receipt  # noqa: E402
from data_sources.modules.source_support.retrieval import fetch_source_text  # noqa: E402

SLUG = "women-in-construction"
DATE = "2026-09-26"  # assembly date (file suffix)
CHECKED = "2026-09-25"  # date the sources were actually fetched and read back
SNAP_DIR = ROOT / "research" / "source-snapshots" / f"{SLUG}-{DATE}"
CAPTURE_DIR = ROOT / "research" / "source-captures" / f"{SLUG}-{DATE}"
CLASS_DIR = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}"
OUT_MD = ROOT / "research" / f"source-rows-{SLUG}-{DATE}.md"
OUT_JSON = ROOT / "research" / f"source-rows-{SLUG}-{DATE}.json"
OUT_METRIC = ROOT / "research" / f"metric-proof-pack-{SLUG}-{DATE}.md"
OUT_TABLE = ROOT / "research" / f"{SLUG}-stats-table-{DATE}.md"

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

BLS11 = "https://www.bls.gov/cps/cpsaat11.htm"
BLS18 = "https://www.bls.gov/cps/cpsaat18.htm"
DOL_TRENDLINES = "https://www.dol.gov/sites/dolgov/files/ETA/opder/DASP/Trendlines/posts/2024_11/Trendlines_November_2024.html"
NAHB = "https://eyeonhousing.org/2026/09/womens-share-of-construction-workforce-reaches-20-year-high-in-2025/"
ABC = "https://www.abc.org/News-Media/News-Releases/abc-construction-industry-must-attract-349000-workers-in-2026-despite-macroeconomic-headwinds"
AGC = "https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20%284%29.pdf"
IWPR = "https://iwpr.org/wp-content/uploads/2025/08/Women-in-Construction-QF_2025.pdf"
OSHA_PPE = "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.95"
OSHA_PPE_RULE = "https://www.osha.gov/laws-regs/federalregister/2024-12-12"
OSHA_SANITATION = "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.51"
NCCER = "https://www.nccer.org/media/2024/01/NCCER-Fact-Sheet-Gender-Composition-of-the-Construction-Industry.pdf"

# Chrome connector readbacks (2026-09-25, UTC ~19:25-19:45). Table rows are the
# connector's cell text joined by single spaces; nothing is paraphrased.
BLS11_TEXT = """Employed people by detailed occupation, sex, race, and Hispanic or Latino ethnicity : U.S. Bureau of Labor Statistics
HOUSEHOLD DATA ANNUAL AVERAGES 11. Employed people by detailed occupation, sex, race, and Hispanic or Latino ethnicity [Numbers in thousands]
Occupation | 2025 | Total employed | Percent of total employed | Women | White | Black or African American | Asian | Hispanic or Latino
Total, 16 years and over 163,493 47.1 75.7 12.7 7.5 20.0
Construction managers 1,199 8.5 87.2 5.6 2.9 20.1
Construction and extraction occupations 8,490 4.3 86.6 7.0 1.8 41.7
First-line supervisors of construction trades and extraction workers 788 3.7 89.2 5.2 1.3 28.3
Carpenters 1,178 3.1 88.9 5.8 1.1 43.3
Construction laborers 2,382 4.7 86.4 7.3 2.0 55.2
Construction equipment operators 404 4.6 86.5 8.3 1.1 21.9
Electricians 1,063 3.5 82.8 9.3 3.0 25.0
Painters and paperhangers 485 11.1 87.5 4.7 2.0 58.2
Plumbers, pipefitters, and steamfitters 624 3.1 86.5 7.1 2.8 30.3
Roofers 259 0.9 87.0 4.2 0.4 64.7
Sheet metal workers 148 4.9 88.7 7.1 2.3 17.1
Construction and building inspectors 120 12.6 84.4 10.0 3.7 25.3
Heating, air conditioning, and refrigeration mechanics and installers 561 2.7 80.9 10.4 4.4 26.7
Welding, soldering, and brazing workers 573 5.8 84.2 8.0 3.0 29.8
NOTE: Estimates for the above race groups (White, Black or African American, and Asian) do not sum to totals because data are not presented for all races. People whose ethnicity is identified as Hispanic or Latino may be of any race. Updated population controls are introduced annually with the release of January data. Dash indicates no data or data that do not meet publication criteria (values not shown where base is less than 50,000). Annual estimates for 2025 are 11-month averages that exclude October. (Data for October 2025 were not collected due to the federal government shutdown.) As a result, 2025 annual estimates are not strictly comparable with annual averages for other years.
Last Modified Date: February 20, 2026
"""

BLS18_TEXT = """Employed people by detailed industry, sex, race, and Hispanic or Latino ethnicity : U.S. Bureau of Labor Statistics
HOUSEHOLD DATA ANNUAL AVERAGES 18. Employed people by detailed industry, sex, race, and Hispanic or Latino ethnicity [Numbers in thousands]
Industry | 2025 | Total employed | Percent of total employed | Women | White | Black or African American | Asian | Hispanic or Latino
Total, 16 years and over 163,493 47.1 75.7 12.7 7.5 20.0
Construction 12,121 11.3 86.8 6.6 2.3 35.4
NOTE: Estimates for the above race groups (White, Black or African American, and Asian) do not sum to totals because data are not shown for all races. People whose ethnicity is identified as Hispanic or Latino may be of any race. Updated population controls are introduced annually with the release of January data. Dash indicates no data or data that do not meet publication criteria (values not shown where base is less than 50,000). Effective with January 2025 data, industries reflect the introduction of the 2022 Census industry classification system, derived from the 2022 North American Industry Classification System (NAICS). No historical data have been revised. Data for 2025 are not strictly comparable with earlier years. Annual estimates for 2025 are 11-month averages that exclude October. (Data for October 2025 were not collected due to the federal government shutdown.) As a result, 2025 annual estimates are not strictly comparable with annual averages for other years.
Last Modified Date: February 20, 2026
"""

DOL_TEXT = """trendlines_november_2024
Youth and Women in Registered Apprenticeship
Female Participation in Apprenticeship
The number of women participating in apprenticeship has increased sizably over the last decade. In FY2024, there were almost 100,000 women active in apprenticeship in various industries across the country. This is approximately a 214% increase in women apprentices since FY2015. Despite the 10-year increase in the number of women apprentices, women still only made up about 14% of active apprentices in FY2024. This is about a 6 percentage point increase from FY2015, but more work is needed to continue to expand women’s participation in apprenticeship.
Number of women apprentices, FY2015 to FY2024
Source: analysis of data from RAPIDS (FY2015–FY2024)
Suggested Citation
Kyle DeMaria (ed.) and Lucas Arbulu, “Youth and Women in Registered Apprenticeship,” Trendlines, U.S. Department of Labor Employment and Training Administration, November 2024, https://www.dol.gov/sites/dolgov/files/ETA/opder/DASP/Trendlines/posts/2024_11/Trendlines_November_2024.html.
"""

CHROME = {BLS11: ("bls-cps-aat11-2025", BLS11_TEXT), BLS18: ("bls-cps-aat18-2025", BLS18_TEXT),
          DOL_TRENDLINES: ("dol-trendlines-2024-11", DOL_TEXT)}
PDFS = {IWPR: "iwpr-women-in-construction-qf-2025", AGC: "agc-2026-workforce-survey", NCCER: "nccer-gender-composition-fact-sheet"}
AGC_DOWNLOAD = "https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20(4).pdf"
LIVE_HTML = {NAHB: "nahb-eye-on-housing-women-share-2025", ABC: "abc-2026-workforce-shortage-release",
             OSHA_PPE: "osha-29cfr-1926-95", OSHA_PPE_RULE: "osha-fr-2024-12-12-ppe-fit-final-rule",
             OSHA_SANITATION: "osha-29cfr-1926-51"}

BLS_CLASS = dict(source_class="primary_authority", original="original", source_date="2026-02-20",
                 freshness="current",
                 reason="BLS CPS 2025 annual averages (last modified February 20, 2026) are the latest published annual table; BLS notes 2025 values are 11-month averages that exclude October 2025 and are not strictly comparable with other years, so copy must not present year-over-year change from this table.")
BLS18_CLASS = dict(BLS_CLASS, reason=BLS_CLASS["reason"] + " Table 18 also moved to the 2022 Census industry classification in January 2025.")
DOL_CLASS = dict(source_class="primary_authority", original="original", source_date="historical",
                 freshness="historical_scoped",
                 reason="DOL ETA Trendlines published November 2024 (month only) with RAPIDS FY2024 figures; it is the latest official narrative women-apprentice share found, the FY2025 dashboard exposes no visible-text share, so copy must keep the FY2024 label.")
NAHB_CLASS = dict(source_class="non_competing_expert", original="original", source_date="2026-09-15",
                  freshness="current",
                  reason="NAHB Eye on Housing post dated September 15, 2026 runs its own CPS 2025 tabulation, including the 2004-2025 trend and within-industry occupation shares; it is the original source for those tabulations.")
ABC_CLASS = dict(source_class="non_competing_expert", original="original", source_date="2026-01-15",
                 freshness="current",
                 reason="ABC released its proprietary 2026 workforce shortage model in this January 15, 2026 release, which is the original publication of the estimate; copy must label it an ABC model estimate, not a BLS count.")
AGC_CLASS = dict(source_class="non_competing_expert", original="original", source_date="2026-09-03",
                 freshness="current",
                 reason="The AGC and NCCER 2026 Workforce Survey analysis is the original publication of the survey result and the current edition; copy must label it a survey of contractors.")
IWPR_CLASS = dict(source_class="non_competing_expert", original="original", source_date="historical",
                  freshness="historical_scoped",
                  reason="IWPR Quick Figure Q120 (August 2025) is the original IWPR calculation of RAPIDS 2024 construction apprentices in 37 states; no newer construction-specific women-apprentice share was found, so copy must keep the 2024 and 37-state scope.")
OSHA_REG_CLASS = dict(source_class="primary_authority", original="original", source_date="undated",
                      freshness="historical_scoped",
                      reason="The eCFR-backed OSHA regulation page is undated, so approval is scoped to the live regulatory text checked on " + CHECKED + ".")
OSHA_FR_CLASS = dict(source_class="primary_authority", original="original", source_date="2024-12-12",
                     freshness="current",
                     reason="The OSHA Federal Register final rule dated December 12, 2024 remains the governing notice for the construction PPE fit requirement effective January 13, 2025.")

# Planned claims: (claim, claim_type, url, evidence, class, intended use, metric?, citation mode)
PLANNED = [
    # Early-artifact stats table cells (one unique cell per row).
    ("11.3 percent (12,121 thousand employed)", "statistic", BLS18, "Construction 12,121 11.3 86.8 6.6 2.3 35.4", BLS18_CLASS, "stats table row: construction industry, all jobs", True),
    ("4.3 percent (8,490 thousand employed)", "statistic", BLS11, "Construction and extraction occupations 8,490 4.3 86.6 7.0 1.8 41.7", BLS_CLASS, "stats table row: construction and extraction occupations", True),
    ("12.6 percent (120 thousand employed)", "statistic", BLS11, "Construction and building inspectors 120 12.6 84.4 10.0 3.7 25.3", BLS_CLASS, "stats table row: construction and building inspectors", True),
    ("8.5 percent (1,199 thousand employed)", "statistic", BLS11, "Construction managers 1,199 8.5 87.2 5.6 2.9 20.1", BLS_CLASS, "stats table row: construction managers", True),
    ("4.7 percent (2,382 thousand employed)", "statistic", BLS11, "Construction laborers 2,382 4.7 86.4 7.3 2.0 55.2", BLS_CLASS, "stats table row: construction laborers", True),
    ("3.7 percent (788 thousand employed)", "statistic", BLS11, "First-line supervisors of construction trades and extraction workers 788 3.7 89.2 5.2 1.3 28.3", BLS_CLASS, "stats table row: first-line supervisors of construction trades", True),
    ("3.5 percent (1,063 thousand employed)", "statistic", BLS11, "Electricians 1,063 3.5 82.8 9.3 3.0 25.0", BLS_CLASS, "stats table row: electricians", True),
    ("3.1 percent (1,178 thousand employed)", "statistic", BLS11, "Carpenters 1,178 3.1 88.9 5.8 1.1 43.3", BLS_CLASS, "stats table row: carpenters", True),
    ("3.1 percent (624 thousand employed)", "statistic", BLS11, "Plumbers, pipefitters, and steamfitters 624 3.1 86.5 7.1 2.8 30.3", BLS_CLASS, "stats table row: plumbers, pipefitters, and steamfitters", True),
    ("2.7 percent (561 thousand employed)", "statistic", BLS11, "Heating, air conditioning, and refrigeration mechanics and installers 561 2.7 80.9 10.4 4.4 26.7", BLS_CLASS, "stats table row: HVAC mechanics and installers", True),
    ("0.9 percent (259 thousand employed)", "statistic", BLS11, "Roofers 259 0.9 87.0 4.2 0.4 64.7", BLS_CLASS, "stats table row: roofers", True),
    # Narrative claims.
    ("women held 11.3 percent of construction industry jobs", "statistic", BLS18, "Construction 12,121 11.3 86.8 6.6 2.3 35.4", BLS18_CLASS, "intro and industry-share narrative", True),
    ("women held 4.3 percent of construction and extraction jobs", "statistic", BLS11, "Construction and extraction occupations 8,490 4.3 86.6 7.0 1.8 41.7", BLS_CLASS, "intro and field-trades narrative", True),
    ("11.3% of total construction employment, the highest share in the past 20 years", "statistic", NAHB, "Women accounted for 11.3% of total construction employment, the highest share in the past 20 years.", NAHB_CLASS, "trend narrative: 20-year high", True),
    ("78% of office and administrative support occupations within the construction industry", "statistic", NAHB, "Women accounted for 78% of office and administrative support occupations within the construction industry", NAHB_CLASS, "office-versus-field gap narrative", True),
    ("an estimated 349,000 net new workers in 2026", "statistic", ABC, "The construction industry needs to attract an estimated 349,000 net new workers in 2026 to meet demand for construction services", ABC_CLASS, "labor-gap demand narrative", True),
    ("88 percent of firms with craft openings report those positions are as hard or harder to fill than a year ago", "statistic", AGC, "88 percent of firms with craft openings report those positions are as hard or harder to fill than a year ago", AGC_CLASS, "labor-gap hiring-difficulty narrative", True),
    ("women made up about 14% of active apprentices in FY2024", "statistic", DOL_TRENDLINES, "women still only made up about 14% of active apprentices in FY2024", DOL_CLASS, "apprenticeship section: all-industry share", True),
    ("almost 100,000 women active in apprenticeship", "statistic", DOL_TRENDLINES, "In FY2024, there were almost 100,000 women active in apprenticeship in various industries across the country.", DOL_CLASS, "apprenticeship section: all-industry count", True),
    ("5.4 percent of construction apprentices in the 37 states", "statistic", IWPR, "women are still just 5.4 percent of construction apprentices in the 37 states with data for 2015 and 2024", IWPR_CLASS, "apprenticeship section: construction-specific share", True),
    ("OSHA requires construction employers to select personal protective equipment that properly fits each affected employee", "process", OSHA_PPE, "Is selected to ensure that it properly fits each affected employee.", OSHA_REG_CLASS, "PPE fit retention section", False),
    ("OSHA's construction PPE fit rule took effect January 13, 2025", "process", OSHA_PPE_RULE, "This final rule is effective January 13, 2025.", OSHA_FR_CLASS, "PPE fit retention section", False),
    ("OSHA's construction sanitation standard sets a minimum number of jobsite toilets by crew size", "process", OSHA_SANITATION, "Toilets shall be provided for employees according to the following table", OSHA_REG_CLASS, "sanitation facilities retention section", False),
]

REJECTED = [
    ("NCCER fact sheet: women 10.8% of construction industry and 4.3% of trades (December 2023)", NCCER,
     "Stale and secondary: NCCER cites BLS CPS Tables 11 and 18 retrieved 2024-03-29 for December 2023; the image-only Canva PDF has no extractable text for an Evidence snippet; superseded by BLS 2025 (11.3 percent industry, 4.3 percent construction and extraction). The 11% figure on the live Simpro page is outdated."),
    ("IWPR 2024 occupation shares (4.3% trades, 3.5% laborers, 3.2% plumbers, 2.9% electricians)", IWPR,
     "Secondary IWPR calculations on BLS CPS 2024 annual averages; superseded by BLS 2025 Table 11 (laborers 4.7, plumbers 3.1, electricians 3.5). The live-page '~3% in field trades' framing matches 2024 IWPR values, not 2025 BLS."),
    ("OSHA women-in-construction topic pages (/women-in-construction, /ppe, /facilities)", "https://www.osha.gov/women-in-construction",
     "HTTP 403 'temporarily unavailable' to curl, the guard fetcher, and the Chrome connector on 2026-09-25; replaced by the OSHA 29 CFR 1926.95, 1926.51, and 2024-12-12 final-rule pages, which resolve."),
    ("Apprenticeship.gov FY2025 women-apprentice share", "https://www.apprenticeship.gov/data-and-statistics/apprentices-by-state-dashboard",
     "Interactive dashboard (data through 9/03/2026) exposes no visible-text women share; a Facebook post and HIGH5 aggregator figures are not original sources."),
    ("DOL FY 2023 women in apprenticeship fact sheet (92,500; under 15%)", "https://www.apprenticeship.gov/sites/default/files/DOLIndFSWomen_043024-508.pdf",
     "Now HTTP 404 and superseded by the FY2024 DOL Trendlines figures."),
    ("ABC 2026 estimate of 499,000 workers", "https://www.abc.org/News-Media/News-Releases/abc-construction-industry-needs-to-attract-an-estimated-499000-new-workers-in-2026",
     "Search-result title only; the current ABC 2026 release checked live states 349,000 for 2026 and 456,000 for 2027."),
    ("LBM Journal 'Share of Women in Construction Reaches 20-Year High'", "lbmjournal.com",
     "Secondary trade-press rewrite of the NAHB Eye on Housing post; not cited."),
    ("Google AI Overview 'about 4% of construction and extraction roles'", "google.com",
     "Not a source; verified against BLS Table 11 2025 (4.3 percent all industries) and NAHB (4% within the construction industry)."),
    ("NAWIC WIC Week page", "https://www.nawic.org/wic-week",
     "Resolves (HTTP 200); background only, no statistic used."),
]


def normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%$.]+", " ", text.lower())).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot(name: str, url: str, data: bytes, content_type: str, method: str, refresh: bool) -> Path:
    path = SNAP_DIR / name
    meta_path = SNAP_DIR / f"{name}.meta.json"
    if path.exists() and meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("sha256") != sha256_bytes(path.read_bytes()):
            raise ValueError(f"snapshot hash mismatch: {path}")
        return path
    path.write_bytes(data)
    meta = {"bytes": len(data), "content_type": content_type, "file": rel(path), "http_status": 200,
            "method": method, "retrieved_at": utc_now(), "sha256": sha256_bytes(data), "url": url}
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    text = "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    for curly, plain in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        text = text.replace(curly, plain)
    return re.sub(r"\s+", " ", text).strip()


def capture(refresh: bool) -> dict[str, dict]:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    sources: dict[str, dict] = {}
    for url, key in LIVE_HTML.items():
        text = fetch_source_text(url)  # the same fetcher source_support_guard uses
        snapshot(f"{key}.visible.txt", url, text.encode("utf-8"), "text/plain", "GET source_support.fetch_source_text", refresh)
        sources[url] = {"mode": "live_html", "text": text}
    for url, (key, text) in CHROME.items():
        raw = snapshot(f"{key}.chrome.txt", url, text.encode("utf-8"), "text/plain", "Chrome connector readback 2026-09-25", refresh)
        art = CAPTURE_DIR / f"{key}.md"
        if refresh or not art.exists():
            art.write_bytes(raw.read_bytes())
        sources[url] = {"mode": "chrome_capture", "text": art.read_text(encoding="utf-8"), "artifact": art, "raw": raw, "method": "html_visible_text"}
    for url, key in PDFS.items():
        pdf = SNAP_DIR / f"{key}.pdf"
        if refresh or not pdf.exists():
            download = AGC_DOWNLOAD if url == AGC else url
            req = urllib.request.Request(download, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
        else:
            data = pdf.read_bytes()
        pdf = snapshot(f"{key}.pdf", url, data, "application/pdf", "GET", refresh)
        art = CAPTURE_DIR / f"{key}.md"
        if refresh or not art.exists():
            art.write_text(extract_pdf_text(pdf), encoding="utf-8", newline="\n")
        sources[url] = {"mode": "pdf_capture", "text": art.read_text(encoding="utf-8"), "artifact": art, "raw": pdf, "method": "pdf_text"}
    for url, src in sources.items():
        if src["mode"] == "live_html" or url == NCCER:
            continue
        receipt = CAPTURE_DIR / f"{src['artifact'].stem}-capture-receipt.json"
        if refresh or not receipt.exists():
            write_source_capture_receipt(receipt, source_url=url, source_content_path=src["raw"],
                                         artifact_path=src["artifact"], artifact_reference=rel(src["artifact"]),
                                         method=src["method"], workspace_root=ROOT)
        src["receipt"] = receipt
    return sources


def classification(url: str) -> tuple[str, str]:
    name = f"source-classification-{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    path = CLASS_DIR / name
    if not path.exists():
        raise SystemExit(f"missing classification artifact for {url}; run build_women_in_construction_source_classifications.py")
    return rel(path), sha256_bytes(path.read_bytes())


def row_line(row: dict) -> str:
    c = row["cls"]
    parts = [f"Claim: {row['claim']}", f"Claim type: {row['claim_type']}", f"URL: {row['url']}", f"Evidence: {row['evidence']}",
             f"Source class: {c['source_class']}", "Evidence relation: directly_supports", f"Original-source status: {c['original']}",
             f"Source date: {c['source_date']}", f"Checked date: {CHECKED}", "Claim fit: direct",
             f"Freshness decision: {c['freshness']}", f"Freshness reason: {c['reason']}"]
    if row.get("artifact"):
        parts += [f"Artifact: {row['artifact']}", f"Capture receipt: {row['receipt']}", f"Capture receipt hash: {row['receipt_hash']}"]
    parts += [f"Classification artifact: {row['class_artifact']}", f"Classification hash: {row['class_hash']}",
              "Status: approved", f"Intended use: {row['use']}", f"Citation mode: {row['mode']}"]
    return "- " + " | ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    sources = capture(args.refresh)
    rows: list[dict] = []
    for claim, claim_type, url, evidence, cls, use, metric in PLANNED:
        if "|" in claim or "|" in evidence:
            raise SystemExit(f"pipe in proof row: {claim}")
        src = sources[url]
        visible = normalize(evidence) in normalize(src["text"])
        artifact, digest = classification(url)
        row = {"claim": claim, "claim_type": claim_type, "url": url, "evidence": evidence, "cls": cls, "use": use,
               "metric": metric, "visible": visible, "verified_via": src["mode"], "class_artifact": artifact,
               "class_hash": digest, "mode": "inline_required"}
        if src["mode"] != "live_html":
            row["artifact"] = rel(src["artifact"])
            row["receipt"] = rel(src["receipt"])
            row["receipt_hash"] = sha256_bytes(src["receipt"].read_bytes())
        rows.append(row)
    return write(rows, sources)


def write(rows: list[dict], sources: dict[str, dict]) -> int:
    lines = ["## Source Map", "",
             "<!-- Planned claims: each Claim string must appear verbatim in the article unit it supports. "
             "Stats-table claims are the women-share cell text; write BLS values as 'N percent', never 'N%'. -->", ""]
    lines += [row_line(r) for r in rows]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    metric = [r for r in rows if r["metric"]]
    m = ["## Metric Proof Pack", "", "- Metric requirement: required",
         "- Reason: The guide cites women's share of construction jobs by occupation, apprenticeship shares, and labor-shortage estimates.",
         "- Search log: On 2026-09-25 read BLS CPS 2025 annual Table 11 and Table 18 through the Chrome connector (www.bls.gov returns HTTP 403 to automated clients), "
         "NAHB Eye on Housing (September 15, 2026 CPS tabulation), the ABC 2026 workforce shortage release, the AGC and NCCER 2026 Workforce Survey PDF, "
         "DOL ETA Trendlines November 2024 (Chrome connector), the IWPR August 2025 Quick Figure PDF, the NCCER gender fact sheet PDF, the Apprenticeship.gov data dashboards, "
         "OSHA 29 CFR 1926.95, 1926.51, and the December 12, 2024 PPE fit final rule, and the OSHA women-in-construction topic pages (HTTP 403). "
         f"Raw captures are in `{rel(SNAP_DIR)}/` and receipt-bound artifacts in `{rel(CAPTURE_DIR)}/`."]
    for r in metric:
        extra = f" | Proof artifact: {r['artifact']}" if r.get("artifact") else ""
        m.append(f"- Approved metric: {r['claim']} | URL: {r['url']}{extra} | Evidence: {r['evidence']} | Status: approved | Use: {r['use']}")
    m.append("- Rejected candidates: " + "; ".join(f"{name} ({reason.rstrip('.')})" for name, _u, reason in REJECTED) + ".")
    OUT_METRIC.write_text("\n".join(m) + "\n", encoding="utf-8", newline="\n")

    table_rows = [
        ("Construction industry, all jobs (office and field)", rows[0]),
        ("Construction and building inspectors", rows[2]),
        ("Construction managers", rows[3]),
        ("Construction laborers", rows[4]),
        ("All construction and extraction occupations", rows[1]),
        ("First-line supervisors of construction trades", rows[5]),
        ("Electricians", rows[6]),
        ("Carpenters", rows[7]),
        ("Plumbers, pipefitters, and steamfitters", rows[8]),
        ("HVAC mechanics and installers", rows[9]),
        ("Roofers", rows[10]),
    ]
    t = [f"# Women in construction stats table ({DATE})", "",
         "Early-artifact candidate. Every women-share cell is a planned Source Map claim; keep the cell text exactly as written.",
         "Source for all rows: BLS Current Population Survey, 2025 annual averages (11-month averages that exclude October 2025).", "",
         "| Role or group | Women's share of workers | Source and year |", "| --- | --- | --- |"]
    for label, r in table_rows:
        src = "[BLS CPS Table 18, 2025](" + BLS18 + ")" if r["url"] == BLS18 else "[BLS CPS Table 11, 2025](" + BLS11 + ")"
        t.append(f"| {label} | {r['claim']} | {src} |")
    t += ["", "Notes for the writer:",
          "- Table 18 counts everyone employed by construction firms, including office staff; Table 11 counts people in each occupation across all industries.",
          "- Do not compute year-over-year change from these 2025 values; BLS says they are not strictly comparable with other years.",
          "- For a trend statement use the NAHB row (11.3% of total construction employment, the highest share in the past 20 years) with its own link."]
    OUT_TABLE.write_text("\n".join(t) + "\n", encoding="utf-8", newline="\n")

    record = {"schema": "simpro-women-in-construction-source-rows/v1", "article": None,
              "note": "planned claims; article not yet written", "generated_on": utc_now(), "checked_date": CHECKED,
              "assembly_date": DATE, "rows": [{k: v for k, v in r.items() if k != "cls"} | {"classification": r["cls"]} for r in rows],
              "metric_rows": len(metric), "rejected": [{"candidate": n, "url": u, "reason": x} for n, u, x in REJECTED],
              "not_visible": [r["claim"] for r in rows if not r["visible"]]}
    OUT_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"source rows={len(rows)} metric rows={len(metric)} not visible={len(record['not_visible'])}")
    for claim in record["not_visible"]:
        print("  NOT VISIBLE:", claim)
    return 1 if record["not_visible"] else 0


if __name__ == "__main__":
    sys.exit(main())
