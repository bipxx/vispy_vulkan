# SPDX-License-Identifier: AGPL-3.0-only
"""CPU-only guards for the distinct Linux software qualification profile."""
from copy import deepcopy
import ast
import json
import re
import pytest
from tools import color_volume_linux_wheel_suite as linux
from tools import color_volume_wheel_suite as windows


def profile():return json.loads((linux.ROOT/linux.PROFILE).read_bytes())


def test_software_profile_has_the_six_pinned_driver_components():
    p=profile();assert linux.validate_profile(p) is p
    assert len(p['paths'])==6 and p['software'] is True


@pytest.mark.parametrize('defect',['hardware','platform','python','renderer','missing-component','bad-digest'])
def test_wrong_profile_refused_before_driver_file_access(defect):
    p=deepcopy(profile())
    if defect=='hardware':p['software']=False
    if defect=='platform':p['platform']='windows'
    if defect=='python':p['python']='3.11.14'
    if defect=='renderer':p['renderer_token']='NVIDIA'
    if defect=='missing-component':p['paths'].pop('llvm')
    if defect=='bad-digest':p['paths']['llvm']['sha256']='not-a-digest'
    with pytest.raises(AssertionError):linux.validate_profile(p)


def test_distinct_original_artifact_and_unchanged_scientific_inputs():
    assert linux.ORIGINAL_SHA=='9e8d65572d164a8ab690815feee9f7b6848fe5a3ce761a9082ad0580c398ff3f'
    assert linux.ORIGINAL_SHA!=windows.ORIGINAL_SHA and linux.RUNTIME!=windows.RUNTIME
    assert linux.CASES==windows.CASES and linux.render is windows.render
    assert linux.PROFILE in linux.SOURCES


def test_all_nine_runtime_versions_equal_the_windows_scientific_pair():
    headers=lambda text:re.findall(r'(?m)^([a-z0-9-]+==[^\s]+)',text)
    assert sorted(headers(linux.runtime_requirements()))==sorted(headers(windows.runtime_requirements()))
    assert len(headers(linux.runtime_requirements()))==9


def test_windows_reference_is_refused_as_a_linux_reference():
    directory=linux.ROOT/'tests/reference/color-volume-opengl'
    with pytest.raises(AssertionError):
        linux.load_reference(directory,'c8af8d76e1ecdaac1e21303a47ba75a7cce83cb269085a230e89cf0f127c4337','rgb_mip')


@pytest.mark.parametrize('name',['compare','assert_opacity_controls','load_reference','verify_package'])
def test_adapter_preserves_exact_quality_and_payload_gate_bodies(name):
    def body(module):
        parsed=ast.parse(open(module.__file__,encoding='utf-8').read())
        return ast.dump(next(node for node in parsed.body if isinstance(node,ast.FunctionDef) and node.name==name),include_attributes=False)
    assert body(linux)==body(windows)


@pytest.mark.parametrize('kind',['upstream','candidate'])
def test_required_mapped_driver_components(kind):
    p=profile()
    keys=('gl_gallium','glx_library','llvm') if kind=='upstream' else ('vulkan_driver','llvm')
    rows=[dict(p['paths'][k]) for k in keys]
    linux.assert_driver_origins(rows,p,kind)


@pytest.mark.parametrize('defect',['missing','digest','extra-mesa','extra-llvm','implicit-layer'])
def test_wrong_or_unloaded_driver_images_refused(defect):
    p=profile();rows=[dict(p['paths'][k]) for k in ('vulkan_driver','llvm')]
    if defect=='missing':rows.pop()
    if defect=='digest':rows[0]['sha256']='0'*64
    if defect=='extra-mesa':rows.append(dict(path='/usr/lib/libgallium-other.so',sha256='0'*64))
    if defect=='extra-llvm':rows.append(dict(path='/usr/lib/libLLVM.so.19',sha256='0'*64))
    if defect=='implicit-layer':rows.append(dict(path='/usr/lib/libVkLayer_MESA_device_select.so',sha256='0'*64))
    with pytest.raises(AssertionError):linux.assert_driver_origins(rows,p,'candidate')


def test_inherited_driver_overrides_removed_and_full_relevant_state_recorded():
    keys=['LD_PRELOAD','LD_LIBRARY_PATH','LIBGL_DRIVERS_PATH','MESA_LOADER_DRIVER_OVERRIDE',
          'MESA_GL_VERSION_OVERRIDE','MESA_SHADER_CACHE_DIR','LP_NUM_THREADS','GALLIVM_PERF',
          'GALLIUM_DRIVER','__GLX_VENDOR_LIBRARY_NAME','__EGL_VENDOR_LIBRARY_FILENAMES',
          'QT_XCB_GL_INTEGRATION','QT_OPENGL','VK_INSTANCE_LAYERS','DAWN_DEBUG']
    original={k:'inherited' for k in keys};original['PATH']='tools'
    assert linux.clean_driver_environment(original)=={'PATH':'tools'}
    assert original['LD_PRELOAD']=='inherited'
    forced=linux.software_driver_environment(profile())
    assert forced['VK_LOADER_LAYERS_DISABLE']=='~implicit~' and forced['QT_XCB_GL_INTEGRATION']=='xcb_glx'
    assert linux.graphics_environment(dict(forced,DISPLAY=':9',PATH='tools'))==dict(sorted(dict(forced,DISPLAY=':9').items()))


def test_only_the_owned_mesa_cache_can_survive_worker_filtering():
    state={'MESA_SHADER_CACHE_DIR':'/tmp/owned/cache','MESA_GL_VERSION_OVERRIDE':'wrong'}
    assert linux.clean_driver_environment(state,keep_owned_cache=True)=={'MESA_SHADER_CACHE_DIR':'/tmp/owned/cache'}



def test_portable_linux_reference_contains_all24_and_four_before_frames():
    directory=linux.ROOT/'tests/reference/color-volume-linux-opengl'
    before=0
    for name in linux.CASES:
        image,params,extras=linux.load_reference(directory,'971d48cee245e2551e27261052d09a04d83988864ebbb6393c292f5175dfe925',name)
        assert image.shape==(96,96,4) and params['case']==name
        before+=len(extras)
    assert before==4


def test_linux_pytest_parent_gate_matches_the_qualified_windows_gate():
    def gate(name):
        tree=ast.parse((linux.ROOT/'tests/contract'/name).read_text(encoding='utf-8'))
        return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assert_successful_parent'),include_attributes=False)
    assert gate('test_color_volume_linux_wheel_parity.py')==gate('test_color_volume_wheel_parity.py')
