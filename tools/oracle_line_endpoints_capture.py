"""Guarded pinned-upstream original vertex-output capture; preflight has no GL."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

import fixture_line_endpoints as f

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "build/evidence/line-endpoints-authoring-3/authoring.json"
PYTHON = ROOT / "build/oracle-opengl/Scripts/python.exe"
PACKAGE = ROOT / "build/oracle-opengl/Lib/site-packages"
SOURCES = ("tools/fixture_line_endpoints.py", "tests/native/test_line_endpoints.py",
           "tools/oracle_line_endpoints_capture.py")
NODE = "tests/native/test_line_endpoints.py::test_upstream_original_vertex_outputs_match_exact_logical_criteria"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def capture_gpu_observation(records, attempted_cases):
    """An attempted context with no retained proof cannot establish no GPU use."""
    attempted = list(attempted_cases)
    assert len(attempted) == len(set(attempted)) and set(attempted) <= set(f.CASES)
    by_case = {}
    for record in records:
        name = record["case"]
        assert name in attempted and name not in by_case
        value = record.get("GPU_used")
        assert value is None or type(value) is bool
        by_case[name] = record
    unverified = [name for name in attempted
                  if name not in by_case or by_case[name].get("GPU_used") is not True]
    verified = [name for name in attempted
                if name in by_case and by_case[name].get("GPU_used") is True]
    return {"GPU_attempted": bool(attempted),
            "GPU_used": True if verified else None if attempted else False,
            "GPU_use_verified_case_ids": verified,
            "GPU_use_unverified_case_ids": unverified,
            "capture_record_missing_case_ids": [name for name in attempted if name not in by_case],
            "GPU_use_scope": "Actual retained context proof, otherwise unknown; missing crash/cleanup records never establish no GPU use."}


def require_authoring(expected_sha):
    assert expected_sha and sha(AUTHORING) == expected_sha
    author = json.loads(AUTHORING.read_text(encoding="utf-8"))
    assert author["contract"] == f.contract() and author["candidate_seen"] is False
    assert author["GPU_used"] is False and author["native_imported"] is False
    assert len(author["GPU_case_ids"]) == 8 and len(set(author["GPU_case_ids"])) == 8
    assert set(author["GPU_case_ids"]) == {NODE + "[" + name + "]" for name in f.CASES}
    for path, digest in author["sources_sha256"].items():
        assert sha(ROOT / path) == digest, path
    for path, digest in author["protected_input_hashes"].items():
        assert sha(ROOT / path) == digest, path
    return author


def package_inputs():
    """Metadata/source reads only; imports no backend, vispy or OpenGL module."""
    assert Path(sys.executable).resolve() == PYTHON.resolve(), "Use the isolated upstream interpreter"
    requirements_path = ROOT / "tools/oracle_requirements.txt"
    requirements = dict(line.split("==", 1) for line in requirements_path.read_text().splitlines() if line)
    checked, distributions = {requirements_path.relative_to(ROOT).as_posix(): sha(requirements_path)}, {}
    for name, version in requirements.items():
        dist = metadata.distribution(name)
        assert dist.version == version, (name, dist.version, version)
        assert Path(dist.locate_file("")).resolve() == PACKAGE.resolve(), (name, dist.locate_file(""))
        files = {str(path).replace("\\", "/"): Path(dist.locate_file(path)).resolve() for path in dist.files or []}
        identity = {path: sha(target) for path, target in files.items()
                    if ".dist-info/" in path and path.rsplit("/", 1)[-1] in ("METADATA", "WHEEL", "RECORD")}
        assert len(identity) == 3, (name, identity)
        distributions[name] = {"version": version, "origin": str(dist.locate_file("")), "identity_files": identity}
        for path in identity:
            target = files[path]
            checked[target.relative_to(ROOT).as_posix()] = identity[path]
    upstream_manifest = ROOT / "compat/upstream_manifest.json"
    pinned = json.loads(upstream_manifest.read_text(encoding="utf-8"))
    checked[upstream_manifest.relative_to(ROOT).as_posix()] = sha(upstream_manifest)
    for relative in ("gloo/program.py", "gloo/glir.py", "gloo/texture.py", "gloo/buffer.py", "gloo/context.py", "gloo/wrappers.py"):
        target = PACKAGE / "vispy" / relative
        assert sha(target) == pinned["files"][relative]
        checked[target.relative_to(ROOT).as_posix()] = sha(target)
    for relative in ("vispy/__init__.py", "vispy/app/backends/_pyqt6.py", "vispy/app/backends/_qt.py",
                     "OpenGL/raw/GL/VERSION/GL_3_0.py", "OpenGL/raw/GL/VERSION/GL_4_3.py",
                     "OpenGL/GL/VERSION/GL_1_5.py"):
        target = PACKAGE / relative
        checked[target.relative_to(ROOT).as_posix()] = sha(target)
    assert not list((PACKAGE / "vispy").glob("_dawn*")), "Fork extension in upstream package"
    return {"python_executable": str(Path(sys.executable).resolve()), "python_version": platform.python_version(),
            "platform": platform.platform(), "distributions": distributions,
            "package_source_hashes": checked, "native_imported": False, "GPU_used": False}


def capture_case(name, output):
    """One real upstream process and fresh record; no pytest dependency needed."""
    import importlib.abc
    import numpy as np

    class RejectCandidate(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname.startswith("vispy._dawn"):
                raise AssertionError("Candidate native import prohibited in upstream oracle")

    sys.meta_path.insert(0, RejectCandidate())
    folder = output / name
    folder.mkdir(parents=True, exist_ok=False)
    record = {"case": name, "authored_case_nodeid": NODE + "[" + name + "]",
              "execution": "direct isolated rawGL child, not pytest",
              "candidate_seen": False, "GPU_attempted": True, "GPU_used": None}
    vertex, fragment = f.shaders(name)
    (folder / "original.vert").write_text(vertex, encoding="utf-8")
    (folder / "original.frag").write_text(fragment, encoding="utf-8")
    code = 0
    try:
        actual, raw, observations = f.capture_upstream(name, ROOT)
        record.update(observations=observations, GPU_used=True)
        (folder / "actual-TF.bin").write_bytes(raw)
        for label, value in actual.items():
            np.save(folder / (label + ".npy"), value, allow_pickle=False)
        f.assert_outputs(name, actual)
        record["exact_logical_outputs"] = True
    except BaseException as error:
        code = 1
        if getattr(error, "endpoint_raw_tf", None) is not None:
            (folder / "actual-TF.bin").write_bytes(error.endpoint_raw_tf)
        observations = getattr(error, "endpoint_observations", record.get("observations"))
        record.update(error_type=type(error).__name__, error=str(error), observations=observations)
        record["GPU_used"] = True if (observations or {}).get("GPU_used") is True else None
        traceback.print_exc()
    finally:
        record.update(process_exit=code, native_imported=any(n.startswith("vispy._dawn") for n in sys.modules))
        write(folder / "record.json", record)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--capture", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-output", type=Path, required=True)
    parser.add_argument("--expected-authoring-sha256", required=True)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--worker", choices=f.CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    output = args.output.resolve()
    assert output.exists() if args.worker else not output.exists(), "Parent capture output must be fresh"
    assert not args.worker or args.capture
    assert output.is_relative_to(ROOT / "tests/reference"), "New independent references only"
    author = require_authoring(args.expected_authoring_sha256)
    packages = package_inputs()
    protected = {**author["protected_input_hashes"], **author["sources_sha256"],
                 **packages["package_source_hashes"], AUTHORING.relative_to(ROOT).as_posix(): sha(AUTHORING)}
    command = [str(PYTHON), "-B", str(Path(__file__).resolve()), "--capture", "--output", str(output),
               "--preflight-output", str(args.preflight_output.resolve()),
               "--expected-authoring-sha256", args.expected_authoring_sha256,
               "--expected-preflight-sha256", "<actual preflight.json SHA256>"]
    if args.preflight:
        assert not args.expected_preflight_sha256
        args.preflight_output.mkdir(parents=True, exist_ok=False)
        value = {"schema": 1, "status": "ready_for_reserved_upstream_capture", "process_exit": 0,
                 "candidate_seen": False, "GPU_used": False, "native_imported": False,
                 "authoring_sha256": sha(AUTHORING), "helper_sha256": sha(__file__),
                 "output": str(output), "GPU_case_ids": author["GPU_case_ids"],
                 "CPU_cases": len(author["CPU_case_ids"]), "protected_inputs": protected,
                 "packages": packages, "capture_command": command,
                 "scope": "Metadata/source preflight only; original shader compilation, driver output and cleanup remain unadmitted."}
        write(args.preflight_output / "preflight.json", value)
        print(json.dumps({"status": value["status"], "GPU_used": False,
                          "preflight_sha256": sha(args.preflight_output / "preflight.json")}))
        return 0
    preflight_path = args.preflight_output / "preflight.json"
    assert args.expected_preflight_sha256 and sha(preflight_path) == args.expected_preflight_sha256
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    assert preflight["authoring_sha256"] == sha(AUTHORING) and preflight["helper_sha256"] == sha(__file__)
    assert preflight["output"] == str(output) and preflight["protected_inputs"] == protected
    assert preflight["packages"] == packages and preflight["GPU_used"] is False
    assert os.environ.get("QT_QPA_PLATFORM") != "offscreen"
    if args.worker:
        return capture_case(args.worker, output)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "parent-command.json", {"argv": sys.argv, "python": sys.executable,
         "authoring_sha256": sha(AUTHORING), "preflight_sha256": sha(preflight_path), "protected_inputs": protected})
    manifest = {"schema": 1, "kind": "upstream", "candidate_seen": False,
                "authoring_sha256": sha(AUTHORING), "preflight_sha256": sha(preflight_path),
                "packages": packages, "cases": {}, "errors": {}, "protected_inputs_before": protected}
    for name in f.CASES:
        child_command = [str(PYTHON), "-B", "-X", "faulthandler", str(Path(__file__).resolve()), "--capture",
                         "--output", str(output), "--preflight-output", str(args.preflight_output.resolve()),
                         "--expected-authoring-sha256", args.expected_authoring_sha256,
                         "--expected-preflight-sha256", args.expected_preflight_sha256, "--worker", name]
        env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1",
                   QT_API="pyqt6", QT_SCALE_FACTOR="1")
        env.pop("PYTHONPATH", None)
        process = {"command": child_command, "environment": {key: env[key] for key in
                   ("PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "QT_API", "QT_SCALE_FACTOR")}}
        with (output / (name + ".stdout.log")).open("xb") as stdout, (output / (name + ".stderr.log")).open("xb") as stderr:
            child = subprocess.Popen(child_command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
            process["pid"] = child.pid
            write(output / (name + ".command.json"), process)
            print(json.dumps({"case": name, "pid": child.pid, "phase": "running"}), flush=True)
            code = child.wait()
        process["exit_code"] = code
        try:
            assert code == 0
            record = json.loads((output / name / "record.json").read_text(encoding="utf-8"))
            assert record["case"] == name and record["authored_case_nodeid"] == NODE + "[" + name + "]"
            assert record["process_exit"] == 0 and record["native_imported"] is False
            assert record["exact_logical_outputs"] is True and record["GPU_used"] is True
            observations = record["observations"]
            assert observations["native_imported"] is False and observations["owned_resources_cleanup_completed"] is True
            assert observations["primitives_written"] == observations["output_count"]
            assert observations["tail_guard_unchanged"] is True and observations["gl_error"] == 0
            assert sha(output / name / "actual-TF.bin") == observations["raw_sha256"]
            assert Path(observations["package_origin"]).resolve().parent == PACKAGE / "vispy"
            assert all(stage["status"] == 1 for stage in observations["compile"])
            assert len(observations["compile"]) == 2 and observations["link"]["status"] == 1
            vertex, fragment = f.shaders(name)
            assert (output / name / "original.vert").read_text(encoding="utf-8") == vertex
            assert (output / name / "original.frag").read_text(encoding="utf-8") == fragment
            query = observations["TF_queried"]
            queried = f.validate_tf_query(name, query["varyings"], query["stride"], query["mode"])
            raw = (output / name / "actual-TF.bin").read_bytes()
            decoded = f.decode_tf(name, f.validate_tf_bytes(name, raw), queried)
            f.assert_outputs(name, decoded)
            for key, value in decoded.items():
                import numpy as np
                retained = np.load(output / name / (key + ".npy"), allow_pickle=False)
                assert retained.dtype == value.dtype and retained.shape == value.shape
                np.testing.assert_array_equal(retained.view(np.uint32), value.view(np.uint32))
            manifest["cases"][name] = {"process": process, "authored_case_nodeid": record["authored_case_nodeid"],
                                      "record_sha256": sha(output / name / "record.json"),
                                      "admission_scope": f.admission_scope(name)}
        except Exception as error:
            traceback.print_exc()
            manifest["errors"][name] = {"process": process, "type": type(error).__name__, "error": str(error)}
        print(json.dumps({"case": name, "exit_code": code, "admitted": name in manifest["cases"]}), flush=True)
    after = {path: sha(ROOT / path) for path in protected}
    manifest["protected_inputs_after"] = after
    manifest["protected_inputs_unchanged"] = after == protected
    assert not any(name.startswith(("vispy", "OpenGL")) for name in sys.modules)
    write(output / "manifest.json", manifest)
    artifacts = {path.relative_to(output).as_posix(): sha(path) for path in output.rglob("*")
                 if path.is_file() and "pytest-cache" not in path.parts}
    code = int(bool(manifest["errors"]) or len(manifest["cases"]) != 8 or after != protected)
    records = [json.loads((output / name / "record.json").read_text(encoding="utf-8"))
               for name in f.CASES if (output / name / "record.json").exists()]
    write(output / "terminal.json", {"process_exit": code, "children_terminal": True,
         **capture_gpu_observation(records, f.CASES),
         "parent_native_imported": False, "admitted": len(manifest["cases"]),
         "unresolved": len(manifest["errors"]), "artifacts": artifacts,
         "protected_inputs_unchanged": after == protected})
    return code


if __name__ == "__main__":
    raise SystemExit(main())
