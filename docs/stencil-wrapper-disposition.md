# Stencil capture and historical stock failures

Current installed checkpoint, 2026-11-13: all eight selected stencil cases pass
in the [current parent-wheel acceptance](../compat/api-acceptance/qt-parent-current-installed-v1.json)
on source `2b8bccd`, Windows `9e4e30cc…` and WSL Linux `a2715d26…`.
Each retained 44-case selected JUnit report has no failures, errors or skips;
its hash matches that packet. The same selection includes eleven numeric-zero
clear/flag/refusal-recovery cases, ten point controls (eight rendered reference
cases), four pending-filter revisions and two fixed scenes per platform.
These are local installed observations, with zero overlays and ten final zero
gauges, not final admission or published coverage. Older pending-installed
statements below describe their own earlier checkpoints.

Status, 2026-11-13: the same eight current source cases pass on Windows Vulkan
(native leaf `6dc06d2c…`) and WSL Mesa25.2.8 software Vulkan (native `5740b28a…`).
Installed successor qualification remains pending.
[Windows source scope](../compat/api-acceptance/stencil-public-routes-source-v1.json),
[WSL source scope](../compat/api-acceptance/stencil-public-routes-wsl-source-v1.json).

These eight cases also pass on the exact unreleased Windows wheel977357ad within
[21 selected installed checks](../compat/api-acceptance/lifecycle-windows-installed-selected-v1.json),
with537package members verified and zero source overrides. Linux installed
acceptance and formal successor qualification remain pending.

The same eight stencil cases now pass on the exact [Linux candidate8a793196 installed target](../compat/api-acceptance/lifecycle-linux-installed-selected-v1.json),
within21selected checks, with537members verified,zero overlays and ten zero final
gauges. Both local installed observations are complete. Formal admission and
delivery remain pending; earlier pending-Linux descriptions are historical.

The exact [manylinux candidate30a40dcb matched-driver installation](../compat/api-acceptance/lifecycle-linux-manylinux-installed-v1.json)
now also passes all eight stencil cases within21selected checks, alongside56Tk
baseline tests and recovery in a separate process on the same target. Both final
gauge sets are zero; archive metadata and installer RECORD also verify. This
adds exact retagged-artifact evidence, not formal profile admission or stock parity.

The historical eight failures describe stock VisPy 0.17.0, not eight confirmed
defects in the Vulkan renderer. The original manifest and failed process records
remain unchanged in `tests/reference/depth-capture-opengl`.

| Historical cases | Stock failure | Current route and disposition |
| --- | --- | --- |
| `stencil_float`, `stencil_u8`, `stencil_crop_float`, `stencil_noalpha_u8` | Public `gloo.read_pixels(mode='stencil')` reaches an unsupported `GL_STENCIL_INDEX8` mapping. | Supported public Vulkan wrapper: exact values, output type, crop and mutation verified against the retained raw-GL reference. |
| `stencil_gl_float`, `stencil_gl_u8`, `stencil_gl_crop_float`, `stencil_gl_noalpha_u8` | Lower-level stock `glReadPixels(GL_STENCIL_INDEX)` raises `KeyError: 6401`. | Raw `glReadPixels` remains unsupported by the Dawn facade. Each selected format/crop receives a useful `DawnCompatibilityError`; subsequent public wrapper reads preserve the expected target values and remain usable after mutation. |

Use `gloo.read_pixels(viewport, mode='stencil', out_type='float')` or
`out_type='unsigned_byte'`. Stencil floats contain integer stencil units, not
values normalized to 0–1. Alpha selection does not change the one-channel
stencil output. The selected single-sample 8×6 packed depth/stencil target
contains independently specified values 3, 37 and 203; mutation clears it to29.
The four stored raw-GL reference arrays provide expected values, types and row
orientation without invoking OpenGL in the candidate process.

Every new case explicitly deletes its program, vertex buffer, framebuffer and
attachments and asserts all nine owned-resource gauges are zero after close.
The source cases alone do not establish arbitrary masks/formats, multisample or
installed-wheel coverage; the finite installed checkpoint above is separate.
It also does not make the unchanged stock wrapper pass. Q08/B10's
historical upstream admission remains unachieved; the practical disposition is
an improved public wrapper plus an explicit raw-GL boundary. SCI-06's selected
source investigation is recorded separately from installed acceptance.
