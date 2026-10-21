# SPDX-License-Identifier: AGPL-3.0-only
"""Keep the corrected cache protocol separate from historical failed references."""
import copy
import hashlib
from pathlib import Path
import zipfile
import numpy as np
from packaging.tags import sys_tags
import pytest
from tools import glue_wheel_suite as suite


def analytic_frame(name):
    image = np.zeros((128, 128, 4), np.uint8)
    image[:, :, 3] = 255
    if name in ('scatter', 'scatter_axes'):
        image[64, 38] = image[64, 90] = [255, 0, 0, 255]
    elif name == 'scatter_edit':
        image[64, 64] = [0, 0, 255, 255]
    elif name == 'volume':
        image[64, 64] = [0, 255, 0, 255]
    else:
        image[64, 88] = [0, 0, 255, 255]
    return image


@pytest.mark.parametrize('name', suite.CASES)
def test_all_original_landmarks_and_exact_alpha_remain_required(name):
    image = analytic_frame(name)
    expected = dict(case=name, inputs=[dict(sha256='original-input')], native_mro=['QOpenGLWidget'])
    actual = dict(expected, native_mro=['DawnWidget'])
    suite.compare(name, image, image, actual, expected)
    changed = image.copy()
    changed[0, 0, 3] ^= 1
    with pytest.raises(AssertionError, match='Exact full Glue frame differs'):
        suite.compare(name, changed, image, actual, expected)
    actual['inputs'] = [dict(sha256='changed-input')]
    with pytest.raises(AssertionError, match='host state/inputs differ'):
        suite.compare(name, image, image, actual, expected)


def test_cache_fix_preserves_the_entire_original_fixture_except_two_protocol_lines():
    old = (suite.ROOT / 'tools/fixture_glue.py').read_bytes()
    new = (suite.ROOT / 'tools/fixture_glue_extensions.py').read_bytes()
    assert hashlib.sha256(old).hexdigest() == 'f5dcf37968064a83282c3eb1e73548c4a7136249c2b7753f01e10bf2cbd02f9b'
    header = b'# SPDX-License-Identifier: AGPL-3.0-only\n'
    insertion = b'                from glue.core.fixed_resolution_buffer import invalidate_cache\n                invalidate_cache(data)\n'
    assert new.startswith(header) and new.count(insertion) == 1
    assert new[len(header):].replace(insertion, b'') == old
    assert b'invalidate_cache(data)\n                data.update_components' in new


def test_only_the_renderer_requirement_is_removed_from_the_pinned_host_closure():
    import re
    original = (suite.ROOT / 'tools/oracle_glue_requirements.txt').read_text()
    changed = suite.runtime_requirements()
    block = re.search(suite.VISPY_BLOCK, original).group()
    assert changed == original.replace(block, '', 1)
    assert 'glue-core==1.27.0' in changed and 'glue-vispy-viewers==1.4.0' in changed
    assert 'pyqt6-qt6==6.11.2' in changed and 'vispy==' not in changed


def test_historical_failed_upstream_packet_cannot_be_promoted_to_fresh_reference():
    original = suite.ROOT / 'tests/reference/glue-opengl'
    with pytest.raises(AssertionError):
        suite.load_reference(original, suite.sha(original / 'manifest.json'), 'volume_edit')


def test_fixed_upstream_artifact_digest_is_in_the_original_lock():
    assert suite.UPSTREAM_WHEEL_SHA256 in suite.upstream_lock_hashes()


def test_an_arbitrary_upstream_artifact_is_refused_before_package_or_graphics_loading(tmp_path):
    wheel = tmp_path / 'not-the-pinned-original.whl'
    wheel.write_bytes(b'wrong upstream artifact')
    with pytest.raises(AssertionError, match='not the locked CP312 artifact'):
        suite.assert_locked_upstream(wheel)


def test_candidate_widget_cannot_be_an_original_opengl_widget():
    image = analytic_frame('volume_edit')
    params = dict(native_mro=['QOpenGLWidget'])
    with pytest.raises(AssertionError):
        suite.compare('volume_edit', image, image, params, params)


def test_installed_candidate_package_change_is_detected_without_loading_it(tmp_path, monkeypatch):
    package = tmp_path / 'vispy'
    members = {'vispy/__init__.py': b'package',
        'vispy/_licenses/LICENSE': (suite.ROOT / 'LICENSE').read_bytes(),
        'vispy/_licenses/LICENSE-BSD': (suite.ROOT / 'LICENSE-BSD').read_bytes()}
    wheel = tmp_path / 'synthetic.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        for name, body in members.items():
            archive.writestr(name, body)
            destination = tmp_path / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        archive.writestr('vispy.dist-info/METADATA', 'Name: vispy\nVersion: 0.17.0+vulkan.1\n')
        archive.writestr('vispy.dist-info/WHEEL', 'Tag: ' + str(next(sys_tags())) + '\n')
    monkeypatch.setattr(suite.metadata, 'version', lambda name: '0.17.0+vulkan.1')
    assert len(suite.package_hashes(wheel, package, 'candidate')) == 3
    (package / '__init__.py').write_bytes(b'changed installation')
    with pytest.raises(AssertionError):
        suite.package_hashes(wheel, package, 'candidate')
