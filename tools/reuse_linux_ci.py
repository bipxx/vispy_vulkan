# SPDX-License-Identifier: AGPL-3.0-only
"""Reuse one verified original Linux CI input; never grant artifact admission.

Changed native/harness/package inputs or unavailable proof fail explicitly. This
does not silently fall back to a dependency build or rewrite original records.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

try:
    from . import qualification_linux_native as native
    from .build_hygiene import Context, no_alias
except ImportError:
    import qualification_linux_native as native
    from build_hygiene import Context, no_alias

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT/'compat/linux-ci-reuse.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    data=(json.dumps(value,indent=2)+'\n').encode()
    if Path(path).exists():
        # Preserve an existing equivalent Windows-serialized receipt byte for byte.
        if Path(path).read_bytes()!=data and read(path)!=value:
            raise ValueError('Existing immutable reuse report differs: '+str(path))
    else:
        with Path(path).open('xb') as stream:stream.write(data)


def reference(value):
    keys = {'schema','repository','run_id','attempt','source_head','artifact_id',
            'artifact_sha256','artifact_bytes','max_expanded_bytes','production_sha256','recovered_members',
            'driver_sha256','driver_pin_sha256'}
    if set(value) != keys or type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('Unknown Linux reuse reference')
    if value['repository'] != 'bipxx/vispy_vulkan':
        raise ValueError('Wrong original repository')
    for key in ('run_id','attempt','artifact_id','artifact_bytes','max_expanded_bytes'):
        if type(value[key]) is not int or value[key] <= 0:
            raise ValueError('Invalid original artifact limit/identity')
    for key, width in (('source_head',40),('artifact_sha256',64),('production_sha256',64),
                       ('driver_sha256',64),('driver_pin_sha256',64)):
        if len(value[key]) != width or any(c not in '0123456789abcdef' for c in value[key]):
            raise ValueError('Invalid original digest')
    return value


def execute(argv, evidence, label, *, stdout=None, env=None):
    log = Path(stdout) if stdout else evidence/(label+'.log')
    with log.open('xb') as stream:
        child = subprocess.Popen([str(a) for a in argv], stdout=stream, stderr=subprocess.PIPE, env=env)
        _, errors = child.communicate()
    write(evidence/(label+'-process.json'), dict(argv=[str(a) for a in argv], child_pid=child.pid,
          actual_exit=child.returncode, child_waited=True, stderr=errors.decode(errors='replace')))
    if child.returncode:
        raise RuntimeError('Original command failed; log retained: '+label)
    return log


def download(pin, scratch, evidence, *, workflow_path='.github/workflows/linux-vulkan.yml'):
    prefix='repos/'+pin['repository']+'/actions/'
    metadata=execute(['gh','api',prefix+'artifacts/'+str(pin['artifact_id'])],evidence,'original-artifact-api')
    run=execute(['gh','api',prefix+'runs/'+str(pin['run_id'])],evidence,'original-run-api')
    artifact, job = read(metadata), read(run)
    if (artifact['id'] != pin['artifact_id'] or artifact['expired']
        or artifact['size_in_bytes'] != pin['artifact_bytes']
        or artifact['digest'] != 'sha256:'+pin['artifact_sha256']
        or artifact['workflow_run']['id'] != pin['run_id']
        or artifact['workflow_run']['head_sha'] != pin['source_head']
        or job['head_sha'] != pin['source_head'] or job['run_attempt'] != pin['attempt']
        or job['status'] != 'completed' or job['conclusion'] != 'success'
        or job['path'] != workflow_path):
        raise ValueError('Original CI/artifact is unavailable or has another identity')
    return execute(['gh','api',prefix+'artifacts/'+str(pin['artifact_id'])+'/zip'],
                   evidence,'original-artifact-download',stdout=scratch/'original-native.zip')


def import_archive(archive_path, pin, workspace, *, available=()):
    """Immutable byte transport. Existing retained inputs can be referenced once."""
    workspace=Path(workspace)
    if archive_path.stat().st_size != pin['artifact_bytes'] or digest(archive_path) != pin['artifact_sha256']:
        raise ValueError('Original artifact archive digest/size differs')
    existing={(row['sha256'],PurePosixPath(row['member']).name):row['path'] for row in available}
    rows=[]
    def retain(member, raw):
        checksum=hashlib.sha256(raw).hexdigest();name=PurePosixPath(member).name
        if (checksum,name) in existing:
            target=no_alias(workspace/existing[(checksum,name)])
            if digest(target)!=checksum:raise ValueError('Existing retained input changed')
        else:
            target=workspace/'build/artifacts'/checksum/name
            no_alias(target.parent)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                if digest(target)!=checksum:raise ValueError('Hash-addressed input changed')
            else:
                with target.open('xb') as stream:stream.write(raw)
        rows.append(dict(member=member,path=target.relative_to(workspace).as_posix(),sha256=checksum))
    with zipfile.ZipFile(archive_path) as archive:
        infos=archive.infolist()
        if len(infos)>4096 or sum(item.file_size for item in infos)>pin['max_expanded_bytes']:
            raise ValueError('Original artifact exceeds declared transport limits')
        if len({item.filename for item in infos})!=len(infos):raise ValueError('Duplicate archive member')
        for item in infos:
            name=PurePosixPath(item.filename)
            if (name.is_absolute() or '..' in name.parts or '\\' in item.filename or ':' in item.filename
                or str(name)!=item.filename.rstrip('/') or stat.S_ISLNK(item.external_attr>>16)):
                raise ValueError('Noncanonical original artifact member')
            if not item.is_dir():retain(str(name),archive.read(item))
    for recovery in pin['recovered_members']:
        if any(row['member']==recovery['member'] for row in rows):continue
        data=bytes.fromhex(recovery['data_hex'])
        if len(data)>128 or hashlib.sha256(data).hexdigest()!=recovery['sha256']:
            raise ValueError('Invalid exact-byte recovery')
        retain(recovery['member'],data)
    return dict(run_id=pin['run_id'],artifact_id=pin['artifact_id'],members=rows)


def validate_inputs(inventory, pin, source, workspace, *, package_current_python=False,
                    keep_original_description=False):
    """Current source/package plus unchanged original native and harness proof."""
    if keep_original_description and not package_current_python:
        raise ValueError('Original description selection requires current Python packaging')
    try:
        from .qualification_native import source_inputs
    except ImportError:
        from qualification_native import source_inputs
    sys.path.insert(0,str(source/'cmake'))
    from runtime_package import wheel_package_hashes
    schema=workspace/native.SCHEMA
    schema.parent.mkdir(parents=True,exist_ok=True)
    expected=(source/native.SCHEMA).read_bytes()
    if schema.exists():
        if schema.read_bytes()!=expected:raise ValueError('Reuse validation schema differs')
    else:
        with schema.open('xb') as stream:stream.write(expected)
    capture=native.capture_from_inventory(inventory,workspace)
    state=read(workspace/capture['state']['path'])
    objects={row['origin']:workspace/row['file']['path'] for row in capture['files']}
    original=lambda name: objects[str(PurePosixPath(state['evidence'])/name)]
    before=read(original('source-before.json'))
    candidate=read(source/'compat/candidates/tk-state-resource-1/candidate.json')
    runtime=read(source/candidate['runtime_inputs']['path'])
    required=source_inputs(runtime,source)
    if not package_current_python:
        for row in runtime['python']:
            required[row['file']['path']]=row['file']['sha256']
    for row in runtime['licenses']:
        required[row['path']]=row['sha256']
    for name, checksum in required.items():
        if before.get(name)!=checksum or digest(source/name)!=checksum:
            raise ValueError('Changed native/harness/package input; explicit production/package decision required: '+name)
    result,environment=native.validate_capture(capture,native.production_inputs(runtime),workspace)
    if result['production_sha256']!=pin['production_sha256']:
        raise ValueError('Original native production identity differs')
    audit=read(original('archive.json'));wheel=objects[audit['wheel']]
    checked=dict(capture=capture,native=result,environment=environment,wheel=wheel,
                 original=original,objects=objects,schema=schema,required=required)
    if package_current_python:
        try:
            from .repackage_python_wheel import repackage_from_source
        except ImportError:
            from repackage_python_wheel import repackage_from_source
        from runtime_package import source_package_hashes
        expected={row['member']:row['file']['sha256'] for row in runtime['python']}
        if expected != source_package_hashes(source):
            raise ValueError('Current runtime input binding differs from source package')
        output,package=repackage_from_source(wheel.read_bytes(),source,before,
            result['native_output_hashes'],platform='linux',
            suffix='.cpython-312-x86_64-linux-gnu.so',tag='cp312-cp312-linux_x86_64',
            keep_original_description=keep_original_description)
        checked.update(package_bytes=output,package_report=package)
    else:
        wheel_package_hashes(wheel,root=source,suffix='.cpython-312-x86_64-linux-gnu.so',platform='linux')
    return checked


def driver_inputs(checked, inventory, pin, source, workspace):
    """Reuse driver bytes with their original source recipe, not a new build."""
    try:
        from .build_software_vulkan import control_cases
    except ImportError:
        from build_software_vulkan import control_cases
    driver=read(checked['original']('software-driver.json'))
    if (driver['status']!='SOURCE_FUNCTIONAL_NOT_ADMITTED' or driver['qualified'] is not False
        or driver['pin_sha256']!=pin['driver_pin_sha256']
        or digest(source/'compat/software-vulkan-build.json')!=pin['driver_pin_sha256']
        or driver['library']['sha256']!=pin['driver_sha256']):
        raise ValueError('Original software driver/recipe differs')
    original_source=PurePosixPath(read(workspace/checked['capture']['state']['path'])['source'])
    original_inputs={str(PurePosixPath(row['path']).relative_to(original_source)):row['sha256']
                     for row in driver['source_inputs']}
    for name in ('tools/build_software_vulkan.py','compat/patches/mesa-26.1.8-noperspective-axis.patch',
                 'LICENSE','compat/patches/mesa-draw-clip-LICENSE.txt'):
        if original_inputs.get(name)!=digest(source/name):raise ValueError('Changed driver production input: '+name)
    cases=control_cases(checked['original']('software-driver-patched-control.log').read_text(encoding='utf-8'),False)
    if cases!=driver['patched_cases']:raise ValueError('Original driver controls differ')
    matches=[row for row in inventory['members'] if row['sha256']==pin['driver_sha256']
             and PurePosixPath(row['member']).name=='libvulkan_lvp.so']
    if len(matches)!=1:raise ValueError('Original driver library missing/duplicated')
    library=workspace/matches[0]['path']
    if digest(library)!=pin['driver_sha256']:raise ValueError('Retained driver library changed')
    return driver,library


def preferred_driver_source(source, workspace, scratch):
    """Keep the exact release once; do not copy an environment or source tree."""
    item=read(source/'compat/software-vulkan-build.json')['source']
    target=workspace/'build/artifacts'/item['sha256']/item['name']
    if not target.exists():
        retained=source/'build/artifacts'/item['sha256']/item['name']
        if retained.exists():
            if digest(retained)!=item['sha256']:raise ValueError('Existing preferred driver source changed')
            return retained
        temporary=scratch/'driver-source.tar.xz'
        with urllib.request.urlopen(item['url'],timeout=60) as response,temporary.open('xb') as stream:
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>item['size']:raise ValueError('Preferred driver source exceeds pin')
                stream.write(chunk)
        if temporary.stat().st_size!=item['size'] or digest(temporary)!=item['sha256']:
            raise ValueError('Preferred driver source digest/size differs')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream,temporary.open('rb') as original:shutil.copyfileobj(original,stream)
    if target.stat().st_size!=item['size'] or digest(target)!=item['sha256']:
        raise ValueError('Retained preferred source differs')
    return target


def project_driver(checked, inventory, pin, source, workspace, scratch, evidence):
    if sys.platform!='linux':raise ValueError('Fresh software-driver controls require Linux')
    try:
        from .build_software_vulkan import control_cases
    except ImportError:
        from build_software_vulkan import control_cases
    _,library=driver_inputs(checked,inventory,pin,source,workspace)
    preferred=preferred_driver_source(source,workspace,scratch)
    icd=evidence/'reuse-driver-icd.json'
    write(icd,dict(file_format_version='1.0.0',ICD=dict(api_version='1.3.0',library_path=str(library))))
    binary=scratch/'reuse-vulkan-control'
    argv=['/usr/bin/c++','-std=c++20','-O1',
          '-I'+str(source/'third_party/dawn/third_party/vulkan-headers/src/include'),
          '-I'+str(source/'third_party/dawn/third_party/spirv-headers/src/include'),
          str(source/'tools/vulkan_interpolation_control.cpp'),'-l:libvulkan.so.1','-o',str(binary)]
    execute(argv,evidence,'reuse-driver-control-build')
    env=dict(os.environ,VK_DRIVER_FILES=str(icd),VK_ICD_FILENAMES=str(icd),
             PYTHONDONTWRITEBYTECODE='1',XDG_CACHE_HOME=str(scratch/'cache'))
    log=execute([str(binary)],evidence,'reuse-driver-control',env=env)
    cases=control_cases(log.read_text(encoding='utf-8'),False)
    result=dict(status='REUSED_SOURCE_FUNCTIONAL_NOT_ADMITTED',qualified=False,
                library=dict(path=str(library),sha256=digest(library)),
                source=dict(path=str(preferred),sha256=digest(preferred)),
                control_source_sha256=digest(source/'tools/vulkan_interpolation_control.cpp'),
                patched_cases=cases,environment=dict(VK_DRIVER_FILES=str(icd),VK_ICD_FILENAMES=str(icd)))
    write(evidence/'reuse-driver-result.json',result)
    return result


def wheel_requirement(wheel, evidence):
    """Install the verified retained wheel, never its original runner path."""
    wheel = Path(wheel).absolute()
    path = evidence/'wheel-requirements.txt'
    data = ('vispy @ '+wheel.as_uri()+' --hash=sha256:'+digest(wheel)+'\n').encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Existing wheel installation reference differs')
    else:
        with path.open('xb') as stream:
            stream.write(data)
    return path


def transport_retention(inventory, workspace, evidence, *, kind='original-linux-ci-reuse-inputs'):
    # Record original inputs before candidate validation can reject reuse.
    retained = []
    for row in inventory['members']:
        path = workspace/row['path']
        if digest(path) != row['sha256']:
            raise ValueError('Retained transport input changed')
        roles = ['evidence', 'repro']
        if path.suffix == '.zip': roles += ['source', 'licenses']
        retained.append(dict(path=str(path), sha256=row['sha256'], roles=roles))
    write(evidence/'reuse-transport-inputs.json', dict(schema=1,
          kind=kind, artifact_admitted=False,
          original_run=inventory['run_id'], retained=retained))
    return retained


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--owner',default='ci')
    parser.add_argument('--reference',type=Path,default=REFERENCE)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--available-index',type=Path)
    parser.add_argument('--metadata-only',action='store_true')
    parser.add_argument('--package-current-python',action='store_true',
                        help='Audit and assemble current pure sources around unchanged proved native outputs')
    parser.add_argument('--keep-original-description',action='store_true',
                        help='Keep the original wheel description when only the repository README differs')
    args=parser.parse_args()
    if args.keep_original_description and not args.package_current_python:
        parser.error('--keep-original-description requires --package-current-python')
    workspace=no_alias(args.workspace.absolute())
    context=Context(workspace,ROOT/'compat/build-hygiene.json',None)
    scratch=context.scratch(args.run_id);context.marker(scratch,args.run_id,args.owner)
    evidence=workspace/'build/runs'/args.run_id;evidence.mkdir(parents=True,exist_ok=True)
    context.check_capacity(0,0)
    pin=reference(read(args.reference))
    archive=args.archive or download(pin,scratch,evidence)
    available=read(args.available_index)['members'] if args.available_index else []
    inventory=import_archive(archive,pin,workspace,available=available)
    write(evidence/'reuse-original-inventory.json',inventory)
    original_inputs=transport_retention(inventory,workspace,evidence)
    if args.package_current_python:
        checked=validate_inputs(inventory,pin,ROOT,workspace,package_current_python=True,
                                keep_original_description=args.keep_original_description)
        original_wheel=checked['wheel']
        if checked['package_report']['changed_members']:
            output=checked['package_bytes'];checksum=hashlib.sha256(output).hexdigest()
            target=no_alias(workspace/'build/artifacts'/checksum/original_wheel.name)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                if digest(target)!=checksum:raise ValueError('Existing assembled wheel changed')
            else:
                with target.open('xb') as stream:stream.write(output)
            checked['wheel']=target
        write(evidence/'reuse-python-package.json',dict(checked['package_report'],
              original_wheel=dict(path=str(original_wheel),sha256=digest(original_wheel)),
              assembled_wheel=dict(path=str(checked['wheel']),sha256=digest(checked['wheel'])),
              production_sha256=checked['native']['production_sha256']))
    else:
        checked=validate_inputs(inventory,pin,ROOT,workspace)
    write(evidence/'reuse-original-capture.json',checked['capture'])
    write(evidence/'reuse-native-result.json',checked['native'])
    wheel_requirement(checked['wheel'],evidence)
    if not args.metadata_only:
        driver=project_driver(checked,inventory,pin,ROOT,workspace,scratch,evidence)
        if os.environ.get('GITHUB_ENV'):
            with Path(os.environ['GITHUB_ENV']).open('a') as stream:
                for key,value in {**driver['environment'],'WHEEL_PATH':str(checked['wheel'])}.items():
                    stream.write(key+'='+value+'\n')
    retained={item['path']:item for item in original_inputs}
    if args.package_current_python:
        retained[str(checked['wheel'])]=dict(path=str(checked['wheel']),sha256=digest(checked['wheel']),
                                             roles=['source','evidence','licenses','repro'])
    retained[str(checked['schema'])]=dict(path=str(checked['schema']),sha256=digest(checked['schema']),roles=['source','evidence'])
    if not args.metadata_only:
        item=driver['source'];retained[item['path']]=dict(**item,roles=['source','licenses','repro'])
    write(evidence/'reuse-inputs.json',dict(schema=1,kind='original-linux-ci-reuse-inputs',
          artifact_admitted=False,original_run=pin['run_id'],retained=list(retained.values())))
    print(json.dumps(dict(status='VERIFIED_ORIGINAL_NATIVE_PREREQUISITE',
                         production_sha256=checked['native']['production_sha256'],artifact_admitted=False)))


if __name__=='__main__':
    main()
