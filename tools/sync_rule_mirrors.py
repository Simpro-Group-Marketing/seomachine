"""Generate .agents and .cursor rule mirrors from .claude/rules (the source of truth).

Usage: python tools/sync_rule_mirrors.py [--check] [--root DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Cursor frontmatter for rules whose .mdc mirror has none yet. Existing .mdc
# frontmatter is always preserved verbatim; nothing here defaults to alwaysApply: true.
FRONTMATTER = {
    "seo-blog-strategy": (
        "description: Production SEO blog strategy contract for Simpro blogs and rewrites\n"
        'globs:\n  - "drafts/**/*.md"\n  - "rewrites/**/*.md"\n  - "research/**/*.md"\n'
        "alwaysApply: false\n"
    ),
    "repository-development": (
        "description: Repository development rules for code, tests, scripts, and developer docs\n"
        'globs:\n  - "data_sources/**/*.py"\n  - "tests/**/*.py"\n  - "tools/**/*.py"\n'
        "alwaysApply: false\n"
    ),
}
_HEADER = re.compile(r"\A---\n.*?\n---\n\n*", re.S)


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _cursor_header(name: str, path: Path) -> str:
    """Return the existing frontmatter (and its trailing blank lines) or the default."""
    if path.exists():
        match = _HEADER.match(_read(path))
        if match:
            return match.group(0)
    if name not in FRONTMATTER:
        raise SystemExit(f"No cursor frontmatter for {name}: add it to FRONTMATTER.")
    return f"---\n{FRONTMATTER[name]}---\n\n"


def expected_mirrors(root: Path) -> dict[Path, str]:
    """Map every mirror path to the exact text it must contain."""
    mirrors: dict[Path, str] = {}
    for source in sorted((root / ".claude" / "rules").glob("*.md")):
        body = _read(source)
        cursor = root / ".cursor" / "rules" / f"{source.stem}.mdc"
        mirrors[root / ".agents" / "rules" / source.name] = body
        mirrors[cursor] = _cursor_header(source.stem, cursor) + body
    return mirrors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if any mirror is stale")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    stale = []
    for path, text in expected_mirrors(root).items():
        if path.exists() and _read(path) == text:
            continue
        stale.append(path.relative_to(root).as_posix())
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
    label = "Stale" if args.check else "Updated"
    for rel in stale:
        print(f"{label}: {rel}")
    if args.check and stale:
        print("Run: python tools/sync_rule_mirrors.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
