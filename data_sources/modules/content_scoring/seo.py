"""Seo responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class SeoScoringMixin:
    def _score_seo(
        self,
        content: str,
        metadata: Dict[str, Any],
        *,
        proof_sidecar: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Score SEO once through the canonical :class:`SEOQualityRater`."""
        frontmatter, visible_body, _ = split_frontmatter(content)

        meta_title = self._scoring_metadata_value(
            metadata, frontmatter, visible_body,
            metadata_key='meta_title', frontmatter_keys=('meta_title', 'title'),
            patterns=(r'\*\*Meta Title\*\*:\s*(.+)', r'^\s*Meta Title:\s*(.+)'),
        )
        meta_description = self._scoring_metadata_value(
            metadata, frontmatter, visible_body,
            metadata_key='meta_description', frontmatter_keys=('meta_description', 'description'),
            patterns=(r'\*\*Meta Description\*\*:\s*(.+)', r'^\s*Meta Description:\s*(.+)'),
        )
        primary_keyword = self._scoring_metadata_value(
            metadata, frontmatter, visible_body,
            metadata_key='primary_keyword', frontmatter_keys=('primary_keyword', 'target_keyword'),
            patterns=(r'\*\*(?:Target|Primary) Keyword\*\*:\s*(.+)', r'^\s*Primary Keyword:\s*(.+)'),
        )

        secondary_keywords = metadata.get('secondary_keywords')
        if not isinstance(secondary_keywords, list):
            secondary_keywords = None

        rate_kwargs = {
            'meta_title': meta_title or None,
            'meta_description': meta_description or None,
            'primary_keyword': primary_keyword or None,
            'secondary_keywords': secondary_keywords,
        }
        if frontmatter.get('brand') is not None:
            rate_kwargs['brand'] = frontmatter.get('brand')

        seo_guidelines = metadata.get('seo_guidelines')
        seo_guidelines = self._seo_guidelines_with_link_policy_override(
            seo_guidelines,
            proof_sidecar=proof_sidecar,
        )
        seo_rater = (
            SEOQualityRater(seo_guidelines)
            if isinstance(seo_guidelines, Mapping) and seo_guidelines
            else self.seo_rater
        )

        rated = seo_rater.rate(
            content,
            **rate_kwargs,
        )

        issues = []
        seen = set()
        finding_groups = (
            ('critical_issues', 'high'),
            ('warnings', 'medium'),
            ('suggestions', 'low'),
        )
        for group, severity in finding_groups:
            for finding in rated.get(group, []):
                normalized = str(finding).strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                issues.append({
                    'issue': normalized,
                    'fix': normalized,
                    'severity': severity,
                })

        details = dict(rated.get('details', {}))
        details.update({
            'meta_title': meta_title,
            'meta_title_length': len(meta_title),
            'meta_description': (
                meta_description[:100] + '...'
                if len(meta_description) > 100
                else meta_description
            ),
            'meta_description_length': len(meta_description),
            'primary_keyword': primary_keyword,
            'category_scores': dict(rated.get('category_scores', {})),
            'grade': rated.get('grade', ''),
            'publishing_ready': bool(rated.get('publishing_ready', False)),
            'threshold': rated.get('threshold', SEO_PUBLISHING_THRESHOLD),
            'target': rated.get('target', SEO_TARGET_SCORE),
            'target_met': bool(rated.get('target_met', False)),
            'target_status': rated.get('target_status', 'failed_floor'),
        })

        return {
            'score': max(0, min(100, round(float(rated.get('overall_score', 0))))),
            'passed': bool(rated.get('passed', rated.get('publishing_ready', False))),
            'threshold': rated.get('threshold', SEO_PUBLISHING_THRESHOLD),
            'target': rated.get('target', SEO_TARGET_SCORE),
            'target_met': bool(rated.get('target_met', False)),
            'target_status': rated.get('target_status', 'failed_floor'),
            'critical_issues': list(rated.get('critical_issues', [])),
            'issues': issues,
            'details': details
        }
    @staticmethod
    def _scoring_metadata_value(
        metadata: Mapping[str, Any],
        frontmatter: Mapping[str, Any],
        visible_body: str,
        *,
        metadata_key: str,
        frontmatter_keys: Tuple[str, ...],
        patterns: Tuple[str, ...],
    ) -> str:
        value = metadata.get(metadata_key, '')
        for key in frontmatter_keys:
            value = value or frontmatter.get(key, '')
        if value:
            return str(value)
        for pattern in patterns:
            match = re.search(pattern, visible_body, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return ''
    def _seo_guidelines_with_link_policy_override(
        self,
        seo_guidelines: object,
        *,
        proof_sidecar: Optional[str],
    ) -> object:
        """Apply a bound exact internal-link override to SEO link scoring."""
        exact_count = self._exact_internal_link_override_count(proof_sidecar)
        if exact_count is None:
            return seo_guidelines

        resolved: Dict[str, Any]
        if isinstance(seo_guidelines, Mapping):
            resolved = dict(seo_guidelines)
        else:
            resolved = dict(self.seo_rater.guidelines)

        resolved['min_internal_links'] = exact_count
        resolved['optimal_internal_links'] = exact_count
        if resolved.get('max_internal_links') is not None:
            resolved['max_internal_links'] = max(
                exact_count,
                int(resolved['max_internal_links']),
            )
        resolved['require_down_funnel_link'] = False
        return resolved
    @staticmethod
    def _exact_internal_link_override_count(proof_sidecar: Optional[str]) -> Optional[int]:
        if not proof_sidecar:
            return None
        try:
            sidecar_text = Path(proof_sidecar).read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            return None
        if not re.search(
            r"Override scope:\s*`?pre_faq_body`?",
            sidecar_text,
            flags=re.IGNORECASE,
        ):
            return None
        if not re.search(
            r"suppress(?:es)?\s+independently\s+derived\s+industry\s*(?:/|and)\s*down-funnel",
            sidecar_text,
            flags=re.IGNORECASE,
        ):
            return None
        count_match = re.search(
            r"exact_count\s*`?(\d+)`?",
            sidecar_text,
            flags=re.IGNORECASE,
        )
        if not count_match:
            return None
        return int(count_match.group(1))
