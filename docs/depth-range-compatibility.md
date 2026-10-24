# Depth-range conversion and explicit fragment depth

This source packet implements STATE-1/2/3/5's reversed-depth-range path. It
retains original GL clip inclusion and per-draw state while using ascending Dawn
viewport depths. Native binary/installed qualification and the independent
implementation review remain separate gates.

## Decision and representation

[Vulkan VkViewport](https://registry.khronos.org/vulkan/specs/latest/man/html/VkViewport.html)
permits either order, but the pinned
[Dawn validator](../third_party/dawn/src/dawn/native/RenderPassEncoder.cpp)
requires ascending minDepth/maxDepth. The parser independently clamps both
finite public endpoints to [0,1] and keeps their logical order. Queries return
that logical pair, including equal endpoints and a reversed pair.

For ordinary raster depth, a reversed draw converts the final original clip
position with `z = (w - z) / 2`, then supplies sorted viewport endpoints. Forward
draws retain `z = (z + w) / 2`. Both conversions preserve the original
`-w <= z <= w` inclusion test. Point expansion retains its existing original
center clipping before the final conversion. User vertex code and its external
effects are not evaluated again.

Orientation is selected after ordinary/point/compact/batch input layout and
before final sampler specialization. The immutable portable shader identity
contains the orientation and window-depth algorithm marker. Earlier queued
snapshots retain their own artifact; changing ranges cannot mutate another
snapshot. Exact near/far values remain captured dynamic state, rather than
creating a shader variant for every numeric pair. Reflection/interface guards
keep the selected input and uniform layout consistent.

## Explicit fragment output and fragment coordinates

The baseline also reproduces a forward-range error: explicit depth .1 is
incorrectly clamped into viewport [.2,.8].
[OpenGL shader output rules](https://registry.khronos.org/OpenGL/specs/gl/glspec43.core.pdf)
apply the viewport mapping to raster depth, while an explicit fragment depth is
already a window-depth value.

A depth-writing fragment program therefore uses native viewport [0,1]. Its
geometry retains original normalized clipping; `gl_FragCoord.z` is mapped into
the logical near/far pair through the captured private vec2 control
`vispy_fragment_depth_range`. XY and reciprocal W retain their previous route.
Plain define aliases are rewritten as well. The private value occupies the
existing std140 uniform block, adding a vec2 and alignment padding where needed;
its size participates in existing resource limits. Other raster programs use an
identity control because their native viewport already supplies logical depth.
This adds shader/uniform work where the coordinate control is active; no
performance-parity claim accompanies the correctness result.

Actual compiled SPIR-V builtins and EarlyFragmentTests determine the native
raster-versus-explicit-depth choice, after compiler cleanup. This preserves
existing early-test classification/refusals rather than assuming every textual
depth mention executes. Generated line consumers already reconstruct logical
fragment depth/coordinates; their native viewport is [0,1] and their private
coordinate control is identity. Their existing side-effect and early-test guards
remain in force. This packet does not admit arbitrary preprocessor-generated
interfaces, early-test side effects or additional attachment formats.

## Acceptance and remaining work

The baseline has 17 failures and four passes across the initial 21 cases,
including the existing forward explicit-depth clamp defect. The final native
suite has 30 cases: less/greater ordering, clamped/equal ranges, disabled testing,
write masks, original clip rejection, homogeneous coordinates, ordinary and
generated lines, points, indexed instancing, A/B/A queued orientation, direct and
aliased fragment coordinates/depth, and device-loss recovery for both paths.
Expectations use independent colors and analytic window-depth values.

Final affected regressions pass 421 Windows and 407 WSL software cases, plus
36 CPU/package cases and Windows state, shader/corpus and artifact/cache C++
contracts. Both native profiles report nine zero shutdown gauges. All 224
Windows SDK members are unchanged. The Linux leaf recompiles all first-party
units against unchanged retained libraries and remains experimental provenance.
No installed wheel or shipping profile was qualified.

Dither enable, multisample disable on multisample storage, fractional/out-of-range
polygon-offset units, mixed blend-constant domains, additional enum/format and
shader forms, full inventory, independent review and exact installed/observer
qualification remain open. Existing Linux scissor/toolkit, threedee and Tcl
shutdown restrictions are not closed by this packet. Historical source receipts
remain attached to their original product/native identities.
