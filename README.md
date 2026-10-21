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

Earlier bounded Windows CPython 3.12 validation independently admitted the tested clean-consumer lifecycle: compiled SDF, text and clear rendering, uninstall, absence verification, upstream restoration, and complete-array comparison. This does not qualify other Python ABIs or hosts.

The earlier 256-byte partition capture passed 19 cases, 22 complete frames, and 66 attachment comparisons. Broader stencil, primitive identity, residency, and performance requirements remain separate.

Fresh Native58 Windows CPython 3.12 validation passes all 14 original uniform tests and a separate two-frame same-generation reuse case. Independent saved review matched all 16 complete frames (4,096 RGBA bytes) against the new OpenGL reference on Vulkan with an RTX 4090, and verified reuse counters and cleanup. The OpenGL fixture uses disclosed reversible compatibility and widget teardown adapters. Broader uniform coverage, other platforms, hosts, and performance remain open; earlier failed captures remain preserved.

Fresh Native58 WSL Linux CPython 3.12 validation builds all 42 targets and passes all 44 CTests without skips. A separate saved-output review confirms six software Vulkan culling cases on lavapipe: nine complete color/depth/stencil frames (27 attachments) match the analytic expectations and retained OpenGL reference byte-for-byte, with draw accounting and cleanup checked. This covers software Vulkan; native Linux GPU and macOS Metal hardware qualification remain open.

The [20-job CPU contract run](https://github.com/bipxx/vispy_vulkan/actions/runs/39570591551) passed at commit `3b531de`, covering CPython 3.10–3.14 on Windows x86_64, Linux x86_64, macOS ARM64, and macOS x86_64. CPU contracts do not establish GPU hardware admission.

Windows wheels for CPython 3.10–3.14, built from the Native58 runtime plus a Python 3.10 build-helper compatibility fix, pass archive/license checks and clean external consumers on hardware Vulkan. Each consumer verifies compiled SDF, clear/text rendering and notices, then uninstalls and restores hash-verified upstream VisPy. All five wheels include AGPL and the unchanged original BSD license.

Linux x86_64 wheels for CPython 3.10–3.14 pass the same bounded archive and consumer checks using software Vulkan in WSL. These raw `linux_x86_64` wheels have not been qualified for manylinux or other distributions. The source distribution retains every tracked source file, all ten pinned dependency trees, AGPL and the original BSD license; a fresh Linux CPython 3.12 wheel built from that archive passes the isolated rendering and rollback checks. Native Linux hardware, Metal artifacts, broader hosts and scientific/performance coverage remain separate release requirements.

The [implementation plan](docs/superpowers/plans/2026-10-10-vispy-vulkan-next-batch-plan.md) records the wider scope. Its links to local `build/` evidence refer to retained qualification packets that are not distributed in this repository.

The [installed-wheel mesh/layout regressions](docs/mesh-layout-wheel-regressions.md) retain thirteen required original OpenGL scenes. A bounded Windows CPython 3.12 run matches twelve complete frames byte-for-byte, including mesh/filter/layout and three text DPI cases. Axes/colorbar remains a required failure because smooth-line coverage is unsupported. This is not a complete scene-suite or release qualification.

The [installed-wheel image/label regressions](docs/image-wheel-regressions.md) cover thirteen original workflows, including NaNs, signed labels, offset painting, multiscale revisions and slice changes. All thirteen passed with exact frames and semantic observations in a bounded Windows CPython 3.12 run. Wider platform, host, performance and release qualification remains open.

## Licensing

This fork’s implementation and modifications are licensed under [AGPL-3.0-only](LICENSE). The original VisPy [BSD 3-Clause license](LICENSE-BSD) remains attached unchanged, and original code retains its copyright and license notices. Bundled dependencies and fonts retain their own licenses. See [licensing details](LICENSING.md) and [third-party notices](third_party/licenses/THIRD-PARTY-NOTICES.txt).
