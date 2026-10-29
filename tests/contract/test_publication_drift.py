# SPDX-License-Identifier: AGPL-3.0-only
"""The publication drift check (tools/publication_drift.py) explains or reports every difference from main."""
import subprocess

from tools import publication_drift as drift

PUBLISHED = {'.gitattributes': b'* -text\n', '.gitignore': b'/build/\n*.log\n', 'README.md': b'readme\n',
             'docs/same.md': b'same\r\nmixed\n', 'docs/content.md': b'old\n', 'docs/endings.md': b'a\r\nb\n',
             'docs/history.md': b'published\n', 'tools/gone.py': b'x = 1\n', 'third_party/dep/file.c': b'int x;\n'}


def git(path, *arguments):
    subprocess.run(['git', '-C', str(path), '-c', 'core.autocrlf=false', '-c', 'user.name=drift', '-c',
                    'user.email=drift@example.invalid', *arguments], check=True, capture_output=True)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def published_and_local(tmp_path):
    clone, tree = tmp_path / 'clone', tmp_path / 'tree'
    for path, data in PUBLISHED.items():
        write(clone / path, data)
        write(tree / path, data)
    git(clone, 'init', '-q')
    git(clone, 'add', '-A')
    git(clone, 'commit', '-q', '-m', 'main')
    write(tree / 'docs/content.md', b'new\n')
    write(tree / 'docs/endings.md', b'a\nb\n')
    write(tree / 'docs/history.md', b'local history\n')
    (tree / 'tools/gone.py').unlink()
    write(tree / 'third_party/dep/file.c', b'int y;\n')  # left to cmake/verify_dependencies.py
    write(tree / 'tools/new.py', b'y = 2\n')
    write(tree / 'tools/run.log', b'ignored by the clone\n')
    write(tree / 'tools/__pycache__/new.cpython-312.pyc', b'\0')
    write(tree / 'build/out.bin', b'\0')  # main has no build/ directory
    write(tree / 'scratch.txt', b'\0')  # nor this root file
    return clone, tree


def test_drift_lists_changed_missing_and_local_only_files_byte_for_byte(tmp_path):
    clone, tree = published_and_local(tmp_path)
    record = drift.drift(tree, clone, 'HEAD', expect=['docs/content.md'], known={'docs/history.md': 'local'})
    assert record['changed'] == [{'path': 'docs/content.md', 'line_endings_only': False},
                                 {'path': 'docs/endings.md', 'line_endings_only': True},
                                 {'path': 'docs/history.md', 'line_endings_only': False}]
    assert record['missing'] == ['tools/gone.py']
    assert record['local_only'] == ['tools/new.py']
    assert record['known'] == {'docs/history.md': 'local'}
    assert record['unexplained'] == ['docs/endings.md', 'tools/gone.py', 'tools/new.py']
    assert len(record['commit']) == 40


def test_directories_explain_their_files_and_only_unexplained_drift_fails(tmp_path, capsys):
    clone, tree = published_and_local(tmp_path)
    record = drift.drift(tree, clone, 'HEAD', expect=['tools/'], known={'docs/': 'local'})
    assert record['unexplained'] == [] and set(record['known']) == {'docs/content.md', 'docs/endings.md',
                                                                    'docs/history.md'}
    arguments = [str(clone), '--ref', 'HEAD', '--root', str(tree)]
    assert drift.main(arguments + ['--expect', 'docs/', 'tools/']) == 0
    assert drift.main(arguments + ['--expect', 'docs/', '--json', str(tmp_path / 'drift.json')]) == 1
    assert 'missing     tools/gone.py' in capsys.readouterr().out
    assert (tmp_path / 'drift.json').read_bytes().count(b'"tools/new.py"') == 2  # local only, unexplained


def test_known_local_differences_give_their_reason():
    for path, reason in drift.KNOWN.items():
        assert reason and not path.startswith(drift.EXCLUDED) and '\\' not in path, path


__all__ = [name for name in dir() if name.startswith('test_')]
