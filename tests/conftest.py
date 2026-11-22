import os
from pathlib import Path, PurePosixPath
import shlex

import pytest


@pytest.fixture
def frozen_source_root():
    """Source input for frozen evidence controls, including full hash validation."""
    return Path(os.environ.get('VISPY_TEST_FROZEN_SOURCE_ROOT',
                               Path(__file__).resolve().parents[1])).resolve()


@pytest.fixture
def frozen_preparation(frozen_source_root):
    """Use the CI preparation selected by the frozen source snapshot."""
    return preparation_paths(frozen_source_root)


@pytest.fixture
def current_preparation():
    """Use the explicit CI preparation selection, never a historical default."""
    return preparation_paths(Path(__file__).resolve().parents[1])


def preparation_paths(root):
    lines = (root / '.github/workflows/cpu-contract.yml').read_text(encoding='utf-8').splitlines()
    commands = {
        'candidate': ('tools/compatibility_candidate.py', '--candidate'),
        'coverage': ('tools/compatibility_coverage.py', '--map'),
        'execution': ('tools/compatibility_execution.py', '--map'),
        'selection': ('tools/compatibility_qualification.py', '--selection'),
    }
    paths = {}
    for key, (script, option) in commands.items():
        matches = [shlex.split(line) for line in lines if script in line]
        assert len(matches) == 1, (key, matches)
        tokens = matches[0]
        value = tokens[tokens.index(option) + 1]
        relative = PurePosixPath(value)
        assert not relative.is_absolute() and '..' not in relative.parts and ':' not in value and '\\' not in value
        paths[key] = root / value
        assert paths[key].is_file(), (key, value)
    assert len({path.parent for path in paths.values()}) == 1, 'CI preparation declarations select different candidates'
    return paths


def pytest_runtest_logreport(report):
    """The gating commands use pytest -q, which hides prints on success.

    The checkpoint log has to show the device, the clear color, the submit
    counters, and the framebuffer comparison. Echo the test's own stdout
    after capture is finished.
    """
    if report.when != "call" or not report.capstdout:
        return
    print(report.capstdout, end="" if report.capstdout.endswith("\n") else "\n")
