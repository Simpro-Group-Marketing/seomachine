# Content Analyzer output

Run ID: `0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5`

Article: `rewrites/best-trade-jobs-california-rewrite-2026-09-24.md`

Article SHA-256: `5e00913900bb1718dd4c13be6bc49cb653a2de5602518b1f4f832cc166b8f422`

Editorial plan SHA-256: `71b09b2b66f843de7e39ab0629a3bcf0a63a759623a7834d5cda404fb7c8b109`

Proof sidecar SHA-256 at review: `38d897c10a04aee98c2f7c977a8e6479da73294dc48adb7d865bdabd99730ca5`

Decision: completed with no open Content Analyzer finding for the current article and plan snapshot.

Findings raised in the 2026-09-24 review pass and applied through /rewrite:

- Operating engineer profile no longer claims crane work, because SOC 47-2073 excludes crane operators; earning levers now cite prevailing-wage and GPS grade-control work, and the seasonal note reflects California weather.
- Training-length FAQ now states 18 months to four years or longer and adds the Cal/OSHA three-year conveyance requirement instead of claiming every program fits the span.
- Transportation equipment profile now lists trains, ships and rail transit cars, matching SOC 49-2093.
- Unsourced comparative claims in the avionics, aircraft mechanic and specialization lines were replaced with non-comparative wording.
- Pay factors now include the California daily overtime rule with a same-line DIR link, and the choice checklist adds job outlook and California's registered apprenticeship search.
- Electrician line separates certification from trainee registration so apprentices are not told they need certification before starting.

Verification:

- `python scripts/build_trade_jobs_ca_review_artifacts.py` exited `0` with zero plan fulfillment findings.
- The plan-phase machine review (`research/machine-review-plan-best-trade-jobs-california-2026-09-24.json`) contains 0 findings.
- The article-phase machine review (`research/machine-review-article-best-trade-jobs-california-2026-09-24.json`) contains 0 findings.

Unresolved review blockers: none.
