# VisPy Vulkan 0.17.0+vulkan.3

Published on 2026-11-18 as the
[GitHub Release](https://github.com/bipxx/vispy_vulkan/releases/tag/v0.17.0-vulkan.3)
`v0.17.0-vulkan.3`. Public-channel delivery checks are recorded in the release asset
`delivery.json` and in the [delivery record](../compat/api-acceptance/vulkan3-public-delivery-v1.json).

This successor delivers the reviewed readback-geometry and state-query fixes, the nine
`vispy.visuals.collections` configurations and the Dawn `jupyter_rfb` backend fixes, and adds
CPython 3.11 and 3.13 wheels. The only source difference from the reviewed Wave 5 source is the
version in `pyproject.toml`, `src/vispy/version.py` and `uv.lock`. Because `pyproject.toml` and
`uv.lock` are native build inputs, the CPython 3.12 native binaries are fresh builds; no C++,
CMake, SDK or toolchain input changed. Full upstream VisPy parity is not the release target.

## Install

```sh
pip install "vispy==0.17.0+vulkan.3" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

Pin the exact local version. The index retains vulkan.1 and vulkan.2 as well as vulkan.3 and uses
SHA256 fragments for each GitHub Release asset.

## Exact assets

All wheels are x86_64. The release tag is `v0.17.0-vulkan.3`.

| Wheel | Bytes | SHA256 | Tier |
| --- | --- | --- | --- |
| `vispy-0.17.0+vulkan.3-cp312-cp312-win_amd64.whl` | 6,816,164 | `e4b9eb92e73ff08d5051a7baec3442e63f6d9f9caa6e69efd507a24c5d9871c6` | scoped-admitted |
| `vispy-0.17.0+vulkan.3-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,565,519 | `fb81c75f12ab99769faa965728ec18b27b890d0b4b8dd0007c65fe1373850b01` | scoped-admitted |
| `vispy-0.17.0+vulkan.3-cp311-cp311-win_amd64.whl` | 6,817,078 | `60590ef7023c88f6e57a15ba3ff455d6fa919a572886e22ebf4198b32305b3b0` | installed-functional |
| `vispy-0.17.0+vulkan.3-cp311-cp311-manylinux_2_39_x86_64.whl` | 10,568,592 | `6f0149d79d91a9365c7f291ac7e8b1d5e78f24167a822b8f2771c69094367c42` | installed-functional |
| `vispy-0.17.0+vulkan.3-cp313-cp313-win_amd64.whl` | 6,815,759 | `7deb265c503d4f979f6ed7f229c83c556023dabca6d7ffb8adc991424802cd87` | installed-functional |
| `vispy-0.17.0+vulkan.3-cp313-cp313-manylinux_2_39_x86_64.whl` | 10,565,277 | `f15e50c91952b5ad5db5ad2b115a2147658aef74001bcba6ac30d185a1559000` | installed-functional |

Product source is `45aee3e262a0dbb62e3db24369f7b289e1914b2e`.

**Tiers.** *scoped-admitted* means the CPython 3.12 wheels are the subject of the strict
qualification and scoped admission below. *installed-functional* means the CPython 3.11 and 3.13 wheels are built from the same
source, pass 44/44 native tests and the same 75 installed GPU cases per platform (Windows RTX 4090;
WSL software Vulkan), and are delivered through the same channel, but have no strict observer
rows, no Tk strict cohort and no scoped admission. CPython 3.10 and 3.14 wheels are not provided.

## Verified observations and release gates

For the two CPython 3.12 wheels: all 128 selected Tk criteria are observed on the exact wheels,
and eight mandatory VisPy-level observations pass: headless and plain QWidget with selected PyQt5,
PyQt6 and PySide6 profiles, on Windows Vulkan and WSL software Vulkan/X11. These are exact
selected no-OpenGL dependency profiles; the install command alone does not provide those Qt
profiles. Ordinary upstream Qt or host installs are not covered by this strict claim.

Independent source/scope/native review of the candidate is approved and bound. All 23
same-head CI jobs pass on qualification head `1a8df91954000a6d891f6cd8fbcb0624a4b66080`, the independent
final promotion review is approved, and the 128 criteria and eight mandatory rows are
scope-admitted for the two CPython 3.12 wheels. The source is integrated by protected merge
`98fb17ee2c2b19f47f032c22a901ffc544ee1998`. The CPython 3.11 and 3.13 wheels are not part of
that admission. Scoped admission is a finite milestone, not full API parity.

## Limits and differences

Tk uses manual pumping and RGB copies to PhotoImage; RGBA capture is separate. The raster path
does not promise native window presentation, vsync, transparent compositing, physical-input
parity or laboratory display latency. Recovery evidence uses explicit device-loss injection.

Qt uses the selected plain-QWidget readback path. Host application qualifications from earlier
artifacts do not transfer to these wheels. Optional napari, Glue, napari-threedee and other host
work remains separately scoped.

The Linux tag is `manylinux_2_39_x86_64`, requiring glibc 2.39 or newer. On Linux only WSL
software Vulkan is qualified for these wheels; the physical NVIDIA Linux evidence recorded for
earlier wheels is not transferred. Native Wayland, other architectures and additional GPU/driver
combinations are outside this release claim. Metal remains experimental with hosted build/CPU
import checks only; no macOS wheel or Metal graphics qualification is included. No full API or
pixel-for-pixel VisPy parity or broad performance claim is made.

## Known Windows startup stall

A rare early-startup stall remains documented under D33; its cause is unresolved. Recurrence is
release-blocking. Preserve a recurrence with the external watcher:

```text
python tools/pool_watch_external.py --output <events.jsonl> -- <command>
```

See `docs/threedee-startup-diagnosis.md` for the retained diagnosis.

## Licensing and evidence

This implementation is AGPL-3.0-only. The unchanged original VisPy BSD license and third-party
notices remain attached to every wheel and the source. See `LICENSING.md`,
`docs/coverage-checklist.md` and the source-local acceptance records under
`compat/api-acceptance/` (`vulkan3-*`). Finite admission does not complete the 142 broader
original compatibility obligations.

## Public channel verification — 2026-11-18

All six wheels were installed from the public index with the command above, each in a fresh
environment, and compared with the released files: 537 installed members equal the exact wheel
and there are no source overrides.

| ABI | Windows (RTX 4090) | Linux (WSL, glibc 2.39) |
| --- | --- | --- |
| CPython 3.11 | exact 64×64 Vulkan clear/readback (3.11.11) | native import (3.11.14) |
| CPython 3.12 | exact 64×64 Vulkan clear/readback (3.12.8) | native import (3.12.13) |
| CPython 3.13 | exact 64×64 Vulkan clear/readback (3.13.8) | native import (3.13.8) |

The Linux delivery check does not render; the 75 installed GPU cases per wheel on WSL software
Vulkan are the separate installed-functional evidence. The index now lists ten hash-pinned links
and keeps the four vulkan.1 and vulkan.2 links unchanged. See the
[delivery record](../compat/api-acceptance/vulkan3-public-delivery-v1.json) for asset ids, hashes and limits.
