# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""Browser-to-kernel acceptance for a disposable JupyterLab notebook."""

import io
import os
from urllib.parse import urlparse
from uuid import uuid4

import pytest

NOTEBOOK_URL = os.getenv("VISPY_TEST_RFB_NOTEBOOK_URL")
pytestmark = [
    pytest.mark.needs_window,
    pytest.mark.gpu,
    pytest.mark.skipif(not NOTEBOOK_URL, reason="needs-window: dedicated local JupyterLab notebook"),
]

# Execute the same cell on both visits. The notebook kernel must be retained
# across frontend reconnect so the second visit can check the old resources.
CELL = """
from IPython.display import display
from ipywidgets import Button, Label, VBox
from vispy import _dawn, app, gloo

reopened = globals().get('rfb_case') == CASE_ID
if 'rfb_canvas' in globals():
    rfb_timer.stop()
    rfb_canvas.close()
    assert not rfb_timer.running
    assert rfb_timer._backend._task is None
    assert rfb_canvas.native._dawn_canvas_id == 0
    assert rfb_canvas.native.get_frame() is None
    _dawn.process_events()
    assert _dawn.probe()['canvas_texture_bytes'] == rfb_baseline
if not reopened:
    rfb_baseline = _dawn.probe()['canvas_texture_bytes']

rfb_case = CASE_ID
rfb_canvas = app.Canvas(app='jupyter_rfb', size=(120, 80))
rfb_status = Label(value='reopened clean' if reopened else 'first connection')
rfb_timer = app.Timer(app=rfb_canvas.app, interval=1.5, iterations=1)
rfb_timer.connect(lambda event: rfb_canvas.update())

@rfb_canvas.events.draw.connect
def rfb_draw(event):
    gloo.clear(color=(0, 1, 0, 1) if reopened else (1, 0, 0, 1))

@rfb_canvas.events.key_press.connect
def rfb_key(event):
    if event.text == 's':
        rfb_canvas.native.css_width = '144px'
    rfb_status.value = 'key ' + event.text

@rfb_canvas.events.mouse_wheel.connect
def rfb_wheel(event):
    rfb_status.value = 'wheel up' if event.delta[1] > 0 else 'wheel down'

rfb_queue = Button(description='Queue delayed frame')
def rfb_schedule(button):
    rfb_timer.start()
    rfb_status.value = 'redraw queued'
rfb_queue.on_click(rfb_schedule)
rfb_cleanup = Button(description='Close RFB')
def rfb_close(button):
    rfb_timer.stop()
    rfb_canvas.close()
    rfb_status.value = 'closed'
rfb_cleanup.on_click(rfb_close)
display(VBox([rfb_canvas.native, rfb_status, rfb_queue, rfb_cleanup]))
""".strip()


@pytest.fixture
def browser():
    assert urlparse(NOTEBOOK_URL).hostname in ("localhost", "127.0.0.1", "::1")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            yield browser
        finally:
            browser.close()


def open_notebook(browser, ratio, case_id):
    context = browser.new_context(device_scale_factor=ratio, permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    page.set_default_timeout(15000)
    page.goto(NOTEBOOK_URL)
    editor = page.locator(".jp-CodeCell .cm-content").first
    editor.click()
    page.keyboard.press("ControlOrMeta+a")
    page.evaluate("(code) => navigator.clipboard.writeText(code)", CELL.replace("CASE_ID", repr(case_id)))
    page.keyboard.press("ControlOrMeta+v")
    page.keyboard.press("Shift+Enter")
    canvas = page.locator(".jp-OutputArea-output canvas").first
    canvas.wait_for()
    return context, page, canvas


def check_browser_pixels(canvas, rgb, ratio, size=(120, 80)):
    from PIL import Image

    assert canvas.evaluate("canvas => window.devicePixelRatio") == ratio
    # Frames arrive asynchronously over the widget connection.
    from time import monotonic

    deadline = monotonic() + 15
    while True:
        image = Image.open(io.BytesIO(canvas.screenshot(scale="device"))).convert("RGB")
        w, h = image.size
        if (w, h) == (size[0] * ratio, size[1] * ratio) and image.getpixel((w // 2, h // 2)) == rgb:
            assert canvas.evaluate("canvas => [canvas.width, canvas.height]") == [w, h]
            assert image.getpixel((w // 4, h // 4)) == rgb
            return
        assert monotonic() < deadline, (image.size, image.getpixel((w // 2, h // 2)))


def exercise_input(page, canvas):
    canvas.click()
    page.keyboard.press("a")
    page.get_by_text("key a", exact=True).wait_for()
    canvas.hover()
    page.mouse.wheel(0, -120)
    page.get_by_text("wheel up", exact=True).wait_for()


def test_rfb_browser_pixels_and_input_at_two_pixel_ratios(browser):
    red = (255, 0, 0)
    context, page, canvas = open_notebook(browser, 1, uuid4().hex)
    try:
        page.get_by_text("first connection", exact=True).wait_for()
        check_browser_pixels(canvas, red, 1)
        exercise_input(page, canvas)

        # Change the same live frontend's DPR. A wire keypress also changes
        # the widget's CSS width so its ResizeObserver must send new geometry.
        session = context.new_cdp_session(page)
        session.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280, "height": 720, "deviceScaleFactor": 2, "mobile": False,
        })
        page.keyboard.press("s")
        page.get_by_text("key s", exact=True).wait_for()
        check_browser_pixels(canvas, red, 2, size=(144, 80))
        exercise_input(page, canvas)
        page.get_by_role("button", name="Close RFB").click()
        page.get_by_text("closed", exact=True).wait_for()
    finally:
        context.close()

def test_rfb_disconnect_during_queued_frame_and_reopen(browser):
    case_id = uuid4().hex
    context, page, canvas = open_notebook(browser, 1, case_id)
    try:
        check_browser_pixels(canvas, (255, 0, 0), 1)
        page.get_by_role("button", name="Queue delayed frame").click()
        page.get_by_text("redraw queued", exact=True).wait_for()
        page.keyboard.press("ControlOrMeta+s")
    finally:
        context.close()
    context, page, canvas = open_notebook(browser, 2, case_id)
    try:
        page.get_by_text("reopened clean", exact=True).wait_for()
        check_browser_pixels(canvas, (0, 255, 0), 2)
        exercise_input(page, canvas)
        page.get_by_role("button", name="Close RFB").click()
        page.get_by_text("closed", exact=True).wait_for()
    finally:
        context.close()
