# SPDX-License-Identifier: AGPL-3.0-only
"""Release projection and independent-control semantics; no compiler or device."""
import copy
import io
import json
from pathlib import Path
import tarfile

import pytest
from tools import build_software_vulkan as driver


@pytest.fixture
def live_context(tmp_path):
    policy = tmp_path / 'policy.json'
    policy.write_text(json.dumps(dict(schema=1, managed_root='build/work', max_scratch_bytes=1024 * 1024,
                                     min_free_bytes=0)))
    context = driver.Context(tmp_path, policy, None)
    context.preflight(driver.SimpleNamespace(run_id='live', owner='test',
        expected_peak_bytes=1024, register=True))
    return context, context.scratch('live')


@pytest.mark.parametrize('over_budget', [False, True])
def test_live_guard_tolerates_disappearing_compiler_file_but_keeps_profile_limit(live_context, monkeypatch, over_budget):
    context, scratch = live_context
    vanished = scratch / 'temporary.o.d'
    vanished.write_bytes(b'transient')
    (scratch / 'resident.o').write_bytes(b'x' * 512)
    original = Path.lstat
    def stat(path, *args, **kwargs):
        if path == vanished:
            raise FileNotFoundError(str(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', stat)
    if over_budget:
        with pytest.raises(RuntimeError, match='bounded profile'):
            driver.check_live_space(context, scratch, 'live', 'test', 256)
    else:
        driver.check_live_space(context, scratch, 'live', 'test', 1024)


def test_live_guard_preserves_other_io_errors(live_context, monkeypatch):
    context, scratch = live_context
    denied = scratch / 'denied.o'
    denied.write_bytes(b'object')
    original = Path.lstat
    def stat(path, *args, **kwargs):
        if path == denied:
            raise PermissionError(str(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', stat)
    with pytest.raises(PermissionError):
        driver.check_live_space(context, scratch, 'live', 'test', 1024)


def test_live_guard_enforces_aggregate_budget(live_context):
    context, scratch = live_context
    other = context.work / 'another-live-owner'
    other.mkdir()
    (other / 'resident.o').write_bytes(b'x' * (1024 * 1024))
    with pytest.raises(RuntimeError, match='managed scratch budget'):
        driver.check_live_space(context, scratch, 'live', 'test', 2 * 1024 * 1024)


def test_live_guard_keeps_owner_check(live_context):
    context, scratch = live_context
    with pytest.raises(ValueError, match='owner/identity'):
        driver.check_live_space(context, scratch, 'live', 'wrong-owner', 1024)


def test_terminal_snapshot_still_refuses_a_disappearing_file(live_context, monkeypatch):
    context, scratch = live_context
    vanished = scratch / 'temporary.o.d'
    vanished.write_bytes(b'transient')
    lstat, stat = Path.lstat, Path.stat
    def disappearing(original):
        def sample(path, *args, **kwargs):
            if path == vanished:
                raise FileNotFoundError(str(path))
            return original(path, *args, **kwargs)
        return sample
    monkeypatch.setattr(Path, 'lstat', disappearing(lstat))
    monkeypatch.setattr(Path, 'stat', disappearing(stat))
    driver.check_live_space(context, scratch, 'live', 'test', 1024)
    with pytest.raises(FileNotFoundError):
        context.snapshot(scratch)


@pytest.mark.parametrize('old_guard', [False, True])
def test_build_entry_uses_live_guard_before_compiler_work(tmp_path, monkeypatch, old_guard):
    """Exercise the actual nested guard, stopping before any compiler process."""
    policy = tmp_path / 'policy.json'
    policy.write_text(json.dumps(dict(schema=1, managed_root='build/work',
        max_scratch_bytes=8 * 1024**3, min_free_bytes=0)))
    context = driver.Context(tmp_path, policy, None)
    args = driver.SimpleNamespace(run_id='live', owner='test', expected_peak_bytes=0, register=True)
    context.preflight(args)
    scratch = context.scratch('live')
    vanished = scratch / 'temporary.o.d'
    vanished.write_bytes(b'transient')
    def disappear(original):
        def sample(path, *a, **kw):
            if path == vanished:
                raise FileNotFoundError(str(path))
            return original(path, *a, **kw)
        return sample
    monkeypatch.setattr(Path, 'lstat', disappear(Path.lstat))
    monkeypatch.setattr(Path, 'stat', disappear(Path.stat))
    monkeypatch.setattr(driver, 'Context', lambda *a, **kw: context)
    monkeypatch.setattr(driver.sys, 'platform', 'linux')
    if not hasattr(driver.os, 'statvfs'):
        monkeypatch.setattr(driver.os, 'statvfs', lambda path: driver.SimpleNamespace(f_flag=0), raising=False)
    if not hasattr(driver.os, 'ST_RDONLY'):
        monkeypatch.setattr(driver.os, 'ST_RDONLY', 1, raising=False)
    if old_guard:
        monkeypatch.setattr(driver, 'check_live_space', lambda *a: context.preflight(
            driver.SimpleNamespace(run_id='live', owner='test', expected_peak_bytes=0, register=False)))
    class BeforeCompiler(RuntimeError):
        pass
    original_digest = driver.digest
    reached = []
    def digest(path):
        if Path(path).as_posix() == '/usr/bin/cc':
            reached.append('compiler-origin')
            raise BeforeCompiler('No compiler or native producer command executed')
        return original_digest(path)
    monkeypatch.setattr(driver, 'digest', digest)
    expected = FileNotFoundError if old_guard else BeforeCompiler
    with pytest.raises(expected):
        driver.build('live', 'test', tmp_path / 'producer.json', workspace=tmp_path)
    assert reached == ([] if old_guard else ['compiler-origin'])
    record = json.loads((tmp_path / 'producer.json').read_bytes())
    assert record['commands'] == [] and record['qualified'] is False


def source_tar(path, entries):
    with tarfile.open(path, 'w') as archive:
        for name, data, link in entries:
            member = tarfile.TarInfo(name)
            if link is not None:
                member.type = tarfile.SYMTYPE
                member.linkname = link
                archive.addfile(member)
            else:
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))


def test_release_aliases_are_regular_and_dangling_hook_is_recorded(tmp_path):
    archive = tmp_path / 'source.tar'
    source_tar(archive, [('mesa-n/include/value.h', b'original header', None),
                         ('mesa-n/include/alias.h', b'', 'value.h'),
                         ('mesa-n/bin/ci/pipeline_message.py', b'', '../../.marge/hooks/pipeline_message.py')])
    destination = tmp_path / 'source'
    projection = driver.project_source(archive, destination)
    assert (destination / 'include/alias.h').read_bytes() == b'original header'
    assert not (destination / 'include/alias.h').is_symlink()
    assert not (destination / 'bin/ci/pipeline_message.py').exists()
    assert len(projection) == 2


def test_other_missing_source_link_is_not_silently_omitted(tmp_path):
    archive = tmp_path / 'source.tar'
    source_tar(archive, [('mesa-n/include/value.h', b'', 'missing.h')])
    with pytest.raises(ValueError, match='unresolved release link'):
        driver.project_source(archive, tmp_path / 'source')


def controls(baseline):
    lines = []
    for clipped in (False, True):
        for linear in (False, True):
            lines.append('CASE ' + json.dumps(dict(clipped=clipped, noperspective=linear,
                covered=256 if clipped else 120, mismatches=40 if baseline and clipped and linear else 0)))
    return '\n'.join(lines) + '\nTERMINAL device_waited=true objects_destroyed=true\n'


def test_control_parser_preserves_expected_failure_and_terminal_cleanup():
    assert len(driver.control_cases(controls(True), True)) == 4
    assert len(driver.control_cases(controls(False), False)) == 4
    with pytest.raises(ValueError, match='baseline'):
        driver.control_cases(controls(False), True)
    with pytest.raises(ValueError, match='patched'):
        driver.control_cases(controls(True), False)
    with pytest.raises(ValueError, match='cleanup'):
        driver.control_cases(controls(False).replace('device_waited=true', 'device_waited=false'), False)
    with pytest.raises(ValueError, match='incomplete'):
        driver.control_cases(controls(False).replace('"clipped": false, "noperspective": true',
                                                     '"clipped": false, "noperspective": false'), False)


@pytest.mark.parametrize('change', ['opengl', 'fallback', 'duplicate', 'conflict'])
def test_recipe_cannot_change_the_observed_configuration(change):
    pin = json.loads(driver.PIN.read_bytes())
    driver.validate_recipe(pin)
    pin = copy.deepcopy(pin)
    if change in ('opengl', 'fallback'):
        original = '-Dopengl=false' if change == 'opengl' else '--wrap-mode=nofallback'
        pin['flags'].remove(original)
    elif change == 'duplicate':
        pin['flags'].append(pin['flags'][0])
    else:
        pin['flags'].append('-Dopengl=true')
    with pytest.raises(ValueError, match='configuration'):
        driver.validate_recipe(pin)


@pytest.mark.parametrize('awaited', [True, False])
def test_completed_producer_cleanup_keeps_evidence_and_refuses_unawaited_work(tmp_path, awaited):
    scratch = tmp_path / 'build/work/synthetic'
    scratch.mkdir(parents=True)
    (scratch / '.build-hygiene-owner.json').write_text(json.dumps(
        dict(schema=1, run_id='synthetic', owner='test')))
    payload = scratch / 'discard.tmp'
    payload.write_bytes(b'disposable')
    source = tmp_path / 'source.txt'
    source.write_bytes(b'synthetic source and license, not native proof')
    output = tmp_path / 'producer.json'
    output.write_text(json.dumps(dict(run_id='synthetic', owner='test',
        status='SOURCE_FUNCTIONAL_NOT_ADMITTED', commands=[dict(child_waited=awaited)],
        retained=[dict(path=str(source), sha256=driver.digest(source),
                       roles=['source','licenses','repro'])])))
    if not awaited:
        with pytest.raises(ValueError, match='unawaited'):
            driver.cleanup_record('synthetic','test',output,0,workspace=tmp_path)
        assert payload.exists()
    else:
        result = driver.cleanup_record('synthetic','test',output,0,workspace=tmp_path)
        assert result['status'] == 'PASS_APPLY'
        assert source.read_bytes() == b'synthetic source and license, not native proof'
        assert not scratch.exists() or not list(scratch.iterdir())


def test_driver_store_can_be_external_without_relaxing_scratch_boundaries(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    workspace = tmp_path / 'external'
    source.mkdir()
    workspace.mkdir()
    monkeypatch.setattr(driver, 'ROOT', source)
    assert driver.library_store_path(workspace) == source / 'build/artifacts'
    assert driver.library_store_path(workspace, workspace / 'build/artifacts') == workspace / 'build/artifacts'
    with pytest.raises(ValueError, match='outside scratch'):
        driver.library_store_path(workspace, workspace / 'build/work/driver')
    nested = source / 'build/work/nested'
    with pytest.raises(ValueError, match='outside scratch'):
        driver.library_store_path(nested, nested / 'build/artifacts')
    with pytest.raises(ValueError, match='selected workspace'):
        driver.library_store_path(workspace, tmp_path / 'unowned')


def test_relocated_library_is_byte_identical_and_conflicting_origin_is_preserved(tmp_path):
    library = tmp_path / 'libvulkan_lvp.so'
    library.write_bytes(b'synthetic library bytes, not an ELF or functional proof')
    store = tmp_path / 'external/build/artifacts'
    retained = driver.retain_library_file(library, store)
    assert retained == store / driver.digest(library) / library.name
    assert retained.read_bytes() == library.read_bytes()
    assert driver.retain_library_file(library, store) == retained
    retained.write_bytes(b'conflicting retained origin')
    with pytest.raises(ValueError, match='retained library differs'):
        driver.retain_library_file(library, store)
    assert retained.read_bytes() == b'conflicting retained origin'
