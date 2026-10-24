"""Real Qt virtual callbacks must surface renderer errors without process abort."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gpu
@pytest.mark.parametrize('event_entry', ['process_events', 'run'])
def test_native_draw_failure_survives_qt_callback_boundary(event_entry):
    # A child lets pytest report the Windows PyQt process-abort regression.
    code = r'''
import json
from vispy import _dawn, app, gloo
api = __import__('os').environ.get('QT_API', 'pyqt6')
application = app.use_app(api)
canvas = app.Canvas(app=api, size=(24, 24), show=False)
canvas.events.draw.ignore_callback_errors = False
def invalid_draw(event):
    gloo.set_line_width(float('nan'))
    gloo.clear()
canvas.events.draw.connect(invalid_draw)
seen = None
try:
    if ENTRY == 'run':
        application.backend_module.QtCore.QTimer.singleShot(0, canvas.show)
        application.run()
    else:
        canvas.show()
        for _ in range(50):
            application.process_events()
except RuntimeError as error:
    seen = str(error)
assert seen is not None and 'glLineWidth' in seen, seen
canvas.close()
good_draws = []
good = app.Canvas(app=api, size=(24, 24), show=False)
def good_draw(event):
    good_draws.append(True)
    gloo.set_clear_color((0, 1, 0, 1))
    gloo.clear()
good.events.draw.connect(good_draw)
good.show()
# X11 mapping and the first paint arrive asynchronously. Require a real draw
# before checking its unchanged exact pixel result.
import time
deadline = time.monotonic() + 3.0
while time.monotonic() < deadline:
    application.process_events()
    if good_draws and good.native.isVisible():
        break
    time.sleep(0.005)
assert good_draws and good.native.isVisible(), 'new canvas received no visible draw'
pixels = _dawn.read_pixels(int(good.native._dawn_canvas_id), 0, 0, 4, 4, True)
assert pixels.shape == (4, 4, 4) and (pixels[..., 1] == 255).all(), pixels
good.close()
application.process_events()
print('callback boundary proof', json.dumps({'entry': ENTRY, 'error': seen, 'new_canvas': 'green'}))
'''
    environment = dict(os.environ, QT_API=os.environ.get('QT_API', 'pyqt6'))
    result = subprocess.run(
        [sys.executable, '-X', 'faulthandler', '-c', f'ENTRY = {event_entry!r}\n' + code],
        cwd=Path(__file__).resolve().parents[2], env=environment,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
    )
    assert result.returncode == 0, result.stdout
    assert 'callback boundary proof' in result.stdout, result.stdout
    assert 'Dawn Qt paintEvent failed' in result.stdout, result.stdout
    print(result.stdout)
