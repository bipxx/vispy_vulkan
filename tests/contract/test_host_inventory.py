"""Host admission metadata and failure contracts; no renderer is initialized."""

import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from tools import host_inventory as inventory


ROOT = Path(__file__).resolve().parents[2]


def archive(tmp_path, name="host/module.py", data=b"import vispy\n", kind=None):
    path = tmp_path / "source.tar.gz"
    with tarfile.open(path, "w:gz") as stream:
        member = tarfile.TarInfo(name)
        if kind:
            member.type = kind
            member.linkname = "../../outside"
            stream.addfile(member)
        else:
            member.size = len(data)
            stream.addfile(member, io.BytesIO(data))
    return path


@pytest.mark.parametrize("name,kind", [
    ("../outside.py", None), ("/outside.py", None),
    ("host/../../outside.py", None), ("C:/outside.py", None),
    ("host\\..\\outside.py", None), ("host/link", tarfile.SYMTYPE),
    ("host/link", tarfile.LNKTYPE),
])
def test_source_extraction_rejects_unsafe_members_before_writing(tmp_path, name, kind):
    path = archive(tmp_path, name, kind=kind)
    target = tmp_path / "extracted"
    with pytest.raises(ValueError):
        inventory.extract_verified(path, target, inventory.sha256(path))
    assert not target.exists()


def test_source_hash_and_existing_source_are_enforced(tmp_path):
    path = archive(tmp_path)
    target = tmp_path / "extracted"
    with pytest.raises(ValueError, match="SHA-256"):
        inventory.extract_verified(path, target, "0" * 64)
    assert not target.exists()
    source = inventory.extract_verified(path, target, inventory.sha256(path))
    assert (source / "module.py").read_bytes() == b"import vispy\n"
    with pytest.raises(FileExistsError):
        inventory.extract_verified(path, target, inventory.sha256(path))


def test_inventory_respects_relative_imports_function_scope_and_importlib_alias(tmp_path):
    (tmp_path / "module.py").write_text(
        "import vispy.scene as scene\n"
        "from .vispy_obj import VispyObj\n"
        "import vispy_other\n"
        "import importlib as _importlib\n"
        "qt = _importlib.import_module('PyQt5.QtCore')\n"
        "def decode():\n"
        "    from PyQt5.QtCore import QByteArray\n"
    )
    result = inventory.scan(tmp_path)
    assert [item["module"] for item in result["vispy_imports"]] == ["vispy.scene"]
    assert result["qt_imports"][0]["scope"] == "decode"
    assert result["dynamic_imports"][0]["call"] == "_importlib.import_module('PyQt5.QtCore')"
    original = result["source"]["sha256"]
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"bytecode")
    assert inventory.scan(tmp_path)["source"]["sha256"] == original
    (tmp_path / "module.py").write_text("import vispy.app\n")
    assert inventory.scan(tmp_path)["source"]["sha256"] != original


def test_missing_host_probe_preserves_error_and_exits_nonzero_outside_checkout(tmp_path):
    lock = tmp_path / "hosts.toml"
    lock.write_text('[phylib]\nimport_probe_modules = ["missing_host_inventory_fixture"]\n'
                    'package_tree_sha256 = "' + "0" * 64 + '"\n')
    output = tmp_path / "evidence/result.json"
    result = subprocess.run([sys.executable, str(ROOT / "tools/host_inventory.py"),
                             "--lock", str(lock), "probe", "--host", "phylib",
                             "--output", str(output)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    record = json.loads(output.read_text())
    assert record["rendering_qualified"] is False
    assert record["modules"] == []
    assert record["errors"][0]["module"] == "missing_host_inventory_fixture"
    assert "ModuleNotFoundError" in record["errors"][0]["traceback"]


@pytest.mark.parametrize("host", inventory.HOSTS)
def test_pinned_host_source_and_environment_evidence_are_consistent(host):
    pin = inventory.read_hosts()[host]
    source = json.loads((ROOT / pin["source_inventory"]).read_text())
    probe = json.loads((ROOT / pin["environment"]["import_inventory"]).read_text())
    assert source["source"]["sha256"] == pin["source_tree_sha256"]
    assert len(source["source"]["files"]) == pin["source_file_count"]
    assert source["declared_dependencies"] == pin["declared_dependencies"]
    assert probe["package_tree_sha256"] == pin["package_tree_sha256"]
    assert [module["name"] for module in probe["modules"]] == pin["import_probe_modules"]
    assert probe["errors"] == []
    assert probe["rendering_qualified"] is False
    assert probe["qualification"] == "import_inventory_only"
    environment = pin["environment"]
    for filename, expected in (
        (pin["source_inventory"], pin["source_inventory_sha256"]),
        (environment["requirements"], environment["requirements_sha256"]),
        (environment["import_inventory"], environment["import_inventory_sha256"]),
    ):
        assert inventory.sha256(ROOT / filename) == expected
    # Hash mode requires an exact version and at least one accepted artifact
    # hash for every runtime requirement, including the source-built exception.
    text = (ROOT / environment["requirements"]).read_text()
    for group in text.replace("\\\n", " ").splitlines():
        if group and not group.startswith(("#", " ", "--")):
            assert "==" in group and "--hash=sha256:" in group


def test_phylib_import_proof_is_cpu_only_and_dive_admission_requires_capture_evidence():
    pins = inventory.read_hosts()
    phylib = pins["phylib"]
    source = json.loads((ROOT / phylib["source_inventory"]).read_text())
    probe = json.loads((ROOT / phylib["environment"]["import_inventory"]).read_text())
    assert source["vispy_imports"] == []
    assert probe["loaded_vispy_modules"] == []
    assert probe["loaded_qt_modules"] == []
    assert phylib["gpu"] is False
    scoped_qt = [item for item in source["qt_imports"]
                 if item["file"].startswith("phylib/") and "/tests/" not in item["file"]]
    assert len(scoped_qt) == 1 and scoped_qt[0]["scope"] == "_decode_qbytearray"
    dive = json.loads((ROOT / "tools/oracle_dive_admission.json").read_text())
    assert dive["candidate_qualification"] == "pending"
    assert dive["commit"] == pins["dive"]["commit"]
    if dive["upstream_qualification"] == "pending":
        assert dive["successful_fixtures"] == []
        assert dive["reference_manifest"] is None
    else:
        # A bounded public screenshot corpus cannot qualify the entire host.
        assert dive["upstream_qualification"] in ("partial", "unresolved")
        assert "arrow" in dive["unresolved_fixtures"]
        reference = ROOT / dive["reference_manifest"]
        assert inventory.sha256(reference) == dive["reference_manifest_sha256"]
        capture = json.loads(reference.read_text())
        assert capture["provenance"]["kind"] == "upstream"
        assert capture["provenance"]["vispy_version"] == "0.17.0"
        assert capture["provenance"]["host_commit"] == dive["commit"]
        assert set(dive["successful_fixtures"]) == set(capture["fixtures"])
        for name, record in capture["fixtures"].items():
            for artifact in [*record["artifacts"].values(), record["capture"]]:
                assert inventory.sha256(reference.parent / artifact["file"]) == artifact["sha256"]
        for name, error in capture["errors"].items():
            assert dive["unresolved_fixtures"][name] == error
