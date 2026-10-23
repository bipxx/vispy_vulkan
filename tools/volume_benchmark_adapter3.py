# SPDX-License-Identifier: AGPL-3.0-only
"""Observer-free volume worker accepting an explicitly pinned v6 admission set.

Only admission loading and source provenance change. The original workload,
sampler, paint ownership, counters, parser handoff and release gates remain in
adapter2 and the frozen benchmark. No expose event is ignored or reassigned.
"""
from __future__ import annotations
import argparse
import json
from contextlib import contextmanager
from pathlib import Path
import re
import sys
if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='tools'

# A Windows venv launcher can outlive early argument/import failure. Emit the
# actual interpreter's creation-bound identity before the heavy imports or
# argparse, so the controller can prove termination even without worker-start.
if __name__=='__main__' and '--output' in sys.argv and '--launch-id' in sys.argv:
    from .mesh_layout_process import process_stamp
    output_index=sys.argv.index('--output');launch_index=sys.argv.index('--launch-id')
    if output_index+1<len(sys.argv) and launch_index+1<len(sys.argv):
        bootstrap=Path(sys.argv[output_index+1]).with_suffix('.bootstrap.json')
        stamp=process_stamp()
        with bootstrap.open('x',encoding='utf-8') as stream:
            json.dump(dict(stage='before-admission-argument-parsing',pid=stamp['pid'],process_stamp=stamp,launch_id=sys.argv[launch_index+1]),stream,indent=2)
from . import volume_benchmark_adapter2 as observer_free

base=observer_free.base
bench=observer_free.bench
_observer_free_sources=observer_free.sources

def sources():
    return {**_observer_free_sources(),'tools/volume_benchmark_adapter3.py':bench.sha256(__file__)}

def load_admission(path,name,qualification_sha256):
    """Require the caller's exact v6 manifest and all original schema checks."""
    base.require(not sys.flags.optimize,'Optimized benchmark workers are forbidden')
    base.require(isinstance(qualification_sha256,str) and re.fullmatch('[0-9a-f]{64}',qualification_sha256) is not None,'Explicit lowercase qualification SHA256 required')
    path=Path(path).resolve(strict=True);qualification_path=path.parent/'qualification.json'
    base.require(bench.sha256(qualification_path)==qualification_sha256,'Scientific admission set digest differs')
    qualification=base.json.loads(qualification_path.read_bytes());record=base.json.loads(path.read_bytes())
    base.require(qualification['status']=='PASS_NATIVE59_V6_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS','Expected new v6 scientific admission set')
    base.require(set(qualification['cases'])==set(base.suite.CASES),'Scientific set lacks registered workloads')
    base.require(name in base.suite.CASES and record['workload']==name,'Registered volume admission required')
    base.require(qualification['cases'][name]['admission_sha256']==bench.sha256(path),'Scientific admission receipt differs')
    base.require(record['producer_epoch']=='Native59-v6-private4','Unsupported scientific producer epoch')
    base.require(record['artifacts']['candidate']['wheel_sha256']==qualification['wheel_sha256'],'Scientific set and candidate artifact differ')
    base.require(record['gate_projection']['benchmark_sha256']==bench.sha256(bench.__file__),'Scientific set uses a different frozen benchmark')
    base.require(qualification['measurement_identity_required'] is True,'Actual measured artifact identity must be required')
    gate=bench.validate_admission(dict(scientific_admission=path.name),bench.CATALOG[name],[dict(data_sha256=record['benchmark_data_sha256'])],path.parent)
    base.require(gate['status']=='passed','Scientific admission evidence did not verify')
    return record

@contextmanager
def admission_set(qualification_sha256):
    """Install metadata-only overrides before scene construction; restore on exit."""
    old_load,old_sources=base.load_admission,observer_free.sources
    def selected(path,name):return load_admission(path,name,qualification_sha256)
    base.load_admission,observer_free.sources=selected,sources
    try:yield
    finally:base.load_admission,observer_free.sources=old_load,old_sources

def main(argv=None):
    parser=argparse.ArgumentParser(add_help=False,allow_abbrev=False)
    parser.add_argument('--admission-set-sha256',required=True)
    selected,remaining=parser.parse_known_args(argv)
    with admission_set(selected.admission_set_sha256):return observer_free.main(remaining)

if __name__=='__main__':raise SystemExit(main())
