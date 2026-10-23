# SPDX-License-Identifier: AGPL-3.0-only
"""Read the original image/label references without regenerating expectations."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import numpy as np
try:
    from .fixture_image_extensions import CASES, COMPARISON, assert_landmarks, case_contract
    from .mesh_layout_reference import read_record
except ImportError:
    from fixture_image_extensions import CASES, COMPARISON, assert_landmarks, case_contract
    from mesh_layout_reference import read_record

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(os.environ.get('VISPY_IMAGE_REFERENCE', ROOT / 'tests/reference/image-extensions-opengl/api-correct-attempt-2'))
MANIFEST_SHA256 = '9675b84eda8cd0c910d31fa668c6b77cda35ea94f26e8bc2e45a8d0ccd7bf70d'
LICENSES = {
    'LICENSE': '0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0',
    'LICENSE-BSD': 'a28bb857d763513c810ca843558c12cf97f64b990b855c1ce7f5e291e52fc25c',
}
OBSERVATIONS = ('actual_label_remap', 'partial_labels_events', 'source_revisions',
                'selected_level_sequence', 'selected_slice_sequence', 'initial_slice_records')
ARTIFACTS = ('capture', 'expanded_shaders', 'filtered_glir', 'parameters_file', 'rgba')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(directory=REFERENCE, *, producer_root=ROOT):
    directory = Path(directory)
    body = (directory / 'manifest.json').read_bytes()
    if hashlib.sha256(body).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Original image reference manifest differs')
    manifest = json.loads(body)
    assert manifest['schema'] == 1 and manifest['errors'] == {}
    assert manifest['comparison'] == COMPARISON
    assert manifest['provenance']['kind'] == 'upstream'
    assert set(manifest['fixtures']) == set(manifest['processes']) == set(CASES)
    author = json.loads(read_record(directory, dict(file='authoring.json', sha256=manifest['authoring_sha256'])))
    assert author['candidate_seen'] is False and author['GPU_used'] is False
    assert author['comparison'] == COMPARISON
    assert author['cases'] == {name: case_contract(name) for name in CASES}
    for name, digest in author['sources_sha256'].items():
        assert sha(Path(producer_root) / name) == digest, f'Original image fixture source differs: {name}'
    lock = author['installed_upstream_lock']
    # The original authoring was written on Windows; retain its bytes while
    # interpreting the recorded relative path on every host.
    assert sha(Path(producer_root) / lock['file'].replace('\\', '/')) == lock['sha256']
    for name, digest in LICENSES.items():
        assert sha(Path(producer_root) / name) == digest, f'Attached license differs: {name}'
    return manifest


def load_case(name, directory=REFERENCE, *, producer_root=ROOT):
    if name not in CASES:
        raise ValueError(f'Unknown required image case: {name}')
    manifest = load_manifest(directory, producer_root=producer_root)
    record = manifest['fixtures'][name]
    process = manifest['processes'][name]
    assert process['exit_code'] == 0
    for key in ('stdout', 'stderr'):
        read_record(directory, process[key])
    bodies = {key: read_record(directory, record[key]) for key in ARTIFACTS}
    capture = json.loads(bodies['capture'])
    assert capture['authoring_sha256'] == manifest['authoring_sha256']
    assert capture['comparison'] == COMPARISON and capture['errors'] == {}
    assert capture['provenance']['kind'] == 'upstream'
    assert set(capture['fixtures']) == {name}
    captured = capture['fixtures'][name]
    for key in ARTIFACTS:
        if key != 'capture':
            assert captured[key] == record[key], (name, key)
    assert captured['parameters'] == record['parameters']
    assert record['actual_renderer_provenance']['kind'] == 'upstream'
    params = json.loads(bodies['parameters_file'])
    assert params == record['parameters']
    for key, value in case_contract(name).items():
        assert params[key] == value, (name, key)
    assert json.loads(bodies['expanded_shaders']) and json.loads(bodies['filtered_glir'])
    image = np.load(io.BytesIO(bodies['rgba']), allow_pickle=False)
    assert image.dtype == np.uint8 and image.shape == tuple(record['shape']) == (96, 128, 4)
    assert_landmarks(name, image)
    image.setflags(write=False)
    return image, params


def compare_case(name, image, reference, params, expected):
    assert image.shape == reference.shape == (96, 128, 4)
    assert image.dtype == reference.dtype == np.uint8
    assert np.array_equal(image, reference), (name, 'Full-frame RGBA differs',
        int(np.abs(image.astype(np.int16) - reference.astype(np.int16)).max()))
    assert_landmarks(name, image)
    for key, value in case_contract(name).items():
        assert params[key] == expected[key] == value, (name, key)
    for key in OBSERVATIONS:
        assert (key in params) == (key in expected), (name, key, 'presence')
        if key in expected:
            assert params[key] == expected[key], (name, key)
