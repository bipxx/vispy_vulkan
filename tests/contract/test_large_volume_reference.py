# SPDX-License-Identifier: AGPL-3.0-only
"""Portable references bind every full-sized workload and actual source factory."""
import json
import pytest
from tools import large_volume_wheel_suite as suite

REFERENCE_SHA256='af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac'
REFERENCE=suite.ROOT/'tests/reference/large-volume-opengl'


@pytest.mark.parametrize('name',suite.CASES)
def test_all_large_volume_original_artifacts_and_controls_are_immutable(name):
    folder=suite.load_reference(REFERENCE,REFERENCE_SHA256,name)
    params=json.loads((folder/'parameters.json').read_bytes())
    assert params['workload_sha256']==suite.case_contract(name)['workload_sha256']
    assert params['workload']==json.loads(json.dumps(suite.case_contract(name)['workload']))
    assert params['source_texture_shape']==params['workload']['shape']+[1]
    assert params['actual_physical_size']==params['workload']['viewport']
    assert params['stages']==['initial','repeat','probe7','probe73']


@pytest.mark.parametrize('mutation',('digest','parent','source'))
def test_large_volume_reference_rejects_digest_parent_and_factory_drift(tmp_path,mutation):
    manifest=json.loads((REFERENCE/'manifest.json').read_bytes())
    if mutation=='parent':manifest['status']='FAILED_REQUIRED_LARGE_VOLUMES'
    if mutation=='source':manifest['sources_sha256']['tools/benchmark_frames.py']='0'*64
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest),encoding='utf-8')
    digest='0'*64 if mutation=='digest' else suite.sha(path)
    with pytest.raises(AssertionError):suite.load_reference(tmp_path,digest,suite.CASES[0])
