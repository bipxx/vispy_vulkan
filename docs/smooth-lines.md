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

These are source-build checks. Refreshed wheel consumers and host workflows,
and GPU checks on other platforms, remain pending. Historical exact OpenGL
comparison results and strict latency/memory benchmark gates remain unchanged.
