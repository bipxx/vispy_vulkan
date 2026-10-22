# SPDX-License-Identifier: AGPL-3.0-only
"""All original frames, host state and auxiliary frames remain exact."""
from pathlib import Path
import numpy as np
import pytest
from tools import napari_plugin_wheel_suite as suite


def candidate_parameters(expected):
    params=dict(expected)
    assert 'QOpenGLWidget' in params['native_mro']
    params['native_mro']=['QWidget']
    return params


@pytest.mark.parametrize('name',suite.CASES)
def test_original_cases_and_auxiliary_frames_are_accepted_with_candidate_widget(name):
    image,params,extras=suite.legacy_reference(name)
    suite.compare(name,image.copy(),image,candidate_parameters(params),params,
        {k:v.copy() for k,v in extras.items()},extras)


@pytest.mark.parametrize('name',suite.CASES)
def test_one_changed_rgba_byte_cannot_be_admitted(name):
    image,params,extras=suite.legacy_reference(name)
    candidate=image.copy();candidate[0,0,3]^=1
    with pytest.raises(AssertionError,match='Exact full plugin frame'):
        suite.compare(name,candidate,image,candidate_parameters(params),params,extras,extras)


@pytest.mark.parametrize('name',('selection','translation','miss'))
def test_before_event_frames_are_mandatory_exact_observations(name):
    image,params,extras=suite.legacy_reference(name)
    changed={k:v.copy() for k,v in extras.items()};changed['before'][0,0,3]^=1
    with pytest.raises(AssertionError,match='Auxiliary frame'):
        suite.compare(name,image,image,candidate_parameters(params),params,changed,extras)


def test_fixed_event_state_cannot_change_even_when_pixels_match():
    image,params,extras=suite.legacy_reference('selection')
    changed=candidate_parameters(params);changed['screenshot_api']='different export'
    with pytest.raises(AssertionError,match='Qt events or callback state'):
        suite.compare('selection',image,image,changed,params,extras,extras)


def test_runtime_replaces_only_vispy_and_adds_the_verified_plugin_wheel(tmp_path,monkeypatch):
    import hashlib
    from types import SimpleNamespace
    wheel=tmp_path/'plugin.whl';wheel.write_bytes(b'synthetic plugin wheel')
    digest=hashlib.sha256(wheel.read_bytes()).hexdigest()
    def block(name,version,value):return name+'=='+version+' '+chr(92)+'\n    --hash=sha256:'+value+'\n'
    unchanged=block('numpy','2.4.6','1'*64)
    original=unchanged+block('vispy','0.17.0','2'*64)+block('asciitree','0.3.3',suite.ASCIITREE_SOURCE_SHA256)
    (tmp_path/'runtime.txt').write_text(original)
    monkeypatch.setattr(suite,'ROOT',tmp_path);monkeypatch.setattr(suite,'RUNTIME','runtime.txt')
    monkeypatch.setattr(suite,'PLUGIN_WHEEL',wheel);monkeypatch.setattr(suite,'capture',SimpleNamespace(WHEEL_SHA=digest))
    monkeypatch.setattr(suite,'ASCIITREE_WHEEL',wheel);monkeypatch.setattr(suite,'ASCIITREE_SHA256',digest)
    assert suite.runtime_requirements()==unchanged+f'\nnapari-threedee @ {wheel.as_uri()} --hash=sha256:{digest}\nasciitree @ {wheel.as_uri()} --hash=sha256:{digest}\n'


def test_dependency_wheel_is_bound_to_the_original_sdist_pin(tmp_path,monkeypatch):
    text='asciitree==0.3.3 '+chr(92)+'\n    --hash=sha256:'+'0'*64+'\nvispy==0.17.0 '+chr(92)+'\n    --hash=sha256:'+'1'*64+'\n'
    (tmp_path/'runtime.txt').write_text(text)
    monkeypatch.setattr(suite,'ROOT',tmp_path);monkeypatch.setattr(suite,'RUNTIME','runtime.txt')
    with pytest.raises(AssertionError):suite.runtime_requirements()



def test_the_declared_original_and_plugin_artifact_pins_remain_explicit():
    assert suite.capture.WHEEL_SHA=='de115619e84a7967b0386651163c29ec12228d59e58000736067f066237ce91e'
    assert suite.LEGACY_SHA256=='b4a118f6320af8f8d12010948ff00964fe5966f967003ab40cb887af37ddc77e'
    assert suite.CASES==('handles','selection','translation','miss','retirement')


@pytest.mark.parametrize('isolated',(False,True))
def test_effective_hash_seed_requires_a_worker_that_honors_the_seed(tmp_path,isolated):
    import json,os,subprocess,sys
    from tools.image_wheel_runner import clean_environment
    env=clean_environment(dict(os.environ,PYTHONHASHSEED='0'))
    code='import sys,json;print(json.dumps(dict(hash_randomization=sys.flags.hash_randomization,no_user_site=sys.flags.no_user_site)))'
    flags=['-I','-B'] if isolated else ['-s','-B']
    result=subprocess.run([sys.executable,*flags,'-c',code],cwd=tmp_path,env=env,capture_output=True,check=True)
    actual=json.loads(result.stdout)
    assert actual['no_user_site']==1
    assert actual['hash_randomization']==(1 if isolated else 0)


def test_portable_inputs_are_complete_and_have_no_build_directory_dependency():
    import hashlib,json
    assert hashlib.sha256((suite.INPUTS/'manifest.json').read_bytes()).hexdigest()==suite.INPUTS_SHA256
    manifest=json.loads((suite.INPUTS/'manifest.json').read_bytes())
    for leaf,digest in manifest['files'].items():
        assert hashlib.sha256((suite.INPUTS/leaf).read_bytes()).hexdigest()==digest
    assert not any(name.startswith('build/') for name in suite.SOURCES)
    assert suite.PLUGIN_WHEEL.parent==suite.ASCIITREE_WHEEL.parent==suite.INPUTS


@pytest.mark.parametrize('raises',(False,True))
def test_original_provenance_checker_wheel_binding_is_restored(monkeypatch,raises):
    import sys
    previous=suite.capture.WHEEL
    def check():
        assert suite.capture.WHEEL==suite.PLUGIN_WHEEL
        if raises:raise ValueError('registration failure')
        return dict(plugin_origin=str(Path(sys.prefix)/'Lib/site-packages/napari_threedee'),
                    napari_origin=str(Path(sys.prefix)/'Lib/site-packages/napari/__init__.py'))
    monkeypatch.setattr(suite.capture,'plugin_provenance',check)
    versions={'napari':'0.9.2','napari-threedee':'0.0.29','numpy':'2.4.6','PyQt6':'6.11.0','asciitree':'0.3.3'}
    monkeypatch.setattr(suite.metadata,'version',versions.__getitem__)
    if raises:
        with pytest.raises(ValueError,match='registration failure'):suite.plugin_info()
    else:suite.plugin_info()
    assert suite.capture.WHEEL==previous
