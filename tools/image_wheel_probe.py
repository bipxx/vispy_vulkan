# SPDX-License-Identifier: AGPL-3.0-only
"""One required image/label workflow in an isolated installed-wheel process."""
from __future__ import annotations
import argparse
from email.parser import BytesParser
import hashlib
from importlib import machinery,metadata
import json
import os
from pathlib import Path
import sys
import traceback
import zipfile

PRODUCER=Path(__file__).resolve().parents[1]
if __package__:
    from .fixture_image_extensions import CASES,VISPY_CASES,render
    from .image_wheel_reference import MANIFEST_SHA256,LICENSES,load_case,load_manifest,compare_case,sha
    from .mesh_layout_process import process_stamp,native_modules,assert_wheel_module_origins
else:
    sys.path.insert(0,str(PRODUCER/'tools'))
    from fixture_image_extensions import CASES,VISPY_CASES,render
    from image_wheel_reference import MANIFEST_SHA256,LICENSES,load_case,load_manifest,compare_case,sha
    from mesh_layout_process import process_stamp,native_modules,assert_wheel_module_origins

SHUTDOWN_FIELDS=('pending_tickets','live_buffer_bytes','live_cpu_buffer_bytes','live_texture_bytes',
                 'deferred_frames','queued_frames','vk_memory_live_allocations','vk_memory_live_bytes')
SOURCES=('tools/fixture_image_extensions.py','tools/fixture_gloo.py',
         'tools/image_wheel_reference.py','tools/image_wheel_probe.py','tools/mesh_layout_process.py',
         'tools/mesh_layout_reference.py','tools/fixture_mesh_layout_extensions.py')


def write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def verify_wheel_package(wheel,package):
    """Require every package member to be the supplied archive's installed bytes."""
    hashes={}
    with zipfile.ZipFile(wheel) as archive:
        names=archive.namelist()
        assert len(names)==len(set(names)), 'Duplicate wheel entries'
        for name in names:
            if not name.startswith('vispy/') or name.endswith('/'):continue
            relative=Path(name).relative_to('vispy')
            installed=(package/relative).resolve()
            assert installed.is_relative_to(package.resolve()), name
            digest=hashlib.sha256(archive.read(name)).hexdigest()
            assert sha(installed)==digest, f'Installed wheel member differs: {name}'
            hashes[name]=digest
    assert {'vispy/__init__.py','vispy/_licenses/LICENSE','vispy/_licenses/LICENSE-BSD'}<=set(hashes)
    return hashes


def capture(args):
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    output=args.output.resolve()
    assert not output.exists(), 'Preserve every prior consumer attempt'
    output.mkdir(parents=True)
    source_hashes={name:sha(PRODUCER/name) for name in SOURCES}
    wheel_hash=sha(args.wheel)
    result=dict(schema=1,status='FAILED_PRESERVED',process_exit=1,case=args.case,pid=os.getpid(),
        launch_id=args.launch_id,
        python=sys.version,executable=sys.executable,producer_sources_sha256=source_hashes,
        reference_manifest_sha256=MANIFEST_SHA256,wheel_sha256=wheel_hash,
        platform_or_release_qualified=False,render_attempted=False,cleanup_passed=False,native_origins_verified=False)
    dawn=None
    try:
        assert len(args.launch_id)==32 and all(c in '0123456789abcdef' for c in args.launch_id)
        result['process_stamp']=process_stamp()
        reference,expected=load_case(args.case,args.reference,producer_root=PRODUCER)
        manifest=load_manifest(args.reference,producer_root=PRODUCER)
        prefix=Path(sys.prefix).resolve()
        assert not prefix.is_relative_to(args.repository.resolve()), 'External installed consumer required'
        import vispy
        package=Path(vispy.__file__).resolve().parent
        assert package.is_relative_to(prefix) and not package.is_relative_to(args.repository.resolve())
        assert metadata.version('vispy')==vispy.__version__=='0.17.0+vulkan.1'
        from packaging.tags import parse_tag,sys_tags
        with zipfile.ZipFile(args.wheel) as archive:
            metadata_names=[name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
            wheel_names=[name for name in archive.namelist() if name.endswith('.dist-info/WHEEL')]
            assert len(metadata_names)==len(wheel_names)==1
            headers=BytesParser().parsebytes(archive.read(metadata_names[0]))
            assert headers['Name'].lower()=='vispy' and headers['Version']==vispy.__version__
            wheel_headers=BytesParser().parsebytes(archive.read(wheel_names[0]))
            tags=set().union(*(parse_tag(value) for value in wheel_headers.get_all('Tag',[])))
            assert tags & set(sys_tags()), 'Wheel tags do not match this interpreter/platform'
        distribution=metadata.distribution('vispy')
        direct_url=distribution.read_text('direct_url.json')
        if direct_url:assert not json.loads(direct_url).get('dir_info',{}).get('editable',False)
        installed_hashes=verify_wheel_package(args.wheel,package)
        for name,digest in LICENSES.items():
            assert installed_hashes['vispy/_licenses/'+name]==digest, name
        from vispy import _dawn
        dawn=_dawn
        from vispy.visuals.text import _sdf_cpu
        native_origins={}
        for module in (_dawn,_sdf_cpu):
            origin=Path(module.__file__).resolve()
            assert origin.is_relative_to(package)
            assert any(str(origin).endswith(suffix) for suffix in machinery.EXTENSION_SUFFIXES)
            member='vispy/'+origin.relative_to(package).as_posix()
            assert member in installed_hashes and sha(origin)==installed_hashes[member]
            native_origins[module.__name__]=dict(member=member,sha256=installed_hashes[member])
        result.update(package=str(package),prefix=str(prefix),installed_package_members=len(installed_hashes),
            installed_package_sha256=installed_hashes,
            native_modules=native_origins,
            dependencies={name:metadata.version(name) for name in ('numpy','freetype-py','hsluv','kiwisolver','packaging')})
        if args.case not in VISPY_CASES:
            os.environ['QT_API']='pyqt6'
            os.environ['QT_SCALE_FACTOR']='1'
            from vispy import app
            app.use_app('pyqt6')
            import napari,numba
            from qtpy import API_NAME,QT_VERSION
            assert metadata.version('napari')=='0.9.2' and metadata.version('numba')=='0.68.0'
            assert API_NAME=='PyQt6'
            host_origins={}
            for module in (napari,numba):
                origin=Path(module.__file__).resolve()
                assert origin.is_relative_to(prefix) and not origin.is_relative_to(args.repository.resolve())
                host_origins[module.__name__]=str(origin)
            result['host']=dict(napari=metadata.version('napari'),numba=metadata.version('numba'),qt_binding=API_NAME,qt_version=QT_VERSION,origins=host_origins)
        result['render_attempted']=True
        image,commands,shaders,params=render(args.case,'dawn_headless')
        import numpy as np
        np.save(output/'rgba.npy',image,allow_pickle=False)
        write(output/'commands.json',commands)
        write(output/'shaders.json',shaders)
        write(output/'parameters.json',params)
        assert commands and shaders, 'Actual expanded shaders and GLIR required'
        device=dict(_dawn.device_info())
        result['device']=device
        assert device['ok'] and device['backend']==args.backend, device
        assert args.allow_software or not device['software'], device
        compare_case(args.case,image,reference,params,expected)
        difference=np.abs(image.astype(np.int16)-reference.astype(np.int16))
        result.update(status='PASS_INSTALLED_WHEEL_IMAGE_CASE',process_exit=0,
            compared_pixels=image.shape[0]*image.shape[1],excluded_pixels=0,
            maximum_channel_error=int(difference.max()),differing_bytes=int(np.count_nonzero(difference)),
            alpha_exact=bool(np.array_equal(image[:,:,3],reference[:,:,3])),semantic_observations_exact=True)
    except BaseException:
        result['error']=traceback.format_exc()
        traceback.print_exc()
    finally:
        try:
            if dawn is not None:
                if result['render_attempted']:
                    try:
                        modules=native_modules((args.repository,PRODUCER))
                        write(output/'native-modules.json',modules)
                        required=[package/Path(item['member']).relative_to('vispy') for item in native_origins.values()]
                        assert_wheel_module_origins(modules,package,installed_hashes,required)
                        result['native_origins_verified']=True
                    except BaseException:
                        result.update(status='FAILED_PRESERVED',process_exit=1,native_origin_error=traceback.format_exc())
                try:
                    if result['render_attempted'] and 'device' not in result:result['device']=dict(dawn.device_info())
                finally:
                    dawn.shutdown()
                probe=dict(dawn.probe())
                result['shutdown_zeros']={name:probe[name] for name in SHUTDOWN_FIELDS}
                assert all(value==0 for value in result['shutdown_zeros'].values()), result['shutdown_zeros']
                assert verify_wheel_package(args.wheel,package)==installed_hashes
                result['cleanup_passed']=True
            assert sha(args.wheel)==wheel_hash
            assert {name:sha(PRODUCER/name) for name in SOURCES}==source_hashes
            load_case(args.case,args.reference,producer_root=PRODUCER)
            result['reference_preserved']=True
        except BaseException:
            result.update(status='FAILED_PRESERVED',process_exit=1,cleanup_error=traceback.format_exc())
        result['artifacts']={path.name:sha(path) for path in output.iterdir() if path.is_file()}
        write(output/'result.json',result)
    print(json.dumps(dict(case=args.case,status=result['status'],process_exit=result['process_exit'],
        result=str(output/'result.json'),sha256=sha(output/'result.json'))))
    return result['process_exit']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=CASES,required=True)
    parser.add_argument('--launch-id',required=True)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--backend',choices=('Vulkan','Metal'),required=True)
    parser.add_argument('--allow-software',action='store_true')
    return capture(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
