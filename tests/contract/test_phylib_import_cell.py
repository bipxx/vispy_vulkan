# SPDX-License-Identifier: AGPL-3.0-only
"""Source-copy admission checks must run before any real host imports."""
from pathlib import Path
import hashlib
import json
import pytest
from tools import phylib_import_cell as cell


@pytest.fixture
def source(tmp_path):
    root=tmp_path/'source';package=root/'phylib';package.mkdir(parents=True)
    (root/'LICENSE').write_text('Original source notice\n')
    (package/'__init__.py').write_text('__version__="fixture"\n')
    (package/'module.py').write_text('VALUE=7\n')
    pin=dict(package_directory='phylib',source_tree_sha256=cell.inventory.source_inventory(root)['sha256'],
        package_tree_sha256=cell.inventory.source_inventory(package)['sha256'])
    return root,pin


def test_package_is_copied_unchanged_without_distribution_metadata(tmp_path,source):
    root,pin=source;dest=tmp_path/'installed/phylib'
    assert cell.install_source(root,dest,pin)==dest.resolve()
    assert cell.inventory.source_inventory(dest)['sha256']==pin['package_tree_sha256']
    assert sorted(p.name for p in dest.parent.iterdir())==['phylib']


@pytest.mark.parametrize('changed',('root','package'))
def test_mismatching_source_is_refused_before_copy(tmp_path,source,changed):
    root,pin=source
    pin['source_tree_sha256' if changed=='root' else 'package_tree_sha256']='0'*64
    dest=tmp_path/'installed/phylib'
    with pytest.raises(AssertionError):cell.install_source(root,dest,pin)
    assert not dest.exists()


def test_existing_package_is_preserved(tmp_path,source):
    root,pin=source;dest=tmp_path/'installed/phylib';dest.mkdir(parents=True)
    (dest/'old.py').write_bytes(b'original')
    with pytest.raises(AssertionError):cell.install_source(root,dest,pin)
    assert (dest/'old.py').read_bytes()==b'original'


@pytest.fixture
def observation():
    pin=dict(version='2.7.1',import_probe_modules=['phylib','phylib.utils'],source_tree_sha256='source',package_tree_sha256='package')
    record=dict(status='PASS_PHYLIB_LINUX_IMPORT_ONLY',host='phylib',scope='import-only',
        rendering=False,rendering_qualified=False,release_qualified=False,python='3.12.8 test',platform='Linux-test',
        errors=[],loaded_vispy_modules=[],loaded_qt_modules=[],modules=[dict(name='phylib',version='2.7.1'),dict(name='phylib.utils')],
        source_tree_sha256='source',package_tree_sha256='package',package_source_sha256='package')
    return pin,record


def test_complete_cpu_observation_is_admissible(observation):
    pin,record=observation
    cell.validate_observation(record,pin)


@pytest.mark.parametrize('change',('module','source','python','renderer','failure'))
def test_partial_or_different_observations_cannot_be_admitted(observation,change):
    pin,record=observation
    if change=='module':record['modules'].pop()
    elif change=='source':record['source_tree_sha256']='other'
    elif change=='python':record['python']='3.12.9 test'
    elif change=='renderer':record['loaded_vispy_modules']=['vispy']
    else:record['errors']=['import failed']
    with pytest.raises(AssertionError):cell.validate_observation(record,pin)


def test_published_linux_cpu_cell_joins_exact_source_requirements_and_imports():
    root=Path(__file__).resolve().parents[2]
    pin=cell.inventory.read_hosts(root/'compat/hosts.lock.toml')['phylib']
    profile=pin['linux_environment']
    admission=json.loads((root/'compat/qualifications/phylib/linux-x11/3.12.8/none/admission.json').read_bytes())
    for file_key,hash_key in (('requirements','requirements_sha256'),('import_inventory','import_inventory_sha256')):
        assert hashlib.sha256((root/profile[file_key]).read_bytes()).hexdigest()==profile[hash_key]
    assert admission['requirements_file']==profile['requirements']
    assert admission['requirements_sha256']==profile['requirements_sha256']
    assert admission['import_inventory_sha256']==profile['import_inventory_sha256']
    assert admission['scope']=='import-only' and not admission['rendering'] and not admission['release_qualified']
    record=json.loads((root/profile['import_inventory']).read_bytes())
    cell.validate_observation(record,pin)
    assert len(record['modules'])==12
