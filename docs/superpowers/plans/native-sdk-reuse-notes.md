# Immutable native SDK reuse for the Python wheel matrix

The opt-in export/import route has produced actual isolated CPython 3.12 and
3.10–3.14 wheels from the same frozen renderer. All five passed separate clean
external consumers with actual headless native pixels, Text, compiled SDF,
packaged assets/notices, uninstall and hashed upstream restoration. CPython
3.10 also proved a NumPy 2.2.6-built extension against NumPy 1.26.4 at runtime.
These checks do not admit public Qt/host fixtures. This reuse route supports Windows x86_64/MSVC Release;
other platforms retain the full source build and need their own qualified
producer artifacts. The complete release and host matrix remains unqualified.

The existing Release renderer links five vendor archives: `webgpu_dawn.lib`,
`glslang.lib`, `glslang-default-resource-limits.lib`, `SPIRV-Tools.lib` and
`SPIRV-Tools-opt.lib`. The monolithic Dawn archive already bundles its internal
Dawn/Tint/Abseil dependencies. Its configured CMake target also preserves the
remaining Windows system library requirements. The separate `nanobind-static`
archive and Python import library are ABI leaves and are not reusable.

Pinned Dawn's official package export installs the monolithic target and public
configuration interface. Those rules are disabled in the current producer;
Dawn also forces SPIRV installation off. Full upstream glslang/SPIRV install sets
include unused compatibility stubs/shared libraries that are not currently built.
`cmake/NativeSDK.cmake` therefore follows the same CMake target export mechanism
for the actual five archives plus `dawn_public_config`, through a dedicated
`VispyNativeSDK` install component. CMake generates the imported target metadata,
including the optimizer-to-static dependency and Dawn's Windows system links.
There is no manually reconstructed linker closure or modification to pinned
vendor sources.

The SDK copies public Dawn headers, generated Dawn API headers, glslang build
information and public header layout, SPIRV-Tools/SPIRV-Headers/Vulkan headers,
vendor source pins and licenses into its own prefix. Exported include paths and
archive locations use that prefix. The consumer does not use the producer's
source tree or build directory. Compiler paths in provenance remain historical
observations; they are not imported include/library paths.

`tools/stage_native_sdk.py` requires an already configured producer with
`VISPY_EXPORT_NATIVE_SDK=ON`, dependency verification enabled, and no imported SDK.
It checks the actual generated Visual Studio archive projects for the Release DLL
CRT, checks the generated Windows SDK value, and runs only `cmake --install`
for the SDK component into a new directory. It records every installed file hash,
actual compiler fingerprint, source-pin lock, producer cache/project hashes and
configuration. It also compares source-package native binaries immediately
before and after staging. It does not configure or compile a target.

The existing stable producer cache was configured once with the export flag,
explicit Python/Python3 discovery and its existing MSVC/SDK selection. It verified
ten pinned source trees and did not compile a target. Its original generator
toolset cache entry is empty; the actual compiler path, version and bytes are
recorded rather than changing that populated cache's generator identity.
The successful staging command was:

```powershell
.venv/Scripts/python.exe tools/stage_native_sdk.py --build build/cp312-cp312-win_amd64 --output build/native-sdk/windows-x64-release-2
```

This SDK contains 224 files; its trusted manifest SHA256 is
`931745be90801980a2291a830d9e5846f301ab26b386662957817445fb72556d`.
The first staging attempt is preserved in `windows-x64-release-1`: its policy
regex incorrectly read the suffix of a CMake `LINK_ONLY:` expression as an
absolute drive path. The corrected verifier has a regression contract. Actual
export inspection also exposed Dawn's `Threads::Threads` requirement, so the
package config now calls `find_dependency(Threads)` before loading its exports.
The package-only refresh and second install performed no vendor compilation.
`cmake/native_sdk.py` checks the trusted identity before
loading any imported CMake code. It rejects changed/missing/extra files, source
pins, architecture, pointer size, configuration, CRT, CMake/compiler versions,
compiler bytes, Windows SDK, compiler flags, and archives or exports containing
Python/nanobind ABI dependencies. Consumers restrict multi-config builds to
Release so CMake cannot silently substitute Release archives in a Debug build.

For an independently frozen snapshot, set both `VISPY_NATIVE_SDK` and
`VISPY_NATIVE_SDK_MANIFEST_SHA256`. The consumer skips the Dawn/glslang source
subdirectories and imports their configured target aliases. It still builds
nanobind, the `_dawn` binding/runtime/shader/platform sources, compiled Cython SDF,
and the small Vulkan layer in its own ABI cache. `VISPY_INPLACE=OFF` remains
required. Existing full source defaults are unchanged.

The new `tools/build_sdk_leaf.ps1` accepts a prepared interpreter manifest, a
complete frozen source snapshot, new evidence directory, SDK prefix and trusted
hash. It sets both CMake Python discovery variables, a separate
`build/sdk-<abi>` cache, Release, source verification and no in-place copying. It
captures the SDK and source manifests plus protected source binary hashes around
each build, checks the expected wheel ABI, and records the wheel hash. The actual
CP312 leaf used seven hash-locked build dependencies in its dedicated environment;
the actual CP310 leaf used its ten-package lock, including NumPy 2.2.6. Both
compiled nanobind and the Python/native leaves in separate caches without
compiling the SDK vendor graph. The protected source binary inventories were
identical before and after each build. CP311/313/314 then completed real artifact
builds in their own caches, exit 0. The CP310 legacy-manifest preflight failure is preserved separately;
the corrected script supports the original preparation schema and verifies the
observed uv version. The exact original CP312 script is archived at
`compat/native-sdk/w5-cp312-build-script.ps1`.

Root's renderer milestone `build/w4/source` remains immutable. `build/w5/source`
overlays its exact frozen `cpp`/`src` content with the reviewed packaging/CMake
helpers. Its 577-file source tree SHA256 is
`69ef9e8160837e71222146f3403a721b4548f3ed1a8b48901d12513ed4e3bda8`.
The manifest records its w4 runtime provenance and file-by-file equality; live
telemetry changes were excluded. These artifacts qualify this frozen renderer,
not subsequent live-source changes.

The SDK exports only public vendor APIs. The private CPU Tint reader harness still
runs in the full source producer. SDK-mode shader contracts validate shader/SPIRV
behavior but do not enable that private header harness. Actual installed Text and
other native graphics fixtures remain necessary for each consumer wheel.

Validation completed: 18 synthetic CPU policy/relocation/import contracts passed;
the CMake import contract uses `LANGUAGES NONE`, without compiler execution. A new
actual producer configure-only cache at `build/sdk-export-configure-contract`
verified ten immutable source trees and generated the real six-target exports
successfully. No libraries were built or installed from that cache. Its initial
PowerShell command emitted an extra-argument warning for an unquoted dotted
system-version definition; the selected/recorded SDK is nevertheless
10.0.22621.0. Future producer commands must quote all definition arguments.

The CP312 wheel SHA256 is
`e94ab51c4d3ad37333506af3c1b99ea3ce05cccd34bb4ea682e63ad70f2c1c3c`.
The actual clean consumer passed one complete install/render/uninstall/restore
contract, exit 0, on NVIDIA RTX4090/Vulkan driver 595.79. It ran outside the
checkout with NumPy 2.5.3, exercised compiled SDF and rendered Text, and restored
the hash-locked upstream VisPy 0.17.0 wheel. Evidence is
`build/evidence/w5-clean-wheel-consumer.{log,xml}`. The SDK, source, native
archives, leaf build and consumer hashes are anchored in
`compat/native-sdk/windows-sdk-reuse-provenance.json`.

The CP310 wheel SHA256 is
`6a1b9f74f7eac4e8fcd665fa78302b2018b71e3929576dfd1571ff53b3857e34`.
Its successful exit-0 build, source/SDK identities and protected binary checks
are under `build/evidence/w5-sdk-cp310` and
`build/evidence/w5-sdk-cp310-build.log`. Its actual NumPy 2.2.6-built extension ran
with NumPy 1.26.4, including a real font glyph and in-place distance transform,
in both a new external minimal environment and the separate locked DIVE/PySide2
candidate environment. These CPU-only witnesses are anchored in
`compat/host-environments/cp310-candidate-numpy126-provenance-w5.json`.

All five actual ABI artifact hashes, native module identities, protected
before/after inventories, preparation manifests and build logs are recorded in
`compat/native-sdk/w5-windows-python-matrix-provenance.json`. The additional wheel
hashes are:

| ABI | SHA256 | External graphics/rollback |
| --- | --- | --- |
| CP311 | `1972fad5374f42ca1b5dfe4b167a88f2ec889041756c1b3122f5b41f771e45d7` | Verified headless consumer |
| CP313 | `041e98665333c0379390c307fab6123f04726db59d5b5fdc2dde3776876f9b0a` | Verified headless consumer |
| CP314 | `bf00f00096f03f93b1cba863d25f139b63a04f2e1450f52504f9b70f59aa54f6` | Verified headless consumer |

Each additional consumer passed one complete install/render/uninstall/restore
contract, exit 0 without skips, serialized on RTX4090/Vulkan 595.79. Runtime NumPy
versions were 1.26.4 for CP310, 2.4.6 for CP311 and 2.5.3 for CP313/314. Each
protected source-native inventory matched before and after. The immutable
post-consumer witness is
`compat/native-sdk/w5-windows-clean-consumers-provenance.json`; individual logs
and XML are `build/evidence/w5-clean-wheel-{abi}-consumer.{log,xml}`.

The installed CP310/PySide2 DIVE attempt exposed a separate native compatibility
failure before any image rendered: Qt loads bundled MSVCP140 14.24, while the
14.44 STL's default constexpr mutex constructor requires a compatible runtime.
The exact candidate PE callsite resolves to `_Mtx_lock`; the retained native
dump reads address zero there. A minimal CPU DLL reproduced the failure with
the exact bundled runtime. Defining `_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR`
passed against that old runtime, and both variants passed against modern
System32 14.50. The matched diagnostic PDB names the mutex lock source line.
Evidence is anchored in
`compat/native-sdk/msvc-legacy-crt-compatibility-proof.json`.

A compatibility producer/SDK rebuild completed. The reviewed global
Windows C++ policy enables the definition before vendor, leaf and layer targets
are created. SDK schema 2 records the policy and rejects original schema 1
archives or contradictory macro switches. All 28 policy CPU contracts passed;
the actual new producer verified 1,218 C++ source items across 284 generated
projects before compilation. Evidence is under
`build/evidence/w8b-compatible-producer-2`; its new cache is `build/p3c` and its
frozen w8b source uses exact pass23/w7 runtime with current packaging inputs.
No old archives are reused. New prefix
`build/native-sdk/windows-x64-release-3` has schema 2 manifest SHA256
`7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2`.
Actual isolated CP312/CP310 SDK leaves were built. The CP312 clean external
Text/SDF/native/assets/notices/uninstall/upstream-restoration consumer passed;
its wheel SHA256 is
`45bc3695f0ca081ab130d576ce26a9c7bae767a3aa73b07020cdd7c1abcc59e8`.
The CP310 compatible wheel SHA256 is
`31ead88d65629cd85d026d68c44156a1dce6411c18c6b5bd82a6ff1d2ff9d5c2`.
Its old-CRT CPU mutex/SDF/import checks and actual two scoped DIVE child renders
and clean exits pass. Exact screenshots fail at 2,178 pixels/channel max
`[1,1,1,64]`, so scoped pixel parity and ordinary host admission remain open.
The sealed mixed result is
`compat/native-sdk/w8b-compatible-windows-provenance.json`; 31 policy and
actual-evidence CPU contracts passed. See
`msvc-runtime-compatibility-notes.md` for retained preflight failures and
compiler-policy checks. The original five w5 artifacts and failed DIVE
attempt remain unchanged. The next gates are the remaining compatible ABI and
final-runtime artifacts, installed public Qt/host graphics and lifecycle
comparisons, then architecture-specific
Linux/macOS producers and consumers. A final release artifact must freeze the
finished runtime and repeat relevant admission gates. SDK hashes establish
dependency reuse provenance; they do not admit a host or graphics result.

The pass24 SDK3 native build used frozen w9 source, separate immutable harness
inputs and a new cache. It built without vendor recompilation and passed all
14 supplied CTest cases. SDK contracts omit private Tint-reader tests; the
matching full-source Tint proof is separately archived under
`build/evidence/native-pass-24/full-source-tint-proof`. Root subsequently
activated these binaries; `native-pass-24/activation.json` is the protected
baseline for following leaves.

Frozen `build/w10/source` has digest
`f4154ac712aae052090dce67294b8d715825b4c3360f6b2a9fd9c60856581c8d`.
Its 581 inputs are identical to w9 except the verified `_qt.py` overlay,
digest `dfddee8774264d7e2a69618084d4248796704123f90305a96b319985699c8ef8`.
The snapshot did not read live C++ while the next storage implementation was
in progress. Actual CP312 and CP310 ABI-isolated leaves against unchanged SDK3
finished exit 0 with `CL_MPCount=3`, the compatible mutex policy and INPLACE OFF.
Their wheel hashes are respectively
`9ccde20b8f7e5b812faf88145e841ee9b78f0563ee91f589d2c7f12e87f8b705` and
`db49eaf39540906f7b10023f5252a10a5760a871208e26bbf935304c44a96647`.
Activated pass24 native files and the layer manifest matched before and after.
The initial Windows PowerShell module-loading failure is retained alongside
the successful PowerShell 7 retry.

New Glue CP312/PyQt6 and scoped DIVE CP310/PySide2 environments preserve original
host source and every original dependency version/hash, changing only the
candidate wheel. Their installed package/source/import CPU checks passed;
the DIVE probe also verified compiled SDF under NumPy1.26.4 and the native mutex
under Qt's bundled old CRT. The sealed CPU witness is
`compat/native-sdk/w10-qt-overlay-packaging-provenance.json`. These new wheels
have no installed graphics or rollback qualification in that witness. Exact
installed Glue volume and scoped DIVE full-frame/export comparisons remain
separate gates. Earlier w5/w8b graphics results and failures remain intact.

The separately authorized installed w10 scoped DIVE run now passes both
`image` and `image_edit`. Both children and the strict comparator exited 0;
every full RGBA array, including the edit-before frame, and every exported PNG
matched the fixed upstream bytes exactly. Public inputs and state matched,
allowing only the documented QOpenGLWidget-to-QWidget implementation difference.
The actual unchanged DIVE source, PySide2/NumPy1.26.4 lock, installed wheel
package hashes and Vulkan RTX4090/595.79 renderer origins are retained in
`compat/host-environments/dive-pyside2-candidate-w10-scoped-parity.json`.
Activated pass24 native artifacts matched before and after. Three scoped
parameter/evidence contracts passed. This closes the fixed w10 screenshot/export
alpha regression; ordinary unchanged host teardown, scatter and clean core
uninstall/restoration remain unqualified. All earlier failure artifacts and the
CPU-only w10 witness retain their original meanings.
