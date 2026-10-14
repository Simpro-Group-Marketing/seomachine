"""Shared helpers for the Chrome page-capture tests: a captured fact page and a workspace that cites it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from data_sources.modules.production import bom_build
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.page_capture import record_capture
from tests.production_bom_support import FACT_QUOTE, FACT_URL, make_workspace, nonconnector_spec
from tests.production_release_support import LINKED_ARTICLE_TEXT, PageTransport

CAPTURE_TEXT = f"Home | Example\n{FACT_QUOTE}.\nCrews log time from any phone.\n"
CAPTURE_DIR = "research/source-captures/field-service-software-2026-10-13"
CAPTURE_RECEIPT = f"{CAPTURE_DIR}/example.org-1.json"
BLOCKED = PageTransport({FACT_URL: (403, "")})


def write_capture(root: Path, *, url: str = FACT_URL, text: str = CAPTURE_TEXT, name: str = "example.org-1") -> str:
    """Record a capture receipt for ``url`` and return its workspace-relative path."""
    text_file = root / CAPTURE_DIR / f"{name}.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text(text, encoding="utf-8", newline="\n")
    receipt = root / CAPTURE_DIR / f"{name}.json"
    record_capture(url=url, title="Example report", text_file=text_file, output=receipt, workspace_root=root)
    return receipt.relative_to(root).as_posix()


def capture_workspace(root: Path, *, capture: str | None = CAPTURE_RECEIPT, **capture_args: Any) -> Layout:
    """A nonconnector workspace whose spec fact f1 carries a capture receipt."""
    spec = nonconnector_spec()
    if capture is not None:
        spec["facts"][0]["capture"] = capture
    layout = make_workspace(root, spec=spec)
    if capture is not None:
        write_capture(root, **capture_args)
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(LINKED_ARTICLE_TEXT, encoding="utf-8", newline="\n")
    return layout


def build_blocked(layout: Layout) -> dict[str, Any]:
    """Build the BOM while the fact page answers 403, and write it as the pipeline does."""
    bom = bom_build.build_bom(layout, transport=BLOCKED)
    bom_build._write_bom(layout, bom)
    return bom
