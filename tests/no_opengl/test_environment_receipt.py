"""Environment evidence must fail closed and parse actual OS contracts."""
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from no_opengl.windows_contracts import parse_namespace


def test_api_set_namespace_reads_exact_contract_host_and_empty_mapping():
    name = 'ext-ms-example-l1-1-0'.encode('utf-16-le')
    host = 'example.dll'.encode('utf-16-le')
    data = bytearray(28 + 24 + 20 + len(name) + len(host))
    struct.pack_into('<7I', data, 0, 6, len(data), 0, 1, 28, 0, 0)
    struct.pack_into('<6I', data, 28, 0, 72, len(name), len(name), 52, 1)
    struct.pack_into('<5I', data, 52, 0, 0, 0, 72 + len(name), len(host))
    data[72:72 + len(name)] = name
    data[72 + len(name):] = host
    assert parse_namespace(bytes(data)) == {'ext-ms-example-l1-1-0.dll': [{'alias': '', 'host': 'example.dll'}]}
    struct.pack_into('<I', data, 52 + 16, 0)
    assert parse_namespace(bytes(data))['ext-ms-example-l1-1-0.dll'][0]['host'] == ''


def test_unknown_or_truncated_api_set_schema_never_means_contract_absent():
    with pytest.raises(ValueError):
        parse_namespace(b'')
    data = struct.pack('<7I', 7, 28, 0, 0, 28, 0, 0)
    with pytest.raises(ValueError):
        parse_namespace(data)
    with pytest.raises(ValueError):
        parse_namespace(struct.pack('<7I', 6, 28, 0, 1, 28, 0, 0))


def test_inventory_cannot_pass_when_exact_wheel_is_missing(tmp_path):
    report = tmp_path / 'inventory.json'
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/no_opengl/inventory.py'),
                             '--wheel', str(tmp_path / 'missing.whl'), '--output', str(report)],
                            capture_output=True, text=True)
    value = json.loads(report.read_text())
    assert result.returncode != 0
    assert value['status'] == 'FAILED_INVENTORY'
    assert 'FileNotFoundError' in value['traceback']
