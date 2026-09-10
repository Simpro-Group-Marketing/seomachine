# Readiness performance and memory contract

The readiness gate path remains serial by design. It performs one complete preflight readiness execution and one receipt-backed finalization delta. P1 introduces concurrency only inside ordered public-HTTP batches, with eight total workers and at most two active requests per hostname.

## Memory boundaries

- Markdown and text control artifacts are limited to 1 MiB each.
- JSON control artifacts retain a deeply immutable parsed object, not raw bytes or a second decoded-text copy, and are limited to 8 MiB each.
- Duplicate BOM labels share one `InputSnapshot` for a resolved path.
- Final sealing streams SHA-256 in 1 MiB chunks instead of loading another full copy.
- Normal releases do not enable `tracemalloc`.
- `process_peak_rss_bytes` is reported only when the platform exposes it without another dependency; it is `null` on Windows.
- The scoring stack is imported only after every pre-scoring gate passes. Import-only and early-blocker paths do not load `content_scorer`, `readability_scorer`, or `textstat`.
- The persistent public-response cache is bounded to 256 MiB and stores response snapshots, never connector payloads, readiness proof, article text, authorization headers, cookies, or credential-bearing URLs.

## I/O boundaries

- Direct and BOM-declared inputs are canonicalized and captured before expensive readiness gates.
- Missing, escaped, oversized, invalid UTF-8, duplicate-key JSON, and declared-hash mismatches fail closed.
- Compatible guards receive immutable article and proof content through content-level adapters. Their standalone `check_file` entry points remain available.
- One run-scoped connector client and one validated claim set are shared by connector-sensitive gates.
- Connector access runs inside one immutable `workflow_snapshot()`: one bounded state parse on entry and one protocol-artifact seal on exit. Revision or hash drift fails closed without retry.
- One run-scoped `PublicHttpTransport` deduplicates semantically identical requests in memory and, when available, through an atomic locked disk cache. Cache availability affects performance only, never proof verdicts.
- Public URL safety and credential checks run before cache lookup. Redirect hops retain IP-pinned SSRF validation and per-host concurrency limits.
- Stable HTTP responses use bounded TTLs: 24 hours for success, 15 minutes for 404/410, and 5 minutes for 401/403. Rate limits, 5xx responses, DNS failures, timeouts, and transport errors remain run-local.
- Trusted scorer finding lookups do not reopen or hash files.
- Every unique bound artifact is streamed once during the final reseal.

## Measurement

`release-telemetry.json` uses `simpro-readiness-telemetry/v1` and is deliberately outside readiness and BOM proof schemas. It contains durations and numeric counters only. Standalone readiness can opt in with `--telemetry-output`.

The controlled performance acceptance run remains: one warm-up followed by ten deterministic offline optimized releases. Report median wall time, full-readiness call count, connector-client count, unique file reads, final rehashes, and peak RSS. Do not claim the 40% wall-time or 10% memory thresholds from unit-test timings.

The checked P0 fixture baseline is stored in `research/performance/p0-offline-release-baseline.json`; the corresponding P1 run is stored in `research/performance/p1-offline-release-benchmark.json`. These records describe only the fixed offline characterization fixture. They do not measure live connector or internet latency.
