"""Command-line entry point: build connector-bound context packs from a spec, resumably."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

try:
    from ..simpro_vault_client import SimproVaultClient, VaultClientError
    from .checkpoints import ContextBuildResumeError
    from .runner import ContextBuildError, run_context_build
    from .spec import ContextBuildSpecError, load_spec
except ImportError:  # pragma: no cover - supports direct script execution.
    from simpro_vault_client import SimproVaultClient, VaultClientError
    from context_build.checkpoints import ContextBuildResumeError
    from context_build.runner import ContextBuildError, run_context_build
    from context_build.spec import ContextBuildSpecError, load_spec


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build connector-bound context packs from a spec, resumably.")
    parser.add_argument("spec", help="Path to a simpro-context-build-spec/v1 JSON file.")
    parser.add_argument("--resume", action="store_true", help="Reuse checkpoints and packs that still validate.")
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        result = run_context_build(spec, client=SimproVaultClient(), workspace_root=Path.cwd(), resume=args.resume)
    except (ContextBuildSpecError, ContextBuildResumeError, ContextBuildError, VaultClientError) as error:
        payload: dict = {"ok": False, "error": {"code": type(error).__name__, "message": str(error)}}
        hint = "Fix the spec or rerun with --resume after a crash."
        if hasattr(error, "stages_not_rebuilt"):
            payload["stages_not_rebuilt"] = list(error.stages_not_rebuilt)
            hint += " Files for stages_not_rebuilt may be stale from an earlier run."
        payload["recovery_hint"] = hint
        print(json.dumps(payload))
        return 1
    print(json.dumps({"ok": True, "result": {"stages": [asdict(s) for s in result.stages],
                                             "trace": result.trace_path.as_posix()}}))
    return 0
