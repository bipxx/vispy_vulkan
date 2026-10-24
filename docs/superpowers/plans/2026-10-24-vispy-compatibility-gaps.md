# VisPy compatibility gap closure

Status: implementation started, 2026-10-24. This extends the bounded Vulkan
candidate; 13/14 selected host rows are not a percentage of upstream coverage.
Preserve the existing artifacts and their matrix. Changed source needs its own
qualification; never transfer old wheel evidence to a rebuilt artifact.

First packet implemented in source: Tkinter raster presentation and selected
immediate state calls through existing native GLIR. Nine real Tk integration
cases pass on Windows and WSL Linux; three immediate-state pixel/ordering/error
cases also pass on both. Device loss recreates rendering without replacing the
Tk widget. Source/package checks are required before handoff. No new native
wheel, environment or recursive source snapshot was created. Installed-wheel
qualification and the other rows below remain open. See
`docs/vispy-compatibility.md` for API boundaries and the captured Tcl test issue.

| Priority | Work | Acceptance |
| --- | --- | --- |
| 1 | Add a Tkinter backend using Vulkan offscreen rendering and Tk raster presentation. | Real draw/readback/display orientation, resize, embedded and multiple canvases, input, timers and native destruction; no pyopengltk or GL context. Windows first, then Linux where Tk/display exist. |
| 1 | Diagnose Windows napari-threedee startup. | Capture the actual stalled OLE call and establish a cause before changing initialization; successful retries alone do not qualify the row. Reuse the current environment and artifacts. |
| 2 | Inventory upstream examples/visuals against the final renderer. | A per-feature table separates supported, unsupported and untested; fixture counts never substitute for public API coverage. Run affected examples with exact failure output. |
| 2 | Extend shader compatibility in bounded packets. | Dynamic sampler indices, multidimensional arrays and matrix/array attributes need actual compile, native negative controls and GPU outputs. Arbitrary geometry shaders require an explicitly designed lowering path. |
| 3 | Port remaining window backends individually. | GLFW, SDL2, pyglet and wx need a no-GL presentation design plus lifecycle/input/capture tests. EGL/OSMesa expose GL-specific contracts and need explicit replacement semantics. Keep legacy implementations excluded until replacements qualify. |
| 3 | Expand pinned host/dependency coverage. | Actual application workflows, loader/dependency observations and capture/recovery results for each new version/profile; no inference from import success. |
| 4 | Qualify native Linux GPU and macOS Metal. | Requires appropriate hardware/runners. WSL software evidence and a Metal build cannot establish GPU qualification. No Mac is currently available. |
| 4 | Measure representative performance. | Reuse fixed scenes and report frame time/readback/presentation separately. Do not promise pixel/driver parity or input-to-visible latency without suitable evidence. |

Use `AGENTS.md` and `docs/build-hygiene.md`: one shared budget, registered
scratch, reused native artifacts and terminal cleanup. No new native build,
environment or source snapshot for a Python-only backend change. Retain original
BSD and third-party notices alongside the AGPL implementation. Skip cybersecurity
work. Do not publish the draft release or advertise full parity while required
qualification remains incomplete.
