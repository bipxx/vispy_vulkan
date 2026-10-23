# SPDX-License-Identifier: AGPL-3.0-only
"""Observer-free measured volume worker; legacy packets remain unchanged."""
from __future__ import annotations
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import traceback

if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='tools'
from . import volume_benchmark_adapter as base
from . import volume_observer_handoff as handoff
from . import volume_geometry_causality as causal
from . import volume_benchmark_geometry2 as geometry
from .mesh_layout_process import process_stamp

bench=base.benchmark
require=base.require
SOURCES=('tools/volume_benchmark_adapter2.py','tools/volume_observer_handoff.py',
         'tools/volume_geometry_causality.py','tools/volume_benchmark_geometry2.py')


def sources():
    return {**base.sources(),**{name:bench.sha256(bench.ROOT/name) for name in SOURCES}}


def scene_identity(canvas):
    from vispy import scene
    views=[node for node in canvas.central_widget.children if isinstance(node,scene.widgets.ViewBox)]
    require(len(views)==1,'One closed benchmark view required')
    children=list(views[0].scene.children)
    volumes=[node for node in children if isinstance(node,scene.visuals.Volume)]
    require(len(volumes)==1 and all(node is volumes[0] or isinstance(node,scene.cameras.BaseCamera) for node in children),
            'One volume and only camera nodes required')
    volume=volumes[0]
    require(volume._vshare.index_buffer is volume._index_buffer,'Volume draw index buffer differs')
    return dict(single_volume_scene=True,visible=bool(volume.visible),view_object=id(views[0]),
        scene_children=sorted((id(node),type(node).__module__,type(node).__name__) for node in children),
        active_camera=id(views[0].camera),volume_object=id(volume),shape=list(volume._vol_shape),
        vertex_object=id(volume._vertices),index_object=id(volume._index_buffer),
        vertex_id=volume._vertices.id,index_id=volume._index_buffer.id,
        last_data_object=id(volume._last_data),last_data_shape=list(volume._last_data.shape),
        last_data_dtype=volume._last_data.dtype.str,need_vertex_update=bool(volume._need_vertex_update),
        physical_size=list(canvas.physical_size))


def measured_work_gate(run,kind,*,admission,expected=None,update=False,directory=None):
    identity=base.science.measurement_identity(admission,run)
    if identity['status']!='passed':return identity
    try:
        require(run['provenance']['kind']==kind and run['provenance']['observer_free_sources_sha256']==sources(),
                'Observer-free worker source/role differs')
        require(run['provenance']['adapter_sources_sha256']==base.sources(),'Legacy source prerequisites differ')
        require(bench.value_sha256(run['workload'])==admission['workload_sha256'],'Actual workload differs')
        if kind=='candidate':base.science.device_cell(run['renderer'])
        else:require(run['renderer']==dict(vendor='NVIDIA Corporation',renderer='NVIDIA GeForce RTX 4090/PCIe/SSE2',
                                         version='4.6.0 NVIDIA 610.88'),'Actual original device differs')
        directory=Path(directory if directory is not None else run['_observer_free_directory']).resolve(strict=True)
        require(run['observer_free_proof']['samples_file']=='samples.json','Measured sample leaf differs')
        require(run['samples']['file']=='samples.json','Run sample leaf differs')
        samples_path=(directory/'samples.json').resolve(strict=True)
        require(samples_path.parent==directory,'Measured sample outside run directory')
        require(bench.sha256(samples_path)==run['samples']['sha256'],'Actual measured samples differ')
        samples=json.loads(samples_path.read_bytes())
        return geometry.validate_run(run,samples,kind=kind,admission=admission,proof=run['observer_free_proof'])
    except (ValueError,KeyError,TypeError,AssertionError,OSError) as error:
        return dict(status='unproven',reasons=[str(error)])


@contextmanager
def worker_adapter(options,wheel,admission):
    held=sources();states=[];boundaries={};source_proof={}
    parser_class=base.ParserObservation
    frozen=bench.PythonFrameTelemetry
    def observer(canvas,ledger):
        method=canvas.context.shared.parser.parse
        function=getattr(method,'__func__',method)
        identity=(function.__module__,function.__qualname__)
        required=('vispy.gloo.glir','GlirParser.parse') if options.worker=='upstream' else ('vispy.gloo.dawn_parser','DawnGlirParser.parse')
        require(identity==required,'Unexpected parser instrumentation in the closed worker')
        state=handoff.Handoff(canvas,ledger)
        state.evidence['pristine_parser_kind']=list(identity)
        states.append(state);return state
    base.ParserObservation=observer
    try:
        with base.worker_adapter(options,wheel,admission):
            old_telemetry,old_provenance,old_gate=bench.PythonFrameTelemetry,bench.package_provenance,bench.measured_work_gate
            def provenance(kind):
                actual=old_provenance(kind)
                actual['observer_free_sources_sha256']=held
                if kind=='upstream':
                    source_proof.update(causal.source_obligations(Path(actual['package']),actual['installed_package_sha256'],options.workload))
                return actual
            def boundary(phase):
                require(len(states)==1,'Unique observer hand-off owner required')
                boundaries[phase]=scene_identity(states[0].canvas)
            def gate(run,kind,*,update=False):
                require(set(boundaries)=={'before','after'},'Measured observer-free boundaries missing')
                run['observer_free_proof']=dict(schema=2,handoff=states[0].snapshot(),scene_before=boundaries['before'],
                    scene_after=boundaries['after'],source_obligations=dict(source_proof),
                    samples_file='samples.json')
                return measured_work_gate(run,kind,admission=admission,update=update,directory=options.output)
            bench.package_provenance=provenance
            bench.PythonFrameTelemetry=handoff.telemetry_class(frozen,lambda:states[0],options.warmup,options.frames,boundary=boundary)
            bench.measured_work_gate=gate
            try:yield
            finally:
                bench.PythonFrameTelemetry,bench.package_provenance,bench.measured_work_gate=old_telemetry,old_provenance,old_gate
    finally:
        base.ParserObservation=parser_class
        require(sources()==held,'Observer-free sources changed during worker')


def run_worker(options,wheel,admission_path):
    require(not options.output.exists(),'Fresh observer-free evidence directory required')
    options.output.mkdir(parents=True)
    receipt=dict(schema=2,launch_id=options.launch_id,pid=os.getpid(),process_stamp=process_stamp(),
        adapter_sources_sha256=base.sources(),observer_free_sources_sha256=sources(),status='started',process_exit=2)
    bench.write_json(options.output/'worker-start.json',receipt)
    code=2
    try:
        admission=base.load_admission(admission_path,options.workload)
        with worker_adapter(options,Path(wheel).resolve(strict=True),admission):code=bench.run_worker(options)
        receipt['status']='measured' if code==0 else 'failed_or_blocked'
    except Exception as error:
        code=2;receipt.update(status='failed',error=str(error),traceback=traceback.format_exc())
    finally:
        receipt['process_exit']=code
        if (options.output/'run.json').exists():receipt['run_sha256']=bench.sha256(options.output/'run.json')
        bench.write_json(options.output/'worker.json',receipt)
    return code


def main(argv=None):
    original=base.run_worker;base.run_worker=run_worker
    try:return base.main(argv)
    finally:base.run_worker=original


if __name__=='__main__':raise SystemExit(main())
