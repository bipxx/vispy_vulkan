# Upstream drafts (not submitted)

These are local drafts for review. **Nothing here has been posted upstream.** Each needs explicit approval, a rebase
onto the project's current main branch and the project's own test suite before a pull request is opened.

Prepared under D28; each change's status is in `compat/host-changes.json`.

**Not planned (D29, 2026-11-01).** The user decided never to open PRs to napari or qtpy ("these are my own project.
nevner pr qtpy and napari"). These drafts, the briefs and the local branches are records of the tested changes,
not submissions.

Both changes are rebased onto the projects' current branches and tested. They live as local branches in
`C:\Users\HEQ\Projects\upstream\{napari,qtpy}`. Both projects' AI policies require the person submitting to test the
change, write the description in their own words and submit it personally, so the files here are facts, not text to
post:
- [napari-brief.md](napari-brief.md) and [napari-lazy-pyopengl-import.patch](napari-lazy-pyopengl-import.patch);
- [qtpy-brief.md](qtpy-brief.md) and [qtpy-lazy-qtopengl.patch](qtpy-lazy-qtopengl.patch).

Context: a Vulkan/Dawn vispy works as a drop-in replacement under stock napari. Neither change removes napari's
declared PyOpenGL dependency, which upstream vispy's `gl+` backend needs.

## napari: stop importing `OpenGL.error` in `canvas.py`

The patch is against napari `main` `b304b99d` (2026-10-30). It holds commits `7d59f65e` and `4fbe6120` (the first,
lazy-import design) and `5e7ff49a` and `0e83c18d` (the final design). Runs `upstream-napari-291` and
`upstream-fixes-294` tested it.

**Change.** `napari/_vispy/canvas.py` imported `OpenGL.error` at module level, only to suppress `GLError` around
`context.finish()` in `_clean_and_update_scenegraph`. `_gl_errors()` now takes `GLError` from `sys.modules` when
PyOpenGL is in use, which is the only case where `finish()` can raise it, and never imports PyOpenGL. The first
design imported it lazily, which would still have loaded the GL library at the first layer removal. Behaviour is
unchanged whenever PyOpenGL is in use.

**Effect, measured** (run `upstream-effects-293`):
- With a vispy whose `gl+` does not use PyOpenGL, importing napari's canvas imports no PyOpenGL and, on Windows,
  loads no GL library. With the final design napari does not import it at layer removal either; a unit test checks
  this.
- With upstream vispy nothing changes, because `_vispy/visuals/markers.py` selects `gl+`, which imports PyOpenGL.
- The earlier claim that `import napari` fails on Linux without a GL library does not survive measurement. Stock
  PyQt6 cannot import `QtGui` there anyway.

**Tested.** The 4 new tests pass. The `_vispy` and `_qt` suites under Xvfb with upstream vispy 0.17.0 give
1249 passed, 1 failed and 83 skipped, against 1245, 1 and 83 on base; the failing test is the same (run
`upstream-fixes-294`).

## qtpy: import Qt6 OpenGL modules only when a QOpenGL name is used

The patch is against qtpy `master` `70f0e887` (2026-10-30). It holds commits `781e0378` (tests) and `7e4af60`
(change). Run `upstream-qtpy-292` tested `d1f7c600`. `7e4af60` rewords only its comments and message, and run
`upstream-fixes-294` re-tested it under PyQt6. The 2.4.3 draft no longer applied, so the change was redone by hand.

**Change.** The existing module `__getattr__` now also imports `<binding>.QtOpenGL` or `QtOpenGLWidgets` on the
first access to a `QOpenGL*` or `QAbstractOpenGL*` name, or to `QOpenGLWidget`, and caches the name. Error behaviour:
- a failed import registers every name in `_QTOPENGL_NAMES` as missing, as before;
- unknown names still raise `AttributeError`.

`from qtpy.QtGui import *` no longer copies the QOpenGL names on Qt6; an `__all__` alternative is possible.

**Effect, measured** (run `upstream-effects-293`):
- Patched qtpy stops importing Qt6's QtOpenGL modules, and so stops loading `Qt6OpenGL.dll` and
  `Qt6OpenGLWidgets.dll` on Windows.
- It does not change whether the system GL library is loaded. On Windows these imports never load `opengl32.dll`; on
  Linux `PyQt6.QtGui` itself loads libGL, libEGL and libGLX. The earlier claim that these modules load the system
  OpenGL library was wrong.
- Import time changes by about 1 ms.

**Tested.** The 6 new tests pass, and the whole suite's failing set is unchanged under PyQt5, PyQt6, PySide6
(Windows) and PySide2 (Linux, CPython 3.10).
