"""Compatibility facade for SEO quality scoring."""

try:
    from .content_scoring.seo_constants import (
        BRAND_INTERNAL_DOMAINS,
        COMMERCIAL_PILLAR_INDEX_PATH,
        DOWN_FUNNEL_EXACT_PATHS,
        DOWN_FUNNEL_PATH_PREFIXES,
        FENCED_CODE_BLOCK_RE,
        FUNCTIONAL_DESTINATION_TERMS,
        GENERIC_LINK_ANCHORS,
        GEO_KEYWORD_TAIL_TOKENS,
        HTML_COMMENT_RE,
        MARKDOWN_IMAGE_RE,
        META_TITLE_BRAND_SUFFIX_RE,
        NON_VISIBLE_HTML_BLOCK_RE,
        OWNED_INTERNAL_DOMAINS,
        PUBLISHING_THRESHOLD,
        SEO_TARGET_SCORE,
    )
    from .content_scoring.seo_metadata import seo_target_status
    from .content_scoring.seo_rater_orchestration import (
        SEOQualityRater,
        rate_seo_quality,
    )
    from .content_scoring.seo_reporting import main
except ImportError:  # pragma: no cover - direct script compatibility.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from data_sources.modules.content_scoring.seo_constants import (
        BRAND_INTERNAL_DOMAINS,
        COMMERCIAL_PILLAR_INDEX_PATH,
        DOWN_FUNNEL_EXACT_PATHS,
        DOWN_FUNNEL_PATH_PREFIXES,
        FENCED_CODE_BLOCK_RE,
        FUNCTIONAL_DESTINATION_TERMS,
        GENERIC_LINK_ANCHORS,
        GEO_KEYWORD_TAIL_TOKENS,
        HTML_COMMENT_RE,
        MARKDOWN_IMAGE_RE,
        META_TITLE_BRAND_SUFFIX_RE,
        NON_VISIBLE_HTML_BLOCK_RE,
        OWNED_INTERNAL_DOMAINS,
        PUBLISHING_THRESHOLD,
        SEO_TARGET_SCORE,
    )
    from data_sources.modules.content_scoring.seo_metadata import seo_target_status
    from data_sources.modules.content_scoring.seo_rater_orchestration import (
        SEOQualityRater,
        rate_seo_quality,
    )
    from data_sources.modules.content_scoring.seo_reporting import main

__all__ = [
    "BRAND_INTERNAL_DOMAINS",
    "COMMERCIAL_PILLAR_INDEX_PATH",
    "DOWN_FUNNEL_EXACT_PATHS",
    "DOWN_FUNNEL_PATH_PREFIXES",
    "FENCED_CODE_BLOCK_RE",
    "FUNCTIONAL_DESTINATION_TERMS",
    "GENERIC_LINK_ANCHORS",
    "GEO_KEYWORD_TAIL_TOKENS",
    "HTML_COMMENT_RE",
    "MARKDOWN_IMAGE_RE",
    "META_TITLE_BRAND_SUFFIX_RE",
    "NON_VISIBLE_HTML_BLOCK_RE",
    "OWNED_INTERNAL_DOMAINS",
    "PUBLISHING_THRESHOLD",
    "SEO_TARGET_SCORE",
    "SEOQualityRater",
    "main",
    "rate_seo_quality",
    "seo_target_status",
]


if __name__ == "__main__":
    raise SystemExit(main())
