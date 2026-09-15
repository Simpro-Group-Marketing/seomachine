import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _author_metadata_paragraphs(path: Path) -> list[str]:
    return [
        re.sub(r"\s+", " ", paragraph).casefold()
        for paragraph in re.split(r"\n\s*\n", _read(path))
        if re.search(r"\bauthor metadata\b", paragraph, re.IGNORECASE)
    ]


def test_author_metadata_controls_identity_not_eeat_credit_in_live_docs():
    paths = [
        ROOT / "context" / "aeo-geo-blog-strategy.md",
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "rewrite.md",
    ]
    concept_patterns = {
        "author_metadata": r"\bauthor metadata\b",
        "identity": r"\bcontrols?\b[^.]*\bidentity\b",
        "person_schema": r"\bperson\b[^.]*\bschema\b",
        "first_person_voice": r"\bfirst.person\b[^.]*\bvoice\b",
        "zero_expertise": r"\b(?:zero|no)\b[^.]*\bexpertise\b",
        "zero_experience": r"\b(?:zero|no)\b[^.]*\bexperience\b",
        "selected_evidence": r"\bselected\b[^.]*\bevidence\b",
        "source_visible": r"\bsource.visible\b[^.]*\bevidence\b",
    }

    for path in paths:
        paragraphs = _author_metadata_paragraphs(path)
        assert len(paragraphs) == 1
        assert {
            name
            for name, pattern in concept_patterns.items()
            if re.search(pattern, paragraphs[0])
        } == set(concept_patterns)

    for path in (
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "rewrite.md",
    ):
        assert re.search(
            r"canonical[^.]*context/aeo-geo-blog-strategy\.md",
            _author_metadata_paragraphs(path)[0],
        )


def test_eeat_expertise_policy_requires_source_visible_expert_evidence():
    paths = [
        ROOT / "context" / "aeo-geo-blog-strategy.md",
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "rewrite.md",
    ]

    for path in paths:
        content = _read(path).casefold()
        assert "source-visible expert evidence" in content
        assert "author/reviewer metadata" not in content
