# SPDX-License-Identifier: AGPL-3.0-only
"""Disjoint fine along-line training controls for origin/normalization setup."""
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from math import gcd
from pathlib import Path
from types import MappingProxyType

import numpy as np

try:
    from .smooth_line_mechanism import Probe, training_probes
    from .smooth_line_training_provider import TrainingSink, WindowsGLTrainingBackend, _capture_admitted
except ImportError:
    from smooth_line_mechanism import Probe, training_probes
    from smooth_line_training_provider import TrainingSink, WindowsGLTrainingBackend, _capture_admitted


@lru_cache(maxsize=1)
def setup_probes():
    probes=[]
    for vector,dx,dy in ((2,36,27),(3,27,36),(0,36,9),(6,36,36)):
        divisor=gcd(dx,dy)
        unit=(dx//divisor,dy//divisor)
        for reverse in (False,True):
            for width in (256,832):
                for mode in ('translate','start-only'):
                    for step in range(17):
                        start=(12*256,12*256)
                        end=((12+dx)*256,(12+dy)*256)
                        if reverse:
                            start,end=end,start
                        delta=(unit[0]*step,unit[1]*step)
                        start=tuple(a+b for a,b in zip(start,delta))
                        if mode=='translate':
                            end=tuple(a+b for a,b in zip(end,delta))
                        identity=f'setup-along-vector{vector}-r{int(reverse)}-w{width}-{mode}-step{step:03}'
                        probes.append(Probe(identity,start,end,width))
    return tuple(probes)


def setup_contract():
    records=[asdict(probe) for probe in setup_probes()]
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1,study_kind='setup-along',scope='Additional training only; no held-out qualification',
                probe_count=544,probes_sha256=digest,size=[64,64],format='linear RGBA8',sample_count=1,
                color=[1,1,1,1],clear=[0,0,0,0],blending=False,line_smooth=True,
                vectors=[2,3,0,6],widths_units=[256,832],directions='both',
                modes=['translate','start-only'],steps=list(range(17)),
                step_units='primitive positive vector /256 pixel',baseline_rows=32,
                baseline_unique_original_rows=16,original7040_unchanged=True,corner4096_unchanged=True,
                model_selected=False,renderer_qualified=False)


def setup_repeat_indices():
    return tuple(index for base in range(0,544,17) for index in (base,base+16))


def setup_baseline_pairs():
    old={(p.start_units,p.end_units,p.width_units):index for index,p in enumerate(training_probes())}
    return tuple((index,old[(probe.start_units,probe.end_units,probe.width_units)])
                 for index,probe in enumerate(setup_probes()) if index%17==0)


@lru_cache(maxsize=1)
def _selected():
    return MappingProxyType({probe.identity:(index,probe) for index,probe in enumerate(setup_probes())})


def admit_setup_probe(probe):
    if (type(probe) is not Probe or type(probe.identity) is not str or
            any(type(v) is not int for v in (*probe.start_units,*probe.end_units,probe.width_units)) or
            _selected().get(probe.identity,(None,None))[1] != probe):
        raise ValueError('Only exact frozen setup-training descriptors are allowed')


def admit_setup_row(probe,index):
    admit_setup_probe(probe)
    if type(index) is not int or _selected()[probe.identity][0] != index:
        raise ValueError('Setup-training row differs from canonical order')


def capture_setup_one(backend,sink,probe,index):
    admit_setup_row(probe,index)
    if backend.target_format != 'rgba8':
        raise ValueError('Setup study requires the original RGBA8 target')
    _capture_admitted(backend,sink,probe,index)


class SetupTrainingSink(TrainingSink):
    def record(self,index,probe,image,before,after,commands):
        admit_setup_row(probe,index)
        if self.dtype != np.uint8:
            raise ValueError('Setup study requires RGBA8 storage')
        self._record_admitted(index,probe,image,before,after,commands)


class SetupTrainingBackend(WindowsGLTrainingBackend):
    def prepare(self,probe):
        admit_setup_probe(probe)
        if self.target_format != 'rgba8':
            raise ValueError('Setup study requires RGBA8')
        self._prepare_admitted(probe)


def read_setup_row(root,identity):
    if type(identity) is not str or identity not in _selected():
        raise ValueError('Descriptor is not in the frozen setup-training selection')
    index=_selected()[identity][0]
    data=np.load(Path(root)/'training.rgba.npy',mmap_mode='r',allow_pickle=False)
    try:
        if data.dtype != np.uint8 or data.shape != (544,64,64,4):
            raise ValueError('Complete setup-training array required')
        return np.array(data[index],copy=True)
    finally:
        data._mmap.close()
