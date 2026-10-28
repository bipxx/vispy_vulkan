# Meshes on Tk

Run `python examples/tk_mesh.py` in an existing Vulkan/Tk environment described
in the [installation recipe](install-tk-cp312.md). The example uses the public
`SceneCanvas`, `Mesh` and `TurntableCamera` interfaces to display two unshaded
indexed cubes. Drag to orbit and use the camera's wheel interaction to zoom.
It uses manual event pumping and closes its canvas and application on exit.

`create_scene(application)` returns the canvas, view and both mesh objects.
Call a mesh's ordinary `set_data(vertices=..., faces=..., color=...)` to replace
its geometry and color. `cube_data(center)` supplies float32 vertices and
uint32 triangle indices without adding a dependency or another renderer.

## Verification boundary

The source regression executes the example's actual scene factory. A bounded
Windows hardware Vulkan and WSL software Vulkan runs check literal 3-by-3 RGBA patches and actual Tk
RGB presentation points for the two cubes, movement and recoloring of one
existing mesh, its vacated position, and restoration followed by a generated
quarter-turn drag. Orthographic height 2 gives 90 pixels/world at 240-by-180;
the initial projection is x=120+90X, y=90-90Z. After -90degree yaw, screen-right
is -Y and the selected cube centers exchange horizontal positions.

Reached controls that ignore the authored mesh update or ignore camera rotation
fail their intended pixel or angle assertions. All three workers per profile finish with
nine zero native resource gauges. The existing admitted native libraries are
reused; there is no native rebuild or new environment. Retained local evidence
is in `build/runs/mesh-windows-192/` and `build/runs/mesh-wsl-193/`.
Both runs retained their inputs and results and cleaned managed scratch.
The earlier broad mutation's unrelated
widget-construction failure is preserved in run191 and rejected as control
evidence. Run192 also preserves an initial JUnit-receipt parser failure and
the subsequent validation of actual worker failures.

Independent review194 approved the exact source packet with no findings, and
PR #21 merged it as `3d73a6a9dd54a8181788d35b4d5eb5a459fc6897` with all eleven
required source checks passed. This is finite source coverage, not a new installed mesh admission, full mesh
parity, depth-occlusion qualification, shading/filter coverage, perspective,
physical input, default wheel-rate or multisample-storage qualification. The
separate [historical mesh suite](mesh-layout-wheel-regressions.md) and
[volume suite](volume-wheel-regressions.md) keep their original artifact and
profile boundaries; their results are not transferred to this example.
