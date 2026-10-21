"""Wheel and editable install keep the vispy distribution, then uninstall cleanly."""

import os
import subprocess
import sys
import tempfile
import hashlib
import json
from pathlib import Path

import pytest
import vispy

ROOT = Path(__file__).resolve().parents[2]


def write_runtime_requirements(target, environment):
    supplied = environment.get("VISPY_TEST_RUNTIME_REQUIREMENTS")
    if supplied:
        source = Path(supplied).resolve(strict=True)
        target.write_bytes(source.read_bytes())
    else:
        subprocess.run(["uv", "export", "--locked", "--no-default-groups", "--no-emit-project", "--output-file", str(target)], cwd=ROOT, env=environment, check=True, stdout=subprocess.DEVNULL)


def test_editable_distribution_identity():
    from importlib.metadata import distribution

    dist = distribution("vispy")
    print("distribution", dist.metadata["Name"])
    print("version", dist.version)
    print("import vispy", vispy.__version__, vispy.__file__)
    assert dist.metadata["Name"].lower() == "vispy"
    assert dist.version == "0.17.0+vulkan.1"
    assert vispy.__version__ == "0.17.0+vulkan.1"
    assert "sys.path overlay" not in (vispy.__file__ or "")


@pytest.mark.wheel
def test_wheel_uninstall_restores_upstream():
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "VISPY_APP_BACKEND", "VISPY_GL_BACKEND"):
        env.pop(name, None)
    supplied_wheel = env.get("VISPY_TEST_WHEEL")
    wheels = [Path(supplied_wheel).resolve()] if supplied_wheel else sorted((ROOT / "dist").glob("vispy-0.17.0+vulkan.1*.whl"))
    assert len(wheels) == 1 and wheels[0].is_file(), "Build the current wheel first or set VISPY_TEST_WHEEL to its absolute path"
    # Each invocation owns a unique environment outside the checkout. It cannot
    # clear another worker's reference environment or accidentally import src.
    with tempfile.TemporaryDirectory(prefix="vispy-wheel-consumer-") as directory:
        consumer = Path(directory).resolve()
        assert not consumer.is_relative_to(ROOT)
        venv = consumer / "venv"
        consumer_python = env.get("VISPY_TEST_PYTHON", sys.executable)
        subprocess.run(["uv", "venv", str(venv), "--python", consumer_python], cwd=consumer, env=env, check=True)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        requirements = consumer / "requirements.txt"
        write_runtime_requirements(requirements, env)
        wheel_digest = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
        with requirements.open("a", encoding="utf-8") as file:
            file.write(f"\nvispy @ {wheels[0].as_uri()} --hash=sha256:{wheel_digest}\n")
        subprocess.run(["uv", "pip", "install", "--python", str(python), "--require-hashes", "--requirements", str(requirements)], cwd=consumer, env=env, check=True)
        probe = subprocess.run([str(python), "-I", str(Path(__file__).with_name("wheel_consumer_probe.py")), str(ROOT)], cwd=consumer, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(probe.stdout)
        subprocess.run(["uv", "pip", "uninstall", "--python", str(python), "vispy"], cwd=consumer, env=env, check=True)
        absent = subprocess.check_output([str(python), "-I", "-c", "import importlib.util; assert importlib.util.find_spec('vispy') is None; print('uninstalled')"], cwd=consumer, env=env, text=True)
        assert absent.strip() == "uninstalled"
        upstream_requirements = consumer / "upstream-requirements.txt"
        write_runtime_requirements(upstream_requirements, env)
        upstream_manifest = json.loads((ROOT / ".github/workflows/upstream-vispy-0.17.0.json").read_text(encoding="utf-8"))
        assert upstream_manifest["version"] == "0.17.0"
        with upstream_requirements.open("a", encoding="utf-8") as file:
            file.write("\nvispy==0.17.0 " + " ".join("--hash=sha256:" + artifact["sha256"] for artifact in upstream_manifest["files"]) + "\n")
        subprocess.run(["uv", "pip", "install", "--python", str(python), "--require-hashes", "--requirements", str(upstream_requirements)], cwd=consumer, env=env, check=True)
        restored = subprocess.check_output([str(python), "-I", "-c", "import pathlib,sys,vispy; assert pathlib.Path(vispy.__file__).is_relative_to(pathlib.Path(sys.prefix)); print(vispy.__version__)"], cwd=consumer, env=env, text=True).strip()
        print("wheel uninstall and upstream reinstall", restored)
        assert restored == "0.17.0"
        # Rollback must be checked even when rendering exposes a runtime defect.
        assert probe.returncode == 0, probe.stdout
        assert "wheel consumer verified" in probe.stdout
