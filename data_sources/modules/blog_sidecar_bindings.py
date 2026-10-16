"""Validate exact sidecar bindings to selector and Fred evidence artifacts."""

from __future__ import annotations

import re


SELECTOR_EVIDENCE_LINE_RE = re.compile(
    r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
    r"SHA-256:\s*([0-9a-f]{64})\s*$"
)
FRED_SELECTION_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]+Fred Voccola Authority Selection[ \t]*\r?\n"
    r".*?(?=^##[ \t]+|\Z)"
)


