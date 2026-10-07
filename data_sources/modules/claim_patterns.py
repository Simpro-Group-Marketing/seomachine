"""Claim-detection patterns shared by the proof policy engine and its gates.

This module is a leaf: it imports nothing from the guards that use it, so the
policy engine, source support, and the owned product language rule can share
one set of patterns without an import cycle.
"""

from __future__ import annotations

import re


STRICT_PUBLIC_RISK_RE = re.compile(
    r"\b(?:code|compliance|deadline|expire[ds]?|fee|fees|insurance|law|legal|"
    r"licen[cs](?:e|ed|ing|es)|pricing|regulat(?:e|ed|es|ion|ions|or|ory)|"
    r"renew(?:al|ed|s)?|safety|statute|tax)\b",
    re.IGNORECASE,
)
MATERIAL_NUMBER_RE = re.compile(
    r"(?:[$£€]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:%|hours?|days?|years?|"
    r"businesses?|customers?|workers?|employees?|licenses?)\b)",
    re.IGNORECASE,
)
COMPARATIVE_RANKING_RE = re.compile(
    r"\b(?:best(?![-\s]+fit\b)|better|leading|top[- ]rated|rank(?:ed|ing|s)?)\b",
    re.IGNORECASE,
)
ANY_PUBLIC_NUMBER_RE = re.compile(r"(?:[$\u00a3\u20ac]\s*\d|\b\d[\d,]*(?:\.\d+)?(?:\s*%|\b))")
STRUCTURED_QUOTE_RE = re.compile(r'(?:"[^"]{20,}"|\u201c[^\u201d]{20,}\u201d)')
STRUCTURED_STATUS_RE = re.compile(
    r"\b(?:is|are|was|were|remains?)\s+(?:currently\s+)?"
    r"(?:available|unavailable|included|excluded|supported|unsupported|free|paid|"
    r"discontinued|deprecated)\b|\b(?:launched|sunset|retired|deprecated)\b",
    re.IGNORECASE,
)
STRUCTURED_PRICING_ASSERTION_RE = re.compile(
    r"\bpricing\s+(?:starts?|costs?|is\s+(?:free|paid|available|[$\u00a3\u20ac]|\d))\b|"
    r"\b(?:costs?|priced)\s+(?:[$\u00a3\u20ac]|\d)|\bper\s+(?:user|seat|technician|month|year|job)\b",
    re.IGNORECASE,
)
GENERAL_CLAIM_PATTERNS = (
    (
        "guarantee",
        re.compile(
            r"\b(?:guarantees?|ensures?|eliminates?)\b|"
            r"\b(?:zero[- ]risk|fail[- ]proof|error[- ]proof|cannot fail)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "absolute",
        re.compile(
            r"\b(?:always|never)\b(?=[^.!?]{0,100}\b(?:is|are|has|have|"
            r"stores?|records?|tracks?|offers?|provides?|includes?|supports?|"
            r"loses?|prevents?|works?|delivers?|produces?))",
            re.IGNORECASE,
        ),
    ),
    (
        "commercial",
        re.compile(
            r"\b(?:pricing|price|costs?|fees?|charges?|subscription|plan|package|premium|trial|"
            r"add[- ]on|upgrade|license|licence)\b[^.!?]{0,90}\b"
            r"(?:is|are|costs?|includes?|included|requires?|available|free|paid|waived)\b|"
            r"\b(?:is|are)\s+included\s+in\s+(?:the\s+)?(?:paid|premium|"
            r"enterprise|standard|basic)?\s*(?:plan|package|subscription)\b|"
            r"\b(?:eligible|ineligible)\b[^.!?]{0,90}\b(?:for|to)\b"
            r"[^.!?]{0,90}\b(?:add[- ]on|feature|product|platform|software)\b|"
            r"\b(?:add[- ]on|feature|product|platform|software)\b[^.!?]{0,90}\b"
            r"(?:is|are|can|cannot|may|must)?\s*(?:be\s+)?access(?:ed|ible)\b|"
            r"\b(?:access|availability|eligibility)\b[^.!?]{0,90}\b"
            r"(?:is|are|remains?|becomes?|requires?|restricted|limited|available|unavailable)\b|"
            r"\b(?:eligible|ineligible|eligibility)\b|"
            r"\b(?:can|cannot|may|must)\s+access\b",
            re.IGNORECASE,
        ),
    ),
    (
        "comparative",
        re.compile(
            r"\b(?:better|worse|more|less|faster|slower|higher|lower)\b[^.!?]{0,80}\bthan\b|"
            r"\bcompared (?:with|to)\b|\bversus\b|\boutperform(?:s|ed|ing)?\b|"
            r"\bUnlike\s+(?!(?:the\s+)?(?:previous|next)\s+(?:section|paragraph|example)\b)"
            r"[^,]{1,100},\s+(?!this\s+(?:section|article|guide)\b)|"
            r",\s+whereas\s+",
            re.IGNORECASE,
        ),
    ),
    (
        "causal",
        re.compile(
            r"\b(?:causes?|leads? to|results? in|because of|therefore|drives?|"
            # "help" is also the noun in vendor destination names such as
            # "help article", "help centre" and "help guide". Only the bare
            # noun form takes that exemption: the inflected verb "helps" is
            # always causal, so "helps guide the technician" and "helps pages
            # load faster" still register as claims. Nouns listed here are the
            # ones the article corpus actually uses.
            r"contributes? to|helps|"
            r"help(?![\s-]+(?:articles?|cent(?:re|er)s?|guides?|desks?|"
            r"pages?|docs|documentation|content))|"
            r"improves?|reduces?|increases?|decreases?|prevents?|"
            r"enables?|boosts?|cuts?|streamlines?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "definitional",
        re.compile(
            r"\b(?:is defined as|refers to|means|describes)\b|"
            r"\b(?:is|are)\s+(?:a|an|the)\s+(?:type|process|practice|method|"
            r"system|software|approach|term|measure|metric|workflow|prioritized list)\b|"
            r"\b(?:is|are)\s+(?:a|an)\s+document\s+(?:that|which|used to)\b|"
            r"^(?!\s*(?:This|That|It)\b)[^.!?]{1,80}\s+(?:is|are)\s+when\s+"
            r"(?:a|an|the|you|teams?|workers?|businesses?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "process",
        re.compile(
            r"\b(?:requires?|involves?|consists of|begins? with|starts? with|"
            r"works? by|follows? a sequence|steps? (?:include|are))\b|"
            r"^\s*First\s+[^.!?;]{3,100},\s+then\s+[^.!?;]{3,100},\s+"
            r"(?:and\s+)?finally\s+|"
            r"\b(?:process|workflow)\s+moves?\s+from\s+[^.!?]{1,80}\s+to\s+"
            r"[^.!?]{1,80}\s+to\s+[^.!?]{1,80}",
            re.IGNORECASE,
        ),
    ),
    (
        "factual",
        re.compile(
            r"^(?:The|A|An|This|That|These|Those|[A-Z][A-Za-z0-9&.+-]+)\s+"
            r"(?:[A-Za-z0-9&.+-]+\s+){0,5}"
            r"(?:stores?|records?|tracks?|offers?|provides?|includes?|supports?|"
            r"connects?|sends?|displays?|manages?|contains?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "recommendation",
        re.compile(
            r"\b(?:should|must|need to|ought to|avoid|choose|recommend(?:ed|s)?|"
            r"best practice|is advisable to|is essential to|is important to)\b|"
            r"^\s*(?:Review|Verify|Confirm|Check)\s+[^.!?]{1,100}\s+"
            r"(?:before|prior to)\s+|"
            r"^\s*Do\s+not\s+[^.!?]{1,100}\s+(?:until|before)\s+",
            re.IGNORECASE,
        ),
    ),
)
