# SPDX-License-Identifier: AGPL-3.0-only
"""Candidate frames and auxiliary frames follow the smooth-line criterion; host state stays exact."""
from pathlib import Path
import numpy as np
import pytest
from tools import napari_plugin_wheel_suite as suite
from tools.smooth_line_parity import (
    EDGE_TOLERANCE,MAX_DIFFERING_FRACTION,reference_edges,smooth_line_difference,
)


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
    with pytest.raises(AssertionError,match='Plugin frame differs beyond smooth-line edges'):
        suite.compare(name,candidate,image,candidate_parameters(params),params,extras,extras)


@pytest.mark.parametrize('name',('selection','translation','miss'))
def test_before_event_frames_are_mandatory_observations(name):
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


# Smooth-line criterion used by compare(): exact uniform regions, bounded and capped elsewhere.
REFERENCE=Path(__file__).resolve().parents[2]/'tests/reference/napari-threedee-overlay-opengl'
MAGENTA = np.array([255, 0, 255])


def line(offset=0, rows=slice(64, 128)):
    """A 64-row vertical line on the real frame size: 3-px core with half-intensity fringes."""
    frame = np.zeros((192, 256, 4), np.uint8)
    frame[..., 3] = 255
    x = 128 + offset
    frame[rows, x - 1:x + 2, :3] = MAGENTA
    frame[rows, [x - 2, x + 2], :3] = MAGENTA // 2
    return frame


@pytest.fixture
def handles():
    return np.load(REFERENCE/'handles.rgba.npy',allow_pickle=False)


def test_identical_frame_is_admitted(handles):
    assert smooth_line_difference(handles.copy(), handles) is None


def test_line_core_centre_is_a_uniform_region_and_fringes_are_edges():
    edges = reference_edges(line())
    assert not edges[96, 128] and edges[96, [126, 127, 129, 130]].all()


def test_line_shifted_by_one_pixel_is_rejected():
    assert 'exceeds' in smooth_line_difference(line(offset=1), line())


def test_missing_line_is_rejected():
    assert 'interior' in smooth_line_difference(line(rows=slice(0, 0)), line())


def test_fringe_recolour_within_the_bound_is_admitted():
    candidate = line()
    candidate[64:128, [126, 130], 0] += 20
    assert smooth_line_difference(candidate, line()) is None


def test_fringe_recolour_beyond_the_bound_is_rejected():
    candidate = line()
    candidate[64:128, [126, 130], 0] += EDGE_TOLERANCE + 8
    assert 'exceeds' in smooth_line_difference(candidate, line())


def test_recolouring_a_line_with_a_uniform_core_is_rejected():
    candidate = line()
    candidate[64:128, 126:131, 0] -= 20
    assert 'interior' in smooth_line_difference(candidate, line())


def perturb_edges(frame, count, step):
    candidate = frame.astype(np.int16)
    for y, x in np.argwhere(reference_edges(frame))[:count]:
        rgb = candidate[y, x, :3]
        candidate[y, x, :3] = np.where(rgb > 255 - step, rgb - step, rgb + step)
    return candidate.astype(np.uint8)


def cap(frame):
    return int(MAX_DIFFERING_FRACTION * frame.shape[0] * frame.shape[1])


def test_bounded_change_on_allowed_edge_pixels_is_admitted(handles):
    assert reference_edges(handles).sum() > cap(handles)
    assert smooth_line_difference(perturb_edges(handles, cap(handles), EDGE_TOLERANCE), handles) is None


def test_widespread_edge_change_is_rejected(handles):
    assert 'pixels differ' in smooth_line_difference(perturb_edges(handles, cap(handles) + 1, 1), handles)


def test_edge_change_beyond_the_bound_is_rejected(handles):
    y, x = map(int, np.argwhere(reference_edges(handles) & (handles[..., 0] < 200))[0])
    candidate = handles.copy()
    candidate[y, x, 0] += EDGE_TOLERANCE + 1
    assert 'exceeds' in smooth_line_difference(candidate, handles)


def test_one_level_interior_change_is_rejected(handles):
    y, x = map(int, np.argwhere(~reference_edges(handles))[0])
    candidate = handles.copy()
    candidate[y, x, 3] ^= 1
    assert 'interior' in smooth_line_difference(candidate, handles)


def test_shape_and_dtype_must_match(handles):
    assert smooth_line_difference(handles[:-1], handles) is not None
    assert smooth_line_difference(handles.astype(np.int16), handles) is not None


HOST_SUITES=('test_napari_threedee_parity.py','test_napari_threedee_initialized_parity.py',
    'test_napari_threedee_overlay_parity.py','test_napari_render_plane_parity.py',
    'test_napari_render_plane_scheduled_parity.py')


@pytest.mark.parametrize('name',HOST_SUITES)
def test_plugin_qt_suites_render_in_the_declared_candidate_interpreter(name):
    source=(Path(__file__).resolve().parents[2]/'tests/hosts'/name).read_text(encoding='utf-8')
    assert 'os.environ.get("VISPY_PLUGIN_CANDIDATE_PYTHON", sys.executable)' in source
    assert 'subprocess.run([str(candidate_python)' in source
    assert source.count('sys.executable')==1  # only as the fallback


@pytest.mark.parametrize('name',HOST_SUITES)
def test_plugin_qt_suites_compare_frames_with_the_smooth_line_criterion(name):
    # Decision D5: every napari-threedee fixture suite compares frames with the smooth-line criterion.
    source=(Path(__file__).resolve().parents[2]/'tests/hosts'/name).read_text(encoding='utf-8')
    assert 'reason = smooth_line_difference(image,' in source
    assert 'array_equal(image' not in source


# CI's curated test list is pinned (compat/qualification-ci.json) until R2, so the curated contract modules
# (tests/contract/curated_contracts.py) run through this module.
from curated_contracts import *  # noqa: E402,F401,F403
