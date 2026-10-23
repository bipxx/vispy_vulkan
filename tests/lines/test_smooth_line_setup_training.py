"""Fine setup selection, geometric invariants and role-before-access controls."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_mechanism import training_probes,read_training_row
from smooth_line_corner_training import corner_probes,capture_corner_one,read_corner_row
from smooth_line_setup_training import (setup_probes,setup_contract,setup_repeat_indices,setup_baseline_pairs,
    capture_setup_one,SetupTrainingBackend,SetupTrainingSink,read_setup_row)
from smooth_line_training_provider import capture_one,expected_vertex_upload
from smooth_line_setup_constraints import directed_infinite_line
sys.path.pop(0)
from test_smooth_line_training_provider import Backend,Sink,state

PROBE=setup_probes()[0]


def test_selection_counts_disjoint_roles_and_exact_baselines():
    probes=setup_probes()
    assert len(probes)==len({p.identity for p in probes})==544
    assert not {p.identity for p in probes}&{p.identity for p in (*training_probes(),*corner_probes())}
    pairs=setup_baseline_pairs()
    assert len(pairs)==32 and len({old for _,old in pairs})==16
    for new,old in pairs:
        p,q=probes[new],training_probes()[old]
        assert (p.start_units,p.end_units,p.width_units)==(q.start_units,q.end_units,q.width_units)
    assert setup_contract()['probe_count']==544
    assert len(setup_repeat_indices())==len(set(setup_repeat_indices()))==64


def test_all_fine_steps_preserve_directed_infinite_geometry_and_clip_bytes():
    probes=setup_probes()
    for base in range(0,544,17):
        expected=directed_infinite_line(vars(probes[base]))
        for probe in probes[base:base+17]:
            assert directed_infinite_line(vars(probe))==expected
            clip=probe.clip_positions()
            reconstructed=np.column_stack(((clip[:,0]+1)*8192,(1-clip[:,1])*8192))
            np.testing.assert_array_equal(reconstructed,[probe.start_units,probe.end_units])


@pytest.mark.parametrize('capture',(capture_one,capture_corner_one))
def test_old_capture_roles_refuse_setup_before_backend_access(capture):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError):
        capture(backend,sink,PROBE,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('probe',(training_probes()[0],corner_probes()[0],
    replace(PROBE,identity='new-holdout-role-0'),replace(PROBE,width_units=384),
    replace(PROBE,start_units=(0,0))))
def test_foreign_or_changed_setup_descriptors_refuse_before_access(probe):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError,match='exact frozen setup'):
        capture_setup_one(backend,sink,probe,0)
    assert not backend.calls and not sink.raw


@pytest.mark.parametrize('index',(-1,True,1,544))
def test_reordered_setup_rows_refuse_before_access(index):
    backend,sink=Backend(),Sink()
    with pytest.raises(ValueError,match='canonical order'):
        capture_setup_one(backend,sink,PROBE,index)
    assert not backend.calls and not sink.raw


def test_setup_reuses_single_read_protocol_and_preserves_raw_before_acceptance():
    backend,sink=Backend(),Sink()
    backend.commands[0][3]=expected_vertex_upload(PROBE)
    capture_setup_one(backend,sink,PROBE,0)
    assert backend.calls==['prepare','dispatch','observe','read','observe']
    assert len(sink.raw)==1 and sink.accepted==[0]


def test_setup_backend_and_sink_repeat_role_admission():
    backend=SetupTrainingBackend('unused','unused')
    with pytest.raises(ValueError):
        backend.prepare(training_probes()[0])
    sink=SetupTrainingSink('unused-root',544)
    with pytest.raises(ValueError):
        sink.record(0,training_probes()[0],Backend().frame,state(),state(),[])
    assert sink.data is None


@pytest.mark.parametrize('reader,identity',((read_setup_row,training_probes()[0].identity),
    (read_setup_row,corner_probes()[0].identity),(read_setup_row,'new-holdout-role-0'),
    (read_training_row,PROBE.identity),(read_corner_row,PROBE.identity)))
def test_cross_role_readers_refuse_before_filesystem(reader,identity,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Filesystem access before role refusal')
    with monkeypatch.context() as context:
        context.setattr(np,'load',forbidden)
        context.setattr(Path,'stat',forbidden)
        context.setattr(Path,'read_bytes',forbidden)
        with pytest.raises(ValueError):
            reader('unused',identity)


def test_setup_sink_keeps_selection_indices_raw_bytes_and_removes_owned_temp():
    with tempfile.TemporaryDirectory(prefix='vispy-setup-sink-control-') as temporary:
        with SetupTrainingSink(temporary,2,(0,543)) as sink:
            for index in (0,543):
                sink.record(index,setup_probes()[index],Backend().frame,state(),state(),[])
                sink.accept(index)
        frames=np.load(Path(temporary)/'training.rgba.npy',allow_pickle=False)
        assert frames.shape==(2,64,64,4) and frames.dtype==np.uint8
        assert sink.raw_frames==sink.accepted_frames==2
    assert not Path(temporary).exists()
