# SPDX-License-Identifier: AGPL-3.0-only
"""CPU controls for exact diagnostic transport; no graphics or line oracle."""
import numpy as np
import pytest
from copy import deepcopy
from tools import smooth_line_shader_arithmetic as probe
from tools.smooth_line_mechanism import training_probes


@pytest.mark.parametrize('rgba,bits',[
    ([0,0,128,63],0x3f800000), ([103,69,35,193],0xc1234567),
    ([0,0,0,128],0x80000000), ([255,255,127,127],0x7f7fffff),
    ([0,255,0,255],0xff00ff00)])
def test_explicit_byte_order(rgba,bits):
    assert probe.rgba_bits(np.array([[rgba]],dtype=np.uint8))==bits


@pytest.mark.parametrize('array',[
    np.zeros((4,),np.uint8),np.zeros((1,1,3),np.uint8),
    np.zeros((1,1,4),np.float32),np.zeros((2,1,4),np.uint8)])
def test_refuse_altered_readback(array):
    with pytest.raises(ValueError):probe.rgba_bits(array)


def test_float_bit_transport_signed_zero_and_fraction():
    assert np.signbit(probe.float_from_bits(0x80000000))
    assert probe.float_from_bits(0x3eaaaaab)==np.float32(1/3)
    assert probe.float_from_bits(0xc1234567).view(np.uint32)==0xc1234567


def test_all_bytes_in_all_channels_and_no_subnormal_nan_or_inf():
    for channel in range(4):
        assert {bits>>(8*channel)&255 for bits in probe.CONTROL_BITS}==set(range(256))
    for bits in probe.CONTROL_BITS:
        value=probe.float_from_bits(bits)
        assert np.isfinite(value)
        assert value==0 or abs(value)>=np.finfo(np.float32).tiny
    assert probe.READBACKS==2356


def test_directions_are_existing_training_only():
    actual={((p.end_units[0]-p.start_units[0])/256,
             (p.end_units[1]-p.start_units[1])/256) for p in training_probes()}
    assert set(probe.TRAINING_DIRECTIONS)<=actual
    assert len(probe.TRAINING_DIRECTIONS)==len(set(probe.TRAINING_DIRECTIONS))==16


def test_unknown_operation_refused():
    with pytest.raises(ValueError):probe.fragment('fitted-normal')


@pytest.mark.parametrize('bits',[-1,2**32,True,1.5])
def test_invalid_bit_inputs(bits):
    with pytest.raises(ValueError):probe.float_from_bits(bits)


def record(bits):
    return dict(bits=f'{bits:08x}',rgba=[[[bits>>(8*i)&255 for i in range(4)]]])


def synthetic_transport():
    return dict(controls=[dict(operation=op,input_bits=f'{b:08x}',**record(b))
                         for b in probe.CONTROL_BITS for op in ('identity-x','identity-y')],
        measurements=[dict(repeat=repeat,direction=list(probe.TRAINING_DIRECTIONS[i]),
                           operation=op,**record(0x3f800000))
                      for repeat,indices in enumerate((range(16),range(15,-1,-1)))
                      for i in indices for op in probe.OPERATIONS])


def test_complete_transport_is_admitted_without_claiming_math():
    # Constant synthetic results validate transport/stability only. They cannot
    # prove that normalization or any line model is correct.
    probe.validate_transport_and_repeats(synthetic_transport())


@pytest.mark.parametrize('defect',['missing-control','missing-repeat','corrupt-byte','wrapped-byte','unstable'])
def test_invalid_transport_or_stability_refused(defect):
    data=deepcopy(synthetic_transport())
    if defect=='missing-control':data['controls'].pop()
    if defect=='missing-repeat':data['measurements'].pop()
    if defect=='corrupt-byte':data['controls'][0]['rgba'][0][0][0]=1
    if defect=='wrapped-byte':data['controls'][0]['rgba'][0][0][0]=256
    if defect=='unstable':data['measurements'][-1].update(record(0x3f800001))
    with pytest.raises(ValueError):probe.validate_transport_and_repeats(data)
