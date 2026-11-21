"""Ordinary and failure/recovery contracts for the reviewed utility rows."""
import importlib
import json
import logging
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

import vispy
from vispy.util import Frozen, SimpleBunch, fetching, keys, load_data_file, ptime
from vispy.util import run_subprocess, transforms, use_log_level
from vispy.util.event import EmitterGroup, Event, EventBlocker, EventEmitter, WarningEmitter
from vispy.util.fonts import _triage, list_fonts
from vispy.util.fourier import fft_freqs, stft
from vispy.util.logs import logger
from vispy.util.quaternion import Quaternion
from vispy.util.svg import Document

config_module = importlib.import_module('vispy.util.config')


def test_config_update():
    config = config_module.Config(data_path='first')
    events = []
    config.events.changed.connect(events.append)
    config.update(data_path='second')
    assert [event.changes for event in events] == [{'data_path': 'second'}]

    with pytest.raises(KeyError, match='nonexistent_key'):
        config.update(data_path='third', nonexistent_key=True)
    assert config['data_path'] == 'second'
    assert len(events) == 1
    config.update(data_path='third')
    assert events[-1].changes == {'data_path': 'third'}


def test_configevent():
    event = config_module.ConfigEvent({'data_path': 'first'})
    assert event.type == 'config_change'
    assert event.changes == {'data_path': 'first'}
    with pytest.raises(TypeError, match='changes'):
        config_module.ConfigEvent()
    assert config_module.ConfigEvent({'data_path': 'second'}).changes == {'data_path': 'second'}


def test_get_config_keys():
    schema = config_module.get_config_keys()
    assert str in schema['data_path']
    assert 'gl_backend' in schema
    schema.pop('data_path')
    with pytest.raises(KeyError):
        schema['data_path']
    assert str in config_module.get_config_keys()['data_path']


def test_config_persistence(tmp_path, monkeypatch):
    config = config_module.Config(data_path='first')
    app_dir = tmp_path / 'settings'
    monkeypatch.setattr(config_module, 'config', config)
    monkeypatch.setattr(config_module, '_get_vispy_app_dir', lambda: str(app_dir))
    monkeypatch.delenv('_VISPY_CONFIG_TESTING', raising=False)
    directory = tmp_path / 'datasets'
    with pytest.raises(OSError, match='create=True'):
        config_module.set_data_dir(str(directory), create=False)
    assert not directory.exists()
    assert config['data_path'] == 'first'
    config_module.set_data_dir(str(directory), create=True, save=True)
    assert directory.is_dir()
    assert config['data_path'] == str(directory)
    assert json.loads((app_dir / 'vispy.json').read_text())['data_path'] == str(directory)


def test_get_dpi_x11_probe_and_fallback(monkeypatch):
    from vispy.util.dpi import _linux

    monkeypatch.setenv('DISPLAY', ':99')
    commands = []

    def probe(argv):
        commands.extend(argv)
        if len(commands) == 1:
            return '  resolution:    110x110 dots per inch\n', ''
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(_linux, 'run_subprocess', probe)
    assert 109 <= _linux.get_dpi() <= 111
    with pytest.raises(RuntimeError, match='could not determine DPI'):
        _linux.get_dpi()
    assert _linux.get_dpi(raise_error=False) == 96.0
    assert commands == ['xdpyinfo', 'xdpyinfo', 'xrandr', 'xdpyinfo', 'xrandr']


@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='needs-window: run against a Linux Xvfb screen configured for 110 DPI',
)
def test_get_dpi_xvfb():
    import os
    from vispy.util.dpi import get_dpi

    if os.getenv('VISPY_TEST_XVFB_110_DPI') != '1':
        pytest.skip('needs-window: set VISPY_TEST_XVFB_110_DPI=1 on the 110 DPI Xvfb display')
    assert 109 <= get_dpi() <= 111


def test_emittergroup():
    received = []

    class Source:
        def on_ping(self, event):
            received.append(event.type)

    source = Source()
    group = EmitterGroup(source=source, ping=Event)
    group.ping()
    assert received == ['ping']

    forwarded = []
    group.connect(lambda event: forwarded.append(event.type))
    with pytest.raises(ValueError, match='ping'):
        group.add(new=Event, ping=Event)
    assert list(group) == ['ping']
    group.add(new=Event)
    assert list(group) == ['ping', 'new']
    group.new()
    assert forwarded == ['new']


def test_event():
    token = object()
    event = Event('ping', native=token, value=23)
    assert (event.type, event.value) == ('ping', 23)
    assert event.native is token
    with pytest.raises(AttributeError, match='source'):
        Event('ping', source='reserved')
    assert Event('ping', value=23).source is None


def test_eventblocker():
    emitter = EventEmitter(type='tick')
    first, second = [], []
    emitter.connect(first.append)
    emitter.connect(second.append)
    with EventBlocker(emitter, callback=first.append):
        emitter()
    assert (len(first), len(second)) == (0, 1)

    with pytest.raises(RuntimeError, match='interrupted'):
        with EventBlocker(emitter), EventBlocker(emitter):
            emitter()
            raise RuntimeError('interrupted')
    assert (len(first), len(second)) == (0, 1)
    assert emitter.blocked() is False
    emitter()
    assert (len(first), len(second)) == (1, 2)


def test_eventemitter():
    emitter = EventEmitter(type='tick')
    calls = []
    emitter.connect(lambda event: calls.append('tail'), ref='tail')
    emitter.connect(lambda event: calls.append('head'), before='tail')
    emitter()
    assert calls == ['head', 'tail']

    emitter.disconnect()
    emitter.ignore_callback_errors = False

    def recurse(event):
        emitter(event)

    emitter.connect(recurse)
    event = Event('tick')
    with pytest.raises(RuntimeError, match='loop detected'):
        emitter(event)
    assert event.sources == []
    emitter.disconnect(recurse)
    calls.clear()
    emitter.connect(lambda event: calls.append(event.type))
    emitter(event)
    assert calls == ['tick']


def test_warningemitter():
    emitter = WarningEmitter('deprecated tick', type='tick')
    calls = []
    with use_log_level('warning', record=True, print_msg=False) as messages:
        emitter.connect(lambda event: calls.append('first'))
        emitter.connect(lambda event: calls.append('second'))
        emitter()
    assert len(messages) == 1
    assert 'deprecated tick' in messages[0]
    assert calls == ['second', 'first']

    emitter.disconnect()
    emitter.connect(lambda event: calls.append(event.type))
    emitter.ignore_callback_errors = False

    def fail(event):
        raise ValueError('bad callback')

    emitter.connect(fail)
    calls.clear()
    with pytest.raises(ValueError, match='bad callback'):
        emitter()
    emitter.disconnect(fail)
    emitter()
    assert calls == ['tick']


def test_list_fonts(monkeypatch):
    monkeypatch.setattr(_triage, '_vispy_fonts', ['OpenSans'])
    monkeypatch.setattr(_triage, '_list_fonts', lambda: ['zeta', 'alpha'])
    assert list_fonts() == ['alpha', 'OpenSans', 'zeta']

    results = iter([OSError('discovery failed'), []])

    def discover():
        result = next(results)
        if isinstance(result, OSError):
            raise result
        return result

    monkeypatch.setattr(_triage, '_list_fonts', discover)
    with pytest.raises(OSError, match='discovery failed'):
        list_fonts()
    assert list_fonts() == ['OpenSans']


def test_fourier():
    assert_allclose(abs(stft(np.ones(8), n_fft=8, step=8, window=None))[:, 0], [1, 0, 0, 0, 0])
    assert_array_equal(fft_freqs(8, 8), [0, 1, 2, 3, 4])
    with pytest.raises(ValueError):
        stft(np.ones((2, 4)), n_fft=8)
    assert stft(np.ones(8), n_fft=8, step=8, window=None).shape == (5, 1)


def test_frozen():
    frozen = Frozen()
    frozen.x = 1
    frozen.freeze()
    frozen.x = 2
    assert frozen.x == 2
    with pytest.raises(AttributeError):
        frozen.y = 3
    frozen.unfreeze()
    frozen.y = 3
    assert frozen.y == 3
    frozen.freeze()
    with pytest.raises(AttributeError):
        frozen.z = 4


def test_key():
    key = keys.Key('Enter', 'Return', '\n')
    assert key.name == 'Enter'
    assert key == 'return'
    assert key == keys.Key('Enter')
    assert hash(key) == hash(keys.Key('Enter'))
    with pytest.raises(ValueError):
        keys.ENTER == {}
    assert keys.ENTER == 'Return'


def test_load_data_file(tmp_path, monkeypatch):
    requests = []

    def offline(url, destination):
        requests.append(Path(destination))
        raise RuntimeError('offline')

    monkeypatch.setattr(fetching, '_fetch_file', offline)
    sample = tmp_path / 'sample.bin'
    sample.write_bytes(b'ok')
    assert Path(load_data_file(sample.name, directory=str(tmp_path))).read_bytes() == b'ok'
    assert not requests

    missing = tmp_path / 'missing.bin'
    with pytest.raises(RuntimeError, match='offline'):
        load_data_file(missing.name, directory=str(tmp_path))
    assert requests == [missing]
    missing.write_bytes(b'recovered')
    assert Path(load_data_file(missing.name, directory=str(tmp_path))) == missing
    assert requests == [missing]

    def refresh(url, destination):
        assert url.endswith('/sample.bin')
        Path(destination).write_bytes(b'refreshed')

    monkeypatch.setattr(fetching, '_fetch_file', refresh)
    assert Path(load_data_file(sample.name, directory=str(tmp_path), force_download=True)).read_bytes() == b'refreshed'


def test_set_log_level():
    with use_log_level('warning'):
        assert vispy.set_log_level('debug', return_old=True) == (logging.WARNING, None)
        assert logger.level == logging.DEBUG
        with pytest.raises(ValueError, match='bogus'):
            vispy.set_log_level('bogus')
        assert logger.level == logging.DEBUG
        vispy.set_log_level('info')
        assert logger.level == logging.INFO


def test_use_log_level():
    with use_log_level('debug', match='accept', record=True, print_msg=False) as records:
        logger.debug('accept this')
        logger.debug('reject this')
    assert len(records) == 1
    assert 'accept this' in records[0]

    with use_log_level('warning'):
        with pytest.raises(RuntimeError, match='interrupted'):
            with use_log_level('debug'):
                raise RuntimeError('interrupted')
        assert logger.level == logging.WARNING


def test_ptime(monkeypatch):
    ticks = iter([10.0, 10.125])
    monkeypatch.setattr(ptime, 'systime', SimpleNamespace(perf_counter=lambda: next(ticks)))
    start = ptime.time()
    assert ptime.time() - start == pytest.approx(0.125, abs=1e-5)

    def fail_once():
        if next(ticks) is None:
            raise RuntimeError('counter unavailable')
        return 10.0

    ticks = iter([None, 10.0])
    monkeypatch.setattr(ptime, 'systime', SimpleNamespace(perf_counter=fail_once))
    with pytest.raises(RuntimeError, match='counter unavailable'):
        ptime.time()
    recovered = ptime.time()
    assert isinstance(recovered, float) and math.isfinite(recovered)


def test_quaternion():
    rotation = Quaternion.create_from_axis_angle(90, 0, 0, 1, degrees=True)
    assert_allclose(rotation.rotate_point((1, 0, 0)), [0, 1, 0], atol=1e-6)
    with pytest.raises(ValueError, match='0-length'):
        Quaternion(0, 0, 0, 0, normalize=True)
    assert Quaternion(2, 0, 0, 0, normalize=True).w == 1


def test_run_subprocess():
    python = [sys.executable, '-B', '-S', '-c']
    out, err, code = run_subprocess(python + ['print(42)'], return_code=True)
    assert (out.strip(), err, code) == ('42', '', 0)
    out, err, code = run_subprocess(
        python + ['import sys; print("diagnostic", file=sys.stderr)'], return_code=True
    )
    assert (out, err.strip(), code) == ('', 'diagnostic', 0)

    command = python + ['raise SystemExit(7)']
    with pytest.raises(subprocess.CalledProcessError) as caught:
        run_subprocess(command)
    assert caught.value.returncode == 7
    assert run_subprocess(command, return_code=True) == ('', '', 7)


def test_simplebunch():
    bunch = SimpleBunch(x=1)
    bunch['x'] = 4
    assert bunch.x == 4
    del bunch['x']
    with pytest.raises(AttributeError):
        bunch.x
    bunch.x = 7
    assert bunch['x'] == 7


def test_svg_document(tmp_path):
    path = tmp_path / 'drawing.svg'
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20"><path d="M 0 0 L 50 0"/></svg>'
    path.write_text(svg, encoding='utf-8')
    doc = Document(path)
    assert len(doc.paths) == 1
    vertices, closed = doc.paths[0].vertices[0]
    assert_array_equal(vertices, [[0, 0, 0], [50, 0, 0]])
    assert closed is False
    path.write_text(doc.xml, encoding='utf-8')
    assert_array_equal(Document(path).paths[0].vertices[0][0], [[0, 0, 0], [50, 0, 0]])
    path.write_text('<html/>', encoding='utf-8')
    with pytest.raises(TypeError):
        Document(path)
    path.write_text(svg, encoding='utf-8')
    assert len(Document(path).paths) == 1


def test_affine_map():
    basis = np.vstack([np.zeros(3), np.eye(3)])
    matrix = transforms.affine_map(basis, basis * 2 + [5, -2, 1])
    assert_allclose(matrix @ [2, 3, 4, 1], [9, 4, 9, 1])
    with pytest.raises(np.linalg.LinAlgError):
        transforms.affine_map(np.zeros((4, 3)), np.zeros((4, 3)))
    assert_allclose(transforms.affine_map(basis, basis), np.eye(4))


def test_affine_matrices():
    matrix = transforms.translate((2, -3, 5), dtype=np.float32)
    assert matrix.dtype == np.float32
    assert_array_equal(np.array([1, 2, 3, 1]) @ matrix, [3, -1, 8, 1])
    with pytest.raises(AssertionError):
        transforms.scale((2, 3))
    assert_array_equal(np.diag(transforms.scale((2, 3, 4))), [2, 3, 4, 1])


def test_projections():
    clip = np.array([1, 0, -1, 1]) @ transforms.perspective(90, 1, 1, 9)
    assert_allclose(clip[:3] / clip[3], [1, 0, -1], atol=1e-6)
    with pytest.raises(AssertionError):
        transforms.frustum(1, 1, -1, 1, 1, 9)
    clip = np.array([0, 0, -1, 1]) @ transforms.frustum(-1, 1, -1, 1, 1, 9)
    assert clip[2] / clip[3] == pytest.approx(-1)


def test_vispy_test_dispatch(monkeypatch):
    from vispy.testing import _runners

    calls = []
    monkeypatch.setattr(_runners, '_unit', lambda *args: calls.append(args))
    vispy.test(label='nobackend', extra_arg_string='-q', coverage=True)
    assert calls == [('nobackend', '-q', True)]
    calls.clear()
    with pytest.raises(ValueError, match='invalid-label'):
        vispy.test(label='invalid-label')
    assert not calls
    vispy.test(label='nobackend')
    assert calls == [('nobackend', '', False)]
