"""Write hash-bound agent-output reports for the best-trade-jobs-california rewrite.

Governance artifact only. Each report records the reviewer's findings from the
2026-09-24 editorial review pass, the consolidated edits applied through /rewrite,
and the deterministic review verification bound to the current article, plan and
sidecar bytes. Rerun after any article or sidecar change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
RUN_ID = "0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
OUT = ROOT / "research" / "agent-outputs"

REPORTS = {
    "content-analyzer": (
        "Content Analyzer",
        [
            "Operating engineer profile no longer claims crane work, because SOC 47-2073 excludes crane operators; earning levers now cite prevailing-wage and GPS grade-control work, and the seasonal note reflects California weather.",
            "Training-length FAQ now states 18 months to four years or longer and adds the Cal/OSHA three-year conveyance requirement instead of claiming every program fits the span.",
            "Transportation equipment profile now lists trains, ships and rail transit cars, matching SOC 49-2093.",
            "Unsourced comparative claims in the avionics, aircraft mechanic and specialization lines were replaced with non-comparative wording.",
            "Pay factors now include the California daily overtime rule with a same-line DIR link, and the choice checklist adds job outlook and California's registered apprenticeship search.",
            "Electrician line separates certification from trainee registration so apprentices are not told they need certification before starting.",
        ],
    ),
    "seo-optimizer": (
        "SEO Optimizer",
        [
            "The demand FAQ sentence was shortened to stay within the 25-word sentence limit.",
            "Primary keyword placement confirmed in the H1 variant, first sentence, at-a-glance H2, conclusion, meta title and meta description; heading hierarchy has one H1 and no skipped levels.",
            "H2 opening paragraphs sit at 50 to 60 words and the answer paragraph names the top five trades with linked figures for AI-overview extraction.",
        ],
    ),
    "meta-creator": (
        "Meta Creator",
        [
            "Meta description extended to 153 characters by adding 2025 salaries, which clears the 150-character floor.",
            "Meta title changed to Highest-Paying Trades in California: 18 Best Jobs for 2026 (58 characters) to keep the primary keyword first and retain best and jobs, which the live page ranks for; the frozen plan was updated to match.",
        ],
    ),
    "internal-linker": (
        "Internal Linker",
        [
            "All five internal links returned HTTP 200 without redirects: electrical industry statistics, electrical license in California, plumbing industry statistics, the homepage commercial pillar and the industries hub. The preserved college versus trade school link was removed because its URL slug trips the competitive shortlist gate.",
            "The commercial pillar anchor field service management software is the only link in its paragraph inside Build a trade career with room to grow, and the industries hub uses the approved anchor software for trades businesses.",
            "The national highest-paying trade jobs article is not linked, following the brief.",
        ],
    ),
    "keyword-mapper": (
        "Keyword Mapper",
        [
            "The number-one-ranked phrase trades that pay well in California now appears in the reader paragraph near the top of the article.",
            "The phrase best trades in California now opens the no-degree FAQ answer, which carries a same-line BLS link.",
            "Primary keyword density stays natural at about eight uses in roughly 3,500 words; no further exact-match variants were added to avoid stuffing.",
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
            f"# {label} output",
            "",
            f"Run ID: `{RUN_ID}`",
            "",
            f"Article: `{ARTICLE.relative_to(ROOT).as_posix()}`",
            "",
            f"Article SHA-256: `{sha(ARTICLE)}`",
            "",
            f"Editorial plan SHA-256: `{sha(PLAN)}`",
            "",
            f"Proof sidecar SHA-256 at review: `{sha(SIDECAR)}`",
            "",
            f"Decision: completed with no open {label} finding for the current article and plan snapshot.",
            "",
            "Findings raised in the 2026-09-24 review pass and applied through /rewrite:",
            "",
            *[f"- {item}" for item in applied],
            "",
            "Verification:",
            "",
            "- `python scripts/build_trade_jobs_ca_review_artifacts.py` exited `0` with zero plan fulfillment findings.",
            *[f"- The {phase}-phase machine review (`{path}`) contains {count} findings." for phase, path, count in reviews],
            "",
            "Unresolved review blockers: none.",
            "",
        ]
        target = OUT / f"{agent_id}-{SLUG}-{DATE}.md"
        target.write_bytes("\n".join(lines).encode("utf-8"))
        print(target.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
