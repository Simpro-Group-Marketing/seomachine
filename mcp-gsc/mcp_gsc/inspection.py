"""URL inspection and indexing-diagnostics tools."""

from __future__ import annotations

from datetime import datetime

from . import auth
from .formatting import site_not_found_error


async def inspect_url_enhanced(site_url: str, page_url: str) -> str:
    """Inspect indexing status and rich results for one URL."""
    try:
        request = {"inspectionUrl": page_url, "siteUrl": site_url}
        response = (
            auth.get_gsc_service()
            .urlInspection()
            .index()
            .inspect(body=request)
            .execute()
        )
        if not response or "inspectionResult" not in response:
            return f"No inspection data found for {page_url}."
        return _format_inspection(page_url, response["inspectionResult"])
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error inspecting URL: {str(error)}"


def _format_inspection(page_url: str, inspection: dict) -> str:
    lines = [f"URL Inspection for {page_url}:", "-" * 80]
    if "inspectionResultLink" in inspection:
        lines.append(f"Search Console Link: {inspection['inspectionResultLink']}")
        lines.append("-" * 80)
    index_status = inspection.get("indexStatusResult", {})
    lines.append(f"Indexing Status: {index_status.get('verdict', 'UNKNOWN')}")
    _append_index_status(lines, index_status)
    _append_referring_urls(lines, index_status)
    _append_rich_results(lines, inspection)
    return "\n".join(lines)


def _append_index_status(lines: list[str], status: dict) -> None:
    fields = (
        ("coverageState", "Coverage"),
        ("pageFetchState", "Page Fetch"),
        ("robotsTxtState", "Robots.txt"),
        ("indexingState", "Indexing State"),
        ("googleCanonical", "Google Canonical"),
    )
    if "coverageState" in status:
        lines.append(f"Coverage: {status['coverageState']}")
    if "lastCrawlTime" in status:
        lines.append(f"Last Crawled: {_format_datetime(status['lastCrawlTime'])}")
    for key, label in fields[1:]:
        if key in status:
            lines.append(f"{label}: {status[key]}")
    if (
        "userCanonical" in status
        and status.get("userCanonical") != status.get("googleCanonical")
    ):
        lines.append(f"User Canonical: {status['userCanonical']}")
    if "crawledAs" in status:
        lines.append(f"Crawled As: {status['crawledAs']}")


def _append_referring_urls(lines: list[str], status: dict) -> None:
    urls = status.get("referringUrls", [])
    if not urls:
        return
    lines.append("\nReferring URLs:")
    for url in urls[:5]:
        lines.append(f"- {url}")
    if len(urls) > 5:
        lines.append(f"... and {len(urls) - 5} more")


def _append_rich_results(lines: list[str], inspection: dict) -> None:
    if "richResultsResult" not in inspection:
        return
    rich = inspection["richResultsResult"]
    lines.append(f"\nRich Results: {rich.get('verdict', 'UNKNOWN')}")
    detected = rich.get("detectedItems", [])
    if detected:
        lines.append("Detected Rich Result Types:")
        for item in detected:
            lines.append(f"- {item.get('richResultType', 'Unknown')}")
            subitems = item.get("items", [])
            for subitem in subitems[:3]:
                if "name" in subitem:
                    lines.append(f"  - {subitem['name']}")
            if len(subitems) > 3:
                lines.append(f"  - ... and {len(subitems) - 3} more items")
    issues = rich.get("richResultsIssues", [])
    if issues:
        lines.append("\nRich Results Issues:")
        for issue in issues:
            severity = issue.get("severity", "Unknown")
            message = issue.get("message", "Unknown issue")
            lines.append(f"- [{severity}] {message}")


def _format_datetime(value: object) -> object:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, TypeError, ValueError):
        return value


async def batch_url_inspection(site_url: str, urls: str) -> str:
    """Inspect up to ten newline-delimited URLs."""
    try:
        service = auth.get_gsc_service()
        url_list = [url.strip() for url in urls.split("\n") if url.strip()]
        validation = _batch_validation(url_list)
        if validation is not None:
            return validation
        results = [_inspect_batch_url(service, site_url, page_url) for page_url in url_list]
        return f"Batch URL Inspection Results for {site_url}:\n\n" + "\n".join(results)
    except Exception as error:
        return f"Error performing batch inspection: {str(error)}"


def _inspect_batch_url(service: object, site_url: str, page_url: str) -> str:
    request = {"inspectionUrl": page_url, "siteUrl": site_url}
    try:
        response = service.urlInspection().index().inspect(body=request).execute()
        if not response or "inspectionResult" not in response:
            return f"{page_url}: No inspection data found"
        inspection = response["inspectionResult"]
        status = inspection.get("indexStatusResult", {})
        verdict = status.get("verdict", "UNKNOWN")
        coverage = status.get("coverageState", "Unknown")
        last_crawl = "Never"
        if "lastCrawlTime" in status:
            formatted = _format_datetime(status["lastCrawlTime"])
            try:
                last_crawl = datetime.strptime(
                    str(formatted), "%Y-%m-%d %H:%M"
                ).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                last_crawl = str(status["lastCrawlTime"])
        rich_results = _batch_rich_results(inspection)
        return (
            f"{page_url}:\n  Status: {verdict} - {coverage}\n"
            f"  Last Crawl: {last_crawl}\n  Rich Results: {rich_results}\n"
        )
    except Exception as error:
        return f"{page_url}: Error - {str(error)}"


def _batch_rich_results(inspection: dict) -> str:
    if "richResultsResult" not in inspection:
        return "None"
    rich = inspection["richResultsResult"]
    detected = rich.get("detectedItems", [])
    if rich.get("verdict") != "PASS" or not detected:
        return "None"
    return ", ".join(item.get("richResultType", "Unknown") for item in detected)


def _batch_validation(url_list: list[str]) -> str | None:
    if not url_list:
        return "No URLs provided for inspection."
    if len(url_list) > 10:
        return (
            f"Too many URLs provided ({len(url_list)}). Please limit to 10 URLs "
            "per batch to avoid API quota issues."
        )
    return None


async def check_indexing_issues(site_url: str, urls: str) -> str:
    """Check up to ten newline-delimited URLs for indexing issues."""
    try:
        service = auth.get_gsc_service()
        url_list = [url.strip() for url in urls.split("\n") if url.strip()]
        validation = _batch_validation(url_list)
        if validation is not None:
            return validation
        issues = {
            "not_indexed": [],
            "canonical_issues": [],
            "robots_blocked": [],
            "fetch_issues": [],
            "indexed": [],
        }
        for page_url in url_list:
            _classify_indexing_result(service, site_url, page_url, issues)
        return _format_indexing_issues(site_url, url_list, issues)
    except Exception as error:
        return f"Error checking indexing issues: {str(error)}"


def _classify_indexing_result(
    service: object,
    site_url: str,
    page_url: str,
    issues: dict[str, list[str]],
) -> None:
    request = {"inspectionUrl": page_url, "siteUrl": site_url}
    try:
        response = service.urlInspection().index().inspect(body=request).execute()
        if not response or "inspectionResult" not in response:
            issues["not_indexed"].append(f"{page_url} - No inspection data found")
            return
        status = response["inspectionResult"].get("indexStatusResult", {})
        verdict = status.get("verdict", "UNKNOWN")
        coverage = status.get("coverageState", "Unknown")
        if verdict != "PASS" or "not indexed" in coverage.lower() or "excluded" in coverage.lower():
            issues["not_indexed"].append(f"{page_url} - {coverage}")
        else:
            issues["indexed"].append(page_url)
        google_canonical = status.get("googleCanonical", "")
        user_canonical = status.get("userCanonical", "")
        if google_canonical and user_canonical and google_canonical != user_canonical:
            issues["canonical_issues"].append(
                f"{page_url} - Google chose: {google_canonical} instead of "
                f"user-declared: {user_canonical}"
            )
        if status.get("robotsTxtState", "") == "BLOCKED":
            issues["robots_blocked"].append(page_url)
        fetch_state = status.get("pageFetchState", "")
        if fetch_state != "SUCCESSFUL":
            issues["fetch_issues"].append(f"{page_url} - {fetch_state}")
    except Exception as error:
        issues["not_indexed"].append(f"{page_url} - Error: {str(error)}")


def _format_indexing_issues(
    site_url: str,
    url_list: list[str],
    issues: dict[str, list[str]],
) -> str:
    lines = [f"Indexing Issues Report for {site_url}:", "-" * 80]
    lines.extend(
        (
            f"Total URLs checked: {len(url_list)}",
            f"Indexed: {len(issues['indexed'])}",
            f"Not indexed: {len(issues['not_indexed'])}",
            f"Canonical issues: {len(issues['canonical_issues'])}",
            f"Robots.txt blocked: {len(issues['robots_blocked'])}",
            f"Fetch issues: {len(issues['fetch_issues'])}",
            "-" * 80,
        )
    )
    sections = (
        ("not_indexed", "\nNot Indexed URLs:"),
        ("canonical_issues", "\nCanonical Issues:"),
        ("robots_blocked", "\nRobots.txt Blocked URLs:"),
        ("fetch_issues", "\nFetch Issues:"),
    )
    for key, heading in sections:
        if issues[key]:
            lines.append(heading)
            lines.extend(f"- {item}" for item in issues[key])
    return "\n".join(lines)


__all__ = ["batch_url_inspection", "check_indexing_issues", "inspect_url_enhanced"]
