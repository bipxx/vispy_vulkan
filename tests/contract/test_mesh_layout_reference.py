# SPDX-License-Identifier: AGPL-3.0-only
"""All thirteen required original scenes remain byte-bound and portable."""
import json
from pathlib import Path
import pytest
from tools.fixture_mesh_layout_extensions import CASES,case_contract
from tools.mesh_layout_reference import REFERENCE,load_case,load_manifest,read_record


def test_portable_packet_retains_all_thirteen_and_historical_failure_scope():
    manifest=load_manifest()
    assert len(CASES)==len(manifest['fixtures'])==13
    assert 'axes_colorbar' in manifest['fixtures']
    assert manifest['historical_candidate_cases_passed']==12
    assert manifest['historical_required_refusal']=='axes_colorbar'
    assert not manifest['full_suite_qualified']
    assert set(manifest['licenses'])=={'LICENSE','LICENSE-BSD'}


@pytest.mark.parametrize('name',CASES)
def test_every_original_frame_atlas_and_contract_is_admitted(name):
    image,params,extras=load_case(name)
    assert image.shape==(160,224,4) and not image.flags.writeable
    for key,value in case_contract(name).items():assert params[key]==value
    assert set(extras)==set(params['cpu_atlases'])
    assert all(not array.flags.writeable for array in extras.values())


def test_manifest_and_payload_changes_are_required_failures(tmp_path):
    (tmp_path/'manifest.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='manifest differs'):load_manifest(tmp_path)
    (tmp_path/'frame.npy').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Reference bytes differ'):
        read_record(tmp_path,dict(file='frame.npy',sha256='0'*64))


def test_unknown_case_cannot_silently_select_another_scene():
    with pytest.raises(ValueError,match='Unknown required'):load_case('mesh_missing')
