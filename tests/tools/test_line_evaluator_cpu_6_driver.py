"""Pure CPU6 schema/refusal controls; no real ACK, snapshot or build is made."""
import copy
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[2]
DRIVER=ROOT/"build/run_line_evaluator_cpu_6.py"
spec=importlib.util.spec_from_file_location("cpu6_guarded_driver",DRIVER)
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def read(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8-sig"))


class NoGraphics(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("vispy","OpenGL","PyQt","PySide")) or "_dawn" in fullname or "_sdf_cpu" in fullname:
            raise AssertionError("CPU driver guard attempted project/native/graphics import: "+fullname)


@pytest.fixture(autouse=True)
def pure_only(monkeypatch):
    blocker=NoGraphics();sys.meta_path.insert(0,blocker)
    def forbidden(*args,**kwargs):
        raise AssertionError("Pure driver guards must not launch a child/compiler/build")
    monkeypatch.setattr(driver.subprocess,"Popen",forbidden)
    try:
        yield
    finally:
        sys.meta_path.remove(blocker)
        assert "vispy._dawn" not in sys.modules


@pytest.fixture
def context():
    return {"a":read("build/evidence/native-pass-31/activation.json"),
            "h":read("build/evidence/native-pass-31-build-handoff-1/result.json"),
            "m":read("compat/native-epochs/pass31-w17-ownership.json"),
            "f":read("build/evidence/native-pass-31/frozen-inputs.json"),
            "s":read("build/evidence/native-pass-31/status.json"),"native":dict(driver.NATIVE31_PINS)}


@pytest.fixture
def synthetic_record(context):
    # This dictionary is an in-memory unit-test input, not an actual ACK6 or
    # owner announcement. No canonical manifest is created or source captured.
    old=read("build/evidence/line-evaluator-cpu-5/acknowledged-source-manifest.json")
    files=dict(old["source_files"])
    files["cpp/shader/line_evaluator.cpp"]="1"*64
    files["tests/lines/line_evaluator_contract.cpp"]="2"*64
    return {"schema":1,"cpu_revision":6,"baseline":dict(driver.BASELINE_BINDINGS),
            "driver_sha256":hashlib.sha256(DRIVER.read_bytes()).hexdigest(),
            "source_stability_acknowledged":True,"GPU_used":False,"native_imported":False,
            "owners":{name:sorted(files) for name,files in driver.EXPECTED_OWNERS.items()},
            "owner_source_holds":{name:True for name in driver.EXPECTED_OWNERS},"source_files":files,
            "changed_sources":sorted(driver.REQUIRED_REPAIRS),
            "change_authorization":{name:"synthetic schema control only" for name in driver.REQUIRED_REPAIRS}}


def check_ack(record,context):
    return driver.validate_ack(record,context["f"]["source_files"],context["f"]["harness_files"],
                               hashlib.sha256(DRIVER.read_bytes()).hexdigest())


def check_context(context):
    return driver.validate_baseline(*(context[k] for k in ("a","h","m","f","s","native")))


def test_real_terminal31_baseline_is_accepted(context):
    check_context(context)


def test_abstract_schema_accepts_reviewed_two_source_change(synthetic_record,context):
    assert check_ack(synthetic_record,context)==driver.REQUIRED_REPAIRS


def test_optional_authorized_runtime_repair(synthetic_record,context):
    synthetic_record["source_files"]["cpp/runtime.cpp"]="3"*64
    synthetic_record["changed_sources"].append("cpp/runtime.cpp")
    synthetic_record["change_authorization"]["cpp/runtime.cpp"]="synthetic causal review"
    assert check_ack(synthetic_record,context)==driver.ALLOWED_REPAIRS


@pytest.mark.parametrize("key",["schema","cpu_revision","source_stability_acknowledged","GPU_used","native_imported","driver_sha256"])
def test_bad_ack_header_refused(key,synthetic_record,context):
    synthetic_record[key]=True if key in ("schema","cpu_revision","GPU_used","native_imported") else False
    with pytest.raises(ValueError):check_ack(synthetic_record,context)


@pytest.mark.parametrize("key",list(driver.BASELINE_BINDINGS))
def test_wrong_typed_ack_baseline_refused(key,synthetic_record,context):
    synthetic_record["baseline"][key]=True if type(synthetic_record["baseline"][key]) is int else "0"*64
    with pytest.raises(ValueError):check_ack(synthetic_record,context)


@pytest.mark.parametrize("case",["missing-source","foreign-source","wrong-owner","duplicate-owner","missing-owner-hold",
                                 "unheld-owner","integer-owner-hold","missing-repair","unapproved-cmake","unapproved-header",
                                 "wrong-declared-change","missing-review","blank-review","invalid-digest"])
def test_owner_and_change_closure_refused(case,synthetic_record,context):
    r=synthetic_record
    if case=="missing-source":r["source_files"].pop("cpp/runtime.hpp")
    elif case=="foreign-source":r["source_files"]["cpp/foreign.hpp"]="0"*64
    elif case=="wrong-owner":r["owners"]["root"][0]="cpp/foreign.hpp"
    elif case=="duplicate-owner":r["owners"]["root"].append(r["owners"]["root"][0])
    elif case=="missing-owner-hold":r["owner_source_holds"].pop("root")
    elif case=="unheld-owner":r["owner_source_holds"]["root"]=False
    elif case=="integer-owner-hold":r["owner_source_holds"]["root"]=1
    elif case=="missing-repair":r["source_files"]["cpp/shader/line_evaluator.cpp"]=context["f"]["source_files"]["cpp/shader/line_evaluator.cpp"]
    elif case=="unapproved-cmake":r["source_files"]["CMakeLists.txt"]="3"*64
    elif case=="unapproved-header":r["source_files"]["cpp/runtime.hpp"]="3"*64
    elif case=="wrong-declared-change":r["changed_sources"].append("cpp/runtime.cpp")
    elif case=="missing-review":r["change_authorization"].pop("cpp/shader/line_evaluator.cpp")
    elif case=="blank-review":r["change_authorization"]["cpp/shader/line_evaluator.cpp"]=" "
    elif case=="invalid-digest":r["source_files"]["cpp/shader/line_evaluator.cpp"]="ABC"
    with pytest.raises(ValueError):check_ack(r,context)


@pytest.mark.parametrize("case",["old-activation","bool-epoch","bool-process-exit","failed-terminal","private-reader",
                                 "different-native","missing-native","wrong-source-tree","wrong-harness-tree","wrong-sdk",
                                 "missing-source","missing-harness","source-count-bool","harness-count-bool","owners-count-bool",
                                 "missing-ctest","missing-target","missing-binary","overlap-owner","partial-cpu5-archive","wrong-path"])
def test_actual_baseline_refusals(case,context):
    c=context
    if case=="old-activation":c["a"]["epoch"]=30
    elif case=="bool-epoch":c["f"]["epoch"]=True
    elif case=="bool-process-exit":c["h"]["process_exit"]=False
    elif case=="failed-terminal":c["s"]["status"]="failed"
    elif case=="private-reader":c["h"]["sdk_private_tint_reader_enabled"]=True
    elif case=="different-native":c["native"]["src/vispy/_dawn.cp312-win_amd64.pyd"]="0"*64
    elif case=="missing-native":c["native"].pop("src/vispy/VkLayer_vispy_submit.dll")
    elif case=="wrong-source-tree":c["h"]["source_tree_sha256"]="0"*64
    elif case=="wrong-harness-tree":c["f"]["harness_tree_sha256"]="0"*64
    elif case=="wrong-sdk":c["s"]["sdk_manifest_sha256"]="0"*64
    elif case=="missing-source":c["f"]["source_files"].pop(next(iter(c["f"]["source_files"])))
    elif case=="missing-harness":c["f"]["harness_files"].pop(next(iter(c["f"]["harness_files"])))
    elif case=="source-count-bool":c["h"]["source_files_verified"]=True
    elif case=="harness-count-bool":c["h"]["harness_files_verified"]=True
    elif case=="owners-count-bool":c["h"]["owned_source_files_verified"]=True
    elif case=="missing-ctest":c["h"]["ctest_expected_names"].pop()
    elif case=="missing-target":c["m"]["targets"].pop()
    elif case=="missing-binary":c["h"]["all_archived_binary_hashes"].pop(next(iter(c["h"]["all_archived_binary_hashes"])))
    elif case=="overlap-owner":
        name=next(iter(c["m"]["packets"][0]["owned_files"]))
        c["m"]["packets"][1]["owned_files"][name]=c["m"]["packets"][0]["owned_files"][name]
    elif case=="partial-cpu5-archive":c["m"]["packets"][0]["files"].pop(next(iter(c["m"]["packets"][0]["files"])))
    elif case=="wrong-path":c["m"]["paths"]["snapshot"]="build/w16/source"
    with pytest.raises(ValueError):check_context(c)


def test_proof_join_is_required(context):
    context["h"]["proof_input_hashes"]["ctest.xml"]="0"*64
    with pytest.raises(ValueError):check_context(context)


@pytest.mark.parametrize("supplied",["build/line-evaluator-source-ack-5.json","build/evidence/native-pass-31/frozen-inputs.json",
                                    "../line-evaluator-source-ack-6.json"])
def test_historical_or_outside_ack_path_refused(supplied,tmp_path):
    with pytest.raises(ValueError):driver.validate_ack_path(tmp_path,tmp_path/supplied)


@pytest.mark.parametrize("case",["historical","existing-out","existing-work","existing-cache"])
def test_fresh_destination_refusal_preserves_sentinel(case,tmp_path):
    paths=[tmp_path/name for name in ("build/evidence/line-evaluator-cpu-6","build/line-evaluator-cpu-6","build/line-evaluator-cmake-6")]
    if case=="historical":paths[0]=tmp_path/"build/evidence/line-evaluator-cpu-5"
    selected=paths[0 if case in ("historical","existing-out") else 1 if case=="existing-work" else 2]
    selected.mkdir(parents=True);sentinel=selected/"sentinel.bin";sentinel.write_bytes(b"immutable prior output\n")
    before=sentinel.read_bytes()
    with pytest.raises(ValueError):driver.validate_destinations(tmp_path,*paths)
    assert sentinel.read_bytes()==before


@pytest.mark.parametrize("value",[True,None,"0"*63,"G"*64,"A"*64])
def test_explicit_digest_refusals(value):
    with pytest.raises(ValueError):driver.digest(value)


def xml_tree():
    root=ET.Element("testsuite",tests="11",failures="0",errors="0",skipped="0",disabled="0")
    for name in driver.SELECTED_TESTS:ET.SubElement(root,"testcase",classname=name,name=name,status="run")
    return root


@pytest.mark.parametrize("case",["valid","failure-child","suite-skip","case-disabled","root-failure","nested-suite",
                                 "nested-testsuites","wrapped-case","duplicate-case","foreign-class","missing-case",
                                 "not-run","bad-result","case-error"])
def test_strict_selected_xml_admission(case,tmp_path):
    root=xml_tree();first=root[0]
    if case=="failure-child":ET.SubElement(first,"failure")
    elif case=="suite-skip":root.set("skipped","1")
    elif case=="case-disabled":first.set("disabled","true")
    elif case=="root-failure":root.set("failures","1")
    elif case=="nested-suite":ET.SubElement(root,"testsuite",tests="0")
    elif case=="nested-testsuites":ET.SubElement(root,"testsuites")
    elif case=="wrapped-case":root.remove(first);ET.SubElement(root,"wrapper").append(first)
    elif case=="duplicate-case":root.append(copy.deepcopy(first));root.set("tests","12")
    elif case=="foreign-class":first.set("classname","foreign")
    elif case=="missing-case":root.remove(first);root.set("tests","10")
    elif case=="not-run":first.set("status","notrun")
    elif case=="bad-result":first.set("result","incomplete")
    elif case=="case-error":first.set("errors","1")
    path=tmp_path/"ctest.xml";ET.ElementTree(root).write(path,encoding="utf-8",xml_declaration=True)
    if case=="valid":assert driver.strict_ctest(path,driver.SELECTED_TESTS)["executed"]==11
    else:
        with pytest.raises(ValueError):driver.strict_ctest(path,driver.SELECTED_TESTS)


def test_failure_observations_retain_all_executed_cases(tmp_path):
    root=xml_tree();ET.SubElement(root[0],"failure").text="real regression failed"
    path=tmp_path/"ctest.xml";ET.ElementTree(root).write(path)
    observed=driver.ctest_observations(path)
    assert observed["actual_executed_count"]==11
    assert observed["executed_names"]==driver.SELECTED_TESTS
    assert observed["cases"][0]["failed"] is True


def test_real_historical_xml_is_strictly_accepted():
    assert driver.strict_ctest(ROOT/"build/evidence/line-evaluator-cpu-5/ctest.xml",driver.SELECTED_TESTS)["executed"]==11


def test_selected_map_and_no_future_ack():
    parent=read("build/evidence/line-evaluator-cpu-5/inputs.json")["matching_harness_files"]
    frozen=read("build/evidence/native-pass-31/frozen-inputs.json")["harness_files"]
    assert len(parent)==driver.SELECTED_HARNESS_COUNT==1027
    assert all(frozen.get(n)==v for n,v in parent.items())
    assert len(driver.TARGETS)==7 and len(driver.SELECTED_TESTS)==11 and len(driver.EXPECTED_CTESTS)==18
    assert not driver.ACK.exists()
    assert not any(p.exists() for p in (driver.OUT,driver.WORK,driver.CACHE))
