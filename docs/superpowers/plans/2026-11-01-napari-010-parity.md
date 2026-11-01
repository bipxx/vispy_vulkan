# napari 0.10.0 Parity Row (D30) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The six core napari parity suites and the probe's napari scenario judge napari 0.10.0. The retained 0.9.2 modules and reference packets are not changed.

**Architecture:**
- **Successor fixtures.** Each core suite gets a version-agnostic successor fixture module. It reuses the retained module's inputs, specification and landmarks, and re-implements only the one function that pins napari 0.9.2, without the pin.
- **Packets.** Upstream OpenGL reference packets are stored per napari version in `tests/reference/<base>-napari-<version>/`, and each packet's provenance names its napari version.
- **Tests.** Successor tests bind every packet (CPU) and compare the candidate with the packet for the installed napari (GPU). A future napari release then needs new packets, not new code.

**Tech Stack:** Python 3.12, pytest, napari 0.10.0, PyQt6 6.12.0, upstream vispy 0.17.0 (oracle), test wheel `cc6fa732` (candidate), uv.

**Spec:** The user's answers of 2026-11-01:
- "close the gaps and review again";
- scope "Core suites + probe": the probe's napari scenario accepts 0.10.0, and the 6 core suites (layer controls, layer families, vector layers, scientific, volume, image extensions) get 0.10.0 packets, while the napari-threedee plugin suites stay on 0.9.2;
- design "Version-agnostic": one new successor set per suite that reads the napari version from each reference packet.

These answers are recorded here as D30. Background: the consolidated plan's W16 row and D6 ("Broken oracle fixtures get new fixture modules and reference packets beside the retained ones … Original references are never replaced.").

## Status (2026-11-01)

**Done** (run `napari-010-parity-298`). The six core suites and the probe's napari scenario judge napari 0.10.0.
- **Task 8, packets.** `tests/reference/<base>-napari-0.10.0/` holds a packet for each suite, captured with upstream
  vispy 0.17.0 on the stock 0.10.0 lock.
- **Task 7, validation.** On napari 0.9.2 the successors reproduce the retained code run in the same environment: every
  frame, every parameter except the image host workflow name, and every shader. Measured against the retained packets,
  GLIR, one antialiased frame (`shapes_selected`, within its D10 rule) and two GLIR-derived image parameters differ.
  The retained code run now differs from its packets in the same way, so those differences come from the present
  environment.
- **Task 9, candidate.** Test wheel `cc6fa732` passes all 55 cases under readback and under native presentation. The
  probe's napari scenario passes on 0.10.0.
- **Deviations from the tasks as written** (rulings in the run's ledger):
  - The packet bindings live in one CI-run contract, `tests/contract/test_napari_successor_references.py`, not in the
    host tests.
  - The import test checks that a successor imports nothing beyond its retained module.
  - The fresh review ran before the captures, because the packets bind the code by hash. Its two Important findings
    were fixed test-first:
    - a candidate capture now requires `--output`;
    - the host lock is checked against the installed environment before any GUI work and kept in each packet as
      `host-lock.txt`.
  - The review's seven minor findings are deferred and listed in the ledger.

## Global Constraints

- **Retained files.** Never edit them: `tools/fixture_napari*.py`, `tools/oracle_napari*_capture.py`, `tools/fixture_image_extensions.py`, `tools/oracle_image_extensions_capture.py`, and every packet under `tests/reference/` (D6; their reference manifests pin them by hash).
- **Python.** Repo Python runs as `uv run --no-sync --frozen python -B …` from the repository root. Scratch interpreters are called directly.
- **Build hygiene** (AGENTS.md):
  - register a run before creating scratch;
  - keep scratch in `build/work/<run-id>`, with no directory aliases or Git repositories;
  - close every run with `terminal.json`, `plan`, `apply` and `audit`.
- **Evidence rules.** Expectations are written before measuring. No `skip` and no `xfail`. Line endings are never normalized.
- **GUI runs** are approved by the user's 2026-11-01 answers.
- **The 0.10.0 row's environments:**
  - oracle: `compat/host-environments/napari-0.10.0-windows-cpython312-pyqt6.txt` (upstream vispy 0.17.0);
  - candidate: `compat/host-environments/napari-0.10.0-hot-swap-windows-cpython312-pyqt6.txt` (only vispy replaced, by `cc6fa732`);
  - both add run 207's numba lock `--only-binary :all: --no-deps`, and the candidate adds run 232's pytest lock.
- **Publication** goes only to `bipxx/vispy_vulkan`, through a sparse worktree with `commit --only`, the 11 required checks and auto-merge. Never open PRs to napari or qtpy (D29).
- **New source files** start with `# SPDX-License-Identifier: AGPL-3.0-only` and use LF.

## Review Focus

1. **A successor that renders differently from its retained module, beyond removing the pin.** Expected: impossible without a failing test. Task 2's AST test and Task 7's 0.9.2 validation capture both catch it.
2. **A GPU test that picks another version's packet, or a packet whose directory version and provenance disagree.** Expected: an assertion naming both versions (Task 1).
3. **A capture into an existing packet, or a worker failure that leaves a partial record.** Expected: refused before any GUI work, and nothing admitted (Task 3).
4. **The probe's napari scenario seeing an unqualified napari (0.9.1, 0.11.0, 0.10.0rc1).** Expected: rejected (Task 6).
5. **Candidate runs writing evidence into the main tree's `build/evidence`.** Expected: an override sends it to scratch (Task 1's `evidence_dir`, used by Tasks 4 and 5).

---

### Task 1: D30 and the host-packet helper

**Files:**
- Create: `tools/napari_host_packets.py`
- Test: `tests/contract/test_napari_host_packets.py`, registered in `tests/contract/curated_contracts.py` `MODULES`

**Interfaces:**
- Produces:
  - `REFERENCES: Path` (`ROOT / "tests/reference"`);
  - `packet_dir(base: str, version: str, root: Path = REFERENCES) -> Path` → `root / f"{base}-napari-{version}"`;
  - `packets(base: str, root: Path = REFERENCES) -> dict[str, Path]` returns every `"{base}-napari-*"` directory keyed by version, sorted, and asserts that each `manifest.json` has `provenance.napari_version` equal to its directory's version;
  - `installed_packet(base: str, version: str | None = None, root: Path = REFERENCES) -> Path` returns the packet for `version` (default `metadata.version("napari")`). Otherwise it raises an `AssertionError` that names the version and `tools/oracle_napari_successor_capture.py`;
  - `is_napari_pin(statement: ast.stmt) -> bool` is true for `assert metadata.version("napari") == "<str>"` and `assert napari.__version__ == "<str>"`, with or without a message;
  - `unpinned_source(function) -> str` is `ast.unparse` of the function's definition with its top-level pins removed;
  - `evidence_dir(name: str, version: str) -> Path` is `Path(os.environ.get("VISPY_NAPARI_EVIDENCE", ROOT / "build/evidence")) / name / version`.

- [ ] **Step 1: Write the failing tests.**
  - `test_packet_dir_names_the_napari_version`.
  - `test_packets_returns_every_version_and_checks_provenance`: 0.10.0 and 0.11.0 come back in order. A 0.10.0 directory whose manifest says 0.9.2 raises an error naming both versions.
  - `test_packets_keeps_bases_apart`: `napari-opengl` does not pick up `napari-volume-opengl-napari-0.10.0`.
  - `test_installed_packet_requires_the_exact_version`: 0.10.1 raises with "napari 0.10.1", and 0.10.0 returns its directory.
  - `test_is_napari_pin_matches_only_napari_pins`: both forms are true, with and without a message. `QtPy`, a non-constant right-hand side and a pin nested in an `if` are false.
  - `test_unpinned_source_removes_only_top_level_pins`.
  - `test_evidence_dir_honours_the_override`, using `monkeypatch`.
- [ ] **Step 2: Run** `uv run --no-sync --frozen python -B -m pytest tests/contract/test_napari_host_packets.py -q -p no:cacheprovider`. Expected: collection fails, because there is no module yet.
- [ ] **Step 3: Implement** `tools/napari_host_packets.py`. Add the D30 row to the consolidated plan's decision table, after D29. D30 records the user's two answers and states that packets carry the napari version, while the retained modules and packets keep 0.9.2.
- [ ] **Step 4: Run** the same tests and the curated contracts. Expected: all pass, and `curated_contracts.py` names the new module.

### Task 2: Successor fixtures for the five napari suites

**Files:**
- Create:
  - `tools/fixture_napari_successor.py` (retained: `tools/fixture_napari.py`, the scientific suite);
  - `tools/fixture_napari_layer_controls_successor.py`;
  - `tools/fixture_napari_layer_families_successor.py`;
  - `tools/fixture_napari_vector_layers_successor.py`;
  - `tools/fixture_napari_volume_successor.py`.
- Test: `tests/contract/test_napari_successor_fixtures.py` (registered in `MODULES`)

**Interfaces:**
- Consumes: Task 1's `is_napari_pin` and `unpinned_source`.
- Produces: each successor exports the retained module's public names: `CASES`, `assert_landmarks`, `render`, and, where the retained module has them, `CRITERIA`, `EXACT`, `masks` and `specification`. Everything except `render` is imported from the retained module. `render` is the retained `render` with its pin statement removed, and nothing else changed. Both import styles of the retained modules are kept (`from .x import` and `from x import`).

- [ ] **Step 1: Write the failing tests** over `PAIRS = {retained: successor}`:
  - `test_successors_reuse_the_retained_inputs` checks that `CASES`, `CRITERIA`, `EXACT` and `specification(name)` for every case are identical to the retained ones;
  - `test_successor_render_is_the_retained_render_without_its_pin` checks that `unpinned_source(successor.render) == unpinned_source(retained.render)`, that the retained `render` has exactly one pin, and that the successor has none;
  - `test_successor_import_creates_no_qapplication` imports all five in a `.venv` subprocess and expects no `PyQt6`, `vispy` or `napari` in `sys.modules`.
- [ ] **Step 2: Run** the tests. Expected: collection fails.
- [ ] **Step 3: Write the five modules.** Each docstring names the retained module and D30.
- [ ] **Step 4: Run** the tests. Expected: they pass.

### Task 3: The generic successor capture tool

**Files:**
- Create: `tools/oracle_napari_successor_capture.py`
- Test: `tests/contract/test_napari_successor_capture.py` (registered in `MODULES`)

**Interfaces:**
- Consumes: Task 2's modules, and Task 1's `packet_dir`.
- Produces:
  - **`SUITES`.** It maps `scientific` → (`napari-opengl`, `fixture_napari_successor`, `tools/fixture_napari.py`), and `layer_controls`, `layer_families`, `vector_layers` and `volume` likewise. Each entry also carries the suite's manifest `comparison` block, copied from its retained capture tool.
  - **The command line.** `--suite`, `--kind {upstream,candidate}`, `--output` (default `packet_dir(base, installed napari)`), `--host-lock` (required for `upstream`) and `--worker` (internal).
  - **`host_provenance(suite: str, napari_version: str, napari_origin: str, host_lock: Path | None) -> dict`.** It returns:
    - `napari_version` and `napari_origin`;
    - `fixture_source_sha256`, of the successor;
    - `retained_fixture_source_sha256`;
    - `capture_source_sha256`;
    - `host_lock` (`{"file", "sha256"}`);
    - `installed`;
    - the volume suite's `host_source_sha256`, over the same three napari files as its retained capture.
  - **The manifest** has the same per-case keys as the retained capture tool writes for that suite. Its `provenance` merges `oracle_capture.provenance(kind)` with `host_provenance`.

- [ ] **Step 1: Write the failing tests:**
  - `test_suites_name_each_retained_and_successor_module`;
  - `test_capture_refuses_an_existing_packet`: a subprocess with a non-empty `--output` exits non-zero with "fresh output required", before any canvas;
  - `test_upstream_capture_requires_a_host_lock`: argparse exits 2;
  - `test_worker_failure_cannot_admit_a_partial_record`, which mirrors `tests/contract/test_reference_inventory.py::test_capture_worker_failure_cannot_admit_a_previous_or_partial_record`;
  - `test_host_provenance_records_the_installed_napari_without_a_pin`, using fake versions 0.10.0 and 0.11.0.
- [ ] **Step 2: Run** the tests. Expected: collection fails.
- [ ] **Step 3: Implement the tool.** It checks that the output is fresh before `provenance()`. Its docstring gives the regenerate command for the 0.10.0 oracle environment.
- [ ] **Step 4: Run** the tests. Expected: they pass.

### Task 4: Successor parity tests for the five napari suites

**Files:**
- Create: `tests/hosts/test_napari_{scientific,layer_controls,layer_families,vector_layers,volume}_successor_parity.py`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: each test mirrors its retained `tests/hosts/test_napari_*_parity.py`, with the same comparisons, criteria and documented-difference calls. It differs in five ways:
  - imports come from the successor module;
  - a CPU test, `test_every_packet_binds_this_successor`, runs over `packets(BASE)`. It requires at least one packet, and checks for each one:
    - kind `upstream` and vispy 0.17.0;
    - `napari_version` equal to the directory's version;
    - the three source hashes;
    - a recorded `host_lock` with a 64-hex sha256, matching the lock file wherever it is present;
    - criteria, `CASES` and FIXED parameters against `specification`;
    - artifact hashes and landmarks;
  - the GPU test uses `installed_packet(BASE)`, and asserts that `napari.__version__` equals the packet's version;
  - there is no hard-coded napari version;
  - evidence goes to `evidence_dir("napari-<suite>-successor-candidate", version)`.

- [ ] **Step 1: Write the five test modules.**
- [ ] **Step 2: Run** `uv run --no-sync --frozen python -B -m pytest tests/hosts/test_napari_*_successor_parity.py -q -p no:cacheprovider -m "not gpu"`. Expected: the binding tests fail with "no packet" (RED), until Task 8 captures packets.

### Task 5: The image-extension successor

**Files:**
- Create: `tools/fixture_image_extensions_successor.py`, `tools/oracle_image_extensions_successor_capture.py`, `tests/parity/test_image_extensions_successor_parity.py`
- Test: extend `tests/contract/test_napari_successor_fixtures.py`

**Interfaces:**
- Consumes: Task 1's helpers.
- Produces:
  - **Fixture.** The successor re-implements `_render_host` (the pinned function, without its pin) and `render` (unchanged, but bound to the successor's `_render_host`). Everything else is imported. If the retained specification embeds the version (`"public napari0.9.2"`), the successor's specification says `"public napari"`, and that is the one allowed difference.
  - **Capture.** It keeps the retained protocol (authoring freeze before capture, source snapshot, one process per case), with version-agnostic origins. Its default output is `packet_dir("image-extensions-opengl", version)`.
  - **Test.** It mirrors `tests/parity/test_image_extensions_parity.py`, with packets as in Task 4.

- [ ] **Step 1: Extend** the AST and reuse tests for this pair; the specification difference is listed explicitly. Write the successor test module.
- [ ] **Step 2: Run** the contract tests. Expected: they fail (RED).
- [ ] **Step 3: Implement** the fixture and the capture tool.
- [ ] **Step 4: Run** the contract tests. Expected: they pass. The successor parity binding test stays RED until Task 8.

### Task 6: The probe accepts qualified napari versions

**Files:**
- Modify: `tools/no_opengl_host_probe.py` (the napari scenario's pin, `napari()`)
- Test: `tests/hosts/test_no_gl_probe_contract.py`

**Interfaces:**
- Produces: `NAPARI_VERSIONS = ("0.9.2", "0.10.0")`. The napari scenario asserts `metadata.version('napari') in NAPARI_VERSIONS`. The QtPy 2.4.3 and numba 0.68.0 pins are unchanged.

- [ ] **Step 1: Write the failing test** `test_napari_scenario_accepts_only_qualified_napari_versions`:
  - `NAPARI_VERSIONS == ("0.9.2", "0.10.0")`;
  - the scenario's source has no `== '0.9.2'` pin for napari;
  - `"0.9.1"`, `"0.11.0"` and `"0.10.0rc1"` are not accepted.
- [ ] **Step 2: Run** it. Expected: it fails.
- [ ] **Step 3: Change the pin.**
- [ ] **Step 4: Run** the probe contract file. Expected: it passes.

### Task 7: Validation on napari 0.9.2 (GUI)

- [ ] **Step 1: Prepare the run.**
  - Register run `napari-010-parity-298` (owner `napari-010-parity`, expected peak 4000000000), and write `expectations.json`.
  - Build `build/work/<run>/oracle-napari-092` from `tools/oracle_napari_requirements.txt` with `--require-hashes`. This is the environment that produced the retained packets.
- [ ] **Step 2: Capture** every successor (Tasks 3 and 5) with `--kind upstream` into scratch.
- [ ] **Step 3: Compare** each case with its retained packet: the RGBA arrays byte for byte, and the parameters equal; GLIR and shader equality are reported. Expected: every case identical.

### Task 8: 0.10.0 reference packets (GUI)

- [ ] **Step 1: Build** `oracle-napari-010` from the 0.10.0 oracle lock plus the numba lock.
- [ ] **Step 2: Capture** each suite's packet into scratch with `--host-lock` set to that lock.
- [ ] **Step 3: Check and copy.** Each manifest must have no errors and pass its successor binding test. Then copy the packets into `tests/reference/<base>-napari-0.10.0/`.
- [ ] **Step 4: Run** the binding tests (`-m "not gpu"`). Expected: they pass (GREEN).

### Task 9: Candidate runs on napari 0.10.0 (GUI)

- [ ] **Step 1: Build** the candidate environment, from the hot-swap lock plus the numba and pytest locks.
- [ ] **Step 2: Run** the six successor suites from the main tree, with `VISPY_NAPARI_EVIDENCE` and `--basetemp` in scratch, a fresh `NAPARI_CONFIG`, and readback and native presentation. Expected: every case passes, or fails with a recorded, triaged cause.
- [ ] **Step 3: Run** the probe's napari scenario under `tools/pool_watch_external.py` (D20). Expected: it passes.

### Task 10: Record, review, publish and close

- [ ] **Step 1: Record the results.**
  - In the consolidated plan: the W16 row and Progress, the D30 row, the plan index entry, and this plan's Status.
  - Retain the run records, and close run 298.
- [ ] **Step 2: Final review.** A fresh reviewer, on the most capable model, reviews the whole change against this plan and its Review Focus. Do one fix pass, each fix test-first.
- [ ] **Step 3: Publish** one PR with the modules, tests, packets, the probe change and the plans. Do the local checks first: the curated contracts and the drift check.
