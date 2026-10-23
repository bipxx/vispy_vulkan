"""Corner selection/protocol controls with no GL device or saved reference input."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_corner_training import (corner_probes,corner_contract,corner_repeat_indices,
    capture_corner_one,CornerTrainingSink,CornerTrainingBackend,read_corner_row)
from smooth_line_mechanism import training_probes,read_training_row
from smooth_line_training_provider import capture_one,expected_vertex_upload
sys.path.pop(0)
from test_smooth_line_training_provider import Backend,Sink,state

PROBE=corner_probes()[0]


def test_corner_selection_exact_order_roundtrips_and_disjoint_scientific_roles():
    probes=corner_probes()
    assert len(probes)==4096 and len({p.identity for p in probes})==4096
    assert len({(p.start_units,p.end_units,p.width_units) for p in probes})==4096
    assert not {p.identity for p in probes}&{p.identity for p in training_probes()}
    for probe in probes:
        clip=probe.clip_positions()
        reconstructed=np.column_stack(((clip[:,0]+1)*8192,(1-clip[:,1])*8192))
        np.testing.assert_array_equal(reconstructed,[probe.start_units,probe.end_units])
    repeats=corner_repeat_indices()
    assert len(repeats)==64 and repeats[0]==0 and repeats[-1]==4095
    assert corner_contract()['probe_count']==4096


def test_original_capture_still_refuses_a_corner_role_before_backend_access():
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError,match='exact frozen training'):
        capture_one(backend,sink,PROBE,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('probe', [training_probes()[0],replace(PROBE,identity='new-holdout-role-0'),
    replace(PROBE,width_units=832),replace(PROBE,start_units=(0,0)),replace(PROBE,end_units=(1,1))])
def test_foreign_or_forged_corner_role_refuses_before_backend_and_sink(probe):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError,match='exact frozen corner'):
        capture_corner_one(backend,sink,probe,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('index',(-1,True,1,4096))
def test_wrong_corner_row_refuses_before_backend(index):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError,match='canonical order'):
        capture_corner_one(backend,sink,PROBE,index)
    assert not backend.calls and not sink.raw


def test_corner_protocol_reuses_exact_one_read_and_raw_before_acceptance():
    backend,sink=Backend(),Sink()
    backend.commands[0][3]=expected_vertex_upload(PROBE)
    capture_corner_one(backend,sink,PROBE,0)
    assert backend.calls==['prepare','dispatch','observe','read','observe']
    assert len(sink.raw)==1 and sink.accepted==[0]


def test_corner_backend_and_sink_recheck_role_before_their_device_or_file_access():
    backend=CornerTrainingBackend('unused','unused')
    with pytest.raises(ValueError):
        backend.prepare(training_probes()[0])
    sink=CornerTrainingSink('unused-root',4096)
    with pytest.raises(ValueError):
        sink.record(0,training_probes()[0],Backend().frame,state(),state(),[])
    assert sink.data is None


@pytest.mark.parametrize('identity',(training_probes()[0].identity,'new-holdout-role-0','../old.npy',None))
def test_corner_reader_refuses_foreign_roles_before_filesystem(identity,monkeypatch):
    calls=[]
    def forbidden(*args,**kwargs):
        calls.append(args)
        raise AssertionError('Filesystem access before role gate')
    with monkeypatch.context() as context:
        context.setattr(np,'load',forbidden)
        context.setattr(Path,'stat',forbidden)
        context.setattr(Path,'read_bytes',forbidden)
        with pytest.raises(ValueError,match='frozen corner-training'):
            read_corner_row('unused',identity)
    assert calls==[]


def test_original_reader_does_not_admit_new_corner_roles(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Original reader accessed a corner artifact')
    with monkeypatch.context() as context:
        context.setattr(np,'load',forbidden)
        with pytest.raises(ValueError,match='frozen training'):
            read_training_row('unused',PROBE.identity)


def test_corner_sink_keeps_separate_selection_indices_and_raw_bytes():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='vispy-corner-sink-control-') as temporary:
        with CornerTrainingSink(temporary,2,(0,4095)) as sink:
            for index in (0,4095):
                sink.record(index,corner_probes()[index],Backend().frame,state(),state(),[])
                sink.accept(index)
        frames=np.load(Path(temporary)/'training.rgba.npy',allow_pickle=False)
        assert frames.shape==(2,64,64,4) and frames.dtype==np.uint8
        assert sink.raw_frames==sink.accepted_frames==2
    assert not Path(temporary).exists()
