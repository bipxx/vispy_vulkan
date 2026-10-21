import pytest

import vispy
from vispy import app
from vispy import _dawn

pytestmark = pytest.mark.gpu


def test_windows_device_is_vulkan_hardware():
    info = _dawn.device_info()
    print("backend", info["backend"])
    print("adapter_type", info["adapter_type"])
    print("device", info["device"])
    print("software", info["software"])
    print("driver", info["driver"])
    print("revision", info["revision"])
    assert info["ok"], info["error"]
    assert info["backend"] == "Vulkan"
    assert info["adapter_type"] != "cpu"
    assert info["software"] is False
    assert vispy.__version__ == "0.17.0+vulkan.1"


def test_device_info_recovers_lost_device_once_and_reuses_it():
    info = _dawn.device_info()
    assert info["ok"] is True, info["error"]
    before = _dawn.probe()
    loss_count = int(info["loss_count"])
    _dawn.lose_device()
    recovered = _dawn.device_info()
    after = _dawn.probe()
    print("recovered device", recovered["ok"], recovered["loss_count"],
          before["device_generation"], after["device_generation"])
    assert recovered["ok"] is True, recovered["error"]
    assert recovered["software"] is False
    assert int(recovered["loss_count"]) == loss_count + 1
    assert after["device_generation"] > before["device_generation"]

    # A successful creation advances this counter; observation must reuse it.
    for _ in range(3):
        repeated = _dawn.device_info()
        assert repeated["ok"] is True, repeated["error"]
        assert int(repeated["loss_count"]) == loss_count + 1
        assert _dawn.probe()["device_generation"] == after["device_generation"]

    canvas = app.Canvas(app="dawn_headless", size=(2, 2), show=False)
    try:
        assert _dawn.frame_ready(canvas._backend._dawn_canvas_id) is True
        assert _dawn.probe()["device_generation"] == after["device_generation"]
        assert int(_dawn.device_info()["loss_count"]) == loss_count + 1
    finally:
        canvas.close()
