# SPDX-License-Identifier: AGPL-3.0-only
"""Independent pixel and input oracles for public scene cameras."""
import numpy as np
import pytest

from vispy import scene
from vispy.app.canvas import MouseEvent
from vispy.scene import cameras
from vispy.scene.events import SceneMouseEvent
from vispy.util import keys
from vispy.util.quaternion import Quaternion

pytestmark = pytest.mark.gpu


def square(parent, center, color='red', size=6):
    return scene.Rectangle(center=center, width=size, height=size,
                           color=color, parent=parent)


def landmark(frame, rgb, xy, atol=1):
    y, x = np.where(np.all(frame == rgb, axis=-1))
    assert len(x) > 3
    np.testing.assert_allclose((x.mean() + .5, y.mean() + .5), xy, atol=atol)


def mouse(view, kind, pos, press=None, buttons=(), delta=(0, 0)):
    event = MouseEvent(kind, pos=pos, button=1 if kind != 'mouse_wheel' else None,
                       buttons=list(buttons), press_event=press, delta=delta)
    getattr(view.events, kind)(SceneMouseEvent(event, view))
    return event


def tick(timer, count=1, dt=.1):
    # Dispatch the real Timer timeout event with a deterministic elapsed time.
    for _ in range(count):
        if timer.running:
            timer.events.timeout(dt=dt)


def test_base_camera_identity_range_and_reset(canvas_factory, draw):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = cameras.BaseCamera()
    view.camera = camera
    square(view.scene, (24, 38))
    camera.set_range(x=(10, 50), y=(20, 60), z=(-2, 4))
    assert tuple(camera.center) == (30, 40, 1)
    # A direct BaseCamera has no resettable state.
    camera.center = (1, 2, 3)
    camera.reset()
    assert tuple(camera.center) == (1, 2, 3)
    landmark(draw(canvas), (255, 0, 0), (24, 38))


def test_base_camera_resize_ownership_after_replacement(canvas_factory, draw):
    class ResizeCamera(cameras.BaseCamera):
        def __init__(self):
            self.sizes = []
            super().__init__()

        def viewbox_resize_event(self, event):
            self.sizes.append(tuple(event.source.size))

    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    old, active = ResizeCamera(), ResizeCamera()
    view.camera = old
    square(view.scene, (24, 38))
    view.camera = active
    view.size = (80, 60)
    assert old.sizes == []
    assert active.sizes == [(80, 60)]
    assert old.viewbox is None
    old.pre_transform = scene.STTransform(translate=(20, 0))
    landmark(draw(canvas), (255, 0, 0), (24, 38))


def test_make_camera_forwards_panzoom_arguments(canvas_factory, draw):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = cameras.make_camera('panzoom', (10, 20, 50, 50), aspect=1,
                                 flip=(False, True, False))
    assert type(camera) is cameras.PanZoomCamera
    assert camera.aspect == 1
    assert (camera.rect.pos, camera.rect.size) == ((10, 20), (50, 50))
    view.camera = camera
    square(view.scene, (25, 40))
    landmark(draw(canvas), (255, 0, 0), (30, 40))


def test_make_camera_rejection_leaves_view_usable(canvas_factory, draw):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    old = view.camera
    square(view.scene, (25, 40))
    with pytest.raises(KeyError, match='Unknown camera type'):
        view.camera = 'unknown-scene-camera'
    assert view.camera is old
    landmark(draw(canvas), (255, 0, 0), (25, 40))
    view.camera = cameras.make_camera('panzoom', (0, 0, 50, 50),
                                     flip=(False, True, False))
    landmark(draw(canvas), (255, 0, 0), (50, 80))


def test_camera_namespace_switches_between_2d_and_3d_projection(canvas_factory, draw):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    scene.Markers(pos=np.array([[20., 30., 0.]]), size=9, face_color='red',
                  edge_width=0, parent=view.scene)
    view.camera = cameras.make_camera('panzoom', (0, 0, 50, 100),
                                     flip=(False, True, False))
    landmark(draw(canvas), (255, 0, 0), (40, 30))
    view.camera = cameras.make_camera('turntable', fov=0, elevation=10, azimuth=35,
                                     center=(20, 30, 0), scale_factor=100)
    assert type(view.camera) is cameras.TurntableCamera
    assert (view.camera.elevation, view.camera.azimuth) == (10, 35)
    landmark(draw(canvas), (255, 0, 0), (50, 50))
    view.camera = 'panzoom'
    landmark(draw(canvas), (255, 0, 0), (40, 30))

def test_camera_switch_stops_lens_and_routes_wheel_to_panzoom(canvas_factory, draw):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    lens = cameras.MagnifyCamera(rect=(0, 0, 100, 100), mag=1)
    lens.flip = (False, True, False)
    view.camera = lens
    square(view.scene, (25, 50))
    landmark(draw(canvas), (255, 0, 0), (25, 50))
    mouse(view, 'mouse_wheel', (50, 50), delta=(0, 2))
    assert lens.timer.running
    view.camera = 'panzoom'
    panzoom = view.camera
    panzoom.flip = (False, True, False)
    panzoom.rect = (0, 0, 100, 100)
    assert not lens.timer.running
    target = lens.mag_target
    mouse(view, 'mouse_wheel', (50, 50), delta=(0, 1))
    tick(lens.timer)
    assert lens.mag_target == target
    # A wheel notch scales the rect by (1 + zoom_factor)**-30.
    factor = (1 + panzoom.zoom_factor) ** 30
    landmark(draw(canvas), (255, 0, 0), (50 - 25 * factor, 50))
    view.camera = 'panzoom'
    assert view.camera is panzoom


def arcball_scene(canvas_factory):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = cameras.ArcballCamera(fov=0, center=(0, 0, 0), scale_factor=2)
    view.camera = camera
    scene.Markers(pos=np.array([[0., 0., 0.], [.6, 0., 0.]]), size=9,
                  face_color=['green', 'red'], edge_width=0, parent=view.scene)
    return canvas, view


def drag_arc(view):
    # Two trackball vectors at x offsets +/- 12.5 have x components
    # +/- 1/4, so their dot product is 7/8. The quaternion doubles that angle.
    press = mouse(view, 'mouse_press', (37.5, 50), buttons=(1,))
    mouse(view, 'mouse_move', (37.5, 50), press, (1,))
    mouse(view, 'mouse_move', (62.5, 50), press, (1,))
    return press


def test_arcball_off_center_drag_projects_landmarks(canvas_factory, draw):
    canvas, view = arcball_scene(canvas_factory)
    landmark(draw(canvas), (255, 0, 0), (80, 50))
    drag_arc(view)
    frame = draw(canvas)
    landmark(frame, (0, 128, 0), (50, 50))
    landmark(frame, (255, 0, 0), (65.9375, 50))


def test_arcball_release_ignores_hover_then_accepts_fresh_drag(canvas_factory, draw):
    canvas, view = arcball_scene(canvas_factory)
    press = drag_arc(view)
    mouse(view, 'mouse_release', (62.5, 50), press)
    released = draw(canvas)
    mouse(view, 'mouse_move', (95, 50))
    np.testing.assert_array_equal(draw(canvas), released)
    drag_arc(view)
    # A second identical drag doubles the first rotation.
    landmark(draw(canvas), (255, 0, 0), (50 + 30 * (2 * .53125**2 - 1), 50))


def fly_scene(canvas_factory):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = cameras.FlyCamera(fov=90, rotation=Quaternion(), center=(0, 0, 0),
                              scale_factor=2)
    camera.auto_roll = False
    view.camera = camera
    # FlyCamera computes a fitted pose when it is first attached.
    camera.set_state(center=(0, 0, 0), scale_factor=2,
                     rotation1=Quaternion(), rotation2=Quaternion())
    scene.Markers(pos=np.array([[1., 0., -4.]]), size=9, face_color='red',
                  edge_width=0, parent=view.scene)
    return canvas, view, camera


def test_fly_forward_tick_and_pointer_yaw(canvas_factory, draw):
    canvas, view, camera = fly_scene(canvas_factory)
    landmark(draw(canvas), (255, 0, 0), (62.5, 50))
    canvas.events.key_press(key=keys.UP)
    assert camera._timer.running
    tick(camera._timer, dt=1)
    # On its first tick acceleration .1 is reduced by 5%, at 2 units/s.
    np.testing.assert_allclose(camera.center, (0, 0, -.19))
    landmark(draw(canvas), (255, 0, 0), (50 + 50 / 3.81, 50))
    canvas.events.key_release(key=keys.UP)
    press = mouse(view, 'mouse_press', (20, 50), buttons=(1,))
    mouse(view, 'mouse_move', (45, 50), press, (1,))
    tick(camera._timer, dt=0)
    # Quarter-width movement gives a 22.5 degree yaw.
    landmark(draw(canvas), (255, 0, 0),
             (50 + 50 * np.tan(np.arctan(1 / 3.81) - np.pi / 8), 50))


def test_fly_release_settles_and_new_press_moves(canvas_factory, draw):
    canvas, _, camera = fly_scene(canvas_factory)
    canvas.events.key_press(key=keys.UP)
    tick(camera._timer, dt=1)
    canvas.events.key_release(key=keys.UP)
    tick(camera._timer, count=20, dt=.1)
    assert not camera._timer.running
    stopped = draw(canvas)
    center = camera.center
    tick(camera._timer, count=5, dt=.1)
    assert camera.center == center
    np.testing.assert_array_equal(draw(canvas), stopped)
    canvas.events.key_press(key=keys.UP)
    tick(camera._timer, dt=1)
    np.testing.assert_allclose(camera.center, (0, 0, center[2] - .19))
    landmark(draw(canvas), (255, 0, 0), (50 + 50 / (4 + camera.center[2]), 50))

    # Switch with the forward key still held. The old camera has no key ownership.
    view = camera.viewbox
    view.camera = cameras.BaseCamera()
    assert not camera._timer.running
    canvas.events.key_press(key=keys.UP)
    assert not camera._timer.running


@pytest.mark.parametrize('camera_type,y_scale', [
    (cameras.Magnify1DCamera, 1), (cameras.MagnifyCamera, 2),
])
def test_magnify_lens_moves_over_two_axis_landmarks(canvas_factory, draw, camera_type, y_scale):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = camera_type(rect=(0, 0, 100, 100), center=(40, 45), mag=2)
    camera.flip = (False, True, False)
    view.camera = camera
    square(view.scene, (44, 45), size=3)
    square(view.scene, (40, 49), 'blue', size=3)
    frame = draw(canvas)
    landmark(frame, (255, 0, 0), (48, 45))
    landmark(frame, (0, 0, 255), (40, 45 + 4 * y_scale))
    mouse(view, 'mouse_move', (42, 46))
    tick(camera.timer, count=2, dt=1)
    camera.size_factor = .3
    camera.view_changed()
    assert camera.mag.radii == (27, 30)
    frame = draw(canvas)
    landmark(frame, (255, 0, 0), (46, 46 - y_scale))
    landmark(frame, (0, 0, 255), (38, 46 + 3 * y_scale))


@pytest.mark.parametrize('camera_type', [cameras.Magnify1DCamera, cameras.MagnifyCamera])
def test_magnify_resize_interrupt_and_neutral_recovery(canvas_factory, draw, camera_type):
    canvas = canvas_factory()
    view = canvas.central_widget.add_view()
    camera = camera_type(rect=(0, 0, 100, 100), mag=1)
    camera.flip = (False, True, False)
    view.camera = camera
    square(view.scene, (44, 50))
    square(view.scene, (90, 10), 'blue')
    mouse(view, 'mouse_wheel', (40, 40), delta=(0, 2))
    tick(camera.timer, dt=.001)
    canvas.size = (120, 100)
    assert view.size == (120, 100)
    camera.rect = (0, 0, 120, 100)
    mouse(view, 'mouse_wheel', (42, 50), delta=(0, 1))
    tick(camera.timer, count=3, dt=1)
    assert not camera.timer.running
    np.testing.assert_allclose(camera.mag.center, (42, 50))
    frame = draw(canvas)
    landmark(frame, (255, 0, 0), (42 + 2 * 1.2**3, 50))
    landmark(frame, (0, 0, 255), (90, 10))
    mouse(view, 'mouse_wheel', (42, 50), delta=(0, -10))
    tick(camera.timer, count=3, dt=1)
    frame = draw(canvas)
    assert camera.mag.mag == 1
    landmark(frame, (255, 0, 0), (44, 50))
    landmark(frame, (0, 0, 255), (90, 10))
