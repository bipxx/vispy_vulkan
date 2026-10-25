# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic CTest fixtures exercise capture, not Linux producer admission."""
import json
from pathlib import Path
import shutil
import sys

import pytest

from tools import run_linux_native_contracts as contracts
from tools.native_epoch import EpochError


POLICY = {
    'VISPY_BUILD_CONTRACT_TESTS': 'ON', 'VISPY_CPU_CONTRACTS_ONLY': 'OFF',
    'VISPY_INPLACE': 'OFF', 'VISPY_VERIFY_DEPENDENCIES': 'ON',
    'DAWN_ENABLE_VULKAN': 'ON', 'DAWN_ENABLE_METAL': 'OFF',
    'DAWN_ENABLE_NULL': 'OFF', 'TINT_BUILD_SPV_READER': 'ON',
    'DAWN_ENABLE_SPIRV_VALIDATION': 'ON',
}


def cache():
    return ''.join(key + ':BOOL=' + value + '\n' for key, value in POLICY.items()).encode()


def discovery():
    return dict(kind='ctestInfo', version=dict(major=1, minor=0),
                tests=[dict(name=name) for name in sorted(contracts.MINIMUM)])


def junit(names, child=''):
    return ('<testsuite>' + ''.join('<testcase name="' + name + '">' + child +
                                   '</testcase>' for name in names) + '</testsuite>').encode()


def test_exact_discovered_inventory_is_required():
    data = discovery()
    names = sorted(contracts.MINIMUM)
    assert contracts.validate_reports(json.dumps(data), junit(names)) == names
    with pytest.raises(EpochError):
        contracts.validate_reports(json.dumps(data), junit(names[:-1]))
    with pytest.raises(EpochError):
        contracts.validate_reports(json.dumps(data), junit(names + ['unexpected']))


def test_nonlegacy_renderer_contract_cannot_disappear():
    data = discovery()
    data['tests'] = [item for item in data['tests']
                     if item['name'] != 'owned_upload_packing_contract']
    with pytest.raises(ValueError): contracts.discovered_names(json.dumps(data))


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'wrong-kind', 'wrong-version', 'bool-version'])
def test_incomplete_discovery_rejects(mutation):
    data = discovery()
    if mutation == 'missing': data['tests'].pop()
    elif mutation == 'duplicate': data['tests'].append(data['tests'][0])
    elif mutation == 'wrong-kind': data['kind'] = 'invented'
    else: data['version']['major'] = True if mutation == 'bool-version' else 2
    with pytest.raises(ValueError): contracts.discovered_names(json.dumps(data))


@pytest.mark.parametrize('child', ['<failure/>', '<skipped/>', '<error/>'])
def test_incomplete_execution_rejects(child):
    with pytest.raises(EpochError):
        contracts.validate_reports(json.dumps(discovery()), junit(sorted(contracts.MINIMUM), child))


@pytest.mark.parametrize('key', list(POLICY))
def test_cpu_or_incomplete_renderer_configuration_rejects(key):
    data = cache().replace((key + ':BOOL=' + POLICY[key]).encode(), (key + ':BOOL=wrong').encode())
    with pytest.raises(ValueError): contracts.renderer_cache(data)


@pytest.fixture(scope='module')
def captured(tmp_path_factory):
    """Real CTest processes execute tiny Python commands, explicitly synthetic."""
    root = tmp_path_factory.mktemp('synthetic-native-contracts')
    build = root/'build'; build.mkdir()
    (build/'CMakeCache.txt').write_bytes(cache())
    (build/'CTestTestfile.cmake').write_text(''.join(
        'add_test(' + name + ' "' + Path(sys.executable).as_posix() + '" "-I" "-B" "-c" "pass")\n'
        for name in sorted(contracts.MINIMUM)))
    executable = Path(sys.executable).with_name('ctest.exe' if sys.platform == 'win32' else 'ctest')
    if not executable.is_file(): executable = Path(shutil.which('ctest') or '')
    assert executable.is_file(), 'The locked build environment must provide CTest'
    output = root/'captured'
    result = contracts.run(build, output, executable)
    assert result['status'] == 'PASS_LINUX_RENDERER_CONTRACTS'
    assert all(item['exit_code'] == 0 and item['child_waited'] for item in result['commands'])
    return build, output


def test_real_ctest_transport_with_synthetic_cases(captured):
    build, output = captured
    result = contracts.validate_retained(output, build, cache())
    assert result['tests'] == sorted(contracts.MINIMUM)
    assert result['producer_admitted'] is result['artifact_admitted'] is result['hardware_qualified'] is False


def test_failed_actual_child_preserves_exit_and_reports(captured, tmp_path):
    original_build, original_output = captured
    build = tmp_path/'failing-build'
    build.mkdir()
    (build/'CMakeCache.txt').write_bytes(cache())
    commands = (original_build/'CTestTestfile.cmake').read_text()
    commands = commands.replace('"-c" "pass"', '"-c" "raise SystemExit(7)"', 1)
    (build/'CTestTestfile.cmake').write_text(commands)
    ctest = json.loads((original_output/'result.json').read_bytes())['ctest']['origin']
    output = tmp_path/'failed'
    with pytest.raises(RuntimeError, match='child failed'):
        contracts.run(build, output, ctest)
    record = json.loads((output/'result.json').read_bytes())
    assert record['status'] == 'FAILED_PRESERVED'
    assert len(record['commands']) == 2
    assert record['commands'][-1]['exit_code'] != 0
    assert record['commands'][-1]['child_waited'] is True
    assert {'ctest.xml', 'ctest.log'} <= set(record['files'])
    with pytest.raises(ValueError): contracts.validate_retained(output, build, cache())


def test_duplicate_configuration_rejects():
    with pytest.raises(ValueError, match='Duplicate'):
        contracts.renderer_cache(cache() + b'DAWN_ENABLE_VULKAN:BOOL=OFF\n')


@pytest.mark.parametrize('mutation', ['exit', 'wait', 'pid', 'argv', 'command-count', 'cache',
                                    'discovery-bytes', 'junit-bytes', 'inventory', 'admitted', 'files', 'tool'])
def test_retained_join_rejects_tampering(captured, tmp_path, mutation):
    build, original = captured
    output = tmp_path/'copy'
    shutil.copytree(original, output)
    record = json.loads((output/'result.json').read_bytes())
    # Relocate the synthetic original JUnit command for this fixture only.
    record['commands'][1]['argv'][-1] = str(output.resolve()/'ctest.xml')
    if mutation == 'exit': record['commands'][1]['exit_code'] = 1
    elif mutation == 'wait': record['commands'][1]['child_waited'] = False
    elif mutation == 'pid': record['commands'][1]['child_pid'] = True
    elif mutation == 'argv': record['commands'][1]['argv'].append('-R=shader')
    elif mutation == 'command-count': record['commands'].pop()
    elif mutation == 'cache': record['cache_sha256'] = '0'*64
    elif mutation == 'discovery-bytes': (output/'discovery.json').write_text('{}')
    elif mutation == 'junit-bytes': (output/'ctest.xml').write_text('<testsuite/>')
    elif mutation == 'inventory': record['tests'].pop()
    elif mutation == 'admitted': record['producer_admitted'] = True
    elif mutation == 'files': record['files'].pop('ctest.log')
    elif mutation == 'tool': record['ctest']['sha256'] = '0'*64
    (output/'result.json').write_text(json.dumps(record))
    with pytest.raises((ValueError, EpochError)):
        contracts.validate_retained(output, build, cache())
