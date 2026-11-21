# VisPy Vulkan 0.17.0+vulkan.4

Published on 2026-11-20 as [`v0.17.0-vulkan.4`](https://github.com/bipxx/vispy_vulkan/releases/tag/v0.17.0-vulkan.4).

This successor speeds up the CPU readback used to show frames in Qt and Tk windows
when native window presentation is not used (`qt_presentation='readback'`, Tk raster). It changes:

- `src/vispy/app/backends/_qt.py`: the Qt readback path builds its `QImage` on the readback array
  instead of copying each frame twice; `grabFramebuffer()` still returns an independent copy.
- `cpp/runtime.cpp`, `cpp/runtime.hpp`, `cpp/bindings/module.cpp`: `read_pixels` reuses a
  per-canvas staging buffer and no longer zero-fills its output before overwriting it.
- `compat/software-vulkan-build.json`: the pinned Mesa source now downloads through Launchpad's
  permanent `+files` link; the file, its size and its sha256 are unchanged.
- The version in `pyproject.toml`, `src/vispy/version.py` and `uv.lock`.

Native binaries are fresh builds for every wheel. Full upstream VisPy parity is not the release
target.

## Performance

Measured on one Windows RTX 4090 machine, single runs (medians of 35-40 frames), so treat the
figures as approximate:

| | 1920x1080 | 3840x1900 |
| --- | --- | --- |
| `read_pixels`, vulkan.3 -> vulkan.4 native module | 4.54 -> 2.69 ms | 14.49 -> 9.53 ms |
| Qt readback repaint, vulkan.3 -> vulkan.4 | 9.69 -> 6.40 ms | 32.76 -> 27.72 ms |

Native window presentation is unaffected. Tk raster presentation benefits only from the faster
readback; most of its per-frame cost is Tk's own image handling.

## Install

```sh
pip install "vispy==0.17.0+vulkan.4" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

Pin the exact local version.

## Exact assets

All wheels are x86_64.

| Wheel | Bytes | SHA256 | Tier |
| --- | --- | --- | --- |
| `vispy-0.17.0+vulkan.4-cp312-cp312-win_amd64.whl` | 6,816,781 | `0138bcb58ad9ad10fbfc34656b8a63b90d2679c02a3e47faf9c844736c304773` | scoped-admitted |
| `vispy-0.17.0+vulkan.4-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,566,229 | `e8a61ae7945c214774fab709d76d2adb9bb2f81ce33a3e2cb3f68031deac16be` | scoped-admitted |
| `vispy-0.17.0+vulkan.4-cp311-cp311-win_amd64.whl` | 6,817,360 | `096d83f2e49b8398ef1c27a0beecc4a3adab2f4291538dfef725458903f01272` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp311-cp311-manylinux_2_39_x86_64.whl` | 10,569,256 | `8a0afe07c766f5737b2ecb5c0219285ee4c10724699e0b9c0fad99099a624468` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp313-cp313-win_amd64.whl` | 6,816,506 | `b52018c4d0a3f65305b92c12fa7285a0232145ae389bfefba55b3f249cee10af` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp313-cp313-manylinux_2_39_x86_64.whl` | 10,565,990 | `1b8f140d673b8e7cc33f64e208fe738c20e8ff7717cf6e2b346f8d60df7c80f8` | installed-functional |

Product source is `07de4afa3858d98b2ff9db40c0e351bd20d08e6e`.

**Tiers.** *scoped-admitted* covers the strict qualification below for the two
CPython 3.12 wheels.
*installed-functional* means the CPython 3.11 and 3.13 wheels are built from the same source, pass
44/44 native tests and the same 75 installed GPU cases per platform (Windows RTX 4090; WSL
software Vulkan), but have no strict observer rows, no Tk strict cohort and no scoped admission.
CPython 3.10 and 3.14 wheels are not provided.

## Verified observations and release gates

For the two CPython 3.12 wheels, the scoped admission covers all 128 selected Tk criteria on the exact wheels,
and eight mandatory VisPy-level observations (headless and plain QWidget with selected PyQt5,
PyQt6 and PySide6 profiles, on Windows Vulkan and WSL software Vulkan/X11). These are exact selected
no-OpenGL dependency profiles; the install command alone does not provide those Qt profiles.

The independent reviews passed, and all 23 same-head CI jobs passed on qualification head
`15cb085e0c12b57601792bf9e7f4f4c2319ef02d`. Protected merge of PR #96 integrated the exact qualified tree
at `9947e1a00816c709abd851773f5232bbbb8aa8db`. The public channel results are recorded in the release asset [`delivery.json`](https://github.com/bipxx/vispy_vulkan/releases/download/v0.17.0-vulkan.4/delivery.json).

## Limits and differences

Tk uses manual pumping and RGB copies to PhotoImage; RGBA capture is separate. The raster path
does not promise native window presentation, vsync, transparent compositing, physical-input
parity or laboratory display latency. Recovery evidence uses explicit device-loss injection.
The readback staging buffer stays allocated per canvas (about 33 MB at 3840x2160) until a
differently sized read, a device reset or the canvas is closed.

The Linux tag is `manylinux_2_39_x86_64`, requiring glibc 2.39 or newer. On Linux only WSL
software Vulkan is qualified for these wheels. Native Wayland, other architectures and additional
GPU/driver combinations are outside this release claim. Metal remains experimental with hosted
build/CPU import checks only; no macOS wheel or Metal graphics qualification is included. No full
API or pixel-for-pixel VisPy parity or broad performance claim is made.

## Licensing and evidence

This implementation is AGPL-3.0-only. The unchanged original VisPy BSD license and third-party
notices remain attached to every wheel and the source. See `LICENSING.md`,
`docs/coverage-checklist.md` and the source-local acceptance records under
`compat/api-acceptance/` (`vulkan4-*`).

## Public channel verification — 2026-11-20

The public index served all six hash-pinned wheels and preserved the ten earlier links.
Each public install resolved to the pinned GitHub release asset and matched all 537
runtime package members, with zero source overrides.

| CPython | Windows x86_64 | Linux x86_64 wheel |
| --- | --- | --- |
| 3.11 | Exact 64×64 headless Vulkan clear and readback | Public install and member verification in a cross-platform pip target |
| 3.12 | Exact 64×64 headless Vulkan clear and readback | Public install and member verification in a cross-platform pip target |
| 3.13 | Exact 64×64 headless Vulkan clear and readback | Public install and member verification in a cross-platform pip target |

The Windows renders used the RTX 4090 and returned ten zero shutdown gauges per run.
WSL was inaccessible during channel verification. The Linux channel checks verified
wheel selection, archive hashes and installed bytes. Linux native import and rendering
remain covered by the separate pre-publication installed-functional evidence.
Temporary installs were removed. See the [delivery record](../compat/api-acceptance/vulkan4-public-delivery-v1.json).

A November 20 follow-up fetched the CPython 3.12 Linux x86_64 wheel via the public
index. Its SHA-256, `e8a61ae7945c214774fab709d76d2adb9bb2f81ce33a3e2cb3f68031deac16be`,
matched the index pin and release `delivery.json`. The WSL launcher returned
`Wsl/E_ACCESSDENIED` before Ubuntu started. The native public install, version import
and `dawn_headless` software Vulkan pixel check remain pending.

A November 21 WSL Ubuntu follow-up (`vulkan4-linux-smoke-1150`) completed that
CPython 3.12 Linux public-channel smoke: downloading `vispy-0.17.0+vulkan.4-cp312-cp312-manylinux_2_39_x86_64.whl`
(SHA-256 `e8a61ae7945c214774fab709d76d2adb9bb2f81ce33a3e2cb3f68031deac16be`) into a clean
CPython 3.12 environment verified all `537/537` package members with zero source overrides,
imported `vispy.__version__ == "0.17.0+vulkan.4"`, rendered an exact 64×64 RGBA `[17, 33, 65, 255]`
clear via `dawn_headless` on `llvmpipe (LLVM 18.1.3, 256 bits)` using pinned Mesa `9c5c41b3`
with 10/10 zero Dawn shutdown gauges, and cleaned WSL managed scratch (`PASS_APPLY`,
`total_managed_bytes: 0`). Existing admission and release-tier boundaries remain unchanged.
