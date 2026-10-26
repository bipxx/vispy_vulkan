# Cropped byte and float capture

The existing `gloo.read_pixels(viewport, alpha=True, out_type=...)` interface is
unchanged. Viewport coordinates use a bottom-left origin; the returned image has
top-left row order. RGBA8 byte output preserves alpha, and `out_type='float'`
returns normalized float32 channels. An invalid viewport shape is rejected
before finishing preceding rendering; a subsequent valid read consumes that
retained work.

The `tk-capture-1` packet selects a finite part of this behavior on Windows
hardware Vulkan/Tk 8.6 and WSL software Vulkan/Tk 9. Its self-contained scenario
creates a supplied-root Tk canvas, selects its actual target, verifies four
8-bit channels and single-sample storage, renders independent quadrants and
closes its resources. It imports no other workflow's qualification receipt.

| Mode | Selected observation |
| --- | --- |
| Ordinary | A 257×129 target and crop(3,4,131,69), with byte/float RGBA values and fractional alpha. |
| Mutation | Resize to 301×177 and crop(5,7,157,97), crossing both quadrant boundaries. |
| Failure | Reject a three-component viewport while real queued clear work and submit/finish/wait/present counters remain unchanged. |
| Recovery | A valid crop reads that exact retained cyan/alpha clear, without intervening repaint or presentation. |

Every returned byte contributes to an independently expected image hash. The
collector decodes lossless runs of actual float32 pixels and checks every value
and position, finiteness and a 1e-6 absolute normalization tolerance. It does not
accept a self-reported error or quantized hash as sufficient float evidence.

The source scenario and five active output/queue controls have passed on both
profiles. The existing exact Windows/Linux wheels also have retained installed
capture tests; no renderer, native module or wheel change is needed for this
packet. Its eight selected criteria require separate candidate-bound review,
installed observation/control/shutdown evidence, CI and promotion before a new
admission claim. Consult the selected subject in
[`compat/candidates/tk-capture-1`](../compat/candidates/tk-capture-1/) and its
retained qualification handoff for the actual artifact status.

Other crops, target dimensions, formats, RGB-only capture, multisampling,
device-loss recovery, OS scaling, arbitrary host ownership and other backends
are outside this finite packet. Passing it does not discharge the broader
readback/context/backend parents. The previous 120-criterion admission remains
bound to its original artifacts and source; it is not a combined current 128
claim. Metal graphics remain experimental, and WSL software results do not
qualify native Linux GPU hardware.
