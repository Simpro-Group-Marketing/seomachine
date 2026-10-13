"""The production BOM reduced to the lookups the truth checks need."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from data_sources.modules.faq_structure import faq_question_match_key
from data_sources.modules.production.bom_text import supported_numbers
from data_sources.modules.proof_link_policy import canonicalize_link_identity

_FAQ_PREFIX = re.compile(r"^\s*(?:(?:q|question)\s*\d*\s*[:.)\-]\s*|\d+\s*[.)]\s*)", re.IGNORECASE)


def canonical(url: str) -> str:
    return canonicalize_link_identity(url) or url.strip()


def question_key(question: str) -> str:
    """Match key for a FAQ question: a leading "Q:" or list number is not part of the question."""
    return faq_question_match_key(_FAQ_PREFIX.sub("", question.strip(), count=1))


def _items(bom: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = bom.get(key)
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _group_by_url(items: Sequence[Mapping[str, Any]]) -> dict[str, tuple[Mapping[str, Any], ...]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        if item.get("url"):
            grouped.setdefault(canonical(item["url"]), []).append(item)
    return {url: tuple(rows) for url, rows in grouped.items()}


def _approved_texts(item: Mapping[str, Any]) -> list[str]:
    return [
        str(quote.get("quote") if isinstance(quote, Mapping) else quote)
        for quote in item.get("approved_quotes") or []
    ]


@dataclass(frozen=True)
class BomIndex:
    facts: tuple[Mapping[str, Any], ...]
    proof: tuple[Mapping[str, Any], ...]
    facts_by_url: Mapping[str, tuple[Mapping[str, Any], ...]]
    proof_by_url: Mapping[str, tuple[Mapping[str, Any], ...]]
    known_urls: frozenset[str]
    questions: frozenset[str]
    year: str

    @classmethod
    def build(cls, bom: Mapping[str, Any]) -> "BomIndex":
        facts, proof = _items(bom, "facts"), _items(bom, "proof")
        facts_by_url, proof_by_url = _group_by_url(facts), _group_by_url(proof)
        cta = bom["identity"].get("cta")
        planned = [link["url"] for link in _items(bom, "links") if link.get("url")]
        planned += [cta["url"]] if isinstance(cta, Mapping) and cta.get("url") else []
        paa = bom.get("paa")
        asked = paa.get("questions") if isinstance(paa, Mapping) else None
        questions = {
            question_key(item["question"]) for item in asked or [] if isinstance(item, Mapping) and item.get("question")
        }
        return cls(
            tuple(facts), tuple(proof), facts_by_url, proof_by_url,
            frozenset({canonical(url) for url in planned} | set(facts_by_url) | set(proof_by_url)),
            frozenset(questions), str(bom["identity"].get("date", ""))[:4],
        )

    @property
    def source_urls(self) -> frozenset[str]:
        return frozenset(self.facts_by_url) | frozenset(self.proof_by_url)

    @property
    def customers(self) -> list[str]:
        return [str(item["customer"]) for item in self.proof if str(item.get("customer") or "").strip()]

    def quote_sources(self) -> list[str]:
        sources = [str(fact["quote"]) for fact in self.facts]
        for item in self.proof:
            sources += [str(item.get("text") or ""), *_approved_texts(item)]
        return [source for source in sources if source.strip()]

    def rows_for(self, urls: Collection[str]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
        """Return (facts, proof) whose canonical URL is among ``urls``."""
        facts = [row for url in sorted(urls) for row in self.facts_by_url.get(url, ())]
        proof = [row for url in sorted(urls) for row in self.proof_by_url.get(url, ())]
        return facts, proof

    def numbers_for(self, urls: Collection[str]) -> frozenset[str]:
        facts, proof = self.rows_for(urls)
        return supported_numbers(facts, proof, "")

    def all_numbers(self) -> frozenset[str]:
        return supported_numbers(self.facts, self.proof, self.year)

    def holder_of(self, number: str) -> str:
        """Name the BOM fact or proof item whose text carries ``number`` ("" when none does)."""
        for kind, rows in (("fact", self.facts), ("proof", self.proof)):
            for row in rows:
                if number in supported_numbers([row] if kind == "fact" else [], [row] if kind == "proof" else [], ""):
                    return f"{kind} {row.get('id')} ({row.get('url')})"
        return ""


__all__ = ["BomIndex", "canonical", "question_key"]
