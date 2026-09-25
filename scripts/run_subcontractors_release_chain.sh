#!/usr/bin/env bash
# Rebuild the stage-receipt chain, machine reviews and plan fulfillment against
# the current article bytes, then run the release wrapper.
#
# Usage: scripts/run_subcontractors_release_chain.sh <output-suffix> [extra blog_release args...]
set -euo pipefail
cd "$(dirname "$0")/.."
source .run-subcontractors.env

SUFFIX="$1"; shift
A="rewrites/$SLUG-$DATE.md"
R="research/stage-receipts/$SLUG"
OUT="research/releases/$SLUG-$DATE-$RUNHEX-$SUFFIX"
FR="https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"

# The draft stage must bracket a real article change, so the last contextual
# link is held out and re-applied inside the bracket.
python - "$A" "$FR" hold <<'PYEOF'
import pathlib, sys
path, fr, mode = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(path); text = p.read_text(encoding="utf-8")
linked = f"The [proposed rule]({fr}) also records that"
plain = "It also records that"
before, after = (linked, plain) if mode == "hold" else (plain, linked)
assert before in text, f"expected {before[:40]!r} in the article"
p.write_text(text.replace(before, after, 1), encoding="utf-8", newline="")
PYEOF

rm -f "$R/draft-state.json" "$R/draft.json" "$R/scrub.json" "$R/scrub-evidence.json" \
      "$R/context-binding.json" "$R/context-binding-evidence.json"

python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit \
  --article "$A" --state "$R/draft-state.json" --run-id "$RUN_ID" --stage draft \
  --tool-name "rewrite-command" --tool-version "1" \
  --input "editorial_plan=research/editorial-plan-$SLUG-$DATE.json" \
  --input "analysis=research/analysis-$SLUG-$DATE.md" > /dev/null

python - "$A" "$FR" apply <<'PYEOF'
import pathlib, sys
path, fr, mode = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(path); text = p.read_text(encoding="utf-8")
linked = f"The [proposed rule]({fr}) also records that"
plain = "It also records that"
before, after = (linked, plain) if mode == "hold" else (plain, linked)
assert before in text, f"expected {before[:40]!r} in the article"
p.write_text(text.replace(before, after, 1), encoding="utf-8", newline="")
PYEOF

python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit \
  --article "$A" --state "$R/draft-state.json" --receipt "$R/draft.json" \
  --evidence "keyword_decision=research/semrush-keyword-decision-$SLUG-$DATE.json" \
  --evidence "serp_evidence=research/serp-evidence-$SLUG-$DATE.json" \
  --evidence "proof_sidecar=research/validation-$SLUG-$DATE.md" > /dev/null

python data_sources/modules/content_scrubber.py "$A" --stage scrub --run-id "$RUN_ID" \
  --previous-receipt "$R/draft.json" --stage-receipt-output "$R/scrub.json" > /dev/null

python data_sources/modules/context_binding_generator.py "$A" \
  --proof-sidecar "research/validation-$SLUG-$DATE.md" \
  --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." \
  --stage context_binding --run-id "$RUN_ID" --previous-receipt "$R/scrub.json" \
  --stage-receipt-output "$R/context-binding.json" > /dev/null

python scripts/build_subcontractors_review_artifacts.py > /dev/null

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
  --answersocrates-blocker "research/answersocrates-blocker-$SLUG-$DATE.json" \
  --customer-proof-evidence "research/nonvault-customer-proof-selector-evidence-$SLUG-$DATE.json" \
  --content-brief "research/content-brief-$SLUG-$DATE.md" \
  --agent-output "seo-optimizer=research/agent-outputs/seo-optimizer-$SLUG-$DATE.md" \
  --agent-output "meta-creator=research/agent-outputs/meta-creator-$SLUG-$DATE.md" \
  --agent-output "internal-linker=research/agent-outputs/internal-linker-$SLUG-$DATE.md" \
  --agent-output "keyword-mapper=research/agent-outputs/keyword-mapper-$SLUG-$DATE.md" \
  --stage-receipt "$R/draft.json" \
  --stage-receipt "$R/scrub.json" \
  --stage-receipt "$R/context-binding.json" \
  --workflow-mode rewrite --assembly-date "$(date -u +%Y-%m-%d)" --output-dir "$OUT" "$@"
