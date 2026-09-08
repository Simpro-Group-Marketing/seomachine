"""
Content Scrubber

Removes generated-content cleanup artifacts including:
- Invisible Unicode characters (zero-width spaces, format-control characters, etc.)
- Em-dashes replaced with contextually appropriate punctuation

AI-writing detection lives in ai_copy_linter.py. Keep this module focused on safe cleanup.
"""

import argparse
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

try:
    from .image_placeholder import is_production_image_placeholder_line
    from .blog_assembly_stage_receipt import (
        StageReceiptError,
        build_stage_receipt,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
        write_stage_receipt,
    )
except ImportError:
    from image_placeholder import is_production_image_placeholder_line
    from blog_assembly_stage_receipt import (
        StageReceiptError,
        build_stage_receipt,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
        write_stage_receipt,
    )


ORIGINAL_MARKDOWN_IMAGE_PLACEHOLDER_RE = re.compile(
    r"\A!\[[^\]\r\n]+\]\(IMAGE_PLACEHOLDER_ORIGINAL_[A-Z0-9_]+\)\Z"
)
MARKDOWN_IMAGE_URL_RE = re.compile(r"\A!\[[^\]\r\n]+\]\(https?://[^\s)]+\)\Z")


def _is_protected_image_placeholder_line(line: str) -> bool:
    stripped = line.strip()
    return (
        is_production_image_placeholder_line(stripped)
        or ORIGINAL_MARKDOWN_IMAGE_PLACEHOLDER_RE.fullmatch(stripped) is not None
        or MARKDOWN_IMAGE_URL_RE.fullmatch(stripped) is not None
    )


class ContentScrubber:
    """
    Scrubs content to remove invisible marks and punctuation artifacts.
    """

    # Specific Unicode characters to remove
    WATERMARK_CHARS = [
        '\u200B',  # Zero-width space
        '\uFEFF',  # Byte Order Mark (BOM)
        '\u200C',  # Zero-width non-joiner
        '\u200D',  # Zero-width joiner
        '\u2060',  # Word joiner
        '\u00AD',  # Soft hyphen
        '\u202F',  # Narrow no-break space
        '\u2062',  # Invisible times
        '\u2063',  # Invisible separator
        '\u2064',  # Invisible plus
        '\u180E',  # Mongolian vowel separator
        '\u200E',  # Left-to-right mark
        '\u200F',  # Right-to-left mark
        '\u2028',  # Line separator
        '\u2029',  # Paragraph separator
    ]

    # Narrow phrase replacements kept for backwards-compatible cleanup.
    AI_PHRASE_REPLACEMENTS = [
        # "It's important to note that X" → "X"
        (r"[Ii]t(?:'s| is) (?:important|worth|crucial|essential) to (?:note|mention|highlight|understand|remember|recognize|emphasize) that ", ""),
        # "In today's [fast-paced/digital/modern] landscape/world"
        (r"[Ii]n today'?s (?:fast-paced|digital|modern|ever-changing|rapidly evolving|dynamic) (?:landscape|world|era|age|environment),? ?", ""),
        # "Delve/dive into"
        (r"\b[Dd]elve(?:s|d)? (?:into|deeper)\b", "explore"),
        (r"\b[Dd]ive(?:s|d)? (?:deep )?into\b", "explore"),
        # "Leverage" (overused by AI) → "use"
        (r"\b[Ll]everage(?:s|d)?\b", "use"),
        # "Utilize" → "use"
        (r"\b[Uu]tilize(?:s|d)?\b", "use"),
        # "In conclusion," / "To summarize,"
        (r"^[Ii]n conclusion,? ?", ""),
        # "It's worth mentioning" / "It bears mentioning"
        (r"[Ii]t(?:'s| is) worth mentioning (?:that )?", ""),
        (r"[Ii]t bears mentioning (?:that )?", ""),
        # "At the end of the day"
        (r"[Aa]t the end of the day,? ?", ""),
        # "This comprehensive guide"
        (r"[Tt]his comprehensive (?:guide|overview|article|resource)", "this guide"),
        # "Without further ado"
        (r"[Ww]ithout further ado,? ?", ""),
    ]

    # Overused AI filler adverbs
    AI_FILLER_ADVERBS = [
        'moreover', 'furthermore', 'additionally', 'consequently',
        'nevertheless', 'nonetheless', 'henceforth', 'thereby',
    ]

    def __init__(self):
        self.stats = {
            'unicode_removed': 0,
            'emdashes_replaced': 0,
            'format_control_removed': 0,
            'ai_phrases_replaced': 0,
        }

    def scrub(self, content: str) -> Tuple[str, Dict]:
        """
        Scrub content of invisible marks and punctuation artifacts.

        Args:
            content: The text content to scrub

        Returns:
            Tuple of (cleaned_content, statistics_dict)
        """
        # Reset stats
        self.stats = {
            'unicode_removed': 0,
            'emdashes_replaced': 0,
            'format_control_removed': 0,
            'ai_phrases_replaced': 0,
        }

        cleaned_segments = []
        for protected, segment in self._split_protected_image_placeholders(content):
            if protected:
                cleaned_segments.append(segment)
                continue
            cleaned_segments.append(self._scrub_unprotected_content(segment))

        return "".join(cleaned_segments), self.stats

    @staticmethod
    def _split_protected_image_placeholders(content: str) -> List[Tuple[bool, str]]:
        """Split complete image markers from scrubbed text without text sentinels."""
        segments: List[Tuple[bool, str]] = []
        cursor = 0
        for match in re.finditer(r"^[^\r\n]+(?=\r?$)", content, re.MULTILINE):
            if not _is_protected_image_placeholder_line(match.group(0)):
                continue
            if match.start() > cursor:
                segments.append((False, content[cursor:match.start()]))
            segments.append((True, match.group(0)))
            cursor = match.end()

        if cursor < len(content):
            segments.append((False, content[cursor:]))
        if not segments:
            segments.append((False, content))
        return segments

    def _scrub_unprotected_content(self, content: str) -> str:
        """Run the cleanup pipeline on text that is safe to mutate."""
        content = self._remove_watermark_chars(content)
        content = self._remove_format_control_chars(content)
        content = self._replace_emdashes(content)
        content = self._replace_ai_phrases(content)
        return self._clean_whitespace(content)

    def _remove_watermark_chars(self, content: str) -> str:
        """Remove specific invisible Unicode watermark characters."""
        original_len = len(content)

        for char in self.WATERMARK_CHARS:
            # For zero-width space, just remove it completely
            # Don't replace with regular space as it breaks URLs
            content = content.replace(char, '')

        self.stats['unicode_removed'] += original_len - len(content)
        return content

    def _remove_format_control_chars(self, content: str) -> str:
        """Remove all Unicode Category Cf (format-control) characters."""
        cleaned = []
        removed = 0

        for char in content:
            if unicodedata.category(char) == 'Cf':
                removed += 1
                continue
            cleaned.append(char)

        self.stats['format_control_removed'] += removed
        return ''.join(cleaned)

    def _replace_emdashes(self, content: str) -> str:
        """
        Replace em-dashes with contextually appropriate punctuation.

        Analyzes the context around each em-dash to determine the best replacement:
        - Comma: For simple separation, parenthetical phrases, or lists
        - Period: For strong breaks or when near sentence end
        - Space: When em-dash is used for attribution or breaking phrases
        """
        # Find all em-dashes with surrounding context
        emdash_pattern = r'([^\u2014]{0,100})\u2014([^\u2014]{0,100})'

        def replace_emdash(match):
            before = match.group(1)
            after = match.group(2)

            replacement = self._determine_emdash_replacement(before, after)
            self.stats['emdashes_replaced'] += 1

            return before + replacement + after

        content = re.sub(emdash_pattern, replace_emdash, content)

        return content

    def _determine_emdash_replacement(self, before: str, after: str) -> str:
        """
        Determine the best punctuation to replace an em-dash.

        Args:
            before: Text before the em-dash
            after: Text after the em-dash

        Returns:
            Replacement punctuation string
        """
        # Get the last 50 chars before and first 50 chars after
        before_context = before[-50:].strip() if before else ""
        after_context = after[:50].strip() if after else ""

        # Check if at the end of a sentence (em-dash before end punctuation)
        if after_context and after_context[0] in '.!?':
            return ''  # Remove em-dash, keep the end punctuation

        # Check if it's an attribution or citation (often at end)
        attribution_patterns = [
            r'\b(said|wrote|noted|according to|via)\s*$',
            r'^[A-Z][a-z]+ [A-Z]',  # Looks like "John Smith" after
        ]
        for pattern in attribution_patterns:
            if re.search(pattern, before_context, re.IGNORECASE) or \
               re.match(pattern, after_context):
                return ', '

        # Check if before text ends with a complete clause
        # Indicators: ends with noun/verb pattern, has subject
        has_verb_before = bool(re.search(r'\b(is|are|was|were|has|have|had|do|does|did|can|could|will|would|should|may|might)\b', before_context[-30:], re.IGNORECASE))
        has_verb_after = bool(re.search(r'\b(is|are|was|were|has|have|had|do|does|did|can|could|will|would|should|may|might)\b', after_context[:30], re.IGNORECASE))

        # If both sides have verbs, they might be independent clauses
        if has_verb_before and has_verb_after:
            # Check if after starts with capital (stronger break)
            if after_context and after_context[0].isupper():
                # Could be a new sentence
                return '. '
            # Check for conjunctive adverbs that need a stronger break
            conjunctive_adverbs = ['however', 'therefore', 'moreover', 'furthermore',
                                   'nevertheless', 'consequently', 'thus', 'hence']
            after_lower = after_context.lower()
            if any(after_lower.startswith(adv) for adv in conjunctive_adverbs):
                return '. '
            # Otherwise use a comma to avoid introducing semicolons
            return ', '

        # Check if it's a list or series
        if ',' in before_context[-20:] or ',' in after_context[:20]:
            return ', '

        # Check for parenthetical or explanatory content
        # Usually lowercase after em-dash for parenthetical
        if after_context and after_context[0].islower():
            return ', '

        # Check if after content is short (might be an aside)
        if len(after_context) < 30:
            return ', '

        # Default: Use comma for general separation
        return ', '

    def _replace_ai_phrases(self, content: str) -> str:
        """Replace common AI-telltale phrases with natural alternatives."""
        for pattern, replacement in self.AI_PHRASE_REPLACEMENTS:
            content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
            self.stats['ai_phrases_replaced'] += count
        return content

    def _clean_whitespace(self, content: str) -> str:
        """Clean up multiple spaces and normalize whitespace."""
        # Replace multiple inline spaces while preserving line indentation and
        # conventional double spacing after a period.
        content = re.sub(r'(?<![.\s]) {2,}', ' ', content)
        
        # Remove spaces that appear between filename and extension (e.g., "file. png" -> "file.png")
        content = re.sub(r'(\w)\s+\.\s*(\w+)', r'\1.\2', content)
        
        # Remove space before punctuation
        content = re.sub(r'\s+([,;:!?])', r'\1', content)
        
        # Only add space after sentence-ending punctuation (.!?) when followed by capital letter
        # AND only if preceded by a word character (ensures it's end of sentence, not a domain/file)
        # This avoids breaking URLs, TLDs, and file extensions while fixing sentence spacing
        content = re.sub(r'([a-z0-9])([.!?])([A-Z])', r'\1\2 \3', content)

        # Clean up line breaks
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 consecutive newlines

        return content


def scrub_content(content: str, verbose: bool = False) -> str:
    """
    Convenience function to scrub content.

    Args:
        content: The text to scrub
        verbose: If True, print statistics

    Returns:
        Cleaned content
    """
    scrubber = ContentScrubber()
    cleaned_content, stats = scrubber.scrub(content)

    if verbose:
        print("Content Scrubbing Complete:")
        print(f"  - Unicode watermarks removed: {stats['unicode_removed']}")
        print(f"  - Format-control chars removed: {stats['format_control_removed']}")
        print(f"  - Em-dashes replaced: {stats['emdashes_replaced']}")
        print(f"  - AI phrases replaced: {stats['ai_phrases_replaced']}")

    return cleaned_content


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _receipt_identity(
    run_id: Optional[str], previous_receipt: Optional[str]
) -> Tuple[str, str]:
    if not previous_receipt:
        return run_id or str(uuid4()), ''
    previous = load_stage_receipt(previous_receipt)
    previous_run_id = str(previous['run_id'])
    if run_id:
        if run_id == previous_run_id:
            pass
        else:
            raise StageReceiptError(
                'stage_receipt_run_id_mismatch',
                'run_id must match the previous receipt',
            )
    return run_id or previous_run_id, str(previous['receipt_hash'])


def scrub_file(
    file_path: str,
    verbose: bool = False,
    *,
    stage_receipt_output: Optional[str] = None,
    run_id: Optional[str] = None,
    previous_receipt: Optional[str] = None,
    stage: str = 'scrub',
) -> Optional[Dict[str, Any]]:
    """
    Inspect a file and report scrub changes without mutating article Markdown.

    Args:
        file_path: Path to file to scrub
        verbose: If True, print statistics
    """
    if stage not in {'scrub', 'post_optimization_scrub'}:
        raise StageReceiptError(
            'stage_receipt_stage_invalid',
            'content scrubber stage must be scrub or post_optimization_scrub',
        )
    input_path = Path(file_path).resolve()
    receipt_path = (
        Path(stage_receipt_output).resolve()
        if stage_receipt_output is not None
        else None
    )
    previous_path = (
        Path(previous_receipt).resolve()
        if previous_receipt is not None
        else None
    )
    _validate_scrub_paths(
        input_path=input_path,
        receipt_path=receipt_path,
        previous_receipt_path=previous_path,
    )
    started_at = datetime.now(timezone.utc) if receipt_path is not None else None
    resolved_run_id = ''
    previous_hash = ''
    if receipt_path is not None:
        resolved_run_id, previous_hash = _receipt_identity(run_id, previous_path)
        _preflight_output_path(receipt_path, "stage receipt")
    # One immutable byte snapshot drives both the input hash and scrub parse.
    input_bytes = input_path.read_bytes()
    input_hash = (
        hashlib.sha256(input_bytes).hexdigest()
        if receipt_path is not None
        else None
    )
    try:
        content = input_bytes.decode('utf-8', errors='strict')
    except UnicodeDecodeError as error:
        raise ValueError(f'content input must use valid UTF-8: {error}') from error

    # Scrub content while retaining the exact execution statistics for the receipt.
    scrubber = ContentScrubber()
    cleaned_content, statistics = scrubber.scrub(content)
    if verbose:
        print("Content Scrubbing Complete:")
        print(f"  - Unicode watermarks removed: {statistics['unicode_removed']}")
        print(f"  - Format-control chars removed: {statistics['format_control_removed']}")
        print(f"  - Em-dashes replaced: {statistics['emdashes_replaced']}")
        print(f"  - AI phrases replaced: {statistics['ai_phrases_replaced']}")

    if receipt_path is None:
        return {
            "file": str(input_path),
            "would_change": content != cleaned_content,
            "statistics": dict(statistics),
        }

    if content != cleaned_content:
        raise StageReceiptError(
            'scrub_changes_required',
            'scrub diagnostics found required edits; apply them through the owning command before minting a clean receipt',
        )

    output_hash = input_hash
    statistics_hash = hashlib.sha256(
        json.dumps(
            statistics,
            ensure_ascii=True,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8')
    ).hexdigest()
    stage_receipt = build_stage_receipt(
        run_id=resolved_run_id,
        stage=stage,
        tool_name='content_scrubber',
        tool_version='1.0.0',
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        mutation=False,
        input_artifact_hashes={'article': input_hash},
        output_artifact_hashes={'article': output_hash},
        evidence_hashes={'scrub_statistics': statistics_hash},
        previous_receipt_hash=previous_hash,
    )
    write_stage_receipt(receipt_path, stage_receipt)

    if verbose:
        print(f"Scrub diagnostics recorded to: {receipt_path}")
    return stage_receipt


def _path_identity(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _validate_scrub_paths(
    *,
    input_path: Path,
    receipt_path: Optional[Path],
    previous_receipt_path: Optional[Path],
) -> None:
    if previous_receipt_path is not None and receipt_path is None:
        raise StageReceiptError(
            'stage_receipt_previous_without_output',
            'previous_receipt requires stage_receipt_output',
        )
    input_identity = _path_identity(input_path)
    previous_identity = (
        _path_identity(previous_receipt_path)
        if previous_receipt_path is not None
        else None
    )
    if previous_identity == input_identity:
        raise StageReceiptError(
            'stage_receipt_path_collision',
            'previous receipt cannot overwrite or be overwritten by article content',
        )
    if receipt_path is not None:
        receipt_identity = _path_identity(receipt_path)
        evidence_identity = _path_identity(stage_evidence_path(receipt_path))
        if receipt_identity in {
            input_identity,
            previous_identity,
        }:
            raise StageReceiptError(
                'stage_receipt_path_collision',
                'stage receipt path must be distinct from article and predecessor paths',
            )
        if evidence_identity in {
            input_identity,
            output_identity,
            previous_identity,
            receipt_identity,
        }:
            raise StageReceiptError(
                'stage_receipt_path_collision',
                'stage evidence path must be distinct from article and receipt paths',
            )


def _preflight_output_path(path: Path, label: str) -> None:
    probe: Optional[Path] = None
    try:
        if path.exists() and not path.is_file():
            raise OSError(f'{label} destination is not a file')
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            'w',
            encoding='utf-8',
            newline='\n',
            dir=path.parent,
            prefix=f'.{path.name}.',
            suffix='.preflight',
            delete=False,
        ) as handle:
            probe = Path(handle.name)
            handle.write('{}\n')
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise StageReceiptError(
            'stage_receipt_destination_invalid',
            f'{label} destination is not writable: {error}',
        ) from error
    finally:
        if probe is not None:
            probe.unlink(missing_ok=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Scrub generated-content artifacts.')
    parser.add_argument('file_path')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--stage-receipt-output')
    parser.add_argument('--run-id')
    parser.add_argument('--previous-receipt')
    parser.add_argument(
        '--stage',
        choices=('scrub', 'post_optimization_scrub'),
        default='scrub',
    )
    args = parser.parse_args(argv)
    try:
        receipt = scrub_file(
            args.file_path,
            verbose=args.verbose,
            stage_receipt_output=args.stage_receipt_output,
            run_id=args.run_id,
            previous_receipt=args.previous_receipt,
            stage=args.stage,
        )
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    if receipt:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
