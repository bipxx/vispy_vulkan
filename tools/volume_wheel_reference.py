# SPDX-License-Identifier: AGPL-3.0-only
"""Original scalar/categorical volume fixtures and their unchanged comparisons."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import numpy as np
try:
    from . import fixture_volume as scalar
    from . import fixture_napari_volume as categorical
    from .mesh_layout_reference import read_record
except ImportError:
    import fixture_volume as scalar
    import fixture_napari_volume as categorical
    from mesh_layout_reference import read_record

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(os.environ.get('VISPY_VOLUME_WHEEL_REFERENCE', ROOT / 'tests/reference'))
DIRECT_CASES = scalar.CASES
CASES = DIRECT_CASES + categorical.CASES
PACKETS = {
    'volume-opengl': 'a09dc2508961dd8dc24d500b4512d1aa731987435f2dd1b8cbdd55a238cf7e0b',
    'napari-volume-opengl': '85dda2a86b89d17e17f2550c8ce766b5cf4b12a9d4c0499de0dd41a815e4a9e0',
}
LICENSES = {
    'LICENSE': '0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0',
    'LICENSE-BSD': 'a28bb857d763513c810ca843558c12cf97f64b990b855c1ce7f5e291e52fc25c',
}
ARTIFACTS = ('capture', 'expanded_shaders', 'filtered_glir', 'rgba')
SCALAR_COMPARISON = dict(interior_max_abs_u8=2, edge_max_differing_fraction=.001,
                         landmark_exact=True, mask='tools.fixture_volume.masks')
CATEGORICAL_COMPARISON = dict(categorical_exact=True, landmark_exact=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def packet_for(name):
    if name not in CASES:
        raise ValueError(f'Unknown required volume case: {name}')
    return 'volume-opengl' if name in DIRECT_CASES else 'napari-volume-opengl'


def load_manifest(packet, directory=REFERENCE, *, producer_root=ROOT):
    if packet not in PACKETS:
        raise ValueError(f'Unknown original volume packet: {packet}')
    directory = Path(directory) / packet
    body = (directory / 'manifest.json').read_bytes()
    if hashlib.sha256(body).hexdigest() != PACKETS[packet]:
        raise ValueError('Original volume reference manifest differs')
    manifest = json.loads(body)
    direct = packet == 'volume-opengl'
    cases = DIRECT_CASES if direct else categorical.CASES
    stem = 'volume' if direct else 'napari_volume'
    provenance = manifest['provenance']
    assert manifest['schema'] == 1 and manifest['errors'] == {}
    assert set(manifest['fixtures']) == set(cases)
    assert manifest['comparison'] == (SCALAR_COMPARISON if direct else CATEGORICAL_COMPARISON)
    assert provenance['kind'] == 'upstream' and provenance['vispy_version'] == '0.17.0'
    for key, name in (
        ('volume_fixture_sha256', f'tools/fixture_{stem}.py'),
        ('volume_capture_sha256', f'tools/oracle_{stem}_capture.py'),
        ('fixture_source_sha256', 'tools/fixture_gloo.py'),
    ):
        assert sha(Path(producer_root) / name) == provenance[key], name
    if not direct:
        assert provenance['napari_version'] == '0.9.2'
        assert provenance['installed']['numba'] == '0.68.0'
        assert sha(Path(producer_root) / 'tools/oracle_napari_requirements.txt') == provenance['host_requirements_sha256']
    for name, digest in LICENSES.items():
        assert sha(Path(producer_root) / name) == digest, name
    return manifest


def assert_landmarks(name, image):
    (scalar if name in DIRECT_CASES else categorical).assert_landmarks(name, image)


def load_case(name, directory=REFERENCE, *, producer_root=ROOT):
    packet = packet_for(name)
    manifest = load_manifest(packet, directory, producer_root=producer_root)
    record = manifest['fixtures'][name]
    bodies = {key: read_record(Path(directory) / packet, record[key]) for key in ARTIFACTS}
    capture = json.loads(bodies['capture'])
    assert capture['errors'] == {} and capture['comparison'] == manifest['comparison']
    assert capture['provenance']['kind'] == 'upstream'
    assert capture['provenance']['volume_fixture_sha256'] == manifest['provenance']['volume_fixture_sha256']
    assert set(capture['fixtures']) == {name}
    captured = capture['fixtures'][name]
    for key in ARTIFACTS:
        if key != 'capture':
            assert captured[key] == record[key], (name, key)
    assert captured['parameters'] == record['parameters']
    assert json.loads(bodies['expanded_shaders']) and json.loads(bodies['filtered_glir'])
    params = record['parameters']
    assert params['case'] == name and params['size'] == [96, 96]
    assert params['relative_step_size'] == .5
    if name in DIRECT_CASES:
        assert set(params['exposed_methods']) == set(scalar.METHODS)
        assert params['exposed_raycasting_modes'] == ['volume', 'plane']
        assert params['data_sha256'] == hashlib.sha256(scalar.phantom().tobytes()).hexdigest()
        assert params['shape'] == [32, 32, 32] and params['dtype'] == '<f4'
        assert params['texture_format'] == 'r32f' and params['clim'] == [0, 1]
    else:
        assert params['labels'] == [0, 7, 65537, 16777473]
        assert params['inputs'][0]['shape'] == [32, 32, 32] and params['inputs'][0]['dtype'] == '<i4'
        assert params['inputs'][0]['sha256'] == hashlib.sha256(categorical.labels().tobytes()).hexdigest()
        assert 'QOpenGLWidget' in params['native_mro']
    image = np.load(io.BytesIO(bodies['rgba']), allow_pickle=False)
    assert image.dtype == np.uint8 and image.shape == tuple(record['shape']) == (96, 96, 4)
    assert_landmarks(name, image)
    image.setflags(write=False)
    return image, params


def compare_case(name, image, reference, params, expected):
    packet_for(name)
    assert image.shape == reference.shape == (96, 96, 4)
    assert image.dtype == reference.dtype == np.uint8
    actual, original = dict(params), dict(expected)
    if name not in DIRECT_CASES:
        assert 'QOpenGLWidget' in original.pop('native_mro')
        assert 'QOpenGLWidget' not in actual.pop('native_mro')
    assert actual == original, (name, 'Volume parameters differ')
    difference = np.abs(image.astype(np.int16) - reference.astype(np.int16))
    if name in DIRECT_CASES:
        interior, edge = scalar.masks(name, image.shape)
        assert np.all(interior ^ edge), 'Every pixel must belong to exactly one original region'
        maximum = int(difference[interior].max())
        differing_edge = int(np.count_nonzero(np.any(difference != 0, axis=2) & edge))
        edge_pixels = int(np.count_nonzero(edge))
        assert maximum <= 2, (name, 'Original interior error exceeded', maximum)
        assert differing_edge <= edge_pixels * .001, (name, 'Original edge mismatch exceeded', differing_edge)
    else:
        assert np.array_equal(image, reference), (name, 'Exact categorical RGBA differs')
        maximum = differing_edge = edge_pixels = 0
    assert_landmarks(name, image)
    return dict(interior_maximum_channel_error=maximum, edge_differing_pixels=differing_edge,
                original_edge_pixels=edge_pixels, semantic_observations_exact=True,
                comparison_criteria_passed=True)


def render(name, backend='dawn_headless'):
    packet_for(name)
    return scalar.render(name, backend) if name in DIRECT_CASES else categorical.render(name)
