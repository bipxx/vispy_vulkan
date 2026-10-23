"""Full saved GLIR batch contract for the original-GL training provider."""
try:
    from .smooth_line_training_provider import FRAGMENT, VERTEX, expected_vertex_upload
except ImportError:
    from smooth_line_training_provider import FRAGMENT, VERTEX, expected_vertex_upload


def expected_batch(probe, program, buffer, shader_ids=None):
    ids = (program, buffer) + (() if shader_ids is None else tuple(shader_ids))
    if any(type(value) is not int or value <= 0 for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Distinct positive GLIR object IDs required')
    state = [['FUNC', 'glLineWidth', probe.width_units / 256],
             ['FUNC', 'glClearColor', 0., 0., 0., 0.], ['FUNC', 'glClear', 0x4000]]
    upload = [['SIZE', buffer, 16], ['DATA', buffer, 0, expected_vertex_upload(probe)]]
    draw = [['DRAW', program, 'lines', [0, 2], 1], ['FUNC', 'glFinish']]
    if shader_ids is None:
        return upload + state + draw
    if len(shader_ids) != 2:
        raise ValueError('Exactly two shader objects required')
    vertex, fragment = shader_ids
    preamble = [['CREATE', program, 'Program'], ['CREATE', vertex, 'VertexShader'],
                ['DATA', vertex, 0, VERTEX], ['ATTACH', program, vertex],
                ['CREATE', fragment, 'FragmentShader'], ['DATA', fragment, 0, FRAGMENT],
                ['ATTACH', program, fragment], ['LINK', program],
                ['DELETE', vertex], ['DELETE', fragment], ['CREATE', buffer, 'VertexBuffer'],
                ['ATTRIBUTE', program, 'a_position', 'vec2', [buffer, 8, 0], None]]
    return state + preamble + upload + draw


def validate_complete_commands(commands, probe, program, buffer, initial=False):
    shaders = None
    if initial:
        values = [[command[1] for command in commands
                   if len(command) == 3 and command[0] == 'CREATE' and command[2] == kind]
                  for kind in ('VertexShader', 'FragmentShader')]
        if any(len(value) != 1 for value in values):
            raise ValueError('Initial draw must create exactly one shader per stage')
        shaders = tuple(value[0] for value in values)
    if commands != expected_batch(probe, program, buffer, shaders):
        raise ValueError('Complete chronological training GLIR batch differs')
