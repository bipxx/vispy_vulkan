# SPDX-License-Identifier: AGPL-3.0-only
"""Reviewed host.napari workflows on a shown napari 0.10.0 Dawn canvas."""

from pathlib import Path
import os

import numpy as np
import pytest

from tools.fixture_napari_layer_controls_successor import BACKGROUND
from tools.no_opengl_host_probe import drain_close_events, pump, require_closed, require_qwidget, settled_moves


pytestmark = [
    pytest.mark.gpu,
    pytest.mark.needs_window,
    pytest.mark.skipif(os.environ.get("VISPY_NAPARI_WINDOW_TESTS") != "1", reason="needs-window"),
]

SIZE = (128, 128)  # width, height in logical pixels, with DPR 1
BLACK, WHITE, RED, GREEN, BLUE = (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255)
TOP_LEFT = np.s_[4:16, 4:16]
BOTTOM_RIGHT = np.s_[16:28, 16:28]


def canvas(viewer):
    return viewer.window._qt_viewer.canvas


@pytest.fixture
def open_viewer():
    import napari
    from napari._qt.qt_event_loop import get_qapp
    from vispy import _dawn, app

    assert napari.__version__ == "0.10.0"
    application = app.use_app("pyqt6")
    qapp = get_qapp()
    old_quit = qapp.quitOnLastWindowClosed()
    qapp.setQuitOnLastWindowClosed(False)
    viewers = []

    def open_one(*, ndisplay=2, size=SIZE):
        viewer = napari.Viewer(show=True, ndisplay=ndisplay)
        viewers.append(viewer)
        native = canvas(viewer).native
        require_qwidget(native, application.backend_module)
        native.setFixedSize(*size)
        pump(application)
        assert native.isVisible()
        assert native.devicePixelRatioF() == 1
        assert (native.width(), native.height()) == size
        canvas(viewer)._scene_canvas.bgcolor = tuple(np.asarray(BACKGROUND) / 255)
        assert _dawn.device_info()["backend"] == "Vulkan"
        return viewer

    try:
        yield open_one
    finally:
        for viewer in reversed(viewers):
            if viewer in napari.Viewer._instances:
                viewer.close()
        drain_close_events(application)
        qapp.setQuitOnLastWindowClosed(old_quit)


def capture(viewer, **kwargs):
    viewer._layer_slicer.wait_until_idle(timeout=10)
    pump(canvas(viewer)._scene_canvas.app)
    frame = viewer.screenshot(canvas_only=True, flash=False, **kwargs)
    assert frame.dtype == np.uint8 and frame.ndim == 3 and frame.shape[2] == 4
    return frame


def camera_2d(viewer):
    viewer.scene.camera.center = (0, 15.5, 15.5)
    viewer.scene.camera.zoom = 4


def camera_3d(viewer, center, zoom):
    camera = viewer.scene.camera
    camera.center = center
    camera.zoom = zoom
    camera.perspective = 0
    camera.set_view_direction((0, 1, 0), up_direction=(-1, 0, 0))


def add_image(viewer, data, **kwargs):
    return viewer.add_image(data, contrast_limits=(0, 1), interpolation2d="nearest",
                            blending="opaque", **kwargs)


def patch(region, color=None):
    if color is None:
        data = np.zeros((32, 32), np.float32)
        data[region] = 1
    else:
        data = np.zeros((32, 32, 3), np.uint8)
        data[region] = color
    return data


def expected_patch(region, color):
    # Logical camera zoom is four. The plane's edges are at -0.5 and 31.5.
    rgb = patch(region, color).repeat(4, axis=0).repeat(4, axis=1)
    return np.dstack((rgb, np.full(SIZE, 255, np.uint8)))


def pixel_at(frame, y, x):
    assert frame.shape == (128, 128, 4)
    return frame[4 * y + 2, 4 * x + 2, :3]


def labels(viewer, data):
    from napari.utils.colormaps import DirectLabelColormap

    color_dict = {0: (0, 0, 0, 0), 7: (1, 0, 0, 1), 65537: (0, 1, 0, 1),
                  16777473: (0, 0, 1, 1), None: (0, 0, 0, 0)}
    layer = viewer.add_labels(data, colormap=DirectLabelColormap(color_dict=color_dict), opacity=1)
    camera_2d(viewer)
    return layer


def drag(viewer, start, end):
    from qtpy.QtCore import QPoint, Qt
    from qtpy.QtTest import QTest

    scene = canvas(viewer)._scene_canvas
    native = canvas(viewer).native
    first, last = QPoint(*start), QPoint(*end)
    button = Qt.MouseButton.LeftButton
    delivered = []

    def record_move(event):
        delivered.append(tuple(event.pos))

    scene.events.mouse_move.connect(record_move)
    try:
        QTest.mousePress(native, button, pos=first)
        settled_moves(scene.app, QTest, native, [last], lambda: end in delivered)
        QTest.qWait(50)
    finally:
        QTest.mouseRelease(native, button, pos=last)
        scene.events.mouse_move.disconnect(record_move)
    pump(scene.app)


def pan_right(viewer):
    before = viewer.scene.camera.center[-1]
    drag(viewer, (44, 48), (68, 48))
    return viewer.scene.camera.center[-1] - before


def lose_device():
    from vispy import _dawn

    generation = _dawn.probe()["device_generation"]
    _dawn.lose_device()
    return generation


def assert_recovered(generation):
    from vispy import _dawn

    assert _dawn.probe()["device_generation"] > generation


def test_camera_input_pan(open_viewer):
    viewer = open_viewer()
    add_image(viewer, patch(TOP_LEFT))
    camera_2d(viewer)
    capture(viewer)
    assert pan_right(viewer) == pytest.approx(-6, abs=.25)


def test_camera_input_disabled_then_reenabled(open_viewer):
    viewer = open_viewer()
    add_image(viewer, patch(TOP_LEFT))
    camera_2d(viewer)
    capture(viewer)
    viewer.scene.camera.mouse_pan = False
    disabled = pan_right(viewer)
    viewer.scene.camera.mouse_pan = True
    assert (disabled, pan_right(viewer)) == pytest.approx((0, -6), abs=.25)


@pytest.mark.parametrize("device_loss", [False, True], ids=["ordinary", "device-loss"])
def test_image_layer_data_replacement(open_viewer, device_loss):
    viewer = open_viewer()
    layer = add_image(viewer, patch(TOP_LEFT))
    camera_2d(viewer)
    np.testing.assert_array_equal(capture(viewer), expected_patch(TOP_LEFT, WHITE))
    if device_loss:
        generation = lose_device()
    layer.data = patch(BOTTOM_RIGHT)
    frame = capture(viewer)
    np.testing.assert_array_equal(frame, expected_patch(BOTTOM_RIGHT, WHITE))
    if device_loss:
        assert_recovered(generation)


def colored_labels(viewer):
    data = np.zeros((32, 32), np.int32)
    data[4:28, 4:16] = 7
    data[4:28, 16:28] = 65537
    return labels(viewer, data)


def test_labels_layer_sparse_ids_and_refresh(open_viewer):
    viewer = open_viewer()
    layer = colored_labels(viewer)
    capture(viewer)
    layer.data[12:20, 12:20] = 16777473
    layer.refresh()
    frame = capture(viewer)
    for (y, x), color in [((16, 8), RED), ((16, 24), GREEN), ((16, 16), BLUE)]:
        np.testing.assert_array_equal(pixel_at(frame, y, x), color)


def test_labels_layer_clear_and_repopulate(open_viewer):
    viewer = open_viewer()
    layer = colored_labels(viewer)
    np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 8), RED)
    layer.data.fill(0)
    layer.refresh()
    np.testing.assert_array_equal(capture(viewer), expected_patch(BOTTOM_RIGHT, BLACK))
    layer.data[BOTTOM_RIGHT] = 65537
    layer.refresh()
    np.testing.assert_array_equal(capture(viewer), expected_patch(BOTTOM_RIGHT, GREEN))


def test_labels_painting_canvas_drag(open_viewer):
    viewer = open_viewer()
    layer = labels(viewer, np.zeros((32, 32), np.uint8))
    layer.selected_label, layer.brush_size, layer.mode = 7, 5, "paint"
    np.testing.assert_array_equal(pixel_at(capture(viewer), 6, 13), BLACK)
    drag(viewer, (42, 26), (66, 26))
    np.testing.assert_array_equal(pixel_at(capture(viewer), 6, 13), RED)


def test_labels_painting_rejected_value_undo_redo(open_viewer):
    viewer = open_viewer()
    layer = labels(viewer, np.zeros((32, 32), np.uint8))
    layer.brush_size = 5
    with pytest.raises(ValueError):
        layer.paint((6, 10), 256)
    rejected = pixel_at(capture(viewer), 6, 10)
    layer.paint((6, 10), 7)
    painted = pixel_at(capture(viewer), 6, 10)
    layer.undo()
    undone = pixel_at(capture(viewer), 6, 10)
    layer.redo()
    redone = pixel_at(capture(viewer), 6, 10)
    np.testing.assert_array_equal([rejected, painted, undone, redone], [BLACK, RED, BLACK, RED])


@pytest.mark.parametrize("invalid_opacity", [False, True], ids=["ordinary", "invalid-opacity"])
def test_layer_controls_opacity_slider(open_viewer, invalid_opacity):
    viewer = open_viewer()
    add_image(viewer, np.zeros((32, 32), np.float32))
    layer = add_image(viewer, patch(TOP_LEFT))
    layer.blending = "translucent"
    camera_2d(viewer)
    controls = viewer.window._qt_viewer.controls.widgets[layer]
    controls._opacity_blending_controls.opacity_slider.setValue(.35)
    np.testing.assert_allclose(pixel_at(capture(viewer), 8, 8), (89,) * 3, atol=2, rtol=0)
    if invalid_opacity:
        with pytest.raises(ValueError):
            layer.opacity = 1.5
        layer.opacity = .5
        np.testing.assert_allclose(pixel_at(capture(viewer), 8, 8), (128,) * 3, atol=2, rtol=0)


@pytest.mark.parametrize("close_pending", [False, True], ids=["ordinary", "close-pending"])
def test_multiple_canvases_independent_screenshots(open_viewer, close_pending):
    first = open_viewer()
    layer = add_image(first, patch(TOP_LEFT))
    camera_2d(first)
    second = open_viewer()
    add_image(second, patch(BOTTOM_RIGHT, RED), rgb=True)
    camera_2d(second)
    for _ in range(2):
        np.testing.assert_array_equal(pixel_at(capture(first), 8, 8), WHITE)
        np.testing.assert_array_equal(pixel_at(capture(second), 20, 20), RED)
    if close_pending:
        layer.data = patch(BOTTOM_RIGHT)
        canvas(first)._scene_canvas.update()
        first.close()
        np.testing.assert_array_equal(capture(second), expected_patch(BOTTOM_RIGHT, RED))


def test_open_viewer_fit_capture_and_close(open_viewer):
    from vispy import _dawn

    viewer = open_viewer()
    native = canvas(viewer).native
    canvas_id = int(native._dawn_canvas_id)
    application = canvas(viewer)._scene_canvas.app
    add_image(viewer, patch(TOP_LEFT))
    viewer.fit_to_view()
    assert np.count_nonzero(np.all(capture(viewer)[..., :3] == WHITE, axis=2)) > 64
    viewer.close()
    drain_close_events(application)
    require_closed(native, canvas_id, _dawn)


def test_open_viewer_again_after_device_loss(open_viewer):
    first = open_viewer()
    add_image(first, patch(TOP_LEFT))
    generation = lose_device()
    first.close()
    second = open_viewer()
    add_image(second, patch(BOTTOM_RIGHT, GREEN), rgb=True)
    camera_2d(second)
    np.testing.assert_array_equal(pixel_at(capture(second), 20, 20), GREEN)
    assert_recovered(generation)


@pytest.mark.parametrize("wrong_dimension", [False, True], ids=["ordinary", "wrong-dimension"])
def test_points_layer_add_point(open_viewer, wrong_dimension):
    viewer = open_viewer()
    add_image(viewer, np.zeros((32, 32), np.float32))
    layer = viewer.add_points([[8, 8], [24, 24]], size=12, face_color="red", border_width=0)
    camera_2d(viewer)
    np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 24), BLACK)
    if wrong_dimension:
        with pytest.raises(ValueError):
            layer.add([[8, 24, 1]])
    layer.add([[8, 24]])
    frame = capture(viewer)
    np.testing.assert_array_equal(pixel_at(frame, 8, 24), RED)
    if wrong_dimension:
        # Test all three disk footprints, allowing only the rasterized edge band.
        y, x = (np.indices(SIZE) + .5) / 4 - .5
        distance = np.minimum.reduce([np.hypot(y - py, x - px) for py, px in [(8, 8), (24, 24), (8, 24)]])
        assert np.all(frame[distance < 5, :3] == RED)
        assert np.all(frame[distance > 7, :3] == BLACK)


def screenshot_viewer(open_viewer):
    viewer = open_viewer(size=(120, 80))
    data = np.zeros((80, 120), np.float32)
    data[:, 60:] = 1
    add_image(viewer, data)
    viewer.fit_to_view(margin=0)
    return viewer


def assert_split_frame(frame):
    assert frame.shape == (80, 120, 4)
    np.testing.assert_array_equal(frame[40, [30, 90]], [(*BLACK, 255), (*WHITE, 255)])


def test_screenshots_png_export(open_viewer, tmp_path):
    from PIL import Image

    viewer = screenshot_viewer(open_viewer)
    path = tmp_path / "frame.png"
    assert_split_frame(capture(viewer, path=str(path), size=(80, 120)))
    with Image.open(path) as png:
        assert png.mode == "RGBA"
        assert_split_frame(np.asarray(png))


def test_screenshots_invalid_size_then_recapture(open_viewer):
    viewer = screenshot_viewer(open_viewer)
    before = capture(viewer, size=(80, 120))
    assert_split_frame(before)
    with pytest.raises(ValueError):
        capture(viewer, size=(80,))
    np.testing.assert_array_equal(capture(viewer, size=(80, 120)), before)


def rectangle(y, x):
    return np.array([[y - 4, x - 4], [y - 4, x + 4], [y + 4, x + 4], [y + 4, x - 4]])


def shapes(open_viewer, both):
    viewer = open_viewer()
    add_image(viewer, np.zeros((32, 32), np.float32))
    layer = viewer.add_shapes([rectangle(10, 10)], shape_type="rectangle",
                              face_color="red", edge_color="red", opacity=1)
    if both:
        layer.add_rectangles([rectangle(24, 24)], face_color="lime", edge_color="lime")
    camera_2d(viewer)
    return viewer, layer


def test_shapes_layer_selected_rectangle_highlight(open_viewer):
    viewer, layer = shapes(open_viewer, both=True)
    layer.mode = "select"
    before = capture(viewer)
    layer.selected_data = {1}
    layer._set_highlight(force=True)  # Use the same refresh as the retained vector-layer fixture.
    after = capture(viewer)
    np.testing.assert_array_equal(pixel_at(after, 10, 10), RED)
    np.testing.assert_array_equal(pixel_at(after, 24, 24), GREEN)
    changed = np.any(after[..., :3] != before[..., :3], axis=2)
    # The green rectangle's four edges are at world 20 and 28, or pixels 82 and 114.
    assert changed[78:87, 92:104].any()
    assert changed[110:119, 92:104].any()
    assert changed[92:104, 78:87].any()
    assert changed[92:104, 110:119].any()
    changed[72:125, 72:125] = False
    assert not changed.any()


def test_shapes_layer_wrong_dimension_then_add(open_viewer):
    viewer, layer = shapes(open_viewer, both=False)
    with pytest.raises(ValueError):
        layer.add_rectangles([np.column_stack((rectangle(24, 24), np.zeros(4)))])
    layer.add_rectangles([rectangle(24, 24)], face_color=(0, 1, 0, 1), edge_color=(0, 1, 0, 1))
    frame = capture(viewer)
    assert len(layer.data) == 2
    np.testing.assert_array_equal(pixel_at(frame, 10, 10), RED)
    np.testing.assert_array_equal(pixel_at(frame, 24, 24), GREEN)
    np.testing.assert_array_equal(pixel_at(frame, 16, 16), BLACK)


def surface(open_viewer):
    viewer = open_viewer(ndisplay=3)
    vertices = np.array([[8, 16, 8], [8, 16, 24], [24, 16, 16]], np.float32)
    data = (vertices, np.array([[0, 1, 2]], np.uint32), np.full(3, .25, np.float32))
    layer = viewer.add_surface(data, colormap="gray", contrast_limits=(0, 1), shading="none")
    layer.wireframe.visible, layer.wireframe.color, layer.wireframe.width = True, "white", 2
    camera_3d(viewer, (16, 16, 16), 4)
    return viewer, layer, data


def assert_triangle(frame):
    assert np.any(np.all(frame[30:35, 62:67, :3] == WHITE, axis=2))
    np.testing.assert_allclose(frame[60, 64, :3], (64,) * 3, atol=2, rtol=0)
    np.testing.assert_array_equal(frame[97, 42, :3], BLACK)


def test_surface_layer_white_wireframe(open_viewer):
    viewer, _, _ = surface(open_viewer)
    assert_triangle(capture(viewer))


def test_surface_layer_empty_faces_then_restore(open_viewer):
    viewer, layer, data = surface(open_viewer)
    before = capture(viewer)
    assert_triangle(before)
    layer.data = (data[0], np.empty((0, 3), np.uint32), data[2])
    np.testing.assert_array_equal(capture(viewer), expected_patch(BOTTOM_RIGHT, BLACK))
    layer.data = data
    after = capture(viewer)
    assert_triangle(after)
    np.testing.assert_array_equal(after, before)


@pytest.mark.parametrize("invalid_color", [False, True], ids=["ordinary", "missing-color-key"])
def test_tracks_layer_tail_at_time_three(open_viewer, invalid_color):
    viewer = open_viewer()
    data = np.array([[0, t, 8, 8 + 4 * t] for t in range(4)])
    layer = viewer.add_tracks(data, tail_length=1, head_length=0, tail_width=4, colormap="hsv")
    if invalid_color:
        with pytest.raises(ValueError):
            layer.color_by = "missing_key"
        layer.color_by = "track_id"
    viewer.dims.set_point(0, 3)
    camera_2d(viewer)
    frame = capture(viewer)
    np.testing.assert_array_equal(pixel_at(frame, 8, 10), BLACK)
    assert np.max(pixel_at(frame, 8, 18)) > 0


@pytest.mark.parametrize("invalid_data", [False, True], ids=["ordinary", "invalid-data"])
def test_vectors_layer_length_and_replacement(open_viewer, invalid_data):
    viewer = open_viewer()
    add_image(viewer, np.zeros((32, 32), np.float32))
    vector = np.array([[[8, 8], [0, 8]]], np.float32)
    color = GREEN if invalid_data else RED
    initial = np.array([[[22, 8], [0, 8]]], np.float32) if invalid_data else vector
    layer = viewer.add_vectors(initial, edge_color=tuple(channel / 255 for channel in color), edge_width=2)
    camera_2d(viewer)
    if invalid_data:
        np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 12), BLACK)
        with pytest.raises(ValueError):
            layer.data = np.zeros((1, 3, 2))
        layer.data = vector
        np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 12), GREEN)
    else:
        np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 20), BLACK)
        layer.length = 2
        np.testing.assert_array_equal(pixel_at(capture(viewer), 8, 20), RED)


def add_volume(viewer, data):
    return viewer.add_image(data, rendering="mip", colormap="gray", contrast_limits=(0, 1),
                            interpolation3d="nearest", blending="opaque")


def test_volume_rendering_switch_mip_to_minip(open_viewer):
    viewer = open_viewer(ndisplay=3)
    data = np.full((24, 24, 24), .25, np.float32)
    data[:, 12:, :] = .75
    layer = add_volume(viewer, data)
    camera_3d(viewer, (11.5, 11.5, 11.5), 4)
    maximum = capture(viewer)[64, 64, :3]
    layer.rendering = "minip"
    minimum = capture(viewer)[64, 64, :3]
    np.testing.assert_allclose([maximum, minimum], [(191,) * 3, (64,) * 3], atol=2, rtol=0)


def test_volume_rendering_iso_after_device_loss(open_viewer):
    viewer = open_viewer(ndisplay=3, size=(96, 96))
    data = np.full((32, 32, 32), .2, np.float32)
    data[9:23, 9:23, 9:23] = 1
    layer = add_volume(viewer, data)
    camera_3d(viewer, (15.5, 15.5, 15.5), 2.4)
    canvas(viewer).layer_to_visual[layer].node.relative_step_size = .5
    np.testing.assert_array_equal(capture(viewer)[48, 48, :3], WHITE)
    generation = lose_device()
    layer.rendering = "iso"
    layer.iso_threshold = .5
    recovered = capture(viewer)
    assert_recovered(generation)
    # The pinned upstream grayscale ISO phantom has the same flat, fully
    # bright front-face normal at the center ray as this binary cube.
    packet = Path(__file__).resolve().parents[1] / "reference" / "volume-opengl"
    reference = np.load(packet / "iso.npy", allow_pickle=False)
    assert int(recovered[48, 48, 0]) == pytest.approx(int(reference[48, 48, 0]), abs=2)
