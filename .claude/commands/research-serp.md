# Research SERP Command

Deep SERP analysis for a specific keyword to understand what Google wants from verified visible results. Treat observed patterns as strong editorial defaults, with documented Reader Contract exceptions when reader intent, evidence, format, or business needs justify a different choice.

## Usage
`/research-serp "keyword phrase" [--word-target 1600]`

## What This Command Does

Analyzes an intent-representative verified result set until dominant patterns and meaningful exceptions are clear:
- Content type patterns (listicle, how-to, guide, etc.)
- Average, median, range, and individual competitor word counts as context only
- SERP features present (featured snippet, PAA, video, etc.)
- AEO/GEO variable candidates for blog writing
- Supplemental visible PAA observations that may refine the AnswerSocrates query or editorial plan but never become provenance
- Observed freshness signals
- Competitive difficulty
- Search intent
- Common content structure

Generates an evidence-bound content brief with explicit observations, strong default recommendations, exception requirements, and proof boundaries.

## Process

Execute SERP analysis for a keyword:
```bash
python scripts/research_serp_analysis.py "your target keyword"
python scripts/research_serp_analysis.py "your target keyword" --word-target 1600
```

Omit `--word-target` when Reader Contract planning has not resolved an intent- and evidence-complete target. The report will mark the target unresolved rather than inventing one from competitor counts.

Within the AEO variable-resolution workflow, "competitive length from `/research-serp`" means the observed competitor distribution is planning context. It does not authorize a derived target, minimum, or expansion recommendation. The Reader Contract remains the source of the caller-supplied target.

This will:
1. Fetch the available organic result candidates from DataForSEO
2. Analyze enough relevant results to establish stable intent, structure, and evidence-gap patterns; document why the sample is sufficient
3. Detect content types from titles
4. Fetch word counts for each result
5. Identify SERP features
6. Analyze search intent
7. Assess competitive difficulty
8. Generate content brief
9. Create report: `research/serp-analysis-[keyword].md`
10. When organic results were actually collected, create the immutable `simpro-serp-evidence/v1` artifact at `research/serp-evidence-[keyword-slug]-[YYYY-MM-DD].json`

The strict evidence JSON contains the exact query and RFC 3339 UTC collection time, collector name/version and run ID, non-empty observed result positions/URLs/titles/types, concrete content-type and SERP-feature observations, must-have sections, competitor gaps, and a canonical evidence hash. A blocked or empty run must not mint verified evidence. Metadata-only `status: verified` files and editorial decisions that are not traceable to the bound observations fail readiness.

The tool-emitted `simpro-serp-evidence/v1` artifact carries an `execution_attestation`, a keyed local execution-integrity attestation. The nested `simpro-answersocrates-run-receipt/v1` in a tool-emitted PAA artifact uses the same control. A handwritten or merely rehashed replacement does not qualify. This local control does not provide a remote/provider signature and does not prove that external observations are true; the workflow still validates query, collection date, source metadata, visible result observations, and eligible PAA questions. For a rewrite, the dedicated pre-picked PAA brief section remains the path/hash-bound precedence exception.

## Required Fallback Order

Use this evidence order every time:

1. DataForSEO
2. Playwright SERP fallback
3. documented blocker plus verified non-SERP evidence only

DataForSEO remains the preferred source because it provides structured SERP data. If `DATAFORSEO_LOGIN` or `DATAFORSEO_PASSWORD` is missing, unavailable, or the DataForSEO request fails, run the Playwright SERP fallback instead of stopping immediately.

The Playwright fallback must use this controlled Google URL pattern:
`https://www.google.com/search?q=[keyword]&num=10&hl=en&gl=us&pws=0`

Before running Playwright, verify `npx` is available. If it is not available, stop with this blocker:
`npx unavailable; install Node/npm or provide a SERP export. PAA provenance still requires AnswerSocrates or the rewrite-only brief exception.`

The Playwright fallback may collect only browser-visible facts:
- Top visible organic result titles, URLs, snippets, and observed positions
- Visible SERP feature labels such as AI Overview, featured snippet, PAA, videos, images, ads, discussions/forums, and shopping modules
- PAA questions only when exact question text is present in the browser snapshot
- Blocker status when Google shows CAPTCHA, consent wall, login wall, no results, or unstable markup

Save raw fallback provenance to:
`research/serp-playwright-[keyword-slug]-[YYYY-MM-DD].json`

Raw fallback provenance is an input, not the final `simpro-serp-evidence/v1` artifact. Only a run with collected organic results may emit the final strict evidence JSON.

The human report must still be saved to:
`research/serp-analysis-[keyword-slug].md`

When fallback is used, the report must include a `Playwright SERP Fallback` section with:
- DataForSEO failure reason
- Search URL used
- Timestamp
- Locale assumptions: US, English, personalization disabled via `pws=0`
- Raw artifact path
- Limitations: browser-visible only, no search volume, no DataForSEO rank metrics, no invented competitor metrics

If Playwright fallback is blocked, the report must state that DataForSEO failed, Playwright SERP fallback failed, no SERP competitor metrics were used, and the next acceptable SERP evidence is a user-provided SERP export, verified Asana brief, GSC, live page evidence, and public sources. A user PAA CSV remains invalid unless a saved AnswerSocrates artifact records a genuine blocked state.

## Output

The report includes:

### Content Context
- Observed competitor word-count average, median, range, and individual counts
- Caller-supplied word target and observed difference when `--word-target` is present; otherwise target status is unresolved
- Match the dominant observed content type by default; document a Reader Contract exception when a different format better serves reader intent, evidence, or business needs
- Content type distribution

### SERP Features
- Featured snippet opportunity
- People Also Ask questions
- Evaluate every identified SERP feature and target every applicable feature supported by search intent, article format, reader value, and verified inputs
- Observed video/image modules to evaluate and target when applicable
- Other SERP features present

### AEO/GEO Inputs
- Candidate `main_question` for direct-answer-first drafting
- Supplemental PAA observations with intent labels; these cannot replace AnswerSocrates or dedicated rewrite-brief provenance
- Capsule Method opportunities by H2/definition/comparison section
- Source mapping needs for credible external claims

PAA provenance remains a separate gate. Every new article requires a structured AnswerSocrates artifact, even when `FAQ policy: required | not_applicable` resolves to `not_applicable` with a non-empty rationale. For a rewrite, PAA in a dedicated brief section takes precedence: bind the brief path/hash, do not rerun AnswerSocrates, and use those exact questions as visible FAQ headings. A rewrite without that section requires AnswerSocrates. A user CSV is permitted only with an AnswerSocrates artifact documenting a genuine blocked state caused by login, CAPTCHA, quota, or unavailability. SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance.

### Content Brief
- Article context (caller-supplied word target or unresolved status, observed type, tone)
- Must-have elements supported by verified observations, reader importance, and available evidence
- Recommended structure based on verified ranking patterns, with any Reader Contract exception documented
- SERP features to target when applicable
- Observed freshness signals

### Competitive Analysis
- Domain authority mix
- Difficulty assessment
- Authority context without ranking or timeframe predictions

### Action Plan
Step-by-step process from research to publishing

## Example Use Cases

**Before creating new content**:
```
/research-serp "best project management tools"
```
Understand: Is this a listicle? What reader questions and evidence patterns recur? What features should the brief evaluate?

**Before updating existing content**:
```
/research-serp "how to choose the right software"
```
Check whether visible SERP patterns have changed, then evaluate them against the Reader Contract, evidence, and intended reader task.

## Integration

After running `/research-serp`:
- Use the content brief to guide writing
- Use visible PAA observations only to refine the AnswerSocrates query or editorial intent. Never write SERP questions into the AnswerSocrates artifact or treat them as eligible provenance.
- Use `/write [keyword]` with insights from SERP analysis
- Match the dominant observed content type by default; evaluate recurring observed structure, include each applicable structure, target every applicable SERP feature, and document any Reader Contract exception
- Use competitor length only as observed context; resolve scope from the Reader Contract, reader payoff, task coverage, and available evidence

## Time & Cost

**Time:** 1-2 minutes per keyword
**API Cost:** ~$0.02 per keyword (DataForSEO)
**Cost:** Free for word count (if pages accessible)

## When to Run

- **Before creating any new content**: Record visible search context before Reader Contract planning
- **Before major content updates**: Check current SERP observations and treat applicable verified patterns as strong defaults, with each deviation documented in the Reader Contract
- **When evaluating format**: Compare observed title patterns with the reader's intended task
- **For competitive research**: Understand difficulty before committing
