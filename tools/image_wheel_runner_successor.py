# SPDX-License-Identifier: AGPL-3.0-only
"""Successor (D30, D31) of tools/image_wheel_runner.py's run_case: the same waited worker launch, of the successor
probe (tools/image_wheel_probe_successor.py), with the 0.10.0 packet as the default reference.

The environments are the retained installed_environment: pass the napari release's runtime as
VISPY_TEST_RUNTIME_REQUIREMENTS.
"""
from __future__ import annotations
import json
from pathlib import Path
import traceback
import uuid
try:
    from . import image_wheel_runner as retained
    from .fixture_image_extensions_successor import CASES
except ImportError:
    import image_wheel_runner as retained
    from fixture_image_extensions_successor import CASES

ROOT=retained.ROOT
installed_environment=retained.installed_environment
run_logged=retained.run_logged
sha=retained.sha
write=retained.write
worker_terminal=retained.worker_terminal


def run_case(name,python,wheel,evidence,environment):
    if name not in CASES:raise ValueError(f'Unknown required scene: {name}')
    evidence=Path(evidence).resolve(strict=True)
    assert not (evidence/'worker-termination-unverified.json').exists(), 'Previous worker termination is unresolved'
    backend=environment.get('VISPY_EXPECTED_BACKEND','Vulkan')
    assert backend in ('Vulkan','Metal')
    repository=Path(environment.get('VISPY_IMAGE_REPOSITORY',ROOT)).resolve(strict=True)
    reference=Path(environment.get('VISPY_IMAGE_REFERENCE',ROOT/'tests/reference/image-extensions-opengl-napari-0.10.0')).resolve(strict=True)
    launch_id=uuid.uuid4().hex
    arguments=[python,'-I','-B',ROOT/'tools/image_wheel_probe_successor.py','--launch-id',launch_id,
        '--case',name,'--repository',repository,'--wheel',Path(wheel).resolve(),
        '--reference',reference,'--output',evidence/name,'--backend',backend]
    if environment.get('VISPY_IMAGE_ALLOW_SOFTWARE')=='1':arguments.append('--allow-software')
    observed=run_logged(arguments,cwd=Path(python).parent,environment=environment,log=evidence/(name+'.stdout.log'))
    observed['launch_id']=launch_id
    report=evidence/name/'result.json'
    observed['report_present']=report.is_file()
    if observed['report_present']:
        observed['report_sha256']=sha(report)
        observed['worker']=json.loads(report.read_bytes())
        try:
            assert observed['worker']['launch_id']==launch_id, 'Worker launch ID differs'
            observed['actual_worker_pid']=observed['worker']['pid']
            observed['actual_worker_terminal']=worker_terminal(observed['worker'],observed['pid'])
            assert observed['actual_worker_terminal']['terminal'], 'Actual worker is not terminal'
        except BaseException:
            observed['worker_admission_error']=traceback.format_exc()
            write(evidence/'worker-termination-unverified.json',observed)
    else:
        write(evidence/'worker-termination-unverified.json',observed)
    write(evidence/(name+'.process.json'),observed)
    return observed
