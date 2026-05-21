# Context Files — Coverage Report

**Generated**: 2026-05-12 | **Last updated**: 2026-05-21 (Voice Style Guide integrated; Product Marketing portal and sitemap rechecked; internal-links-map rebuilt from live sitemap)
**Source**: Simpro Marketing Portal (`sites.google.com/simpro.us/simpromarketingportal`) — Product Marketing, Creative Resources, Growth Marketing tabs
**Auth context**: `patrick.grueschow@simprogroup.com` (signed-in via Playwright MCP and gws CLI)
**Scope this pass**: Brand/product context files plus sitemap-backed internal-link discovery. SEO metric files remain deferred.

---

## Direct Answer to the Original Question

**Does the Simpro Marketing Portal contain all the data needed to fill the `context/` folder?**

**Partially.** The portal is a rich source for brand voice, product features/value props, competitive positioning, customer proof points, and source discovery. It is **not** a complete source for: (a) traffic/ranking-validated target keywords, (b) CRO playbooks (the portal has experiment/resource links but no standalone CRO rules doc), (c) AI citation targets, or (d) Reddit/community strategy. Those still require GSC, GA4, DataForSEO, Ahrefs/Semrush, live SERP work, or manual community research.

**Bottom line**: The portal and linked sources now cover the brand/product files plus a sitemap-backed internal-link map. Search-volume, ranking, AI-citation, Reddit/community, and tested-CRO guidance still need non-portal sources.

---

## In-Scope This Pass (6 files)

| File | Status | Primary Source(s) | What's Missing |
|---|---|---|---|
| `brand-voice.md` | ✅ **FILLED** (high confidence) | Simpro Voice Style Guide + FY26 Message House | Residual strategic questions only: multi-brand scope and canonical domain choice. |
| `features.md` | ✅ **FILLED** (high confidence) | FY26 Message House (Simpro tab), ICP slides, Battlecards, simprogroup.com/pricing (2026-05-12), sitemap customer-story verification (2026-05-21) | Pricing is quote-based (no published tiers) — confirmed from live pricing page. Add-on names and descriptions now populated. Datasheets folder may deepen feature details but is not blocking. |
| `competitor-analysis.md` | ✅ **COMPREHENSIVE** (40+ competitors — full battlecard extraction 2026-05-12) | All battlecard sheets from Drive folder 1alu7OAkdsuB7yBhZs6aco_zvGillqmpq: Direct (27 individual + 6 segment buckets), Indirect (Buildertrend, Contractor Foreman, Housecall Pro, Jobber, Nexvia, Procore), ERP/Upmarket (Autodesk, Oracle Primavera, Procore, MS Project, Planview, Oracle CRM, Dynamics 365, SedonaOffice, ServiceTrade, Foundation). **ServiceTitan resolved**: full April 2026 battlecard present in Direct sheet. | Keyword/ranking data still deferred to SEO-tactical track. Pricing detail for Simpro itself still a GAP. |
| `style-guide.md` | ✅ **FILLED** (canonical + FY26 overlay; table-level spot check complete 2026-05-21) | Simpro Voice Style Guide Google Doc (`1Hl78trTAMAnZcSBfsdM0Qn0Xa1f-DW51s-8LbeU_Knk`, Aug 2024) + FY26 Message House | Residual open questions: Simpro Group mention frequency, AI feature title-case after first mention, vertical name capitalization. |
| `cro-best-practices.md` | 🟡 **PARTIAL** (Simpro overlay added) | Generic CRO best practices (was already in repo) + Simpro-specific overlay derived from Message House and battlecards | No dedicated Simpro CRO playbook exists in the portal. Growth Marketing's `2025 Completed Experiments` deck (1f4E7yay4s-SsVUFcg-EZ06aB31d2MADJ3oNfQrEGnXo) is the closest existing resource — review for tested patterns. |
| `writing-examples.md` | ✅ **FILLED** (4 full articles, 2026-05-12) | simprogroup.com/blog — Exit Ready (Apr 2026), Stop Chasing Invoices / Agentic AI (Apr 2026), 12 Best FSM Software (Sep 2025), What Is FSM (Apr 2025) | All customer quotes, named outcomes, and statistics preserved verbatim. `/write` and `/rewrite` commands now have real voice examples. |

---

## Deferred This Pass (5 SEO-tactical files)

These were intentionally out of scope per the approved plan. They need different source data — not portal content.

| File | Recommended Source for Next Pass |
|---|---|
| `seo-guidelines.md` | Generic framework rules; can stay as-is. Update if Simpro has a published SEO style standard. |
| `target-keywords.md` | ✅ Rebuilt 2026-05-21 as a Simpro sitemap-derived topic-cluster map. Search volume, difficulty, rankings, and priority still need DataForSEO/GSC/GA4/Ahrefs/Semrush validation. |
| `internal-links-map.md` | ✅ Rebuilt 2026-05-21 from `https://www.simprogroup.com/sitemap.xml` via Playwright MCP. Needs GSC/GA4 later to rank pages by traffic/conversion, but placeholders are removed. |
| `ai-citation-targets.md` | Use the existing `/research-ai-citations` command in this repo. Pair with Simpro Group's known directory presence (G2, Capterra, TrustRadius). |
| `reddit-strategy.md` | Manual subreddit identification — likely r/HVAC, r/electricians, r/Plumbing, r/lowvoltage, r/sysadmin (for security/A/V), r/Construction, r/SmallBusiness. |

---

## Sources Successfully Used

| Source | Type | Used For |
|---|---|---|
| `FY26 Brand Message House — Simpro Group` (Sheet `1VVfWFFohv5IyroehwuRrJGLyvyyXv0Z5JjiU_elIrbs`) | Google Sheet, 15 tabs | brand-voice, features, style-guide |
| `Simpro Battlecards (Direct Competitors)` (Sheet `1bZgf9r8kZcttZKnO4XAkH9nccU7QAMcsmt_0EygL3pY`) | Google Sheet, ~25 tabs | competitor-analysis (BuildOps, Housecall Pro, ServiceTrade pulled) |
| `Ideal Customer Profile — Simpro Group` (Slides `1HLAPBGpSYziuhDDhQWjwSUIbd_G027A2bYcn7temH_s`) | Google Slides, 37 slides | brand-voice (audience), features (use cases by segment) |
| `Simpro Marketing Portal` (home + Product Marketing + Creative Resources + Growth Marketing) | Google Sites | Discovery — mapped the source tree |
| `www.simprogroup.com` XML sitemap (`https://www.simprogroup.com/sitemap.xml`) | Public sitemap, 855 URLs, accessed via Playwright MCP 2026-05-21 | internal-links-map; target-keywords topic clusters (URLs and themes only, not metrics) |

## Sources Identified But Not Pulled This Pass

| Source | Reason | Priority |
|---|---|---|
| `Simpro Voice Style Guide` (Doc `1Hl78trTAMAnZcSBfsdM0Qn0Xa1f-DW51s-8LbeU_Knk`) | ✅ **PULLED** 2026-05-21 — integrated into `style-guide.md` and `brand-voice.md` | Done |
| `Simpro Software Sales Battlecards (ERP/Upmarket)` (Sheet `1XyzYwOUjMMdLwTx0VRKJnywYbGIZNVTb-3f0ngL1VZk`) | ✅ **PULLED** in second pass — SedonaOffice, Dynamics 365, Procore, Foundation added. Autodesk Construction Cloud, Oracle Primavera, Oracle CRM, MS Project, Planview judged low-fit and skipped. **ServiceTitan is NOT in this sheet** — strategic finding documented in competitor-analysis.md. | Done |
| `Simpro Software Sales Battlecards (Indirect Competitors)` (`1ie9-N4RQIyPNWNYJTbVmM0jBsUWoGuWgSCXlFOKyP58`) | ✅ **PULLED** in second pass — Jobber, Buildertrend added. Contractor Foreman, Nexvia judged low-fit and skipped. | Done |
| `Simpro Software Sales Battlecards (Upmarket)` (`1ud7OfBNvnnjwP5Uibhm6m9t67ORd_mLb64Exk-3lf38`) | Subset of ERP/Upmarket — same competitors, no new content | Skipped (redundant) |
| Datasheets folder (`1-85gG7kDBfswS2blOc9DVZjmAuavWdAr`) — Verticals, Payments, Add-ons, AI, Multi-Company, Data Security, Implementation, Prof. Services | Time + multiple PDF/Slides files | Medium — fills pricing and add-on detail in features.md |
| `Internal-Only Simpro Cheat Sheet` (Drive file `10aj3LlY9Aps2lBFIf5SwnNzj_7r29Jra`) | Time | Medium — quick messaging crib |
| `Customer Archetypes` folder (`11A3W390YlG__XaneRJgsU3O9VecWqg7T`) | Time | Medium — could deepen audience profile in brand-voice |
| `Best-Fit Targeting Framework` folder (`1YdCo-xWNqRsQHTdQQhCmbiUX3_dzdq70`) | Time | Medium — could deepen competitor analysis |
| `Message Maps for Add-ons` (Slides `1Yo6Jk_NjuZa5k1Ea4KeougJaFffqaypVwVm4ZthC8Qw`) | Time | Low — add-on level detail for features.md |
| Customer Stories deck (`1UzYrlZAh0iqoPjnC34DNS789xhpWXUzFgW-h4y4eTqk`), Quote Matrix (`1nCeAyY7FHEXHmAmthJFXGvAViG8hPck_fuQVQaTiNAk`), References (`1tWlR0WNDRRnvA5b-2fdBdjC7rwaQQs1CYCc48pD62HE`) | Time | Medium — could expand named-customer proof beyond the ~13 already captured |
| `2025 Completed Experiments` (Slides `1f4E7yay4s-SsVUFcg-EZ06aB31d2MADJ3oNfQrEGnXo`) | Time | Medium — would add tested patterns to cro-best-practices.md |
| `SEO Monthly Reports` (Drive `1UEfci23FQ59zJrJPLDSfX9IcT7HwNPd3`) | Time + multiple files | High for SEO-tactical pass (deferred); identifies top-performing URLs for writing-examples.md |

---

## Verification (per the approved plan)

1. **Primary context files have no generic company/template placeholders unless explicitly marked as needing a separate data source**: ✅
   - brand-voice.md: Voice Style Guide and FY26 Message House integrated.
   - features.md: All bracketed placeholders replaced; quote-based pricing boundary preserved; BGE Digital case-study spelling verified from live page title.
   - competitor-analysis.md: All bracketed placeholders replaced; ~6 GAP comments for unpulled battlecards, SEO data, etc.
   - style-guide.md: Rewritten from canonical Voice Style Guide plus FY26 overlay; residual open questions are explicit.
   - cro-best-practices.md: Simpro overlay prepended to existing template; 1 GAP comment.
   - writing-examples.md: Populated with real Simpro examples.
   - internal-links-map.md: Rebuilt from sitemap.
   - target-keywords.md: Rebuilt as sitemap-derived Simpro clusters with unverified metric fields.

2. **This report matches the actual state of the 6 files**: ✅ (the table above).

3. **Smoke test**: `/research field service software` generated `research/brief-field-service-software-2026-05-21.md` and the brief surfaced Simpro voice markers: AI-first operating platform language, trade/field-service leader audience framing, 24/6 support, no "tradies" in US copy, no "all-in-one," and named proof points.

4. **SEO-tactical boundary**: `internal-links-map.md` is now sitemap-backed and `target-keywords.md` is now sitemap-derived. Both still need GSC/GA4 and SEO-platform validation for priority. `ai-citation-targets.md` and `reddit-strategy.md` still need separate non-portal research. `seo-guidelines.md` can stay generic unless a Simpro SEO standard is found.

---

## Open Strategic Questions (surfaced during extraction)

1. **Multi-brand scope**: The `seomachine-main` workspace is configured for a single brand (Simpro) per CLAUDE.md. But Simpro Group operates four brands (Simpro, BigChange, AroFlo, ClockShark) with distinct ICPs, voices, and positioning. The Message House has dedicated tabs for each. **Should this workspace be cloned per brand**, or stay Simpro-focused? Recommended follow-up plan if multi-brand is needed.

2. **FY25 vs. FY26 positioning**: The Message House has both an older (`25 - Simpro` — Work. Smarter., Empower/Elevate/Excel pillars) and newer (`Simpro` — AI-first, Profitability/AI/Control/Champion pillars) tab. I led with FY26 in the context files and footnoted FY25. Confirm this is correct before bulk-republishing older blog content.

3. **AI domain**: Boilerplates reference both `simprogroup.com` (older 200-word) and `simpro.ai` (newer 25/50/100-word). Confirm canonical URL for body-copy mentions and CTAs.

4. **ServiceTitan**: ✅ **RESOLVED** — ServiceTitan now has a full battlecard in the Direct Competitors sheet (Last Updated: April 2026). Simpro does compete with and name ServiceTitan. The battlecard is in `competitor-analysis.md → ## ServiceTitan`. Recommend building /vs/servicetitan and alternatives-to-servicetitan SEO content.

---

## Recommended Next Actions (in priority order)

1. ✅ ~~**Pull the ERP/Upmarket battlecard sheet**~~ — Done 2026-05-12. 40+ competitors now in competitor-analysis.md including ServiceTitan (April 2026 battlecard).
2. ✅ ~~**Pull 3–5 top-performing blog posts**~~ — Done 2026-05-12. 4 articles fetched via Playwright from simprogroup.com/blog; writing-examples.md being populated.
3. ✅ ~~**Pull pricing detail**~~ — Done 2026-05-12. Confirmed quote-based model, base plan inclusions, and add-on list from simprogroup.com/pricing.
4. ✅ ~~**Request access** to the Simpro Voice Style Guide doc~~ — Done 2026-05-21.
5. **Smoke test**: Run `/research field service software` and verify Simpro voice/proof points come through. Voice-guide parity spot check completed 2026-05-21; product-name rows, off-site/off site, 2x, and video-script sub-rules are now captured in `style-guide.md`.
6. **Run the remaining SEO-tactical validation** in a separate pass using GSC + GA4 + DataForSEO + Ahrefs/Semrush plus manual community research. Add metrics and priority to `target-keywords.md`, add traffic/conversion priority to `internal-links-map.md`, and fill `ai-citation-targets.md` plus `reddit-strategy.md`.
7. **Quarterly refresh**: Re-pull Message House tabs and battlecards every quarter (or when FY messaging refresh lands). Next due: 2026-08-12.

---

**Reviewer**: SEO / content-ops
**Last updated**: 2026-05-12
**Next review**: After Voice Style Guide access is granted, or by 2026-08-12 (quarterly)
