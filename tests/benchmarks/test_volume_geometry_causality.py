# SPDX-License-Identifier: AGPL-3.0-only
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
from tools import volume_geometry_causality as causal
from tools import volume_observer_handoff as handoff

BASE=causal.original
NAME=BASE.suite.CASES[0]
PACKAGE=causal.ROOT/'third_party/parity/vispy/vispy'


@pytest.fixture(scope='module')
def expected():
    directory=causal.ROOT/'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'
    return BASE.load_admission(directory/(NAME+'.json'),NAME)['artifacts']['upstream']['installed_package_sha256']


@pytest.mark.parametrize('name',BASE.suite.CASES)
def test_all_closed_volume_programs_have_source_and_predicted_byte_obligations(expected,name):
    result=causal.source_obligations(PACKAGE,expected,name)
    assert result['status']=='source_obligations_passed'
    assert result['measured_geometry_proven'] is False
    assert len(result['required_runtime_obligations'])==7


@pytest.mark.parametrize('mutation',['writer','cube','cull','shape'])
def test_changed_geometry_dataflow_is_rejected(mutation):
    source=(PACKAGE/'visuals/volume.py').read_text(encoding='utf-8')
    if mutation=='writer':source += '\n' # Insert an extra method inside VolumeVisual.
    if mutation=='writer':source=source.replace('    def _create_vertex_data(self):','    def extra_writer(self):\n        self._vol_shape = (1,1,1)\n\n    def _create_vertex_data(self):')
    if mutation=='cube':source=source.replace('shape[2] - 0.5','shape[2] - 1.5')
    if mutation=='cull':source=source.replace('    def _prepare_draw(self, view):','    def _prepare_draw(self, view):\n        if not self.visible:\n            return False')
    if mutation=='shape':source=source.replace('shape = vol.shape[:3]','shape = vol.shape[1:4]')
    with pytest.raises(ValueError):causal.volume_obligations(source)


@pytest.mark.parametrize('relative',causal.CRITICAL)
def test_every_critical_installed_source_digest_is_required(expected,relative):
    changed=dict(expected);changed['vispy/'+relative]='0'*64
    with pytest.raises(ValueError,match='Installed source differs'):
        causal.source_obligations(PACKAGE,changed,NAME)


class Parser:
    def __init__(self):self.calls=0
    def parse(self,batch):self.calls+=1;return 'parsed'


class Backend:
    def __init__(self,canvas):self.canvas=canvas
    def _vispy_swap_buffers(self):pass
    def paintGL(self):
        self.canvas.draw_visual(None)
        self._vispy_swap_buffers()


class Canvas:
    def __init__(self):
        self.context=SimpleNamespace(shared=SimpleNamespace(parser=Parser()),glir=SimpleNamespace(_shared=SimpleNamespace(_commands=[])))
        self._backend=Backend(self);self.batch=[]
    def draw_visual(self,visual):self.context.shared.parser.parse(self.batch)


def model():
    canvas=Canvas()
    vertices=np.zeros((8,1),dtype=[('f0',np.float32,3)]);indices=np.arange(14,dtype=np.uint32)
    expected={kind:dict(size=array.nbytes,payload=BASE.geometry.array_record(array)) for kind,array in zip(BASE.geometry.BUFFER_TYPES,(vertices,indices))}
    ledger=BASE.geometry.GeometryObservation(expected,frame_limit=3)
    state=handoff.Handoff(canvas,ledger)
    canvas.batch=[['CREATE',9,'VertexBuffer'],['SIZE',9,96],['DATA',9,0,vertices],
                  ['CREATE',13,'IndexBuffer'],['SIZE',13,56],['DATA',13,0,indices]]
    canvas.draw_visual(None);ledger.bind([9,13])
    canvas.batch=[row for row in canvas.batch if row[0]!='CREATE']
    return canvas,ledger,state


def paint(telemetry,canvas,frame):
    telemetry.begin(frame);telemetry.update(lambda current:0,frame);canvas._backend.paintGL()


def test_actual_frozen_telemetry_wraps_pristine_parser_and_observer_is_absent_from_measured_frames():
    canvas,ledger,state=model()
    frozen=BASE.benchmark.PythonFrameTelemetry
    cls=handoff.telemetry_class(frozen,lambda:state,1,2)
    assert cls.begin is frozen.begin
    assert {name for name,value in cls.__dict__.items() if callable(value)}=={'__init__','snapshot'}
    telemetry=cls(canvas)
    try:
        paint(telemetry,canvas,0);telemetry.snapshot()
        calls=state.calls
        assert state.warm_wrapper is None and canvas.context.shared.parser.parse is state.telemetry_parse
        paint(telemetry,canvas,1);paint(telemetry,canvas,2);telemetry.snapshot()
        proof=state.snapshot()
        assert state.calls==calls and proof['evidence']['observer_invocation_delta']==0
        assert proof['evidence']['handoff_parse_calls']==0 and proof['evidence']['handoff_queue_unchanged']
        assert set(proof['warm']['frames'])=={'0'} and not ledger.frames and not ledger.cold
        assert sys.getprofile() is None
    finally:
        telemetry.close();state.close()


@pytest.mark.parametrize('mutation',['parser','invocation'])
def test_any_measured_parser_change_or_observer_call_fails(mutation):
    canvas,ledger,state=model();cls=handoff.telemetry_class(BASE.benchmark.PythonFrameTelemetry,lambda:state,1,2);telemetry=cls(canvas)
    try:
        paint(telemetry,canvas,0);telemetry.snapshot();paint(telemetry,canvas,1);paint(telemetry,canvas,2)
        if mutation=='parser':canvas.context.shared.parser.parse=lambda batch:None
        else:state.calls+=1
        with pytest.raises(ValueError):telemetry.snapshot()
    finally:telemetry.close();state.close()


def test_parse_during_handoff_is_detected_and_partial_wrappers_are_restored():
    canvas,ledger,state=model();frozen=BASE.benchmark.PythonFrameTelemetry
    class Unexpected(frozen):
        def __init__(self,canvas,**kwargs):
            super().__init__(canvas,**kwargs)
            canvas.context.shared.parser.parse([])
    cls=handoff.telemetry_class(Unexpected,lambda:state,1,2)
    with pytest.raises(ValueError,match='hand-off'):cls(canvas)
    assert sys.getprofile() is None
    state.close()


def test_queue_mutation_during_actual_frozen_constructor_handoff_fails():
    canvas,ledger,state=model();frozen=BASE.benchmark.PythonFrameTelemetry
    class Queues(frozen):
        def __init__(self,canvas,**kwargs):
            super().__init__(canvas,**kwargs)
            canvas.context.glir._shared._commands.append(('unexpected',))
    cls=handoff.telemetry_class(Queues,lambda:state,1,2)
    with pytest.raises(ValueError,match='hand-off'):cls(canvas)
    assert sys.getprofile() is None
    state.close()
