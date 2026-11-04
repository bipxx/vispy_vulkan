# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of tools/image_wheel_reference.py: read the original image/label references without
regenerating expectations, on the napari release NAPARI names.

The packet is the image successor fixture's per-version packet (tests/reference/image-extensions-opengl-napari-<version>),
which binds its freeze and sources (tests/contract/test_napari_successor_references.py). load_case and compare_case are
the retained code, rebound to this module's inputs (the successor fixture's case_contract, this packet); load_manifest
is the retained one verifying the oracle's host lock by the packet's own snapshot, as every checkout can.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import types
import numpy as np
try:
    from . import image_wheel_reference as retained
    from .fixture_image_extensions_successor import CASES, COMPARISON, assert_landmarks, case_contract
    from .napari_host_packets import packet_dir
except ImportError:
    import image_wheel_reference as retained
    from fixture_image_extensions_successor import CASES, COMPARISON, assert_landmarks, case_contract
    from napari_host_packets import packet_dir

ROOT, LICENSES, OBSERVATIONS, ARTIFACTS = retained.ROOT, retained.LICENSES, retained.OBSERVATIONS, retained.ARTIFACTS
read_record, sha = retained.read_record, retained.sha
NAPARI = '0.10.0'
REFERENCE = packet_dir('image-extensions-opengl', NAPARI)
MANIFEST_SHA256 = 'afa230b2a6b8bcc1f3676a7a36fa6580bec5c5b98254e7b32a4d20135491dfb0'


def _retained(function, defaults=None):
    """The retained step's own code, reading this module's inputs."""
    rebound = types.FunctionType(function.__code__, globals(), function.__name__,
                                 function.__defaults__ if defaults is None else defaults, function.__closure__)
    rebound.__kwdefaults__ = function.__kwdefaults__
    return rebound


load_case = _retained(retained.load_case, defaults=(REFERENCE,))
compare_case = _retained(retained.compare_case)


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
    # The packet keeps the oracle's host lock as its snapshot, so every checkout can verify it.
    assert sha(directory / lock['snapshot']) == lock['sha256']
    for name, digest in LICENSES.items():
        assert sha(Path(producer_root) / name) == digest, f'Attached license differs: {name}'
    return manifest
