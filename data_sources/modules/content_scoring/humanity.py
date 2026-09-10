"""Humanity responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class HumanityScoringMixin:
    def _clean_for_analysis(self, content: str) -> str:
        """Remove markdown formatting for text analysis"""
        _, text, _ = split_frontmatter(content)

        # Remove frontmatter/metadata block
        text = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)

        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text)

        # Exclude non-visible HTML while retaining text rendered inside tables
        # and other semantic elements.
        text = re.sub(
            r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',
            '',
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)

        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove bold/italic markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remove headers but keep text
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        return text.strip()
    def _score_humanity(self, content: str, lint_source: Optional[str] = None) -> Dict[str, Any]:
        """Score content for human voice and personality"""
        issues = []
        details = {}

        word_count = len(content.split())

        # Use the shared deterministic AI copy linter so scoring and lint gates
        # do not drift into separate phrase lists.
        copy_lint_findings = lint_content(lint_source or content)
        copy_lint_errors = [
            finding for finding in copy_lint_findings
            if finding["severity"] == "error"
        ]
        copy_lint_warnings = [
            finding for finding in copy_lint_findings
            if finding["severity"] == "warning"
        ]
        passive_findings = [
            finding for finding in copy_lint_findings
            if finding["rule_id"] == "passive_voice"
        ]

        ai_density = (len(copy_lint_errors) / max(word_count, 1)) * 1000
        warning_density = (len(copy_lint_warnings) / max(word_count, 1)) * 1000
        passive_ratio = len(passive_findings) / max(word_count / 100, 1)

        details['ai_phrases_per_1000'] = round(ai_density, 1)
        details['ai_phrases_found'] = [
            str(finding["match"]) for finding in copy_lint_errors[:5]
        ]
        details['ai_copy_lint_errors'] = len(copy_lint_errors)
        details['ai_copy_lint_warnings'] = len(copy_lint_warnings)
        details['ai_copy_lint_findings'] = [
            {
                "rule_id": finding["rule_id"],
                "severity": finding["severity"],
                "line": finding["line"],
                "match": finding["match"],
            }
            for finding in copy_lint_findings[:10]
        ]

        # Count conversational devices
        conversational_count = 0
        for pattern in self.CONVERSATIONAL_PATTERNS:
            conversational_count += len(re.findall(pattern, content, re.IGNORECASE))

        conv_density = (conversational_count / max(word_count, 1)) * 1000
        details['conversational_per_1000'] = round(conv_density, 1)

        details['passive_voice_ratio'] = round(passive_ratio, 2)

        # Count contractions
        contractions = len(re.findall(r"'(?:t|s|re|ve|ll|d|m)\b", content))
        contraction_density = (contractions / max(word_count, 1)) * 100
        details['contractions_per_100'] = round(contraction_density, 1)

        # Calculate score
        score = 100

        # Penalize blocking AI copy lint errors (up to -35)
        if copy_lint_errors:
            penalty = min(35, max(10, ai_density * 3))
            score -= penalty
            issues.append({
                'issue': f'AI copy lint errors detected ({len(copy_lint_errors)} instances)',
                'fix': 'Remove or rephrase: ' + ", ".join(
                    str(finding["match"]) for finding in copy_lint_errors[:3]
                ),
                'severity': 'high'
            })

        # Penalize warning clusters (up to -15)
        if warning_density > 8:
            penalty = min(15, (warning_density - 8) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'AI copy lint warnings detected ({len(copy_lint_warnings)} instances)',
                'fix': 'Review linter warnings for passive voice, filler, vague language, and modal verbs',
                'severity': 'medium'
            })

        # Penalize high passive voice (up to -15)
        if passive_ratio > 2:
            penalty = min(15, (passive_ratio - 2) * 5)
            score -= penalty
            issues.append({
                'issue': 'High passive voice usage',
                'fix': 'Convert passive sentences to active voice',
                'severity': 'medium'
            })

        # Reward conversational devices (up to +15)
        if conv_density > 3:
            bonus = min(15, (conv_density - 3) * 2)
            score = min(100, score + bonus)

        # Penalize lack of contractions (up to -10)
        if contraction_density < 1:
            score -= 10
            issues.append({
                'issue': 'Lacks contractions (sounds formal)',
                'fix': "Use contractions like don't, can't, you're, it's",
                'severity': 'low'
            })

        return {
            'score': max(0, min(100, round(score))),
            'issues': issues,
            'details': details
        }
