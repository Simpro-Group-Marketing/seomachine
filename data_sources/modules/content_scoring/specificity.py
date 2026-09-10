"""Specificity responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class SpecificityScoringMixin:
    def _score_specificity(self, content: str) -> Dict[str, Any]:
        """Score content for concrete examples vs vague generalizations"""
        issues = []
        details = {}

        content_lower = content.lower()
        word_count = len(content.split())

        # Count vague words
        vague_count = 0
        vague_found = []
        for pattern in self.VAGUE_WORDS:
            matches = re.findall(pattern, content_lower)
            vague_count += len(matches)
            if matches and len(vague_found) < 5:
                vague_found.extend(matches[:2])

        vague_density = (vague_count / max(word_count, 1)) * 1000
        details['vague_words_per_1000'] = round(vague_density, 1)
        details['vague_words_found'] = list(set(vague_found))[:5]

        # Count proof-sensitive specifics without treating them as proof.
        proof_sensitive_specific_count = 0
        workflow_content = content
        for pattern in self.PROOF_SENSITIVE_SPECIFICITY_PATTERNS:
            proof_sensitive_specific_count += len(re.findall(pattern, content))
            workflow_content = re.sub(pattern, " ", workflow_content)

        workflow_specific_count = 0
        for pattern in self.WORKFLOW_SPECIFICITY_PATTERNS:
            workflow_specific_count += len(
                re.findall(pattern, workflow_content, re.IGNORECASE)
            )

        specific_count = workflow_specific_count
        specific_density = (specific_count / max(word_count, 1)) * 1000
        proof_sensitive_specific_density = (
            proof_sensitive_specific_count / max(word_count, 1)
        ) * 1000
        details['specifics_per_1000'] = round(specific_density, 1)
        details['concrete_workflow_terms_per_1000'] = round(specific_density, 1)
        details['proof_sensitive_specifics_per_1000'] = round(
            proof_sensitive_specific_density,
            1,
        )
        details['proof_sensitive_specifics_count'] = proof_sensitive_specific_count

        # Count numbers and data points
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', content)
        number_density = (len(numbers) / max(word_count, 1)) * 1000
        details['numbers_per_1000'] = round(number_density, 1)

        # Calculate score
        score = 70  # Start at baseline

        # Penalize vague words (up to -25)
        if vague_density > 15:
            penalty = min(25, (vague_density - 15) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'Too many vague words ({vague_count} instances)',
                'fix': f'Replace vague words with specifics: {", ".join(vague_found[:3])}',
                'severity': 'high' if vague_density > 25 else 'medium'
            })

        # Reward concrete workflow specificity (up to +25)
        if specific_density > 2:
            bonus = min(25, specific_density * 3)
            score += bonus

        return {
            'score': max(0, min(100, round(score))),
            'issues': issues,
            'details': details
        }
