# VisPy replacement using Dawn

Date: 2026-10-08. Status: historical architecture/design baseline; its original
findings and proposed slices describe the pre-implementation review.

Implementation now exists. Use the [current gap-closure specification](2026-10-24-vispy-compatibility-gap-closure.md)
and [execution plan](../plans/2026-10-24-vispy-compatibility-gaps.md) for remaining
work and acceptance status. The current root AGENTS.md and build-hygiene policy
govern command/environment reuse; commands below are historical recipes.
Existing mandatory qualification gates are not waived by this status correction.

Keep a compatibility fork of VisPy's Python package and put a batched C++ renderer behind its gloo/GLIR boundary, using Dawn with Vulkan on Windows/Linux and Metal on macOS. Replace the handwritten GLSL-to-WGSL compiler with a compiler-assisted GLSL-to-SPIR-V path that Tint still consumes, and make installation, ordered GLIR snapshots, host capture, shader validation on both backends, and measured speed release gates: this can replace VisPy for an explicit application matrix, but cannot promise arbitrary OpenGL programs or switch applications that import a vendored copy.

Pinned source governs behavior. Current upstream documentation is only a map to that source. Every Python command in this plan runs under `uv run`. This document does not add implementation files.

## Findings, in severity order

### 1. Blocking: import compatibility does not guarantee replacement

**What breaks:** A differently named distribution exporting `vispy` does not satisfy a host's dependency on the `vispy` distribution. Installing both creates overlapping files. An application importing `host.extern.vispy` never reaches top-level `vispy`, and a dependency upgrade can reinstall upstream even after a successful switch. [Python packaging distinguishes distribution names from import names.](https://packaging.python.org/en/latest/discussions/distribution-package-vs-import-package/)

**Who hits it:** napari, plugins with VisPy requirements, older glue installations, and managed application environments.

**Required change, adopted:** Both distribution and import are named `vispy`. Initially ship `0.17.0+vulkan.1` through direct wheels or a dedicated index, and lock the wheel/source and its hash in each consumer environment. The public base version describes the API being replaced; keep `vispy.__version__` and distribution metadata consistent. Do not publish a competing package that merely writes into upstream's directory, use `Provides-Dist` as a dependency workaround, or overwrite modules through `sys.path` tricks. Public PyPI release under `vispy` requires upstream project ownership/cooperation and is outside this implementation plan.

Correct the glue premise: glue-vispy-viewers **1.4.0 imports top-level `vispy`**. `VispyWidgetHelper` executes `from vispy import scene` and constructs `scene.SceneCanvas(..., config={'depth_size': 24})`. Its packaging still contains old vendored package-data entries; those entries are not the runtime namespace. Support 1.4.0 as an installation of top-level `vispy`. Older releases that actually import a vendored namespace require a host upgrade or explicit host integration and cannot be advertised as installation-only replacements. Preserve glue's existing plugin entry points; no new renderer entry point switches them. [Glue widget](https://github.com/glue-viz/glue-vispy-viewers/blob/33509adb53909b7542069563f77fb9a80bd565a4/glue_vispy_viewers/common/vispy_widget.py), [dependency and entry-point metadata](https://github.com/glue-viz/glue-vispy-viewers/blob/v1.4.0/setup.cfg).

### 2. Blocking: a GLSL token rewriter is not a shader compiler

**What breaks:** Changing `attribute`, `varying`, and `texture2D` cannot translate functions with `out` parameters, matrices, uniform arrays, sampler bindings, macros, integer arithmetic, or control flow into valid WGSL. Successful compilation of a triangle says little about volume loops or subclass-injected filters. Implicit texture derivatives in divergent loops can fail validation or change results.

**Who hits it:** Every custom Visual, napari labels and categorical volumes, clipping filters, and scientific volume rendering.

**Required change, adopted:** Compile composer-expanded GLSL through the contract in [Shader compiler contract](#shader-compiler-contract). Legacy GLSL still needs a bounded compatibility transform before glslang. Native Dawn SPIR-V is not unrestricted Vulkan execution: at pin `499e5c6ff9b37d5de70c6493fb74c251e0d35c1c`, `ParseSPIRV` calls `tint::spirv::reader::ReadIR` and then `tint::wgsl::writer::ProgramFromIR`. `Device::CreateShaderModule` rejects SPIR-V unless `TINT_BUILD_SPV_READER` is enabled, `Toggle::DisallowSpirv` is off, and the instance has `wgpu::InstanceFeatureName::ShaderSourceSPIRV`. `TINT_BUILD_SPV_READER` defaults to `${DAWN_ENABLE_VULKAN}`, so a Metal-only macOS build leaves the reader off unless the fork forces it on. Prove a real render pipeline, with layouts and attachment formats, on Vulkan and on Metal before any visual slice expands. Retain SPIR-V and Tint validation. [ShaderLang.h preprocess warning](https://github.com/KhronosGroup/glslang/blob/23baa3f7b58f0dfdccec6755c53e85c31e52efba/glslang/Public/ShaderLang.h), [GlslangToSpv](https://github.com/KhronosGroup/glslang/blob/23baa3f7b58f0dfdccec6755c53e85c31e52efba/SPIRV/GlslangToSpv.h), [Dawn SPIR-V gate](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/src/dawn/native/Device.cpp), [ParseSPIRV](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/src/dawn/native/ShaderModule.cpp).

`glslang::TShader::preprocess` documents that obtaining a preprocessed shader string is not an officially supported or fully working path. Preprocess output is not the normalization step.

### 3. Blocking: the original v1 omits ordinary host behavior

**What breaks:** An image/points demonstration is not a usable napari replacement. Missing categorical labels, multiscale updates, clipping, depth-correct volumes, interpolation, text overlays, or the host's actual blend equations changes scientific interpretation or leaves common controls broken.

**Who hits it:** napari on its first labels/3D session; glue axes and volume viewers; visbrain meshes and annotations once that host is admitted; DIVE axes, colorbars, and text.

**Required change, adopted:** Use the host-visible v1 in the scope table below and the fixtures in [Scientific fixtures](#scientific-fixtures). Inventory comes before backend implementation and records runtime calls and composed shaders. The selected napari labels subclass is `LabelVisual(TextureMixin, ImageVisual)` and builds color through `Function` and `FunctionChain`. Its volume subclass copies `VolumeVisual._rendering_methods` and adds `iso_categorical` and `translucent_categorical`. “Basic volume” and “text for a scale bar” are removed as scope descriptions. [Labels source](https://github.com/napari/napari/blob/v0.9.2/src/napari/_vispy/visuals/labels.py), [volume source](https://github.com/napari/napari/blob/v0.9.2/src/napari/_vispy/visuals/volume.py).

visbrain 0.4.5 is a PyPI release, not a resolved Git tree. phylib 2.7.1 is an import inventory. The separate phy GUI renderer is a separate admission. See the reference table.

### 4. Blocking: the driver boundary includes queries, Qt capture, and real completion

**What breaks:** Swapping only GLIR's drawing implementation leaves capability queries calling GL without a context. A normal QWidget lacks `QOpenGLWidget.grabFramebuffer()`. Treating every wait as forbidden breaks napari's explicit `context.finish()`. A capture of a stale swapchain image, or a capture that ignores resolve, crop, alpha, or row origin, fails the host screenshot.

**Who hits it:** napari 0.9.2. `get_max_texture_sizes` reads `GL_MAX_TEXTURE_SIZE` and raw enum `32883` (`GL_MAX_3D_TEXTURE_SIZE`). `VispyCanvas.screenshot` calls `on_draw` and then `self.native.grabFramebuffer()`. Layer removal calls `self._scene_canvas.context.finish()` inside `suppress(AttributeError, GLError)`. `QtViewer` parents that canvas. [Queries and blend definitions](https://github.com/napari/napari/blob/v0.9.2/src/napari/_vispy/utils/gl.py), [capture and finish](https://github.com/napari/napari/blob/v0.9.2/src/napari/_vispy/canvas.py), [QtViewer](https://github.com/napari/napari/blob/v0.9.2/src/napari/_qt/qt_viewer.py).

**Required change, adopted:** Implement the Qt and capture contract below. `grabFramebuffer()` and `context.finish()` are mandatory compatible wrappers on this fork. `finish()` is a GPU completion barrier. Interactive frames do not take that barrier. The `QOpenGLWidget.paintGL` path that clears only alpha is a widget workaround and is not copied onto the new QWidget.

### 5. High: GLIR is an ordered, filtered command language

**What breaks:** There is no `SHADERS` opcode in the pinned parser. Flattening uploads to the start of a frame, keeping only the latest uniform, or re-running `_filter` across flush boundaries changes draws that update resources between uses. Clear, scissor, framebuffer nesting, shared objects, and state changes require ordered pass boundaries.

**Who hits it:** multi-layer compositing, repeated Program draws, text atlas growth, clipping, framebuffer filters, and multiple canvases.

**Required change, adopted:** Keep the Python emitters and `_GlirQueueShare._filter`. Execute the filtered stream with the state, generation, and snapshot rules in [Ordered GLIR execution](#ordered-glir-execution). Derive every opcode from the pinned emitters listed there. The commented `SHADERS` branch is not an opcode.

### 6. High: one projection fix cannot establish screenshot parity

**What breaks:** Cameras are only one source of positions. Custom GLSL writes clip coordinates directly. Flipped framebuffer coordinates affect texture sampling, fragment coordinates, point coordinates, clipping, culling, and derivative signs. Logical-pixel sizes, fractional DPI, surface gamma, and alpha conventions can all pass the triangle test while corrupting host screenshots.

**Who hits it:** image/label overlays, scale bars, 3D meshes, volumes mixed with points, transparent exports, and users moving a window between monitors.

**Required change, adopted:** Define a renderer-wide coordinate/color contract and test it at shader entry points, render targets, capture, and Qt events. Apply clip-depth conversion after the user vertex shader, leaving Python camera/transformation math in OpenGL coordinates. Preserve the host's separate RGB/alpha blend factors; do not globally premultiply scientific layer colors. Use the parity gates and fixtures below.

### 7. High: Dawn alone does not establish a speed advantage

**What breaks:** A resident 4K image pan can already be a cheap uniform update in OpenGL. Point quads increase vertex work and overdraw, and upstream VisPy already has an instanced marker path. Volume rendering is often limited by sampling and fragment work. Moving driver calls into C++ does not remove Python scene traversal, host slicing, or CPU data conversion. A probe that omits the presentation Y flip and format conversion understates the frame that users see. A count of Dawn `Queue.Submit` calls is not a count of `vkQueueSubmit`.

**Who hits it:** all three promised performance workloads.

**Required change, adopted:** Record reference timings in slice 1, instrument the first Dawn draw in slice 2, and run workload probes before completing visual parity. Include the GPU presentation flip and any channel/format conversion in those probes. Report Dawn submit counts and backend submit counts separately. Compare against the fastest applicable upstream path, including instanced markers. Raw Vulkan could offer more control over allocation, descriptors, validation overhead, and indirect execution; it would not eliminate bandwidth or overdraw limits, and it is not a v1 fallback. [Upstream marker implementation](https://github.com/vispy/vispy/blob/v0.17.0/vispy/visuals/markers.py), [Vulkan queue submit](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/src/dawn/native/vulkan/QueueVk.cpp).

### 8. High: “no copy,” portable binaries, and GPU-free CI are overstated

**What breaks:** nanobind can avoid copying at the Python/C++ boundary, but Dawn uploads still stage or copy data. Noncontiguous arrays, row alignment, texture conversion, and source lifetimes need explicit handling. A source hash alone does not identify a reusable native pipeline binary. A CI machine without a GPU cannot establish hardware correctness, presentation, or performance.

**Who hits it:** large streaming images/points, wheel users on every OS, and release qualification.

**Required change, adopted:** Use the upload and retirement rules below. Cache translated artifacts separately from in-memory pipelines. Pin the native toolchain. Build wheels early. Use CPU, software-Vulkan, and real-hardware CI tiers. Standard CPython wheels come first. nanobind's stable ABI option does not automatically make retained upstream compiled helpers ABI-independent. [ndarray ownership and conversion](https://nanobind.readthedocs.io/en/latest/ndarray.html), [nanobind packaging](https://nanobind.readthedocs.io/en/latest/packaging.html).

## Replacement contract and reference versions

The compatibility target is an upstream VisPy **0.17.0 source fork**, including its public modules, Python class identities within the installation, signatures, events, subclass hooks, composer, transforms, scene widgets, and Python cameras. Preserve upstream source, assets, and licenses, and document each internal deviation. Do not implement a selection of lookalike classes from scratch. [VisPy 0.17.0 release](https://pypi.org/project/vispy/0.17.0/).

The annotated tag object `v0.17.0` is `59b7b96e5cdec4cbd7a05f1b81d1a35c316035d0` and points at commit `117b054598f4758b598f4b8f48feea48c11fe7b0`. Behavior is read from that commit.

| Input | Initial pin | Purpose |
| --- | --- | --- |
| VisPy | `v0.17.0`, commit `117b054598f4758b598f4b8f48feea48c11fe7b0` | API/source and OpenGL oracle |
| napari | `0.9.2`, commit `595639295a153c84bcb127a9e07d801355440a35` | Primary host; requires `vispy>=0.17.0,<0.18` |
| glue-vispy-viewers | `1.4.0`, commit `33509adb53909b7542069563f77fb9a80bd565a4` | Qt scatter/volume host importing top-level VisPy |
| visbrain | PyPI `0.4.5` | Candidate mesh/markers/lines/text/camera host after the sdist is unpacked |
| phylib | `2.7.1`, annotated tag object `c9cc6ca910948a3948f9dd9abee08006873bd80a` | Import/dependency inventory; peel the tag before citing a tree commit |
| DIVE | commit `aa575e1c020f0c5e8227bfb234fa192fa2b12924` | Source-distributed Qt host |
| napari-threedee | commit `7bd485085186ebe1907f8de931aa7a93e0d58a83` | Plugin admission candidate plus a synthetic subclass/shader fixture |
| Dawn | commit `499e5c6ff9b37d5de70c6493fb74c251e0d35c1c` | Initial native API/build candidate, not yet build-qualified |

visbrain 0.4.5 was uploaded to PyPI on 2019-09-10. The wheel `visbrain-0.4.5-py3-none-any.whl` has sha256 `b483683577a619d565212ae0e0b35091f72258173f8cae5850152938b359ad84`. The sdist has sha256 `1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6`. Project metadata points at `https://github.com/EtienneCmb/visbrain/archive/v0.4.5.tar.gz` and requires `vispy>=0.5.3`. During this review, GitHub refs `0.4.5` and `v0.4.5` returned no commit on `EtienneCmb/visbrain` and on `visbrain/visbrain`. Slice 1 unpacks the PyPI sdist, checks the hash, and records the tree. The historical VisPy requirement does not prove that 0.4.5 runs on VisPy 0.17.0. A rendering workload is admitted only after that run succeeds on upstream 0.17.0.

phylib's tag object is not the peeled commit. Slice 1 peels it and records the commit before any import inventory cites paths. phylib is not a GPU benchmark. If the intended target is the **phy GUI**, that is a separate admission: `phy/plot/base.py` in cortex-lab/phy is its own renderer and is not switched by installing `vispy`. [phy renderer](https://github.com/cortex-lab/phy/blob/master/phy/plot/base.py).

The napari requirement was checked against its release source. [Pinned napari metadata](https://github.com/napari/napari/blob/v0.9.2/pyproject.toml). The plugin pin is a candidate until its upstream-reference fixture runs. The reviewed tree contains `src/napari_threedee/_backend/manipulator/vispy_manipulator_visual.py`, `vispy_visual_data.py`, and `tests/test_manipulator_visual_data.py`. It does not contain a file named `vispy.py` in the portion of the tree reviewed. Use those two manipulator modules. [Plugin repository](https://github.com/napari-threedee/napari-threedee).

Dawn DEPS at the candidate commit, to freeze with checksums in slice 1a and qualify in slice 2:

| Dependency | Path in Dawn | Revision |
| --- | --- | --- |
| glslang | `third_party/glslang/src` | `23baa3f7b58f0dfdccec6755c53e85c31e52efba` |
| SPIRV-Headers | `third_party/spirv-headers/src` | `86f980c731e62ae4eaf383d320449d71687936bf` |
| SPIRV-Tools | `third_party/spirv-tools/src` | `ce818d1f2db53916d89fa1fe0012237779480a9b` |
| Tint | inside Dawn, `src/tint` | same Dawn commit; there is no separate DEPS pin |

Inventory both static imports/subclasses and runtime calls: gloo operations, private fields, raw GL accesses, Qt native methods, filters, expanded shader pairs, formats, uniforms, blend states, and picking. Exercise alternate UI modes. Record exact Python, NumPy, Qt, plugin, and host versions in separate locked environments. Qt5 and Qt6 hosts do not need to share one process.

If a named host cannot run with upstream 0.17.0 in its reference environment, record that as a host blocker before claiming support. If a required path cannot be represented through Dawn, that host fails admission. A v1 release requires napari, selected visual-constructing plugins, current glue, an admitted visbrain fixture, and DIVE fixtures to pass. “Other VisPy apps” means the documented compatible API/feature subset, backed by upstream tests.

## Revised v1

Windows 10/11 x86-64 and Linux x86-64 use only Dawn Vulkan. macOS 13+ on arm64 and x86-64 uses only Dawn Metal. Linux Qt presentation initially supports X11, including `xcb` through XWayland; pure native Wayland is deferred. Support PyQt5 for legacy hosts and PyQt6/PySide6 for current hosts in separate environments. Initial wheel support is standard CPython 3.10–3.14; the development baseline is 3.12.

| Area | Required v1 behavior |
| --- | --- |
| Python extension surface | `Canvas`, `SceneCanvas`, `Visual`, `VisualView`, scene nodes/widgets, compound visuals, filters, `Function`, `FunctionChain`, transforms, events, 2D and 3D cameras; existing subclasses and GLSL hooks work |
| gloo | `Program`, indexed/instanced drawing, vertex/index buffers and views, partial updates, constant attributes, `Texture2D`, `Texture3D`, host-used LUT textures, `RenderBuffer`, nested `FrameBuffer`, clear/viewport/scissor, and inventoried `set_gl_state`/query/control behavior |
| Images and labels | Scalar and RGB(A) images; existing clim, gamma, colormaps, NaN behavior and host-used interpolation; categorical lookup and nearest-neighbor label semantics; editing/subregion uploads; host-managed multiscale levels, tile/subregion updates, and slice changes |
| Points/lines/shapes | Existing marker symbols, sizes, edge widths, antialiasing, scaling, spherical depth/shading, and instanced mode; host-used line joins/caps/widths, polygons, arrows, vectors, tracks, and selection outlines |
| Mesh and layout | Flat/smooth shading and inventoried filters; 3D cameras; clip planes; ViewBox/Grid clipping, depth/stencil and polygon offset where used; axes/colorbars and multiple viewports |
| Volumes | `mip`, `minip`, `attenuated_mip`, `translucent`, `additive`, `iso`, `average`; napari `iso_categorical` and `translucent_categorical`; ray and plane depiction, clipping, thresholds, gradients, sampling step, interpolation, opacity, and fragment depth; RGB(A) variants exposed by admitted hosts |
| Text | Existing glyph rasterization/atlas and SDF behavior for host annotations, axes, labels, colorbars and scale bars; fonts, anchors, rotation and DPI |
| Compositing | Upstream presets and actual host states, including napari `translucent_no_depth`, `minimum`, `multiplicative`, layer opacity, first-layer behavior, and multi-channel additive stacks; preserve draw order and separate alpha factors |
| Canvas and Qt | Parentable QWidget, host subclassing, timers/events and coordinate mapping, shared-resource lifetimes, resize/reparent/show/hide, multiple canvases, capture, and offscreen `canvas.render()` including region/size/alpha behavior |

Keep multiscale selection and host slicing in Python. The renderer honors updates and transforms and leaves unchanged levels unuploaded. This is not a new out-of-core scheduler. Preserve data normalization used by the reference. Internal GPU upload paths are added only where results remain equivalent.

Picking is initially excluded. An admitted host or plugin's actual picking path becomes mandatory before that admission. This exception does not expand v1 to every gallery feature.

## Renderer architecture

### Python/C++ boundary and device ownership

Python owns all subclassable application objects and executes the existing composer. C++ owns resource registries, ordered GLIR interpretation, shader compilation/reflection, uniform packing, resource updates, pipeline and bind-group caches, command recording, surfaces, submission, and readback. Use `nanobind_add_module` for `vispy._dawn`. Parse a flushed command batch. Keep array payload owners alive across the binding. Avoid one binding call per uniform or primitive.

A contiguous NumPy array crosses as `nb::ndarray` with an explicit contiguity constraint and an owner object. That binding-boundary transfer is not GPU zero-copy. `rv_policy::reference` without an owner is reserved for storage the extension itself keeps alive. `forcecast` is an explicit compatibility copy and is counted.

Use a small internal `Device` interface for capabilities, resources, program compilation, frame recording and submission, surface lifecycle, and readback. Its types describe resources and render state. They do not export Dawn handles to Python. Implement only `DawnDevice`. Share one device where compatible canvases share a VisPy context. Keep independent per-canvas targets and state. Reject cross-device sharing.

`device_info()` reports the Dawn backend (`Vulkan` or `Metal`), adapter type, vendor, device, driver, and the limits actually granted. A hardware run fails if the selected adapter is a software adapter. Software runs are a separate, labeled tier.

Keep Python gloo queue merging, resource IDs, variable introspection, errors for unset inputs, and shader invalidation. Implement inventoried GL query and control wrappers directly against Dawn limits. Unsupported calls fail with the operation, object or visual, and capability. There is no silent OpenGL fallback.

### Ordered GLIR execution

The opcode set comes from [vispy/gloo/glir.py](https://github.com/vispy/vispy/blob/117b054598f4758b598f4b8f48feea48c11fe7b0/vispy/gloo/glir.py) and the emitters in `program.py`, `buffer.py`, `texture.py`, `framebuffer.py`, and `wrappers.py` at the same commit. The module docstring lists 15 commands: `CURRENT`, `CREATE`, `DELETE`, `UNIFORM`, `ATTRIBUTE`, `DRAW`, `SIZE`, `DATA`, `WRAPPING`, `INTERPOLATION`, `ATTACH`, `FRAMEBUFFER`, `FUNC`, `SWAP`, `LINK`. `TEXTURE` is implemented in `GlirParser._parse` and is absent from that list of 15. The `SHADERS` branch is commented out. `SWAP` is documented and is not a branch in desktop `_parse`; an unexpected `SWAP` takes the invalid-command path. Present is a Qt frame-boundary action, not a reconstructed `SWAP` opcode.

`CREATE` class strings in `_classmap` are `VertexShader`, `FragmentShader`, `GeometryShader`, `Program`, `VertexBuffer`, `IndexBuffer`, `Texture1D`, `Texture2D`, `Texture3D`, `TextureCube`, `RenderBuffer`, and `FrameBuffer`. The docstring's "10 classes" omits `Texture1D` and `TextureCube`. The interpreter accepts the classmap, not the shorter docstring.

| Opcode | Who emits it | Payload at the pin | C++ effect |
| --- | --- | --- | --- |
| `CURRENT` | `GLContext.flush_commands`, injected as `parser.parse([('CURRENT', 0, fbo)])` before `glir.flush`. It is not queued in `GlirQueue`. `fbo` is `canvas._backend._vispy_get_fb_bind_location()` or `0`. | `('CURRENT', 0, fbo)` | Clear `env`. Bind the canvas target. `fbo == 0` means the canvas surface, because the new widget has no GL default framebuffer. |
| `CREATE` | `GLObject` construction | `('CREATE', id, class_name)` | Allocate a new object generation for `id`. |
| `DELETE` | object deletion | `('DELETE', id)` | Mark `JUST_DELETED` for the rest of this parse. GPU retirement waits for completion. |
| `SIZE` | `Buffer.resize_bytes`, same-size `set_data` discard, texture and renderbuffer resize | `('SIZE', id, size_or_shape, optional format, optional internalformat)` | Bump the allocation generation when size or format changes. A same-size `SIZE` still participates in filtering. |
| `DATA` | `Shader.code` after `preprocess`, `Buffer.set_data` / `set_subdata`, texture upload | `('DATA', id, offset, payload)`. Shader offset is the hardcoded `0` and payload is source text. Buffer offset on `Buffer` is bytes. | Bump the content revision. Copy into staging owned by this command. |
| `ATTACH` | `Program.set_shaders`; framebuffer attach | Program: `('ATTACH', program_id, shader_id)`. Framebuffer: `('ATTACH', framebuffer_id, attachment, object_id)` with attachment `color`, `depth`, or `stencil`. | Record shader or attachment linkage. |
| `LINK` | `Program.set_shaders` after `ATTACH` | `('LINK', program_id)` | Build the program artifact from attached shader `DATA`. Detach is a parser-side GL behavior; Python already calls `shader.delete()`. |
| `UNIFORM` | `Program.__setitem__` for numeric and array uniforms | `('UNIFORM', program_id, name, gtype, raveled_array)` | Store pending uniform values. They are copied into the draw snapshot. |
| `ATTRIBUTE` | `Program.__setitem__` | Buffer form: name, type, `(buffer_id, stride, offset)`, divisor. Constant form: `tuple([0] + components)`, divisor. | Record the binding. Constants become a cached internal buffer when the backend has no immediate attribute. |
| `TEXTURE` | sampler assignment | `('TEXTURE', program_id, name, texture_id)` | Record the sampler name to texture generation. |
| `DRAW` | `Program.draw` on `canvas.context.glir` | `('DRAW', program_id, mode, selection, instances)`. `selection` is `(start, count)` or `(index_id, 'UNSIGNED_BYTE'/'UNSIGNED_SHORT'/'UNSIGNED_INT', count)`. | Capture one immutable snapshot. |
| `WRAPPING` | texture | wrapping modes | Sampler state. |
| `INTERPOLATION` | texture | min and mag, `nearest` or `linear` | Sampler state. |
| `FRAMEBUFFER` | `FrameBuffer` activate and deactivate | `('FRAMEBUFFER', id, use_bool)` | Push or pop `env['fb_stack']`. Deactivate rebinds the previous target, seeded from `env['fbo']`. |
| `FUNC` | `BaseGlooFunctions` setters, `clear`, `set_state`, `finish`, `flush` | `('FUNC', gl_function_name, *args)`. The second tuple slot is the function name, not an object id. `GlirParser._parse` does `getattr(gl, id_)`. | Apply named state, or a completion/flush barrier. |
| `SWAP` | documented, not handled by desktop `_parse` | none accepted | Ignore as a present. Record if inventory finds an emitter. |
| `SHADERS` | commented branch only | absent | Do not implement. |

`Shader.code` assigns `preprocess(code)` and then emits `DATA`. `Program.set_shaders` builds `VertexShader` and `FragmentShader`, and `GeometryShader` when `geom` is set, associates their queues, emits `ATTACH` per shader, emits `LINK`, and deletes the shader objects. It reparses variables from the stored source and re-emits pending uniforms and attributes. Geometry shaders that survive inventory still fail closed unless a specific host algorithm has an admitted geometry-generation replacement.

`Program.draw` associates the program queue with the canvas queue, derives `instances` from divisor attributes, emits `DRAW`, and the queue docstring states that drawing pushes commands to the shared parser. Slice 1 copies the exact flush call that follows the `DRAW` emission in `Program.draw`.

`_GlirQueueShare._filter` walks one flush from the end. After it sees `SIZE` for an id, it drops earlier `SIZE` and `DATA` for that same id and keeps every other opcode, including an earlier `DRAW`. The filter applies only to commands still in that flush. A later flush does not reopen commands already parsed. The C++ batch is the concatenation of these already-filtered flush sequences. The interpreter does not run `_filter` again across flush boundaries, and it does not move a later `DATA` above an earlier `DRAW`.

Two `DRAW` commands that differ only in uniform values stay two snapshots. Two `DRAW` commands separated by `DATA` stay two snapshots with two content revisions.

#### Context state

One `GLShared.parser` is shared by canvases that share a VisPy context. The C++ context mirrors that object:

- An object table keyed by the Python integer id.
- `JUST_DELETED` entries removed at the start of the next `parse`, matching `GlirParser.parse`.
- `env`, cleared on every `CURRENT`. It holds `fbo` and `fb_stack`.
- Per-canvas target, viewport, scissor, blend, depth, stencil, color mask, cull, and polygon offset, because `FUNC` mutates the current canvas and `CURRENT` switches canvases.
- Capabilities reported from the Dawn device, not from a GL context.

`GLContext.flush_commands` is the Python flush boundary. `finish` emits `FUNC glFinish` and then calls `flush_commands`. Upstream desktop `glFinish` waits. The docstring says a remote interpreter may return early. This fork waits: napari calls `finish()` so that deletions complete before the next scene-graph update. `flush` emits `FUNC glFlush` and flushes the queue; it parses commands and does not promise GPU completion. `read_pixels` bypasses GLIR, calls `glReadPixels`, and returns `im[::-1, ...]`. The replacement capture uses the same row origin.

#### Generations, artifacts, and snapshots

Each object has an allocation generation and a content revision.

- `CREATE` allocates generation 1 and content revision 0.
- `SIZE` that changes byte size, shape, or format increments the allocation generation and resets the content revision. The previous GPU allocation remains until every snapshot that names it has completed.
- `DATA` increments the content revision and does not reallocate when the range fits.
- A same-size `SIZE` inside a flush exists so `_filter` can drop earlier `DATA`. After filtering, the surviving `SIZE` plus `DATA` is the new content. The interpreter still executes that surviving pair in order.
- `DELETE` invalidates the id for later commands in the same parse. In-flight snapshots keep the generation they captured.

A program artifact is immutable and keyed by the attached shader `DATA` strings plus the `LINK` that closed them:

- original composer GLSL, retained in Python on `Program` and `ModularProgram`
- normalized GLSL per stage
- SPIR-V words per stage
- Tint diagnostic log and generated WGSL when the debug artifact path is on
- reflection: uniform block offsets and strides, sampler bindings, attribute locations
- source map from composer line/column through normalized GLSL and SPIR-V to Tint diagnostics

`set_shaders` / `LINK` builds a new artifact and drops the old one after in-flight draws complete. An ordinary `UNIFORM` or `ATTRIBUTE` does not rebuild it. Pending variables are re-emitted by Python after `set_shaders`; the interpreter consumes those commands and does not invent values from the previous program.

At each `DRAW` the interpreter freezes a snapshot. The snapshot holds ids plus generations, never a live pointer:

- program artifact id
- pipeline key
- uniform bytes packed at reflected offsets, including a distinct copy when the same program is drawn twice
- texture and sampler bindings at their content revisions
- vertex and index bindings with stride, offset, divisor, topology, and instance count
- framebuffer generation and the clear, viewport, scissor, blend, depth, stencil, and color-mask state at that point in the stream

#### Frames, tickets, and surfaces

Successive `flush_commands` calls append to the open frame in parse order. The frame is submitted at the Qt paint boundary, at `canvas.render()`, at `grabFramebuffer()`, at `finish()`, and when an ordering hazard requires a submit before a later read. Ordinary flushes do not each call Dawn `Queue.Submit`.

A frame uses one slot from a fixed-size ring. Each submit returns a completion ticket. The slot's CPU snapshot, staging bytes, and GPU resources stay alive until the ticket completes. The ring does not overwrite a busy slot. If every slot is busy, the canvas schedules another submission from the event loop. It does not grow the ring without a bound.

A surface generation increments when the native handle is created or replaced, when the physical size changes, when the surface is lost, or when the device is lost. Snapshots record the generation they targeted. After the ticket completes, resources for a retired generation are destroyed. They are not reused for the new surface.

Device loss is reported to Python on a thread that may take the GIL. The affected canvas recreates its device and surface or closes. Stale Dawn objects from the lost device are dropped with the device.

#### Required order proofs

`tests/gloo/test_program_parity.py` keeps these cases, each compared with the OpenGL oracle:

1. Draw, change a uniform, draw. The two fragments differ, and the first draw keeps the first value.
2. Draw, `set_data` or `set_subdata` on a vertex buffer, draw. The second draw sees the new bytes and the first draw keeps the old bytes.
3. Draw, partial texture update, draw. Include a same-flush `SIZE` that discards an earlier `DATA` for that id, and a second flush whose `DATA` does not erase a draw already parsed.
4. Draw into a framebuffer, switch with `FRAMEBUFFER`, sample that attachment in a later draw. The sample sees the first pass.
5. Two canvases sharing one `GLShared` parser. `CURRENT` clears `env` and selects the right target. Object ids remain shared.
6. Record a draw that uses a buffer or texture, then resize or `DELETE` it before the submit ticket completes. The in-flight snapshot stays valid. The id is reusable only after `JUST_DELETED` is cleared and a new `CREATE` arrives. The GPU allocation is freed only after the ticket.

### Upload, capture, and retirement

Contiguous CPU NumPy inputs cross nanobind without a binding copy. Hold the GIL, or an owner that keeps the buffer alive, until the staging copy into C++-owned memory has returned. Honor `set_data(copy=...)`. Test mutation of the NumPy array after the call returns and before the deferred flush, for both `copy=False` and `copy=True`.

Structured arrays are described, not guessed. For each `VertexBuffer` view record dtype, itemsize, field name, field offset, shape of the field, stride, and divisor. `MarkersVisual._upload_data` builds one structured array with fields `a_position` (float32, 3), `a_fg_color` (float32, 4), `a_bg_color` (float32, 4), `a_size` (float32), `a_edgewidth` (float32), and `a_symbol` (float32), then assigns `self._vbo[name]` and sets `divisor = 1` in instanced mode. The upload path must accept that view.

Explicit compatibility copies, each counted in the probe byte counter:

- noncontiguous or misaligned arrays
- Dawn row-pitch padding
- RGB, luminance, and other formats that the device cannot store directly
- label integers that cannot be sampled as the host dtype without the host's existing remapping
- constant attributes lowered to a buffer

Returned readback arrays own their memory and remain valid after the canvas is destroyed. Awkward row widths are tested by reading a width that is not a multiple of the alignment Dawn uses.

Interactive warmed frames do not call GPU completion waits. `canvas.render()`, `grabFramebuffer()`, explicit `finish()`, shutdown, and benchmark completion may wait. Capture returns the scene produced by the `on_draw` that just ran.

Capture sequence for `grabFramebuffer` and for region-aware `canvas.render()`:

1. Run the same draw the reference would run. napari's screenshot calls `on_draw` first.
2. Render that scene into an owned color target, not into a swapchain image that presentation may replace.
3. If the canvas config requests samples (napari sets `samples` to 4 when multisampling is enabled, otherwise 0), resolve into a single-sample texture before the copy.
4. Copy the requested rectangle. Apply the reference crop. Honor `alpha=True/False` the way `read_pixels` selects RGBA or RGB.
5. Match `read_pixels`'s vertical flip exactly once. A texture sampled by a later visual is not flipped again.
6. Return a `QImage` from `grabFramebuffer`, and a NumPy array from `canvas.render` / `read_pixels`, with ownership independent of the swapchain.

Offscreen rendering requires neither a native surface nor a Qt display. Headless tests still need a hardware or software GPU.

### Shader compiler contract

Normalization is a constrained compatibility pass. It is not `TShader::preprocess`, and it is not a regex chain. The public header at glslang `23baa3f7b58f0dfdccec6755c53e85c31e52efba` says standalone preprocess output is not an officially supported or fully working path. The supported route is `TShader` environment setup and `parse`, `TProgram` link, then `GlslangToSpv` on `glslang::TIntermediate` ([GlslangToSpv.h](https://github.com/KhronosGroup/glslang/blob/23baa3f7b58f0dfdccec6755c53e85c31e52efba/SPIRV/GlslangToSpv.h)).

Any use of `TIntermediate` or other compiler-internal objects stays inside one pinned translation unit, `cpp/shader/glslang_spv.cpp`. The rest of the renderer sees SPIR-V words, a diagnostic string, and a source map. That isolation is mandatory because those glslang types are unstable across the pin.

#### Artifacts

For each linked stage pair or triple the artifact directory stores:

| Artifact | Contents |
| --- | --- |
| Input | Composer-expanded GLSL after VisPy `preprocess` and `Compiler.compile`, one string per stage, plus the Python variable list from `Program._parse_variables_from_code` |
| Normalized GLSL | Vulkan-flavored GLSL passed to glslang, still carrying original uniform and sampler names in the source map |
| SPIR-V | Validated words per stage |
| Reflection | Block offsets, matrix and array strides, sampler binding indices, attribute locations |
| Debug | glslang log, SPIR-V disassembly, Tint log, generated WGSL when debug artifacts are enabled |
| Source map | Composer line/column to normalized line/column to SPIR-V instruction to Tint diagnostic |

A failure returned to Python includes the original stage, the normalized stage, the compiler stage that failed, and the mapped line. `tests/shaders/test_corpus.py` feeds one intentional bad snippet and checks that the reported line refers to the composer source, not only to a generated line number.

#### Stages, bindings, and samplers

Vertex and fragment stages are paired by the `LINK` command. A geometry stage is rejected with the program id and a stated reason unless inventory has admitted a specific non-shader replacement. Locations are assigned in a deterministic order recorded in the artifact: attributes by the order `Program` reports them, varyings by a single shared assignment used by both stages.

Standalone uniforms move into one uniform block per program, with a layout the reflection pass records. Boolean uniforms lower to a supported integer. Matrix and array strides come from reflection, not from NumPy's packed itemsize. Dynamic offsets respect the device's minimum uniform-buffer offset alignment. Each draw snapshot gets its own uniform bytes.

Samplers are not left as legacy `sampler2D` / `sampler3D` globals paired by name at runtime. The normalization pass rewrites `texture2D`, `texture3D`, and related calls into calls of generated helper functions. Each helper takes the coordinates the user shader already computed and samples one explicit texture-plus-sampler binding. The helper's binding index is in the reflection. The Python name from the `TEXTURE` command remains the key used to fill that binding. This is how combined GLSL samplers become the separate texture and sampler resources Dawn requires, without asking Visual authors to write WGSL.

Builtins are lowered in the same pass and listed in the source map: `gl_Position`, `gl_FragCoord`, `gl_PointCoord`, `gl_FragDepth`, `gl_VertexID`, `gl_InstanceID`, and the point-size and front-face builtins that admitted shaders use. Clip-space depth is converted at the final write of the user vertex output with `z_webgpu = (z_gl + w_gl) / 2`. A fragment shader that already writes window depth in `[0, 1]` does not get a second conversion. The pass records which pattern it matched so a fixture can show the inserted operation.

#### What Dawn does with the SPIR-V

At the Dawn pin, SPIR-V is accepted through `ShaderSourceSPIRV` or `DawnShaderSourceSPIRV`, with optional `DawnShaderModuleSPIRVOptionsDescriptor`. `ParseSPIRV` is compiled only under `TINT_BUILD_SPV_READER`. It calls `tint::spirv::reader::ReadIR` ([reader.h](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/src/tint/lang/spirv/reader/reader.h)) and then `tint::wgsl::writer::ProgramFromIR` with `allow_non_uniform_derivatives` and the device's allowed features ([writer.h](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/src/tint/lang/wgsl/writer/writer.h)). When `DAWN_ENABLE_SPIRV_VALIDATION` is on, `ValidateSpirv` runs before that parse.

The fork forces all of the following, because the pin's defaults do not:

- `TINT_BUILD_SPV_READER=ON` on Windows, Linux, and macOS
- the instance feature `ShaderSourceSPIRV`
- `Toggle::DisallowSpirv` left off
- `DAWN_ENABLE_SPIRV_VALIDATION=ON` even for a Metal-only build, where the CMake default follows Vulkan or GL and would otherwise stay off
- `TINT_BUILD_WGSL_WRITER=ON` because `ProgramFromIR` is the in-process consumer
- `TINT_BUILD_MSL_WRITER=ON` on macOS and `TINT_BUILD_SPV_WRITER` as required by the Vulkan backend

`allow_non_uniform_derivatives` is set only on an artifact whose fixture demonstrates a non-uniform derivative that the reference also computes. It is not a global flag. `AllowUnsafeAPIs` and `kChromiumDisableUniformityAnalysis` stay off. A derivative failure is a corpus failure, not a toggle change.

Pipeline creation is the feasibility test. For every admitted variant, build a `PipelineLayout` and a `RenderPipeline` using the reflected bind-group layout, vertex layout, and the color and depth formats that visual will use. Do this on a Vulkan device and on a Metal device. Shader-module parse alone does not pass slice 2b. Dawn's own end-to-end tests live in `src/dawn/tests/end2end` and are a reference for how the pin creates pipelines; they are not a substitute for the VisPy corpus.

#### Cache invalidation

Disk cache key, all of it:

- hash of composer-expanded GLSL per stage
- normalization version
- glslang, SPIRV-Tools, Tint, and Dawn pins, plus compiler flags
- stage list, entry points, and binding schema version
- feature and format choices, including the non-uniform-derivative bit for that artifact

In-memory pipeline cache key adds the device id and the full pipeline key from the feature table below. A disk cache hit still creates the pipeline on the current device. There is no promise of a portable pipeline binary keyed by source. Changing any key field discards the artifact. Ordinary uniform edits miss neither cache.

### Pipeline key

The pipeline key includes translated shader and entry points and specialization values; binding layouts and texture sample types; vertex formats, strides, and step modes; topology and strip index format; all color, depth, and stencil attachment formats; color write masks and separate blend components; depth test, write, and bias; stencil state; front face and culling; sample count and alpha-to-coverage. Viewport, scissor, resources, and uniform values stay dynamic where the backend allows. Bind-group caching is separate and is invalidated when views, samplers, or resource generations change.

### Feature policy

| Feature | Actual limitation and v1 treatment |
| --- | --- |
| Point sprites | WebGPU point primitives cannot implement arbitrary GL point size or coordinates. Reuse upstream's instanced marker path where `MarkersVisual.method == 'instanced'`. Lower admitted gloo point-sprite shaders to instanced quads while preserving their vertex logic, fragment hooks, coordinates, size, scaling, clipping, and spherical depth. No Python loop over points. |
| Wide lines | WebGPU has no programmable wide-line width. `LineVisual` has `method='agg'` (`_AggLineVisual`, baked structured vertices) and `method='gl'` (`_GLLineVisual`). Widths above 1 px are only guaranteed on the Agg path. Retain supported baked Agg geometry and implement segment, join, and cap expansion for required GL-style widths, preserving DPI and connectivity. A vertex shader cannot replace arbitrary geometry-shader output. [line.py](https://github.com/vispy/vispy/blob/v0.17.0/vispy/visuals/line/line.py). |
| Geometry and tessellation | No general emulation. If inventory finds a known host algorithm, implement that geometry generation and keep the public visual contract. Arbitrary user geometry or tessellation shaders fail explicitly. |
| Integer and label textures | Supported formats have sampling restrictions. Preserve categorical identity, nearest sampling, and LUT indexing. Never convert large label IDs through float32 unless the host already does that remapping and the fixture shows the same integers. Test signed and unsigned values, sparse IDs, background, and edited tiles. |
| Scientific texture formats | Negotiate features and keep a format table. GL RGB, luminance, and normalized 16-bit formats are not assumed to match baseline WebGPU formats. Expansion and conversion must reproduce normalization and are included in upload costs. Unfilterable float textures need a verified interpolation path. |
| 3D textures and raycasting | Dawn supports 3D textures and fragment raycasting. Preserve loop, step, threshold, and accumulation semantics. Do not lower the sample count to meet a speed target. |
| Clipping, fragment depth, derivatives | `Clipper` discards from `gl_FragCoord` against a rectangle. `PlanesClipper` discards against planes. Fragment depth and derivatives exist; preserve volume and marker depth and derivative orientation. Explicit LOD for a proven single-level volume can resolve one implicit-derivative validation failure. It is not a global replacement for mipmapped sampling. [WGSL uniformity](https://gpuweb.github.io/gpuweb/wgsl/#uniformity). |
| Polygon offset and stencil | Translate admitted depth-bias and stencil states. Qualify depth-format differences with overlap tests. GL offset units are not assumed to equal WebGPU depth bias. |
| MRT | WebGPU supports multiple color attachments within format, count, and bytes-per-sample limits. Implement the inventoried attachment subset when a host uses it. The full gallery MRT surface is not automatic scope. |
| Logical operations | Not a general WebGPU render state. No silent replacement by blending. A required operation needs a proven equivalent multipass or the host fails admission. |
| Limits | Query the adapter, request the limits admitted hosts need, and report the resulting device limits to Python. Defaults are not the hardware maximum. Validate texture dimensions, buffer and binding sizes, vertex attributes, samplers, and attachment budgets before allocating. Preserve the host's resizing and downsampling decisions. [WebGPU limits](https://gpuweb.github.io/gpuweb/#limits). |

## Qt, coordinates, and pixel parity

Refactor `vispy/app/backends/_qt.py` while retaining its mouse, key, wheel, touch, modifier, focus, timer, and DPI translation. `QtBaseCanvasBackend` is the event base. `CanvasBackendDesktop` currently subclasses `QGLWidget`, which at this pin is an alias of `QOpenGLWidget` for PyQt5 (Qt >= 5.4), PyQt6, PySide6, and PySide2 (Qt >= 5.4). The replacement subclasses `QWidget` and is parentable. It is not a `QOpenGLWidget`. Keep backend names `PyQt5`, `PyQt6`, and `PySide6` and the existing selection precedence. `use(gl='gl+')` selects the compatible instanced path and does not load a system GL driver. Unsupported window backends fail clearly.

`canvas.native` is that QWidget. Python supplies platform-typed handle data. C++ creates and owns the Dawn surface.

| Platform | Handle the widget must supply | Surface rule |
| --- | --- | --- |
| Windows | HWND plus the instance data Dawn's Windows surface requires | Recreate the surface when the native handle changes |
| X11 | `Display*` and XID. An untyped integer is not enough | Linux v1 is X11, including XWayland. `winId()` is not treated as `wl_surface*` |
| macOS | NSView plus a retained `CAMetalLayer` from an Objective-C++ helper | Drawable size is the physical pixel size |

Do not link a second Qt into the native extension.

Lifecycle, all on the Qt GUI thread, all required in slice 3a:

- native-handle creation and `WinIdChange`
- reparent into an existing layout and into napari's canvas container
- zero-size and minimized widgets, with no submit of a zero drawable
- resize, including `screen_changed`, which today calls `resizeGL` after a monitor move
- scale factors 1, 1.25, 1.5, and 2, and a move between monitors
- welcome widget and child overlays stacking above the canvas; screenshots include the documented content and do not include overlays that the reference excludes
- destruction while a frame ticket is in flight
- device loss and surface loss

`resizeGL` multiplies logical size by `devicePixelRatioF()` when that method exists and emits `resize` with logical `size` and `physical_size`. Keep that split. The new-API `paintGL` alpha-only clear stays deleted with `QOpenGLWidget`.

The rendering contract is:

- Preserve OpenGL coordinates inside user shader and transform computations. At the final vertex output map clip depth with `z_webgpu = (z_gl + w_gl) / 2`, covering direct `gl_Position` writes and every return path. Fragment shaders that already write window depth in `[0, 1]` do not receive a second conversion.
- Texture and render-target row zero is OpenGL's low-Y row. Preserve uploaded texture row order. Negate final vertex clip Y so Dawn writes that convention, then flip Y in a GPU presentation pass. GL viewport, scissor, and fragment-coordinate values keep their numeric low-Y convention inside the renderer. Map front-face and point-coordinate semantics once and verify derivative signs. Capture applies the `read_pixels` flip once.
- Logical dimensions and event positions stay logical. Target dimensions, scissors, and pixel-sized visuals use the reference physical-pixel conventions.
- Select color, depth, and sample formats explicitly. Match upstream color transfer and the separate RGB and alpha equations. Do not apply an accidental sRGB conversion at presentation. A surface that needs a different encoding or channel order uses one defined conversion pass, and that pass is inside the timed frame. Premultiplication for the Qt compositor happens at the output boundary only.

Dawn `Queue.Submit` accounting, from the pin: `Queue::SubmitImpl` in `src/dawn/native/vulkan/QueueVk.cpp` records every WebGPU command buffer in the submit into the current recording context and then calls `SubmitPendingCommandsImpl`. That function issues one `vkQueueSubmit` (`QueueSubmit(mQueue, 1, &submitInfo, fence)`) containing however many `VkCommandBuffer`s the recording context holds. Present, readback, and initialization can submit on their own. Probes report three numbers: application-level frame presents, Dawn `Queue.Submit` calls, and backend submits (`vkQueueSubmit` on Vulkan, command-buffer commits on Metal). An ordinary onscreen frame targets one Dawn submit and one present. Resource initialization, `finish()`, capture, and hazard splits are allowed to add submits and must be visible in the counters.

A corner triangle is a diagnostic. Parity fixtures are the set in the next section.

Capture the OpenGL oracle and the Dawn output with the same data, transforms, fonts, interpolation, quality, sample counts, and render dimensions. Keep raw RGBA and a difference image. Initial acceptance is a maximum absolute difference of 2/255 per channel on defined interior pixels, and at most 0.1% differing pixels inside a fixed one-pixel edge band. Declare masks before looking at the candidate. Categorical regions, landmark positions, and occlusion decisions are exact. No global alignment, blur, gamma fitting, or later widening of the tolerance. Where a screenshot cannot prove label identity, clim, or depth, the fixture adds a numeric check.

Run the pinned upstream test suite with headless render tests pointed at a Dawn offscreen app backend. Preserve assertions. Keep a capability manifest that separates supported tests, genuine upstream skips, and explicit non-goal tests. Headless execution still needs a hardware or software GPU.

## Scientific fixtures

These fixtures are the acceptance set. Parameters are frozen in slice 1c and reused by later slices. Seeds are integers stored next to the arrays.

**Images.** `ImageVisual` data of shape `(M, N)`, `(M, N, 3)`, and `(M, N, 4)`. Dtypes: `uint8`, `uint16`, `float32`, plus `int8` and `int16` after the conversion `napari._vispy.utils.gl.fix_data_dtype` performs (its documented acceptable set is int8, uint8, int16, uint16, float32). Clim `"auto"` and an explicit narrow window. A float image with a NaN block: GPU scaling discards single-band NaNs, CPU scaling maps them to 0, matching `ImageVisual`'s documented split. Gamma not equal to 1. One continuous colormap and one LUT. Interpolation `nearest` and `linear`. A 4096×4096 resident scalar image and a 4096×4096 RGBA image.

**Labels.** Exact integer IDs, including background 0, a sparse high ID, and at least one negative ID when the dtype is signed. The rendered category of each region equals the input ID after the host LUT. IDs that do not fit in float32 mantissa stay exact; if the host remaps them, the fork uses that remapping and the fixture lists the map. Sampling is nearest. One tile `set_data` with an offset updates only that rectangle. A multiscale stack changes the displayed level and leaves the other levels' content revisions unchanged.

**Partial updates.** A buffer `set_subdata` of a middle slice. A texture sub-rectangle. One flush containing an early `DATA`, a `DRAW`, a `SIZE`, and a later `DATA` for the same id, asserting the filter result documented above. A second flush that updates the same buffer after the first draw has been parsed.

**Points.** One million points, fixed seed, positions in a structured array using the `MarkersVisual` field layout. Compare `method='points'` and `method='instanced'`. Include a small disc, a large symbol, edge width, antialiasing, and spherical shading. Camera motion with no vertex upload. A color-only change. A full position replacement.

**Volumes.** An analytic sphere or ellipsoid on a grid, with a known iso value and a known MIP voxel. Modes: `mip`, `minip`, `attenuated_mip`, `translucent`, `additive`, `iso`, `average`, plus napari `iso_categorical` and `translucent_categorical`. The categorical background value in the napari shader is 0. Same `relative_step_size`, interpolation, and camera for the oracle and the candidate. One clipping plane from `PlanesClipper`. Depth against a mesh drawn in front of the volume. Sizes 256³ and 512³ for the benchmark; a smaller phantom is allowed for the exact numeric check. Record the keys of `VolumeVisual._raycasting_modes` during slice 1 and include every mode the constructor exposes, including plane depiction.

**Text.** A font file committed under `tests/data` with its license. `FontManager(method='cpu')` and `SDFRendererCPU`, which calls `_calc_distance_field`. Strings with an anchor, a rotation, and a newline. Render at DPI 1, 1.25, and 1.5. Compare atlas texels and the final RGBA.

**Hosts.**

- napari: screenshot through `on_draw` plus `grabFramebuffer`; `context.finish()` on layer removal; blend modes `opaque`, `translucent`, `translucent_no_depth`, `additive`, `minimum`, and `multiplicative`. napari's `translucent` blend factors are `('src_alpha', 'one_minus_src_alpha', 'one', 'one')`. VisPy's preset `translucent` is `('src_alpha', 'one_minus_src_alpha', 'zero', 'one')`. The fixture uses the factors the host set.
- glue 1.4.0: top-level `scene.SceneCanvas` with `depth_size` 24, axes, scatter, and volume. This is not the older vendored-namespace release.
- visbrain: only after the PyPI sdist is unpacked and the same fixture runs on upstream VisPy 0.17.0. Until then it is an inventory item.
- DIVE: axes, colorbars, and text, starting from the paths in the navigation guide. Slice 1 records the symbols inside those files.
- phylib: import inventory after the tag is peeled. No rendering fixture.
- phy GUI: separate admission, not part of the phylib line.
- napari-threedee: manipulator visual and visual-data modules, plus plugin discovery. Admission waits on a passing fixture.

## Performance gates

Instrumentation starts with the first frame: Python traversal and update time, batch interpretation, upload and conversion bytes and time, compiler and pipeline misses, draw, pass, and submit counts, cache reuse, allocations, queue depth, GPU time where timestamp queries exist, and completed-frame latency. Report cold startup separately from warmed rendering. Submit counts follow the three-number split above.

The early slice-2 probes include the presentation Y flip and any format or channel conversion. A probe that stops at an offscreen target without that pass is labeled as such and is not the number compared with upstream presentation.

Benchmark separate reference and candidate processes on the same hardware and driver, with the same host versions and quality. Disable presentation pacing for throughput measurements and separately measure normal presentation and input-to-visible latency. Do not use `canvas.render()` timings as interactive timings. Measure completed frames. Timestamp readback and completion collection stay off the sampled interactive path.

| Workload | Required measurements |
| --- | --- |
| Large images | Resident 4096×4096 scalar and RGB(A) pan/zoom; 1 and 8 image layers with additive and translucent states; 4K viewport; full-image streaming and small edited-region uploads measured separately |
| Points | 1,000,000 points, fixed seed and camera; representative small and large symbols, edge, antialiasing, and depth settings; static camera motion, color changes, and full position updates; compare upstream instanced and point paths |
| Volumes | 256³ and 512³ scalar datasets at 1024² and a larger viewport; MIP, translucent, and iso as the primary cases; categorical, depth, and clipping checks; same step length, interpolation, thresholds, and view; resident rotation and data updates separately |

Warm at least 100 frames and measure at least 1,000 frames in five alternating reference and candidate runs. Retain median, p95, and variability. The release target is **reference median time / candidate median time >= 1.20** on each primary resident workload, with no worse p95, and no regression above 10% on admitted update workloads. Fix parameters and designated hardware before tuning. Qualify Windows and Linux Vulkan on representative integrated and discrete GPUs and macOS Metal on Apple silicon. Publish that matrix.

Unchanged-data pan or rotation has zero texture and vertex reuploads, no steady-state shader or pipeline compilation, and no deliberate completion wait. Captures and explicit barriers are outside that assertion. Software adapters are correctness only. If batching and resource reuse cannot meet the three goals at fixed quality, stop the replacement release. A raw Vulkan backend or a quality reduction does not satisfy the plan.

## Source navigation

Upstream paths below were read at the pins in the reference table. Proposed paths do not exist yet. They are the local owners for the implementation. A symbol listed here was found in the pinned file. Where a file was confirmed and its interior was not fully extracted, the investigation column says what slice 1 must still copy out.

Search a pinned checkout from PowerShell with [ripgrep](https://github.com/BurntSushi/ripgrep). Set `$Vispy`, `$Napari`, `$Glue`, `$Dawn`, and `$Glslang` to the extracted pins before running the samples.

```powershell
rg -n "^\s*\('DATA'|'UNIFORM'|'TEXTURE'|'DRAW'|'ATTACH'|'LINK'" $Vispy\vispy\gloo
rg -n "SHADERS|def _filter|JUST_DELETED|_classmap" $Vispy\vispy\gloo\glir.py
rg -n "def set_shaders|def draw|class Shader" $Vispy\vispy\gloo\program.py
rg -n "class Function|class FunctionChain|class Compiler|class ModularProgram" $Vispy\vispy\visuals\shaders
rg -n "grabFramebuffer|def finish|def screenshot" $Napari\src\napari
rg -n "TINT_BUILD_SPV_READER|ParseSPIRV|ReadIR|ProgramFromIR" $Dawn\src
rg -n "not an officially supported" $Glslang\glslang\Public\ShaderLang.h
rg -n "vkQueueSubmit|SubmitPendingCommandsImpl" $Dawn\src\dawn\native\vulkan
```

### VisPy gloo and GLIR

| | |
| --- | --- |
| Upstream | `vispy/gloo/program.py`: `Shader`, `VertexShader`, `FragmentShader`, `GeometryShader`, `Program.set_shaders`, `Program.draw`, `Program.bind`. `vispy/gloo/glir.py`: `GlirQueue`, `_GlirQueueShare._filter`, `GlirParser.parse`, `GlirParser._parse`, `convert_shader`, `JUST_DELETED`. `vispy/gloo/context.py`: `GLContext.flush_commands`, `GLShared.parser`, `set_current_canvas`, `FakeCanvas`. `vispy/gloo/buffer.py`: `Buffer`, `DataBuffer`, `DataBufferView`, `VertexBuffer`, `IndexBuffer`. `vispy/gloo/texture.py`: `BaseTexture`, `Texture2D`, `Texture3D`, `CPUScaledTexture` users live in visuals. `vispy/gloo/framebuffer.py`: `RenderBuffer`, `FrameBuffer`. `vispy/gloo/globject.py`: `GLObject`. `vispy/gloo/wrappers.py`: `BaseGlooFunctions`, `GL_PRESETS`, `finish`, `flush`, `read_pixels`. |
| Inspect | Opcode spellings, `_filter` direction, `CURRENT` injection, `FUNC` name-in-the-id-slot, commented `SHADERS`, `DataBuffer.set_subdata` offset unit, and the flush call at the end of `Program.draw`. |
| Investigation output | A machine-readable opcode table checked against this document, plus one recorded GLIR trace for each order proof. |
| Tests to reuse | `vispy/gloo/tests/` at the pin: `test_glir.py`, `test_program.py`, `test_buffer.py`, `test_texture.py`, `test_framebuffer.py`, `test_context.py`, `test_wrappers.py`, and the neighboring gloo tests in that directory. |
| Local owner | Forked copies under `src/vispy/gloo/`. Interpreter in `cpp/glir/`. |

### VisPy composer, scene, and Qt

| | |
| --- | --- |
| Upstream | `vispy/visuals/shaders/function.py`: `Function`, `MainFunction`, `FunctionChain`, `StatementList`. `compiler.py`: `Compiler`. `program.py`: `ModularProgram`. `multiprogram.py`: `MultiProgram`, `MultiShader`. `variable.py`: `Variable`, `Varying`, `InVar`. `shader_object.py`: `ShaderObject`. `parsing.py`: `parse_function_signature`, `find_functions`, `find_prototypes`, `find_program_variables`, `find_template_variables`. `vispy/scene/canvas.py`: `SceneCanvas`. `vispy/scene/widgets/viewbox.py`: `ViewBox`. `vispy/scene/cameras/`: `BaseCamera`, `PanZoomCamera`, `ArcballCamera`, `TurntableCamera`, `FlyCamera`, `MagnifyCamera`, `Magnify1DCamera`. `vispy/visuals/transforms/`: `NullTransform`, `STTransform`, `MatrixTransform`, `LogTransform`, `PolarTransform`, `ChainTransform`, `TransformSystem`, `PanZoomTransform`, `BaseTransform`. `vispy/app/backends/_qt.py`: `QtBaseCanvasBackend`, `CanvasBackendDesktop`, `CanvasBackendEgl`. |
| Inspect | How `ModularProgram` calls `set_shaders` when a `Function` changes. How `MultiProgram` builds one program per view. How `SceneCanvas` owns the root and the viewbox. Which camera writes which matrix. How `devicePixelRatioF` splits logical and physical size. |
| Investigation output | A list of composer hooks that change GLSL versus hooks that only change uniforms. A trace of one pan that changes a matrix and does not relink. |
| Tests to reuse | `vispy/visuals/shaders/tests/test_function.py`, `test_multiprogram.py`, `test_parsing.py`. Scene and camera tests under `vispy/scene/` and `vispy/scene/cameras/tests`. |
| Local owner | Forked Python under `src/vispy/visuals/shaders/`, `src/vispy/scene/`, `src/vispy/app/backends/_qt.py`. New offscreen backend `src/vispy/app/backends/_dawn_headless.py`. |

### VisPy visuals and testing

| | |
| --- | --- |
| Upstream | `vispy/visuals/image.py`: `ImageVisual`. `vispy/visuals/_scalable_textures.py`: `_ScaledTextureMixin`, `CPUScaledTextureMixin`, `GPUScaledTextureMixin`, `CPUScaledTexture2D`, `GPUScaledTexture2D`, `CPUScaledTexture3D`, `GPUScaledTextured3D` (the 3D GPU class name is spelled that way in the pin). `vispy/visuals/markers.py`: `MarkersVisual`. `vispy/visuals/line/line.py`: `LineVisual`, `_GLLineVisual`, `_AggLineVisual`. `vispy/visuals/volume.py`: `VolumeVisual`, `_rendering_methods`. `vispy/visuals/filters/clipper.py`: `Clipper`. `vispy/visuals/filters/clipping_planes.py`: `PlanesClipper`. `vispy/visuals/text/text.py`: `TextureFont`, `FontManager`, `TextVisual`, `SDFRendererCPU`. `vispy/testing/image_tester.py`: `assert_image_approved`, `assert_image_match`, `ImageTester`. `vispy/testing/rendered_array_tester.py`: `compare_render`, `make_rgba`. |
| Inspect | Clim and NaN paths in the texture mixins. Marker `points` versus `instanced`. Agg bake dtype. Volume snippet hooks `$sampler_type`, `texture_lookup`, and the method snippets. Clip discard. SDF CPU call into `_calc_distance_field`. The keys of `_raycasting_modes`. |
| Investigation output | Expanded GLSL for one image, one label chain, each volume method, one marker method, and one text visual. The format and dtype of each uploaded texture. |
| Tests to reuse | Upstream visual tests that call `assert_image_approved` or `compare_render`, retargeted at the Dawn offscreen backend. Keep their assertions. |
| Local owner | Forked visuals under `src/vispy/visuals/`. Parity fixtures under `tests/parity/` and `tests/data/`. |

### Hosts

| | |
| --- | --- |
| Upstream napari `595639295` | `src/napari/_vispy/canvas.py`: `NapariSceneCanvas`, `VispyCanvas.screenshot`, `context.finish` in layer removal. `src/napari/_vispy/utils/gl.py`: `get_max_texture_sizes`, `fix_data_dtype`, `BLENDING_MODES`. `src/napari/_vispy/visuals/`: `image.py`, `labels.py` (`LabelVisual`, `LabelNode`), `volume.py` (`Volume`, `ISO_CATEGORICAL_SNIPPETS`, `TRANSLUCENT_CATEGORICAL_SNIPPETS`), `markers.py`, `points.py`, plus the other visual modules in that directory. `src/napari/_qt/qt_viewer.py`: `QtViewer` constructs `VispyCanvas` with a parent and a sample count. Layer and camera packages under `src/napari/layers/` and the camera modules imported by the vispy canvas; slice 1 lists the call sites rather than assuming a single camera class. |
| Upstream glue `33509adb` | `glue_vispy_viewers/common/vispy_widget.py` (`VispyWidgetHelper`), `common/axes.py`, `compat/text.py`, `utils.py`, `scatter/`, `volume/`. Modern 1.4.0 imports top-level `vispy`. Older vendored releases are a different integration. |
| Upstream visbrain | No GitHub tree was resolved for 0.4.5. After unpacking the sdist, search for canvas construction, embed widgets, capture, `objects/`, and `visuals/`. Record paths in `compat/hosts.lock.toml`. |
| Upstream DIVE `aa575e1c` | Confirmed paths: `DIVE/_widget.py`, `DIVE/_plotting/custom_vispy.py`, `DIVE/_plotting/artists.py`, `DIVE/_plotting/axis_instance.py`, `DIVE/_components/dive_axis.py`, `dive_axis_group.py`, `dive_filters.py`, `dive_manager.py`. Slice 1 reads these files and records which VisPy types they construct. |
| Plugin | `src/napari_threedee/_backend/manipulator/vispy_manipulator_visual.py`, `vispy_visual_data.py`, and `tests/test_manipulator_visual_data.py` at commit `7bd485085`. |
| Inspect | Every `gloo`, `Function`, `set_gl_state`, `grabFramebuffer`, `finish`, `glGetParameter`, and private VisPy attribute. |
| Investigation output | The capability manifest: calls, shader variants, blend states, formats, and picking uses, each marked admitted or blocked. |
| Tests to reuse | The host's own vispy tests, run first against upstream 0.17.0 and then against the fork. napari-threedee's `test_manipulator_visual_data.py` is the plugin's existing data test. |
| Local owner | No host edits in v1. Fixtures live in `tests/hosts/`. Pins live in `compat/hosts.lock.toml`. |

### Dawn, Tint, glslang, and nanobind

| | |
| --- | --- |
| Upstream Dawn `499e5c6f` | `CMakeLists.txt` options `DAWN_ENABLE_VULKAN`, `DAWN_ENABLE_METAL`, `DAWN_ENABLE_SPIRV_VALIDATION`, `TINT_BUILD_SPV_READER`, `TINT_BUILD_MSL_WRITER`, `TINT_BUILD_SPV_WRITER`, `TINT_BUILD_WGSL_WRITER`, `DAWN_USE_X11`, `DAWN_USE_WAYLAND`. `DEPS` for glslang and SPIRV pins. `src/dawn/dawn.json` for the API schema. `src/dawn/native/Device.cpp` SPIR-V gate. `src/dawn/native/ShaderModule.cpp`: `ParseSPIRV`. `src/dawn/native/RenderPipeline.cpp`. `src/dawn/native/PipelineLayout.cpp`: `PipelineLayoutBase`. `src/dawn/native/BindGroupLayout.cpp` and `BindGroupLayoutInternal.cpp`. `src/dawn/native/Surface.cpp`: `Surface::APIConfigure`, `APIGetCurrentTexture`, `APIPresent`. `src/dawn/native/Queue.cpp`: `QueueBase::SubmitInternal`. `src/dawn/native/vulkan/QueueVk.cpp`: `Queue::SubmitImpl`, `SubmitPendingCommandsImpl`. `src/dawn/tests/end2end/` and `src/dawn/tests/DawnTest.h`. |
| Tint at that commit | `src/tint/lang/spirv/reader/reader.h`: `ReadIR`. `src/tint/lang/wgsl/writer/writer.h`: `ProgramFromIR`. |
| glslang `23baa3f7` | `glslang/Public/ShaderLang.h`: `TShader::parse`, `TShader::preprocess` warning, `getIntermediate`. `SPIRV/GlslangToSpv.h`: `GlslangToSpv(const TIntermediate&, ...)`. |
| nanobind | Current docs are the navigation aid for `nb::ndarray`, `c_contig` / `f_contig` / `any_contig`, `forcecast`, the owner argument, and `nanobind_add_module`. The pin recorded in slice 1 is the authority for the API actually compiled. [ndarray](https://nanobind.readthedocs.io/en/latest/ndarray.html), [packaging](https://nanobind.readthedocs.io/en/latest/packaging.html). |
| Inspect | Which CMake options default off on Metal. How a SPIR-V module becomes a render pipeline. How one Dawn submit becomes one `vkQueueSubmit`. How surface configure and present behave after a zero-size resize. |
| Investigation output | A frozen `cmake/dependencies.cmake` with revisions and checksums, and a one-page note of the pipeline-creation calls the corpus test will use. |
| Local owner | `cpp/device/` (`DawnDevice` only), `cpp/shader/` (`glslang_spv.cpp` isolated), `cpp/platform/`, `cpp/bindings/`. Dawn stays an external pin, not a copied tree of edited backends. |

## First three implementation slices

These are approval units in dependency order. Each checkpoint has a test, retained evidence, and a stop condition. A native clear or a triangle does not earn application compatibility. A stop blocks every later checkpoint that consumes that checkpoint's result. Checkpoint 3a consumes the device and the QWidget surface. It does not consume the shader corpus. Checkpoints 2d, 3b, and 3c consume the corpus. Checkpoint 2c consumes the compiler only for its order-proof shaders.

### Slice 1 — fork identity, then inventory

#### 1a. Source and package preservation

**Implement:** Import the pinned VisPy tree, including assets, licenses, and CPU extensions, into `src/vispy`. Record a file manifest against commit `117b054598f4758b598f4b8f48feea48c11fe7b0`. Document every deviation. Add the uv, scikit-build-core, and CMake skeleton and the dependency pins, including Dawn DEPS checksums, without building a renderer yet.

**Test:** `tests/contract/test_source_manifest.py`.

**Evidence:** Manifest diff, license list, and the frozen revision file.

**Stop:** Stop if public class identities, module paths, or `vispy.__version__`'s upstream base differ from the pin. CPU helper sources stay in the tree.

#### 1b. Replacement installation

**Implement:** Build a wheel and an editable install whose distribution name is `vispy` and whose version is `0.17.0+vulkan.1`. Install the pinned host dependency sets. Prove uninstall restores upstream in a disposable environment.

**Test:** `tests/contract/test_installation.py` on both the wheel and the editable install.

**Evidence:** `importlib.metadata` distribution name, version, and file origin; a second environment that returns to upstream VisPy after uninstall.

**Stop:** Stop on a mixed install, an entry-point change, a `sys.path` overlay, or a second distribution that writes into the same import package. This checkpoint needs no GPU. It is the first Windows command below.

#### 1c. Inventory, oracles, and timings

**Implement:** Run each named host on upstream 0.17.0. Peel the phylib tag and record imports only. Unpack the visbrain sdist, verify sha256 `1b5596e9e6971ffa1ef5450d297955f1d8f3c1d020050b8f4d935e3fa7276ea6`, and try the candidate fixture on upstream. Capture composed shaders, filtered GLIR traces, reference frames, and benchmark parameters for every admitted fixture in [Scientific fixtures](#scientific-fixtures).

**Test:** `tests/contract/test_reference_inventory.py` checks that the manifest, traces, and oracle images exist and name the pins.

**Evidence:** `compat/hosts.lock.toml`, shader corpus, GLIR traces, oracle images, and reference timing notes.

**Stop:** A host that cannot run on upstream 0.17.0 is a host blocker, not a renderer success. visbrain stays out of the rendering matrix until that run exists. phylib gains no GPU workload. Do not start slice 2 while an admitted host's shader corpus is missing.

### Slice 2 — device, compiler, ordered gloo, early probes

#### 2a. Device and readback

**Implement:** `vispy._dawn`, `DawnDevice`, `device_info()`, limits, errors, and a headless target. Clear a known color and read it back.

**Test:** `tests/native/test_device.py` and `tests/native/test_offscreen_clear.py`.

**Evidence:** Backend, adapter type, limits, exact RGBA result, awkward-row readback, and an array that outlives the canvas.

**Stop:** Stop if Windows or Linux is not Vulkan, if macOS is not Metal, or if a hardware run selected a software adapter. Software runs are labeled and do not satisfy this stop.

#### 2b. Compiler pipeline

**Implement:** The shader contract above, including forced `TINT_BUILD_SPV_READER` and SPIR-V validation on Metal. Compile the captured corpus. Create a render pipeline per variant on Vulkan and on Metal.

**Test:** `tests/shaders/test_corpus.py`.

**Evidence:** Per-variant pipeline logs for both backends, one mapped diagnostic for a bad snippet, and the cache key of a repeated compile.

**Stop:** Stop if any required variant fails validation or pipeline creation. Do not disable validation. A triangle pipeline alone does not close this checkpoint. Checkpoints 2d, 3b, and 3c stay closed until every required variant has a pipeline on Vulkan and on Metal. Checkpoint 3a may use a clear color while this stop is open.

#### 2c. Ordered gloo

**Implement:** The interpreter, generations, snapshots, and the six order proofs.

**Test:** `tests/gloo/test_program_parity.py`.

**Evidence:** Oracle and candidate images for each proof, plus the filtered command log showing two draws kept distinct.

**Stop:** Stop if any proof collapses to one draw, drops a `DRAW` across a flush, or frees a resource before its ticket completes.

#### 2d. Early performance probes

**Implement:** Counters from the first frame. Run a large textured quad, an instanced point set, and a fragment volume using captured shaders. Include the presentation flip and format conversion in the timed path. Record Dawn submits and backend submits separately.

**Test:** `tests/native/test_early_probe.py` asserts the counters are present and that a resident pan records zero reuploads. The numeric speed goal is not claimed here.

**Evidence:** Probe logs with byte counts, pipeline misses, and the three submit numbers.

**Stop:** Stop the performance plan if the compiler route cannot represent the probe shaders with the required sample counts and formats. Feasibility numbers are not a release claim.

### Slice 3 — QWidget, unmodified napari, resident reuse

#### 3a. QWidget lifecycle

**Implement:** The Qt contract: parentable `QWidget`, native handles, reparent, zero size, minimize, DPI, overlays, destruction, capability queries, and `finish()`. Cover PyQt5, PyQt6, and PySide6 in separate environments. Qualify Windows, macOS, and Linux X11.

**Test:** `tests/qt/test_widget_lifecycle.py`.

**Evidence:** Widget type assertion (`QWidget`, and not `QOpenGLWidget`), handle and surface logs, DPI sizes, overlay stacking, and a `finish()` that waits.

**Stop:** A surface, reparent, or DPI failure stops the slice. A standalone clear window does not pass.

#### 3b. Unmodified napari image and a custom Function

**Implement:** One scalar image in unmodified napari 0.9.2, and a subclass fixture that adds a `Function` and a transform. No host edits and no GL context. Compare `canvas.render()` and `grabFramebuffer()` after `on_draw` with the oracle.

**Test:** `tests/qt/test_embed_image.py`.

**Evidence:** Oracle image, candidate image, difference image, and the napari version and VisPy distribution origin.

**Stop:** Stop if the host required a source edit, created a GL context, or captured a stale or un-resolved frame.

#### 3c. Resident interaction

**Implement:** Pan and zoom a resident 4096×4096 image inside the same embedding. Reuse the pipeline and the texture allocation.

**Test:** The resident section of `tests/qt/test_embed_image.py`.

**Evidence:** Counters showing no texture reupload, no warmed pipeline miss, and no per-frame completion wait.

**Stop:** Stop if the interaction depends on a CPU readback or `finish()` per frame.

### Remaining release sequence

4. Images and labels: interpolation, LUT and format conversion, categorical identity, multiscale and subregion updates, and multi-layer blending. Prove napari 2D images, labels, editing, and screenshots, including additive channel stacks and transparent exports.
5. Markers, lines, shapes, mesh, and text: keep instanced marker hooks, add the private point and line lowering, finish axes, colorbars, annotations, clipping, layout, depth, and 3D cameras. Prove the million-point benchmark and the admitted glue, visbrain, and DIVE frames. Run inventoried picking before those admissions.
6. Volumes: implement every admitted mode, categorical rendering, plane depiction, clipping, and depth. Compilation and the early probe already happened in slice 2.
7. Release qualification: supported upstream suite, host and plugin matrix, hardware parity and performance, lifecycle stress, wheel install and rollback. Publish the compatibility matrix. All v1 rows and performance gates pass before this is called a replacement.

## Repository layout and build

The implementation layout below is proposed. This plan does not create those files.

```text
pyproject.toml                    # distribution vispy; scikit-build-core; extras/groups
uv.lock                           # locked developer dependencies
CMakeLists.txt                    # upstream helpers + nanobind module + pinned native deps
CMakePresets.json                 # reproducible platform build presets
cmake/dependencies.cmake          # immutable revisions, checksums, build options
src/vispy/                        # upstream Python API/source/assets with focused changes
  app/backends/_qt.py             # shared Qt event behavior + QWidget lifecycle
  app/backends/_dawn_headless.py  # offscreen app/test backend
  gloo/                           # queues, compatibility wrappers, and parser bridge
  _dawn.*                         # installed compiled extension, never a separate import package
cpp/
  bindings/                       # nanobind batches, ndarray ownership, and errors
  device/                         # minimal Device interface and DawnDevice
  glir/                           # resource and state interpreter, ordered frame recording
  shader/                         # normalization, glslang_spv.cpp, reflection, source maps
  platform/                       # HWND, X11, Objective-C++ NSView/CAMetalLayer helpers
tests/
  contract/ native/ gloo/ shaders/ qt/ parity/ hosts/
  reference/                      # separate upstream environment and fixture manifests
  data/                           # deterministic phantoms, fonts, goldens, and licenses
benchmarks/                       # identical upstream/fork workload definitions
tools/                            # inventory, oracle capture, wheel and qualification commands
compat/hosts.lock.toml            # host, plugin, source, and data pins; capability manifest
third_party/licenses/             # shipped native dependency notices
docs/superpowers/specs/           # this plan
.github/workflows/                # CPU, software Vulkan, native builds, hardware qualification
```

Use scikit-build-core to drive CMake and Ninja and `nanobind_add_module(_dawn)`. Keep and build upstream compiled helpers. Pin build requirements and lock native compiler dependencies, including Dawn's DEPS. Python code generation uses the uv-selected interpreter, and that interpreter is passed to CMake. Wheels do not download a branch tip or a compiler at install time.

Build only Vulkan on Windows and Linux, and only Metal on macOS. Disable Dawn D3D, OpenGL, GLES, and null backends in shipping builds, and disable unneeded samples, tests, and tools. Force `TINT_BUILD_SPV_READER=ON` and `DAWN_ENABLE_SPIRV_VALIDATION=ON` on every shipping platform, including Metal-only macOS. Enable the `ShaderSourceSPIRV` instance feature. Keep the WGSL writer. Keep the MSL writer on macOS and the SPIR-V writer required by the Vulkan backend. Verify every option against the pinned `CMakeLists.txt` when the pin moves. [Dawn CMake at the pin](https://github.com/google/dawn/blob/499e5c6ff9b37d5de70c6493fb74c251e0d35c1c/CMakeLists.txt).

Prefer static native linkage, hidden symbols, and stripped release artifacts. Qt stays a Python-selected host dependency. Vulkan and Metal loaders and drivers stay platform prerequisites. Produce platform-specific CPython wheels. Do not claim ABI3 because `_dawn` might be buildable that way: retained upstream compiled helpers are not covered by that claim. Test Linux and macOS wheel library paths and Windows DLL discovery on clean machines without a compiler. The initial compressed-wheel budget is 100 MiB. Record cold-build time and peak memory in slice 2 and remove unneeded targets before expanding the wheel matrix.

CI has three tiers:

- Every change: packaging, API, composer, and normalization tests without a GPU, plus native builds on three operating systems.
- Every renderer change: real rendering through a pinned software Vulkan ICD on Linux, the upstream OpenGL oracle through a separately pinned software GL implementation, and shader and pipeline validation. A null backend is not a rendering test. Qt's `offscreen` platform is not a rendering test.
- Before release: real Vulkan GPUs on Windows and Linux, Metal on macOS, parented Qt presentation, capture, input, and DPI, host and plugin fixtures, and performance. Missing hardware blocks qualification. It does not block CPU work. CI reports the missing coverage and does not turn it into a passing skip.

### Windows: build and run the first test

These commands become runnable in slice 1. They do not run against the current tree, which has no implementation. Use PowerShell from an x64 Visual Studio 2022 developer shell with the C++ workload, the Windows SDK, Git, and uv. CMake, Ninja, and Python build requirements come from the pinned project.

```powershell
Set-Location C:\Users\HEQ\Projects\vispy_vulkan
uv python install 3.12
uv sync --locked --python 3.12 --extra pyqt6 --group dev
uv run --no-sync pytest tests/contract/test_source_manifest.py tests/contract/test_installation.py -q
```

`test_installation.py` is checkpoint 1b and needs no GPU. After checkpoint 1c exists:

```powershell
uv run --no-sync pytest tests/contract/test_reference_inventory.py -q
```

Once slice 2 exists, install a current vendor Vulkan driver. A Vulkan SDK is not required to consume the wheel.

```powershell
uv run --no-sync pytest tests/native/test_device.py tests/native/test_offscreen_clear.py -q -m gpu
uv run --no-sync pytest tests/shaders/test_corpus.py -q -m gpu
uv run --no-sync pytest tests/gloo/test_program_parity.py -q -m gpu
uv run --no-sync pytest tests/native/test_early_probe.py -q -m gpu
```

`test_device.py` fails if the backend is not Vulkan, if no suitable adapter exists, or if a hardware run selected a software adapter. Once slice 3 exists, on an interactive desktop:

```powershell
$env:QT_API = 'pyqt6'
uv run --no-sync pytest tests/qt/test_widget_lifecycle.py tests/qt/test_embed_image.py -q -m gpu
```

Repeat the Qt file with `QT_API` set to `pyqt5` and `pyside6` in the environments that admit those bindings.

The build and the tests print the fork revision, Python and Qt versions, adapter, backend, driver, selected limits and formats, Dawn submit counts, backend submit counts, and artifact paths. `uv sync` installs the project editable for development. Clean-wheel consumer tests stay mandatory. [uv editable installs](https://docs.astral.sh/uv/concepts/projects/config/#editable-mode).

## Explicit non-goals

- A new import name, a public scene-graph API, a C++ application object model, VisPy2, or a GSP migration.
- A raw Vulkan-Hpp backend, a runtime graphics-backend fallback, or an OpenGL context kept to fill gaps.
- Full OpenGL or PyOpenGL emulation, native GL handles, context interop, arbitrary geometry, tessellation, or extension shaders, or every gloo gallery example.
- Automatic switching of vendored VisPy namespaces, every historical host version, or the independent phy renderer.
- Treating visbrain 0.4.5 as admitted before the sdist is unpacked and the fixture runs on upstream VisPy 0.17.0.
- Treating phylib as a rendering workload, or treating the phy GUI as the same package.
- Jupyter, the web, other window toolkits, native Wayland, unsupported Qt bindings, Windows or Linux ARM wheels, musl, free-threaded Python, and an ABI3 migration in v1.
- New public compute APIs, CUDA or GL interop, indirect or culling architectures, a new out-of-core scheduler, or picking beyond actual admitted host use.
- Using `TShader::preprocess` output as the shader normalizer, or shipping a general GLSL-to-WGSL translator.
- Faster rendering from fewer volume samples, different interpolation, reduced precision that changes scientific results, a different blend order, wider parity tolerances, or dropping a faster upstream path from the comparison.
- A replacement release before the compatibility, parity, installation, and performance gates pass.
