"""Blog publish gate shared by the WordPress and Grav publishers.

A blog post publishes only when its latest release record passed for the exact article bytes
(``record.verify_publishable``). After a successful live publish the publisher records each linked
BOM proof item in the customer-proof usage ledger (``usage_ledger.record_publish_use``).
WordPress landing pages keep the older publish-readiness gate and never come here.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

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


def record_release_use(file_path: str | Path, root: Path) -> list[dict[str, Any]]:
    """Record the published article's linked BOM proof in the usage ledger; return the new entries."""
    article = Path(file_path).resolve()
    return record_publish_use(article, root, published_path=article.relative_to(root).as_posix())


def retired_blog_flags(args: Any) -> list[str]:
    """CLI flags of the retired readiness gate that a blog post was given."""
    return [
        "--" + name.replace("_", "-") for name in RETIRED_BLOG_GATE_ARGS if getattr(args, name, None) is not None
    ]


__all__ = [
    "REPO_ROOT",
    "RETIRED_BLOG_GATE_ARGS",
    "ensure_released_bytes",
    "record_release_use",
    "release_root",
    "require_release",
    "retired_blog_flags",
]
