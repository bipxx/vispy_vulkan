"""Separate predeclared corner training selection; original role gates stay strict."""
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np

try:
    from .smooth_line_mechanism import Probe
    from .smooth_line_training_provider import TrainingSink, WindowsGLTrainingBackend, _capture_admitted
except ImportError:
    from smooth_line_mechanism import Probe
    from smooth_line_training_provider import TrainingSink, WindowsGLTrainingBackend, _capture_admitted


@lru_cache(maxsize=1)
def corner_probes():
    probes=[]
    major_phases=sorted({value for base in range(0,256,16) for value in (base,base+1)})
    for orientation in ('horizontal','vertical'):
        for reverse in (False,True):
            for width in (256,384):
                for major in major_phases:
                    for minor in range(1,256,16):
                        start=(12*256+major,20*256+minor)
                        end=(52*256+major,20*256+minor)
                        if orientation=='vertical':
                            start,end=start[::-1],end[::-1]
                        if reverse:
                            start,end=end,start
                        probes.append(Probe(f'corner-{orientation}-r{int(reverse)}-w{width}-major{major:03}-minor{minor:03}',
                                            start,end,width))
    return tuple(probes)


def corner_contract():
    records=[asdict(probe) for probe in corner_probes()]
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1,study_kind='corner-joint',scope='Additional training only; no held-out qualification',
                probe_count=4096,probes_sha256=digest,size=[64,64],format='linear RGBA8',sample_count=1,
                color=[1,1,1,1],clear=[0,0,0,0],blending=False,line_smooth=True,
                major_phases='base and base+1, base=0..240 step16',minor_phases='1..241 step16',
                widths_units=[256,384],directions='both',orientations=['horizontal','vertical'],
                original7040_unchanged=True,old800_family_unchanged=True,
                model_selected=False,renderer_qualified=False)


def corner_repeat_indices():
    return tuple(range(0,4096,65))


@lru_cache(maxsize=1)
def _selected():
    return MappingProxyType({probe.identity:(index,probe) for index,probe in enumerate(corner_probes())})


def admit_corner_probe(probe):
    if type(probe) is not Probe or _selected().get(probe.identity,(None,None))[1]!=probe:
        raise ValueError('Only exact frozen corner-training descriptors are allowed')


def admit_corner_row(probe,index):
    admit_corner_probe(probe)
    if type(index) is not int or _selected()[probe.identity][0]!=index:
        raise ValueError('Corner-training row differs from canonical order')


def capture_corner_one(backend,sink,probe,index):
    admit_corner_row(probe,index)
    if backend.target_format!='rgba8':
        raise ValueError('Corner study requires the original RGBA8 target')
    _capture_admitted(backend,sink,probe,index)


class CornerTrainingSink(TrainingSink):
    def record(self,index,probe,image,before,after,commands):
        admit_corner_row(probe,index)
        if self.dtype!=np.uint8:
            raise ValueError('Corner study requires RGBA8 storage')
        self._record_admitted(index,probe,image,before,after,commands)


class CornerTrainingBackend(WindowsGLTrainingBackend):
    def prepare(self,probe):
        admit_corner_probe(probe)
        if self.target_format!='rgba8':
            raise ValueError('Corner study requires RGBA8')
        self._prepare_admitted(probe)


def read_corner_row(root,identity):
    if type(identity) is not str or identity not in _selected():
        raise ValueError('Descriptor is not in the frozen corner-training selection')
    index=_selected()[identity][0]
    data=np.load(Path(root)/'training.rgba.npy',mmap_mode='r',allow_pickle=False)
    try:
        if data.dtype!=np.uint8 or data.shape!=(4096,64,64,4):
            raise ValueError('Complete corner-training array required')
        return np.array(data[index],copy=True)
    finally:
        data._mmap.close()
