# SPDX-License-Identifier: AGPL-3.0-only
"""The observed workflow must exercise real Tk and both native flush routes."""
import pytest

from tools.tkinter_state_scenario import run

pytestmark = pytest.mark.gpu


def test_real_tk_state_observer_scenario():
    result = run()
    assert result['status'] == 'PASS'
    assert [item['route'] for item in result['submissions']] == ['gloo.flush', 'glFlush']
