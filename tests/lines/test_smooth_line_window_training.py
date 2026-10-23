"""Declared correspondence, scientific roles and raw-before-acceptance controls."""
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
from smooth_line_viewport_training import viewport_probes,capture_viewport_one
from smooth_line_training_provider import capture_one,expected_vertex_upload
from smooth_line_window_training import (OFFSETS,window_probes,window_contract,window_repeat_indices,
    window_baseline_pairs,capture_window_one,WindowTrainingBackend,WindowTrainingSink,
    read_window_row,compare_integer_correspondence)
sys.path.pop(0)
from test_smooth_line_training_provider import Backend,Sink,state

PROBE=window_probes()[0]


def test_selection_exact_geometry_offsets_baselines_and_clip_roundtrip():
    probes=window_probes()
    assert len(probes)==len({p.identity for p in probes})==576
    assert window_contract()['probe_count']==576 and window_repeat_indices()==tuple(range(575,-1,-1))
    pairs=window_baseline_pairs()
    assert len(pairs)==64 and len({i for _,i in pairs})==64
    for base,old in pairs:
        reference=training_probes()[old]
        np.testing.assert_array_equal(probes[base].clip_positions(),reference.clip_positions())
        for shift,(x,y) in enumerate(OFFSETS):
            p=probes[base-4+shift]
            assert p.start_units==tuple(v+d*256 for v,d in zip(reference.start_units,(x,y)))
            assert p.end_units==tuple(v+d*256 for v,d in zip(reference.end_units,(x,y)))
            clip=p.clip_positions()
            actual=np.column_stack(((clip[:,0]+1)*8192,(1-clip[:,1])*8192))
            np.testing.assert_array_equal(actual,[p.start_units,p.end_units])


@pytest.mark.parametrize('offset',OFFSETS)
def test_correspondence_reads_declared_pixels_and_keeps_both_raw_frames(offset):
    baseline=np.zeros((64,64,4),np.uint8);baseline[20,25]=[255,255,255,132]
    moved=np.zeros_like(baseline);dx,dy=offset;moved[20+dy,25+dx]=baseline[20,25]
    a,b=baseline.copy(),moved.copy()
    result=compare_integer_correspondence(baseline,moved,offset)
    assert result['differing_pixels']==result['unmatched_baseline_nonclear']==result['unmatched_moved_nonclear']==0
    np.testing.assert_array_equal(a,baseline);np.testing.assert_array_equal(b,moved)
    moved[20+dy,25+dx,3]+=1
    assert compare_integer_correspondence(baseline,moved,offset)['differing_pixels']==1


def test_correspondence_exposes_unmatched_nonclear_pixels():
    baseline=np.zeros((64,64,4),np.uint8);moved=baseline.copy()
    baseline[20,63]=[255,255,255,0];moved[20,0]=[0,0,0,1]
    result=compare_integer_correspondence(baseline,moved,(4,0))
    assert result['unmatched_baseline_nonclear']==result['unmatched_moved_nonclear']==1


@pytest.mark.parametrize('capture',(capture_one,capture_corner_one,capture_setup_one,capture_viewport_one))
def test_old_roles_refuse_window_before_backend(capture):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError):capture(backend,sink,PROBE,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('probe',(training_probes()[0],corner_probes()[0],setup_probes()[0],viewport_probes()[0],
    replace(PROBE,identity='new-holdout-role-0'),replace(PROBE,width_units=384)))
def test_foreign_and_forged_roles_refuse_before_access(probe):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError):capture_window_one(backend,sink,probe,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('index',(-1,True,1,576))
def test_bad_order_refuses_before_access(index):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError):capture_window_one(backend,sink,PROBE,index)
    assert not backend.calls and not sink.raw


def test_protocol_has_one_read_and_raw_before_post_state_refusal():
    backend,sink=Backend(),Sink();backend.commands[0][3]=expected_vertex_upload(PROBE)
    capture_window_one(backend,sink,PROBE,0)
    assert backend.calls==['prepare','dispatch','observe','read','observe'] and sink.accepted==[0]
    backend,sink=Backend(),Sink();backend.commands[0][3]=expected_vertex_upload(PROBE);backend.after['blend']=True
    with pytest.raises(ValueError):capture_window_one(backend,sink,PROBE,0)
    assert len(sink.raw)==1 and not sink.accepted


def test_direct_operations_recheck_role():
    backend=WindowTrainingBackend('unused','unused')
    with pytest.raises(ValueError):backend.prepare(training_probes()[0])
    sink=WindowTrainingSink('unused',576)
    with pytest.raises(ValueError):sink.record(0,training_probes()[0],None,None,None,None)
    assert sink.data is None


@pytest.mark.parametrize('identity',(training_probes()[0].identity,'new-holdout-role-0',None))
def test_reader_refuses_before_filesystem(identity,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('File access before role refusal')
    with monkeypatch.context() as context:
        context.setattr(np,'load',forbidden);context.setattr(Path,'stat',forbidden)
        with pytest.raises(ValueError):read_window_row('unused',identity)


def test_selected_sink_rows_and_owned_temp_cleanup():
    with tempfile.TemporaryDirectory(prefix='vispy-window-sink-control-') as temporary:
        with WindowTrainingSink(temporary,2,(0,575)) as sink:
            for index in (0,575):
                sink.record(index,window_probes()[index],Backend().frame,state(),state(),[]);sink.accept(index)
        assert np.load(Path(temporary)/'training.rgba.npy',allow_pickle=False).shape==(2,64,64,4)
    assert not Path(temporary).exists()
