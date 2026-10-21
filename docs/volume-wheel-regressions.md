# Installed-wheel scalar and categorical volume regressions

All eleven original scalar cases and six categorical napari cases are required.
The scalar suite covers seven exposed methods, nearest/linear interpolation,
ray/plane depiction, clipping and an isosurface occluded by foreground geometry.
The categorical suite covers fast/smooth isosurfaces, translucent rendering,
plane depiction, clipping and a sparse-label edit.

The original fixtures and reference bytes remain unchanged. Scalar comparisons
retain the original fixed analytic interior and edge regions: maximum RGBA error
two in the interior, and at most 0.001 differing fraction in the edge region.
Every pixel belongs to one checked region; the edge band is never discarded.
Categorical RGBA must match exactly. Both suites retain original landmarks and
all parameters, including quality settings, input revisions, sparse IDs and
camera geometry. The categorical candidate must also retain the original check
that its widget is not a `QOpenGLWidget`.

For example, from PowerShell with a compatible built wheel:

```powershell
$env:VISPY_TEST_WHEEL = 'C:/artifacts/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
$env:VISPY_VOLUME_WHEEL_EVIDENCE = 'C:/artifacts/volume-wheel-run-1'
python -B -m pytest -q tests/parity/test_volume_wheel_parity.py
```

The evidence path must be new. `uv` creates an owned external environment and
installs locked runtime/hosts dependencies together with the exact hashed wheel.
The pinned napari 0.9.2/numba 0.68.0 host group requires Python 3.11 or later and
a working PyQt6 desktop session. Scalar cases use `dawn_headless`; categorical
cases use the fork's PyQt6 backend. Missing cases, artifacts, dependencies,
references or display support fail rather than skip.

`VISPY_TEST_PYTHON` selects the consumer interpreter.
`VISPY_TEST_RUNTIME_REQUIREMENTS` can supply hashed runtime/host requirements.
`VISPY_VOLUME_WHEEL_PYTHON` selects an existing external environment instead,
which is neither installed into nor deleted; its installed wheel must match the
supplied archive. `VISPY_VOLUME_WHEEL_REFERENCE` selects a root containing both
original `volume-opengl` and `napari-volume-opengl` packets, still hash-pinned.

`VISPY_EXPECTED_BACKEND` defaults to `Vulkan`; `Metal` requires its matching
artifact. Software devices require `VISPY_VOLUME_WHEEL_ALLOW_SOFTWARE=1` and do
not establish native GPU qualification. These settings do not imply platform
qualification.

Every case launches in a separate isolated worker, with actual worker identity
and terminal state, installed package bytes, loaded-native-image origins,
device/backend, comparison results and shutdown counters recorded. Unknown
termination blocks subsequent workers and environment removal. After all workers
terminate, the newly owned environment is removed once and all evidence remains.
Both exact AGPL and original BSD license texts are checked against the wheel.

The original manifest digests are:

- Scalar: `a09dc2508961dd8dc24d500b4512d1aa731987435f2dd1b8cbdd55a238cf7e0b`.
- Categorical: `85dda2a86b89d17e17f2550c8ce766b5cf4b12a9d4c0499de0dd41a815e4a9e0`.

This suite does not close Glue's separate volume discrepancy, other host/plugin
or physical Qt lifecycle rows, smooth lines, other ABIs/platforms, fresh-build,
performance or complete release qualification.

## Bounded Windows observation

On 2026-10-21, all seventeen cases passed from the archived CPython 3.12.8 Windows
wheel on hardware RTX 4090 Vulkan driver 610.88. All 156672 pixels were byte-exact,
including alpha, while the original scalar tolerances remained unchanged. All
parameters and categorical input revisions matched. The six host cases used
napari 0.9.2, numba 0.68.0 and PyQt6. All seventeen workers terminated, native
origins and eight zero-resource shutdown counters passed, and the newly owned
environment was removed.

The wheel SHA256 was
`105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81`.
Independent saved-result verification SHA256:
`69efb1aa9b1953c4eb7a32dcab6aec1a934484b77e3ab71c94d61ac3a5fbc099`.
Raw local qualification evidence is retained locally. This observation does not
qualify a fresh renderer build or another platform.
