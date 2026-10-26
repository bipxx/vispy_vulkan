# SPDX-License-Identifier: AGPL-3.0-only
"""The finite observed capture workflow must prove every selected mode."""
import pytest

from tools.tkinter_capture_scenario import run
from tools.no_opengl.functional import CAPTURE_BRANCHES, validate_capture_result

pytestmark = pytest.mark.gpu


def test_real_tk_capture_observer_scenario():
    verdict = validate_capture_result(run())
    assert verdict['status'] == 'PASS_FUNCTIONAL_RESULT'
    assert verdict['branch_ids'] == sorted(CAPTURE_BRANCHES.values())
    assert verdict['qualified'] is False
