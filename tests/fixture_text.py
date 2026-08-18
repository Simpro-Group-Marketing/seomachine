"""Load exact multiline test payloads from focused fixture packs."""

from functools import lru_cache
import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).with_name("fixtures")
PACKS = frozenset({"content_evidence", "sealed_workflows", "publisher_contracts"})


@lru_cache(maxsize=None)
def _pack(name: str) -> dict[str, str]:
    if name not in PACKS:
        raise KeyError(f"unknown fixture pack: {name}")
    return json.loads((FIXTURE_ROOT / f"{name}.json").read_text(encoding="utf-8"))


def fixture_text(key: str) -> str:
    """Return one exact payload addressed as ``pack:key``."""
    pack, name = key.split(":", 1)
    return _pack(pack)[name]
