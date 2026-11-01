# SPDX-License-Identifier: AGPL-3.0-only
"""D30: every successor reference packet records its napari version and binds its successor fixture, the retained
fixture that fixture reuses, the successor capture and the oracle's host lock.

The retained packets keep their own bindings (tests/contract/test_napari_*_reference.py and
tests/contract/test_reference_inventory.py); these are the packets in tests/reference/<base>-napari-<version>/.
"""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re

import numpy as np
import pytest

from tools.napari_host_packets import packets

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / 'tools/oracle_napari_successor_capture.py'
SUITES = ('scientific', 'layer_controls', 'layer_families', 'vector_layers', 'volume')
# The parameters the retained binding tests compare with the fixture's specification.
FIXED = {'layer_controls': ('case', 'size', 'camera', 'controls', 'background', 'criterion', 'inputs_sha256'),
         'layer_families': ('case', 'size', 'camera', 'background', 'criterion', 'inputs_sha256'),
         'vector_layers': ('case', 'size', 'camera_center', 'camera_zoom', 'background', 'criterion', 'inputs_sha256')}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_lock(packet, lock):
    """The packet keeps the oracle's lock it names, so every checkout can verify it."""
    assert lock['file'] and re.fullmatch('[0-9a-f]{64}', lock['sha256']), packet.name
    assert lock['snapshot'] == 'host-lock.txt' and digest(packet / lock['snapshot']) == lock['sha256'], packet.name
    if (ROOT / lock['file']).is_file():  # the stock host locks themselves are local files (gitignored)
        assert digest(ROOT / lock['file']) == lock['sha256'], packet.name


def capture_tool(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('successor_capture_references', CAPTURE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('suite', SUITES)
def test_every_successor_packet_binds_its_napari_version_and_sources(suite, monkeypatch):
    capture = capture_tool(monkeypatch)
    entry = capture.SUITES[suite]
    fixture = importlib.import_module(f'tools.{entry.module}')
    found = packets(entry.base)
    assert found, f'no {entry.base} successor packet: capture one with tools/oracle_napari_successor_capture.py'
    for version, packet in found.items():
        manifest = json.loads((packet / 'manifest.json').read_text(encoding='utf-8'))
        origins = manifest['provenance']
        assert origins['kind'] == 'upstream' and origins['vispy_version'] == '0.17.0', packet.name
        assert origins['suite'] == suite and origins['napari_version'] == version, packet.name
        assert origins['fixture_source_sha256'] == digest(ROOT / f'tools/{entry.module}.py'), packet.name
        assert origins['retained_fixture_source_sha256'] == digest(ROOT / entry.retained), packet.name
        assert origins['capture_source_sha256'] == digest(CAPTURE), packet.name
        check_lock(packet, origins['host_lock'])
        assert manifest['comparison'] == json.loads(json.dumps(capture.comparison(suite))), packet.name
        assert not manifest['errors'] and set(manifest['fixtures']) == set(fixture.CASES), packet.name
        for name, record in manifest['fixtures'].items():
            assert record['process'] == {'exit_code': 0}, (packet.name, name)
            if entry.record == 'criterion':
                assert record['criterion'] == fixture.CRITERIA[name], (packet.name, name)
            elif entry.record == 'exact':
                assert record['exact'] == (name in fixture.EXACT), (packet.name, name)
            if suite in FIXED:
                fixed = FIXED[suite]
                assert ({key: record['parameters'][key] for key in fixed}
                        == {key: fixture.specification(name)[key] for key in fixed}), (packet.name, name)
            for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'], record['capture']):
                assert digest(packet / artifact['file']) == artifact['sha256'], (packet.name, artifact['file'])
            fixture.assert_landmarks(name, np.load(packet / record['rgba']['file'], allow_pickle=False))


def test_every_image_extension_packet_binds_its_freeze_and_sources():
    from tools.fixture_image_extensions_successor import CASES, COMPARISON, assert_landmarks, case_contract

    found = packets('image-extensions-opengl')
    assert found, ('no image-extensions-opengl successor packet: freeze and capture one with '
                   'tools/oracle_image_extensions_successor_capture.py')
    for version, packet in found.items():
        authoring = json.loads((packet / 'authoring.json').read_text(encoding='utf-8'))
        assert authoring['candidate_seen'] is False and authoring['GPU_used'] is False, packet.name
        assert authoring['napari_version'] == version and authoring['comparison'] == COMPARISON, packet.name
        assert authoring['cases'] == {name: case_contract(name) for name in CASES}, packet.name
        for source, sha in authoring['sources_sha256'].items():
            assert digest(ROOT / source) == sha == digest(packet / 'authoring-sources' / Path(source).name), source
        lock = authoring['installed_upstream_lock']
        check_lock(packet, lock)
        manifest = json.loads((packet / 'manifest.json').read_text(encoding='utf-8'))
        origins = manifest['provenance']
        assert origins['kind'] == 'upstream' and origins['napari_version'] == version, packet.name
        assert origins['host_lock'] == lock and manifest['authoring_sha256'] == digest(packet / 'authoring.json')
        assert origins['fixture_sha256'] == authoring['sources_sha256']['tools/fixture_image_extensions_successor.py']
        assert origins['retained_fixture_sha256'] == authoring['sources_sha256']['tools/fixture_image_extensions.py']
        assert manifest['comparison'] == COMPARISON and not manifest['errors'], packet.name
        assert set(manifest['fixtures']) == set(CASES), packet.name
        for name, record in manifest['fixtures'].items():
            assert manifest['processes'][name]['exit_code'] == 0, (packet.name, name)
            for artifact in (record['rgba'], record['filtered_glir'], record['expanded_shaders'],
                             record['parameters_file'], record['capture']):
                assert digest(packet / artifact['file']) == artifact['sha256'], (packet.name, artifact['file'])
            for key, expected in case_contract(name).items():
                assert record['parameters'][key] == expected, (packet.name, name, key)
            assert_landmarks(name, np.load(packet / record['rgba']['file'], allow_pickle=False))


__all__ = [name for name in dir() if name.startswith('test_')]
