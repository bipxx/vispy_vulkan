# SPDX-License-Identifier: AGPL-3.0-only
"""Current sampler-index refusals must be precise and leave compilation usable."""
import pytest
from vispy import _dawn

pytestmark = pytest.mark.gpu
VERTEX = 'attribute vec2 position;void main(){gl_Position=vec4(position,0,1);}'


@pytest.mark.parametrize('index,diagnostic', [
    ('selector', 'dynamic indexing remains unsupported'),
    ('int(gl_FragCoord.x)%2', 'dynamic indexing remains unsupported'),
    ('-1', 'literal nonnegative'),
    ('2', 'exceeds the declared length'),
])
@pytest.mark.parametrize('helper', [False, True])
def test_sampler_index_refusal_and_valid_compilation_recovery(index, diagnostic, helper):
    function = ('vec4 fetch_image(sampler2D image){return texture2D(image,vec2(.5));}'
                if helper else '')
    read = 'fetch_image(images[%s])' if helper else 'texture2D(images[%s],vec2(.5))'
    def fragment(element):
        return ('uniform sampler2D images[2];uniform int selector;' + function +
                'void main(){gl_FragColor=' + read % element + ';}')
    refused = _dawn.compile_variant(VERTEX, fragment(index))
    assert not refused['ok'], refused
    assert 'sampler array images' in refused['error'], refused
    assert diagnostic in refused['error'], refused
    recovered = _dawn.compile_variant(VERTEX, fragment('1'))
    assert recovered['ok'], recovered
    assert recovered['spirv_vertex_words'] > 0 and recovered['spirv_fragment_words'] > 0
