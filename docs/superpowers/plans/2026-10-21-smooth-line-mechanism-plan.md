# Smooth-line mechanism investigation

2026-10-23 scope update (historical; superseded by the smooth-line criterion,
`tools/smooth_line_parity.py`, merged in PR #25 on 2026-10-28, and by decisions
D5 and D9 of the consolidated plan): the user explicitly relaxed extreme
rasterizer parity.
The following historical exact-reference investigation remains evidence, not a
requirement to reproduce every driver edge pixel before shipping useful lines.
Implementation now uses the existing generated ABI2 consumer with an explicit
`SmoothAnalytic` policy: a butt-ended rectangle with separable one-pixel edge
coverage, fractional widths and alpha modulation after the original fragment.
This is an approximation of single-sample GL smoothing. Exact-reference and
multisample policies remain unsupported rather than silently substituted.
Clipping, interpolation, fragment helpers, depth and resource ownership continue
through the existing consumer. Validate representative rendered lines and the
previously blocked axes/colorbar workflow before declaring this gap closed.
As of 2026-10-23, the source was under validation, and Native66 receipts
described the prior build.

The required axes/colorbar scene still fails because the generated line consumer
honestly refuses smooth coverage. The shipping renderer remains unchanged until
a real mechanism passes the original quality, lifetime, state and budget gates.
This investigation is one prerequisite to implementation, not a replacement for
the full Vulkan/Metal, MSAA, scientific, host and performance requirements.

## Decision and evidence

Use the existing evaluator/storage-row/ABI2 consumer architecture for a portable
coverage implementation. Width remains captured per DRAW and supplied as a
uniform; changing width must preserve pipeline reuse. Generate coverage logic
through the existing GLSL/SPIR-V/Tint chain rather than adding an unrelated WGSL
compiler path. Keep original fragment transport, derivative/helper behavior,
depth/stencil ordering, clipping, topology, instance identity, budget accounting
and retirement intact.

The previously rejected 162-candidate convolution study remains rejected. Its
holdouts and protected files are not inputs to this work. No old capture or model
is replayed or retuned. The new hypothesis is a fixed subpixel sampling mechanism,
distinct from selecting another continuous convolution/extension combination.
Whether that hypothesis is true is unmeasured.

Current physical-device queries show RTX4090/610.88 supports native Vulkan smooth
lines, but Intel UHD770/101.7088 does not. Native smooth mode therefore cannot be
the complete implementation. An isolated Vulkan diagnostic may later compare
native smooth mode with original GL training data on NVIDIA; it must not become
an NVIDIA-only substitute or change the instrumentation layer. The Vulkan
[smooth-line rules](https://docs.vulkan.org/spec/latest/chapters/primsrast.html)
leave coverage details implementation dependent, so matching feature names do
not prove matching pixels.

The bounded Claude peer plan is retained in
`build/smooth-native-mechanism-prep-root-1/peer-plan-response2.json`. It had no
repository or tool access and is advisory, not source admission. Root corrects
these points before applying it:

- Direct coverage requires blending **disabled**, a transparent clear, and a
  constant white fragment output. Otherwise alpha blending can square coverage.
- RGBA8 alpha values lie on an integer lattice even for continuous coverage.
  A histogram can exclude finite-sample hypotheses; it cannot establish a unique
  mechanism or qualify a renderer.
- Track the generated-fragment mask separately from alpha. A generated fragment
  with quantized alpha zero may still affect RGB, depth/stencil or shader helper
  behavior. Do not blindly discard all zero-alpha expanded-quad fragments.
- Preserve the existing compiler chain. Demote/discard and side-effect/helper
  semantics need their own original-reference controls; advice is not proof.
- Intel Vulkan availability does not prove that an Intel OpenGL context can be
  selected here. Do not change desktop graphics preferences to manufacture it.

## Frozen first training scope

The first oracle is installed upstream VisPy0.17.0 on the currently observed
NVIDIA desktop GL implementation. WSL llvmpipe is a separate later oracle. Intel
GL and macOS GL remain unadmitted until actual context identities are established.
No result on one oracle qualifies the others.

Use a64x64 linear RGBA8, single-sample offscreen target. Clear RGBA to zero. Use
one independent GL line segment per frame with constant white output, blending,
depth and stencil tests disabled, and line smoothing enabled. Record actual
sample/channel precision, line-smooth state/hint, requested width, GL width range
and granularity, renderer/version, source hashes and all commands. Each probe has
one final read; no performance claim follows. Do not silently change a requested
width or retune after seeing a frame.

Set the line-smooth hint to GL_DONT_CARE and disable dithering and framebuffer
sRGB conversion. Verify the actual state instead of assuming defaults.

All endpoints are exact integer multiples of1/256 pixel and converted to clip
coordinates using powers of two. Two directed axial orientations, forward and
reverse, sweep all256 perpendicular phases at widths1,1.5,3.25. Eight directed
oblique vectors, each forward and reverse, use four fixed phase paths over a
16-phase coarse grid at widths1,1.5,3.25,7.5. Duplicate phase pairs are removed
before capture. The resulting7040 ordered input descriptors are deterministic.
All geometry remains inside the target with room for coverage.

Analyze training only: exact alpha histogram, generated-fragment mask, zero-alpha
generated fragments, forward/reverse differences, width/phase behavior and
necessary compatibility with fixed sample counts4/8/16/32/64 under fixed floor
or nearest conversion. These are observations and necessary conditions, not
model selection or qualification. Include a continuous-area synthetic null that
can share a discrete alpha histogram so the analyzer cannot overclaim identity.

Before observing those captures, fix the later candidate family: all ordered
power-of-two factor pairs for each sample count give25 centered rectangular
grids; identity or45degree rotation with coefficient46341/65536; floor or nearest
endpoint snapping to1/256pixel; butt or half-width endpoint extent; floor or
nearest alpha conversion; and either nonzero sample population or positive
rectangle/pixel intersection for the generated-fragment mask. These are800
coupled hypotheses, not free per-frame parameters. This is a finite new family,
not an assertion that any member matches GL. A candidate must match **all**
training RGBA bytes exactly to be selectable; a nonzero-error winner is refused.
If more than one matches, choose the lowest canonical ID before opening new
holdout inputs, seal its complete predictions and retain the ambiguity. No
holdout-based tie break, extension or retuning is permitted. This first family
does not qualify MSAA or the full later fragment/depth/state contract.

## Separation and refusal gates

The capture input reader accepts only the exact frozen training IDs and canonical
training artifact names. Reject holdout/unknown descriptors before any filesystem
access. Preserve the existing17 protected payloads,58 family files and8 reserved
stems; this work never lists or opens those payload trees.

Reserve eight new holdout roles. Their capture artifacts are not created or
opened during training analysis. After a mechanism and code are frozen from
training, generate new holdout inputs using the predeclared scope (unseen phases,
slopes, short/reversed/degenerate segments, width and clipping boundaries). Seal
CPU predictions and source/selection identities before any holdout GL capture.
A miss refuses that mechanism; it cannot retune the frozen selection. Later
gradient, blend, depth/stencil, helper/derivative, custom-fragment, topology,
instance, clipping and MSAA references remain required, separately scoped work.

The64x64 experiment does not establish arithmetic safety at normal device limits.
Before integration, derive bounds after homogeneous clipping for every admitted
viewport/width grant and prove the required multiword integer operations; do not
assume native64-bit shader integers exist in WGSL or that signed overflow is
portable. Fragment generation, zero-alpha execution, helper status, custom depth
and side effects need actual controls before choosing any demote/discard order.

2026-10-21 training result: the complete Source2 capture passes saved review for
all7040 descriptors (build/smooth-training-saved-review-root-3/result.json,
SHA256 f7c7820695264c7c0fb8ee503b0f29ac265c443ff82ee0f010360bfef4d41af4).
The alpha-level necessary condition rejects every predeclared4/8/16/32/64
population with floor/nearest conversion, hence rejects this entire800-member
family. Preserve the family unchanged as refuted; there is no selected model.
These single-shot NVIDIA observations remain conditional on the unobserved driver
application profile and spec-default compatibility state. Repetition/stability
and direct observation of those additional states remain prerequisites to a
stronger mechanism claim. No holdout has been accessed and no renderer changed.

The next observation packet repeats the unchanged full7040 training selection in
a fresh upstream context with line stipple and alpha test explicitly disabled
and observed, COLOR_ATTACHMENT0 read buffer and canonical CPU pack state checked.
After that sweep, repeat the64 canonical training indices given by sorted unique
{0,7039} union range(0,7040,113), using separate repeat-control artifacts. Compare
every fresh sweep row against Source2, then compare each repeat against its fresh
sweep row. All comparisons are full RGBA exact with independently checked raw
hashes, GL state and command batches. A mismatch is retained and refuses the
corresponding stability claim; no replacement frame is selected. This control
uses training only, never changes the rejected800-member family, and does not
prove general determinism outside the observed contexts and repetitions.

This stability packet now passes saved review for all7040 fresh-context frames
and64 end-of-sweep repeats, with zero differing RGBA pixels in either comparison.
The exact full GLIR batches and added GL state checks pass too. Evidence:
build/smooth-training-stability-review-root-3/result.json,
SHA256 d216968a4afabf10efe5d32d7e01d5143eb8d664db3aa55c3a2acae972af515d.
Training analysis nevertheless finds stable direction dependence:435 of3520
reversal pairs differ, including6090 differing pixels in the central projected
t interval(0.2,0.8).94 of1536 axial transpose pairs differ. The31 observed alpha
values also differ from nearest(255*k/31) at three ranks, so even that simple
conversion assumption is refused. Observed ranks are diagnostic labels only;
they must not become a fitted shader lookup. A subsequent mechanism must explain
directed subpixel setup and conversion, beyond endpoint-cap changes, and pass the
unchanged full training frames before any unseen holdout capture. There is still
no selected mechanism, renderer change or general determinism claim.

The next observation changes only the owned target/readback format to linear
RGBA32F with standard GL_FLOAT readback. Use all unchanged7040 training inputs,
the same constant-white shader/state and64 separate end-of-sweep repeats. Require
observed32-bit GL_FLOAT attachment components and channels, a complete owned FBO,
finite normalized RGBA float32 frames, and the same state/command/lifecycle gates.
Preserve raw float32 bits and each per-row hash; never quantize before saving.
This is a measurement of the conversion stage, not a new coverage-family trial.

Saved review will compare generated masks with Source3 RGBA8, and compare that
RGBA8 reference with two predeclared CPU conversions of the float32 frames:
floor(float64(value)*255+0.5) and nearest-even(float64(value)*255). Report every
whole-frame difference, including maxima and differing rows/pixels. Neither
conversion is assumed to match; changing target format may itself change the
implementation path. A mismatch is retained without retuning either conversion.
Report exact generated-fragment alpha float bit patterns and rational values,
including generated zero-alpha fragments, as descriptive observations only.
Repeat comparisons must use raw float bit equality. No observed-level lookup
may become shader code, no rejected family is rescued, and no holdout is opened.

Source4 RGBA32F saved review now passes all7040 rows and64 bit-identical repeats
(build/smooth-float-saved-review-root-4/result.json,
SHA256 1faf1f92bbbaceaf9cb0e98de6a82abfdaa4fad3afab012284b2605f479361ff).
It contains only generated alpha1.0, with326366 generated-mask differences and
553968 converted-frame differing pixels against Source3 for either predeclared
conversion. Every row differs. Thus this target cannot currently be used to
observe the RGBA8 coverage before rounding. This is a scoped observation, not a
claim that floating targets generally disable smoothing. The primary
[ARB_color_buffer_float specification](https://registry.khronos.org/OpenGL/extensions/ARB/ARB_color_buffer_float.txt)
describes antialias coverage multiplying floating-point alpha; the mechanism
behind this observed divergence remains unresolved. Clamp/pixel-transfer state
and driver-profile limitations remain explicit. Neither frames nor conversions
are changed to hide the result.

Next repeat the unchanged full7040 selection and64 repeats with a normalized
RGBA16 attachment, observed16-bit UNSIGNED_NORMALIZED components/channels and
standard GL_FLOAT readback. Upstream Gloo already exposes this internal format;
no upstream rendering source is modified. Save raw float32 readback and run the
same two fixed conversions/mask comparisons against Source3. The target is
fixed-point, while the readback dtype is float32; do not conflate those. Treat
any difference as an observation rather than evidence of a selected model.

Source5 normalized16 review passes all7040 rows and64 raw-bit repeats
(build/smooth-normalized16-saved-review-root-5/result.json,
SHA256 e413f4d7e022e1577e5ddbc72f8025fabef812181de19d49688414ebd631220f).
Its generated masks exactly match Source3. Both predeclared nearest conversions
still fail:5980 rows,261718 pixels, maximum channel error1. Their failures remain
unchanged; this observation does not identify a rounding tie rule. Readback is
itself quantized and clamp/pixel-transfer/profile limitations stay explicit.

Exploratory training-only analysis then finds that reconstructing each normalized
16-bit code and taking its high byte exactly matches every Source3 RGBA8 frame.
All537127 partial-alpha fragments have a zero low byte in the reconstructed
16-bit code. This relation was derived after observation, is recorded separately
at build/smooth-training-fixed-transfer-analysis-root-6/result.json
(SHA256 438ec8e82dd79544eca12ad667a7355193fed8e614b2a890898b71f86bd622ed),
and does not turn either predeclared conversion into a pass or identify a full
coverage mechanism. No observed alpha table is installed in a shader.

One new CPU-only, training-derived axial hypothesis is frozen in
build/smooth-directed-axial-study-root-1/authoring.json, with all3072 predictions
sealed before its whole-array comparison. It snaps the two minor antialias ramp
intercepts toward containing-pixel centers on a1/16 grid, using a directed
1/512-pixel perturbation along the negative oriented normal. It uses1/8-pixel
longitudinal endpoint extension, separable ramp-overlap product, nearest31
coverage quantization and integer alpha expansion nearest(code*8415/1024).
This is an exploratory deterministic formula, not a lookup or selected model.
Six arithmetic/domain controls pass. Complete study
build/smooth-directed-axial-study-root-1/result.json
(SHA256 388728280a28c359763a3ea785bc2a98b9f1c3338ded367eaf3ba62f681ba69e)
REFUSES the hypothesis:2304/3072 whole frames match, but768 each have one wrong
endpoint pixel (maximum channel error9). All interiors match. Preserve the
failed source, prediction seal and frames; do not patch those pixels or call
this a solution. The3968 oblique training inputs remain unrepresented. Next
work must investigate the joint endpoint/minor-edge coverage rule, with a
separate predeclared training control if the existing inputs are insufficient,
then explain oblique setup and pass the whole unchanged training union before
any new holdout capture. All original fragment/state/platform gates remain.

Predeclare a separate4096-input corner training control: horizontal/vertical,
forward/reverse, widths1/1.5; longitudinal phase takes base and base+1 for
base0..240 step16, and perpendicular phase takes1..241 step16. Keep segment
length40, origin12 along its length and20 perpendicular, in the same64x64 target.
The canonical IDs begin corner- and remain inadmissible to the original7040
capture/reader. Conversely, the corner reader and provider reject original and
holdout roles before device/file access. This extends training and leaves the
original7040 frames unchanged. Its128 geometry overlaps with the original study
must compare exactly as a separate control. Repeat indices0..4095 step65 give64
separate end-of-sweep repeats. Use the original linear RGBA8 observation state.
Freeze the already-refused axial prototype's4096 predictions before this new
capture. Report full-frame and endpoint/interior errors without correcting any
predictions. This experiment is intended to distinguish joint edge coverage from
separable product/quantization order; it is not a model-selection or holdout run.

The corner capture now passes saved review for all4096 rows,64 exact repeats and
128 byte-exact overlaps with the original study. Evidence:
build/smooth-corner-saved-review-root-7/result.json,
SHA256 76199e3ad564abeb763dd113c257f9ccd9c6d5f8b0c16f08652c8a35e8c59d87.
The original prototype misses5984 endpoint pixels in3208 frames and zero central
interior pixels. Its predictions stay unchanged. The first saved reader's NPY
header assumption failed before any row comparison; the corrected reader requires
NPY1.0 only for the sealed np.save predictions and still requires NPY2.0 for all
oracle/repeat arrays. Both reader versions and the failed report remain retained.

A separate analysis of continuous separable-factor feasibility stops at its
decoder assumption: the first prototype's8415/1024 alpha expansion gives131 for
code16, while the captured alphabet contains132. It does not produce a proof
against all separable models. Retain this analysis refusal without claiming the
solver was reached.

The second training-derived axial hypothesis uses the same directed ramp geometry
but quantizes before multiplication. Its minor code is nearest(31*minorCoverage).
The major factor is0 for zero longitudinal overlap, otherwise
min(32,ceil(32*overlap)+1). The combined code is floor(minorCode*majorFactor/32),
and alpha is floor((263*combinedCode+16)/32). Generate a fragment iff the combined
code is positive. These are fixed arithmetic expressions, not an observed-level
lookup or a pixel-specific correction. All7168 predictions are sealed before
the full comparison. The refactor also preserves every one of the first
hypothesis's3072+4096 frozen predictions, including its failures.

This staged hypothesis matches all3072 original axial frames and all4096 corner
training frames in every RGBA byte. Eight CPU arithmetic/domain controls pass.
The frozen study is build/smooth-directed-axial-study-root-2/result.json
(SHA256 c9321170297e2a10232d76249da721f4a30166c5f15017649d449da12291b82a).
Saved verification regenerates all7168 predictions from frozen sources and checks
every oracle frame at build/smooth-directed-axial-saved-review-root-2/result.json
(SHA256 9d9feabf81ff9419f0acde1a02249e650bea3c3edb2f9a9ac39bd8edd4c92bb6).
This is an exact axial training result only. The3968 original oblique cases,
unseen holdouts, arbitrary fragment semantics, normal device-scale arithmetic,
GPU reproducibility, state/width reuse and full platform gates remain open.
No renderer path is enabled and no full model is selected.

First oblique extension: freeze eight training-informed hypotheses before the
whole3968-row comparison. Use normal-space antialias width/gradient and Euclidean
endpoint extension, or major-space antialias width/unit gradient and fixed1/8
endpoint extension; combine each with nearest31 or floor32 minor quantization,
and explicit float64 or float32 arithmetic. Both use directed nextafter
perturbations before the existing1/16 ramp-intercept snap, an unsnapped full-core
test, perpendicular endpoint planes and the staged integer major attenuation /
alpha encoding. Axial inputs delegate unchanged to predict_axial_staged.
These are hypotheses about oblique setup, not claims of driver equivalence or
portable arithmetic. Seal all prediction streams before opening the full oracle
array. Check every full RGBA frame, with separate central-interior diagnostics.
Only zero-error candidates can advance; no tolerance, reference mutation, best
nonzero admission, new holdout access or renderer change is permitted.

All eight extensions are now refused by the unchanged whole oblique corpus.
Each differs in161121 to232152 pixels, including85372 to128795 central-interior
pixels. Frozen result: build/smooth-oblique-study-root-1/result.json,
SHA25648696ff86428bdc53a89a23ff11dbef588b700969cf0e6526b99dab47ec3133b.
No nonzero-error candidate advances; the exact axial mechanism remains training
evidence rather than a general line implementation.

The standalone native Vulkan diagnostic has now completed. CPU build and both
SPIR-V validation checks pass. Reviewed Source2 freezes49 members with executable,
shaders, all11136 canonical inputs, AGPL, original BSD and dependency notices.
Actual child60964 exits0 and is waited. Parent checks exact PID/module and NVIDIA
vendor4318/device9860/driver2559967232, accepted KHR/EXT extension, raw hash/length
and source/native4 preservation. The RECTANGULAR_SMOOTH pipeline uses dynamic
width, transparent RGBA8, sample1 and constant white, with blend/depth/stencil off.
Positive viewport height and one readback row reversal were declared beforehand.

All11136 native frames match GL byte for byte, including all3968 oblique rows.
Both have834535 fractional-alpha pixels; no frame is empty or fully aliased.
Saved result: build/smooth-native-vulkan-saved-review-root-2/result.json,
SHA256b13077031757b19bb3828930d332d1d870308055d6885a64ee174844b1c9989c.
Reusable tools/smooth_line_frame_comparison.py adds exact canonical role/order/
geometry gates before frame access, separate mask/alpha counts and false-pass
controls. All17 mutation/stream tests pass. Separate saved audit rechecks every
frame without a device: build/smooth-native-vulkan-saved-audit-root-4/result.json,
SHA2563a4f9b1ea4a8c78f5a5c27a0b6d84dbb99887ba60f69775c121d85e22a621078.
The first audit snapshot's omitted fixture_gloo import fails before frame access;
its root-3 snapshot/refusal is preserved. Root-4 adds the unchanged dependency,
without changing comparison criteria or frames.

This measures shared native/GL behavior on one NVIDIA configuration, rather than
identifying a portable formula. No Vulkan runtime validation layer was enabled;
application profiles may differ across executables. Intel has no native smooth
feature here. Investigate oblique rasterizer setup/interpolation and quantization
next, without substituting a driver-specific native path for the required
portable generated fallback. Shipping renderer, holdouts and original references
remain unchanged; general fragments/state, width reuse, MSAA and all platform/
lifetime/performance requirements remain open.

The next finite family uses perpendicular normal-distance coverage
(width+1)/2-abs(distance), floor(16*coverage) saturated to0..15, and four-to-five
bit expansion2*nibble+(nibble>>3). This is a fixed arithmetic expression, with no
observed-level table. Directed one-ULP coverage ties use the oriented normal.
Freeze three precision paths: float64 normal coefficient/float64 evaluation,
float32 coefficient/float64 evaluation, and float32 coefficient/float32 evaluation.
The rational centerline slope is evaluated separately from the setup coefficient.
Axial cases delegate unchanged to the exact staged axial hypothesis. Retain the
previous perpendicular cap planes,1/8 extension and staged major factor without
claiming those cap rules are established for oblique lines. Seal every complete
prediction stream before the full3968-row comparison; report interior separately
but refuse every nonzero whole-frame candidate. No holdout or renderer admission.

All three first nibble variants are refused. Frozen result
build/smooth-nibble-study-root-1/result.json has SHA256
7aeb8b959bed554081652d4f8c9c13cd9123549e41befb1f8afedbf6618dd68c.
Variants0/2 differ in20871 pixels, including1760 interior pixels; variant1 differs
in21392 pixels, including1770 interior pixels. Saved regeneration of variant0
preserves its complete prediction seal. Of its1760 interior differences,1755
occur at exact rational normal-coverage bin boundaries, and five share
oblique-5-r1-w832-p000-255. All observed interior codes belong to the16-value
arithmetic nibble expansion. These observations do not promote a nonzero model.

Second nibble family changes only longitudinal cap evaluation: use signed normal
distances from both endpoint planes, raw cap coverage
clip(.625+min(distanceFromStart,distanceFromEnd),0,1), then the retained
min(32,ceil(32*coverage)+1) for positive overlap and0 otherwise. The .625 is the
preexisting half-pixel footprint plus1/8 extension in perpendicular space.
Keep all three arithmetic variants and every minor/tie/encoding rule fixed.
Regenerate all first-family streams unchanged, then seal all second-family
streams before the unchanged whole-frame comparison. No correction or holdout.

The second family preserves all three complete first-family prediction streams
and seals all new streams before comparison. Eighteen current CPU controls pass.
All variants remain refused:2770/3580/2770 differing whole-frame pixels. Variant0
has351 differing frames, including1760 interior pixels; four complete vector
groups (1984 frames) match byte for byte. Frozen result:
build/smooth-nibble-study-root-2/result.json,
SHA25690c9407a4c55779c588d3efea1bca9e6c62d95264d99d689c7f609e624c82d9f.
Saved regeneration verifies its complete stream and localizes2751/2770 differences
to exact rational minor or cap quantization boundaries. The remaining19 belong
to oblique-5-r1-w832-p000-255 and oblique-7 phase096-159 (widths3.25/7.5, both
directions). Evidence: build/smooth-nibble-saved-diagnosis-root-2/result.json,
SHA25650ef2eaa35c13ca8c858433240872cd36fbc3e73d88ff485cbf842b9d2829a81.
The non-tie minor geometry is about2.176e-7 coverage units below a nibble boundary
in exact arithmetic, so setup precision is a live hypothesis; this is not an
authorization to add an epsilon or geometry-specific branch.

Independent exact constraints also establish zero central-half differences for
all1304 along-line translation pairs, and rational contradictions to an
unsnapped nearest-integer affine ramp in all64 wide-line side groups.
tools/smooth_line_setup_constraints.py passes15 controls, including strict-bound
contact and duplicate-coordinate contradictions. Frozen training report:
build/smooth-line-setup-constraints-root-1/result.json,
SHA25664caa17b88b9dd5d3fbd189e9a70984f390f60949261fb9e85fc3fbe2a654771.
This does not refute the quantized nibble mechanism or prove a hardware formula.
Next derive normal-plane setup/evaluation precision and directed ties, including
first-endpoint dependence and cap zero-projection cases. Keep all current failed
families unchanged; no per-pixel patch, fitted tolerance or nonzero admission.

Next finite setup family constructs the two minor and two cap coverage halfplanes
directly in binary32 window coordinates. Normalize the directed endpoint delta;
minor constants include(width+1)/2 and cap constants include .625. Minor planes
use the first endpoint; start/end caps use their respective endpoints. Freeze
twelve variants: split or nested-fused constant construction, binary32 split /
binary32 nested-fused / binary64 plane evaluation, and no extra tie perturbation
or the retained oriented nextafter rule. Fused order is y-term then x-term.
Preserve nibble/alpha expansion and staged major attenuation, with unchanged
axial delegation. Binary64 emulates one binary32 FMA rounding only for the bounded
training-coordinate domain; it is not a claim about arbitrary shader inputs.
Freeze code and all prediction streams before the complete unchanged comparison.
No origin offset, geometry-specific constant, epsilon, tolerance or holdout.

The twelve direct binary32 plane variants are all refused:4103 to6481 differing
pixels. Result build/smooth-plane-setup-study-root-1/result.json,
SHA256e9ecc4aa7e1787108f9178980fd1f611c4ffa7b63a849a7aeca457ebca44b2c4.
All29 arithmetic/domain controls pass; no nonzero model is selected.

Exact nibble-affine constraints admit all64 wide-line side groups, while the
unsnapped five-bit affine analysis refused all64. Fixing either the binary64 or
binary32 normal coefficient still admits an intercept interval in all64 groups;
the exact ideal width intercept belongs to59/64 intervals in either case.
No intercept midpoint or fitted bias is selected. Evidence:
build/smooth-line-setup-constraints-root-3/result.json,
SHA256c6e653961721ba87578a13c60c94ce9df6448a42fc8d01d52c399ea836c0d74c.
Thus current data do not identify coefficient precision uniquely.

Predeclare a disjoint setup-along training selection to distinguish origin and
normalization dependence. Use vectors(36,27),(27,36),(36,9),(36,36), both directions,
widths1/3.25 and seventeen steps0..16 along each primitive positive integer vector
in1/256-pixel units. In translate mode shift both endpoints; in start-only mode
shift only the first directed endpoint. All preserve the exact directed infinite
line, while start-only changes length. The544 ordered rows contain32 step-zero
baseline rows matching16 unique original references; retain the intentional
duplicate baselines across modes. Repeat each17-row group's first and last rows
after the sweep, for64 repeats. Constant-white RGBA8 observation rules stay fixed.
Original/corner role gates must refuse these IDs before device/file access, and
the new role must refuse original/corner/holdout/changed/reordered inputs. Freeze
the already-refused models' predictions before observation. This is additional
training, not a holdout or renderer qualification. Review and source admission
must precede any actual provider/device capture.

Setup-along Source7 is frozen and observed after source and admission-condition
reviews. All three prior models'544 predictions were sealed beforehand. CPU suite
passes227 cases. The pre-capture full geometry check corrects a32-only overlap
assumption: four diagonal translate-step016 rows also match the original coarse
phase016, so all36 overlaps are required exactly. No reference is changed.

The original peer F1 proposal to inspect reserved holdout descriptors is corrected:
the eight new roles are names whose coordinates have not been generated by this
investigation. Old162-study holdouts remain protected and permanently rejected;
their numerical disjointness is not claimed. Before observation, freeze a complete
training-only geometry exclusion registry, including endpoint reversal. Future
new holdout generation must call require_unseen_geometry against this pinned
registry before capture. Registry build/smooth-training-geometry-exclusion-root-1/registry.json
(SHA256de613ec705abd00db4a21091318ac72ce087a1ed639d90eb271025f4c8ac5c76)
stores5886 hashes over11680 training rows/11516 directed geometries. Seven controls
pass. No held-out coordinate or frame was read to construct it. The future
generator/qualification is not yet implemented or admitted.

The conditions review closes that scope correction and seal binding, then requires
two reader fixes before capture. Final reader8 validates exact setup/direct/
cleanup chronology in addition to all row batches, cross-checks baseline copies
with startup identity, expected implementation and the admitted original baseline,
and records generated RGB and minimum-pixel semantics. Fourteen mutation tests
and a check against prior real admitted metadata pass. The review explicitly
allows closure after those fixes without another review. Reader hash is pinned
before launch, and prediction/registry hashes are checked before and after.

Actual544-row capture passes all state/hash/identity/command/cleanup gates,
64 exact repeats and36 exact original overlaps. Saved report:
build/smooth-setup-saved-review-root-8/result.json,
SHA25699f8526c78d79a057a0814315387bd6a12fbfd58fe95324b1563c649eb290f4f.
Across512 exact central-half comparisons with each group's baseline, all256
rigid translations match, while64/256 start-only rows differ in269 pixels.
Differences occur only for vectors(36,27)/(27,36). The other two vectors are null
controls here. Both modes move the first endpoint identically at a given step,
but only start-only changes the other-end relation and length. This supports
length-normalization or end-dependent setup as the next investigation and
contradicts a pure first-origin effect with an otherwise fixed infinite-line
formula. It does not uniquely identify the hardware operations. Direction and
length sign, and different Euclidean step sizes, remain confounded as declared.
Variants0/2 still miss1132 pixels in166 rows; variant1 misses1438 in217. All remain
refused, and identical0/2 streams are not treated as distinguishable models.

Next investigate unnormalized signed edge/dot products and a shared reciprocal
length, with explicit precision/rounding. Preserve all former predictions,
including failed direct-plane families. No fitted offset, tolerance, per-pixel
branch, holdout access or shipping-renderer enablement follows from this study.

Predeclare the shared-reciprocal family: use local signed unnormalized cross and
endpoint dot products, then multiply all three by one reciprocal segment length.
Keep the nibble/alpha encoding, normal cap footprint and staged major attenuation.
Freeze twelve precision paths: binary64 sqrt/reciprocal, binary32 sqrt followed
by reciprocal, or one binary32 rounding of reciprocal sqrt of the binary32 squared
norm; binary64 or binary32 edge/dot evaluation; no tie perturbation or the retained
oriented nextafter. The single-round path does not claim to emulate a GPU's
approximate-rsqrt instruction. Axial delegation is unchanged. Seal predictions
for all3968 original oblique rows and544 setup rows before full comparison to
either array. Require zero full-RGBA errors across both datasets; report interiors
separately, without selecting a nonzero winner or fitting an epsilon/offset.

The shared-reciprocal family is now refused on both complete training datasets.
Thirty-one CPU controls pass. All twelve paired streams were sealed first and
regenerated unchanged during comparison. Original errors range2770..8782 pixels;
setup errors1154..3642. Frozen result:
build/smooth-reciprocal-study-root-1/result.json,
SHA256613931a7519c870db127db544db92bcaedc6522cf12534aa5f12fedb12746730.
No scalar-precision path is selected.

A stronger saved-data counterexample rules out the whole local-product class
tested here, rather than just those twelve precision choices. Vector2, width1,
phase0 forward pixel(29,24) and reversed pixel(30,26) have identical canonical
segment delta, width, signed unnormalized cross and both endpoint dot products.
The integer feature tuple is(9216,6912,256,-1474560,63406080,69304320), but
reference alpha is115 versus140. The local operands/products at these two pixels
are exactly representable in binary32 before reciprocal multiplication. Every
frozen predictor returns equal RGBA for both, verified independently from saved
source and admitted original frames. Six integer identity/domain controls pass.
Proof: build/smooth-reciprocal-symmetry-proof-root-1/result.json,
SHA256f4e6ce1fbc112be98e5f6597d07e3b51ad54104c42825b2e7091425cb174bb1b.

Thus changing only a direction-independent scalar inverse-square-root/length
approximation cannot resolve this witness. The proof does not exclude setup
depending on signed delta direction, absolute screen coordinates or joint
endpoint-origin/length rounding. Those dependencies are the next investigation;
the earlier naive binary32 direct-plane family remains rejected. Keep all frozen
models and images unchanged. The witness is diagnostic evidence, with no
geometry-specific shader branch, calibrated bias or pixel correction.

Predeclare a signed-coefficient family: normalize the exact binary window delta
in binary64, then convert the signed tangent components to binary32 using nearest,
toward-negative-infinity, toward-positive-infinity or toward-zero rounding.
Use the existing twelve direct-plane constant/evaluation/tie paths, for48 coupled
variants. This is a test of signed conversion, not a claim about native hardware.
Keep both minor/cap footprints and nibble/alpha arithmetic fixed. Freeze all source
first, then apply the already-saved115/140 two-pixel training witness as a necessary
condition. Refuse failing variants immediately. Seal all4512 predictions for each
survivor before opening either full original-oblique/setup array. A survivor still
needs zero full-frame errors over both sets. No origin tuning, free epsilon,
observed-value lookup, holdout or renderer change is allowed.

The signed-coefficient family is refused. Fifty-six arithmetic/domain controls
pass. After source freeze,36/48 variants fail the fixed two-pixel necessary
condition; all4512 predictions for each of the12 survivors are sealed before
either full reference array is opened. Every survivor then fails: original
errors4097..6544 pixels and setup errors1657..2972. Evidence:
build/smooth-signed-plane-study-root-1/result.json,
SHA25620eb3f62ab16d0e7811ab0a91761269ebcfc7f5c2911ce77368def76eac128ee.
Signed coefficient conversion alone, in these declared plane paths, is insufficient.

Predeclare a viewport control before any new observation. Reuse all eight
original oblique vectors, both directions, widths1/3.25 and phases(0,0)/(0,255),
for64 existing window geometries. For each, use viewports(0,0,64,64),
(-8,-8,64,64),(0,0,128,128),(-16,-16,128,128). Keep the FBO/readback64x64 and
derive clip positions by the inverse viewport transform, accounting for GL's
bottom-left viewport Y and the readback's top-left window coordinates. Every
transform is dyadic/exact in binary32, and endpoints retain at least3 pixels of
viewport margin for the declared widths. This gives256 rows,64 baseline rows
matching original vertex bytes and64 end-of-sweep baseline repeats. No new
window-space geometry is added to the training-exclusion set.

tools/smooth_line_viewport_training.py has a distinct exact typed role; original,
corner and setup roles reject it. Its validator checks the actual declared
viewport first, then reuses all other unchanged state invariants through a copy,
preserving the raw state record. Require exactly one declared glViewport prefix
and the unchanged complete row batch after it. The separate capture entry point
preserves exactly one read and raw-before-after-state/frame/command acceptance.
The shared provider and old role guards remain unchanged. Two hundred fifty
combined CPU controls and isolated worker CLI import smoke pass. This is CPU
preparation only; a fresh source packet, prior prediction seals, peer review,
admission and saved reader are required before capture.

All64 baseline rows and64 repeats must match exactly or invalidate the capture.
For each nonbaseline viewport, compare all RGBA bytes with its same-window
baseline without requiring equality as an observation-admission gate: differences
are the quantity under investigation. Record every comparison and both viewport
states. The fixed normal-cap CPU hypotheses predict viewport invariance in
window coordinates; construct those predictions from a plain Probe with the same
window geometry, not from the viewport-dependent clip upload. Seal all predictions
before observing. A viewport effect would support coordinate-conversion/setup
dependence, while equality would be bounded evidence only. No geometry-specific
correction, free origin selection, holdout or renderer admission follows.

The viewport control is now frozen as Source8 with32 members, including the exact
250-case passing provider controls, AGPL and unchanged original BSD. Authoring:
build/smooth-training-source-root-8/authoring.json,
SHA256ed146ff07eb016f22bbea22397a1382e73d6639e8ae7421f258154c8516a7b5d.
All three refused normal-cap hypotheses have256 window-coordinate predictions
saved before observation; each four-viewport group is verified identical, and
all64 baseline aliases have matching original vertex bytes. Seal:
build/smooth-viewport-prior-predictions-root-1/seal.json,
SHA256166428d67b3d1701a3468055b0506153fe22283599f0ddf591d33bab95fb325f.
Frozen CLI imports pass; the launcher requires256 accepted frames and64 repeats.
This packet has no capture authority yet. Fresh source/reader review and explicit
admission remain necessary before the new observation; no GPU has been used here.

Source8 viewport observation now passes saved review after scoped peer review and
source admission. CPU bridge verifies all256 window roundtrips and64 default-
viewport upload aliases; all32 reversal-invariant window geometries are already
covered by the frozen training-only exclusion registry. No held-out input is read.
The peer verdict is ready subject only to pinning the fresh review digest and
resolving a stale supplementary-review comment; both are closed before execution.
The reviewed reader hash is pinned before capture and is not changed afterward.

Actual capture retains256 accepted observations and64 end-of-sweep repeats;
the direct launcher stages and real worker are terminal before owned environment
cleanup. The parent holds frozen source/native4 and prediction/registry hashes
before/after. Reader validates complete setup/row/cleanup chronology, actual
viewport and other state, startup/oracle baselines, artifact/frame hashes and
exact64 repeats/64 original baselines before analysis. Evidence:
build/smooth-viewport-saved-review-root-9/result.json,
SHA25673ed028041f09120f11f65fb45aab64c43e394cec130530875a76c4ead47a6cd.

Every one of the192 changed-viewport full-frame comparisons is byte-exact, with
zero maximum channel error in each group. No origin/scale effect is observed
here. The recorded viewport-edge caveat therefore does not explain a measured
difference in this experiment; universal invariance is not established.
Models0/2 still miss168 pixels/20 rows and model1 misses192/28, all remaining
refused. These data do not select a plane origin or qualify a renderer. Focus next
on signed primitive setup and actual window-coordinate evaluation; additional
window-translation controls, if needed, must be predeclared with explicit pixel
correspondence and without mutating stored reference frames or future holdouts.

Predeclare a separate integer window-translation control: the same64 baseline
geometries from the viewport study, with all offsets(x,y) in{-4,0,4} squared,
ordered Y then X. This is576 rows; offset(0,0) is row4 of each9-row group and all64
such rows repeat after the sweep. Viewport/FBO/readback stay(0,0,64,64). Length,
direction, width and subpixel phase remain fixed within a group. Expected
comparison pairs baseline pixel(x,y) with shifted pixel(x+offsetX,y+offsetY),
over the in-bounds intersection. Both frames' unmatched pixels must remain clear;
the existing four-pixel border rule also remains mandatory. Store both raw frames
unchanged: the correspondence is an invariance diagnostic, not a candidate-image
alignment, modified reference, pixel correction or renderer qualification.
Every512 nonbaseline comparison must be reported, whether equal or different.
Any baseline/repeat mismatch invalidates the capture. Freeze all prior predictions
and update the training-geometry exclusion registry before observation, preserving
the old registry and protected holdouts. New roles remain disjoint and must be
admitted before device/file access. Fresh source/reader review and admission are
required before any actual window-translation capture.

The integer-window control is implemented with exact role gates and raw-preserving
correspondence diagnostics. Complete provider controls pass281 cases. Source9:
build/smooth-training-source-root-9/authoring.json,
SHA2561f71e9a4acbfe955f075fb925a76575592adcdefbc146d94a1c43b657dc3b331,
34 frozen members including AGPL and unchanged original BSD. Three prior models'
576 window-coordinate predictions are saved and sealed before observation:
build/smooth-window-prior-predictions-root-1/seal.json,
SHA256b6d4678606e86a63a1aa6b853f5afdb039205ce12a5202fd284bb4703bf5643f.
All1728 corresponding model-image checks are exact with clear unmatched pixels;
the models stay refused because their earlier full-training failures remain.
All64 baseline aliases reproduce original clip uploads. Frozen CLI imports pass.

The new training-only exclusion registry contains6142 reversal-invariant hashes
(12028 directed geometries over12512 declared rows), retaining every prior5886
key as a subset: build/smooth-training-geometry-exclusion-root-2/registry.json,
SHA25671be08191ffa5df72a526c29c5142c152ef68eeee7d5e2990c748c07fc975e3f.
Previous registry/data stay unchanged; no held-out descriptor or frame is read.
Source9 is not capture-authorized yet. Fresh source/reader review and admission
must precede observation, with exact64 baseline and64 repeat gates and all512
nonbaseline correspondences reported irrespective of their equality.

Source9 review identifies pre-capture conditions. Preserve its frozen64-repeat
packet and the failing review without launching it. Corrected Source10 keeps the
same576 main descriptors and changes the repeat sweep to all576 rows in reverse
order. Every moved
row must therefore reproduce exactly as well as every baseline. Before capture,
read only the64 already-admitted original training baselines and require their
nonclear bounding boxes within[8,56) on both axes, proving feasibility for the
declared±4 shifts under the unchanged four-pixel-clear border rule. Unmatched-
clear checks are implied by that border rule here and are not independent proof.
An admission review must end with the exact ready token and contain no fix token;
mentions of readiness inside a failing review do not authorize execution. Update
all receipt text to the corrected source and retain historical export/shader
controls only as explicitly labelled lineage. Freeze corrected source, prediction
lineage and reader before a fresh conditions review and observation.

Predeclare a directed-normalization family, separate from capture source. Compute
the signed major/minor delta and squared length in binary32. Use binary32
sqrt-then-reciprocal or single-rounded reciprocal-sqrt of that squared value.
Multiply signed major delta by that rounded reciprocal in binary64 (exact product
for two binary32 operands), then round that signed product toward positive
infinity to binary32. Use its magnitude as the normal gradient. Keep oriented
one-ULP nibble ties, the existing normal cap rule, staged attenuation and alpha
encoding fixed; test binary32 and binary64 evaluation, for four variants. This
tests operation order and signed conversion, not an asserted hardware formula.
No fitted epsilon, geometry-specific bias or lookup is added. Freeze sources,
apply the retained two-pixel necessary condition, and seal all surviving full
training predictions before comparing complete arrays. Axial delegation is held.

Source10 observation is admitted by the saved reader:576 main frames,576 reverse
repeats and64 original baselines pass. Of512 prescribed window comparisons,
21 rows differ at26 pixels. No raw image is changed. Before reading those pixels
for localization, classify by exact integer projection t=dot(pixel-start,delta)
and L=dot(delta,delta): central-half when L<=4*t<=3*L; otherwise within-segment
when 0<=t<=L; otherwise beyond-endpoint. Preserve signed direction in the complete
local input key and require equality for every shifted witness. This diagnostic
must report all26 witnesses and reconcile all512 counts with the saved reader;
it does not select a model or qualify the renderer.

Localization now passes all512 count joins and all26 signed-local key joins:
build/smooth-window-localization-root-1/result.json,
SHA2566e1ee6aefe3b809f8cd6112f41bdbb29553926e4784ca9d2d7dfd2424fa34cdc.
Four pixels are central-half and22 are elsewhere on the closed segment; four of
those22 have exactly endpoint projection. Vector3 forward has15 alpha-only
differences, vector5 reverse has7 covered/clear differences (4 central), vector6
has4 endpoint alpha differences. All raw bytes remain unchanged. A local-only,
translation-invariant formula is insufficient even for interior coverage; examine
absolute-coordinate setup/evaluation next. This does not uniquely identify the
dependency. An absolute centerline evaluated in floating point, already present
in some refused models, is not itself translation invariant in finite precision.

The four directed-normalization hypotheses have been tested: binary64 evaluation
fails the retained necessary witness; the two binary32 variants still miss
829/834 original and790/732 setup pixels. The family remains refused; its12 CPU
controls pass. Saved result:
build/smooth-directed-normalization-study-root-1/result.json,
SHA256f3e664c7a8d6d13517914fa537c2a5d462f01bb99ed520cf53f799c8d03313cb.

Only a mechanism passing full-frame references can enter the generated consumer.
Before another full study, test24 absolute normalized-plane variants against all
26 admitted translated pixel pairs. Combine two staged reciprocal paths
(binary32 sqrt-reciprocal or single-rounded reciprocal sqrt) with signed
reciprocal products rounded toward positive infinity, two existing plane-constant
paths (split/fused), three evaluation paths (binary32 split/fused or binary64),
and two existing nibble tie paths (none/oriented-nextafter). Keep width, cap,
attenuation and alpha rules fixed. This combines independently refused pieces
without fitted parameters. Freeze source and seal all52 RGBA predictions per
variant before comparing those saved observations. Only a variant matching
every necessary witness may proceed to a full reference study; passing this
gate would not establish full-frame parity.

The24-variant normalized-plane family now fails that gate: best8/26 exact pairs,
no survivors. Its29 CPU controls pass, and all predictions are sealed before
comparison in build/smooth-normalized-plane-witnesses-root-1. Result SHA256:
f02c6687136b26568b5e7740b4e7053fc0ce55b43bcd40823de296d5d90c4d14.
Do not run full-image sweeps or qualify a renderer from this family. This rules
out only the declared standard global-plane operation orders, leaving other
absolute-coordinate and incremental setup structures open.

Predeclare the next24 variants as distance-plane staging: retain the same
normalization, setup, evaluation and tie choices, but calculate a zero-offset
signed perpendicular plane first, then halfWidth-abs(distance). Longitudinal
planes also have zero offset, followed by adding0.625 to their minimum. The
previous family folds halfWidth/0.625 into plane constants; distributivity is
not assumed in finite precision. No coefficient or parameter is fitted. Seal
all52 necessary-witness predictions before comparing, and refuse any variant
that misses even one of26 pairs. No full sweep follows a refused witness gate.

All24 distance-plane variants now fail the necessary gate, best10/26 pairs:
build/smooth-distance-plane-witnesses-root-1/result.json,
SHA2568196bd4d0462d4a781fa839fa5951ea99b9876f2058a688dd0f0009aff97f80a.
The frozen packet preserves all52 predictions per variant before comparison.
This family is refused without generating redundant full-frame arrays or
changing any reference, renderer, tolerance or held-out input.

Before further hypotheses, inspect all576 admitted window frames for conflicting
RGBA at identical exact signed perpendicular-distance numerators within each
frame's strict central half (L<4*dot<3*L). Group within a single frame only, so
direction, endpoints, width and absolute segment setup are held. Record every
conflicting distance group and its pixels, including covered/clear distinctions.
This tests the necessary condition of a distance-only coverage function within
that region; it neither assumes affine coverage nor selects coefficients. A
conflict rejects that class, not all possible position-dependent evaluation.
Freeze the diagnostic source before raw access and keep all raw bytes unchanged.

The exact same-frame diagnostic finds3 conflicting frames, each with one
distance group, all vector5 reverse width832 phase000/255. In frame423, pixels
(8,19) and(9,23) are clear while(10,27),(11,31),(12,35) have RGBA255/255/255/16;
all are strictly central and have signed cross numerator-5015808. Frames424
and426 have the same clear/covered conflict along that exact-distance locus.
Saved result: build/smooth-window-equal-distance-root-1/result.json,
SHA2562be0a3bcc6338e5829d8496f60ab845a483493157b7f5b87f45f1d7d4ec85fa1.
No scalar function of ideal exact perpendicular distance, with arbitrary
per-frame scalar coefficients/intercept, can explain these conflicts. This
does not rule out a tilted two-coefficient plane, along-line dependence, or
position-dependent evaluation rounding. In particular, do not misstate this
as rejecting all coefficient-setup errors. Preserve these same-frame witnesses
alongside the26 cross-frame necessary pairs for future hypothesis admission.

Before another predictor family, check existence of an arbitrary tilted affine
nibble plane independently for each signed side of frames423/424/426. Use all
strict-central-half pixels on that side, including clear and saturated pixels.
Nibble0 constrains plane<1, nibble15 constrains plane>=15, and other nibbles
constrain n<=plane<n+1. A numerical LP may suggest a rational certificate, but
every observation must pass an exact Fraction verification before feasibility
is claimed. Solver failure or a failed certificate is inconclusive, not proof
of infeasibility. These fitted diagnostic coefficients cannot enter a predictor
or renderer. Freeze code and CPU controls before reading admitted raw frames.

All6 independent side/frame groups have exact feasible certificates, covering
3696 central pixels. Result: build/smooth-tilted-affine-diagnostic-root-1/result.json,
SHA256f704b4ebf03fead31b53c0b666ddf4f7dca865c9aa30c958ee039068ea98d9d7.
The exact certificate helper passes9 CPU cases, including strict bounds,
saturation and a rational distinction lost by binary64 conversion. Feasibility
does not establish a shared coefficient rule, mechanism or generation mask.

Next check a stronger coupled constraint: all three frames share one coefficient
pair, with opposite slopes on their two sides, while the6 intercepts remain
independent. Bound each doubled-coordinate nibble slope to the adjacent binary32
values around the nearest binary32 ideal geometric value (8 times the unit
normal). Preserve every3696 sample constraint and require exact rational
certificate and bound verification. This is an existence test only: no chosen
coefficient/intercept may enter a predictor, and solver failure is inconclusive.

The coupled near-ideal test has an exact feasible certificate across all3696
pixels with one shared coefficient pair and6 independent intercepts. Result:
build/smooth-tilted-affine-diagnostic-root-2/result.json,
SHA256e342cd8423853af97d6db08fed7d8b19dfa7309c02eec68b94b371d0b2d0bbeb.
No LP coefficient is selected for prediction. This motivates testing rotation
before signed rounding: earlier models round the tangent then rotate/negate it,
which preserves a power-of-two component ratio when signs match. Independently
rounding the already rotated normal, whose component signs differ, can tilt it.

Predeclare48 variants: take the24 normalized-plane arithmetic paths and the two
coverage-offset/distance-first stages. Normalize each of the four unrounded
signed normals (-dy,dx),(dy,-dx),(dx,dy),(-dx,-dy) independently; never obtain an
opposing normal by negating already rounded coefficients. Keep cap footprint,
attenuation, nibble mapping and alpha encoder fixed. Before any full sweep,
seal predictions and require all26 translated pairs, all15 same-frame conflict
pixels, and the earlier forward/reverse two-pixel witness. No fitted diagnostic
coefficient, epsilon or pixel lookup may enter these predictors.

The48 rotation-before-rounding variants all fail the combined necessary gate,
best10/26 translated pairs. All15 same-frame pixels and the earlier2 reciprocal
symmetry pixels are included as independent necessary gates. Its51 CPU controls
pass, including the noncommuting rotation/rounding case and48 exact axial
delegation cases. Result: build/smooth-rotated-plane-witnesses-root-1/result.json,
SHA256070c08b32452307cb832cd210df4466fb3bcfd19be1f66800d780177ae2d42f8.
Thus neither arbitrary per-frame scalar distance corrections nor any tested
standard plane setup/rounding order closes the gap. Shared near-ideal tilted
slopes remain compatible diagnostically, with intercept construction/evaluation
still unresolved. No diagnostic LP coefficients are renderer inputs.

Predeclare a fixed-coefficient intercept diagnostic on the same6 groups. Use
the two reciprocal normalization paths, with normals either rotated before
rounding or obtained by rotating the rounded tangent. Intersect exact bounds
on the constant from every central pixel for each of24 group/path cases.
Do not select a constant from a feasible interval. Check whether the ideal
geometric constant and the existing binary32 split/fused constants (coverage
offset or zero-distance then width) fall inside. This concerns exact evaluation
and plain nibble floor only; it cannot exclude other finite-precision evaluation
or tie rules. Freeze helper/tests/normal arithmetic before admitted raw access.

The three-anchor diagnostic does not find a common construction for all groups.
Midpoint admits the same12 cases as first endpoint; exact second-endpoint
construction adds only2 cases, while binary32 constructions still admit12.
Result: build/smooth-anchor-intercepts-root-1/result.json,
SHA256f6ea6f3f558010298a611618e2a00f5638af2478c83f3843403d5cd3f7e7fdd1.

Predeclare48 homogeneous-normalization variants. For each of four unrounded
signed normals, form raw C=-a*x0-b*y0 (one binary32 rounding of the bounded
binary64 sum), then apply the same rounded reciprocal length to a,b,C. Signed
normal products use the existing positive-infinity binary32 rounding. Constant
products use nearest or positive-infinity rounding, either adding the coverage
offset before that rounding or adding it after distance-plane evaluation.
Use the two existing reciprocal paths, three existing evaluation paths, and two
tie paths. This forms C before normal-component rounding and introduces no fitted
constant. Freeze and require all26 translated pairs,15 same-frame pixels and2
older symmetry pixels before a full-array sweep. All prior refusals stand.

The fixed-normal diagnostic finds18/24 feasible constant intervals. All6
problematic-side tangent-first cases have no feasible exact constant; all6
rotate-first cases have a feasible interval but none of the five existing
constant constructions is admitted. The12 opposite-side cases admit all five.
Result: build/smooth-fixed-normal-intercepts-root-1/result.json,
SHA2561b5c9a80e249be277ebbb1d3cf2818b8424cb337babf245ecdee727616e4c610.
The extended exact interval helper passes18 controls. No constant is selected.

Next test constant anchors at first endpoint, exact segment midpoint and second
endpoint, with the same five constant constructions and all24 fixed-normal
cases. These are geometric anchors, not fitted positions. Use saved exact
intervals, freeze this diagnostic before comparison, and report every anchor
whether admitted or refused. Anchor feasibility remains an exact-plane/nibble
diagnostic, not a finite-precision full-frame model or mechanism admission.

The48 homogeneous-normalization variants now all fail the combined necessary
gate; best8/26 translated pairs. Its53 CPU controls pass. No full-array sweep
follows. Saved result: build/smooth-homogeneous-plane-witnesses-root-1/result.json,
SHA2565ab97a3cf334d2f1bb828813845d6dcbcdc03f1f8ee5f985da5aa75626e88eff.
Do not replace the exact interval constraints with fitted constants or promote
any of these refused operation orders. Finite-precision or incremental plane
evaluation remains an unresolved mechanism direction.

Before another rounding family, check exact binary32 representability inside
every saved fixed-normal constant interval. For a coverage-plane constant divide
the nibble intercept bounds by16; for a distance constant divide by16 then
subtract half-width. Test the ordered finite binary32 encoding space by exact
rational comparisons, including signed zeros/subnormals. No midpoint or fitted
constant is chosen for a predictor. This diagnoses exact evaluation with the
fixed normal coefficients and plain nibble floor only; per-pixel finite-precision
evaluation and other coefficients/ties remain outside this class test.

Representability result:13/24 coverage-constant cases and12/24 distance-constant
cases admit any binary32. In the6 problematic rotate-first cases, only frame426
sqrt-recip coverage constant is representable; none of the6 distance constants
is representable. The other12 admitted cases are on the opposite side. Result:
build/smooth-constant-representability-root-1/result.json,
SHA256bf3555b8bd04a85f308239088a52ee441e7f9cb3bd4a6f6684b77a3e62896aac.
The exact encoding-space helper and prior certificate/interval controls pass27
cases, including subnormals, signed zero, finite extrema and strict rational
gaps. This excludes only binary32 constants with exact evaluation for those
fixed normals, not finite-precision evaluation or different normal coefficients.

Before adding a higher-precision constant predictor, compare the unrounded
homogeneous reciprocal product with every saved exact interval. Form raw C
from each unrounded signed normal and first endpoint, round raw C once to
binary32, then multiply by the prescribed binary32 reciprocal but preserve
the exact rational product and width addition. No final constant rounding,
fitted bias or selected interval point is allowed. Use the same24 normal/group
cases and report all. This tests whether constant rounding alone is a viable
next mechanism direction before generating any images.

The unrounded homogeneous product admits only the12 opposite-side cases and
none of the problematic-side cases. Saved result:
build/smooth-unrounded-constant-diagnostic-root-1/result.json,
SHA2563ce03bf96b78e0d814082e94a461e8e712e98d6b84a313ce3af309767a019df3.
Removing the final constant rounding alone does not close these exact intervals.

Predeclare a coordinate-order expansion of the independently rotated
normal family: two reciprocal paths; split or either fused constant nesting;
three binary32 split evaluation parenthesizations, either fused nesting, or
binary64 evaluation; two tie rules and two offset stages. These144 variants
retain existing arithmetic and parameters, adding only previously absent x/y
orders. Require the same26 translated pairs,15 same-frame pixels and2 original
symmetry pixels after sealing predictions. No full-array sweep after refusal.

All144 declared coordinate-order variants fail the combined necessary gate;
best11/26 translated pairs. The9 order-arithmetic CPU controls pass. Saved
result: build/smooth-ordered-plane-witnesses-root-1/result.json,
SHA2567e21d9bad199b7435f6085abc7487302dcac663eae54b0247bd92669f6080a52.
No full arrays or renderer qualification follows. These tests cover only their
declared operations, not all possible hardware setup, incremental evaluation,
coefficient quantization or precision formats. Retain every prior witness and
exact interval for the next structurally different mechanism investigation.

The [Vulkan smooth-line rules](https://docs.vulkan.org/spec/latest/chapters/primsrast.html#primsrast-lines-smooth)
leave coverage and area calculation implementation-dependent; they do not
specify the internal fixed-point or floating-point format needed to choose a
next exact model. Do not infer an NVIDIA precision format from that specification.

Predeclare the next exact diagnostic: enumerate all9 binary32 slope pairs from
the previously bounded three-value neighborhood of each ideal doubled-coordinate
nibble slope. Check each side independently, sharing its slope pair across
frames423/424/426 and allowing an independent constant per frame. For every
candidate intersect all central-pixel constraints and test existence of any
binary32 coverage or distance constant, using exact rational endpoints. Report
all18 side/candidate combinations, including rational-feasible but unrepresentable
cases; do not choose a fitted coefficient or constant for prediction. Opposing
sides may select independently, so this does not impose artificial negation of
rounded normals. The diagnostic concerns exact evaluation/plain nibble floor
within the stated neighborhood, not other normals or per-pixel rounding.

All9 nearby binary32 slope pairs fail to admit binary32 coverage or distance
constants across the3 problematic-side frames. Three pairs admit rational
constants. The opposite side admits all9 pairs with binary32 constants. Result:
build/smooth-nearby-binary32-planes-root-1/result.json,
SHA256851f7910f28f85231e4c35ce96ced116a9fb777e031b18acdcc33f1610fe55e6.
This is a class exclusion within the stated neighborhood, with sides independent;
it does not exclude finite-precision per-pixel evaluation or other coefficients.

Predeclare a block-relative evaluation family. Retain the144 declared ordered
normal paths. For block sizes1,2,4,8,16,32,64, anchor each block at its first
pixel center (floor(pixel/block)*block+0.5). Construct each plane constant from
endpoint coordinates relative to that anchor and evaluate it at pixel coordinates
relative to the same anchor. All calculations retain their declared binary32/
binary64 setup/evaluation stages. This is1008 variants; the block1 case is a
local-distance control, and block64 is one global pixel-center anchor. The sizes
are hypotheses, not asserted hardware tile dimensions. No raw data is sampled
by the predictor or used as a correction. Seal all necessary-witness predictions
before comparing; require all26 pairs,15 same-frame pixels and2 original pixels.
Do not generate full arrays if the necessary gate refuses the family.

The1008 block-relative variants all fail the combined necessary gate, best12/26
translated pairs;20 CPU controls pass. Result:
build/smooth-block-plane-witnesses-root-1/result.json,
SHA256b7df434989d81e31b2400fe5a347868239b4234a1420079722ec71a0b821562d.

Predeclare the related two-stage incremental family, retaining all1008 paths
and block sizes. First construct a single global plane constant from the endpoint.
Evaluate that plane at each block's first-pixel-center anchor using its declared
evaluation order, then evaluate the shared coefficients and that block value
at local pixel coordinates with the same order. This retains global setup error
before local evaluation, unlike rebuilding geometry relative to each block.
Block1 must exactly reproduce its parent global evaluator on the control probe
for every144 arithmetic path. Freeze and seal all necessary predictions before
comparison. No fitted tile offsets, extra precision knobs or image corrections.

The1008 two-stage incremental variants also fail the combined necessary gate,
best11/26 translated pairs. Its145 CPU controls pass. Saved result:
build/smooth-incremental-plane-witnesses-root-1/result.json,
SHA256dbc82ae329f5996b0c5a6fe9b8df24c26ce213b38cb27f72f70bd4001d4a70cd.
Saved prediction verification additionally proves every144 block1 incremental
stream equals the parent global stream for all retained witnesses. All432
block-relative size1/2/4 streams predict equal RGBA across each translated pair,
as required by their translation-preserving local coordinates; actual native
inequalities therefore refute that local-only class independently of parameter
choice. This does not refute a small-block evaluator retaining global setup.
All source/prediction seals are held. No full arrays, new device call, image
correction or renderer integration follows either refused block family. Further
work must examine another coefficient/setup/precision structure, preserving all
same-frame and translated witnesses and the full-reference qualification gates.

Predeclare a fixed binary-grid diagnostic on all3696 central samples of the6
side/frame groups. Quantize each signed ideal unit-normal component exactly
on fractional grids8 through32 with nearest-even, downward, upward or toward-
zero rounding. Determine square-root rounding using integer squared comparisons,
not a floating approximation. For each of100 shared format/rule candidates,
intersect exact constant intervals and find the minimum common constant fractional
precision0 through48 admitting a coverage or distance constant on every frame/
side. Integer range is unbounded in this diagnostic; no hardware word width is
asserted. No coefficient or interval member is selected for prediction. These
are exact-plane/nibble existence constraints only, not finite-precision evaluation
or full-frame qualification. Freeze helper/tests before admitted raw access.

The range8..32 contains25 precisions and100 format/rule cases; the initial84
count was an arithmetic typo, retained in the first frozen source, and is now
corrected. The actual diagnostic covers all100;49 admit rational constants
across all6 groups. Result:
build/smooth-fixed-grid-format-diagnostic-root-1/result.json,
SHA2561f2ebfa580ef003704e7e2bfa36480223444d2a110a1e46e123f8de94910fa94.
The exact sqrt/grid helper passes22 CPU controls. Independent per-frame constants
remain diagnostic only; no precision format is selected from this feasibility.

Predeclare400 explicit fixed-grid predictors: fractional precision8..32, four
signed rounding modes, two constant formulas and two existing nibble boundary
rules. Independently quantize each of four ideal signed normal components using
the exact integer sqrt helper. Either quantize the ideal homogeneous constant
from the unrounded normal and endpoint, or quantize the endpoint dot product
of already quantized normals. Constant precision equals normal precision. Evaluate
planes exactly on the pixel-center lattice, add half-width/cap footprint after
distance evaluation, and retain staged attenuation/alpha encoding. The oriented
boundary rule uses a strict upper nibble bin when left-right>=0, equivalent to
the declared one-sided boundary limit, not a fitted epsilon. Preserve the axial
delegate. Require the same69 necessary pixels after sealing predictions before
any complete-array study. No LP coefficients or interval-selected constants.

The400 explicit fixed-grid predictors all fail the combined necessary gate;
best2/26 translated pairs. Result:
build/smooth-fixed-plane-witnesses-root-1/result.json,
SHA2565855349fe95f52e5fac00759c6145e84fdf77ee3e5c94b453b1781a684773594.
The final predictor source passes10 CPU controls in addition to22 exact arithmetic
controls. No constant or precision is selected for renderer use.

Predeclare a rounded-quad geometry family before further coefficient formats.
Construct an oriented rectangle from the segment and its unit tangent/normal,
then round its four corners to binary32 before deriving each inward edge plane.
Use three initial normalizations (binary64, binary32 division, binary32 reciprocal
product), two corner paths (split32 offset additions or binary64 construction
then32), two geometries (width/2 with1/8 longitudinal extension and0.5 plane
offset, or width/2+0.5 with5/8 extension and zero plane offset), two edge-plane
setup precisions (32/64), two constant constructions (normal dot or determinant),
the6 declared evaluation orders and2 nibble tie paths:576 variants. Binary32
evaluation explicitly transports setup coefficients to binary32. Preserve staged
cap attenuation/alpha encoding and the axial delegate. This is a hypothesis
about rounded geometry preceding plane setup, not a claimed hardware algorithm.
Freeze and seal all69 necessary-pixel predictions; every prior gate remains.

All576 rounded-quad variants fail the combined necessary gate, best11/26
translated pairs. Its21 CPU controls pass. Result:
build/smooth-quad-plane-witnesses-root-1/result.json,
SHA256e8c6b8608fc2d0cd05b30f5311b379759c76244596c3d6dbf9b7ffec13bee6d4.
These refusals do not exhaust rounded geometry or fixed internal formats, but
none of the declared mechanisms can enter the renderer. Retain all same-frame,
translated and older symmetry witnesses, and every full-reference gate. No
full arrays, held-out read, native process or image correction follows.

After a mechanism passes full-frame references, prove CPU-to-GPU bit
reproducibility on NVIDIA Vulkan, Intel Vulkan and lavapipe, actual whole-frame
GL parity for each admitted oracle, all changed
state/lifetime/budget and width-reuse contracts, and fresh installed-wheel scene
regressions. Metal and its oracle remain required. No unsupported case is skipped,
silently aliased, routed through foreign GL, or fitted with per-pixel corrections.

Predeclare a global slope/intercept-before-normalization family, distinct from
the previous endpoint-relative slope and normalized coefficient planes. Retain
dominant-axis selection. Use3 slope paths (divide32, reciprocal32 product,64),
4 intercept paths (split32, fused32,64-then32,64),5 residual evaluation orders,
4 normalizations from1+slope*slope (split32 or fused32 sqrt/reciprocal,64-to32,
64),3 normalization/coverage orders (split32, fused32,64), relative or global
longitudinal planes, the2 existing nibble ties, and2 generated-mask rules
(positive quantized alpha or positive geometric side/cap support):5760 variants.
Keep the existing staged cap attenuation, alpha encoding and axial delegate.
Generated zero-alpha fragments remain distinguishable under the geometric mask.
All constants derive from endpoints and width; no fitted coefficient/intercept.

The new finite binary32 FMA helper must preserve a tiny addend when a binary64
intermediate lands on a binary32 midpoint. Use exact binary32 products in64,
TwoSum error recovery and midpoint correction; check against rational rounding
including a2^-60 perturbation that plain64-to32 double-rounding loses. It remains
a bounded finite training helper, not a general floating-point implementation.
The pixel API and complete-frame API must be byte-identical. Freeze source and
CPU controls, then seal every69 retained necessary-pixel prediction before any
comparison. No full-array study follows a failed necessary gate. Original
holdouts and all protected payloads remain excluded; no native operation or
renderer integration follows unless every earlier quality/state/lifetime/budget
and new full-frame/held-out gate is met.

The5760 slope/intercept variants are refused: none matches any of the26
non-equal translated pairs. All149760 predicted pairs are equal. The selected
slopes are exactly -1/2,1/4,1/2,3/4,1 in every declared slope calculation.
Their bounded raw intercept/residual products and sums are exactly representable
on the1/1024 lattice in binary32. Normalization occurs only after cancellation,
so the same local geometry necessarily yields the same output. Extending this
translation-invariant factorization cannot explain the observed differences.
Result: build/smooth-slope-plane-witnesses-root-1/result.json,
SHA2561b2b78182d40b57714dc0e4d1bb23f3fd25ee1b691d58527ac568c6848a9843c.
Independent saved inspection verifies every source/prediction seal and all pair
equalities. No full-reference arrays, heldouts, provider or native renderer are
used or changed. The finite FMA helper passes25 rational/arithmetic controls;
this does not admit a smooth rendering mechanism.

Future holdout exclusions must now use
build/smooth-training-geometry-exclusion-root-3/registry.json,
SHA256a3ebbc9a3f696d05e0d91c30b2a4f64fa5dfa6924c9b48b902cbca01b8bf9420.
It retains all6142 native-training undirected keys and separately adds3 valid
synthetic CPU-control geometries, including endpoint reversal, for6145 total.
The12028 directed count remains explicitly scoped to native training. No new
holdout descriptor or capture is generated.

Before another setup-formula sweep, test whether finite binary32 evaluation
itself admits a shared nearby normalized slope pair and any binary32 constant
per original side/frame group. Keep the existing9 nearby coefficient pairs and
all3696 central observations; use declared evaluation orders and monotone ordered-
float bisection to intersect constant bounds. This is a representability
diagnostic, not a fitted raster model. Do not select an interval member for
prediction or claim full-frame coverage; freeze/test the exact arithmetic and
source before accessing the admitted observations. All original quality,
state/lifetime, hardware and protected-data gates remain required.

Finite-evaluation diagnostic declaration: six orders (sum-then-constant,
x-constant-first, y-constant-first, fused-x-outer, fused-y-outer, float64)
each use the same binary32 coefficient and constant transport. Three split
orders round each arithmetic operation to binary32; two nested FMA orders use
the bounded exact FMA helper; float64 evaluates transported inputs in binary64.
Coverage constants use offset zero; distance constants add width/512+0.5 after
plane evaluation in that order's precision. Saturated floor(16*value) supplies
alpha constraints only, including one-sided saturation. RGB/generated-fragment
masks remain outside this diagnostic.

Reuse exactly the prior nine nearby binary32 normal pairs (divide the prior
doubled-coordinate nibble slopes by eight), both sides of frames423/424/426,
and all3696 central observations. A constant may differ by side/frame, while
the nearby coefficient-pair index and evaluation order/placement must agree
across all six groups. Report648 group intersections and216 side summaries,
then list coupled pair existence per order/placement without choosing any
constant or selecting a model. Search every binary32 encoding in[-512,512],
including signed zeros/subnormals. Every group must contain a nonsaturated
observation: coordinates<=63.5, coefficient magnitudes<=2 and offset<=8 bound
the nonconstant terms by254+8, so constants beyond this domain cannot yield
that observation for these orders. The driver must freeze sources and the69
passing CPU controls, verify an independent source review, then read only the
previously admitted Source10 training array through its pinned Reader. Preserve
all original raw bytes and perform no new capture or heldout access.

Finite-evaluation diagnostic completed, 2026-10-21. The new interval helper
and existing exact-FMA helper pass69 controls (zero errors/failures/skips);
owned scratch is removed. First review requested stronger sample/coefficient/
shared-module bindings; its driver was never executed. The second packet is
superseded without execution. Third restricted read-only review operation
9cde31c1b8f4de7f87c2bea8d77c509fe197fe2490beee9c2c4babdab65004b7
admits the corrected driver, which freezes15 files before reading the admitted
training array. It reproduces all54 predecessor rational intervals, including
per-group counts and boundary witnesses, verifies exact binary32 slope transport,
width832, no omitted central cross-zero pixels and identical shared helpers.

Result build/smooth-float-interval-existence-root-1/result.json,
SHA256c09809d5b03864255285d0d0eec545c967b07b0d0bc5e1feb2e51d95b0b42bcc:
all12 coupled summaries have zero feasible nearby pair indices. Opposite-side
groups admit constants for all nine pairs, but no negative-side pair admits
constants across all three frames in any declared order/placement. Thus finite
evaluation in this declared neighborhood cannot rescue the shared normalized
gradient assumption, even with a free independent binary32 constant per group.
This conclusion is limited to the nine declared pairs and six declared orders;
it does not exclude every affine or interpolation mechanism.

Independent saved inspection recomputes all648 group intersections and54 prior
rational records, and separately checks2592 boundary comparisons using exact
rational arithmetic and direct nearest-even rounding, without the TwoSum FMA.
build/smooth-float-interval-prep-root-1/saved-review1.json,
SHA256799465f24e863332ce41b230a9655ee57058ed4e4b8d5fec5e610e8456feddaa.
Original training bytes, native4, AGPL license and all three original BSD license
copies are unchanged. All three review scratch directories are removed; useful
frozen/negative evidence remains. No fitted model, renderer change, full-array
qualification, heldout access, new capture or new geometry follows this result.

Next investigate geometry-derived raster/interpolation setup that can change
gradients between translated primitives, rather than repeating this refused
shared-gradient neighborhood or expanding arbitrary fitted coefficients. A new
mechanism needs a concrete derivation, frozen source/controls and preregistered
necessary observations before any study. Keep all original release requirements
and the latest future-holdout exclusion registry intact.

Triangle-attribute interpolation declaration, before prediction: reuse the
rounded coverage_quad geometry (three normalizations, two corner paths and
inner/support extents), assign the four inward coverage attributes from ideal
rectangle dimensions, then derive affine attribute gradients from each triangle's
rounded vertex differences and determinant. Use split32 or float64 setup followed
by explicit binary32 coefficient transport, both diagonals and the six declared
finite-evaluation orders. Use ordinary saturated nibble floor, original cap/alpha
encoding and the two existing generated-fragment masks (quantized-alpha or
positive-geometry). This gives576 fixed variants. No LP/interval-selected slope
or constant; every attribute derives from endpoints/width/declared rectangle.

For each attribute, gradients solve the two vertex-difference equations; the
constant reproduces the first vertex in the declared setup arithmetic. The
distance between rounded corners is used through the triangle determinant,
without renormalizing an edge to unit length. Both triangles extrapolate across
their diagonal half-plane; use exact dyadic integer orientation on the rounded
binary32 coordinates to choose the half, first triangle at the diagonal. Coverage
clamping supplies the rectangle's outside rejection. The diagonal partition is
a declared computational hypothesis, not a claimed native primitive algorithm.
Require CPU controls for affine reproduction, reversed winding, singular input,
attribute transport, diagonal partition, selected/full pixel identity and the
unchanged axial delegate. Reuse only the three already-excluded synthetic CPU
geometries. Freeze reviewed sources and passing controls, seal all69 necessary
predictions for every variant before comparison, and require every retained
translation/same-frame/original-symmetry observation. No failed necessary gate
permits a full-array study; all earlier release and protected-data gates apply.

Triangle-attribute study completed, 2026-10-21.19 new controls plus the69
existing arithmetic controls pass88/88 with no failures/errors/skips. Exact
dyadic integer diagonal tests include a minimum-subnormal corner that binary64
orientation would lose. Synthetic Probe geometries remain the same three already
listed in the latest holdout-exclusion registry; no new geometry is captured.
Restricted read-only source review operation
842f27af00aaeea033bdf10fc646955eff89b62b630ea1d0144835ea44af0986
admits the bounded study. It freezes21 reviewed files plus the actual Source10
descriptor definition, verifies shared descriptor dependencies and module origins,
then seals every69 necessary prediction for all576 variants before comparison.

Result build/smooth-triangle-attribute-witnesses-root-1/result.json,
SHA256a6609ae64d151657fccf2665621f552f866521d10569656e9b18a04251cec1b2,
is REFUSED_TRIANGLE_ATTRIBUTE_FAMILY with zero survivors and best9/26 translated
pairs. Predictions SHA256f45e24a2c4c514e94e193148f90ef9848d53f10935ce52d2a5adf1fe07386024;
source seal bf9c1d8608721a68ecacd7af625953afb8785ad9c5b6c3e70b90b300d32c4114.
Independent saved inspection reproduces all39744 predicted RGBA values from
the frozen source, checks every necessary comparison and finds10190 equal
translated predictions. It preserves zero survivors rather than selecting the
best mismatching variant. Saved inspection
build/smooth-triangle-attribute-prep-root-1/saved-review1.json,
SHA25685ff3dd50e797343a7de0854b29e80371cf71434558a53b188ae600a28296778.

No full reference arrays, heldout/protected payloads, native operation, provider
or renderer change follows. Both new CPU/review scratch directories are removed;
source, prediction and refusal evidence remain. Continuity754071655baff8846f42a6f6ac524aa3d41fb878f7c1c752ff530068334ad076
holds native4 and AGPL/original BSD licenses unchanged. Do not repeat this
declared rounded-attribute family. Before another family, obtain a specific
derivation for sample-coordinate reconstruction or interpolation precision from
primary specifications/implementation evidence and explain its distinct necessary
prediction. A failed formula family does not weaken the original parity gates.

Primary-source check, 2026-10-21: the Vulkan specification's
[Smooth Lines](https://docs.vulkan.org/spec/latest/chapters/primsrast.html)
section leaves covered-pixel selection and area approximation to implementations;
it does not specify a bit-exact coverage arithmetic or interpolation precision.
NVIDIA's [Fast Prefiltered Lines](https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-22-fast-prefiltered-lines)
describes a programmable filter/lookup-table technique and notes vendor variation
in hardware antialiasing. It does not identify the observed OpenGL implementation's
setup formula. Neither source justifies another fixed precision/formula sweep or
a claim of native equivalence. Keep the smooth-line mechanism unresolved while
continuing independent original release work; no approximate substitute is enabled.


Shader arithmetic measurement declaration, before GPU operation, 2026-10-21.
The CPU rsqrt hypotheses used correctly rounded binary64 reciprocal sqrt cast to
binary32. They do not establish the actual shader coefficient bits. The current
WGSL accuracy table (https://www.w3.org/TR/2026/CRD-WGSL-20261021/#floating-point-accuracy)
allows inverseSqrt error2 ULP and inherits sqrt/normalize accuracy. The Vulkan
GLSL.std.450 precision table (https://docs.vulkan.org/spec/latest/appendices/spirvenv.html)
also allows inversesqrt2 ULP. Neither specifies fixed-function rasterizer setup.
This supports measuring actual arithmetic, not another arbitrary formula sweep.

Declare tools/smooth_line_shader_arithmetic.py: the16 directed vectors already
in original training,9 runtime-uniform fragment expressions (identity x/y,
dot squared length, inverse sqrt, reciprocal sqrt, inverse-sqrt product x/y,
normalize x/y), forward then reverse order. Encode floatBitsToUint results using
explicit byte shifts into one linear RGBA8 texel with blending disabled. Ten
fixed finite bit-pattern identity controls run through both uniform components;
signed zero, fraction, maximum finite and mixed bytes are included. Preserve all
308 raw readbacks and decoded bits before any line-observation comparison.
Require CPU byte-order, malformed-readback, signed-zero, training-membership and
missing/corrupt/unstable sequence controls before source review and GPU execution.
Use a clean installed archived Native58 wheel, exact package/module origins,
actual Vulkan hardware/device identity, waited worker and eight shutdown zeros.
Fresh external environment/cache ownership is removed after terminal workers.

This diagnostic measures this shader/compiler/device path only. It does not
identify an NVIDIA internal algorithm or admit a renderer model. No raw line
reference, holdout/protected payload, formula selection or fitted coefficient is
needed. First seal the measured bits. Only then compare the measured product
normal for the already admitted negative-side direction(-9,-36) with the exact
nine-pair neighborhood from the previous existence proof. If it falls inside,
reject that product-path explanation without another interval sweep. Other
arithmetic outputs are descriptive and do not authorize new model selection.
All original parity/platform/state/lifetime/performance requirements remain.


Source1 review06b5a6ef4d48592be5be3fcf259cd733aa111f81b83cc395b85f1fdeccccd953
requires exhaustive channel-byte controls and failure-path worker termination
protection before execution. Source1 already failed parent structure preflight;
no GPU operation occurred. Preserve its12 exact source inputs under the prep
source1 tree and its review/refusal. Source3 supersedes Source2 before execution:
append1024 finite normal identity words so every byte value appears in every
channel; retain original10 words. Both identity paths give2068 controls, with
288 arithmetic/reverse-repeat reads, total2356. No subnormal/NaN/Inf word is
transported. Add exhaustive CPU membership/finite-word control. Include the
training descriptor definition in the source seal. Missing/malformed/nonce or
termination failures preserve a parent process/error receipt and write the
unverified-worker marker before environment teardown.

Predeclare the follow-up normal mapping: for direction(-9,-36), set
normal a=-product-y and b=product-x by exact binary32 sign-bit operation, with
no divide-by-8. The prior existence study already divides its older doubled-
coordinate slope coefficients by8 and evaluates pixel-center coordinates; its
stored coefficient_a_bits/coefficient_b_bits are these unit-normal components.
Compare those exact stored pairs to the measured pair, without rounding or
coefficient selection. An outside-neighborhood result also admits no model and
does not authorize a formula sweep; it only identifies an uncovered arithmetic
path requiring separate derivation. Keep all release gates unchanged.


Shader arithmetic diagnostic completed, 2026-10-21. The23 CPU controls pass.
Source3/run3 corrects the parent stamp and exhaustive byte transport; Source4/run4
also preserves the owned cache when actual worker termination is unverified.
Read-only review2 admits the arithmetic and review3 confirms cache preservation.
Review3's sole refusal misattributes review-operation3 to Source3. Actual saved
operation2 binds run3, while operation3 binds run4 and all13 current source hashes;
run4 correctly asserts operation3. The review prompt's global text replacement
obscured the old operation-name diff. Exact authoritative joins resolve the
naming objection without changing code, recorded in review-resolution3.json.
This is a recorded primary decision, not a claim of a READY verdict from review3.

The frozen Source4 installed archived Native58 wheel diagnostic succeeds on
NVIDIA RTX4090 Vulkan.2068 identity controls cover all256 byte values in all four
channels;288 arithmetic observations/reverse repeats are exact.2356 actual draws,
18 pipeline misses and4712 queue submissions are observed.550 installed package
members and native origins match the supplied pinned wheel. The nonce-bound
actual worker is terminal, all eight shutdown counters are zero, and both new
external environment and owned cache are removed. No line reference array,
holdout, protected payload, native4 or renderer change occurs.

Result build/smooth-shader-arithmetic-run-root-1/result.json
SHA2567278077b7c6b0a6edb11f5bcbbb15446141c0f4650be750c52d3ff4ebb3e3ea9;
raw measurements baf9bd1887734218a9e4fd88bd5fe5ca225651ba015869dea95d630ccb5fd0b1.
For direction(-9,-36), exact sign-rotated product normal bits are
(3f785b42,be785b42), INSIDE the prior nine-pair neighborhood. The earlier empty
shared-constant result already covers that pair. Reject the proposed explanation
that this measured GPU inverse-sqrt product escaped the CPU neighborhood; do not
repeat that interval sweep or promote another operation from this diagnostic.
This does not identify native rasterizer arithmetic or a coverage model.

Independent saved inspection verifies every2356 raw byte readback, all identity
and exact squared-length controls, all reverse repeats, actual draws/device,
source/review/CPU/provenance/process/cleanup joins and the predeclared normal-pair
membership. Saved inspection build/smooth-shader-arithmetic-prep-root-1/saved-review1.json
SHA25606fb1da1e7c4352cc3df39d7f033d2465c839ab5050e4873773255eb3f80894c.
All13 exact Source4 inputs are retained under the prep source4 snapshot before
this result is appended to the evolving plan. Preserve both failed preflight and
review lineage. Portable exact smooth coverage remains unresolved; no model,
full-array comparison, holdout study or release qualification is enabled.
