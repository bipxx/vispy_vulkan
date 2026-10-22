"""Viewport role, exact window geometry and raw-observation protocol controls."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_corner_training import corner_probes,capture_corner_one
from smooth_line_setup_training import setup_probes,capture_setup_one
from smooth_line_training_provider import capture_one,expected_vertex_upload,validate_commands
from smooth_line_training_commands import expected_batch
from smooth_line_viewport_training import (viewport_probes,viewport_contract,viewport_repeat_indices,
    capture_viewport_one,validate_viewport_state,validate_viewport_commands,read_viewport_row,
    ViewportTrainingBackend,ViewportTrainingSink)
sys.path.pop(0)
from test_smooth_line_training_provider import Backend,Sink,state

PROBE=viewport_probes()[2]


def test_every_viewport_preserves_exact_window_coordinates_and_clip_margin():
    probes=viewport_probes()
    originals={(p.start_units,p.end_units,p.width_units):p for p in training_probes()}
    assert len(probes)==len({p.identity for p in probes})==256
    assert viewport_contract()['baseline_rows']==64 and len(viewport_repeat_indices())==64
    for index,probe in enumerate(probes):
        old=originals[(probe.start_units,probe.end_units,probe.width_units)]
        clip=probe.clip_positions()
        x,y,w,h=probe.viewport
        reconstructed=np.column_stack(((clip[:,0]+1)*(w/2)+x,64-((clip[:,1]+1)*(h/2)+y)))*256
        np.testing.assert_array_equal(reconstructed,[probe.start_units,probe.end_units])
        if index%4==0:
            np.testing.assert_array_equal(clip,old.clip_positions())
        window=np.array([probe.start_units,probe.end_units])/256
        assert np.all(window[:,0]>=x+3) and np.all(window[:,0]<=x+w-3)
        assert np.all(64-window[:,1]>=y+3) and np.all(64-window[:,1]<=y+h-3)


@pytest.mark.parametrize('capture',(capture_one,capture_corner_one,capture_setup_one))
def test_existing_roles_refuse_viewport_subclass_before_backend_access(capture):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError): capture(backend,sink,PROBE,2)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('probe',(training_probes()[0],corner_probes()[0],setup_probes()[0],
    replace(PROBE,identity='new-holdout-role-0'),replace(PROBE,viewport=(0,0,63,64)),
    replace(PROBE,start_units=(0,0))))
def test_other_or_forged_viewport_roles_refuse_before_access(probe):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError): capture_viewport_one(backend,sink,probe,2)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('index',(-1,True,1,256))
def test_wrong_row_refuses_before_access(index):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError): capture_viewport_one(backend,sink,PROBE,index)
    assert not backend.calls and not sink.raw


def test_viewport_state_keeps_raw_record_and_all_other_state_checks():
    original=state();original['viewport']=list(PROBE.viewport)
    held=deepcopy(original)
    validate_viewport_state(original,PROBE,state())
    assert original==held
    for key,value in (('viewport',[0,0,64,64]),('blend',True),('pack_state',[1,0,0,0,0,0,0])):
        changed=dict(original);changed[key]=value
        with pytest.raises(ValueError): validate_viewport_state(changed,PROBE,state())


def backend():
    value=Backend()
    value.before['viewport']=value.after['viewport']=list(PROBE.viewport)
    value.commands[0][3]=expected_vertex_upload(PROBE)
    value.commands.insert(0,['FUNC','glViewport',*PROBE.viewport])
    return value


def test_one_read_and_raw_before_after_state_refusal():
    value,sink=backend(),Sink()
    capture_viewport_one(value,sink,PROBE,2)
    assert value.calls==['prepare','dispatch','observe','read','observe']
    assert len(sink.raw)==1 and sink.accepted==[2]
    value,sink=backend(),Sink()
    value.after['blend']=True
    with pytest.raises(ValueError): capture_viewport_one(value,sink,PROBE,2)
    assert len(sink.raw)==1 and not sink.accepted


def test_complete_commands_require_single_viewport_prefix_and_unchanged_body():
    commands=[['FUNC','glViewport',*PROBE.viewport]]+expected_batch(PROBE,7,5,(8,9))
    validate_viewport_commands(commands,PROBE,7,5,complete=True,initial=True)
    with pytest.raises(ValueError): validate_commands(commands,PROBE,7,5)
    for changed in (commands[1:],commands[:1]+commands,commands+[['FUNC','glViewport',*PROBE.viewport]]):
        with pytest.raises(ValueError): validate_viewport_commands(changed,PROBE,7,5,complete=True,initial=True)


def test_direct_backend_and_sink_recheck_roles():
    value=ViewportTrainingBackend('unused','unused')
    with pytest.raises(ValueError): value.prepare(training_probes()[0])
    sink=ViewportTrainingSink('unused',256)
    with pytest.raises(ValueError): sink.record(0,training_probes()[0],None,None,None,None)
    assert sink.data is None


@pytest.mark.parametrize('identity',(training_probes()[0].identity,setup_probes()[0].identity,'new-holdout-role-0',None))
def test_viewport_reader_refuses_before_filesystem(identity,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('Read before role refusal')
    with monkeypatch.context() as context:
        context.setattr(np,'load',forbidden)
        context.setattr(Path,'stat',forbidden)
        with pytest.raises(ValueError): read_viewport_row('unused',identity)


def test_sink_serializes_selected_raw_rows_and_cleans_owned_temp():
    with tempfile.TemporaryDirectory(prefix='vispy-viewport-sink-control-') as temporary:
        with ViewportTrainingSink(temporary,2,(0,255)) as sink:
            for index in (0,255):
                sink.record(index,viewport_probes()[index],Backend().frame,state(),state(),[])
                sink.accept(index)
        data=np.load(Path(temporary)/'training.rgba.npy',allow_pickle=False)
        assert data.shape==(2,64,64,4) and sink.raw_frames==sink.accepted_frames==2
    assert not Path(temporary).exists()
