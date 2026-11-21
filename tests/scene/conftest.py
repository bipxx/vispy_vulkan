# SPDX-License-Identifier: AGPL-3.0-only
import numpy as np
import pytest

from vispy import scene
from vispy.app import Application, _default_app


@pytest.fixture
def canvas_factory(monkeypatch):
    app = Application('dawn_headless')
    monkeypatch.setattr(_default_app, 'default_app', app)
    canvases = []

    def create(size=(100, 100)):
        canvas = scene.SceneCanvas(app=app, size=size, dpi=96, bgcolor='black',
                                   show=False, decorate=False, config={'samples': 0})
        canvases.append(canvas)
        return canvas

    yield create
    for canvas in reversed(canvases):
        canvas.close()


@pytest.fixture
def draw():
    def render(canvas):
        return np.array(canvas.render(alpha=False), copy=True)
    return render
