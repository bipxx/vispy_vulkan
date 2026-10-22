# SPDX-License-Identifier: AGPL-3.0-only
"""Public RGB/RGBA volume controls authored before either renderer is run."""
from __future__ import annotations
import hashlib
import numpy as np
try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE=(96,96)
METHODS=('mip','minip','attenuated_mip','translucent','additive','iso','average')
CASES=tuple(f'{kind}_{method}' for kind in ('rgb','rgba') for method in METHODS)+(
    'rgba_mip_opaque','rgba_mip_alpha_low','rgb_plane','rgba_plane',
    'rgb_update','rgba_update','rgb_linear','rgba_linear','rgb_to_rgba','rgba_to_rgb')


def array_record(data):
    return dict(shape=list(data.shape),dtype=data.dtype.str,
                sha256=hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest())


def phantom(channels, *, edited=False, alpha=.5):
    if type(channels) is not int or channels not in (3,4):
        raise ValueError('RGB or RGBA required')
    axis=np.linspace(-1,1,32,dtype=np.float32)
    z,y,x=np.meshgrid(axis,axis,axis,indexing='ij')
    inside=(x/.7)**2+(y/.55)**2+(z/.4)**2<=1
    rgb=np.empty((32,32,32,3),np.float32)
    rgb[:]=(.04,.02,.01)
    rgb[inside & (x<0)]=(1,.125,.25)
    rgb[inside & (x>=0)]=(.125,1,.5)
    if edited:rgb=rgb[...,::-1].copy()
    if channels==3:return rgb
    opacity=np.full((*inside.shape,1),np.float32(alpha),np.float32)
    return np.concatenate((rgb,opacity),axis=-1)


def input_arrays(name):
    if name not in CASES:raise ValueError('Unknown color-volume case')
    channels=4 if name.startswith('rgba_') else 3
    alpha=1 if name=='rgba_mip_opaque' else .125 if name=='rgba_mip_alpha_low' else .5
    before=phantom(channels,alpha=alpha)
    if name.endswith('_update'):
        return before,phantom(channels,edited=True,alpha=alpha)
    if name=='rgb_to_rgba':return before,phantom(4,alpha=.5)
    if name=='rgba_to_rgb':return before,phantom(3)
    return (before,)


def case_contract(name):
    data=input_arrays(name)
    method=next((m for m in METHODS if name in ('rgb_'+m,'rgba_'+m)),'mip')
    return dict(case=name,size=list(SIZE),inputs=[array_record(a) for a in data],
        method=method,texture_format='auto',clim=[0,1],cmap='grays',gamma=1,
        threshold=.25,relative_step_size=.5,
        interpolation='linear' if name.endswith('_linear') else 'nearest',
        raycasting_mode='plane' if name.endswith('_plane') else 'volume',
        camera=dict(fov=0,azimuth=0,elevation=0,distance=100,
                    center=[15.5,15.5,15.5],scale_factor=40,up='+z'),
        public_update='VolumeVisual.set_data' if len(data)==2 else None,
        comparison=dict(full_frame_exact=True,excluded_pixels=0))


def assert_landmarks(name,image):
    if name not in CASES:raise ValueError('Unknown color-volume case')
    assert image.shape==(96,96,4) and image.dtype==np.uint8
    assert image[2,2].tolist()==[0,0,0,255]
    assert np.any(image[...,:3]),'Blank volume cannot pass'
    assert np.any(image[...,0]!=image[...,1]),'Color channels must not collapse to luminance'
    if name=='rgb_plane':
        for x,color in ((32,[255,32,64]),(64,[32,255,128])):
            patch=image[47:50,x-1:x+2,:3].astype(int)
            assert np.max(np.abs(patch-np.array(color)))<=1,(name,x,patch.tolist())


def render(name,backend='dawn_headless'):
    spec=case_contract(name)
    from vispy import scene
    from vispy.visuals.volume import VolumeVisual
    canvas=scene.SceneCanvas(app=backend,size=SIZE,show=backend=='pyqt6',
        decorate=False,bgcolor=(0,0,0,1),config={'samples':0})
    commands,shaders=[],{}
    original=canvas.context.shared.parser.parse
    def log(batch):
        for row in batch:
            commands.append(freeze(row))
            if row[0]=='DATA' and isinstance(row[3],str):shaders[str(row[1])]=row[3]
        return original(batch)
    canvas.context.shared.parser.parse=log
    try:
        if backend=='pyqt6':
            canvas.app.native.setQuitOnLastWindowClosed(False)
            canvas._backend._vispy_warmup()
        view=canvas.central_widget.add_view()
        view.camera=scene.cameras.TurntableCamera(**spec['camera'])
        arrays=input_arrays(name)
        kwargs={k:spec[k] for k in ('method','texture_format','clim','cmap','gamma',
                                   'threshold','relative_step_size','interpolation','raycasting_mode')}
        if spec['raycasting_mode']=='plane':
            kwargs.update(plane_position=(15.5,15.5,15.5),plane_normal=(0,1,0),plane_thickness=1)
        volume=scene.visuals.Volume(arrays[0],parent=view.scene,**kwargs)
        extras={}
        if len(arrays)==2:
            extras['before']=np.array(canvas.render(size=SIZE,alpha=True),copy=True)
            volume.set_data(arrays[1],clim=(0,1))
        image=np.array(canvas.render(size=SIZE,alpha=True),copy=True)
        params=dict(spec,exposed_methods=list(VolumeVisual._rendering_methods),
                    exposed_raycasting_modes=list(VolumeVisual._raycasting_modes),
                    final_texture_shape=list(volume._texture.shape),
                    final_volume_shape=list(volume._vol_shape))
        return image,commands,shaders,params,extras
    finally:
        canvas.context.shared.parser.parse=original
        canvas.close()
