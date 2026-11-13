# qtpy: import Qt6 OpenGL modules only when a QOpenGL name is used (brief)

Facts for the person submitting this change. This is not a PR description. Spyder, which maintains qtpy, follows
NumPy's AI policy. You must:
- disclose AI use on the PR;
- not use AI to create or interact with issues or PRs;
- write the description and any comments in your own words.

## Branch

- Clone: `C:\Users\HEQ\Projects\upstream\qtpy`, branch `lazy-qtopengl`, local only.
- Base: qtpy `master` `70f0e887` (2026-10-30, "PR: Use PyQt6 by default (#538)").
- Commits:
  - `781e0378`: 6 tests in `tests/test_qtgui.py` and `tests/test_qtwidgets.py`.
  - `7e4af60`: the change in `qtpy/QtGui.py` and `qtpy/QtWidgets.py`. It replaces `d1f7c600`, whose two comments and
    message said the OpenGL modules load the system OpenGL library; run 293 disproved that, and only that wording
    changed.
- The diff from base is in `qtpy-lazy-qtopengl.patch`, next to this file. qtpy titles PRs `PR: ...` and targets
  `master`. The commit messages carry a `Co-Authored-By: Claude` trailer; reword or squash them as you like.

## What changes

On Qt6, `qtpy.QtGui` no longer star-imports `QtOpenGL`, and `qtpy.QtWidgets` no longer imports
`QtOpenGLWidgets.QOpenGLWidget`, at import time (#387 made them eager). The module `__getattr__` imports them on the
first access to a `QOpenGL*` or `QAbstractOpenGL*` name, or to `QOpenGLWidget`, and caches the name. Error behaviour:
- if the import fails, every name in `_QTOPENGL_NAMES` is registered as missing, and accessing one raises
  `QtModuleNotInstalledError`, as today;
- an unknown `QOpenGL*` name is still an `AttributeError`.

Behaviour change to point out: `from qtpy.QtGui import *` no longer copies the `QOpenGL*` names on Qt6. A test pins
this. An alternative, if reviewers want star-import compatibility, is an `__all__` that lists those names. A star
import would then trigger the lazy import.

## What it does (measured, run `upstream-effects-293`)

- **Windows, PyQt6 and PySide6 6.12.0.**
  - Stock master imports `<binding>.QtOpenGL` and `QtOpenGLWidgets`, and loads `Qt6OpenGL.dll` and
    `Qt6OpenGLWidgets.dll`.
  - Patched, it imports neither.
  - Neither version loads `opengl32.dll` at these imports.
- **Linux, PyQt6.** `import PyQt6.QtGui` alone already maps libEGL, libGL and libGLX, so the change does not affect
  which GL libraries are loaded. Without libGL, `QtGui` cannot be imported at all.
- **Import time.** `PyQt6.QtOpenGL` costs about 1.3 ms; whole-import times differ within noise.

So the effect is small: applications that never use OpenGL stop importing Qt's OpenGL modules. Do not claim that it
avoids loading the system OpenGL library, or that it is faster. The 2026-10-28 draft README made the first claim, and
it was wrong for Windows.

## Tests run

- **The 6 new tests** (Qt6-only ones use qtpy's own `skipif`):
  - `test_qtgui_import_defers_qtopengl`
  - `test_qopengl_names_resolve_on_first_access`
  - `test_unknown_qopengl_name_raises_attribute_error`
  - `test_missing_qtopengl_raises_module_not_installed`
  - `test_star_import_on_qt6_omits_qopengl_names`
  - `test_qopenglwidget_resolves_on_first_access`

  On the tests-only commit under PyQt6, 3 of them fail as expected. Two mutations failed their tests: not registering
  the missing names, and narrowing the name prefixes.
- **Whole suite, base against patched** (run `upstream-qtpy-292`). The failing set is the same on both sides for every
  binding:

  | Binding | Platform | base (passed / failed) | patched (passed / failed) | The failures |
  | --- | --- | --- | --- | --- |
  | PyQt5 5.15.11 | Windows | 122 / 1 | 123 / 1 | `test_qfontmetrics_width`, offscreen |
  | PyQt6 6.12.0 | Windows | 115 / 1 | 121 / 1 | `test_qfontmetrics_width`, offscreen |
  | PySide6 6.12.0 | Windows | 133 / 1 | 139 / 1 | `test_qfontmetrics_width`, offscreen |
  | PySide2 5.15.2.1 | Linux, CPython 3.10, pytest-qt 4.2.0 | 122 / 3 | 123 / 3 | 3 failures + 1 collection error |

  PySide2's collection error is `tests/test_qtmultimedia.py`, which needs a system library (libpulse-mainloop-glib)
  that the machine lacks.

  Those runs used `d1f7c600`. On `7e4af60`, in an environment identical to run 292's PyQt6 one, the 6 new tests pass
  and the whole suite again gives 115 / 1 on base against 121 / 1 patched (run `upstream-fixes-294`).
- **Lint.** qtpy's pinned black 23.11.0 and ruff 0.1.6 are clean (logs in run `upstream-fixes-294`).
- **Not run:**
  - macOS;
  - Qt 6 versions other than 6.12;
  - conda builds (where QtOpenGL can be a separate package);
  - qtpy's CI matrix.

## Submitting

- **AI policy** (spyder-ide/spyder `CONTRIBUTING.md`, "AI Policy", adopting NumPy's): disclose AI use; do not let AI
  create or interact with the PR; write the description and comments in your own words; be ready to explain every
  line.
- **Timing.** The v2.5.0 milestone is open, with merges on 2026-10-29 and 2026-10-30.
