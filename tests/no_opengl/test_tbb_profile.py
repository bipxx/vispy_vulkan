"""The extra CPU runtime has a real ABI, narrow contents and original license."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl.tbb_profile import build


def test_core_profile_keeps_pinned_numba_abi_and_omits_unavailable_plugins():
    manifest = json.loads((ROOT / 'compat/dependencies/windows-numba-tbb.json').read_text())
    assert manifest['numba']['version'] == '0.68.0'
    assert manifest['numba']['observed_interface_version'] >= manifest['numba']['minimum_interface_version'] == 12060
    assert manifest['numba']['required_symbols'] and len(set(manifest['numba']['required_symbols'])) == len(manifest['numba']['required_symbols'])
    assert manifest['core']['source'].endswith('/tbb12.dll')
    assert any('tbbbind' in name for name in manifest['excluded_optional_plugins'])
    assert manifest['runtime_license'] == 'Intel Simplified Software License'
    assert manifest['original_notices'] and all(len(item['sha256']) == 64 for item in manifest['original_notices'])


def test_changed_original_runtime_is_rejected_before_packaging(tmp_path):
    manifest = ROOT / 'compat/dependencies/windows-numba-tbb.json'
    changed = tmp_path / 'changed.whl'
    changed.write_bytes(b'not the pinned original runtime')
    with pytest.raises(ValueError, match='Pinned original'):
        build(manifest, changed, tmp_path / 'output')
