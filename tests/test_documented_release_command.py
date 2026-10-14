"""Every production CLI invocation the command docs prescribe must match that CLI's real parser."""

import argparse
import re
from pathlib import Path
from unittest import mock

import pytest

from data_sources.modules import paa_provenance_guard
from data_sources.modules.production import bom_build, keyword_record, layout, page_capture, record, release, serp_coverage

ROOT = Path(__file__).resolve().parents[1]
COMMAND_DIR = ROOT / ".claude" / "commands"
PRODUCTION_RE = re.compile(r"python -m data_sources\.modules\.production\.([a-z_]+)([^`\n]*)")
PAA_RECORD_RE = re.compile(r"python data_sources/modules/paa_provenance_guard\.py record([^`\n]*)")
FLAG_RE = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
ENTRIES = {
    "layout": lambda: layout.main([]),
    "release": lambda: release.main([]),
    "record": lambda: record.main([]),
    "bom_build": lambda: bom_build.main([]),
    "serp_coverage": lambda: serp_coverage.main([]),
    "keyword_record": lambda: keyword_record.main([]),
    "page_capture": lambda: page_capture.main([]),
    "paa_record": lambda: paa_provenance_guard._main(["record"]),
}


class _Captured(Exception):
    pass


def _parser(name: str) -> argparse.ArgumentParser:
    """Run the CLI entry until it parses arguments and return the parser it built."""
    holder = []

    def capture(self, args=None, namespace=None):
        holder.append(self)
        raise _Captured

    with mock.patch.object(argparse.ArgumentParser, "parse_args", capture), pytest.raises(_Captured):
        ENTRIES[name]()
    return holder[0]


def _invocations():
    found = []
    for path in sorted(COMMAND_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        found += [(path.name, match.group(1), match.group(2)) for match in PRODUCTION_RE.finditer(text)]
        found += [(path.name, "paa_record", match.group(1)) for match in PAA_RECORD_RE.finditer(text)]
    return found


INVOCATIONS = _invocations()


def test_command_docs_document_the_production_clis():
    documented = {name for _doc, name, _args in INVOCATIONS}
    assert set(ENTRIES) <= documented


@pytest.mark.parametrize(("doc", "name", "args"), INVOCATIONS, ids=lambda value: str(value)[:40])
def test_documented_invocation_matches_the_parser(doc, name, args):
    assert name in ENTRIES, f"{doc} documents an unknown production CLI: {name}"
    parser = _parser(name)
    flags = set(FLAG_RE.findall(args))
    known = {option for action in parser._actions for option in action.option_strings}
    assert sorted(flags - known) == [], f"{doc}: {name} has no such flag"
    if not flags:
        return  # a prose mention such as "runs `... release [article]`" names the command, not a full call
    missing = [
        action.option_strings[0]
        for action in parser._actions
        if action.required and action.option_strings and not flags & set(action.option_strings)
    ]
    for group in parser._mutually_exclusive_groups:
        options = {option for action in group._group_actions for option in action.option_strings}
        if group.required and not flags & options:
            missing.append(" | ".join(sorted(options)))
    assert missing == [], f"{doc}: {name} invocation omits required {missing}"


def test_publish_readiness_shows_the_full_release_invocation():
    doc = (COMMAND_DIR / "publish-readiness.md").read_text(encoding="utf-8")
    calls = [args for match in PRODUCTION_RE.finditer(doc) if match.group(1) == "release" for args in [match.group(2)]]
    options = {a.option_strings[0] for a in _parser("release")._actions if a.option_strings and a.dest != "help"}
    assert any(options <= set(FLAG_RE.findall(args)) for args in calls)
    assert "data_sources.modules.blog_release" not in doc
