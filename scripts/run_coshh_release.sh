#!/usr/bin/env bash
# Mint the scrub and context-binding receipts on the current article bytes,
# rebuild plan fulfillment and machine reviews, then run the release wrapper.
# The draft receipt is minted separately around the native /rewrite edit.
#
# Usage: scripts/run_coshh_release.sh <output-suffix> [extra blog_release args...]
set -euo pipefail
cd "$(dirname "$0")/.."
source .run-coshh.env

SUFFIX="$1"; shift
A="rewrites/$SLUG-$DATE.md"
R="research/stage-receipts/$SLUG"
OUT="research/releases/$SLUG-$DATE-$RUNHEX-$SUFFIX"

rm -f "$R/scrub.json" "$R/scrub-evidence.json" "$R/context-binding.json" "$R/context-binding-evidence.json"

python data_sources/modules/content_scrubber.py "$A" --stage scrub --run-id "$RUN_ID" \
  --previous-receipt "$R/draft.json" --stage-receipt-output "$R/scrub.json" > /dev/null

python data_sources/modules/context_binding_generator.py "$A" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --not-applicable-reason "BigChange nonconnector article: no Simpro brand, URL, or connector-sensitive language." \
  --stage context_binding --run-id "$RUN_ID" --previous-receipt "$R/scrub.json" \
  --stage-receipt-output "$R/context-binding.json" > /dev/null

python scripts/build_coshh_review_artifacts.py

rm -rf "$OUT"
python -m data_sources.modules.blog_release "$A" --run-id "$RUN_ID" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --editorial-plan "research/editorial-plan-$SLUG-$DATE.json" \
  --plan-review "research/machine-review-plan-$SLUG-$DATE.json" \
  --article-review "research/machine-review-article-$SLUG-$DATE.json" \
  --keyword-decision "research/semrush-keyword-decision-$SLUG-$DATE.json" \
  --scrub-receipt "$R/scrub.json" \
  --serp-evidence "research/serp-evidence-$SLUG-$DATE.json" \
  --plan-fulfillment "research/blog-plan-fulfillment-$SLUG-$DATE.json" \
  --commercial-pillar-index "context/commercial-pillar-index.json" \
  --customer-proof-evidence "research/nonvault-customer-proof-selector-evidence-$SLUG-$DATE.json" \
  --content-brief "research/content-brief-$SLUG-$DATE.md" \
  --agent-output "seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md" \
  --agent-output "meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md" \
  --agent-output "internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md" \
  --agent-output "keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md" \
  --stage-receipt "$R/draft.json" \
  --stage-receipt "$R/scrub.json" \
  --stage-receipt "$R/context-binding.json" \
  --workflow-mode rewrite --assembly-date "$DATE" --output-dir "$OUT" "$@"
