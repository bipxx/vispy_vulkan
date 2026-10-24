# SPDX-License-Identifier: AGPL-3.0-only
"""Artifact and failure reporting contracts for installed host qualification."""

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'no_opengl_host_probe', ROOT / 'tools/no_opengl_host_probe.py')
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_stale_source_overlay_cannot_pass_exact_artifact_check(tmp_path):
    package = tmp_path / 'installed/vispy'
    package.mkdir(parents=True)
    payload = {'__init__.py': b'# wheel source\n', '_dawn.test.pyd': b'native payload'}
    wheel = tmp_path / 'candidate.whl'
    with zipfile.ZipFile(wheel, 'w') as bundle:
        for name, value in payload.items():
            bundle.writestr('vispy/' + name, value)
            (package / name).write_bytes(value)
    result = PROBE.verify_installed_payload(wheel, package)
    assert result['verified_files'] == 2
    assert result['wheel_sha256'] == PROBE.file_sha256(wheel)
    (package / '__init__.py').write_bytes(b'# source from another worktree\n')
    with pytest.raises(RuntimeError, match='differs from exact wheel: vispy/__init__.py'):
        PROBE.verify_installed_payload(wheel, package)


def test_native_payload_is_required_even_when_metadata_and_python_exist(tmp_path):
    package = tmp_path / 'vispy'
    package.mkdir()
    (package / '__init__.py').write_bytes(b'')
    wheel = tmp_path / 'python-only.whl'
    with zipfile.ZipFile(wheel, 'w') as bundle:
        bundle.writestr('vispy/__init__.py', b'')
    with pytest.raises(RuntimeError, match='lacks the required VisPy Python/native payload'):
        PROBE.verify_installed_payload(wheel, package)


def test_functional_failure_is_retained_before_process_exit(tmp_path):
    evidence = PROBE.Evidence(tmp_path / 'evidence', 'napari')
    with pytest.raises(RuntimeError, match='device lost'):
        with evidence.stage('volume_capture'):
            raise RuntimeError('device lost')
    report = json.loads((evidence.output / 'functional.json').read_text())
    assert report['stages'][0]['status'] == 'failed'
    assert 'device lost' in report['stages'][0]['error']
    assert report['native_no_opengl_gates'] == 'external monitor required'


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / 'evidence'
    PROBE.Evidence(output, 'qwidget')
    with pytest.raises(FileExistsError):
        PROBE.Evidence(output, 'napari')
