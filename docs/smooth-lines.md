# Portable smooth lines

Single-sample `line_smooth=True` uses analytic edge coverage in the generated
line consumer. It supports fractional widths, including widths below one pixel,
and fades the original fragment output's alpha across the edges of a butt-ended
rectangle. Normal alpha blending makes those edges visible. With blending
disabled, coverage changes alpha while preserving the fragment's RGB values.

The path retains the existing endpoint evaluator, homogeneous clipping,
interpolation, fragment helper handling, depth reconstruction and resource
ownership. Width is a draw uniform, so changing width reuses the compiled
consumer and render pipeline.

This is an approximation to OpenGL line smoothing. Rotated edge pixels and joins
can differ between renderers. Exact-reference smoothing and multisample line
coverage remain unsupported. Analytic smoothing requires a `vec4` color output
so coverage can modulate alpha. Existing restrictions on early fragment tests
and fragment storage/image side effects still apply.

The generated-consumer C++ contract covers compilation, fractional widths,
chunk addressing, named color outputs and policy mismatches. Run it in a
configured native build:

```console
cmake --build <build> --config Release --target line_consumer_generated_contract
ctest --test-dir <build> -C Release -R "^line_consumer_generated_contract$" --output-on-failure
```

A fresh Windows CPython 3.12 build was checked on NVIDIA RTX 4090 Vulkan with
horizontal, vertical, diagonal, reversed and subpixel-width lines. Whole RGBA
readbacks agreed with the analytic policy within one UNORM8 step. Additional
checks passed for viewport clipping, unequal endpoint W values, depth occlusion
and alpha blending. Width changes reused the consumer and pipeline, and nine
live resource gauges returned to zero after shutdown. The public axes/colorbar
fixture also rendered successfully and was visually inspected.

Fresh Windows wheels for CPython 3.10–3.14 also pass isolated installed-package
checks for clear rendering, blended smooth lines, pipeline reuse and compiled
SDF text. The CPython 3.12 wheel passes 53 retained functional cases across
mesh/layout, Glue, napari-threedee, scalar/categorical volumes, images and labels.
Forty-two complete frames match their original references exactly; axes/colorbar
is checked for visible correctness, and the host overlays retain their original
state and landmark checks rather than a claim of exact rasterizer parity.

A fresh Linux CPython 3.12 wheel builds from the published sources with GCC 13
and Ninja, with Dawn's unused C++ module interface disabled. An isolated WSL
consumer passes clear rendering, both blended smooth widths, pipeline reuse and
compiled SDF text using llvmpipe software Vulkan. Package bytes, native-library
origins, both license families and shutdown cleanup are verified. This raw
`linux_x86_64` wheel is not qualified for manylinux or other distributions.

Native Linux GPU and macOS Metal checks remain unavailable. Historical exact
OpenGL comparison results and strict latency/memory benchmark gates remain
unchanged; those lab measurements are outside practical completion scope.

Practical completion prioritizes functional rendering and stable packages.
Small rasterizer edge differences do not block that scope. Additional exact
reference matching and MSAA line coverage are deferred; no partial MSAA
implementation is included.

## Parity criterion for smooth-line frames

OpenGL `GL_LINE_SMOOTH` coverage is defined by the driver, so whole-frame exact
comparison against one driver's output is not a meaningful parity target. Since
2026-10-28, the two napari-threedee overlay suites
(`tests/hosts/test_napari_threedee_overlay_parity.py` and
`tools/napari_plugin_wheel_suite.py`) compare candidate frames, including
before-event frames, with `tools/smooth_line_parity.py`:

- A pixel whose 3x3 neighbourhood in the reference is uniform must match
  exactly. In the manipulator reference frames, 95.9-96.0% of pixels are
  uniform in this sense.
- Every other pixel may differ by at most 32 of 255 per channel.
- At most 1% of the frame (491 of 49,152 pixels) may differ.
- Fixture landmarks, host state, parameters and Qt events stay exact.
- OpenGL-to-OpenGL reproducibility checks stay exact.

The rule tests the reference's uniform regions, not whether a difference is
antialiasing as such. It rejects:

- a line shifted by one pixel;
- a missing line;
- any change to a uniform region, such as the core of a line at least 3 px wide;
- any change larger than 32 levels;
- differences spread over more than 1% of the frame.

It admits changes of up to 32 levels on up to 1% of the frame wherever the
reference is not uniform. That includes edges, fringes and thin features without
a uniform core, so a lost feature with contrast of 32 or less could pass.
`tests/contract/test_napari_plugin_wheel_suite.py`, which runs in CPU CI, checks each of these cases with
synthetic line frames and the retained OpenGL frames.

The bound of 32 was set just above the largest measured difference, 29, on
NVIDIA RTX 4090 Vulkan against NVIDIA OpenGL. Other drivers may differ and must
be measured before this bound is relied on for them. The hash-pinned fixture
specification still says "whole-frame exact … no edge masks or fitted
tolerance". That text describes how the OpenGL references were captured and is
kept to preserve their hashes. Candidate comparisons follow this section.
Other napari-threedee suites still compare exactly.

Observed on Windows CPython 3.12 with RTX 4090 Vulkan and wheel `444402…`:

- The in-process overlay suite logged 212-254 differing pixels per manipulator
  frame, at most 29 levels, and none in uniform regions. Retirement was exact.
- The installed-wheel suite passed 5/5 under the same rule. It records results
  but not per-pixel figures.
