# SPDX-License-Identifier: AGPL-3.0-only
"""Original-protocol adapter controls; no historical approvals are fabricated."""
from copy import deepcopy

import pytest

from tools import qualification_epoch as qe


def sample():
    sources = {'cpp/runtime.cpp': '1' * 64}
    harness = {'tests/shaders/original.cpp': '2' * 64}
    ownership = {'schema': 1, 'sealed': True, 'epoch': 29, 'snapshot_epoch': 15,
                 'source_files': sources, 'sdk_manifest_sha256': qe.SDK_SHA,
                 'harness_inputs': {k: {'path': k, 'sha256': v} for k, v in harness.items()},
                 'targets': sorted(qe.native_epoch.REQUIRED_TARGETS),
                 'ctest_expected_names': ['original_contract']}
    ownership_sha = qe.digest(ownership)
    frozen = {'schema': 1, 'epoch': 29, 'snapshot_epoch': 15,
              'ownership_manifest_sha256': ownership_sha,
              'source_files': deepcopy(sources), 'source_tree_sha256': qe.native_epoch.tree_digest(sources),
              'harness_files': harness, 'harness_tree_sha256': qe.native_epoch.tree_digest(harness),
              'protected_native_before': {'old.pyd': '3' * 64}, 'protected_native_after': {'old.pyd': '3' * 64},
              'sdk_tint_reader_enabled': False}
    status = {'status': 'build_and_ctest_passed', 'epoch': 29,
              'source_tree_sha256': frozen['source_tree_sha256'], 'sdk_manifest_sha256': qe.SDK_SHA,
              'in_place_copy': False, 'gpu_qualified': False, 'sdk_tint_reader_enabled': False}
    terminal = {'exit_code': 0, 'child_waited': True, 'ownership_manifest_sha256': ownership_sha,
                'source_tree_sha256': frozen['source_tree_sha256'],
                'source_directory': 'C:/original/source', 'build_directory': 'C:/original/native-pass29-sdk',
                'ctest_output': 'C:/original/evidence/ctest.xml'}
    def command(argv): return {'argv': argv, 'CL_MPCount': '3'}
    commands = {'configure': command(['cmake.exe', '-S', terminal['source_directory'], '-B', terminal['build_directory'],
                                      '-DVISPY_NATIVE_SDK_MANIFEST_SHA256=' + qe.SDK_SHA,
                                      '-DVISPY_INPLACE=OFF', '-DVISPY_VERIFY_DEPENDENCIES=ON']),
                'build': command(['cmake.exe', '--build', terminal['build_directory'], '--config', 'Release',
                                  '--parallel', '3', '--target', *ownership['targets'], '--', '/p:CL_MPCount=3']),
                'ctest': command(['ctest.exe', '--test-dir', terminal['build_directory'], '-C', 'Release',
                                  '--output-on-failure', '--output-junit', terminal['ctest_output']]),
                'dependencies-after': command(['python.exe', 'cmake/verify_dependencies.py'])}
    ctest = b'<testsuite failures="0" errors="0"><testcase name="original_contract"/></testsuite>'
    outputs = {name: '4' * 64 for name in qe.MEMBERS}
    binaries = {qe.PureWindowsPath(name).name: value for name, value in outputs.items()}
    return ownership, ownership_sha, frozen, status, terminal, commands, ctest, outputs, binaries


def test_original_command_and_original_test_inventory_are_preserved():
    arguments = sample()
    result = qe.validate_join(*arguments)
    assert result['status'] == 'PASS_ORIGINAL_EPOCH_JOIN'
    assert result['native_build_verified'] and not result['artifact_admitted']
    assert not result['hardware_qualified']
    # Original policy predates the new recipe's test list/managed build path.
    assert arguments[0]['ctest_expected_names'] == ['original_contract']
    assert arguments[5]['build']['argv'][-2:] == ['--', '/p:CL_MPCount=3']


@pytest.mark.parametrize('change', ['unsealed', 'epoch', 'freeze', 'source', 'harness', 'protected',
                                   'sdk', 'scope', 'status', 'exit', 'wait', 'terminal-source',
                                   'targets', 'missing-command', 'rewrite-command', 'configure',
                                   'ctest-command', 'skipped-test', 'missing-test', 'output',
                                   'missing-output', 'bool-exit'])
def test_original_provenance_semantic_rejections(change):
    ownership, checksum, frozen, status, terminal, commands, ctest, outputs, binaries = sample()
    if change == 'unsealed': ownership['sealed'] = False
    elif change == 'epoch': status['epoch'] += 1
    elif change == 'freeze': frozen['ownership_manifest_sha256'] = '9' * 64
    elif change == 'source': frozen['source_files']['cpp/runtime.cpp'] = '9' * 64
    elif change == 'harness': frozen['harness_files']['tests/shaders/original.cpp'] = '9' * 64
    elif change == 'protected': frozen['protected_native_after']['old.pyd'] = '9' * 64
    elif change == 'sdk': status['sdk_manifest_sha256'] = '9' * 64
    elif change == 'scope': status['gpu_qualified'] = True
    elif change == 'status': status['status'] = 'compiled_only'
    elif change == 'exit': terminal['exit_code'] = 1
    elif change == 'wait': terminal['child_waited'] = False
    elif change == 'terminal-source': terminal['source_tree_sha256'] = '9' * 64
    elif change == 'targets': ownership['targets'].remove('_dawn')
    elif change == 'missing-command': commands.pop('ctest')
    elif change == 'rewrite-command': commands['build']['argv'] = commands['build']['argv'][:-2]
    elif change == 'configure': commands['configure']['argv'].remove('-DVISPY_VERIFY_DEPENDENCIES=ON')
    elif change == 'ctest-command': commands['ctest']['argv'][2] = 'C:/other/build'
    elif change == 'skipped-test': ctest = b'<testsuite><testcase name="original_contract"><skipped/></testcase></testsuite>'
    elif change == 'missing-test': ctest = b'<testsuite/>'
    elif change == 'output': outputs[next(iter(outputs))] = '9' * 64
    elif change == 'missing-output': outputs.pop(next(iter(outputs)))
    else: terminal['exit_code'] = False
    with pytest.raises((qe.InventoryError, qe.native_epoch.EpochError)):
        qe.validate_join(ownership, checksum, frozen, status, terminal, commands, ctest, outputs, binaries)


def test_original_record_needs_review_before_any_old_origin_is_consumed(monkeypatch, without_current_reviews):
    # Exercise the real gate with reviews removed only from its in-memory input.
    without_current_reviews(qe)
    ref = {'path': 'unit-only-unused.json', 'sha256': '0' * 64}
    candidate = qe.ROOT / 'compat/candidates/tk-state-resource-1/candidate.json'
    record = {'schema': 1, 'kind': 'original-native-epoch-reuse',
              'reuse': {'candidate_scope_sha256': '0' * 64, 'profile': 'unit', 'ownership_sha256': '0' * 64,
                        'frozen_sha256': '0' * 64, 'outputs_sha256': '0' * 64, 'impact': 'unit only'}}
    for name in ('candidate', 'ownership', 'frozen', 'status', 'terminal', 'preparation', 'sdk', 'cache', 'ctest', 'binaries'):
        record[name] = ref
    record['candidate'] = {'path': candidate.relative_to(qe.ROOT).as_posix(), 'sha256': qe.sha(candidate.read_bytes())}
    for name in ('guard_tools', 'source_inputs', 'harness_inputs'): record[name] = [{'path': 'unit', 'file': ref}]
    record['commands'] = [{'phase': 'unit', 'command': ref, 'log': ref}]
    record['outputs'] = [{'member': 'unit', 'file': ref}]
    record['projects'] = [{'target': 'unit', 'before': ref, 'after': ref}]
    with pytest.raises(qe.InventoryError, match='source and scope review remain pending'):
        qe.validate_record(record)
