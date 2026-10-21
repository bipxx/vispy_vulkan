"""Independent future-native full Qt paint gates; CPU authoring uses no GPU.

GPU execution requires an explicit matching full-paint epoch. No synthetic
scope/receipt/query success is substituted when a required feature is absent.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SIZE = (40, 30)
FRAME_IDS = tuple(range(12))
PHASES = {frame_id: "warmup" if frame_id < 4 else "measured" for frame_id in FRAME_IDS}
KINDS = ("clear", "scene", "present_capture", "surface_conversion", "clear", "present_capture", "surface_conversion")
INTERMEDIATE_KINDS = ("clear", "scene", "surface_conversion", "clear", "present_capture", "surface_conversion")
RESIDENT = (
    "completion_waits", "finish_calls", "texture_uploads", "texture_upload_bytes",
    "buffer_uploads", "geometry_upload_bytes", "point_conversion_builds", "point_conversion_bytes",
    "vertex_input_conversion_builds", "vertex_input_conversion_bytes", "pipeline_misses", "portable_shader_misses",
    "shader_normalizations", "shader_parse_calls", "shader_link_calls", "shader_spirv_stages",
    "shader_normalize_ns", "shader_parse_ns", "shader_link_ns", "shader_spirv_ns", "shader_reflect_ns", "shader_cpu_build_ns",
    "texture_conversion_ns", "texture_upload_cpu_ns",
)
QUERY_COUNTERS = ("timestamp_query_sets", "timestamp_resolves", "timestamp_readbacks")
UNSUBMITTED_INDEX = 2 ** 64 - 1
VERT = "attribute vec2 a_position; void main(){gl_Position=vec4(a_position,0.,1.);}"
FRAG = "uniform vec4 u_color; void main(){gl_FragColor=u_color;}"
POSITIONS = np.array([[-1, -1], [1, -1], [-1, 1], [-1, 1], [1, -1], [1, 1]], np.float32)


def contract():
    return {"schema": 3, "size": list(SIZE), "frames": list(FRAME_IDS), "issued_phases": PHASES,
            "event_path": "actual shown Canvas.update -> Qt paintEvent -> public draw callbacks -> existing autoswap -> Qt alpha tail -> existing final present -> native paint close",
            "one_receipt": "one unique receipt per issued frame, unavailable during after-autoswap observer while the real paint remains open, successful only after ownership_closed and ownership_retired",
            "receipt_scope": "qt_paint with positive unique paint_token and actual nonempty submission-frozen counters_captured=True",
            "normal": {"submissions": 2, "presents": 2, "last_present": 1, "scene_draws": 1, "native_draws": 6, "pass_kinds": list(KINDS), "pass_submission_indices": [0, 0, 0, 0, 1, 1, 1]},
            "intermediate": {"submissions": 3, "presents": 2, "last_present": 2, "scene_draws": 1, "native_draws": 5, "pass_kinds": list(INTERMEDIATE_KINDS), "pass_submission_indices": [0, 0, 1, 2, 2, 2]},
            "pass_kinds": list(KINDS), "resident_unchanged_counters": list(RESIDENT),
            "draw_semantics": "one actual public scene DRAW; masked Qt alpha clear remains a semantic clear and adds one physical native draw; initial unmasked clear has a separate load-clear pass and no draw",
            "transient_uniforms": {"bytes_per_paint": 32, "source": "one std140 vec4 u_color plus one std140 vec4 vispy_clear_color, each16bytes; final two submissions retain both owned uniform allocations", "timer": "buffer_upload_cpu_ns includes legitimate transient Uniform upload_buffer calls; preserve raw per-frame/global cost rather than mislabel it resident geometry reupload", "geometry_policy": "buffer_uploads/geometry_upload_bytes and all conversion/compile/wait gates remain exactly unchanged"},
            "disabled_queries": "no allocated query sets/resolves/readbacks or GPU records; ownership and final counters still required",
            "enabled_queries": "actual granted timestamp feature; every declared render/presentation pass pair joined to the same closed paint and both Surface.Present submissions",
            "unsupported_feature": "explicit unresolved required hardware gate; never a skip or synthetic successful GPU map",
            "terminal_cases": ["actual NaN glLineWidth callback error before submission", "explicit matching unpainted request cancellation", "actual device loss after the first autoswap", "genuine surface detachment after the first autoswap before the existing final present"],
            "terminal_scope": "typed failed/cancelled/device_lost rows are retained and rejected as success; logical terminal retirement is not a claim of successful GPU completion",
            "backpressure": "cooperative actual frame_ready scheduler with no finish/WaitAny; bounded pending tickets/queued batches/query owners and FIFO successful frame IDs; actual queued-path coverage remains unqualified unless observed",
            "fifo": "vsync=True requests actual FIFO mode with frame_slots=1; the real Qt paint must admit its own already-reserved unpainted request; this is present-intent/ownership proof, not visible scanout timing",
            "quality": "final solid binary RGB with alpha64 after the real Qt alpha tail; explicit final capture occurs after resident counter assertions",
            "capture_representation": "native read_presented returns raw BGRA uint8 HxWx4; retain raw bytes, then explicitly map channels2,1,0,3 to an owned RGBA array without flipping rows or changing alpha before exact expected_pixels comparison",
            "scope_limits": ["no scanout measurement", "no allocator-residency claim", "no claim that a deferred batch occurred without its actual counter witness", "actual attached Surface.GetCurrentTexture acquisition-fault hardware gate remains OPEN; detachment is a distinct real failure path"],
            "candidate_seen": True, "matching_native28_hardware_seen": True,
            "revision_provenance": "Retained native27 authoring1 and native28 authoring2 failures remain unchanged. Authoring2 compared raw BGRA directly to RGBA despite the established test_early_probe read_presented contract. This variant corrects only that representation mapping, preserves all exact expected frames/payloads and telemetry criteria, and adds independent asymmetric CPU proof. Matching native28 was observed in the failed authoring2 run; this CPU authoring does not qualify a new GPU run.",
            "GPU_used": False}


def expected_pixels(frame_id):
    image = np.zeros((SIZE[1], SIZE[0], 4), np.uint8)
    image[..., 0 if frame_id % 2 else 1] = 255
    image[..., 3] = 64
    return image


def presented_bgra_to_rgba(raw):
    """Map established native BGRA readback to owned RGBA, keeping row order."""
    if (not isinstance(raw, np.ndarray) or raw.dtype != np.uint8 or
            raw.ndim != 3 or raw.shape[2] != 4 or min(raw.shape[:2]) <= 0):
        raise ValueError("native presented capture must be nonempty uint8 HxWx4 BGRA")
    return raw[..., [2, 1, 0, 3]].copy(order="C")


def require_full_paint_api(native):
    required = ("begin_canvas_paint", "end_canvas_paint", "abort_canvas_paint", "benchmark_cancel_frame")
    absent = [name for name in required if not callable(getattr(native, name, None))]
    if absent:
        raise RuntimeError("matching full-paint native epoch required; absent API: " + ", ".join(absent))


def check_success(receipt, before, *, intermediate=False):
    layout = contract()["intermediate" if intermediate else "normal"]
    assert receipt["status"] == "success" and receipt["presented"] is True, receipt
    assert receipt["frame_scope"] == "qt_paint"
    assert type(receipt["paint_token"]) is int and receipt["paint_token"] > 0
    assert receipt["ownership_closed"] is True and receipt["ownership_retired"] is True
    assert receipt["counters_captured"] is True and receipt["counter_capture"] == "submission"
    assert receipt["submission_count"] == layout["submissions"]
    assert receipt["present_count"] == layout["presents"]
    assert receipt["last_present_submission_index"] == layout["last_present"]
    counters = receipt["counters"]
    assert isinstance(counters, dict) and counters
    assert counters["dawn_queue_submits"] - before["dawn_queue_submits"] == layout["submissions"]
    assert counters["application_presents"] - before["application_presents"] == layout["presents"]
    assert counters["draw_calls"] - before["draw_calls"] == layout["scene_draws"]
    assert counters["native_draw_calls"] - before["native_draw_calls"] == layout["native_draws"]
    assert counters["uniform_upload_bytes"] - before["uniform_upload_bytes"] == contract()["transient_uniforms"]["bytes_per_paint"]
    assert counters["buffer_upload_cpu_ns"] >= before["buffer_upload_cpu_ns"]
    assert 0 < receipt["submit_latency_ns"] <= receipt["completion_latency_ns"]
    assert receipt["completion_timestamp_ns"] > receipt["completion_latency_ns"]


def check_timing(timing, receipt, *, intermediate=False):
    layout = contract()["intermediate" if intermediate else "normal"]
    assert timing["status"] == "success" and not timing["error"], timing
    for field in ("frame_id", "frame_scope", "paint_token", "submission_count", "last_present_submission_index"):
        assert timing[field] == receipt[field], field
    assert [item["kind"] for item in timing["passes"]] == layout["pass_kinds"]
    assert [item["submission_index"] for item in timing["passes"]] == layout["pass_submission_indices"]
    for item in timing["passes"]:
        assert 0 <= item["begin_ns"] <= item["end_ns"]
        assert item["elapsed_ns"] == item["end_ns"] - item["begin_ns"]
        quantum = timing["quantization_ns"]
        if quantum:
            assert item["begin_ns"] % quantum == item["end_ns"] % quantum == 0
    assert timing["pass_sum_ns"] == sum(item["elapsed_ns"] for item in timing["passes"])
    assert timing["render_span_ns"] == max(item["end_ns"] for item in timing["passes"]) - min(item["begin_ns"] for item in timing["passes"])


class Evidence:
    """Persist incoming native batches before any admission, including failure."""
    def __init__(self, name):
        base = os.environ.get("VISPY_NATIVE_PAINT_EVIDENCE")
        self.output = (Path(base) if base else ROOT / "build/evidence/native-paint-frames" / uuid.uuid4().hex) / name
        self.output.mkdir(parents=True, exist_ok=False)
        self.value = {"scope": contract(), "issued": [], "events": [], "raw_batches": [], "snapshots": {}, "GPU_used": False}
        self.save()

    def save(self):
        (self.output / "observations.json").write_text(json.dumps(self.value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def event(self, kind, **fields):
        self.value["events"].append(dict(kind=kind, observed_host_ns=time.perf_counter_ns(), **copy.deepcopy(fields)))
        self.save()

    def batch(self, point, receipts, gpu):
        row = {"point": point, "observed_host_ns": time.perf_counter_ns(), "receipts": copy.deepcopy(receipts), "gpu_maps": copy.deepcopy(gpu)}
        self.value["raw_batches"].append(row)
        self.save()


class PaintHarness:
    """Real Qt/public events, with an observer after the existing autoswap."""
    def __init__(self, evidence, *, queries, vsync=False, intermediate=False, frame_slots=None):
        self.evidence, self.canvas = evidence, None
        self.scene_before, self.seen, self.raw_receipts, self.raw_gpu = {}, {}, [], []
        from vispy import _dawn, app, gloo
        from tools.benchmark_frames import CandidateCompletions, FrameCompletionSamples
        require_full_paint_api(_dawn)  # Fail before Canvas creation on old26.
        self.native, self.gloo, self.evidence = _dawn, gloo, evidence
        self.previous_slots = None
        if frame_slots is not None:
            self.previous_slots = int(_dawn.probe()["frame_slots"])
            _dawn.configure_frame_slots(frame_slots)
        self.intermediate, self.requested, self.action, self.cold_draws = intermediate, None, None, 0
        evidence.value["GPU_used"] = True  # Real device/surface creation is attempted below.
        evidence.save()
        self.canvas = app.Canvas(app="pyqt6", size=SIZE, show=False, autoswap=True, vsync=vsync)
        self.canvas.events.draw.ignore_callback_errors = False
        self.canvas_id = int(self.canvas._backend._dawn_canvas_id)
        self.program = gloo.Program(VERT, FRAG)
        self.program["a_position"] = gloo.VertexBuffer(POSITIONS)
        self.program["u_color"] = (0., 1., 0., .125)
        self.canvas.events.draw.connect(self.draw_scene, position="first")
        self.canvas.events.draw.connect(self.after_autoswap, position="last", after="swap_buffers")
        evidence.value.update(GPU_used=True, python_executable=__import__("sys").executable,
                              native_origin=_dawn.__file__, native_sha256=hashlib.sha256(Path(_dawn.__file__).read_bytes()).hexdigest(),
                              vispy_origin=__import__("vispy").__file__)
        self.canvas.show()
        deadline = time.monotonic() + 5
        while not self.cold_draws:
            self.canvas.app.process_events()
            assert time.monotonic() < deadline, "actual shown Qt cold paint did not arrive"
            time.sleep(.001)
        self.canvas.app.process_events()
        _dawn.finish(self.canvas_id)  # Cold setup only, before resident baseline.
        evidence.value["cold_setup"] = {"finish_allowed": True, "probe": dict(_dawn.probe())}
        self.collector = CandidateCompletions(self.canvas)
        self.collector.gpu_metadata = dict(_dawn.benchmark_configure_gpu_timing(self.canvas_id, queries))
        self.completions = FrameCompletionSamples()
        self.surface = dict(_dawn.benchmark_surface_info(self.canvas_id))
        evidence.value.update(surface=self.surface, telemetry=self.collector.telemetry,
                              query_configuration=self.collector.gpu_metadata, device=dict(_dawn.device_info()),
                              requested_frame_slots=frame_slots)
        evidence.save()
        assert self.surface["attached"] and self.surface["vsync_requested"] == vsync
        if vsync:
            assert self.surface["present_mode"] == "fifo"
        assert self.collector.telemetry.get("frame_ownership_scope") == "whole_qt_paint_v1"
        if queries and not self.collector.gpu_metadata["supported"]:
            evidence.value["unresolved_gate"] = "required hardware timestamp feature was not granted; no synthetic successful query admission"
            evidence.save()
            from tools.benchmark_frames import InstrumentationUnavailable
            raise InstrumentationUnavailable(evidence.value["unresolved_gate"])

    def draw_scene(self, event):
        frame_id = self.requested
        if frame_id is None:
            self.cold_draws += 1
            if self.cold_draws > 1:
                return  # Exposures are unmarked, not extra sampled scene draws.
        else:
            self.scene_before[frame_id] = dict(self.native.probe())
            self.seen[frame_id] = self.seen.get(frame_id, 0) + 1
            self.evidence.event("draw", frame_id=frame_id, before=self.scene_before[frame_id], public_event_type=event.type)
            assert self.seen[frame_id] == 1, "one issued update unexpectedly caused multiple sampled scene draws"
            if self.action == "error":
                self.gloo.set_line_width(float("nan"))
                self.canvas.context.flush_commands()  # Actual native validation error.
        self.gloo.set_viewport(0, 0, *SIZE)
        self.gloo.set_state(blend=False, depth_test=False, stencil_test=False, scissor_test=False, cull_face=False)
        self.gloo.clear(color=(0., 0., 0., .25), depth=False, stencil=False)
        self.program["u_color"] = (1., 0., 0., .125) if frame_id is not None and frame_id % 2 else (0., 1., 0., .125)
        self.program.draw("triangles")
        if self.intermediate and frame_id is not None:
            self.native.benchmark_submit_intermediate(self.canvas_id)

    def after_autoswap(self, event):
        if self.requested is None:
            return
        frame_id = self.requested
        receipts, gpu = self.poll_native("inside-paint-after-autoswap")
        self.evidence.event("after-existing-autoswap", frame_id=frame_id, probe=dict(self.native.probe()))
        assert all(row.get("frame_id") != frame_id for row in receipts + gpu), "open Qt paint published its terminal receipt or GPU map"
        if self.action == "loss":
            self.native.lose_device()
            raise RuntimeError("intentional native-paint device loss after autoswap")
        if self.action == "detach":
            self.native.clear_surface(self.canvas_id)
            self.evidence.event("actual-surface-detached", frame_id=frame_id,
                                surface=dict(self.native.benchmark_surface_info(self.canvas_id)))
        # Previous owners may retire during this real callback; retain/admit
        # those rows by their issued phases without losing their drained data.
        if self.action is None:
            self.accept(receipts, gpu)

    def poll_native(self, point):
        self.native.process_events()
        gpu = list(self.native.benchmark_gpu_timings(self.canvas_id))
        receipts = list(self.native.benchmark_completions(self.canvas_id))
        self.raw_receipts.extend(copy.deepcopy(receipts))
        self.raw_gpu.extend(copy.deepcopy(gpu))
        self.evidence.batch(point, receipts, gpu)  # Always before admission.
        return receipts, gpu

    def collect(self, point, phase):
        receipts, gpu = self.poll_native(point)
        self.accept(receipts, gpu)

    def accept(self, receipts, gpu):
        if self.collector.gpu_metadata["enabled"]:
            self.collector.gpu_frames.collect(gpu)
        else:
            assert gpu == [], "timestamps-disabled owner emitted GPU records"
        for phase in ("warmup", "measured"):
            rows = [row for row in receipts if self.completions.issued.get(row.get("frame_id")) == phase]
            self.completions.collect(rows, phase)
        assert all(row.get("frame_id") in self.completions.issued for row in receipts), "unissued raw receipt"

    def issue(self, frame_id, phase, action=None):
        self.evidence.value["issued"].append({"frame_id": frame_id, "phase": phase, "action": action, "request_host_ns": time.perf_counter_ns()})
        self.evidence.save()
        self.collector.begin(frame_id)
        self.completions.begin(frame_id, phase)
        self.requested, self.action = frame_id, action
        self.canvas.update()

    def dispatch(self, frame_id):
        deadline = time.monotonic() + 5
        while frame_id not in self.seen:
            self.canvas.app.process_events()
            assert time.monotonic() < deadline, "actual Qt paint update timed out under nonblocking backpressure"
            time.sleep(.001)
        self.evidence.event("public-process-events-returned", frame_id=frame_id, probe=dict(self.native.probe()))
        self.requested = None

    def close(self):
        try:
            if hasattr(self, "native"):
                self.evidence.value["snapshots"]["before-cleanup"] = dict(self.native.probe())
            self.evidence.value["raw_receipts"] = copy.deepcopy(self.raw_receipts)
            self.evidence.value["raw_gpu_maps"] = copy.deepcopy(self.raw_gpu)
            self.evidence.value["scene_before"] = copy.deepcopy(self.scene_before)
            self.evidence.value["scene_counts"] = copy.deepcopy(self.seen)
            if hasattr(self, "completions"):
                self.evidence.value["issued_phase_ledger"] = dict(self.completions.issued)
                self.evidence.value["admitted_receipts"] = copy.deepcopy(self.completions.results)
                self.evidence.value["observed_receipts"] = copy.deepcopy(self.completions.observed)
                self.evidence.value["observed_gpu_maps"] = copy.deepcopy(self.collector.gpu_frames.observed)
            self.evidence.save()
        finally:
            if self.canvas is not None:
                self.canvas.close()
            if getattr(self, "previous_slots", None) is not None:
                self.native.configure_frame_slots(self.previous_slots)
