# Stencil capture and historical stock failures

Status, 2026-11-13: the same eight current source cases pass on Windows Vulkan
(native leaf `6dc06d2c…`) and WSL Mesa25.2.8 software Vulkan (native `5740b28a…`).
Installed successor qualification remains pending.
[Windows source scope](../compat/api-acceptance/stencil-public-routes-source-v1.json),
[WSL source scope](../compat/api-acceptance/stencil-public-routes-wsl-source-v1.json).

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
This does not establish arbitrary masks/formats, multisample or installed-wheel
coverage. It also does not make the unchanged stock wrapper pass. Q08/B10's
historical upstream admission remains unachieved; the practical disposition is
an improved public wrapper plus an explicit raw-GL boundary. SCI-06's selected
source investigation is recorded separately from installed acceptance.
