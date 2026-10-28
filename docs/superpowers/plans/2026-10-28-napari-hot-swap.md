# napari hot-swap plan

Active work, including these workstreams, is tracked in the
[consolidated plan](2026-10-28-consolidated-plan.md). This document records the
hot-swap workstreams' origin and progress.

## Context

Goal: a user installs **stock napari from PyPI** and replaces only the `vispy`
distribution with this project's `vispy-0.17.0+vulkan.N` wheel. napari then runs
on Dawn/Vulkan with practical parity, with no patched napari, qtpy or Qt wheels.
napari 0.9.2 requires `vispy>=0.17.0,<0.18`, which `0.17.0+vulkan.N` satisfies.

Where things stand on 2026-10-28:

- **Qualified napari rows are not hot swaps.** They use patched napari and qtpy
  (`compat/host-patches/`) and PyQt6 profiles with Qt's OpenGL modules removed
  (`+vispynogl.1`). That configuration is the **strict no-OpenGL profile**.
- **A functional stock swap works.** In the repo's dev environment and in
  `compat/host-environments/napari-threedee-candidate-windows-cpython312-pyqt6.txt`
  ("only VisPy is replaced"), stock napari, qtpy and PyQt6 render on the port.
  On 2026-10-21, 17 napari workflows matched the original frames byte-for-byte
  (`docs/volume-wheel-regressions.md`). That used an older wheel; the current
  admitted wheel (`444402…`, Windows cp312) has no napari row.
- **Stock napari's only hard dependency on OpenGL** is the module-level
  `from OpenGL.error import GLError` in `napari/_vispy/canvas.py:15`. PyOpenGL
  therefore stays installed, and importing it loads the platform GL library.
  Stock qtpy imports Qt's OpenGL modules, and stock Qt wheels ship them. **A
  stock host stack cannot pass the strict gates**, whatever vispy does
  (`tools/no_opengl/policy.py`; no host exemption).

## Profiles

| Profile | Hosts | Claim |
| --- | --- | --- |
| Strict no-OpenGL (existing, unchanged) | patched napari and qtpy, `+vispynogl` Qt | No GL import, load or execution in the process, and no install or link requirement |
| **Hot swap (new)** | stock PyPI napari, qtpy, PyQt6 or PySide6, PyOpenGL | All rendering goes through Dawn. vispy and `vispy._dawn` never import, load or resolve GL. **No GL context is created or made current, and no GL draw runs** in the process. GL loads by host packages are recorded and attributed to the module and stack that caused them, not claimed absent. |

The strict rows and policy stay unchanged. The hot-swap profile is a separate,
explicitly narrower claim.

## Workstreams

Each workstream is delivered in bounded source packets that follow the
established loop: failing test or control first, the fix, Windows and WSL
evidence, independent review, then a PR merged through the 11 required checks.

| ID | Gap | Work | Exit criterion |
| --- | --- | --- | --- |
| W0 | PR #24 (drag-race fix) | Merge when CI passes and verify the tree | Merged tree matches the tested tree |
| W1 | `GL_EXTENSIONS` always reports `texture_float` | Report `GL_ARB_texture_float` only when `float32_filterable` is available (`src/vispy/gloo/dawn_parser.py`), so napari's own fallback (`texture_format=None`) applies on GPUs without filterable float32 | CPU tests cover both device answers; a napari float image renders with the fallback forced |
| W2 | No hot-swap baseline with the current wheel | Install the stock lock with only `vispy` replaced by the current wheel. Run the probe's napari and threedee scenarios and the napari parity suites (`tests/hosts/test_napari_*parity*.py`) | Every case passes or has a recorded, triaged cause |
| W3 | No hot-swap gate profile | Add a hot-swap mode to the audit (`tools/audit_no_opengl.py`, `tools/no_opengl/`) that records host GL events with attribution and fails on renderer-attributed GL activity or on any GL context, make-current or draw call. Add controls proving it detects renderer GL use. Strict mode is unchanged. | Controls are reached; the stock baseline passes the hot-swap gates |
| W4 | napari layers and overlays untested on the port | Add OpenGL-reference parity fixtures, using the existing pattern in `tools/fixture_napari*.py` with `tools/oracle_napari_*_capture.py`, for: default cyclic labels (r8/r16), Points (all symbols, large counts), Shapes, Vectors, Tracks, Surface (shading and wireframe), the scale bar, axes and colorbar overlays, the histogram canvas, and sized export | Each family matches its OpenGL reference within the suite's tolerance, or has a documented, tested difference |
| W5 | Known napari-relevant defects from the scientific coverage (`docs/superpowers/plans/scientific-fixture-coverage.md`) | M02 all-symbol markers (42 px difference), M06 million-marker baseline, M08/M09 wide and agg lines, B03 opacity mutation, H01 layer removal and screenshot, V04/V07/V09 volume controls, plane widget, large volumes | Each fixed and admitted, or recorded as an intentional difference with a test |
| W6 | Bindings and Python versions | Hot-swap rows for PyQt6 and PySide6 on cp311–cp314 (napari needs at least 3.11), with Windows wheels for each ABI | One row per cell passes W2 and W3 |
| W7 | Platforms | WSL lavapipe hot-swap rows. Native Linux GPU and macOS Metal need hardware not on this machine; they stay recorded as unqualified | WSL rows pass; the other platforms' status is documented |
| W8 | Performance (PERF-1 unmeasured) | Measure napari interaction frame time and large image and volume loads against upstream OpenGL. In the hot-swap profile, native swapchain presentation is allowed even where the driver loads `opengl32`, so evaluate it against the current QImage copy | A measured report, with the presentation choice decided from the data |
| W9 | Windows napari-threedee startup stall | Arm live native-stack and WCT capture on every napari launch in W2 and W6 | Root cause from a captured recurrence, or the row's status stays as decided |
| W10 | Single-pump drag race in `tools/fixture_napari_threedee.py` | Apply `settled_moves()` and regenerate its pinned OpenGL reference | Parity test passes against the regenerated reference |
| W11 | Distribution channel (**needs approval before publishing**) | Release wheels (manylinux for Linux), a GitHub Release, and a PEP 503 index, so that `pip install napari "vispy==0.17.0+vulkan.N" --extra-index-url …` works. Write the install docs | A clean venv installs and the W2 smoke test passes from the published channel |
| W12 | Strict profile with stock hosts (**needs approval for upstream PRs**) | Propose upstream changes: a lazy or optional `GLError` import in napari's `canvas.py`, and lazy `QtOpenGL` imports in qtpy | Upstream releases contain the changes; strict rows can then use stock hosts |

Out of scope, recorded rather than claimed: the 142 inventory parents that
napari does not use, non-Qt vispy backends, PySide2 (refused by the port),
native Wayland (refused by the Qt backend), and physical-input and DPI hardware
rows.

## Order

1. W0 and W1, which are small and local.
2. W2, the baseline that sizes everything after it.
3. W3, then W4 and W5 in families ranked by napari usage: labels, Points, Shapes,
   Vectors and Tracks, Surface, overlays.
4. W6 and W7 matrix expansion, and W8 performance.
5. W11 and W12 after explicit approval.
6. W9 and W10 alongside.

## Progress

**W0 done.** PR #24 merged as `63f76ec` with all 11 required checks passing and
no admin override. The merged tree equals the tested tree.

**W2 baseline, Windows cp312 PyQt6, RTX 4090, current wheel `444402…`** (run
`napari-hotswap-baseline-207`). The hot-swap environment held 116
distributions, and only `vispy` and the napari-threedee plugin wheel came from
outside the index. napari 0.9.2, QtPy 2.4.3, PyQt6 6.11.0 with Qt 6.11.2, and
PyOpenGL 3.1.10 were stock PyPI.

| Check | Result |
| --- | --- |
| Probe `napari` lifecycle: image, overlay and pan, labels edits, 3D volume and export, device loss, close | **pass** |
| Probe `threedee` lifecycle: registration, Qt drag, device recovery, retirement, close | **pass** |
| Installed-wheel volume suite, runner-owned stock environment (119 hashed requirements) | **17/17 pass**, including 6 exact napari categorical cases |
| In-process scientific (17) and volume (6) suites with stock napari | **23/23 pass** |
| Overlay plugin suite | retirement exact. The other 4 cases differ **only outside uniform regions of the reference** (at most 29 levels): the manipulator's smooth lines are an analytic approximation of NVIDIA's driver line smoothing |
| threedee, initialized and render-plane suites | 11 blocked by **unadmitted OpenGL references**, from oracle-side fixture defects (W10). 6 blocked by **napari-threedee 0.0.29 calling `np.row_stack`**, which numpy 2.5 removed. That is a plugin bug unrelated to vispy; those suites pair with numpy 2.4.6. 1 (`initialized` retirement) ran in the dev interpreter, which has no plugin, because that suite ignores `VISPY_PLUGIN_CANDIDATE_PYTHON`. |

Live stall capture was armed for every napari launch and never fired.

A lesson for later packets: create scratch environments with
`UV_LINK_MODE=copy`. The default hardlinks were refused by cleanup and had to be
materialized first (25,711 files).

Decisions (user, 2026-10-28):
1. **Smooth lines:** small differences are acceptable if the frame stays
   semantically consistent. This is implemented as the fixed criterion in
   [smooth-lines.md](../../smooth-lines.md#parity-criterion-for-smooth-line-frames).
   Run `napari-smooth-line-208` (in-process) and `napari-smooth-line-pinned-211`
   (installed wheel, helper pinned) on the hot-swap stack: the overlay suite passes
   7/7 and the installed-wheel plugin suite passes 5/5 (it was 1/5 on
   2026-10-21).
2. **W11:** a GitHub Release plus a PEP 503 index. Prepare everything and ask
   again before publishing.
3. **W12:** draft the upstream napari and qtpy changes locally. Nothing is
   posted without approval.

**W9: live recurrence captured and analysed 2026-10-28** (runs
`napari-startup-stall-recurrence-209` and `com-stall-harness-213`; details in
[the diagnosis](../../threedee-startup-diagnosis.md)). The hung process had lost
its default thread pool. Something closed the pool's worker-factory handle
early in startup, no later than about a second after the process's first COM
RPC. COM work then stopped
running, and the UI Automation activation in `window.show()` waited forever. The
pending-activation hypothesis is refuted, while CPython's WMI timeout path is not
excluded. The closer is not identified: 1,995 controlled trials able to detect a
loss showed none. They ran sequentially, with the window shown, 8-way concurrent
with kernel handle tracing, and under a debugger. Next: instrument and wait.

## Verification

- CPU contract tests for every new tool, policy and parser change.
- For every packet: Windows RTX 4090 and WSL lavapipe runs, reached controls,
  actual exit and wait receipts, and build-hygiene registration, retention and
  cleanup. Only `build/work/<run>` is used for scratch.
- Hot-swap rows: the full napari probe scenario plus the parity suites, in a
  stock-lock environment where the only non-PyPI distribution is `vispy`
  (verified from the hash lock and installed RECORD files).
- Independent review before each publication, and PRs merged only through the
  required checks.
