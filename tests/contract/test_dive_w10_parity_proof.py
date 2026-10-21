"""Guard the actual scoped proof while preserving unresolved whole-host coverage."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_actual_two_child_image_and_export_proof_is_exact_and_scoped():
    proof = json.loads((ROOT / "compat/host-environments/dive-pyside2-candidate-w10-scoped-parity.json").read_text())
    for relative, expected in proof["artifact_hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    assert set(proof["children"]) == {"image", "image_edit"}
    for child in proof["children"].values():
        assert child["process_exit"] == 0 and child["qapplication_destroyed"]
        assert child["renderer"]["backend"] == "Vulkan" and not child["renderer"]["software"]
        assert child["public_parameters_exact"] and all(child["png_bytes_exact"].values())
        assert all(frame["exact"] and frame["file_bytes_exact"] and frame["pixels_differing"] == frame["max_abs"] == 0
                   for frame in child["frames"].values())
    assert proof["protected_native_before"] == proof["protected_native_after"]
    assert proof["scoped_image_export_parity_qualified"]
    assert not proof["ordinary_host_teardown_qualified"]
    assert not proof["scatter_qualified"]
    assert not proof["installed_core_rollback_qualified"]
