# SPDX-License-Identifier: AGPL-3.0-only
"""The admitted cell must prepare an exact original and retain all five cases."""
import hashlib
import io
import json
from pathlib import Path
import pytest
from tools import prepare_glue_host_cell as cell


@pytest.fixture
def admitted(monkeypatch):
    monkeypatch.setattr(cell.platform,'system',lambda:'Windows')
    monkeypatch.setattr(cell.platform,'machine',lambda:'AMD64')
    monkeypatch.setattr(cell.platform,'python_version',lambda:'3.12.8')
    return dict(host='glue_vispy_viewers',cell=dict(platform='windows',python='3.12.8',binding='pyqt6'),
        upstream_fixture_status='passed',upstream_cases=list(cell.CASES),
        upstream_wheel=dict(filename=cell.UPSTREAM_FILENAME,sha256=cell.UPSTREAM_SHA256,url=cell.UPSTREAM_URL))


def test_existing_pinned_wheel_is_used_without_download(tmp_path,monkeypatch,admitted):
    body=b'synthetic original wheel';digest=hashlib.sha256(body).hexdigest()
    monkeypatch.setattr(cell,'UPSTREAM_SHA256',digest);admitted['upstream_wheel']['sha256']=digest
    wheel=tmp_path/cell.UPSTREAM_FILENAME;wheel.write_bytes(body)
    monkeypatch.setattr(cell.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Unexpected download'))
    result=cell.prepare(admitted,tmp_path/'evidence',supplied_wheel=wheel)
    assert result['VISPY_GLUE_UPSTREAM_WHEEL']==str(wheel.resolve())
    assert not Path(result['VISPY_GLUE_WHEEL_EVIDENCE']).exists()
    saved=json.loads((tmp_path/'evidence/preparation.json').read_bytes())
    assert saved['downloaded'] is False and not saved['candidate_qualified'] and not saved['release_qualified']


def test_download_uses_only_the_locked_original_artifact(tmp_path,monkeypatch,admitted):
    body=b'synthetic downloaded wheel';digest=hashlib.sha256(body).hexdigest();calls=[]
    monkeypatch.setattr(cell,'UPSTREAM_SHA256',digest);admitted['upstream_wheel']['sha256']=digest
    def fetch(url,timeout):calls.append((url,timeout));return io.BytesIO(body)
    monkeypatch.setattr(cell.urllib.request,'urlopen',fetch)
    result=cell.prepare(admitted,tmp_path/'evidence')
    assert calls==[(cell.UPSTREAM_URL,60)]
    assert Path(result['VISPY_GLUE_UPSTREAM_WHEEL']).read_bytes()==body


@pytest.mark.parametrize('change',('missing_case','failed_upstream','wrong_cell','wrong_wheel'))
def test_unadmitted_input_fails_before_evidence_or_network(tmp_path,monkeypatch,admitted,change):
    if change=='missing_case':admitted['upstream_cases'].pop()
    elif change=='failed_upstream':admitted['upstream_fixture_status']='failed'
    elif change=='wrong_cell':admitted['cell']['binding']='pyqt5'
    else:admitted['upstream_wheel']['sha256']='0'*64
    monkeypatch.setattr(cell.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Unexpected download'))
    with pytest.raises(AssertionError):cell.prepare(admitted,tmp_path/'evidence')
    assert not (tmp_path/'evidence').exists()


def test_corrupt_supplied_wheel_cannot_produce_preparation_pass(tmp_path,admitted):
    wheel=tmp_path/cell.UPSTREAM_FILENAME;wheel.write_bytes(b'wrong bytes')
    with pytest.raises(AssertionError):cell.prepare(admitted,tmp_path/'evidence',supplied_wheel=wheel)
    assert not (tmp_path/'evidence/preparation.json').exists()
    assert wheel.read_bytes()==b'wrong bytes'


def test_other_runtime_patch_version_is_not_the_admitted_cell(tmp_path,monkeypatch,admitted):
    monkeypatch.setattr(cell.platform,'python_version',lambda:'3.12.9')
    with pytest.raises(AssertionError):cell.prepare(admitted,tmp_path/'evidence')
    assert not (tmp_path/'evidence').exists()


def test_published_upstream_admission_binds_all_five_exact_fixture_artifacts():
    root=Path(__file__).resolve().parents[2]
    admission=json.loads((root/'compat/qualifications/glue_vispy_viewers/windows/3.12.8/pyqt6/admission.json').read_bytes())
    reference_path=root/admission['reference_manifest']
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==admission['reference_manifest_sha256']
    reference=json.loads(reference_path.read_bytes())
    assert reference['errors']==[] and reference['provenance']['kind']=='upstream'
    assert set(reference['fixtures'])==set(admission['upstream_cases'])==set(cell.CASES)
    assert reference['upstream_only'] and not reference['candidate_qualified'] and not admission['candidate_qualified']
    for case,fixture in reference['fixtures'].items():
        assert fixture['comparison']==dict(exact=True,excluded_pixels=0,shape=[128,128,4],dtype='uint8')
        for role in ('rgba','filtered_glir','expanded_shaders','parameters_artifact'):
            assert hashlib.sha256((reference_path.parent/fixture[role]['file']).read_bytes()).hexdigest()==fixture[role]['sha256']
    for file,digest in admission['fixture_sources_sha256'].items():
        assert hashlib.sha256((root/file).read_bytes()).hexdigest()==digest
