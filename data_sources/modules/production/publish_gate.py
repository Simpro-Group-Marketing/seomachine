"""Blog publish gate shared by the WordPress and Grav publishers.

A blog post publishes only when its latest release record passed for the exact article bytes
(``record.verify_publishable``). After a successful live publish the publisher records each linked
BOM proof item in the customer-proof usage ledger (``usage_ledger.record_publish_use``).
WordPress landing pages keep the older publish-readiness gate; ``require_landing_page`` admits
only a file that resolves as a landing page, so a blog cannot take that route.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from data_sources.modules.context_binding_guard import resolve_artifact_kind
from data_sources.modules.production.layout import Layout, LayoutError
from data_sources.modules.production.record import verify_publishable
from data_sources.modules.production.usage_ledger import record_publish_use

REPO_ROOT = Path(__file__).resolve().parents[3]
RETIRED_BLOG_GATE_ARGS = ("proof_sidecar", "context_request", "context_pack", "context_receipt", "assembly_bom", "vault_root")


def release_root(workspace_root: str | Path | None) -> Path:
    return Path(workspace_root).resolve() if workspace_root is not None else REPO_ROOT


def require_release(file_path: str | Path, root: Path, context: str) -> dict[str, Any]:
    """Return the passing release record, or raise ValueError naming the reason and the publish step."""
    try:
        return verify_publishable(Path(file_path).resolve(), root)
    except ValueError as error:
        raise ValueError(f"Release record check failed before {context}: {error}") from error


def ensure_released_bytes(record: Mapping[str, Any] | None, sha256: str, path: str | Path) -> None:
    """The bytes about to be published must be the bytes the passing release checked."""
    if record is not None and (record.get("article") or {}).get("sha256") != sha256:
        raise ValueError(f"article changed since its passing release: {path}; release it again")


def _is_production_article(file_path: str | Path, root: Path) -> bool:
    try:
        Layout.for_article(Path(file_path).resolve(), root)
    except LayoutError:
        return False
    return True


def require_landing_page(file_path: str | Path, root: Path) -> None:
    """Allow the page gate only for a resolved landing page that is not a drafts/rewrites article."""
    content = Path(file_path).read_text(encoding="utf-8")
    kind = resolve_artifact_kind(content, article_path=file_path)
    if kind != "landing_page" or _is_production_article(file_path, root):
        raise ValueError(
            f"{file_path} does not resolve as a landing page (artifact kind: {kind or 'unknown'}); "
            "blogs need a passing release record and publish as posts"
        )


def record_release_use(file_path: str | Path, root: Path) -> list[dict[str, Any]]:
    """Record the published article's linked BOM proof in the usage ledger; return the new entries."""
    article = Path(file_path).resolve()
    return record_publish_use(article, root, published_path=article.relative_to(root).as_posix())


def record_proof_use(file_path: str | Path, root: Path | None) -> str:
    """After a successful live publish, record proof use; a failure is a warning, never a failed publish."""
    if root is None:
        return ""
    try:
        record_release_use(file_path, root)
    except Exception as error:  # the publish already happened; report, do not fail it
        return f"published, but the usage ledger was not updated: {error}; add the entry by hand"
    return ""


def retired_blog_args(values: Mapping[str, Any]) -> list[str]:
    """Retired readiness-gate arguments that a blog post was given (non-None values)."""
    return [name for name in RETIRED_BLOG_GATE_ARGS if values.get(name) is not None]


def retired_blog_flags(args: Any) -> list[str]:
    """CLI flags of the retired readiness gate that a blog post was given."""
    return ["--" + name.replace("_", "-") for name in retired_blog_args(vars(args))]


__all__ = [
    "REPO_ROOT",
    "RETIRED_BLOG_GATE_ARGS",
    "ensure_released_bytes",
    "record_proof_use",
    "record_release_use",
    "require_landing_page",
    "release_root",
    "require_release",
    "retired_blog_args",
    "retired_blog_flags",
]
