"""Proof Parsing responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _extract_proof_entries(content: str) -> List[ProofEntry]:
    entries: List[ProofEntry] = []
    section = ""

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        section_match = SECTION_RE.match(stripped)
        if section_match and not stripped.startswith("-"):
            section = _normalize_section(section_match.group("section"))

        row_match = PROOF_ROW_RE.match(stripped)
        if not row_match:
            continue

        fields = _parse_proof_fields(row_match.group("body"))
        if "approved metric" in fields:
            kind = "approved_metric"
        elif "approved quote" in fields:
            kind = "approved_quote"
        else:
            kind = "claim"
        claim = fields.get("approved metric") or fields.get("approved quote") or fields.get("claim", "")
        url = fields.get("url", "")
        evidence = fields.get("evidence", "")
        status = fields.get("status", "")
        if not claim or not evidence:
            continue

        entries.append(
            ProofEntry(
                kind=kind,
                claim=claim,
                url=url,
                evidence=evidence,
                status=status,
                line=line_number,
                section=section,
                customer=fields.get("customer/brand", "") or fields.get("customer", ""),
                artifact=(
                    fields.get("artifact", "")
                    or fields.get("proof artifact", "")
                    or fields.get("local proof artifact", "")
                ),
                use=fields.get("use", ""),
                source_class=fields.get("source class", ""),
                claim_type=fields.get("claim type", ""),
                evidence_relation=fields.get("evidence relation", ""),
                capture_receipt=fields.get("capture receipt", ""),
                capture_receipt_hash=fields.get("capture receipt hash", ""),
                classification_artifact=fields.get("classification artifact", ""),
                classification_hash=fields.get("classification hash", ""),
            )
        )

    return entries

def _parse_proof_fields(row_body: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for segment in row_body.split("|"):
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        fields[_normalize_key(key)] = _clean_field_value(value)
    return fields

def _extract_claim_candidates(
    content: str,
    known_customer_names: Sequence[str],
) -> List[ClaimCandidate]:
    body = _strip_frontmatter_preserve_lines(content)
    body = _blank_fenced_code(body)
    body = _blank_reader_supplied_worksheet_tables(body)
    candidates: List[ClaimCandidate] = []

    for paragraph in _iter_paragraphs(body):
        paragraph_text = paragraph.text.strip()
        if (
            is_production_image_placeholder_line(paragraph_text)
            or MARKDOWN_IMAGE_LINE_RE.fullmatch(paragraph_text)
        ):
            continue
        numeric_tokens = []
        if _is_candidate_claim(paragraph.text):
            numeric_tokens = _extract_numeric_tokens(_claim_text_for_detection(paragraph.text))

        names = _customer_names_in_text(paragraph.text, known_customer_names)
        has_case_study_link = _has_case_study_link(paragraph.text)
        text_for_detection = _claim_text_for_detection(paragraph.text)
        is_quote_claim = _is_exact_quote_claim(paragraph.text, names, has_case_study_link)
        is_review_authority_claim = _is_review_authority_claim(text_for_detection)
        is_named_outcome = (
            (has_case_study_link or bool(names))
            and bool(OUTCOME_SIGNAL_RE.search(text_for_detection))
        )
        is_special_claim = bool(
            numeric_tokens or is_named_outcome or is_quote_claim or is_review_authority_claim
        )
        if not is_special_claim:
            general_candidates = []
            for sentence in _split_claim_sentences(paragraph.text):
                if _is_general_claim_exempt(sentence):
                    continue
                claim_type = _general_claim_type(_claim_text_for_detection(sentence))
                if claim_type:
                    general_candidates.append(
                        ClaimCandidate(
                            text=sentence,
                            line=paragraph.line,
                            numeric_tokens=[],
                            normalized_tokens=frozenset(),
                            customer_names=frozenset(),
                            has_case_study_link=False,
                            requires_approved_quote=False,
                            claim_type=claim_type,
                        )
                    )
            if general_candidates:
                candidates.extend(general_candidates)
            continue

        candidates.append(
            ClaimCandidate(
                text=paragraph.text.strip(),
                line=paragraph.line,
                numeric_tokens=numeric_tokens,
                normalized_tokens=frozenset(_normalize_numeric_token(token) for token in numeric_tokens),
                customer_names=frozenset(names),
                has_case_study_link=has_case_study_link,
                requires_approved_quote=is_quote_claim,
                claim_type="",
            )
        )

    return candidates

def _split_claim_sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[])", text.strip())
        if sentence.strip()
    ]

def _blank_reader_supplied_worksheet_tables(content: str) -> str:
    """Exclude variable-only calculation worksheets from empirical claim checks."""
    lines = content.splitlines(keepends=True)
    blanked = list(lines)
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not (
            stripped.startswith("|")
            and "reader-supplied variables" in stripped.casefold()
            and "calculation" in stripped.casefold()
        ):
            index += 1
            continue
        cursor = index
        while cursor < len(lines) and lines[cursor].strip().startswith("|"):
            newline = "\n" if lines[cursor].endswith("\n") else ""
            blanked[cursor] = newline
            cursor += 1
        index = cursor
    return "".join(blanked)


__all__ = [
    "_extract_proof_entries", "_parse_proof_fields", "_extract_claim_candidates",
    "_split_claim_sentences", "_blank_reader_supplied_worksheet_tables",
]
