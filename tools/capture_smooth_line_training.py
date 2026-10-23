"""Capture the complete frozen training selection using installed original GL."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

if not sys.flags.isolated or not sys.flags.dont_write_bytecode or sys.flags.optimize != 0:
    raise RuntimeError('Training capture requires -I -B with optimization disabled')

import numpy as np

_tools_directory = str(Path(__file__).resolve().parent)
sys.path.append(_tools_directory)
from line_endpoint_process_identity import observe_process_identity
from smooth_line_mechanism import training_contract, training_probes
from smooth_line_training_provider import TrainingSink, WindowsGLTrainingBackend, capture_one, repeat_indices
from upstream_qt_lifecycle import upstream_qt_teardown
from smooth_line_corner_training import (corner_contract, corner_probes, corner_repeat_indices,
                                        CornerTrainingBackend, CornerTrainingSink, capture_corner_one)
from smooth_line_setup_training import (setup_contract, setup_probes, setup_repeat_indices,
                                       SetupTrainingBackend, SetupTrainingSink, capture_setup_one)
from smooth_line_viewport_training import (viewport_contract, viewport_probes, viewport_repeat_indices,
                                          ViewportTrainingBackend, ViewportTrainingSink, capture_viewport_one)
from smooth_line_window_training import (window_contract, window_probes, window_repeat_indices,
                                        WindowTrainingBackend, WindowTrainingSink, capture_window_one)
sys.path.remove(_tools_directory)

SNAPSHOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--authoring', type=Path, required=True)
    parser.add_argument('--authoring-sha256', required=True)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--admission-sha256', required=True)
    args = parser.parse_args()
    assert sys.flags.isolated == sys.flags.dont_write_bytecode == 1 and sys.version_info[:3] == (3, 12, 8)
    workspace = args.workspace
    assert workspace.is_absolute() and '..' not in workspace.parts
    loader = workspace / 'build/native58-activation-root-1/build_loader.py'
    assert sha(loader) == '8ed806014a374d14c5cb0d362f7986693dbed804ee16782af5d5a519cf75544b'
    r = runpy.run_path(str(loader), run_name='_smooth_training_worker_metadata')['Reader'](workspace)
    author_ref = dict(path=args.authoring.relative_to(workspace).as_posix(), sha256=args.authoring_sha256)
    admission_ref = dict(path=args.admission.relative_to(workspace).as_posix(), sha256=args.admission_sha256)
    author = r.json(author_ref)
    admission = r.json(admission_ref)
    assert admission['status'] == 'ADMITTED_TRAINING_OBSERVATION_SOURCE_ONLY' and admission['process_exit'] == 0
    assert admission['authoring_sha256'] == args.authoring_sha256 and admission['capture_provider_reviewed'] is True
    assert not admission['model_selected'] and not admission['renderer_qualified']
    target_format = author.get('target_format', 'rgba8')
    study_kind = author.get('study_kind', 'original')
    if study_kind == 'window-translation':
        assert target_format == 'rgba8' and author['contract'] == window_contract()
        probes, repeats = window_probes(), window_repeat_indices()
        Backend, Sink, capture = WindowTrainingBackend, WindowTrainingSink, capture_window_one
    elif study_kind == 'viewport-setup':
        assert target_format == 'rgba8' and author['contract'] == viewport_contract()
        probes, repeats = viewport_probes(), viewport_repeat_indices()
        Backend, Sink, capture = ViewportTrainingBackend, ViewportTrainingSink, capture_viewport_one
    elif study_kind == 'setup-along':
        assert target_format == 'rgba8' and author['contract'] == setup_contract()
        probes, repeats = setup_probes(), setup_repeat_indices()
        Backend, Sink, capture = SetupTrainingBackend, SetupTrainingSink, capture_setup_one
    elif study_kind == 'corner-joint':
        assert target_format == 'rgba8' and author['contract'] == corner_contract()
        probes, repeats = corner_probes(), corner_repeat_indices()
        Backend, Sink, capture = CornerTrainingBackend, CornerTrainingSink, capture_corner_one
    elif study_kind == 'original':
        assert author['contract'] == training_contract(target_format)
        probes, repeats = training_probes(), repeat_indices()
        Backend, Sink, capture = WindowsGLTrainingBackend, TrainingSink, capture_one
    else:
        raise ValueError('Unknown scientific training selection')
    assert author['training_only'] is True
    assert workspace / author['snapshot_relative_path'] == SNAPSHOT
    for name, expected in author['sources_sha256'].items():
        r.read(dict(path=(SNAPSHOT / name).relative_to(workspace).as_posix(), sha256=expected))
    for name in ('line_endpoint_process_identity', 'smooth_line_mechanism', 'smooth_line_training_provider',
                 'fixture_gloo', 'upstream_qt_lifecycle', 'smooth_line_corner_training',
                 'smooth_line_setup_training', 'smooth_line_viewport_training', 'smooth_line_training_commands',
                 'smooth_line_window_training'):
        if Path(sys.modules[name].__file__).resolve() != SNAPSHOT / 'tools' / (name + '.py'):
            raise ValueError('Imported provider dependency differs from the pinned snapshot: ' + name)
    draft = json.loads((SNAPSHOT / 'build/smooth-mechanism-authoring-root-1/authoring.json').read_bytes())
    assert draft['contract'] == training_contract()
    assert draft['probes'] == json.loads(json.dumps([asdict(probe) for probe in training_probes()]))
    assert len(probes) == author['contract']['probe_count']
    assert author['repeat_control'] == dict(indices=list(repeats), after_full_training_sweep=True,
                                           training_only=True, separate_artifacts=True)
    for name, expected in author['runtime_versions'].items():
        assert metadata.version(name) == expected, (name, metadata.version(name))
    import vispy
    import PyQt6
    import PyQt6.sip
    for module in (np, PyQt6, PyQt6.sip):
        assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert vispy.__version__ == metadata.version('vispy') == '0.17.0'
    package = Path(vispy.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()) and not list(package.glob('_dawn*'))
    pins = json.loads((SNAPSHOT / 'compat/upstream_manifest.json').read_bytes())['files']
    observed_sources = {}
    for name in ('gloo/program.py', 'gloo/glir.py', 'gloo/wrappers.py', 'gloo/context.py',
                 'gloo/buffer.py', 'gloo/texture.py', 'gloo/framebuffer.py', 'gloo/gl/_gl2.py',
                 'gloo/gl/gl2.py', 'app/backends/_qt.py', 'gloo/util.py'):
        observed_sources[name] = sha(package / name)
        assert observed_sources[name] == pins[name], name
    vispy.use(gl='gl2')
    output = r.path(author['output_relative_path'])
    assert not output.exists(), 'Preserve every prior attempt'
    output.mkdir()
    process_identity = observe_process_identity()
    startup = dict(schema=1, pid=os.getpid(), version=sys.version, executable=sys.executable,
                   process_identity=process_identity, package=str(package), source_hashes=observed_sources,
                   authoring_sha256=args.authoring_sha256, graphics_creation_attempted=False)
    write(output / 'startup.json', startup)
    print(json.dumps(dict(stage='training-worker-startup', pid=os.getpid(), output=str(output))), flush=True)
    result = dict(startup, status='FAILED_PRESERVED', process_exit=1, contract=author['contract'],
                  raw_frames=0, accepted_frames=0, all_training_complete=False, holdouts_accessed=False,
                  model_selected=False, renderer_qualified=False, original13complete=False)
    result['driver_application_overrides'] = dict(observed=False, limitation=
        'NVIDIA application-profile AA/line-gamma overrides are not observable through GL; '
        'these measurements are conditional on the current unobserved application profile.')
    backend, sink, repeat_sink, teardown = None, None, None, {}
    started = time.monotonic()
    try:
        backend = Backend(author['expected_oracle']['renderer'], author['expected_oracle']['version'],
                                          target_format=target_format)
        sink = Sink(output, len(probes), target_format=target_format)
        result['graphics_creation_attempted'] = True
        with upstream_qt_teardown() as teardown:
            with backend, sink:
                result['baseline'] = backend.baseline
                write(output / 'setup-commands.json', dict(commands=backend.setup_commands,
                                                         direct_state_calls=backend.direct_state_calls))
                for index, probe in enumerate(probes):
                    result['last_attempted_probe'] = dict(index=index, identity=probe.identity)
                    capture(backend, sink, probe, index)
                    if (index + 1) % 256 == 0:
                        print(json.dumps(dict(stage='training', accepted=index + 1, total=len(probes))), flush=True)
                repeat_output = output / 'repeat-control'
                repeat_output.mkdir()
                repeat_sink = Sink(repeat_output, len(repeats), repeats, target_format=target_format)
                with repeat_sink:
                    for index in repeats:
                        result['last_attempted_probe'] = dict(index=index, identity=probes[index].identity, repeat=True)
                        capture(backend, repeat_sink, probes[index], index)
        assert sink.raw_frames == sink.accepted_frames == len(probes)
        assert repeat_sink.raw_frames == repeat_sink.accepted_frames == len(repeats)
        assert backend.closed and backend.parser_restored
        assert teardown['closed'] == teardown['disposed'] == 1 and teardown['embedded_preserved'] == 0 and teardown['restored']
        result.update(status='PASS_TRAINING_OBSERVATIONS_PENDING_SAVED_REVIEW', process_exit=0, all_training_complete=True)
    except BaseException:
        result['error'] = traceback.format_exc()
        traceback.print_exc()
    finally:
        if backend is not None:
            result['baseline'] = backend.baseline
            write(output / 'failure-and-cleanup-diagnostics.json', dict(
                baseline=backend.baseline, last_before=backend.last_before, last_after=backend.last_after,
                last_probe_commands=backend.last_commands, pending_or_cleanup_commands=backend.peek_commands(),
                direct_state_calls=backend.direct_state_calls, cleanup_error=backend.cleanup_error))
            write(output / 'shaders.json', backend.shaders)
            result.update(parser_hook_restored=backend.parser_restored, backend_close_called=backend.closed,
                          backend_cleanup_error=backend.cleanup_error)
        if sink is not None:
            result.update(raw_frames=sink.raw_frames, accepted_frames=sink.accepted_frames,
                          artifact_streams_closed=all(stream is None or stream.closed for stream in
                                                      (sink.data, sink.observations, sink.commands)))
        if repeat_sink is not None:
            result.update(repeat_raw_frames=repeat_sink.raw_frames, repeat_accepted_frames=repeat_sink.accepted_frames,
                          repeat_artifact_streams_closed=all(stream is None or stream.closed for stream in
                              (repeat_sink.data, repeat_sink.observations, repeat_sink.commands)))
        result['teardown'] = teardown
        result['elapsed_seconds'] = time.monotonic() - started
        try:
            for name, expected in author['sources_sha256'].items():
                r.read(dict(path=(SNAPSHOT / name).relative_to(workspace).as_posix(), sha256=expected))
            result['frozen_sources_preserved'] = True
        except BaseException:
            result.update(status='FAILED_PRESERVED', process_exit=1, preservation_error=traceback.format_exc())
        result['artifacts'] = {path.name: sha(path) for path in output.iterdir() if path.is_file()}
        if repeat_sink is not None:
            result['repeat_artifacts'] = {path.name: sha(path) for path in repeat_sink.directory.iterdir() if path.is_file()}
        write(output / 'result.json', result)
    print(json.dumps(dict(status=result['status'], process_exit=result['process_exit'], raw_frames=result['raw_frames'],
                          accepted_frames=result['accepted_frames'], result=str(output / 'result.json'),
                          sha256=sha(output / 'result.json'))), flush=True)
    return result['process_exit']


if __name__ == '__main__':
    raise SystemExit(main())
