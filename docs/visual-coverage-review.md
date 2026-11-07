# Visual namespace review

Reviewed 2026-11-07 against source `786079e8`. All **76 visual seed parents**
have a source route below: 39 visual classes, 14 filters, nine shader helpers
and 14 transform helpers, resolving to 56 definition files. This is a parent and
source-route review, not qualification of each method or rendered output.
The canonical inventory and its original obligations remain unchanged with
`reviewed=false`. API-05/06 retain method/example/event reconciliation and exact
installed acceptance. Existing shader, state and scientific-workflow gaps remain
in the live checklist.

CPU geometry preparation, GLSL text composition and actual Vulkan compilation /
rendering are distinct evidence levels. The selected CPU tests do not instantiate
an application, canvas or timer, or import the native GPU module. Published v1
qualifications and newer local Linux v2 results retain their exact artifact,
profile and finite workflow scopes; none qualifies all of these parents.

Paths below are relative to `src/vispy/visuals/`. Each row records a route that
exists, followed by the acceptance work that its existence alone does not prove.

## Visual classes

| Parent | Source route and behavior | Acceptance boundary / remaining work |
| --- | --- | --- |
| `visuals.arrowvisual` | `line/arrow.py:ArrowVisual`; extends LineVisual with arrowhead rendering. | Line method, head type/size, endpoint mutation, clipping and joins need rendered cases. |
| `visuals.axisvisual` | `axis.py:AxisVisual`; compound lines, ticks and text. Source explicitly refuses non-linear `scale_type`. | Tick placement, orientation, font/layout and domain/transform mutations need independent output cases. |
| `visuals.basevisual` | `visual.py:BaseVisual`; events, transforms, visibility, bounds, views and filter interface. | A framework base, not a standalone rendered primitive. Shared view/filter lifetime and update propagation need method cases. |
| `visuals.boxvisual` | `box.py:BoxVisual`; compound box mesh and border lines. | Segment counts, colors, border/depth interactions and mutation need mesh/line output cases. |
| `visuals.colorbarvisual` | `colorbar.py:ColorBarVisual`; compound color ramp, border and text, with size/orientation validation. | Color mapping, ticks, all orientations, resizing and text require finite rendered expectations. |
| `visuals.compleximagevisual` | `image_complex.py:ComplexImageVisual`; complex values become paired float channels, with selectable complex color transforms. | Complex modes, channel format, real/complex transitions, clim and mutation need exact texture/shader cases. |
| `visuals.compoundvisual` | `visual.py:CompoundVisual`; manages/draws subvisuals and propagates views/filters. | Add/remove, shared views, visibility, filter attachment and cleanup need lifecycle tests. |
| `visuals.cubevisual` | `cube.py:CubeVisual`; BoxVisual convenience constructor for cube/cuboid size. | Inherits mesh/border acceptance; constructor availability is not separate rendered coverage. |
| `visuals.ellipsevisual` | `ellipse.py:EllipseVisual`; polygon-based ellipse/arc geometry and border. | Radii, angular extent, segment count and updates need geometry plus fill/border output cases. |
| `visuals.graphvisual` | `graphs/graph.py:GraphVisual`; compound ArrowVisual edges and MarkersVisual nodes driven by a layout iterator. | CPU layout tests do not prove graph drawing, animation scheduling, arrows or node picking. Optional networkx layouts are separate. |
| `visuals.gridlinesvisual` | `gridlines.py:GridLinesVisual`; ImageVisual specialization with procedural grid shader/transform logic. | Nonlinear transforms, scale, derivatives, line widths and clip boundaries need rendering cases. |
| `visuals.gridmeshvisual` | `gridmesh.py:GridMeshVisual`; builds a mesh from initialized x/y/z grid arrays. | Shape compatibility, color/shading, normals and grid-data mutations need scoped proof. |
| `visuals.histogramvisual` | `histogram.py:HistogramVisual`; NumPy histogram preparation feeds MeshVisual; source accepts 1D data and `h`/`v` orientation. | Bin/count geometry, empty/invalid data and rendered orientation/color remain method/value work. |
| `visuals.imagevisual` | `image.py:ImageVisual`; texture-backed scalar/color image with subdivision/impostor paths, color transforms and interpolation. | Dtype/channel/format, clim, interpolation, nonlinear transforms, partial updates and loss recovery need finite texture cases. |
| `visuals.infinitelinevisual` | `infinite_line.py:InfiniteLineVisual`; viewport-spanning horizontal/vertical line shader. | Positions, width/antialias, transforms and clipping need independent pixels. |
| `visuals.instancedmeshvisual` | `instanced_mesh.py:InstancedMeshVisual`; MeshVisual with per-instance 3D positions, 3x3 transforms and colors. | Matrix attribute layout/divisors, normal transforms, input limits and mutations remain SHD-03 / API-06 work. |
| `visuals.isocurvevisual` | `isocurve.py:IsocurveVisual`; CPU contour extraction feeds LineVisual, preserving original level/color indices and empty results. Optional skimage and built-in paths differ. | Selected CPU contour tests are not line-raster or real optional-library qualification. Levels, colors, transforms and actual rendering remain scoped work. |
| `visuals.isolinevisual` | `isoline.py:IsolineVisual`; extracts level lines from scalar values on a triangle mesh, then uses LineVisual. | Degenerate/equal-valued triangles, connectivity, level/color updates and line rendering need cases. |
| `visuals.isosurfacevisual` | `isosurface.py:IsosurfaceVisual`; built-in CPU isosurface extraction with cached vertices/faces feeds MeshVisual. | Topology/degeneracies, level/data updates, normals/shading and scientific rendered accuracy need finite cases. |
| `visuals.linearregionvisual` | `linear_region.py:LinearRegionVisual`; horizontal/vertical filled regions with position/color validation. | Multiple boundaries, alpha/depth, transforms and mutations require rendered expectations. |
| `visuals.lineplotvisual` | `line_plot.py:LinePlotVisual`; compound line and optional markers; non-solid `line_kind` is refused. | Input layouts, marker/line mutation and rendered output inherit separate line/marker obligations. |
| `visuals.linevisual` | `line/line.py:LineVisual`; selects `gl` or `agg` implementation and interprets strip/segments/index/bool connectivity. The `gl` name denotes a compatibility route. | Neither name implies native GL. Width, caps, joins, AA, topology and depth/clip cases need bounded raster acceptance. |
| `visuals.markersvisual` | `markers.py:MarkersVisual`; supports `points` and `instanced` methods with symbol/color/edge/scaling inputs. | Point versus instanced shaders, sizing limits, AA, picking, depth and mutations require separate finite cases. |
| `visuals.meshnormalsvisual` | `mesh_normals.py:MeshNormalsVisual`; generates face/vertex normal segments through LineVisual. | CPU normal geometry, lengths/origins, transforms and line output need distinct expectations. |
| `visuals.meshvisual` | `mesh.py:MeshVisual`; MeshData-backed geometry, colors/values, draw mode and optional shading filters. | Topology, normals, textures, blending/depth and data/filter mutations need mesh-specific proof. |
| `visuals.planevisual` | `plane.py:PlaneVisual`; compound plane geometry and optional edge lines. | Direction, segmentation, colors, borders and transform mutations inherit mesh/line cases. |
| `visuals.polygonvisual` | `polygon.py:PolygonVisual`; compound triangulated fill and border line. | Concavity, degenerate input, winding and fill/border mutations require geometry/output cases. |
| `visuals.rectanglevisual` | `rectangle.py:RectangleVisual`; PolygonVisual specialization including corner radii. | Radius/extent validation, rounded geometry, borders and resizing need cases. |
| `visuals.regularpolygonvisual` | `regular_polygon.py:RegularPolygonVisual`; ellipse specialization with a regular polygon side count. | Side/radius/rotation changes and fill/border behavior need scoped proof. |
| `visuals.scrollinglinesvisual` | `scrolling_lines.py:ScrollingLinesVisual`; texture-backed equal-length line strips with a rolling data offset and per-line offsets/colors. | 1D sampler translation, wrap/update ordering, texture formats and multi-line output need separate tests. |
| `visuals.spectrogramvisual` | `spectrogram.py:SpectrogramVisual`; CPU signal transform produces ImageVisual data, with log/linear color scale and FFT/window/sample-rate properties. | FFT preparation does not prove image output. Property updates, numerical ranges and texture/rendering need finite acceptance. |
| `visuals.spherevisual` | `sphere.py:SphereVisual`; compound generated sphere mesh and optional edges. | Tessellation methods, pole/seam behavior, normals/shading and mutation need mesh/output cases. |
| `visuals.surfaceplotvisual` | `surface_plot.py:SurfacePlotVisual`; regular x/y grid and z heights feed MeshVisual. | Grid shapes, height/color mutations, normals and scientific axes need independent cases. |
| `visuals.textvisual` | `text/text.py:TextVisual`; glyph layout, font resources, text quads and distance-field rendering. | Font/SDF producer identity, glyphs, Unicode, scale/rotation, atlas growth and cleanup need exact text cases. |
| `visuals.tubevisual` | `tube.py:TubeVisual`; constructs a mesh around a piecewise-linear path. | Path frames, radii, closed seams, degenerate segments and shading require geometry/rendered cases. |
| `visuals.visual` | `visual.py:Visual`; one modular shader program with shared/view state, preparation hooks and draw submission. | `gcode` availability does not establish geometry shader support: the native renderer explicitly refuses geometry shaders. Views/state/filter and error lifetimes need cases. |
| `visuals.volumevisual` | `volume.py:VolumeVisual`; 3D texture, generated raycasting methods, transfer/color controls, interpolation and clipping planes. | Each numerical sampling/raycasting/format/plane combination needs scientific expectations; import availability is not all-method volume qualification. |
| `visuals.windbarbvisual` | `windbarb.py:WindbarbVisual`; wind-vector symbols through its own vertex/fragment shader and data buffers. | Speed thresholds, direction, symbol/size/color, depth/clipping and updates need dedicated cases. |
| `visuals.xyzaxisvisual` | `xyz_axis.py:XYZAxisVisual`; LineVisual convenience geometry for red/green/blue 3D axes. | Inherits line/depth/transform acceptance; CPU coordinates do not qualify rendered orientation. |

## Filters

| Parent | Source route and behavior | Acceptance boundary / remaining work |
| --- | --- | --- |
| `visuals.filters.alpha` | `filters/color.py:Alpha`; fragment hook multiplies alpha; property updates its shader variable. | CPU mutation passes; blend/order and multi-filter rendered behavior remain separate. |
| `visuals.filters.clipper` | `filters/clipper.py:Clipper`; normalizes bounds to a `Rect` and discards fragments outside transformed framebuffer coordinates. | CPU bounds normalization passes. Shader coordinates, edges, nested clips and updates need pixels. |
| `visuals.filters.colorfilter` | `filters/color.py:ColorFilter`; fragment color multiplier. | Hook order, component values, alpha/blending and updates need finite cases. |
| `visuals.filters.facepickingfilter` | `filters/mesh.py:FacePickingFilter`; repeats one ID across each triangle's vertices via PrimitivePickingFilter. | Geometry/data updates and byte-exact face IDs need rendered picking; alpha encodes ID bits, so blending must be disabled. |
| `visuals.filters.filter` | `filters/base_filter.py:Filter`; inserts/removes vertex/fragment expressions at ordered hooks. | Per-visual/view attachment, detach/re-attach, duplicates and hook composition need lifecycle cases. |
| `visuals.filters.instancedshadingfilter` | `filters/mesh.py:InstancedShadingFilter`; extends mesh shading for instance transforms. | Normal matrices, instance colors and attribute/divisor layout need shader/rendered cases. |
| `visuals.filters.isolinefilter` | `filters/color.py:IsolineFilter`; derives contour-like bands from fragment luminance using derivatives. | This is distinct from CPU Isocurve/Isoline visuals. Derivatives, line/AA settings and colors need rendered expectations. |
| `visuals.filters.markerpickingfilter` | `filters/markers.py:MarkerPickingFilter`; assigns marker IDs and selects a divisor for the instanced marker path. | Points/instanced correspondence, updates and byte-exact picking require output cases with blending disabled. |
| `visuals.filters.pickingfilter` | `filters/picking.py:PickingFilter`; replaces fragment color with one visual's encoded ID. | Transparent-fragment, depth, blend and scene lookup behavior need exact readback cases. |
| `visuals.filters.primitivepickingfilter` | `filters/base_filter.py:PrimitivePickingFilter`; abstract ID provider, uint32-to-RGBA packing and data-update hooks. | CPU byte packing/dtype refusal passes; abstract base is not constructible. Subclass GPU interpolation/picking remains separate. |
| `visuals.filters.shadingfilter` | `filters/mesh.py:ShadingFilter`; Phong-style material/light and flat/smooth normal shader hooks. | Normals, light/material updates and derivative/depth interactions need finite rendering cases. |
| `visuals.filters.texturefilter` | `filters/mesh.py:TextureFilter`; applies a sampled texture using mesh texture coordinates. | Coordinate/texture size, wrapping/filtering, formats and data changes need exact texture/mesh cases. |
| `visuals.filters.wireframefilter` | `filters/mesh.py:WireframeFilter`; barycentric edge shader and mesh-data update hooks. | Width/AA, indexed mesh expansion, attach/detach and data mutation need output/lifetime cases. |
| `visuals.filters.zcolormapfilter` | `filters/color.py:ZColormapFilter`; maps vertex z through a colormap using shader hooks. | Coordinate space, clim/color mapping, updates and filter order need rendered expectations. |

## Shader composition helpers

These helpers build GLSL text and program-variable relationships. Their CPU
tests do not validate the native GLSL/SPIR-V/WGSL pipeline or Vulkan execution.

| Parent | Source route and behavior | Acceptance boundary / remaining work |
| --- | --- | --- |
| `visuals.shaders.compiler` | `shaders/compiler.py:Compiler`; dependency ordering, naming and composed shader output. | Native compilation, reflection, supported interfaces and shader failures remain SHD/API-06 work. |
| `visuals.shaders.function` | `shaders/function.py:Function`; code templates, expressions, arguments and dependencies. | CPU composition tests cover named examples; generated consumer shaders need separate compilation/output proof. |
| `visuals.shaders.functionchain` | `shaders/function.py:FunctionChain`; ordered composition of functions. | Dynamic updates, signatures and actual stage consumers need finite cases. |
| `visuals.shaders.mainfunction` | `shaders/function.py:MainFunction`; shader main code with multiple definitions and template substitutions. | Native stage/interface acceptance is not established by string generation. |
| `visuals.shaders.modularprogram` | `shaders/program.py:ModularProgram`; gloo Program driven by Function-based shader composition. | Build/draw, variables, rebuild/error ordering and resource lifetime need installed cases. |
| `visuals.shaders.multiprogram` | `shaders/multiprogram.py:MultiProgram`; weak program collection with shared/per-program variables and code propagation. | Existing CPU test exercises propagation and weak ownership, not GPU compilation/draw or context sharing. |
| `visuals.shaders.statementlist` | `shaders/function.py:StatementList`; ordered shader statements and dependencies. | Imported publicly but omitted from shaders `__all__`; wildcard behavior and hook mutation remain API-05/06. |
| `visuals.shaders.variable` | `shaders/variable.py:Variable`; shader variable declaration/value/type and dependency representation. | Storage/type/reflection and uniform/attribute value acceptance require native shader cases. |
| `visuals.shaders.varying` | `shaders/variable.py:Varying`; links stage-passed values in composed shader code. | Interpolation, type/location linkage and limits need native compile/output cases. |

## Transform helpers

| Parent | Source route and behavior | Acceptance boundary / remaining work |
| --- | --- | --- |
| `visuals.transforms.arg-to-array` | `transforms/_util.py:arg_to_array`; decorator converts mapping input to an array. | Shape/dtype and wrapped method semantics need method-level cases. |
| `visuals.transforms.arg-to-vec4` | `transforms/_util.py:arg_to_vec4`; decorator promotes coordinates and restores result shape. | Batched/empty/invalid dimensions and defaults need explicit cases. |
| `visuals.transforms.as-vec4` | `transforms/_util.py:as_vec4`; pads up to four components; rejects more than four. | Position/scale defaults and dtype/shape behavior need explicit API acceptance. |
| `visuals.transforms.basetransform` | `transforms/base_transform.py:BaseTransform`; complementary CPU and shader mappings with change notification. | A base contract, not every mapping's numerical or shader qualification. |
| `visuals.transforms.chaintransform` | `transforms/chain.py:ChainTransform`; composed CPU mappings, inverse and generated function chain. | CPU composition tests pass; dynamic shader updates and shared transform lifetime remain separate. |
| `visuals.transforms.create-transform` | `transforms/__init__.py:create_transform`; class-name registry lookup and constructor forwarding. | Registry/export distinctions and invalid key/argument behavior remain API-05/06. |
| `visuals.transforms.logtransform` | `transforms/nonlinear.py:LogTransform`; per-axis logarithmic/exponential mappings. | Domain/sign/base limits, inverses and CPU-versus-shader output need finite numerical cases. |
| `visuals.transforms.matrixtransform` | `transforms/linear.py:MatrixTransform`; affine/projective matrix mapping and matrix-building operations. | CPU mapping/inverse tests are bounded; singular/projective and shader consumers remain explicit work. |
| `visuals.transforms.nulltransform` | `transforms/linear.py:NullTransform`; identity CPU/shader mapping. | Shape conventions, composition and GPU consumers retain their own cases. |
| `visuals.transforms.panzoomtransform` | `transforms/interactive.py:PanZoomTransform`; STTransform with optional canvas event attachment and aspect handling. | CPU transform availability does not test delivered input, canvas attachment/detach or rendered response. |
| `visuals.transforms.polartransform` | `transforms/nonlinear.py:PolarTransform`; polar/cartesian mappings in Python and GLSL. | Angle/radius conventions, seams/origin, inverse and shader behavior need numerical/output cases. |
| `visuals.transforms.sttransform` | `transforms/linear.py:STTransform`; scale then translation with inverse/composition support. | Selected CPU mapping tests pass; zero scale, dtype and rendered consumers need scoped cases. |
| `visuals.transforms.transformcache` | `transforms/_util.py:TransformCache`; reuse/cache of transform chains. | Cache age, updates, identity and lifetime require method cases, not just class availability. |
| `visuals.transforms.transformsystem` | `transforms/transform_system.py:TransformSystem`; coordinates visual/scene/document/canvas/framebuffer/render mappings. | Viewport/FBO/pixel-scale changes, inverse mappings and linked views require exact scene/profile cases. |

## Evidence and next batch

Existing shader parsing/function/multiprogram, transform, graph-layout and
Isocurve CPU tests pass **51 cases without skips on each of Windows and WSL**.
Additional probes resolve every inventory parent to canonical source, check
uint32 picking bytes against independent bit shifts, reject int64 picking IDs,
verify the primitive filter remains abstract, normalize negative clipping bounds
through `Rect.pos`/`Rect.size`, and mutate Alpha's shader variable. No native GPU
module is imported and no application, canvas or timer is created.

The initial harness incorrectly attempted `tuple(Rect)` before reaching pytest;
that failure and its source are retained separately. The successful probe uses
the actual Rect properties and the same expected coordinates. This is a harness
correction, not a product change or relaxed expectation.

[Initial accounting/failure](../build/runs/visual-audit-363/external-evidence.json),
[source accounting and CPU evidence](../build/runs/visual-cpu-364/external-evidence.json).

The seed does not exhaust collection renderers, visual views, private visual
helpers, custom shader hooks, generated scene aliases or their methods/examples.
The GLSL `Compiler` is not the native shader compiler. Geometry shader input is
explicitly refused by the renderer; affected custom consumers need a supported
rewrite or documented disposition. Other shader/state/typed texture/scientific
gaps remain open rather than being inferred absent or complete from exports.

The public visuals module still says it defines only OpenGL machinery. Queue
that stale description with the widgets introduction and ViewBox default-camera
corrections already recorded by API-03. Finish method/route reconciliation and
batch those public documentation edits before another shipping pure-source
freeze. This audit changes no shipping code and needs no native build or wheel
rebuild. API-05/06 must bind each selected workflow to its values, expected
outputs, mutations, failures/recovery and exact installed profile; source review
does not transfer an admission.
