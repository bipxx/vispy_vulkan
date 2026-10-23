"""ELF path-bearing DT_NEEDED follows loader semantics, not filename search."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl import dependencies


@pytest.mark.parametrize('template', ['$ORIGIN/../lib/target.so', '${ORIGIN}/../lib/target.so', 'absolute'])
def test_elf_explicit_needed_origin_and_absolute_paths(tmp_path, monkeypatch, template):
    binary, target = tmp_path / 'bin/python', tmp_path / 'lib/target.so'
    binary.parent.mkdir()
    target.parent.mkdir()
    binary.write_bytes(b'independent parser input fixture')
    target.write_bytes(b'independent dependency fixture')
    needed = target.as_posix() if template == 'absolute' else template
    def inspect(path):
        return dict(path=str(path), sha256='fixture', format='ELF',
                    imports=[dict(name=needed, delay=False, symbols=[])] if path == binary else [], runpaths=[])
    monkeypatch.setattr(dependencies, 'inspect_binary', inspect)
    result = dependencies.dependency_closure([binary], [])
    assert result['gate'] == 'PASS'
    assert result['edges'][0]['resolved'] == str(target.resolve())
    assert len(result['binaries']) == 2


def test_elf_cwd_relative_needed_stays_unverified_even_if_parent_has_file(tmp_path, monkeypatch):
    root = tmp_path / 'python'
    root.write_bytes(b'fixture')
    (tmp_path / 'subdir').mkdir()
    (tmp_path / 'subdir/target.so').write_bytes(b'fixture')
    monkeypatch.setattr(dependencies, 'inspect_binary', lambda path: dict(path=str(path), format='ELF',
                        imports=[dict(name='subdir/target.so', delay=False, symbols=[])], runpaths=[]))
    result = dependencies.dependency_closure([root], [tmp_path / 'subdir'])
    assert result['gate'] == 'UNVERIFIED'
    assert result['unresolved'][0]['name'] == 'subdir/target.so'
