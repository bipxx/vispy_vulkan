"""Exercise top-level VisPy entry points with a real headless Dawn backend."""
import subprocess
import sys

import pytest

pytestmark = pytest.mark.gpu


@pytest.mark.parametrize('reject_empty_selection', [False, True], ids=['ordinary', 'recovery'])
def test_use(reject_empty_selection):
    code = """
import sys
import vispy

if sys.argv[1] == 'True':
    try:
        vispy.use()
    except TypeError as error:
        assert 'Must specify' in str(error)
    else:
        raise AssertionError('Empty backend selection was accepted')

vispy.use(app='dawn_headless', gl='dawn')
assert vispy.app.use_app().backend_name.lower() == 'dawn_headless'
assert vispy.config['gl_backend'] == 'dawn'
"""
    result = subprocess.run(
        [sys.executable, '-B', '-S', '-c', code, str(reject_empty_selection)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_sys_info(tmp_path, monkeypatch):
    import vispy
    from vispy.app import _default_app, use_app

    monkeypatch.setenv('_VISPY_TESTING_APP', 'dawn_headless')
    monkeypatch.setattr(_default_app, 'default_app', None)
    use_app('dawn_headless')
    path = tmp_path / 'info.txt'
    report = vispy.sys_info(path)
    assert path.read_text() == report
    assert 'backend:  dawn_headless' in report.lower()
    assert 'MAX_TEXTURE_SIZE:' in report
    assert 'App info-gathering error' not in report

    path.write_text('sentinel')
    with pytest.raises(OSError, match='overwrite=True'):
        vispy.sys_info(path)
    assert path.read_text() == 'sentinel'
    overwritten = vispy.sys_info(path, overwrite=True)
    assert path.read_text() == overwritten
    assert 'Platform:' in overwritten and 'App info-gathering error' not in overwritten
