# Full-update upload optimization plan

The current native volume full-update path is too slow in the new observations.
Two valid 256³ float32 MIP pairs have a median of run medians of approximately
31 ms upstream and 116 ms candidate. The collection is incomplete and retains
instrumentation gaps, so these numbers do not qualify a release. They identify
an engineering problem against the unchanged update requirement: candidate
median must be at most 1.10 times the upstream median.

Native counters and source inspection identify repeated host byte copies and
texture preparation as concrete targets. Inclusive timer scopes overlap and
must not be added together. Removing copies alone is not assumed sufficient to
meet the target. The first independent planning packet is retained privately at
`build/volume-full-upload-plan-root-1`; it is advice, not an implementation or
admission result.

1. Build a private CPU prototype after live timing workers finish. Preserve the
   canonical native source, current native modules, frozen inputs, and wheels.
   Compare a copied legacy preparation path against the proposed path using
   identical inputs and exact descriptor/byte/exception comparisons.
2. First optimize only complete uploads whose existing direct-format predicate
   already proves byte identity. Separate descriptor validation from materialized
   preparation bytes, and use a short-lived view of the engine-owned source
   vector through the upload call. For aligned rows, avoid creating and copying
   a redundant padded vector. Preserve conversion, empty-source, partial-update,
   and unaligned-row fallbacks. Borrow no Python pointer beyond the binding call.
3. Test float32 NaN payloads, signed zero, subnormals and infinities; integer
   identities; normalized and half-float conversion; channel expansion; empty
   input; mixed source types; bounds and overflow; and aligned/unaligned 2D/3D
   extents. Check source immutability and ownership through moves. Run the
   existing texture contracts and conversion corpus against both paths.
4. Audit every consumer of preparation bytes before porting the change. Storage
   accounting, texture views, samplers, pending revisions and asynchronous GPU
   lifetimes must retain their existing behavior. Reject any byte, descriptor,
   exception, non-timing counter, or ownership mismatch.
5. Port a proven prototype through a new native source epoch, fresh build and
   wheel, and fresh scientific and image admissions. Existing artifacts and
   saved references remain unchanged. Compare actual full-update upload counts
   and bytes, all hot-work gates, GPU ownership, waits, and allocation accounting.
6. Collect a fresh predeclared five-pair full-update result after fixing the
   unsolicited expose-paint ownership problem. Keep all failed attempts.
   Preserve the quality limits, input sizes, update formulas, precision, volume
   sampling, and performance thresholds.

If the first change is insufficient, next evaluate transferring an already
owned full-replacement blob rather than copying it, and removing the redundant
Python `tobytes` intermediate while still capturing immutable bytes before the
binding returns. An asynchronous staging-buffer design requires a separate
lifetime and reuse plan; no synchronous wait is acceptable on the measured path.

Pending independently: scanout measurement, complete driver/allocator peak
accounting, the remaining workload/platform matrix, and every other original
release requirement. The implementation remains AGPL-3.0-only with the original
VisPy BSD license and third-party notices attached unchanged.
