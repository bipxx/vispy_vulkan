"""Fixed-quality, isolated-process complete-frame benchmark scaffold.

CPU planning: python tools/benchmark_frames.py --list
Run only after native completion telemetry and scientific admission exist:
  python tools/benchmark_frames.py --reference-python <upstream-python> \
      --candidate-python <fork-python> --output <evidence-dir> \
      --workloads image-scalar-1-translucent-resident

No timing of canvas.render() is used for interactive performance. Captures
are outside warm/measured phases. Missing telemetry, presentation evidence,
quality, hardware equivalence, or complete repetitions keeps gates unproven.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
_work_spec = importlib.util.spec_from_file_location('_benchmark_measured_work', Path(__file__).with_name('benchmark_work.py'))
_work = importlib.util.module_from_spec(_work_spec)
_work_spec.loader.exec_module(_work)
measured_work_gate = _work.measured_work_gate
NATIVE_RESIDENT_ZERO = _work.NATIVE_RESIDENT_ZERO
OPENGL_RESIDENT_ZERO = _work.OPENGL_RESIDENT_ZERO
_gl_spec = importlib.util.spec_from_file_location('_benchmark_upstream_GL', Path(__file__).with_name('benchmark_opengl.py'))
_upstream_gl = importlib.util.module_from_spec(_gl_spec)
_gl_spec.loader.exec_module(_upstream_gl)
OpenGLAttribution = _upstream_gl.OpenGLAttribution
OpenGLPaintQueries = _upstream_gl.OpenGLPaintQueries
_pacing_spec = importlib.util.spec_from_file_location('_benchmark_presentation_pacing', Path(__file__).with_name('benchmark_pacing.py'))
_pacing = importlib.util.module_from_spec(_pacing_spec)
_pacing_spec.loader.exec_module(_pacing)
SEED = 20261009
MIN_WARMUP, MIN_FRAMES, MIN_REPETITIONS = 100, 1000, 5
REQUIRED_COUNTERS = ("application_presents", "dawn_queue_submits", "vk_queue_submits",
                     "texture_uploads", "buffer_uploads", "pipeline_misses", "pipeline_hits",
                     "presentation_passes", "completion_waits", "finish_calls", "copy_bytes",
                     "portable_shader_misses", "draw_calls", "buffer_allocations", "texture_allocations",
                     "native_batches", "native_commands", "shader_module_creations", "render_pipeline_creations",
                     "render_passes", "command_encoders", "bind_group_creations", "native_draw_calls", "binding_decode_bytes",
                     "point_conversion_builds", "point_conversion_bytes")
NATIVE_TIMINGS = ("native_interpret_ns", "native_submit_ns", "texture_conversion_ns",
                  "texture_upload_cpu_ns", "buffer_upload_cpu_ns", "shader_cache_lookup_ns",
                  "shader_normalize_ns", "shader_parse_ns", "shader_link_ns", "shader_spirv_ns",
                  "shader_reflect_ns", "shader_cpu_build_ns", "device_cache_lookup_ns",
                  "pipeline_cache_lookup_ns", "shader_module_creation_ns", "pipeline_creation_ns", "binding_decode_ns")
NATIVE_PEAKS = ("peak_pending_tickets", "peak_queued_frames", "peak_pending_draws",
                "peak_pending_timestamp_frames", "peak_shader_cache_bytes",
                "sampled_peak_live_buffer_bytes", "sampled_peak_live_texture_bytes")
VULKAN_MEMORY_COUNTERS = ("vk_memory_allocate_calls", "vk_memory_allocate_failures", "vk_memory_allocation_count",
                         "vk_memory_allocated_bytes", "vk_memory_free_calls", "vk_memory_free_count",
                         "vk_memory_freed_bytes", "vk_memory_unknown_free_calls", "vk_memory_retired_allocations",
                         "vk_memory_retired_bytes", "vk_memory_tracking_errors")
VULKAN_MEMORY_PEAKS = ("vk_memory_peak_live_allocations", "vk_memory_peak_live_bytes")
SCIENTIFIC_CHECKS = {
    "image": ("float_clim_nan_gamma", "rgba", "interpolation", "partial_update", "blend_layers"),
    "points": ("points_and_instanced", "point_coord_size", "edge_antialias", "spherical_depth", "updates"),
    "volume": ("primary_modes", "categorical_background", "depth_mesh", "clipping_plane", "iso_mip_numeric"),
}


class InstrumentationUnavailable(RuntimeError):
    pass


ALLOCATION_WINDOW_SCOPE = "process-wide intercepted Vulkan device-memory allocationSize totals; event-level measured window including seeded tracked handles; not physical residency, imported payload size, or opaque driver allocations"
ALLOCATION_WINDOW_COUNTERS = (
    'allocate_calls', 'allocate_failures', 'allocation_count', 'allocated_bytes',
    'free_calls', 'free_count', 'freed_bytes', 'null_free_calls', 'unknown_free_calls',
    'retired_allocations', 'retired_bytes', 'tracking_errors', 'live_allocations',
    'live_bytes', 'peak_live_allocations', 'peak_live_bytes')


def validate_allocation_window(record, *, token=None, active=False):
    """Independently validate saved native window records; bool is not an integer."""
    def unsigned(value):
        return type(value) is int and 0 <= value <= (1 << 64)-1
    if type(record) is not dict or record.get('scope') != ALLOCATION_WINDOW_SCOPE:
        raise ValueError('allocation window scope/record missing')
    for name in ('schema', 'token', 'invalidations', 'seed_live_allocations', 'seed_live_bytes'):
        if not unsigned(record.get(name)):
            raise ValueError('allocation window unsigned field malformed: '+name)
    if record['schema'] != 1 or any(type(record.get(n)) is not bool for n in ('supported', 'available', 'complete')):
        raise ValueError('allocation window schema/availability flags malformed')
    if token is not None and (not unsigned(token) or not token or record['token'] != token):
        raise ValueError('allocation window token differs')
    c = record.get('counters')
    if type(c) is not dict or set(c) != set(ALLOCATION_WINDOW_COUNTERS) or any(not unsigned(v) for v in c.values()):
        raise ValueError('allocation window counters incomplete or malformed')
    expected = 'active' if active else 'complete'
    if (record.get('status') != expected or record['token'] == 0 or
            record['supported'] is not True or record['available'] is not True or
            record['complete'] is not True or record['invalidations'] != 0):
        raise ValueError('allocation window is not a complete '+expected+' observation')
    if any(c[n] != 0 for n in ('unknown_free_calls', 'retired_allocations', 'retired_bytes', 'tracking_errors')):
        raise ValueError('allocation window ownership was incomplete')
    if c['allocate_calls'] != c['allocation_count'] + c['allocate_failures'] or c['free_calls'] != c['free_count'] + c['null_free_calls']:
        raise ValueError('allocation window event totals differ')
    for suffix, allocated, freed in (('allocations', 'allocation_count', 'free_count'), ('bytes', 'allocated_bytes', 'freed_bytes')):
        seed = record['seed_live_'+suffix]
        total = seed + c[allocated]
        live, peak = c['live_'+suffix], c['peak_live_'+suffix]
        if total > (1 << 64)-1 or total-c[freed] != live or not max(seed, live) <= peak <= total:
            raise ValueError('allocation window live/peak conservation differs')
        if active and (c[allocated] or c[freed] or live != seed or peak != seed):
            raise ValueError('allocation window begin must contain only seeded ownership')
    if active and any(c[n] for n in ('allocate_calls', 'allocate_failures', 'free_calls', 'null_free_calls')):
        raise ValueError('allocation window begin event deltas must be zero')
    return copy.deepcopy(record)


class NativeAllocationWindow:
    """An optional additive API, with exact owner cleanup on failed measurement."""
    def __init__(self, native):
        self.native, self.token = native, None
        self.observed = {'scope': ALLOCATION_WINDOW_SCOPE, 'begin': None, 'end': None}

    def begin(self):
        if not all(callable(getattr(self.native, name, None)) for name in
                   ('benchmark_memory_window_begin', 'benchmark_memory_window_end')):
            self.observed['begin'] = {'status': 'unsupported', 'supported': False,
                                      'reason': 'additive native/layer window API absent'}
            return False
        raw = self.native.benchmark_memory_window_begin()
        if type(raw) is dict and raw.get('status') == 'active' and type(raw.get('token')) is int and 0 < raw['token'] < 1 << 64:
            self.token = raw['token'] # Retain the owner even if another field is malformed.
        # Native has returned ownership: even deepcopy/store can fail. Capture
        # the exact token first so outer finally can still cancel that owner.
        raw = copy.deepcopy(raw)
        self.observed['begin'] = raw
        if type(raw) is dict and raw.get('status') in ('unavailable', 'incomplete', 'busy', 'token_exhausted'):
            raise InstrumentationUnavailable('allocation window begin unavailable: '+str(raw.get('status')))
        validate_allocation_window(raw, active=True)
        return True

    def end(self):
        if self.token is None:
            return False
        raw = copy.deepcopy(self.native.benchmark_memory_window_end(self.token))
        self.observed['end'] = raw
        token = self.token
        if type(raw) is dict and type(raw.get('token')) is int and raw['token'] == token and raw.get('status') in ('complete', 'incomplete', 'cancelled'):
            self.token = None # The additive API consumed this terminal owner, even when its evidence fails validation.
        result = validate_allocation_window(raw, token=token)
        return result

    def cancel(self):
        if self.token is not None:
            raw = copy.deepcopy(self.native.benchmark_memory_window_end(self.token, cancel=True))
            self.observed['cleanup_cancel'] = raw
            if type(raw) is not dict or type(raw.get('token')) is not int or raw['token'] != self.token or raw.get('status') != 'cancelled' or raw.get('complete') is not False:
                raise ValueError('allocation window cleanup did not close the exact owner')
            self.token = None


def validate_allocation_window_pair(window, warmup, frames):
    if type(warmup) is not int or warmup < 0 or type(frames) is not int or frames <= 0:
        raise ValueError('allocation window frame boundary malformed')
    if type(window) is not dict or window.get('scope') != ALLOCATION_WINDOW_SCOPE:
        raise ValueError('measured allocation window missing')
    begin = validate_allocation_window(window.get('begin'), active=True)
    end = validate_allocation_window(window.get('end'), token=begin['token'])
    if any(begin[n] != end[n] for n in ('seed_live_allocations', 'seed_live_bytes')):
        raise ValueError('allocation window seed changed')
    boundary = window.get('boundary')
    if (type(boundary) is not dict or set(boundary) != {'begin_after_warm_retirement', 'end_after_measured_retirement', 'first_frame', 'frame_count'} or
            boundary['begin_after_warm_retirement'] is not True or boundary['end_after_measured_retirement'] is not True or
            type(boundary['first_frame']) is not int or type(boundary['frame_count']) is not int or
            boundary['first_frame'] != warmup or boundary['frame_count'] != frames):
        raise ValueError('allocation window measured boundary missing')
    return end


@dataclass(frozen=True)
class Workload:
    name: str
    family: str
    shape: tuple[int, ...]
    viewport: tuple[int, int]
    update: str = "resident"
    layers: int = 1
    blend: str = "translucent"
    method: str = "points"
    symbol: str = "disc"
    size: float = 4.0
    spherical: bool = False
    interpolation: str = "linear"
    relative_step_size: float = 0.8
    threshold: float = 0.5
    gamma: float = 1.0
    clim: tuple[float, float] = (0.0, 1.0)
    edge_width: float = 1.0
    antialias: float = 1.0
    seed: int = SEED


def workload_catalog():
    result = {}
    for channels in (1, 4):
        for layers in (1, 8):
            for blend in ("additive", "translucent"):
                for update in ("resident", "full", "patch"):
                    name = f"image-{'scalar' if channels == 1 else 'rgba'}-{layers}-{blend}-{update}"
                    result[name] = Workload(name, "image", (4096, 4096, channels), (3840, 2160), update=update, layers=layers, blend=blend)
    for method in ("points", "instanced"):
        for symbol, size, spherical in (("disc", 4.0, False), ("star", 16.0, False), ("disc", 8.0, True)):
            for update in ("resident", "color", "positions"):
                name = f"points-{method}-{symbol}-{int(size)}-{'sphere' if spherical else 'flat'}-{update}"
                result[name] = Workload(name, "points", (1_000_000, 3), (1920, 1080), update=update, method=method, symbol=symbol, size=size, spherical=spherical)
    for side in (256, 512):
        for viewport in ((1024, 1024), (2048, 2048)):
            for method in ("mip", "translucent", "iso"):
                for update in ("resident", "full"):
                    name = f"volume-{side}-{viewport[0]}-{method}-{update}"
                    result[name] = Workload(name, "volume", (side, side, side), viewport, update=update, method=method)
    return result


CATALOG = workload_catalog()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def counter_delta(before, after, *, peaks=(), gauges=()):
    """Subtract cumulative numeric events, retaining statuses in raw snapshots."""
    excluded = set(peaks) | set(gauges)
    return {key: after[key] - value for key, value in before.items()
            if key not in excluded and isinstance(value, (int, float))
            and not isinstance(value, bool) and isinstance(after.get(key), (int, float))
            and not isinstance(after[key], bool)}


def native_counter_summary(before, after, *, telemetry, backend):
    """Separate declared gauges and lifetime peaks from cumulative events."""
    required = NATIVE_PEAKS + (VULKAN_MEMORY_PEAKS if backend == "Vulkan" else ())
    peaks = tuple(dict.fromkeys(required + tuple(telemetry.get("high_water_marks", ()))))
    return {
        "counter_delta": counter_delta(before, after, peaks=peaks,
                                       gauges=telemetry.get("gauges", ())),
        "native_high_water_marks": {key: after[key] for key in peaks if key in after},
        "missing_native_high_water_marks": [key for key in peaks if key not in after],
        "high_water_scope": "process lifetime, including cold setup and warmup; not measured-window deltas",
    }


def percentile(values, fraction):
    if not values or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("percentile requires nonempty samples and a fraction in [0,1]")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("percentile samples must be finite")
    values = sorted(float(value) for value in values)
    position = (len(values) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def metrics(samples_ns):
    if not samples_ns or any(not math.isfinite(value) or value <= 0 for value in samples_ns):
        raise ValueError("completion latencies must be finite and positive")
    samples = [float(value) / 1e6 for value in samples_ns]
    median = statistics.median(samples)
    return {"count": len(samples), "median_ms": median, "p95_ms": percentile(samples, .95),
            "mean_ms": statistics.mean(samples), "stdev_ms": statistics.pstdev(samples),
            "mad_ms": statistics.median(abs(value - median) for value in samples),
            "min_ms": min(samples), "max_ms": max(samples)}


def alternating_schedule(repetitions):
    if repetitions < MIN_REPETITIONS:
        raise ValueError("release measurement requires at least five alternating repetitions")
    return [(index, kind) for index in range(repetitions)
            for kind in (("upstream", "candidate") if index % 2 == 0 else ("candidate", "upstream"))]


def compare_quality(reference, candidate, *, edge_mask=None, exact=False):
    import numpy as np
    if reference.shape != candidate.shape or reference.dtype != candidate.dtype or reference.dtype != np.uint8 or reference.ndim != 3 or reference.shape[-1] != 4 or not reference.size:
        return {"status": "failed", "reason": "raw RGBA shape/dtype differ"}
    delta = np.abs(reference.astype(np.int16) - candidate.astype(np.int16))
    differing = np.any(delta != 0, axis=-1)
    if exact:
        return {"status": "passed" if not differing.any() else "failed", "exact": True,
                "differing_pixels": int(differing.sum()), "max_abs_u8": int(delta.max())}
    edge = np.zeros(reference.shape[:2], bool) if edge_mask is None else np.asarray(edge_mask, bool)
    if edge.shape != reference.shape[:2]:
        return {"status": "failed", "reason": "predeclared edge-mask extent differs"}
    interior = ~edge
    interior_error = int(delta[interior].max()) if interior.any() else 0
    edge_count = int(edge.sum())
    edge_differing = int((differing & edge).sum())
    passed = interior_error <= 2 and edge_differing <= edge_count * .001
    return {"status": "passed" if passed else "failed", "interior_max_abs_u8": interior_error,
            "edge_pixels": edge_count, "edge_differing_pixels": edge_differing,
            "rules": {"interior_max_abs_u8": 2, "edge_max_differing_fraction": .001}}


def release_gate(reference_runs, candidate_runs, *, update=False, quality_passed=False, same_hardware=False):
    reasons = []
    observed_work_failure = False
    if len(reference_runs) < MIN_REPETITIONS or len(candidate_runs) < MIN_REPETITIONS:
        reasons.append("missing five complete alternating repetitions")
    for run in reference_runs + candidate_runs:
        if run.get("status") != "measured" or run.get("measured_frames", 0) < MIN_FRAMES or run.get("warmup_frames", 0) < MIN_WARMUP:
            reasons.append("missing required completed-frame measurements")
        if not run.get("boundary", {}).get("presented") or not run.get("boundary", {}).get("gpu_completion"):
            reasons.append("actual presented GPU completion is unproven")
        if run.get("boundary", {}).get("whole_qt_paint_scope_verified") is False:
            reasons.append("completion ownership through the final Qt paint submission is unproven")
        if run.get("vsync", True) or not run.get("surface", {}).get("pacing_disabled"):
            reasons.append("unpaced throughput presentation is unproven")
        if run.get("instrumentation_gaps"):
            reasons.append("required performance instrumentation remains incomplete")
        latency = run.get("latency", {})
        if latency.get("count") != run.get("measured_frames") or any(
                not isinstance(latency.get(key), (int, float)) or not math.isfinite(latency[key]) or latency[key] <= 0
                for key in ("median_ms", "p95_ms")):
            reasons.append("completed latency sample statistics missing or invalid")
    for kind, runs in (("upstream", reference_runs), ("candidate", candidate_runs)):
        for run in runs:
            work = measured_work_gate(run, kind, update=update)
            observed_work_failure |= work['status'] == 'failed'
            if work['status'] != 'passed':
                reasons.extend(kind + ': ' + reason for reason in work['reasons'])
    for run in reference_runs:
        try:
            _pacing.validate_completed_samples(run.get('_release_upstream_completed_samples'),
                range(run.get('warmup_frames', 0) + run.get('measured_frames', 0)), unpaced=True)
        except (ValueError, TypeError, KeyError, _pacing.PacingUnavailable):
            reasons.append('each completed upstream sample lacks independently validated owned interval-zero receipt')
    for run in candidate_runs:
        if run.get('renderer', {}).get('backend') == 'Vulkan':
            try:
                validate_allocation_window_pair(run.get('measured_allocation_window'), run.get('warmup_frames'), run.get('measured_frames'))
            except (ValueError, TypeError, KeyError):
                reasons.append('event-level measured Vulkan allocation window is unproven')
    expected_indices = list(range(len(reference_runs)))
    if sorted(run.get("run_index", -1) for run in reference_runs) != expected_indices or sorted(
            run.get("run_index", -1) for run in candidate_runs) != expected_indices:
        reasons.append("paired alternating run identities missing or duplicate")
    if not quality_passed:
        reasons.append("fixed-quality comparison/admission missing or failed")
    if not same_hardware:
        reasons.append("hardware/driver/host equivalence unproven")
    if reasons:
        return {"status": "failed" if observed_work_failure else "unproven", "reasons": sorted(set(reasons))}
    reference_median = statistics.median(run["latency"]["median_ms"] for run in reference_runs)
    candidate_median = statistics.median(run["latency"]["median_ms"] for run in candidate_runs)
    reference_p95 = statistics.median(run["latency"]["p95_ms"] for run in reference_runs)
    candidate_p95 = statistics.median(run["latency"]["p95_ms"] for run in candidate_runs)
    ratio = reference_median / candidate_median
    passed = candidate_median <= reference_median * 1.10 if update else ratio >= 1.20 and candidate_p95 <= reference_p95
    return {"status": "passed" if passed else "failed", "resident": not update,
            "reference_median_ms": reference_median, "candidate_median_ms": candidate_median,
            "reference_p95_ms": reference_p95, "candidate_p95_ms": candidate_p95,
            "speedup": ratio, "update_regression_fraction": candidate_median / reference_median - 1,
            "run_median_ms": {"upstream": [run["latency"]["median_ms"] for run in reference_runs],
                              "candidate": [run["latency"]["median_ms"] for run in candidate_runs]}}


def evidence_path(value, base):
    path = Path(value)
    return path if path.is_absolute() else Path(base) / path


def validate_admission(plan, workload, runs, base):
    """Admission schema binds predeclared parameters and passing checks to real evidence.

    scientific_admission points to JSON with status=passed, workload_sha256,
    benchmark_data_sha256, checks (SCIENTIFIC_CHECKS names -> passed), and
    evidence [{file, sha256}]. Files resolve relative to that JSON's directory.
    This validator verifies evidence identity; the independent oracle produces
    the scientific results. A pathname or an unchecked qualified flag is not a
    scientific admission.
    """
    reasons, record = [], {"status": "unproven"}
    if not plan or not plan.get("scientific_admission"):
        return {**record, "reasons": ["scientific admission manifest missing"]}
    path = evidence_path(plan["scientific_admission"], base)
    try:
        admission = json.loads(path.read_text(encoding="utf-8"))
        record.update(file=str(path.resolve()), sha256=sha256(path))
        if admission.get("schema") != 1 or admission.get("status") != "passed":
            reasons.append("scientific admission did not pass")
        if admission.get("workload_sha256") != value_sha256(asdict(workload)):
            reasons.append("scientific admission workload parameters differ")
        inputs = {run.get("data_sha256") for run in runs}
        if len(inputs) != 1 or None in inputs or inputs != {admission.get("benchmark_data_sha256")}:
            reasons.append("scientific admission benchmark input identity differs or is missing")
        checks = admission.get("checks", {})
        if any(checks.get(name) != "passed" for name in SCIENTIFIC_CHECKS[workload.family]):
            reasons.append("required scientific checks are missing or failed")
        evidence = admission.get("evidence", [])
        if not evidence:
            reasons.append("scientific admission has no retained evidence")
        verified = []
        for item in evidence:
            evidence_file = evidence_path(item["file"], path.parent)
            digest = sha256(evidence_file)
            if digest != item.get("sha256"):
                reasons.append("scientific admission evidence hash differs")
            verified.append({"file": str(evidence_file.resolve()), "sha256": digest})
        record["evidence"] = verified
    except (OSError, ValueError, KeyError, TypeError) as error:
        reasons.append(f"scientific admission cannot be verified: {error}")
    return {**record, "status": "passed" if not reasons else "unproven", "reasons": reasons}


def validate_hardware(hardware, runs):
    """Verify actual renderer and host captures against a predeclared identity.

    The hardware manifest supplies adapter_id, driver, presentation_environment,
    and renderer mappings upstream/candidate containing observed identity keys.
    Candidate vendor_id/device_id/driver/backend and reference vendor/renderer/
    version are mandatory, allowing two API names to identify one designated GPU.
    Human designation is retained and hashed, and actual captures must match it.
    """
    reasons = []
    if not hardware or hardware.get("schema") != 1 or not all(hardware.get(key) for key in (
            "adapter_id", "driver", "presentation_environment")):
        reasons.append("designated adapter/driver/presentation manifest missing")
    expected = (hardware or {}).get("renderers", {})
    mandatory = {"upstream": ("vendor", "renderer", "version"),
                 "candidate": ("vendor_id", "device_id", "driver", "backend")}
    common_provenance = []
    for kind in ("upstream", "candidate"):
        identity = expected.get(kind, {})
        if not all(key in identity for key in mandatory[kind]):
            reasons.append(f"designated {kind} renderer identity missing")
        for run in runs[kind]:
            actual = run.get("renderer", {})
            if not actual or any(actual.get(key) != value for key, value in identity.items()) or actual.get("software"):
                reasons.append(f"actual {kind} renderer differs from designated hardware")
            provenance = run.get("provenance", {})
            common = {key: provenance.get(key) for key in ("python", "platform", "machine", "qt_runtime", "runner_sha256")}
            common["versions"] = {key: value for key, value in provenance.get("versions", {}).items() if key != "vispy"}
            common["environment"] = provenance.get("environment")
            if any(value is None for value in common.values()) or not common["versions"]:
                reasons.append("actual host provenance missing")
            common_provenance.append(value_sha256(common))
    if not runs["upstream"] or not runs["candidate"] or len(set(common_provenance)) != 1:
        reasons.append("reference and candidate host versions/environments differ")
    return {"status": "passed" if not reasons else "unproven", "reasons": sorted(set(reasons))}


def package_provenance(kind):
    import vispy
    import numpy as np
    from PyQt6 import QtCore
    expected = "0.17.0" if kind == "upstream" else "0.17.0+vulkan.1"
    if metadata.version("vispy") != expected or vispy.__version__ != expected:
        raise RuntimeError("distribution/module version differs from selected renderer")
    package = Path(vispy.__file__).resolve().parent
    files = ("gloo/program.py", "gloo/glir.py", "gloo/texture.py", "gloo/buffer.py", "visuals/markers.py", "visuals/image.py", "visuals/volume.py")
    hashes = {file: sha256(package / file) for file in files}
    if kind == "upstream":
        if "site-packages" not in str(package) or list(package.glob("_dawn*")):
            raise RuntimeError("reference environment imports the fork or an uninstalled checkout")
        pinned = json.loads((ROOT / "compat/upstream_manifest.json").read_text())["files"]
        for file, digest in hashes.items():
            if digest != pinned[file]:
                raise RuntimeError(f"upstream source pin differs: {file}")
    versions = {name: metadata.version(name) for name in ("vispy", "numpy", "PyQt6", "PyQt6-Qt6", "PyQt6-sip")}
    return {"kind": kind, "python": platform.python_version(), "executable": sys.executable,
            "platform": platform.platform(), "machine": platform.machine(), "package": str(package),
            "numpy_origin": np.__file__, "versions": versions, "qt_runtime": QtCore.qVersion(),
            "source_sha256": hashes, "runner_sha256": sha256(__file__),
            "environment": {name: os.environ.get(name) for name in ("QT_API", "QT_QPA_PLATFORM", "QT_SCALE_FACTOR", "PYTHONPATH")}}


class PythonFrameTelemetry:
    """Observe the unchanged scene's Python calls in a benchmark process.

    Draw includes scene traversal, shader composition and GLIR generation.
    Exclusive draw subtracts nested parser calls, which include native/driver
    work. These are host wall times, not additive CPU or GPU execution times.
    Qt frame ownership includes the outer Python paint callback's work after
    swap. Backends without a Python paint callback end at the swap call.
    """

    FIELDS = ("python_update_ns", "python_draw_inclusive_ns", "python_draw_exclusive_ns",
              "python_glir_parse_inclusive_ns", "python_glir_pack_ns",
              "python_update_calls", "python_draw_calls", "python_glir_parse_calls", "python_glir_pack_calls",
              "python_paint_calls", "python_paint_inclusive_ns",
              "python_paint_tail_glir_parse_calls", "python_paint_tail_glir_parse_ns")

    def __init__(self, canvas, *, pack_module=None, clock=time.perf_counter_ns):
        self.clock = clock
        self.current = None
        self.frames = {}
        self.totals = dict.fromkeys(self.FIELDS, 0)
        self.totals["unattributed_draw_calls"] = 0
        for name in ("unattributed_glir_parse_calls", "unattributed_glir_parse_ns",
                     "unattributed_glir_pack_calls", "unattributed_glir_pack_ns",
                     "unattributed_paint_calls", "unattributed_paint_ns"):
            self.totals[name] = 0
        self._restores = []
        self._draw_depth = self._parse_depth = 0
        self._paint_depth = 0
        self._after_swap = False
        self.paint_methods = []
        self._parser_time = 0

        def replace(owner, name, wrapper):
            namespace = getattr(owner, '__dict__', {})
            had_own = name in namespace
            old_own = namespace.get(name)
            original = getattr(owner, name)
            setattr(owner, name, wrapper(original))
            self._restores.append((owner, name, had_own, old_own))

        def draw_wrapper(original):
            def draw(*args, **kwargs):
                outer = self._draw_depth == 0
                frame, start, parser_before = self.current, self.clock(), self._parser_time
                self._draw_depth += 1
                try:
                    return original(*args, **kwargs)
                finally:
                    self._draw_depth -= 1
                    if outer:
                        elapsed = self.clock() - start
                        if frame is None:
                            self.totals["unattributed_draw_calls"] += 1
                        else:
                            self._add(frame, "python_draw_calls", 1)
                            self._add(frame, "python_draw_inclusive_ns", elapsed)
                            self._add(frame, "python_draw_exclusive_ns", max(0, elapsed - (self._parser_time - parser_before)))
            return draw

        def parse_wrapper(original):
            def parse(*args, **kwargs):
                outer, frame, start = self._parse_depth == 0, self.current, self.clock()
                self._parse_depth += 1
                try:
                    return original(*args, **kwargs)
                finally:
                    self._parse_depth -= 1
                    if outer:
                        elapsed = self.clock() - start
                        self._parser_time += elapsed
                        if frame is not None:
                            self._add(frame, "python_glir_parse_calls", 1)
                            self._add(frame, "python_glir_parse_inclusive_ns", elapsed)
                            if self._paint_depth and self._after_swap:
                                self._add(frame, "python_paint_tail_glir_parse_calls", 1)
                                self._add(frame, "python_paint_tail_glir_parse_ns", elapsed)
                        else:
                            self.totals["unattributed_glir_parse_calls"] += 1
                            self.totals["unattributed_glir_parse_ns"] += elapsed
            return parse

        def swap_wrapper(original):
            def swap(*args, **kwargs):
                try:
                    return original(*args, **kwargs)
                finally:
                    self._after_swap = self.current is not None
                    if not self._paint_depth:
                        self.current = None
                        self._after_swap = False
            return swap

        def paint_wrapper(original):
            def paint(*args, **kwargs):
                outer, frame, start = self._paint_depth == 0, self.current, self.clock()
                if outer:
                    self._after_swap = False
                self._paint_depth += 1
                try:
                    return original(*args, **kwargs)
                finally:
                    self._paint_depth -= 1
                    if outer:
                        elapsed = self.clock() - start
                        if frame is None:
                            self.totals["unattributed_paint_calls"] += 1
                            self.totals["unattributed_paint_ns"] += elapsed
                        else:
                            self._add(frame, "python_paint_calls", 1)
                            self._add(frame, "python_paint_inclusive_ns", elapsed)
                        if self._after_swap and self.current is frame:
                            self.current = None
                        self._after_swap = False
            return paint

        replace(canvas, "draw_visual", draw_wrapper)
        replace(canvas.context.shared.parser, "parse", parse_wrapper)
        replace(canvas._backend, "_vispy_swap_buffers", swap_wrapper)
        for name in ("paintGL", "paintEvent"):
            method = getattr(canvas._backend, name, None)
            # Native Qt base methods do not expose Python parser work. Wrap
            # actual Python overrides, including nested paint dispatch once.
            if getattr(getattr(method, "__func__", method), "__code__", None) is not None:
                replace(canvas._backend, name, paint_wrapper)
                self.paint_methods.append(name)
        if pack_module is not None:
            def pack_wrapper(original):
                def pack(*args, **kwargs):
                    frame, start = self.current, self.clock()
                    try:
                        return original(*args, **kwargs)
                    finally:
                        if frame is not None:
                            self._add(frame, "python_glir_pack_calls", 1)
                            self._add(frame, "python_glir_pack_ns", self.clock() - start)
                        else:
                            self.totals["unattributed_glir_pack_calls"] += 1
                            self.totals["unattributed_glir_pack_ns"] += self.clock() - start
                return pack
            replace(pack_module, "pack_commands", pack_wrapper)

    def _add(self, frame, name, value):
        frame[name] += value
        self.totals[name] += value

    def begin(self, frame_id):
        if self.current is not None or frame_id in self.frames:
            raise RuntimeError("Python telemetry frame coalesced or repeated before presentation")
        self.current = dict.fromkeys(self.FIELDS, 0)
        self.frames[frame_id] = self.current

    def update(self, function, frame_id):
        frame, start = self.current, self.clock()
        if frame is None or frame is not self.frames.get(frame_id):
            raise RuntimeError("Python update has no matching begun frame")
        try:
            return function(frame_id)
        finally:
            self._add(frame, "python_update_calls", 1)
            self._add(frame, "python_update_ns", self.clock() - start)

    def snapshot(self):
        return dict(self.totals)

    def close(self):
        for owner, name, had_own, old_own in reversed(self._restores):
            if had_own:
                setattr(owner, name, old_own)
            else:
                delattr(owner, name)
        self._restores.clear()
        self.current = None
        self._after_swap = False


class FrameCompletionSamples:
    """Own every received receipt, including batches that fail admission."""
    def __init__(self):
        self.issued = {}
        self.results = {}
        self.observed = []

    def begin(self, frame_id, phase):
        if type(frame_id) is not int or frame_id < 0 or phase not in ("warmup", "measured"):
            raise RuntimeError("invalid completion frame identity or phase")
        if frame_id in self.issued:
            raise RuntimeError(f"duplicate completion frame request {frame_id}")
        self.issued[frame_id] = phase

    def collect(self, records, phase):
        # Freeze the entire incoming batch before checking its first member.
        # A bad early receipt must not hide later failure/status evidence.
        batch = copy.deepcopy(list(records))
        self.observed.extend(batch)
        for record in batch:
            frame_id = record.get("frame_id") if isinstance(record, dict) else None
            if type(frame_id) is not int or frame_id < 0:
                raise RuntimeError("invalid completion frame identity")
            if frame_id not in self.issued:
                raise RuntimeError(f"unissued completion frame {frame_id}")
            if self.issued[frame_id] != phase:
                raise RuntimeError(f"wrong-phase completion frame {frame_id}")
            if frame_id in self.results:
                raise RuntimeError(f"duplicate completion frame {frame_id}")
            if record.get("status") != "success" or record.get("presented") is not True:
                raise RuntimeError(f"failed or unpresented completion frame {frame_id}: {record.get('status')}")
            self.results[frame_id] = copy.deepcopy(record)

    def count(self, phase):
        return sum(self.issued[frame_id] == phase for frame_id in self.results)

    def samples(self, phase):
        return [copy.deepcopy(self.results[frame_id]) for frame_id in sorted(self.results)
                if self.issued[frame_id] == phase]


class GPUFrameSamples:
    """Join separately arriving GPU maps to issued frames without losing failures."""
    def __init__(self):
        self.issued = set()
        self.results = {}
        self.observed = []

    def begin(self, frame_id):
        if type(frame_id) is not int or frame_id < 0:
            raise RuntimeError("invalid GPU timing frame identity")
        if frame_id in self.issued:
            raise RuntimeError(f"duplicate GPU timing frame {frame_id}")
        self.issued.add(frame_id)

    def collect(self, records):
        batch = copy.deepcopy(list(records))
        self.observed.extend(batch)
        for record in batch:
            frame_id = record.get("frame_id") if isinstance(record, dict) else None
            if type(frame_id) is not int or frame_id < 0:
                raise RuntimeError("invalid GPU timing frame identity")
            if frame_id not in self.issued or frame_id in self.results:
                raise RuntimeError(f"unissued or duplicate GPU timing frame {frame_id}")
            # Retain failure statuses as well as successful/quantized-zero data.
            self.results[frame_id] = copy.deepcopy(record)

    def complete(self, first, count):
        return all(frame_id in self.results for frame_id in range(first, first + count))

    def join(self, samples):
        for sample in samples:
            frame_id = sample.get("frame_id") if isinstance(sample, dict) else None
            if type(frame_id) is not int or frame_id < 0:
                raise RuntimeError("invalid GPU timing frame identity")
            if frame_id not in self.results:
                raise InstrumentationUnavailable(f"GPU timing not received for frame {frame_id}")
            result = self.results[frame_id]
            sample["gpu_timing"] = copy.deepcopy(result)
            if result.get("status") != "success":
                raise InstrumentationUnavailable(f"GPU timing frame {frame_id}: {result.get('status')}: {result.get('error', '')}")
            passes = result.get("passes", [])
            if not passes or int(result.get("submission_count", 0)) < 1:
                raise InstrumentationUnavailable(f"GPU timing frame {frame_id} has no complete render passes")
            intervals = [(int(item["begin_ns"]), int(item["end_ns"]), int(item["elapsed_ns"])) for item in passes]
            if any(begin < 0 or end < begin or elapsed != end - begin for begin, end, elapsed in intervals):
                raise InstrumentationUnavailable(f"GPU timing frame {frame_id} has invalid pass intervals")
            if int(result["pass_sum_ns"]) != sum(elapsed for _, _, elapsed in intervals):
                raise InstrumentationUnavailable(f"GPU timing frame {frame_id} has inconsistent summed pass time")
            if int(result["render_span_ns"]) != max(end for _, end, _ in intervals) - min(begin for begin, _, _ in intervals):
                raise InstrumentationUnavailable(f"GPU timing frame {frame_id} has inconsistent render span")


class CandidateCompletions:
    def __init__(self, canvas):
        from vispy import _dawn
        self.native = _dawn
        self.canvas = canvas
        self.canvas_id = int(canvas._backend._dawn_canvas_id)
        if not all(hasattr(_dawn, name) for name in ("benchmark_begin_frame", "benchmark_completions", "benchmark_surface_info")):
            raise InstrumentationUnavailable("native final-presentation completion telemetry is absent")
        self.surface = dict(_dawn.benchmark_surface_info(self.canvas_id))
        self.telemetry = dict(_dawn.benchmark_telemetry_info()) if hasattr(_dawn, "benchmark_telemetry_info") else {}
        self.gpu_frames = GPUFrameSamples()
        self.gpu_metadata = {"supported": False, "enabled": False, "reason": "native GPU timestamp API absent"}
        if all(hasattr(_dawn, name) for name in ("benchmark_configure_gpu_timing", "benchmark_gpu_timings")):
            self.gpu_metadata = dict(_dawn.benchmark_configure_gpu_timing(self.canvas_id, True))
        self.boundary = {"presented": True, "gpu_completion": True,
                         "method": "native presentation ticket completion callback",
                         "whole_qt_paint_scope_verified": False,
                         "scanout_measured": False, "deliberate_gpu_waits": False}
    def begin(self, frame_id):
        self.native.benchmark_begin_frame(self.canvas_id, frame_id)
        self.gpu_frames.begin(frame_id)
    def request_ready(self):
        # A Qt update may be deferred even after event processing. Wait until
        # its paint has consumed the reservation before requesting another
        # frame; already painted GPU work may remain in flight.
        if self.telemetry.get("frame_ownership_scope") != "whole_qt_paint_v1":
            return True
        ready = getattr(self.native, "benchmark_frame_request_ready", None)
        if not callable(ready):
            raise InstrumentationUnavailable("native Qt paint frame request readiness is absent")
        value = ready(self.canvas_id)
        if type(value) is not bool:
            raise InstrumentationUnavailable("native Qt paint frame request readiness must be a boolean")
        return value
    def poll(self):
        self.native.process_events()
        if self.gpu_metadata.get("enabled"):
            self.gpu_frames.collect(self.native.benchmark_gpu_timings(self.canvas_id))
        return list(self.native.benchmark_completions(self.canvas_id))
    def drain_gpu(self, first, count, timeout, *, completions=None, phase=None):
        if completions is not None and phase not in ("warmup", "measured"):
            raise ValueError("completion drain requires its owning phase")
        if completions is None and not self.gpu_metadata.get("enabled"):
            return
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() >= deadline:
                raise InstrumentationUnavailable("owned asynchronous GPU timing readback timed out")
            self.canvas.app.process_events()
            if completions is not None:
                completions.collect(self.poll(), phase)
            else:
                self.native.process_events()
                self.gpu_frames.collect(self.native.benchmark_gpu_timings(self.canvas_id))
            if not self.gpu_metadata.get("enabled") or self.gpu_frames.complete(first, count):
                break
    def counters(self):
        return dict(self.native.probe())

    def verify_scope(self, samples):
        """Admit actual paint-owned receipts, then their final presentation maps.

        A capability string alone is insufficient. Legacy/native-present
        samples remain usable for diagnosis with the scope gate explicitly off.
        """
        self.boundary["whole_qt_paint_scope_verified"] = False
        if self.telemetry.get("frame_ownership_scope") != "whole_qt_paint_v1" or not samples:
            return False
        tokens = dict(getattr(self, "_verified_paint_tokens", {}))
        for sample in samples:
            frame_id = sample.get("frame_id")
            token = sample.get("paint_token")
            submissions = sample.get("submission_count")
            presents = sample.get("present_count")
            last_present = sample.get("last_present_submission_index")
            if (type(frame_id) is not int or frame_id < 0 or
                    sample.get("status") != "success" or sample.get("presented") is not True or
                    sample.get("frame_scope") != "qt_paint" or
                    type(token) is not int or token <= 0 or
                    sample.get("ownership_closed") is not True or
                    sample.get("ownership_retired") is not True or
                    sample.get("counters_captured") is not True or
                    sample.get("counter_capture") != "submission" or
                    not isinstance(sample.get("counters"), dict) or not sample["counters"] or
                    type(submissions) is not int or submissions < 1 or
                    type(presents) is not int or not 0 < presents <= submissions or
                    type(last_present) is not int or not 0 <= last_present < submissions):
                raise InstrumentationUnavailable(f"frame {frame_id} lacks complete Qt paint ownership")
            if token in tokens and tokens[token] != frame_id:
                raise InstrumentationUnavailable(f"Qt paint token {token} belongs to multiple frames")
            if frame_id in tokens.values() and tokens.get(token) != frame_id:
                raise InstrumentationUnavailable(f"frame {frame_id} belongs to multiple Qt paint tokens")
            tokens[token] = frame_id
            if self.gpu_metadata.get("enabled"):
                timing = sample.get("gpu_timing")
                if (not isinstance(timing, dict) or timing.get("status") != "success" or
                        timing.get("frame_scope") != "qt_paint" or
                        type(timing.get("frame_id")) is not int or timing["frame_id"] != frame_id or
                        type(timing.get("paint_token")) is not int or timing["paint_token"] != token or
                        type(timing.get("submission_count")) is not int or
                        timing["submission_count"] != submissions or
                        type(timing.get("last_present_submission_index")) is not int or
                        timing["last_present_submission_index"] != last_present):
                    raise InstrumentationUnavailable(f"frame {frame_id} GPU timing has different paint ownership")
                passes = timing.get("passes", [])
                if any(type(item.get("submission_index")) is not int or
                       not 0 <= item["submission_index"] < submissions for item in passes):
                    raise InstrumentationUnavailable(f"frame {frame_id} GPU pass is outside owned submissions")
                conversions = [item for item in passes if item.get("kind") == "surface_conversion"]
                if (len(conversions) != presents or
                        len({item["submission_index"] for item in conversions}) != presents or
                        max((item["submission_index"] for item in conversions), default=-1) != last_present):
                    raise InstrumentationUnavailable(f"frame {frame_id} lacks the final owned presentation pass")
        self._verified_paint_tokens = tokens
        self.boundary.update({
            "whole_qt_paint_scope_verified": True,
            "method": "native Qt paint ownership closed and all owned submissions retired",
            "verified_paint_frames": len(tokens),
            "final_presentation_gpu_pass_verified": bool(self.gpu_metadata.get("enabled")),
        })
        return True


def make_presentation_pacing(canvas):
    from PyQt6 import QtCore, QtGui
    observer = _pacing.WindowsPresentationPacing(canvas, QtGui.QOpenGLContext, QtCore.QThread)
    observer.formats = _pacing.qt_format_metadata(canvas, QtGui.QOpenGLContext, QtGui.QSurfaceFormat)
    return observer


class OpenGLCompletions:
    def __init__(self, canvas, *, gl=None, qt_context=None, gl_adapter=None, attribution=None, pacing_observer=None, require_unpaced=False):
        if gl is None:
            from OpenGL import GL as gl
        if qt_context is None:
            from PyQt6.QtGui import QOpenGLContext as qt_context
        if gl_adapter is None:
            from vispy.gloo import gl as gl_adapter
        self.gl, self.qt_context, self.canvas = gl, qt_context, canvas
        self.waiting, self.fences, self.failure = None, [], None
        self.frame_before, self.frame_counters = {}, {}
        self.paint_fences, self.fence_contexts = {}, {}
        self.attribution, self.queries = attribution, None
        if type(require_unpaced) is not bool:
            raise ValueError('explicit unpaced requirement must be boolean')
        self.pacing_observer, self.require_unpaced = pacing_observer, require_unpaced
        self.presentation_receipts = {}
        if not hasattr(canvas.native, "frameSwapped"):
            raise InstrumentationUnavailable("reference Qt canvas has no actual frameSwapped signal")
        self.surface = {"swap_interval": canvas.native.context().format().swapInterval()}
        self.surface.update(scene_context_swap_interval=self.surface["swap_interval"], swap_interval_field_scope="scene_context_format_metadata_only", pacing_disabled=False)
        if pacing_observer is not None:
            self.surface.update(getattr(pacing_observer, "formats", {}))
            self.surface.update(pacing_observer.metadata())
        try:
            required_adapter = ('glBufferData','glBufferSubData','glTexImage2D','glTexSubImage2D',
                                'glCompileShader','glLinkProgram','glCreateBuffer','glCreateTexture')
            required_raw = ('glTexImage3D','glTexSubImage3D','glFinish','glClientWaitSync','glWaitSync','glReadPixels')
            if (not all(callable(getattr(gl_adapter,name,None)) for name in required_adapter) or
                    not all(callable(getattr(gl,name,None)) for name in required_raw)):
                raise InstrumentationUnavailable('complete pinned upstream GL call-observation API absent')
            if self.attribution is None:
                self.attribution = OpenGLAttribution([('vispy', gl_adapter), ('raw', gl)])
            self.queries = OpenGLPaintQueries(gl, canvas, qt_context.currentContext)
            self.queries.on_paint_end = self._paint_closed
            self.gpu_metadata = self.queries.metadata()
            self.telemetry = self.attribution.metadata()
            canvas.native.frameSwapped.connect(self._presented)
        except BaseException:
            if self.queries is not None:
                self.queries.close()
            if self.attribution is not None:
                self.attribution.close()
            raise
        self.boundary = {"presented": True, "gpu_completion": True,
                         "method": "scene-context fence after whole paint plus Qt frameSwapped fence in verified same-or-sharing presentation context; both zero-timeout polls must signal",
                         "gpu_paint_scope": "same-scene-context timestamp pair including the post-draw alpha tail; not Qt compositor GPU time",
                         "scanout_measured": False, "deliberate_gpu_waits": False}

    def _paint_closed(self, frame_id):
        fence = self.gl.glFenceSync(self.gl.GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
        if not fence:
            raise InstrumentationUnavailable('scene-context paint completion fence creation failed')
        self.paint_fences[frame_id] = fence
        self.gl.glFlush()
        after = self.attribution.snapshot()
        self.frame_counters[frame_id] = counter_delta(self.frame_before.pop(frame_id), after,
            peaks=self.telemetry['high_water_marks'], gauges=self.telemetry['gauges'])

    def request_ready(self):
        return self.waiting is None and self.queries.ready()

    def begin(self, frame_id):
        if not self.request_ready():
            raise RuntimeError("reference frame updates coalesced before the preceding presentation")
        self.queries.begin(frame_id)
        self.frame_before[frame_id] = self.attribution.snapshot()
        self.waiting = (frame_id, time.perf_counter_ns())
    def _presented(self):
        self.attribution.totals['gl_application_presents'] += 1
        if self.waiting is None:
            self.attribution.totals['gl_unattributed_presents'] += 1
            return
        try:
            frame_id, begin = self.waiting
            if frame_id not in self.frame_counters:
                raise InstrumentationUnavailable('Qt frameSwapped precedes the owning complete VisPy paint')
            if self.pacing_observer is not None:
                receipt = self.pacing_observer.observe(frame_id, closed_frame_id=frame_id)
                self.surface.update(self.pacing_observer.metadata())
            else:
                receipt = dict(schema=1, frame_id=frame_id, status='unproven', interval=None,
                    errors=['no explicit presentation observer'], owned_after_closed_paint=True)
            self.presentation_receipts[frame_id] = copy.deepcopy(receipt)
            context = self.qt_context.currentContext()
            scene_context = self.canvas.native.context()
            if context is None or (context != scene_context and not self.qt_context.areSharing(context, scene_context)):
                raise InstrumentationUnavailable("Qt frameSwapped exposes no active GL presentation context sharing with the scene")
            if self.require_unpaced:
                _pacing.validate_receipt(receipt, frame_id, unpaced=True)
            fence = self.gl.glFenceSync(self.gl.GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
            if not fence:
                raise InstrumentationUnavailable("presentation-context GL fence creation failed")
            self.fences.append((frame_id, begin, fence))
            self.gl.glFlush()
            self.boundary["presentation_context_verified"] = True
            self.boundary["presentation_context_is_scene_context"] = context == scene_context
            self.fence_contexts[frame_id] = dict(presentation_context_is_scene_context=context==scene_context,
                compatible_share_group_verified=context==scene_context or self.qt_context.areSharing(context,scene_context))
            self.waiting = None
        except Exception as error:
            self.failure = str(error)
    def poll(self):
        if self.failure:
            raise InstrumentationUnavailable(self.failure)
        self.canvas.set_current()
        self.queries.poll()
        completed = []
        while self.fences:
            frame_id, begin, fence = self.fences[0]
            if frame_id not in self.paint_fences:
                raise InstrumentationUnavailable('reference frame has no owning scene-paint fence')
            scene_fence = self.paint_fences[frame_id]
            statuses = [self.gl.glClientWaitSync(item,0,0) for item in (scene_fence,fence)]
            if any(status not in (self.gl.GL_TIMEOUT_EXPIRED,self.gl.GL_ALREADY_SIGNALED,self.gl.GL_CONDITION_SATISFIED) for status in statuses):
                raise RuntimeError('reference scene/presentation fence failed')
            if self.gl.GL_TIMEOUT_EXPIRED in statuses:
                break
            end = time.perf_counter_ns()
            self.gl.glDeleteSync(fence)
            self.gl.glDeleteSync(scene_fence)
            del self.paint_fences[frame_id]
            self.fences.pop(0)
            if frame_id not in self.frame_counters:
                raise InstrumentationUnavailable("reference presentation has no closed owning VisPy paint")
            completed.append({"frame_id": frame_id, "completion_latency_ns": end - begin,
                              "completion_timestamp_ns": end, "presented": True, "status": "success",
                              "opengl_paint_counters": self.frame_counters.pop(frame_id),
                              "scene_and_presentation_syncs_signaled":True,
                              "opengl_fence_contexts":self.fence_contexts.pop(frame_id),
                              "presentation_pacing":copy.deepcopy(self.presentation_receipts.pop(frame_id))})
        return completed

    def drain_gpu(self, first, count, timeout, *, completions, phase):
        deadline = time.monotonic() + timeout
        while not self.queries.complete(first, count):
            if time.monotonic() >= deadline:
                raise InstrumentationUnavailable("owned upstream paint timestamp readback timed out")
            self.canvas.app.process_events()
            completions.collect(self.poll(), phase)
        self.queries.join(completions.samples(phase))

    def verify_pacing(self, samples, expected_ids):
        if self.require_unpaced:
            _pacing.validate_completed_samples(samples, expected_ids, unpaced=True)
        return bool(samples) and all(sample.get('presentation_pacing', {}).get('status') == 'observed' for sample in samples)

    def counters(self):
        return self.attribution.snapshot()

    def close(self):
        failures = []
        try:
            self.canvas.native.frameSwapped.disconnect(self._presented)
        except Exception as error:
            failures.append(str(error))
        for frame, begin, fence in self.fences:
            try:
                self.gl.glDeleteSync(fence)
            except Exception as error:
                failures.append(str(error))
        self.fences.clear()
        for fence in self.paint_fences.values():
            try:
                self.gl.glDeleteSync(fence)
            except Exception as error:
                failures.append(str(error))
        self.paint_fences.clear()
        try:
            self.queries.close()
        except Exception as error:
            failures.append(str(error))
        finally:
            self.attribution.close()
        if failures:
            raise RuntimeError('upstream telemetry cleanup failed: '+repr(failures))


def configure_qt_presentation(vsync, observation=None, *, qt_core=None, qt_gui=None):
    """Request pacing before Qt can create internal/shared presentation contexts.

    The default readback is a request, never proof of actual unpaced swaps.
    Existing actual surface/context pacing checks remain independently required.
    Explicit Qt dependencies allow provider-free CPU protocol controls.
    """
    if type(vsync) is not bool:
        raise ValueError('explicit boolean vsync required')
    if observation is None:
        observation = {}
    observation.update(vsync=vsync, requested_default_swap_interval=1 if vsync else 0,
                       scope='Qt default format request before native application/context; not actual presentation evidence')
    if qt_core is None or qt_gui is None:
        from PyQt6 import QtCore, QtGui
        qt_core = QtCore if qt_core is None else qt_core
        qt_gui = QtGui if qt_gui is None else qt_gui
    observation['preexisting_application'] = qt_core.QCoreApplication.instance() is not None
    observation['preexisting_current_GL_context'] = qt_gui.QOpenGLContext.currentContext() is not None
    if observation['preexisting_application'] or observation['preexisting_current_GL_context']:
        raise InstrumentationUnavailable('Qt presentation defaults require a fresh process before application/context creation')
    previous = qt_gui.QSurfaceFormat.defaultFormat()
    observation['previous_default_swap_interval'] = int(previous.swapInterval())
    requested = qt_gui.QSurfaceFormat(previous)
    requested.setSwapInterval(observation['requested_default_swap_interval'])
    qt_gui.QSurfaceFormat.setDefaultFormat(requested)
    observation['readback_default_swap_interval'] = int(qt_gui.QSurfaceFormat.defaultFormat().swapInterval())
    if observation['readback_default_swap_interval'] != observation['requested_default_swap_interval']:
        raise InstrumentationUnavailable('Qt default swap-interval request did not survive immediate readback')
    return observation


def build_scene(workload, kind, vsync):
    import numpy as np
    from vispy import scene
    canvas = scene.SceneCanvas(app="pyqt6", size=workload.viewport, show=True, vsync=vsync,
                               bgcolor="black", config={"depth_size": 24, "stencil_size": 8, "samples": 0})
    canvas.app.native.setQuitOnLastWindowClosed(False)
    view = canvas.central_widget.add_view()
    visuals, data = [], None
    rng = np.random.default_rng(workload.seed)
    if workload.family == "image":
        side, _, channels = workload.shape
        ramp = np.linspace(0, 1, side, dtype=np.float32)
        if channels == 1:
            data = (ramp[:, None] * .6 + ramp[None, :] * .4).astype(np.float32)
        else:
            data = np.empty(workload.shape, np.uint8)
            axis = np.arange(side, dtype=np.uint16)
            data[..., 0] = (axis[None, :] % 256).astype(np.uint8)
            data[..., 1] = (axis[:, None] % 256).astype(np.uint8)
            data[..., 2] = ((axis[:, None] ^ axis[None, :]) % 256).astype(np.uint8)
            data[..., 3] = 255
        for layer in range(workload.layers):
            visual = scene.visuals.Image(data, parent=view.scene, cmap="grays", clim=workload.clim,
                                          gamma=workload.gamma, interpolation=workload.interpolation,
                                          texture_format="r32f" if channels == 1 else "rgba8")
            visual.set_gl_state(workload.blend, depth_test=False)
            visual.opacity = 1.0 if workload.layers == 1 else .125
            visuals.append(visual)
        view.camera = scene.PanZoomCamera(rect=(0, 0, side, side), aspect=1)
    elif workload.family == "points":
        data = rng.uniform(-1, 1, workload.shape).astype(np.float32)
        marker = scene.visuals.Markers(parent=view.scene, method=workload.method, spherical=workload.spherical,
                                       antialias=workload.antialias)
        marker.set_data(data, size=workload.size, symbol=workload.symbol, edge_width=workload.edge_width,
                        edge_color=(0.2, 0.2, 0.2, 1), face_color=(0.1, 0.5, 0.9, 1))
        visuals.append(marker)
        view.camera = scene.PanZoomCamera(rect=(-1, -1, 2, 2), aspect=1)
    else:
        side = workload.shape[0]
        axis = np.linspace(-.5, .5, side, dtype=np.float32)
        plane = (axis[:, None] / .36) ** 2 + (axis[None, :] / .28) ** 2
        data = np.empty(workload.shape, np.float32)
        for z in range(side):
            data[z] = np.clip(1 - plane - (axis[z] / .42) ** 2, 0, 1)
        data[side // 2, side // 2, side // 2] = 1.0
        visual = scene.visuals.Volume(data, parent=view.scene, method=workload.method, clim=workload.clim,
                                      gamma=workload.gamma, threshold=workload.threshold,
                                      relative_step_size=workload.relative_step_size,
                                      interpolation=workload.interpolation, texture_format="r32f")
        visuals.append(visual)
        view.camera = scene.TurntableCamera(azimuth=30, elevation=20, distance=side * 2.5,
                                            fov=45, center=(side / 2, side / 2, side / 2))
    update_buffer = np.empty_like(data)
    source_hash = hashlib.sha256(memoryview(np.ascontiguousarray(data)).cast("B")).hexdigest()
    def update(frame):
        phase = frame * 2 * math.pi / 180
        if workload.update == "resident":
            if workload.family == "volume":
                view.camera.azimuth = 30 + 8 * math.sin(phase)
            else:
                extent = workload.shape[0] if workload.family == "image" else 2
                origin = 0 if workload.family == "image" else -1
                zoom = 1 + .02 * math.sin(phase)
                shift = extent * .01 * math.cos(phase)
                view.camera.rect = (origin + shift, origin, extent * zoom, extent * zoom)
            return 0
        if workload.family == "image" and workload.update == "patch":
            extent = 64
            patch = data[:extent, :extent].copy()
            patch[..., 0] = frame % 255 if patch.ndim == 3 else patch[..., 0]
            if patch.ndim == 2:
                patch.fill((frame % 100) / 100)
            for visual in visuals:
                visual._texture.set_data(patch, offset=(128, 128))
            return patch.nbytes * len(visuals)
        if workload.family == "points":
            colors = (0.1 + .1 * math.sin(phase), .5, .9, 1)
            positions = data
            if workload.update == "positions":
                np.add(data, np.float32(.01 * math.sin(phase)), out=update_buffer)
                positions = update_buffer
            visuals[0].set_data(positions, size=workload.size, symbol=workload.symbol,
                                edge_width=workload.edge_width, face_color=colors, edge_color=(.2, .2, .2, 1))
            return data.shape[0] * (4 * 4 if workload.update == "color" else 3 * 4)
        if data.dtype == np.uint8:
            np.bitwise_xor(data, np.uint8(frame % 7), out=update_buffer)
            update_buffer[..., 3] = 255
        else:
            np.multiply(data, np.float32(1 - .01 * math.sin(phase)), out=update_buffer)
        for visual in visuals:
            visual.set_data(update_buffer)
        return update_buffer.nbytes * len(visuals)
    return canvas, update, source_hash


def run_worker(options):
    import numpy as np
    workload = CATALOG[options.workload]
    directory = options.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    result = {"schema": 1, "status": "pending", "workload": asdict(workload), "run_index": options.run_index,
              "warmup_frames": options.warmup, "measured_frames": options.frames,
              "queue_depth": options.queue_depth, "vsync": options.vsync}
    canvas = python_telemetry = collector = reference_attribution = allocation_window = None
    completions = FrameCompletionSamples()
    started = time.perf_counter_ns()
    try:
        os.environ.setdefault("QT_API", "pyqt6")
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            raise InstrumentationUnavailable("required actual presentation cannot use Qt offscreen")
        result['qt_presentation_setup'] = {}
        configure_qt_presentation(options.vsync, result['qt_presentation_setup'])
        import vispy
        if options.worker == "upstream":
            vispy.use(gl="gl+")
            from OpenGL import GL
            from vispy.gloo import gl as gl_adapter
            reference_attribution = OpenGLAttribution([('vispy',gl_adapter),('raw',GL)])
            result['opengl_cold_counters_before'] = reference_attribution.snapshot()
        result["provenance"] = package_provenance(options.worker)
        if options.worker == "candidate":
            from vispy import _dawn
            if not all(hasattr(_dawn, name) for name in ("benchmark_begin_frame", "benchmark_completions", "benchmark_surface_info")):
                raise InstrumentationUnavailable("native final-presentation completion telemetry is absent")
        canvas, update, source_hash = build_scene(workload, options.worker, options.vsync)
        canvas.app.process_events()
        if tuple(canvas.physical_size) != workload.viewport:
            raise InstrumentationUnavailable("physical framebuffer extent differs from the fixed workload viewport")
        canvas.set_current()
        if options.worker == "candidate":
            from vispy import _dawn
            result["renderer"] = _dawn.device_info()
            if result["renderer"].get("software"):
                raise InstrumentationUnavailable("software adapters supply correctness evidence only")
        else:
            from OpenGL import GL
            result["renderer"] = {name: GL.glGetString(enum).decode() for name, enum in
                                  (("vendor", GL.GL_VENDOR), ("renderer", GL.GL_RENDERER), ("version", GL.GL_VERSION))}
            result["surface_format_metadata_before_collector"] = {"scene_context_swap_interval": canvas.native.context().format().swapInterval()}
        # This capture verifies quality, not performance. All explicit waits
        # and readback are before the instrumentation/warm phases.
        captures = []
        for probe_frame in (None, 7, 73):
            if probe_frame is not None:
                update(probe_frame)
            quality = canvas.render(alpha=True)
            file = f"quality-{'initial' if probe_frame is None else probe_frame}.npy"
            np.save(directory / file, quality, allow_pickle=False)
            captures.append({"file": file, "sha256": sha256(directory / file), "probe_frame": probe_frame,
                             "shape": list(quality.shape), "outside_sampled_path": True})
        result["quality_captures"] = captures
        result["data_sha256"] = source_hash
        result["cold_startup_ms"] = (time.perf_counter_ns() - started) / 1e6
        telemetry_start = time.perf_counter_ns()
        if reference_attribution is not None:
            result['opengl_cold_counters_after'] = reference_attribution.snapshot()
        collector = CandidateCompletions(canvas) if options.worker == "candidate" else OpenGLCompletions(canvas,attribution=reference_attribution,pacing_observer=make_presentation_pacing(canvas),require_unpaced=not options.vsync)
        result['telemetry_setup_ms'] = (time.perf_counter_ns()-telemetry_start)/1e6
        if isinstance(collector, OpenGLCompletions):
            result['opengl_telemetry'] = collector.attribution.metadata()
            result['gpu_telemetry'] = collector.gpu_metadata
            result['gpu_timing_collection'] = {
                'method':'same-scene-context asynchronous paint timestamps joined to independent presentation fences by frame ID',
                'scope':'whole VisPy paint including alpha tail; excludes Qt compositor, presentation engine and scanout',
                'final_drain':'availability-only polling after completion; completion latency samples are not overwritten',
                'instrumentation_cost':'actual GL wrappers, timestamp commands and collection remain in observed work; no overhead subtraction',
            }
        pack_module = None
        if options.worker == "candidate":
            from vispy.gloo import dawn_parser as pack_module
            result["native_telemetry"] = collector.telemetry
            result["gpu_telemetry"] = collector.gpu_metadata
            result["gpu_timing_collection"] = {
                "method": "owned asynchronous query maps; frame IDs joined independently of queue completion",
                "final_drain": "nonblocking event polls after the last completion, outside throughput interval",
                "instrumentation_cost": "resolve/copy work and in-flight query capacity affect actual measured frames; no subtraction",
            }
        python_telemetry = PythonFrameTelemetry(canvas, pack_module=pack_module)
        result["python_telemetry"] = {
            "clock": "time.perf_counter_ns monotonic host wall time",
            "scope": "benchmark-process wrappers around unchanged scene draw, parser, command packing, update, swap and Python Qt paint callbacks",
            "draw_inclusive": "scene traversal, visual preparation, composition and GLIR generation, including nested parser work",
            "draw_exclusive": "outer draw wall time minus nested outer parser wall time",
            "parse_inclusive": "filtered GLIR interpretation including native/driver calls; candidate includes packing",
            "pack": "candidate ndarray contiguity and command payload copying",
            "timings_overlap": True,
            "frame_boundary": "begin request through outer Python paint return after swap; swap fallback for backends without Python paint callbacks; completion separately polled",
            "paint_methods": python_telemetry.paint_methods,
            "paint_tail_parse": "outer parser calls after backend swap and before owning Python paint returns; included in total parser work",
        }
        result["boundary"] = collector.boundary
        result["surface"] = collector.surface
        if isinstance(collector, OpenGLCompletions):
            result['qt_presentation_setup']['actual_context_swap_interval'] = collector.surface['swap_interval']
        if isinstance(collector, CandidateCompletions) and not options.vsync and not collector.surface.get("pacing_disabled"):
            raise InstrumentationUnavailable("actual presentation pacing remains enabled")
        logical_update_bytes = 0
        def phase(first, count, phase_name):
            nonlocal logical_update_bytes
            issued = first
            deadline = time.monotonic() + options.timeout
            while completions.count(phase_name) < count:
                if time.monotonic() > deadline:
                    raise RuntimeError("actual presented-frame completion timed out")
                canvas.app.process_events()
                completions.collect(collector.poll(), phase_name)
                pending = issued - first - completions.count(phase_name)
                presented = not isinstance(collector, OpenGLCompletions) or collector.request_ready()
                if issued < first + count and pending < options.queue_depth and presented:
                    if isinstance(collector, CandidateCompletions) and not collector.request_ready():
                        continue
                    collector.begin(issued)
                    completions.begin(issued, phase_name)
                    python_telemetry.begin(issued)
                    logical_update_bytes += python_telemetry.update(update, issued)
                    canvas.update()
                    issued += 1
            return time.perf_counter_ns()
        phase(0, options.warmup, "warmup")
        if isinstance(collector, CandidateCompletions):
            collector.drain_gpu(0, options.warmup, options.timeout,
                                completions=completions, phase="warmup")
            if collector.gpu_metadata.get("enabled"):
                # Failed warm maps must stop admission just like measured maps.
                warm = completions.samples("warmup")
                collector.gpu_frames.join(warm)
            else:
                warm = completions.samples("warmup")
            collector.verify_scope(warm)
        else:
            collector.drain_gpu(0, options.warmup, options.timeout, completions=completions, phase='warmup')
            collector.verify_pacing(completions.samples('warmup'), range(options.warmup))
        if isinstance(collector, CandidateCompletions) and result['renderer'].get('backend') == 'Vulkan':
            allocation_window = NativeAllocationWindow(collector.native)
            allocation_window.begin()
            result['measured_allocation_window'] = allocation_window.observed
        counters_before = collector.counters()
        python_before = python_telemetry.snapshot()
        logical_update_bytes = 0
        measured_start = time.perf_counter_ns()
        measured_end = phase(options.warmup, options.frames, "measured")
        if isinstance(collector, CandidateCompletions):
            collector.drain_gpu(options.warmup, options.frames, options.timeout,
                                completions=completions, phase="measured")
        else:
            collector.drain_gpu(options.warmup, options.frames, options.timeout,
                                completions=completions, phase='measured')
        if allocation_window is not None and allocation_window.token is not None:
            allocation_window.end()
            allocation_window.observed['boundary'] = dict(begin_after_warm_retirement=True,
                end_after_measured_retirement=True, first_frame=options.warmup, frame_count=options.frames)
        counters_after = collector.counters()
        python_after = python_telemetry.snapshot()
        measured = completions.samples("measured")
        if len(measured) != options.frames:
            raise RuntimeError("measured completion count differs from requested frame count")
        for sample in measured:
            cpu = python_telemetry.frames[int(sample["frame_id"])]
            if cpu["python_update_calls"] != 1 or cpu["python_draw_calls"] != 1:
                raise RuntimeError("actual scene draw/update attribution differs from one per measured frame")
            sample["python_cpu"] = dict(cpu)
        if isinstance(collector, CandidateCompletions) and collector.gpu_metadata.get("enabled"):
            collector.gpu_frames.join(measured)
        if isinstance(collector, CandidateCompletions):
            collector.verify_scope(measured)
        else:
            collector.queries.join(measured)
            collector.verify_pacing(measured, range(options.warmup, options.warmup + options.frames))
            result['opengl_telemetry'] = collector.attribution.metadata()
            result['gpu_telemetry'] = collector.gpu_metadata
        write_json(directory / "samples.json", measured)
        result["samples"] = {"file": "samples.json", "sha256": sha256(directory / "samples.json")}
        result["latency"] = metrics([sample["completion_latency_ns"] for sample in measured])
        result["completed_throughput_fps"] = options.frames * 1e9 / (measured_end - measured_start)
        result["logical_update_bytes"] = logical_update_bytes
        result["logical_update_bandwidth_bytes_per_second"] = logical_update_bytes * 1e9 / (measured_end - measured_start)
        result["counters_before"], result["counters_after"] = counters_before, counters_after
        result["python_counters_before"], result["python_counters_after"] = python_before, python_after
        result["python_counter_delta"] = {key: python_after[key] - value for key, value in python_before.items()}
        if isinstance(collector, CandidateCompletions):
            result.update(native_counter_summary(counters_before, counters_after,
                                                telemetry=collector.telemetry,
                                                backend=result["renderer"].get("backend")))
        else:
            result['counter_delta'] = counter_delta(counters_before, counters_after,
                peaks=collector.telemetry['high_water_marks'], gauges=collector.telemetry['gauges'])
            result['opengl_descriptor_high_water_marks'] = {key:counters_after[key] for key in collector.telemetry['high_water_marks']}
        # High-water marks describe process lifetime. Subtracting two maxima
        # cannot give a measured-window peak, so retain both raw snapshots.
        if options.worker == "candidate":
            delta = result["counter_delta"]
            missing = [key for key in REQUIRED_COUNTERS if key not in delta]
            if missing:
                raise InstrumentationUnavailable(f"required native performance counters absent: {missing}")
        result['measured_work_validation'] = measured_work_gate(result, options.worker,
                                                               update=workload.update != 'resident')
        if result['measured_work_validation']['status'] != 'passed':
            error = '; '.join(result['measured_work_validation']['reasons'])
            if result['measured_work_validation']['status'] == 'unproven':
                raise InstrumentationUnavailable(error)
            raise RuntimeError(error)
        result["instrumentation_gaps"] = ["input-to-visible scanout measurement",
                                          "complete driver/allocator allocation peak accounting"]
        if not collector.gpu_metadata.get("enabled"):
            result["instrumentation_gaps"].append("GPU timestamp query timing")
        if result["python_counter_delta"]["unattributed_draw_calls"]:
            result["instrumentation_gaps"].append("scene draws outside issued-frame attribution")
        if result["python_counter_delta"]["unattributed_glir_parse_calls"]:
            result["instrumentation_gaps"].append("parser work outside issued-frame attribution")
        if isinstance(collector, OpenGLCompletions) and result['counter_delta']['gl_unattributed_presents']:
            result['instrumentation_gaps'].append('upstream presentation signals outside issued-frame ownership')
        if not python_telemetry.paint_methods:
            result["instrumentation_gaps"].append("Python Qt paint callback boundary unavailable")
        if options.worker == "candidate":
            if not collector.boundary.get("whole_qt_paint_scope_verified"):
                result["instrumentation_gaps"].append("native completion/query/counter ownership through final Qt paint submission")
            if any(key not in result["counter_delta"] for key in NATIVE_TIMINGS):
                result["instrumentation_gaps"].append("native compiler/interpretation/upload host timing")
            if result["missing_native_high_water_marks"]:
                result["instrumentation_gaps"].append("native cache/queue/descriptor high-water marks")
            if result["renderer"].get("backend") == "Vulkan":
                try:
                    validate_allocation_window_pair(result.get('measured_allocation_window'), options.warmup, options.frames)
                except (ValueError, TypeError, KeyError):
                    result['instrumentation_gaps'].append('event-level measured Vulkan allocation high-water window')
                if not counters_after.get("vk_memory_available") or any(
                        key not in result["counter_delta"] for key in VULKAN_MEMORY_COUNTERS):
                    result["instrumentation_gaps"].append("actual Vulkan device-memory allocation/free accounting")
                elif not counters_after.get("vk_memory_complete") or any(
                        counters_after.get(key) for key in ("vk_memory_tracking_errors", "vk_memory_retired_allocations")):
                    result["instrumentation_gaps"].append("incomplete Vulkan device-memory ownership tracking")
            if collector.telemetry.get("counter_capture") != "submission":
                result["instrumentation_gaps"].append("submission-frozen per-frame native counters")
        result["status"] = "measured"
    except Exception as error:
        result["status"] = "blocked" if isinstance(error, InstrumentationUnavailable) else "failed"
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
    finally:
        if allocation_window is not None:
            try:
                allocation_window.cancel()
            except Exception as error:
                result['allocation_window_cleanup_error'] = str(error)
                result['status'] = 'failed'
            result['measured_allocation_window'] = copy.deepcopy(allocation_window.observed)
        if reference_attribution is not None:
            result['observed_opengl_counters'] = dict(reference_attribution.totals)
            result['opengl_call_observation'] = reference_attribution.metadata()
        if isinstance(collector, CandidateCompletions) and collector.gpu_frames.observed:
            gpu_samples = collector.gpu_frames.observed
            write_json(directory / "observed-gpu-timings.json", gpu_samples)
            result["observed_gpu_timings"] = {
                "file": "observed-gpu-timings.json", "sha256": sha256(directory / "observed-gpu-timings.json"),
                "scope": "all received warmup/measured maps in arrival order, including rejected batches and failed/partial runs",
            }
        if isinstance(collector, OpenGLCompletions):
            result['surface'] = copy.deepcopy(collector.surface)
            result['presentation_pacing_observations'] = copy.deepcopy(collector.pacing_observer.records) if collector.pacing_observer is not None else []
            write_json(directory / 'observed-opengl-timings.json', collector.queries.observed)
            result['observed_opengl_timings'] = {
                'file':'observed-opengl-timings.json','sha256':sha256(directory/'observed-opengl-timings.json'),
                'scope':'all received upstream scene-context paint timestamps, including partial/failed runs',
            }
            result['pending_opengl_queries'] = copy.deepcopy(collector.queries.pending)
            result['opengl_attribution_errors'] = copy.deepcopy(collector.attribution.errors)
        write_json(directory / "issued-frames.json", completions.issued)
        result["issued_frames"] = {
            "file": "issued-frames.json", "sha256": sha256(directory / "issued-frames.json"),
            "scope": "successfully begun collector frame requests and their owning phases",
        }
        if completions.observed:
            write_json(directory / "observed-samples.json", completions.observed)
            result["observed_samples"] = {
                "file": "observed-samples.json", "sha256": sha256(directory / "observed-samples.json"),
                "scope": "all received warmup/measured receipts in arrival order, including rejected batches and failed/partial runs",
            }
        if python_telemetry is not None:
            python_telemetry.close()
        if isinstance(collector, OpenGLCompletions):
            try:
                canvas.set_current()
                collector.close()
            except Exception as error:
                result['telemetry_shutdown_error'] = str(error)
                result['status'] = 'failed'
        elif reference_attribution is not None:
            reference_attribution.close()
        if canvas is not None:
            try:
                canvas.close()  # shutdown waits are outside measured counters
            except Exception as error:
                result["shutdown_error"] = str(error)
                result["status"] = "failed"
        write_json(directory / "run.json", result)
    return 0 if result["status"] == "measured" else 2


def orchestrate(options):
    import numpy as np
    names = options.workloads or list(CATALOG)
    request = {"schema": 1, "status": "planned", "workloads": [asdict(CATALOG[name]) for name in names],
               "warmup": options.warmup, "frames": options.frames, "repetitions": options.repetitions,
               "queue_depth": options.queue_depth, "vsync": options.vsync,
               "runner_sha256": sha256(__file__), "reference_python": str(options.reference_python.resolve()),
               "candidate_python": str(options.candidate_python.resolve()), "schedule": alternating_schedule(options.repetitions)}
    options.output.mkdir(parents=True, exist_ok=True)
    write_json(options.output / "request.json", request)
    if options.dry_run:
        return 0
    manifest = {"schema": 1, "status": "incomplete", "request_sha256": sha256(options.output / "request.json"), "workloads": {}}
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(QT_API="pyqt6", QT_SCALE_FACTOR="1")
    quality_plan = json.loads(options.quality_plan.read_text()) if options.quality_plan else {}
    plan_base = options.quality_plan.resolve().parent if options.quality_plan else ROOT
    hardware = json.loads(options.hardware.read_text()) if options.hardware else None
    if options.quality_plan:
        manifest["quality_plan_sha256"] = sha256(options.quality_plan)
    if options.hardware:
        manifest["hardware_sha256"] = sha256(options.hardware)
    for name in names:
        runs = {"upstream": [], "candidate": []}
        directories = {"upstream": [], "candidate": []}
        for index, kind in alternating_schedule(options.repetitions):
            directory = (options.output / name / f"{index:02}-{kind}").resolve()
            interpreter = options.reference_python if kind == "upstream" else options.candidate_python
            argv = [str(interpreter.resolve()), str(Path(__file__).resolve()), "--worker", kind,
                    "--workload", name, "--run-index", str(index), "--output", str(directory),
                    "--warmup", str(options.warmup), "--frames", str(options.frames),
                    "--queue-depth", str(options.queue_depth), "--timeout", str(options.timeout)]
            if options.vsync:
                argv.append("--vsync")
            directory.mkdir(parents=True, exist_ok=True)
            # Never reuse stale success evidence if an interpreter fails before
            # producing this run. Child environments import only their installed
            # renderer; the controller imports no VisPy package.
            run_path = directory / "run.json"
            if run_path.exists():
                run_path.unlink()
            try:
                with tempfile.TemporaryDirectory(prefix="vispy-benchmark-") as external_cwd:
                    result = subprocess.run(argv, cwd=external_cwd, env=env, capture_output=True, text=True,
                                            timeout=options.timeout * 3)
                stdout, stderr = result.stdout, result.stderr
                run = json.loads(run_path.read_text()) if run_path.exists() else {"status": "failed", "error": f"worker exited {result.returncode} without evidence"}
                if result.returncode and run.get("status") == "measured":
                    run = {"status": "failed", "error": f"worker exited {result.returncode} despite measured result"}
            except (OSError, subprocess.TimeoutExpired, ValueError) as error:
                stdout, stderr = "", str(error)
                run = {"status": "failed", "error": str(error)}
            (directory / "stdout.txt").write_text(stdout, encoding="utf-8")
            (directory / "stderr.txt").write_text(stderr, encoding="utf-8")
            write_json(run_path, run)
            if kind == 'upstream' and run.get('status') == 'measured':
                try:
                    item = run['observed_samples']
                    path = (directory / item['file']).resolve()
                    if not path.is_relative_to(directory) or sha256(path) != item['sha256']:
                        raise ValueError('actual completed upstream samples file/hash differs')
                    raw_samples = json.loads(path.read_text())
                    if run['warmup_frames'] != options.warmup or run['measured_frames'] != options.frames:
                        raise ValueError('actual upstream sample counts differ from requested run inputs')
                    _pacing.validate_completed_samples(raw_samples, range(options.warmup + options.frames), unpaced=True)
                    run['_release_upstream_completed_samples'] = raw_samples
                except (OSError, ValueError, TypeError, KeyError, _pacing.PacingUnavailable) as error:
                    run['upstream_pacing_admission_error'] = str(error)
                    run.pop('_release_upstream_completed_samples', None)
            runs[kind].append(run)
            directories[kind].append(directory)
            print(name, index, kind, run["status"], flush=True)
        quality = []
        plan = quality_plan.get(name)
        for index, (reference_dir, candidate_dir) in enumerate(zip(directories["upstream"], directories["candidate"])):
            ref_captures = runs["upstream"][index].get("quality_captures", [])
            cand_captures = runs["candidate"][index].get("quality_captures", [])
            if len(ref_captures) != 3 or [item.get("probe_frame") for item in ref_captures] != [item.get("probe_frame") for item in cand_captures]:
                quality.append({"status": "unproven", "reason": "paired initial/update quality captures missing"})
                continue
            for reference, candidate in zip(ref_captures, cand_captures):
                try:
                    edge_file = evidence_path(plan["edge_mask"], plan_base) if plan and plan.get("edge_mask") else None
                    edge_mask = np.load(edge_file, allow_pickle=False) if edge_file else None
                    ref_file, cand_file = reference_dir / reference["file"], candidate_dir / candidate["file"]
                    if sha256(ref_file) != reference["sha256"] or sha256(cand_file) != candidate["sha256"]:
                        raise ValueError("retained quality capture hash differs")
                    comparison = compare_quality(np.load(ref_file, allow_pickle=False), np.load(cand_file, allow_pickle=False),
                                                 edge_mask=edge_mask, exact=bool(plan and plan.get("exact")))
                    comparison.update(run_index=index, probe_frame=reference["probe_frame"])
                    if edge_file:
                        comparison["predeclared_edge_mask_sha256"] = sha256(edge_file)
                    quality.append(comparison)
                except (OSError, ValueError, KeyError) as error:
                    quality.append({"status": "unproven", "reason": str(error)})
        hardware_check = validate_hardware(hardware, runs)
        admission = validate_admission(plan, CATALOG[name], runs["upstream"] + runs["candidate"], plan_base)
        quality_passed = admission["status"] == "passed" and len(quality) == options.repetitions * 3 and all(item["status"] == "passed" for item in quality)
        record = {"runs": runs, "quality": quality,
                  "scientific_admission": admission, "hardware_equivalence": hardware_check,
                  "gate": release_gate(runs["upstream"], runs["candidate"], update=CATALOG[name].update != "resident", quality_passed=quality_passed, same_hardware=hardware_check["status"] == "passed")}
        manifest["workloads"][name] = record
        write_json(options.output / "manifest.json", manifest)
    manifest["status"] = "passed" if all(record["gate"]["status"] == "passed" for record in manifest["workloads"].values()) else "incomplete"
    manifest["scope"] = "selected fixed workloads only; full release requires the complete designated platform matrix"
    write_json(options.output / "manifest.json", manifest)
    return 0 if manifest["status"] == "passed" else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--worker", choices=("upstream", "candidate"), help=argparse.SUPPRESS)
    parser.add_argument("--workload", choices=tuple(CATALOG), help=argparse.SUPPRESS)
    parser.add_argument("--run-index", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--workloads", nargs="+", choices=tuple(CATALOG))
    parser.add_argument("--reference-python", type=Path)
    parser.add_argument("--candidate-python", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/benchmarks")
    parser.add_argument("--quality-plan", type=Path)
    parser.add_argument("--hardware", type=Path)
    parser.add_argument("--warmup", type=int, default=MIN_WARMUP)
    parser.add_argument("--frames", type=int, default=MIN_FRAMES)
    parser.add_argument("--repetitions", type=int, default=MIN_REPETITIONS)
    parser.add_argument("--queue-depth", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--vsync", action="store_true", help="measure paced presentation separately from throughput")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(argv)
    if options.list:
        print(json.dumps([asdict(workload) for workload in CATALOG.values()], indent=2))
        return 0
    if options.warmup < MIN_WARMUP or options.frames < MIN_FRAMES or options.repetitions < MIN_REPETITIONS:
        parser.error("qualification requires >=100 warm frames, >=1000 measured frames, >=5 repetitions")
    if options.queue_depth < 1 or options.queue_depth > 3:
        parser.error("queue depth must be 1..3 for the bounded measurement ring")
    if not math.isfinite(options.timeout) or options.timeout <= 0:
        parser.error("completion timeout must be finite and positive")
    if options.worker:
        if not options.workload:
            parser.error("worker requires one workload")
        return run_worker(options)
    if not options.reference_python or not options.candidate_python:
        parser.error("separate reference and candidate Python executables are required")
    if options.reference_python.resolve() == options.candidate_python.resolve():
        parser.error("reference/candidate interpreters must be independent environments")
    return orchestrate(options)


if __name__ == "__main__":
    raise SystemExit(main())
