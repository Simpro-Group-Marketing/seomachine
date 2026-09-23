"""Insert the preflight readiness receipt into the final release stage chain.

The optimization receipt chains from the preflight readiness receipt, so that
receipt has to appear in the chain the release wrapper validates.
"""
from __future__ import annotations

import pathlib
import sys

SCRIPT = pathlib.Path("scripts/run_subcontractors_final_release.sh")
ANCHOR = '  --stage-receipt "$R/optimization.json"'
INSERT = '  --stage-receipt "$PRE_DIR/preflight-readiness-stage-receipt.json" \\'


def main() -> int:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    if any("preflight-readiness-stage-receipt.json" in line and "--stage-receipt" in line
           for line in lines):
        print("preflight readiness receipt already in the chain")
        return 0
    out: list[str] = []
    for line in lines:
        if line.startswith(ANCHOR):
            out.append(INSERT)
        out.append(line)
    SCRIPT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
    print("preflight readiness receipt inserted into the chain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
