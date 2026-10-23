# SPDX-License-Identifier: AGPL-3.0-only
"""Portable immutable-reference admission without a renderer import."""
import json
from pathlib import Path
import pytest
from tools import large_image_wheel_suite as suite

REFERENCE_SHA256 = 'ace47caea32759727170debd5a08db2c3255b29296873090290f12a12670c4d2'
REFERENCE = suite.ROOT/'tests/reference/large-image-opengl'


@pytest.mark.parametrize('name', suite.CASES)
def test_immutable_reference_has_all_full_frames_and_matching_sources(name):
    directory = suite.load_reference(REFERENCE, REFERENCE_SHA256, name)
    assert directory == REFERENCE/name
    parameters = json.loads((directory/'parameters.json').read_bytes())
    assert parameters['framebuffer_shape'] == [4096, 4096, 4]
    assert parameters['stages'] == ['baseline', 'repeat', 'pan', 'return']


@pytest.mark.parametrize('mutation', ('digest', 'parent', 'source'))
def test_reference_rejects_changed_digest_failed_parent_and_source_drift(tmp_path, mutation):
    manifest = json.loads((REFERENCE/'manifest.json').read_bytes())
    if mutation == 'parent': manifest['status'] = 'FAILED_REQUIRED_LARGE_IMAGES'
    if mutation == 'source': manifest['sources_sha256']['tools/fixture_large_image.py'] = '0'*64
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    digest = '0'*64 if mutation == 'digest' else suite.sha(path)
    with pytest.raises(AssertionError):
        suite.load_reference(tmp_path, digest, suite.CASES[0])
