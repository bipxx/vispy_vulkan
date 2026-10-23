# Installed-wheel mesh/layout regressions

The suite tests thirteen public scenes against immutable original NVIDIA OpenGL
references: flat/smooth meshes, SurfacePlot, texture/clipping/wireframe filters,
filter detach, perspective, polygon offset, adjacent clipped Grid ViewBoxes,
axes/colorbar, and multiline text at DPI 96/120/144.

All thirteen remain required. The axes/colorbar case currently fails at the
unsupported smooth-line consumer; it is not skipped or marked as an expected
failure. The renderer implementation and wider release requirements remain open.

## Run the wheel regressions

Build a wheel matching the selected Python interpreter, install the locked test
dependencies, and provide a fresh evidence destination. For example, in PowerShell:

```powershell
$env:VISPY_TEST_WHEEL = 'C:/artifacts/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
$env:VISPY_MESH_LAYOUT_EVIDENCE = 'C:/artifacts/mesh-layout-run-1'
python -B -m pytest -q tests/parity/test_mesh_layout_wheel_parity.py
```

The parent uses `uv` to create one owned environment outside the checkout, install
hashed locked dependencies and the selected wheel, and launch one isolated process
per scene. It waits for every launcher, verifies actual worker termination, and
removes the owned environment after the suite, including when a scene fails.
Every failed report and rendered artifact remains in the evidence destination.

`VISPY_TEST_PYTHON` optionally selects the consumer interpreter.
`VISPY_TEST_RUNTIME_REQUIREMENTS` can supply a hashed runtime requirements file.
`VISPY_MESH_LAYOUT_PYTHON` selects an existing external environment instead; the
suite neither installs into nor deletes that environment. The wheel must already
be installed there, and its package bytes must match the supplied archive.

`VISPY_EXPECTED_BACKEND` defaults to `Vulkan`; select `Metal` explicitly for a
matching macOS wheel. Software devices require
`VISPY_MESH_LAYOUT_ALLOW_SOFTWARE=1`. Actual device identity is recorded, and a
software run does not establish native GPU coverage. Linux/macOS graphics and
other Python ABIs are not qualified by the Windows observation below.

The hardware qualification workflow discovers these tests through
`tests/parity` and the `gpu` marker. The CPU workflow runs the four provider-free
contract modules before compilation; those controls do not create a graphics
device or establish hardware admission.

## What is checked

Each worker verifies installed package files and actual compiled-module origins
against the wheel, compatible wheel tags, and exact AGPL/original BSD texts. It
records loaded native images before shutdown, rejects repository native images,
and requires loaded VisPy libraries to be members of the installed wheel.

Comparison covers every 224x160 RGBA pixel with exact alpha. The original
per-case RGB limit remains unchanged: exact for layout/text/polygon offset and
at most one UNORM8 step for the specified shaded/filter scenes. There is no
alignment, edge exclusion or fitted correction. CPU text atlas arrays, glyph
metadata, font bytes and view rectangles must also agree exactly. Shutdown must
leave all eight existing resource counters at zero.

The fixed reference packet includes the original frames, atlases, commands,
shaders, parameters, source reports and authoring metadata. Its manifest digest
is `d4bdd74c7de56c9f2f615f6d0f9d591bf0de3670e762f7fc28b48e356719c153`.
Fixture-source hashes bind the recipes to those captures. Reference bytes and
both attached licenses are unchanged; tests never regenerate expected images.

## Bounded Windows observation

An independently reviewed frozen harness ran on 2026-10-21 using CPython 3.12.8,
NumPy 2.5.3 and hardware NVIDIA RTX 4090 Vulkan driver 610.88. The archived wheel
digest was `105698c7c6cef1e643b788a7b3a800e9630ebd7d9d6422fb4d11323389286f81`.
Twelve cases matched 430080 pixels with zero differing bytes and exact text
observations. Axes/colorbar failed at the existing smooth/MSAA policy refusal.
All thirteen actual workers terminated; native origins and cleanup checks passed,
and the newly owned environment was removed.

The complete local suite remained failed. Saved-result verification digest:
`eecee6bc7cd8886cbba777f69b9bc7aae75689805f629afcacfcda8f895e68ea`.
Raw local qualification packets are not distributed in this repository. This
observation does not refresh formal current-source identity or qualify a fresh
renderer build, other ABIs, drivers, platforms, hosts, physical Qt or performance.
