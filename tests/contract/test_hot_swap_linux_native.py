# SPDX-License-Identifier: AGPL-3.0-only
"""Native controls of the hot-swap Linux observer: the derived collectors compile and observe synthetic fixtures.

Linux-only, in the style of tests/no_opengl/test_probe_failures.py: other platforms collect no case, because
qualification forbids skips. The cases need the existing C compiler and ptrace of child processes; nothing renders.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

if sys.platform.startswith('linux'):
    from tools.hot_swap import linux_controls
    from tools.hot_swap.policy import (CONTEXT_NAMES, CONTEXT_PREFIXES, DRAW_NAMES, DRAW_PREFIXES, NOT_DRAW_PREFIXES,
                                       context_or_draw)

    # Classify names with the derived debugger's own C function.
    HARNESS = r'''#define main observer_program_main
#include "debugger_linux.c"
#undef main
int main(int argc, char **argv) {
    for (int i = 1; i < argc; ++i) printf("%d %s\n", context_or_draw(argv[i]), argv[i]);
    return 0;
}
'''

    def _compiler():
        compiler = shutil.which('cc')
        assert compiler, 'The hot-swap Linux observer controls require the existing C compiler'
        return compiler

    def test_the_derived_collectors_compile_without_warnings(tmp_path):
        log = []
        auditor, debugger = linux_controls.build_collectors(_compiler(), tmp_path, log)
        assert auditor.is_file() and debugger.is_file(), log
        assert [(entry['exit'], entry['stderr']) for entry in log] == [(0, ''), (0, '')], log

    def test_the_c_context_and_draw_names_are_the_policy_tables(tmp_path):
        source, executable = tmp_path / 'classify.c', tmp_path / 'classify'
        source.write_text(HARNESS)
        build = subprocess.run([_compiler(), '-std=gnu11', '-O0', '-Wall', '-Wextra', '-Werror',
                                '-I', str(ROOT / 'tools/hot_swap'), str(source), '-o', str(executable)],
                               capture_output=True, text=True)
        assert build.returncode == 0, build.stderr
        names = set()
        for name in (*CONTEXT_PREFIXES, *CONTEXT_NAMES, *DRAW_PREFIXES, *DRAW_NAMES, *NOT_DRAW_PREFIXES, 'glGetError',
                     'glClearColor', 'glDrawBuffers', 'glXGetProcAddressARB', 'eglGetDisplay', 'glBeginQuery',
                     'glCallListsARB', 'glArrayElementEXT', 'SwapBuffersEXT', 'glHotSwapQueryControl'):
            names |= {name, name + 'ARB', name + 's', name[:-1], name.lower()}
        names = sorted(names)
        result = subprocess.run([str(executable), *names], capture_output=True, text=True, check=True)
        native = {line.split(' ', 1)[1]: line.split(' ', 1)[0] == '1' for line in result.stdout.splitlines()}
        assert native == {name: context_or_draw(name) for name in names}

    def test_native_controls_record_step_over_and_stop(tmp_path):
        output = tmp_path / 'controls'
        code = linux_controls.main(['--output', str(output), '--cc', _compiler()])
        report = json.loads((output / 'controls.json').read_text())
        failed = sorted(name for name, passed in report['checks'].items() if not passed)
        assert code == 0 and report['status'] == 'PASS_CONTROLS' and not failed, failed


# Only the tests are re-exported if CI's curated list includes this module (tests/contract/curated_contracts.py).
__all__ = [name for name in dir() if name.startswith('test_')]
