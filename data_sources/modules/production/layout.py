"""Article layout and production run identity for the blog pipeline.

Usage: python -m data_sources.modules.production.layout <article> [--workspace-root DIR]

Prints the article's slug, date, workflow mode, production run id (minted and stored when
none exists), and every layout path as JSON. Exit codes: 0 printed, 2 bad layout or run state.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from data_sources.modules.blog_assembly_contract import atomic_write_json

RUN_STATE_SCHEMA = "simpro-production-run/v1"
_ARTICLE_NAME = re.compile(r"^(?P<slug>[a-z0-9][a-z0-9-]*)-(?P<date>\d{4}-\d{2}-\d{2})\.md$")
_WORKFLOW_MODES = {"drafts": "new", "rewrites": "rewrite"}


class LayoutError(ValueError):
    """Raised when an article path does not match the pipeline layout."""


@dataclass(frozen=True)
class Layout:
    root: Path
    article: Path
    slug: str
    date: str
    workflow_mode: str

    @classmethod
    def for_article(cls, article: str | Path, root: str | Path) -> Layout:
        root_path = Path(root).resolve()
        article_path = Path(article)
        if not article_path.is_absolute():
            article_path = root_path / article_path
        article_path = article_path.resolve()
        folder = article_path.parent
        if folder.parent != root_path or folder.name not in _WORKFLOW_MODES:
            raise LayoutError(
                f"article must live directly in {root_path / 'drafts'} or "
                f"{root_path / 'rewrites'}, found folder: {folder}"
            )
        match = _ARTICLE_NAME.match(article_path.name)
        if match is None:
            raise LayoutError(
                f"article filename must match <slug>-YYYY-MM-DD.md, found: {article_path.name}"
            )
        article_date = match.group("date")
        try:
            datetime.date.fromisoformat(article_date)
        except ValueError as exc:
            raise LayoutError(f"invalid article date in filename: {article_date}") from exc
        return cls(
            root=root_path,
            article=article_path,
            slug=match.group("slug"),
            date=article_date,
            workflow_mode=_WORKFLOW_MODES[folder.name],
        )

    @property
    def bom(self) -> Path:
        return self._research(f"production-bom-{self.slug}-{self.date}.json")

    @property
    def bom_spec(self) -> Path:
        return self._research(f"production-bom-spec-{self.slug}-{self.date}.json")

    @property
    def serp_evidence(self) -> Path:
        return self._research(f"serp-evidence-{self.slug}-{self.date}.json")

    @property
    def serp_coverage(self) -> Path:
        return self._research(f"serp-coverage-{self.slug}-{self.date}.json")

    @property
    def keyword_decision(self) -> Path:
        return self._research(f"semrush-keyword-decision-{self.slug}-{self.date}.json")

    @property
    def keyword_shortlist(self) -> Path:
        return self._research(f"keyword-shortlist-{self.slug}-{self.date}.json")

    @property
    def paa_artifact(self) -> Path:
        return self._research(f"paa-evidence-{self.slug}-{self.date}.json")

    @property
    def context_pack(self) -> Path:
        return self._research(f"context-pack-{self.slug}.json")

    @property
    def context_receipt(self) -> Path:
        return self._research(f"context-receipt-{self.slug}.json")

    @property
    def customer_proof_evidence(self) -> Path:
        return self._research(f"customer-proof-selector-evidence-{self.slug}.json")

    @property
    def nonvault_customer_proof_evidence(self) -> Path:
        return self._research(f"nonvault-customer-proof-selector-evidence-{self.slug}.json")

    @property
    def run_state(self) -> Path:
        return self.root / "research" / "runs" / f"{self.slug}-{self.date}.json"

    def release_dirs(self, run_id: str) -> list[Path]:
        """Existing release directories for this run, in release-number order."""
        return [path for _number, path in self._numbered_releases(run_id) if path.is_dir()]

    def release_dir(self, run_id: str) -> Path:
        """Return the name after the highest release number for this run, counting a file or a
        directory at any release name; does not create it."""
        parent, base = self._release_base(run_id)
        numbers = [number for number, _path in self._numbered_releases(run_id)]
        return parent / f"{base}-{max(numbers, default=0) + 1}"

    def _numbered_releases(self, run_id: str) -> list[tuple[int, Path]]:
        parent, base = self._release_base(run_id)
        pattern = re.compile(re.escape(base) + r"-(\d+)")
        if not parent.is_dir():
            return []
        return sorted(
            (int(match.group(1)), path) for path in parent.iterdir() if (match := pattern.fullmatch(path.name))
        )

    def _release_base(self, run_id: str) -> tuple[Path, str]:
        return self.root / "research" / "releases", f"{self.slug}-{self.date}-{run_id[:8]}"

    def _research(self, name: str) -> Path:
        return self.root / "research" / name


def load_or_create_run_id(layout: Layout, *, run_id: str | None = None) -> str:
    """Return the persisted run id, minting and storing one when none exists."""
    if run_id:
        _write_run_state(layout, run_id)
        return run_id
    stored = _read_stored_run_id(layout.run_state)
    if stored:
        return stored
    minted = str(uuid.uuid4())
    _write_run_state(layout, minted)
    return minted


def stored_run_id(layout: Layout) -> str | None:
    """Return the persisted run id without minting one; None when no run state exists."""
    return _read_stored_run_id(layout.run_state)


def stored_bom_sha256(layout: Layout) -> str | None:
    """The sha256 of the BOM the pipeline last wrote for this run; None when none was recorded."""
    payload = _read_run_state(layout.run_state)
    value = payload.get("bom_sha256") if payload else None
    return value if isinstance(value, str) and value else None


def record_bom_sha256(layout: Layout, bom_sha256: str) -> None:
    """Record the hash of a BOM the pipeline just wrote, keeping the run id."""
    _write_run_state(layout, load_or_create_run_id(layout), bom_sha256)


def _read_run_state(path: Path) -> dict | None:
    """Return the run state object, None when no run state exists, or raise on an invalid file."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LayoutError(f"run state {path} is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise LayoutError(f"run state {path} is not a JSON object")
    value = payload.get("run_id")
    if not isinstance(value, str) or not value:
        raise LayoutError(f"run state {path} has no non-empty string run_id")
    return payload


def _read_stored_run_id(path: Path) -> str | None:
    payload = _read_run_state(path)
    return payload["run_id"] if payload else None


def _write_run_state(layout: Layout, run_id: str, bom_sha256: str | None = None) -> None:
    """Write the run state; a new run id carries no BOM hash until a pipeline BOM write records one."""
    state = {"schema": RUN_STATE_SCHEMA, "run_id": run_id}
    if bom_sha256:
        state["bom_sha256"] = bom_sha256
    layout.run_state.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(layout.run_state, state)


_PRINTED_PATHS = (
    "article", "run_state", "bom", "bom_spec", "serp_evidence", "serp_coverage", "keyword_decision",
    "keyword_shortlist", "paa_artifact", "context_pack", "context_receipt", "customer_proof_evidence",
    "nonvault_customer_proof_evidence",
)


def describe(layout: Layout) -> dict:
    """The article identity, its run id (minted when missing), and every layout path, workspace-relative."""
    return {
        "slug": layout.slug,
        "date": layout.date,
        "workflow_mode": layout.workflow_mode,
        "run_id": load_or_create_run_id(layout),
        "paths": {name: getattr(layout, name).relative_to(layout.root).as_posix() for name in _PRINTED_PATHS},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="layout", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("article", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    try:
        layout = Layout.for_article(args.article, (args.workspace_root or Path.cwd()).resolve())
        payload = describe(layout)
    except (LayoutError, OSError) as error:
        print(f"layout: {error}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
