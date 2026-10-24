# Additive execution ledger

`tools/compatibility_execution.py` materializes and validates the selected
candidate's concrete execution rows without changing its frozen baseline.
`compat/vispy-execution.schema.json` defines the closed mapping declaration.
The default command is read-only:

```text
python -B tools/compatibility_execution.py
python -B tools/compatibility_execution.py --require-reviewed
```

The current draft lives beside the preparation as `execution.json` and
`execution-ledger.json`. It contains 30 selected required pairs and 120 criterion
bindings. All 142 original required parents, original applicability, profiles,
historical rows and receipts remain unchanged. The existing v2 inventory schema
validates the derived ledger; the preparation/coverage validators continue to
read their original baseline. Pointing preparation back at the derived ledger
is not a migration and is rejected.

Every new feature preserves the selected public methods, upstream sources,
requirements, finite expected behavior and excluded residual scope. Every
criterion maps to one stable concrete feature/profile/criterion and its exact
composite workflow. Mutation, failure and recovery fixtures remain conjunctive;
v2's mutation fixture category aggregates their expectations without erasing
their distinct mapping IDs. Several required workflows cannot silently collapse
to one receipt: this materializer requires one actual composite per execution
row, or an explicitly reviewed split in a subsequent declaration.

The selected pairs are required, with their complete same-profile dependency
closure. The schema's other newly introduced cross-product combinations are
explicitly optional and unreviewed: this records unselected work, never a
nonapplicability conclusion or discharge of an original required obligation.
The current 157 features and 5 profiles therefore have 785 applicability records.
There are 188 rows: the original 158 and 30 new execution rows. These counts
describe metadata, not VisPy completeness or a completion percentage.

New profiles start unadmitted, and new rows start with no identity or receipt.
Source observations remain attached to the preparation rather than being
silently converted into positive evidence for a new row. Required applicability
is unreviewed until the real source/scope approvals are bound and applied.
Global review/full closure remain false; the derived ledger has 172 required
pairs including the 142 unchanged parents.

## Explicit generation

Materialization requires new paths and never overwrites an existing file:

```text
python -B tools/compatibility_execution.py --materialize --output-ledger <new-relative-ledger.json> --output-map <new-relative-execution.json>
```

The defaults select the current candidate/coverage. `--candidate`, `--coverage`
and `--root` can select an explicit frozen declaration in another workspace.
Both output paths must remain inside that workspace and differ from each other
and every immutable input. Generation/validation performs no imports of VisPy,
builds, installations, observation or qualification. Missing script branches or
incompatible workflow aggregation stop generation.

## Review and evidence identities

The map pins the candidate scope, exact coverage file, original baseline and the
execution ledger's semantic scope. That scope includes all original objects,
new feature/profile descriptions, applicability/dependencies, workflows and
fixtures. It excludes only selected-row operational proof fields, selected-pair
review flags and new-profile evidence-admission fields. A later artifact subject
must bind the complete actual ledger/report bytes, not just this projection.

The existing source/scope approvals are reused. The scope approval must bind
`candidate_scope_sha256`, `coverage_map_sha256` and this map's
`execution_map_sha256`. A valid older approval without the execution binding
cannot approve these rows. Candidate scope excludes approval references, and
the execution scope excludes only application of review/evidence state, avoiding
a review/hash cycle without omitting behavioral scope. Validators check content
binding; they do not establish the truth of reviewer independence.

After actual bound approvals exist, an explicit command applies only selected
applicability review flags:

```text
python -B tools/compatibility_execution.py --apply-reviewed --require-reviewed
```

Missing/wrong approvals fail before writing. Neither this operation nor any
synthetic unit approval makes a profile admitted or a row qualified. Positive
rows still require the existing inventory's actual source/product/profile,
functional, installed-member and original absence/control checks. This tool
always reports `installable: false`, `qualified: false`, zero original discharge
and incomplete full inventory.

The existing evidence normalizer can consume the new concrete rows with
`--ledger compat/candidates/tk-state-resource-1/execution-ledger.json` and the
corresponding feature/profile. Its raw-report requirements are unchanged. The
pending worker-bound branch-result contract and exact-artifact index must still
join every required selected criterion and dependency before scoped admission.

Source controls cover preserved parents/history, lost/optionalized dependencies,
narrowed selected scope, omitted/duplicate/wrong criterion destinations, profile
and workflow substitutions, unauthorized review/admission flags, unproved
positive rows, stale approvals, read-only defaults and output overwrite refusal.
Current real reviews remain null. No original host, scissor, platform or full
parity obligation is retired by this preparation.

## Functional branch assignments

The [observed-child result contract](functional-results.md) adds the closed
optional `functional_result` mapping field. Known Tk mappings require its exact
contract/version and branch IDs; unknown or substituted assignments cannot pass
by resealing. The existing scope approval binds the complete execution-map digest.
Actual worker results and original gate receipts are still required for admission.
