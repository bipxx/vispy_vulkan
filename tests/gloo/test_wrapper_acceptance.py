# SPDX-License-Identifier: AGPL-3.0-only
"""Public wrapper contracts independent of the native backend."""

import pytest

from vispy import gloo
from vispy.gloo import context


def test_get_state_presets_contents():
    assert gloo.get_state_presets()['translucent']['blend_func'] == (
        'src_alpha', 'one_minus_src_alpha', 'zero', 'one',
    )


def test_get_state_presets_survives_caller_mutation():
    presets = gloo.get_state_presets()
    presets['opaque']['blend'] = True
    del presets['opaque']
    assert gloo.get_state_presets()['opaque']['blend'] is False


def test_set_hint_enqueues_public_request(monkeypatch):
    monkeypatch.setattr(context, 'canvasses', [])
    canvas = context.FakeCanvas()
    gloo.set_hint('line_smooth_hint', 'nicest')
    assert canvas.context.glir.clear() == [
        ('FUNC', 'glHint', 'line_smooth_hint', 'nicest'),
    ]


@pytest.mark.parametrize(('value', 'expected'), [
    (True, (1., False)),
    (False, (0., False)),
    (.25, (.25, False)),
    ((.25, True), (.25, True)),
])
def test_set_state_sample_coverage_sets_parameters(monkeypatch, value, expected):
    monkeypatch.setattr(context, 'canvasses', [])
    canvas = context.FakeCanvas()
    gloo.set_state(sample_coverage=value)
    assert canvas.context.glir.clear() == [
        ('FUNC', 'glSampleCoverage', *expected),
    ]
