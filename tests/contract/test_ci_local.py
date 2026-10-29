# SPDX-License-Identifier: AGPL-3.0-only
"""The local concurrent CI runner (tools/ci_local.py) selects CI's test commands and shards them without losing any."""
from tools.ci_local import WORKFLOW, commands, shard, listed_files

WORKFLOW_TEXT = '''
        run: |
          "$CI_PYTHON" .github/workflows/qualification_gate.py pytest --output "$EVIDENCE/a.json" -- -q tests/contract/test_a.py --junitxml="$EVIDENCE/a.xml"
          "$CI_PYTHON" -B tools/qualification_ci.py --capture --workflow x.yml --output "$EVIDENCE/ci.json"
          "$CI_PYTHON" -B tools/compatibility_inventory.py
          "$CI_PYTHON" cmake/verify_dependencies.py
          cmake -S . -B build/ci-native
'''


def test_commands_select_the_gate_pytest_runs_and_the_validators():
    found = commands(WORKFLOW_TEXT, 'E')
    assert found == [['.github/workflows/qualification_gate.py', 'pytest', '--output', 'E/a.json', '--',
                      '-p', 'no:cacheprovider', '-q', 'tests/contract/test_a.py', '--junitxml=E/a.xml'],
                     ['-B', 'tools/compatibility_inventory.py']]


def test_shards_partition_the_files_and_keep_options_and_separate_evidence():
    # The workflow also names tests inside the package (src/vispy/**/tests); each file must run in exactly one shard.
    files = ['tests/contract/test_%d.py' % index for index in range(3)] + ['src/vispy/util/tests/test_%d.py' % index
                                                                          for index in range(2)]
    tokens = ['-B', '.github/workflows/qualification_gate.py', 'pytest', '--output', 'E/x.json', '--', '-q', '-p',
              'no:cacheprovider', *files, '--junitxml=E/x.xml']
    assert listed_files(tokens) == files
    parts = shard(tokens, 2)
    assert len(parts) == 3
    assert sorted(file for part in parts for file in listed_files(part)) == sorted(files)
    for number, part in enumerate(parts, 1):
        assert part[:3] == tokens[:3] and part[part.index('--'):part.index('--') + 4] == ['--', '-q', '-p', 'no:cacheprovider']
        assert part[part.index('--output') + 1] == 'E/x-shard%d.json' % number
        assert part[-1] == '--junitxml=E/x-shard%d.xml' % number


def test_small_and_validator_commands_are_not_sharded():
    small = ['.github/workflows/qualification_gate.py', 'pytest', '--output', 'E/a.json', '--', 'tests/contract/test_a.py']
    assert shard(small, 2) == [small]
    assert shard(['-B', 'tools/compatibility_inventory.py'], 1) == [['-B', 'tools/compatibility_inventory.py']]


def test_the_cpu_contract_workflow_yields_only_gate_runs_and_validators():
    found = commands(WORKFLOW.read_text(encoding='utf-8'), 'E')
    assert found
    for tokens in found:
        assert 'tools/qualification_ci.py' not in tokens
        assert 'pytest' in tokens or any(token.startswith('tools/compatibility_') for token in tokens)


# Only the tests are re-exported into CI's curated list (tests/contract/curated_contracts.py).
__all__ = [name for name in dir() if name.startswith('test_')]
