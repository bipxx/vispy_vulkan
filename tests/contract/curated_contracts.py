# SPDX-License-Identifier: AGPL-3.0-only
"""The contract modules that CI runs through one curated entry.

CI's curated test list (.github/workflows/cpu-contract.yml) is pinned until R2 renews it, so
tests/contract/test_napari_plugin_wheel_suite.py imports this module and CI runs these tests there. At R2 the list
names this file instead, and the wheel suite drops the import. A new contract module is added to MODULES here, never
to an unrelated module. This file has no test_ prefix, so collecting tests/contract does not run the tests again.
"""
import importlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MODULES = ('test_hot_swap_policy', 'test_napari_vector_layers_reference', 'test_napari_layer_families_reference',
           'test_napari_layer_controls_reference', 'test_wide_lines_comparison', 'test_agg_lines_reference',
           'test_markers_d17_reference', 'test_pool_watch', 'test_documented_outcomes', 'test_publication_drift',
           'test_benchmark_frames_w8', 'test_ci_local', 'test_hot_swap_linux_observer')
# Contract modules that no workflow runs, with the reason. A new module goes in MODULES or here.
NOT_IN_CI = {
    **dict.fromkeys(('test_color_volume_linux_wheel_parity', 'test_color_volume_wheel_parity',
                     'test_large_image_wheel_parity', 'test_large_volume_wheel_parity'),
                    'GPU wheel parity: needs VISPY_TEST_WHEEL, the Dawn device and its reference paths'),
    **dict.fromkeys(('test_compatible_sdk', 'test_dive_w10_parameters', 'test_dive_w10_parity_proof',
                     'test_installed_plugin_candidate', 'test_native_sdk', 'test_newer_build_environments',
                     'test_pass25_guards', 'test_plugin_registration', 'test_qt_overlay_packaging',
                     'test_volume_benchmark_adapter3', 'test_windows_wheel_matrix'),
                    'not yet checked in CI\'s environment (consolidated plan, Organization)'),
    'test_hot_swap_linux_native': 'Linux-only native ptrace controls (C compiler, static libc, ptrace); not yet checked '
                                  'in CI\'s environment (W7)',
}
# Contract modules that stay local until their publication; a checkout may lack them.
UNPUBLISHED = {'test_wheel_index': 'W11 index tooling, published with W11 on approval (D2)'}

for _name in MODULES:
    _module = importlib.import_module(_name)
    for _test in _module.__all__:
        if _test in globals():  # a shadowed test would silently never run
            raise ImportError('%s.%s is already curated' % (_name, _test))
        globals()[_test] = getattr(_module, _test)


def test_every_contract_module_runs_in_ci_or_is_declared():
    workflows = ''.join(path.read_text(encoding='utf-8') for path in (ROOT / '.github/workflows').glob('*.yml'))
    named = set(re.findall(r'tests/contract/(test_\w+)\.py', workflows))
    modules = {path.stem for path in (ROOT / 'tests/contract').glob('test_*.py')}
    assert not set(MODULES) & named and not set(NOT_IN_CI) & (named | set(MODULES))
    assert not set(UNPUBLISHED) & (named | set(MODULES) | set(NOT_IN_CI))
    assert modules - named - set(MODULES) - set(UNPUBLISHED) == set(NOT_IN_CI)


__all__ = [name for name in dir() if name.startswith('test_')]
