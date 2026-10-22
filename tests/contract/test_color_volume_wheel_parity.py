# SPDX-License-Identifier: AGPL-3.0-only
"""24 required installed-wheel color-volume cases for the admitted hardware cell."""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import color_volume_wheel_suite as suite

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]
REFERENCE_SHA256='c8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337'


def assert_successful_parent(return_code,manifest):
    assert return_code==0 and manifest.get('status')=='PASS_ALL_CANDIDATE_COLOR_VOLUMES',manifest.get('error',manifest)
    assert not manifest.get('error')
    assert manifest.get('opacity_controls_passed') is True
    assert manifest.get('required_cases_without_verified_result')==[]


@pytest.fixture(scope='module')
def qualified_color_suite():
    assert sys.platform=='win32' and sys.implementation.name=='cpython' and sys.version_info[:3]==(3,12,8), 'Only the admitted Windows CPython3.12.8 cell is qualified by this packet'
    wheel=os.environ.get('VISPY_TEST_WHEEL')
    assert wheel,'An installed-wheel artifact is required; no missing-artifact skip'
    reference=Path(os.environ.get('VISPY_COLOR_VOLUME_REFERENCE',suite.ROOT/'tests/reference/color-volume-opengl')).resolve()
    output=Path(os.environ.get('VISPY_COLOR_VOLUME_EVIDENCE',suite.ROOT/'build/evidence/color-volume-wheel')).resolve()
    args=SimpleNamespace(kind='candidate',wheel=Path(wheel).resolve(),repository=suite.ROOT,
        output=output,reference=reference,reference_sha256=REFERENCE_SHA256)
    return_code=suite.run(args)
    for n in suite.CASES:suite.load_reference(reference,REFERENCE_SHA256,n)
    return output,json.loads((output/'manifest.json').read_bytes()),return_code


@pytest.mark.parametrize('name',suite.CASES)
def test_installed_color_volume_matches_original_every_pixel(name,qualified_color_suite):
    output,manifest,return_code=qualified_color_suite
    assert name in manifest['workers'],manifest.get('error',manifest)
    row=manifest['workers'][name]
    worker=json.loads((output/name/'result.json').read_bytes())
    assert row['child_waited'] and row['actual_worker_terminal']['terminal']
    assert row['report_sha256']==suite.sha(output/name/'result.json')
    assert row['process_exit']==worker['process_exit']==0,worker.get('error',worker)
    assert worker['status']=='PASS_CANDIDATE_COLOR_VOLUME'
    assert worker['compared_pixels']==9216 and worker['excluded_pixels']==0
    assert worker['cleanup_passed'] and worker['native_origins_verified']
    assert len(worker['shutdown_zeros'])==8 and set(worker['shutdown_zeros'].values())=={0}
    assert_successful_parent(return_code,manifest)
