# SPDX-License-Identifier: AGPL-3.0-only
"""Independent installed napari/OpenGL reference capture of the successor fixtures (D30), one isolated process per case.

The retained capture tools pin napari 0.9.2 and stay bound to their packets. This tool captures any napari release
into a fresh packet, tests/reference/<base>-napari-<installed napari>/ unless --output names another fresh directory.
Each packet records its napari version, the successor and retained fixture sources, this tool and the oracle's host
lock; the per-case records keep the keys the retained capture tool writes for that suite. For napari 0.10.0, with the
oracle environment built from the stock lock (upstream vispy 0.17.0, PyQt6) plus run 207's numba lock:
    <oracle>/Scripts/python.exe tools/oracle_napari_successor_capture.py --suite layer_controls --kind upstream \
        --host-lock compat/host-environments/napari-0.10.0-windows-cpython312-pyqt6.txt
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from typing import NamedTuple

import numpy as np

from napari_host_packets import LOCK_SNAPSHOT, lock_mismatches, packet_dir
from oracle_capture import ROOT, provenance, sha256, write_json


class Suite(NamedTuple):
    base: str  # the retained packet's directory under tests/reference
    module: str  # the successor fixture module in tools/
    retained: str  # the retained fixture source
    comparison: dict | None  # the retained capture's comparison block; None: criteria and the smooth-line rule
    record: str | None  # the per-case key the retained capture adds: 'criterion', 'exact' or nothing
    host_sources: tuple = ()  # napari sources whose hashes the retained capture records


SUITES = {
    'scientific': Suite('napari-opengl', 'fixture_napari_successor', 'tools/fixture_napari.py',
                        {'interior_max_abs_u8': 2, 'edge_max_differing_fraction': .001, 'categorical_exact': True,
                         'mask': 'tools.fixture_napari.masks'}, 'exact'),
    'layer_controls': Suite('napari-layer-controls-opengl', 'fixture_napari_layer_controls_successor',
                            'tools/fixture_napari_layer_controls.py', None, 'criterion'),
    'layer_families': Suite('napari-layer-families-opengl', 'fixture_napari_layer_families_successor',
                            'tools/fixture_napari_layer_families.py', None, 'criterion'),
    'vector_layers': Suite('napari-vector-layers-opengl', 'fixture_napari_vector_layers_successor',
                           'tools/fixture_napari_vector_layers.py', None, 'criterion'),
    'volume': Suite('napari-volume-opengl', 'fixture_napari_volume_successor', 'tools/fixture_napari_volume.py',
                    {'categorical_exact': True, 'landmark_exact': True}, None,
                    ('_vispy/visuals/volume.py', '_vispy/layers/labels.py', '_vispy/camera.py')),
}


def successor(suite):
    return importlib.import_module(SUITES[suite].module)


def comparison(suite):
    entry = SUITES[suite]
    if entry.comparison is not None:
        return entry.comparison
    return {'criteria': successor(suite).CRITERIA, 'smooth_line': 'tools.smooth_line_parity.smooth_line_difference'}


def napari_identity() -> tuple[str, str]:
    """The installed napari's version and package origin, read without importing napari."""
    return metadata.version('napari'), importlib.util.find_spec('napari').origin


def portable(path: Path) -> str:
    """A repository-relative POSIX path, so a packet captured on Windows names its lock the same way everywhere."""
    resolved = Path(path).resolve()
    return resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else resolved.as_posix()


def host_provenance(suite: str, napari_version: str, napari_origin: str, host_lock: Path | None) -> dict:
    """What the packet binds besides the renderer: napari, both fixture sources, this tool and the host lock."""
    entry = SUITES[suite]
    record = {'suite': suite, 'napari_version': napari_version, 'napari_origin': napari_origin,
              'fixture_source_sha256': sha256(ROOT / f'tools/{entry.module}.py'),
              'retained_fixture_source_sha256': sha256(ROOT / entry.retained),
              'capture_source_sha256': sha256(Path(__file__)),
              'host_lock': None if host_lock is None else {'file': portable(host_lock), 'sha256': sha256(host_lock),
                                                           'snapshot': LOCK_SNAPSHOT},
              'installed': {dist.metadata['Name']: dist.version for dist in metadata.distributions()}}
    if entry.host_sources:
        package = Path(napari_origin).resolve().parent
        record['host_source_sha256'] = {name: sha256(package / name) for name in entry.host_sources}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--suite', choices=SUITES, required=True)
    parser.add_argument('--kind', choices=('upstream', 'candidate'), required=True)
    parser.add_argument('--output', type=Path, help='a fresh directory (default: the packet for the installed napari)')
    parser.add_argument('--host-lock', type=Path, help="the oracle environment's lock; required for --kind upstream")
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.kind == 'upstream' and args.host_lock is None:
        parser.error('--host-lock is required for --kind upstream')
    if args.host_lock is not None and not args.host_lock.is_file():
        parser.error(f'--host-lock {args.host_lock} is not a file')
    if args.kind == 'candidate' and args.output is None:
        parser.error('--output is required for --kind candidate: the packet is the reference')
    entry = SUITES[args.suite]
    output = args.output or packet_dir(entry.base, napari_identity()[0])
    if not args.worker and output.exists() and any(output.iterdir()):
        raise SystemExit(f'fresh output required: {output} is not empty')
    if not args.worker and args.host_lock is not None:
        mismatches = lock_mismatches(args.host_lock)
        if mismatches:
            raise SystemExit(f'the host lock {args.host_lock} does not describe this environment: {mismatches[:5]}')
    os.environ.setdefault('QT_API', 'pyqt6')
    os.environ.setdefault('QT_SCALE_FACTOR', '1')
    os.environ.setdefault('VISPY_PYQT5_SHARE_CONTEXT', 'true')
    assert os.environ.get('QT_QPA_PLATFORM') != 'offscreen'
    fixture = successor(args.suite)
    if args.worker:
        assert args.worker in fixture.CASES, args.worker
    if args.kind == 'upstream':
        import vispy
        vispy.use(gl='gl+')
    origins = provenance(args.kind)
    origins.update(host_provenance(args.suite, *napari_identity(), args.host_lock))
    output.mkdir(parents=True, exist_ok=True)
    if not args.worker and args.host_lock is not None:
        shutil.copyfile(args.host_lock, output / LOCK_SNAPSHOT)
    manifest = {'schema': 1, 'provenance': origins, 'comparison': comparison(args.suite), 'fixtures': {}, 'errors': {}}
    for name in ([args.worker] if args.worker else fixture.CASES):
        if not args.worker:
            captured = output / f'{name}.capture.json'
            command = [sys.executable, '-X', 'faulthandler', str(Path(__file__)), '--suite', args.suite,
                       '--kind', args.kind, '--output', str(output), '--worker', name]
            if args.host_lock is not None:
                command += ['--host-lock', str(args.host_lock)]
            child = subprocess.run(command, capture_output=True, text=True)
            (output / f'{name}.stdout.log').write_text(child.stdout, encoding='utf-8')
            (output / f'{name}.stderr.log').write_text(child.stderr, encoding='utf-8')
            if captured.exists():
                data = json.loads(captured.read_text(encoding='utf-8'))
                if child.returncode == 0:
                    manifest['fixtures'].update(data['fixtures'])
                manifest['errors'].update(data['errors'])
                if name in manifest['fixtures']:
                    manifest['fixtures'][name]['capture'] = {'file': captured.name, 'sha256': sha256(captured)}
                    manifest['fixtures'][name]['process'] = {'exit_code': child.returncode}
            if child.returncode and name not in manifest['errors']:
                manifest['errors'][name] = {'error': f'capture subprocess exited {child.returncode}'}
            print(name, 'exit', child.returncode, flush=True)
            continue
        try:
            image, commands, shaders, params = fixture.render(name)
            fixture.assert_landmarks(name, image)
            assert commands and shaders
            arrays, trace, source = (output / f'{name}{suffix}' for suffix in ('.npy', '.glir.json', '.shaders.json'))
            np.save(arrays, image, allow_pickle=False)
            write_json(trace, commands)
            write_json(source, shaders)
            record = {'parameters': params, 'shape': list(image.shape)}
            if entry.record == 'criterion':
                record['criterion'] = fixture.CRITERIA[name]
            elif entry.record == 'exact':
                record['exact'] = name in fixture.EXACT
            record.update({'rgba': {'file': arrays.name, 'sha256': sha256(arrays)},
                           'filtered_glir': {'file': trace.name, 'sha256': sha256(trace)},
                           'expanded_shaders': {'file': source.name, 'sha256': sha256(source)}})
            manifest['fixtures'][name] = record
            print(f'PASS napari {args.suite} {name}: {image.shape}, independent {args.kind}', flush=True)
        except Exception as exc:
            manifest['errors'][name] = {'type': type(exc).__name__, 'error': str(exc)}
            traceback.print_exc()
    write_json(output / (f'{args.worker}.capture.json' if args.worker else 'manifest.json'), manifest)
    return 1 if manifest['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
