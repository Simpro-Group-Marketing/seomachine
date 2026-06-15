"""
Proof sidecar helpers.

Validation sidecars hold non-public proof blocks such as PAA provenance,
Metric Proof Packs, Source Maps, and Customer Proof Packs. Public article
copy stays clean, while proof-aware gates can still read the evidence contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


WORKING_CONTENT_DIRS = {
    "drafts",
    "rewrites",
    "published",
    "review-required",
    "landing-pages",
    "output",
}


def default_sidecar_path(source_path: str | Path) -> Path:
    """Return the default validation sidecar path for a content artifact."""
    source = Path(source_path)
    root = _content_root(source)
    return root / "research" / f"validation-{source.stem}.md"


def resolve_sidecar_path(
    source_path: str | Path | None = None,
    proof_sidecar: str | Path | None = None,
) -> Optional[Path]:
    """Resolve an explicit or default sidecar path."""
    if proof_sidecar:
        return _resolve_explicit_sidecar(Path(proof_sidecar), source_path)
    if source_path:
        return default_sidecar_path(source_path)
    return None


def load_sidecar_content(
    source_path: str | Path | None = None,
    proof_sidecar: str | Path | None = None,
) -> str:
    """
    Load proof sidecar content.

    Missing default sidecars return an empty string so legacy inline-proof
    workflows keep working. Missing explicit sidecars raise FileNotFoundError,
    because an explicit CLI argument should fail loudly.
    """
    sidecar_path = resolve_sidecar_path(source_path, proof_sidecar)
    if sidecar_path is None:
        return ""
    if not sidecar_path.exists():
        if proof_sidecar:
            raise FileNotFoundError(f"Proof sidecar not found: {sidecar_path}")
        return ""
    return sidecar_path.read_text(encoding="utf-8")


def compose_with_sidecar(content: str, proof_content: str | None = None) -> str:
    """Append sidecar proof content behind a clear non-public delimiter."""
    if not proof_content:
        return content
    return "\n\n".join(
        [
            content.rstrip(),
            "<!-- SEO_MACHINE_PROOF_SIDECAR_START -->",
            proof_content.strip(),
            "<!-- SEO_MACHINE_PROOF_SIDECAR_END -->",
        ]
    )


def _content_root(source_path: Path) -> Path:
    source = Path(source_path)
    if source.parent.name in WORKING_CONTENT_DIRS:
        return source.parent.parent
    return source.parent


def _resolve_explicit_sidecar(
    proof_sidecar: Path,
    source_path: str | Path | None,
) -> Path:
    if proof_sidecar.is_absolute():
        return proof_sidecar

    candidates = [Path.cwd() / proof_sidecar]
    if source_path:
        source = Path(source_path).resolve()
        candidates.append(source.parent / proof_sidecar)
        candidates.append(_content_root(source) / proof_sidecar)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
