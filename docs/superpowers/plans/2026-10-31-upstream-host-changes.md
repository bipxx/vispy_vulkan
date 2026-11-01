# Upstream-First Host Changes (D28) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Small host changes reach napari users through napari and qtpy releases, while hot-swap rows keep stock PyPI hosts and the strict profile keeps its host patches until those releases exist.

**Architecture:** Three tracks.
1. **This repository** records the policy (D28) and registers every host patch with its upstream status, enforced by a CPU contract. The hot-swap audit also learns to name the host package behind each GL event.
2. **The two W12 changes** are prepared on napari `main` and qtpy `master`, in clones outside managed scratch. They are tested from `git archive` exports inside registered runs, measured, and posted only after the user approves each PR.
3. **Adoption.** When a host release contains a change, hot-swap rows move to that release, and the matching strict patch shrinks at the next requalification.

**Tech Stack:**
- Python 3.12 via uv; pytest and pytest-qt
- napari `main` (after v0.10.0) with upstream vispy 0.17.x
- qtpy `master` (after v2.4.3) with PyQt5, PyQt6 and PySide6
- `gh`; the WSL rootfs with Xvfb and Mesa
- `tools/audit_hot_swap.py`, `tools/build_hygiene.py`

**Spec:**
- This plan's D28 text (Task 1): proposed, and it needs the user's approval.
- `docs/upstream-drafts/README.md`: the two changes and the checks they need.
- `docs/superpowers/plans/2026-10-28-napari-hot-swap.md`, "Profiles".
- The consolidated plan's W12 row and "Standing rules".

## Where things stand (2026-10-31)

- **No upstream issue or PR exists** for either change. A search of napari and qtpy found none.
- **napari v0.10.0 is PyPI's current napari** (released 2026-10-30). It still has `from OpenGL.error import GLError` at `src/napari/_vispy/canvas.py:15`. It still requires `vispy>=0.17.0,<0.18`, `qtpy>=2.4.0` and `PyOpenGL>=3.1.10`. The qualified hot-swap rows use napari 0.9.2, so W16 (Task 9) is new work.
- **napari's change only matters with a vispy whose `gl+` does not use PyOpenGL.** napari's `_vispy/visuals/markers.py` calls `use(gl='gl+')` at import. Upstream vispy 0.17.0 then imports PyOpenGL (`gloo/gl/_pyopengl2.py:10`), so with upstream vispy, PyOpenGL loads anyway. The PR text claims only what Task 6 measures.
- **qtpy `master` (`70f0e887`, 2026-10-30) still imports Qt6's OpenGL modules eagerly** (`qtpy/QtGui.py:73`, `qtpy/QtWidgets.py:59`). Its last release is v2.4.3 (2025-02-11). A v2.5.0 milestone is open, with merges on 2026-10-29 and 2026-10-30. qtpy's tests live in the top-level `tests/`.

## Global Constraints

- **The hot-swap claim** (hot-swap plan, Profiles): "All rendering goes through Dawn. vispy and `vispy._dawn` never import, load or resolve GL. **No GL context is created or made current, and no GL draw runs** in the process. GL loads by host packages are recorded and attributed to the module and stack that caused them, not claimed absent."
- **The strict profile is untouched.** "The strict rows and policy stay unchanged. The hot-swap profile is a separate, explicitly narrower claim." A row that uses a patched host is not a hot-swap row.
- **Approvals.** W12 and every upstream post need explicit approval. Each draft "needs explicit approval, a rebase onto the project's current main branch and the project's own test suite before a pull request is opened" (drafts README). Forks, pushes, PRs, comments and replies are outward-facing, so show their exact text to the user first.
- **Upstream AI policies.** napari's AI policy says: "**Do not allow AI agents to submit PRs for you**, and **do not submit an AI-generated PR you haven't personally understood and tested**". Spyder, which maintains qtpy, adopted NumPy's AI policy: disclose AI use on the PR, "You must not use AI to autonomously create or interact with issues or pull requests", and write descriptions and comments "in your own words". So the agent never creates, comments on or replies to an upstream issue or PR. The user tests the branches, writes the descriptions and submits both PRs personally; the agent prepares the branches and factual briefs.
- **D2:** nothing is published before the release gates pass. This plan publishes no wheel.
- **Hygiene** (AGENTS.md, `docs/build-hygiene.md`):
  - Register each run with `tools/build_hygiene.py preflight --run-id <id> --owner upstream-host-changes --expected-peak-bytes <n> --register`, using the next free id (290 or higher).
  - Keep scratch only in `build/work/<run-id>`. No Git repositories, aliases or hardlinked writable files go in managed scratch.
  - Set `UV_LINK_MODE=copy` for every environment.
  - Close each run in this order: `terminal.json` (after all writers stop), `plan --manifest`, `apply --plan`, `audit`.
  - Retain sources by commit, never by a mutable path.
- **Python in this repository:** `uv run --no-sync --frozen python -B …` from the repo root. Call scratch interpreters directly. Never use bare `python`.
- **Upstream clones** are `C:\Users\HEQ\Projects\upstream\napari` and `C:\Users\HEQ\Projects\upstream\qtpy`, outside this repository and outside managed scratch. Tests never run from a clone; they run from `git archive` exports in scratch.
- **Evidence:**
  - Write each measurement's expectation before running it.
  - No xfail or skip in this repository's suites.
  - Upstream tests follow upstream conventions; qtpy marks Qt6-only tests with `skipif`. Our runs cover every binding, so each such test runs where it applies, and the run records the counts.
  - Never normalize line endings (`.gitattributes` is `* -text`).
- **GUI runs:**
  - None while the user is in napari, or while another owner's R1 launch is registered in `build/work`.
  - napari's upstream suites run in WSL under Xvfb. qtpy's run with `QT_QPA_PLATFORM=offscreen`.
- **Publishing this repository's files:**
  - Go through `..\vispy_vulkan-publication`, and only while no other owner has a branch checked out there.
  - Use `git commit --only <paths>`, never `git add -A`.
  - Merge through the 11 required checks with `gh pr merge N --auto --merge`.
- **Attribution:** commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## Review Focus

1. **PyOpenGL is installed but its GL library is missing or can't load.** `_gl_errors()` must return `()` for both `ImportError` and `OSError`. Test: Task 4, `test_gl_errors_is_empty_when_the_gl_library_cannot_load`.
2. **Layer removal on a working GL stack.** Upstream vispy's `context.finish()` can still raise `GLError`, and it must stay suppressed. Test: Task 4, `test_layer_removal_still_suppresses_gl_error`.
3. **Star imports on Qt6.** `from qtpy.QtGui import *` no longer copies the `QOpenGL*` names, so a caller relying on that gets a `NameError`.
   - Test: Task 5, `test_star_import_on_qt6_omits_qopengl_names`, pins the new behaviour.
   - The brief flags it. The `__all__` alternative is built only if reviewers ask for it (Task 8).
4. **A binding without its QtOpenGL module.** The first access must raise qtpy's existing `QtModuleNotInstalledError`, not `AttributeError` and not an error at import. Test: Task 5, `test_missing_qtopengl_raises_module_not_installed`.
5. **A hot-swap lock that picks up a patched host.** A regenerated lock could carry `napari==0.9.2+vispynogl.1` or a `file:` napari. Test: Task 2, `test_stock_swap_locks_name_stock_hosts_only`.

---

## File Structure

This repository:
- `docs/superpowers/plans/2026-10-28-consolidated-plan.md`: the D28 row, the W12 and new W16 rows, a standing rule and the plan index entry (Task 1).
- `docs/superpowers/plans/2026-10-28-napari-hot-swap.md`: one sentence under Profiles (Task 1).
- `docs/upstream-drafts/`:
  - the README and both `*.patch` drafts, refreshed against the upstream heads;
  - new `napari-pr.md` and `qtpy-pr.md` (Tasks 4, 5 and 7).
- `compat/host-changes.json` (new): every host patch, its profiles, why vispy cannot fix it, and its upstream status (Task 2).
- `tests/contract/test_host_change_registry.py` (new) and `tests/contract/curated_contracts.py`: the registry's CPU contract and its registration (Task 2).
- `tools/hot_swap/policy.py`: `first_caller()` and `host_gl_sources()` (Task 3).
- `tools/hot_swap/host_sources.py` (new): prints the host GL sources of audit reports (Task 3).
- `tests/contract/test_hot_swap_policy.py`: tests for the two functions and the command (Task 3).

Upstream clones:
- napari: `src/napari/_vispy/canvas.py` and `src/napari/_vispy/_tests/test_canvas.py` (Task 4).
- qtpy: `qtpy/QtGui.py`, `qtpy/QtWidgets.py`, `tests/test_qtgui.py` and `tests/test_qtwidgets.py` (Task 5).

Runs, each registered, closed and retained:
- `upstream-napari-<id>` (Task 4)
- `upstream-qtpy-<id>` (Task 5)
- `upstream-effects-<id>` (Task 6)
- `napari-010-baseline-<id>` (Task 9)
- one adoption run per host release (Task 10)

## Gates

- **Gate A, before Task 1:** the user approves D28 and this plan.
  - Tasks 2–6 then need no further approval.
  - Task 9 needs the user's go-ahead for its GUI runs.
- **Gate B, before Task 8:** the agent hands the user each branch, its final diff and a factual brief (Task 7). The user decides whether to submit, and does so personally.
- **Outside our control:** upstream review, merge and release. Task 10 starts when a release exists.

---

### Task 1: Record D28, the host-change rule and W16

**Files:**
- Modify `docs/superpowers/plans/2026-10-28-consolidated-plan.md`:
  - the Decisions table, after D27;
  - the "No decisions are open" sentence;
  - the W12 row and the Hot swap table;
  - "Standing rules" and "Plan index".
- Modify `docs/superpowers/plans/2026-10-28-napari-hot-swap.md`: Profiles, after "The strict rows and policy stay unchanged…".
- Modify `docs/upstream-drafts/README.md`: the paragraph under the title.

**Interfaces:**
- Produces:
  - decision `D28` and work item `W16`;
  - the registry path `compat/host-changes.json`, which Task 2 creates.

- [ ] **Step 1: Add the D28 row after D27.** Put the user's approval words in place of `<quote>`:

```markdown
| D28 | **Minor host changes are allowed, upstream first** (user, 2026-10-31: "<quote>"). A host behaviour that needs a change outside vispy is fixed in this order: in vispy, which this project ships; upstream, in the host's own project, with the user's approval for each post (W12); or as a host patch used only by strict rows and registered in `compat/host-changes.json` with its upstream status. Hot-swap rows keep stock PyPI hosts; a row with a patched host is not a hot-swap row. A strict patch shrinks only at a requalification (R2 under D1), after a host release contains its upstream change. | Replacing only `vispy` is the hot swap's value. Patched hosts would need our own index (PyPI rejects local versions), re-patching for each host release, and a third profile. The two W12 changes are small: napari imports `OpenGL.error` lazily; qtpy imports Qt6's OpenGL modules lazily. Plan: `2026-10-31-upstream-host-changes.md`. |
```

- [ ] **Step 2: Replace the decision summary sentence** with "No decisions are open. The latest is D28, upstream-first host changes."
- [ ] **Step 3: Update W12's "Needs" cell.** Append: "Under D28 (plan `2026-10-31-upstream-host-changes.md`). Each post needs approval; status in `compat/host-changes.json`."
- [ ] **Step 4: Add W16 to the Hot swap table:**

```markdown
| W16 | Hot-swap baseline on napari 0.10.0, PyPI's napari since 2026-10-30 (still `vispy>=0.17.0,<0.18`, `qtpy>=2.4.0`, `PyOpenGL>=3.1.10`) | On stock 0.10.0 with the current test wheel, every W2 case passes or has a recorded, triaged cause, and the stock scenario reaches `PASS_HOT_SWAP_GATES` | GUI runs need the user's go-ahead. Task 9 of `2026-10-31-upstream-host-changes.md`. |
```

- [ ] **Step 5: Add the standing rule** "**Host changes (D28).** Fix in vispy first, upstream second, and with a strict-only host patch last. Every file in `compat/host-patches/` is registered in `compat/host-changes.json`, and hot-swap locks name stock hosts only; `tests/contract/test_host_change_registry.py` checks both."
- [ ] **Step 6: Link the plan.**
  - Add this plan to "Plan index".
  - Add to the hot-swap plan's Profiles: "Host changes follow D28 in the consolidated plan: upstream first, and hot-swap rows keep stock hosts."
- [ ] **Step 7: Update the drafts README.** Keep "Nothing here has been posted upstream." and add "Prepared under D28; each change's status is in `compat/host-changes.json`."
- [ ] **Step 8: Check the drift.**
  - Run: `uv run --no-sync --frozen python -B tools/publication_drift.py ../vispy_vulkan-publication --expect docs/superpowers/plans/2026-10-28-consolidated-plan.md docs/superpowers/plans/2026-10-28-napari-hot-swap.md docs/superpowers/plans/2026-10-31-upstream-host-changes.md docs/upstream-drafts/`
  - Expected: no unexplained differences.
- [ ] **Step 9:** publish with Tasks 2 and 3 (Task 3, Step 6).

### Task 2: Host-change registry and its contract

**Files:**
- Create: `compat/host-changes.json`
- Create: `tests/contract/test_host_change_registry.py`
- Modify: `tests/contract/curated_contracts.py` (`MODULES`)

**Interfaces:**
- Produces: registry schema 1, read by Tasks 7, 8 and 10. Stock-swap locks are not listed in it: they name local wheel paths and stay local (`.gitignore`: `/compat/host-environments/*`), so the contract finds them by their header ("only VisPy is replaced") wherever they exist.

```json
{
  "schema": 1,
  "decision": "D28",
  "patches": [
    {"patch": "compat/host-patches/napari-0.9.2-no-opengl.patch", "sha256": "<sha256 of the file's bytes>",
     "host": "napari", "version": "0.9.2", "profiles": ["strict"],
     "why_not_vispy": "napari imports OpenGL.error at module level and declares PyOpenGL; vispy can change neither.",
     "upstream": [{"change": "docs/upstream-drafts/napari-lazy-pyopengl-import.patch", "status": "draft",
                   "pr": null, "released_in": null}],
     "strict_only": "<the patch's hunks that its upstream changes do not contain, by file>"}
  ]
}
```

**Registry contents:**
- Statuses: `draft`, `approved`, `posted`, `merged`, `released`, `declined`, and `not_planned` (which carries a `reason`).
- **The napari and qtpy patches** each point at their draft. qtpy's `why_not_vispy` reads: "qtpy imports Qt6's OpenGL modules whenever qtpy.QtGui or qtpy.QtWidgets is imported; vispy cannot change that."
- **The two Glue patches** each carry one `not_planned` entry whose reason says why no upstream change is planned.

- [ ] **Step 1: Write the failing tests.** Use three helpers:
  - `registry() -> dict`;
  - `header(path) -> list[str]`, a lock's leading comment lines;
  - `requirements(path) -> list[tuple[str, str]]`, which returns each requirement line's normalized name and its text before ` \`.

```python
STATUSES = {'draft', 'approved', 'posted', 'merged', 'released', 'declined', 'not_planned'}
PR = re.compile(r'^https://github\.com/(napari/napari|spyder-ide/qtpy)/pull/\d+$')

def test_every_host_patch_is_registered_once():
    names = [entry['patch'] for entry in registry()['patches']]
    on_disk = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'compat/host-patches').glob('*.patch')]
    assert sorted(names) == sorted(on_disk) and len(names) == len(set(names))

def test_registered_hashes_match_the_patch_files():
    for entry in registry()['patches']:
        assert hashlib.sha256((ROOT / entry['patch']).read_bytes()).hexdigest() == entry['sha256'], entry['patch']

def test_host_patches_serve_strict_rows_only():
    assert all(entry['profiles'] == ['strict'] for entry in registry()['patches'])

def test_each_patch_says_why_vispy_cannot_fix_it():
    assert all(entry['why_not_vispy'].strip() for entry in registry()['patches'])

def test_upstream_entries_are_consistent():
    for entry in registry()['patches']:
        assert entry['upstream'], entry['patch']
        for change in entry['upstream']:
            assert change['status'] in STATUSES
            if change['status'] == 'not_planned':
                assert change['reason'].strip()
            if change['status'] == 'draft':  # drafts stay local until posting is approved (user, 2026-10-28)
                assert change['change'].startswith('docs/upstream-drafts/') and change['change'].endswith('.patch')
            if change['status'] == 'approved':
                assert (ROOT / change['change']).is_file()
            if change['status'] in {'posted', 'merged', 'released', 'declined'}:
                assert PR.match(change['pr'] or '')
            assert (change.get('released_in') is not None) == (change['status'] == 'released')

def test_stock_swap_locks_name_stock_hosts_only():
    for lock in (ROOT / 'compat/host-environments').glob('*.txt'):
        if any('only VisPy is replaced' in line for line in header(lock)):
            for name, spec in requirements(lock):
                if name != 'vispy':
                    assert '@' not in spec and '+' not in spec, (lock.name, name, spec)
```

- [ ] **Step 2: Run the tests and see them fail.**
  - Run: `uv run --no-sync --frozen python -B -m pytest tests/contract/test_host_change_registry.py -q -p no:cacheprovider`
  - Expected: `6 failed`, each with `FileNotFoundError` for `compat/host-changes.json`.
- [ ] **Step 3: Create `compat/host-changes.json`** with the four patch entries. Compute the hashes from the files' bytes, and fill `strict_only` by comparing each patch with its draft.
- [ ] **Step 4: Run the tests again.** Expected: `6 passed`.
- [ ] **Step 5: Register the contract.**
  - Add `'test_host_change_registry'` to `MODULES` in `tests/contract/curated_contracts.py`.
  - Run: `uv run --no-sync --frozen python -B -m pytest tests/contract/curated_contracts.py tests/contract/test_host_change_registry.py -q -p no:cacheprovider -k "test_every_contract_module_runs_in_ci_or_is_declared or test_host_change_registry.py"` (`curated_contracts.py` re-exports every curated test, so `-k` picks its own check).
  - Expected: `7 passed`.

### Task 3: Name the host package behind each hot-swap GL event

**Files:**
- Modify: `tools/hot_swap/policy.py` (`attribute()` and the new functions beside it)
- Create: `tools/hot_swap/host_sources.py`
- Test: `tests/contract/test_hot_swap_policy.py`

**Interfaces:**
- Produces:
  - `first_caller(modules: list[str]) -> str | None`: the first module name, innermost first, that the existing `_TRANSPARENT` rule does not skip. `attribute()` keeps its behaviour and is rewritten on top of it.
  - `host_gl_sources(events: list[dict]) -> dict[str, int]`: counts events by the top-level package of `first_caller(event['stack'])`. Events with no stack, or whose stack gives `None`, count under `'native'`.
  - The command `python -m tools.hot_swap.host_sources <audit.json>...`. For each report it reads `gates.host_gl_events` and prints `source<TAB>count` lines, sorted, under a `== <path>` header, then exits 0.
- Consumed by: Tasks 9 and 10.

- [ ] **Step 1: Write the failing tests:**

```python
def test_first_caller_skips_machinery_gl_modules_and_shims():
    assert first_caller(['ctypes', 'OpenGL.GL', 'qtpy.QtOpenGL', 'napari.utils.info']) == 'napari.utils.info'
    assert first_caller(['importlib._bootstrap', 'tools.hot_swap.probe']) is None

def test_host_gl_sources_name_the_host_package_behind_each_event():
    events = [{'stack': ['importlib._bootstrap', 'OpenGL.platform.win32', 'OpenGL.error', 'napari._vispy.canvas']},
              {'stack': ['PyQt6.QtOpenGL', 'qtpy.QtGui', 'superqt.utils._qthrottler']},
              {'stack': ['qtpy.QtWidgets']},
              {'kind': 'native_load'}]
    assert host_gl_sources(events) == {'napari': 1, 'qtpy': 2, 'native': 1}

def test_host_sources_command_prints_each_report(tmp_path, capsys):
    report = tmp_path / 'audit.json'
    report.write_text(json.dumps({'gates': {'host_gl_events': [{'stack': ['qtpy.QtGui']}, {}]}}))
    assert host_sources.main([str(report)]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == ['native\t1', 'qtpy\t1']
```

- [ ] **Step 2: Run the tests and see them fail.**
  - Run: `uv run --no-sync --frozen python -B -m pytest tests/contract/test_hot_swap_policy.py -q -p no:cacheprovider`
  - Expected: the three new tests fail with `ImportError`, and the 14 existing tests pass.
- [ ] **Step 3: Implement** `first_caller()` and `host_gl_sources()` in `policy.py`, and `main(argv: list[str] | None = None) -> int` in `host_sources.py`.
- [ ] **Step 4: Run the tests again.** Expected: `17 passed`.
- [ ] **Step 5: Run every hot-swap contract.**
  - Run: `uv run --no-sync --frozen python -B -m pytest tests/contract/test_hot_swap_policy.py tests/contract/test_hot_swap_linux_native.py tests/contract/test_hot_swap_linux_observer.py -q -p no:cacheprovider`
  - Expected: all pass.
- [ ] **Step 6: Publish Tasks 1–3 as one PR.**
  - Precondition: `git -C ../vispy_vulkan-publication status -sb` shows a detached HEAD at `origin/main`, with no other owner's branch checked out. Otherwise wait.
  - Create the branch `work/d28-host-changes` from `origin/main`.
  - Copy the changed files byte for byte, commit them with `git commit --only <paths>`, push, and open the PR.
  - Merge with `gh pr merge N --auto --merge`.
  - Verify that all 11 required checks passed and that the merged tree equals the tested tree. Then return the clone to a detached `origin/main`.

### Task 4: The napari change on napari `main` (local only)

**Files (napari clone):**
- Modify `src/napari/_vispy/canvas.py`:
  - the module-level `from OpenGL.error import GLError`;
  - the `contextlib.suppress(AttributeError, GLError)` call in `_clean_and_update_scenegraph`;
  - a new `_gl_errors()` at the end of the module.
- Test: `src/napari/_vispy/_tests/test_canvas.py`

**Files (this repository):**
- `docs/upstream-drafts/napari-lazy-pyopengl-import.patch` and the README's napari section.

**Interfaces:**
- Consumes: napari `origin/main`, with the commit recorded in Step 1 (`b304b99d` on 2026-10-30 or later).
- Produces:
  - the branch `lazy-pyopengl-import`;
  - `_gl_errors() -> tuple[type[BaseException], ...]` in `napari._vispy.canvas`, as in the draft: it catches `ImportError` and `OSError`, and returns `()` or `(GLError,)`;
  - run `upstream-napari-<id>`, with the base and patched JUnit results.

- [ ] **Step 1: Clone and branch.**
  - Run: `git clone --filter=blob:none https://github.com/napari/napari /c/Users/HEQ/Projects/upstream/napari && git -C /c/Users/HEQ/Projects/upstream/napari switch -c lazy-pyopengl-import origin/main`
  - Record `git rev-parse origin/main` as the base.
- [ ] **Step 2: Register the run** with `--expected-peak-bytes 6000000000`. It holds two WSL environments, built with the pattern from `build/runs/threedee-drag-fix-wsl-204/wsl_driver.py`:
  - each env is Python 3.12 with `"<export>[pyqt6,testing]"` installed from a `git archive` export;
  - the base env is built from the recorded base commit, the patched env from the branch tip.
- [ ] **Step 3: Write the failing tests** in `test_canvas.py`:

```python
def test_canvas_has_no_module_level_opengl_import():
    tree = ast.parse(inspect.getsource(canvas_module))
    top = {node.module or '' for node in tree.body if isinstance(node, ast.ImportFrom)}
    top |= {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    assert not {name for name in top if name.split('.')[0] == 'OpenGL'}

def test_gl_errors_returns_pyopengl_error():
    from OpenGL.error import GLError
    assert _gl_errors() == (GLError,)

def test_gl_errors_is_empty_when_pyopengl_is_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, 'OpenGL.error', None)
    assert _gl_errors() == ()

def test_gl_errors_is_empty_when_the_gl_library_cannot_load(monkeypatch):
    monkeypatch.setitem(sys.modules, 'OpenGL.error', _Unloadable())  # __getattr__ raises OSError
    assert _gl_errors() == ()

def test_layer_removal_still_suppresses_gl_error(make_napari_viewer, monkeypatch):
    from OpenGL.error import GLError
    viewer = make_napari_viewer()
    layer = viewer.add_points([[0, 0]])
    context = viewer.window._qt_viewer.canvas._scene_canvas.context
    monkeypatch.setattr(context, 'finish', partial(_raise, GLError(err=1282, baseOperation='glFinish')))
    viewer.layers.remove(layer)  # must not raise
```

- [ ] **Step 4: Run the new tests and see them fail.**
  - Commit the tests alone, export that commit, and run, under `xvfb-run -a` in the patched env: `python -m pytest --pyargs napari._vispy._tests.test_canvas -p no:cacheprovider -q`
  - Expected: collecting `test_canvas.py` fails with `ImportError: cannot import name '_gl_errors'`.
- [ ] **Step 5: Implement the change** from the draft, rebased onto the base commit. Lint with `uvx ruff check --no-cache` and `uvx ruff format --check --no-cache` on the two files, run in the clone so napari's settings apply.
- [ ] **Step 6: Rerun the new tests.** Re-export and rerun Step 4's command. Expected: all 5 pass.
- [ ] **Step 7: Run the full suites on both envs.**
  - Run, under `xvfb-run -a`: `python -m pytest --pyargs napari._vispy napari._qt -p no:cacheprovider -q --junitxml=<run>/<side>.xml`
  - Expected: the patched env's failing node ids equal the base env's, and the 5 new tests pass.
- [ ] **Step 8: Refresh the draft.**
  - Write `git -C <clone> diff <base> lazy-pyopengl-import` to `docs/upstream-drafts/napari-lazy-pyopengl-import.patch`.
  - Record the base commit, the run id and the suite counts in the README.
- [ ] **Step 9:** close and retain the run.

### Task 5: The qtpy change on qtpy `master` (local only)

**Files (qtpy clone):**
- Modify:
  - `qtpy/QtGui.py`: the PyQt6 and PySide6 blocks and `__getattr__`;
  - `qtpy/QtWidgets.py`: the same.
- Test: `tests/test_qtgui.py`, `tests/test_qtwidgets.py`

**Files (this repository):**
- `docs/upstream-drafts/qtpy-lazy-qtopengl.patch` and the README's qtpy section.

**Interfaces:**
- Consumes: qtpy `origin/master`, with the commit recorded in Step 1 (`70f0e887` or later).
- Produces:
  - the branch `lazy-qtopengl`;
  - module-level `__getattr__` in `qtpy.QtGui` and `qtpy.QtWidgets` that, on Qt6:
    - imports `<binding>.QtOpenGL` and `<binding>.QtOpenGLWidgets` on the first access to a `QOpenGL*` or `QAbstractOpenGL*` name, or to `QOpenGLWidget`;
    - caches the name;
    - otherwise falls through to `getattr_missing_optional_dep`;
  - run `upstream-qtpy-<id>`.

- [ ] **Step 1: Clone and branch.** Run: `git clone https://github.com/spyder-ide/qtpy /c/Users/HEQ/Projects/upstream/qtpy && git -C … switch -c lazy-qtopengl origin/master`, then record the base.
- [ ] **Step 2: Register the run** with `--expected-peak-bytes 4000000000`. It holds Windows Python 3.12 envs for PyQt5, PyQt6 and PySide6. Each env installs `"<export>[test]"` (pytest, pytest-cov, pytest-qt) plus its binding, from a `git archive` export.
- [ ] **Step 3: Write the failing tests.** Mark the Qt6 ones with qtpy's own `skipif(not (PYQT6 or PYSIDE6))`. Each `sys.modules` check runs in a subprocess with the parent's `QT_API`.

```python
def test_qtgui_import_defers_qtopengl():
    loaded = run_child("import sys, qtpy.QtGui, qtpy.QtWidgets; "
                       "print(sorted(m for m in sys.modules if m.endswith(('.QtOpenGL', '.QtOpenGLWidgets'))))")
    assert loaded == '[]'

def test_qopengl_names_resolve_on_first_access():
    assert qtpy.QtGui.QOpenGLBuffer is import_module(f'{qtpy.API_NAME}.QtOpenGL').QOpenGLBuffer
    assert qtpy.QtGui.QAbstractOpenGLFunctions

def test_qopenglwidget_resolves_on_first_access():
    from qtpy.QtWidgets import QOpenGLWidget
    assert QOpenGLWidget is import_module(f'{qtpy.API_NAME}.QtOpenGLWidgets').QOpenGLWidget

def test_unknown_qopengl_name_raises_attribute_error():
    with pytest.raises(AttributeError):
        qtpy.QtGui.QOpenGLNoSuchClass

def test_missing_qtopengl_raises_module_not_installed(monkeypatch):
    monkeypatch.delitem(vars(qtpy.QtGui), 'QOpenGLBuffer', raising=False)
    monkeypatch.setattr(qtpy.QtGui, 'import_module', _raise_import_error)
    with pytest.raises(qtpy.QtModuleNotInstalledError):
        qtpy.QtGui.QOpenGLBuffer

def test_star_import_on_qt6_omits_qopengl_names():
    assert run_child("from qtpy.QtGui import *; print('QOpenGLBuffer' in dir())") == 'False'
```

`qtpy.API_NAME` is `PyQt6` or `PySide6` here. Both are qtpy's binding module names.

- [ ] **Step 4: Run the new tests and see them fail.**
  - Commit the tests alone and export them. Run, in the PyQt6 env: `QT_API=pyqt6 QT_QPA_PLATFORM=offscreen <env>\Scripts\python.exe -m pytest tests/test_qtgui.py tests/test_qtwidgets.py -p no:cacheprovider -q`
  - Expected: these fail:
    - `test_qtgui_import_defers_qtopengl`, because the modules are loaded;
    - `test_star_import_on_qt6_omits_qopengl_names` prints `True`;
    - `test_missing_qtopengl_raises_module_not_installed`, because `import_module` is missing.
- [ ] **Step 5: Implement the change** from the draft, rebased onto the base commit. In the clone, run qtpy's two pre-commit code hooks on the changed files: `uvx black --check <files>` and `uvx ruff check --no-cache <files>`.
- [ ] **Step 6: Rerun the new tests.** Re-export, then rerun Step 4's command in each binding env with its `QT_API`. Expected:
  - all the new tests pass on PyQt6 and PySide6;
  - on PyQt5, the Qt6-only ones are marked as skipped by qtpy's convention, and the others pass.
- [ ] **Step 7: Run qtpy's whole suite** per binding on the base and patched exports: `… -m pytest tests -p no:cacheprovider -q --junitxml=<run>/<binding>-<side>.xml`
  - Expected: the patched failing node ids equal the base ones for each binding.
  - PySide2 needs Python 3.10. Run it in WSL if a cp310 PySide2 wheel installs there. Otherwise the PR text says PySide2 was left to qtpy's CI.
- [ ] **Step 8:** refresh the draft and the README as in Task 4, Step 8, then close and retain the run.

### Task 6: Measure what each change avoids

**Files:**
- Create: `build/runs/upstream-effects-<id>/effects.py`. It runs each check below in a fresh subprocess and writes `effects.json` with one result per check: command, exit status, value, exception type and message.

**Interfaces:**
- Consumes:
  - the branches from Tasks 4 and 5, exported;
  - our test wheel `cc6fa732…` from run `p6-buffer-uploads-266`, as content-addressed in `build/artifacts`;
  - napari 0.10.0, qtpy 2.4.3 and vispy 0.17.x from PyPI.
- Produces: `effects.json`. Task 7 quotes only its values.

**Expectations, written before any run:**

| Check | Environment | Measured | Expected |
| --- | --- | --- | --- |
| N1 | our wheel, napari 0.10.0, PyQt6 | `'OpenGL' in sys.modules` after `import napari._vispy.canvas` | `True` |
| N2 | our wheel, patched napari | same | `False` |
| N3 | upstream vispy 0.17.x, napari 0.10.0 | same | `True` |
| N4 | upstream vispy, patched napari | same | `True` (markers' `use(gl='gl+')`) |
| Q1 / Q3 | stock qtpy, PyQt6 / PySide6 | `<binding>.QtOpenGL` imported, and `opengl32.dll` loaded (`GetModuleHandleW`), after `import qtpy.QtGui, qtpy.QtWidgets` | both `True` |
| Q2 / Q4 | patched qtpy, PyQt6 / PySide6 | same | both `False` |
| T1 | N1 against N2; Q1 against Q2; Q3 against Q4 | median of 5 `-X importtime` cumulative times for the import | recorded, no threshold |
| L1 | WSL, stock PyQt6, `libGL`/`libEGL`/`libOpenGL`/`libGLX` masked | `import PyQt6.QtGui` | recorded |
| L2 / L3 | WSL, masked, stock / patched qtpy | `import qtpy.QtWidgets` | recorded |

The L checks run as root under `unshare -m`, with an empty file bind-mounted over each library path that `ldconfig -p` resolves. The run records the mount table and the `ldconfig -p` output. If L1 fails, no PR may claim any benefit on Linux without a GL library.

- [ ] **Step 1: Register the run** with `--expected-peak-bytes 5000000000`. Build one Windows env per N and Q row (seven, since Q1 runs in N1's env) and the two WSL envs.
- [ ] **Step 2: Run** `<env>\Scripts\python.exe -B effects.py --output effects.json` for each env, and run the L checks through the WSL driver.
- [ ] **Step 3: Compare `effects.json` with the expectation table.**
  - Each N and Q check must match its expectation.
  - A mismatch stops the task. It is recorded as a finding and diagnosed before any PR text is written.
- [ ] **Step 4:** close and retain the run.

### Task 7: Briefs for the user, then Gate B

Both projects forbid an AI agent from submitting a PR or writing its description (Global Constraints, "Upstream AI policies"). So this task hands the user facts, not text to post.

**Files:**
- Create: `docs/upstream-drafts/napari-brief.md`, `docs/upstream-drafts/qtpy-brief.md`
- Modify: `docs/upstream-drafts/README.md`, and `compat/host-changes.json` (statuses become `approved` once the user decides to submit)

**Interfaces:**
- Consumes: the diffs from Tasks 4 and 5, and the values in `effects.json`.
- Produces, per change, a brief with:
  - the branch, its base, its commits and how to rerun the tests;
  - why the change helps, and what Task 6 measured (with the numbers and their run);
  - behaviour notes and what was not tested;
  - the project's submission rules: napari's PR template sections and AI policy; for qtpy, Spyder's AI policy and its required AI-use disclosure.

- [x] **Step 1: Read each project's PR template, contributing guide and AI policy.** napari: `.github/PULL_REQUEST_TEMPLATE.md` and the AI use policy (`napari/docs`, `docs/developers/contributing/ai.md`). qtpy: `CONTRIBUTING.md`, and Spyder's AI policy (`spyder-ide/spyder`, `CONTRIBUTING.md`).
- [ ] **Step 2: Write the napari brief.**
  - The module-level import serves one `suppress` call.
  - The measured effect: N1/N2 for vispy builds whose `gl+` does not use PyOpenGL, and N3/N4 to show no change with upstream vispy.
  - The new tests and the suites run (with the Task 4 counts).
- [ ] **Step 3: Write the qtpy brief.**
  - The measured effect: Q1–Q4 and T1, plus L1–L3 only where they show a difference.
  - The star-import behaviour change, and the `__all__` alternative.
  - The bindings run (with the Task 5 counts), including how PySide2 was covered.
- [ ] **Step 4: Gate B.** Hand the user each branch, its base-to-branch diff (`git -C <clone> diff <base> <branch>`) and its brief. The user decides whether to submit. When they do, record their decision in the W12 row, set the registry status to `approved`, and publish through the Task 3, Step 6 procedure. Expected: `test_host_change_registry.py` passes with `approved`.

### Task 8: The user submits the PRs and takes them through review

**Interfaces:**
- Consumes: the Task 7 briefs and the registry.
- Produces: PR URLs, and status changes in `compat/host-changes.json` (`posted`, then `merged` with its merge commit, or `declined` with the reason).

- [ ] **Step 1: The user submits.** The user tests each branch, writes the description in their own words, and forks, pushes and opens the PR personally. For qtpy the description discloses the AI use. The agent runs no `gh` command against napari or qtpy.
- [ ] **Step 2: Record the posts.** When the user shares the URLs, set the registry statuses to `posted` with their URLs, update the W12 row, and publish. Expected: the registry contract passes.
- [ ] **Step 3: The review loop.** The user answers reviewers. When the user asks, the agent explains code or reruns Task 4 or 5's Steps 6–7 on a new commit in a new registered run, and reports the results to the user only.
- [ ] **Step 4: Record the outcome.** On merge or decline, update the registry and the W12 row, then publish.

### Task 9: W16, the hot-swap baseline on napari 0.10.0 (after the user's GUI go-ahead)

**Files:**
- Create:
  - `compat/host-environments/napari-0.10.0-hot-swap-windows-cpython312-pyqt6.in`;
  - its `uv pip compile --generate-hashes` lock `.txt`, whose first line is "Candidate lock derives from the immutable upstream host lock; only VisPy is replaced.";
  - `vispy` as a `file:` reference to the R2 branch's latest test wheel (when this was written, `cc6fa732…` from run `p6-buffer-uploads-266`).
  - Like the other stock-swap locks, it stays local (`.gitignore`).

**Interfaces:**
- Consumes: Task 3's command and Task 2's lock checks.
- Produces: the baseline host GL sources that Task 10 compares against.

- [ ] **Step 1: Check the new lock.**
  - Run: `uv run --no-sync --frozen python -B -m pytest tests/contract/test_host_change_registry.py -q -p no:cacheprovider`
  - Expected: `6 passed`. The contract finds the new lock by its header, and it names stock hosts only.
- [ ] **Step 2: Register the run** with `--expected-peak-bytes 8000000000`. Install:
  - the lock, with `UV_LINK_MODE=copy`;
  - run 207's numba lock (`--only-binary :all: --no-deps`);
  - a fresh `NAPARI_CONFIG=<scratch>/settings.yaml`.
- [ ] **Step 3: Run W2.** That is the probe's napari and threedee scenarios, plus `tests/hosts/test_napari_*parity*.py`.
  - Control: run the same suites with upstream vispy 0.17.x on napari 0.10.0. A case that fails on both is a napari 0.10 change, not a port defect.
  - Expected: every case passes or has a triaged cause.
- [ ] **Step 4: Run W3.**
  - Run: `<env>\Scripts\python.exe -B tools/audit_hot_swap.py --python <env python> --script tools/hot_swap/scenarios/stock_napari.py --output <run>/audit.json`
  - Expected: `"status": "PASS_HOT_SWAP_GATES"`.
  - Then run `uv run --no-sync --frozen python -B -m tools.hot_swap.host_sources <run>/audit.json`. Expected: the sources include `napari` and `qtpy`.
- [ ] **Step 5: Record and close.** Add W16's result to the consolidated plan's Progress, publish, and close the run.

### Task 10: Adopt a host release that contains a change (one run per release)

**Interfaces:**
- Consumes: the registry entries with status `merged`, and Task 9's baseline sources.
- Produces: registry status `released` with `released_in`, a hot-swap lock on the release, and a prepared strict patch reduction.

- [ ] **Step 1: Detect the release.** Look for a new PyPI release of the host, then check that it contains the merge.
  - Run: `gh api repos/<owner>/<repo>/compare/<release-tag>...<merge-sha> --jq .status`
  - Expected: `behind` or `identical`.
  - For napari, also check that the release still accepts `vispy` 0.17. If it doesn't, record that in the registry and the consolidated plan, and stop: moving the port to a newer vispy is a separate decision.
- [ ] **Step 2: Lock the release.** Copy Task 9's lock with only this host's version changed, check it with Task 9, Step 1's command, and run W3 as in Task 9, Step 4.
  - Expected: `PASS_HOT_SWAP_GATES`.
  - Expected: `host_sources` no longer lists the adopted host (`qtpy` or `napari`).
- [ ] **Step 3: Record the release** as `released` with `released_in`. Run the registry contract and publish.
- [ ] **Step 4: Prepare the strict patch for R2.**
  - Write the reduced strict patch against the released version, with only the entry's `strict_only` hunks, and register it.
  - The strict rows switch to it only at R2's requalification (D1), not before.
