# Practical VisPy compatibility for the next release

The release targets familiar VisPy workflows over Vulkan, with useful
improvements and documented differences. It does not promise full upstream
parity. Qualification below applies only to the exact selected artifacts and profiles.

## Compatibility baseline

Some parity is a requirement: existing VisPy code using a claimed workflow
should keep working with familiar inputs and observable behavior, except for
explicitly documented and tested differences. An improvement does not by itself
justify breaking that baseline. Full API, backend and pixel-for-pixel parity
across upstream VisPy is not required. Assess progress against this supported
baseline and release readiness, rather than a percentage of all upstream APIs.

Preserve public call signatures and ordinary array, resource, event and rendering
semantics for each claimed workflow. Start with existing VisPy programs and
upstream-derived test bodies, plus independently expected pixels/counters.
Changed behavior is acceptable when intentional, explained, tested and supplied
with migration guidance where callers must change. An accidental regression,
missing error, stale state or resource leak is a defect within supported scope.

Use the existing candidate's finite 15-feature scope as the first milestone;
retain all its ordinary, mutation, failure and recovery criteria on both Windows
GPU/Tk 8.6 and WSL software Vulkan/Tk 9 profiles. Shared composite runs may prove
several criteria without repeating the same workload per API key. WSL software
results do not claim native Linux GPU support. Metal remains experimental;
its current build/installed CPU checks do not establish graphics qualification.

| Feature key | Bounded behavior to verify |
| --- | --- |
| `tk.backend.raster` | Raster Tk standalone and supplied-parent targets under manual pumping. |
| `tk.application.manual` | Manual event progress and quit preserving the supplied host interpreter. |
| `tk.canvas.basic` | One embedded and one standalone canvas, actual configured extent, RGB presentation and close order. |
| `tk.context.current` | Current-target ordering and GLIR command delivery between two Tk canvases. |
| `tk.context.shared` | Shared Program/Texture/VertexBuffer resources survive first-consumer close. |
| `tk.canvas.recovery` | Same live widget and resources render blue after explicit native device-loss injection. |
| `tk.timer.once` | One public Timer callback uploads green pixels and stops its own generation. |
| `tk.gl.flush` | Raw glFlush submits prior clear work without completion/presentation. |
| `tk.wrappers.submission` | Ordered clear/flush/finish with known RGBA pixels and independent submission counters. |
| `tk.wrappers.raster` | Viewport and disabled blend/depth/scissor state for a full-screen textured triangle, then explicit finish. |
| `tk.readback.rgba` | Full actual client target RGBA8 readback equals independent red/green/blue values. |
| `tk.object.delete` | Explicit Program/Texture/VertexBuffer deletion and queued retirement on the surviving context. |
| `tk.buffer.triangle` | Three float32 vec2 vertices describe an oversized full-screen triangle. |
| `tk.texture.rgba8` | One uint8 RGBA texel updates red/green/blue and remains usable across consumer close and device loss. |
| `tk.program.texture` | One vec2 vertex attribute and one sampler2D render a full-screen textured triangle. |

The candidate's explicit exclusions remain authoritative; these are deliberately
narrow behaviors, not complete coverage of every method or value in those APIs.
Rendering/scene improvements outside this milestone can ship only with their
own stated support limits and relevant regression/installed checks.

## Differences and deferred breadth

Tk presentation currently copies RGB pixels through CPU memory to a PhotoImage;
RGBA readback is separate. This mode does not promise native Vulkan window
presentation, vsync or transparent window compositing. Device-loss acceptance
uses explicit injection/recreation; it is not proof of physical driver removal.
Manual pumping is the selected application scope, not a blanket guarantee for
every external loop. These differences must stay visible in release notes.

Other upstream APIs, shader forms, backends, host integrations and hardware
profiles remain tracked backlog unless separately included in the release's
claims. Keep their failed/unavailable evidence and the original inventory.
Do not mark the 142 parent obligations complete because a subset passes.
The historical 14-host matrix remains a separate broader qualification claim;
this proposal does not certify every host or remove a failure from that matrix.

## Release exit and current gaps

Require independently reviewed implementation and finite scope, admitted or
explicitly reviewed matching native production, exact installed member/license
checks, complete selected workflows and their recovery/control/shutdown proofs,
current required CI, and promotion evidence for the claims made. AGPL and
original third-party licenses remain attached. No-OpenGL claims retain their
actual observation gates; changing the parity target does not relax them.

The existing selection still requests all 120 criteria. None becomes proved
because of this scope clarification. Preserve that selection while completing
the first milestone; a later scope change must explicitly update reviewed
selection and dependent evidence rather than filter failures out of a report.

Current checkpoint (2026-10-26): PR #14 merged as
`b9599ca88062103fd57b2d37a24c24a268603011`; its complete tree matches the
qualified implementation head `c2499093d5ee9b2653e6db15078de65ee14f0b82`.
The exact Windows and WSL wheels passed all 120 selected criteria, independent
promotion review and all 23 required CI jobs. The local reconstruction/evidence
entry point is `build/runs/final-admission-112/milestone-handoff.md`.
This closes the bounded first milestone, not the 142 parent obligations or the
broader host matrix. Full upstream parity remains outside the release exit.

The readback follow-up is merged in PR #15 as
`c80de037a44377d7e617f57c17d32edbe78e7df1`, with the exact complete tree of
qualified head `98694c6b7c9ed9befbfaf73e2f377d1516fca4c0`. Invalid explicit
viewport shapes and integer-conversion failures are rejected before finishing
queued rendering; default viewport resolution still finishes first. Seven
ordering tests and 56 state/capture cases per Windows/WSL profile pass, including
the four actual-queue cases that fail on the original function.

Runs117-123 established Python-only archive renewal, exact native/archive joins
and renewed source/scope approvals. Runs124-129 completed the full installed
observation/control/profile protocols on the successor Windows and WSL wheels,
all 120 selected criteria, all 23 current-head required CI jobs, independent
promotion review and strict scoped admission. The exact wheel hashes are
`444402459f79465fb1cb42b0dea55fb7e66ce73c22df9e96017f437786ce0d56`
(Windows) and `bd89a9944c71fb3b40260a3197c8f436e7a29021e485ff5f4a561fed907f844a`
(Linux). Use `build/runs/readback-promotion-129/milestone-handoff.md` for the
local reconstruction/evidence entry point. Native outputs, metadata and original
licenses remain unchanged. Failed attempts are preserved and scratch is cleaned.
The Mac CPU/build checks passed; Metal graphics remain experimental.

PR #16 merged the source-only stencil packet as
`2ed257abc45f775ae490afe432ec5374f2f087a8`. Its 196 cases per Windows hardware
Vulkan and WSL software Vulkan profile check eight separate-face operations,
finite boundaries/write masks and shared/split routes, with active operation
and branch controls. A further reviewed source packet adds 97 direct both-face
operation cases per profile, including invalid-input recovery and reached
single-face controls that distinguish masked inversion and wrapping. See the limits in
[immediate-state compatibility](immediate-state-compatibility.md).
This extends source regression evidence without changing the renderer, selected
120-criterion admission or original 142 parent obligations. Continue broader
work through the per-API route map, preserving documented differences and
distinguishing source-tested behavior from newly admitted artifact claims.

The cropped byte/float capture follow-up separately proves eight criteria on
the exact Windows and WSL wheels under the unchanged strict subject validator.
Source/scope/native-reuse and installed-evidence reviews, all 23 current-head
CI jobs, final promotion and strict separate eight-criterion admission passed.
PR #17 merged as `48df4b47b5ab5d4428e1207d0597363257d03f7a`, with the exact tested tree of
`27242b51f76eae5d96cc7163ee1af105f46f22ba`. This is not a combined current
128-criterion admission. A separate PanZoom source packet now verifies literal
camera rectangles, rendered landmark patches and actual Tk presentation points
through drag, resize, focus-loss cancellation and gesture recovery on both
profiles. Independent review162 approved the finite source evidence and its
reached disabled-pan/reversed-vertical-pan controls. It does not admit an
installed camera workflow, whole-image parity or physical/mixed-DPI input.
A companion source test, independently reviewed in165, verifies cursor-anchored
wheel zoom and its inverse with a custom sensitivity. Expected rectangles and
landmark/presentation coordinates pass on both profiles; reached center-only
and reversed-zoom controls fail. Default scroll-rate and installed camera
qualification remain separate.

The Turntable companion also passes on both profiles and has independent
review169. Its explicit orthographic, +Z-up quarter-turn checks literal pose,
rendered landmark patches, actual Tk points, cancellation and restoration.
Reached missing-rotation/reversed-yaw controls fail; this source result does
not admit perspective, arbitrary poses or an installed 3D camera workflow.
