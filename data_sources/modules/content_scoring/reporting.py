"""Reporting responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class ScoringReportingMixin:
    def format_report(self, result: Dict[str, Any]) -> str:
        """Format scoring result as readable report"""
        lines = []
        lines.append("=" * 50)
        lines.append("CONTENT QUALITY SCORE")
        lines.append("=" * 50)
        lines.append("")

        status = "PASSED" if result['passed'] else "BELOW THRESHOLD"
        lines.append(f"Composite Score: {result['composite_score']}/100 ({status})")
        lines.append(f"Content Quality Threshold: {result['threshold']}")
        aeo_geo = result.get('aeo_geo', {})
        if aeo_geo:
            lines.append(
                f"AEO/GEO Score: {aeo_geo.get('score', 0)}/100 "
                f"(threshold: {aeo_geo.get('threshold', 90)})"
            )
        lines.append("")

        lines.append("Dimensions:")
        for dim_name, dim_data in result['dimensions'].items():
            score = dim_data['score']
            weight = dim_data['weight']
            check = "OK" if score >= 70 else "NEEDS WORK"
            extra = ""
            if dim_name == 'structure_balance':
                extra = f" ({round(dim_data.get('prose_ratio', 0) * 100)}% prose)"
            elif dim_name == 'readability':
                flesch = dim_data.get('flesch', 0)
                details = dim_data.get('details', {})
                rhythm = details.get('rhythm_score', 'N/A')
                long_paras = details.get('long_paragraphs', 0)
                extra = f" (Flesch: {flesch}, Rhythm: {rhythm}, Long¶: {long_paras})"

            lines.append(f"  {dim_name:20} {score:3}/100 (weight: {int(weight*100)}%) [{check}]{extra}")

        lines.append("")

        if result['priority_fixes']:
            lines.append("Priority Fixes:")
            for i, fix in enumerate(result['priority_fixes'][:5], 1):
                dim = fix.get('dimension', 'unknown')
                issue = fix.get('issue', 'Unknown issue')
                suggestion = fix.get('fix', 'No suggestion')
                lines.append(f"  {i}. [{dim}] {issue}")
                lines.append(f"     Fix: {suggestion}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)
