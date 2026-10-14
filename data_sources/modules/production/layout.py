"""Article layout and production run identity for the blog pipeline."""

from __future__ import annotations

import datetime
import json
import re
import uuid
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
        parent, base = self._release_base(run_id)
        pattern = re.compile(re.escape(base) + r"-(\d+)")
        if not parent.is_dir():
            return []
        numbered = [
            (int(match.group(1)), path)
            for path in parent.iterdir()
            if (match := pattern.fullmatch(path.name)) and path.is_dir()
        ]
        return [path for _number, path in sorted(numbered)]

    def release_dir(self, run_id: str) -> Path:
        """Return the directory after the highest-numbered release for this run; does not create it."""
        parent, base = self._release_base(run_id)
        existing = self.release_dirs(run_id)
        number = int(existing[-1].name.rsplit("-", 1)[1]) + 1 if existing else 1
        return parent / f"{base}-{number}"

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


def _read_stored_run_id(path: Path) -> str | None:
    """Return the stored run id, None when no run state exists, or raise on an invalid file."""
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
    return value


def _write_run_state(layout: Layout, run_id: str) -> None:
    layout.run_state.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(layout.run_state, {"schema": RUN_STATE_SCHEMA, "run_id": run_id})
