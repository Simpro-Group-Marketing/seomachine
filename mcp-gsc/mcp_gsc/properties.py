"""Search Console property listing and mutation tools."""

from __future__ import annotations

import json

from googleapiclient.errors import HttpError

from . import auth


async def list_properties() -> str:
    """Retrieve and format the user's Search Console properties."""
    try:
        site_list = auth.get_gsc_service().sites().list().execute()
        sites = site_list.get("siteEntry", [])
        if not sites:
            return "No Search Console properties found."
        lines = []
        for site in sites:
            site_url = site.get("siteUrl", "Unknown")
            permission = site.get("permissionLevel", "Unknown permission")
            lines.append(f"- {site_url} ({permission})")
        return "\n".join(lines)
    except FileNotFoundError:
        return (
            "Error: Service account credentials file not found.\n\n"
            "To access Google Search Console, please:\n"
            "1. Create a service account in Google Cloud Console\n"
            "2. Download the JSON credentials file\n"
            "3. Save it as 'service_account_credentials.json' in the same "
            "directory as this script\n"
            "4. Share your GSC properties with the service account email"
        )
    except Exception as error:
        return f"Error retrieving properties: {str(error)}"


async def add_site(site_url: str) -> str:
    """Add a site to the authenticated Search Console account."""
    try:
        response = auth.get_gsc_service().sites().add(siteUrl=site_url).execute()
        lines = [f"Site {site_url} has been added to Search Console."]
        if "permissionLevel" in response:
            lines.append(f"Permission level: {response['permissionLevel']}")
        return "\n".join(lines)
    except HttpError as error:
        return _add_site_http_error(site_url, error)
    except Exception as error:
        return f"Error adding site: {str(error)}"


def _add_site_http_error(site_url: str, error: HttpError) -> str:
    code, message, reason = _http_error_parts(error)
    if code == 409:
        return f"Site {site_url} is already added to Search Console."
    common = _common_http_error(code, message, reason, "add this site. Please verify ownership first.")
    if common is not None:
        return common
    return f"Error adding site (HTTP {code}): {message}"


async def delete_site(site_url: str) -> str:
    """Remove a site from the authenticated Search Console account."""
    try:
        auth.get_gsc_service().sites().delete(siteUrl=site_url).execute()
        return f"Site {site_url} has been removed from Search Console."
    except HttpError as error:
        return _delete_site_http_error(site_url, error)
    except Exception as error:
        return f"Error removing site: {str(error)}"


def _delete_site_http_error(site_url: str, error: HttpError) -> str:
    code, message, reason = _http_error_parts(error)
    if code == 404:
        return f"Site {site_url} was not found in Search Console."
    common = _common_http_error(code, message, reason, "remove this site.")
    if common is not None:
        return common
    return f"Error removing site (HTTP {code}): {message}"


def _common_http_error(
    code: int,
    message: str,
    reason: str,
    forbidden_action: str,
) -> str | None:
    if code == 403:
        by_reason = {
            "forbidden": f"Error: You don't have permission to {forbidden_action}",
            "quotaExceeded": "Error: API quota exceeded. Please try again later.",
        }
        return by_reason.get(reason, f"Error: Permission denied. {message}")
    if code == 400:
        if reason == "invalidParameter":
            return "Error: Invalid site URL format. Please check the URL format and try again."
        return f"Error: Bad request. {message}"
    return {
        401: "Error: Unauthorized. Please check your credentials.",
        429: "Error: Too many requests. Please try again later.",
        500: "Error: Internal server error from Google Search Console API. Please try again later.",
        503: (
            "Error: Service unavailable. Google Search Console API is currently "
            "down. Please try again later."
        ),
    }.get(code)


def _http_error_parts(error: HttpError) -> tuple[int, str, str]:
    content = json.loads(error.content.decode("utf-8"))
    details = content.get("error", {})
    return (
        error.resp.status,
        details.get("message", str(error)),
        details.get("errors", [{}])[0].get("reason", ""),
    )


async def get_site_details(site_url: str) -> str:
    """Get detailed information about a Search Console property."""
    try:
        site_info = auth.get_gsc_service().sites().get(siteUrl=site_url).execute()
        lines = [f"Site details for {site_url}:", "-" * 50]
        lines.append(
            f"Permission level: {site_info.get('permissionLevel', 'Unknown')}"
        )
        if "siteVerificationInfo" in site_info:
            verification = site_info["siteVerificationInfo"]
            lines.append(
                "Verification state: "
                f"{verification.get('verificationState', 'Unknown')}"
            )
            if "verifiedUser" in verification:
                lines.append(f"Verified by: {verification['verifiedUser']}")
            if "verificationMethod" in verification:
                lines.append(
                    f"Verification method: {verification['verificationMethod']}"
                )
        if "ownershipInfo" in site_info:
            ownership = site_info["ownershipInfo"]
            lines.append("\nOwnership Information:")
            lines.append(f"Owner: {ownership.get('owner', 'Unknown')}")
            if "verificationMethod" in ownership:
                lines.append(
                    f"Ownership verification: {ownership['verificationMethod']}"
                )
        return "\n".join(lines)
    except Exception as error:
        return f"Error retrieving site details: {str(error)}"


__all__ = ["add_site", "delete_site", "get_site_details", "list_properties"]
