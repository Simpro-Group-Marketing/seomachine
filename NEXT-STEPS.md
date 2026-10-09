# Next Steps

This checkout now follows the vault-only Simpro source boundary.

## Current Local Context Scope

Local `context/` files are allowed only for:

- SEO/AEO strategy and evidence
- Brand-neutral editorial mechanics
- Generic CRO best practices
- Link maps, site architecture, and commercial SEO routing
- Source and URL governance

Every remaining context file must be registered in `context/context-policy.json`.

## Do Not Add Local Brand Mirrors

Do not recreate local files for Simpro brand voice, message house, ICP, audience, product language, feature language, solution or industry positioning, Lightning positioning, competitor battlecards, customer proof, reviews, metrics, ebooks, E-E-A-T sources, approved claims, or full brand writing examples.

For Simpro-owned or Simpro-signal work, use the Brand Vault connector. If vault status, search, read/expand, claims, context build, or validation cannot complete, stop and record the blocker.

## Recommended Workflow

1. Keep SEO/AEO records, link maps, commercial routing, and generic editorial/CRO mechanics current.
2. Use the vault connector for brand, product, proof, customer-story, review, competitor, ebook, and writing-exemplar inputs.
3. Run the context boundary guard after changing `context/`, commands, guard docs, or source-routing instructions.
4. For changed Simpro blogs, run the required scrub, readiness, optimize, post-edit scrub, and final readiness sequence.

## Useful Checks

```bash
python -m data_sources.modules.context_boundary_guard --workspace-root . --fail-on error
python -m pytest tests/test_customer_proof_selector.py
python -m pytest tests/test_context_binding_guard.py tests/test_vault_brand_language_guard.py
```
