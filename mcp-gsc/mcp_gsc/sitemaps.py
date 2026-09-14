"""Google Search Console sitemap tools."""

from __future__ import annotations

import logging
from datetime import datetime

import mcp_gsc.auth as auth
from .formatting import site_not_found_error

logger = logging.getLogger(__name__)


async def get_sitemaps(site_url: str) -> str:
    """List sitemaps using the compact legacy format."""
    try:
        response = auth.get_gsc_service().sitemaps().list(siteUrl=site_url).execute()
        if not response.get("sitemap"):
            return f"No sitemaps found for {site_url}."
        lines = [
            f"Sitemaps for {site_url}:",
            "-" * 80,
            "Path | Last Downloaded | Status | Indexed URLs | Errors",
            "-" * 80,
        ]
        for sitemap in response.get("sitemap", []):
            last_downloaded = _format_date(sitemap.get("lastDownloaded", "Never"))
            errors = int(sitemap.get("errors", 0))
            status = "Has errors" if "errors" in sitemap and errors > 0 else "Valid"
            lines.append(
                f"{sitemap.get('path', 'Unknown')} | {last_downloaded} | {status} | "
                f"{_web_count(sitemap)} | {errors}"
            )
        return "\n".join(lines)
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error retrieving sitemaps: {str(error)}"


async def list_sitemaps_enhanced(
    site_url: str, sitemap_index: str = None
) -> str:
    """List sitemaps with submission, type, error, and warning details."""
    try:
        resource = auth.get_gsc_service().sitemaps()
        if sitemap_index:
            response = resource.list(
                siteUrl=site_url, sitemapIndex=sitemap_index
            ).execute()
            source = f"child sitemaps from index: {sitemap_index}"
        else:
            response = resource.list(siteUrl=site_url).execute()
            source = "all submitted sitemaps"
        if not response.get("sitemap"):
            return f"No sitemaps found for {site_url}" + (
                f" in index {sitemap_index}" if sitemap_index else "."
            )
        entries = response.get("sitemap", [])
        lines = [
            f"Sitemaps for {site_url} ({source}):",
            "-" * 100,
            "Path | Last Submitted | Last Downloaded | Type | URLs | Errors | Warnings",
            "-" * 100,
        ]
        lines.extend(_enhanced_row(sitemap) for sitemap in entries)
        pending_count = sum(1 for item in entries if item.get("isPending", False))
        if pending_count > 0:
            lines.append(
                f"\nNote: {pending_count} sitemaps are still pending processing by Google."
            )
        return "\n".join(lines)
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error retrieving sitemaps: {str(error)}"


def _format_date(value):
    if value == "Never":
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, TypeError, ValueError):
        return value


def _web_count(sitemap):
    for content in sitemap.get("contents", []):
        if content.get("type") == "web":
            return content.get("submitted", "0")
    return "N/A"


def _enhanced_row(sitemap):
    sitemap_type = "Index" if sitemap.get("isSitemapsIndex", False) else "Sitemap"
    return (
        f"{sitemap.get('path', 'Unknown')} | "
        f"{_format_date(sitemap.get('lastSubmitted', 'Never'))} | "
        f"{_format_date(sitemap.get('lastDownloaded', 'Never'))} | {sitemap_type} | "
        f"{_web_count(sitemap)} | {int(sitemap.get('errors', 0))} | "
        f"{int(sitemap.get('warnings', 0))}"
    )


async def get_sitemap_details(site_url: str, sitemap_url: str) -> str:
    """Get details for one submitted sitemap."""
    try:
        details = (
            auth.get_gsc_service()
            .sitemaps()
            .get(siteUrl=site_url, feedpath=sitemap_url)
            .execute()
        )
        if not details:
            return f"No details found for sitemap {sitemap_url}."
        is_index = details.get("isSitemapsIndex", False)
        lines = [
            f"Sitemap Details for {sitemap_url}:",
            "-" * 80,
            f"Type: {'Sitemap Index' if is_index else 'Sitemap'}",
            "Status: "
            + (
                "Pending processing"
                if details.get("isPending", False)
                else "Processed"
            ),
        ]
        _append_detail_dates(lines, details)
        lines.extend(
            (
                f"Errors: {details.get('errors', 0)}",
                f"Warnings: {details.get('warnings', 0)}",
            )
        )
        if details.get("contents"):
            lines.append("\nContent Breakdown:")
            for content in details["contents"]:
                lines.append(
                    f"- {content.get('type', 'Unknown').upper()}: "
                    f"{content.get('submitted', 0)} submitted, "
                    f"{content.get('indexed', 'N/A')} indexed"
                )
        if is_index:
            lines.extend(
                (
                    "\nThis is a sitemap index. To list child sitemaps, use:",
                    f"list_sitemaps_enhanced with sitemap_index={sitemap_url}",
                )
            )
        return "\n".join(lines)
    except Exception as error:
        return f"Error retrieving sitemap details: {str(error)}"


def _append_detail_dates(lines, details):
    for field, label in (
        ("lastSubmitted", "Last Submitted"),
        ("lastDownloaded", "Last Downloaded"),
    ):
        if field in details:
            lines.append(f"{label}: {_format_date(details[field])}")


async def submit_sitemap(site_url: str, sitemap_url: str) -> str:
    """Submit or resubmit a sitemap."""
    try:
        resource = auth.get_gsc_service().sitemaps()
        resource.submit(siteUrl=site_url, feedpath=sitemap_url).execute()
        try:
            details = resource.get(siteUrl=site_url, feedpath=sitemap_url).execute()
            lines = [f"Successfully submitted sitemap: {sitemap_url}"]
            if "lastSubmitted" in details:
                lines.append(
                    f"Submission time: {_format_date(details['lastSubmitted'])}"
                )
            pending = details.get("isPending", True)
            lines.extend(
                (
                    f"Status: {'Pending processing' if pending else 'Processing started'}",
                    "\nNote: Google may take some time to process the sitemap. "
                    "Check back later for full details.",
                )
            )
            return "\n".join(lines)
        except Exception as error:
            logger.warning(
                "Sitemap submitted, but follow-up details were unavailable: %s", error
            )
            return (
                f"Successfully submitted sitemap: {sitemap_url}\n\n"
                "Google will queue it for processing."
            )
    except Exception as error:
        return f"Error submitting sitemap: {str(error)}"


async def delete_sitemap(site_url: str, sitemap_url: str) -> str:
    """Delete a submitted sitemap from Search Console."""
    try:
        resource = auth.get_gsc_service().sitemaps()
        try:
            resource.get(siteUrl=site_url, feedpath=sitemap_url).execute()
        except Exception as error:
            if "404" in str(error):
                return (
                    f"Sitemap not found: {sitemap_url}. It may have already been "
                    "deleted or was never submitted."
                )
            raise
        resource.delete(siteUrl=site_url, feedpath=sitemap_url).execute()
        return (
            f"Successfully deleted sitemap: {sitemap_url}\n\n"
            "Note: This only removes the sitemap from Search Console. Any URLs "
            "already indexed will remain in Google's index."
        )
    except Exception as error:
        return f"Error deleting sitemap: {str(error)}"


async def manage_sitemaps(
    site_url: str,
    action: str,
    sitemap_url: str = None,
    sitemap_index: str = None,
) -> str:
    """Dispatch a sitemap list, details, submit, or delete action."""
    try:
        action = action.lower().strip()
        valid_actions = ["list", "details", "submit", "delete"]
        if action not in valid_actions:
            return f"Invalid action: {action}. Please use one of: {', '.join(valid_actions)}"
        if action in ["details", "submit", "delete"] and not sitemap_url:
            return f"The {action} action requires a sitemap_url parameter."
        if action == "list":
            return await list_sitemaps_enhanced(site_url, sitemap_index)
        if action == "details":
            return await get_sitemap_details(site_url, sitemap_url)
        if action == "submit":
            return await submit_sitemap(site_url, sitemap_url)
        return await delete_sitemap(site_url, sitemap_url)
    except Exception as error:
        return f"Error managing sitemaps: {str(error)}"


__all__ = [
    "delete_sitemap",
    "get_sitemap_details",
    "get_sitemaps",
    "list_sitemaps_enhanced",
    "manage_sitemaps",
    "submit_sitemap",
]
