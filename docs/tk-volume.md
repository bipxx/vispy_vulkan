# Scalar volume on Tk

Run `python examples/tk_volume.py` in an existing Vulkan/Tk environment from the
[installation recipe](install-tk-cp312.md). It uses the public `SceneCanvas`,
`Volume` and `TurntableCamera` interfaces, with manual event pumping and canvas/
application cleanup on exit. Drag to orbit and use the camera's wheel to zoom.

The example displays two bright blocks in a 32-by-32-by-32 float32 volume.
Array axes are Z/Y/X. Rendering uses maximum-intensity projection (`mip`),
nearest interpolation, grayscale, contrast limits (0, 1), `r32f` texture storage
and relative step size 0.5. `create_scene(application)` returns the canvas,
view and volume; update the same visual with `volume.set_data(data, clim=(0, 1))`
or select `volume.method = 'minip'` for minimum-intensity projection.

## Finite source verification

The regression executes the actual example factory on Windows hardware Vulkan
and WSL software Vulkan. Literal 3-by-3 RGBA patches and actual Tk RGB points
check both initial blocks, movement of one block through a data update, its
vacated position, MIP/minimum-intensity changes, restoration, and unchanged
output after rejected method/array inputs. A final valid update restores the
original data using the same volume object.

The orthographic view has height 40 at 240-by-180, giving 4.5 pixels/world.
With camera center (15.5, 15.5, 15.5), zero azimuth/elevation and +Z up, block
centers (X, Z)=(8.5, 22.5) and (22.5, 8.5) project to (88.5, 58.5) and
(151.5, 121.5). Integer samples (89, 59) and (152, 122) lie inside the blocks.
All rays through a block also meet zero voxels along Y, so minimum-intensity
projection produces black at these samples while maximum intensity is white.

Reached controls suppressing the data update or the switch to minimum intensity
fail the intended pixel assertions on both profiles. All six workers terminate
with nine zero native resource gauges. Existing native libraries, interpreters
and dependencies are reused; managed scratch is cleaned after evidence retention.
Local evidence entry points are `build/runs/volume-windows-196/` and
`build/runs/volume-wsl-197/`. Source/native identity checks remain separate from
installed-artifact qualification.

Independent review198 approved the exact source packet with no findings, and
PR #22 merged it as `062fff14520e50e5892e48352bb0394b4b342320` with all eleven
required source checks passed. These checks do not qualify the example's `main()` loop, physical orbit/wheel input,
all volume methods, interpolation/clim combinations, scientific accuracy beyond
the authored binary data, mesh occlusion, perspective, performance or multisample
storage. The [historical volume tests](volume-wheel-regressions.md) and
[scientific admissions](volume-scientific-admissions.md) retain their original
artifacts/profiles; they are not new admission for this example. Metal graphics
remain experimental.
