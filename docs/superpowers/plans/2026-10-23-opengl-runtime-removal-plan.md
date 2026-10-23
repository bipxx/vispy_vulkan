# OpenGL runtime removal: three-agent execution plan

Date: 2026-10-23. Status: execution plan; groundwork partially implemented,
full installed-artifact qualification remains pending.
Original inspected source: `390f901ced79d339f46d7f825f21c8e12596d434`.
Integrated implementation checkpoint: `cc4a66c09` on
`work/opengl-runtime-removal`. The final installed-artifact matrix is incomplete.

## Resumption checkpoint

Use this checkpoint to resume execution; the original phases below retain their
requirements. Earlier "current groundwork" notes describe historical results.

- Native N0/N1 functional tests pass 25/25 on Windows hardware Vulkan and WSL
  software Vulkan. Linux PyQt6 QWidget and the three admitted hosts have scoped
  all-three-gate evidence on the N1 artifact, not on the latest native source.
- Integrated sampler-array test region correction, generated-line integer
  sampling specialization, depth uploads, and actual sample-zero multisample
  depth/stencil capture. The latest fixes still require fresh GPU qualification.
  Preserve the earlier four endpoint failures until a matching new wheel passes.
- Integrated selected Windows PyQt5/PySide6 packaging, the core-only TBB runtime
  profile, and exact Linux host dependency/CPU runtime locks. Focused profile
  tests pass 11/11; the integrated no-OpenGL CPU suite passes 60 with one
  platform-specific skip. These checks do not qualify the final graphics matrix.
- The N2/N3 Linux wheel build completed from source `531b19236`, SHA256
  `39a725766dab08dc6e284af807d40c44202584d4972e5714f34691e6e4375c41`.
  It predates the generated-line fix and depth changes; installation and GPU
  qualification remain pending. Do not label it the final candidate.
- Disk exhaustion initially paused Linux Qt 6.12. After space recovery and exact
  process-identity verification, resumption exited at 1480/1636 with EROFS. WSL
  now mounts read-only as a fallback and reports I/O errors; no Qt processes
  remain. Do not restart Linux builds before filesystem recovery is authorized
  and verified. Offline repair requires explicit approval because it changes
  filesystem metadata and available space cannot hold a full disk backup.
- All 94,583 canonical vendor files match the Git blobs byte for byte. The empty
  publication vendor directories remain untouched after automatic review
  rejected their replacement. New frozen build snapshots link directly to the
  verified canonical source. Never stage the vendor deletions, and never retry
  a rejected cleanup or replacement through another command or its parent.

Exactly three execution owners continue in parallel:

| Agent | Next packet | Exit evidence |
| --- | --- | --- |
| 1 — Native | Validate generated-line sampling, depth uploads and sample-zero capture in a fresh artifact; finish the paused Linux binding builds after capacity recovery. | Actual GPU pixels, mutation/recovery tests and zero resources; source/configuration/license handoff for Qt. |
| 2 — Python/hosts | Qualify persistent Windows binding/host consumers, investigate the intermittent PyQt5 startup hang, and replay required host flows against the final renderer. | Real mapped-window interaction/capture/recovery/shutdown; failures remain visible until resolved. |
| 3 — Packaging/proof | Finish binding/dependency profiles, reproducible artifacts, whole-process-tree observations and current matrix documentation. | Same-artifact proof of all three gates for every mandatory row; complete hashes and notices. |

The coordinator integrates and tests completed packets without adding another
execution agent. Sequence: recover capacity and verify sources; integrate ready
changes; build a batched final native candidate; qualify each installed row;
run required CI; publish and merge only after the release gates pass. Keep
Windows hardware and WSL software results distinct. Metal remains experimental.

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

Agent 3 owns the committed audit interface and its native negative controls.
Use fresh output paths for each observation. A dependency-only report cannot
qualify the installed environment; inventory binds successful runtime evidence
to the exact wheel and consumer before the final replay:

```text
python -B tools/audit_no_opengl.py dependencies --root <installed-native-extension> --qt-root <installed-qt> --output <closure.json>
python -B tools/audit_no_opengl.py run --python <external-consumer-python> --wheel <wheel> --scenario qt --binding <binding> --output <runtime.json>
python -B tools/audit_no_opengl.py inventory --python <external-consumer-python> --wheel <wheel> --runtime-report <runtime.json> --output <receipt.json>
python -B tools/audit_no_opengl.py run --python <external-consumer-python> --wheel <wheel> --scenario qt --binding <binding> --dependencies-report <receipt.json> --output <qualified.json>
python -B -m pytest tests/no_opengl -q
```

On Linux, both runtime invocations also require `--native-auditor
<loader_audit.so> --native-debugger <debugger_linux>`. Host rows use `--scenario
script --script <host-probe.py> -- <host arguments>`; headless uses `--scenario
headless`. A first runtime run without an installed-environment receipt remains
UNVERIFIED for the aggregate three-gate claim even if execution and loads pass.

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

## Current groundwork and remaining execution

The following are partial results, not a completed OpenGL-removal claim:

- Integrated native framebuffer query, Dawn Python facade, Qt import cleanup,
  explicit backend selection and exact runtime-package manifest.
- Focused integrated Python/package checks: 45 passed. Native CPU framebuffer
  contract passed; new GPU framebuffer cases still need a matching fresh wheel.
- A fresh Linux runtime rootfs without GL runtime libraries reproduced the old
  wheel's GL import failure. It is ready for candidate qualification.
- Stock Linux QtGui and XCB plugins require libGL/libEGL. Removing Python imports
  alone cannot finish Linux GUI support; a no-GL Qt and binding build is required.
- Pinned napari/QtPy source patches and focused host checks are prepared in the
  Python agent's branch; integration and full mapped host runs remain pending.
- Native load/call collectors and their negative controls are being developed.
  Windows import-only checks do not qualify an installed GUI or host artifact.

## Next three-agent execution wave

Use the existing three agents/worktrees. Do not create additional execution
agents. The coordinator integrates completed packets, resolves interfaces and
reviews reports. Resume from the current groundwork instead of repeating Phase 0.

| Agent | Next bounded packet | Handoff and completion check |
| --- | --- | --- |
| **1 — Native and no-GL Qt build** | Qualify the new framebuffer query against a fresh Vulkan wheel. Build pinned Qtbase/QtSvg and selected PyQt6 modules with OpenGL disabled inside the separate owned Linux build rootfs. Fix native defects demonstrated by required fixtures. | Give Agent 3 exact configure commands, source hashes, build outputs and original licenses. Qt source/build scripts stay in owned local build directories; Agent 3 retains project packaging/dependency ownership. A successful configure alone is insufficient. |
| **2 — Python, Qt and hosts** | Integrate the pinned napari/QtPy patch packet, then run real QWidget and admitted host workflows against the fresh artifacts. Cover image/labels/volume, overlays, input, capture, recovery and close. | Provide versioned patches, source hashes and functional fixtures. Report unsupported required features to Agent 1; request packaging changes from Agent 3. Import-only host checks remain partial. |
| **3 — Artifacts and proof** | Finish native dependency/load/API collectors with negative controls, resolve Windows dependency redirects, and build/audit fresh Windows and Linux wheels. Package Agent 1's Qt/binding output reproducibly. | Produce the mandatory application matrix and per-artifact evidence for all three gates. Keep fresh strict Linux consumer environments separate from the Qt build environment. |

Execute these checkpoints in order, with the three packets running in parallel:

1. **Headless first:** build and install the current source; pass clear, image,
   markers, text, framebuffer, missing-Vulkan failure and recovery checks under
   all three gates on Windows and the strict Linux rootfs.
2. **Mapped Qt:** use the measured Windows Qt closure and the no-GL Linux Qt
   build. Pass lifecycle, resize/DPI/input/capture and shutdown on the selected
   binding. Other required bindings retain explicit pending rows until tested.
3. **Hosts and feature gaps:** run the admitted pinned host/plugin matrix and
   implement only native features required by those rows. Keep failures visible;
   do not substitute an error stub for a completed required feature.
4. **Release:** run relevant regressions and CI, publish exact artifact hashes
   and the capability matrix, preserve AGPL/BSD/third-party notices, then merge
   the tested implementation through the already-authorized normal workflow.

Clean owned disposable build objects and caches after terminal results, retaining
source inputs, wheels, binaries, frames and meaningful logs. Previously rejected
cleanup paths and their parent worktrees remain untouched. Metal stays
experimental; WSL software Vulkan does not establish native Linux GPU support.

The critical path is the Linux no-GL Qt/binding artifact plus installed-artifact
native tracing. Estimate completion after their first successful runs; do not
infer completion from import cleanup or existing Vulkan rendering alone.
