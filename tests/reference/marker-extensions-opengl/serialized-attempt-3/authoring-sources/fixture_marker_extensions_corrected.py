"""Separate API-correct marker authoring; original failed criteria are retained.

There is one final FBO read. Camera cases have a distinct resident prewarm
submission without a read; revision draws remain pending until the final read.
Private visual data is observed, never mutated, to witness the public API.
Public Visual.draw retains the activated FBO; SceneCanvas.draw_visual makes
the canvas current and can reset that target between dependent draws.
"""

from __future__ import annotations

import hashlib
import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (128, 96)
METHODS = ("points", "instanced")
WORKFLOWS = ("style_grid", "camera_fixed", "camera_scene", "camera_visual",
             "spherical_depth", "color_revision", "position_revision")
CASES = tuple(f"{method}_{workflow}" for method in METHODS for workflow in WORKFLOWS)
COMPARISON = {"full_frame_exact": True, "candidate_alignment_or_color_fit": False,
              "landmarks": "fixed analytic RGBA values or fixed channel bounds; no edge exclusions"}
GRID_POS = np.array([[20, 24, 0], [64, 24, 0], [108, 24, 0],
                     [20, 72, 0], [64, 72, 0], [108, 72, 0]], np.float32)
GRID_SYMBOLS = ("disc", "square", "diamond", "triangle_up", "cross", "ring")
GRID_SIZE = np.array([12, 16, 20, 14, 18, 24], np.float32)
GRID_EDGE = np.array([4, 2, 1, 3, 2, 2], np.float32)
RGB = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]], np.float32)
CMY = np.array([[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1]], np.float32)
REV_POS = np.array([[24, 24, 0], [56, 24, 0], [88, 24, 0]], np.float32)


def array_record(array):
    array = np.asarray(array)
    return {"shape": list(array.shape), "dtype": array.dtype.str,
            "dtype_descr": freeze(array.dtype.descr), "bytes": array.nbytes,
            "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()}


def split_case(name):
    method, workflow = name.split("_", 1)
    if method not in METHODS or workflow not in WORKFLOWS:
        raise ValueError(name)
    return method, workflow


def ring_aa_geometry():
    """Fixed signed-distance/Gaussian bounds from the pinned ring shader.

    Integer-centered point and instanced grids may straddle a pixel-center
    convention. Bound both adjacent centers, then include one output-byte
    quantization step; full-image candidate equality remains mandatory.
    """
    radii = np.hypot(np.array([8.5, 9.5]), .5)
    distances = np.maximum(radii - 12., 6. - radii)
    alpha = np.exp(-distances ** 2)  # edge_width2, AA1 gives t=0.
    colors = np.c_[alpha, 1 - alpha, np.zeros(2), np.ones(2)] * 255
    low = np.maximum(0, np.floor(colors.min(axis=0)).astype(int) - 1)
    high = np.minimum(255, np.ceil(colors.max(axis=0)).astype(int) + 1)
    low[2:] = high[2:] = [0, 255]
    return {"point": [72, 117], "symbol_size": 24., "edge_width": 2., "antialias": 1.,
            "radius_samples": radii.tolist(), "signed_distances": distances.tolist(),
            "gaussian_edge_mix": alpha.tolist(), "minimum_rgba": low.tolist(),
            "maximum_rgba": high.tolist(),
            "formula": "r=max(hypot(dx,dy)-12,6-hypot(dx,dy)); mix=exp(-r*r); color=(mix,1-mix,0,1)",
            "full_frame_exact_unchanged": True}


def specification(name):
    method, workflow = split_case(name)
    spec = {"case": name, "method": method, "workflow": workflow,
            "size": list(SIZE), "dpi": 96, "samples": 1, "readbacks": 1,
            "api_scope": "public scene Markers / MarkersVisual.set_data, camera.rect, SceneCanvas.push_fbo and Visual.draw",
            "authoring_variant": "separate API-correct attempt2; original failed capture remains immutable",
            "scaling": "fixed", "antialias": 1., "spherical": False,
            "camera_rect": [0, 0, *SIZE], "camera_flip": [False, True, False],
            "camera_depth_value": 100., "clear_depth": 1., "depth_func": "less",
            "prewarm_submission_without_read": False,
            "dependent_intermediate_present_or_finish": False,
            "input": {"pos": REV_POS.copy(), "size": 14., "edge_width": 0.,
                      "edge_color": [0, 0, 0, 1], "face_color": RGB.copy(), "symbol": "disc"}}
    if workflow == "style_grid":
        spec["input"] = {"pos": GRID_POS.copy(), "size": GRID_SIZE.copy(),
                         "edge_width": GRID_EDGE.copy(), "edge_color": [1, 0, 0, 1],
                         "face_color": [0, 1, 0, 1], "symbol": list(GRID_SYMBOLS)}
        spec["ring_aa_geometry"] = ring_aa_geometry()
    elif workflow.startswith("camera_"):
        spec.update(scaling=workflow.removeprefix("camera_"), antialias=0.,
                    prewarm_submission_without_read=True,
                    final_camera_rect=[16, 12, 64, 48], visual_scale=[2, 2, 1])
        spec["published_diameter_pixels"] = 10. if workflow == "camera_fixed" else 20.
        spec["visual_scaling_contract"] = "own Visual scale2 times size10; camera zoom excluded"
        spec["input"] = {"pos": np.array([[16, 18, 0], [28, 12, 0]], np.float32),
                         "size": 10., "edge_width": 0., "edge_color": [0, 0, 0, 1],
                         "face_color": RGB[:2].copy(), "symbol": "disc"}
    elif workflow == "spherical_depth":
        spec.update(spherical=True, light_position=[0, 0, 1], light_color=[1, 1, 1],
                    light_ambient=.05,
                    front_mesh_vertices=[[40, 24, -10], [88, 24, -10],
                                         [40, 72, -10], [88, 72, -10]],
                    front_mesh_faces=[[0, 1, 2], [2, 1, 3]],
                    front_mesh_color=[1, 0, 0, 1],
                    depth_geometry={"sphere_center_window_depth": .5,
                                    "sphere_center_depth_change": -.1,
                                    "front_mesh_window_depth": .45,
                                    "formula": ".5 - .1 * sqrt(1 - (dx/20)^2 - (dy/20)^2)"})
        spec["input"] = {"pos": np.array([[64, 48, 0]], np.float32),
                         "size": 40., "edge_width": 0., "edge_color": [0, 0, 0, 1],
                         "face_color": [0, 1, 0, 1], "symbol": "disc"}
    elif workflow == "color_revision":
        spec["updated_input"] = dict(spec["input"], face_color=CMY.copy())
        spec["updated_visual_translation"] = [0, 48, 0]
    elif workflow == "position_revision":
        spec["updated_input"] = dict(spec["input"], pos=REV_POS + np.array([16, 48, 0], np.float32))
    return spec


def landmarks(name):
    _, workflow = split_case(name)
    marks = [{"row": 2, "column": 2, "rgba": [0, 0, 0, 255]}]
    if workflow == "style_grid":
        for x, y, _ in GRID_POS[:5].astype(int):
            marks.append({"row": int(y), "column": int(x),
                          "minimum": [0, 240, 0, 255], "maximum": [15, 255, 0, 255]})
        marks += [{"row": 24, "column": 26, "rgba": [255, 0, 0, 255]},
                  {"row": 72, "column": 108, "rgba": [0, 0, 0, 255]},
                  {"row": 72, "column": 117,
                   "minimum": ring_aa_geometry()["minimum_rgba"],
                   "maximum": ring_aa_geometry()["maximum_rgba"]}]
    elif workflow.startswith("camera_"):
        scaling = workflow.removeprefix("camera_")
        marks += [{"row": 48, "column": 32, "rgba": [255, 0, 0, 255]},
                  {"row": 24, "column": 80, "rgba": [0, 255, 0, 255]},
                  {"row": 48, "column": 39,
                   "rgba": [0, 0, 0, 255] if scaling == "fixed" else [255, 0, 0, 255]},
                  {"row": 48, "column": 46,
                   "rgba": [0, 0, 0, 255]},
                  {"row": 48, "column": 54, "rgba": [0, 0, 0, 255]}]
    elif workflow == "spherical_depth":
        marks += [{"row": 48, "column": 64, "minimum": [180, 230, 180, 255],
                   "maximum": [255, 255, 255, 255]},
                  {"row": 48, "column": 76, "minimum": [0, 170, 0, 255],
                   "maximum": [15, 255, 15, 255]},
                  {"row": 48, "column": 83, "rgba": [255, 0, 0, 255]},
                  {"row": 48, "column": 35, "rgba": [0, 0, 0, 255]}]
    else:
        for x, y, color in zip(REV_POS[:, 0].astype(int), REV_POS[:, 1].astype(int), RGB):
            marks.append({"row": int(y), "column": int(x), "rgba": (color * 255).astype(int).tolist()})
        positions = REV_POS + np.array([0, 48, 0] if workflow == "color_revision" else [16, 48, 0])
        colors = CMY if workflow == "color_revision" else RGB
        for (x, y, _), color in zip(positions.astype(int), colors):
            marks.append({"row": int(y), "column": int(x), "rgba": (color * 255).astype(int).tolist()})
        marks.append({"row": 48, "column": 56, "rgba": [0, 0, 0, 255]})
    return marks


def case_contract(name):
    spec = specification(name)
    return {key: ({field: array_record(value) if isinstance(value, np.ndarray) else value
                   for field, value in item.items()} if key in ("input", "updated_input") else item)
            for key, item in spec.items()} | {"landmarks": landmarks(name), "comparison": COMPARISON}


def assert_landmarks(name, image):
    assert image.shape == (SIZE[1], SIZE[0], 4) and image.dtype == np.uint8
    for mark in landmarks(name):
        pixel = image[mark["row"], mark["column"]].astype(int)
        if "rgba" in mark:
            assert pixel.tolist() == mark["rgba"], (name, mark, pixel.tolist())
        else:
            assert np.all(pixel >= mark["minimum"]) and np.all(pixel <= mark["maximum"]), (name, mark, pixel.tolist())


def render(name, backend="dawn_headless"):
    from vispy import scene, gloo
    from vispy.visuals.transforms import STTransform

    spec = specification(name)
    canvas = scene.SceneCanvas(app=backend, size=SIZE, dpi=96, show=backend == "pyqt6",
        decorate=False, bgcolor=(0, 0, 0, 1), config={"samples": 0})
    if backend == "pyqt6":
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
    canvas.set_current()
    commands, shaders, uploaded = [], {}, []
    parser, records = canvas.context.shared.parser, []
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA":
                if isinstance(command[3], str):
                    shaders[str(command[1])] = command[3]
                elif isinstance(command[3], np.ndarray):
                    uploaded.append((command[1], array_record(command[3])))
        return original(batch)

    parser.parse = log
    fbo = None
    pushed = False
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.PanZoomCamera(rect=spec["camera_rect"], flip=(False, True, False))
        view.camera.depth_value = spec["camera_depth_value"]
        markers = scene.visuals.Markers(parent=view.scene, method=spec["method"],
            scaling=spec["scaling"], antialias=spec["antialias"], spherical=spec["spherical"],
            light_position=spec.get("light_position", (1, -1, 1)),
            light_color=spec.get("light_color", "white"), light_ambient=spec.get("light_ambient", .3))
        markers.order = 1
        markers.set_data(**spec["input"])
        records.append(array_record(markers._data))
        marker_id = markers._vbo.id
        if "visual_scale" in spec:
            markers.transform = STTransform(scale=spec["visual_scale"])
        if spec["spherical"]:
            mesh = scene.visuals.Mesh(parent=view.scene,
                vertices=np.array(spec["front_mesh_vertices"], np.float32),
                faces=np.array(spec["front_mesh_faces"], np.uint32),
                color=spec["front_mesh_color"], shading=None)
            mesh.set_gl_state(depth_test=True, depth_func="less", blend=False)
            mesh.order = 2
        fbo = gloo.FrameBuffer(color=gloo.RenderBuffer(SIZE[::-1], format="color"),
                              depth=gloo.RenderBuffer(SIZE[::-1], format="depth"))
        canvas.push_fbo(fbo, (0, 0), SIZE)
        pushed = True
        canvas.context.flush_commands()  # Activate once, before dependent scope.
        targets = []

        def observe_target(stage):
            record = {"stage": stage, "expected_gloo_framebuffer": fbo.id,
                      "scope": "actual parsed GLIR framebuffer; final pixels prove the owned target"}
            if backend == "pyqt6":
                from OpenGL import GL
                expected_handle = parser._objects[fbo.id].handle
                actual = int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
                assert actual == expected_handle, (stage, actual, expected_handle)
                record.update(driver_framebuffer_binding=actual, parser_framebuffer_handle=expected_handle,
                              scope="OpenGL driver GL_FRAMEBUFFER_BINDING after actual parse")
            targets.append(record)

        def draw_markers_and_mesh(stage):
            # Node.draw delegates to public Visual.draw with its public scene
            # camera/transform system; it does not make the canvas current.
            markers.draw()
            observe_target(stage + "_markers")
            if spec["spherical"]:
                mesh.draw()
                observe_target(stage + "_mesh")
        observations = {"sample_source": "explicit single-sample RenderBuffers; candidate facade"}
        if backend == "pyqt6":
            samples = int(gloo.gl.glGetParameter(0x80A9))
            observations = {"sample_source": "OpenGL driver GL_SAMPLES", "gl_samples": samples,
                            "physical_samples": max(1, samples),
                            "point_size_range": np.asarray(gloo.gl.glGetParameter(0x846D)).tolist()}
        scope_start = len(commands)
        gloo.set_clear_depth(spec["clear_depth"])
        if spec["prewarm_submission_without_read"]:
            canvas.context.clear(color=(0, 0, 0, 1), depth=True)
            draw_markers_and_mesh("prewarm")
            canvas.swap_buffers()
            scope_start = len(commands)
            view.camera.rect = spec["final_camera_rect"]
        native = None
        if backend != "pyqt6":
            from vispy import _dawn
            native = _dawn
            observations["native_before_dependent_draws"] = dict(native.probe())
        gloo.set_state(depth_func="less", depth_mask=True, color_mask=(True, True, True, True))
        canvas.context.clear(color=(0, 0, 0, 1), depth=True)
        draw_markers_and_mesh("initial")
        if "updated_input" in spec:
            markers.set_data(**spec["updated_input"])
            records.append(array_record(markers._data))
            if "updated_visual_translation" in spec:
                markers.transform = STTransform(translate=spec["updated_visual_translation"])
            draw_markers_and_mesh("updated")
        if native is not None:
            observations["native_before_final_read"] = dict(native.probe())
        # Public FBO.read returns upper-left row zero and an owned copied array.
        observe_target("before_final_read")
        image = np.array(fbo.read(), copy=True)
        if native is not None:
            observations["native_after_final_read"] = dict(native.probe())
        params = case_contract(name)
        observations.update(readbacks=1, dependent_trace_start=scope_start,
            marker_vbo_id=marker_id, structured_revisions=records,
            target_observations=targets, gloo_framebuffer_id=fbo.id,
            actual_marker_uploads=[record for identity, record in uploaded if identity == marker_id])
        return image, commands, shaders, params, observations
    finally:
        if pushed:
            canvas.pop_fbo()
        parser.parse = original
        canvas.close()


def assert_trace(name, commands, observations):
    spec = specification(name)
    trace = commands[observations["dependent_trace_start"]:]
    assert not [command for command in trace if command[0] == "CURRENT"], (name, "active FBO was reset")
    assert all(item["expected_gloo_framebuffer"] == observations["gloo_framebuffer_id"]
               for item in observations["target_observations"])
    uploads = observations["actual_marker_uploads"]
    revisions = observations["structured_revisions"]
    assert uploads == revisions, (name, uploads, revisions)
    draws = [command for command in trace if command[0] == "DRAW"]
    mode = "points" if spec["method"] == "points" else "triangle_strip"
    marker_draws = [command for command in draws if command[2] == mode]
    assert len(marker_draws) == (2 if "updated_input" in spec else 1), (name, draws)
    if spec["prewarm_submission_without_read"]:
        assert not [command for command in trace if command[0] == "DATA" and command[1] == observations["marker_vbo_id"]], name
    if "updated_input" in spec:
        data_indices = [index for index, command in enumerate(trace)
                        if command[0] == "DATA" and command[1] == observations["marker_vbo_id"]]
        draw_indices = [index for index, command in enumerate(trace) if command in marker_draws]
        assert len(data_indices) == 2 and data_indices[0] < draw_indices[0] < data_indices[1] < draw_indices[1], name
