# Admission selection before artifact qualification

`tools/compatibility_qualification.py` implements the selection part of H4a.
It cannot admit artifacts. The initial declaration is
`compat/candidates/tk-state-resource-1/admission-selection.json`; all 120 mapped
criteria across both development profiles remain requested. Its closed schema
is `compat/vispy-admission-selection.schema.json`.

Each request expands to all ordinary/mutation/failure/recovery criteria in its
execution row and every transitive required same-profile dependency row. Missing
rows/criteria, optional dependencies, profile substitution, cycles and duplicate
mappings fail. Closure and requested keys are sorted, unique and separately
retained. Changing the declared closure and recomputing the manifest seal does
not bypass deterministic recomputation against the validated execution map.

The selection digest binds candidate scope and execution-map identity but contains
no review or artifact references. Strict review requires the existing approved
source/coverage/execution scope chain and the scope review's exact
`admission_scope_sha256`. The synthetic review-binding unit controls supply no
real approval. Actual candidate reviews remain null, wheels absent and execution
rows unqualified. The full immutable artifact subject, admission of producers,
original installed/absence/control joins, attempt index, authoritative CI policy,
promotion basis/envelope and terminal retention join remain H4/H5 work.

Read-only commands from the workspace root:

```powershell
python -B tools/compatibility_qualification.py
python -B tools/compatibility_qualification.py --require-reviewed
```

The first reports a valid incomplete selection with admitted/qualified/full
inventory false and an explicit missing-proof list. The second currently exits
one because bound source/scope review is pending. Output/request options are
rejected without explicit `--materialize`. Materialization requires a separate
root-relative JSON request-array input and a new root-relative output path;
existing files and paths outside the workspace are rejected before writing.
It validates the generated declaration before creating the output.

The source packet changes only selection tooling/schema/tests, the CPU check
list, documentation and affected declaration hashes. Product source stays
`6345ceef42df1a64a7401a83c2d1a30384903cd1`; the frozen baseline stays
`875c1be945f27398577ef140450b6998fe22713836a9defea2ec57b24fae538d`.
All 142 original parents remain required, with no discharge. No native wheel,
SDK, environment, source snapshot or writable managed scratch is created.
Existing pytest environments disable incidental bytecode/plugin/cache output;
there are no new build assets to clean.

Verification: 25 focused CPU checks pass on Windows (35.19 seconds) and WSL
Linux (704.82 seconds), with exit zero and the actual child waited in each case.
These include synthetic dependency/review controls, resealed real-selection
controls, read-only CLI checks and four existing current-declaration contracts.
Strict real review remains exit one as expected. Fifty-one local documentation
links/anchors resolve. Small local source/result/license references are retained
in `build/runs/admission-selection-34/source-checks.json`; no managed scratch
was allocated, so no cleanup deletion was necessary.
