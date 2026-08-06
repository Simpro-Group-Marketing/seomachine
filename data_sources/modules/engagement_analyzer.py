"""
Engagement Analyzer

Analyzes articles for the 4 current engagement criteria:
1. Hook quality (not generic opening)
2. Sentence rhythm variety
3. CTA alignment with an optional article-plan CTA map
4. Paragraph length (max 4 sentences)
"""

import argparse
import glob
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class EngagementAnalyzer:
    """Analyzes articles for engagement criteria"""

    # Generic opening patterns to flag (bad hooks)
    GENERIC_OPENERS = [
        r'^[A-Z][^.!?]*\bis\s+(?:a|an|the)\s+',  # "X is a/an/the..."
        r'^[A-Z][^.!?]*\bare\s+(?:a|an|the|both)\s+',  # "X are a/an/the..."
        r'^When it comes to',
        r'^In (?:today\'s|the|this)\s+(?:digital|modern|world|age)',
        r'^(?:Podcast|Audio|Content)\s+(?:hosting|marketing|creation)\s+(?:is|has|can)',
        r'^If you\'re (?:looking|searching|trying)',
        r'^(?:Many|Most|Some)\s+(?:podcasters?|creators?|people)',
        r'^There are (?:many|several|numerous)',
        r'^It\'s (?:no secret|important|essential)',
    ]

    # Good hook patterns
    GOOD_HOOK_PATTERNS = [
        r'^\?',  # Ends with question (first sentence)
        r'^["\']',  # Opens with quote
        r'^\d+%?\s+',  # Opens with number/statistic
        r'^(?:What if|Imagine|Picture this|Here\'s (?:the thing|a secret))',
        r'^(?:Last|In) (?:week|month|year|January|February|March|April|May|June|July|August|September|October|November|December)',
        r'^[A-Z][a-z]+\s+(?:discovered|realized|learned|found|spent|launched|started)',  # Name + past verb (story)
    ]

    # CTA patterns
    CTA_PATTERNS = [
        r'\[.{5,50}→\]',  # [Text →]
        r'\*\*\[.{5,50}\]',  # **[Text]
        r'(?:Start|Try|Get|Begin|Sign up|Create).{0,20}(?:free|trial|today|now)',
        r'(?:Learn|Read|Discover|Explore|See)\s+(?:more|how)',
        r'Ready to\s+\w+',
        r'Want to\s+(?:see|learn|try|get)',
    ]

    # Legacy name patterns retained only for older report compatibility.
    NAME_PATTERNS = [
        r'\b(?:Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|Tom|Anna|James|Maria|Rachel|Dan|Kate)\b',
        r'\b(?:The team at|At) [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',  # "The team at Acme"
        r'\b[A-Z][a-z]+\'s (?:podcast|show|episode|company|business|team)\b',  # "Sarah's podcast"
    ]

    def analyze(
        self,
        content: str,
        filename: str = "",
        cta_plan: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Analyze article engagement and optionally enforce its planned CTA count."""
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if not isinstance(filename, str):
            raise ValueError("filename must be a string")
        self._validate_cta_plan(cta_plan)
        results = {
            'filename': filename,
            'hook': self._analyze_hook(content),
            'rhythm': self._analyze_rhythm(content),
            'ctas': self._analyze_ctas(content, cta_plan),
            'paragraphs': self._analyze_paragraphs(content),
        }

        # CTA compliance is unassessed when no article-plan CTA map is supplied.
        results['scores'] = {
            'hook': results['hook']['is_good'],
            'rhythm': results['rhythm']['score'] >= 45,  # Lowered from 60 - comparison articles are table-heavy by design
            'ctas': results['ctas']['meets_plan'],
            'paragraphs': results['paragraphs']['long_count'] <= 3,
        }

        assessed_scores = [
            score for score in results['scores'].values() if score is not None
        ]
        results['passed_count'] = sum(score is True for score in assessed_scores)
        results['total_criteria'] = len(assessed_scores)
        results['all_passed'] = all(score is True for score in assessed_scores)

        return results

    @staticmethod
    def _validate_cta_plan(cta_plan: Optional[Dict[str, int]]) -> None:
        if cta_plan is None:
            return
        if not isinstance(cta_plan, dict):
            raise ValueError("cta_plan must be a dictionary or None")
        for role, section_number in cta_plan.items():
            if not isinstance(role, str) or not role.strip():
                raise ValueError("cta_plan roles must be non-empty strings")
            if (
                isinstance(section_number, bool)
                or not isinstance(section_number, int)
                or section_number <= 0
            ):
                raise ValueError("cta_plan section numbers must be positive integers")
        if len(cta_plan.values()) != len(set(cta_plan.values())):
            raise ValueError("cta_plan section numbers must be distinct")

    def _analyze_hook(self, content: str) -> Dict[str, Any]:
        """Analyze opening hook quality"""
        # Get first paragraph after metadata
        lines = content.split('\n')
        first_para = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('**') or line.startswith('#') or line.startswith('---'):
                continue
            # Found first content paragraph
            first_para = line
            break

        if not first_para:
            return {'is_good': False, 'reason': 'No opening paragraph found', 'opening': ''}

        # Get first sentence
        first_sentence_match = re.match(r'^([^.!?]+[.!?])', first_para)
        first_sentence = first_sentence_match.group(1) if first_sentence_match else first_para[:150]

        # Check for generic openers (bad)
        for pattern in self.GENERIC_OPENERS:
            if re.search(pattern, first_para, re.IGNORECASE):
                return {
                    'is_good': False,
                    'reason': 'Generic opening detected',
                    'opening': first_sentence[:100]
                }

        # Check for good hook patterns
        for pattern in self.GOOD_HOOK_PATTERNS:
            if re.search(pattern, first_para):
                return {
                    'is_good': True,
                    'reason': 'Good hook pattern found',
                    'opening': first_sentence[:100]
                }

        # Check if first sentence is a question
        if first_sentence.strip().endswith('?'):
            return {
                'is_good': True,
                'reason': 'Opens with question',
                'opening': first_sentence[:100]
            }

        # Check for numbers/statistics in opening
        if re.search(r'\b\d+(?:%|,\d{3}|\s+(?:percent|downloads?|episodes?))', first_para[:200]):
            return {
                'is_good': True,
                'reason': 'Opens with statistic',
                'opening': first_sentence[:100]
            }

        # Default: check if it's reasonably engaging (not definitional)
        if not re.search(r'\bis\s+(?:a|an|the)\s+\w+\s+(?:that|which|for)', first_sentence):
            return {
                'is_good': True,
                'reason': 'Acceptable opening (not definitional)',
                'opening': first_sentence[:100]
            }

        return {
            'is_good': False,
            'reason': 'Opening may be too generic',
            'opening': first_sentence[:100]
        }

    def _analyze_rhythm(self, content: str) -> Dict[str, Any]:
        """Analyze sentence rhythm variety in prose sections only"""
        # Clean content - remove all structured elements
        clean = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', content, flags=re.MULTILINE)  # Bold labels
        clean = re.sub(r'^#+\s+.+$', '', clean, flags=re.MULTILINE)  # Headers
        clean = re.sub(r'^\|.+\|$', '', clean, flags=re.MULTILINE)  # Tables
        clean = re.sub(r'^[-*]\s+.+$', '', clean, flags=re.MULTILINE)  # Bullet lists
        clean = re.sub(r'^\d+\.\s+.+$', '', clean, flags=re.MULTILINE)  # Numbered lists
        clean = re.sub(r'^---+$', '', clean, flags=re.MULTILINE)  # Horizontal rules
        clean = re.sub(r'^\*\*[^*]+\*\*$', '', clean, flags=re.MULTILINE)  # Bold-only lines (winners, labels)
        clean = re.sub(r'^\[.+→\].*$', '', clean, flags=re.MULTILINE)  # CTA links

        # Extract sentences
        sentences = re.split(r'[.!?]+(?:\s|$)', clean)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        if len(sentences) < 10:
            return {'score': 70, 'monotonous_sections': 0, 'std_dev': 0}

        word_counts = [len(s.split()) for s in sentences]

        # Check for monotonous sections
        monotonous = 0
        window_size = 5
        for i in range(len(word_counts) - window_size + 1):
            window = word_counts[i:i + window_size]
            avg = sum(window) / len(window)
            if all(abs(wc - avg) <= 5 for wc in window):
                monotonous += 1

        # Calculate std dev
        mean = sum(word_counts) / len(word_counts)
        std_dev = (sum((wc - mean) ** 2 for wc in word_counts) / len(word_counts)) ** 0.5

        # Score based on std_dev (variety)
        if std_dev < 5:
            score = 40 + (std_dev * 6)
        elif std_dev <= 15:
            score = 100 - abs(10 - std_dev) * 2
        else:
            score = 80

        # Reduce penalty - cap monotonous impact at 20 points
        monotonous_penalty = min(monotonous, 10) * 2
        score -= monotonous_penalty
        score = max(0, min(100, score))

        return {
            'score': round(score),
            'monotonous_sections': monotonous,
            'std_dev': round(std_dev, 1),
            'sentence_count': len(sentences),
            'avg_length': round(mean, 1)
        }

    def _analyze_mini_stories(self, content: str) -> Dict[str, Any]:
        """Legacy helper retained for older report compatibility."""
        stories_found = []

        # Look for name patterns
        for pattern in self.NAME_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 100)
                context = content[start:end]

                # Check if it's in a story context (has outcome indicators)
                if re.search(r'(?:discovered|realized|found|spent|cost|saved|grew|increased|launched|started|switched|moved)', context, re.IGNORECASE):
                    stories_found.append({
                        'name': match.group(),
                        'context': context[:80].strip()
                    })

        # Deduplicate by name
        unique_names = set()
        unique_stories = []
        for story in stories_found:
            if story['name'] not in unique_names:
                unique_names.add(story['name'])
                unique_stories.append(story)

        return {
            'count': len(unique_stories),
            'names_found': list(unique_names)[:5],
            'stories': unique_stories[:3]
        }

    def _analyze_ctas(
        self,
        content: str,
        cta_plan: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Report CTA observations and evaluate count only when a plan is supplied."""
        ctas = []
        candidates = []

        for pattern in self.CTA_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                candidates.append((match.start(), match.end(), match.group()))

        accepted_spans = []
        for start, end, matched_text in sorted(
            candidates,
            key=lambda item: (item[0], -(item[1] - item[0])),
        ):
            if any(
                start < accepted_end and end > accepted_start
                for accepted_start, accepted_end in accepted_spans
            ):
                continue
            accepted_spans.append((start, end))
            position = start / max(len(content), 1) * 100
            ctas.append({
                'text': matched_text[:50],
                'position_pct': round(position),
                'role': self._classify_cta_role(matched_text),
                '_start_offset': start,
            })

        ctas.sort(key=lambda item: item['_start_offset'])

        h2_starts = [
            match.start()
            for match in re.finditer(r'^##\s+', content, re.MULTILINE)
        ]
        for cta in ctas:
            cta['section_number'] = 1 + sum(
                heading_start < cta['_start_offset'] for heading_start in h2_starts
            )
            del cta['_start_offset']

        # Check distribution
        word_count = len(content.split())
        words_before_first_cta = None

        if ctas:
            first_cta_pos = min(c['position_pct'] for c in ctas)
            words_before_first_cta = int(word_count * first_cta_pos / 100)

        # Check if CTAs are distributed (not all at end)
        distributed = False
        if len(ctas) >= 2:
            positions = [c['position_pct'] for c in ctas]
            # Check if at least one CTA in first half and at least one in second half
            has_early = any(p < 50 for p in positions)
            has_late = any(p > 70 for p in positions)
            distributed = has_early and has_late

        evaluation_status = 'evaluated' if cta_plan is not None else 'reported'
        required_count = len(cta_plan) if cta_plan is not None else None
        planned_section_locations = (
            list(cta_plan.values()) if cta_plan is not None else None
        )
        observed_section_locations = [cta['section_number'] for cta in ctas]
        locations_match_plan = (
            sorted(observed_section_locations) == sorted(planned_section_locations)
            if planned_section_locations is not None
            else None
        )
        role_mismatches = []
        if cta_plan is not None:
            for planned_role, section_number in cta_plan.items():
                observed_roles = {
                    cta['role']
                    for cta in ctas
                    if cta['section_number'] == section_number
                }
                compatible_roles = {
                    "soft_resource_action": {"educational_next_step"},
                    "thought_leadership_next_action": {"educational_next_step"},
                }.get(planned_role, {planned_role})
                if not observed_roles.intersection(compatible_roles):
                    role_mismatches.append({
                        "planned_role": planned_role,
                        "section_number": section_number,
                        "observed_roles": sorted(observed_roles),
                    })
        roles_match_plan = not role_mismatches if cta_plan is not None else None
        meets_plan = (
            len(ctas) == required_count and locations_match_plan and roles_match_plan
            if required_count is not None
            else None
        )

        return {
            'count': len(ctas),
            'distributed': distributed,
            'first_cta_word_position': words_before_first_cta,
            'within_500_words': words_before_first_cta is not None and words_before_first_cta <= 500,
            'ctas': ctas[:5],
            'evaluation_status': evaluation_status,
            'required_count': required_count,
            'planned_section_locations': planned_section_locations,
            'observed_section_locations': observed_section_locations,
            'locations_match_plan': locations_match_plan,
            'roles_match_plan': roles_match_plan,
            'role_mismatches': role_mismatches,
            'meets_plan': meets_plan,
        }

    @staticmethod
    def _classify_cta_role(text: str) -> str:
        """Classify only CTA intent that is explicit in the observed wording."""
        normalized = re.sub(r"[*\[\]]", "", text).strip().lower()
        if re.search(r"\b(?:start|try|get|begin|sign up|create)\b", normalized):
            return "commercial_conversion"
        if re.search(r"\b(?:ready to|want to)\s+(?:see|try|get)\b", normalized):
            return "contextual_product"
        if re.search(r"\b(?:learn|read|discover|explore|see)\s+(?:more|how)\b", normalized):
            return "educational_next_step"
        return "unresolved"

    def _analyze_paragraphs(self, content: str) -> Dict[str, Any]:
        """Analyze paragraph lengths"""
        paragraphs = re.split(r'\n\s*\n', content)

        long_paragraphs = []
        total_paras = 0

        for para in paragraphs:
            para = para.strip()
            # Skip non-prose (headers, lists, tables, metadata, numbered lists)
            if not para or para.startswith('#') or para.startswith('-') or para.startswith('*') or para.startswith('|') or para.startswith('**Meta'):
                continue
            # Skip numbered lists (1. 2. etc.)
            if re.match(r'^\d+\.', para):
                continue

            total_paras += 1
            sentences = re.split(r'[.!?]+(?:\s|$)', para)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

            if len(sentences) > 4:
                long_paragraphs.append({
                    'sentence_count': len(sentences),
                    'preview': para[:60] + '...'
                })

        return {
            'total_paragraphs': total_paras,
            'long_count': len(long_paragraphs),
            'long_paragraphs': long_paragraphs[:3]
        }


def format_results(results: List[Dict]) -> str:
    """Format analysis results as a table"""
    lines = []
    lines.append("=" * 90)
    lines.append("ENGAGEMENT CRITERIA ANALYSIS")
    lines.append("=" * 90)
    lines.append("")

    # Summary header (4 criteria, stories removed)
    lines.append(f"{'Article':<45} {'Hook':^8} {'Rhythm':^8} {'CTAs':^8} {'Paras':^8} {'Score':^8}")
    lines.append("-" * 90)

    passed_all = 0
    totals = {'hook': 0, 'rhythm': 0, 'ctas': 0, 'paragraphs': 0}

    for r in results:
        name = Path(r['filename']).stem[:43] if r['filename'] else "Untitled"
        hook = "✓" if r['scores']['hook'] else "✗"
        rhythm = "✓" if r['scores']['rhythm'] else "✗"
        ctas = "✓" if r['scores']['ctas'] else "✗"
        paras = "✓" if r['scores']['paragraphs'] else "✗"
        if r['scores']['ctas'] is None:
            ctas = "N/A"
        score = f"{r['passed_count']}/{r['total_criteria']}"

        if r['all_passed']:
            passed_all += 1

        for key in totals:
            if r['scores'][key]:
                totals[key] += 1

        lines.append(f"{name:<45} {hook:^8} {rhythm:^8} {ctas:^8} {paras:^8} {score:^8}")

    lines.append("-" * 90)
    lines.append(f"{'TOTALS PASSING':<45} {totals['hook']:^8} {totals['rhythm']:^8} {totals['ctas']:^8} {totals['paragraphs']:^8} {passed_all:^8}")
    lines.append(f"{'(out of ' + str(len(results)) + ')':<45}")
    lines.append("")

    # Detailed issues
    lines.append("=" * 90)
    lines.append("DETAILED ISSUES BY CRITERION")
    lines.append("=" * 90)

    # Hook issues
    hook_issues = [r for r in results if not r['scores']['hook']]
    if hook_issues:
        lines.append("")
        lines.append(f"❌ HOOK ISSUES ({len(hook_issues)} articles):")
        for r in hook_issues:
            lines.append(f"   • {Path(r['filename']).stem}")
            lines.append(f"     Opening: \"{r['hook']['opening'][:70]}...\"")
            lines.append(f"     Reason: {r['hook']['reason']}")

    # CTA issues
    cta_issues = [r for r in results if r['scores']['ctas'] is False]
    if cta_issues:
        lines.append("")
        lines.append(f"❌ CTA DISTRIBUTION ISSUES ({len(cta_issues)} articles):")
        for r in cta_issues:
            lines.append(f"   • {Path(r['filename']).stem}: {r['ctas']['count']} CTAs, distributed={r['ctas']['distributed']}")

    # Paragraph issues
    para_issues = [r for r in results if not r['scores']['paragraphs']]
    if para_issues:
        lines.append("")
        lines.append(f"❌ PARAGRAPH LENGTH ISSUES ({len(para_issues)} articles - >3 long paragraphs):")
        for r in para_issues:
            lines.append(f"   • {Path(r['filename']).stem}: {r['paragraphs']['long_count']} paragraphs >4 sentences")

    # Rhythm issues (list last as there are many)
    rhythm_issues = [r for r in results if not r['scores']['rhythm']]
    if rhythm_issues:
        lines.append("")
        lines.append(f"❌ RHYTHM ISSUES ({len(rhythm_issues)} articles - monotonous sentence patterns):")
        for r in rhythm_issues:
            lines.append(f"   • {Path(r['filename']).stem}: score={r['rhythm']['score']}, monotonous_sections={r['rhythm']['monotonous_sections']}")

    lines.append("")
    lines.append("=" * 90)

    return "\n".join(lines)


def parse_cli_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse explicit files or a configurable Markdown glob."""
    parser = argparse.ArgumentParser(
        description="Analyze article engagement and optional CTA-plan compliance."
    )
    parser.add_argument("files", nargs="*", help="Markdown files to analyze")
    parser.add_argument(
        "--glob",
        dest="pattern",
        default="drafts/*.md",
        help="Glob used when no explicit files are supplied (default: drafts/*.md)",
    )
    parser.add_argument(
        "--cta-plan",
        help=(
            "CTA map as JSON, or a JSON article-plan file containing "
            "engagement_map.ctas"
        ),
    )
    return parser.parse_args(argv)


def load_cta_plan(value: Optional[str]) -> Optional[Dict[str, int]]:
    """Load a direct CTA map or extract one from a serialized article plan."""
    if value is None:
        return None
    candidate = Path(value)
    try:
        raw = candidate.read_text(encoding="utf-8") if candidate.is_file() else value
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid --cta-plan: {exc}") from exc

    if isinstance(payload, dict) and "engagement_map" in payload:
        payload = payload["engagement_map"]
    if isinstance(payload, dict) and "ctas" in payload:
        payload = payload["ctas"]
    EngagementAnalyzer._validate_cta_plan(payload)
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    """Analyze explicit Markdown files or all drafts matching a caller glob."""
    args = parse_cli_args(argv)
    files = sorted(args.files or glob.glob(args.pattern))
    try:
        cta_plan = load_cta_plan(args.cta_plan)
    except ValueError as exc:
        print(str(exc))
        return 2

    if not files:
        print(f"No files found matching {args.pattern}")
        return 1

    print(f"Found {len(files)} articles to analyze...")
    print("")

    analyzer = EngagementAnalyzer()
    results = []

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        filename = Path(filepath).name
        result = analyzer.analyze(content, filename, cta_plan=cta_plan)
        results.append(result)

    print(format_results(results))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
