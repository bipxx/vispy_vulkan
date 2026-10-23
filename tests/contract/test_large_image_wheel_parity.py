# SPDX-License-Identifier: AGPL-3.0-only
"""Mandatory full4096 installed-wheel graphics regressions for the admitted cell."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from tools import large_image_wheel_suite as suite

pytestmark = [pytest.mark.gpu, pytest.mark.wheel]
REFERENCE_SHA256 = 'ace47caea32759727170debd5a08db2c3255b29296873090290f12a12670c4d2'


@pytest.fixture(scope='module')
def qualified_large_image_suite():
    assert sys.platform == 'win32' and sys.implementation.name == 'cpython' and sys.version_info[:3] == (3, 12, 8)
    wheel = os.environ.get('VISPY_TEST_WHEEL')
    assert wheel, 'The pinned installed-wheel artifact is required; no missing-artifact skip'
    reference = Path(os.environ.get('VISPY_LARGE_IMAGE_REFERENCE', suite.ROOT/'tests/reference/large-image-opengl')).resolve()
    output = Path(os.environ.get('VISPY_LARGE_IMAGE_EVIDENCE', suite.ROOT/'build/evidence/large-image-wheel')).resolve()
    args = SimpleNamespace(kind='candidate', wheel=Path(wheel).resolve(), repository=suite.ROOT,
                           output=output, reference=reference, reference_sha256=REFERENCE_SHA256)
    code = suite.run(args)
    return output, json.loads((output/'manifest.json').read_bytes()), code


@pytest.mark.parametrize('name', suite.CASES)
def test_installed_large_image_full_frame_pan_and_residency(name, qualified_large_image_suite):
    output, manifest, code = qualified_large_image_suite
    assert code == 0, manifest.get('error', manifest)
    suite.assert_successful_parent(manifest, 'candidate')
    row = manifest['workers'][name]
    worker = json.loads((output/name/'result.json').read_bytes())
    assert row['report_sha256'] == suite.sha(output/name/'result.json')
    assert row['process_exit'] == worker['process_exit'] == 0, worker.get('error', worker)
    assert worker['status'] == 'PASS_CANDIDATE_LARGE_IMAGE'
    assert worker['compared_pixels'] == 67108864 and worker['excluded_pixels'] == 0
    assert worker['cleanup_passed'] and worker['native_origins_verified']
    assert len(worker['shutdown_zeros']) == 8 and set(worker['shutdown_zeros'].values()) == {0}
    assert set(worker['stages']) == set(suite.STAGES)
    for stage, checks in worker['stages'].items():
        assert checks['analytic']['passed'] and checks['exact_original']
        assert checks['glir_draws_on_owned_framebuffer'] > 0
        if stage != 'baseline':
            assert checks['residency']['passed']
