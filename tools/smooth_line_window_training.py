# SPDX-License-Identifier: AGPL-3.0-only
"""Disjoint integer window-translation controls; raw reference frames stay intact."""
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import numpy as np

try:
    from .smooth_line_mechanism import Probe,training_probes
    from .smooth_line_training_provider import TrainingSink,WindowsGLTrainingBackend,_capture_admitted
except ImportError:
    from smooth_line_mechanism import Probe,training_probes
    from smooth_line_training_provider import TrainingSink,WindowsGLTrainingBackend,_capture_admitted

OFFSETS=tuple((x,y) for y in (-4,0,4) for x in (-4,0,4))


@lru_cache(maxsize=1)
def window_probes():
    selected=[p for p in training_probes() if p.identity.startswith('oblique-') and
              p.width_units in (256,832) and p.identity.endswith(('-p000-000','-p000-255'))]
    assert len(selected)==64
    return tuple(Probe(f'window-shift-{p.identity}-ox{x}-oy{y}',
                       (p.start_units[0]+x*256,p.start_units[1]+y*256),
                       (p.end_units[0]+x*256,p.end_units[1]+y*256),p.width_units)
                 for p in selected for x,y in OFFSETS)


def window_contract():
    records=[asdict(p) for p in window_probes()]
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1,study_kind='window-translation',scope='Additional training only; no held-out qualification',
        probe_count=576,probes_sha256=digest,size=[64,64],format='linear RGBA8',sample_count=1,
        color=[1,1,1,1],clear=[0,0,0,0],blending=False,line_smooth=True,
        viewport=[0,0,64,64],offsets_pixels=[list(v) for v in OFFSETS],baseline_rows=64,
        repeat_scope='all576 rows in reverse order after the complete sweep',
        comparison='Declared integer pixel correspondence; unmatched source/target pixels must remain clear',
        model_selected=False,renderer_qualified=False)


def window_repeat_indices():
    return tuple(range(575,-1,-1))


def window_baseline_pairs():
    original={(p.start_units,p.end_units,p.width_units):i for i,p in enumerate(training_probes())}
    return tuple((i,original[(p.start_units,p.end_units,p.width_units)])
                 for i,p in enumerate(window_probes()) if i%9==4)


@lru_cache(maxsize=1)
def _selected():
    return MappingProxyType({p.identity:(i,p) for i,p in enumerate(window_probes())})


def admit_window_probe(probe):
    if (type(probe) is not Probe or type(probe.identity) is not str or
            any(type(v) is not int for v in (*probe.start_units,*probe.end_units,probe.width_units)) or
            _selected().get(probe.identity,(None,None))[1]!=probe):
        raise ValueError('Only exact frozen window-training descriptors are allowed')


def admit_window_row(probe,index):
    admit_window_probe(probe)
    if type(index) is not int or _selected()[probe.identity][0]!=index:
        raise ValueError('Window-training row differs from canonical order')


def capture_window_one(backend,sink,probe,index):
    admit_window_row(probe,index)
    if backend.target_format!='rgba8':
        raise ValueError('Window study requires RGBA8')
    _capture_admitted(backend,sink,probe,index)


class WindowTrainingSink(TrainingSink):
    def record(self,index,probe,image,before,after,commands):
        admit_window_row(probe,index)
        if self.dtype!=np.uint8:
            raise ValueError('Window study requires RGBA8 storage')
        self._record_admitted(index,probe,image,before,after,commands)


class WindowTrainingBackend(WindowsGLTrainingBackend):
    def prepare(self,probe):
        admit_window_probe(probe)
        if self.target_format!='rgba8':
            raise ValueError('Window study requires RGBA8')
        self._prepare_admitted(probe)


def read_window_row(root,identity):
    if type(identity) is not str or identity not in _selected():
        raise ValueError('Descriptor is not in the frozen window-training selection')
    data=np.load(Path(root)/'training.rgba.npy',mmap_mode='r',allow_pickle=False)
    try:
        if data.dtype!=np.uint8 or data.shape!=(576,64,64,4):
            raise ValueError('Complete window-training array required')
        return np.array(data[_selected()[identity][0]],copy=True)
    finally:
        data._mmap.close()


def compare_integer_correspondence(baseline,moved,offset):
    """Compare declared positions without constructing or modifying a reference."""
    if type(offset) is not tuple or offset not in OFFSETS or any(type(v) is not int for v in offset):
        raise ValueError('Declared integer offset required')
    for frame in (baseline,moved):
        if not isinstance(frame,np.ndarray) or frame.dtype!=np.uint8 or frame.shape!=(64,64,4):
            raise ValueError('64x64 RGBA8 frame required')
    dx,dy=offset
    x0,x1=max(0,-dx),min(64,64-dx)
    y0,y1=max(0,-dy),min(64,64-dy)
    source_mask=np.ones((64,64),bool)
    target_mask=np.ones((64,64),bool)
    source_mask[y0:y1,x0:x1]=False
    target_mask[y0+dy:y1+dy,x0+dx:x1+dx]=False
    source_extra=int(np.count_nonzero(np.any(baseline[source_mask]!=0,axis=1)))
    target_extra=int(np.count_nonzero(np.any(moved[target_mask]!=0,axis=1)))
    delta=np.abs(baseline[y0:y1,x0:x1].astype(np.int16)-moved[y0+dy:y1+dy,x0+dx:x1+dx])
    return dict(pixels_compared=(x1-x0)*(y1-y0),differing_pixels=int(np.count_nonzero(np.any(delta,axis=2))),
                maximum_channel_error=int(delta.max()),unmatched_baseline_nonclear=source_extra,
                unmatched_moved_nonclear=target_extra,raw_frames_modified=False)
