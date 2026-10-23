# vispy_vulkan

A VisPy 0.17.0 compatibility fork using Dawn for Vulkan rendering on Windows and Linux, with a Metal path for macOS.

This is an implementation in progress. Platform support in the source does not establish hardware qualification. The release plan still has open ABI, host, rendering, platform, and performance requirements.

## Build

The repository includes the supplied dependency sources and their immutable checksums. No Git submodule initialization is required. Vendor Git attributes include platform line-ending rules, so use this initial checkout sequence to preserve the pinned bytes.

Windows PowerShell:

```powershell
git clone --no-checkout https://github.com/bipxx/vispy_vulkan.git
Set-Content -LiteralPath vispy_vulkan/.git/info/attributes -Value '* -text -eol -filter -ident' -Encoding ascii
git -C vispy_vulkan config core.autocrlf false
git -C vispy_vulkan config core.longpaths true
git -C vispy_vulkan checkout main
cd vispy_vulkan
```

Linux/macOS shell:

```sh
git clone --no-checkout https://github.com/bipxx/vispy_vulkan.git
printf '%s\n' '* -text -eol -filter -ident' > vispy_vulkan/.git/info/attributes
git -C vispy_vulkan config core.autocrlf false
git -C vispy_vulkan checkout main
cd vispy_vulkan
```

Keep dependency bytes unchanged; verification is part of configuration. Existing checkouts with modified line endings must be repaired from a fresh checkout before building.

For the Windows development setup:

```powershell
uv sync --locked --python 3.12.8 --extra pyqt6 --group dev --group build --group hosts
.venv/Scripts/python.exe cmake/verify_dependencies.py
.venv/Scripts/cmake.exe --preset windows-release
.venv/Scripts/cmake.exe --build --preset windows-release
```

See [build instructions](cmake/README.md) for CPU contracts, wheels, isolated environments, and platform presets. Build products, development environments, local qualification packets, and generated binaries are excluded from this source repository.

## Current qualification

The historical Native63 Windows CPython 3.12 build passes all 47 native CTests.
A fresh wheel passes package, native-origin and license checks, followed by
35 hardware Vulkan cases on an RTX 4090: eight rendering/transfer cases,
eight queued-lifetime cases, seven device-recovery cases and twelve numeric
transfer cases. Separate saved-output audits verify the original complete
images, transfer bytes and counters. Both the native build and the wheel's
binding pass 17 failure-path CPU checks. These results cover this artifact;
broader scientific workflows, performance, other ABIs and platforms remain
release requirements. The wheel includes AGPL and the unchanged original
VisPy BSD license and notices.

Nine additional cases pass on that same wheel, with 15 exact complete-image
comparisons: queued 1D texture revisions and recovery, generated lines in
color-only and depth-attached targets, and Qt recovery during an actual paint.
These bring the bounded hardware case count to 44. The generated-line checks
cover the whole route; forced chunking remains a separate private experiment.

The same Native63 wheel also passes all 17 original scalar and categorical
scientific volume controls. A separate saved-output audit verifies every
complete 96-by-96 RGBA frame against its unchanged OpenGL reference, together
with the host, native-module, process and cleanup records. Performance and the
wider platform matrix remain open.

All 13 original image and label cases also pass on the Native63 wheel. The
independent audit verifies complete 128-by-96 RGBA frames, original host
observations, native origins and cleanup, with zero differing bytes or excluded
pixels. These results retain the original reference images and assertions.

The Native63 large-workload checks also pass: 24 volume cases cover 96 complete
frames and 48 change-discrimination checks. The largest channel difference is
1, within the original limit of 2, with no excluded pixels. Four large-image
cases cover 16 complete 4096-by-4096 frames with exact equality. Separate audits
recompute the original image, analytic, residency and raw counter checks.
These are quality checks; performance, opaque driver memory peaks, scanout and
the remaining platform and host requirements remain open.

Smooth-line coverage remains incomplete. A private native Vulkan experiment
matches the fixed horizontal OpenGL frame but fails the fixed diagonal frame
at one color byte. The exact comparison and references are unchanged, and
the experiment has not been promoted into the renderer.

Earlier bounded Windows CPython 3.12 validation independently admitted the tested clean-consumer lifecycle: compiled SDF, text and clear rendering, uninstall, absence verification, upstream restoration, and complete-array comparison. This does not qualify other Python ABIs or hosts.

The earlier 256-byte partition capture passed 19 cases, 22 complete frames, and 66 attachment comparisons. Broader stencil, primitive identity, residency, and performance requirements remain separate.

Fresh Native58 Windows CPython 3.12 validation passes all 14 original uniform tests and a separate two-frame same-generation reuse case. Independent saved review matched all 16 complete frames (4,096 RGBA bytes) against the new OpenGL reference on Vulkan with an RTX 4090, and verified reuse counters and cleanup. The OpenGL fixture uses disclosed reversible compatibility and widget teardown adapters. Broader uniform coverage, other platforms, hosts, and performance remain open; earlier failed captures remain preserved.

Fresh Native58 WSL Linux CPython 3.12 validation builds all 42 targets and passes all 44 CTests without skips. A separate saved-output review confirms six software Vulkan culling cases on lavapipe: nine complete color/depth/stencil frames (27 attachments) match the analytic expectations and retained OpenGL reference byte-for-byte, with draw accounting and cleanup checked. This covers software Vulkan; native Linux GPU and macOS Metal hardware qualification remain open.

The [20-job CPU contract run](https://github.com/bipxx/vispy_vulkan/actions/runs/39570591551) passed at commit `3b531de`, covering CPython 3.10–3.14 on Windows x86_64, Linux x86_64, macOS ARM64, and macOS x86_64. CPU contracts do not establish GPU hardware admission.

Windows wheels for CPython 3.10–3.14, built from the Native58 runtime plus a Python 3.10 build-helper compatibility fix, pass archive/license checks and clean external consumers on hardware Vulkan. Each consumer verifies compiled SDF, clear/text rendering and notices, then uninstalls and restores hash-verified upstream VisPy. All five wheels include AGPL and the unchanged original BSD license.

Linux x86_64 wheels for CPython 3.10–3.14 pass the same bounded archive and consumer checks using software Vulkan in WSL. These raw `linux_x86_64` wheels have not been qualified for manylinux or other distributions. The source distribution retains every tracked source file, all ten pinned dependency trees, AGPL and the original BSD license; a fresh Linux CPython 3.12 wheel built from that archive passes the isolated rendering and rollback checks. Native Linux hardware, Metal artifacts, broader hosts and scientific/performance coverage remain separate release requirements.

The [implementation plan](docs/superpowers/plans/2026-10-10-vispy-vulkan-next-batch-plan.md) records the wider scope. Its links to local `build/` evidence refer to retained qualification packets that are not distributed in this repository.

Current source adds [portable analytic smooth lines](docs/smooth-lines.md), including fractional widths. A fresh Windows Vulkan build passes line, clipping, perspective, depth and blending checks and renders the previously blocked axes/colorbar scene. Edge coverage approximates OpenGL smoothing; exact driver rasterizer parity is not a practical completion requirement. Refreshed Windows CPython 3.12 wheel validation passes 53 functional cases, including the previously blocked Glue axes and plugin overlays; 42 complete reference frames match exactly. Windows CPython 3.10-3.14 wheels and a fresh Linux CPython 3.12 wheel also pass isolated clear, smooth-line, pipeline-reuse and compiled-text checks. Linux uses WSL software Vulkan; native Linux GPU and Metal remain unverified. The detailed reports below preserve earlier results; the smooth-line notes describe the refreshed coverage.

`SceneCanvas.render()` now allocates empty RGBA8 color renderbuffers through Dawn without uploading a CPU zero image. Fresh Windows CPython 3.12 Vulkan and Linux CPython 3.12 WSL software-Vulkan wheels pass [renderbuffer and marker checks](tools/marker_wheel_smoke.py): zero-initialized reads, clears, resize and queued-clear ownership, plus one-million-marker point and instanced 2D clouds with color updates. Fourteen checked compiler, pipeline, conversion and upload counters remain unchanged during resident draws, and nine live gauges return to zero on shutdown. Saved marker frames match the preceding wheel on each backend. These focused checks cover the allocation fix; the broader suites above and below retain their preceding artifact scopes. No speedup is claimed.

The [installed-wheel mesh/layout regressions](docs/mesh-layout-wheel-regressions.md) retain thirteen original OpenGL scenes. The retained Windows CPython 3.12 wheel run matches twelve complete frames byte-for-byte, including mesh/filter/layout and three text DPI cases. Axes/colorbar failed in that run because smooth-line coverage was unsupported. This is not a complete scene-suite or release qualification.

The [installed-wheel image/label regressions](docs/image-wheel-regressions.md) cover thirteen original workflows, including NaNs, signed labels, offset painting, multiscale revisions and slice changes. All thirteen passed with exact frames and semantic observations in a bounded Windows CPython 3.12 run. Wider platform, host, performance and release qualification remains open.

The [installed-wheel volume regressions](docs/volume-wheel-regressions.md) retain eleven scalar and six categorical napari workflows, including clipping, plane depiction, sparse-label edits and depth ordering against geometry. All seventeen matched the original full frames byte-for-byte in a bounded Windows CPython 3.12 run, with the original comparison rules unchanged. Glue volume updates use the public cache-invalidation protocol described below; the earlier complete Glue run was blocked by smooth lines; the refreshed functional checks above pass.

The [Glue cache-update regressions](docs/glue-wheel-regressions.md) use the pinned host's public cache invalidation before a data update, preserving the original data, geometry and criteria. All five fresh upstream scenes pass, including volume edit. Four candidate scenes match exactly; scatter axes failed in that historical run at unsupported smooth lines; the refreshed installed-wheel functional check passes. The historical failed-reference audit is retained, and active coverage lives under `tests/hosts`.

The [installed-wheel plugin overlay regressions](docs/napari-plugin-wheel-regressions.md) retain all five napari-threedee handle, mouse-event and retirement workflows. All five fresh original cases reproduce the retained frames and state exactly. Candidate retirement matches exactly; four workflows failed in that historical run at the smooth-line refusal; all five refreshed installed-wheel functional checks pass. Exact small test-input artifacts and upstream licenses are included, with no private build-directory dependency.

The [phylib Linux import admission](docs/phylib-import-admission.md) verifies twelve source-pinned CPU imports in WSL and on the Ubuntu CI runner. It imports no VisPy or Qt and grants no GUI or graphics qualification.

## Licensing

This fork’s implementation and modifications are licensed under [AGPL-3.0-only](LICENSE). The original VisPy [BSD 3-Clause license](LICENSE-BSD) remains attached unchanged, and original code retains its copyright and license notices. Bundled dependencies and fonts retain their own licenses. See [licensing details](LICENSING.md) and [third-party notices](third_party/licenses/THIRD-PARTY-NOTICES.txt).
