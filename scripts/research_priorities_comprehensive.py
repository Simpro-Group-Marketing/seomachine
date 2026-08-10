#!/usr/bin/env python3
"""Run source-backed research modules and inventory their verified artifacts."""

from __future__ import annotations

import hashlib
import importlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional


RESEARCH_MODULES: Dict[str, Dict[str, str]] = {
    "quick_wins": {
        "module": "scripts.research_quick_wins",
        "artifact": "quick-wins-{date}.md",
    },
    "competitor_gaps": {
        "module": "scripts.research_competitor_gaps",
        "artifact": "competitor-gaps-{date}.md",
    },
    "performance_matrix": {
        "module": "scripts.research_performance_matrix",
        "artifact": "performance-matrix-{date}.md",
    },
    "topic_clusters": {
        "module": "scripts.research_topic_clusters",
        "artifact": "topic-clusters-{date}.md",
    },
    "trending": {
        "module": "scripts.research_trending",
        "artifact": "trending-{date}.md",
    },
}

REVIEW_GUIDANCE = (
    "Evaluate all identified SERP features and target every applicable feature only "
    "when the verified report supports it. Evaluate all identified coverage gaps; "
    "treat recurring, reader-critical, evidence-supported gaps as candidates and "
    "document the Reader Contract exception for justified exclusions."
)


def _default_runner(module_path: str) -> Callable[[], Any]:
    def run() -> Any:
        module = importlib.import_module(module_path)
        module_main = getattr(module, "main", None)
        if not callable(module_main):
            raise RuntimeError(f"{module_path} does not expose a callable main()")
        return module_main()

    return run


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_research_modules(
    *,
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
    module_runners: Optional[Mapping[str, Callable[[], Any]]] = None,
    module_names: Optional[Iterable[str]] = None,
    include_competitor_gaps: bool = False,
    print_fn: Callable[..., None] = print,
) -> Dict[str, Dict[str, str]]:
    """Run requested modules and mark completion only after artifact readback."""
    now = now or datetime.now()
    date_text = now.strftime("%Y-%m-%d")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    requested_names = list(module_names or RESEARCH_MODULES)
    supplied_runners = dict(module_runners or {})
    results: Dict[str, Dict[str, str]] = {}

    for name in requested_names:
        if name not in RESEARCH_MODULES:
            raise ValueError(f"Unknown research module: {name}")
        if name == "competitor_gaps" and not include_competitor_gaps:
            results[name] = {"status": "skipped"}
            print_fn("SKIP competitor_gaps: not requested")
            continue

        spec = RESEARCH_MODULES[name]
        artifact = output_root / spec["artifact"].format(date=date_text)
        before_hash = _sha256(artifact)
        runner = supplied_runners.get(name) or _default_runner(spec["module"])
        print_fn(f"RUN  {name}")
        try:
            runner()
            after_hash = _sha256(artifact)
            if after_hash is None:
                raise RuntimeError(f"Expected artifact was not written: {artifact}")
            if before_hash is not None and after_hash == before_hash:
                raise RuntimeError(f"Expected artifact was not refreshed: {artifact}")
        except Exception as exc:
            results[name] = {"status": "failed", "error": str(exc)}
            print_fn(f"FAIL {name}: {exc}")
            continue

        results[name] = {
            "status": "completed",
            "artifact": str(artifact),
            "artifact_sha256": after_hash,
        }
        print_fn(f"PASS {name}: {artifact}")

    return results


def generate_unified_roadmap(
    results: Mapping[str, Mapping[str, str]],
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build a review queue containing only verified completed artifacts."""
    now = now or datetime.now()
    completed_artifacts = []
    actions = []
    for name in RESEARCH_MODULES:
        result = results.get(name, {})
        if result.get("status") != "completed" or not result.get("artifact"):
            continue
        artifact = result["artifact"]
        label = name.replace("_", " ").title()
        completed_artifacts.append(artifact)
        actions.append(
            {
                "source": label,
                "artifact": artifact,
                "action": (
                    f"Review the verified {label} report and select supported priorities."
                ),
            }
        )

    return {
        "generated": now.strftime("%Y-%m-%d %H:%M"),
        "completed_artifacts": completed_artifacts,
        "actions": actions,
        "review_guidance": REVIEW_GUIDANCE,
    }


def write_roadmap_report(
    roadmap: Mapping[str, Any],
    results: Mapping[str, Mapping[str, str]],
    *,
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
) -> Path:
    """Write an evidence-bound roadmap inventory and return its path."""
    now = now or datetime.now()
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"ROADMAP-{now.strftime('%Y-%m-%d')}.md"
    lines = [
        "# Content Strategy Roadmap",
        "",
        f"**Generated:** {roadmap['generated']}",
        "",
        "## Research execution status",
        "",
    ]
    for name in RESEARCH_MODULES:
        result = results.get(name, {"status": "not_run"})
        line = f"- {name.replace('_', ' ').title()}: {result.get('status', 'not_run')}"
        if result.get("artifact"):
            line += f" | `{result['artifact']}` | SHA-256 `{result['artifact_sha256']}`"
        if result.get("error"):
            line += f" | blocker: {result['error']}"
        lines.append(line)

    lines.extend(["", "## Verified report review queue", ""])
    actions = list(roadmap.get("actions", []))
    if actions:
        for action in actions:
            lines.append(f"- [{action['source']}]({Path(action['artifact']).as_posix()}): {action['action']}")
    else:
        lines.append("No verified research artifacts were produced; no priorities were generated.")
    lines.extend(["", "## Review boundary", "", str(roadmap["review_guidance"]), ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> int:
    print("=" * 80)
    print("COMPREHENSIVE CONTENT PRIORITIES")
    print("=" * 80)
    try:
        input("Press Enter to run, or Ctrl+C to cancel: ")
        include_gaps = input("Run paid competitor-gap analysis? (y/N): ").strip().lower() == "y"
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return 130

    now = datetime.now()
    results = run_research_modules(
        now=now,
        include_competitor_gaps=include_gaps,
    )
    failed = [name for name, result in results.items() if result["status"] == "failed"]
    if failed:
        print(f"Research failed; roadmap not written. Failed modules: {', '.join(failed)}")
        return 1

    roadmap = generate_unified_roadmap(results, now=now)
    output_path = write_roadmap_report(roadmap, results, now=now)
    print(f"PASS roadmap written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
