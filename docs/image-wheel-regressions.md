# Installed-wheel image and label regressions

The thirteen required image-extension cases cover signed and unsigned scalar
images, RGB, CPU/GPU NaN scaling, alpha NaNs, multiplicative and additive layers,
signed label remapping, offset painting, multiscale revisions and slice changes.
They use the existing original OpenGL references without regeneration, alignment,
pixel exclusion or tolerance changes. Every full 128x96 RGBA frame must be exact.
Label remaps, paint events, source revisions and level/slice sequences must also
match; a matching screenshot alone is insufficient.

Provide a compatible wheel and a new evidence destination, for example:

```powershell
$env:VISPY_TEST_WHEEL = 'C:/artifacts/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
$env:VISPY_IMAGE_EVIDENCE = 'C:/artifacts/image-wheel-run-1'
python -B -m pytest -q tests/parity/test_image_wheel_parity.py
```

The runner uses `uv` to install locked runtime and `hosts` dependencies into a
new external environment, then installs the supplied wheel with its exact hash.
The pinned napari 0.9.2 and numba 0.68.0 host group requires Python 3.11 or later.
Host cases need a working PyQt6 desktop session. Direct ImageVisual cases use
`dawn_headless`; napari cases use the fork's PyQt6 backend. Missing dependencies,
references, display support or artifacts remain failures.

`VISPY_TEST_PYTHON` selects the consumer interpreter.
`VISPY_TEST_RUNTIME_REQUIREMENTS` can supply a hashed requirements file including
the host dependencies. `VISPY_IMAGE_PYTHON` instead selects an existing external
environment, which the runner neither installs into nor deletes. The supplied
wheel must already be installed there with matching package bytes.

`VISPY_EXPECTED_BACKEND` defaults to `Vulkan`; set `Metal` for the matching macOS
artifact. Software devices require explicit `VISPY_IMAGE_ALLOW_SOFTWARE=1` and
do not establish native GPU qualification. The harness supports those selections;
their availability does not establish a platform pass.

Each case runs in a separate isolated process. Reports retain actual worker
identity, interpreter/package/host origins, wheel hashes, rendered pixels,
commands, shaders, semantic observations, loaded native images and shutdown
counters. Unknown worker termination prevents further launches and environment
removal. Once all workers are terminal, the runner removes its newly owned
environment, including after test failure. Evidence remains at the supplied path.

The reference manifest is pinned to
`9675b84eda8cd0c910d31fa668c6b77cda35ea94f26e8bc2e45a8d0ccd7bf70d`.
Both the implementation's AGPL license and original VisPy BSD license remain
attached and are checked against the installed wheel. These scientific cases do
not complete physical Qt lifecycle, other host/plugin, smooth-line, platform,
performance or release requirements.

## Bounded Windows observation

On 2026-10-21, all thirteen cases passed from the archived CPython 3.12.8 Windows
wheel on hardware RTX 4090 Vulkan driver 610.88. The ten napari cases used napari
0.9.2, numba 0.68.0 and PyQt6 6.11.0. All 159744 pixels matched byte-for-byte,
including exact alpha and the original semantic observations. All thirteen
workers terminated, loaded-native-image checks passed, resource counters were
zero after shutdown, and the newly owned environment was removed.

The wheel SHA256 was
`105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81`.
The independent saved-result verification SHA256 was
`753f983f62435341cae11e1f0d320eeaa1e1fa2bf6300dca4fea7b7daa519943`.
Raw local qualification packets are retained locally. This observation uses the
archived wheel and does not qualify a fresh renderer build or another platform.
