# SPDX-License-Identifier: AGPL-3.0-only
"""Linux software RGB(A) volume adapter; frozen Windows references stay unchanged."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
import sys,traceback,uuid,zipfile
ROOT=Path(__file__).resolve().parents[1]
if not __package__:sys.path.insert(0,str(ROOT/'tools'))
try:
    from .fixture_color_volume import CASES,METHODS,render,case_contract,assert_landmarks
    from .image_wheel_runner import installed_environment,run_logged,write,sha
    from .mesh_layout_process import process_stamp,worker_terminal,native_modules,assert_wheel_module_origins
except ImportError:
    from fixture_color_volume import CASES,METHODS,render,case_contract,assert_landmarks
    from image_wheel_runner import installed_environment,run_logged,write,sha
    from mesh_layout_process import process_stamp,worker_terminal,native_modules,assert_wheel_module_origins

ORIGINAL_SHA='9e8d65572d164a8ab690815feee9f7b6848fe5a3ce761a9082ad0580c398ff3f'
RUNTIME='compat/host-environments/color-volume-linux-cpython312-pyqt6.txt'
PROFILE='compat/software-stacks/color-volume-linux-llvmpipe.json'
SOURCES=('tools/color_volume_linux_wheel_suite.py','tools/fixture_color_volume.py','tools/fixture_gloo.py',
         'tools/image_wheel_runner.py','tools/fixture_image_extensions.py','tools/mesh_layout_process.py',
         RUNTIME,'LICENSE','LICENSE-BSD','LICENSING.md',PROFILE)
ZEROS=('pending_tickets','live_buffer_bytes','live_cpu_buffer_bytes','live_texture_bytes',
       'deferred_frames','queued_frames','vk_memory_live_allocations','vk_memory_live_bytes')

def sources():return {n:sha(ROOT/n) for n in SOURCES}

def runtime_requirements():
    import re
    text=(ROOT/RUNTIME).read_text(encoding='utf-8');blocks=[]
    for name in ('numpy','freetype-py','hsluv','kiwisolver','packaging','pyqt6','pyqt6-qt6','pyqt6-sip','pyopengl'):
        selected=re.findall(r'(?m)^'+re.escape(name)+r'==[^\n]+\n(?:    --hash=[^\n]+\n)+',text)
        assert len(selected)==1,name
        blocks.append(selected[0])
    return ''.join(blocks)

def verify_package(wheel,package,kind):
    if kind=='upstream':assert sha(wheel)==ORIGINAL_SHA
    hashes={}
    with zipfile.ZipFile(wheel) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        for n in z.namelist():
            if n.endswith('/'):continue
            # Installers rewrite RECORD to include their generated files.
            # All actual wheel payloads, including METADATA/WHEEL/licenses,
            # are checked; RECORD itself is the sole explicit exclusion.
            if n.endswith('/RECORD') and n.split('/')[0].endswith('.dist-info'):continue
            assert '.data/' not in n,'Wheel relocation requires an explicit installation map'
            p=(package.parent/n).resolve();assert p.is_relative_to(package.parent)
            h=hashlib.sha256(z.read(n)).hexdigest();assert sha(p)==h,n
            hashes[n]=h
    assert 'vispy/__init__.py' in hashes
    if kind=='candidate':
        assert hashes['vispy/_licenses/LICENSE']==sha(ROOT/'LICENSE')
        assert hashes['vispy/_licenses/LICENSE-BSD']==sha(ROOT/'LICENSE-BSD')
    return hashes

def compare(image,params,extras,reference,expected,prior_extras):
    import numpy as np
    assert params==expected,'Original color-volume state differs'
    assert np.array_equal(image,reference),'Exact full color-volume frame differs'
    assert set(extras)==set(prior_extras)
    for key in extras:assert np.array_equal(extras[key],prior_extras[key]),key

def assert_opacity_controls(directory):
    import numpy as np
    def rgba(name):return np.load(Path(directory)/name/'rgba.npy',allow_pickle=False)
    assert np.array_equal(rgba('rgb_mip'),rgba('rgba_mip_opaque')),'RGB implicit alpha must equal explicit opaque RGBA'
    assert not np.array_equal(rgba('rgba_mip'),rgba('rgba_mip_alpha_low')),'RGBA opacity must affect rendered pixels'

def load_reference(directory,digest,name):
    import numpy as np
    directory=Path(directory);assert sha(directory/'manifest.json')==digest
    manifest=json.loads((directory/'manifest.json').read_bytes())
    assert manifest['status']=='PASS_ALL_UPSTREAM_COLOR_VOLUMES'
    assert manifest['kind']=='upstream' and manifest['cases']==list(CASES)
    assert manifest['sources_sha256']==sources() and manifest['wheel_sha256']==ORIGINAL_SHA
    row=manifest['workers'][name];worker=json.loads((directory/name/'result.json').read_bytes())
    assert sha(directory/name/'result.json')==row['report_sha256']
    assert row['process_exit']==worker['process_exit']==0 and row['actual_worker_terminal']['terminal']
    assert worker['status']=='PASS_UPSTREAM_COLOR_VOLUME' and worker['case']==name
    for leaf,h in worker['artifacts'].items():
        assert Path(leaf).name==leaf and sha(directory/name/leaf)==h
    params=json.loads((directory/name/'parameters.json').read_bytes())
    image=np.load(directory/name/'rgba.npy',allow_pickle=False)
    extras={}
    if len(case_contract(name)['inputs'])==2:
        extras['before']=np.load(directory/name/'before.npy',allow_pickle=False)
    assert_landmarks(name,image)
    return image,params,extras


def validate_profile(profile):
    assert profile['schema']==1 and profile['platform']=='linux-x86_64'
    assert profile['python']=='3.12.8' and profile['software'] is True
    assert profile['renderer_token']=='llvmpipe' and profile['mesa_version']=='25.2.8'
    assert set(profile['paths'])=={'vulkan_icd','vulkan_driver','gl_driver','glx_library','gl_gallium','llvm'}
    for row in profile['paths'].values():
        assert row['path'].startswith('/usr/')
        assert len(row['sha256'])==64 and all(c in '0123456789abcdef' for c in row['sha256'])
    return profile


def check_software_stack():
    profile=validate_profile(json.loads((ROOT/PROFILE).read_bytes()))
    for row in profile['paths'].values():assert sha(Path(row['path']))==row['sha256']
    return profile


def driver_steering_variable(name):
    return (name.startswith(('VK_','DAWN_','MESA_','LIBGL_','LP_','GALLIVM_','GALLIUM_',
                             '__GLX_','__EGL_')) or name in ('LD_PRELOAD','LD_LIBRARY_PATH',
                             'QT_XCB_GL_INTEGRATION','QT_OPENGL','QT_QPA_PLATFORM',
                             'QT_SCALE_FACTOR','QT_API'))


def clean_driver_environment(environment,*,keep_owned_cache=False):
    return {n:v for n,v in environment.items() if not driver_steering_variable(n)
            or keep_owned_cache and n=='MESA_SHADER_CACHE_DIR'}


def graphics_environment(environment):
    return {n:environment[n] for n in sorted(environment) if driver_steering_variable(n)
            or n in ('DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','XDG_CACHE_HOME')}


def software_driver_environment(profile):
    return dict(VK_DRIVER_FILES=profile['paths']['vulkan_icd']['path'],
        VK_ICD_FILENAMES=profile['paths']['vulkan_icd']['path'],VK_LOADER_LAYERS_DISABLE='~implicit~',
        LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',QT_QPA_PLATFORM='xcb',
        QT_XCB_GL_INTEGRATION='xcb_glx',QT_SCALE_FACTOR='1',QT_API='pyqt6')


def assert_driver_origins(records,profile,kind):
    pinned={str(Path(row['path']).resolve()):row['sha256'] for row in profile['paths'].values()}
    mapped=set()
    for row in records:
        key=str(Path(row['path']).resolve());name=Path(key).name.lower()
        driver_class=(name.startswith(('libgallium','libllvm','libvulkan_','libvklayer_mesa',
                                      'libglx_mesa','libegl_mesa','libdril_')) or name.endswith('_dri.so'))
        if driver_class:assert key in pinned,('Unpinned software driver image',key)
        if key in pinned:
            assert row['sha256']==pinned[key],key
            mapped.add(key)
    required=('gl_gallium','glx_library','llvm') if kind=='upstream' else ('vulkan_driver','llvm')
    assert {str(Path(profile['paths'][n]['path']).resolve()) for n in required}<=mapped

def worker(args):
    import numpy as np
    from importlib import metadata
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert sys.platform.startswith('linux') and sys.version_info[:3]==(3,12,8)
    args.output.mkdir(parents=True,exist_ok=False)
    held=sources();wheel_sha=sha(args.wheel)
    result=dict(status='FAILED_PRESERVED',process_exit=1,case=args.case,kind=args.kind,
        pid=os.getpid(),process_stamp=process_stamp(),launch_id=args.launch_id,
        sources_sha256=held,wheel_sha256=wheel_sha,renderer_qualified=False)
    dawn=qapp=None;package=installed=profile=None
    try:
        profile=check_software_stack()
        selected=clean_driver_environment(os.environ,keep_owned_cache=True)
        os.environ.clear();os.environ.update(selected)
        os.environ.update(software_driver_environment(profile))
        result.update(software_profile_sha256=sha(ROOT/PROFILE),driver_environment=graphics_environment(os.environ))
        import vispy
        from vispy import app,gloo
        package=Path(vispy.__file__).resolve().parent;prefix=Path(sys.prefix).resolve()
        assert package.is_relative_to(prefix) and not prefix.is_relative_to(ROOT)
        version='0.17.0' if args.kind=='upstream' else '0.17.0+vulkan.1'
        assert vispy.__version__==metadata.version('vispy')==version
        installed=verify_package(args.wheel,package,args.kind)
        result['installed_wheel_payloads_sha256']=installed
        result['excluded_installer_metadata']='Only the installer-rewritten dist-info/RECORD; all wheel payload bytes checked'
        result['dependencies']={n:metadata.version(n) for n in ('numpy','freetype-py','hsluv','kiwisolver','packaging','PyQt6','PyQt6-Qt6','PyQt6-sip','PyOpenGL')}
        if args.kind=='upstream':
            app.use_app('pyqt6')
            from PyQt6 import QtWidgets
            qapp=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            qapp.setQuitOnLastWindowClosed(False)
            control=app.Canvas(app='pyqt6',size=(2,2),show=False)
            try:
                control.set_current();gloo.clear();gloo.finish()
                result['renderer']={k:str(gloo.gl.glGetParameter(getattr(gloo.gl,n)))
                    for k,n in (('vendor','GL_VENDOR'),('renderer','GL_RENDERER'),('version','GL_VERSION'))}
                assert 'Mesa' in result['renderer']['vendor']
                assert 'llvmpipe' in result['renderer']['renderer'].lower()
                assert 'LLVM 20' in result['renderer']['renderer']
                assert 'Mesa 25.2.8' in result['renderer']['version']
            finally:control.close()
        else:
            from vispy import _dawn
            dawn=_dawn;before=dict(dawn.probe())
            original,expected,prior_extras=load_reference(args.reference,args.reference_sha256,args.case)
        image,commands,shaders,params,extras=render(args.case,'pyqt6' if args.kind=='upstream' else 'dawn_headless')
        np.save(args.output/'rgba.npy',image,allow_pickle=False)
        write(args.output/'commands.json',commands);write(args.output/'shaders.json',shaders)
        write(args.output/'parameters.json',params)
        for key,array in extras.items():np.save(args.output/(key+'.npy'),array,allow_pickle=False)
        assert commands and shaders
        assert_landmarks(args.case,image)
        if extras:
            assert not np.array_equal(extras['before'],image),'Public volume update must change pixels'
        assert set(params['exposed_methods'])==set(METHODS)
        assert params['final_volume_shape']==[32,32,32]
        if args.kind=='candidate':
            compare(image,params,extras,original,expected,prior_extras)
            after=dict(dawn.probe())
            result['native_work_delta']={k:after[k]-before[k] for k in ('draw_calls','pipeline_misses','vk_queue_submits')}
            assert all(v>0 for v in result['native_work_delta'].values())
            device=dict(dawn.device_info());result['device']=device
            assert device['ok'] and device['backend']=='Vulkan' and device['software'] is True
            assert device['adapter_type'].lower()=='cpu' and 'llvmpipe' in device['device'].lower()
            assert '25.2.8' in device['driver']
        result.update(status='PASS_UPSTREAM_COLOR_VOLUME' if args.kind=='upstream' else 'PASS_CANDIDATE_COLOR_VOLUME',
                      process_exit=0,compared_pixels=96*96,excluded_pixels=0)
    except BaseException:result['error']=traceback.format_exc()
    finally:
        result['driver_environment_at_close']=graphics_environment(os.environ)
        try:
            if qapp is not None:
                from PyQt6 import QtCore
                qapp.closeAllWindows();qapp.processEvents()
                QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
                qapp.processEvents()
                result['visible_windows_after_close']=sum(w.isVisible() for w in qapp.topLevelWidgets())
                assert result['visible_windows_after_close']==0
            if package is not None and installed is not None:
                records=native_modules((ROOT,args.repository))
                assert_driver_origins(records,profile,args.kind)
                package_hashes={n:h for n,h in installed.items() if n.startswith('vispy/')}
                assert_wheel_module_origins(records,package,package_hashes,[dawn.__file__] if dawn else [])
                if args.kind=='upstream':
                    assert not any('_dawn' in Path(r['path']).name.lower() or 'vispy_submit' in Path(r['path']).name.lower() for r in records)
                write(args.output/'native-modules.json',records)
                result['native_origins_verified']=True
        except BaseException:result.update(status='FAILED_PRESERVED',process_exit=1,origin_cleanup_error=traceback.format_exc())
        finally:
            try:
                if dawn is not None:
                    dawn.shutdown();counters=dict(dawn.probe())
                    result['shutdown_zeros']={k:counters[k] for k in ZEROS}
                    assert all(v==0 for v in result['shutdown_zeros'].values())
                assert sources()==held and sha(args.wheel)==wheel_sha
                if installed is not None:assert verify_package(args.wheel,package,args.kind)==installed
                if profile is not None:assert check_software_stack()==profile
                result['cleanup_passed']=True
            except BaseException:result.update(status='FAILED_PRESERVED',process_exit=1,cleanup_error=traceback.format_exc())
        result['artifacts']={p.name:sha(p) for p in args.output.iterdir() if p.is_file()}
        write(args.output/'result.json',result)
    return result['process_exit']

def run(args):
    assert not args.output.exists()
    if args.kind=='upstream':assert sha(args.wheel)==ORIGINAL_SHA
    else:
        for name in CASES:load_reference(args.reference,args.reference_sha256,name)
    held=sources();wheel_sha=sha(args.wheel)
    args.output.mkdir(parents=True)
    runtime=args.output/'runtime.txt';runtime.write_text(runtime_requirements(),encoding='utf-8')
    env=clean_driver_environment(os.environ,keep_owned_cache=True)
    for n in list(env):
        if n.upper().startswith(('VISPY_IMAGE_','VISPY_TEST_')):env.pop(n)
    env['VISPY_TEST_PYTHON']=sys.executable
    env['VISPY_TEST_RUNTIME_REQUIREMENTS']=str(runtime.resolve())
    result=dict(kind=args.kind,cases=list(CASES),sources_sha256=held,wheel_sha256=wheel_sha,
                pid=os.getpid(),process_stamp=process_stamp(),
                status='FAILED_REQUIRED_COLOR_VOLUMES',workers={},release_qualified=False)
    try:
        with installed_environment(args.wheel,args.output/'environment',environment=env) as (python,environment):
            for name in CASES:
                nonce=uuid.uuid4().hex
                cmd=[python,'-I','-B',Path(__file__),'--worker','--kind',args.kind,'--case',name,
                     '--launch-id',nonce,'--wheel',args.wheel,'--repository',args.repository,'--output',args.output/name]
                if args.kind=='candidate':cmd+=['--reference',args.reference,'--reference-sha256',args.reference_sha256]
                observed=run_logged(cmd,cwd=Path(python).parent,environment=environment,log=args.output/(name+'.log'))
                try:
                    report=args.output/name/'result.json';child=json.loads(report.read_bytes())
                    assert child['launch_id']==nonce
                    observed.update(report_sha256=sha(report),actual_worker_terminal=worker_terminal(child,observed['pid']))
                    assert observed['actual_worker_terminal']['terminal']
                except BaseException:
                    write(args.output/'environment/worker-termination-unverified.json',dict(**observed,error=traceback.format_exc()))
                    raise
                observed['worker_status']=child['status'];result['workers'][name]=observed
                write(args.output/(name+'.process.json'),observed)
        passed=all(row['process_exit']==0 and row['worker_status'].startswith('PASS_') for row in result['workers'].values())
        assert set(result['workers'])==set(CASES) and sources()==held and sha(args.wheel)==wheel_sha
        if passed:
            assert_opacity_controls(args.output)
            result['opacity_controls_passed']=True
            result['status']='PASS_ALL_UPSTREAM_COLOR_VOLUMES' if args.kind=='upstream' else 'PASS_ALL_CANDIDATE_COLOR_VOLUMES'
    except BaseException:result['error']=traceback.format_exc()
    finally:
        result['required_cases_without_verified_result']=[n for n in CASES if n not in result['workers']]
        write(args.output/'manifest.json',result)
    return 0 if result['status'].startswith('PASS_ALL_') else 1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker',action='store_true');p.add_argument('--kind',choices=('upstream','candidate'),required=True)
    p.add_argument('--wheel',type=Path,required=True);p.add_argument('--repository',type=Path,default=ROOT)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=CASES)
    p.add_argument('--reference',type=Path);p.add_argument('--reference-sha256');p.add_argument('--launch-id')
    args=p.parse_args()
    args.output=args.output.resolve();args.wheel=args.wheel.resolve(strict=True);args.repository=args.repository.resolve(strict=True)
    return worker(args) if args.worker else run(args)

if __name__=='__main__':raise SystemExit(main())
