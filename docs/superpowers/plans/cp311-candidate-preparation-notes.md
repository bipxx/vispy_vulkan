# CPython 3.11 candidate preparation

The build-only environment at `build/cp311-candidate/build-env` is prepared with
CPython 3.11.11 and seven wheel-only, hash-checked packages. No native configure,
compilation, wheel build, consumer install or GPU operation was performed in
this packet. The existing CPython 3.12 source binaries are unchanged.

`cmake/prepare_cp311_candidate.py` selects the actual Python 3.11 build-system
requirements from `pyproject.toml` and exact compatible wheel metadata from
`uv.lock`. It refuses to replace an existing environment. The resulting lock and
provenance are in `compat/cp311-candidate/`:

- scikit-build-core 0.11.6, nanobind 3.1.0, CMake 4.4.4, Cython 3.1.5;
- NumPy 2.4.6, packaging 26.3 and pathspec 1.1.1;
- actual SOABI `cp311-win_amd64`, expected native modules
  `_dawn.cp311-win_amd64.pyd` and `_sdf_cpu.cp311-win_amd64.pyd`;
- expected wheel `vispy-0.17.0+vulkan.1-cp311-cp311-win_amd64.whl`.

The recorded Windows toolchain is Visual Studio 17 2022 x64/v143, MSVC toolset
14.44.35207, compiler 19.44.35225.0, and SDK 10.0.22621.0. Compiler path/hash and
the existing CMake compiler metadata hash are recorded. The build command pins
that toolset/SDK and Release configuration. The current installation was
identified as Visual Studio Community 2022 17.14.37203.1.

## Build isolation and native dependency reuse

When root declares the native/Python sources stable, freeze them into a new short
path, for example `build/c11`, using `cmake/snapshot_wheel_sources.py`. The script
copies precisely hashed source bytes and excludes `.pyd`, `.dll`, `.so` and
Python caches. The immutable Dawn/parity dependency sources are shared through
junctions and must pass complete dependency verification before and after the
candidate build.

The CPython 3.11 candidate uses a new `build/n11` cache inside that snapshot,
explicit build-environment `Python_EXECUTABLE` and `Python3_EXECUTABLE`, and
`VISPY_INPLACE=OFF`. It cannot reuse the CPython 3.12 `_dawn`, SDF module, nanobind
objects or CMake Python cache. The prepared command also checks the original
source `.pyd`/`.dll` inventory and hashes before/after the build. Reserve a native
build slot so another root build cannot legitimately change that inventory
during this check.

Sharing verified native dependency source trees is implemented. Importing the
existing prebuilt Dawn/glslang/SPIRV libraries into an independent CMake graph is
not implemented. The current graph always adds the vendored Dawn subdirectory,
and the observed cache has no usable exported Dawn package/targets. A fresh
isolated cache therefore recompiles those libraries. Faster binary reuse would
require a separate immutable exported prefix/imported-target integration with
the complete transitive libraries, generated/public headers, exact source
digests, compiler/SDK/runtime/assertion flags and configuration provenance. Do
not point a second configure at the live CPython 3.12 Dawn binary directory or
copy its CMake cache.

## Prepared commands, not executed

After source stabilization, capture a fresh snapshot:

```powershell
.venv/Scripts/python.exe cmake/snapshot_wheel_sources.py build/c11
```

Then, when root schedules the candidate native build:

```powershell
compat/cp311-candidate/build-from-stable-snapshot.ps1 -Snapshot build/c11 -Evidence build/evidence/cp311-candidate-1
```

The script requires a frozen-source manifest and a new evidence directory. It
uses the hash-checked installed build tools with `uv build --no-build-isolation`,
keeps the native cache/output separate, records artifact hashes/source manifest,
and restores the caller's CMake environment variables. Preparation alone does
not establish that this build succeeds.

The already prepared runtime environments remain separate:
`build/host-environments/dive-cpython311-pyqt5` and
`build/host-environments/visbrain-cpython311-pyqt5`. Both have NumPy 1.26.4 and
upstream VisPy 0.17.0; DIVE additionally has pandas 1.5.3. The candidate's NumPy
2.4.6 build versus NumPy 1.26.4 runtime needs an actual SDF import/reference and
wheel-consumer ABI check. Consumer tests must run outside the source checkout,
verify exact module origins/native hashes, then uninstall/restore hashed
upstream VisPy before host admission.

## DIVE admission remains unresolved

The four real upstream DIVE children failed at the pinned manager's public
`QSplitter.setSizes` call because its list contains floats. The current locked
PyQt5 5.15.11 binding rejects those values. Logs/manifest and source hashes are
preserved under `tests/reference/dive-opengl` and the admission record remains
unresolved. A cp311 wheel cannot fix that upstream host failure.

The source README gives no Qt/SIP version bounds. An older binding combination
must demonstrate accepted unchanged public widget construction and capture
before an alternate isolated lock could admit DIVE. Host patches, monkeypatches
and treating missing screenshots as passing skips do not supply that proof.
Historical primary-source inspection is recorded in `dive-qt-history.json`.
The PyPI sdists for PyQt5 5.15.6, 5.15.9 and 5.15.11 declare
`QSplitter.setSizes(const QList<int>&)` and map each QList integer through
`sipLong_AsInt`. The inspected SIP 12.8.1, 12.9.1, 12.11.0 and 12.20.0 sources
convert that integer through `PyLong_AsLongLong`; they provide no float coercion
in that path. The actual CPython 3.11.11 C API probe accepted integer 100 and
rejected floats 100.0 and 100.5 for both `PyLong_AsLong` and
`PyLong_AsLongLong`. Its result and hash are preserved in
`cpython311-integer-conversion.json`.

Primary wheel metadata also shows no CPython 3.11 Windows wheel for SIP 12.8.1 or
12.9.1. PyQt5 5.15.6's abi3 wheel and SIP 12.11.0's cp311 wheel are available,
but the inspected source still routes float inputs into the rejecting API. This
is a source-backed inference about those inspected combinations; it does not
claim a runtime test of every historical binding release. No alternate lock or
environment is presented as compatible, and no host source was patched.
