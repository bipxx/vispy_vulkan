# napari: stop importing `OpenGL.error` in `canvas.py` (brief)

Facts for the person submitting this change. This is not a PR description: napari's AI policy asks that you
understand and test the change yourself, write the description, and submit the PR personally.

## Branch

- Clone: `C:\Users\HEQ\Projects\upstream\napari`, branch `lazy-pyopengl-import`, local only.
- Base: napari `main` `b304b99d` (2026-10-30, after v0.10.0).
- Commits (squash them if you like; each message carries a `Co-Authored-By: Claude` trailer):
  - `7d59f65e`: tests for a lazy import.
  - `4fbe6120`: the lazy import (the first design).
  - `5e7ff49a`: a test that `_gl_errors()` never imports `OpenGL.error`.
  - `0e83c18d`: the final design, below.
- The diff from base is in `napari-lazy-pyopengl-import.patch`, next to this file.

## Why

`canvas.py` imports `OpenGL.error` at module level (line 15) only to suppress `GLError` around
`self._scene_canvas.context.finish()` in `_clean_and_update_scenegraph`.
- **The change.** `canvas.py` drops that import. `_gl_errors()` returns `(GLError,)` when `OpenGL.error` is already
  in `sys.modules`, and `()` otherwise; it never imports PyOpenGL.
- **Why that is safe.** `context.finish()` can raise `GLError` only through PyOpenGL, which vispy's `gl+` backend
  imports. When PyOpenGL is not in use there is nothing to suppress.
- **Why not a lazy import.** The first design imported `OpenGL.error` lazily at the first layer removal, so it would
  still have loaded the GL library then.

## What it does (measured, run `upstream-effects-293`)

These are Windows measurements of `import napari._vispy.canvas` on commit `4fbe6120`. The final commit changes only
the body of `_gl_errors()`, which importing does not call. The base and patched pairs differ only by the change.

| vispy | napari | PyOpenGL imported | `opengl32.dll` loaded |
| --- | --- | --- | --- |
| a build whose `gl+` does not use PyOpenGL (this project's) | base | yes | yes |
| same | patched | no | no |
| upstream 0.17.0 | base | yes | yes |
| upstream 0.17.0 | patched | yes | yes |

- **At layer removal.** With the final design napari does not import PyOpenGL there either.
  `test_gl_errors_does_not_import_pyopengl` checks this as a unit test; it was not measured in a running viewer.
- **No change with upstream vispy.** `_vispy/visuals/markers.py` calls `use(gl='gl+')` at import, and upstream
  vispy's `gl+` imports PyOpenGL. Expect reviewers to ask about this. The benefit is for vispy builds that do not use
  PyOpenGL.
- **Import time.** PyOpenGL's own import is about 2.5 ms; whole-import times differ within noise. Do not claim a
  speed-up.
- **Linux without a GL library.** Not a benefit: stock PyQt6 cannot import `QtGui` without libGL (measured in the
  same run), so napari cannot start there either way. Do not claim headless or container support.
- **napari's other PyOpenGL import.** `utils/info.py` still imports PyOpenGL inside `sys_info()`, the version
  report, when that is called.

## Tests run

- **The 4 new tests** in `src/napari/_vispy/_tests/test_canvas.py`:
  - `test_canvas_has_no_module_level_opengl_import`
  - `test_gl_errors_returns_pyopengl_error`
  - `test_gl_errors_does_not_import_pyopengl`
  - `test_layer_removal_still_suppresses_gl_error`

  `test_gl_errors_does_not_import_pyopengl` fails on the lazy-import design: it re-imports `OpenGL.error` and returns
  `(GLError,)`. All 4 pass on `0e83c18d`. Run `upstream-napari-291` also caught two mutations of the first design:
  removing the `GLError` suppression, and narrowing its except clause.
- **`src/napari/_vispy` and `src/napari/_qt`** ran under Xvfb with Mesa software rendering
  (`LIBGL_ALWAYS_SOFTWARE=1`), upstream vispy 0.17.0, PyQt6 6.12.0 and CPython 3.12.8 (run `upstream-fixes-294`):

  | | passed | failed | skipped |
  | --- | --- | --- | --- |
  | base | 1245 | 1 | 83 |
  | patched (`0e83c18d`) | 1249 | 1 | 83 |

  The same test fails on both: `test_help_menu.py::test_tour_escape_closes_regardless_of_focus`, a focus wait that
  times out with no window manager. Run 291 gave the same picture for the first design.
- **Lint.** `ruff format --check` and `ruff check` with napari's pinned ruff 0.17.2 are clean (logs in run
  `upstream-fixes-294`).
- **Not run:**
  - napari's test suite on Windows or macOS, with PySide6, or on other Python versions;
  - napari's other test directories.

  napari's CI covers these.

To rerun locally, in a fresh environment from the branch:

```
pip install -e ".[pyqt6,testing]"
pytest src/napari/_vispy/_tests/test_canvas.py
```

## Submitting

- **PR template sections:** "References and relevant issues" and "Description". No related napari issue or PR was
  found (search: `OpenGL.error`, PyOpenGL import).
- **AI policy** (https://napari.org/dev/developers/contributing/ai.html): do not let an AI agent submit the PR;
  submit only what you have understood and tested; keep the description short and about why; reply to reviewers
  yourself.
