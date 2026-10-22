"""Full-command scope controls including first-draw program association."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from smooth_line_mechanism import training_probes
from smooth_line_training_commands import expected_batch, validate_complete_commands
sys.path.pop(0)


@pytest.mark.parametrize('initial', (False, True))
def test_complete_batch_accepts_only_the_declared_program_lifecycle(initial):
    probe = training_probes()[0]
    commands = expected_batch(probe, 4, 3, (5, 6) if initial else None)
    validate_complete_commands(commands, probe, 4, 3, initial)


@pytest.mark.parametrize('kind', ('framebuffer', 'attribute', 'foreign_data', 'data_offset',
                                 'late_data', 'shader', 'stride', 'duplicate_link'))
def test_full_batch_refuses_non_func_mutations(kind):
    probe = training_probes()[0]
    commands = copy.deepcopy(expected_batch(probe, 4, 3, (5, 6)))
    if kind == 'framebuffer':
        commands.insert(3, ['FRAMEBUFFER', 2, True])
    elif kind == 'attribute':
        commands.insert(-2, ['ATTRIBUTE', 4, 'a_position', 'vec2', [9, 8, 0], None])
    elif kind == 'foreign_data':
        commands.insert(-2, ['DATA', 9, 0, {}])
    elif kind == 'data_offset':
        commands[-3][2] = 8
    elif kind == 'late_data':
        commands[-3], commands[-2] = commands[-2], commands[-3]
    elif kind == 'shader':
        commands[5][3] = 'void main() {}'
    elif kind == 'stride':
        commands[14][4][1] = 16
    else:
        commands.insert(11, ['LINK', 4])
    with pytest.raises(ValueError):
        validate_complete_commands(commands, probe, 4, 3, initial=True)
