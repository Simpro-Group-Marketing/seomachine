"""Stand-ins for the blog publish gate in publisher tests that do not build a real release record."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

GATE = "data_sources.modules.production.publish_gate"


def passing_record(article: Any, root: Any = None) -> dict[str, Any]:
    """A passing release record for the article bytes on disk now."""
    return {"passed": True, "article": {"sha256": hashlib.sha256(Path(article).read_bytes()).hexdigest()}}
