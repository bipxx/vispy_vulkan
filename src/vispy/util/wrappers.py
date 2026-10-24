# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""
Some wrappers to avoid circular imports, or make certain calls easier.

The idea of a 'global' vispy.use function is that although vispy.app
and vispy.gloo.gl can be used independently, they are not complely
independent for some configureation. E.g. when using real ES 2.0,
the app backend should use EGL and not a desktop OpenGL context. Also,
we probably want it to be easy to configure vispy to use the ipython
notebook backend, which requires specific config of both app and gl.

This module does not have to be aware of the available app and gl
backends, but it should be(come) aware of (in)compatibilities between
them.
"""

import subprocess
from .config import _get_args


def use(app=None, gl=None):
    """Select a Dawn-compatible application or GL-named interface.

    ``app`` selects PyQt5, PyQt6, PySide6, dawn_headless, or the supported
    image-transport notebook backend. ``gl`` selects ``dawn``; ``gl2`` and
    ``gl+`` are compatibility aliases and do not enable native OpenGL or
    arbitrary GL extensions. Legacy context-based application and GL backends
    fail explicitly rather than activating an OpenGL fallback.
    """
    if app is None and gl is None:
        raise TypeError('Must specify at least one of "app" or "gl".')

    if app is not None:
        from ..app.backends import LEGACY_BACKEND_NAMES
        if app.lower() in LEGACY_BACKEND_NAMES:
            raise RuntimeError('Application backend %r requires an unported '
                               'OpenGL context path.' % app)

    # Apply now
    if gl:
        from .. import gloo, config
        gloo.gl.use_gl(gl)
        config['gl_backend'] = gl
    if app:
        from ..app import use_app
        use_app(app)


def run_subprocess(command, return_code=False, **kwargs):
    """Run command using subprocess.Popen

    Run command and wait for command to complete. If the return code was zero
    then return, otherwise raise CalledProcessError.
    By default, this will also add stdout= and stderr=subproces.PIPE
    to the call to Popen to suppress printing to the terminal.

    Parameters
    ----------
    command : list of str
        Command to run as subprocess (see subprocess.Popen documentation).
    return_code : bool
        If True, the returncode will be returned, and no error checking
        will be performed (so this function should always return without
        error).
    **kwargs : dict
        Additional kwargs to pass to ``subprocess.Popen``.

    Returns
    -------
    stdout : str
        Stdout returned by the process.
    stderr : str
        Stderr returned by the process.
    code : int
        The command exit code. Only returned if ``return_code`` is True.
    """
    # code adapted with permission from mne-python
    use_kwargs = dict(stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    use_kwargs.update(kwargs)

    p = subprocess.Popen(command, **use_kwargs)
    output = p.communicate()

    # communicate() may return bytes, str, or None depending on the kwargs
    # passed to Popen(). Convert all to unicode str:
    output = ['' if s is None else s for s in output]
    output = [s.decode('utf-8') if isinstance(s, bytes) else s for s in output]
    output = tuple(output)

    if not return_code and p.returncode:
        print(output[0])
        print(output[1])
        err_fun = subprocess.CalledProcessError.__init__
        if 'output' in _get_args(err_fun):
            raise subprocess.CalledProcessError(p.returncode, command, output)
        else:
            raise subprocess.CalledProcessError(p.returncode, command)
    if return_code:
        output = output + (p.returncode,)
    return output


def test(*args, **kwargs):
    """Proxy function to delay `.testing` import"""
    from vispy.testing import test as _test  # noqa
    return _test(*args, **kwargs)

test.__test__ = False  # no discover test function as test
