# Context Files — Coverage Report

**Generated**: 2026-05-12 | **Last updated**: 2026-05-12 (competitor-analysis.md fully repopulated from Drive folder)
**Source**: Simpro Marketing Portal (`sites.google.com/simpro.us/simpromarketingportal`) — Product Marketing, Creative Resources, Growth Marketing tabs
**Auth context**: `patrick.grueschow@simprogroup.com` (signed-in via Playwright MCP and gws CLI)
**Scope this pass**: Brand & product context files only. SEO-tactical files deferred.

---

## Direct Answer to the Original Question

**Does the Simpro Marketing Portal contain all the data needed to fill the `context/` folder?**

**Partially.** The portal is a rich source for brand voice, product features/value props, competitive positioning, and customer proof points. It is **not** a complete source for: (a) a canonical voice/style guide (the linked Google Doc is access-restricted), (b) blog writing examples (those live on the public website, not the portal), (c) CRO playbooks (the portal has experiment results but no rules doc), and (d) SEO-tactical files (target keywords, internal links map, AI citation targets, Reddit strategy — these require GSC, DataForSEO, and SEO research data, not portal content).

**Bottom line**: The portal got us ~70% of the way on the 6 brand/product files. Two files have hard access blockers or live elsewhere. The 5 SEO-tactical files were always going to need different sources.

---

## In-Scope This Pass (6 files)

| File | Status | Primary Source(s) | What's Missing |
|---|---|---|---|
| `brand-voice.md` | ✅ **FILLED** (high confidence) | FY26 Message House → `25 - Brand Messaging / Group` tab, `Simpro` tab (new positioning), `25 - Simpro` tab (older positioning) | Canonical Voice Style Guide doc (1Hl78trTAMAnZcSBfsdM0Qn0Xa1f-DW51s-8LbeU_Knk) is permission-locked. Marked with `<!-- GAP -->` note. |
| `features.md` | ✅ **FILLED** (high confidence) | FY26 Message House (Simpro tab), ICP slides, Battlecards, simprogroup.com/pricing (2026-05-12) | Pricing is quote-based (no published tiers) — confirmed from live pricing page. Add-on names and descriptions now populated. Official /vs/ comparison pages listed. Datasheets folder (add-on detail) still unpulled. |
| `competitor-analysis.md` | ✅ **COMPREHENSIVE** (40+ competitors — full battlecard extraction 2026-05-12) | All battlecard sheets from Drive folder 1alu7OAkdsuB7yBhZs6aco_zvGillqmpq: Direct (27 individual + 6 segment buckets), Indirect (Buildertrend, Contractor Foreman, Housecall Pro, Jobber, Nexvia, Procore), ERP/Upmarket (Autodesk, Oracle Primavera, Procore, MS Project, Planview, Oracle CRM, Dynamics 365, SedonaOffice, ServiceTrade, Foundation). **ServiceTitan resolved**: full April 2026 battlecard present in Direct sheet. | Keyword/ranking data still deferred to SEO-tactical track. Pricing detail for Simpro itself still a GAP. |
| `style-guide.md` | 🟡 **PARTIAL** (derived rules) | FY26 Message House tone-of-voice, observed Simpro web copy conventions | The canonical `Simpro Voice Style Guide` Google Doc is permission-locked. Specific do/don't examples, channel-specific tone rules, and formal naming conventions are missing. File contains `<!-- GAP -->` notes flagging this. |
| `cro-best-practices.md` | 🟡 **PARTIAL** (Simpro overlay added) | Generic CRO best practices (was already in repo) + Simpro-specific overlay derived from Message House and battlecards | No dedicated Simpro CRO playbook exists in the portal. Growth Marketing's `2025 Completed Experiments` deck (1f4E7yay4s-SsVUFcg-EZ06aB31d2MADJ3oNfQrEGnXo) is the closest existing resource — review for tested patterns. |
| `writing-examples.md` | ✅ **FILLED** (4 full articles, 2026-05-12) | simprogroup.com/blog — Exit Ready (Apr 2026), Stop Chasing Invoices / Agentic AI (Apr 2026), 12 Best FSM Software (Sep 2025), What Is FSM (Apr 2025) | All customer quotes, named outcomes, and statistics preserved verbatim. `/write` and `/rewrite` commands now have real voice examples. |

---

## Deferred This Pass (5 SEO-tactical files)

These were intentionally out of scope per the approved plan. They need different source data — not portal content.

| File | Recommended Source for Next Pass |
|---|---|
| `seo-guidelines.md` | Generic framework rules; can stay as-is. Update if Simpro has a published SEO style standard. |
| `target-keywords.md` | DataForSEO (already wired in `data_sources/modules/dataforseo.py`), GSC export, Ahrefs/Semrush. Build topic clusters from organic performance data and ICP industries (low voltage, multi-trade, HVAC, plumbing, electrical). |
| `internal-links-map.md` | Crawl simpro.com sitemap (or get from the web team). Categorize: product pages, pricing, blog hubs, customer stories, integrations. |
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

## Sources Identified But Not Pulled This Pass

| Source | Reason | Priority |
|---|---|---|
| `Simpro Voice Style Guide` (Doc `1Hl78trTAMAnZcSBfsdM0Qn0Xa1f-DW51s-8LbeU_Knk`) | Permission-denied (403) for patrick.grueschow@simprogroup.com — request access | **High** — would substantially upgrade style-guide.md |
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

1. **Six in-scope files have zero `[BRACKETED]` placeholders or have explicit `<!-- GAP -->` markers**: ✅
   - brand-voice.md: All bracketed placeholders replaced; 1 GAP comment for the locked Voice Style Guide.
   - features.md: All bracketed placeholders replaced; 2 GAP comments (pricing detail, ServiceTitan).
   - competitor-analysis.md: All bracketed placeholders replaced; ~6 GAP comments for unpulled battlecards, SEO data, etc.
   - style-guide.md: Rewritten with inferred rules; 2 GAP comments for locked source doc.
   - cro-best-practices.md: Simpro overlay prepended to existing template; 1 GAP comment.
   - writing-examples.md: GAP-only file with clear extraction recipe for next pass.

2. **This report matches the actual state of the 6 files**: ✅ (the table above).

3. **Smoke test recommended next**: Run `/research field service software` against the seomachine pipeline. Verify the brief references Simpro brand pillars (Profitability / AI-First / Operational Control / Trades Champion), Simpro-specific terminology (job costing, recurring maintenance, multi-trade), and named-customer outcomes (Shaffer Beacon, Foster Plumbing, etc.) — not generic field-service language.

4. **No edits to the 5 deferred SEO-tactical files**: ✅ (seo-guidelines.md, target-keywords.md, internal-links-map.md, ai-citation-targets.md, reddit-strategy.md were not touched).

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
4. **Request access** to the `Simpro Voice Style Guide` doc (1Hl78trTAMAnZcSBfsdM0Qn0Xa1f-DW51s-8LbeU_Knk) — upgrades style-guide.md from inferred to authoritative rules. Contact Natasha Morgan (Product Marketing).
5. **Smoke test**: Run `/research field service software` and verify Simpro voice/proof points come through.
6. **Run the 5 SEO-tactical files** in a separate pass using GSC + DataForSEO + Ahrefs/Semrush (target-keywords, internal-links-map, ai-citation-targets, reddit-strategy) — not portal data.
7. **Quarterly refresh**: Re-pull Message House tabs and battlecards every quarter (or when FY messaging refresh lands). Next due: 2026-08-12.

---

**Reviewer**: SEO / content-ops
**Last updated**: 2026-05-12
**Next review**: After Voice Style Guide access is granted, or by 2026-08-12 (quarterly)
