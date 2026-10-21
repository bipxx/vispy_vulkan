"""CPU-only linked-stage and retained-admission guards; no GPU replay."""
import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "build/admit_native_pass_30_ordinary_oversized_pending_2.py"
spec = importlib.util.spec_from_file_location("pending2_offline_stage_admission", PATH)
admit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admit)
VERTEX, FRAGMENT = "exact vertex source", "exact fragment source"


@pytest.fixture(autouse=True)
def native_import_is_forbidden(monkeypatch):
    create = importlib.machinery.ExtensionFileLoader.create_module
    execute = importlib.machinery.ExtensionFileLoader.exec_module
    def checked_create(loader, spec):
        assert not loader.name.startswith(("vispy._dawn", "vispy.visuals.text._sdf_cpu"))
        return create(loader, spec)
    def checked_execute(loader, module):
        assert not loader.name.startswith(("vispy._dawn", "vispy.visuals.text._sdf_cpu"))
        return execute(loader, module)
    monkeypatch.setattr(importlib.machinery.ExtensionFileLoader, "create_module", checked_create)
    monkeypatch.setattr(importlib.machinery.ExtensionFileLoader, "exec_module", checked_execute)
    yield
    assert "vispy._dawn" not in sys.modules


def graph():
    return [
        ["CREATE", 111, "Program"], ["CREATE", 112, "VertexShader"],
        ["DATA", 112, 0, VERTEX], ["ATTACH", 111, 112],
        ["CREATE", 113, "FragmentShader"], ["DATA", 113, 0, FRAGMENT],
        ["ATTACH", 111, 113], ["LINK", 111],
        ["DRAW", 111, "triangles", [3, 6], 1],
    ]


def check(commands):
    return admit.linked_working_draws([commands], VERTEX, FRAGMENT)


def test_actual_stage_order_and_deleted_handles_leave_linked_program_usable():
    commands = graph()
    commands[8:8] = [["DELETE", 112], ["DELETE", 113]]
    value = check(commands)
    assert value["linked_draw_count"] == 1
    row = value["draws"][0]
    assert (row["program"], row["vertex_stage"], row["fragment_stage"]) == (111, 112, 113)
    assert row["vertex_version"] == row["fragment_version"] == 1
    assert row["link_position"] < row["position"]


def test_buffer_data_and_unrelated_uniform_commands_are_not_shader_text():
    commands = graph()
    commands[8:8] = [["CREATE", 114, "VertexBuffer"], ["DATA", 114, 0, {"array": [0, 1]}],
                     ["UNIFORM", 111, "a_size", "float", [3.0]]]
    assert check(commands)["linked_draw_count"] == 1


def test_sources_are_frozen_at_link_until_an_actual_relink():
    commands = graph()
    commands[8:8] = [["DATA", 112, 0, "changed after link"]]
    assert check(commands)["draws"][0]["vertex_version"] == 1
    commands.insert(-1, ["LINK", 111])
    with pytest.raises(ValueError, match="source differs"):
        check(commands)


def test_relink_can_restore_exact_sources_with_new_version():
    commands = graph()
    commands[8:8] = [["DATA", 112, 0, "changed"], ["DATA", 112, 0, VERTEX], ["LINK", 111]]
    assert check(commands)["draws"][0]["vertex_version"] == 3


def test_reused_stage_id_after_link_does_not_replace_frozen_image():
    commands = graph()
    commands[8:8] = [["DELETE", 112], ["CREATE", 112, "VertexShader"], ["DATA", 112, 0, "foreign new generation"]]
    assert check(commands)["draws"][0]["vertex_generation"] == 2


def test_independent_programs_and_batch_boundaries_retain_each_link_identity():
    first, second = graph(), graph()
    for command in second:
        if len(command) > 1:
            command[1] += 1000
        if command[0] == "ATTACH":
            command[2] += 1000
    value = admit.linked_working_draws([first[:5], first[5:], second], VERTEX, FRAGMENT)
    assert value["linked_draw_count"] == 2
    assert [row["program"] for row in value["draws"]] == [111, 1111]
    assert value["draws"][0]["program_generation"] != value["draws"][1]["program_generation"]


BAD = (
    "missing_vertex_data", "missing_fragment_data", "missing_vertex_attach", "missing_fragment_attach",
    "wrong_vertex", "wrong_fragment", "no_link", "deleted_vertex_before_link", "deleted_fragment_before_link",
    "recreated_stage_before_link", "foreign_attach", "foreign_draw", "unlinked_other_program",
    "matching_unattached_stage", "buffer_masquerading_as_stage", "two_vertex_stages", "duplicate_attach",
    "extra_stage", "partial_shader_data", "nontext_shader_data", "empty_shader_data", "bool_object_id",
    "duplicate_live_create", "deleted_program_draw", "deleted_program_recreated_without_link",
    "stage_data_before_create", "shader_data_after_delete", "matching_shaders_command_without_link",
    "empty_draw_inventory", "detached_before_link", "foreign_detach", "malformed_link",
)


@pytest.mark.parametrize("kind", BAD)
def test_rejects_incomplete_foreign_unattached_or_modified_linked_sources(kind):
    commands = graph()
    if kind == "missing_vertex_data": del commands[2]
    elif kind == "missing_fragment_data": del commands[5]
    elif kind == "missing_vertex_attach": del commands[3]
    elif kind == "missing_fragment_attach": del commands[6]
    elif kind == "wrong_vertex": commands[2][3] = "modified source"
    elif kind == "wrong_fragment": commands[5][3] = "modified source"
    elif kind == "no_link": del commands[7]
    elif kind == "deleted_vertex_before_link": commands.insert(7, ["DELETE", 112])
    elif kind == "deleted_fragment_before_link": commands.insert(7, ["DELETE", 113])
    elif kind == "recreated_stage_before_link":
        commands[7:7] = [["DELETE", 112], ["CREATE", 112, "VertexShader"], ["DATA", 112, 0, VERTEX]]
    elif kind == "foreign_attach": commands[3][2] = 999
    elif kind == "foreign_draw": commands[-1][1] = 999
    elif kind == "unlinked_other_program":
        commands.insert(-1, ["CREATE", 999, "Program"]); commands[-1][1] = 999
    elif kind == "matching_unattached_stage":
        commands[3] = ["CREATE", 999, "VertexShader"]
        commands.insert(4, ["DATA", 999, 0, VERTEX])
    elif kind == "buffer_masquerading_as_stage": commands[1][2] = "VertexBuffer"
    elif kind == "two_vertex_stages": commands[4][2] = "VertexShader"
    elif kind == "duplicate_attach": commands.insert(7, ["ATTACH", 111, 112])
    elif kind == "extra_stage":
        commands[7:7] = [["CREATE", 999, "VertexShader"], ["DATA", 999, 0, VERTEX], ["ATTACH", 111, 999]]
    elif kind == "partial_shader_data": commands[2][2] = 1
    elif kind == "nontext_shader_data": commands[2][3] = {"source": VERTEX}
    elif kind == "empty_shader_data": commands[2][3] = ""
    elif kind == "bool_object_id": commands[0][1] = True
    elif kind == "duplicate_live_create": commands.insert(1, ["CREATE", 111, "Program"])
    elif kind == "deleted_program_draw": commands.insert(-1, ["DELETE", 111])
    elif kind == "deleted_program_recreated_without_link":
        commands[-1:-1] = [["DELETE", 111], ["CREATE", 111, "Program"]]
    elif kind == "stage_data_before_create": commands[1], commands[2] = commands[2], commands[1]
    elif kind == "shader_data_after_delete": commands.insert(2, ["DELETE", 112])
    elif kind == "matching_shaders_command_without_link": commands[7] = ["SHADERS", 111, VERTEX, FRAGMENT]
    elif kind == "empty_draw_inventory": commands.pop()
    elif kind == "detached_before_link": commands.insert(7, ["DETACH", 111, 112])
    elif kind == "foreign_detach": commands.insert(7, ["DETACH", 111, 999])
    elif kind == "malformed_link": commands[7].append("extra")
    with pytest.raises(ValueError):
        check(commands)


@pytest.fixture(scope="module")
def actual():
    module = admit.load_wrapper()
    inputs = admit.read(admit.JOB / "inputs.json")
    retired, fixture = module.load_fixtures(inputs["protected_hashes"])
    return module, retired, fixture


@pytest.mark.parametrize("index", range(15))
def test_actual_all_fifteen_case_validators_remain_unchanged_except_shader_predicate(actual, index):
    original, retired, fixture = actual
    module = admit.load_wrapper()
    ledger = {}
    proof = admit.replace_shader_predicate(module, ledger)
    name = module.GPU_NAMES[index]
    folder = admit.JOB / "cases" / name
    records = admit.read(folder / "records.json")
    value = module.validate_case(folder, name, records, retired, fixture)
    assert value["exact_images"] > 0
    assert proof["replacement_count"] == 1 and proof["other_validator_AST_identical"] is True
    if index < 12:
        assert not ledger
    else:
        assert ledger[name]["linked_draw_count"] == (6, 6, 14)[index - 12]


@pytest.mark.parametrize("key", ("vertex_input_conversion_builds", "buffer_uploads", "completion_waits", "finish_calls"))
def test_shader_repair_does_not_relax_resident_no_conversion_upload_or_wait(actual, key):
    _, retired, fixture = actual
    module = admit.load_wrapper()
    admit.replace_shader_predicate(module, {})
    name = module.GPU_NAMES[12]
    folder = admit.JOB / "cases" / name
    records = admit.read(folder / "records.json")
    records["resident-0"]["after_retirement_before_read"][key] += 1
    with pytest.raises(ValueError, match="Resident work changed"):
        module.validate_case(folder, name, records, retired, fixture)


@pytest.mark.parametrize("key", ("draw_calls", "dawn_queue_submits", "retired_tickets"))
def test_shader_repair_still_rejects_skipped_draw_extra_submit_or_missing_retirement(actual, key):
    _, retired, fixture = actual
    module = admit.load_wrapper()
    admit.replace_shader_predicate(module, {})
    name = module.GPU_NAMES[12]
    folder = admit.JOB / "cases" / name
    records = admit.read(folder / "records.json")
    records["cold-A"]["after_retirement_before_read"][key] += 1
    with pytest.raises(ValueError, match="execution witness differs"):
        module.validate_case(folder, name, records, retired, fixture)


def test_shader_repair_preserves_exact_array_record_admission(actual):
    _, retired, fixture = actual
    module = admit.load_wrapper()
    admit.replace_shader_predicate(module, {})
    name = module.GPU_NAMES[12]
    folder = admit.JOB / "cases" / name
    records = admit.read(folder / "records.json")
    records["images"]["cold-A"]["actual"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="artifact identity differs"):
        module.validate_case(folder, name, records, retired, fixture)


@pytest.mark.parametrize("key,extra", (("vertex_input_oversized_entries", 9), ("vertex_input_oversized_bytes", 256 * 1024 * 1024 + 1)))
def test_shader_repair_still_enforces_shared_entry_and_byte_budget(actual, key, extra):
    _, retired, fixture = actual
    module = admit.load_wrapper()
    admit.replace_shader_predicate(module, {})
    name = module.GPU_NAMES[12]
    folder = admit.JOB / "cases" / name
    records = admit.read(folder / "records.json")
    records["cold-A"]["after_retirement_before_read"][key] = records["baseline"][key] + extra
    with pytest.raises(ValueError, match="outside scoped bound"):
        module.validate_case(folder, name, records, retired, fixture)


@pytest.mark.parametrize("mutation", ("child_failed", "child_not_terminal", "unprotected", "second_error", "wrong_error"))
def test_only_original_terminal_successful_child_and_known_outer_shader_failure_are_repairable(mutation):
    value = admit.read(admit.JOB / "terminal.json")
    if mutation == "child_failed": value["child_exit"] = 1
    elif mutation == "child_not_terminal": value["child_terminal"] = False
    elif mutation == "unprotected": value["protected_inputs_unchanged"] = False
    elif mutation == "second_error": value["errors"].append(copy.deepcopy(value["errors"][0]))
    else: value["errors"][0]["traceback"] = "ValueError: different failure\n"
    with pytest.raises(ValueError):
        admit.validate_original_terminal(value)


def test_held_wrapper_and_original_terminal_hashes_are_exact():
    assert admit.sha(admit.WRAPPER) == admit.WRAPPER_SHA
    assert admit.sha(admit.JOB / "terminal.json") == admit.TERMINAL_SHA
    admit.validate_original_terminal(admit.read(admit.JOB / "terminal.json"))


def test_offline_helper_cannot_run_a_child_or_offer_gpu_execution():
    import ast
    parsed = ast.parse(PATH.read_text(encoding="utf-8"))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) and
                   any(alias.name == "subprocess" for alias in n.names) for n in ast.walk(parsed))
    assert not any(isinstance(n, ast.Name) and n.id in ("child_command", "run", "freeze", "pytest_sessionstart")
                   for n in ast.walk(parsed))
