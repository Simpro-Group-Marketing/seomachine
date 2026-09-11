"""Early bounded validation for primary blog-release text inputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .limits import ARTICLE_MAX_BYTES, SIDECAR_MAX_BYTES, validate_text_artifact


def validate_release_text_inputs(
    required_files: Mapping[str, str | Path],
    *,
    workspace_root: Path,
) -> None:
    """Validate article and sidecar before release output creation."""
    limits = {"article": ARTICLE_MAX_BYTES, "proof_sidecar": SIDECAR_MAX_BYTES}
    for label, max_bytes in limits.items():
        validate_text_artifact(
            required_files[label],
            label=label,
            workspace_root=workspace_root,
            max_bytes=max_bytes,
        )
