"""Setup and metadata mutation controls without a graphics provider."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from smooth_line_setup_commands import expected_setup,validate_setup,validate_metadata,DISABLED
sys.path.pop(0)


def payload():
    return dict(commands=expected_setup(20,10,1),direct_state_calls=[['glDisable',k,v] for k,v in DISABLED.items()]+[['glHint',0x0C52,0x1100]])


def test_exact_setup_with_dynamic_ids_admits():
    assert validate_setup(payload())==(20,10)


@pytest.mark.parametrize('mutation',('draw','texture-bytes','attachment','viewport','reorder','direct','hint'))
def test_setup_mutations_refuse(mutation):
    value=payload()
    if mutation=='draw': value['commands'].append(['DRAW',4,'lines',[0,2],1])
    elif mutation=='texture-bytes': value['commands'][6][3]['array']['sha256']='0'*64
    elif mutation=='attachment': value['commands'][7][3]=11
    elif mutation=='viewport': value['commands'][9][-1]=63
    elif mutation=='reorder': value['commands'][10:12]=value['commands'][10:12][::-1]
    elif mutation=='direct': value['direct_state_calls'].pop(0)
    else: value['direct_state_calls'][-1][-1]=0x1102
    with pytest.raises(ValueError): validate_setup(value)


@pytest.mark.parametrize('mutation',('none','startup','baseline','oracle','prior','cleanup'))
def test_metadata_binding_mutations(mutation):
    baseline=dict(renderer='r',version='v',vendor='n',width_range=[1,64],width_granularity=.0625,
                  subpixel_bits=8,profile_mask=2,context_flags=0)
    startup=dict(pid=20,authoring_sha256='a',graphics_creation_attempted=False)
    worker=dict(startup,baseline=deepcopy(baseline));worker['graphics_creation_attempted']=True
    diagnostics=dict(baseline=deepcopy(baseline),cleanup_error=None)
    expected=dict(renderer='r',version='v');prior=deepcopy(baseline)
    if mutation=='startup': startup['pid']=21
    elif mutation=='baseline': diagnostics['baseline']['vendor']='other'
    elif mutation=='oracle': expected['renderer']='other'
    elif mutation=='prior': prior['width_range']=[1,8]
    elif mutation=='cleanup': diagnostics['cleanup_error']='failed'
    if mutation=='none': validate_metadata(startup,worker,diagnostics,expected,prior)
    else:
        with pytest.raises(ValueError): validate_metadata(startup,worker,diagnostics,expected,prior)
