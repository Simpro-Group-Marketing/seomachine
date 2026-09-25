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
from scripts.trade_jobs_ca_wage_support import check_sources, onet_evidence, write_markdown  # noqa: E402

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


def close_band(rows: list[dict], start: int, end: int) -> dict:
    band = [row for row in rows if start <= row["rank"] <= end]
    gaps = [{"from_rank": a["rank"], "to_rank": b["rank"], "gap": a["annual_median"] - b["annual_median"]}
            for a, b in zip(band, band[1:])]
    return {"ranks": f"{start}-{end}",
            "spread": band[0]["annual_median"] - band[-1]["annual_median"] if band else None,
            "max_gap": max((gap["gap"] for gap in gaps), default=None),
            "min_gap": min((gap["gap"] for gap in gaps), default=None),
            "gaps": gaps}


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
            "to every SOC in groups 47 and 49 (51-80 listed as exclusions); detailed = SOC code not ending in 0; suppressed = "
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
    write_markdown(payload, {
        "SLUG": SLUG, "RUN_ID": RUN_ID, "SCOPE_RULE": SCOPE_RULE, "TABLE_N": TABLE_N, "TOP_N": TOP_N,
        "CORE_TRADES": CORE_TRADES, "SMALL_SAMPLE_RSE": SMALL_SAMPLE_RSE, "OUT_MD": OUT_MD,
        "OUT_JSON_REL": rel(OUT_JSON), "SNAP_DIR_REL": rel(SNAP_DIR),
    })

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
