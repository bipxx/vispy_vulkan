# Large image quality and residency protocol

This protocol addresses the 4096×4096 scientific image gap with four cases:
float32 scalar and uint8 RGBA, each with nearest and linear interpolation.
The scalar field has four dyadic intensities and variation along both axes.
RGBA has distinct spatial formulas for all channels, including RGB beneath zero
alpha. Blending and depth testing are disabled. The ImageVisual uses its public
GPU texture scaling path and a single-cell subdivided image mesh.
The ViewBox explicitly has zero border, margin and padding. Both its outer and
inner rectangles must cover the complete 64×64 logical canvas; the runtime
asserts these bounds and the canvas size before capture.
The public TransformSystem is configured with the actual 4096-square FBO size
and the physical canvas region it covers. Runtime corner checks assert the
complete logical canvas maps onto the complete framebuffer, including Y flip.

Each fresh installed-wheel worker keeps one image and one 4096×4096 RGBA8
framebuffer alive for baseline, unchanged repeat, camera pan by (-13,17), and
camera return. The public PanZoomCamera.pan method changes the view. No source
update is permitted after baseline. Pixel centers map to texel centers, also in
the linear cases. These cases do not qualify fractional interpolation or zoom.
Each draw explicitly rebinds the same persistent framebuffer after GLIR CURRENT
resets the context binding. Saved command order must prove the owned target is
bound for every draw; rebinding does not allocate a new framebuffer or texture.

All four original OpenGL cases must finish before any candidate case starts.
The original is official VisPy 0.17.0 on Windows CPython 3.12.8, PyQt6, NumPy
2.4.6 and NVIDIA RTX 4090 driver 610.88. The candidate is the existing audited
Native58 Windows CPython 3.12 artifact; no native rebuild or activation is needed.
Archive hashes and the nine-package hashed runtime closure are pinned in
tools/large_image_wheel_suite.py and its unchanged shared helpers. Installed
payloads, including license files, must match the supplied archives. Loaded
native module origins must belong to the external installed-wheel environment.

Every frame is saved losslessly before quality admission. Every channel of every
pixel must match the corresponding original exactly. An independent analytic
check derives the input pattern and camera mapping without consulting input or
reference arrays. It requires exact RGBA for the color cases, RGB error at most
one byte for scalar quantization, and exact alpha in every case. No pixels are
excluded. Newly exposed pan regions must be opaque black; returning the camera
must restore the original image.

Every repeat, pan and return frame must submit actual draws and Vulkan queue
work, with zero source/geometry uploads, conversions, compiler work, or pipeline
creation/misses. Missing, negative, noninteger or reset counter deltas fail
admission. GLIR DATA commands are forbidden after baseline for both renderers.
The protocol saves counter snapshots, deltas, texture identities, camera bounds,
GLIR and shader sources. It waits for every actual child, verifies shutdown
resource zeros, and removes only newly owned external environments/scratch.
Failures and their raw artifacts are retained.

This qualifies only the Native58 cp312 artifact against official VisPy 0.17.0
with PyQt6 OpenGL in this Windows CPython 3.12.8 / NumPy 2.4.6 / NVIDIA
RTX 4090 / driver 610.88 cell. It does not qualify other Python ABIs, Qt bindings,
providers, GPUs, drivers, or the remaining full-release requirements.

These are quality captures with deliberate readbacks and completion waits.
They do not establish no-wait rendering, timing speedups, long-run memory
plateaus, the full performance matrix, native Linux hardware, or Metal coverage.
AGPL-3.0-only covers the implementation; the original BSD license and notices
remain attached unchanged.

The Source4 execution passes all four fresh original cases before all four
installed Native58 candidates. All 268,435,456 paired frame pixels (1,073,741,824
RGBA bytes) match exactly, with no exclusions. Independent saved-byte inspection
also recomputes analytic quality, verifies repeat/return equal baseline and pan
differs, checks stable source/target/framebuffer identities, actual owned-target
draws, all 20 resident-zero counters for every later candidate frame, eight
shutdown zeros per candidate, eight actual workers and two parent suites waited,
and removal of both owned environments and the cache. Quality readback waits are
recorded and allowed; these captures establish no performance qualification.

The actual pair is `build/large-image-wheel-run-root-4/result.json`, SHA256
`3ab78ee3cade212f63f3ca7c4695ac5f796dcadeb24431728989f343efda6ed2`. Independent inspection is
`build/large-image-prep-root-1/saved-review1.json`, SHA256 `b1e9c1753f20c44bc32cb2bc1bfdf0102469e15131d07a8464f01b5488278276`.
Its inspector imports no VisPy/provider and does not replay graphics. Source4
preregistration is `build/large-image-prep-root-1/source-seal4.json`, SHA256
`32d54700c1fd4cd7abca02223d408f0bf53f2b46238049c7e6f4323b67843dd6`, with exact source snapshots preserved for later doc updates.

The unchanged 53-file original bundle is in
`tests/reference/large-image-opengl`; manifest SHA256
`ace47caea32759727170debd5a08db2c3255b29296873090290f12a12670c4d2`.
The committed manifest and all 52 case artifact/report files are byte-identical
to the successful Source4 original run. The candidate parent and all four actual
worker command receipts bind that exact original manifest digest.
`tests/contract/test_large_image_wheel_parity.py` defines four mandatory installed
candidate cases and requires each successful worker AND the complete successful
parent. Missing artifacts fail rather than skip. The actual graphics evidence
above comes from the waited driver; the pytest wrapper is not separately replayed.
The CPU workflow includes the analytic, capture/metadata, residency, parent and
immutable-reference controls, without invoking graphics.

Three earlier failed execution roots remain intact. Source1 hit NumPy integer
JSON serialization before quality admission; Source2 exposed the incorrect
logical/physical FBO mapping; Source3 passed every baseline and exposed GLIR
CURRENT restoring the default FBO before repeat. Each failure blocked all
candidates, preserved raw artifacts, verified all actual children terminal, and
removed newly owned environments/cache. Fixes serialize coordinates, explicitly
configure the public transform system, and rebind the same owned target. The
image patterns, analytic tolerances and exact original comparison never change.
The two peer reviews and root resolutions are retained; the second peer's
FIX_BEFORE_EXECUTION border finding was resolved by explicit zero layout/bounds
checks before any run. No later peer READY verdict is claimed.
