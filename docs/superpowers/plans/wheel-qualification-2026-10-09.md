# Windows wheel qualification evidence, 2026-10-09

The corrected frozen Windows milestone wheel passes the clean external consumer
test, including actual Text rendering, uninstall, and hash-verified upstream
restoration. Its SHA256 is
`38102fec05667cd31a9fa8db8908cbc72b98f80019b99dc09e175dee8c858dce`.
The first failed wheel and its exact source/artifact evidence remain preserved.
Linux/macOS, other CPython versions, other Qt bindings, broader hosts, and newer
runtime/platform edits are not qualified by this run.

The runtime/Python sources were captured at `2026-10-09T15:34:00Z`, after the
normalized-16-bit texture feature request and Python `atexit` teardown fixes.
Those sources passed the parent agent's 141 candidate tests, including 17 napari
cases. Subsequent runtime changes are excluded from this captured artifact.

## First artifact and preserved failure

| Item | Recorded value |
| --- | --- |
| Source snapshot | `build/w1` (560 copied project source files) |
| Source tree SHA256 | `7fa98f4edf3577a07a1caeed00e0660f4347faa97409697f5f3bb7019123f564` |
| Wheel | `vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl` |
| Wheel SHA256 | `bbf42127bf754f4950ce8e30bb384d91e69d7b5c015bbf056d5ac78658c809b1` |
| Wheel size | 6,174,814 bytes; 567 archive entries |
| Interpreter | CPython 3.12.8, Windows x86_64 |
| Build tools | scikit-build-core 0.11.6, CMake 4.4.4, nanobind 3.1.0, Cython 3.1.5, NumPy 2.5.3 |
| Compiler / SDK | MSVC 19.44.35225.0 / Windows SDK 10.0.22621.0 |

The snapshot copies `cpp`, `src`, CMake configuration, Python dependency pins,
and notices, excluding loaded native products and caches. Dawn and upstream
VisPy sources are shared immutable trees; all 10 dependency tree checksums
passed before and after compilation. The verifier resolves directory aliases
to physical paths to avoid Windows `MAX_PATH` when snapshots link to Dawn.

Run from the original checkout with `CMAKE_BUILD_PARALLEL_LEVEL=4`:

```powershell
uv build build/w1 --python C:/Users/HEQ/Projects/vispy_vulkan/.venv/Scripts/python.exe --wheel --out-dir dist --config-setting build-dir=build/w2
```

The isolated cache records `VISPY_INPLACE=OFF` and
`VISPY_VERIFY_DEPENDENCIES=ON`. No extension was copied into the active source
environment. The unqualified wheel is retained at `build/w1/artifact/` so a
later corrected wheel cannot overwrite its evidence.

## Consumer result

The test installs six hash-verified packages into a unique temporary environment
outside the checkout and uses isolated Python (`-I`). It passes distribution
identity, native module origins, all 19 notice hashes, submit-layer DLL and JSON,
the packaged OpenSans glyph, compiled in-place SDF generation, and a native
headless blue clear. Actual `Text("R", face="OpenSans", font_size=18)` rendering
fails: the normalized interface contains phantom `float d` and reserved
`float in` declarations; glslang rejects `IN`, mapped to line 25.

The installation test continues to verify rollback before asserting renderer
success. Uninstall leaves no importable `vispy`; hash-verified unmodified
upstream VisPy 0.17.0 reinstalls and imports from the external environment. The
overall test remains red because rendering fails.

```powershell
$env:VISPY_TEST_WHEEL = 'C:/Users/HEQ/Projects/vispy_vulkan/dist/vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl'
python -m pytest tests/contract/test_installation.py -q -m wheel -s
```

Machine-readable provenance, interpreter/native hashes, immutable dependency
verification, copied source milestone logs, consumer logs/JUnit, and exact raw
and normalized Text shaders are under `build/w1/evidence/`.
`wheel-provenance.json` records the source and artifact hashes and clearly marks
the artifact unqualified. Non-wheel packaging/CPU contracts passed 20 tests.

This failure required a new source snapshot/artifact and another complete
consumer test. The failed snapshot and its recorded hashes remain unchanged.

## Corrected shader-only milestone

`build/w3` branches from the frozen first snapshot and changes only
`cpp/shader/normalize.cpp`. The correction keeps helper `in`/`out` parameters
out of stage interfaces, splits sampler helper arguments/calls, and renames the
legacy `sample` helper around the GLSL 450 keyword. The independent expanded
Text shaders at DPI 96/144/192 pass the CPU shader validator/reflection checks.

| Item | Recorded value |
| --- | --- |
| Source tree SHA256 | `9e3f6c37a446fb1ecb55573c9904bce3cd4d81be2fa3f600c3c55f8dac4825ac` |
| Wheel SHA256 | `38102fec05667cd31a9fa8db8908cbc72b98f80019b99dc09e175dee8c858dce` |
| Isolated build cache | `build/w3/build/w4` |
| Consumer | 1 passed, 1 deselected, exit 0 |
| Actual device | NVIDIA GeForce RTX 4090, Vulkan, driver 595.79 |

```powershell
uv build build/w3 --python C:/Users/HEQ/Projects/vispy_vulkan/.venv/Scripts/python.exe --wheel --out-dir dist --config-setting build-dir=build/w4
```

This run used `CMAKE_BUILD_PARALLEL_LEVEL=3` and the same exact interpreter/build
pins as the first build. All 10 immutable dependency trees and all 560 copied
project inputs passed post-build checks. The corrected artifact is retained in
`build/w3/artifact/`; provenance, installed native module hashes, complete
consumer output/JUnit, and actual device/dependency details are in
`build/w3/evidence/`. The four native CPU harnesses also pass in the current
Windows build; fresh CPU-only/null-backend CMake configuration succeeds.

The successful artifact deliberately excludes ongoing runtime/platform edits.
A wheel built from those later sources requires its own candidate and consumer
qualification before release.
