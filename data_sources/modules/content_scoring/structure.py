"""Structure responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class StructureScoringMixin:
    def _score_structure_balance(self, content: str) -> Dict[str, Any]:
        """Score content for prose-to-structure ratio"""
        issues = []
        details = {}

        _, content, _ = split_frontmatter(content)

        # Remove metadata block
        content = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^---+\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(
            r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',
            '',
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )

        lines = content.split('\n')

        list_chars, table_chars, header_chars, total_chars = self._structure_counts(lines)

        structured_chars = list_chars + table_chars
        prose_chars = total_chars - structured_chars - header_chars

        prose_ratio = prose_chars / max(total_chars - header_chars, 1)
        list_ratio = list_chars / max(total_chars, 1)
        table_ratio = table_chars / max(total_chars, 1)

        details['prose_ratio'] = round(prose_ratio, 2)
        details['list_ratio'] = round(list_ratio, 2)
        details['table_ratio'] = round(table_ratio, 2)
        details['prose_chars'] = prose_chars
        details['list_chars'] = list_chars
        details['table_chars'] = table_chars

        # Calculate score
        # Target: 50-75% prose (sweet spot for readable, scannable content)
        score, balance_issue = self._structure_balance_result(prose_ratio)
        if balance_issue is not None:
            issues.append(balance_issue)

        return {
            'score': round(score),
            'prose_ratio': round(prose_ratio, 2),
            'issues': issues,
            'details': details
        }
    @staticmethod
    def _structure_counts(lines: List[str]) -> Tuple[int, int, int, int]:
        list_chars = table_chars = header_chars = total_chars = 0
        in_html_table = False
        for line in lines:
            raw_line = line.strip()
            opens_table = bool(re.search(r'<table\b', raw_line, re.IGNORECASE))
            table_line = in_html_table or opens_table
            in_html_table = in_html_table or opens_table
            visible = html.unescape(re.sub(r'<[^>]+>', '', raw_line)).strip()
            if re.search(r'</table\s*>', raw_line, re.IGNORECASE):
                in_html_table = False
            if not visible or re.fullmatch(r'!\[[^\]]*\]\([^)]+\)', visible):
                continue
            count = len(visible)
            total_chars += count
            if table_line or '|' in visible:
                table_chars += count
            elif re.match(r'^[-*+]\s', visible) or re.match(r'^\d+\.\s', visible):
                list_chars += count
            elif re.match(r'^#+\s', visible):
                header_chars += count
        return list_chars, table_chars, header_chars, total_chars
    @staticmethod
    def _structure_balance_result(prose_ratio: float) -> Tuple[float, Optional[Dict[str, str]]]:
        if 0.50 <= prose_ratio <= 0.75:
            return 100, None
        if prose_ratio < 0.50:
            return max(0, 100 - ((0.50 - prose_ratio) * 150)), {
                'issue': f'Too much structure ({round(prose_ratio * 100)}% prose, target 50-75%)',
                'fix': 'Convert some bullet lists or tables to prose paragraphs',
                'severity': 'high' if prose_ratio < 0.35 else 'medium',
            }
        return max(0, 100 - ((prose_ratio - 0.75) * 100)), {
            'issue': f'Too much prose ({round(prose_ratio * 100)}% prose, target 50-75%)',
            'fix': 'Add tables for comparisons, lists for features, or visual breaks',
            'severity': 'medium' if prose_ratio < 0.90 else 'high',
        }
