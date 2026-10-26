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

A subsequent local readback fix validates malformed explicit viewport inputs
before consuming queued rendering. Its seven Python ordering tests and 56
state/capture cases on each of Windows Vulkan and WSL software Vulkan pass;
the original function fails the four new actual-queue rejection cases. This
follow-up is source-tested only, not pushed or covered by the prior wheels'
admission. Evidence is retained in `build/runs/readback-validation-114/`,
`build/runs/readback-native-115/` and `build/runs/readback-wsl-116/`.
Renew affected candidate bindings, exact Python wheel/member checks and
installed/CI/review evidence before promoting it; reuse unchanged native
production outputs. Continue breadth through the per-API route map, fixing
supported-workflow defects first and documenting intentional differences.
