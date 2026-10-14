"""Customer-proof usage ledger entries recorded by the publishers after a successful live publish.

``record_publish_use`` trusts only the passing release record (``record.verify_publishable``),
reads that release's BOM, and appends one ``uses[]`` entry for each BOM proof item whose URL the
article body links. Entries are deduped on proof id and artifact path (one use per article,
whatever the day or publisher), and the read-modify-write holds an exclusive ``<ledger>.lock`` file (holding the holder's pid and
``created_at``) so concurrent publishes cannot lose an entry. A lock older than
``LOCK_STALE_SECONDS`` or whose holder process has exited is broken; a fresh lock held by a live
process is never broken. The release itself
never writes the ledger; the WordPress and Grav publishers call this only after the live write
succeeded, never on a dry run, refusal, or failure.
"""

from __future__ import annotations

import ctypes
import datetime
import json
import os
import re
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import DEFAULT_JSON_MAX_BYTES, current_utc_date
from data_sources.modules.bounded_io import atomic_write_text
from data_sources.modules.customer_proof.selection import _source_type_for_claim
from data_sources.modules.production.record import verify_publishable
from data_sources.modules.production.truth_index import canonical
from data_sources.modules.production.truth_text import body_lines
from data_sources.modules.public_http.markdown_urls import extract_urls

USAGE_LEDGER = Path("config") / "customer-proof-usage-ledger.json"
NONVAULT_INDEX = Path("config") / "nonvault-customer-proof-index.json"
REUSE_REASON = "Recorded at publish from the passing release record."
SUMMARY_LIMIT = 200
LOCK_WAIT_SECONDS = 10.0
LOCK_STALE_SECONDS = 60.0
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_USE_TYPES = {"metric": "metric", "quote": "approved_quote", "theme": "theme", "experience_story": "experience_story"}
_H2 = re.compile(r"^\s{0,3}##\s+(.+?)\s*#*\s*$")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error


def _linked_sections(article: str) -> dict[str, str]:
    """Canonical URL of each body link -> the H2 heading above its first link ("" before any H2)."""
    raw = body_lines(article)
    sections, current = [], ""
    for line in raw:
        match = _H2.match(line)
        current = match.group(1) if match else current
        sections.append(current)
    found: dict[str, str] = {}
    for link in extract_urls("\n".join(raw)):
        found.setdefault(canonical(link.url), sections[link.line - 1])
    return found


def _source_type(item: Mapping[str, Any], nonvault: Mapping[str, Mapping[str, Any]] | None) -> str:
    if nonvault is None:
        evidence = {"claim_type": str(item.get("claim_type") or "")}
        return _source_type_for_claim(evidence, str(item.get("url") or ""), str(item.get("use_mode") or ""))
    row = nonvault.get(item["claim_id"])
    if row is None or not row.get("source_type"):
        raise ValueError(f"nonvault proof row {item['claim_id']} has no source_type in {NONVAULT_INDEX}")
    return str(row["source_type"])


def _summary(text: Any) -> str:
    summary = " ".join(str(text or "").split())
    return summary if len(summary) <= SUMMARY_LIMIT else summary[: SUMMARY_LIMIT - 3].rstrip() + "..."


def proof_use_entries(
    bom: Mapping[str, Any],
    article: str,
    *,
    nonvault_rows: Sequence[Mapping[str, Any]],
    published_path: str,
    date_used: str,
) -> list[dict[str, Any]]:
    """One ledger entry per BOM proof item whose URL the article body links, in BOM order."""
    connector = (bom.get("context") or {}).get("status") != "not_applicable"
    nonvault = None if connector else {str(row.get("proof_id")): row for row in nonvault_rows}
    sections = _linked_sections(article)
    entries = []
    for item in bom.get("proof") or []:
        url = str(item.get("url") or "")
        if not url or canonical(url) not in sections:
            continue
        entries.append({
            "proof_id": item["claim_id"],
            "source_type": _source_type(item, nonvault),
            "customer": str(item.get("customer") or ""),
            "source_url": url,
            "article_slug": (bom.get("identity") or {}).get("slug", ""),
            "artifact_path": published_path,
            "date_used": date_used,
            "section": sections[canonical(url)],
            "use_type": _USE_TYPES[item["kind"]],
            "claim_summary": _summary(item.get("text")),
            "reuse_reason": REUSE_REASON,
        })
    return entries


def _nonvault_rows(root: Path, bom: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if (bom.get("context") or {}).get("status") != "not_applicable":
        return []
    rows = (_read_json(root / NONVAULT_INDEX) or {}).get("proof")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _write_ledger(path: Path, ledger: dict[str, Any], newline: str) -> None:
    text = json.dumps(ledger, indent=2) + "\n"
    atomic_write_text(path, text.replace("\n", newline), max_bytes=DEFAULT_JSON_MAX_BYTES, field="usage ledger")


def _windows_pid_running(pid: int) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == _ERROR_ACCESS_DENIED  # exists, but not ours to query
    try:
        code = ctypes.c_ulong()
        return not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _pid_running(pid: int) -> bool:
    """Whether a process with this pid is still running (unknown counts as running)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        return _windows_pid_running(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _lock_age_seconds(lock: Path, holder: Mapping[str, Any]) -> float:
    try:
        created = datetime.datetime.fromisoformat(str(holder["created_at"])).timestamp()
    except (KeyError, TypeError, ValueError):
        created = lock.stat().st_mtime
    return time.time() - created


def _lock_is_stale(lock: Path) -> bool:
    """Old, or held by an exited process. A lock still being written is judged by its file age."""
    try:
        holder = json.loads(lock.read_text(encoding="utf-8") or "{}")
        holder = holder if isinstance(holder, dict) else {}
        if _lock_age_seconds(lock, holder) > LOCK_STALE_SECONDS:
            return True
        pid = holder.get("pid")
        return isinstance(pid, int) and not _pid_running(pid)
    except (OSError, ValueError):
        return False


def _try_lock(lock: Path) -> bool:
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    created = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "created_at": created}, stream)
    return True


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive lockfile next to the ledger so concurrent publishes cannot lose an entry."""
    lock = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while not _try_lock(lock):
        if _lock_is_stale(lock):
            lock.unlink(missing_ok=True)
            continue
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"usage ledger is locked by another publish: {lock}; delete it only if no publish is running"
            )
        time.sleep(0.05)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def _key(entry: Mapping[str, Any]) -> tuple[str, str]:
    """One use per proof per article: a republish or a second publisher on a later day adds nothing."""
    return (str(entry.get("proof_id")), str(entry.get("artifact_path")))


def record_publish_use(
    article_path: Path, root: Path, *, published_path: str, date: str | None = None
) -> list[dict[str, Any]]:
    """Append the published article's linked BOM proof to the usage ledger; return the new entries."""
    root = Path(root).resolve()
    record = verify_publishable(article_path, root)
    bom = _read_json(root / record["bom"]["path"])
    article = (root / record["article"]["path"]).read_text(encoding="utf-8")
    entries = proof_use_entries(
        bom, article, nonvault_rows=_nonvault_rows(root, bom), published_path=published_path,
        date_used=date or current_utc_date().isoformat(),
    )
    path = root / USAGE_LEDGER
    with _ledger_lock(path):
        return _append_entries(path, entries)


def _append_entries(path: Path, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw = path.read_bytes().decode("utf-8") if path.is_file() else ""
    ledger = json.loads(raw) if raw else {"version": 1, "updated_at": "", "uses": []}
    if not isinstance(ledger, dict) or not isinstance(ledger.get("uses"), list):
        raise ValueError(f"{path} has no uses list")
    seen = {_key(entry) for entry in ledger["uses"] if isinstance(entry, Mapping)}
    added = []
    for entry in entries:
        if _key(entry) not in seen:
            seen.add(_key(entry))
            added.append(entry)
    if not added:
        return []
    ledger["uses"].extend(added)
    ledger["updated_at"] = added[0]["date_used"]
    _write_ledger(path, ledger, "\r\n" if "\r\n" in raw else "\n")
    return added


__all__ = ["REUSE_REASON", "USAGE_LEDGER", "proof_use_entries", "record_publish_use"]
