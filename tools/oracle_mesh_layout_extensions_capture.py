"""Freeze mesh/layout criteria, then capture one installed-renderer case per process."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import traceback

import numpy as np

from fixture_mesh_layout_extensions import CASES, assert_landmarks, case_contract, compare, render

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('tools/fixture_mesh_layout_extensions.py', 'tools/fixture_gloo.py',
           'tools/oracle_mesh_layout_extensions_capture.py', 'tests/contract/test_mesh_layout_authoring.py',
           'compat/upstream_manifest.json', '.github/workflows/upstream-vispy-0.17.0.json',
           'pyproject.toml', 'uv.lock', 'LICENSE', 'LICENSE-BSD',
           'build/native58-wheel-archive-review-cp312-fixed-root-1/result.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def freeze_authoring(output):
    assert not output.exists(), 'Preserve every prior authoring attempt'
    output.mkdir(parents=True)
    candidate_audit = ROOT / SOURCES[-1]
    assert sha(candidate_audit) == '2bd19a2c785a058488b860312699c75d497f6b88f072dcefb66159ec6975cbeb'
    payload = dict(schema=1, scope='13 public mesh/filter/layout/text cases; no host or platform admission',
                   candidate_pixels_seen=False, GPU_invoked=False,
                   cases={name: case_contract(name) for name in CASES},
                   sources_sha256={name: sha(ROOT / name) for name in SOURCES},
                   runtime_versions={'numpy': '2.5.3', 'PyQt6': '6.11.0', 'PyQt6-Qt6': '6.11.2',
                                     'PyQt6-sip': '13.13.0', 'freetype-py': '2.5.1',
                                     'hsluv': '5.0.4', 'kiwisolver': '1.5.1', 'packaging': '26.3'})
    for name in SOURCES:
        target = output / 'snapshot' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((ROOT / name).read_bytes())
    write(output / 'authoring.json', payload)
    print(json.dumps(dict(authoring=str(output / 'authoring.json'), sha256=sha(output / 'authoring.json'),
                          cases=len(CASES), GPU_invoked=False)))


def capture(args):
    assert sys.flags.isolated == sys.flags.dont_write_bytecode == 1, 'Isolated installed consumer required'
    assert sha(args.authoring) == args.authoring_sha256
    authoring = json.loads(args.authoring.read_bytes())
    assert authoring['candidate_pixels_seen'] is False and authoring['GPU_invoked'] is False
    assert authoring['cases'] == {name: case_contract(name) for name in CASES}
    for name, expected in authoring['sources_sha256'].items():
        assert sha(ROOT / name) == expected, name
    for name, version in authoring['runtime_versions'].items():
        assert metadata.version(name) == version, (name, metadata.version(name), version)
    import vispy
    expected_version = '0.17.0' if args.kind == 'upstream' else '0.17.0+vulkan.1'
    assert vispy.__version__ == metadata.version('vispy') == expected_version
    package = Path(vispy.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()), 'Installed external package origin'
    source_hashes = {}
    if args.kind == 'upstream':
        assert not list(package.glob('_dawn*')), 'Fork native module in upstream environment'
        manifest = json.loads((ROOT / 'compat/upstream_manifest.json').read_bytes())
        for name in ('gloo/program.py', 'gloo/glir.py', 'gloo/texture.py',
                     'visuals/mesh.py', 'visuals/text/text.py', 'scene/canvas.py'):
            source_hashes[name] = sha(package / name)
            assert source_hashes[name] == manifest['files'][name], name
        vispy.use(gl='gl2')
    else:
        audit = json.loads((ROOT / SOURCES[-1]).read_bytes())
        assert audit['status'] == 'CLEAR_WITH_SCOPE' and audit['process_exit'] == 0
        for name, artifact in audit['native_build_artifacts'].items():
            installed = package / Path(name).relative_to('vispy')
            assert sha(installed) == artifact['sha256'], name
            source_hashes[name] = artifact['sha256']
    assert not args.output.exists(), 'Fresh worker output required'
    args.output.mkdir(parents=True)
    result = dict(schema=1, status='FAILED_PRESERVED', process_exit=1, kind=args.kind, case=args.case,
                  pid=os.getpid(), python=sys.version, executable=sys.executable, package=str(package),
                  versions={name: metadata.version(name) for name in authoring['runtime_versions']},
                  source_hashes=source_hashes, authoring_sha256=args.authoring_sha256,
                  full_platform_or_scientific_admission=False)
    try:
        image, commands, shaders, params, extras = render(args.case, 'pyqt6' if args.kind == 'upstream' else 'dawn_headless')
        np.save(args.output / 'rgba.npy', image, allow_pickle=False)
        write(args.output / 'commands.json', commands)
        write(args.output / 'shaders.json', shaders)
        write(args.output / 'parameters.json', params)
        for name, array in extras.items():
            np.save(args.output / (name + '.npy'), array, allow_pickle=False)
        result['parameters'] = params
        assert commands and shaders, 'Actual GLIR and expanded shaders required'
        assert_landmarks(args.case, image)
        if args.kind == 'candidate':
            from vispy import _dawn
            result['device'] = dict(_dawn.device_info())
            assert result['device']['ok'] and result['device']['backend'] == 'Vulkan' and not result['device']['software']
            assert args.reference is not None and args.reference_sha256 is not None
            assert sha(args.reference / 'result.json') == args.reference_sha256
            reference = json.loads((args.reference / 'result.json').read_bytes())
            assert reference['kind'] == 'upstream' and reference['status'] == 'PASS_UPSTREAM_CASE'
            assert reference['case'] == args.case and reference['authoring_sha256'] == args.authoring_sha256
            for name, digest in reference['artifacts'].items():
                assert sha(args.reference / name) == digest
            compare(args.case, image, np.load(args.reference / 'rgba.npy', allow_pickle=False))
            for key in ('view_rectangles', 'cpu_atlases', 'glyphs', 'font_sha256'):
                if key in reference['parameters']:
                    assert params[key] == reference['parameters'][key], key
            for name in extras:
                np.testing.assert_array_equal(extras[name], np.load(args.reference / (name + '.npy'), allow_pickle=False))
        result.update(status='PASS_UPSTREAM_CASE' if args.kind == 'upstream' else 'PASS_MATCHED_CANDIDATE_CASE', process_exit=0)
    except BaseException:
        result['error'] = traceback.format_exc()
        traceback.print_exc()
    finally:
        if args.kind == 'candidate':
            try:
                from vispy import _dawn
                _dawn.shutdown()
                probe = dict(_dawn.probe())
                fields = ('pending_tickets', 'live_buffer_bytes', 'live_cpu_buffer_bytes', 'live_texture_bytes',
                          'deferred_frames', 'queued_frames', 'vk_memory_live_allocations', 'vk_memory_live_bytes')
                result['shutdown_zeros'] = {name: probe[name] for name in fields}
                assert all(value == 0 for value in result['shutdown_zeros'].values()), result['shutdown_zeros']
            except BaseException:
                result.update(status='FAILED_PRESERVED', process_exit=1, cleanup_error=traceback.format_exc())
        result['artifacts'] = {path.name: sha(path) for path in args.output.iterdir() if path.is_file()}
        write(args.output / 'result.json', result)
    print(json.dumps(dict(status=result['status'], case=args.case, process_exit=result['process_exit'],
                          result=str(args.output / 'result.json'), sha256=sha(args.output / 'result.json'))))
    return result['process_exit']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kind', choices=('upstream', 'candidate'))
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--authoring', type=Path)
    parser.add_argument('--authoring-sha256')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-sha256')
    args = parser.parse_args()
    if args.freeze:
        freeze_authoring(args.output)
        return 0
    assert args.kind and args.case and args.authoring and args.authoring_sha256
    return capture(args)


if __name__ == '__main__':
    raise SystemExit(main())
