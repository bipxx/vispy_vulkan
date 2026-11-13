# SPDX-License-Identifier: AGPL-3.0-only
"""Run the production shutdown wrapper against real CPU caches, without Dawn."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def test_shutdown_releases_warm_and_engine_owned_upload_caches():
    cmake = shutil.which('cmake')
    assert cmake, 'The existing CMake/compiler build profile is required'
    source = (ROOT / 'cpp/runtime.cpp').read_text(encoding='utf-8')
    wrappers = re.findall(r'^void shutdown_runtime\(\) \{\n.*?^\}', source, re.M | re.S)
    assert len(wrappers) == 1, 'Exactly one production shutdown wrapper must be exercised'
    with tempfile.TemporaryDirectory(prefix='upload-shutdown-') as temporary:
        build = Path(temporary)
        (build / 'shutdown_runtime_body.inc').write_text(wrappers[0] + '\n', encoding='utf-8')
        commands = [
            [cmake, '-S', str(ROOT / 'tests/native/upload_cache_shutdown'), '-B', str(build),
             '-DVISPY_SOURCE_ROOT=' + str(ROOT)],
            [cmake, '--build', str(build), '--config', 'Release', '--parallel', '2'],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
        candidates = [directory / name for directory in (build, build / 'Release')
                      for name in ('upload_cache_shutdown_contract', 'upload_cache_shutdown_contract.exe')]
        executables = [path for path in candidates if path.is_file()]
        assert len(executables) == 1, 'Exactly one compiled shutdown contract must exist'
        result = subprocess.run([str(executables[0])], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.startswith('PASS warm caches, engine-owned imports, external owners')


__all__ = ['test_shutdown_releases_warm_and_engine_owned_upload_caches']
