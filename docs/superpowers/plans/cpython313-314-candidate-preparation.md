# CPython 3.13 and 3.14 candidate wheel preparation

The Windows x86_64 build-only environments are installed and their public module
imports pass. No VisPy wheel or native target was built for either interpreter.
The release matrix still requires actual CPython 3.10–3.14 artifacts and external
consumer qualification for each artifact.

| Observed input | CPython 3.13 | CPython 3.14 |
| --- | --- | --- |
| Exact interpreter | 3.13.8 | 3.14.0 |
| Standard ABI / SOABI | cp313 / cp313-win_amd64 | cp314 / cp314-win_amd64 |
| Extension suffix | .cp313-win_amd64.pyd | .cp314-win_amd64.pyd |
| Build environment | build/cp313-candidate/build-env | build/cp314-candidate/build-env |
| Future snapshot build directory | build/n13 | build/n14 |
| Preparation manifest SHA-256 | 3fdc93232408ff212e6f0298b67002970bc0eddfad61835251c19337c9115641 | cf7690b69ae395f23cac76c0560178548ca1d55688edeb738e5424c7cfc5beb9 |

The exact patch versions match the current CI matrix. These are regular CPython
interpreters: the observed pointer size is eight bytes, `Py_GIL_DISABLED` is
unset, and `sys._is_gil_enabled()` returns true. Free threaded wheel qualification
has no evidence in this packet.

`cmake/prepare_newer_candidates.py` selected the active exact build requirements
and their dependency closure from the existing `uv.lock`. It admitted only
compatible standard CPython Windows wheels and installed with `--require-hashes`
and `--only-binary :all:`. Both environments contain exactly seven distributions:
CMake 4.4.4, Cython 3.1.5, nanobind 3.1.0, NumPy 2.5.3, packaging 26.3, pathspec
1.1.1, and scikit-build-core 0.11.6. The root environment and lock were not changed.

The executed preparation commands were:

```powershell
.venv/Scripts/python.exe cmake/prepare_newer_candidates.py --python-version 3.13.8 --install
.venv/Scripts/python.exe cmake/prepare_newer_candidates.py --python-version 3.14.0 --install
```

The two `compat/cp31*-candidate/preparation.json` files retain interpreter and
base-interpreter binary hashes, installed distribution RECORD hashes, actual
module origins and hashes, NumPy header paths, selected wheel URLs and hashes,
requirements hashes, and root packaging input hashes. Every observed build module
origin is inside its dedicated environment. The environment's CMake executable
was run only for its version; configure and build were not invoked.

The observed existing compiler is MSVC 19.44.35225.0, toolset
`v143,version=14.44.35207`. The compiler binary and its generated CMake metadata
are hashed. Windows SDK 10.0.22621.0 was additionally verified from the existing
`_dawn.vcxproj`; that project's hash and path are retained. These are observed
toolchain inputs, not proof that this compiler accepts both new Python headers
or that pinned Dawn builds with either interpreter.

Both preparation runs observed three source-package native artifacts before and
after their own work, with identical hashes. These hashes are historical
observations. Root's later native work may replace those artifacts. A future
isolated build compares the source artifact inventory immediately before and
after its own execution; it does not require equality with historical hashes.

The future commands below have **not** been executed. Root must first reserve a
native build slot and provide a stable, complete frozen source snapshot whose
`wheel-source-manifest.json` includes the matching `pyproject.toml` and `uv.lock`
hashes:

```powershell
& compat/cp313-candidate/build-from-stable-snapshot.ps1 -Snapshot <frozen-source-directory> -Evidence <new-evidence-directory>
& compat/cp314-candidate/build-from-stable-snapshot.ps1 -Snapshot <frozen-source-directory> -Evidence <new-evidence-directory>
```

Both scripts passed the PowerShell parser. They pin the prepared interpreter for
both CMake Python discovery variables, select separate snapshot build directories,
verify vendored source hashes before and after the build, set `VISPY_INPLACE=OFF`,
and require a new evidence directory. They record source native inventory at
build start and compare it at completion. They require exactly one expected
standard-ABI wheel and record its hash plus the frozen source manifest.
Dependency reuse is limited to verified source trees; sharing prebuilt Dawn
libraries across these Python builds has not been implemented or qualified.

The preparation contracts passed with the plugin and packaging input contracts:
`16 passed` using
`.venv/Scripts/python.exe -m pytest tests/contract/test_newer_build_environments.py tests/contract/test_plugin_registration.py tests/contract/test_package_inputs.py -q`.
The 16 Pydantic deprecation warnings came from existing pytest plugin loading and
are retained in the command output.

Acceptance gates remain: build each wheel from the frozen milestone; verify
installed compiled `_dawn` and `_sdf_cpu` module ABI/origins, CPU SDF behavior,
packaged shader/font assets and licenses outside the checkout; prove rollback;
then run actual graphics and public Qt lifecycle fixtures in separate supported
binding environments. A missing binding or host is unresolved qualification.
No GPU run, green skip, platform support, host admission, or published release is
claimed by this preparation packet.
