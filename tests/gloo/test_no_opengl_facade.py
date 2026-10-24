"""Dawn compatibility calls must not activate a native OpenGL loader."""

from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

import vispy
from vispy import gloo
from vispy.gloo import gl
from vispy.gloo.dawn_parser import install_gl_queries


ROOT = Path(__file__).resolve().parents[2]


def test_fresh_import_and_backend_aliases_do_not_load_gl():
    # A base interpreter plus explicitly supplied package paths avoids editable
    # finders silently redirecting source-worktree tests to a different checkout.
    paths = [str(Path(p).resolve()) for p in sys.path
             if p and Path(p).name == 'site-packages' and Path(p).is_dir()]
    code = '''import sys, importlib.abc, json
sys.path.extend(%r)
sys.path.insert(0, %r)
attempts=[]
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == 'OpenGL' or name.startswith('OpenGL.') or 'QtOpenGL' in name:
            attempts.append(name)
            raise RuntimeError('forbidden OpenGL import: '+name)
sys.meta_path.insert(0,Deny())
def audit(event,args):
    if event == 'ctypes.dlopen' and args and args[0]:
        name=str(args[0]).lower()
        if any(s in name for s in ('opengl32','libgl.so','libegl','libgles','osmesa')):
            attempts.append(name)
            raise RuntimeError('forbidden OpenGL load: '+name)
sys.addaudithook(audit)
import vispy, vispy.gloo, vispy.scene
from vispy.gloo import gl
assert vispy.__file__.startswith(%r)
for alias in ('dawn','gl2','gl+','gl2 debug'):
    gl.use_gl(alias)
    assert gl.current_backend.__name__ == 'vispy.gloo.gl.dawn'
from vispy.gloo.gl import gl2, glplus
assert gl2.glGetError() == glplus.glGetError() == 0
assert not attempts, attempts
assert not any(n == 'OpenGL' or n.startswith('OpenGL.') for n in sys.modules)
print(json.dumps({'attempts':attempts,'source':vispy.__file__}))
''' % (paths, str(ROOT / 'src'), str(ROOT / 'src'))
    result = subprocess.run([sys._base_executable, '-I', '-B', '-c', code],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['attempts'] == []


@pytest.fixture
def device(monkeypatch):
    info = dict(ok=True, backend='Vulkan', device='test adapter',
                max_texture_dimension_2d=8192, max_texture_dimension_3d=2048,
                max_sampled_textures_per_shader_stage=16, max_samplers_per_shader_stage=12,
                max_uniform_buffer_binding_size=65536, max_vertex_attributes=24)
    native = SimpleNamespace(device_info=lambda: info)
    monkeypatch.setattr(vispy, '_dawn', native, raising=False)
    return native, info


def test_aliases_preserve_device_queries_before_and_after_install(device):
    native, info = device
    for install in (False, True):
        if install:
            install_gl_queries()
        for alias in ('gl2', 'gl+', 'dawn'):
            gl.use_gl(alias)
            assert gl.glGetParameter(gl.GL_MAX_TEXTURE_SIZE) == 8192
            assert gl.glGetParameter(gl.GL_MAX_TEXTURE_IMAGE_UNITS) == 12
            assert gl.glGetParameter(gl.GL_MAX_UNIFORM_BLOCK_SIZE) == 65536
            assert gl.glGetParameter(gl.GL_RENDERER) == 'test adapter'
    info['max_texture_dimension_2d'] = 4096
    assert gl.glGetParameter(gl.GL_MAX_TEXTURE_SIZE) == 4096
    with pytest.raises(RuntimeError, match='unsupported GL query'):
        gl.glGetParameter(gl.GL_MAX_ARRAY_TEXTURE_LAYERS)


def test_failed_device_is_not_reported_as_capabilities(device):
    _, info = device
    info.update(ok=False, error='no Vulkan adapter')
    with pytest.raises(RuntimeError, match='no Vulkan adapter'):
        gl.glGetParameter(gl.GL_MAX_TEXTURE_SIZE)


@pytest.mark.parametrize('target', ['es2', 'pyopengl2', 'osmesa', 'unknown'])
def test_legacy_gl_backends_fail_without_changing_selection(target):
    gl.use_gl('dawn')
    previous = gl.current_backend
    with pytest.raises(RuntimeError, match='OpenGL backend'):
        gl.use_gl(target)
    assert gl.current_backend is previous


def test_unsupported_immediate_draw_is_not_a_noop():
    gl.use_gl('dawn')
    with pytest.raises(RuntimeError, match='glDrawArrays.*immediate OpenGL'):
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)


def test_current_target_configuration_preserves_unknown_precision(device, monkeypatch):
    native, _ = device
    events = []
    configuration = dict(red_size=8, green_size=8, blue_size=8, alpha_size=8,
                         depth_size=None, depth_size_minimum=24, depth_size_exact=False,
                         stencil_size=8, samples=4, sample_count=4, stereo=False,
                         double_buffer=True, srgb=False, framebuffer_id=29)
    native.framebuffer_config = lambda canvas_id: (events.append(('query', canvas_id)) or configuration)
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=17),
                             context=SimpleNamespace(flush_commands=lambda: events.append('flush')))
    monkeypatch.setattr(gloo.context, 'get_current_canvas', lambda: canvas)
    assert gloo.get_gl_configuration() == configuration
    assert events == ['flush', ('query', 17)]
    assert gl.glGetParameter(gl.GL_SAMPLES) == 4
    assert gl.glGetParameter(gl.GL_DOUBLEBUFFER) is True
    assert gl.glGetParameter(gl.GL_STEREO) is False
    assert configuration['depth_size'] is None


def test_target_queries_need_a_canvas_and_matching_native(device, monkeypatch):
    monkeypatch.setattr(gloo.context, 'get_current_canvas', lambda: None)
    with pytest.raises(RuntimeError, match='current Dawn canvas'):
        gloo.get_gl_configuration()
    with pytest.raises(RuntimeError, match='current Dawn canvas'):
        gl.glGetParameter(gl.GL_VIEWPORT)
    canvas = SimpleNamespace(_backend=SimpleNamespace(_dawn_canvas_id=17),
                             context=SimpleNamespace(flush_commands=lambda: None))
    monkeypatch.setattr(gloo.context, 'get_current_canvas', lambda: canvas)
    with pytest.raises(RuntimeError, match='matching native Dawn build'):
        gloo.get_gl_configuration()


def test_raw_backend_request_does_not_change_config():
    old = vispy.config['gl_backend']
    with pytest.raises(RuntimeError, match='OpenGL backend'):
        vispy.use(gl='es2')
    assert vispy.config['gl_backend'] == old


@pytest.mark.parametrize('backend', ['glfw', 'osmesa', 'egl', 'pyglet', 'pyside2'])
def test_legacy_app_selection_is_explicitly_unavailable(backend):
    from vispy.app import Application
    with pytest.raises(RuntimeError, match='unported OpenGL'):
        Application(backend)
    with pytest.raises(RuntimeError, match='unported OpenGL'):
        vispy.use(app=backend)
