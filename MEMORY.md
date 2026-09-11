# Architectural Memory

## Architecture

- The atomic release owner is [blog_release.py](data_sources/modules/blog_release.py). It performs one full preflight readiness execution followed by receipt-backed finalization.
- Readiness orchestration enters through [readiness/api.py](data_sources/modules/readiness/api.py). Compatibility facades preserve established imports and result schemas.
- Public HTTP work is run-scoped and bounded by [public_http/transport.py](data_sources/modules/public_http/transport.py). Readiness gates remain serial.

## Proof invariants

- Proof, input seals, BOM bindings, receipts, connector revisions, and fail-closed behavior are never weakened for performance.
- Cache, telemetry, architectural memory, and retention metadata are operational aids, never proof authority.
- The full proof-sensitive and connector workflow contract remains in [AGENTS.md](AGENTS.md).

## Resource limits

- Article and validation-sidecar UTF-8 files are capped at 1 MiB each. JSON control artifacts are capped at 8 MiB.
- Subprocess stdout and stderr spool after 1 MiB and fail above 32 MiB per stream.
- Final hashes stream in 1 MiB chunks. Duplicate readiness labels share one immutable snapshot.
- Public HTTP persistence is capped at 256 MiB. Stable responses retain their policy TTLs; transient failures remain run-local.
- Scoring dependencies load only after pre-scoring gates pass. Normal releases do not enable `tracemalloc`.

## Evidence index

- Structural debt and declining limits: [python-structure-baseline.json](config/python-structure-baseline.json).
- P0 release characterization: [p0-offline-release-baseline.json](research/performance/p0-offline-release-baseline.json).
- P1 release characterization: [p1-offline-release-benchmark.json](research/performance/p1-offline-release-benchmark.json).
- P2 test-sharding characterization: [p2-test-sharding-benchmark.json](research/performance/p2-test-sharding-benchmark.json).
- Repository reliability method: [2026-08-10-repository-reliability-review.md](docs/superpowers/plans/2026-08-10-repository-reliability-review.md).

## Update discipline

- Keep only durable architecture, proof invariants, resource limits, and tracked evidence pointers here.
- Do not add task status, raw evidence, credentials, copied operating instructions, or speculative behavior.
- Update this file and its CI limits in the same change when an architectural contract changes.
