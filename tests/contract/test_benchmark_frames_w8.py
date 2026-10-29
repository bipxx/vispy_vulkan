# SPDX-License-Identifier: AGPL-3.0-only
"""The W8 benchmark (tools/benchmark_frames_w8.py) is the pinned harness with three declared single-line changes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools import benchmark_frames_w8 as w8

ROOT = Path(__file__).resolve().parents[2]


def test_the_successor_changes_three_lines_of_the_pinned_harness():
    harness = (ROOT / 'tools/benchmark_frames.py').read_bytes()
    assert hashlib.sha256(harness).hexdigest() == w8.HARNESS_SHA256
    source = w8.derived_source()
    old, new = harness.decode('utf-8').splitlines(), source.splitlines()
    assert len(old) == len(new) and sum(a != b for a, b in zip(old, new)) == len(w8.CHANGES) == 3
    assert 'else "r8")' in source and '"rgba8"' not in source
    assert 'VISPY_PYQT5_SHARE_CONTEXT="true", VISPY_QT_PRESENTATION="native")' in source
    compile(source, str(w8.HARNESS), 'exec', dont_inherit=True)


def test_vispy_expands_r8_to_the_rgba_format_the_harness_meant():
    # In a child process: the CPU benchmark contracts forbid importing a renderer into the test process.
    code = ('from vispy.visuals._scalable_textures import GPUScaledTextureMixin as M\n'
            'print(M._get_gl_tex_format(None, "r8", 4), M._get_gl_tex_format(None, "rgba8", 4), '
            'M._get_gl_tex_format(None, "r32f", 1))')
    child = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, check=True, cwd=ROOT)
    assert child.stdout.split() == ['rgba8', 'rgbagba8', 'r32f']


def test_the_successor_runs_the_harness_and_records_both_hashes(tmp_path):
    output = tmp_path / 'evidence'
    subprocess.run([sys.executable, '-B', str(ROOT / 'tools/benchmark_frames_w8.py'), '--dry-run',
                    '--reference-python', str(tmp_path / 'upstream/python'),
                    '--candidate-python', str(tmp_path / 'candidate/python'),
                    '--workloads', 'image-rgba-8-translucent-patch', '--output', str(output)], check=True, cwd=ROOT)
    request = json.loads((output / 'request.json').read_text(encoding='utf-8'))
    assert request['harness_sha256'] == w8.HARNESS_SHA256
    assert request['runner_sha256'] == hashlib.sha256((ROOT / 'tools/benchmark_frames_w8.py').read_bytes()).hexdigest()
    assert [workload['name'] for workload in request['workloads']] == ['image-rgba-8-translucent-patch']


__all__ = [name for name in dir() if name.startswith('test_')]
