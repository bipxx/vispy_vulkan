# OpenGL runtime removal: three-agent execution plan

Date: 2026-10-23. Status: planned; implementation has not started.
Inspected source: `390f901ced79d339f46d7f825f21c8e12596d434`.

## Outcome and boundaries

Deliver a VisPy-compatible installation that uses Vulkan on Windows and Linux
without requiring, loading or executing an OpenGL runtime in its admitted
application processes. Verify headless, Qt GUI and each host/plugin separately.
Windows hardware Vulkan and WSL llvmpipe software Vulkan are the initial test
targets; WSLg/X11 supplies the mapped Linux GUI row. Metal remains experimental.

Keep `vispy`, its scene/gloo APIs, GLIR compatibility commands and GLSL inputs.
GLSL compilation through glslang to SPIR-V is compatible with this outcome.
Retain AGPL-3.0-only for this implementation and all original BSD/third-party
licenses. Keep pinned upstream sources and independent OpenGL oracle captures
in separate reference environments; they are not candidate runtime dependencies.

This is runtime removal, not erasure of every source-code occurrence of `gl`.
It also does not establish compatibility with every arbitrary OpenGL program.
Functional equivalence, depth/order correctness and supported application flows
are required; bit-exact driver edge rasterization is not. Cybersecurity work is
excluded.

## Findings that determine the order

| Finding in the inspected source | Consequence |
| --- | --- |
| `CMakeLists.txt:126–130` disables Dawn desktop GL/GLES. `cpp/platform/native_library.cpp:78–89` selects Vulkan on Windows/Linux; `cpp/runtime.cpp:1925–1953` requires that backend. | The native renderer does not need a second Vulkan rewrite. Preserve and test its existing backend restriction. |
| `src/vispy/gloo/gl/__init__.py:235–241` imports and selects `gl2`; `gloo/gl/gl2.py:25–51` loads `opengl32`/`libGL`. | Remove this eager import/dispatch dependency first. A successful Dawn frame currently does not prove GL-free import. |
| `_pyqt5.py`, `_pyqt6.py`, `_pyside6.py` import QtOpenGL; `_qt.py:95–123` imports OpenGL widget classes, while its actual desktop canvas is a QWidget (`:915`). | Separate the Dawn QWidget backend from legacy Qt GL imports and base classes. |
| `_qt.py:341–345` requests shared OpenGL contexts; its EGL branch and automatic application selection still expose legacy backends. | Remove GL-specific application setup from the Dawn path and prevent implicit fallback. |
| `src/vispy/gloo/wrappers.py:700–764` still performs native framebuffer/error queries in `get_gl_configuration()`. | Return actual Dawn target formats, depth/stencil and sample configuration through an agreed native query contract. |
| The inspected pinned napari installation imports `OpenGL.error.GLError`; its marker integration requests `vispy.use(gl='gl+')`, whose current loader imports `OpenGL.GL`. | A fork-only change cannot prove host-level removal. Record host provenance and provide an explicit, reproducible host integration where necessary. |
| `pyproject.toml` packages the whole `src/vispy` tree; wheel auditors expect every tracked package file. | If legacy implementations leave the wheel, introduce an explicit shipping manifest and update exact-content audits together. |
| Existing native-module audits check provenance, not absence of GL usage or transient library loads. | Add dedicated dependency, loader and API/context evidence; existing passing graphics results alone are insufficient. |

## Three completion gates

All three gates must pass on the same installed artifact and environment for
each admitted headless/GUI/host row.

1. **No OpenGL execution:** no GL/EGL/GLX/WGL context creation, entry-point
   resolution or API calls from import through shutdown. The actual renderer
   reports Vulkan, including after device recovery. No GL fallback is permitted.
   Observe native Qt/plugin calls as well as Python wrappers.
2. **No OpenGL runtime loaded:** observe native loads throughout the lifecycle,
   including transient loads, alongside Python imports. Reject GL-only loaders,
   QtOpenGL and applicable OpenGL/EGL/GLES/GLX/OSMesa runtime libraries.
   Capture OS-loader startup/dependency events; intercepting only explicit
   `ctypes`/`dlopen` calls or inspecting the final module list is insufficient.
3. **No OpenGL installation/link requirement:** audit required and delayed
   binary dependency closures, installed packages and plugins. On Linux, install
   and run the candidate in a fresh environment without GL runtime packages or
   files; include the selected GUI/host dependencies before auditing.

Classify libraries by their role and actual dependency graph, not a `gl`
substring. X11, GLSL compiler components and the Vulkan ICD are not themselves
proof of OpenGL use. A vendor ICD can share implementation code with other APIs;
document that boundary without waiving GL-loader dependencies or observed GL
calls. On Windows, prove the candidate does not require/load/use `opengl32.dll`;
do not delete or claim to remove that OS component.

Stock Qt is an early feasibility gate. Removing Python QtOpenGL imports may
still leave QtGui or a platform plugin with a transitive GL dependency. If so,
the strict GUI artifact needs a reproducible Qt/binding build with OpenGL
disabled. First distinguish required libraries from unused optional plugins:
a reviewed, reproducibly packaged runtime that excludes optional GL modules may
suffice if its complete selected dependency closure is already GL-free. An
unproven binding remains incomplete; deleting DLLs from an existing
Qt installation or checking only `QWidget` inheritance does not pass the gate.

## Exactly three execution agents

The coordinator integrates their work and reviews evidence; it does not create
a fourth implementation workstream. Use one branch/worktree per agent.

| Agent | Exclusive edit ownership | Deliverable |
| --- | --- | --- |
| **1 — Native Vulkan and required features** | `cpp/**`; native/shader/line/texture tests under `tests/native`, `tests/shaders`, `tests/lines`, `tests/textures` | Explicit Vulkan-only behavior and functional native support for the required application inventory. |
| **2 — Python, Qt and host integration** | `src/vispy/**`; `tests/gloo`, `tests/qt`, `tests/hosts`; `compat/deviations.txt`; explicitly registered new host patch/fixture files | GL-free Python import/dispatch, QWidget integration and supported host adapters without PyOpenGL or GL fallback. |
| **3 — Builds, packaging and proof** | Project CMake/presets and `cmake/**`; `pyproject.toml`, `uv.lock`; shipping/dependency manifests; wheel auditors, loader-audit tools and native probes under `tools/no_opengl/**`; `tests/no_opengl/**`, package contract tests and `.github/workflows/**` | Reproducible GL-free artifacts and automated proof of all three gates. |

Each execution prompt must state: **You are not alone in the codebase. Do not
revert another agent's edits. Adapt to agreed interfaces and coordinate changes
outside your ownership before editing.** Agent 1 requests CMake changes from
Agent 3; Agent 2 requests dependency/Qt-package changes from Agent 3. Assign a
single owner before touching shared tools or new fixture paths.

## Execution sequence

### Phase 0 — Freeze the contract and reproduce the dependency

All three agents work in parallel, without changing production behavior yet.

- Agent 1 records backend/surface selection and unsupported native operations.
- Agent 2 traces import, default app selection, `use_gl`, capability queries,
  headless rendering and mapped Qt creation. Trace each pinned host separately.
- Agent 3 records wheel/package inventories, PE/ELF dependency closures, dynamic
  loads and Qt feasibility. Capture current failures of gates 1–3.
- Agree on a manifest listing every required application, binding, platform,
  feature and fixture. Seed it with existing image/label/volume/marker/mesh/text,
  Qt lifecycle and admitted napari/Glue/napari-threedee workflows. DIVE, visbrain
  or other applications need their own explicit admission rows.

**Exit:** reproducible baseline failures, the mandatory application matrix,
library classifications, capability/query contract and file ownership are
recorded. Do not classify a required feature as optional just because it fails.

### Phase 1 — First GL-free headless vertical slice

- **Agent 2:** replace the eager `gl2` activation with a Dawn-backed compatibility
  dispatch/facade. Route supported queries to actual device capabilities before
  any canvas exists. Handle repeated `vispy.use(gl='gl+')` requests explicitly
  without importing PyOpenGL. Unsupported direct GL calls must produce useful
  errors, not no-ops. Separate legacy parsers/loaders from normal context imports.
- Agents 1 and 2 agree the native framebuffer-configuration query before porting
  `get_gl_configuration()`: report real formats, depth/stencil and sample count,
  including offscreen targets; do not invent GL defaults to satisfy callers.
- **Agent 1:** test existing Vulkan-only selection, missing-adapter failure and
  recovery. Add native behavior only where the agreed query/feature contract
  actually needs it. Preserve granted-limit reporting and ownership semantics.
- **Agent 3:** implement import/load/dependency audits and a fresh Linux no-GL
  environment. Preserve exact shipped-file hashes and native-origin checks.

**Exit:** clean installed-wheel processes import VisPy and render clear, image,
markers and compiled text with all three gates passing, including first render,
recovery and shutdown. Missing Vulkan must fail rather than activate OpenGL.

### Phase 2 — Qt GUI and complete artifact dependency closure

- **Agent 2:** remove eager QtOpenGL imports from all three binding wrappers;
  split the Dawn QWidget path from retained upstream GL widget implementations.
  Set binding/version flags independently of OpenGL imports: `PYQT6_API`,
  `PYSIDE6_API` and `QT5_NEW_API` also govern enums, alpha handling and QImages.
  Adapt existing tests that import a GL widget solely to assert the canvas is
  not one; test QWidget identity and lifecycle under the no-GL import gate.
  Audit other auto-selected application backends so none silently creates GL
  contexts. Preserve parent/handle/resize/DPI/input/capture/close semantics.
- **Agent 3:** measure stock Qt first. Where its dependency closure fails, build
  and pin the required no-GL Qt/binding artifact, with notices and provenance.
  Define the shipping manifest: retain mandated compatibility import paths as
  clear failure stubs where needed, and exclude executable legacy GL loaders
  from runtime artifacts. Keep source/reference history separately.
- **Agent 1:** fix only demonstrated native surface, depth/capture or recovery
  defects exposed by these GUI runs.

**Exit:** headless and each declared Qt binding independently pass gates 1–3
and the mapped-window lifecycle/capture suite on their installed artifacts.
Stock Qt import removal alone is not an exit criterion.

### Phase 3 — Required hosts and feature closure

Agent 2 owns host integration; Agent 1 can implement native gaps concurrently
once each required feature row is defined; Agent 3 validates each resulting
installed host artifact.

- Patch or integrate pinned hosts that independently import PyOpenGL, probe GL
  limits or create GL contexts. Deliver versioned, reproducible patches/forks and
  explicit dependency metadata. Do not inject fake `OpenGL` modules or rely on
  temporary monkeypatches as the shipped solution.
- Run the real application launch, image/label and volume updates, overlays,
  interaction, capture/export, recovery and close paths. Record host/plugin
  versions and direct/transitive dependencies.
- Agent 1 implements required gaps in small batches: functional four-sample
  lines/interpolation/depth; shader arrays/attributes/LOD operations; required
  depth/stencil revisions and generated-line side effects. Keep the existing
  single-sample and ordinary pipeline behavior covered.
- Geometry-stage consumers need a supported compute/instanced expansion path
  or an application/visual rewrite. Do not promise arbitrary geometry-shader
  translation through WebGPU's vertex/fragment/compute interface.

Native starting points are the explicit refusals in `cpp/runtime.cpp:4548,6350`,
`cpp/shader/normalize.cpp:231,717–742,896,949` and
`cpp/shader/line_consumer.cpp:587–599,624,675` at the inspected revision.
These are an inventory, not a reason to implement every feature before the
first headless slice. A missing required feature still blocks its application
row; an explicit refusal is honest but does not count as feature completion.

**Exit:** every required host/feature row passes its functional criteria and all
three no-GL gates. An unresolved row stays unresolved and cannot be advertised
as a completed host port.

### Phase 4 — Integration and release evidence

- Integrate by completed vertical slice; retain a known-good artifact before
  changes. Agent 3 rebuilds affected wheels and tests them externally.
- Re-run the existing native contracts, current Python CPU selection and
  relevant scientific/host/Qt suites. Extend import/provenance and package tests
  deliberately when shipping contents change; do not weaken them to fit output.
- Publish artifact hashes, dependency/load evidence, functional results and the
  exact headless/GUI/host capability matrix. Keep strict comparison failures and
  historical captures unchanged; do not aggregate different artifacts into a
  claim that one artifact passed all gates.
- Remove owned disposable objects, environments and caches only after terminal
  results. Retain meaningful inputs, binaries, wheels, frames, logs and failures.
  Never retry cleanup paths previously rejected by automatic approval review.

**Final exit:** all mandatory rows have same-artifact proof of gates 1–3,
functional behavior, recovery and clean shutdown. No silent fallback, skipped
mandatory test or stock-Qt assumption can substitute for evidence. Metal and
native Linux hardware remain separately labelled until actually qualified.

## Test commands and new tooling

Retain existing commands, using isolated build/consumer environments:

```text
python cmake/verify_dependencies.py
cmake --build <native-build> --config Release
ctest --test-dir <native-build> -C Release --output-on-failure
python -B -m pytest tests/contract/test_package_inputs.py tests/contract/test_source_distribution.py
<consumer-python> -I -B tools/linux_wheel_smoke.py --tag cp312 --wheel <wheel> --output <fresh-output>
<consumer-python> -I -B tools/marker_wheel_smoke.py --wheel <wheel> --output <fresh-output>
```

Agent 3 will add these tools/tests; they do **not** exist yet:

```text
python -B tools/audit_no_opengl.py dependencies --wheel <wheel> --qt-root <installed-qt> --output <report>
python -B tools/audit_no_opengl.py run --python <external-consumer-python> --binding <binding> --output <report>
python -B -m pytest tests/no_opengl -q
```

The harness must observe the whole process tree from startup, not just the last
module snapshot. Add independent negative controls proving that a forbidden
Python import, transient native GL load, context/API call and missing Vulkan
adapter are detected. Keep OpenGL oracle processes outside the candidate tree.

Agent 3 owns a new application/shipping contract and a single status table
(`docs/opengl-removal-status.md`, planned). Per-run reports belong under a fresh
`build/no-opengl/<run-id>/` directory, with source commit, wheel SHA256, platform,
adapter/ICD, binding/host versions, fixture IDs, observed dependency paths and
load/call events, actual process exits and cleanup results. Link the underlying
frames/traces; a self-declared `no_opengl=true` field is not proof. Reuse a tested
artifact for matching checks rather than rebuilding it for every report edit.

## Dispatch order

Start all three agents on Phase 0. Then run the Python facade change, native
contract work and audit harness in parallel. Integrate the headless slice first.
Make the Qt binary feasibility decision before promising a GL-free GUI date.
Proceed to Qt and required host slices, with native feature packets running in
parallel as their contracts become clear. The principal uncertainties are Qt
binary dependencies and independent host OpenGL usage, not the already-Dawn
native renderer. Estimate the implementation after that inventory, rather than
promising completion based only on removing a few imports.
