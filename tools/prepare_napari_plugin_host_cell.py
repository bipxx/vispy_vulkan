# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare the admitted Windows CPython3.12.8/PyQt6 napari-threedee wheel-pair job."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import urllib.request

UPSTREAM_FILENAME='vispy-0.17.0-cp312-cp312-win_amd64.whl'
UPSTREAM_SHA256='c4862155e735009b1af6aeda45ea94a72e1a375d6086c89273455d66238bb18e'
UPSTREAM_URL='https://files.pythonhosted.org/packages/73/e7/4e79b8c7da4eebea966be0d79e42b12fd0651252c4bb383a74f5b25c4534/vispy-0.17.0-cp312-cp312-win_amd64.whl'
CASES=('handles','selection','translation','miss','retirement')


def prepare(admission, evidence, *, supplied_wheel=None):
    """Return explicit worker environment only for the independently admitted cell."""
    assert admission['host']=='napari_threedee'
    assert admission['cell']==dict(platform='windows',python='3.12.8',binding='pyqt6')
    assert admission['upstream_fixture_status']=='passed' and admission['upstream_cases']==list(CASES)
    assert admission['upstream_wheel']==dict(filename=UPSTREAM_FILENAME,sha256=UPSTREAM_SHA256,url=UPSTREAM_URL)
    assert platform.system()=='Windows' and platform.machine() in ('AMD64','x86_64')
    assert platform.python_version()=='3.12.8'
    evidence=Path(evidence).resolve()
    assert not evidence.exists(), 'Preserve previous host preparation evidence'
    evidence.mkdir(parents=True)
    if supplied_wheel:
        wheel=Path(supplied_wheel).resolve(strict=True)
    else:
        wheel=evidence/UPSTREAM_FILENAME
        with urllib.request.urlopen(UPSTREAM_URL,timeout=60) as response, wheel.open('xb') as stream:
            while chunk:=response.read(1024*1024):stream.write(chunk)
    assert wheel.name==UPSTREAM_FILENAME
    assert hashlib.sha256(wheel.read_bytes()).hexdigest()==UPSTREAM_SHA256, 'Pinned original wheel bytes differ'
    env=dict(VISPY_NAPARI_PLUGIN_UPSTREAM_WHEEL=str(wheel),VISPY_NAPARI_PLUGIN_EVIDENCE=str(evidence/'pair'),
             VISPY_TEST_PYTHON=sys.executable)
    record=dict(schema=1,scope='Upstream host cell preparation only',cell=admission['cell'],
        original_wheel_sha256=UPSTREAM_SHA256,downloaded=supplied_wheel is None,environment=env,
        candidate_qualified=False,release_qualified=False)
    with (evidence/'preparation.json').open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2)
    return env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--github-env',type=Path,required=True)
    parser.add_argument('--upstream-wheel',type=Path)
    args=parser.parse_args()
    wrapped=json.loads(args.admission.read_bytes())
    env=prepare(wrapped['admission'],args.evidence,supplied_wheel=args.upstream_wheel)
    with args.github_env.open('a',encoding='utf-8') as stream:
        for key,value in env.items():
            assert '\n' not in value and '\r' not in value
            stream.write(key+'='+value+'\n')


if __name__=='__main__':main()
