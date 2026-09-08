# Blog Editorial Quality Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical non-AEO editorial contract across blog brands, repair story-policy conflicts, strengthen reader promise and continuity, make CTAs intent-sensitive, and remove fixed blog length and low keyword-density penalties.

**Architecture:** Keep editorial craft in `context/blog-editorial-strategy.md`, then make existing research, writing, rewrite, analysis, optimization, and editing workflows consume that contract. Align the existing engagement, keyword, SEO-quality, and content-scoring modules without adding a new publish gate or changing AEO behavior.

**Tech Stack:** Markdown workflow contracts, Python 3 analysis modules, pytest.

## Global Constraints

- Apply shared editorial mechanics to all blog brands while preserving brand-specific voice and proof authority.
- Do not change landing-page, product-page, email, social, or CRO scoring rules.
- Do not modify AEO raters, FAQ/PAA/schema guards, proof selectors, or AEO thresholds.
- Preserve all pre-existing dirty checkout changes by working on `codex/blog-editorial-quality` in an isolated worktree.

## Tasks

- [ ] Create the canonical editorial contract and documentation regression tests.
- [ ] Wire the Reader Contract, proof-safe scenes, headline integrity, stakes, and continuity pass into blog workflows and agents.
- [ ] Make CTA requirements and the engagement analyzer intent-sensitive.
- [ ] Remove fixed blog word-count and low keyword-density instructions and scoring penalties while preserving diagnostics and stuffing detection.
- [ ] Run targeted editorial tests, unchanged AEO regression tests, read-only cross-brand pilots, the full test suite, and diff verification.

## Acceptance Commands

```powershell
python -m pytest tests/test_blog_editorial_workflow_docs.py tests/test_engagement_analyzer.py tests/test_editorial_scoring.py tests/test_optimizer_modules.py -q
python -m pytest tests/test_aeo_geo_workflow_docs.py tests/test_aeo_geo_rater.py tests/test_content_scorer_aeo_geo_gate.py tests/test_faq_answer_quality_guard.py tests/test_faq_proof_guard.py -q
python -m pytest -q
git diff --check
rg -n "2-3 specific scenarios with names|2-3 mini-stories|Minimum 2000 words|1-2% density" .claude context README.md tests
```
