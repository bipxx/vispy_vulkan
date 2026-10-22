# SPDX-License-Identifier: AGPL-3.0-only
"""Versioned volume timing worker around the unchanged benchmark implementation.

This module supplies artifact identity and an exact original-cube allowance.
It does not qualify a worker alone: paired scientific, hardware, presentation
and full release gates must also pass. No renderer command or time is removed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
import traceback

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'tools'

from . import benchmark_frames as benchmark
from . import large_volume_wheel_suite as suite
from . import volume_scientific_admission as science
from . import volume_benchmark_geometry as geometry
from .color_volume_wheel_suite import verify_package
from .mesh_layout_process import process_stamp

OVERHEAD_GAP = 'per-role geometry observation overhead effect on paired timing remains unbounded'


SOURCES = ('tools/volume_benchmark_adapter.py', 'tools/volume_benchmark_geometry.py',
           'tools/volume_scientific_admission.py', *suite.SOURCES)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sources():
    return {name: benchmark.sha256(benchmark.ROOT / name) for name in SOURCES}


def load_admission(path, name):
    path = Path(path).resolve(strict=True)
    record = json.loads(path.read_bytes())
    require(name in suite.CASES and record['workload'] == name, 'Registered volume admission required')
    # The frozen scientific gate verifies every retained evidence file as well
    # as parameters and data; the identity-only rows here are not timing runs.
    result = benchmark.validate_admission(dict(scientific_admission=path.name),
        benchmark.CATALOG[name], [dict(data_sha256=record['benchmark_data_sha256'])], path.parent)
    require(result['status'] == 'passed', 'Scientific admission evidence did not verify')
    qualification = json.loads((path.parent / 'qualification.json').read_bytes())
    require(qualification['status'] == 'PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS', 'Incomplete scientific admission set')
    require(set(qualification['cases']) == set(suite.CASES), 'Scientific admission set lacks workloads')
    require(qualification['cases'][name]['admission_sha256'] == benchmark.sha256(path), 'Admission receipt differs')
    return record


def expected_geometry(name):
    reference = suite.load_reference(science.ORIGINAL_ROOT, science.LARGE_ORIGINAL_SHA, name)
    return geometry.reference_geometry(json.loads((reference / 'initial.json').read_bytes()))


def measured_work_gate(run, kind, *, admission, expected, update=False):
    """Revalidate saved runs; never trust a worker's previous gate verdict."""
    identity = science.measurement_identity(admission, run)
    if identity['status'] != 'passed':
        return identity
    if run.get('provenance', {}).get('kind') != kind:
        return dict(status='unproven', reasons=['Actual renderer role differs'])
    if run['provenance'].get('adapter_sources_sha256') != sources():
        return dict(status='unproven', reasons=['Timing adapter source identity differs'])
    if benchmark.value_sha256(run.get('workload')) != admission['workload_sha256']:
        return dict(status='unproven', reasons=['Actual measured workload differs'])
    # Scientific controls are bounded to this actual device/driver cell.
    try:
        if kind == 'candidate':
            science.device_cell(run['renderer'])
        else:
            require(run['renderer'] == dict(vendor='NVIDIA Corporation',
                renderer='NVIDIA GeForce RTX 4090/PCIe/SSE2', version='4.6.0 NVIDIA 610.88'),
                'Actual original renderer differs from the scientific cell')
    except (AssertionError, ValueError, KeyError, TypeError) as error:
        return dict(status='unproven', reasons=['Scientific device cell differs: ' + str(error)])
    return geometry.measured_work_gate(run, kind, update=update, expected=expected)


def release_gate(reference_runs, candidate_runs, *, admission, quality_passed, same_hardware):
    """Retain every frozen release threshold and add actual artifact validation."""
    expected = expected_geometry(admission['workload'])
    original = benchmark.measured_work_gate
    def gate(run, kind, *, update=False):
        return measured_work_gate(run, kind, admission=admission, expected=expected, update=update)
    benchmark.measured_work_gate = gate
    try:
        result = benchmark.release_gate(reference_runs, candidate_runs,
            update=benchmark.CATALOG[admission['workload']].update != 'resident',
            quality_passed=quality_passed, same_hardware=same_hardware)
    finally:
        benchmark.measured_work_gate = original
    if result['status'] == 'passed':
        return dict(status='unproven', reasons=[OVERHEAD_GAP], observed_release_metrics=result)
    return result


class ParserObservation:
    def __init__(self, canvas, ledger):
        self.canvas, self.ledger, self.telemetry = canvas, ledger, None
        self.owner = canvas.context.shared.parser
        self.original = self.owner.parse
        self.had_own = 'parse' in self.owner.__dict__
        self.old_own = self.owner.__dict__.get('parse')
        self.observer_cpu_ns = {}
        def observe(batch):
            current = self.telemetry
            frame = current.geometry_frame if current is not None and current.current is not None else None
            # Observe the same batch, then execute it without rewriting/filtering.
            # All observation time remains inside the measured parse/draw scope.
            started = time.perf_counter_ns()
            self.ledger.observe(batch, frame)
            self.observer_cpu_ns[frame] = self.observer_cpu_ns.get(frame, 0) + time.perf_counter_ns() - started
            return self.original(batch)
        self.wrapper = observe
        self.owner.parse = observe

    def close(self):
        require(self.owner.parse is self.wrapper, 'Parser observation was replaced or not restored by telemetry')
        if self.had_own:
            self.owner.parse = self.old_own
        else:
            del self.owner.parse


@contextmanager
def worker_adapter(options, wheel, admission):
    """Install only benchmark observation hooks for one isolated worker process."""
    require(not sys.flags.optimize, 'Optimized benchmark workers are forbidden')
    require(options.workload in suite.CASES, 'Only registered volume workloads supported')
    expected = expected_geometry(options.workload)
    held = sources()
    original_provenance = benchmark.package_provenance
    original_scene = benchmark.build_scene
    original_telemetry = benchmark.PythonFrameTelemetry
    original_gate = benchmark.measured_work_gate
    ledger = geometry.GeometryObservation(expected, frame_limit=options.warmup + options.frames)
    observed = []

    def provenance(kind):
        actual = original_provenance(kind)
        require(benchmark.sha256(wheel) == admission['artifacts'][kind]['wheel_sha256'], 'Selected wheel differs from scientific artifact')
        payloads = verify_package(wheel, Path(actual['package']), kind)
        package = {name: digest for name, digest in payloads.items() if name.startswith('vispy/')}
        require(package == admission['artifacts'][kind]['installed_package_sha256'], 'Actual installed scientific artifact differs')
        actual.update(wheel_sha256=benchmark.sha256(wheel), installed_package_sha256=package,
                      installed_wheel_payloads_sha256=payloads, adapter_sources_sha256=held)
        require(actual['python'] == '3.12.8' and actual['versions']['numpy'] == '2.4.6',
                'Actual Python/NumPy differs from scientific cell')
        return actual

    def build_scene(workload, kind, vsync, *, on_canvas=None):
        require(on_canvas is None, 'Nested scene instrumentation is not supported')
        def capture(canvas):
            observed.append(ParserObservation(canvas, ledger))
        try:
            canvas, update, source_hash = original_scene(workload, kind, vsync, on_canvas=capture)
            from vispy import scene
            views = [node for node in canvas.central_widget.children if isinstance(node, scene.widgets.ViewBox)]
            require(len(views) == 1, 'Exactly one volume view required')
            volumes = [node for node in views[0].scene.children if isinstance(node, scene.visuals.Volume)]
            require(len(volumes) == 1, 'Exactly one volume visual required')
            ledger.bind([volumes[0]._vertices.id, volumes[0]._index_buffer.id])
            return canvas, update, source_hash
        except BaseException:
            if observed:
                observed[0].canvas.close()
            raise

    class Telemetry(original_telemetry):
        def __init__(self, canvas, **kwargs):
            super().__init__(canvas, **kwargs)
            require(len(observed) == 1, 'Missing early parser observation')
            self.geometry_frame = None
            self.geometry_snapshots = 0
            observed[0].telemetry = self
            ledger.active = True

        def begin(self, frame_id):
            super().begin(frame_id)
            self.geometry_frame = frame_id

        def snapshot(self):
            result = super().snapshot()
            require(self.current is None, 'Measured boundary still owns an unfinished paint')
            if self.geometry_snapshots == 0:
                require(set(self.frames) == set(range(options.warmup)), 'Warm frame range incomplete at measured boundary')
                ledger.begin_window(options.warmup, options.frames)
            elif self.geometry_snapshots == 1:
                require(set(self.frames) == set(range(options.warmup + options.frames)), 'Measured frame range incomplete at boundary')
                ledger.end_window()
            else:
                raise ValueError('Unexpected Python counter snapshot boundary')
            self.geometry_snapshots += 1
            return result

    def work_gate(run, kind, *, update=False):
        run['geometry_observer_cpu_ns'] = {('cold' if key is None else str(key)): value
            for key, value in observed[0].observer_cpu_ns.items()}
        if kind == 'upstream':
            run['original_geometry'] = ledger.snapshot()
        return measured_work_gate(run, kind, admission=admission, expected=expected, update=update)

    benchmark.package_provenance = provenance
    benchmark.build_scene = build_scene
    benchmark.PythonFrameTelemetry = Telemetry
    benchmark.measured_work_gate = work_gate
    try:
        yield
    finally:
        benchmark.package_provenance = original_provenance
        benchmark.build_scene = original_scene
        benchmark.PythonFrameTelemetry = original_telemetry
        benchmark.measured_work_gate = original_gate
        errors = []
        for observation in reversed(observed):
            try:
                observation.close()
            except Exception as error:
                errors.append('Parser restoration: ' + str(error))
        if sources() != held:
            errors.append('Timing adapter sources changed during worker execution')
        require(not errors, '; '.join(errors))


def run_worker(options, wheel, admission_path):
    require(not options.output.exists(), 'A fresh timing evidence directory is required')
    options.output.mkdir(parents=True)
    receipt = dict(schema=1, launch_id=options.launch_id, pid=os.getpid(), process_stamp=process_stamp(),
                   adapter_sources_sha256=sources(), status='started', process_exit=2)
    benchmark.write_json(options.output / 'worker-start.json', receipt)
    code = 2
    try:
        admission = load_admission(admission_path, options.workload)
        with worker_adapter(options, Path(wheel).resolve(strict=True), admission):
            code = benchmark.run_worker(options)
        # Do not let asymmetric observation overhead establish a release pass.
        # Retain the real timing numbers and report the unresolved effect.
        run_path = options.output / 'run.json'
        if run_path.exists():
            run = json.loads(run_path.read_bytes())
            run.setdefault('instrumentation_gaps', []).append(OVERHEAD_GAP)
            benchmark.write_json(run_path, run)
        receipt['status'] = 'measured' if code == 0 else 'failed_or_blocked'
    except Exception as error:
        code = 2
        receipt.update(status='failed', error=str(error), traceback=traceback.format_exc())
    finally:
        receipt['process_exit'] = code
        run_path = options.output / 'run.json'
        if run_path.exists():
            receipt['run_sha256'] = benchmark.sha256(run_path)
        benchmark.write_json(options.output / 'worker.json', receipt)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', required=True, choices=('upstream', 'candidate'))
    parser.add_argument('--launch-id', required=True)
    parser.add_argument('--workload', required=True, choices=suite.CASES)
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--admission', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run-index', type=int, default=0)
    parser.add_argument('--warmup', type=int, default=benchmark.MIN_WARMUP)
    parser.add_argument('--frames', type=int, default=benchmark.MIN_FRAMES)
    parser.add_argument('--queue-depth', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--vsync', action='store_true')
    options = parser.parse_args(argv)
    require(options.warmup >= benchmark.MIN_WARMUP and options.frames >= benchmark.MIN_FRAMES,
            'At least 100 warm and 1000 measured frames are required')
    require(1 <= options.queue_depth <= 3, 'Queue depth must be 1..3')
    require(options.timeout > 0 and options.timeout < float('inf'), 'Finite positive timeout required')
    return run_worker(options, options.wheel, options.admission)


if __name__ == '__main__':
    raise SystemExit(main())
