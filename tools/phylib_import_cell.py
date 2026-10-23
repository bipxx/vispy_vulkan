# SPDX-License-Identifier: AGPL-3.0-only
"""Install the unchanged pinned phylib source and verify the Linux CPU import cell."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import sys
import sysconfig

sys.path.insert(0,str(Path(__file__).resolve().parent))
import host_inventory as inventory
sys.path.pop(0)


def install_source(source, destination, pin):
    """Copy verified upstream package bytes; never invent distribution metadata."""
    source=Path(source).resolve(strict=True)
    destination=Path(destination).resolve()
    assert not destination.exists(), 'A fresh phylib package destination is required'
    assert inventory.source_inventory(source)['sha256']==pin['source_tree_sha256']
    package=source/pin['package_directory']
    assert inventory.source_inventory(package)['sha256']==pin['package_tree_sha256']
    shutil.copytree(package,destination)
    assert inventory.source_inventory(destination)['sha256']==pin['package_tree_sha256']
    return destination


def validate_observation(record,pin):
    assert record['status']=='PASS_PHYLIB_LINUX_IMPORT_ONLY'
    assert record['host']=='phylib' and record['scope']=='import-only'
    assert record['rendering'] is False and record['rendering_qualified'] is False and record['release_qualified'] is False
    assert record['python'].startswith('3.12.8 ') and record['platform'].startswith('Linux-')
    assert record['errors']==[] and record['loaded_vispy_modules']==[] and record['loaded_qt_modules']==[]
    assert [module['name'] for module in record['modules']]==pin['import_probe_modules']
    assert record['modules'][0]['version']==pin['version']
    assert record['source_tree_sha256']==pin['source_tree_sha256']
    assert record['package_tree_sha256']==record['package_source_sha256']==pin['package_tree_sha256']


def run(source, output, *, lock=inventory.LOCK):
    assert not sys.flags.optimize and sys.flags.isolated and sys.flags.dont_write_bytecode
    assert sys.prefix!=sys.base_prefix, 'Use a newly created isolated dependency environment'
    assert platform.system()=='Linux' and platform.machine()=='x86_64'
    assert platform.python_version()=='3.12.8'
    output=Path(output).resolve()
    assert not output.exists(), 'Preserve earlier import observations'
    pin=inventory.read_hosts(lock)['phylib']
    destination=Path(sysconfig.get_paths()['purelib']).resolve()/'phylib'
    assert destination.is_relative_to(Path(sys.prefix).resolve())
    install_source(source,destination,pin)
    record=inventory.probe('phylib',lock)
    expected=pin['import_probe_modules']
    passed=(not record['errors'] and [m['name'] for m in record['modules']]==expected
        and record.get('package_tree_sha256')==pin['package_tree_sha256']
        and not record['loaded_vispy_modules'] and not record['loaded_qt_modules'])
    record.update(status='PASS_PHYLIB_LINUX_IMPORT_ONLY' if passed else 'FAILED_PHYLIB_LINUX_IMPORT_ONLY',
        source_tree_sha256=pin['source_tree_sha256'],package_source_sha256=pin['package_tree_sha256'],
        installation='unchanged verified upstream source package copy; no generated distribution metadata',
        rendering=False,scope='import-only',release_qualified=False)
    if passed:validate_observation(record,pin)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2,sort_keys=True)
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lock',type=Path,default=inventory.LOCK)
    args=parser.parse_args()
    code=run(args.source,args.output,lock=args.lock)
    print(json.dumps(dict(status='passed' if code==0 else 'failed',rendering=False,scope='import-only')))
    return code


if __name__=='__main__':raise SystemExit(main())
