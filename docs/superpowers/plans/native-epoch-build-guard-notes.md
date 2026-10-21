# Sealed native build epochs

`tools/freeze_native_epoch.py` and `tools/build_native_epoch.py` prepare new Windows x64 standard CPython 3.12 SDK builds. They do not replace the fixed pass25 tools or authorize activation or graphics qualification. Pass25 still requires its original pass24 baseline and original frozen-input pin.

Both new entrypoints require a workspace-relative ownership manifest and its separately reviewed SHA256. The build also requires the separately reviewed frozen-inputs SHA256. There is no default source, evidence, cache, SDK, activation or epoch. Do not create a sealed manifest until every source owner has acknowledged its tested archive; the current next epoch needs both the ordinary-input packet and the root-owned unsized-texture after-proof.

The schema1 ownership manifest must contain:

| Field | Required content |
| --- | --- |
| `schema`, `sealed`, `epoch`, `snapshot_epoch` | `1`, `true`, explicit new pass number at least 26 and source number at least 12. New freezes must advance past all existing epoch directories. |
| `paths` | Exactly `snapshot`, `evidence`, `harness`, `build`, `sdk`, `preparation`, `activation`, all lexical workspace-relative paths. For pass26/w12 the first four are `build/w12/source`, `build/evidence/native-pass-26`, its `harness`, and `build/native-pass26-sdk`. |
| `activation_manifest_sha256`, `protected_native` | Hash of the current acknowledged activation manifest and every current native module/library plus layer JSON under `src/vispy`. The four activated artifact hashes must agree with this full protected map. |
| `preparation_sha256`, `ctest_sha256` | Exact prepared CP312 interpreter/environment/toolchain record and CTest executable. Interpreter wrapper/base executable, environment configuration, CMake, build-module origins and dependency requirement lock are checked. |
| `sdk_manifest_sha256` | Exact compatible-CRT SDK manifest. The public SDK verifier checks complete exports/headers/libraries, compiler, configuration, runtime, policy and dependency-lock identities. |
| `source_files` | Full project-source relative-path to SHA256 map, using the same source roots as wheel snapshots. Native binaries, caches and the installed layer JSON are excluded. Every source byte is pinned before capture. |
| `harness_inputs` | Target relative-path to `{path, sha256}` map. `path` is the explicit workspace-relative input origin. Include matching copies of every `cpp/` file, all applicable contracts and their datasets. |
| `packets` | Distinct sealed CPU proof descriptors described below, with disjoint source ownership. Full archives are verified and copied; retained earlier failure evidence remains separate. |
| `tool_files` | Exact hashes of `tools/native_epoch.py`, `tools/freeze_native_epoch.py`, `tools/build_native_epoch.py`. |
| `targets`, `ctest_expected_names` | Explicit native leaf/contract targets and exact executed CTest names. All existing native and contract targets are required; additional targets must be contracts. Vendor rebuild targets are rejected. |
| `sdk_tint_reader_enabled` | `false`. Matching full-source CPU Tint evidence belongs in the sealed archives; SDK contracts use the exported public headers. |

Each CPU descriptor has `name`, `sealed: true`, `archive`, full `files` map, `files_tree_sha256`, `owned_files`, `source_tree_sha256`, `proof_file`, and `proof_assertions`. `owned_files` maps project source names to archive-relative source files; its tree digest hashes project names and their archived checksums. `proof_assertions` maps dotted JSON paths to exact values, for example `compile_exit: 0` and `run_exit: 0`. At least one successful exit assertion is required, and every asserted exit must be zero. Reviewers must include all successful terminal compile/run gates for the packet; preserved earlier failing attempts must not be asserted as its terminal result. The full archive inventory includes proof JSON, logs, executables, objects, sources and datasets, including any archive hash manifest itself.

Tree identities hash sorted POSIX relative names, a NUL byte, and raw SHA256 bytes. File names must be unique lexical relative paths without traversal. Source destinations, evidence, caches and archived inputs reject symlinks and Windows junctions. Only the two checked vendor-source dependency links inside a newly created snapshot are intentional; their immutable source trees are verified before and after the native build.

Run read-only freeze preflight first, then capture only after the source owners acknowledge the manifest:

```powershell
.venv/Scripts/python.exe -B tools/freeze_native_epoch.py --ownership-manifest compat/native-epochs/<epoch>-ownership.json --ownership-sha256 <reviewed-sha256> --preflight-only
.venv/Scripts/python.exe -B tools/freeze_native_epoch.py --ownership-manifest compat/native-epochs/<epoch>-ownership.json --ownership-sha256 <reviewed-sha256>
```

Review the emitted source/harness/frozen-input identities before starting a build:

```powershell
.venv/Scripts/python.exe -B tools/build_native_epoch.py --ownership-manifest compat/native-epochs/<epoch>-ownership.json --ownership-sha256 <reviewed-sha256> --frozen-inputs-sha256 <reviewed-freeze-sha256> --preflight-only
.venv/Scripts/python.exe -B tools/build_native_epoch.py --ownership-manifest compat/native-epochs/<epoch>-ownership.json --ownership-sha256 <reviewed-sha256> --frozen-inputs-sha256 <reviewed-freeze-sha256>
```

Initial source/evidence/cache destinations must be absent, and a first build accepts only the five freeze outputs: frozen-inputs JSON, ownership-manifest JSON, harness, sealed CPU packets and archived guard-tool sources. Partial freezes and prior attempt outputs are retained and rejected. Builds claim an exclusive active lock after read-only checks. An interrupted or failed build can use `--resume --attempt <fresh-label>` only with an owned configured cache whose actual cache hash and all source/harness/Python/SDK/toolchain/settings match the approved epoch. Resume never overwrites an attempt. A stale active lock requires inspection and an explicit recovery decision; it is not removed automatically.

Child jobs receive `CL_MPCount=3`; the parent environment stays unchanged. Unrecorded ambient `CL`, `_CL_`, `CFLAGS`, `CXXFLAGS` and `CMAKE_TOOLCHAIN_FILE` overrides are rejected. Generated projects must attest the legacy-compatible CRT mutex policy, omit the SDK's unavailable private Tint reader, and contain no vendor build graph. Success requires exact CTest inventory, no failures/errors/skips/unexecuted cases, unchanged frozen inputs, repeated SDK/dependency checks, complete native output archive and unchanged protected activation. Only then is a CPU/native success record written. No tool copies outputs into `src`, activates artifacts, runs a GPU fixture or qualifies a wheel.
