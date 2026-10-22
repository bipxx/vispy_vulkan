# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh installed-wheel alternating volume runs with retained evidence joins.

Collection completion is distinct from release qualification. The adapter's
unresolved instrumentation gaps remain mandatory release failures.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import copy
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tempfile
import traceback
import uuid
from types import SimpleNamespace

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'tools'
from . import volume_benchmark_adapter as adapter
from .image_wheel_runner import installed_environment, clean_environment, write
from .mesh_layout_process import worker_terminal, process_stamp

bench = adapter.benchmark
require = adapter.require
GLOBAL_HOLD = bench.ROOT / 'build/volume-benchmark-pairs-unresolved-worker.json'


def wait_child(process, timeout):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(getattr(process, 'args', 'worker'), timeout)
        try:
            return process.wait(timeout=min(1, remaining))
        except subprocess.TimeoutExpired:
            pass


def read(path):
    return json.loads(Path(path).read_bytes())


def sources():
    return {**adapter.sources(), 'tools/volume_benchmark_pairs.py': bench.sha256(__file__)}


def leaf(directory, record):
    name = record['file']
    require(isinstance(name, str) and Path(name).name == name and name not in ('.', '..'), 'Artifact must be a leaf file')
    path = (Path(directory) / name).resolve(strict=True)
    require(path.parent == Path(directory).resolve(strict=True), 'Artifact outside worker directory')
    require(bench.sha256(path) == record['sha256'], 'Retained artifact hash differs: ' + name)
    return path


def validate_samples(directory, run, kind):
    """Rebuild receipts, CPU totals, timestamps and latency from raw artifacts."""
    warm, count = run['warmup_frames'], run['measured_frames']
    require(type(warm) is int and warm >= bench.MIN_WARMUP and type(count) is int and count >= bench.MIN_FRAMES,
            'Required frame counts missing')
    issued = read(leaf(directory, run['issued_frames']))
    require(issued == {str(frame): 'warmup' if frame < warm else 'measured' for frame in range(warm + count)},
            'Issued frame identities or phases differ')
    observed = read(leaf(directory, run['observed_samples']))
    require(isinstance(observed, list) and len(observed) == warm + count, 'Incomplete raw completed samples')
    collector = bench.FrameCompletionSamples()
    for frame in range(warm + count):
        collector.begin(frame, 'warmup' if frame < warm else 'measured')
    for sample in observed:
        frame = sample.get('frame_id')
        require(type(frame) is int, 'Malformed observed frame identity')
        require(type(sample.get('completion_latency_ns')) is int and sample['completion_latency_ns'] > 0 and
                type(sample.get('completion_timestamp_ns')) is int and sample['completion_timestamp_ns'] > 0,
                'Malformed completed-frame clock values')
        collector.collect([sample], 'warmup' if frame < warm else 'measured')
    require(collector.count('warmup') == warm and collector.count('measured') == count, 'Incomplete frame retirement')
    samples = read(leaf(directory, run['samples']))
    require(isinstance(samples, list) and [sample.get('frame_id') for sample in samples] == list(range(warm, warm + count)),
            'Complete ordered measured samples required')
    indexed = {sample['frame_id']: sample for sample in observed}
    for sample in samples:
        require(all(sample.get(key) == value for key, value in indexed[sample['frame_id']].items()),
                'Measured sample differs from raw completion receipt')
        cpu = sample['python_cpu']
        require(set(cpu) == set(bench.PythonFrameTelemetry.FIELDS), 'Per-frame CPU attribution missing')
        require(all(type(value) is int and value >= 0 for value in cpu.values()), 'Malformed CPU attribution')
        require(cpu['python_update_calls'] == cpu['python_draw_calls'] == 1, 'Frame lacks exactly one update and draw')
    for key in bench.PythonFrameTelemetry.FIELDS:
        require(sum(sample['python_cpu'][key] for sample in samples) == run['python_counter_delta'][key], 'CPU counter total differs: ' + key)
    require({key: run['python_counters_after'][key] - value for key, value in run['python_counters_before'].items()} == run['python_counter_delta'],
            'Python measured deltas differ from raw snapshots')
    require(all(value == 0 for key, value in run['python_counter_delta'].items() if key.startswith('unattributed_')),
            'Unattributed measured Python work')
    statistics = bench.metrics([sample['completion_latency_ns'] for sample in samples])
    require(set(statistics) == set(run['latency']), 'Latency summary fields differ')
    for key, value in statistics.items():
        reported = run['latency'][key]
        if key == 'stdev_ms':
            # CPython 3.10's statistics.pstdev differs from 3.11+ by one ULP
            # on the retained real original run. This descriptive field is not
            # used by a release threshold. Median/p95/count remain exact.
            require(type(reported) in (int, float) and math.isfinite(reported) and
                    abs(value - reported) <= max(math.ulp(value), math.ulp(reported)),
                    'Latency standard deviation differs beyond one ULP')
        else:
            require(value == reported, 'Latency statistics differ from retained samples: ' + key)
    require(run['gpu_telemetry']['enabled'] is True, 'GPU timestamp collection missing in the admitted cell')
    if kind == 'upstream':
        bench._pacing.validate_completed_samples(observed, range(warm + count), unpaced=True)
        timing = read(leaf(directory, run['observed_opengl_timings']))
        require(len(timing) == warm + count and {row['frame_id'] for row in timing} == set(range(warm + count)), 'Incomplete original GPU timestamps')
        contexts = set()
        for row in timing:
            require(row['status'] == 'success' and row['scope'] == 'upstream_vispy_paint' and
                    row['includes_alpha_tail'] and row['same_scene_context_verified'], 'Original GPU timing scope differs')
            require(all(type(row[key]) is int for key in ('begin_ns', 'end_ns', 'elapsed_ns')) and
                    0 <= row['begin_ns'] <= row['end_ns'] and row['elapsed_ns'] == row['end_ns'] - row['begin_ns'], 'Invalid original GPU interval')
            contexts.add(row['scene_context_identity'])
        require(len(contexts) == 1 and next(iter(contexts)) > 0, 'Original timestamps changed scene context')
        timing_by_id = {row['frame_id']: row for row in timing}
        require(all(sample['opengl_gpu_timing'] == timing_by_id[sample['frame_id']] for sample in samples), 'Original timestamp join differs')
        telemetry = run['opengl_telemetry']
        delta = bench.counter_delta(run['counters_before'], run['counters_after'],
            peaks=telemetry['high_water_marks'], gauges=telemetry['gauges'])
        run['_release_upstream_completed_samples'] = observed
    else:
        timing = read(leaf(directory, run['observed_gpu_timings']))
        gpu = bench.GPUFrameSamples()
        for frame in range(warm + count): gpu.begin(frame)
        gpu.collect(timing)
        require(len(gpu.results) == warm + count, 'Incomplete native GPU maps')
        joined = copy.deepcopy(observed)
        gpu.join(joined)
        scope = SimpleNamespace(telemetry=run['native_telemetry'], gpu_metadata=run['gpu_telemetry'], boundary={})
        require(bench.CandidateCompletions.verify_scope(scope, joined), 'Native whole-paint ownership unproven')
        require(scope.boundary['verified_paint_frames'] == warm + count, 'Native paint frame count differs')
        require(all(sample['gpu_timing'] == gpu.results[sample['frame_id']] for sample in samples), 'Native timestamp join differs')
        bench.validate_allocation_window_pair(run['measured_allocation_window'], warm, count)
        delta = bench.native_counter_summary(run['counters_before'], run['counters_after'],
            telemetry=run['native_telemetry'], backend=run['renderer']['backend'])['counter_delta']
    require(delta == run['counter_delta'], 'Measured counter deltas differ from raw snapshots')
    return dict(warm_frames=warm, measured_frames=count, raw_completion_count=len(observed),
                gpu_map_count=len(timing), statistics_recomputed=True, recomputed_latency=statistics)


def verify_run(directory, kind, name, index, admission, process, *, warmup, frames):
    """Only actual waited/nonce-bound workers can join the paired data set."""
    directory = Path(directory)
    worker, start = read(directory / 'worker.json'), read(directory / 'worker-start.json')
    require(process['child_waited'] and process['actual_worker_terminal']['terminal'] and not process.get('timed_out'), 'Actual worker wait missing')
    require(process['process_exit'] == worker['process_exit'] == 0 and worker['status'] == 'measured', 'Worker did not measure successfully')
    require(worker['launch_id'] == start['launch_id'] == process['launch_id'], 'Worker launch identity differs')
    require(bench.sha256(directory / 'worker.json') == process['worker_sha256'], 'Worker receipt hash differs')
    require(all(worker[key] == start[key] for key in ('pid', 'process_stamp', 'adapter_sources_sha256')), 'Worker start/finish process differs')
    stamp = worker['process_stamp']
    require(stamp['pid'] == worker['pid'] and (worker['pid'] == process['pid'] or stamp['parent_pid'] == process['pid']), 'Worker launcher edge differs')
    require(worker['adapter_sources_sha256'] == adapter.sources(), 'Worker source identity differs')
    run_path = leaf(directory, dict(file='run.json', sha256=worker['run_sha256']))
    run = read(run_path)
    require(run['status'] == 'measured' and run['run_index'] == index, 'Measured run identity differs')
    require(run['warmup_frames'] == warmup and run['measured_frames'] == frames and run['vsync'] is False, 'Actual timing settings differ')
    require(bench.value_sha256(run['workload']) == bench.value_sha256(asdict(bench.CATALOG[name])), 'Actual workload differs')
    sample_check = validate_samples(directory, run, kind)
    check = adapter.measured_work_gate(run, kind, admission=admission, expected=adapter.expected_geometry(name),
                                      update=bench.CATALOG[name].update != 'resident')
    require(check['status'] == 'passed', 'Saved measured work did not verify: ' + str(check))
    captures = run['quality_captures']
    require([item['probe_frame'] for item in captures] == [None, 7, 73], 'Required quality captures missing')
    for item in captures: leaf(directory, item)
    return run, dict(status='verified', worker_sha256=process['worker_sha256'], run_sha256=worker['run_sha256'],
                     samples=sample_check, measured_work=check)


def compare_pair(name, original_directory, candidate_directory, original, candidate):
    import numpy as np
    images = {'upstream': [], 'candidate': []}
    comparisons = []
    for kind, directory, run in (('upstream', original_directory, original), ('candidate', candidate_directory, candidate)):
        for item in run['quality_captures']:
            image = np.load(leaf(directory, item), allow_pickle=False)
            adapter.suite.assert_nonblank(name, image)
            images[kind].append(image)
    for probe, reference, image in zip((None, 7, 73), images['upstream'], images['candidate']):
        result = bench.compare_quality(reference, image)
        require(result['status'] == 'passed', 'Paired whole-frame RGBA comparison failed')
        comparisons.append(dict(probe_frame=probe, **result))
    changes = []
    for position in (1, 2):
        result = adapter.suite.change_discrimination(images['upstream'][0], images['upstream'][position],
            images['candidate'][0], images['candidate'][position])
        require(result['passed'], 'Paired quality update did not discriminate changed pixels')
        changes.append(result)
    return dict(status='passed', comparisons=comparisons, changed_frame_checks=changes)


def launch_worker(arguments, *, directory, environment, environment_evidence, timeout, launch_id):
    """Wait the launched process AND its actual worker before removing owned cwd."""
    directory = Path(directory)
    require(not directory.exists(), 'Fresh worker directory required')
    require(not GLOBAL_HOLD.exists(), 'Unresolved actual worker blocks every controller invocation; explicit resolution required')
    require(not (Path(environment_evidence) / 'worker-termination-unverified.json').exists(), 'Previous actual worker termination unresolved')
    directory.parent.mkdir(parents=True, exist_ok=True)
    owner = Path(tempfile.mkdtemp(prefix='vispy-volume-pair-worker-')).resolve()
    record = dict(arguments=[str(value) for value in arguments], launch_id=launch_id, child_waited=False,
                  timed_out=False, cwd=str(owner), pid=None, process_exit=None)
    process = None
    try:
        with directory.with_suffix('.log').open('xb') as stream:
            process = subprocess.Popen(record['arguments'], cwd=owner, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            record['pid'] = process.pid
            write(directory.with_suffix('.launch.json'), record)
            try:
                record['process_exit'] = wait_child(process, timeout)
                record['child_waited'] = True
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                process.terminate()
                record['process_exit'] = process.wait(timeout=10)
                record['child_waited'] = True
    except BaseException as error:
        record['error'] = traceback.format_exc()
        record['interrupted'] = isinstance(error, KeyboardInterrupt)
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                record['process_exit'] = process.wait(timeout=10)
                record['child_waited'] = True
            except BaseException:
                record['termination_error'] = traceback.format_exc()
    finally:
        terminal = process is None
        try:
            if process is not None:
                require(record['child_waited'], 'Launched process still unverified')
                report = directory / ('worker.json' if (directory / 'worker.json').exists() else 'worker-start.json')
                worker = read(report)
                require(worker['launch_id'] == launch_id, 'Actual worker launch nonce differs')
                record['actual_worker_terminal'] = worker_terminal(worker, process.pid)
                terminal = record['actual_worker_terminal']['terminal']
                if report.name == 'worker.json': record['worker_sha256'] = bench.sha256(report)
        except BaseException:
            terminal = False
            record['worker_observation_error'] = traceback.format_exc()
        if terminal:
            require(owner.parent == Path(tempfile.gettempdir()).resolve() and owner.name.startswith('vispy-volume-pair-worker-'), 'Owned cwd boundary differs')
            shutil.rmtree(owner)
        else:
            GLOBAL_HOLD.parent.mkdir(parents=True, exist_ok=True)
            write(GLOBAL_HOLD, dict(schema=1, process=record, environment_evidence=str(environment_evidence),
                resolution_required='Retain this hold until actual creation-bound process termination is verified and an explicit operator resolution is recorded'))
            write(Path(environment_evidence) / 'worker-termination-unverified.json', record)
        record['cwd_removed'] = not owner.exists()
        write(directory.with_suffix('.process.json'), record)
    if record.get('interrupted'):
        raise KeyboardInterrupt
    require(terminal and record['child_waited'] and not record.get('error') and not record['timed_out'], 'Worker termination or deadline failed; retained evidence')
    return record


def preflight(options):
    require(not sys.flags.optimize, 'Optimized controller forbidden')
    require(not GLOBAL_HOLD.exists(), 'Unresolved actual worker blocks every controller invocation; explicit resolution required')
    require(options.warmup >= bench.MIN_WARMUP and options.frames >= bench.MIN_FRAMES, 'Minimum 100 warm/1000 measured frames required')
    require(options.repetitions >= bench.MIN_REPETITIONS and 1 <= options.queue_depth <= 3, 'Five pairs and queue depth 1..3 required')
    require(all(math.isfinite(value) and value > 0 for value in (options.timeout, options.worker_timeout)), 'Finite positive deadlines required')
    require(options.workloads and len(set(options.workloads)) == len(options.workloads) and set(options.workloads) <= set(adapter.suite.CASES), 'Unique registered volume workloads required')
    require(not options.output.exists(), 'Fresh controller output required')
    plan = read(options.quality_plan)
    admissions = {}
    for name in options.workloads:
        entry = plan[name]
        require(set(entry) == {'scientific_admission', 'exact'} and entry['exact'] is False, 'Unchanged whole-frame quality plan required')
        relative = entry['scientific_admission']
        require(Path(relative).name == relative, 'Admission must be a plan sibling')
        path = options.quality_plan.resolve().parent / relative
        admissions[name] = (path, adapter.load_admission(path, name))
    hardware = read(options.hardware)
    require(hardware['schema'] == 1 and all(hardware.get(key) for key in ('adapter_id', 'driver', 'presentation_environment')), 'Designated hardware metadata required')
    for kind, fields in (('upstream', ('vendor', 'renderer', 'version')), ('candidate', ('vendor_id', 'device_id', 'driver', 'backend'))):
        require(all(key in hardware['renderers'][kind] for key in fields), 'Designated renderer identity incomplete')
    for kind, wheel in (('upstream', options.reference_wheel), ('candidate', options.candidate_wheel)):
        digest = bench.sha256(wheel)
        require(all(record['artifacts'][kind]['wheel_sha256'] == digest for _, record in admissions.values()), 'Selected wheel differs from scientific admission')
    return admissions, hardware


def collect(options):
    admissions, hardware = preflight(options)
    held = sources()
    options.output.mkdir(parents=True)
    request = dict(schema=1, workloads=options.workloads, parameters={name: asdict(bench.CATALOG[name]) for name in options.workloads},
        warmup=options.warmup, frames=options.frames, repetitions=options.repetitions, queue_depth=options.queue_depth,
        schedule=bench.alternating_schedule(options.repetitions), sources_sha256=held,
        quality_plan_sha256=bench.sha256(options.quality_plan), hardware_sha256=bench.sha256(options.hardware),
        admission_sha256={name: bench.sha256(path) for name, (path, _) in admissions.items()},
        hardware=hardware, quality_plan=read(options.quality_plan),
        wheel_sha256={kind: bench.sha256(wheel) for kind, wheel in (('upstream', options.reference_wheel), ('candidate', options.candidate_wheel))},
        scope='Selected registered volume workloads only; full66 and all platform cells are not implied')
    executables = {str(Path(path).resolve(strict=True)): bench.sha256(path) for path in
                   (sys.executable, getattr(sys, '_base_executable', sys.executable), options.python)}
    request['controller_interpreter'] = dict(version=sys.version, executable=sys.executable,
        base_executable=getattr(sys, '_base_executable', sys.executable))
    request['python_executables_sha256'] = executables
    def verify_inputs():
        for path, digest in executables.items():
            require(bench.sha256(path) == digest, 'Controller/base Python executable changed')
        require(bench.sha256(options.quality_plan) == request['quality_plan_sha256'] and read(options.quality_plan) == request['quality_plan'], 'Quality plan changed')
        require(bench.sha256(options.hardware) == request['hardware_sha256'] and read(options.hardware) == hardware, 'Designated hardware changed')
        for name, (path, record) in admissions.items():
            require(bench.sha256(path) == request['admission_sha256'][name] and read(path) == record, 'Scientific admission changed')
        for kind, wheel in (('upstream', options.reference_wheel), ('candidate', options.candidate_wheel)):
            require(bench.sha256(wheel) == request['wheel_sha256'][kind], 'Selected wheel changed')
    verify_inputs()
    write(options.output / 'request.json', request)
    manifest = dict(schema=1, status='incomplete', collection_status='partial', workloads={}, process_stamp=process_stamp(),
                    request_sha256=bench.sha256(options.output / 'request.json'), full_release_qualified=False)
    envdirs = {kind: options.output / ('environment-' + kind) for kind in ('upstream', 'candidate')}
    cache = None
    try:
        runtime = options.output / 'runtime-requirements.txt'
        runtime.write_text(adapter.suite.runtime_requirements(), encoding='utf-8')
        manifest['runtime_requirements_sha256'] = bench.sha256(runtime)
        cache = Path(tempfile.mkdtemp(prefix='vispy-volume-pairs-cache-')).resolve()
        manifest['owned_cache_root'] = str(cache)
        bench.write_json(options.output / 'manifest.json', manifest)
        environment = clean_environment(os.environ)
        for key in tuple(environment):
            if key.startswith('VISPY_'): environment.pop(key)
        environment.update(VISPY_TEST_PYTHON=str(options.python), VISPY_TEST_RUNTIME_REQUIREMENTS=str(runtime.resolve()),
            VISPY_IMAGE_REPOSITORY=str(bench.ROOT), UV_CACHE_DIR=str(cache), QT_API='pyqt6', QT_SCALE_FACTOR='1')
        with ExitStack() as stack:
            installed = {kind: stack.enter_context(installed_environment(wheel, envdirs[kind], environment=environment))
                         for kind, wheel in (('upstream', options.reference_wheel), ('candidate', options.candidate_wheel))}
            for name in options.workloads:
                runs, directories, receipts = {'upstream': [], 'candidate': []}, {'upstream': [], 'candidate': []}, []
                for index, kind in bench.alternating_schedule(options.repetitions):
                    require(sources() == held, 'Controller/worker sources changed')
                    verify_inputs()
                    path, admission = admissions[name]
                    python, env = installed[kind]
                    nonce = uuid.uuid4().hex
                    directory = options.output / name / f'{index:02}-{kind}'
                    wheel = options.reference_wheel if kind == 'upstream' else options.candidate_wheel
                    argv = [python, '-I', '-B', bench.ROOT / 'tools/volume_benchmark_adapter.py', '--worker', kind,
                        '--launch-id', nonce, '--workload', name, '--run-index', str(index), '--wheel', wheel,
                        '--admission', path, '--output', directory.resolve(), '--warmup', str(options.warmup), '--frames', str(options.frames),
                        '--queue-depth', str(options.queue_depth), '--timeout', str(options.timeout)]
                    process = launch_worker(argv, directory=directory, environment=env, environment_evidence=envdirs[kind],
                                            timeout=options.worker_timeout, launch_id=nonce)
                    run, verification = verify_run(directory, kind, name, index, admission, process, warmup=options.warmup, frames=options.frames)
                    verify_inputs()
                    write(directory.with_suffix('.validation.json'), verification)
                    runs[kind].append(run); directories[kind].append(directory)
                    receipts.append(dict(index=index, role=kind, run_sha256=verification['run_sha256'],
                        evidence={suffix: dict(file=directory.with_suffix(suffix).relative_to(options.output).as_posix(),
                            sha256=bench.sha256(directory.with_suffix(suffix))) for suffix in ('.launch.json', '.process.json', '.validation.json', '.log')}))
                    print(name, index, kind, 'verified', flush=True)
                quality = [compare_pair(name, ref, cand, original, candidate) for ref, cand, original, candidate in
                           zip(directories['upstream'], directories['candidate'], runs['upstream'], runs['candidate'])]
                hardware_check = bench.validate_hardware(hardware, runs)
                path, admission = admissions[name]
                scientific = bench.validate_admission(dict(scientific_admission=path.name), bench.CATALOG[name],
                    runs['upstream'] + runs['candidate'], path.parent)
                gate = adapter.release_gate(runs['upstream'], runs['candidate'], admission=admission,
                    quality_passed=scientific['status'] == 'passed' and len(quality) == options.repetitions,
                    same_hardware=hardware_check['status'] == 'passed')
                manifest['workloads'][name] = dict(runs=receipts, quality=quality, hardware_equivalence=hardware_check,
                    scientific_admission=scientific, gate=gate)
                bench.write_json(options.output / 'manifest.json', manifest)
        require(sources() == held, 'Sources changed during collection')
        verify_inputs()
        manifest['collection_status'] = 'complete'
        manifest['status'] = 'passed' if all(row['gate']['status'] == 'passed' for row in manifest['workloads'].values()) else 'unqualified'
    except BaseException as error:
        manifest.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=traceback.format_exc())
    finally:
        unresolved = any((path / 'worker-termination-unverified.json').exists() for path in envdirs.values())
        if cache is not None and not unresolved:
            try:
                require(cache.parent == Path(tempfile.gettempdir()).resolve() and cache.name.startswith('vispy-volume-pairs-cache-'), 'Owned cache boundary differs')
                shutil.rmtree(cache)
            except Exception:
                manifest.update(status='failed', cache_cleanup_error=traceback.format_exc())
        manifest.update(owned_cache_removed=cache is None or not cache.exists(), cache_preserved_for_unverified_worker=unresolved)
        bench.write_json(options.output / 'manifest.json', manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-wheel', required=True, type=Path)
    parser.add_argument('--candidate-wheel', required=True, type=Path)
    parser.add_argument('--quality-plan', required=True, type=Path)
    parser.add_argument('--hardware', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--workloads', nargs='+', choices=adapter.suite.CASES)
    selection.add_argument('--all-workloads', action='store_true')
    parser.add_argument('--warmup', type=int, default=bench.MIN_WARMUP)
    parser.add_argument('--frames', type=int, default=bench.MIN_FRAMES)
    parser.add_argument('--repetitions', type=int, default=bench.MIN_REPETITIONS)
    parser.add_argument('--queue-depth', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--worker-timeout', type=float, default=3600)
    options = parser.parse_args(argv)
    if options.all_workloads: options.workloads = list(adapter.suite.CASES)
    for key in ('output', 'reference_wheel', 'candidate_wheel', 'quality_plan', 'hardware', 'python'):
        setattr(options, key, getattr(options, key).resolve())
    result = collect(options)
    print(json.dumps(dict(status=result['status'], collection_status=result['collection_status'], output=str(options.output))))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
