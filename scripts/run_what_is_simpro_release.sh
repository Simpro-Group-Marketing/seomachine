#!/usr/bin/env bash
# Run the atomic release wrapper for the new What Is Simpro blog.
#
# Usage: scripts/run_what_is_simpro_release.sh initial <suffix>
#        scripts/run_what_is_simpro_release.sh final <preflight-suffix> <suffix> [extra wrapper args]
set -euo pipefail
cd "$(dirname "$0")/.."
source .run-what-is-simpro.env

MODE="$1"
A="drafts/$SLUG-$DATE.md"
P="research/stage-receipts/$SLUG/$DATE-$RUNHEX"
BASE="research/releases/$SLUG-$DATE-$RUNHEX"

COMMON=(
  --run-id "$RUN_ID"
  --proof-sidecar "research/validation-$SLUG-$DATE.md"
  --editorial-plan "research/editorial-plan-$SLUG-$DATE.json"
  --plan-review "research/machine-review-plan-$SLUG-$DATE.json"
  --article-review "research/machine-review-article-$SLUG-$DATE.json"
  --keyword-decision "research/semrush-keyword-decision-$SLUG-$DATE.json"
  --serp-evidence "research/serp-evidence-$SLUG-$DATE.json"
  --plan-fulfillment "research/blog-plan-fulfillment-$SLUG-$DATE.json"
  --commercial-pillar-index "context/commercial-pillar-index.json"
  --context-request "research/context-request-$SLUG.json"
  --context-pack "research/context-pack-$SLUG.json"
  --context-receipt "research/context-receipt-$SLUG.json"
  --customer-proof-evidence "research/customer-proof-selector-evidence-$SLUG-decision-$DATE.json"
  --fred-authority-evidence "research/fred-authority-selector-$SLUG-$DATE.md"
  --hindsight-strategy-evidence "research/hindsight-strategy-evidence-$SLUG-$DATE.json"
  --paa-artifact "research/paa-evidence-$SLUG-$DATE.json"
  --content-brief "research/brief-$SLUG-$DATE.md"
  --workflow-mode new
  --assembly-date "$DATE"
)

AGENTS=(
  --agent-output "content-analyzer=research/agent-outputs/content-analyzer-$SLUG-$DATE.md"
  --agent-output "seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md"
  --agent-output "meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md"
  --agent-output "internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md"
  --agent-output "keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md"
)

if [ "$MODE" = "initial" ]; then
  OUT="$BASE-$2"
  python -m data_sources.modules.blog_release "$A" "${COMMON[@]}" "${AGENTS[@]}" \
    --scrub-receipt "$P-scrub.json" \
    --stage-receipt "$P-draft.json" \
    --stage-receipt "$P-scrub.json" \
    --stage-receipt "$P-context-binding.json" \
    "${@:3}" \
    --output-dir "$OUT"
else
  PRE_DIR="$BASE-$2"; OUT="$BASE-$3"
  python -m data_sources.modules.blog_release "$A" "${COMMON[@]}" "${AGENTS[@]}" \
    --scrub-receipt "$P-post-optimization-scrub.json" \
    --optimizer-output "research/optimizer-output-$SLUG-$DATE.json" \
    --prior-preflight-readiness "$PRE_DIR/preflight-readiness.json" \
    "${@:4}" \
    --output-dir "$OUT"
fi
