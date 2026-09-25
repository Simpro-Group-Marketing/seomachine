"""Build proof rows for the best-trade-jobs-california rewrite.

Governance artifact only: reads the public article, maps every cited figure and
licensing statement to its linked public source, confirms each Evidence snippet is
visible with the repository's own source fetcher, and writes a sidecar fragment
(Source Map, Metric Proof Pack, FAQ Proof Map) plus a JSON check record. It never
edits public Markdown.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.proof_link_policy import _article_units, _plain_text  # noqa: E402
from data_sources.modules.source_support.retrieval import fetch_source_text  # noqa: E402
from data_sources.modules.source_support.text_matching import _extract_visible_text  # noqa: E402,F401
from data_sources.modules.source_support.claim_matching import _general_claim_type  # noqa: E402
from data_sources.modules.source_support.common import _claim_text_for_detection  # noqa: E402

SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
WAGES = ROOT / "research" / f"ca-oews-trade-wages-{SLUG}-{DATE}.json"
OUT_MD = ROOT / "research" / f"source-rows-{SLUG}-{DATE}.md"
OUT_JSON = ROOT / "research" / f"source-rows-{SLUG}-{DATE}.json"

ONET_RE = re.compile(r"https://www\.onetonline\.org/link/localwages/(\d{2}-\d{4})\.00\?st=CA")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MONEY_RE = re.compile(r"\$\d[\d,]*")
PCT_RE = re.compile(r"\b\d+(?:\.\d+)?(?:%| percent\b)")
PROJ_URL = "https://data.bls.gov/projections/occupationProj"
ONET_CLASS = (
    "Source class: primary_authority | Evidence relation: directly_supports | Original-source status: original | Source date: undated | "
    f"Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | "
    "Freshness reason: O*NET OnLine is the Department of Labor display of the original BLS May 2025 "
    "OEWS California estimates (page label: Bureau of Labor Statistics 2025 wage data); values match "
    "the BLS API series recorded in the wage source table, and approval is scoped to the latest release "
    f"checked on {DATE}."
)
PROJ_CLASS = (
    "Source class: primary_authority | Evidence relation: directly_supports | Original-source status: original | Source date: undated | "
    f"Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | "
    "Freshness reason: the BLS Employment Projections table shows the 2025-2035 projection cycle and "
    f"typical entry-level education and training, scoped to the version checked on {DATE}."
)
GOV_CLASS = (
    "Source class: primary_authority | Evidence relation: directly_supports | Original-source status: original | Source date: undated | "
    f"Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | "
    "Freshness reason: the official page is undated, so approval is scoped to the live page state "
    f"checked on {DATE}."
)
UNION_CLASS = (
    "Source class: primary_authority | Evidence relation: directly_supports | Original-source status: original | Source date: undated | "
    f"Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | "
    "Freshness reason: the BLS Current Population Survey series shows the 2025 annual value, which BLS "
    "footnotes as an 11-month average; approval is scoped to the value checked on "
    f"{DATE}."
)
# Evidence snippets for non-O*NET sources, verified live below.
LICENSING = {
    "https://www.dir.ca.gov/dosh/elevatorcertification.html": (
        "Submit a certificate of completion from an approved apprenticeship program",
        "licensing"),
    "https://www.faa.gov/mechanics/become": ("18 months of practical experience", "licensing"),
    "https://www.cslb.ca.gov/contractors/applicants/contractors_license/exam_application/experience_for_exam.aspx": (
        "must have at least four (4) years of experience, in the class you are applying for", "licensing"),
    "https://www.epa.gov/section608/section-608-technician-certification-0": ("Section 608 Technician Certification", "licensing"),
    "https://www.dir.ca.gov/dlse/ecu/electricaltrade.html": (
        "persons performing work as electrician under a C-10 licensed contractor be certified", "licensing"),
    "https://www.dir.ca.gov/das/DAS_overview.html": ("apprenticeship", "licensing"),
    "https://www.dir.ca.gov/dlse/faq_overtime.htm": (
        "one and one-half times his or her regular rate of pay for all hours worked over eight hours in any workday", "licensing"),
}
UNION = {
    "https://data.bls.gov/timeseries/LUU0254815900": ("1,561", "2024 1492 2025 1561"),
    "https://data.bls.gov/timeseries/LUU0254829700": ("1,004", "2024 974 2025 1004"),
}
PROJ_PCT_SOC = {"3.4 percent": "49-9052", "36.5 percent": "47-2231", "10.9 percent": "49-9021", "10.3 percent": "49-9051", "9.2 percent": "47-2111"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%$]+", " ", text.lower())).strip()


def clause(plain: str, token_start: int, token_end: int, floor: int) -> str:
    """Return the non-overlapping clause that ends at a figure (plus a trailing 'or more')."""
    left = plain.rfind(". ", 0, token_start)
    left = max(left + 2 if left >= 0 else 0, floor)
    comma = plain.rfind(", ", left, token_start)
    colon = plain.rfind(": ", left, token_start)
    left = max(left, comma + 2 if comma >= 0 else left, colon + 2 if colon >= 0 else left)
    end = token_end
    tail = plain[end:end + 8]
    if tail.startswith(" or more"):
        end += len(" or more")
    text = plain[left:end].strip()
    text = re.sub(r"^(?:and|then)\s+", "", text)
    return text.rstrip(",;: ")


class RowCollector:
    """Collect Source Map and Metric Proof Pack rows for one article."""

    def __init__(self, by_soc: dict) -> None:
        self.by_soc = by_soc
        self.fetched: dict[str, str] = {}
        self.source_rows: list[dict] = []
        self.metric_rows: list[dict] = []
        self.seen: set[tuple[str, str]] = set()

    def page(self, url: str) -> str:
        if url not in self.fetched:
            raw = fetch_source_text(url)
            RAW[url] = raw
            self.fetched[url] = normalize(raw)
        return self.fetched[url]

    def add(self, claim: str, claim_type: str, url: str, evidence: str, cls: str, use: str, metric: bool) -> None:
        if (claim, url) in self.seen:
            return
        self.seen.add((claim, url))
        visible = normalize(evidence) in self.page(url)
        self.source_rows.append({"claim": claim, "claim_type": claim_type, "url": url, "evidence": evidence,
                                 "cls": cls, "use": use, "visible": visible})
        if metric:
            self.metric_rows.append({"claim": claim, "url": url, "evidence": evidence, "use": use, "visible": visible})

    def table_row(self, plain: str, links: list, use_base: str) -> None:
        match = next((ONET_RE.search(url) for _a, url in links if ONET_RE.search(url)), None)
        if not match:
            return
        row = self.by_soc[match.group(1)]
        cells = [cell.strip() for cell in plain.strip().strip("|").split("|")]
        self.add(cells[2], "statistic", match.group(0), row["evidence_snippet"], ONET_CLASS,
                 f"comparison table row: {use_base}", True)
        for anchor, url in links:
            if url in LICENSING:
                self.add(anchor, "factual", url, LICENSING[url][0], GOV_CLASS, f"credential cell: {use_base}", False)

    def money_figure(self, claim: str, token: str, onet_socs: list, line: int, use_base: str) -> None:
        value = int(token[1:].replace(",", ""))
        url = next((u for u, (label, _e) in UNION.items() if label == token[1:]), None)
        if url:
            self.add(claim, "statistic", url, UNION[url][1], UNION_CLASS, f"union pay: {use_base}", True)
            return
        soc = next((s for s in onet_socs if value in (self.by_soc[s]["annual_median"], self.by_soc[s]["annual_p90"])), None)
        if soc is None:
            raise SystemExit(f"unmapped figure {token} at line {line}")
        row = self.by_soc[soc]
        is_p90 = value == row["annual_p90"] and value != row["annual_median"]
        evidence = f"10% of workers earn ${value:,} or more" if is_p90 else row["evidence_snippet"]
        self.add(claim, "statistic", f"https://www.onetonline.org/link/localwages/{soc}.00?st=CA", evidence,
                 ONET_CLASS, f"California pay: {use_base}", True)

    def figures(self, plain: str, links: list, line: int, use_base: str) -> list:
        found = sorted([(m.start(), m.end(), m.group(0)) for m in MONEY_RE.finditer(plain)]
                       + [(m.start(), m.end(), m.group(0)) for m in PCT_RE.finditer(plain)])
        onet_socs = [ONET_RE.search(url).group(1) for _a, url in links if ONET_RE.search(url)]
        floor = 0
        for start, end, token in found:
            if token in ("10%", "$100,000"):
                continue  # carried inside the following clause or FAQ threshold wording
            claim = clause(plain, start, end, floor)
            floor = end
            if token.startswith("$") and token[1:].replace(",", "").isdigit():
                self.money_figure(claim, token, onet_socs, line, use_base)
            elif token in PROJ_PCT_SOC:
                self.add(claim, "statistic", PROJ_URL, PROJ_PCT_SOC[token], PROJ_CLASS,
                         f"national outlook: {use_base}", True)
            else:
                raise SystemExit(f"unmapped percentage {token} at line {line}")
        return found

    def link_claims(self, plain: str, links: list, has_figures: bool, in_faq: bool, use_base: str) -> None:
        sentences = re.split(r"(?<=[.!?])\s+", plain)
        for anchor, url in links:
            sentence = next((s for s in sentences if anchor in s), anchor)
            if url in LICENSING:
                snippet = LICENSING[url][0]
                if "three years" in sentence and "elevatorcertification" in url:
                    snippet = "Document a minimum of three years of work experience in the conveyance industry"
                kind = _general_claim_type(_claim_text_for_detection(sentence)) or "factual"
                self.add(sentence.rstrip("."), kind, url, snippet, GOV_CLASS, f"credential statement: {use_base}", False)
            if url == PROJ_URL and not has_figures and not in_faq:
                self.add(sentence.rstrip("."), "process", url, "Typical Entry-Level Education", PROJ_CLASS,
                         f"training route background: {use_base}", False)


def main() -> int:
    wages = json.loads(WAGES.read_text(encoding="utf-8"))
    collector = RowCollector({row["soc"]: row for row in wages["included"]})
    article = ARTICLE.read_text(encoding="utf-8")
    for unit in _article_units(article):
        in_faq = unit.section.lower().startswith(("faqs about", "frequently asked questions"))
        plain = _plain_text(unit.text)
        links = LINK_RE.findall(unit.text)
        use_base = f"{unit.section} (line {unit.line})"
        if unit.is_table_row:
            collector.table_row(plain, links, use_base)
            continue
        found = collector.figures(plain, links, unit.line, use_base)
        collector.link_claims(plain, links, bool(found), in_faq, use_base)
    return write(collector.source_rows, collector.metric_rows, collector.fetched, article)


RAW: dict[str, str] = {}


def fix_projection_evidence(rows: list[dict], fetched: dict[str, str]) -> None:
    text = re.sub(r"\s+", " ", RAW.get(PROJ_URL, ""))
    for row in rows:
        if row["url"] == PROJ_URL and re.fullmatch(r"\d{2}-\d{4}", row["evidence"]):
            soc = row["evidence"]
            match = re.search(rf"{re.escape(soc)} [\d.,]+ [\d.,]+ -?[\d.,]+ -?[\d.,]+", text)
            snippet = match.group(0).strip() if match else soc
            row["evidence"] = snippet
            row["visible"] = bool(match) and normalize(snippet) in fetched.get(PROJ_URL, "")


def classification(url: str) -> tuple[str, str]:
    name = f"source-classification-{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    path = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}" / name
    if not path.exists():
        raise SystemExit(f"missing classification artifact for {url}; run build_trade_jobs_ca_source_classifications.py")
    return path.relative_to(ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def write(source_rows, metric_rows, fetched, article) -> int:
    fix_projection_evidence(source_rows, fetched)
    fix_projection_evidence(metric_rows, fetched)
    lines = ["## Source Map", ""]
    for row in source_rows:
        artifact, digest = classification(row["url"])
        lines.append(
            f"- Claim: {row['claim']} | Claim type: {row['claim_type']} | URL: {row['url']} | "
            f"Evidence: {row['evidence']} | {row['cls']} | Classification artifact: {artifact} | "
            f"Classification hash: {digest} | Status: approved | Intended use: {row['use']} | "
            f"Citation mode: {'inline_required' if row['claim_type'] != 'process' else 'section_source_allowed'}"
        )
    lines += ["", "## Metric Proof Pack", "", "- Metric requirement: required",
              "- Reason: The article ranks California trades by 2025 median and 90th-percentile wages and cites national projection and union earnings figures.",
              "- Search log: Pulled the full BLS OEWS May 2025 California table (data.bls.gov OESServices), cross-checked every published figure series by series against the BLS Public Data API, confirmed each value on the O*NET OnLine California local-wage page, read the BLS 2025-2035 Employment Projections table and the BLS union earnings series, and rejected www.bls.gov pages (HTTP 403), EDD Q1-2026 aged wages (different method), and job-board salary figures (different methods). Claim-ready values are saved in `research/ca-oews-trade-wages-best-trade-jobs-california-2026-09-24.json`."]
    for row in metric_rows:
        lines.append(f"- Approved metric: {row['claim']} | URL: {row['url']} | Evidence: {row['evidence']} | Status: approved | Use: {row['use']}")
    lines.append("- Rejected candidates: EDD Q1-2026 wage estimates (ECI-aged, hourly median only); national OEWS medians (not California); job-board salary estimates (inconsistent methods); California 14.9% union membership rate (no validator-safe public source).")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    record = {
        "schema": "simpro-trade-jobs-ca-source-rows/v1",
        "article": ARTICLE.relative_to(ROOT).as_posix(),
        "article_sha256": hashlib.sha256(ARTICLE.read_bytes()).hexdigest(),
        "generated_on": DATE,
        "rows": source_rows,
        "metric_rows": len(metric_rows),
        "not_visible": [row for row in source_rows if not row["visible"]],
    }
    OUT_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"source rows={len(source_rows)} metric rows={len(metric_rows)} not visible={len(record['not_visible'])}")
    for row in record["not_visible"]:
        print("  NOT VISIBLE:", row["url"], "|", row["evidence"])
    return 1 if record["not_visible"] else 0


if __name__ == "__main__":
    sys.exit(main())
