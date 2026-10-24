# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh-process stderr proof for host-owned root destruction and re-entry."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from vispy import _dawn

pytestmark = pytest.mark.gpu

CHILD = r'''
import json
import runpy
from pathlib import Path
import sys
sys.path[:0] = json.loads(sys.argv[1])
import vispy
vispy.__path__.insert(0, str(Path(sys.argv[2]).parent))
from vispy import _dawn
assert Path(_dawn.__file__).resolve() == Path(sys.argv[2]).resolve()
scope = runpy.run_path(sys.argv[3])
workflow = scope['test_root_without_children_preserves_host_work_on_quit']
workflow('destroy-binding')
workflow('command')
import tkinter as tk
sentinel = tk.Tk()
try:
    sentinel.withdraw()
    sentinel.tk.call('puts', 'stderr', 'KNOWN_TCL_STDERR_CAPTURE_CONTROL')
    sentinel.tk.call('flush', 'stderr')
    sentinel.update_idletasks()
finally:
    sentinel.destroy()
_dawn.process_events()
from tools.no_opengl.policy import LIVE_GAUGES
state = _dawn.probe()
gauges = {key: state[key] for key in LIVE_GAUGES}
assert all(type(value) is int and value == 0 for value in gauges.values()), gauges
print(json.dumps({'native_origin': _dawn.__file__, 'shutdown_gauges': gauges}))
'''


def test_host_destroy_binding_has_no_deferred_tcl_diagnostics(tmp_path_factory):
    # Keeping one stderr handle for the entire child is essential: Tcl caches
    # its channel, so per-test FD replacement can itself produce bad-file errors.
    output = tmp_path_factory.getbasetemp() / 'tk-shutdown-child'
    output.mkdir()
    completed = subprocess.run(
        [sys.executable, '-B', '-c', CHILD, json.dumps(sys.path), _dawn.__file__,
         str(Path(__file__).with_name('test_tkinter_backend.py'))],
        capture_output=True, text=True, timeout=30,
    )
    (output / 'child.stdout').write_text(completed.stdout, encoding='utf-8')
    (output / 'child.stderr').write_text(completed.stderr, encoding='utf-8')
    assert completed.returncode == 0, completed.stdout + completed.stderr
    control = 'KNOWN_TCL_STDERR_CAPTURE_CONTROL'
    # The pinned WSL software profile emits these existing, non-Tcl advisories.
    # Retain them verbatim and reject every other stderr line; never ignore a
    # generic warning prefix or suppress Tcl's callback/error channel.
    advisories = set()
    if _dawn.device_info().get('software'):
        advisories = {
            'WARNING: could not determine DPI',
            'Warning: maxDynamicUniformBuffersPerPipelineLayout artificially reduced from 500000 to 16 to fit dynamic offset allocation limit.',
            'Warning: maxDynamicStorageBuffersPerPipelineLayout artificially reduced from 500000 to 16 to fit dynamic offset allocation limit.',
        }
    lines = completed.stderr.splitlines()
    assert lines.count(control) == 1, completed.stderr
    assert all(line == control or line in advisories for line in lines), completed.stderr
    records = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith('{')]
    assert len(records) == 1 and records[0]['native_origin'] == _dawn.__file__
    assert len(records[0]['shutdown_gauges']) == 9
    print(json.dumps({'child_exit': completed.returncode, 'child_waited': True,
                      'captured_stderr': completed.stderr, **records[0]}))
