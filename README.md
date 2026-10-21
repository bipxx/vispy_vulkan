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

Local Windows CPython 3.12 validation has independently admitted the tested clean-consumer lifecycle: compiled SDF, text and clear rendering, uninstall, absence verification, upstream restoration, and complete-array comparison. This does not qualify other Python ABIs or hosts.

The current 256-byte partition capture passed 19 cases, 22 complete frames, and 66 attachment comparisons. Broader stencil, primitive identity, residency, and performance requirements remain separate.

The uniform reference remains unqualified. The latest capture with an explicit reversible upstream-only compatibility adapter failed its pytest gate; failed captures are retained and are not counted as passes.

The [implementation plan](docs/superpowers/plans/2026-10-10-vispy-vulkan-next-batch-plan.md) records the wider scope. Its links to local `build/` evidence refer to retained qualification packets that are not distributed in this repository.

## Licensing

This fork’s implementation and modifications are licensed under [AGPL-3.0-only](LICENSE). The original VisPy [BSD 3-Clause license](LICENSE-BSD) remains attached unchanged, and original code retains its copyright and license notices. Bundled dependencies and fonts retain their own licenses. See [licensing details](LICENSING.md) and [third-party notices](third_party/licenses/THIRD-PARTY-NOTICES.txt).
