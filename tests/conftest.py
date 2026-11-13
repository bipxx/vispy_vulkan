from pathlib import Path, PurePosixPath
import shlex

import pytest


@pytest.fixture
def current_preparation():
    """Use the explicit CI preparation selection, never a historical default."""
    root = Path(__file__).resolve().parents[1]
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
