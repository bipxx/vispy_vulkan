# SPDX-License-Identifier: AGPL-3.0-only
import numpy as np
import pytest
from vispy.gloo import VertexBuffer
from vispy.visuals.shaders import Variable, ModularProgram

MATRICES=[('mat%d'%c if c==r else 'mat%dx%d'%(c,r),c,r) for c in (2,3,4) for r in (2,3,4)]

@pytest.mark.parametrize('gtype,c,r',MATRICES)
@pytest.mark.parametrize('shape',[(),(2,2)])
@pytest.mark.parametrize('form',['constant','raw','list','buffer','interleaved'])
def test_explicit_matrix_attributes_reach_composed_uploads(gtype,c,r,shape,form):
    declaration='attribute %s value%s'%(gtype,''.join('[%d]'%d for d in shape))
    words=np.arange(3*int(np.prod(shape))*c*r,dtype=np.float32).reshape((3,)+shape+(c,r))
    if form=='constant':value=tuple(words[0].ravel().tolist())
    elif form=='raw':value=words
    elif form=='list':value=words.tolist()
    else:
        dtype=([('prefix',np.float32,2)] if form=='interleaved' else [])+[('value',np.float32,shape+(c,r))]
        records=np.zeros(3,dtype=dtype);records['value']=words
        buffer=VertexBuffer(records,divisor=2)
        value=buffer['value'] if form=='interleaved' else buffer
    variable=Variable(declaration,value)
    suffix='[1][1]' if shape else ''
    program=ModularProgram('void main(){gl_Position=vec4($data%s[0][0]);}'%suffix,'void main(){gl_FragColor=vec4(1);}')
    program.vert['data']=variable
    program.build_if_needed();name=program.compiler[variable]
    program.glir.clear();program.update_variables()
    commands=program.glir.clear();uploads=[c for c in commands if c[0]=='ATTRIBUTE']
    assert len(uploads)==1 and uploads[0][2:4]==(name,gtype)
    if form=='constant':assert uploads[0][4][0]==0 and len(uploads[0][4])==1+words[0].size
    else:
        assert program[name].size==3 and uploads[0][5]==(2 if form in ('buffer','interleaved') else None)
        payload=[c[3] for c in commands if c[0]=='DATA' and c[1]==program[name].id][-1]
        field='value' if 'value' in payload.dtype.names else 'f0'
        np.testing.assert_array_equal(payload[field],words)
    program.update_variables();assert program.glir.clear()==[]

@pytest.mark.parametrize('declaration,good,bad',[
 ('attribute mat2 a',(1.,0.,0.,1.),(1.,2.,3.)),
 ('attribute vec2 a[2][2]',tuple(range(8)),tuple(range(7))),
 ('attribute mat2 a',np.zeros((3,2,2),np.float32),np.zeros((3,2,3),np.float32)),
 ('attribute mat2 a',np.zeros((3,2,2),np.float32),np.zeros((3,2,2),np.float64)),
 ('uniform float a',1.,(1.,2.)),
])
def test_rejected_values_preserve_value_and_upload_identity(declaration,good,bad):
    variable=Variable(declaration,good);old=variable.value;state=variable.state_id
    with pytest.raises((TypeError,ValueError)):
        variable.value=bad
    assert variable.value is old and variable.state_id==state


def test_explicit_integer_array_and_natural_scalar_array_records():
    for gtype,leaf,dtype in [('ivec3',(3,),np.int32),('float',(),np.float32)]:
        value=Variable('attribute %s a[2][2]'%gtype,np.zeros((3,2,2)+leaf,dtype))
        assert value.value.shape==(3,) and value.value.dtype['f0'].base==dtype


def test_rejected_buffer_record_keeps_previous_value_and_identity():
    old=VertexBuffer(np.zeros(3,dtype=[('a',np.float32,(2,3))]))
    variable=Variable('attribute mat2x3 a',old)
    state=variable.state_id
    bad=VertexBuffer(np.zeros((3,3),np.float32))
    with pytest.raises(TypeError,match='incompatible buffer'):
        variable.value=bad
    assert variable.value is old and variable.state_id==state
