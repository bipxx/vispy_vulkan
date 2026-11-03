# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of tools/volume_wheel_reference.py: the original scalar and categorical volume fixtures and
their unchanged comparisons, with the categorical (napari) cases on the napari release NAPARI names.

The scalar packet (volume-opengl) has no napari, so it stays the retained packet, read by the retained load_manifest.
The categorical cases render with the napari volume successor fixture and compare with its per-version packet, which
binds the successor and retained fixtures, the capture tool and the oracle's host lock
(tests/contract/test_napari_successor_references.py). assert_landmarks, compare_case and render are the retained code,
rebound to this module's inputs; load_case is the retained one reading the packet's fixture_source_sha256, the D30 key
for the retained format's volume_fixture_sha256; packet_for and load_manifest are this module's own.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import types
import numpy as np
try:
    from . import volume_wheel_reference as retained
    from . import fixture_napari_volume_successor as categorical
    from .napari_host_packets import LOCK_SNAPSHOT, packet_dir
except ImportError:
    import volume_wheel_reference as retained
    import fixture_napari_volume_successor as categorical
    from napari_host_packets import LOCK_SNAPSHOT, packet_dir

ROOT, REFERENCE, scalar, read_record, sha = retained.ROOT, retained.REFERENCE, retained.scalar, retained.read_record, retained.sha
DIRECT_CASES, CASES, LICENSES, ARTIFACTS = retained.DIRECT_CASES, retained.CASES, retained.LICENSES, retained.ARTIFACTS
SCALAR_COMPARISON, CATEGORICAL_COMPARISON = retained.SCALAR_COMPARISON, retained.CATEGORICAL_COMPARISON
NAPARI = '0.10.0'
CATEGORICAL = packet_dir('napari-volume-opengl', NAPARI).name
PACKETS = {
    'volume-opengl': retained.PACKETS['volume-opengl'],
    CATEGORICAL: 'ea07cc6bfc29dccc1c5faa6ec33b40d0310a35251d6464d852a912c721482c47',
}


def _retained(function, defaults=None):
    """The retained step's own code, reading this module's inputs."""
    rebound = types.FunctionType(function.__code__, globals(), function.__name__,
                                 function.__defaults__ if defaults is None else defaults, function.__closure__)
    rebound.__kwdefaults__ = function.__kwdefaults__
    return rebound


assert_landmarks = _retained(retained.assert_landmarks)
compare_case = _retained(retained.compare_case)
render = _retained(retained.render)


def packet_for(name):
    if name not in CASES:
        raise ValueError(f'Unknown required volume case: {name}')
    return 'volume-opengl' if name in DIRECT_CASES else CATEGORICAL


def load_manifest(packet, directory=REFERENCE, *, producer_root=ROOT):
    if packet == 'volume-opengl':  # no napari: the retained packet, with the retained checks
        return retained.load_manifest(packet, directory, producer_root=producer_root)
    if packet != CATEGORICAL:
        raise ValueError(f'Unknown original volume packet: {packet}')
    directory = Path(directory) / packet
    body = (directory / 'manifest.json').read_bytes()
    if hashlib.sha256(body).hexdigest() != PACKETS[packet]:
        raise ValueError('Original volume reference manifest differs')
    manifest = json.loads(body)
    provenance = manifest['provenance']
    assert manifest['schema'] == 1 and manifest['errors'] == {}
    assert set(manifest['fixtures']) == set(categorical.CASES)
    assert manifest['comparison'] == CATEGORICAL_COMPARISON
    assert provenance['kind'] == 'upstream' and provenance['vispy_version'] == '0.17.0'
    assert provenance['napari_version'] == NAPARI and provenance['installed']['numba'] == '0.68.0'
    for key, name in (('fixture_source_sha256', 'tools/fixture_napari_volume_successor.py'),
                      ('retained_fixture_source_sha256', 'tools/fixture_napari_volume.py'),
                      ('capture_source_sha256', 'tools/oracle_napari_successor_capture.py')):
        assert sha(Path(producer_root) / name) == provenance[key], name
    assert sha(directory / LOCK_SNAPSHOT) == provenance['host_lock']['sha256']
    for name, digest in LICENSES.items():
        assert sha(Path(producer_root) / name) == digest, name
    return manifest


def load_case(name, directory=REFERENCE, *, producer_root=ROOT):
    packet = packet_for(name)
    manifest = load_manifest(packet, directory, producer_root=producer_root)
    record = manifest['fixtures'][name]
    bodies = {key: read_record(Path(directory) / packet, record[key]) for key in ARTIFACTS}
    capture = json.loads(bodies['capture'])
    assert capture['errors'] == {} and capture['comparison'] == manifest['comparison']
    assert capture['provenance']['kind'] == 'upstream'
    assert capture['provenance']['fixture_source_sha256'] == manifest['provenance']['fixture_source_sha256']
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
