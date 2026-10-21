"""Origin hashing works on the minimum supported Python without weaker pins."""
import hashlib
import importlib.util
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[2] / "cmake/dependency_origins.py"
spec = importlib.util.spec_from_file_location("dependency_origins_hash_contract", MODULE)
origins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(origins)


@pytest.mark.parametrize("payload", [b"", bytes(range(256)) * 8193], ids=["empty", "binary-multiple-chunks"])
def test_sha256_without_python311_file_digest(tmp_path, monkeypatch, payload):
    monkeypatch.delattr(hashlib, "file_digest", raising=False)
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    assert origins.sha(path) == hashlib.sha256(payload).hexdigest()


def test_changed_origin_reference_remains_rejected(tmp_path, monkeypatch):
    monkeypatch.delattr(hashlib, "file_digest", raising=False)
    path = tmp_path / "context.json"
    payload = b'{"schema": 1}\n'
    path.write_bytes(payload)
    row = {"path": "context.json", "sha256": hashlib.sha256(payload).hexdigest()}
    assert origins.reference(tmp_path, row) == (path, {"schema": 1})
    path.write_bytes(b'{"schema": 2}\n')
    with pytest.raises(origins.OriginError, match="Changed pinned origin input"):
        origins.reference(tmp_path, row)
