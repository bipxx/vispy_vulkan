# Installed-wheel Glue cache-update regressions

The suite requires all five Glue workflows: scatter, scatter edit, scatter axes,
volume and volume edit. The edit protocol invalidates Glue's fixed-resolution
buffer cache for the Data object before `update_components`. This uses the pinned
host's public API. Host source, data, camera, quality settings, landmarks and
exact full-frame criteria remain unchanged.

The old upstream volume-edit failure and its metadata audit remain retained.
Fresh references are captured with the corrected protocol; the old failed image
is never accepted as an expected result.

This bounded runner uses a Windows desktop, CPython 3.12, PyQt6, pinned Glue
1.4.0 viewers/core 1.27.0 and hardware NVIDIA RTX 4090. The original OpenGL and
candidate Vulkan runs must use that adapter. Other ABI, binding, platform and
adapter rows remain required work and are not qualified by this observation.

Provide the original and candidate wheels, plus a new evidence path:

```powershell
$env:VISPY_GLUE_UPSTREAM_WHEEL = 'C:/artifacts/vispy-0.17.0-cp312-cp312-win_amd64.whl'
$env:VISPY_TEST_WHEEL = 'C:/artifacts/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
$env:VISPY_GLUE_WHEEL_EVIDENCE = 'C:/artifacts/glue-wheel-run-1'
python -B -m pytest -q tests/hosts/test_glue_wheel_parity.py
```

The upstream artifact must match SHA256
`c4862155e735009b1af6aeda45ea94a72e1a375d6086c89273455d66238bb18e`,
which is checked against the existing original hash lock. All 517 pinned source
files and the four explicit generated/native members must match. The candidate
must contain the exact supplied package bytes and both attached license texts.

`uv` installs the pinned host closure and the selected wheel together in each
new external environment. Before rendering, a separate CPU child reproduces
the real stale-buffer problem and verifies invalidation before update, without
creating a QApplication or importing Dawn. Every graphics case has its own
isolated worker. All five upstream cases must pass and their saved evidence must
verify before any candidate case runs.

Candidate comparisons require exact 128x128 RGBA, all original inputs and state,
the original widget distinction, positive actual native draw/pipeline/queue work
and the original landmarks. Failed candidate cases remain named failing tests;
they are never skipped or marked as expected failures. Every case must still
prove actual worker termination, loaded-native-image origins, no visible windows
after close and eight zero-resource shutdown counters.

The newly owned environments are removed once all actual workers are terminal.
Original references, rendered frames, commands, shaders, parameters, reports and
failure evidence remain at the selected evidence path. This suite does not
establish full Glue lifecycle/recovery, smooth-line support, fresh-build,
cross-platform, performance or complete release qualification. The original BSD
license remains attached alongside the implementation's AGPL license.

## Bounded Windows observation

On 2026-10-21, both real CPU cache controls passed. All five fresh original
OpenGL scenes passed, including volume edit, and repeated original frames were
byte-exact across two captures. Four candidate scenes matched all 65536 pixels
exactly. `scatter_axes` failed at the existing generated smooth-line consumer
refusal; it remains a required failing test. Pytest reported four passes, one
failure, zero errors and zero skips.

All ten actual graphics workers terminated. Native origins, visible-window
cleanup and all candidate shutdown counters passed, including the failed case.
Both newly owned environments were removed. The candidate wheel SHA256 was
`105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81`.
Independent saved-result verification SHA256:
`5638fb93615444e0529a5812ac680375b1e7efbae994b7a3e9d3776a2f835cef`.
The suite remains failed. Raw local evidence is retained locally; wider release
qualification remains open.

The independently verified upstream packet is also attached in
`tests/reference/glue-cache-update-opengl`, with all five exact frames, GLIR,
shaders and parameter artifacts. It preserves the original failed packet in
`tests/reference/glue-opengl`. Its formal upstream environment admission is
`compat/qualifications/glue_vispy_viewers/windows/3.12.8/pyqt6/admission.json`.
This admission covers the observed Windows CPython 3.12.8/PyQt6/NVIDIA RTX 4090
upstream fixtures. It grants no candidate, lifecycle or release qualification.

The existing host matrix uses that admission and runs every node in
`tests/hosts/test_glue_wheel_parity.py`. `tools/prepare_glue_host_cell.py` supplies
the hash-pinned original wheel and a fresh evidence directory; the CI job's built
candidate wheel remains mandatory. The test still captures all five fresh original
scenes before running candidates. Other cells retain missing-admission failures.
This workflow requires the declared self-hosted hardware; hosted CPU CI does not
exercise the graphics job or promote the recorded four-of-five candidate result.
