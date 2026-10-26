# Generated-line and Metal build corrections

The parent CI logs at `c59b44f41b73c4f2b3a49677e4362a8748ba365a` expose two
independent failures. The Metal arm64 wheel compilation cannot resolve
`CATransaction`; the generated-line CPU contract stops at an assertion that its
original shader has no uniforms. Neither failure is a hardware qualification.

The Metal surface update uses `CATransaction` while importing only
`CAMetalLayer.h`. Its source now imports `QuartzCore/CATransaction.h` explicitly.
Actual Apple compilation remains a CI requirement; a Windows/Linux source check
cannot qualify this declaration change or Metal rendering.

The generated-line contract's basic fragment reads `gl_FragCoord`, which now
requires the runtime depth-range uniform. Windows reproduces the same original
assertion failure as CI. The correction checks the exact reflected `vec2` name,
storage type, offset, size, component count and 16-byte UBO, then preservation
before the generated consumer's four appended parameters. A second shader with
no fragment-coordinate use retains the original empty-UBO assertion, including
the reserved 16 bytes and 80-byte generated extent. No runtime or shader guard
was weakened. The complete compiler contract passes 46,055 checks on Windows
and Linux with existing libraries; these are CPU compiler checks, not GPU proof.

While recording this change, preparation validation exposed a separate identity
gap: its native input inventory omitted `.mm` files. The complete input set now
includes Objective-C++ platform source. Resealed missing/changed-input controls
fail before the verifier correction, and the corrected validator accepts an
intact set while rejecting omission or mutation. Current source/profile pins
must be refreshed together; adding a previously omitted source is not a new
native producer or an upgrade of experimental Linux provenance.

The selected Windows/WSL functional reports retain their original runtime
commit, member hashes and actual exits. Their current preparation references
the complete source snapshot and records why those observations remain useful:
the only changed production source is Apple-only and is not compiled on either
platform. All production Python, non-Apple native, build, lock and license bytes
remain identical. This source equivalence does not transfer installed receipts,
CI results, reviews or hardware qualification to another head.

The existing Windows SDK is reused for one first-party compiler-contract target;
Linux links four retained static compiler libraries with recorded hashes. No
renderer, SDK, wheel, environment or dependency source tree is rebuilt locally.
Small contract executables are retained once by hash. Original CI logs are
referenced from `build/runs/observed-submission-30/`; local baseline failure,
compiler commands, exact inputs, diagnostic outputs and retention/cleanup
records are under `build/runs/ci-contracts-31/`. Terminal cleanup is established
only by that run's applied receipt and retained-hash verification.

Independent cumulative source/fixture review, actual current-head CI, the
execution-ledger/worker-result/index handoff and all original installed,
absence/control, host and platform obligations remain required. The draft PR
must not be promoted from these local CPU passes.
