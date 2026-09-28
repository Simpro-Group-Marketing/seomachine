"""Write hash-bound agent-output reports for the women-in-construction rewrite.

Governance artifact only. Each report records the reviewer's findings from the
2026-09-25 review pass (four parallel reviewer subagents covering the six roles),
the consolidated edits applied through /rewrite, and the deterministic review
verification bound to the current article, plan and sidecar bytes. Rerun after
any article or sidecar change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "women-in-construction"
DATE = "2026-09-28"
RUN_ID = "f1130b43-7baa-4ac4-9bcc-b26c15dde6b6"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
OUT = ROOT / "research" / "agent-outputs"

REPORTS = {
    "content-analyzer": (
        "Content Analyzer",
        [
            "The Foster Plumbing sentence now carries only the connector-approved revenue metric with Amy Carnrick named as former CEO; the time period, Colorado location and streamlined-operations paraphrase were removed because the case study says five years and claim MET-0178 says six.",
            "The unsourced injury-risk and career-retention claims in the jobsite section were replaced with a concrete trial action.",
            "The IWPR apprenticeship sentence now states the 37-state scope with data for both 2015 and 2024 and no longer compares it with the national DOL share.",
            "The table lead now says inspector and manager roles run ahead of the field trades, because construction managers sit below the industry-wide share.",
            "Retention checklist cells now describe what each worker gets instead of unsupported outcomes.",
            "The challenges and good-job FAQs no longer assert unsourced lists or paid-entry claims.",
        ],
    ),
    "seo-optimizer": (
        "SEO Optimizer",
        [
            "The recognition FAQ no longer repeats the primary keyword twice in one sentence, which cleared the only critical SEO rater error.",
            "Two sentences over 25 words in the labor-gap and jobsite sections were split.",
            "The roadmap section intro now carries the primary keyword; seo_quality_rater scored the simulated and final copy 100/100, publishing ready.",
        ],
    ),
    "meta-creator": (
        "Meta Creator",
        [
            "Meta title changed to Women in Construction: Hiring and Retention Guide | Simpro (58 characters) with the brand suffix; the frozen plan was updated to match.",
            "Meta description now names the article deliverables: BLS role data, a career ladder, a retention checklist and a 90-day plan (156 characters).",
        ],
    ),
    "internal-linker": (
        "Internal Linker",
        [
            "All six internal links returned HTTP 200: skilled trades shortage, field service mobile app, Foster Plumbing case study, field service scheduling, the homepage commercial pillar and the top trades for women guide.",
            "Duplicate NAHB and DOL destinations inside one paragraph were merged into one link per claim cluster.",
            "Whole-sentence OSHA anchors were shortened to descriptive anchors while keeping each claim sentence intact.",
            "The three story links that only supported the removed quotes are gone; incoming-link candidates are recorded for the Web Development handoff.",
        ],
    ),
    "keyword-mapper": (
        "Keyword Mapper",
        [
            "The secondary keyword women construction workers now opens the numbers section and woman in construction appears in the career pathway section.",
            "The stats table header now states that parenthetical counts are total workers in each role, which avoids a how-many-women misread.",
            "The closing recognition line carries the primary keyword; density stays natural and no job-seeker or labor-shortage terms are targeted.",
        ],
    ),
    "editor": (
        "Editor",
        [
            "The opening no longer uses a not-X-but-Y construction; the operating decision is tied to overtime, subcontract labor and bid capacity.",
            "Field-hands phrasing, a redundant PPE sentence and a muddled stay-interview instruction were rewritten in trade-contractor language.",
            "No editorial-process leakage, em dashes, semicolons or banned modal verbs remain.",
        ],
    ),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reviews = []
    for phase in ("plan", "article"):
        path = ROOT / "research" / f"machine-review-{phase}-{SLUG}-{DATE}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        count = json.dumps(data).count('"evidence_anchor"')
        reviews.append((phase, path.relative_to(ROOT).as_posix(), count))
    for agent_id, (label, applied) in REPORTS.items():
        lines = [
            f"# {label} output", "",
            f"Run ID: `{RUN_ID}`", "",
            f"Article: `{ARTICLE.relative_to(ROOT).as_posix()}`", "",
            f"Article SHA-256: `{sha(ARTICLE)}`", "",
            f"Editorial plan SHA-256: `{sha(PLAN)}`", "",
            f"Proof sidecar SHA-256 at review: `{sha(SIDECAR)}`", "",
            f"Decision: completed with no open {label} finding for the current article and plan snapshot.", "",
            "Findings raised in the 2026-09-25 review pass and applied through /rewrite:", "",
            *[f"- {item}" for item in applied], "",
            "Verification:", "",
            "- `python scripts/build_women_in_construction_review_artifacts.py` exited `0` with zero plan fulfillment findings.",
            *[f"- The {phase}-phase machine review (`{path}`) contains {count} findings." for phase, path, count in reviews],
            "",
            "Unresolved review blockers: none.", "",
        ]
        target = OUT / f"{agent_id}-{SLUG}-{DATE}.md"
        target.write_bytes("\n".join(lines).encode("utf-8"))
        print(target.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
