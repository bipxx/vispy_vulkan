# Multidimensional stage varyings: source implementation and driver failure

The current source preserves ordered varying-array dimensions through native
normalization, cross-stage matching and ordinary stage declarations. Generated
wide-line evaluation stores flat reflected leaves, then reconstructs the logical
shape before original fragment code. Equal-product different shapes reject.
The new dimension capacities count toward portable/evaluator cache budgets;
line layout validation rejects inconsistent shape metadata.

Python declaration discovery now retains shader stage identity: vertex `in`
variables are attributes, fragment `in` variables are varyings. Array varyings
remain interfaces and cannot be assigned as uniforms. Varying input aliases keep
their source dimensions and compiler-assigned name. Existing uniform/sampler
and unsupported attribute/geometry contracts remain separate.

The 48 new pixel cases cover two- and three-dimensional float, vector, matrix
and flat full-width integer interfaces; smooth, noperspective and flat policies;
ordinary triangles and generated wide lines; changing uniforms and dynamic
fragment indices; legacy and modern declarations. Expected interpolation is
derived independently from window coordinates and unequal clip W values. These
cases are shared with the installed smoke helper; no failure is skipped.

Windows Vulkan passes all 218 combined regressions and all 171 shared smoke
controls, with nine zero shutdown gauges. Linux passes 212 combined regressions
and fails six clipped noperspective triangle cases. All other new varying cases
pass, including the generated-line path. Linux's smoke phase is not reported as
passing: it does not run after the regression failure. Compiler/reflection and
generated-line contracts pass on both platforms; Windows evaluator/cache
contracts also pass. The 84 Python declaration/composition/function tests pass.
The retained earlier module reproduces the original unsupported-interface error.
These results are source-functional and supply no installed/producer admission.

The published sampler checkpoint's CPU matrix also exposed an old assertion in
`typed_sampling_contract.cpp` that still expected typed arrays to be rejected.
It now verifies live signed/unsigned literal leaves and retains a separate
dynamic-index refusal. All 44 registered native CPU contracts pass on Windows;
the corrected typed compiler contract passes on Linux (1,695 assertions). No
native wheel or dependency was rebuilt for that assertion correction. This fix
will be published with the settled source packet, avoiding another CI restart
while the driver failure remains unresolved.

## Independent driver isolation

Scalar and nested controls produce byte-identical images. Both fail with clipped
noperspective triangles, while unclipped noperspective and smooth controls pass.
`tools/vulkan_interpolation_control.cpp` then reproduces the clipping error using
hand-assembled scalar SPIR-V and Vulkan directly, without VisPy, Dawn or a shader
translator. Three controls pass; clipped noperspective fails with 40 mismatched
pixels. Its device is the isolated Mesa 26.1.8 llvmpipe configuration already used
for qualification preparation. The device is awaited and objects destroyed.

The [Vulkan clipping contract](https://docs.vulkan.org/spec/latest/chapters/vertexpostproc.html#vertexpostproc-clipping)
requires noperspective output clipping to preserve linear framebuffer variation.
Inspection of the exact retained Mesa source finds a candidate arithmetic cause
in `src/gallium/auxiliary/draw/draw_pipe_clip.c`: it selects a coordinate axis by
comparing clip coordinates, then divides their difference after perspective
division. Unequal clip coordinates can project to an identical screen coordinate,
giving a zero denominator. A compiled reproducer using the extracted original
block yields NaN for a vertical unequal-W edge. The proposed
`compat/patches/mesa-26.1.8-noperspective-axis.patch` selects an axis after division;
the same CPU case then yields the independently expected 0.8. An ordinary-axis
control remains 0.8.

That initial CPU proposal is now separately GPU-verified in the bounded source
repair below. System packages, the original driver and immutable dependency
origins are unchanged. The original failing observations remain retained. No
test was changed to use unclipped geometry, an xfail or a different interpolation
formula, and no renderer workaround was introduced.

## Verified isolated source repair

Run `build/runs/mesa-lvp-repair-64/` uses the named build-hygiene profile with a
6 GiB declared peak under the unchanged aggregate 20 GiB cap. It projects the
same retained release archive into an owned Linux workspace, reuses existing
GCC/LLVM 18/Python and the system DRM runtime, and supplies small isolated build
tools/headers without installing packages or creating an environment. The
headless Vulkan-only configuration disables OpenGL/EGL/GLX and unrelated drivers.

The unpatched build reproduces the direct Vulkan failure on LLVM 18. Applying
only the recorded clip-axis patch rebuilds the affected object/archive/library
in 1.07 seconds; all four direct controls then pass. The initial driver build
takes 69.55 seconds. This isolates the source change within one configuration,
rather than attributing a result to switching from the original LLVM 20 driver.

The original six VisPy cases fail against the retained unpatched LLVM 18
library and pass within the complete 218-case patched run. The join verifies
identical renderer bytes, observed source and other loaded libraries. The
patched run also passes all 171 shared smoke controls, the original 58 scissor/
Tk resize/device-loss regressions and all four independent scissor controls.
Both complete eight-branch source Tk composites pass on their retained Windows
and Linux renderer modules. All nine shutdown gauges are zero.

This proves the source repair for the tested headless software configuration.
It does not establish complete window-system or native Linux GPU support, an
installed VisPy artifact, producer admission or aggregate release readiness.
The original LLVM 20 package/profile remains unchanged. The repaired driver,
exact patch/configuration, preferred sources, original notices and actual build/
control records are retained by hash; expanded sources, objects and caches are
disposable. Next: make this driver reproducible in the preparation/installed-CI
path, then renew affected profiles and publish the coherent source packet.

## Reconstruction and remaining work

Local records under `build/runs/varying-array-shapes-63/` retain the original
module rejection, Windows/Linux results, scalar controls and images, normalized
sources, original driver-source member hashes, direct Vulkan build/run, extracted
CPU reproducer, source delta, native artifacts and terminal cleanup receipts.
An initial Linux launcher used an obsolete script filename and exited before
rendering; its original command is retained separately from the six GPU failures.

The published sampler/cube checkpoint and its CI remain separate. Candidate
preparation stays bound to that earlier source until driver preparation/CI
integration settles; the repaired local observation is not installed proof.
The wider storage/interface inventory, runtime sampler indices, matrix/array
attributes, other shader/API/host obligations, independent review, producers and
installed qualification remain open. Metal stays experimental.
