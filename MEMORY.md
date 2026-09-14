# Architectural Memory

## Architecture

- The atomic release owner is [blog_release.py](data_sources/modules/blog_release.py). It performs one full preflight readiness execution followed by receipt-backed finalization.
- Readiness orchestration enters through [readiness/api.py](data_sources/modules/readiness/api.py). One `ValidationSession` owns its `InstrumentedArtifactStore`, parsed views, connector and Git state, source text, transport, and telemetry; compatibility facades preserve established imports and result schemas.
- Proof gates, connector revision checks, parsing, and lazy scoring remain serial. Only deduplicated public HTTP retrieval uses bounded worker threads behind [public_http/transport.py](data_sources/modules/public_http/transport.py), with stable result ordering.

## Package ownership

- `bounded_io` owns bounded bytes, strict UTF-8/JSON decoding, hashing, canonical JSON, and file identity; `resource_metrics` owns portable process-memory sampling.
- `connector_snapshot` owns immutable connector workflow state and successful read-only operation caching; `public_http` owns typed transport, cache identity, concurrency, and batch byte budgets.
- `blog_bom_validation`, `paa_provenance`, `customer_proof`, and `editorial_plan` own their proof-domain contracts and orchestration. Their historical top-level modules are explicit compatibility facades.
- `content_scoring` owns serial, lazy AEO/SEO scoring. `mcp-gsc/mcp_gsc` owns GSC authentication, contracts, tools, and server composition; `gsc_server.py` is its compatibility facade.

## Proof invariants

- Proof, input seals, BOM bindings, receipts, connector revisions, and fail-closed behavior are never weakened for performance.
- Cache, telemetry, architectural memory, and retention metadata are operational aids, never proof authority.
- The full proof-sensitive and connector workflow contract remains in [AGENTS.md](AGENTS.md).

## Resource limits

| Limit key | Bytes |
| --- | ---: |
| `article_max_bytes` | 1048576 |
| `artifact_store_max_bytes` | 33554432 |
| `connector_result_cache_max_bytes` | 33554432 |
| `hash_chunk_bytes` | 1048576 |
| `http_batch_max_bytes` | 33554432 |
| `http_cache_max_bytes` | 268435456 |
| `http_memo_max_bytes` | 33554432 |
| `json_max_bytes` | 8388608 |
| `session_normalized_source_max_bytes` | 33554432 |
| `sidecar_max_bytes` | 1048576 |
| `subprocess_spool_threshold_bytes` | 1048576 |
| `subprocess_input_max_bytes` | 8388608 |
| `subprocess_stream_max_bytes` | 33554432 |
| `xdist_worker_peak_rss_max_bytes` | 100663296 |

- Final hashes stream once in deterministic path order. Duplicate readiness labels and BOM-expanded inputs share one immutable snapshot and parsed view.
- Stable HTTP responses retain their policy TTLs; transient failures remain run-local. Request reservations count against the batch ceiling before submission.
- Scoring dependencies load only after pre-scoring gates pass. Normal releases do not enable `tracemalloc`.

## Evidence index

- Structural debt and declining limits: [python-structure-baseline.json](config/python-structure-baseline.json).
- P0 release characterization: [p0-offline-release-baseline.json](research/performance/p0-offline-release-baseline.json).
- P1 release characterization: [p1-offline-release-benchmark.json](research/performance/p1-offline-release-benchmark.json).
- Authoritative-session cold/warm characterization: [p1-offline-release-benchmark-v2-final.json](research/performance/p1-offline-release-benchmark-v2-final.json).
- P2 test-sharding characterization: [p2-test-sharding-benchmark.json](research/performance/p2-test-sharding-benchmark.json).
- Repository reliability method: [2026-08-10-repository-reliability-review.md](docs/superpowers/plans/2026-08-10-repository-reliability-review.md).

## Update discipline

- Keep only durable architecture, proof invariants, resource limits, and tracked evidence pointers here.
- Do not add task status, raw evidence, credentials, copied operating instructions, or speculative behavior.
- Update this file and its CI limits in the same change when an architectural contract changes.
