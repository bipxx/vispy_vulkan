# Gloo namespace review

Reviewed 2026-11-07 against the source routes in `fa72c6da`, with the separately
recorded module-description corrections. This accounts for all **19 gloo seed
parents** at source-route scope. API-05/06 retain method/value reconciliation and
exact-artifact acceptance. The canonical inventory and original required pairs
remain unchanged, with `reviewed=false`.

Gloo objects submit ordered GLIR commands to the Dawn parser and native runtime.
GL-prefixed names preserve the calling interface; they do not denote native GL
objects or an OpenGL context. The public module descriptions now state this
bounded compatibility model. Original BSD headers remain, and the two changed
module descriptions are declared in `compat/deviations.txt`.

## Evidence boundaries

Published v1 evidence remains bounded to the checklist's exact wheels/profiles,
finite Tk state/resource criteria and capture criteria. Earlier shader/texture
development results retain their own source and artifact identities. Neither
export availability nor this source review qualifies an entire resource family
on v2. See [the live checklist](coverage-checklist.md),
[immediate state](immediate-state-compatibility.md),
[static sampler arrays](static-sampler-arrays.md),
[uniform updates](uniform-array-updates.md) and
[cropped capture](cropped-capture-compatibility.md).

## All seed parents

Paths below are relative to `src/vispy/gloo/`.

| Parent | Source route and present behavior | Acceptance scope / remaining gap |
| --- | --- | --- |
| `gloo.framebuffer` | `framebuffer.py:FrameBuffer`; ordered activation/deactivation, attachment and resize commands. Public attachments accept `Texture2D`, `RenderBuffer` or `None`. | Native format/attachment compatibility, nested restoration, resize, error ordering and loss/sharing need scoped proof. This route does not expose arbitrary 3D/cube-layer attachments. |
| `gloo.get-current-canvas` | `context.py:get_current_canvas`; returns the last live weak-referenced canvas or `None`. Canvas current/close routes update the list. | Finite Tk current-target/close behavior has bounded evidence. Mixed backend canvases, all close/error paths and thread ownership remain method-level work. |
| `gloo.get-default-config` | `context.py:get_default_config`; returns a copy of requested compatibility defaults. | Requested defaults are distinct from actual target configuration and device capabilities. Backend-specific refusal/normalization must be tested at canvas creation. |
| `gloo.get-gl-configuration` | `wrappers.py:get_gl_configuration` delegates to the Dawn framebuffer-configuration query. | Actual target values include backend/format information; opaque native depth precision may be `None`. Verify color/depth/stencil/sample values on each claimed target, including missing/current/closed targets. |
| `gloo.gl` | `gl/__init__.py` selects the Dawn compatibility facade; `gl2`/`gl+` are aliases, and `dummy` is a testing route. | Selected queries and immediate state/submission calls have separate operation/value records. Arbitrary raw object creation/drawing is outside the facade. Legal state exclusions, query values and ordering remain STA/SHD/API-06 work. |
| `gloo.glcontext` | `context.py:GLContext` owns a GLIR queue and shared parser namespace; configuration keys/types are checked. `Canvas.context` supplies the normal application route. | Direct constructor/shared-namespace and backend-extension methods require explicit reconciliation. Source `shared` handling expects a `GLShared` object; class availability does not establish every documented direct-call form. Finite Tk sharing/recovery is narrower. |
| `gloo.globject` | `globject.py:GLObject` assigns a process-local GLIR identity, associates queues and enqueues idempotent deletion. | An ID is a logical resource handle. Native retirement, queued uploads, external owners and shutdown caches require their own counters/readback proof; Python deletion alone is insufficient. |
| `gloo.indexbuffer` | `buffer.py:IndexBuffer` uses typed data-buffer storage, updates and views. | Index widths, bounds, offsets, empty/replaced storage and indexed draw/topology combinations must match each claim. Source buffer construction does not prove a rendered index path. |
| `gloo.program` | `program.py:Program` assembles shaders, reflected variables, buffers/textures and ordered draw commands. Native `cpp/runtime.cpp` rejects an attached geometry shader at LINK. | Vertex/fragment and bounded array/attribute/sampler forms have distinct evidence. Geometry consumers use separately scoped expansion routes. Dynamic indexing, typed sampler restrictions, stage interfaces, invalid layouts and recovery remain SHD/API-06 work. |
| `gloo.read-pixels` | `wrappers.py:read_pixels`; explicit viewport shape/integer-coercion checks precede queue completion. Positive extents and target bounds are checked later by native readback. | Finite color crop/mutation/shape-error retry criteria are qualified on v1. Depth/stencil, multisample sample selection, formats, alpha/orientation and rectangle-bound failures require their own exact-artifact scope and ordering proof. |
| `gloo.renderbuffer` | `framebuffer.py:RenderBuffer`; shape/format/resizeability and deferred native storage. | Accepted Python format tokens do not by themselves prove backend precision or storage format. Verify requested versus actual color/depth/stencil/sample behavior and attachment failures. |
| `gloo.texture1d` | `texture.py:Texture1D`; one-dimensional data shape and sampler interface feed the Dawn resource path. | Qualify channel/dtype/internal format, wrapping/filtering, partial updates and sampling coordinates. Static sampler-array source results retain their bounded type/rank scope. |
| `gloo.texture2d` | `texture.py:Texture2D`; data/shape and indexed/slice updates, plus numeric/typed sampler metadata. | Finite Tk RGBA8 texel mutation/sharing/recovery is covered. Other channel layouts, signed/unsigned/unfilterable formats, interpolation, offsets, ownership and NaN behavior remain scoped TEX/API-06 acceptance. |
| `gloo.texture3d` | `texture.py:Texture3D`; volume data and sampler interface have a native resource route. | Volume dimensions, format/filtering and ordered subvolume updates need claimed-layout proof. Large scientific volumes, performance and general 3D texture compatibility are distinct claims. |
| `gloo.textureatlas` | `texture.py:TextureAtlas` packs regions in a 2D texture with a skyline allocator. | Exhaustion, returned regions, orientation/borders, resize/update and rendered consumer behavior need acceptance. It is distinct from every text/glyph pipeline or arbitrary array texture. |
| `gloo.texturecube` | `texture.py:TextureCube` requires six faces; native cube allocation/view and ordered face-upload routes exist. | Six square faces, face ordering, seam/filter behavior, partial face changes and supported sampler forms need separate proof. The old module-level “not implemented” statement was stale. Source/development cube controls do not qualify every cube combination. |
| `gloo.textureemulated3d` | `texture.py:TextureEmulated3D` packs a volume into a `Texture2D` and supplies sampling helpers. | Packing, slice boundaries, interpolation and coordinate behavior need consumer proof. This class is distinct from native `Texture3D`; evidence must identify which route ran. |
| `gloo.util` | `util.py` supplies identifier/enum helpers, texture drawing and a screenshot delegation helper. | Enum validation is distinct from backend support. `draw_texture` is a composite shader/state/draw route; `_screenshot` delegates to readback. Both require their own value/current-target scope when claimed. |
| `gloo.vertexbuffer` | `buffer.py:VertexBuffer`; typed/structured storage, updates/views and divisor metadata. | Finite Tk float32 triangle data is a narrow pass. Integer/matrix/array attributes, strides/offsets, constants/divisors, instances, mutation ordering and source ownership remain distinct shader/point acceptance cases. |

## Routes that the parent seed does not enumerate

`gloo.__init__` imports `wrappers` through `*`. The wrapper module exports state
setters, presets, `set_state`, `flush`, `finish` and helper objects in addition to
the seed's two wrapper functions. API-05 must reconcile the runtime-bound methods
and `wrappers.__all__`; the 19 parents are not an exhaustive callable list.

Buffer views, texture assignment, shader helper classes, `GLShared`, context capabilities and
properties, ndarray assignment, program variable indexing and convenience
draw routes also need method/alias reconciliation. Their source presence does
not discharge original parent obligations. Preserve the raw interoperability
boundary and the documented legal exclusions when selecting API-06 criteria.

## Follow-up acceptance order

Reuse existing finite Tk/capture proofs for their exact forms. Then bind buffer
layout/ownership and framebuffer configuration/readback cases to the successor
artifacts, followed by the selected typed textures and shader/array forms.
Keep dynamic samplers, legal raster-state exclusions, geometry/line side effects
and scientific workflow breadth in their existing checklist entries. Each claim
needs supported values plus ordinary, mutation, failure and recovery cases on its
named installed artifact/profile.

This closes parent identification/source-route disposition for API-02 only after
the source audit and independent review are retained. Full method/value coverage
and installed qualification remain separate.
