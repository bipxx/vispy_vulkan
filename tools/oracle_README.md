The references are actual captures from installed upstream VisPy 0.17.0 in
separate environments. The harness verifies the imported source against the
pinned manifest before creating an OpenGL context. Qt renders on the NVIDIA
OpenGL driver; `QT_QPA_PLATFORM=offscreen` is rejected.

Run from the repository root on Windows:

```powershell
uv venv build/oracle-opengl --python 3.12
uv pip install --python build/oracle-opengl/Scripts/python.exe -r tools/oracle_requirements.txt
build/oracle-opengl/Scripts/python.exe tools/oracle_capture.py --kind upstream --output tests/reference/opengl
build/oracle-opengl/Scripts/python.exe tools/oracle_volume_capture.py --kind upstream --output tests/reference/volume-opengl
build/oracle-opengl/Scripts/python.exe tools/oracle_scene_capture.py --kind upstream --output tests/reference/scene-opengl
build/oracle-opengl/Scripts/python.exe tools/oracle_revisions_capture.py --kind upstream --output tests/reference/texture-revisions-opengl

uv venv build/oracle-napari --python 3.12
uv pip install --python build/oracle-napari/Scripts/python.exe --require-hashes -r tools/oracle_napari_requirements.txt
build/oracle-napari/Scripts/python.exe tools/oracle_napari_capture.py --kind upstream --output tests/reference/napari-opengl
build/oracle-napari/Scripts/python.exe tools/oracle_napari_volume_capture.py --kind upstream --output tests/reference/napari-volume-opengl

uv venv build/oracle-glue --python 3.12
uv pip install --python build/oracle-glue/Scripts/python.exe --require-hashes -r tools/oracle_glue_requirements.txt
build/oracle-glue/Scripts/python.exe tools/oracle_glue_capture.py --kind upstream --output tests/reference/glue-opengl

.venv/Scripts/python.exe -m pytest tests/contract/test_reference_inventory.py -q
.venv/Scripts/python.exe -m pytest tests/gloo tests/parity tests/native -q -m gpu
.venv/Scripts/python.exe -m pytest tests/hosts/test_napari_scientific_parity.py -q -m gpu
.venv/Scripts/python.exe -m pytest tests/hosts/test_napari_volume_parity.py -q -m gpu
```

Each fixture runs in a separate process to avoid PyOpenGL context-cache state
surviving native widget destruction. Every captured fixture includes raw RGBA,
filtered GLIR with input-array hashes, expanded shaders, fixture parameters,
package origins and versions, renderer/driver strings, and artifact/source
checksums. The napari environment includes Numba because direct colormaps with
sparse large integer values require it upstream. Required host dependencies
fail their tests if missing.

The six order fixtures keep dependent commands pending until one final color
readback per target. The shared-canvas proof reads each target once. No capture,
finish, or present separates their dependent draws and updates. The numerical
landmarks and edge-band geometry are defined in fixture code before candidate
capture. Comparisons use at most 2/255 per channel in interiors, at most 0.1%
differing pixels in fixed edge bands, and exact categorical regions.

The scalar volume fixtures hold the analytic ellipsoid, step size, threshold,
camera, and interpolation constant across the two implementations. They cover
all seven upstream scalar methods, plane slicing, clipping, and an exact mesh
depth decision. Actual napari categorical fixtures cover both gradient modes,
sparse label identity, plane slicing, clipping, and edited regions. Text uses
the bundled pinned OpenSans-Regular font, whose SFNT license record names
Apache License 2.0; its CPU-generated atlas and final frames at 96, 144, and
192 DPI are compared separately.

The texture revision packet first submits one warmup frame to establish an
actual resident texture allocation. It then records an old draw, changes sampler wrapping,
performs a partial or full public texture update, and records the new draw
before one final readback. A separate pending green FBO draw followed by a
blue corner update proves the untouched pixels retain GPU-produced contents.
Both the complete analytic image and the independent OpenGL frame are exact.

Glue uses a separate hashed environment and the unmodified 1.4.0 Qt viewers.
`tools/oracle_glue_admission.json` retains the pinned source hashes, successful
fixtures, unresolved fixtures, and the upstream tests' historical Windows skip
reason. Four minimal upstream viewers currently pass. The public volume-data
update fixture remains unresolved because glue-core 1.27.0 returns its previous
fixed-resolution cached array after `Data.update_components`; the CPU
reproduction is in `build/evidence/glue-volume-update-cpu-repro.py`. Its raw
failure artifacts are unadmitted. The complete glue qualification job fails
that case explicitly and requires its own installed candidate wheel and host
dependencies; it does not convert the unresolved case or missing dependencies
into a skip.

Candidate artifacts and raw difference arrays are saved under
`build/evidence/`. Metadata-only contract tests do not create a GPU. Native
lifetime tests use live renderer-owned BufferRev/TextureRev allocation bytes
and completion counters; process RSS is not the retirement assertion. The
native allocation counters' current scope is defined by the runtime accounting.

Typed capture references live in `typed-capture-opengl`. Twelve exact cases
cover R/RG/RGBA32f, RGBA16f, byte/16-bit normalized attachments, float/byte output,
NumPy dtype aliases, RGB crop orientation and horizontal offsets, and returned
array lifetime through another read and canvas destruction. Floating captures
preserve units such as -2, 15 and 0.125. The normalized input avoids a rounding
tie; its initial authoring artifacts and correction rationale are preserved in
`build/reports/typed-capture-authoring-evidence.json`. Eleven cases have one
final read; the array-lifetime case explicitly has two independent read stages.

`depth-capture-opengl` has four admitted public depth captures from an explicit
packed GL_DEPTH24_STENCIL8 attachment. Float output preserves the actual 24-bit
conversion, including 0.25 becoming float32(4194304/16777215), with exact crop,
byte and scalar/alpha behavior. Its eight public stencil read attempts remain
unadmitted: pinned VisPy's generated GL2 reader rejects both the wrapper's
GL_STENCIL_INDEX8 and the canonical GL_STENCIL_INDEX in its component table.
The failed calls retain shader/GLIR/parameter evidence and nonzero exits.

Four separate `stencil-capture-opengl` references render through unchanged
public gloo and read the real GL stencil buffer using external
`OpenGL.GL.glReadPixels(GL_STENCIL_INDEX)`. Their provenance records that API,
installed PyOpenGL source hashes, and the failed upstream-wrapper manifest.
They prove GL stencil semantics, including unnormalized float values 3/37/203;
the candidate feature test calls public `gloo.read_pixels(mode='stencil')`.
These references do not admit the broken upstream VisPy wrapper.

DIVE uses the immutable source copy and hashed CPython3.11/PyQt5 host environment
under `compat/host-environments`. All four public widget/export fixtures fail
upstream during construction at DIVE/_components/dive_manager.py:170 because
QSplitter.setSizes receives floats. No PNG or host scene is admitted. Per-child
exit codes, source/dependency origins, and stderr hashes are recorded in
`dive-opengl` and `tools/oracle_dive_admission.json`. Candidate admission remains
pending and requires its own compatible interpreter artifact.

```powershell
build/oracle-opengl/Scripts/python.exe tools/oracle_typed_capture.py --kind upstream --output tests/reference/typed-capture-opengl
build/oracle-opengl/Scripts/python.exe tools/oracle_depth_capture.py --kind upstream --output tests/reference/depth-capture-opengl
build/oracle-opengl/Scripts/python.exe tools/oracle_stencil_capture.py --kind upstream --output tests/reference/stencil-capture-opengl
build/host-environments/dive-cpython311-pyqt5/Scripts/python.exe tools/oracle_dive_capture.py --kind upstream --output tests/reference/dive-opengl

.venv/Scripts/python.exe -m pytest tests/parity/test_typed_capture_parity.py tests/parity/test_depth_capture_parity.py tests/parity/test_stencil_capture_semantics.py tests/hosts/test_dive_parity.py tests/contract/test_host_inventory.py -q -m "not gpu"
```

The depth/stencil and DIVE upstream commands exit nonzero for their retained
failures. Full qualification tests require successful upstream admission and
installed host dependencies; unresolved cases remain explicit failures.

This evidence applies to the captured Windows NVIDIA OpenGL reference and
Windows Vulkan candidate. Each candidate fixture requires a passing image
comparison; an upstream capture alone does not admit the candidate renderer.
Linux/Metal, other Qt bindings, other hosts, benchmark release gates, and
uncaptured scientific modes need their own qualification evidence.
