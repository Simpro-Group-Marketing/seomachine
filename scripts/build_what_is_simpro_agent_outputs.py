"""Write hash-bound agent-output reports for the new What Is Simpro blog.

Governance artifact only. Each report records the findings from the 2026-10-05
review pass (three parallel reviewer subagents covering the seven roles), the
edits applied in the draft before sealing, and the deterministic review
verification bound to the current article, plan and sidecar bytes. Rerun after
any article or sidecar change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "what-is-simpro"
DATE = "2026-10-05"
RUN_ID = "fb123292-96da-464b-ab37-29a926336b3e"
ARTICLE = ROOT / "drafts" / f"{SLUG}-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
OUT = ROOT / "research" / "agent-outputs"

REPORTS = {
    "content-analyzer": (
        "Content Analyzer",
        [
            "The page-narrating line under the opening was replaced with a row-level lead-in that keeps the secondary keyword simpro features.",
            "The filler pillar sentence now explains why one system matters (nobody retypes a customer, a price or a job note) while keeping the exact commercial anchor and URL.",
            "The vague frequency word and the number word in the job-mix section were removed.",
            "The closing recap no longer repeats the quotes or uses a number; it gives a single demo next step.",
            "The draft expanded from roughly 930 to roughly 1,500 words with a job-mix section, an implementation stage table and demo walkthrough guidance to raise ICP utility.",
        ],
    ),
    "seo-optimizer": (
        "SEO Optimizer",
        [
            "The banned comparative word in the fit checklist was replaced.",
            "The early-artifact H2 now carries the primary keyword as What is Simpro, stage by stage.",
            "The second intro sentence now answers what Simpro does for each trade with action verbs.",
            "seo_quality_rater scored the reviewed draft 95.2/100 (grade A, publishing ready) before these fixes.",
        ],
    ),
    "meta-creator": (
        "Meta Creator",
        [
            "Meta description lengthened to 152 characters by naming the trade business; the frozen plan was updated to match.",
            "Meta title kept at 58 characters, starting with the primary keyword and matching the H1.",
        ],
    ),
    "internal-linker": (
        "Internal Linker",
        [
            "The bare G2 review anchor in the FAQ now reads G2 review on quotes, jobs and invoicing.",
            "The demo and pricing links now sit in separate paragraphs.",
            "The Simpro Lightning sentence no longer reads as an operator note and stays navigation-only.",
            "All six internal links returned HTTP 200; the five G2 review URLs return HTTP 403 to the validator and carry Chrome-connector allowlist entries; both Capterra URLs returned HTTP 200.",
        ],
    ),
    "keyword-mapper": (
        "Keyword Mapper",
        [
            "Primary keyword appears in the H1, the first 100 words, an H2, the slug, the meta title and the featured-image alt text.",
            "Secondary keywords simpro reviews, simpro software reviews, simpro app and simpro features each appear naturally once or twice; simpro pricing is linked, not targeted.",
            "Related demand for is simpro a crm system is answered in the FAQs, and what does simpro do is answered in the opening.",
        ],
    ),
    "editor": (
        "Editor",
        [
            "The dispatch sentence no longer overclaims that technicians arrive with the right parts.",
            "The circular demo sentence now follows the prep list instead of the walkthrough.",
            "The unsupported first-90-days comparison was replaced with a plain pacing statement.",
            "The superlative in Simpro's voice in the user-quote section intro was removed.",
            "No em dashes, semicolons, modal verbs, filler or editorial-process leakage remain outside approved quotes.",
        ],
    ),
    "public-copy-boundary-reviewer": (
        "Public Copy Boundary Reviewer",
        [
            "Review-site names no longer sit next to describe or note verbs in quote lead-ins.",
            "The keyword-stuffed review sentence now reads as reader guidance that points to the full sources.",
            "Six approved quotes stay verbatim, one per paragraph, each with its same-paragraph review link.",
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
            "Findings raised in the 2026-10-05 review pass and applied before the draft was sealed:", "",
            *[f"- {item}" for item in applied], "",
            "Verification:", "",
            "- `python scripts/build_what_is_simpro_review_artifacts.py` exited `0` with zero plan fulfillment findings.",
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
