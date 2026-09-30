#!/usr/bin/env bash
# Governed no-op /optimize: article bytes are unchanged, so no optimization
# receipt is minted. Rebuild the sidecar, write the optimizer output, rerun the
# post-optimization scrub and context binding from the preflight receipt, then
# run the final release on the optimized tail.
#
# Usage: scripts/run_coshh_final_release.sh <preflight-release-suffix> <output-suffix>
set -euo pipefail
cd "$(dirname "$0")/.."
source .run-coshh.env

PRE="$1"; SUFFIX="$2"
A="rewrites/$SLUG-$DATE.md"
R="research/stage-receipts/$SLUG"
PRE_DIR="research/releases/$SLUG-$DATE-$RUNHEX-$PRE"
OUT="research/releases/$SLUG-$DATE-$RUNHEX-$SUFFIX"

python scripts/build_coshh_sidecar.py > /dev/null
python scripts/build_coshh_optimizer_output.py --preflight-readiness "$PRE_DIR/preflight-readiness.json" > /dev/null

rm -f "$R/post-optimization-scrub.json" "$R/post-optimization-scrub-evidence.json" \
      "$R/post-optimization-context-binding.json" "$R/post-optimization-context-binding-evidence.json"

python data_sources/modules/content_scrubber.py "$A" --stage post_optimization_scrub \
  --run-id "$RUN_ID" --previous-receipt "$PRE_DIR/preflight-readiness-stage-receipt.json" \
  --stage-receipt-output "$R/post-optimization-scrub.json" > /dev/null

python data_sources/modules/context_binding_generator.py "$A" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." \
  --stage post_optimization_context_binding --run-id "$RUN_ID" \
  --previous-receipt "$R/post-optimization-scrub.json" \
  --stage-receipt-output "$R/post-optimization-context-binding.json" > /dev/null

python scripts/build_coshh_review_artifacts.py > /dev/null

rm -rf "$OUT"
python -m data_sources.modules.blog_release "$A" --run-id "$RUN_ID" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --editorial-plan "research/editorial-plan-$SLUG-$DATE.json" \
  --plan-review "research/machine-review-plan-$SLUG-$DATE.json" \
  --article-review "research/machine-review-article-$SLUG-$DATE.json" \
  --keyword-decision "research/semrush-keyword-decision-$SLUG-$DATE.json" \
  --scrub-receipt "$R/post-optimization-scrub.json" \
  --serp-evidence "research/serp-evidence-$SLUG-$DATE.json" \
  --plan-fulfillment "research/blog-plan-fulfillment-$SLUG-$DATE.json" \
  --commercial-pillar-index "context/commercial-pillar-index.json" \
  --customer-proof-evidence "research/nonvault-customer-proof-selector-evidence-$SLUG-$DATE.json" \
  --content-brief "research/content-brief-$SLUG-$DATE.md" \
  --optimizer-output "research/optimizer-output-$SLUG-$DATE.json" \
  --prior-preflight-readiness "$PRE_DIR/preflight-readiness.json" \
  --agent-output "content-analyzer=research/agent-outputs/content-analyzer-$SLUG-$DATE.md" \
  --agent-output "seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md" \
  --agent-output "meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md" \
  --agent-output "internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md" \
  --agent-output "keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md" \
  --stage-receipt "$R/post-optimization-scrub.json" \
  --stage-receipt "$R/post-optimization-context-binding.json" \
  --workflow-mode rewrite --assembly-date "$DATE" --output-dir "$OUT"
