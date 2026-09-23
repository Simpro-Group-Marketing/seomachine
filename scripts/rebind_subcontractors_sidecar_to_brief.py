"""Rebind the validation sidecar to the supplied brief.

Replaces the FAQ Proof Map, PAA provenance and internal link plan with the
brief's FAQ set and link set. The compliance Source Map rows are untouched
because those claims survived the restructure.
"""
from __future__ import annotations

import pathlib
import sys

SIDECAR = pathlib.Path(
    "research/validation-best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
BRIEF = "research/content-brief-best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
AGC = (
    "https://www.agc.org/sites/default/files/users/user21902/"
    "2026%20Workforce%20Survey%20Analysis%20%284%29.pdf"
)

FAQ_PROOF_MAP = f"""## FAQ Proof Map

- FAQ: Who is responsible for hiring subcontractors on a construction project? | URL: https://www.osha.gov/enforcement/directives/cpl-02-00-124 | Source class: neutral | Competitor check: passed | Support: Supports the responsibility boundary because the source establishes that more than one employer can be citable for the same jobsite hazard. | Status: approved
- FAQ: What should you ask a subcontractor before hiring them? | URL: https://www.irs.gov/forms-pubs/about-form-w-9 | Source class: neutral | Competitor check: passed | Support: Supports the legal entity name request because the source is the form that carries the name, entity type and taxpayer identification number. | Status: approved
- FAQ: How do general contractors keep track of multiple subcontractors? | URL: https://www.osha.gov/ords/imis/establishment.html | Source class: neutral | Competitor check: passed | Support: Supports tracking against verifiable records rather than memory by providing the public inspection history route. | Status: approved
- FAQ: How do you evaluate subcontractor performance? | URL: https://www.osha.gov/ords/imis/establishment.html | Source class: neutral | Competitor check: passed | Support: Supports verifying a safety claim at its source rather than accepting it during the job. | Status: approved
- FAQ: How can contractors build a reliable subcontractor network? | URL: {AGC} | Source class: non_competing_expert | Competitor check: passed | Support: Supports the reciprocal reliability point because the source names worker shortages, including subcontractors' workers, as the most listed cause of project delays. | Status: approved

"""

PAA_PROVENANCE = f"""## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: {BRIEF}
- Selected questions:
  - Who is responsible for hiring subcontractors on a construction project?
  - What should you ask a subcontractor before hiring them?
  - How do general contractors keep track of multiple subcontractors?
  - How do you evaluate subcontractor performance?
  - How can contractors build a reliable subcontractor network?
Status: approved

Precedence rationale: the supplied content brief carries a dedicated FAQ set, and
for a rewrite that pre-picked brief section takes precedence over SERP or
AnswerSocrates collection. The five questions above are reproduced from it
without alteration and match the article's visible FAQ headings exactly.

Superseded research inputs, retained for the record: the AnswerSocrates quota
blocker at
`research/answersocrates-blocker-best-practices-hiring-and-managing-subcontractors-2026-09-18.json`
and the live Google People Also Ask capture at
`research/paa-serp-observed-best-practices-hiring-and-managing-subcontractors-2026-09-18.md`.
Both were collected before the correct brief was supplied on 2026-09-19 and no
longer drive the FAQ set.

"""

INTERNAL_LINKS = """## Internal Link Plan

| Target | Anchor | Role | Status |
|---|---|---|---|
| https://www.clockshark.com/blog/construction-bid-template | prices subcontracted work with scope and exclusions spelled out | supporting | approved |
| https://www.clockshark.com/blog/construction-schedule-example | sequence trades so each sub knows what has to finish before they mobilize | supporting | approved |
| https://www.clockshark.com/blog/construction-kpis-protect-margin | track labor cost variance before the job closes instead of after | supporting | approved |
| https://www.clockshark.com/blog/construction-timesheet-template | captures hours by job and cost code | supporting | approved |
| https://www.clockshark.com/blog/best-time-tracking-apps-general-contractors | compare time tracking apps on the features field crews actually use | down_funnel | approved |

Source of the set: all five destinations are specified by the supplied content
brief. Each resolved HTTP 200 through `url_validator.py` on 2026-09-22 with zero
blockers.

Internal-link count decision: five editorial destinations, inside the 3 to 5
target and under the hard maximum of 7. The schedule destination appears twice,
once in practice 7 and once in the tracking FAQ, because both passages need the
same sequencing reference; that is one destination, not two.

Anchor constraint recorded during verification: the published H1 of
`best-time-tracking-apps-general-contractors` is "Best Time Tracking Apps for
Small Businesses, Contractors, and Field Teams", which does not match its
general-contractor slug. Anchor text therefore does not promise a
general-contractor-specific roundup. That page is a vendor-owned ranked list and
is used as an internal link only, never as neutral comparison evidence.

Superseded: the earlier link set (`industries/general-contractor`,
`tour/job-costing`, `blog/construction-labor-cost`,
`blog/ways-to-hire-and-pay-contractors`,
`blog/managing-safety-compliance-jobsite`) was chosen before the correct brief
arrived and has been replaced by the briefed set.

"""


def replace_section(text: str, heading: str, replacement: str) -> str:
    start = text.index(heading)
    nxt = text.find("\n## ", start + len(heading))
    end = len(text) if nxt == -1 else nxt + 1
    return text[:start] + replacement + text[end:]


def main() -> int:
    text = SIDECAR.read_text(encoding="utf-8")
    text = replace_section(text, "## FAQ Proof Map", FAQ_PROOF_MAP)
    text = replace_section(text, "## PAA/FAQ Provenance", PAA_PROVENANCE)
    text = replace_section(text, "## Internal Link Plan", INTERNAL_LINKS)
    SIDECAR.write_text(text, encoding="utf-8", newline="")
    print("sidecar FAQ map, PAA provenance and link plan rebound to the brief")
    return 0


if __name__ == "__main__":
    sys.exit(main())
