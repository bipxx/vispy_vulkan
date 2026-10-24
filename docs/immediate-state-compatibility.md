# Immediate state and query contracts

This records the current Dawn facade subset against pinned VisPy 0.17.0. The
30 names in `src/vispy/gloo/gl/dawn.py` are entry routes, not 30 fully compatible
OpenGL features. This document supplements the canonical workflow ledger and
STATE-1..5; it is not a second completion denominator or installed qualification.

State belongs to the selected live Dawn canvas. An FBO changes the active
attachments and target dimensions; it does not create another context's blend,
depth, stencil, viewport or scissor state. Accepted immediate calls execute the
preceding queued GLIR before returning. Each draw retains its captured state.
Validation failure preserves the last committed state/cache; earlier commands
already executed in the same stream are not rolled back. Exceptions are
synchronous; `glGetError()` is not an OpenGL error queue.

Native numeric arguments accept Python/NumPy scalars packed as integers, floats
or booleans where the operation calls for a numeric flag/value. Rectangles need
integer-valued finite signed-32-bit components. Enum arguments accept the named
lowercase native tokens or the mapped integer GL enums. Stencil masks/clear
values require integer values in signed-32-bit through unsigned-32-bit range;
negative masks preserve their bit representation. Arbitrary arrays, objects,
unknown enums and nonfinite values are outside the admitted input domain.
Named Python signatures enforce argument counts before command submission.

## Operation records

Defaults below are native context defaults, before any VisPy state preset.
The fixture names are in `tests/native/test_dawn_immediate_state.py`, except
synchronization fixtures in `tests/native/test_public_submission.py`. A fixture
can prove a subset of a row; untested values are not promoted by association.

| Entry point / arguments | Accepted behavior and default | Ordinary/mutation or failure fixture |
| --- | --- | --- |
| `glViewport(x,y,w,h)` | Signed origin; nonnegative integer-valued extent. Explicit viewport overrides target-sized default. Successful raw calls update the Python context cache. | `test_raw_clear_and_scissor_preserve_queued_gloo_work`; `test_invalid_raw_parameters_leave_next_draw_usable` |
| `glScissor(x,y,w,h)` | Signed origin/nonnegative extent; affects clears/draws when enabled. Default disabled, target-sized rectangle. | `test_raw_clear_and_scissor_preserve_queued_gloo_work`; invalid-parameter fixture |
| `glClearColor(r,g,b,a)` | Finite values clamped to [0,1]; default (0,0,0,0). | Raw clear/scissor and color-mask fixtures; invalid-parameter fixture |
| `glClearDepth(depth)` | Finite clamped [0,1]; default 1. | `test_raw_depth_range_clamping_and_invalid_recovery`; invalid-parameter fixture |
| `glClearStencil(value)` | Integer bit value reduced to stencil attachment width when applied; default 0. | `test_raw_stencil_masked_replace_and_masked_clear`; invalid-parameter fixture |
| `glClear(mask)` | Color/depth/stencil bit union (0x4500); respects color/depth/stencil write masks and scissor. Unsupported bits fail in the facade. | Raw clear/color-mask and masked-stencil-clear fixtures; invalid-parameter fixture |
| `glEnable(capability)` | Blend, depth/stencil/cull/scissor tests, polygon offset, multisample, alpha-to-coverage, sample coverage and line smoothing. Defaults: multisample enabled; other listed tests disabled. Dither enable remains unsupported. | Per-family fixtures below; invalid-parameter fixture |
| `glDisable(capability)` | Disable the listed capabilities; disabling dither is accepted. Disabling multisample on a four-sample target has a draw-time restriction below. | Raw cull/depth/blend/stencil/coverage fixtures; invalid-parameter fixture |
| `glColorMask(r,g,b,a)` | Numeric zero/nonzero flags; default all enabled. Applies to clears and draws. | `test_raw_color_mask_and_invalid_state_are_not_silently_ignored`; stencil masking and invalid-parameter fixtures |
| `glDepthMask(flag)` | Numeric zero/nonzero flag; default enabled. Also controls depth clears. Depth writes require depth testing. | `test_raw_depth_write_mask_and_queued_draw_order`; invalid-parameter fixture |
| `glDepthRange(near,far)` | Finite endpoints clamped [0,1]; default [0,1]. Reversed ranges remain unsupported. | `test_raw_depth_range_clamping_and_invalid_recovery` |
| `glDepthFunc(comparison)` | Never/less/equal/lequal/greater/notequal/gequal/always; default less. | `test_raw_depth_comparisons_at_exact_far_endpoint`; invalid/recovery fixture |
| `glFrontFace(winding)` | CW/CCW; default CCW. | `test_raw_culling_and_front_face`; invalid-parameter fixture |
| `glCullFace(face)` | Front/back/front-and-back; default back, culling disabled. Polygon culling does not suppress nonpolygon logical primitives. | `test_raw_culling_and_front_face`; existing native/C++ topology contracts; invalid-parameter fixture |
| `glLineWidth(width)` | Positive finite native float; default 1. Width/smoothing use the renderer's line lowering and its separate shader restrictions. | `test_raw_line_width_updates_preserve_prior_draw_coverage`; invalid-parameter fixture |
| `glPolygonOffset(factor,units)` | Finite native-float-range values; defaults 0,0, disabled. Validate both before commit; draw-time units restriction below. | `test_raw_polygon_offset_changes_depth_visibility`; `test_raw_polygon_offset_overflow_rejects_before_mutating_state` |
| `glBlendColor(r,g,b,a)` | Finite clamped [0,1]; default zeros. Constants are captured for each draw. | `test_raw_separate_blend_and_constant_updates`; invalid-parameter fixture |
| `glBlendFunc(src,dst)` | Mapped zero/one, source/destination color/alpha, inverse, constant and source-alpha-saturate factors; both RGB/alpha components. Default one/zero. | `test_raw_blend_equations_and_integer_enums`; invalid-parameter fixture |
| `glBlendFuncSeparate(srcRGB,dstRGB,srcA,dstA)` | Separate component factors, same default. Mixed constant domains have a draw-time restriction below. | `test_raw_separate_blend_and_constant_updates`; invalid-parameter fixture |
| `glBlendEquation(mode)` | Add/subtract/reverse-subtract/min/max; default add. Min/max ignore factors. | `test_raw_blend_equations_and_integer_enums`; invalid-parameter fixture |
| `glBlendEquationSeparate(rgb,alpha)` | Independent equations; default add/add. | `test_raw_separate_blend_and_constant_updates`; invalid-parameter fixture |
| `glStencilFunc(compare,ref,mask)` | Comparison tokens as depth; ref clamped to 8-bit stencil range; default always, ref 0, full read mask. Sets both faces. | `test_raw_stencil_masked_replace_and_masked_clear`; invalid-parameter fixture |
| `glStencilFuncSeparate(face,compare,ref,mask)` | Front/back/both projection of the same contract. | `test_raw_distinct_front_back_stencil_state`; invalid-parameter fixture |
| `glStencilMask(mask)` | Integer write mask for both faces; default full mask. | Masked replacement/clear fixture; invalid-parameter fixture |
| `glStencilMaskSeparate(face,mask)` | Independent front/back masks with native face conversion. | Distinct-face fixture; invalid-parameter fixture |
| `glStencilOp(fail,depthFail,pass)` | Keep/zero/replace/increment/decrement/invert and wrap variants; default keep/keep/keep for both faces. | Masked replacement/clear fixture; invalid-parameter fixture; remaining operation-value coverage stays open |
| `glStencilOpSeparate(face,fail,depthFail,pass)` | Same operations applied to the selected face(s). | Distinct-face fixture; invalid-parameter fixture; remaining operation-value coverage stays open |
| `glSampleCoverage(value,invert)` | Finite clamped [0,1], numeric inversion flag; default 1/false, disabled. Native sample mask is derived from granted sample count. | `test_raw_sample_coverage_endpoints`; invalid-parameter fixture |
| `glFinish()` | Submit preceding selected-canvas work and wait for completion; no GUI draw/presentation request or target/state change. | `test_finish_waits_without_presentation_gui_draw_or_state_change` in the submission suite |
| `glFlush()` | Shared real submission path with `gloo.flush()`, without a deliberate completion wait. Empty calls may be no-ops; explicit capacity failure preserves unsent work. | Submission suite's nonempty/empty/saturated/owner-failure/loss/close fixtures |

The invalid-parameter fixture establishes contextual rejection, unchanged viewport
cache and a usable following draw. It does not independently prove every hidden
state field; the C++ state contract checks parser defaults, descriptors, full keys
and atomic updates. Polygon-offset overflow additionally has an output regression
that proves preservation of the prior offset and subsequent valid-state recovery.

## Query records

`glGetParameter(pname)` accepts integer enums, including NumPy integer scalars.
Floating values, numeric strings and booleans cannot silently select another
query. Target queries require a live Dawn canvas, even if a failed close retains
a native owner for retry. Device capability queries may initialize/access the
device without a current canvas. Queries do not submit draw work merely to read
a device limit; target queries first execute queued GLIR state in order.

| Selectors | Return / origin |
| --- | --- |
| VIEWPORT | Integer tuple from the selected native canvas, not requested window geometry. |
| SAMPLES, STEREO, DOUBLEBUFFER | Actual active framebuffer configuration; sample count uses public 0/4 convention. Defaults are not fabricated from constructor requests. |
| VENDOR, RENDERER, VERSION, EXTENSIONS, SHADING_LANGUAGE_VERSION | Compatibility-profile strings. Version/extension labels do not advertise arbitrary OpenGL operations. |
| MAX_TEXTURE_SIZE, MAX_RENDERBUFFER_SIZE, MAX_3D_TEXTURE_SIZE, MAX_VERTEX_ATTRIBS, MAX_UNIFORM_BLOCK_SIZE | Integer granted native limits; texture dimensions are pixels and uniform-block size is bytes. |
| MAX_TEXTURE_IMAGE_UNITS, MAX_VERTEX_TEXTURE_IMAGE_UNITS | Minimum of granted per-stage sampled-texture and sampler budgets, for their respective stages. |
| MAX_ARRAY_TEXTURE_LAYERS, MAX_COMBINED_TEXTURE_IMAGE_UNITS, MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS | Accepted only if the native renderer reports that separate domain explicitly. A per-stage count or byte count is not substituted. |
| Other selectors, including general mutable-state queries | Contextual unsupported-query error; they need a native-state snapshot design and additional fixtures. |

`glGetError()` returns integer NO_ERROR because errors use synchronous exceptions.
It carries no deferred error state and does not establish success for refused
raw object, shader, draw or query APIs. Actual framebuffer format/precision details
also remain available through the existing framebuffer-configuration route,
preserving unknown exact depth precision and reported minimums.

## Legal input gaps and promotion

Required future work includes reversed depth ranges, enabled dither, disabled
multisample rasterization on multisample targets, fractional/out-of-int32 polygon
offset units when polygon offset is active, mixed constant-color/constant-alpha
RGB blend factors, remaining enum/value combinations and general state queries.
These are legal-input compatibility gaps, not all invalid arguments. Keep their
current contextual refusals until the matching implementation has output proof.
Finite scalar values outside a native representation's admitted range also fail
contextually instead of committing infinities or inventing limits.

The new native leaf repairs polygon-offset overflow; Python query selection now
requires an integer enum and target queries reject closed canvases. The original
native candidates reproduce four overflow failures and the former Python query
route reproduces five selector failures. Matching candidates pass all 77 immediate
state cases. Broader affected suites pass 286 Windows and 272 WSL software cases,
plus 19 CPU/package contracts and the Windows C++ state contract. Both profiles
finish with nine zero native shutdown gauges. The Linux leaf remains experimental
under its retained-library/toolchain provenance limits; it is not an admitted SDK.
Exact installed members, complete workflow mapping, independent implementation
review, all three observer gates and platform-specific failures remain separate
qualification obligations. No support percentage follows from this table.
