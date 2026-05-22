# AEO/GEO Blog Strategy

This file is the canonical blog-writing strategy for AEO and GEO. In this repo, GEO means Generative Engine Optimization: structuring content so generative answer systems can understand, extract, cite, and recommend it.

Use this file for blog workflows only. It supports `/research`, `/research-serp`, `/article`, and `/write`; it does not replace marketing skills.

## Required Variable Resolution

Before drafting, resolve these variables from the user prompt, research brief, and repo context files:

| Variable | First source | Fallback |
|---|---|---|
| `topic` | User prompt or topic file | Ask the user |
| `audience` | `context/brand-voice.md` audience and fit guidance | Ask only if multiple audiences fit |
| `main_question` | SERP/PAA intent, title, or brief | Ask if no clear primary question exists |
| `related_questions` | AnswerSocrates PAA artifact, SERP, Reddit, YouTube | Ask for PAA/FAQ CSV if AnswerSocrates is blocked |
| `tone` | `context/brand-voice.md` and `context/style-guide.md` | Ask only if user requests a non-standard tone |
| `expertise` | `context/features.md`, customer proof, expert quotes | Ask if a named author/reviewer is required and missing |
| `length` | SERP/content brief | Default to competitive length from `/research-serp` |

Do not synthesize facts, search volume, PAA questions, customer claims, or expert quotes. If the repo and live research do not provide an input, ask for it or mark it as missing.

## AnswerSocrates PAA Workflow

For every new `/article` run, collect People Also Ask style questions from `https://answersocrates.com` with Playwright MCP.

Required browser flow:

1. Open AnswerSocrates with `browser_navigate`.
2. Use `browser_snapshot` to identify the query input and submit action.
3. Enter the inferred `main_question`; if no main question exists, enter `topic`.
4. Submit with snapshot-derived targets only. Do not hard-code selectors.
5. Wait for results and extract visible questions with `browser_evaluate`.
6. Save the result to `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`.

If AnswerSocrates is blocked, unavailable, or requires login/CAPTCHA, record the blocker in the artifact and ask the user for a PAA/FAQ CSV export. Do not invent replacement questions.

## PAA Artifact Format

```markdown
# PAA Questions: [Topic]

**Date:** [YYYY-MM-DD]
**Source:** AnswerSocrates via Playwright MCP
**Query Used:** [main_question or topic]
**Status:** [collected / blocked / user-export-needed]

## Raw Questions
- [question]

## Closest Related Questions
1. [question]
2. [question]
3. [question]

## Intent Breakdown
- [How-to / Understanding / Comparative / Future-Trends / Commercial]: [brief note]

## Insight Summary
[2-3 sentences explaining what these questions reveal about user intent.]

## Suggested Blog Focus
[1-2 sentences that should guide the article.]

## Section Assignment
| Question | Intent | Article Section | Answer Format |
|---|---|---|---|
| [question] | [intent] | [H2/FAQ] | [capsule/list/table/FAQ] |
```

## Drafting Rules

- Open with a direct answer in the first 1-2 sentences. The answer comes before the hook.
- Use the Capsule Method below the H1 and at least 60% of major H2s: 50-60 words, complete answer, no preamble.
- Include a Key Takeaways block after the introduction with 3-5 standalone conclusions.
- Use one clear idea per H2/H3 section.
- Integrate at least three credible external sources naturally inside sentences.
- Include 3-5 selected PAA/FAQ questions from research.
- Write FAQ answers as 40-60 word direct answers before any supporting context.
- Add schema notes for `BlogPosting`, `FAQPage`, `Author`, and `VideoObject` when relevant.

## AEO/GEO Map

Every `/article` plan must include:

| Field | Requirement |
|---|---|
| Main answer target | The core question the article answers |
| Capsule targets | H1 plus 60%+ major H2s |
| Selected PAA questions | 3-5 questions from AnswerSocrates or user export |
| Source map | Source, claim, anchor text, target section |
| E-E-A-T proof | Author, reviewer if available, customer proof, expert quote, source-backed claim, limitation/caveat |
| AI citation target | Snippet, PAA, FAQ, comparison table, definition, or list |

## Publish Gates

A draft is publish-ready only when both gates pass:

- General content quality score: 85/100 or higher.
- AEO/GEO score: 90/100 or higher.

Below-threshold drafts route to revision or `review-required/` with notes explaining failed checks.
