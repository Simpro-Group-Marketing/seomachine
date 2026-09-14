"""Run-scoped publish-readiness infrastructure.

The public command remains ``data_sources.modules.publish_readiness``.  This
package contains the small, single-responsibility building blocks used by that
compatibility facade and the atomic blog-release workflow.
"""

from .artifact_store import InstrumentedArtifactStore
from .artifact_views import (
    ArtifactBytesView,
    ArtifactJsonView,
    ArtifactMarkdownView,
    ArtifactTextView,
    FileIdentity,
)
from .inputs import ReadinessInputs
from .git_registry import GitRegistryState
from .session import ValidationSession
from .telemetry import ReadinessTelemetry

__all__ = [
    "ArtifactBytesView",
    "ArtifactJsonView",
    "ArtifactMarkdownView",
    "ArtifactTextView",
    "FileIdentity",
    "GitRegistryState",
    "InstrumentedArtifactStore",
    "ReadinessInputs",
    "ReadinessTelemetry",
    "ValidationSession",
]
