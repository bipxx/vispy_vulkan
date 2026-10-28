# Installed-wheel napari-threedee overlay workflows

The required suite contains handles, selection, translation, a missed click and
callback retirement. It uses the existing unchanged registered layer-manipulator
fixture, real Qt mouse events, fixed data/cameras and full 256x192 RGBA frames. The
selection, translation and miss cases also require their complete before-event
frames. Callback membership, selected axes, translation, panning and retirement
states remain exact. This is a bounded plugin workflow suite; the rest of the
plugin, opaque-volume workflow and wider host matrix remain separate requirements.

Each attempt installs the original or candidate VisPy wheel into a fresh external
environment with the same pinned NumPy 2.4.6 host closure and the genuine pinned
napari-threedee 0.0.29 wheel. This is the previously prepared paired dependency
profile. Source plugin files and its public registration command must match that
wheel, and a separate CPU registration child must construct no QApplication or
graphics context and import no Dawn module.

All five fresh original OpenGL cases must pass and reproduce the retained original
frames, auxiliary frames and parameters exactly before candidate workers can run.
Every candidate case remains required, including failures. Candidate frames use
the [smooth-line criterion](smooth-lines.md#parity-criterion-for-smooth-line-frames).
Pixels uniform in the reference must match exactly; other pixels may differ by
at most 32 of 255 on at most 1% of the frame. That bound was chosen just above
the differences measured on NVIDIA. No hand-drawn masks, alignment, reduced
quality or substitute picking path is allowed. Each passing
candidate must prove actual native work, correct installed native origins, no
visible windows after close and eight zero-resource shutdown counters. Failed
candidate cases must also prove process closure, native origins and cleanup.

The bounded hardware cell is Windows CPython 3.12.8/PyQt6 with NVIDIA RTX 4090.
Other ABIs, bindings, adapters, operating systems and release conditions remain
open. The original VisPy wheel hash is
`c4862155e735009b1af6aeda45ea94a72e1a375d6086c89273455d66238bb18e`.
The genuine plugin wheel hash is
`de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e`.
The exact plugin and dependency artifacts, original source/build evidence and
unchanged upstream license texts are included in
`tests/reference/napari-plugin-wheel-inputs`. The original plugin checker uses
this wheel location for the call and restores its previous binding afterwards.
The pinned host/provenance files are included under `compat/host-environments`.
Only the original and candidate VisPy wheels are external inputs. Missing or
changed inputs fail setup; no private build directory is required.

```powershell
$env:VISPY_NAPARI_PLUGIN_UPSTREAM_WHEEL = 'C:/artifacts/vispy-0.17.0-cp312-cp312-win_amd64.whl'
$env:VISPY_TEST_WHEEL = 'C:/artifacts/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
$env:VISPY_NAPARI_PLUGIN_EVIDENCE = 'C:/artifacts/napari-plugin-wheel-run-1'
python -B -m pytest -q tests/hosts/test_napari_plugin_wheel_parity.py
```

Newly owned environments are removed after actual workers finish. Source,
registration, frame, state, process and failure evidence is retained at the fresh
evidence path. The implementation is AGPL-3.0-only, with original VisPy BSD and
upstream plugin/dependency notices retained unchanged.

## Bounded Windows observation

On 2026-10-21, the frozen suite passed 19 CPU controls and both real CPU
registration checks. A wheel built from the exact pinned asciitree 0.3.3 source
provided binary-only installation; every upstream package and license file stayed
byte-identical and no dependency version changed. Effective hash-seed and context
sharing checks reproduce the retained oracle conditions.

All five fresh original cases matched the retained 245760 final-frame pixels,
147456 before-event pixels and all recorded parameters exactly. The candidate
retirement case matched all 49152 pixels and its callback/Qt state exactly.
Handles, selection, translation and miss each failed at the existing explicit
smooth-line consumer refusal. Pytest reported one pass, four failures, zero errors
and zero skips. The suite remains failed.

Independent saved-result inspection verified the full artifact namespaces,
installed plugin/VisPy/native origins, effective interpreter policies, actual
native work for the passing case, ten terminal graphics workers, two terminal
CPU workers, no visible windows and eight zero shutdown counters for every
candidate. Both newly owned environments were removed. Inspection SHA256:
`c2badba32da687f0acc19e49f6b4e53cc4a01a774b8a0eee8f4681f5645fd5e9`.

The portable Source5 helper repeated the same complete original and candidate
outcome after passing 22 CPU controls. Independent inspection verified that all
twelve real workers used the bundled wheel while the old private artifact paths
were absent. Its inspection SHA256 is
`712bef63a385b25cc2710d0b21c9432f13d09f456eda0d1803831183cfee78e1`.
A separate check materialized all required staged Git files in a clean temporary
tree with no `build/` directory and verified the complete runtime source and input
closure. The publication checkout passed all 156 combined CPU controls.

No candidate plugin host-cell, wider graphics or release qualification is granted by the
recorded one-of-five candidate result. All four failing workflows stay mandatory.
That exact-comparison result is superseded for candidate frames by the
2026-10-28 observation below; this historical record is unchanged.

The upstream-only environment/fixture admission for Windows CPython 3.12.8/PyQt6
is `compat/qualifications/napari_threedee/windows/3.12.8/pyqt6/admission.json`.
It references the exact original frame artifacts through a separate standard
manifest, preserving the original manifest unchanged. The matching host matrix
row installs the hash-locked portable host closure and supplies the original
wheel through `tools/prepare_napari_plugin_host_cell.py`; the candidate still
comes from the job's actual build. Every fresh original and candidate case stays
mandatory. Other missing admissions keep failing. This upstream admission grants
no candidate or release pass and schedules no hardware job by itself.

## Hot-swap observation - 2026-10-28

The suite passed 5 of 5 with candidate wheel `444402…` and the original wheel
`c4862155…`, both in fresh owned environments on Windows CPython 3.12.8 with
PyQt6 and NVIDIA RTX 4090 Vulkan. All five fresh OpenGL cases reproduced the
retained frames exactly. All five candidate cases met the smooth-line criterion.
This suite records results, not per-pixel figures. The in-process overlay suite
logged the figures for the same workflows: 212-254 differing pixels, at most 29
levels, none in uniform regions, and retirement exact. The installed-wheel evidence,
with the helper hash pinned, is in run `napari-smooth-line-pinned-211`; the
in-process figures are in run `napari-smooth-line-208`.
