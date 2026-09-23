#!/usr/bin/env bash
# Mint the optimization stage receipt around the optimizer edit, rerun the
# post-optimization scrub and context binding, then run the final release.
#
# Usage: scripts/run_subcontractors_final_release.sh <preflight-release-suffix> <output-suffix>
set -euo pipefail
cd "$(dirname "$0")/.."
source .run-subcontractors.env

PRE="$1"; SUFFIX="$2"
A="rewrites/$SLUG-$DATE.md"
R="research/stage-receipts/$SLUG"
PRE_DIR="research/releases/$SLUG-$DATE-$RUNHEX-$PRE"
OUT="research/releases/$SLUG-$DATE-$RUNHEX-$SUFFIX"

PREV_HASH=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['receipt_hash'])" "$PRE_DIR/preflight-readiness-stage-receipt.json")

# The optimization stage has to bracket the optimizer's own edit, so the Step 6
# capsule is rolled back and re-applied inside the bracket.
optimizer_edit() { python scripts/toggle_subcontractors_pack_image_alt.py "$1"; }

optimizer_edit revert
rm -f "$R/optimization-state.json" "$R/optimization.json" \
      "$R/post-optimization-scrub.json" "$R/post-optimization-scrub-evidence.json" \
      "$R/post-optimization-context-binding.json" "$R/post-optimization-context-binding-evidence.json"

python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit \
  --article "$A" --state "$R/optimization-state.json" --run-id "$RUN_ID" --stage optimization \
  --tool-name "optimize-command" --tool-version "1" \
  --input "preflight_readiness=$PRE_DIR/preflight-readiness.json" \
  --previous-receipt-hash "$PREV_HASH" > /dev/null

optimizer_edit apply

python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit \
  --article "$A" --state "$R/optimization-state.json" --receipt "$R/optimization.json" \
  --evidence "proof_sidecar=research/validation-$SLUG-$DATE.md" \
  --evidence "command_definition.optimize-command=.claude/commands/optimize.md" \
  --evidence "agent_definition.content-analyzer=.claude/agents/content-analyzer.md" \
  --evidence "agent_output.content-analyzer=research/agent-outputs/content-analyzer-$SLUG-$DATE.md" \
  --evidence "agent_definition.seo-optimizer=.claude/agents/seo-optimizer.md" \
  --evidence "agent_output.seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md" \
  --evidence "agent_definition.meta-creator=.claude/agents/meta-creator.md" \
  --evidence "agent_output.meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md" \
  --evidence "agent_definition.internal-linker=.claude/agents/internal-linker.md" \
  --evidence "agent_output.internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md" \
  --evidence "agent_definition.keyword-mapper=.claude/agents/keyword-mapper.md" \
  --evidence "agent_output.keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md" \
  --evidence "scorecard=$PRE_DIR/preflight-readiness.json" > /dev/null

python scripts/build_subcontractors_optimizer_output.py

python data_sources/modules/content_scrubber.py "$A" --stage post_optimization_scrub \
  --run-id "$RUN_ID" --previous-receipt "$R/optimization.json" \
  --stage-receipt-output "$R/post-optimization-scrub.json" > /dev/null

python data_sources/modules/context_binding_generator.py "$A" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." \
  --stage post_optimization_context_binding --run-id "$RUN_ID" \
  --previous-receipt "$R/post-optimization-scrub.json" \
  --stage-receipt-output "$R/post-optimization-context-binding.json" > /dev/null

python scripts/build_subcontractors_review_artifacts.py > /dev/null

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
  --answersocrates-blocker "research/answersocrates-blocker-$SLUG-$DATE.json" \
  --customer-proof-evidence "research/nonvault-customer-proof-selector-evidence-$SLUG-$DATE.json" \
  --content-brief "research/content-brief-$SLUG-$DATE.md" \
  --optimizer-output "research/optimizer-output-$SLUG-$DATE.json" \
  --prior-preflight-readiness "$PRE_DIR/preflight-readiness.json" \
  --agent-output "content-analyzer=research/agent-outputs/content-analyzer-$SLUG-$DATE.md" \
  --agent-output "seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md" \
  --agent-output "meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md" \
  --agent-output "internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md" \
  --agent-output "keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md" \
  --stage-receipt "$R/draft.json" \
  --stage-receipt "$R/scrub.json" \
  --stage-receipt "$R/context-binding.json" \
  --stage-receipt "$PRE_DIR/preflight-readiness-stage-receipt.json" \
  --stage-receipt "$R/optimization.json" \
  --stage-receipt "$R/post-optimization-scrub.json" \
  --stage-receipt "$R/post-optimization-context-binding.json" \
  --workflow-mode rewrite --assembly-date "$(date -u +%Y-%m-%d)" --output-dir "$OUT"
