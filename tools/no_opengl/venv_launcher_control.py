"""Real symlink-venv controls for runtime and inventory subprocess launchers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv


def run(root):
    root = Path(root).absolute()
    root.mkdir(parents=True, exist_ok=False)
    env = root / 'env'
    venv.EnvBuilder(with_pip=False, symlinks=True).create(env)
    python = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    query = subprocess.check_output([str(python), '-I', '-B', '-c', 'import sysconfig;print(sysconfig.get_path("purelib"))'], text=True)
    site = Path(query.strip())
    (site / 'launcher_sentinel.py').write_text('VALUE = "venv-only"\n')
    marker, script = root / 'marker.json', root / 'script.py'
    script.write_text('import json,sys,launcher_sentinel\nfrom pathlib import Path\n'
                      + f'Path({str(marker)!r}).write_text(json.dumps(dict(prefix=sys.prefix,value=launcher_sentinel.VALUE)))\n')
    controller = Path(__file__).resolve().parents[1] / 'audit_no_opengl.py'
    runtime = root / 'runtime.json'
    outcome = subprocess.run([sys.executable, '-B', str(controller), 'run', '--python', str(python),
                              '--scenario', 'script', '--script', str(script), '--gates', 'imports', '--output', str(runtime)])
    value = json.loads(marker.read_text())
    assert outcome.returncode == 0 and Path(value['prefix']).resolve() == env.resolve() and value['value'] == 'venv-only'
    # Invalid wheel is intentional: inventory must fail closed, but its actual
    # subprocess must still report the selected venv prefix rather than base.
    wheel = root / 'invalid.whl'
    wheel.write_bytes(b'not a candidate wheel')
    worker = root / 'synthetic-runtime.worker.json'
    worker.write_text(json.dumps(dict(status='PASS_SCENARIO', executable=str(python),
                                     wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(), wheel_members_verified=1)))
    synthetic = root / 'synthetic-runtime.json'
    synthetic.write_text(json.dumps(dict(scenario='script', source_mode=False, worker_report=str(worker),
                                        gates=dict(no_gl_execution='PASS', no_gl_loads='PASS'))))
    receipt = root / 'receipt.json'
    outcome = subprocess.run([sys.executable, '-B', str(controller), 'inventory', '--python', str(python),
                              '--wheel', str(wheel), '--runtime-report', str(synthetic), '--output', str(receipt)])
    result = json.loads(receipt.read_text())
    assert outcome.returncode != 0 and result['gate'] == 'FAIL'
    assert Path(result['inventory_result']['prefix']).resolve() == env.resolve()
    proof = {'status': 'PASS_LAUNCHER_CONTROLS', 'venv_symlink': python.is_symlink(),
             'prefix': str(env), 'runtime_sentinel': value, 'inventory_failed_closed_in_venv': True}
    (root / 'controls.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(run(args.output)['status'])
