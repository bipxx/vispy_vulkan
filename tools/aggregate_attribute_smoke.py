# SPDX-License-Identifier: AGPL-3.0-only
"""Shared source/installed aggregate-input pixel oracles on an active 8x8 canvas."""

def aggregate_attribute_checks(gloo, np, max_vertex_attributes):
    report = {'cases': []}
    positions = {'triangles': [[-1, -1], [3, -1], [-1, 3]], 'points': [[0, 0]], 'lines': [[-1, 0], [1, 0]]}
    fragment = 'varying vec4 color;void main(){gl_FragColor=color;}'

    def draw(p, mode, expected, label):
        gloo.set_viewport(0, 0, 8, 8)
        gloo.set_state(blend=False, depth_test=False, cull_face=False)
        gloo.set_line_width(5)
        gloo.clear(color='black')
        p.draw(mode)
        pixel = gloo.read_pixels(alpha=True)[4, 4].astype(int)
        want = np.rint(np.array(expected) * 255).astype(int)
        assert np.max(np.abs(pixel - want)) <= 1, (label, pixel.tolist(), want.tolist())
        report['cases'].append(dict(case=label, pixel=pixel.tolist(), expected=want.tolist()))
    for c in (2, 3, 4):
        for rows in (2, 3, 4):
            typ = 'mat%d' % c if c == rows else 'mat%dx%d' % (c, rows)
            source = 'attribute vec2 p;attribute %s a;varying vec4 color;vec4 seed=vec4(a[%d][%d],a[0][0],a[0][%d],1);void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=seed;}' % (typ, c - 1, rows - 1, rows - 1)
            words = np.arange(1, c * rows + 1, dtype=np.float32).reshape(c, rows) / (c * rows)
            expected = [1, 1 / (c * rows), 1 / c, 1]
            for mode in positions:
                for form in ('constant', 'buffer', 'interleaved'):
                    p = gloo.Program(source, fragment)
                    p['p'] = np.array(positions[mode], np.float32)
                    n = len(positions[mode])
                    if form == 'constant':
                        p['a'] = tuple(words.ravel().tolist())
                    elif form == 'buffer':
                        p['a'] = np.broadcast_to(words, (n, c, rows)).copy()
                    else:
                        data = np.zeros(n, dtype=[('prefix', np.float32, 3), ('a', np.float32, (c, rows)), ('suffix', np.float32, 2)])
                        data['a'] = words
                        vbo = gloo.VertexBuffer(data)
                        p['a'] = vbo['a']
                    draw(p, mode, expected, '%s-%s-%s' % (typ, mode, form))
                    if form == 'constant':
                        p.set_shaders(source, fragment)
                        draw(p, mode, expected, '%s-%s-constant-rebuild' % (typ, mode))
    for mode in positions:
        source = 'attribute vec2 p;attribute vec2 a[2][2];varying vec4 color;vec4 seed=vec4(a[1][1],a[0][0].x,1);void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=seed;}'
        n = len(positions[mode])
        p = gloo.Program(source, fragment)
        p['p'] = np.array(positions[mode], np.float32)
        values = np.array([[[0.125, 0.25], [0.375, 0.5]], [[0.625, 0.75], [0.875, 1]]], np.float32)
        p['a'] = np.broadcast_to(values, (n, 2, 2, 2)).copy()
        draw(p, mode, [0.875, 1, 0.125, 1], 'nested-array-%s-parent-buffer' % mode)
        p['a'].set_subdata(np.broadcast_to(values * 0.5, (n, 2, 2, 2)).copy(), offset=0)
        draw(p, mode, [0.4375, 0.5, 0.0625, 1], 'nested-array-%s-buffer-update' % mode)
        p['a[1]'] = (0.1, 0.2, 0.3, 0.4)
        draw(p, mode, [0.3, 0.4, 0.0625, 1], 'nested-array-%s-subarray-constant' % mode)
        p['a[1][1]'] = (0.7, 0.8)
        p['a'] = tuple(values.ravel().tolist())
        draw(p, mode, [0.7, 0.8, 0.125, 1], 'nested-array-%s-leaf-over-parent' % mode)
        p.set_shaders(source, fragment)
        draw(p, mode, [0.7, 0.8, 0.125, 1], 'nested-array-%s-rebuild' % mode)
    for mode in positions:
        n = len(positions[mode])
        source = 'attribute vec2 p;attribute mat2x3 a[2][2];varying vec4 color;vec4 seed=vec4(a[1][1][1][2],a[0][0][0][0],a[1][0][0][1],1);void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=seed;}'
        values = np.arange(1, 25, dtype=np.float32).reshape(2, 2, 2, 3) / 24
        for form in ('constant', 'buffer'):
            p = gloo.Program(source, fragment)
            p['p'] = np.array(positions[mode], np.float32)
            p['a'] = tuple(values.ravel().tolist()) if form == 'constant' else np.broadcast_to(values, (n, 2, 2, 2, 3)).copy()
            draw(p, mode, [1, 1 / 24, 14 / 24, 1], 'nested-matrix-array-%s-%s' % (mode, form))
        source = 'attribute vec2 p;attribute mat2x3 a;varying vec4 color;void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=vec4(a[1][2],a[0][0],a[0][1],1);}'
        data = np.zeros(2, dtype=[('prefix', np.float32, 2), ('a', np.float32, (2, 3))])
        data['a'][0] = 0.25
        data['a'][1] = 0.75
        vbo = gloo.VertexBuffer(data, divisor=2)
        p = gloo.Program(source, fragment)
        p['p'] = np.array(positions[mode], np.float32)
        p['a'] = vbo['a']
        draw(p, mode, [0.75, 0.75, 0.75, 1], 'matrix-%s-interleaved-divisor2' % mode)
        source = 'attribute vec2 p;attribute mat4 a;varying vec4 color;void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=vec4(a[0][3],a[1][3],a[2][3],1);}'
        p = gloo.Program(source, fragment)
        p['p'] = np.array(positions[mode], np.float32)
        draw(p, mode, [1, 1, 1, 1], 'matrix-%s-generic-column-defaults' % mode)
        data = np.zeros((4, 4), np.float32)
        data[:3, 3] = [0.25, 0.5, 0.75]
        p['a'] = tuple(data.ravel().tolist())
        draw(p, mode, [0.25, 0.5, 0.75, 1], 'matrix-%s-assignment-after-defaults' % mode)
        source = 'attribute vec2 p;attribute vec2 a[2];uniform int index;varying vec4 color;void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;color=vec4(a[index],a[0].x,1);}'
        p = gloo.Program(source, fragment)
        p['p'] = np.array(positions[mode], np.float32)
        p['a'] = (0.25, 0.5, 0.75, 1.0)
        p['index'] = 1
        draw(p, mode, [0.75, 1, 0.25, 1], 'array-%s-dynamic-index' % mode)
    p = gloo.Program('attribute vec2 p;attribute mat2x3 a;varying vec4 color;void main(){gl_Position=vec4(p,0,1);color=vec4(a[1][2],a[0][0],a[0][1],1);}', fragment)
    p['p'] = np.array(positions['triangles'], np.float32)
    p['a'] = np.ones((3, 2, 3), np.float32)
    patch = np.ones((1, 2, 3), np.float32)
    patch[0, 1, 2] = 0
    p['a'].set_subdata(patch, offset=0)
    # Vulkan clip-Y conversion puts this readback sample at a 1/2 weight.
    # Compare the matrix subupdate with an independent ordinary vector input.
    control = gloo.Program('attribute vec2 p;attribute vec3 a;varying vec4 color;void main(){gl_Position=vec4(p,0,1);color=vec4(a,1);}', fragment)
    control['p'] = np.array(positions['triangles'], np.float32)
    control['a'] = np.array([[0, 1, 1], [1, 1, 1], [1, 1, 1]], np.float32)
    draw(control, 'triangles', [0.5, 1, 1, 1], 'partial-update-vector-control')
    draw(p, 'triangles', [0.5, 1, 1, 1], 'matrix-partial-vertex-update')
    for mode in positions:
        count = len(positions[mode])
        source = ('attribute vec2 p;attribute ivec2 a[2][2];varying vec4 color;'
                  'void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;'
                  'color=vec4(vec2(a[1][1])/4.,float(a[0][0].x)/4.,1);}')
        values = np.array([[[1, 2], [2, 3]], [[3, 4], [4, 2]]], np.int32)
        for form in ('constant', 'buffer'):
            p = gloo.Program(source, fragment)
            p['p'] = np.array(positions[mode], np.float32)
            p['a'] = (tuple(values.ravel().tolist()) if form == 'constant' else
                      np.broadcast_to(values, (count, 2, 2, 2)).copy())
            draw(p, mode, [1, .5, .25, 1], 'integer-array-%s-%s' % (mode, form))
    limit = max_vertex_attributes
    count = limit // 4 + 1
    p = gloo.Program('attribute vec2 p;attribute mat4 a[%d];void main(){gl_Position=vec4(p+a[%d][3].xy,0,1);}' % (count, count - 1), 'void main(){gl_FragColor=vec4(1);}')
    p['p'] = np.array(positions['triangles'], np.float32)
    p['a'] = tuple([0.0] * (count * 16))
    try:
        p.draw('triangles')
    except RuntimeError as error:
        assert 'exceed granted attribute limit' in str(error), str(error)
        report['expected_limit_refusal'] = str(error)
    else:
        raise AssertionError('Aggregate locations bypassed granted attribute limit')
    report['passed'] = len(report['cases'])
    return report


def aggregate_indexed_checks(gloo, np):
    """Compare indexed matrix inputs with independent ordinary vector inputs."""
    cases = []
    fragment = 'varying vec4 color;void main(){gl_FragColor=color;}'
    for mode in ('triangles', 'points', 'lines'):
        if mode == 'triangles':
            positions = [[3, -1], [8, 8], [-1, 3], [-1, -1]]
            colors = [[0, 0, 1], [1, 1, 1], [0, 1, 0], [1, 0, 0]]
            indices = [3, 0, 2]
            expected = [.5, .21875, .28125, 1]
        elif mode == 'points':
            positions = [[-4, -4], [4, 4], [0, 0]]
            colors = [[1, 0, 0], [0, 0, 1], [0, 1, 0]]
            indices = [2]
            expected = [0, 1, 0, 1]
        else:
            positions = [[-1, 0], [0, 4], [1, 0]]
            colors = [[0, 1, 0], [1, 0, 0], [0, 1, 0]]
            indices = [2, 0]
            expected = [0, 1, 0, 1]
        positions = np.array(positions, np.float32)
        colors = np.array(colors, np.float32)
        records = np.zeros((len(positions), 2, 2), np.float32)
        records.reshape(len(positions), 4)[:, :3] = colors
        selection = gloo.IndexBuffer(np.array(indices, np.uint16))
        images = []
        for matrix in (False, True):
            declaration = 'mat2' if matrix else 'vec3'
            expression = 'vec3(a[0][0],a[0][1],a[1][0])' if matrix else 'a'
            vertex = ('attribute vec2 p;attribute %s a;varying vec4 color;'
                      'void main(){gl_Position=vec4(p,0,1);gl_PointSize=5.;'
                      'color=vec4(%s,1);}') % (declaration, expression)
            program = gloo.Program(vertex, fragment)
            program['p'] = positions
            program['a'] = records if matrix else colors
            gloo.set_viewport(0, 0, 8, 8)
            gloo.set_state(blend=False, depth_test=False, cull_face=False)
            gloo.set_line_width(5)
            gloo.clear(color='black')
            program.draw(mode, selection)
            images.append(gloo.read_pixels(alpha=True))
        delta = int(np.max(np.abs(images[0].astype(int) - images[1].astype(int))))
        assert delta <= 1, (mode, delta)
        pixel = images[1][4, 4].astype(int)
        wanted = np.rint(np.array(expected) * 255).astype(int)
        assert np.max(np.abs(pixel - wanted)) <= 1, (mode, pixel.tolist(), wanted.tolist())
        cases.append(dict(mode=mode, indices=indices, index_dtype='uint16',
                          center=pixel.tolist(), expected=wanted.tolist(), max_delta=delta))
    return cases


def composed_attribute_checks(gloo, np):
    """Explicit composed inputs retain values through updates and rebuilds."""
    from vispy.visuals.shaders import Variable, ModularProgram
    positions = {'triangles': [[-1,-1],[3,-1],[-1,3]],
                 'points': [[0,0]], 'lines': [[-1,0],[1,0]]}
    configs = [(('mat%d' % c if c == r else 'mat%dx%d' % (c,r)), c,r,(),form)
               for c in (2,3,4) for r in (2,3,4) for form in ('constant','raw')]
    configs += [('mat2x3',2,3,(2,2),form) for form in ('constant','raw')]
    configs += [('vec2',1,2,(2,2),form) for form in ('constant','raw')]
    configs += [('mat2x3',2,3,(),'interleaved')]
    cases = []
    fragment = 'varying vec4 color;void main(){gl_FragColor=color;}'
    for gtype,columns,rows,shape,form in configs:
        suffix = ''.join('[%d]' % d for d in shape)
        first = ''.join('[0]' for d in shape)
        last = ''.join('[%d]' % (d-1) for d in shape)
        leaf = (columns,rows) if columns > 1 else (rows,)
        record_shape = shape + leaf
        words = np.arange(1,int(np.prod(record_shape))+1,dtype=np.float32).reshape(record_shape)
        words /= words.size
        if columns > 1:
            expression = 'vec4($data%s[%d][%d],$data%s[0][0],$data%s[0][%d],1)' % (last,columns-1,rows-1,first,first,rows-1)
        else:
            expression = 'vec4($data%s[%d],$data%s[0],$data%s[%d],1)' % (last,rows-1,first,first,rows-1)
        vertex = ('varying vec4 color;vec4 seed=%s;void main(){'
                  'gl_Position=vec4($position,0,1);gl_PointSize=5.;color=seed;}') % expression
        for mode in positions:
            count = len(positions[mode])
            def value(data):
                if form == 'constant':
                    return tuple(data.ravel().tolist())
                if form == 'interleaved':
                    records = np.zeros(1,dtype=[('padding',np.float32,3),('data',np.float32,record_shape)])
                    records['data'] = data
                    return gloo.VertexBuffer(records,divisor=2)['data']
                return np.broadcast_to(data,(count,)+record_shape).copy()
            variable = Variable('attribute %s data%s' % (gtype,suffix),value(words))
            program = ModularProgram(vertex,fragment)
            program.vert['data'] = variable
            program.vert['position'] = gloo.VertexBuffer(np.array(positions[mode],np.float32))
            changed = words.copy()
            changed.reshape(-1)[-1] = .5
            for phase,data in [('initial',words),('update',changed),('rebuild',changed)]:
                if phase == 'update':
                    variable.value = value(data)
                    assert not program._need_build
                elif phase == 'rebuild':
                    program.frag = fragment + '\n'
                gloo.set_viewport(0,0,8,8)
                gloo.set_state(blend=False,depth_test=False,cull_face=False)
                gloo.set_line_width(5)
                gloo.clear(color='black')
                program.draw(mode)
                pixel = gloo.read_pixels(alpha=True)[4,4].astype(int)
                expected = [float(data.reshape(-1)[-1]),float(data.reshape(-1)[0]),
                            float(data.reshape(-1)[rows-1]),1]
                wanted = np.rint(np.array(expected)*255).astype(int)
                assert np.max(np.abs(pixel-wanted)) <= 1,(gtype,shape,form,mode,phase,pixel.tolist(),wanted.tolist())
                cases.append(dict(type=gtype,shape=shape,form=form,mode=mode,phase=phase,
                                  pixel=pixel.tolist(),expected=wanted.tolist()))
    return cases
