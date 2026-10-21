"""Isolated installed-wheel comparisons against admitted pinned Glue frames."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

import numpy as np

from fixture_glue import assert_landmarks, render
from oracle_capture import ROOT, provenance, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--worker', choices=('scatter', 'scatter_edit', 'scatter_axes', 'volume'))
    args = parser.parse_args()
    output, wheel = args.output.resolve(), args.wheel.resolve()
    output.mkdir(parents=True, exist_ok=True)
    reference = ROOT / 'tests/reference/glue-opengl'
    oracle = json.loads((reference / 'manifest.json').read_text())
    os.environ.setdefault('QT_API', 'pyqt6')
    os.environ.setdefault('QT_SCALE_FACTOR', '1')
    if args.worker:
        record = {'case': args.worker, 'status': 'failed'}
        try:
            import vispy
            from vispy import _dawn
            vispy.use(app='pyqt6')
            assert metadata.version('vispy') == vispy.__version__ == '0.17.0+vulkan.1'
            package = Path(vispy.__file__).resolve().parent
            assert 'site-packages' in str(package), 'An installed candidate is required'
            native = Path(_dawn.__file__).resolve()
            with zipfile.ZipFile(wheel) as archive:
                member = next(name for name in archive.namelist() if name.endswith('/' + native.name))
                assert hashlib.sha256(archive.read(member)).hexdigest() == sha256(native)
            import glue_vispy_viewers
            host = Path(glue_vispy_viewers.__file__).resolve().parent
            admission = json.loads((ROOT / 'tools/oracle_glue_admission.json').read_text())
            host_sources = {name: sha256(host / name) for name in admission['source_files']}
            assert all(actual == admission['source_files'][name]['sha256']
                       for name, actual in host_sources.items()), 'Pinned host source changed'
            record.update(wheel_sha256=sha256(wheel), native_origin=str(native),
                          native_sha256=sha256(native), host_source_sha256=host_sources,
                          provenance=provenance('candidate'))
            before = dict(_dawn.probe())
            image, commands, shaders, parameters = render(args.worker)
            after = dict(_dawn.probe())
            record.update(counters_before=before, counters_after=after,
                          parameters=parameters, filtered_commands=len(commands))
            np.save(output / f'{args.worker}.candidate.npy', image, allow_pickle=False)
            write_json(output / f'{args.worker}.glir.json', commands)
            write_json(output / f'{args.worker}.shaders.json', shaders)
            expected = dict(oracle['fixtures'][args.worker]['parameters'])
            actual = dict(parameters)
            assert 'QOpenGLWidget' in expected.pop('native_mro')
            assert 'QOpenGLWidget' not in actual.pop('native_mro')
            assert actual == expected, 'Host state/inputs differ from the fixed reference'
            golden = np.load(reference / oracle['fixtures'][args.worker]['rgba']['file'], allow_pickle=False)
            difference = np.abs(image.astype(np.int16) - golden.astype(np.int16))
            np.save(output / f'{args.worker}.difference.npy', difference, allow_pickle=False)
            record['difference'] = {'max_abs_u8': int(difference.max()),
                                    'differing_pixels': int(np.any(difference != 0, axis=-1).sum())}
            assert np.array_equal(image, golden), 'Fixed exact Glue frame mismatch'
            assert_landmarks(args.worker, image)
            assert commands and shaders
            for key in ('draw_calls', 'pipeline_misses', 'vk_queue_submits'):
                assert after[key] > before[key], f'Actual native {key} was not observed'
            record['status'] = 'passed'
            print('PASS installed Glue', args.worker, record['difference'], flush=True)
        except Exception as error:
            record.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
            traceback.print_exc()
        finally:
            record['artifacts'] = {path.name: sha256(path) for path in output.glob(args.worker + '.*')
                                   if path.suffix not in ('.log',) and not path.name.endswith('.result.json')}
            write_json(output / f'{args.worker}.result.json', record)
        return int(record['status'] != 'passed')

    manifest = {'schema': 1, 'wheel': str(wheel), 'wheel_sha256': sha256(wheel),
                'reference_manifest_sha256': sha256(reference / 'manifest.json'),
                'fixture_sha256': sha256(ROOT / 'tools/fixture_glue.py'),
                'harness_sha256': sha256(Path(__file__)),
                'scope': 'Four admitted installed Glue workflows; original unresolved volume_edit remains open',
                'cases': {}}
    for name in ('scatter', 'scatter_edit', 'scatter_axes', 'volume'):
        command = [sys.executable, '-X', 'faulthandler', str(Path(__file__).resolve()),
                   '--output', str(output), '--wheel', str(wheel), '--worker', name]
        child = subprocess.run(command, capture_output=True, text=True, errors='replace',
                               timeout=120, env=dict(os.environ))
        (output / f'{name}.stdout.log').write_text(child.stdout, encoding='utf-8')
        (output / f'{name}.stderr.log').write_text(child.stderr, encoding='utf-8')
        result = output / f'{name}.result.json'
        row = json.loads(result.read_text()) if result.exists() else {'status': 'failed', 'error': 'Child exited without result'}
        row.update(process_exit=child.returncode, command=command,
                   stdout_sha256=sha256(output / f'{name}.stdout.log'),
                   stderr_sha256=sha256(output / f'{name}.stderr.log'))
        manifest['cases'][name] = row
        write_json(output / 'manifest.json', manifest)
        print('Installed Glue', name, row['status'], 'exit', child.returncode, flush=True)
    manifest['status'] = 'passed' if all(row['status'] == 'passed' and row['process_exit'] == 0
                                        for row in manifest['cases'].values()) else 'failed'
    write_json(output / 'manifest.json', manifest)
    return int(manifest['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
