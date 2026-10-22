# SPDX-License-Identifier: AGPL-3.0-only
"""Observer-free worker integration with the unchanged paired controller."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys
if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='tools'
from . import volume_benchmark_pairs as legacy
from . import volume_benchmark_adapter2 as adapter


def sources():
    return {**adapter.sources(),'tools/volume_benchmark_pairs.py':legacy.bench.sha256(legacy.__file__),
            'tools/volume_benchmark_pairs2.py':legacy.bench.sha256(__file__)}


def release_gate(reference_runs,candidate_runs,*,admission,quality_passed,same_hardware):
    bench=legacy.bench;original=bench.measured_work_gate
    def gate(run,kind,*,update=False):
        return adapter.measured_work_gate(run,kind,admission=admission,update=update)
    bench.measured_work_gate=gate
    try:
        # No gap strings are removed from any run. New workers never install
        # the measured observer, so the old observer reason is not produced.
        return bench.release_gate(reference_runs,candidate_runs,
            update=bench.CATALOG[admission['workload']].update!='resident',
            quality_passed=quality_passed,same_hardware=same_hardware)
    finally:bench.measured_work_gate=original


@contextmanager
def controller(directory=None):
    old_adapter,old_launch,old_sources,old_verify=legacy.adapter,legacy.launch_worker,legacy.sources,legacy.verify_run
    active=[directory]
    proxy=SimpleNamespace(**vars(old_adapter))
    def gate(run,kind,*,admission,expected=None,update=False):
        legacy.require(active[0] is not None,'Observer-free run directory missing')
        run['_observer_free_directory']=str(Path(active[0]).resolve())
        return adapter.measured_work_gate(run,kind,admission=admission,update=update)
    def launch(arguments,**kwargs):
        arguments=list(arguments)
        legacy.require(Path(arguments[3])==legacy.bench.ROOT/'tools/volume_benchmark_adapter.py','Unexpected legacy worker launch target')
        arguments[3]=legacy.bench.ROOT/'tools/volume_benchmark_adapter2.py'
        active[0]=kwargs['directory']
        return old_launch(arguments,**kwargs)
    def verify(directory,*args,**kwargs):
        directory=Path(directory)
        start=legacy.read(directory/'worker-start.json');worker=legacy.read(directory/'worker.json')
        legacy.require(start['observer_free_sources_sha256']==worker['observer_free_sources_sha256']==adapter.sources(),
                       'Observer-free start/finish source identity differs')
        active[0]=directory
        return old_verify(directory,*args,**kwargs)
    proxy.measured_work_gate=gate;proxy.release_gate=release_gate
    legacy.adapter,legacy.launch_worker,legacy.sources,legacy.verify_run=proxy,launch,sources,verify
    try:yield
    finally:legacy.adapter,legacy.launch_worker,legacy.sources,legacy.verify_run=old_adapter,old_launch,old_sources,old_verify


def verify_run(directory,*args,**kwargs):
    with controller(directory):return legacy.verify_run(directory,*args,**kwargs)


def collect(options):
    with controller():return legacy.collect(options)


def main(argv=None):
    with controller():return legacy.main(argv)


if __name__=='__main__':raise SystemExit(main())
