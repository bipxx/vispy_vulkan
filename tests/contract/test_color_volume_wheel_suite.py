# SPDX-License-Identifier: AGPL-3.0-only
import json
import zipfile
import runpy
import numpy as np
import pytest
from tools import color_volume_wheel_suite as suite


def test_minimal_runtime_keeps_nine_hash_locked_distributions_and_no_renderer():
    text=suite.runtime_requirements()
    headers=[s for s in text.splitlines() if s and not s.startswith(' ')]
    assert len(headers)==9 and all('==' in s for s in headers)
    assert not any('vispy' in s.lower() or 'napari' in s.lower() for s in headers)
    assert '--hash=sha256:' in text
    assert any(s.startswith('pyopengl==3.1.10 ') for s in headers)


def test_exact_compare_checks_all_channels_params_and_before_frames():
    image=np.zeros((96,96,4),np.uint8);before=image.copy();before[0,0]=1
    params={'case':'rgba_update'};extras={'before':before}
    suite.compare(image,params,extras,image.copy(),dict(params),{'before':before.copy()})
    wrong=image.copy();wrong[20,30,3]=1
    with pytest.raises(AssertionError):suite.compare(wrong,params,extras,image,params,extras)
    with pytest.raises(AssertionError):suite.compare(image,{'case':'rgb_update'},extras,image,params,extras)
    with pytest.raises(AssertionError):suite.compare(image,params,extras,image,params,{'before':image})
    with pytest.raises(AssertionError):suite.compare(image,params,extras,image,params,{})


def test_reference_hash_failure_precedes_artifact_access(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps(dict(status='PASS_ALL_UPSTREAM_COLOR_VOLUMES')))
    with pytest.raises(AssertionError):suite.load_reference(tmp_path,'0'*64,'rgb_mip')


def test_portable_reference_preserves_all_24_cases_and_before_frames():
    directory=suite.ROOT/'tests/reference/color-volume-opengl'
    digest='c8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337'
    before=0
    for name in suite.CASES:
        image,params,extras=suite.load_reference(directory,digest,name)
        assert image.shape==(96,96,4) and image.dtype==np.uint8
        assert params['case']==name
        before+=len(extras)
    assert before==4


def test_opacity_pair_controls_reject_ignored_alpha_and_rgb_channel_mismatch(tmp_path):
    for name,value in [('rgb_mip',1),('rgba_mip_opaque',1),('rgba_mip',2),('rgba_mip_alpha_low',3)]:
        p=tmp_path/name;p.mkdir();np.save(p/'rgba.npy',np.full((96,96,4),value,np.uint8))
    suite.assert_opacity_controls(tmp_path)
    np.save(tmp_path/'rgba_mip_alpha_low/rgba.npy',np.full((96,96,4),2,np.uint8))
    with pytest.raises(AssertionError):suite.assert_opacity_controls(tmp_path)


def test_wheel_metadata_payloads_checked_with_only_installer_record_excluded(tmp_path):
    contents={'vispy/__init__.py':b'example',
        'vispy/_licenses/LICENSE':(suite.ROOT/'LICENSE').read_bytes(),
        'vispy/_licenses/LICENSE-BSD':(suite.ROOT/'LICENSE-BSD').read_bytes(),
        'vispy-0.17.0.dist-info/METADATA':b'Name: vispy\nVersion: 0.17.0+vulkan.1\n',
        'vispy-0.17.0.dist-info/WHEEL':b'Wheel-Version: 1.0\n',
        'vispy-0.17.0.dist-info/RECORD':b'original record'}
    wheel=tmp_path/'candidate.whl';site=tmp_path/'site'
    with zipfile.ZipFile(wheel,'w') as z:
        for name,body in contents.items():
            z.writestr(name,body);path=site/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    (site/'vispy-0.17.0.dist-info/RECORD').write_bytes(b'installer rewritten record')
    verified=suite.verify_package(wheel,site/'vispy','candidate')
    assert len(verified)==len(contents)-1
    assert 'vispy-0.17.0.dist-info/METADATA' in verified
    (site/'vispy-0.17.0.dist-info/METADATA').write_bytes(b'wrong version')
    with pytest.raises(AssertionError):suite.verify_package(wheel,site/'vispy','candidate')


def successful_parent():
    return dict(status='PASS_ALL_CANDIDATE_COLOR_VOLUMES',opacity_controls_passed=True,
                required_cases_without_verified_result=[])


def parent_checker():
    # Loading the marked module defines tests/fixtures; it creates no canvas.
    return runpy.run_path(str(suite.ROOT/'tests/contract/test_color_volume_wheel_parity.py'))['assert_successful_parent']


def test_successful_parent_admitted():
    parent_checker()(0,successful_parent())


@pytest.mark.parametrize('defect',['return-code','status','opacity','missing-case','error'])
def test_all_worker_passes_cannot_hide_parent_failure(defect):
    manifest=successful_parent();code=0
    if defect=='return-code':code=1
    if defect=='status':manifest['status']='FAILED_REQUIRED_COLOR_VOLUMES'
    if defect=='opacity':manifest['opacity_controls_passed']=False
    if defect=='missing-case':manifest['required_cases_without_verified_result']=['rgb_mip']
    if defect=='error':manifest['error']='parent cleanup or source seal failed'
    with pytest.raises(AssertionError):parent_checker()(code,manifest)
