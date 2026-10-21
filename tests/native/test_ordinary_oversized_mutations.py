"""Independent future-epoch SIZE/LINK old/new and pending DELETE gates."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import pytest

from tools import fixture_ordinary_oversized_mutations as f

ROOT = Path(__file__).resolve().parents[2]
AUTHORING = ROOT / "build/evidence/ordinary-oversized-mutations-authoring-1/authoring.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _context_header(path, expected, checksum, activation, epoch):
    assert type(epoch) is int and epoch >= 31, "future exact epoch required before native import"
    assert Path(path).resolve() == ROOT / f"build/evidence/native-pass-{epoch}/activation.json", "canonical actual epoch"
    assert len(expected) == 64 and set(expected) <= set("0123456789abcdef")
    assert checksum == expected, "activation substitution"
    assert type(activation.get("epoch")) is int and activation["epoch"] == epoch, "strict exact epoch"


def _activation_before_native():
    raw_epoch = os.environ.get("VISPY_OVERSIZED_MUTATIONS_EPOCH", "")
    assert raw_epoch.isdecimal() and str(int(raw_epoch)) == raw_epoch
    epoch = int(raw_epoch)
    path = Path(os.environ.get("VISPY_OVERSIZED_MUTATIONS_ACTIVATION", "")).resolve()
    expected = os.environ.get("VISPY_OVERSIZED_MUTATIONS_ACTIVATION_SHA256", "")
    assert epoch >= 31 and path == ROOT / f"build/evidence/native-pass-{epoch}/activation.json"
    activation = _read(path)
    _context_header(path, expected, _sha(path), activation, epoch)
    handoff_path = ROOT / f"build/evidence/native-pass-{epoch}-build-handoff-1/result.json"
    expected_handoff = os.environ.get("VISPY_OVERSIZED_MUTATIONS_HANDOFF_SHA256", "")
    assert len(expected_handoff) == 64 and set(expected_handoff) <= set("0123456789abcdef")
    assert _sha(handoff_path) == expected_handoff
    handoff = _read(handoff_path)
    assert handoff["status"] == "passed_read_only_terminal_build_handoff" and type(handoff["process_exit"]) is int and handoff["process_exit"] == 0
    assert handoff["native_binary_hashes"] == activation["activated"]
    assert handoff["source_tree_sha256"] == activation["native_source_tree_sha256"]
    assert handoff["proof_input_hashes"] == activation["proof_input_hashes"]
    for name, digest in activation["proof_input_hashes"].items():
        assert _sha(path.parent / name) == digest
    frozen = _read(path.parent / "frozen-inputs.json")
    assert type(frozen["epoch"]) is int and frozen["epoch"] == epoch
    assert frozen["source_tree_sha256"] == handoff["source_tree_sha256"]
    for name, checksum in activation["activated"].items():
        base = ROOT / ("src/vispy/visuals/text" if name.startswith("_sdf_cpu.") else "src/vispy")
        assert _sha(base / name) == checksum
    return {"epoch": epoch, "path": str(path), "sha256": expected,
            "handoff_sha256": expected_handoff, "activation": activation}


@pytest.mark.parametrize("name", f.CASES)
@pytest.mark.parametrize("mode", f.MODES)
def test_cpu_fixed_pairs_preserve_old_ids_LAST_and_distinguish_new_state(name, mode):
    p = f.plan(name, f.SAMPLE_LIMITS)
    old, new, pair = f.retired.expected_image(p), f.expected_new(p, mode), f.expected_pair(p, mode)
    assert p.target_bytes > 64 * 1024 * 1024
    np.testing.assert_array_equal(pair[12:], old[12:])
    np.testing.assert_array_equal(pair[:12], new[12:])
    assert not np.array_equal(old, new)
    assert not np.array_equal(pair, f.pending.shift_band(new, 12)), "skipped old draw"
    assert not np.array_equal(pair, f.pending.overlay(old, f.pending.shift_band(old, 12))), "ignored mutation"
    for cell in range(4 if name == f.CASES[2] else 1):
        instance = p.instances - 4 + cell if name == f.CASES[2] else 0
        for y in range(6):
            for x in range(8):
                halfplane = 6 * (x + .5) + 8 * (y + .5)
                assert halfplane != 48
                corner = 2 if halfplane < 48 else 5
                vertex = p.visible_first + corner
                row, column = 23 - (4 + y), 4 + 10 * cell + x
                rgb = [255 * (vertex % 2), 255, 255 * (instance % 2 if name == f.CASES[2] else int(vertex >= 16777217)), 255]
                np.testing.assert_array_equal(old[row, column], rgb)
                if mode == "link":
                    np.testing.assert_array_equal(new[row, column], [255 - rgb[0], *rgb[1:]])
                elif name == f.CASES[0]:
                    np.testing.assert_array_equal(new[row, column], [255 - rgb[0], *rgb[1:]])
                else:
                    np.testing.assert_array_equal(new[row, column], [rgb[0], 0, *rgb[2:]])
    assert pair.dtype == np.uint8 and pair.shape == (24, 48, 4) and np.all(pair[..., 3] == 255)


@pytest.mark.parametrize("name", f.CASES)
def test_cpu_resized_active_sources_preserve_original_draw_legality(name):
    p = f.plan(name, f.SAMPLE_LIMITS)
    q = f.resized_plan(p, f.SAMPLE_LIMITS)
    assert q.target_bytes > 64 * 1024 * 1024
    assert q.lanes == p.lanes > f.SAMPLE_LIMITS["max_vertex_buffers"]
    assert q.stride <= f.SAMPLE_LIMITS["max_vertex_buffer_array_stride"]
    assert q.count % 6 == 0
    assert (q.instances % 4 == 0) if name == f.CASES[2] else (q.instances == 1)
    # Every extra draw remains a legal input; its geometric visibility is fixed.
    if name == f.CASES[2]:
        assert q.instances == p.instances + 4 and q.source_rows * 2 == q.instances
        assert f"gl_InstanceID < {p.instances}" in f.vertex_source(p)
    maximum = max(q.target_bytes, q.source_rows * 4)
    with pytest.raises(ValueError):
        f.resized_plan(p, {**f.SAMPLE_LIMITS, "max_buffer_size": maximum - 1})
    with pytest.raises(ValueError):
        f.plan(name, {**f.SAMPLE_LIMITS, "max_vertex_buffer_array_stride": p.stride - 1})


def _all_commands(program, buffers, index):
    queue = program.glir
    for source in [*buffers, index]:
        if source is not None:
            queue.associate(source.glir)
    return queue.clear()


@pytest.mark.parametrize("name", f.CASES)
@pytest.mark.parametrize("mode", f.MODES)
def test_cpu_scaled_unchanged_public_SIZE_DATA_or_LINK_emitters(name, mode):
    from vispy import gloo
    p = f.plan(name, f.SAMPLE_LIMITS, budget=256)
    program, buffers, index = f.make_program(gloo, p)
    _all_commands(program, buffers, index)
    ids = f.source_ids(p, buffers, index)
    expected = f.expected_command_footprint(p, mode, ids, program.id)
    q = f.mutate(program, buffers, index, p, f.SAMPLE_LIMITS, mode)
    commands = _all_commands(program, buffers, index)
    f.assert_mutation_commands([f.pending.command_record(c) for c in commands], expected, mode)
    if mode == "size":
        arrays = f.resized_arrays(p)
        for key, source in ids.items():
            sizes = [c for c in commands if c[:2] == ("SIZE", source)]
            data = [c for c in commands if c[:2] == ("DATA", source)]
            assert len(sizes) == len(data) == 1
            assert sizes[0][2] == expected["SIZE_DATA"][str(source)]["SIZE"]
            assert data[0][2] == 0
            actual = data[0][3].view(arrays[key].dtype).reshape(-1)
            np.testing.assert_array_equal(actual, arrays[key])
            assert actual.dtype == arrays[key].dtype
            old_bytes = p.count * 4 if name == f.CASES[0] else p.source_rows * 4
            assert sizes[0][2] > old_bytes, "actual allocation size changed"
        if name == f.CASES[2]:
            divisors = [getattr(program[f"a_lane{lane}"], "divisor") for lane in range(p.lanes)]
            counts = [program[f"a_lane{lane}"].size for lane in range(p.lanes)]
            assert divisors == [2] * p.lanes and counts == [q.source_rows] * p.lanes
        assert not any(c[0] == "LINK" for c in commands)
    else:
        assert sum(c[:2] == ("LINK", program.id) for c in commands) == 1
        assert sum(c[:2] == ("ATTACH", program.id) for c in commands) == 2
        typed_sources = [c[3] for c in commands if c[0] == "DATA" and isinstance(c[3], str)]
        assert typed_sources == [f.vertex_source(p), f.LINK_FRAGMENT]
        assert not any(c[0] == "SIZE" for c in commands)
    retained_queue = program.glir
    f.delete(program, buffers, index)
    deleted = retained_queue.clear()
    assert {c[1] for c in deleted if c[0] == "DELETE"} == {program.id, *(source.id for source in buffers), *(() if index is None else (index.id,))}


def test_cpu_mutation_command_witness_rejects_foreign_or_wrong_upload_and_LINK():
    expected = {"program": 7, "SIZE_DATA": {"8": {"SIZE": 16, "DATA_offset": 0, "logical_array": {"shape": [4], "sha256": "a" * 64}}}}
    good = [["SIZE", 8, 16], ["DATA", 8, 0, {"shape": [4], "sha256": "a" * 64}]]
    f.assert_mutation_commands(good, expected, "size")
    for wrong in ([["SIZE", 9, 16], good[1]], [["SIZE", 8, 12], good[1]],
        [good[0], ["DATA", 8, 4, good[1][3]]], [good[0], ["DATA", 8, 0, {"shape": [4], "sha256": "b" * 64}]]):
        with pytest.raises(AssertionError):
            f.assert_mutation_commands(wrong, expected, "size")
    linked = {"program": 7, "vertex": "exact vertex", "fragment": "exact fragment"}
    stages = [["CREATE", 9, "VertexShader"], ["DATA", 9, 0, linked["vertex"]], ["ATTACH", 7, 9],
              ["CREATE", 10, "FragmentShader"], ["DATA", 10, 0, linked["fragment"]], ["ATTACH", 7, 10], ["LINK", 7]]
    f.assert_mutation_commands(stages, linked, "link")
    for wrong in (stages[:-1] + [["LINK", 8]], stages[:4] + [["DATA", 10, 0, "wrong fragment"]] + stages[5:], stages[:2] + [["ATTACH", 8, 9]] + stages[3:],
                  [["LINK", 7], *stages[:-1]], [*stages[:-1], ["DELETE", 9], stages[-1]],
                  [*stages[:2], ["DRAW", 7, "triangles", [0, 6], 1], *stages[2:]]):
        with pytest.raises(AssertionError):
            f.assert_mutation_commands(wrong, linked, "link")
    # Stage deletion after LINK preserves the frozen linked image for the DRAW.
    f.assert_mutation_commands([*stages, ["DELETE", 9], ["DELETE", 10], ["DRAW", 7, "triangles", [0, 6], 1]], linked, "link")


def test_cpu_pending_and_execution_counters_reject_skipped_or_submitted_work():
    before = {"pending_draws": 0, "pending_tickets": 0, "queued_frames": 0,
              "draw_calls": 7, "dawn_queue_submits": 11, "retired_tickets": 11, "completion_waits": 0, "finish_calls": 0}
    first, both = {**before, "pending_draws": 2}, {**before, "pending_draws": 3}
    f.assert_pending(before, first, both)
    for key, value in (("pending_draws", 2), ("draw_calls", 8), ("dawn_queue_submits", 12), ("pending_tickets", 1), ("queued_frames", 1), ("completion_waits", 1), ("finish_calls", 1)):
        with pytest.raises(AssertionError):
            f.assert_pending(before, first, {**both, key: value})
    after = {**before, "draw_calls": 9, "dawn_queue_submits": 12, "retired_tickets": 12, "pending_timestamp_frames": 0}
    f.assert_executed(before, after, draws=2)
    for key, value in (("draw_calls", 8), ("dawn_queue_submits", 13), ("retired_tickets", 11), ("pending_draws", 1), ("completion_waits", 1), ("finish_calls", 1)):
        with pytest.raises(AssertionError):
            f.assert_executed(before, {**after, key: value}, draws=2)


def test_cpu_resident_negative_counters_keep_all_costs_and_waits_strict():
    before = {key: 9 for key in f.RESIDENT}
    f.pending.assert_resident(before, dict(before))
    for key in f.RESIDENT:
        with pytest.raises(AssertionError):
            f.pending.assert_resident(before, {**before, key: 10})


def test_cpu_future_context_rejects_old_epoch_unpinned_or_foreign_activation():
    path = ROOT / "build/evidence/native-pass-31/activation.json"
    good = "a" * 64
    _context_header(path, good, good, {"epoch": 31}, 31)
    for target, expected, actual, value, epoch in ((path, good, good, {"epoch": 30}, 30),
        (path, good, good, {"epoch": True}, 31), (path, good, "b" * 64, {"epoch": 31}, 31),
        (path, "", "", {"epoch": 31}, 31), (ROOT / "build/foreign/native-pass-31/activation.json", good, good, {"epoch": 31}, 31)):
        with pytest.raises(AssertionError):
            _context_header(target, expected, actual, value, epoch)


def _retire(native, cid, record):
    deadline = time.monotonic() + 120
    while True:
        native.process_events()
        record.setdefault("raw_completion_batches", []).append(native.benchmark_completions(cid))
        value = dict(native.probe())
        if all(value[key] == 0 for key in ("pending_draws", "pending_tickets", "queued_frames", "pending_timestamp_frames")):
            return value
        assert time.monotonic() < deadline, value
        time.sleep(.001)


class Evidence:
    def __init__(self, name):
        self.folder = Path(os.environ["VISPY_OVERSIZED_MUTATIONS_EVIDENCE"]) / name
        self.folder.mkdir(parents=True, exist_ok=False)
        self.record = {"contract": f.contract(), "GPU_used": False, "images": {}, "filtered_GLIR": []}

    def save(self):
        (self.folder / "records.json").write_text(json.dumps(self.record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def image(self, phase, actual, expected):
        np.save(self.folder / (phase + ".npy"), actual, allow_pickle=False)
        np.save(self.folder / (phase + "-expected.npy"), expected, allow_pickle=False)
        self.record["images"][phase] = {"actual": f.pending.array_record(actual), "expected": f.pending.array_record(expected)}
        self.save()
        np.testing.assert_array_equal(actual, expected)


@pytest.fixture
def hardware(request):
    activation = _activation_before_native()
    authored = _read(AUTHORING)
    assert authored["contract"] == f.contract() and authored["candidate_seen"] is False
    for name, checksum in authored["sources_sha256"].items():
        assert _sha(ROOT / name) == checksum
    from vispy import _dawn as native, app, gloo
    e = Evidence(request.node.name)
    canvas, parser, original_parse = None, None, None
    try:
        assert Path(native.__file__).resolve() == ROOT / "src/vispy/_dawn.cp312-win_amd64.pyd"
        assert _sha(native.__file__) == activation["activation"]["activated"][Path(native.__file__).name]
        canvas = app.Canvas(app="dawn_headless", size=f.SIZE, show=False)
        canvas.set_current()
        cid = canvas._backend._dawn_canvas_id
        device = native.device_info()
        assert device["ok"] is True and device["software"] is False and device["backend"] == "Vulkan" and device["last_vertex_provoking"] is True
        parser = canvas.context.shared.parser
        original_parse = parser.parse
        def observe(commands):
            e.record["filtered_GLIR"].append([f.pending.command_record(c) for c in commands])
            return original_parse(commands)
        parser.parse = observe
        f.pending.configure(gloo, clear=True)
        canvas.context.flush_commands()
        canvas.swap_buffers()
        baseline = _retire(native, cid, e.record)
        e.record.update(GPU_used=True, authoring=authored, activation=activation, device=device,
                        native_origin=native.__file__, native_sha256=_sha(native.__file__), baseline=baseline)
        e.save()
        yield canvas, native, gloo, cid, e
    except BaseException:
        e.record["assertion_traceback"] = traceback.format_exc()
        raise
    finally:
        e.save()
        if parser is not None and original_parse is not None:
            parser.parse = original_parse
        if canvas is not None:
            canvas.close()


def _capture(native, gloo, cid, e, phase, expected):
    before = _retire(native, cid, e.record)
    e.record[phase + "-before-quality-read"] = before
    e.image(phase, gloo.read_pixels((0, 0, *f.SIZE), alpha=True), expected)
    e.record[phase + "-after-quality-read"] = _retire(native, cid, e.record)
    return before


@pytest.mark.gpu
@pytest.mark.parametrize("name", f.CASES)
@pytest.mark.parametrize("mode", f.MODES)
@pytest.mark.parametrize("lifetime", f.LIFETIMES)
def test_SIZE_or_LINK_old_new_oversized_snapshots_and_pending_lifetime(name, mode, lifetime, hardware):
    canvas, native, gloo, cid, e = hardware
    p = f.plan(name, e.record["device"])
    program, buffers, index = f.make_program(gloo, p)
    deleted = False
    try:
        f.draw(canvas, gloo, program, index, p)
        canvas.swap_buffers()
        before = _retire(native, cid, e.record)
        f.draw(canvas, gloo, program, index, p)
        first = dict(native.probe())
        mutation_batch_start = len(e.record["filtered_GLIR"])
        footprint = f.expected_command_footprint(p, mode, f.source_ids(p, buffers, index), program.id)
        q = f.mutate(program, buffers, index, p, e.record["device"], mode)
        f.draw(canvas, gloo, program, index, q, clear=False, band=12)
        both = dict(native.probe())
        mutation_commands = [c for batch in e.record["filtered_GLIR"][mutation_batch_start:] for c in batch]
        f.assert_mutation_commands(mutation_commands, footprint, mode)
        e.record.update(plan=asdict(p), resized_draw_plan=asdict(q), mode=mode, lifetime=lifetime,
                        actual_mutated_sources=footprint, before=before, first_pending=first, both_pending=both)
        f.assert_pending(before, first, both)
        if lifetime == "delete-before-present":
            f.delete(program, buffers, index)
            deleted = True
            canvas.context.flush_commands()
            e.record["deleted_pending"] = dict(native.probe())
            f.assert_pending(before, first, e.record["deleted_pending"])
            assert e.record["deleted_pending"]["live_cpu_buffer_bytes"] - e.record["baseline"]["live_cpu_buffer_bytes"] >= p.target_bytes
        canvas.swap_buffers()
        after = _capture(native, gloo, cid, e, "old-new", f.expected_pair(p, mode))
        f.assert_executed(before, after, draws=2)
        if lifetime == "survivor":
            if mode == "size":
                assert after["vertex_input_conversion_builds"] > before["vertex_input_conversion_builds"]
                assert after["vertex_input_conversion_bytes"] - before["vertex_input_conversion_bytes"] >= q.target_bytes
                assert after["geometry_upload_bytes"] - before["geometry_upload_bytes"] >= q.target_bytes
            warm_before = _retire(native, cid, e.record)
            f.draw(canvas, gloo, program, index, q)
            canvas.swap_buffers()
            warm_after = _retire(native, cid, e.record)
            e.record.update(warm_before=warm_before, warm_after=warm_after)
            f.assert_executed(warm_before, warm_after, draws=1)
            f.pending.assert_resident(warm_before, warm_after)
            _capture(native, gloo, cid, e, "new-retired-resident", f.expected_new(p, mode))
        else:
            released = dict(native.probe())
            e.record["after_retirement_and_registry_collection"] = released
            for key in ("vertex_input_current_entries", "vertex_input_cache_entries", "vertex_input_oversized_entries", "live_cpu_buffer_bytes", "live_buffer_bytes"):
                assert released[key] == e.record["baseline"][key], key
    finally:
        try:
            _retire(native, cid, e.record)
        finally:
            if not deleted:
                f.delete(program, buffers, index)
                canvas.context.flush_commands()
