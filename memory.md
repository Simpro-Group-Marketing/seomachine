# Readiness performance and memory contract

The P0 release path is serial by design. It performs one complete preflight readiness execution and one receipt-backed finalization delta. Parallel gate execution remains deferred until connector, HTTP-cache, and atomic-output state is proven concurrency-safe.

## Memory boundaries

- Markdown and text control artifacts are limited to 1 MiB each.
- JSON control artifacts retain a deeply immutable parsed object, not raw bytes or a second decoded-text copy, and are limited to 8 MiB each.
- Duplicate BOM labels share one `InputSnapshot` for a resolved path.
- Final sealing streams SHA-256 in 1 MiB chunks instead of loading another full copy.
- Normal releases do not enable `tracemalloc`.
- `process_peak_rss_bytes` is reported only when the platform exposes it without another dependency; it is `null` on Windows.

## I/O boundaries

- Direct and BOM-declared inputs are canonicalized and captured before expensive readiness gates.
- Missing, escaped, oversized, invalid UTF-8, duplicate-key JSON, and declared-hash mismatches fail closed.
- Compatible guards receive immutable article and proof content through content-level adapters. Their standalone `check_file` entry points remain available.
- One run-scoped connector client and one validated claim set are shared by connector-sensitive gates.
- Trusted scorer finding lookups do not reopen or hash files.
- Every unique bound artifact is streamed once during the final reseal.

## Measurement

`release-telemetry.json` uses `simpro-readiness-telemetry/v1` and is deliberately outside readiness and BOM proof schemas. It contains durations and numeric counters only. Standalone readiness can opt in with `--telemetry-output`.

The controlled performance acceptance run remains: one warm-up followed by ten deterministic offline optimized releases. Report median wall time, full-readiness call count, connector-client count, unique file reads, final rehashes, and peak RSS. Do not claim the 40% wall-time or 10% memory thresholds from unit-test timings.
