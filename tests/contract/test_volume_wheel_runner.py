# SPDX-License-Identifier: AGPL-3.0-only
"""Host dependencies, per-case identity and environment teardown without graphics."""
import json
import os
from pathlib import Path
import sys
import pytest
from tools import volume_wheel_runner as runner


def test_owned_environment_installs_locked_hosts_and_removes_only_its_root(tmp_path, monkeypatch):
    wheel = tmp_path / 'archive.whl'
    wheel.write_bytes(b'CPU control; not installed')
    calls = []

    def logged(arguments, *, cwd, environment, log):
        calls.append([str(value) for value in arguments])
        if '-c' in arguments:
            # The identity is outside either repository, as the real worker is.
            prefix = Path(arguments[0]).parent.parent
            log.write_text(json.dumps(dict(prefix=str(prefix), executable=str(arguments[0]))))
        else:
            log.write_text('CPU control')
        if 'export' in arguments:
            Path(arguments[-1]).write_text('# synthetic locked runtime\n')
        return dict(pid=1, child_waited=True, process_exit=0, log=str(log), log_sha256=runner.sha(log))

    monkeypatch.setattr(runner.shutil, 'which', lambda name: 'uv-control')
    monkeypatch.setattr(runner, 'run_logged', logged)
    evidence = tmp_path / 'evidence'
    with runner.installed_environment(wheel, evidence, environment={}) as (_, environment):
        assert environment['PYTHONDONTWRITEBYTECODE'] == '1'
    export = next(call for call in calls if 'export' in call)
    assert export[export.index('--group') + 1] == 'hosts'
    assert '--locked' in export and '--no-emit-project' in export
    install = next(call for call in calls if 'install' in call)
    requirements = [Path(install[index + 1]) for index, value in enumerate(install) if value == '--requirements']
    assert requirements == [evidence / 'runtime-requirements.txt', evidence / 'wheel-requirements.txt']
    assert '--require-hashes' in install
    assert wheel.as_uri() in requirements[1].read_text()
    assert runner.sha(wheel) in requirements[1].read_text()
    cleanup = json.loads((evidence / 'environment-teardown.json').read_bytes())
    assert cleanup['owned_root_removed'] and cleanup['wheel_preserved']
    assert not Path(cleanup['owned_root']).exists()
    assert cleanup['status'] == 'PASS_OWNED_ENVIRONMENT_TEARDOWN'


def test_wrong_launch_id_blocks_further_workers(tmp_path, monkeypatch):
    def logged(arguments, *, cwd, environment, log):
        output = Path(arguments[arguments.index('--output') + 1])
        output.mkdir()
        (output / 'result.json').write_text(json.dumps(dict(launch_id='wrong', pid=1)))
        log.write_text('CPU controlled wrong identity')
        return dict(pid=1, child_waited=True, process_exit=0)
    monkeypatch.setattr(runner, 'run_logged', logged)
    environment = {'VISPY_VOLUME_WHEEL_REFERENCE': str(tmp_path)}
    observed = runner.run_case('categorical_edit', sys.executable, tmp_path / 'wheel.whl', tmp_path, environment)
    assert 'worker_admission_error' in observed
    assert (tmp_path / 'worker-termination-unverified.json').is_file()
    with pytest.raises(AssertionError, match='Previous worker termination'):
        runner.run_case('mesh_front_iso', sys.executable, tmp_path / 'wheel.whl', tmp_path, environment)


def test_image_controls_are_preserved_without_other_renderer_controls():
    env = runner.clean_environment(dict(os.environ, VISPY_VOLUME_WHEEL_EVIDENCE='evidence',
        VISPY_VOLUME_WHEEL_REFERENCE='reference', VISPY_RANDOM_RENDER_OPTION='other'))
    assert env['VISPY_VOLUME_WHEEL_REFERENCE'] == 'reference'
    assert env['VISPY_VOLUME_WHEEL_EVIDENCE'] == 'evidence'
    assert 'VISPY_RANDOM_RENDER_OPTION' not in env
