"""Run the quarantined best-apps-electricians release artifact helper here.

Repository maintenance moved the article-specific helper into local P0
quarantine. This wrapper keeps the helper logic intact while binding every path
to the active checkout, so sidecar, fulfillment, machine-review, and optimizer
artifacts are regenerated from current bytes.
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
    / "build_best_apps_electricians_release_artifacts.py"
)
RUN_ID = "a5af3ed0-51b6-4d13-8b2f-9c1d40e2a738"


def _load_helper():
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    spec = importlib.util.spec_from_file_location(
        "best_apps_electricians_release_artifacts_quarantine",
        HELPER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper from {HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bind_paths(module, precheck: Path | None) -> None:
    module.ROOT = ROOT
    module.ARTICLE = ROOT / "rewrites" / "electrician-apps-2026-09-30.md"
    module.PLAN = ROOT / "research" / "editorial-plan-best-apps-for-electricians-2026-09-30.json"
    module.SIDECAR = ROOT / "research" / "validation-best-apps-for-electricians-2026-09-30.md"
    module.REQUEST = ROOT / "research" / "context-request-best-apps-electricians.json"
    module.PACK = ROOT / "research" / "context-pack-best-apps-electricians.json"
    module.RECEIPT = ROOT / "research" / "context-receipt-best-apps-electricians.json"
    module.SELECTOR_PACK = (
        ROOT / "research" / "context-pack-best-apps-electricians-customer-selector.json"
    )
    module.SELECTOR_RECEIPT = (
        ROOT / "research" / "context-receipt-best-apps-electricians-customer-selector.json"
    )
    module.CLAIM_LOOKUP = (
        ROOT / "research" / "customer-proof-claim-lookup-best-apps-electricians-2026-09-30.json"
    )
    module.FRED = ROOT / "research" / "fred-authority-selector-evidence-best-apps-electricians.md"
    module.CUSTOMER_PROOF = (
        ROOT / "research" / "customer-proof-selector-evidence-best-apps-electricians.json"
    )
    module.RUN_ID = RUN_ID
    if precheck is not None:
        module.PRECHECK = precheck.resolve()
    module.OPTIMIZER = (
        ROOT / "research" / "optimizer-output-best-apps-for-electricians-2026-10-01-v12.json"
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    precheck: Path | None = None
    if "--precheck" in args:
        index = args.index("--precheck")
        try:
            precheck = ROOT / args[index + 1]
        except IndexError as error:
            raise SystemExit("--precheck requires a path") from error
        del args[index : index + 2]
    module = _load_helper()
    _bind_paths(module, precheck)
    original_argv = sys.argv[:]
    try:
        sys.argv = [str(HELPER), *args]
        module.main()
    finally:
        sys.argv = original_argv
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
