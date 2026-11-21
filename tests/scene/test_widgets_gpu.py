# SPDX-License-Identifier: AGPL-3.0-only
"""Headless layout and recovery checks for public scene widgets."""
import numpy as np
import pytest

from vispy import scene
from vispy.app.canvas import MouseEvent
from vispy.color import Colormap
from vispy.scene import widgets
from vispy.scene.events import SceneMouseEvent

pytestmark = pytest.mark.gpu
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)


def pixel(frame, x, y, color):
    np.testing.assert_array_equal(frame[y, x], color)


def place(widget, parent, pos, size):
    widget.parent = parent
    widget.pos = pos
    widget.size = size
    return widget


def label_bounds(frame):
    y, x = np.where((frame[..., 0] > 100) & (frame[..., 1:] == 0).all(axis=-1))
    assert len(x) > 15
    return np.array([x.min(), y.min(), x.max() + 1, y.max() + 1])


def test_label_rotated_glyphs_are_centered(canvas_factory, draw):
    canvas = canvas_factory()
    label = widgets.Label('HHHH', rotation=90, color='red', font_size=12)
    place(label, canvas.scene, (10, 12), (70, 66))
    x0, y0, x1, y1 = label_bounds(draw(canvas))
    assert y1 - y0 > 2 * (x1 - x0)
    np.testing.assert_allclose(((x0 + x1) / 2, (y0 + y1) / 2), (45, 45), atol=3)


def test_label_empty_then_restores_at_resized_center(canvas_factory, draw):
    canvas = canvas_factory(size=(150, 110))
    label = place(widgets.Label('HHHH', color='red'), canvas.scene, (4, 8), (62, 36))
    label_bounds(draw(canvas))
    label.text = ''
    label.size = (138, 100)
    assert not draw(canvas).any()
    label.text = 'HHHH'
    x0, y0, x1, y1 = label_bounds(draw(canvas))
    assert x1 - x0 > 2 * (y1 - y0)
    np.testing.assert_allclose(((x0 + x1) / 2, (y0 + y1) / 2), (73, 58), atol=3)


def test_console_wrap_scroll_and_no_wrap(canvas_factory, draw):
    canvas = canvas_factory()
    console = widgets.Console(parent=canvas.scene, pos=(10, 20), size=(24, 20),
                              text_color='red', font_size=6)
    console.write('HHHHHH')
    mask = draw(canvas)[20:40, 10:34, 0] > 100
    assert mask[:10, :24].sum() == 68  # Four H glyphs, 17 lit pixels each.
    assert mask[10:, :12].sum() == 34
    assert not mask[10:, 12:].any()
    console.write(' ')
    console.write('HHHHHH', wrap=False)
    mask = draw(canvas)[20:40, 10:34, 0] > 100
    assert not mask[:10].any()
    assert mask[10:].sum() == 68


def test_console_reject_clear_before_draw_and_recover(canvas_factory, draw):
    canvas = canvas_factory()
    console = widgets.Console(parent=canvas.scene, pos=(10, 20), size=(24, 20),
                              text_color='red', font_size=6)
    console.write('HHHHHH')
    with pytest.raises(TypeError, match='text must be a string'):
        console.write(42)
    console.clear()
    assert not draw(canvas).any()
    console.write('H')
    frame = draw(canvas)
    assert (frame[30:40, 10:16, 0] > 100).sum() == 17
    assert not frame[:30].any()
    assert not frame[:, 16:].any()


def test_widget_margin_border_background_and_visibility(canvas_factory, draw):
    canvas = canvas_factory()
    widget = widgets.Widget(parent=canvas.scene, pos=(10, 18), size=(55, 44),
                            bgcolor='red', border_color='blue', border_width=3,
                            margin=4, padding=5)
    frame = draw(canvas)
    pixel(frame, 12, 35, BLACK)
    pixel(frame, 15, 35, BLUE)
    pixel(frame, 23, 35, RED)
    assert (widget.inner_rect.pos, widget.inner_rect.size) == ((13, 13), (29, 18))
    widget.visible = False
    assert not draw(canvas).any()


def test_widget_invalid_stretch_then_manage_child_after_resize(canvas_factory, draw):
    canvas = canvas_factory()
    widget = widgets.Widget(parent=canvas.scene, pos=(10, 18), size=(55, 44),
                            bgcolor='red', margin=3, padding=5)
    original_stretch = tuple(widget.stretch)
    with pytest.raises(RuntimeError, match='received 0 as stretch'):
        widget.stretch = (0, 1)
    assert tuple(widget.stretch) == original_stretch
    widget.stretch = (2, 1)
    child = widget.add_widget(widgets.Widget(bgcolor='blue'))
    widget.size = (64, 52)
    assert tuple(child.pos) == (8, 8)
    assert tuple(child.size) == (48, 36)
    pixel(draw(canvas), 30, 40, BLUE)
    widget.remove_widget(child)
    assert child.parent is None
    pixel(draw(canvas), 30, 40, RED)
    widget.add_widget(child)
    pixel(draw(canvas), 30, 40, BLUE)


def split_views(canvas):
    left = widgets.ViewBox(parent=canvas.scene, pos=(5, 8), size=(40, 60))
    right = widgets.ViewBox(parent=canvas.scene, pos=(52, 8), size=(45, 60))
    for view, width, color in [(left, 40, 'red'), (right, 90, 'blue')]:
        view.camera = scene.PanZoomCamera(rect=(0, 0, width, 60),
                                          flip=(False, True, False))
        scene.Rectangle(center=(15, 20), width=64, height=14,
                        color=color, parent=view.scene)
    return left, right


def test_viewbox_independent_clip_and_camera_scales_after_resize(canvas_factory, draw):
    canvas = canvas_factory()
    left, right = split_views(canvas)
    frame = draw(canvas)
    pixel(frame, 6, 28, RED)
    pixel(frame, 43, 28, RED)
    pixel(frame, 45, 28, BLACK)
    pixel(frame, 74, 28, BLUE)
    pixel(frame, 77, 28, BLACK)
    right.size = (40, 45)
    frame = draw(canvas)
    pixel(frame, 43, 28, RED)
    pixel(frame, 72, 24, BLUE)
    pixel(frame, 74, 24, BLACK)


def test_viewbox_invalid_camera_and_replacement_input_stays_local(canvas_factory, draw):
    canvas = canvas_factory()
    left, right = split_views(canvas)
    old = left.camera
    before = draw(canvas)
    with pytest.raises(ValueError, match='Not a camera'):
        left.camera = object()
    assert left.camera is old
    left.camera = scene.PanZoomCamera(rect=(0, 0, 40, 60), flip=(False, True, False))
    old_rect = old.rect.pos, old.rect.size
    event = MouseEvent('mouse_wheel', pos=(25, 38), delta=(0, 1))
    left.events.mouse_wheel(SceneMouseEvent(event, left))
    assert (old.rect.pos, old.rect.size) == old_rect
    np.testing.assert_allclose(left.camera.rect.center, (20, 30))
    after = draw(canvas)
    pixel(before, 20, 17, BLACK)
    pixel(after, 20, 17, RED)
    np.testing.assert_array_equal(after[:, 50:], before[:, 50:])
    assert right.camera.viewbox is right


def test_grid_nested_span_fixed_width_and_stretch(canvas_factory, draw):
    canvas = canvas_factory(size=(124, 84))
    outer = canvas.central_widget.add_grid(spacing=4)
    fixed = outer.add_widget(row=0, col=0, bgcolor='red')
    fixed.width_min = fixed.width_max = 30
    flexible = outer.add_widget(row=0, col=1, bgcolor='blue')
    nested = outer.add_grid(row=1, col=0, col_span=2, spacing=4)
    a = nested.add_widget(row=0, col=0, bgcolor='yellow')
    b = nested.add_widget(row=0, col=1, bgcolor='magenta')
    a.stretch, b.stretch = (1, 1), (2, 1)
    for width in (124, 154):
        canvas.size = (width, 84)
        frame = draw(canvas)
        np.testing.assert_allclose(nested.size, (width, 40))
        np.testing.assert_allclose((a.width, b.width), ((width - 4) / 3, (width - 4) * 2 / 3))
        assert (fixed.width, flexible.pos) == (30, (34, 0))
        pixel(frame, 27, 20, RED)
        pixel(frame, 32, 20, BLACK)
        pixel(frame, 37, 20, BLUE)
        pixel(frame, 3, 60, (255, 255, 0))
        pixel(frame, width - 3, 60, (255, 0, 255))


def test_grid_collision_then_remove_and_reflow(canvas_factory, draw):
    canvas = canvas_factory(size=(124, 84))
    grid = canvas.central_widget.add_grid(spacing=4)
    top = grid[0, 0:2]
    top.bgcolor = 'red'
    bottom = grid.add_view(row=1, col=0, col_span=2)
    scene.Rectangle(center=(60, 10), width=150, height=24, color='blue',
                    parent=bottom.scene)
    before = draw(canvas)
    pixel(before, 50, 20, RED)
    pixel(before, 50, 43, BLACK)
    pixel(before, 50, 48, BLUE)
    with pytest.raises(ValueError, match='collision'):
        _ = grid[0, 0]
    grid.remove_widget(bottom)
    assert bottom.parent is None
    after = draw(canvas)
    assert tuple(top.size) == (124, 84)
    pixel(after, 50, 48, RED)


def test_axis_linked_ticks_then_relink_and_resize(canvas_factory, draw):
    canvas = canvas_factory(size=(160, 120))
    first = widgets.ViewBox(parent=canvas.scene, pos=(20, 0), size=(100, 60))
    second = widgets.ViewBox(parent=canvas.scene, pos=(20, 0), size=(100, 60))
    first.camera = scene.PanZoomCamera(rect=(0, 0, 10, 6))
    second.camera = scene.PanZoomCamera(rect=(100, 50, 20, 12))
    bottom = place(widgets.AxisWidget(orientation='bottom', axis_color='red',
                                      tick_color='red', text_color='white',
                                      major_tick_length=9, minor_tick_length=3),
                   canvas.scene, (20, 60), (100, 50))
    left = place(widgets.AxisWidget(orientation='left', axis_color='blue',
                                    tick_color='blue', text_color='white'),
                 canvas.scene, (0, 0), (20, 60))
    bottom.link_view(first)
    left.link_view(first)
    np.testing.assert_allclose(bottom.axis.domain, (0, 10))
    np.testing.assert_allclose(left.axis.domain, (0, 6))
    frame = draw(canvas)
    assert frame[65:69, 69:72, 0].max() > 100  # midpoint major tick
    assert (frame[70:110, 20:120].min(axis=-1) > 80).sum() > 10
    first.camera.pan((10, 0))
    np.testing.assert_allclose(bottom.axis.domain, (10, 20))
    bottom.link_view(second)
    first.camera.pan((10, 0))
    np.testing.assert_allclose(bottom.axis.domain, (100, 120))
    second.size = (120, 60)
    bottom.size = (120, 50)
    second.camera.pan((20, 0))
    np.testing.assert_allclose(bottom.axis.domain, (120, 140))
    frame = draw(canvas)
    assert frame[65:69, 79:82, 0].max() > 100
    assert frame[65:69, 69:72, 0].max() == 0


@pytest.mark.parametrize('orientation', ['bottom', 'right'])
def test_colorbar_orientation_endpoints_mutation_and_restore(canvas_factory, draw, orientation):
    canvas = canvas_factory(size=(160, 160))
    bar = widgets.ColorBarWidget(Colormap(['red', 'blue']), orientation,
                                 label='HH', label_color='white', clim=(1, 9),
                                 axis_ratio=.2)
    place(bar, canvas.scene, (10, 10), (140, 140))
    low, high = ((30, 80), (130, 80)) if orientation == 'bottom' else ((80, 130), (80, 30))
    original = draw(canvas)
    assert original[low[1], low[0], 0] > 220
    assert original[high[1], high[0], 2] > 220
    assert (original.min(axis=-1) > 120).sum() > 20  # Label and numeric tick ink.
    bar.cmap = Colormap(['green', 'yellow'])
    bar.clim = (20, 90)
    bar.label = 'MMMM'
    changed = draw(canvas)
    assert changed[high[1], high[0], :2].min() > 130
    assert changed[high[1], high[0], 2] == 0
    bar.cmap = Colormap(['red', 'blue'])
    bar.clim = (1, 9)
    bar.label = 'HH'
    np.testing.assert_array_equal(draw(canvas), original)


def test_widgets_composed_grid_survives_middle_widget_removal(canvas_factory, draw):
    canvas = canvas_factory(size=(184, 164))
    grid = canvas.central_widget.add_grid(spacing=4)
    axis = grid.add_widget(widgets.AxisWidget(orientation='bottom', axis_color='red',
                                              tick_color='red'), row=0, col=0)
    bar = grid.add_widget(widgets.ColorBarWidget(Colormap(['red', 'blue']), 'bottom',
                                                  axis_ratio=.2), row=0, col=1)
    label = grid.add_widget(widgets.Label('HHH', color='red'), row=1, col=0)
    console = grid.add_widget(widgets.Console(text_color='red', font_size=6), row=1, col=1)
    view = grid.add_view(row=2, col=0, col_span=2, bgcolor='blue')
    axis.link_view(view)
    console.write('HHHH')
    before = draw(canvas)
    assert before[:55, :89, 0].max() == 255
    assert before[20:35, 100:175, 2].max() > 200
    assert (before[65:100, :89, 0] > 100).sum() > 20
    assert (before[97:108, 94:120, 0] > 100).sum() > 20
    pixel(before, 30, 130, BLUE)
    grid.remove_widget(label)
    canvas.size = (204, 194)
    after = draw(canvas)
    assert label.parent is None
    assert not after[75:117, :90].any()
    assert after[25:40, 112:190, 2].max() > 200
    pixel(after, 30, 160, BLUE)
