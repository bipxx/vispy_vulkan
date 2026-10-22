# SPDX-License-Identifier: AGPL-3.0-only
"""Disjoint viewport-origin/scale controls with identical window-space lines."""
from dataclasses import asdict,dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import numpy as np

try:
    from .smooth_line_mechanism import Probe,training_probes,SIZE
    from .smooth_line_training_provider import (TrainingSink,WindowsGLTrainingBackend,
        validate_state,validate_frame,validate_commands)
    from .smooth_line_training_commands import validate_complete_commands
except ImportError:
    from smooth_line_mechanism import Probe,training_probes,SIZE
    from smooth_line_training_provider import (TrainingSink,WindowsGLTrainingBackend,
        validate_state,validate_frame,validate_commands)
    from smooth_line_training_commands import validate_complete_commands

VIEWPORTS=((0,0,64,64),(-8,-8,64,64),(0,0,128,128),(-16,-16,128,128))


@dataclass(frozen=True)
class ViewportProbe(Probe):
    viewport: tuple[int,int,int,int]

    def clip_positions(self):
        positions=np.array([self.start_units,self.end_units],dtype=np.float32)/np.float32(256)
        x,y,w,h=self.viewport
        positions[:,0]=(positions[:,0]-np.float32(x))/np.float32(w/2)-np.float32(1)
        # Window geometry uses top-left readback coordinates; GL viewport Y is bottom-left.
        positions[:,1]=(np.float32(SIZE[1])-positions[:,1]-np.float32(y))/np.float32(h/2)-np.float32(1)
        return positions


@lru_cache(maxsize=1)
def viewport_probes():
    selected=[p for p in training_probes() if p.identity.startswith('oblique-') and
              p.width_units in (256,832) and p.identity.endswith(('-p000-000','-p000-255'))]
    assert len(selected)==64
    return tuple(ViewportProbe('viewport-'+p.identity+f'-vp{index}',p.start_units,p.end_units,p.width_units,viewport)
                 for p in selected for index,viewport in enumerate(VIEWPORTS))


def viewport_contract():
    records=[asdict(p) for p in viewport_probes()]
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1,study_kind='viewport-setup',scope='Additional training only; no held-out qualification',
        probe_count=256,probes_sha256=digest,size=[64,64],format='linear RGBA8',sample_count=1,
        color=[1,1,1,1],clear=[0,0,0,0],blending=False,line_smooth=True,viewports=[list(v) for v in VIEWPORTS],
        baseline_rows=64,window_geometries=64,window_geometry_unchanged=True,
        model_selected=False,renderer_qualified=False)


def viewport_repeat_indices():
    return tuple(range(0,256,4))


@lru_cache(maxsize=1)
def _selected():
    return MappingProxyType({p.identity:(i,p) for i,p in enumerate(viewport_probes())})


def admit_viewport_probe(probe):
    if (type(probe) is not ViewportProbe or type(probe.identity) is not str or
        any(type(v) is not int for v in (*probe.start_units,*probe.end_units,probe.width_units,*probe.viewport)) or
        _selected().get(probe.identity,(None,None))[1]!=probe):
        raise ValueError('Only exact frozen viewport-training descriptors are allowed')


def admit_viewport_row(probe,index):
    admit_viewport_probe(probe)
    if type(index) is not int or _selected()[probe.identity][0]!=index:
        raise ValueError('Viewport-training row differs from canonical order')


def validate_viewport_state(state,probe,baseline):
    admit_viewport_probe(probe)
    if state['viewport']!=list(probe.viewport):
        raise ValueError('Actual viewport differs from the declared control')
    # The changed viewport has already been checked. Reuse every other unchanged
    # state invariant without modifying the raw observed record or baseline.
    validate_state(dict(state,viewport=[0,0,*SIZE]),probe,baseline,target_format='rgba8')


def validate_viewport_commands(commands,probe,program,buffer,*,complete=False,initial=False):
    admit_viewport_probe(probe)
    if not commands or commands[0]!=['FUNC','glViewport',*probe.viewport]:
        raise ValueError('One declared viewport command must precede the row batch')
    if complete:
        validate_complete_commands(commands[1:],probe,program,buffer,initial=initial)
    else:
        validate_commands(commands[1:],probe,program,buffer)


def capture_viewport_one(backend,sink,probe,index):
    admit_viewport_row(probe,index)
    if backend.target_format!='rgba8':
        raise ValueError('Viewport study requires RGBA8')
    backend.last_before=backend.last_after=None
    backend.last_commands=[]
    backend.prepare(probe)
    backend.flush_commands()
    before=backend.observe()
    backend.last_before=before
    backend.last_commands=backend.peek_commands()
    validate_viewport_state(before,probe,backend.baseline)
    image=backend.read_pixels()
    after=backend.observe()
    backend.last_after=after
    commands=backend.take_commands()
    backend.last_commands=commands
    sink.record(index,probe,image,before,after,commands)
    validate_viewport_state(after,probe,backend.baseline)
    validate_frame(image,target_format='rgba8')
    validate_viewport_commands(commands,probe,backend.program_id,backend.vertex_buffer_id)
    sink.accept(index)


class ViewportTrainingSink(TrainingSink):
    def record(self,index,probe,image,before,after,commands):
        admit_viewport_row(probe,index)
        if self.dtype!=np.uint8:
            raise ValueError('Viewport study requires RGBA8 storage')
        self._record_admitted(index,probe,image,before,after,commands)


class ViewportTrainingBackend(WindowsGLTrainingBackend):
    def prepare(self,probe):
        admit_viewport_probe(probe)
        if self.target_format!='rgba8':
            raise ValueError('Viewport study requires RGBA8')
        self.gloo.set_viewport(*probe.viewport)
        self._prepare_admitted(probe)


def read_viewport_row(root,identity):
    if type(identity) is not str or identity not in _selected():
        raise ValueError('Descriptor is not in the frozen viewport-training selection')
    data=np.load(Path(root)/'training.rgba.npy',mmap_mode='r',allow_pickle=False)
    try:
        if data.dtype!=np.uint8 or data.shape!=(256,64,64,4):
            raise ValueError('Complete viewport-training array required')
        return np.array(data[_selected()[identity][0]],copy=True)
    finally:
        data._mmap.close()
