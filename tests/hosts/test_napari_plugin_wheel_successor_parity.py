# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of test_napari_plugin_wheel_parity.py: the five mandatory installed-wheel plugin event and
retirement workflows on the napari release that tools/napari_plugin_wheel_suite_successor.py locks (0.10.0).

The fresh upstream run must reproduce that release's overlay packet exactly before the candidate runs. Evidence goes
to VISPY_NAPARI_EVIDENCE (tools/napari_host_packets.evidence_dir) and must be fresh.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import napari_plugin_wheel_suite_successor as suite
from tools.napari_host_packets import evidence_dir

pytestmark=[pytest.mark.gpu,pytest.mark.wheel]


@pytest.fixture(scope='module')
def qualified_suite():
    original=os.environ.get('VISPY_NAPARI_PLUGIN_UPSTREAM_WHEEL')
    candidate=os.environ.get('VISPY_TEST_WHEEL')
    assert original and candidate, 'Both original and candidate VisPy wheel artifacts required'
    output=evidence_dir('napari-plugin-wheel-successor-suite',suite.HOST_VERSIONS['napari']).resolve()
    assert not output.exists(), 'Preserve every earlier plugin attempt'
    output.mkdir(parents=True)
    repository=Path(os.environ.get('VISPY_NAPARI_PLUGIN_REPOSITORY',suite.ROOT)).resolve()
    upstream=SimpleNamespace(kind='upstream',wheel=Path(original).resolve(),output=output/'upstream',
        repository=repository,reference=None,reference_sha256=None)
    assert suite.run(upstream)==0, 'Fresh original failure blocks candidate work'
    digest=suite.sha(upstream.output/'manifest.json')
    verified=suite.verify_saved(upstream.output,digest,upstream.wheel,'upstream')
    suite.write(output/'upstream-verification.json',verified)
    run=SimpleNamespace(kind='candidate',wheel=Path(candidate).resolve(),output=output/'candidate',
        repository=repository,reference=upstream.output,reference_sha256=digest)
    code=suite.run(run)
    verified=suite.verify_saved(run.output,suite.sha(run.output/'manifest.json'),run.wheel,'candidate',
        reference=upstream.output,reference_sha256=digest)
    assert code==(1 if verified['failed'] else 0)
    suite.write(output/'candidate-verification.json',verified)
    return json.loads((run.output/'manifest.json').read_bytes())


@pytest.mark.parametrize('name',suite.CASES)
def test_plugin_event_and_retirement_workflow_matches_original_exactly(name,qualified_suite):
    row=qualified_suite['workers'][name]
    assert row['process_exit']==row['worker']['process_exit']==0,row['worker'].get('error',row['worker']['status'])
    assert row['worker']['status']=='PASS_CANDIDATE_PLUGIN_CASE'
    assert row['worker']['compared_pixels']==suite.SIZE[0]*suite.SIZE[1] and row['worker']['excluded_pixels']==0
    assert row['worker']['host_versions']==suite.HOST_VERSIONS
