# SPDX-License-Identifier: AGPL-3.0-only
"""Strict setup/teardown and baseline checks for the RGBA8 training reader."""
import numpy as np
try:
    from .fixture_gloo import freeze
    from .smooth_line_training_provider import DISABLED
except ImportError:
    from fixture_gloo import freeze
    from smooth_line_training_provider import DISABLED


def expected_setup(framebuffer,texture,current):
    return [['CURRENT',0,current],['CREATE',framebuffer,'FrameBuffer'],['CREATE',texture,'Texture2D'],
        ['INTERPOLATION',texture,'nearest','nearest'],['WRAPPING',texture,['clamp_to_edge','clamp_to_edge']],
        ['SIZE',texture,[64,64,4],'rgba','rgba8'],['DATA',texture,[0,0],freeze(np.zeros((64,64,4),np.uint8))],
        ['ATTACH',framebuffer,'color',texture],['FRAMEBUFFER',framebuffer,True],
        ['FUNC','glViewport',0,0,64,64],['FUNC','glDisable','cull_face'],['FUNC','glLineWidth',1],
        ['FUNC','glEnable',0x0B20],['FUNC','glDisable','blend'],['FUNC','glDisable','depth_test'],
        ['FUNC','glDisable','stencil_test'],['FUNC','glDisable','scissor_test'],
        ['FUNC','glColorMask',True,True,True,True]]


def validate_setup(payload):
    commands=payload['commands']
    if len(commands)<3 or commands[0][:2]!=['CURRENT',0]:
        raise ValueError('Setup current-context command required')
    current=commands[0][2]
    framebuffer,texture=commands[1][1],commands[2][1]
    if (any(type(v) is not int or v<=0 for v in (current,framebuffer,texture)) or
            framebuffer==texture or commands!=expected_setup(framebuffer,texture,current)):
        raise ValueError('Complete setup GLIR sequence differs')
    direct=[['glDisable',name,value] for name,value in DISABLED.items()]+[['glHint',0x0C52,0x1100]]
    if payload['direct_state_calls']!=direct:
        raise ValueError('Direct setup state sequence differs')
    return framebuffer,texture


def validate_metadata(startup,worker,diagnostics,expected_oracle,prior_baseline):
    if startup['graphics_creation_attempted'] is not False or diagnostics['cleanup_error'] is not None:
        raise ValueError('Startup or cleanup status differs')
    for key,value in startup.items():
        if key!='graphics_creation_attempted' and worker[key]!=value:
            raise ValueError('Startup identity/source binding differs')
    baseline=worker['baseline']
    if diagnostics['baseline']!=baseline:
        raise ValueError('Baseline copies differ')
    for key,value in expected_oracle.items():
        if baseline[key]!=value:
            raise ValueError('Declared oracle differs')
    for key in ('renderer','version','vendor','width_range','width_granularity','subpixel_bits','profile_mask','context_flags'):
        if baseline[key]!=prior_baseline[key]:
            raise ValueError('Baseline differs from admitted original implementation')
