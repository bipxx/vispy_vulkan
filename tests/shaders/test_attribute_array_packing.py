# SPDX-License-Identifier: AGPL-3.0-only
import numpy as np
import pytest
from vispy.gloo import Program

CASES=[('float',(1,),np.float32),('vec2',(2,),np.float32),('ivec3',(3,),np.int32),('mat2x2',(2,2),np.float32),('mat3x3',(3,3),np.float32),('mat4x4',(4,4),np.float32)]+[
    ('mat%d%s' % (c,'' if c==r else 'x%d'%r),(c,r),np.float32)
    for c in (2,3,4) for r in (2,3,4)]

def shader(gtype,count=0):
    return Program('attribute %s a[2][3];void main(){}'%gtype,'void main(){}',count=count)

@pytest.mark.parametrize('gtype,leaf,dtype',CASES)
@pytest.mark.parametrize('prefix,shape',[('a',(2,3)),('a[1]',(3,)),('a[1][2]',())])
def test_array_records_updates_and_offsets(gtype,leaf,dtype,prefix,shape):
    p=shader(gtype)
    values=np.arange(5*int(np.prod(shape+leaf)),dtype=dtype).reshape((5,)+shape+leaf)
    p[prefix]=values
    buffer=p[prefix]
    assert buffer.size==5 and buffer.stride==int(np.prod(shape+leaf))*4
    original_dtype=buffer.dtype
    p.glir.clear()
    replacement=values[:2].copy()
    buffer.set_subdata(replacement,offset=2)
    commands=p.glir.clear()
    data=[c for c in commands if c[0]=='DATA' and c[1]==buffer.id]
    assert len(data)==1 and data[0][2]==2*buffer.stride
    assert data[0][3].dtype==original_dtype
    p[prefix]=values[:3].copy()
    assert p[prefix] is buffer and buffer.size==3 and buffer.dtype==original_dtype

@pytest.mark.parametrize('gtype,leaf,dtype',CASES)
def test_parent_constants_stay_constants_after_shader_rebuild(gtype,leaf,dtype):
    p=shader(gtype)
    values=list(range(6*int(np.prod(leaf))))
    p['a']=values
    p.glir.clear()
    p.set_shaders('attribute %s a[2][3];void main(){}'%gtype,'void main(){}')
    commands=p.glir.clear()
    attributes=[c for c in commands if c[0]=='ATTRIBUTE' and c[2]=='a']
    assert len(attributes)==1 and attributes[0][4][0]==0
    np.testing.assert_array_equal(attributes[0][4][1:],values)

@pytest.mark.parametrize('gtype,leaf,dtype',CASES)
def test_count_stores_only_logical_root(gtype,leaf,dtype):
    p=shader(gtype,count=5)
    assert p._buffer.dtype.names==('a',)
    natural=leaf if leaf!=(1,) else ()
    values=np.zeros((5,2,3)+natural,dtype=dtype)
    p['a']=values
    assert p._buffer.shape==(5,)

@pytest.mark.parametrize('gtype,leaf,dtype',CASES)
def test_bad_array_update_does_not_replace_buffer(gtype,leaf,dtype):
    p=shader(gtype)
    values=np.zeros((5,2,3)+leaf,dtype=dtype)
    p['a']=values
    old=p['a'];p.glir.clear()
    with pytest.raises((ValueError,TypeError)):
        p['a']=np.zeros((5,2,4)+leaf,dtype=dtype)
    assert p['a'] is old and old.size==5 and p.glir.clear()==[]


def test_interleaved_views_inherit_and_can_override_divisor():
    from vispy.gloo import VertexBuffer
    buffer=VertexBuffer(np.zeros(3,dtype=[('padding',np.float32),('a',np.float32,(2,3))]),divisor=2)
    view=buffer['a']
    assert view.divisor==2
    buffer.divisor=4
    assert view.divisor==4
    view.divisor=3
    assert view.divisor==3 and buffer.divisor==4
    p=Program('attribute mat2x3 a;void main(){}','void main(){}')
    p['a']=view
    command=[c for c in p.glir.clear() if c[0]=='ATTRIBUTE'][-1]
    assert command[4]==(buffer.id,buffer.stride,4) and command[5]==3
