"""Source checks and Markdown rendering for the California OEWS trade wage table.

Split from build_trade_jobs_ca_wage_table.py so each script stays within the
repository's structure limits. Governance artifact helpers only.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from data_sources.modules.source_support_guard import fetch_source_text

BLS_TIMESERIES_URL = "https://data.bls.gov/timeseries/{series}"
PROJECTIONS_URL = "https://data.bls.gov/projections/nationalMatrix?queryParams={soc}&ioType=o"
ONET_LOCAL_WAGES = "https://www.onetonline.org/link/localwages/{code}?st=CA"
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


def money(value: float | int | None) -> str:
    return "n/a" if value is None else f"${int(round(value)):,}"


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


def write_markdown(payload: dict, cfg: dict) -> None:
    rows = payload["included"]
    by_soc = {row["soc"]: row for row in rows}
    lines = [
        f"# California OEWS May 2025 trade wage table: {cfg['SLUG']}",
        "",
        f"- Run ID: {cfg['RUN_ID']}",
        f"- Retrieved: {payload['retrieved_at']}",
        f"- Release: {payload['release']} | Area: {payload['area']}",
        f"- Ranking measure: California annual median wage (OEWS datatype 13); 'top 10% earn' uses the annual 90th percentile (datatype 15).",
        f"- Machine artifact: `{cfg['OUT_JSON_REL']}`",
        f"- Raw snapshots: `{cfg['SNAP_DIR_REL']}/`",
        "",
        "## Method",
        "",
        payload["method"],
        "",
        "## Scope rule",
        "",
        cfg["SCOPE_RULE"],
        "",
        f"## Ranked table (top {cfg['TABLE_N']} of {len(rows)} in-scope occupations)",
        "",
        "| Rank | SOC | Occupation | CA median | CA p90 (top 10%) | CA mean | CA p10 | Hourly median | Employment | Emp. RSE | API check | Server-visible evidence |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows[:cfg["TABLE_N"]]:
        lines.append(
            f"| {row['rank']} | {row['soc']} | {row['title']} | {money(row['annual_median'])} | "
            f"{money(row['annual_p90'])} | {money(row['annual_mean'])} | {money(row['annual_p10'])} | "
            f"${row['hourly_median']:.2f} | {row['employment']:,} | {row['employment_rse']}% | "
            f"{row.get('api_cross_check', 'not run')} | "
            f"{'yes (O*NET)' if row.get('evidence_visible_to_repo_fetcher') else 'no'} |")
    top = rows[:cfg["TOP_N"]]
    lines += [
        "",
        f"## Top-{cfg['TOP_N']} cut",
        "",
        f"The top {cfg['TOP_N']} run from {money(top[0]['annual_median'])} ({top[0]['title']}) to "
        f"{money(top[-1]['annual_median'])} ({top[-1]['title']}). Rank {cfg['TOP_N'] + 1} is "
        f"{rows[cfg["TOP_N"]]['title']} at {money(rows[cfg["TOP_N"]]['annual_median'])}, "
        f"{money(top[-1]['annual_median'] - rows[cfg["TOP_N"]]['annual_median'])} below the cut.",
        "",
        f"## Core service trades just outside the top {cfg['TOP_N']}",
        "",
        "| SOC | Occupation | Rank | CA median | CA p90 | Employment | Emp. RSE |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for soc in cfg["CORE_TRADES"]:
        row = by_soc.get(soc)
        if row is None:
            lines.append(f"| {soc} | not in scope | | | | | |")
            continue
        if soc == "47-2111" and row["rank"] <= cfg["TOP_N"]:
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
    caveats = [row for row in rows[:cfg["TABLE_N"]] if (row["employment_rse"] or 0) >= cfg["SMALL_SAMPLE_RSE"]]
    lines += ["", f"## Small-sample caveats (employment RSE >= {cfg['SMALL_SAMPLE_RSE']:.0f}%)", ""]
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
    cfg["OUT_MD"].write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
