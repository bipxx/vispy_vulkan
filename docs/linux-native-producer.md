# Linux native producer integration

The selected WSL software profile has a working development module, not an
admitted native producer. Windows vendor SDK qualification cannot establish
Linux archive provenance. Keep the current producer policy blocked until the
complete Linux proof is implemented, independently reviewed and collected.

The shortest route is to use the existing full-source Linux wheel CI build as
the producer. It already builds the pinned dependencies and renderer together;
do not create a second SDK, environment or renderer build merely to collect a
different report format. The current installed workflow remains a separate
functional check and does not replace producer proof.

| Retained input / path | Current decision | Required next evidence |
| --- | --- | --- |
| Windows aggregate module `715022fbbcfa319cd504b8b9f91a53c983db1cba23a464f98525aff63c1158bf` and existing Windows SDK | Reuse for development checks; evaluate admission through the existing Windows provenance route. | Actual cumulative reviews and complete original/native-reuse joins; a functional pass alone does not admit this leaf. |
| Linux aggregate module `bde985b44e07f554a3ec653856e73d0e4c07518375ca614f9be9a5bf97eb5337` | Reuse for development checks. Its recorded first-party compile/link commands and four focused contracts do not supply a complete admitted Linux producer. | Full source/toolchain/dependency/configuration/output joins and required native contract evidence under an implemented Linux validator. |
| Existing Linux vendor archives recorded by `build/runs/aggregate-linux-77/vendor-inputs.json` | Preserve their exact origins and hashes. They are development inputs, not a qualified Linux SDK. | A reviewed original-provenance reuse decision or proof from the existing full-source CI build. Do not relabel their hashes as SDK qualification. |
| Existing Linux wheel CI build | Preferred collection path; its earlier archive check disabled native contracts. | Enable contracts in that same build, capture discovery and actual execution, then complete the source/compiler/generated-build/strip-output provenance joins. |

The first integration change enables `VISPY_BUILD_CONTRACT_TESTS` in the wheel
build. `tools/run_linux_native_contracts.py` captures original CTest discovery,
then runs the entire discovered inventory without a test filter. It records both
actual child PIDs, exits and waits, logs, JUnit, the CTest tool hash and unchanged
renderer cache. The original native-epoch JUnit verifier rejects missing,
duplicate, failed, skipped or unexecuted tests. All 44 current non-dataset
renderer contracts are a mandatory floor; additional discovered tests must also
execute. An empty or reduced discovery cannot become a pass. The archive audit binds the
same cache and complete retained reports before accepting its byte checks.

These reports are prerequisites. They do not yet prove the full dependency
build, compiler read set or stripped-output production chain, and they do not
admit a producer. Next, extend the existing native provenance/index route for the
Linux full-source build: bind original source/dependency snapshots and toolchain,
actual build commands and exits/waits, generated build configuration, all
shipping outputs and the controlled strip/install join. Preserve independent
candidate source/scope approval and reuse links, terminal retention, original
installed absence/control/shutdown evidence, complete attempt history and final
promotion review. No policy boolean or synthetic test fixture supplies those
proofs. Native Linux GPU and Metal hardware obligations remain separate.

Evidence and the finite retained-input decision are in
`build/runs/linux-producer-contracts-81/`. A source-only control uses real CTest
processes with explicitly synthetic Python test cases; it is transport and
rejection coverage, not execution of the renderer's C++ contracts.

The managed CI collection path is now implemented by
`tools/linux_ci_lifecycle.py`. The existing wheel build, environments and consumer
use one registered external native lease alongside Mesa's registered run in the
same workspace. Direct native commands retain actual argv/PID/exit/wait receipts;
setup scripts retain their original bytes. Source/license inputs and before/after
maps, raw CMake/Ninja/compile configuration, observed compiler/Python/tool hashes
and shipping outputs are retained before registry-aware cleanup. uv uses package
cache copy mode and its own per-run cache clean operation. Owned aliases are audited without
changing original targets, and source mutation remains a failed run after its
reproducer is saved and scratch removed. See
`build/runs/linux-ci-lifecycle-82/` for 517 Windows regression checks, 47 WSL
source controls and seven parsed/Bash-checked workflow bodies. The WSL controls
exercise actual processes and aliases with explicitly synthetic inputs.

This completes managed collection, not the Linux admission validator. The next
join must consume these original records through the existing native/index
route, check the complete dependency/build/strip-output chain and bind actual
independent reviews. Do not turn the unchanged experimental producer policy into
an approval or rebuild unchanged native inputs solely to fit a new report shape.

The first managed CI attempt (`40225865740`) failed during preparation, before
native compilation: `uv venv` does not accept the stdlib venv `--copies` option.
The workflow now uses supported uv arguments. Interpreter aliases are separately
materialized by the lifecycle tool, including the private relative libpython
required by standalone CPython. Existing conflicting runtime bytes are refused;
the base interpreter and library are never changed. A real existing CPython
3.12.8 control reproduces the missing-library failure before this repair and
successful execution afterward, without installing packages or rebuilding the
renderer. Run `build/runs/linux-native-join-83/` retains that before/after control,
the original failed CI evidence, 517 Windows checks and 49 WSL controls. These
checks do not establish successful producer CI or Linux admission.

The native/index source now adds `tools/qualification_linux_native.py` to the
existing native dispatcher and qualification index. It reads the original CI
state, preferred source archive, process receipts, build graph/toolchain,
unfiltered CTest discovery and execution, raw/stripped/wheel outputs and original
in-process cleanup records. Portable transport references preserve original
absolute origins and bytes. The index also requires terminal retention of every
raw capture input, including the original cleanup records, rather than retaining
only the transport wrapper. The observer protocol pins the preparation repair;
older incompatible collector bytes cannot silently supply successful proof.

A complete synthetic capture exercises this join and rejection controls without
running a native build. Its explicitly synthetic process records and ELF headers
are test fixtures, not producer evidence. The producer policy now requires
`reviewed-full-source-native-proof-required`; this names required evidence,
not an approval. Dispatch refuses an unreviewed real candidate before reading
its capture. The legacy experimental mode remains rejected. Exact independent
source/scope reuse approvals, original successful native capture, reviewed ABI
facts and all installed qualification/promotion gates are still required.
See `build/runs/linux-native-semantic-85/` for the initial local verification;
this source work does not admit an artifact or hardware profile.

Local verification passes 571 affected Windows regressions and 87 WSL
native-adapter/index controls. These include a successful synthetic native join,
31 rebound semantic rejection cases, portable transport checks, blocked real
producer policy and six outer-index raw-retention controls. Original failed
attempts remain retained. New CPU CI selects the maintained adapter tests; the
real subject still has 120 missing criteria and no admission.

The follow-up reuse-record controls pass all 64 adapter checks on Windows and
the 16 new reuse checks in WSL (`build/runs/linux-native-reuse-86/`). They test
distinct build Python 3.12.8 and consumer Python 3.12.13 facts, exact independent
review links, selected profile, production digest and refusal of unreviewed
candidates. The outer candidate-validation seam and all approval-like records
are explicitly synthetic. The suite retains legacy-policy refusal and now tests
the actual unreviewed-candidate guard; that test-only checkpoint supplied no actual approval, producer-policy
change or native rebuild.

CI run `40231008361` completed native compilation, then passed 43 of 44 native
contracts. `shader_contract` failed because its full-source Tint-reader branch
passed raw integer sampling SPIR-V directly to Tint, while production first
specializes captured nearest/one-level sampler policies and finalizes the stage.
The corrected contract keeps the original integer-array GLSL and reader
assertion, calls those existing production transforms, and requires the typed
array sample to actually be lowered. It does not remove a test or change renderer
code. A focused Linux build with the real retained Tint reader reproduces the
original failure and passes the full shader corpus after the correction. The
Windows SDK shader contract also passes; that SDK mode does not enable the Tint
reader branch. Original CI reports and cleanup remain retained in
`build/runs/linux-ci-failure-87/`. A successful new full-source CI result is still
required; these local controls do not turn the failed producer into admission.

Run `40235407061` subsequently passed native compilation, all 44 contracts,
archive audit and the installed-wheel smoke. The native validator now accepts
that original capture, with production identity
`6e21a4bbed7849a564bf5c425d1519ca7794327e61602aabdb5a4b8c0c59726f`.
It separately validates the measured CTest Python console launcher, its copied
interpreter and CMake's packaged ELF backend. The launcher digest is checked
against the known entry-point bytes with the original interpreter path; it is
not equated with the different ELF digest. Original process/PID/exit/wait records
remain unchanged. Recorded-format and changed-identity controls cover this join.

The original artifact upload omitted one byte: `wheels/.gitignore`. An existing
identical `*` byte matches the original terminal SHA-256; its hash-addressed
recovery and provenance are retained without changing any original record.
Future uploads explicitly include hidden files. Both exact known workflow
revisions are supported; unknown collector revisions still fail. CPU CI exposed
an incidental PyYAML dependency in the synthetic fixture. Standard-library
literal-block extraction removes that dependency, with YAML-blocked coverage.
See `build/runs/linux-ctest-launcher-89/` for original records and controls.
This establishes a native production prerequisite. Source/scope/reuse approval,
both selected installed qualification protocols, complete current-head CI and
promotion review remain open; the real subject is still unadmitted.
