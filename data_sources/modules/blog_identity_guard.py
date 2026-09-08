"""Validate the explicit identity and freshness contract for blog artifacts."""

from __future__ import annotations

from datetime import date
from typing import Any

try:
    from . import blog_assembly_contract
    from .artifact_detection import extract_frontmatter
    from .frontmatter import FrontmatterError
    from .guard_common import Finding, make_finding
    from .named_person import is_named_person
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_contract
    from artifact_detection import extract_frontmatter
    from frontmatter import FrontmatterError
    from guard_common import Finding, make_finding
    from named_person import is_named_person


BLOG_REQUIRED_FIELDS = (
    "artifact_type",
    "brand",
    "title",
    "objective",
    "audience",
    "region",
    "last_updated",
    "schema_notes",
)
PLACEHOLDER_VALUES = frozenset(
    {
        "unknown",
        "not provided",
        "not available",
        "n/a",
        "na",
        "none",
        "tbd",
        "todo",
        "placeholder",
    }
)


def check_article(
    content: str,
    *,
    assembly_date: date | str | None = None,
) -> list[Finding]:
    """Return stable findings for an explicit blog identity contract."""
    try:
        metadata = extract_frontmatter(content)
    except FrontmatterError as error:
        return [_finding("blog_identity_frontmatter_invalid", str(error))]
    artifact_type = str(metadata.get("artifact_type") or "").strip()
    normalized_kind = _normalize_kind(artifact_type)
    if normalized_kind != "blog":
        return []

    findings: list[Finding] = []
    for field in BLOG_REQUIRED_FIELDS:
        value = metadata.get(field)
        if not _present(value):
            findings.append(
                _finding(
                    f"blog_identity_{field}_missing",
                    f"Blog frontmatter requires a non-empty {field} field.",
                )
            )
            continue
        if _is_placeholder(value):
            findings.append(
                _finding(
                    f"blog_identity_{field}_placeholder",
                    f"Blog frontmatter {field} cannot use a placeholder value.",
                )
            )

    if "author" in metadata:
        author = metadata.get("author")
        if not isinstance(author, str) or not author.strip():
            findings.append(
                _finding(
                    "blog_identity_author_empty",
                    "Blog frontmatter author must be omitted when no named author is available.",
                )
            )
        elif _is_placeholder(author):
            findings.append(
                _finding(
                    "blog_identity_author_placeholder",
                    "Blog frontmatter author cannot use a placeholder value.",
                )
            )
        elif not is_named_person(author):
            findings.append(
                _finding(
                    "blog_identity_author_not_named_person",
                    "Blog frontmatter author must identify a named person, not an organization, team, or role byline.",
                )
            )

    updated = str(metadata.get("last_updated") or "").strip()
    parsed_updated: date | None = None
    if updated:
        try:
            parsed_updated = date.fromisoformat(updated)
        except ValueError:
            findings.append(
                _finding(
                    "blog_identity_last_updated_invalid",
                    "Blog last_updated must be a valid ISO date in YYYY-MM-DD form.",
                )
            )
        else:
            if parsed_updated.isoformat() != updated:
                parsed_updated = None
                findings.append(
                    _finding(
                        "blog_identity_last_updated_invalid",
                        "Blog last_updated must be a valid ISO date in YYYY-MM-DD form.",
                    )
                )
    expected = _parse_assembly_date(assembly_date)
    if expected is not None and expected != blog_assembly_contract.current_utc_date():
        findings.append(
            _finding(
                "blog_identity_assembly_date_not_current",
                "Blog assembly_date must equal the current UTC date.",
            )
        )
    if expected is not None and parsed_updated is not None and parsed_updated > expected:
        findings.append(
            _finding(
                "blog_identity_last_updated_mismatch",
                "Blog last_updated cannot be later than the current assembly date.",
            )
        )
    return sorted(findings, key=lambda item: str(item["rule_id"]))


def _parse_assembly_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _normalize_kind(value: str) -> str | None:
    normalized = value.casefold().replace("-", "_").replace(" ", "_")
    if normalized in {"blog", "article", "post", "posts"}:
        return "blog"
    if normalized in {"landing_page", "landing", "landingpage", "page", "pages"}:
        return "landing_page"
    return None


def _present(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value) and all(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def _is_placeholder(value: Any) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(str(item).strip().casefold() in PLACEHOLDER_VALUES for item in values)


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Supply the exact current blog identity before readiness.",
    )
