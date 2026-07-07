# Research SERP Command

Deep SERP analysis for a specific keyword to understand what Google wants.

## Usage
`/research-serp "keyword phrase"`

## What This Command Does

Analyzes the top 10 ranking results for a keyword to provide detailed content requirements:
- Content type patterns (listicle, how-to, guide, etc.)
- Average word count and recommended length
- SERP features present (featured snippet, PAA, video, etc.)
- AEO/GEO variable candidates for blog writing
- PAA/FAQ questions that should feed the AnswerSocrates artifact or article plan
- Freshness requirements
- Competitive difficulty
- Search intent
- Common content structure

Generates comprehensive content brief for creating or updating content.

## Process

Execute SERP analysis for a keyword:
```bash
python scripts/research_serp_analysis.py "your target keyword"
```

This will:
1. Fetch top 20 organic results from DataForSEO
2. Analyze content patterns in top 10
3. Detect content types from titles
4. Fetch word counts for each result
5. Identify SERP features
6. Analyze search intent
7. Assess competitive difficulty
8. Generate content brief
9. Create report: `research/serp-analysis-[keyword].md`

## Required Fallback Order

Use this evidence order every time:

1. DataForSEO
2. Playwright SERP fallback
3. documented blocker plus verified non-SERP evidence only

DataForSEO remains the preferred source because it provides structured SERP data. If `DATAFORSEO_LOGIN` or `DATAFORSEO_PASSWORD` is missing, unavailable, or the DataForSEO request fails, run the Playwright SERP fallback instead of stopping immediately.

The Playwright fallback must use this controlled Google URL pattern:
`https://www.google.com/search?q=[keyword]&num=10&hl=en&gl=us&pws=0`

Before running Playwright, verify `npx` is available. If it is not available, stop with this blocker:
`npx unavailable; install Node/npm or provide a SERP/PAA export.`

The Playwright fallback may collect only browser-visible facts:
- Top visible organic result titles, URLs, snippets, and observed positions
- Visible SERP feature labels such as AI Overview, featured snippet, PAA, videos, images, ads, discussions/forums, and shopping modules
- PAA questions only when exact question text is present in the browser snapshot
- Blocker status when Google shows CAPTCHA, consent wall, login wall, no results, or unstable markup

Save raw fallback provenance to:
`research/serp-playwright-[keyword-slug]-[YYYY-MM-DD].json`

The human report must still be saved to:
`research/serp-analysis-[keyword-slug].md`

When fallback is used, the report must include a `Playwright SERP Fallback` section with:
- DataForSEO failure reason
- Search URL used
- Timestamp
- Locale assumptions: US, English, personalization disabled via `pws=0`
- Raw artifact path
- Limitations: browser-visible only, no search volume, no DataForSEO rank metrics, no invented competitor metrics

If Playwright fallback is blocked, the report must state that DataForSEO failed, Playwright SERP fallback failed, no SERP competitor metrics were used, and the next acceptable evidence is user-provided SERP/PAA export, verified Asana brief, GSC, live page evidence, and public sources.

## Output

The report includes:

### Content Requirements
- Recommended word count (based on top 10 average + 10%)
- Dominant content type (what format works)
- Content type distribution

### SERP Features
- Featured snippet opportunity
- People Also Ask questions
- Video/image requirements
- Other SERP features present

### AEO/GEO Inputs
- Candidate `main_question` for direct-answer-first drafting
- 3-5 closest PAA questions with intent labels
- Capsule Method opportunities by H2/definition/comparison section
- Source mapping needs for credible external claims

### Content Brief
- Target specifications (word count, type, tone)
- Must-have elements
- Recommended structure
- SERP features to target
- Freshness requirements

### Competitive Analysis
- Domain authority mix
- Difficulty assessment
- Timeframe expectations

### Action Plan
Step-by-step process from research to publishing

## Example Use Cases

**Before creating new content**:
```
/research-serp "best project management tools"
```
Understand: Is this a listicle? How long should it be? What features to include?

**Before updating existing content**:
```
/research-serp "how to choose the right software"
```
Check if SERP patterns have changed, update to match current expectations

## Integration

After running `/research-serp`:
- Use the content brief to guide writing
- Feed the PAA questions and `main_question` into `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md` or the `/article` AEO/GEO Map
- Use `/write [keyword]` with insights from SERP analysis
- Ensure content matches recommended structure and length

## Time & Cost

**Time:** 1-2 minutes per keyword
**API Cost:** ~$0.02 per keyword (DataForSEO)
**Cost:** Free for word count (if pages accessible)

## When to Run

- **Before creating any new content**: Know requirements upfront
- **Before major content updates**: Check current SERP expectations
- **When stuck on format**: See what type of content ranks
- **For competitive research**: Understand difficulty before committing
