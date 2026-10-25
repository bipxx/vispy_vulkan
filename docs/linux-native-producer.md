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
and shipping outputs are retained before registry-aware cleanup. uv uses copies
and its own per-run cache clean operation. Owned aliases are audited without
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
