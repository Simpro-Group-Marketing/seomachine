"""Bind the optimize command, agent definitions and agent outputs to the receipt.

The optimization stage receipt has to carry a definition hash for the optimize
command, for each agent definition in the registry, and for each of that agent's
final outputs, or the release wrapper rejects the chain.
"""
from __future__ import annotations

import pathlib
import sys

SCRIPT = pathlib.Path("scripts/run_subcontractors_final_release.sh")
AGENTS = (
    "content-analyzer",
    "seo-optimizer",
    "meta-creator",
    "internal-linker",
    "keyword-mapper",
)
CONT = " \\"


def main() -> int:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    if any("command_definition.optimize-command" in line for line in lines):
        print("optimization evidence bindings already present")
        return 0

    inserts = [
        '  --evidence "command_definition.optimize-command=.claude/commands/optimize.md"' + CONT
    ]
    for agent in AGENTS:
        inserts.append(
            f'  --evidence "agent_definition.{agent}=.claude/agents/{agent}.md"' + CONT
        )
        inserts.append(
            f'  --evidence "agent_output.{agent}=research/agent-outputs/{agent}-$SLUG-$DATE.md"'
            + CONT
        )

    out: list[str] = []
    inserted = False
    for line in lines:
        if not inserted and line.strip().startswith('--evidence "scorecard='):
            out.extend(inserts)
            inserted = True
        out.append(line)
    if not inserted:
        print("MISS: could not find the optimization evidence anchor")
        return 1
    SCRIPT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
    print(f"added {len(inserts)} optimization evidence bindings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
