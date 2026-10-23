# SPDX-License-Identifier: AGPL-3.0-only
"""Full 4096-square image controls; criteria are independent of either renderer.

Integer camera pans preserve texel centers for both interpolation modes. These
quality captures intentionally read back each frame; they are not timing or
no-wait performance measurements.
"""
from __future__ import annotations

import numpy as np

try:
    from .fixture_gloo import freeze
    from .benchmark_work import NATIVE_RESIDENT_ZERO
except ImportError:
    from fixture_gloo import freeze
    from benchmark_work import NATIVE_RESIDENT_ZERO

SIDE = 4096
CASES = ('scalar_nearest', 'scalar_linear', 'rgba_nearest', 'rgba_linear')
STAGES = ('baseline', 'repeat', 'pan', 'return')
PAN = (-13, 17)
RESIDENT_ZERO = NATIVE_RESIDENT_ZERO + ('texture_upload_bytes', 'geometry_upload_bytes')
# Preserve order without requiring duplicate evidence for geometry_upload_bytes.
RESIDENT_ZERO = tuple(dict.fromkeys(RESIDENT_ZERO))


def _validate(name, stage='baseline'):
    if name not in CASES or stage not in STAGES:
        raise ValueError('Unknown large-image case or stage')


def _levels(x, y):
    return ((x // 17) + (y // 23) + ((x % 13) // 4)) % 4


def input_data(name):
    _validate(name)
    y, x = np.ogrid[:SIDE, :SIDE]
    if name.startswith('scalar_'):
        return np.array([0, .25, .5, 1], np.float32)[_levels(x, y)]
    data = np.empty((SIDE, SIDE, 4), np.uint8)
    data[..., 0] = (3*x + 5*y + 17) % 256
    data[..., 1] = (7*x + 11*y + 43) % 256
    data[..., 2] = ((x // 17) ^ ((y // 31) * 29)) % 256
    data[..., 3] = ((x // 64 + y // 32) % 4) * 85
    return data


def expected_rows(name, stage, start, stop):
    """Analytic RGBA for complete rows, including newly exposed background.

    No input array, reference image, or renderer output is consulted.
    """
    _validate(name, stage)
    if not (type(start) is int and type(stop) is int and 0 <= start < stop <= SIDE):
        raise ValueError('Invalid row range')
    dx, dy = PAN if stage == 'pan' else (0, 0)
    y = np.arange(start, stop, dtype=np.int64)[:, None] + dy
    x = np.arange(SIDE, dtype=np.int64)[None, :] + dx
    valid = (x >= 0) & (x < SIDE) & (y >= 0) & (y < SIDE)
    result = np.empty((stop-start, SIDE, 4), np.uint8)
    if name.startswith('scalar_'):
        gray = np.array([0, 64, 128, 255], np.uint8)[_levels(x, y)]
        result[..., :3] = gray[..., None]
        result[..., 3] = 255
    else:
        result[..., 0] = (3*x + 5*y + 17) % 256
        result[..., 1] = (7*x + 11*y + 43) % 256
        result[..., 2] = ((x // 17) ^ ((y // 31) * 29)) % 256
        result[..., 3] = ((x // 64 + y // 32) % 4) * 85
    result[~valid] = (0, 0, 0, 255)
    return result


def quality_result(name, stage, image):
    """Check every channel of every pixel with bounded temporary memory."""
    _validate(name, stage)
    if image.shape != (SIDE, SIDE, 4) or image.dtype != np.uint8:
        raise ValueError('Full 4096x4096 uint8 RGBA frame required')
    maximum = bad = 0
    tolerance = 1 if name.startswith('scalar_') else 0
    for start in range(0, SIDE, 64):
        expected = expected_rows(name, stage, start, min(start+64, SIDE))
        difference = np.abs(image[start:start+64].astype(np.int16)-expected.astype(np.int16))
        maximum = max(maximum, int(difference.max()))
        invalid = np.any(difference[..., :3] > tolerance, axis=-1) | (difference[..., 3] != 0)
        bad += int(np.count_nonzero(invalid))
    return dict(passed=bad == 0, checked_pixels=SIDE*SIDE, excluded_pixels=0,
                bad_pixels=bad, max_abs_channel_error=maximum, rgb_tolerance=tolerance,
                alpha_tolerance=0)


def residency_result(delta):
    """Fail closed on missing, reset, malformed, or forbidden resident work."""
    if not isinstance(delta, dict):
        return dict(passed=False, invalid=['counter_delta'], nonzero=[])
    invalid = [key for key in RESIDENT_ZERO if type(delta.get(key)) is not int or delta[key] < 0]
    nonzero = [key for key in RESIDENT_ZERO if key not in invalid and delta[key] != 0]
    for key in ('draw_calls', 'vk_queue_submits'):
        if type(delta.get(key)) is not int or delta[key] <= 0:
            invalid.append(key)
    return dict(passed=not invalid and not nonzero, invalid=invalid, nonzero=nonzero,
                quality_readback_waits_excluded=True)


def case_contract(name):
    _validate(name)
    return dict(case=name, image_shape=[SIDE, SIDE], framebuffer_shape=[SIDE, SIDE, 4],
                logical_canvas_size=[64, 64], stages=list(STAGES), pan=list(PAN),
                viewbox=dict(border_width=0, margin=0, padding=0),
                interpolation=name.rsplit('_', 1)[1], texture_format='auto',
                clim=[0, 1] if name.startswith('scalar_') else 'auto', cmap='grays',
                method='subdivide', grid=[1, 1], blend=False, depth_test=False,
                camera=dict(rect=[0, 0, SIDE, SIDE], aspect=1, flip=[False, True, False]),
                comparison=dict(full_frame_exact_original=True, excluded_pixels=0,
                                analytic_rgb_tolerance=1 if name.startswith('scalar_') else 0,
                                analytic_alpha_tolerance=0),
                resident_zero=list(RESIDENT_ZERO), performance_qualified=False)


def record_commands(batch, commands, shaders):
    """The pinned VisPy 0.17 program emits separate shader DATA commands."""
    for row in batch:
        commands.append(freeze(row))
        if row[0] == 'DATA' and isinstance(row[3], str):
            shaders[str(row[1])] = row[3]


def rect_bounds(rect):
    """Rect coordinates may be NumPy scalars; save ordinary JSON numbers."""
    return [float(value) for value in (rect.left, rect.bottom, rect.width, rect.height)]


def assert_framebuffer_draws(commands, framebuffer_id):
    """CURRENT resets the GLIR FBO binding even when the context is unchanged."""
    active = False
    draws = 0
    for row in commands:
        if row[0] == 'CURRENT':
            active = False
        elif row[0] == 'FRAMEBUFFER':
            active = row[1] == framebuffer_id and row[2] is True
        elif row[0] == 'DRAW':
            assert active, 'Draw does not bind the persistent quality framebuffer after CURRENT'
            draws += 1
    assert draws > 0, 'No actual GLIR draw for this stage'
    return draws


def render(name, backend, capture):
    """Stream four frames to capture(stage, rgba, metadata) before validation.

    One persistent RGBA8 framebuffer and one ImageVisual survive all stages.
    The camera's public pan method changes only the view, never the source data.
    """
    spec = case_contract(name)
    from vispy import scene, gloo
    dawn = None
    if backend == 'dawn_headless':
        from vispy import _dawn as dawn
    elif backend != 'pyqt6':
        raise ValueError('Explicit original OpenGL or candidate Dawn backend required')
    canvas = scene.SceneCanvas(app=backend, size=(64, 64), show=backend == 'pyqt6',
                               decorate=False, bgcolor=(0, 0, 0, 1), config={'samples': 0})
    commands, shaders = [], {}
    original = canvas.context.shared.parser.parse
    def log(batch):
        record_commands(batch, commands, shaders)
        return original(batch)
    canvas.context.shared.parser.parse = log
    pushed = False
    try:
        if backend == 'pyqt6':
            canvas.app.native.setQuitOnLastWindowClosed(False)
            canvas._backend._vispy_warmup()
        assert tuple(canvas.size) == (64, 64), 'Logical camera mapping requires the declared canvas size'
        view = canvas.central_widget.add_view(**spec['viewbox'])
        for rect in (view.rect, view.inner_rect):
            assert rect_bounds(rect) == [0, 0, 64, 64]
        view.camera = scene.cameras.PanZoomCamera(**spec['camera'])
        visual = scene.visuals.Image(input_data(name), parent=view.scene,
                                     **{key: spec[key] for key in
                                        ('interpolation', 'texture_format', 'clim', 'cmap', 'method', 'grid')})
        visual.set_gl_state(blend=False, depth_test=False, cull_face=False)
        target = gloo.Texture2D(shape=(SIDE, SIDE, 4), format='rgba', internalformat='rgba8')
        framebuffer = gloo.FrameBuffer(color=target)
        canvas.push_fbo(framebuffer, (0, 0), canvas.size)
        pushed = True
        # SceneCanvas.push_fbo uses its csize as both the covered canvas region
        # and the FBO size. Explicitly configure the public TransformSystem for
        # a differently sized target, rather than leaving a 64-pixel image in
        # the corner of a 4096-pixel viewport.
        canvas.transforms.configure(viewport=(0, 0, SIDE, SIDE),
                                    fbo_size=(SIDE, SIDE),
                                    fbo_rect=(0, 0, *canvas.physical_size))
        mapped = canvas.transforms.get_transform('canvas', 'framebuffer').map([[0, 0], [64, 64]])
        np.testing.assert_allclose(mapped[:, :2], [[0, SIDE], [SIDE, 0]], rtol=0, atol=1e-9)
        stages = {}
        for stage in STAGES:
            first = len(commands)
            before = dict(dawn.probe()) if dawn else None
            if stage == 'pan':
                view.camera.pan(PAN)
            elif stage == 'return':
                view.camera.pan(tuple(-value for value in PAN))
            # draw_visual makes the context current again. GLIR CURRENT resets
            # the FBO binding, so rebind the same owned object for every draw.
            framebuffer.activate()
            gloo.clear(color=(0, 0, 0, 1), depth=False, stencil=False)
            canvas.draw_visual(canvas.scene)
            rgba = np.array(framebuffer.read(alpha=True), copy=True)
            after = dict(dawn.probe()) if dawn else None
            delta = ({key: after[key]-value for key, value in before.items()
                      if type(value) is int and type(after.get(key)) is int} if dawn else None)
            rect = view.camera.rect
            row = dict(command_start=first, command_stop=len(commands),
                       camera_rect=rect_bounds(rect),
                       source_texture_id=visual._texture.id, target_texture_id=target.id,
                       framebuffer_id=framebuffer.id,
                       counter_before=before, counter_after=after, counter_delta=delta,
                       commands=commands[first:], shaders=dict(shaders))
            # Full command/shader evidence is already persisted per stage.
            stages[stage] = {key: value for key, value in row.items() if key not in ('commands', 'shaders')}
            capture(stage, rgba, row)
            del rgba
        return commands, shaders, dict(spec, stages_observed=stages,
                                       physical_canvas_size=list(canvas.physical_size),
                                       canvas_to_framebuffer_corners=mapped.tolist(),
                                       source_texture_shape=list(visual._texture.shape))
    finally:
        try:
            if pushed:
                canvas.pop_fbo()
        finally:
            canvas.context.shared.parser.parse = original
            canvas.close()
