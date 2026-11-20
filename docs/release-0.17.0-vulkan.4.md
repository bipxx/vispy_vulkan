# VisPy Vulkan 0.17.0+vulkan.4

Qualification in progress on 2026-11-20; publication pending. Nothing on this page is an admitted
or delivered claim until the gates below complete and this page is updated. The intended release
tag is `v0.17.0-vulkan.4`.

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

After publication:

```sh
pip install "vispy==0.17.0+vulkan.4" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

Pin the exact local version.

## Exact assets

All wheels are x86_64.

| Wheel | Bytes | SHA256 | Tier |
| --- | --- | --- | --- |
| `vispy-0.17.0+vulkan.4-cp312-cp312-win_amd64.whl` | 6,816,781 | `0138bcb58ad9ad10fbfc34656b8a63b90d2679c02a3e47faf9c844736c304773` | strict candidate |
| `vispy-0.17.0+vulkan.4-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,566,229 | `e8a61ae7945c214774fab709d76d2adb9bb2f81ce33a3e2cb3f68031deac16be` | strict candidate |
| `vispy-0.17.0+vulkan.4-cp311-cp311-win_amd64.whl` | 6,817,360 | `096d83f2e49b8398ef1c27a0beecc4a3adab2f4291538dfef725458903f01272` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp311-cp311-manylinux_2_39_x86_64.whl` | 10,569,256 | `8a0afe07c766f5737b2ecb5c0219285ee4c10724699e0b9c0fad99099a624468` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp313-cp313-win_amd64.whl` | 6,816,506 | `b52018c4d0a3f65305b92c12fa7285a0232145ae389bfefba55b3f249cee10af` | installed-functional |
| `vispy-0.17.0+vulkan.4-cp313-cp313-manylinux_2_39_x86_64.whl` | 10,565,990 | `1b8f140d673b8e7cc33f64e208fe738c20e8ff7717cf6e2b346f8d60df7c80f8` | installed-functional |

Product source is `07de4afa3858d98b2ff9db40c0e351bd20d08e6e`.

**Tiers.** *strict candidate* means the CPython 3.12 wheels are the subject of the strict
qualification below; they become scoped-admitted only after the remaining gates pass.
*installed-functional* means the CPython 3.11 and 3.13 wheels are built from the same source, pass
44/44 native tests and the same 75 installed GPU cases per platform (Windows RTX 4090; WSL
software Vulkan), but have no strict observer rows, no Tk strict cohort and no scoped admission.
CPython 3.10 and 3.14 wheels are not provided.

## Verified observations and remaining gates

For the two CPython 3.12 wheels, observed so far: all 128 selected Tk criteria on the exact wheels,
and eight mandatory VisPy-level observations (headless and plain QWidget with selected PyQt5,
PyQt6 and PySide6 profiles, on Windows Vulkan and WSL software Vulkan/X11). These are exact selected
no-OpenGL dependency profiles; the install command alone does not provide those Qt profiles.

Independent source, candidate, failed-attempt and eight-row reviews are approved. The remaining
gates are the change-impact review, the same-head required CI jobs, the final promotion review,
scoped admission, protected source integration and public-channel delivery.

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
