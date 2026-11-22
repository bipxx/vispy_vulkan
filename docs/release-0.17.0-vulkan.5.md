# VisPy Vulkan 0.17.0+vulkan.5

Qualification in progress; publication pending.

This successor closes Wave 5 and scene/visual/geometry/I/O/timer/camera runtime and shader
gaps on top of `0.17.0+vulkan.4`. It changes:

- `CMakeLists.txt`, `cpp/shader/tint_wgsl.cpp`, `cpp/shader/tint_wgsl.hpp`,
  `cpp/shader/glslang_spv.*`, `cpp/shader/line_consumer.*`, `cpp/shader/artifact.hpp`,
  `cpp/runtime.cpp`, `cpp/runtime.hpp`, `cpp/runtime_texture.hpp`, `cpp/bindings/module.cpp`:
  Tint/WGSL shader translation and the `standard-only` Dawn profile, warm pooled mapped upload
  staging (`>= 4 MiB`) for non-host-mapped streamed uploads, sample coverage reset in
  `lower_masked_clear`, and readback-delegated completion via `glFinish(..., "readback")`.
- `src/vispy/`: runtime gap closures across `_dawn_headless.py` (`position` and explicit present),
  `gloo/dawn_parser.py` (`_finishing_for_readback`), `app/canvas.py`, `app/timer.py` (`_run_generation`),
  `app/backends/_qt.py`, `scene/` (`cameras/fly.py`, `canvas.py`, `node.py`, `visuals.py`,
  `widgets/`), `visuals/` (`image_complex.py`, `isocurve.py`, `isoline.py`, `infinite_line.py`,
  `linear_region.py`, `collections/`, `filters/color.py`, `graphs/graph.py`, `line/`, `mesh.py`,
  `polygon.py`, `rectangle.py`, `surface_plot.py`, `transforms/`), `color/colormap.py`,
  `geometry/`, `io/`, `plot/fig.py`, `util/svg/svg.py`, and `testing/_runners.py` (declared in
  `compat/deviations.txt`).
- `pyproject.toml`, `src/vispy/version.py` and `uv.lock`: version `0.17.0+vulkan.5`.
- Qualification and CI tooling: `tools/no_opengl/functional.py` accepts readback-delegated
  completion (`finish_calls >= before`), renewed `compat/linux-ci-reuse.json` and
  `compat/metal-ci-reuse.json`, `compat/qualification-ci.json`, `.github/workflows/`,
  `tests/contract/{curated_contracts.py, test_app_timer_context_api05_contract.py, test_optional_hosts_current_wheel_renewal.py}`,
  and `tests/no_opengl/test_capture_results.py`.

Native binaries are fresh builds for every wheel. Full upstream VisPy parity is not the release
target.

## Install

After publication:

```sh
pip install "vispy==0.17.0+vulkan.5" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

Pin the exact local version.

## Exact assets

All wheels are x86_64.

| Wheel | Bytes | SHA256 | Tier |
| --- | --- | --- | --- |
| `vispy-0.17.0+vulkan.5-cp312-cp312-win_amd64.whl` | 6,834,429 | `be5da8bc3db92aca682110b8f9f0896b5984945b50d1fc1d8269386c6cf0973a` | strict candidate |
| `vispy-0.17.0+vulkan.5-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,579,198 | `d9a23bf22deab3724b1b67de4ca83a5152d4074255d8d6bee2ba70576ffdd253` | strict candidate |
| `vispy-0.17.0+vulkan.5-cp311-cp311-win_amd64.whl` | 6,835,125 | `f0ecad9fa66cebf14a661c43e80edcdfa4dc01c6ec7112dd0afb010f94f41758` | installed-functional |
| `vispy-0.17.0+vulkan.5-cp311-cp311-manylinux_2_39_x86_64.whl` | 10,582,138 | `c9d4919a8902d5a4e1f995f6c682361bc522221fddd12374a69daa52997a218f` | installed-functional |
| `vispy-0.17.0+vulkan.5-cp313-cp313-win_amd64.whl` | 6,834,006 | `8dedab24bb0fee1fb54b35788bead64e314e8ae180de76e650a4fbaf9a67f69f` | installed-functional |
| `vispy-0.17.0+vulkan.5-cp313-cp313-manylinux_2_39_x86_64.whl` | 10,578,888 | `072a6dacea5112134146d431783685e7bca11d070c6e406f6be27968dde48168` | installed-functional |

Product source is `9576e7f3031c51b4674667c5725c5b0a8afde864`.

**Tiers.** *strict candidate* means the two CPython 3.12 wheels are undergoing strict qualification
in `compat/candidates/tk-state-resource-20` and are not admitted or published yet.
*installed-functional* means the CPython 3.11 and 3.13 wheels are built from the same source, pass
44/44 native tests and the same 75 installed GPU cases per platform (Windows RTX 4090; WSL
software Vulkan), but have no strict observer rows, no Tk strict cohort and no scoped admission.
CPython 3.10 and 3.14 wheels are not provided.

## Verified observations and remaining gates

For the two CPython 3.12 wheels, observed so far: all 128 selected Tk criteria on the exact wheels,
and eight mandatory VisPy-level observations (headless and plain QWidget with selected PyQt5,
PyQt6 and PySide6 profiles, on Windows Vulkan and WSL software Vulkan/X11). These are exact selected
no-OpenGL dependency profiles; the install command alone does not provide those Qt profiles.

Independent source, scope, attempt and mandatory-row reviews passed, contributing proof retention
verified 1,721 inputs with scratch removed, and guarded subject validation proved all 128 selected
bindings (`admitted == False`). Change-impact review, qualification-head push, 23-job same-head CI,
final promotion review, scoped admission, protected merge, release publication and public channel
smoke verification remain pending; nothing is admitted or published yet.

## Limits and differences

Tk uses manual pumping and RGB copies to PhotoImage; RGBA capture is separate. The raster path
does not promise native window presentation, vsync, transparent compositing, physical-input
parity or laboratory display latency. Recovery evidence uses explicit device-loss injection.
The readback staging buffer stays allocated per canvas until a differently sized read, a device
reset or the canvas is closed.

The Linux tag is `manylinux_2_39_x86_64`, requiring glibc 2.39 or newer. On Linux only WSL
software Vulkan (`llvmpipe`) is qualified for these wheels; on WSL software Vulkan (`9c5c41b3`),
`test_generated_line_alpha_to_coverage` stays recorded as a known Mesa `llvmpipe` finding from
source testing. Native Wayland, other architectures and additional GPU/driver combinations are
outside this release claim. Metal remains experimental with hosted build/CPU import checks only;
no macOS wheel or Metal graphics qualification is included. No full API or pixel-for-pixel VisPy
parity or broad performance claim is made.

## Licensing and evidence

This implementation is AGPL-3.0-only. The unchanged original VisPy BSD license and third-party
notices remain attached to every wheel and the source. See `LICENSING.md`,
`docs/coverage-checklist.md` and the source-local acceptance records under
`compat/api-acceptance/` (`vulkan5-*`).
