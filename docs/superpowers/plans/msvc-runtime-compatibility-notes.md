# Windows MSVC runtime compatibility evidence and rebuild gate

The installed frozen-w5 CP310/PySide2 DIVE candidate fails before either image
fixture renders. Both original children exit `0xC0000005` when the Qt backend's
first provenance canvas calls `_dawn.register_canvas`. The retained native dump
reads address zero in bundled `MSVCP140.dll` at RVA `0x12590`.

The candidate module's exact PE bytes prove the caller chain: return RVA
`0x535fb`, relative call at `0x535f6`, import thunk `0x808a88`, IAT entry
`0x844188`, symbol `MSVCP140.dll:_Mtx_lock`. The module hash matches the actual
CP310 wheel. The wheel has no matching leaf PDB, so those original renderer
frames remain named by module/RVA; the unrelated CP312 PDB was not substituted.

The exact pinned Shiboken2/PySide2 runtime is `14.24.28127.4`, SHA256
`f87819ae8c6f7c90d3237a1abb9809e8cba9dcd0c80ac3f0969a5e68ef652ca4`.
System32's installed runtime is `14.50.35719.0`, SHA256
`def46aa6a8f72f27bafac0c43334419486a4d1dcdb6c479a8ef7034b3e1fa4cb`.
The SDK/leaf compiler is MSVC `19.44.35225.0`, toolset `14.44.35207`.
Its actual installed `<mutex>` header defaults to constexpr storage
initialization; `_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR` selects the alternative
call to `_Mtx_init_in_situ`.

An independent seven-line C++ DLL constructs and locks one `std::mutex`. Both
variants use `/MD /O2 /Ob2 /DNDEBUG`, plus `/Zi /DEBUG` for genuine diagnostic
symbols. Their only compiler-policy difference is that compatibility
definition. Each runs in a fresh CPU-only child, explicitly loading one exact
runtime path. The diagnostic DLL's resolved mutex IAT pointer is verified to
equal that selected runtime's exported function pointer.

| Selected runtime | Default constructor | Compatibility constructor |
| --- | --- | --- |
| Exact pinned 14.24 | Exit 1, null access violation | Exit 0, result 73 |
| Installed System32 14.50 | Exit 0, result 73 | Exit 0, result 73 |

The old/default failure is caught by ctypes as an access-violation error; it
does not become a success. A first-chance native dump with the diagnostic DLL's
matching PDB identifies `vispy_mutex_probe` at its lock-guard source line and the
same runtime RVA/null read as DIVE. No Qt, VisPy, device or graphics context is
created by these four controls. No host, binding or system DLL was replaced.

The immutable CPU proof is
`compat/native-sdk/msvc-legacy-crt-compatibility-proof.json`, SHA256
`4594f30e7e56214bbbda46d10ae41a39a4d4a36dcef129949a7da088d47b3e0a`.
Copied source, actual compiler/argument/DLL/PDB/runtime identities, four child
records and matching-symbol dump are under
`build/evidence/crt-mutex-compatibility-1`. The original renderer failure,
unsymbolized dump and exact IAT mapping remain under
`build/evidence/dive-pyside2-style-candidate-w5-{pass-1,debug-1}`.

The Windows build now defaults to the compatibility policy. The helper is
included before vendor targets and adds the definition to the global C++ flags,
covering vendor object libraries, Python/native leaves and the Vulkan layer.
Explicit `VISPY_LEGACY_MSVC_CRT_MUTEX=OFF` selects the earlier constexpr policy.
Other platforms retain their existing flags. SDK schema 2 records the compiler
policy and the actual Release/x64 settings of every generated C++ source item.
Exact macro definitions are required; explicit `/U` switches, MSBuild
undefinitions, source overrides without inheritance and missing compiler
settings are rejected. The verifier also checks common and Release compiler
flags. Existing schema 1 SDKs are rejected by the new consumer; their original
frozen helpers and successful core-wheel proofs remain preserved.

All 28 SDK policy CPU contracts passed, including the negative cases, in
`build/evidence/native-sdk-compatibility-policy-4.{log,xml}`. These contracts use
synthetic archives and actual configure-only CMake import checks. They do not
establish a new SDK archive or graphics qualification.

The first isolated producer configure is retained in
`build/evidence/compatible-producer-configure.log`. It failed before compilation
because contract targets were enabled while the frozen wheel source omitted
their C++ files. No old producer archives were reused. The corrected full
producer uses new cache `build/p3c`, contract targets disabled and frozen source
`build/w8b/source`, SHA256
`01c3e80263277f24392f028cde7dc9576072cabdabf4e9329d02449ddb9f8fc4`.
Its runtime is exact `build/w7/source`, SHA256
`ce3ebfb7d9f413e3c9ecb8fb363798ad7476e9464256e5fdff3d193a97d2c1d2`;
only reviewed packaging inputs are refreshed. Build commands, preparation,
generated compiler-policy checks and protected source-binary hashes are
recorded in `build/evidence/w8b-compatible-producer-2`. The earlier p3b attempt
is preserved under `w8b-compatible-producer-1`: Windows PowerShell 5.1 treated
an upstream fallback Git diagnostic on stderr as a terminating error before
compilation. The corrected runner retains stderr and checks the actual process
exit code. Configure completed with exit 0; the generated-project verifier
confirmed the policy in 1,218 C++ source items across 284 projects before
launching the full vendor build. Matching pass23 CPU
binaries remain separate evidence; current mutable contract sources are not
substituted into this older runtime snapshot.

The full new vendor build completed with exit 0. Post-build source verification
confirmed all ten pinned dependency trees. SDK prefix
`build/native-sdk/windows-x64-release-3` contains 224 immutable copied files and
the five newly built vendor archives. Its schema 2 manifest SHA256 is
`7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2`.
No old default archives or Python ABI objects were reused. The active source
pass23 native module, layer and SDF hashes remained unchanged throughout.

Freeze a new truthful renderer/packaging snapshot before building compatible
ABI leaves. Repeat CP310–314 clean core consumers, then real Qt5/Qt6 canvas and
installed host/plugin comparisons. The original five frozen-w5 core wheels and
their successful headless/rollback evidence remain immutable. Their core passes
do not admit the failed PySide2 host. The DIVE style runner's separately scoped
image/export oracle also cannot admit ordinary unchanged DIVE teardown or its
unresolved scatter API path.

Two isolated compatible ABI leaves were built from w8b:

| ABI | Wheel SHA256 | Observed result |
| --- | --- | --- |
| CP312 | `45bc3695f0ca081ab130d576ce26a9c7bae767a3aa73b07020cdd7c1abcc59e8` | Clean external Vulkan/Text/SDF/assets/notices/uninstall/hash-locked upstream restoration passed |
| CP310 | `31ead88d65629cd85d026d68c44156a1dce6411c18c6b5bd82a6ff1d2ff9d5c2` | NumPy1.26.4, binding-first old-CRT imports/native mutex and actual scoped DIVE rendering/clean exit passed; full-frame parity failed |

The CP312 consumer log/XML are
`build/evidence/w8b-clean-wheel-cp312-consumer.{log,xml}`. It passed one test with
zero skips/errors/failures on RTX4090/Vulkan 595.79. The CP310 environment is
`build/host-environments/dive-pyside2-cpython310-candidate-w8b`; all 22 dependency
versions match the prior candidate and the pinned DIVE package is unchanged.
Binding-first import confirms the actual bundled old-runtime hash. Two native
shutdown mutex locks passed without creating a QApplication, context or device.
CPU origin/SDF/dependency evidence is under
`build/evidence/w8b-dive-pyside2-cpu-preflight`.

The unchanged scoped style runner then ran `image` and `image_edit` in separate
actual GPU children. Both exited 0, passed fixed landmarks and public export,
and destroyed their owned Qt objects. Exact full-frame comparison still fails:
all three RGBA frames differ at 2,178 pixels; channel maximum differences are
`[1,1,1,64]`. PNG bytes also differ. The only captured parameter difference is
the expected QWidget/QOpenGLWidget backend MRO. The candidate manifest is
`build/evidence/dive-pyside2-style-candidate-w8b-pass-1/manifest.json`; the strict
comparison is `comparison.json` in that directory. The comparison command is:

```powershell
.venv/Scripts/python.exe tools/compare_dive_installed.py --reference tests/reference/dive-pyside2-style-opengl --candidate build/evidence/dive-pyside2-style-candidate-w8b-pass-1 --output NEW-COMPARISON.json
```

It returns exit 1 for the preserved mismatch. No pixel criteria, host, fixture,
Qt binding or reference files were changed. The successful legacy initialization
does not admit full-frame parity, ordinary unchanged DIVE teardown or scatter.

The sealed result is
`compat/native-sdk/w8b-compatible-windows-provenance.json`, SHA256
`6f9280f88ddb5814b3a2f7384c53e5c874dd708cd4bf8d88e48104e059954699`.
All 31 policy and actual-evidence CPU contracts passed in
`build/evidence/w8b-compatible-sdk-contracts.{log,xml}`. Remaining gates are
compatible CP310 core rollback and CP311/313/314 builds/consumers, corrected
exact scoped screenshot parity, final-runtime artifacts and installed binding,
host and plugin comparisons. Linux/macOS producers and hardware remain separate
platform acceptance gates.
