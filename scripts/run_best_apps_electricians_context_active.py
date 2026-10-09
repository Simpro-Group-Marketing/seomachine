"""Run the quarantined best-apps-electricians vault context helper against this repo.

The helper was moved into the local P0 quarantine by repository maintenance, but
the release workflow still needs to rebuild the exact same context artifacts
against the active article bytes. This wrapper imports the quarantined helper,
overrides its path globals to the current checkout, and then executes its main
function without changing helper logic.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (
    ROOT
    / ".seomachine"
    / "local-p0-quarantine"
    / "20261001-095244"
    / "scripts"
    / "build_best_apps_electricians_context.py"
)
SLUG = "best-apps-electricians"


def _load_helper():
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    spec = importlib.util.spec_from_file_location(
        "best_apps_electricians_context_quarantine",
        HELPER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper from {HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_helper()
    module.ROOT = ROOT
    module.ARTICLE = ROOT / "rewrites" / "electrician-apps-2026-09-30.md"
    module.REQUEST_PATH = ROOT / "research" / f"context-request-{SLUG}.json"
    module.PACK_PATH = ROOT / "research" / f"context-pack-{SLUG}.json"
    module.RECEIPT_PATH = ROOT / "research" / f"context-receipt-{SLUG}.json"
    module.SELECTOR_PACK_PATH = (
        ROOT / "research" / f"context-pack-{SLUG}-customer-selector.json"
    )
    module.SELECTOR_RECEIPT_PATH = (
        ROOT / "research" / f"context-receipt-{SLUG}-customer-selector.json"
    )
    module.CLAIM_LOOKUP_PATH = (
        ROOT / "research" / f"customer-proof-claim-lookup-{SLUG}-2026-09-30.json"
    )
    module.TRACE_PATH = ROOT / "research" / f"context-refresh-{SLUG}-2026-09-30.json"
    module.CUSTOMER_PROOF_SELECTOR_CLAIMS = [
        {
            "claim_id": "selector-search-public-metric-best-apps-electricians",
            "query": "Simpro electrician contractor customer proof metric scheduling dispatch invoicing job costing",
            "use_mode": "public_metric",
            "brand_scope": "Simpro",
        },
        {
            "claim_id": "claim-metric-MET-1024",
            "query": "Simpro electrician contractor customer quote mobile app scheduling dispatch invoicing",
            "use_mode": "exact_quote",
            "brand_scope": "Simpro",
        },
        {
            "claim_id": "selector-search-public-paraphrase-best-apps-electricians",
            "query": "Simpro electrician contractor review theme mobile app scheduling dispatch invoicing",
            "use_mode": "public_paraphrase",
            "brand_scope": "Simpro",
        },
    ]
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
