"""Build the California OEWS May 2025 trade wage table for best-trade-jobs-california.

Data path:
1. data.bls.gov OESServices (the JSON API behind https://data.bls.gov/oes/) supplies
   the release label, datatype codes, footnotes, and the full California
   cross-industry table in one POST. That table is the occupation list.
2. The BLS Public Data API v2 (api.bls.gov, no key) cross-checks every ranked
   figure by series ID.
3. The repo's own source-support fetcher checks, per ranked row, whether a public
   HTML page shows the same figures server-side (O*NET OnLine Local Wages).
4. Supporting career sources (union series, projections, licensing pages) are
   checked with the same fetcher.

Raw responses are saved byte-for-byte under research/source-snapshots/. Existing
snapshots are reused unless --refresh is passed, to protect the unregistered BLS
API daily query limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.source_support_guard import fetch_source_text

SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
RUN_ID = "0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5"
AREA_CODE = "0600000"
AREA_LABEL = "California (0600000)"
YEAR = "2025"
TOP_N = 18
TABLE_N = 25
MIN_EMPLOYMENT = 1000
SMALL_SAMPLE_RSE = 20.0

SNAP_DIR = ROOT / "research" / "source-snapshots" / f"ca-oews-{SLUG}-{DATE}"
OUT_JSON = ROOT / "research" / f"ca-oews-trade-wages-{SLUG}-{DATE}.json"
OUT_MD = ROOT / "research" / f"ca-oews-trade-wages-{SLUG}-{DATE}.md"
SOURCES_JSON = ROOT / "research" / f"ca-trade-career-sources-{SLUG}-{DATE}.json"

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
OES_BASE = "https://data.bls.gov/OESServices"
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_READER_URL = f"https://data.bls.gov/oes/#/area/{AREA_CODE}/{YEAR}"
ONET_LOCAL_WAGES = "https://www.onetonline.org/link/localwages/{code}?st=CA"
PROJECTIONS_URL = "https://data.bls.gov/projections/nationalMatrix?queryParams={soc}&ioType=o"
BLS_TIMESERIES_URL = "https://data.bls.gov/timeseries/{series}"

# Datatype codes, verified against /OESServices/prefilter/datatype at run time.
DT = {
    "employment": "01",
    "employment_rse": "02",
    "annual_mean": "04",
    "hourly_median": "08",
    "annual_p10": "11",
    "annual_p25": "12",
    "annual_median": "13",
    "annual_p75": "14",
    "annual_p90": "15",
}
DT_NAMES = {
    "01": "Employment",
    "02": "Employment percent relative standard error",
    "04": "Annual mean wage",
    "08": "Hourly median wage",
    "11": "Annual 10th percentile wage",
    "12": "Annual 25th percentile wage",
    "13": "Annual median wage",
    "14": "Annual 75th percentile wage",
    "15": "Annual 90th percentile wage",
}
API_FIELDS = ("employment", "employment_rse", "annual_mean", "hourly_median",
              "annual_p10", "annual_median", "annual_p90")
BENCHMARKS = ("00-0000", "47-0000", "49-0000")
CORE_TRADES = ("47-2152", "49-9021", "49-2098", "47-2231", "47-2111")

SCOPE_RULE = (
    "Include hands-on detailed occupations in SOC major group 47 (construction and "
    "extraction) and 49 (installation, maintenance, and repair). "
    "EXCLUDE: first-line supervisors (47-1011, 49-1011); helpers (47-3xxx and 49-9098); "
    "extraction workers (47-5xxx); 'all other' residual codes (xx-xxx9 ending 'All "
    "Other', e.g. 47-4099, 49-9099); any occupation with California employment "
    "under 1,000 or with suppressed CA wage/employment data. Use only detailed "
    "occupations (not broad/minor groups). Detailed 51-80xx plant and system operators "
    "are listed as exclusions for transparency because they are utility and plant "
    "operation roles rather than construction or repair trades."
)
NON_HANDS_ON = {"51-8012": "dispatcher / non-hands-on role (power distributors and dispatchers)"}

UNION_SERIES = (
    ("LUU0204899600", "union membership rate, US, 2025"),
    ("LUU0253169100", "median usual weekly earnings, full-time wage and salary, union members"),
    ("LUU0253169300", "median usual weekly earnings, full-time wage and salary, non-union"),
    ("LUU0252881500", "median usual weekly earnings, full-time wage and salary, all workers"),
    ("LUU0254815900", "median usual weekly earnings, union members, construction and extraction occupations"),
    ("LUU0254829700", "median usual weekly earnings, non-union, construction and extraction occupations"),
    ("LUU0254816000", "median usual weekly earnings, union members, installation, maintenance, and repair occupations"),
    ("LUU0254829800", "median usual weekly earnings, non-union, installation, maintenance, and repair occupations"),
)
CA_UNION_CANDIDATES = (
    "https://www.bls.gov/regions/west/news-release/unionmembership_california.htm",
    "https://laborcenter.berkeley.edu/state-of-the-unions-california-labor-in-2025/",
    "https://laborcenter.berkeley.edu/union-density-and-membership-in-california/",
    "https://www.dailycal.org/news/uc/uc-s-state-of-the-unions-reports-staggering-growth-in-california-union-membership/article_cc0e9d53-bcb5-4966-a267-6ecc324ccb98.html",
    "https://en.wikipedia.org/wiki/Labor_unions_in_the_United_States",
)
LICENSING_PAGES = (
    ("https://www.dir.ca.gov/das/DAS_overview.html", ("apprenticeship program offers", "apprentice")),
    ("https://www.dir.ca.gov/dlse/ecu/electricaltrade.html", ("persons performing work as electrician", "certified")),
    ("https://www.cslb.ca.gov/contractors/applicants/contractors_license/exam_application/experience_for_exam.aspx", ("Credit for experience is given only", "journey")),
    ("https://www.cslb.ca.gov/contractors/journeymen/journeymen_faqs.aspx", ("What is journey-level experience?", "journey")),
    ("https://www.dir.ca.gov/dosh/elevatorcertification.html", ("certificate of completion from an approved apprenticeship program", "certif")),
    ("https://www.faa.gov/mechanics/become", ("18 months of practical experience", "certif")),
    ("https://www.epa.gov/section608/section-608-technician-certification-0", ("must be certified", "certif")),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


class Snapshots:
    """Byte-exact raw response store with reuse unless refresh is requested."""

    def __init__(self, refresh: bool) -> None:
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers["User-Agent"] = BROWSER_UA
        self.manifest: list[dict] = []
        SNAP_DIR.mkdir(parents=True, exist_ok=True)

    def get(self, name: str, method: str, url: str, payload: dict | None = None) -> bytes:
        path = SNAP_DIR / name
        meta_path = SNAP_DIR / f"{name}.meta.json"
        if path.exists() and meta_path.exists() and not self.refresh:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            data = path.read_bytes()
            if meta.get("sha256") != sha256_bytes(data):
                raise ValueError(f"snapshot hash mismatch: {path}")
            meta["reused"] = True
            self.manifest.append(meta)
            return data
        if method == "POST":
            response = self.session.post(url, json=payload, timeout=180)
        else:
            response = self.session.get(url, timeout=120)
        response.raise_for_status()
        data = response.content
        path.write_bytes(data)
        meta = {
            "file": rel(path),
            "method": method,
            "url": url,
            "request_payload": payload,
            "http_status": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "retrieved_at": utc_now(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        meta["reused"] = False
        self.manifest.append(meta)
        time.sleep(1.0)
        return data


def parse_number(raw: str) -> float | None:
    value = (raw or "").strip()
    if not value or not re.fullmatch(r"\d+(?:\.\d+)?", value):
        return None
    return float(value)


def as_int(value: float | None) -> int | None:
    return None if value is None else int(round(value))


def money(value: float | int | None) -> str:
    return "n/a" if value is None else f"${int(round(value)):,}"


def series_id(soc: str, datatype: str) -> str:
    return f"OEUS{AREA_CODE}000000{soc.replace('-', '')}{datatype}"


def load_oes_table(snaps: Snapshots) -> tuple[dict, dict, dict, str]:
    years = json.loads(snaps.get("oesservices-prefilter-year.json", "GET", f"{OES_BASE}/prefilter/year"))
    release = next((row["description"] for row in years if row["releaseDate"].startswith(YEAR)), "")
    if release != "May 2025":
        raise ValueError(f"unexpected OEWS release label: {years}")
    datatypes = json.loads(snaps.get("oesservices-prefilter-datatype.json", "GET", f"{OES_BASE}/prefilter/datatype"))
    published = {row["datatypeCode"]: row["datatypeName"] for row in datatypes}
    for code, name in DT_NAMES.items():
        if published.get(code) != name:
            raise ValueError(f"datatype {code} is {published.get(code)!r}, expected {name!r}")
    footnotes = {
        row["footnoteCode"]: row["footnoteText"]
        for row in json.loads(snaps.get("oesservices-combo-footnote.json", "GET", f"{OES_BASE}/combo/footnote"))
    }
    payload = {"areaCode": AREA_CODE, "industryCode": "000000", "year": YEAR,
               "tableSuffix": "pub", "userId": "", "pwd": ""}
    rows = json.loads(snaps.get(f"oesservices-prefilter-table-{AREA_CODE}-{YEAR}.json", "POST",
                                f"{OES_BASE}/prefilter/table", payload))
    occupations: dict[str, dict] = {}
    for row in rows:
        if row["areaCode"] != AREA_CODE or row["industryCode"] != "000000":
            continue
        entry = occupations.setdefault(row["formattedOccupationCode"], {
            "title": row["occupationName"], "values": {}, "footnotes": {}})
        entry["values"][row["datatypeCode"]] = row["value"].strip()
        if row["footnoteCodes"]:
            entry["footnotes"][row["datatypeCode"]] = row["footnoteCodes"]
    return occupations, published, footnotes, release


def in_scope_group(soc: str) -> bool:
    return soc.startswith(("47-", "49-", "51-80"))


def is_detailed(soc: str) -> bool:
    return soc[-1] != "0"


def exclusion_reason(soc: str, title: str, employment: float | None, median: float | None,
                     footnotes: dict) -> str:
    if soc in ("47-1011", "49-1011") or soc.startswith(("47-1", "49-1")):
        return "first-line supervisor"
    if soc.startswith("47-3") or soc == "49-9098":
        return "helper occupation"
    if soc.startswith("47-5"):
        return "extraction worker (47-5xxx)"
    if soc in NON_HANDS_ON:
        return NON_HANDS_ON[soc]
    if soc.startswith("51-"):
        return "plant and system operator (SOC 51-80xx), outside the construction and repair trade scope"
    if soc.endswith("9") and title.rstrip().endswith("All Other"):
        return "'All Other' residual code"
    if employment is None or median is None:
        notes = "; ".join(f"{DT_NAMES.get(k, k)}: {footnotes.get(v, v)}" for k, v in sorted(
            (k, v) for k, v in footnotes.items()))
        return f"suppressed CA estimate ({notes or 'value not published'})"
    if employment < MIN_EMPLOYMENT:
        return f"California employment {int(employment):,} is under {MIN_EMPLOYMENT:,}"
    return ""


def build_rows(occupations: dict, footnote_text: dict) -> tuple[list, list]:
    included, excluded = [], []
    for soc in sorted(occupations):
        if not in_scope_group(soc):
            continue
        entry = occupations[soc]
        values = {name: parse_number(entry["values"].get(code, "")) for name, code in DT.items()}
        notes = {code: footnote_text.get(fn, fn) for code, fn in entry["footnotes"].items()}
        if not is_detailed(soc):
            excluded.append({"soc": soc, "title": entry["title"],
                             "reason": "not a detailed occupation (major, minor, or broad group)",
                             "employment": as_int(values["employment"]),
                             "annual_median": as_int(values["annual_median"])})
            continue
        reason = exclusion_reason(soc, entry["title"], values["employment"], values["annual_median"], notes)
        if reason:
            excluded.append({"soc": soc, "title": entry["title"], "reason": reason,
                             "employment": as_int(values["employment"]),
                             "annual_median": as_int(values["annual_median"])})
            continue
        included.append({
            "soc": soc,
            "title": entry["title"],
            "employment": as_int(values["employment"]),
            "employment_rse": values["employment_rse"],
            "annual_median": as_int(values["annual_median"]),
            "annual_mean": as_int(values["annual_mean"]),
            "annual_p10": as_int(values["annual_p10"]),
            "annual_p25": as_int(values["annual_p25"]),
            "annual_p75": as_int(values["annual_p75"]),
            "annual_p90": as_int(values["annual_p90"]),
            "hourly_median": values["hourly_median"],
            "table_footnotes": notes,
            "series_ids": {name: series_id(soc, DT[name]) for name in DT},
        })
    included.sort(key=lambda row: (-row["annual_median"], row["soc"]))
    for rank, row in enumerate(included, start=1):
        row["rank"] = rank
    return included, excluded


def api_cross_check(snaps: Snapshots, socs: list[str]) -> tuple[dict, list[dict]]:
    wanted = [series_id(soc, DT[name]) for soc in socs for name in API_FIELDS]
    values: dict[str, str] = {}
    responses = []

    def absorb(name: str, data: bytes, count: int) -> None:
        payload = json.loads(data)
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API batch {name} failed: {payload.get('message')}")
        responses.append({"file": rel(SNAP_DIR / name), "series_count": count,
                          "sha256": sha256_bytes(data), "message": payload.get("message", [])})
        for series in payload["Results"]["series"]:
            point = next((row for row in series["data"]
                          if row["year"] == YEAR and row["period"] == "A01"), None)
            values[series["seriesID"]] = point["value"] if point else ""

    # Reuse every cached batch first so a changed ranking only fetches missing series.
    if not snaps.refresh:
        for path in sorted(p for p in SNAP_DIR.glob("bls-api-v2-batch-*.json") if not p.name.endswith(".meta.json")):
            data = snaps.get(path.name, "POST", BLS_API, None)
            absorb(path.name, data, len(json.loads(data)["Results"]["series"]))
    missing = [series for series in wanted if series not in values]
    for index in range(0, len(missing), 25):
        batch = missing[index:index + 25]
        name = f"bls-api-v2-batch-{hashlib.sha256('|'.join(batch).encode()).hexdigest()[:12]}.json"
        data = snaps.get(name, "POST", BLS_API, {"seriesid": batch, "startyear": YEAR, "endyear": YEAR})
        absorb(name, data, len(batch))
    return values, responses


def onet_evidence(row: dict) -> dict:
    snippet = "California " + " ".join(money(row[key]) for key in
                                       ("annual_p10", "annual_p25", "annual_median", "annual_p75", "annual_p90"))
    attempts = []
    for suffix in (".00", ".01", ".02"):
        url = ONET_LOCAL_WAGES.format(code=f"{row['soc']}{suffix}")
        try:
            text = fetch_source_text(url)
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            attempts.append({"url": url, "http_status": status, "error": str(error)[:200]})
            continue
        except Exception as error:  # record and try the next O*NET-SOC suffix
            attempts.append({"url": url, "http_status": None, "error": str(error)[:200]})
            continue
        visible = snippet in text
        release_visible = "Bureau of Labor Statistics 2025 wage data" in text
        attempts.append({"url": url, "http_status": 200, "snippet_visible": visible,
                         "release_label_visible": release_visible})
        if visible:
            return {"evidence_url": url, "evidence_http_status": 200, "evidence_snippet": snippet,
                    "evidence_visible_to_repo_fetcher": True,
                    "evidence_release_label_visible": release_visible,
                    "evidence_attempts": attempts}
    return {"evidence_url": None, "evidence_http_status": None, "evidence_snippet": snippet,
            "evidence_visible_to_repo_fetcher": False, "evidence_release_label_visible": False,
            "evidence_attempts": attempts}


def visible_text(url: str) -> tuple[int | None, str, str]:
    try:
        return 200, fetch_source_text(url), ""
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else None
        return status, "", str(error)[:200]
    except Exception as error:
        return None, "", str(error)[:200]


def snippet_around(text: str, needle: str, before: int = 120, after: int = 220) -> str:
    index = text.lower().find(needle.lower())
    if index < 0:
        return ""
    return re.sub(r"\s+", " ", text[max(0, index - before):index + after]).strip()


def projection_check(soc: str) -> dict:
    url = PROJECTIONS_URL.format(soc=soc)
    status, text, error = visible_text(url)
    match = re.search(
        r"Total, all industries TE1000 Summary ((?:-?[\d,]+\.\d+ ){7}-?[\d,]+\.\d+)", text)
    record = {"soc": soc, "url": url, "status": status, "fetched_at": utc_now(), "error": error,
              "visible_server_side": bool(match)}
    if match:
        numbers = match.group(1).split()
        record.update({
            "snippet": f"Total, all industries TE1000 Summary {match.group(1)}",
            "employment_2025_thousands": numbers[0],
            "employment_2035_thousands": numbers[3],
            "employment_change_thousands": numbers[6],
            "percent_change_2025_35": numbers[7],
            "figure": f"{numbers[7]}%",
        })
    return record


def union_series_check(series: str, label: str) -> dict:
    url = BLS_TIMESERIES_URL.format(series=series)
    status, text, error = visible_text(url)
    title = snippet_around(text, "Series title:", 0, 200)
    match = re.search(r"2024 ([\d.]+) 2025 ([\d.]+)(\(\d+\))?", text)
    record = {"series_id": series, "label": label, "url": url, "status": status,
              "fetched_at": utc_now(), "error": error, "series_title_snippet": title}
    if match:
        record.update({"snippet": match.group(0), "figure_2025": match.group(2),
                       "figure_2024": match.group(1),
                       "footnote": "2025 annual estimate is an 11-month average excluding October 2025"
                       if match.group(3) else ""})
    return record


def check_sources(ranked_socs: list[str]) -> dict:
    records = {"union_series": [union_series_check(s, label) for s, label in UNION_SERIES]}
    ca_union = []
    for url in CA_UNION_CANDIDATES:
        status, text, error = visible_text(url)
        ca_union.append({"url": url, "status": status, "fetched_at": utc_now(), "error": error,
                         "figure_14_9_visible": "14.9" in text,
                         "snippet_14_9": snippet_around(text, "14.9"),
                         "figure_16_7_visible": "16.7%" in text,
                         "snippet_16_7": snippet_around(text, "16.7%")})
    records["california_union_membership_candidates"] = ca_union
    records["projections"] = [projection_check(soc) for soc in ranked_socs]
    licensing = []
    for url, needles in LICENSING_PAGES:
        status, text, error = visible_text(url)
        snippet, needle_used = "", ""
        for needle in needles:
            snippet = snippet_around(text, needle)
            if snippet:
                needle_used = needle
                break
        licensing.append({"url": url, "status": status, "fetched_at": utc_now(), "error": error,
                          "snippet_keyword": needle_used, "snippet": snippet,
                          "visible_text_chars": len(text)})
    records["licensing_pages"] = licensing
    return records


def close_band(rows: list[dict], start: int, end: int) -> dict:
    band = [row for row in rows if start <= row["rank"] <= end]
    gaps = [{"from_rank": a["rank"], "to_rank": b["rank"], "gap": a["annual_median"] - b["annual_median"]}
            for a, b in zip(band, band[1:])]
    return {"ranks": f"{start}-{end}",
            "spread": band[0]["annual_median"] - band[-1]["annual_median"] if band else None,
            "max_gap": max((gap["gap"] for gap in gaps), default=None),
            "min_gap": min((gap["gap"] for gap in gaps), default=None),
            "gaps": gaps}


def write_markdown(payload: dict) -> None:
    rows = payload["included"]
    by_soc = {row["soc"]: row for row in rows}
    lines = [
        f"# California OEWS May 2025 trade wage table: {SLUG}",
        "",
        f"- Run ID: {RUN_ID}",
        f"- Retrieved: {payload['retrieved_at']}",
        f"- Release: {payload['release']} | Area: {payload['area']}",
        f"- Ranking measure: California annual median wage (OEWS datatype 13); 'top 10% earn' uses the annual 90th percentile (datatype 15).",
        f"- Machine artifact: `{rel(OUT_JSON)}`",
        f"- Raw snapshots: `{rel(SNAP_DIR)}/`",
        "",
        "## Method",
        "",
        payload["method"],
        "",
        "## Scope rule",
        "",
        SCOPE_RULE,
        "",
        f"## Ranked table (top {TABLE_N} of {len(rows)} in-scope occupations)",
        "",
        "| Rank | SOC | Occupation | CA median | CA p90 (top 10%) | CA mean | CA p10 | Hourly median | Employment | Emp. RSE | API check | Server-visible evidence |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows[:TABLE_N]:
        lines.append(
            f"| {row['rank']} | {row['soc']} | {row['title']} | {money(row['annual_median'])} | "
            f"{money(row['annual_p90'])} | {money(row['annual_mean'])} | {money(row['annual_p10'])} | "
            f"${row['hourly_median']:.2f} | {row['employment']:,} | {row['employment_rse']}% | "
            f"{row.get('api_cross_check', 'not run')} | "
            f"{'yes (O*NET)' if row.get('evidence_visible_to_repo_fetcher') else 'no'} |")
    top = rows[:TOP_N]
    lines += [
        "",
        f"## Top-{TOP_N} cut",
        "",
        f"The top {TOP_N} run from {money(top[0]['annual_median'])} ({top[0]['title']}) to "
        f"{money(top[-1]['annual_median'])} ({top[-1]['title']}). Rank {TOP_N + 1} is "
        f"{rows[TOP_N]['title']} at {money(rows[TOP_N]['annual_median'])}, "
        f"{money(top[-1]['annual_median'] - rows[TOP_N]['annual_median'])} below the cut.",
        "",
        f"## Core service trades just outside the top {TOP_N}",
        "",
        "| SOC | Occupation | Rank | CA median | CA p90 | Employment | Emp. RSE |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for soc in CORE_TRADES:
        row = by_soc.get(soc)
        if row is None:
            lines.append(f"| {soc} | not in scope | | | | | |")
            continue
        if soc == "47-2111" and row["rank"] <= TOP_N:
            continue
        lines.append(f"| {soc} | {row['title']} | {row['rank']} | {money(row['annual_median'])} | "
                     f"{money(row['annual_p90'])} | {row['employment']:,} | {row['employment_rse']}% |")
    band = payload["close_band"]
    lines += [
        "",
        "## Close-band note",
        "",
        f"Ranks {band['ranks']} are separated by {money(band['spread'])} in total; consecutive gaps "
        f"range from {money(band['min_gap'])} to {money(band['max_gap'])}. Small differences in this "
        "band are within ordinary survey variation, so public copy should not over-interpret rank order there.",
        "",
        "| From rank | To rank | Median gap |",
        "|---:|---:|---:|",
    ]
    lines += [f"| {gap['from_rank']} | {gap['to_rank']} | {money(gap['gap'])} |" for gap in band["gaps"]]
    caveats = [row for row in rows[:TABLE_N] if (row["employment_rse"] or 0) >= SMALL_SAMPLE_RSE]
    lines += ["", f"## Small-sample caveats (employment RSE >= {SMALL_SAMPLE_RSE:.0f}%)", ""]
    lines += [f"- Rank {row['rank']} {row['soc']} {row['title']}: employment {row['employment']:,}, "
              f"RSE {row['employment_rse']}%." for row in caveats] or ["- None in the ranked table."]
    lines += ["", "## Exclusions", "", "| SOC | Occupation | Reason | Employment | CA median |",
              "|---|---|---|---:|---:|"]
    for row in payload["excluded"]:
        employment = f"{row['employment']:,}" if row["employment"] is not None else "suppressed"
        lines.append(f"| {row['soc']} | {row['title']} | {row['reason']} | {employment} | "
                     f"{money(row['annual_median'])} |")
    lines += ["", "## Benchmarks", "", "| SOC | Group | CA median | Employment |", "|---|---|---:|---:|"]
    lines += [f"| {row['soc']} | {row['title']} | {money(row['annual_median'])} | {row['employment']:,} |"
              for row in payload["benchmarks"]]
    lines += ["", "## Evidence routes", "", payload["evidence_note"], ""]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="refetch raw BLS responses")
    args = parser.parse_args()

    retrieved_at = utc_now()
    snaps = Snapshots(refresh=args.refresh)
    occupations, datatypes, footnote_text, release = load_oes_table(snaps)
    included, excluded = build_rows(occupations, footnote_text)

    checked = [row["soc"] for row in included[:TABLE_N]]
    checked += [soc for soc in CORE_TRADES if soc not in checked and any(r["soc"] == soc for r in included)]
    api_values, api_responses = api_cross_check(snaps, checked + list(BENCHMARKS))

    by_soc = {row["soc"]: row for row in included}
    for soc in checked:
        row = by_soc[soc]
        mismatches = []
        for name in API_FIELDS:
            api_value = parse_number(api_values.get(row["series_ids"][name], ""))
            table_value = row[name]
            if api_value is None or abs(float(api_value) - float(table_value)) > 0.001:
                mismatches.append({"field": name, "api": api_values.get(row["series_ids"][name]),
                                   "table": table_value})
        row["api_cross_check"] = "match" if not mismatches else "MISMATCH"
        row["api_mismatches"] = mismatches
        row["reader_url"] = BLS_READER_URL
        row.update(onet_evidence(row))
        if row["evidence_visible_to_repo_fetcher"]:
            row["public_copy_url"] = row["evidence_url"]
        row["api_evidence_url"] = f"https://api.bls.gov/publicAPI/v2/timeseries/data/{row['series_ids']['annual_median']}"
        time.sleep(0.5)

    benchmarks = []
    for soc in BENCHMARKS:
        entry = occupations[soc]
        employment = parse_number(entry["values"].get("01", ""))
        median = parse_number(entry["values"].get("13", ""))
        api_median = parse_number(api_values.get(series_id(soc, "13"), ""))
        benchmarks.append({"soc": soc, "title": entry["title"], "employment": as_int(employment),
                           "annual_median": as_int(median), "annual_mean": as_int(parse_number(entry["values"].get("04", ""))),
                           "series_ids": {"employment": series_id(soc, "01"), "annual_median": series_id(soc, "13")},
                           "api_cross_check": "match" if api_median == median else "MISMATCH"})

    evidence_note = (
        "data.bls.gov/oes/ and data.bls.gov/timeseries/OEUS... return HTTP 200 to the repo fetcher but "
        "the OEWS figures are not in the server-rendered HTML (SPA / empty series table), so they fail "
        "source_evidence_not_found if cited as the proof URL. api.bls.gov JSON is rejected by the fetcher's "
        "MIME policy (text/html, text/plain, application/xhtml+xml only), which routes source support to the "
        "local-artifact fallback and requires a tool-emitted capture receipt. O*NET OnLine Local Wages "
        "(DOL-sponsored, 'Source: Bureau of Labor Statistics 2025 wage data') renders the California "
        "p10/p25/median/p75/p90 row server-side and is the working public-copy proof URL. Employment "
        "counts and RSEs are not on the O*NET page; they are evidenced only by the saved BLS API/OESServices "
        "snapshots."
    )
    payload = {
        "schema": "simpro-ca-oews-wage-table/v1",
        "run_id": RUN_ID,
        "topic_slug": SLUG,
        "retrieved_at": retrieved_at,
        "release": release,
        "area": AREA_LABEL,
        "method": (
            "Full California cross-industry OEWS table from POST https://data.bls.gov/OESServices/prefilter/table "
            f"(areaCode {AREA_CODE}, industryCode 000000, year {YEAR}); datatype codes verified against "
            "/OESServices/prefilter/datatype; release label from /OESServices/prefilter/year. Scope rule applied "
            "to every SOC in groups 47, 49, and 51-80; detailed = SOC code not ending in 0; suppressed = "
            "non-numeric value (footnote 8 'Estimate not released'). Occupations absent from the published "
            "California table are treated as not published. Ranked by annual median descending; ranked top-"
            f"{TABLE_N} plus core trades cross-checked series-by-series against the BLS Public Data API v2 "
            "(employment, employment RSE, annual mean, hourly median, annual p10, annual median, annual p90)."
        ),
        "scope_rule": SCOPE_RULE,
        "min_employment": MIN_EMPLOYMENT,
        "datatype_codes_verified": {code: datatypes[code] for code in sorted(DT_NAMES)},
        "footnotes": footnote_text,
        "reader_url": BLS_READER_URL,
        "evidence_note": evidence_note,
        "top_n": TOP_N,
        "included": included,
        "excluded": excluded,
        "benchmarks": benchmarks,
        "core_trades": [{"soc": soc, "rank": by_soc[soc]["rank"] if soc in by_soc else None,
                         "inside_top_n": bool(soc in by_soc and by_soc[soc]["rank"] <= TOP_N)}
                        for soc in CORE_TRADES],
        "close_band": close_band(included, 12, 24),
        "small_sample_rows": [row["soc"] for row in included if (row["employment_rse"] or 0) >= SMALL_SAMPLE_RSE],
        "api_responses": api_responses,
        "raw_snapshots": snaps.manifest,
    }
    atomic_write_json(OUT_JSON, payload)
    write_markdown(payload)

    sources = check_sources(checked)
    atomic_write_json(SOURCES_JSON, {
        "schema": "simpro-ca-trade-career-sources/v1",
        "run_id": RUN_ID,
        "topic_slug": SLUG,
        "checked_at": utc_now(),
        "fetcher": "data_sources.modules.source_support_guard.fetch_source_text (SOURCE_VISIBLE_TEXT_POLICY)",
        **sources,
    })

    mismatched = [row["soc"] for row in included if row.get("api_cross_check") == "MISMATCH"]
    print(f"included={len(included)} excluded={len(excluded)} api_mismatches={mismatched}")
    for row in included[:TABLE_N]:
        print(f"{row['rank']:>2} {row['soc']} {row['annual_median']:>7} p90={row['annual_p90']} "
              f"emp={row['employment']} rse={row['employment_rse']} onet={row['evidence_visible_to_repo_fetcher']}")
    return 1 if mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
