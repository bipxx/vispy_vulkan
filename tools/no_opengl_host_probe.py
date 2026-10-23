# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise installed Dawn GUI artifacts under the external no-OpenGL monitor.

This is functional evidence. Native dependency/load/context gates are reported
by tools/audit_no_opengl.py, which should wrap this script in scenario=script.
No missing dependency, display, adapter or functional stage counts as a skip.
The napari sparse-label case requires numba==0.68.0 and compatible NumPy.
"""

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import zipfile


SCENARIOS = ('qwidget', 'napari', 'glue', 'threedee')
HOST_PROFILES = {
    'napari': {'napari': 'napari', 'qtpy': 'qtpy'},
    'glue': {'glue-vispy-viewers': 'glue_vispy_viewers', 'qtpy': 'qtpy'},
    'threedee': {'napari': 'napari', 'qtpy': 'qtpy', 'napari-threedee': 'napari_threedee'},
}


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_installed_payload(wheel, package_root, package='vispy', require_native=True):
    """Refuse stale/source-overlay code even if package metadata names the wheel."""
    package_root = Path(package_root).resolve()
    checked = []
    with zipfile.ZipFile(wheel) as bundle:
        for entry in bundle.infolist():
            if not entry.filename.startswith(package + '/') or entry.is_dir():
                continue
            relative = entry.filename[len(package) + 1:]
            installed = package_root / relative
            expected = hashlib.sha256(bundle.read(entry)).hexdigest()
            if not installed.is_file() or file_sha256(installed) != expected:
                raise RuntimeError('installed file differs from exact wheel: ' + entry.filename)
            checked.append(entry.filename)
    if package + '/__init__.py' not in checked or (require_native and not any(
            name.startswith('vispy/_dawn.') and name.endswith(('.pyd', '.so'))
            for name in checked)):
        raise RuntimeError('wheel lacks the required VisPy Python/native payload')
    return {'wheel': str(Path(wheel).resolve()), 'wheel_sha256': file_sha256(wheel),
            'package_root': str(package_root), 'verified_files': len(checked)}


class Evidence:
    def __init__(self, output, scenario):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.report = {'schema': 1, 'scenario': scenario, 'status': 'running',
                       'platform': platform.platform(), 'python': sys.version,
                       'executable': sys.executable, 'stages': [], 'frames': {},
                       'native_no_opengl_gates': 'external monitor required'}
        self.save()

    def save(self):
        (self.output / 'functional.json').write_text(
            json.dumps(self.report, indent=2, default=str) + '\n', encoding='utf-8')

    @contextmanager
    def stage(self, name):
        item = {'name': name, 'status': 'running'}
        self.report['stages'].append(item)
        self.save()
        start = time.monotonic()
        try:
            yield item
        except BaseException as error:
            item.update(status='failed', error=repr(error))
            raise
        else:
            item['status'] = 'passed'
        finally:
            item['seconds'] = time.monotonic() - start
            self.save()

    def frame(self, name, array):
        import numpy as np
        array = np.asarray(array)
        if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 4:
            raise AssertionError('expected uint8 RGBA frame: ' + str((array.shape, array.dtype)))
        if min(array.shape[:2]) <= 0:
            raise AssertionError('empty frame')
        path = self.output / (name + '.npy')
        np.save(path, array, allow_pickle=False)
        self.report['frames'][name] = {'file': path.name, 'sha256': file_sha256(path),
                                      'shape': list(array.shape)}
        self.save()
        return array.copy()


def pump(application, condition=lambda: True, timeout=15):
    deadline = time.monotonic() + timeout
    while True:
        application.process_events()
        if condition():
            return
        if time.monotonic() >= deadline:
            raise TimeoutError('Qt/Dawn did not reach the required functional state')
        time.sleep(.005)


def rgba_qimage(image, qtgui):
    import numpy as np
    formats = getattr(qtgui.QImage, 'Format', qtgui.QImage)
    converted = image.convertToFormat(formats.Format_RGBA8888)
    pointer = converted.bits()
    if hasattr(pointer, 'setsize'):
        pointer.setsize(converted.sizeInBytes())
    array = np.frombuffer(pointer, np.uint8).reshape(converted.height(), converted.bytesPerLine())
    return array[:, :converted.width() * 4].reshape(converted.height(), converted.width(), 4).copy()


def require_qwidget(native, backend):
    names = [cls.__name__ for cls in type(native).__mro__]
    if not isinstance(native, backend.QWidget) or any(
            name in names for name in ('QOpenGLWidget', 'QGLWidget')):
        raise AssertionError('canvas is not an ordinary QWidget: ' + str(names))
    return names


def require_closed(native, canvas_id, dawn):
    try:
        dawn.benchmark_surface_info(canvas_id)
    except RuntimeError as error:
        if 'missing canvas' not in str(error):
            raise
    else:
        raise AssertionError('closed canvas is still registered in the renderer')
    try:
        native.isVisible()
    except RuntimeError as error:
        if 'deleted' in str(error):
            return  # The host destroyed the QObject, rather than closing Canvas.
        raise
    if native.context() is not None:
        raise AssertionError('closed canvas still exposes its rendering context')


def drain_close_events(application):
    # napari legitimately uses deleteLater. Qt's processEvents alone does not
    # dispatch DeferredDelete while a standalone probe pumps outside exec().
    core = application.backend_module.QtCore
    kinds = getattr(core.QEvent, 'Type', core.QEvent)
    application.native.sendPostedEvents(None, kinds.DeferredDelete)
    pump(application)


def qwidget(evidence, application, dawn):
    import numpy as np
    from vispy import app, gloo
    backend = application.backend_module
    parent = backend.QWidget()
    parent.resize(160, 120)
    canvas = app.Canvas(app=application, size=(128, 96), parent=parent,
                        show=False, resizable=True)
    native, draws = canvas.native, []
    canvas_id = int(native._dawn_canvas_id)
    color = [(1, 0, 0, 1)]

    def draw(event):
        gloo.set_viewport(0, 0, *canvas.physical_size)
        gloo.set_clear_color(color[0])
        gloo.clear()
        draws.append(len(draws))

    canvas.events.draw.connect(draw)
    try:
        with evidence.stage('qwidget_show_parent_resize') as stage:
            stage['native_mro'] = require_qwidget(native, backend)
            assert native.parent() is parent
            parent.show()
            native.show()
            pump(application, lambda: bool(draws))
            native.resize(144, 104)
            pump(application, lambda: canvas.size == (144, 104))
            stage['logical_size'] = list(canvas.size)
            stage['physical_size'] = list(canvas.physical_size)
            stage['surface'] = dawn.benchmark_surface_info(canvas_id)
            stage['presentation'] = native._dawn_presentation
            assert stage['surface']['attached'] == (native._dawn_presentation == 'native')
        with evidence.stage('qwidget_capture_update_and_image_ownership'):
            owned = native.grabFramebuffer()
            initial = evidence.frame('qwidget_red', rgba_qimage(owned, backend.QtGui))
            np.testing.assert_array_equal(initial[..., :3], np.broadcast_to([255, 0, 0], initial[..., :3].shape))
            color[0] = (0, 1, 0, 1)
            before = len(draws)
            canvas.update()
            pump(application, lambda: len(draws) > before)
            updated = evidence.frame('qwidget_green', rgba_qimage(native.grabFramebuffer(), backend.QtGui))
            np.testing.assert_array_equal(updated[..., :3], np.broadcast_to([0, 255, 0], updated[..., :3].shape))
            if native._dawn_presentation == 'readback':
                presented = evidence.frame('qwidget_qpainter_visible', rgba_qimage(
                    native.grab().toImage(), backend.QtGui))
                np.testing.assert_array_equal(presented[..., :3],
                    np.broadcast_to([0, 255, 0], presented[..., :3].shape))
            np.testing.assert_array_equal(rgba_qimage(owned, backend.QtGui), initial)
            assert owned.save(str(evidence.output / 'qwidget-owned.png'), 'PNG')
        with evidence.stage('qwidget_overlay_interaction_hide_restore') as stage:
            overlay = backend.QWidget(native)
            overlay.setGeometry(2, 2, 12, 12)
            overlay.setStyleSheet('background-color: rgb(0,0,255)')
            overlay.show()
            assert overlay.parent() is native
            pump(application)
            overlay_pixels = evidence.frame('qwidget_overlay', rgba_qimage(
                overlay.grab().toImage(), backend.QtGui))
            np.testing.assert_array_equal(overlay_pixels[6, 6, :3], [0, 0, 255])
            without_overlay = evidence.frame('qwidget_framebuffer_excludes_overlay',
                rgba_qimage(native.grabFramebuffer(), backend.QtGui))
            np.testing.assert_array_equal(without_overlay, updated)
            events = []
            canvas.events.mouse_press.connect(lambda event: events.append(tuple(int(value) for value in event.pos)))
            buttons = getattr(backend.QtCore.Qt, 'MouseButton', backend.QtCore.Qt)
            backend.QtTest.QTest.mouseClick(native, buttons.LeftButton,
                                            pos=backend.QtCore.QPoint(40, 40))
            pump(application, lambda: bool(events))
            stage['mouse_presses'] = events
            native.hide()
            pump(application)
            native.show()
            native.showMinimized()
            pump(application)
            native.showNormal()
            before = len(draws)
            canvas.update()
            pump(application, lambda: len(draws) > before)
            assert native.isVisible()
            stable = evidence.frame('qwidget_restored', rgba_qimage(native.grabFramebuffer(), backend.QtGui))
        with evidence.stage('qwidget_device_loss_recovery') as stage:
            previous = dawn.probe()['device_generation']
            dawn.lose_device()
            canvas.update()
            pump(application, lambda: dawn.probe()['device_generation'] > previous)
            restored = evidence.frame('qwidget_recovered', rgba_qimage(native.grabFramebuffer(), backend.QtGui))
            np.testing.assert_array_equal(restored, stable)
            stage['device_generation_before'] = previous
            stage['device_generation_after'] = dawn.probe()['device_generation']
    finally:
        with evidence.stage('qwidget_close'):
            canvas.close()
            parent.close()
            pump(application)
            require_closed(native, canvas_id, dawn)


def napari(evidence, application, dawn):
    import numpy as np
    import napari as host
    from napari.utils.colormaps import DirectLabelColormap
    assert metadata.version('napari') == '0.9.2'
    assert metadata.version('QtPy') == '2.4.3'
    assert metadata.version('numba') == '0.68.0'
    evidence.report['host_versions'] = {name: metadata.version(name)
                                        for name in ('napari', 'QtPy', 'superqt', 'numpy', 'numba', 'llvmlite')}
    viewer = host.Viewer(show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene, native = canvas._scene_canvas, canvas.native
    canvas_id = int(native._dawn_canvas_id)
    size = (128, 128)
    require_qwidget(native, application.backend_module)
    native.setFixedSize(*size)
    application.native.setQuitOnLastWindowClosed(False)

    def capture(name):
        viewer._layer_slicer.wait_until_idle(timeout=15)
        pump(application)
        image = viewer.screenshot(canvas_only=True, flash=False)
        return evidence.frame(name, image)

    def changed(before, after):
        assert before.shape == after.shape
        assert np.count_nonzero(np.any(before != after, axis=2)) >= 32

    def fit():
        viewer.fit_to_view(margin=.05)
        viewer.scene.camera.perspective = 0
        scene.bgcolor = (0, 0, 0, 1)

    try:
        with evidence.stage('napari_image_initial_update_capture'):
            data = np.zeros((32, 32), np.float32)
            data[4:16, 4:16] = 1
            image_layer = viewer.add_image(data, colormap='gray', contrast_limits=(0, 1),
                                           interpolation2d='nearest', blending='opaque')
            fit()
            initial = capture('napari_image_initial')
            assert np.count_nonzero(initial[..., 0] > 220) > 64
            assert np.count_nonzero(initial[..., 0] < 20) > 64
            updated = np.zeros_like(data)
            updated[16:28, 16:28] = 1
            image_layer.data = updated
            changed(initial, capture('napari_image_updated'))
        with evidence.stage('napari_overlays_and_mouse_pan') as stage:
            before = capture('napari_overlay_before')
            viewer.text_overlay.text = 'Dawn noGL'
            viewer.text_overlay.visible = True
            changed(before, capture('napari_overlay_visible'))
            center = tuple(viewer.scene.camera.center)
            backend = application.backend_module
            buttons = getattr(backend.QtCore.Qt, 'MouseButton', backend.QtCore.Qt)
            backend.QtTest.QTest.mousePress(native, buttons.LeftButton,
                                            pos=backend.QtCore.QPoint(44, 48))
            backend.QtTest.QTest.mouseMove(native, backend.QtCore.QPoint(72, 64), 40)
            backend.QtTest.QTest.mouseRelease(native, buttons.LeftButton,
                                              pos=backend.QtCore.QPoint(72, 64))
            pump(application)
            stage['camera_center_before'] = center
            stage['camera_center_after'] = tuple(viewer.scene.camera.center)
            assert stage['camera_center_after'] != center
            viewer.text_overlay.visible = False
        with evidence.stage('napari_labels_edit_refresh_capture'):
            viewer.layers.clear()
            labels = np.zeros((32, 32), np.int32)
            labels[4:28, 4:16], labels[4:28, 16:28] = 7, 65537
            cmap = DirectLabelColormap(color_dict={0: (0, 0, 0, 0),
                7: (1, 0, 0, 1), 65537: (0, 1, 0, 1), 16777473: (0, 0, 1, 1),
                None: (1, 1, 0, 1)})
            layer = viewer.add_labels(labels, colormap=cmap, opacity=1)
            fit()
            initial = capture('napari_labels_initial')
            assert np.count_nonzero((initial[..., 0] > 220) & (initial[..., 1] < 20)) > 64
            layer.data[8:24, 8:14] = 16777473
            layer.refresh()
            updated = capture('napari_labels_edited')
            changed(initial, updated)
            assert np.count_nonzero((updated[..., 2] > 220) & (updated[..., 0] < 20)) > 32
        with evidence.stage('napari_volume_update_capture_export'):
            viewer.layers.clear()
            viewer.dims.ndisplay = 3
            data = np.zeros((24, 24, 24), np.float32)
            data[3:11, 4:12, 5:13] = 1
            layer = viewer.add_image(data, rendering='mip', colormap='gray',
                                     contrast_limits=(0, 1), interpolation3d='nearest',
                                     blending='opaque')
            fit()
            initial = capture('napari_volume_initial')
            assert np.count_nonzero(initial[..., 0] > 220) > 32
            data = np.zeros_like(data)
            data[14:21, 13:20, 12:19] = 1
            layer.data = data
            stable = capture('napari_volume_updated')
            changed(initial, stable)
            export = evidence.output / 'napari-volume-export.png'
            exported = viewer.screenshot(path=str(export), canvas_only=True, flash=False)
            assert export.is_file() and export.stat().st_size > 0
            np.testing.assert_array_equal(exported, stable)
        with evidence.stage('napari_device_loss_recovery') as stage:
            previous = dawn.probe()['device_generation']
            dawn.lose_device()
            scene.update()
            pump(application, lambda: dawn.probe()['device_generation'] > previous)
            recovered = capture('napari_volume_recovered')
            np.testing.assert_array_equal(recovered, stable)
            stage['device_generation_before'] = previous
            stage['device_generation_after'] = dawn.probe()['device_generation']
    finally:
        with evidence.stage('napari_close'):
            viewer.close()
            drain_close_events(application)
            require_closed(native, canvas_id, dawn)


def glue(evidence, application, dawn):
    import numpy as np
    from glue.config import settings
    from glue.core import Data, DataCollection
    from glue_qt.app.application import GlueApplication
    from glue_vispy_viewers.scatter.qt.scatter_viewer import VispyScatterViewer
    from glue_vispy_viewers.volume.qt.volume_viewer import VispyVolumeViewer
    from glue.viewers.volume3d.viewer_state import VolumeViewerState3D
    versions = {'glue-core': '1.27.0', 'glue-qt': '0.4.2', 'glue-vispy-viewers': '1.4.0'}
    assert {name: metadata.version(name) for name in versions} == versions
    evidence.report['host_versions'] = versions
    backend = application.backend_module
    dialogs = []
    timer = backend.QtCore.QTimer(application.native)

    def reject_error_dialogs():
        # Observe/reject actual modal dialogs through Qt rather than replacing
        # QMessageBox methods or suppressing a required host failure.
        for widget in application.native.topLevelWidgets():
            if isinstance(widget, backend.QtWidgets.QMessageBox) and widget.isVisible():
                dialogs.append(widget.text())
                widget.reject()

    timer.timeout.connect(reject_error_dialogs)
    timer.start(25)
    previous_colors = settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR
    settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = 'black', 'white'
    scatter_data = Data(label='Dawn scatter', x=np.array([.25, .75], np.float32),
                        y=np.array([.5, .5], np.float32), z=np.array([.5, .5], np.float32))
    volume_data = np.zeros((32, 32, 32), np.float32)
    volume_data[8:24, 8:24, 8:24] = 1
    volume = Data(label='Dawn volume', intensity=volume_data)
    host = GlueApplication(DataCollection([scatter_data, volume]))
    viewers = []

    def capture(viewer, name):
        pump(application)
        assert not dialogs, dialogs
        assert viewer._opengl_ok, 'host compatibility context check failed'
        canvas = viewer._vispy_widget.canvas
        image = evidence.frame(name, canvas.render(size=(128, 128), alpha=True))
        assert np.count_nonzero(image[..., :3]) > 32
        return image

    def configure(viewer, data, color):
        viewers.append(viewer)
        assert viewer.add_data(data)
        state = viewer.state
        state.visible_axes, state.perspective_view = False, False
        layer = state.layers[0]
        layer.alpha, layer.color_mode, layer.color = 1, 'Fixed', color
        canvas = viewer._vispy_widget.canvas
        require_qwidget(canvas.native, backend)
        canvas.native.setFixedSize(128, 128)
        host.show()
        viewer.show()
        pump(application, lambda: viewer._opengl_ok is not None)
        assert not dialogs, dialogs
        canvas.size = (128, 128)
        canvas.central_widget.size = (128, 128)
        camera = viewer._vispy_widget.view.camera
        camera.azimuth, camera.elevation = 0, 0
        camera.center, camera.scale_factor = (0, 0, 0), 2.5
        return state, layer

    try:
        with evidence.stage('glue_scatter_update_axes_capture'):
            scatter = host.new_data_viewer(VispyScatterViewer)
            state, layer = configure(scatter, scatter_data, '#ff0000')
            state.x_att, state.y_att, state.z_att = (scatter_data.id[axis] for axis in 'xyz')
            layer.size_mode, layer.size = 'Fixed', 14
            state.set_limits(0, 1, 0, 1, 0, 1)
            before = capture(scatter, 'glue_scatter_initial')
            assert np.count_nonzero((before[..., 0] > 220) & (before[..., 1] < 20)) > 32
            scatter_data.update_components({scatter_data.id['x']: np.array([.5, .75], np.float32)})
            layer.color = '#0000ff'
            updated = capture(scatter, 'glue_scatter_updated')
            assert np.count_nonzero((updated[..., 2] > 220) & (updated[..., 0] < 20)) > 32
            assert not np.array_equal(before, updated)
            state.visible_axes = True
            axes = capture(scatter, 'glue_scatter_axes')
            assert not np.array_equal(updated, axes)
        with evidence.stage('glue_volume_update_capture_export'):
            viewer = host.new_data_viewer(VispyVolumeViewer,
                state=VolumeViewerState3D(resolution=32, downsample=False))
            state, layer = configure(viewer, volume, '#00ff00')
            layer.attribute = volume.id['intensity']
            layer.v_min, layer.v_max = 0, 1
            state.set_limits(-.5, 31.5, -.5, 31.5, -.5, 31.5)
            before = capture(viewer, 'glue_volume_initial')
            updated_data = np.zeros_like(volume_data)
            updated_data[10:22, 8:24, 18:26] = 1
            volume.update_components({volume.id['intensity']: updated_data})
            layer.color = '#0000ff'
            stable = capture(viewer, 'glue_volume_updated')
            assert not np.array_equal(before, stable)
            image = viewer._vispy_widget.canvas.native.grabFramebuffer()
            assert image.save(str(evidence.output / 'glue-volume-export.png'), 'PNG')
        with evidence.stage('glue_device_loss_recovery') as stage:
            previous = dawn.probe()['device_generation']
            dawn.lose_device()
            for current in viewers:
                current._vispy_widget.canvas.update()
            pump(application, lambda: dawn.probe()['device_generation'] > previous)
            np.testing.assert_array_equal(capture(viewer, 'glue_volume_recovered'), stable)
            stage['device_generation_before'] = previous
            stage['device_generation_after'] = dawn.probe()['device_generation']
    finally:
        with evidence.stage('glue_close'):
            handles = [(viewer._vispy_widget.canvas.native,
                        int(viewer._vispy_widget.canvas.native._dawn_canvas_id)) for viewer in viewers]
            for viewer in viewers:
                viewer.close(warn=False)
            host.close()
            drain_close_events(application)
            for native, canvas_id in handles:
                require_closed(native, canvas_id, dawn)
            assert not dialogs, dialogs
        timer.stop()
        settings.BACKGROUND_COLOR, settings.FOREGROUND_COLOR = previous_colors


def threedee(evidence, application, dawn):
    import numpy as np
    import napari as host
    assert metadata.version('napari-threedee') == '0.0.29'
    evidence.report['host_versions'] = {name: metadata.version(name)
        for name in ('napari', 'napari-threedee', 'QtPy', 'numpy')}
    viewer = host.Viewer(ndisplay=2, show=True)
    canvas = viewer.window._qt_viewer.canvas
    scene, native = canvas._scene_canvas, canvas.native
    canvas_id = int(native._dawn_canvas_id)
    backend = application.backend_module
    require_qwidget(native, backend)

    def capture(name):
        viewer._layer_slicer.wait_until_idle(timeout=15)
        pump(application)
        frame = evidence.frame(name, viewer.screenshot(canvas_only=True, flash=False))
        assert np.count_nonzero(frame[..., :3]) > 32
        return frame

    def project(transform, world):
        value = np.asarray(transform.map(np.asarray(world)[::-1]), float)
        return value[:2] / value[3]

    try:
        with evidence.stage('threedee_registered_widget_activation') as stage:
            data = np.zeros((12, 16, 20), np.float32)
            data[2:5, 3:7, 4:9], data[6:10, 8:13, 11:17] = .25, 1
            layer = viewer.add_image(data, contrast_limits=(0, 1), colormap='gray',
                                     rendering='mip', interpolation3d='nearest', blending='opaque')
            viewer.dims.ndisplay = 3
            pump(application)
            dock, widget = viewer.window.add_plugin_dock_widget('napari-threedee', 'layer manipulator')
            assert type(widget).__name__ == 'QtLayerManipulatorWidget'
            assert type(widget).__module__.startswith('napari_threedee.')
            widget.model.set_layers(layer)
            widget.activate_button.click()
            assert widget.model.enabled and widget.activate_button.isChecked()
            viewer.dims.ndisplay = 2
            viewer.dims.ndisplay = 3
            widget.model.radius, widget.model.handle_size = 8, 2
            widget.model.origin = np.zeros(3)
            native.setFixedSize(256, 192)
            pump(application)
            canvas.size = (192, 256)
            scene.central_widget.size = (256, 192)
            scene.bgcolor = (0, 0, 0, 1)
            viewer.scene.camera.center = (4.5, 5.5, 7.5)
            viewer.scene.camera.zoom = 6
            viewer.scene.camera.angles = (20, 35, 0)
            viewer.scene.camera.perspective = 0
            initial = capture('threedee_handles_initial')
            stage['widget_class'] = type(widget).__module__ + '.' + type(widget).__name__
        with evidence.stage('threedee_real_qt_selection_translation') as stage:
            transform = canvas.view.transform * canvas.view.scene.transform
            start_pixel = np.rint(project(transform, (0, 0, 10))).astype(int)
            end_pixel = np.rint(project(transform, (0, 0, 12))).astype(int)
            direction = end_pixel - start_pixel
            first_pixel = np.rint(start_pixel + direction / np.linalg.norm(direction) * 2).astype(int)
            assert 3 <= start_pixel[0] < 253 and 3 <= start_pixel[1] < 189
            points = [backend.QtCore.QPoint(*map(int, point))
                      for point in (start_pixel, first_pixel, end_pixel)]
            buttons = getattr(backend.QtCore.Qt, 'MouseButton', backend.QtCore.Qt)
            backend.QtTest.QTest.mousePress(native, buttons.LeftButton, pos=points[0])
            pump(application)
            assert widget.model._backend.is_dragging
            assert widget.model.selected_translator.id == 2
            evidence.frame('threedee_selected', viewer.screenshot(canvas_only=True, flash=False))
            backend.QtTest.QTest.mouseMove(native, points[1], 40)
            pump(application)
            backend.QtTest.QTest.mouseMove(native, points[2], 40)
            pump(application)
            backend.QtTest.QTest.mouseRelease(native, buttons.LeftButton, pos=points[2])
            pump(application)
            assert not widget.model._backend.is_dragging
            assert widget.model.selected_translator is None
            translation = np.asarray(layer.translate)
            np.testing.assert_allclose(widget.model.origin, translation, atol=1e-6, rtol=0)
            np.testing.assert_allclose(translation[:2], 0, atol=1e-6, rtol=0)
            assert translation[2] > .25
            stage['translation'] = translation.tolist()
            moved = capture('threedee_translated')
            assert not np.array_equal(initial, moved)
        with evidence.stage('threedee_data_update_and_device_recovery') as stage:
            layer.data = data[::-1].copy()
            stable = capture('threedee_volume_updated')
            assert not np.array_equal(stable, moved)
            previous = dawn.probe()['device_generation']
            dawn.lose_device()
            scene.update()
            pump(application, lambda: dawn.probe()['device_generation'] > previous)
            np.testing.assert_array_equal(capture('threedee_recovered'), stable)
            stage['device_generation_before'] = previous
            stage['device_generation_after'] = dawn.probe()['device_generation']
        with evidence.stage('threedee_callback_retirement'):
            callbacks = (widget.model._backend._mouse_callback, widget.model._mouse_callback)
            widget.activate_button.click()
            assert not widget.model.enabled
            viewer.dims.ndisplay = 2
            pump(application)
            assert not any(callback in layer.mouse_drag_callbacks for callback in callbacks)
            capture('threedee_retired')
            viewer.layers.remove(layer)
    finally:
        with evidence.stage('threedee_close'):
            viewer.close()
            drain_close_events(application)
            require_closed(native, canvas_id, dawn)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--binding', choices=('pyqt5', 'pyqt6', 'pyside6'), default='pyqt6')
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--host-wheel', type=Path, action='append', default=[],
                        help='exact host profile wheels; required for each host scenario')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-software', action='store_true')
    args = parser.parse_args(argv)
    evidence = Evidence(args.output, args.scenario)
    try:
        os.environ['QT_API'] = args.binding
        with evidence.stage('exact_installed_artifact'):
            import vispy
            evidence.report['artifact'] = verify_installed_payload(args.wheel, Path(vispy.__file__).parent)
            from vispy import _dawn, app
            evidence.report['native_origin'] = _dawn.__file__
            if Path(_dawn.__file__).resolve().parent != Path(vispy.__file__).resolve().parent:
                raise RuntimeError('native extension origin differs from verified installed package')
        with evidence.stage('device_and_qt_binding'):
            device = _dawn.device_info()
            evidence.report['device'] = device
            assert device['ok'], device
            assert device['backend'] == 'Vulkan', device
            if not args.allow_software:
                assert not device['software'], device
            application = app.use_app(args.binding)
            application.native.setQuitOnLastWindowClosed(False)
            evidence.report['binding'] = args.binding
            evidence.report['qt_platform'] = application.backend_module.QtGui.QGuiApplication.platformName()
        if args.scenario in HOST_PROFILES:
            with evidence.stage('exact_patched_host_artifacts'):
                found = {}
                required = HOST_PROFILES[args.scenario]
                for host_wheel in args.host_wheel:
                    with zipfile.ZipFile(host_wheel) as bundle:
                        names = [name for name in bundle.namelist()
                                 if name.endswith('.dist-info/METADATA')]
                        if len(names) != 1:
                            raise RuntimeError('host wheel must contain exactly one METADATA')
                        from email.parser import BytesParser
                        project = BytesParser().parsebytes(bundle.read(names[0]))['Name'].lower()
                    if project not in required or project in found:
                        raise RuntimeError('unexpected or duplicate host wheel for ' + args.scenario)
                    distribution = metadata.distribution(project)
                    found[project] = verify_installed_payload(
                        host_wheel, distribution.locate_file(required[project]), required[project],
                        require_native=False)
                if set(found) != set(required):
                    raise RuntimeError(args.scenario + ' requires --host-wheel for ' + ', '.join(required))
                evidence.report['host_artifacts'] = found
        globals()[args.scenario](evidence, application, _dawn)
        evidence.report['status'] = 'passed'
        return 0
    except BaseException:
        evidence.report.update(status='failed', traceback=traceback.format_exc())
        return 1
    finally:
        evidence.save()
        print(json.dumps({'functional_report': str(evidence.output / 'functional.json'),
                          'status': evidence.report['status']}))


if __name__ == '__main__':
    raise SystemExit(main())
