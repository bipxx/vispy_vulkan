# SPDX-License-Identifier: AGPL-3.0-only
"""Tiny synthetic workspaces test real process receipts and managed cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import linux_ci_lifecycle as lifecycle
from tools.build_hygiene import digest


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    policy = tmp_path/'synthetic-policy.json'
    policy.write_text(json.dumps(dict(schema=1, max_scratch_bytes=32*1024**2,
                                     min_free_bytes=0, managed_root='build/work')))
    monkeypatch.setattr(lifecycle, 'POLICY', policy)
    source = tmp_path/'source'
    source.mkdir()
    for name in ('LICENSE', 'LICENSE-BSD', 'LICENSING.md', 'CMakeLists.txt'):
        (source/name).write_text('Explicit synthetic source/license fixture\n')
    state = lifecycle.initialize(source, tmp_path/'workspace', 'unit-1', 'unit', 1024)
    return state


def command(state, phase='control', code=0):
    return lifecycle.run_command(state, phase,
        [sys.executable, '-I', '-B', '-c', 'print("synthetic");raise SystemExit(%d)' % code], interval=.1)


def test_complete_lifecycle_keeps_evidence_and_removes_only_scratch(prepared):
    receipt = command(prepared)
    assert receipt['actual_exit'] == 0 and receipt['child_waited'] is True
    assert receipt['child_pid'] > 0
    state = json.loads(prepared.read_bytes())
    result = lifecycle.finish(prepared)
    assert result['status'] == 'PASS_APPLY'
    assert not Path(state['scratch']).exists()
    manifest = json.loads((prepared.parent/'terminal.json').read_bytes())
    assert manifest['state'] == 'succeeded' and manifest['process_exit'] == 0
    for row in manifest['retained']: assert digest(Path(row['path'])) == row['sha256']
    assert Path(state['source']).is_dir()


def test_failed_child_has_truthful_exit_and_reproducer(prepared):
    with pytest.raises(RuntimeError): command(prepared, code=7)
    receipt = json.loads((prepared.parent/'control-process.json').read_bytes())
    assert receipt['actual_exit'] == 7 and receipt['child_waited'] is True
    lifecycle.finish(prepared)
    manifest = json.loads((prepared.parent/'terminal.json').read_bytes())
    assert manifest['state'] == 'failed' and manifest['process_exit'] == 7
    assert {'source', 'evidence', 'licenses', 'repro'} <= {role for r in manifest['retained'] for role in r['roles']}


def test_live_unawaited_record_refuses_cleanup(prepared):
    state = json.loads(prepared.read_bytes())
    state['active'] = dict(pid=os.getpid(), phase='unfinished')
    lifecycle.write(prepared, state)
    with pytest.raises(ValueError, match='awaited'): lifecycle.finish(prepared)
    assert Path(state['scratch']).is_dir()


def test_same_phase_cannot_replace_its_original_receipt(prepared):
    command(prepared)
    original = (prepared.parent/'control-process.json').read_bytes()
    with pytest.raises(ValueError, match='already executed'): command(prepared)
    assert (prepared.parent/'control-process.json').read_bytes() == original
    lifecycle.finish(prepared)


def test_existing_lease_cannot_be_adopted(prepared):
    state = json.loads(prepared.read_bytes())
    with pytest.raises(ValueError, match='already exists'):
        lifecycle.initialize(Path(state['source']), Path(state['workspace']), 'unit-1', 'unit', 1)


def test_source_mutation_is_retained_and_fails_after_cleanup(prepared):
    command(prepared)
    state = json.loads(prepared.read_bytes())
    (Path(state['source'])/'CMakeLists.txt').write_text('Changed synthetic source\n')
    with pytest.raises(RuntimeError, match='retained and cleaned'): lifecycle.finish(prepared)
    assert not Path(state['scratch']).exists()
    assert (prepared.parent/'changed-source.zip').is_file()
    assert json.loads((prepared.parent/'terminal.json').read_bytes())['state'] == 'failed'


def test_budget_guard_stops_and_waits_for_its_owned_child(prepared, monkeypatch):
    def stop(context): raise ValueError('synthetic capacity refusal')
    monkeypatch.setattr(lifecycle, 'check_space', stop)
    with pytest.raises(RuntimeError):
        lifecycle.run_command(prepared, 'budget', [sys.executable, '-I', '-B', '-c',
                                                  'import time;time.sleep(60)'], interval=.05)
    receipt = json.loads((prepared.parent/'budget-process.json').read_bytes())
    assert receipt['child_waited'] is True
    assert receipt['actual_exit'] != 0
    assert 'capacity refusal' in receipt['observer_error']
    lifecycle.finish(prepared)


def test_build_outputs_survive_cleanup_by_hash(prepared):
    state = json.loads(prepared.read_bytes())
    build = Path(state['scratch'])/'native'; build.mkdir()
    (build/'CMakeCache.txt').write_text('Synthetic cache\n')
    (build/'_dawn.synthetic.so').write_bytes(b'not a native module; explicit unit fixture')
    command(prepared, phase='wheel-build')
    report = json.loads((prepared.parent/'wheel-build-build-inputs-outputs.json').read_bytes())
    lifecycle.finish(prepared)
    assert Path(report['_dawn.synthetic.so']['path']).read_bytes().startswith(b'not a native')
    assert not build.exists()


def test_protected_owned_cache_is_not_sent_to_uv_cleanup(prepared):
    command(prepared)
    state = json.loads(prepared.read_bytes())
    workspace = Path(state['workspace'])
    cache = workspace/'build/cache'/state['run_id']; cache.mkdir(parents=True)
    payload = cache/'synthetic-protected-input'; payload.write_text('preserve')
    registry = workspace/'build/.hygiene/registry.json'; registry.parent.mkdir()
    registry.write_text(json.dumps(dict(schema=1, protected_roots=[str(cache)], blocked_roots=[])))
    with pytest.raises(ValueError, match='protected/blocked'): lifecycle.finish(prepared)
    assert payload.read_text() == 'preserve'
    assert not (prepared.parent/'cache-clean-process.json').exists()


def test_policy_cannot_change_after_registration(prepared):
    original = lifecycle.POLICY.read_bytes()
    data = json.loads(original); data['max_scratch_bytes'] *= 2
    lifecycle.POLICY.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='policy changed'): command(prepared)
    assert json.loads(prepared.read_bytes())['commands'] == []
    lifecycle.POLICY.write_bytes(original)
    command(prepared)
    lifecycle.finish(prepared)


if os.name == 'posix':
    # These operations are used by Linux CI. Windows never collects a skipped
    # substitute; the Linux/WSL source suite executes the real alias controls.
    def test_uv_alias_materialization_preserves_original_targets(prepared, tmp_path):
        state, context = lifecycle.load(prepared)
        env = Path(state['scratch'])/'env'; (env/'bin').mkdir(parents=True)
        (env/'lib').mkdir()
        base = tmp_path/'base/bin'; base.mkdir(parents=True)
        interpreter = base/'python3.12'; interpreter.write_bytes(b'synthetic interpreter')
        (env/'pyvenv.cfg').write_text('home = '+str(base)+'\n')
        (env/'bin/python').symlink_to(interpreter)
        (env/'bin/python3').symlink_to('python')
        (env/'lib64').symlink_to('lib', target_is_directory=True)
        command(prepared)
        assert not (env/'lib64').is_symlink()
        assert not (env/'bin/python').is_symlink() and not (env/'bin/python3').is_symlink()
        assert (env/'bin/python3').read_bytes() == interpreter.read_bytes()
        lifecycle.finish(prepared)
        assert interpreter.read_bytes() == b'synthetic interpreter'

    def test_native_alias_chain_is_unlinked_without_following_it(prepared):
        state = json.loads(prepared.read_bytes())
        build = Path(state['scratch'])/'native'; build.mkdir()
        (build/'libfixture.so.1').write_bytes(b'synthetic intermediate')
        (build/'libfixture.so').symlink_to('libfixture.so.0')
        (build/'libfixture.so.0').symlink_to('libfixture.so.1')
        command(prepared)
        lifecycle.finish(prepared)
        plan = json.loads((prepared.parent/'native-alias-cleanup.json').read_bytes())
        assert len(plan['links']) == 2

    def test_standalone_runtime_is_copied_with_the_interpreter(prepared, tmp_path):
        state, context = lifecycle.load(prepared)
        env = Path(state['scratch'])/'env'; (env/'bin').mkdir(parents=True)
        (env/'lib').mkdir()
        base = tmp_path/'standalone'; (base/'bin').mkdir(parents=True)
        (base/'lib').mkdir()
        interpreter = base/'bin/python3.12'; interpreter.write_bytes(b'synthetic executable')
        library = base/'lib/libpython3.12.so.1.0'; library.write_bytes(b'synthetic shared runtime')
        (env/'pyvenv.cfg').write_text('home = '+str(base/'bin')+'\n')
        (env/'bin/python').symlink_to(interpreter)
        command(prepared)
        assert (env/'lib/libpython3.12.so.1.0').read_bytes() == library.read_bytes()
        assert not (env/'bin/python').is_symlink()
        lifecycle.finish(prepared)
        assert library.read_bytes() == b'synthetic shared runtime'

    def test_existing_runtime_is_not_replaced(prepared, tmp_path):
        state, context = lifecycle.load(prepared)
        env = Path(state['scratch'])/'env'; (env/'lib').mkdir(parents=True)
        base = tmp_path/'standalone'; (base/'bin').mkdir(parents=True)
        (base/'lib').mkdir()
        (base/'lib/libpython3.12.so.1.0').write_bytes(b'base runtime')
        target = env/'lib/libpython3.12.so.1.0'; target.write_bytes(b'different existing runtime')
        (env/'pyvenv.cfg').write_text('home = '+str(base/'bin')+'\n')
        with pytest.raises(ValueError, match='Existing environment libpython differs'):
            lifecycle.normalize_environments(state, context, 'mismatch')
        assert target.read_bytes() == b'different existing runtime'

    if sys.platform == 'linux':
        def test_actual_cli_preserves_stdin_script_bytes(prepared):
            body = b"printf 'synthetic CLI transport\\n'\n"
            program = ('import sys;from pathlib import Path;from tools import linux_ci_lifecycle as m;'
                       'm.POLICY=Path('+repr(str(lifecycle.POLICY))+');'
                       'sys.argv=["lifecycle","--state",'+repr(str(prepared))+',"run",'
                       '"--phase","cli-control","--script-stdin"];raise SystemExit(m.main())')
            result = subprocess.run([sys.executable, '-B', '-c', program], cwd=lifecycle.ROOT,
                                    input=body, capture_output=True)
            assert result.returncode == 0, result.stderr + result.stdout
            assert (prepared.parent/'cli-control.sh').read_bytes() == body
            assert (prepared.parent/'cli-control.log').read_bytes() == b'synthetic CLI transport\n'
            lifecycle.finish(prepared)
