# Compatibility workflow inventory

`compat/vispy-compatibility.json` is the selected G0 feature/profile ledger.
Its versioned shape is `compat/vispy-compatibility.schema.json` (ledger v2); the validator
is `tools/compatibility_inventory.py`. It imports no VisPy, toolkit or native
module. Run it with an existing Python environment:

```text
python -B tools/compatibility_inventory.py
python -B tools/compatibility_inventory.py --require-complete
```

The first command checks structure, pins, references and any claimed evidence.
`VALID_INCOMPLETE` is a structurally valid draft, not a functional pass or a
qualification. The second command fails until the inventory has been reviewed
and every required feature/profile has matching qualification. CPU CI checks
structural integrity and negative controls; it does not require a false complete
inventory while implementation is ongoing.

The initial seed contains 142 entries derived without imports from hash-verified
VisPy 0.17.0 exports and backend registration. It expands gloo wrapper exports and
merges duplicate public entry points while retaining their source pins. Every
row starts `not-inventoried`, profile `unassigned`, with no positive receipt.
This does not erase previously recorded host evidence; the host matrix and
reference inventories are linked by hashes and keep their separate scopes.

The seed is deliberately unreviewed. G0 still needs method-level contracts,
wildcard scene aliases, examples/events, shader-specific consumers, host workflow
mapping and concrete required platform profiles. Broad source-file availability
is not evidence of supported rendering. The row count is not a coverage
denominator or percentage. Do not flip `reviewed` until that reconciliation is
complete and reviewed.

## Editing and generating

Update the existing ledger as requirements and real fixtures are reviewed. Each
feature has its pinned source member(s), public entry point, requirements,
capabilities, scope rationale, ordinary and mutation acceptance and owner.
Applicability and dependencies are declared per feature/profile pair. Each
feature/profile row carries state, latest outcome, exact fixture
node IDs/case counts, current identity/receipt, blocker and next action. Pending
fixtures remain empty explicitly; positive rows must name both ordinary and
mutation coverage. A failed new attempt clears a current positive claim; retain
its prior receipt as historical evidence outside scratch and link it in the
packet report. No failed result may be hidden by retaining a stale green row.

The bootstrap generator is for a new reviewed source baseline, not everyday
updates; it refuses to overwrite an existing ledger:

```text
python -B tools/generate_compatibility_catalog.py --source <existing-pinned-vispy-package> --output <new-source-ledger.json>
```

It reads existing preferred source and verifies each consumed member against
`compat/upstream_manifest.json`. No clone or source snapshot is needed. Selecting
a different inventory scope requires explicit rationale; removing a required
entry is not an implementation fix.

## Required applicability and migration

Ledger v2 has an `applicability` entry for every declared feature/profile pair.
Each entry names `feature`, `profile`, `status` (`required`, `optional` or
`not-applicable`), a nonblank `rationale`, an explicit `reviewed` boolean and
same-profile feature `dependencies`. Adding a feature or profile without all
its applicability decisions fails validation. Duplicate/dangling pairs, cycles,
dependencies on nonapplicable pairs and required dependencies marked optional
also fail. Dependency direction may differ between profiles.

Only required pairs determine incomplete-row counts. A required pair without a
row, with a failure, or without qualified same-identity evidence stays incomplete.
Optional pending/failed experiments do not block closure, but any positive
optional claim must still pass every receipt check. Nonapplicable pairs cannot
carry workflow rows or dependencies; preserve observed failures/blockers as
applicable work. Missing hardware is a `blocked-external` row for a required
applicable pair, never a rationale to silently exclude that pair. Nonapplicability
is a reviewed scope decision, not a successful implementation outcome.

A fully reviewed inventory requires every applicability decision to be reviewed.
The validator cannot infer whether a human's scope rationale is true; review must
check changes against the existing required contracts. The current seed preserves
all 142 originally required pairs and remains unreviewed and incomplete. No
feature/profile was excluded or promoted during migration.

For another retained v1 ledger, use the explicit non-overwriting migration:

```text
python -B tools/migrate_compatibility_inventory.py --input <v1-ledger.json> --output <new-v2-ledger.json>
```

It preserves every workflow row/receipt and legacy required feature/profile pair,
copies dependencies to each profile and marks other legacy pairs optional.
It never infers nonapplicability. It resets both overall and pair-level review,
validates the new ledger and refuses to overwrite an existing output. Required
dependencies previously marked optional need explicit scope reconciliation;
migration fails rather than silently broadening or dropping those requirements.
The validator rejects v1 directly rather than guessing its scope. Bootstrap
generation uses the same mapping and continues to refuse existing output paths.

## Evidence receipt contract

Positive states require a hash-bound JSON receipt with `schema: 1`, feature and
profile IDs, requirement IDs, `phase` equal to the state, actual integer
`exit_code: 0`, `child_waited: true` and exactly matching `identity`:

```json
{
  "source_commit": "<40 lowercase hex digits>",
  "patch_sha256": "<64 lowercase hex digits; hash of exact dirty patch or empty bytes>",
  "profile_sha256": "<64 lowercase hex digits; pinned environment/profile>",
  "wheel_sha256": "<64 lowercase hex digits, or null for source-only evidence>"
}
```

The receipt's `pytest` field is a `{path, sha256}` reference to the original
`qualification_gate.py pytest` output. Selected fixture counts must match its
collection, with successful setup/call/teardown and no failed/skipped reports.
The observation file is never replaced by a handwritten passing test list.
Profile identity must match the ledger's concrete environment pin. Dependency
features must meet the same phase for the same profile and exact identity.

Installed states additionally require `installed_origin_verified: true` and a
`distribution_audit` hash reference to a normalized audit record with
`status: PASS` and the exact identity. Qualified receipts require `gates` with
three hash references named `dependency-closure`, `startup-transient-loads` and
`execution-api`. Each normalized gate record has its matching `gate`, exact
identity, `status: PASS` and `controls_passed: true`.

Those records are integration summaries produced only after the existing full
member auditor and observer/control protocols succeed. They do not replace,
reimplement or relax those verifiers. The adapter and validator now bind the
original reports to the actual workflow as described below. The seed still
admits no installed or qualified claims. Evidence integrity does not establish
whether an arbitrary author honestly performed a claimed experiment; retain
the originals and review the scenario's assertions and coverage.

## Workflow-bound qualification

A qualified row must have a `workflow` mapping with `id`, `scenario` (`script`,
`headless` or `qt`), `binding`, `script` and `arguments`. Script scenarios name a
local `{path, sha256}` reference; builtins require `script: null` and no ignored
script arguments. Qt requires an explicit binding. Pending/source/wheel-tested
rows may omit this additive v2 field; qualified claims cannot.

The existing observer accepts `--workflow-id <id>` and repeated
`--covered-feature <feature-id>` options. Controller and worker independently
record the scenario, script hash, binding and actual argument list. A script
changing during execution fails. Only the initial CLI boundary is consumed;
literal `--` and empty arguments inside the script's argument list are preserved.
Feature declarations require review against the script; they do not automatically
establish broad API coverage or satisfy unrelated inventory rows.

Use the original discovery → installed inventory → fresh receipt-bound replay
protocol, with matching workflow metadata on both runs. Prepare a JSON bundle
with these hash references: `runtime`, `worker`, `dependencies`, `inventory`,
`discovery`, `discovery_worker` and `controls`. Its `control_reports` member maps
every independent control case name to its own hash reference. Keep reports
outside scratch from the start, or retain their exact bytes and use portable
references; normalization checks hash edges rather than rewriting original paths.

```text
python -B tools/compatibility_evidence.py --ledger <ledger.json> --feature <feature-id> --profile <profile-id> --raw-reports <bundle.json> --output <new-index.json>
```

This writes three separate gate records plus an index of their file references,
refusing existing outputs. It checks original member-audit results, worker
completion/shutdown, same-wheel/environment/interpreter identity, observer
coverage and independent controls. Collector implementation/native-tool identity
and control report hashes must agree. The dependency receipt must bind the
discovery flow; the fresh replay must bind that exact receipt. Source/import-only
reports and unverified/failed replay gates cannot qualify a workflow.

Put the resulting gate references into the feature receipt. The inventory
validator recomputes normalization from the raw bundle; a handwritten green
label or same-wheel headless report cannot replace an observed Tk script.
Legacy gate summaries without this binding remain historical and cannot promote
new qualified rows. The separate full distribution audit and functional pytest
receipt are still required. `PASS_NORMALIZED` is not full inventory completion.

`tools/tkinter_state_scenario.py` supplies a bounded real Tk/state flow for the
script observer: two displayed targets, embedded input/host binding, both actual
flush routes before synchronization, independent color expectations, finish
without presentation and host-root survival. Source checks pass with retained
Windows/WSL native candidates. It is not the complete Tk/state acceptance matrix
and has not yet qualified a final installed wheel.

Follow [build hygiene](build-hygiene.md) for experiments. Keep durable receipts
outside scratch and reference stable artifacts by hash. A new validator/schema
or inventory edit requires CPU checks, not a native wheel or environment clone.


## Recorded Tk/state source observations

The canonical ledger now appends two **optional development profiles**:
`source-windows-vulkan-tk86-cp312` and
`source-wsl-software-vulkan-tk86-cp312`. They record selected observed behavior,
not final required-platform applicability or shipping admission. All 142 original
required feature/unassigned pairs, their unresolved rows and source-export pins
remain unchanged. No required work became optional or nonapplicable; the new
optional pairs belong only to these additional development profiles. The full
inventory remains unreviewed and `--require-complete` still fails with 142
incomplete required rows.

Each profile has source-tested observations for Application, the Tk backend,
Canvas, Timer, GLContext, Program, Texture2D and the selected GL-shaped query
route. Row fixture node IDs, parameter counts and independent expected outcomes
name the actual ordinary/mutation subset. Profile-local dependencies bind those
observations to the same recorded runtime source and profile. A composite
sharing fixture proves both initial output and later updates; using it in two
acceptance roles does not count it as two executed cases.

Original reports and receipts live under
[`compat/receipts/tk-state-source-17`](../compat/receipts/tk-state-source-17/README.md).
The 14 selected fixture functions collect 37 cases on each platform. The raw
qualification reports include successful setup/call/teardown, and each original
observation contains interpreter/base executable hashes, dependency lock hash,
native contract/manifest identity, toolkit identity, source-member hashes,
adapter/software status and all nine zero native shutdown gauges. The WSL
observation also retains loaded-library identities. These are observed-source
profiles, not complete installed dependency-closure audits.

`environment_sha256` pins that profile's exact observation JSON. The optional
source receipt `observation` file reference must have that same hash, a matching
profile ID, successful exit/status and complete zero shutdown gauges. The
validator rejects failed, borrowed, mismatched or incomplete observations. That
field is source-only and cannot back an installed claim. Existing synthetic or
legacy receipts without that field retain their existing validation contract;
installed/qualified rows still require every original wheel/member/observer gate.

Runtime source identity remains the exact product commit exercised by these
observations; the later inventory metadata commit does not relabel it. Native
binaries and their producer manifests are reused unchanged. All source rows
retain blockers for broader method/enum/format coverage, required-profile
reconciliation, independent implementation review and exact installed gates.
The Linux toolkit/scissor failures, mandatory threedee row and Tcl shutdown
attribution remain open. No feature-completeness percentage follows.

The bootstrap generator still refuses overwrite. Its regression now verifies
that every original feature, profile, required pair and seed row survives
curation, rather than requiring the evolving canonical ledger to remain forever
byte-for-byte equal to a generated seed. Synthetic promotion controls explicitly
isolate their single test profile and cannot accidentally inherit these real
observations.


## Conserved obligation transfers (v3 tooling)

The validator also reads `compat/vispy-compatibility-v3.schema.json`. The
canonical inventory remains v2, with its 142 original required obligations and
optional development observations unchanged. v3 tooling is source-tested; no
concrete required-profile transfer or installed qualification is claimed.

A v3 ledger adds `conservation.baseline`, a path/SHA-256 reference to a frozen,
valid v2 ledger, and `conservation.transfers`. The baseline stays inside the
selected source root, outside managed scratch. Retain it once by hash. Prepare
a separate output explicitly; the migration refuses to overwrite an existing
file and resets global review without changing feature, row or receipt bytes:

```text
python -B tools/compatibility_conservation.py --input compat/history/<frozen-v2-ledger>.json --output compat/<new-v3-ledger>.json
python -B tools/compatibility_inventory.py --ledger compat/<new-v3-ledger>.json
```

The baseline must remain available with its original referenced evidence. An
input at the current mutable ledger path is not a durable frozen history copy.
The command validates the result before writing; merely migrating leaves all
required work incomplete. A v1 ledger still uses the existing explicit v1-to-v2
migration first. Evidence receipts retain their existing format and gates.

Each transfer contains an `origin` feature/profile pair; `origin_sha256` over
its baseline feature, profile, applicability and row; a rationale; complete
criterion coverage; and a hash-pinned scope review. `digest()` in
`tools/compatibility_conservation.py` defines object identity: SHA-256 over UTF-8
JSON with sorted keys, compact separators and ASCII escapes. The criterion set
is `scope`, `ordinary`, `mutation`, plus `requirement:<id>`, `capability:<name>`
and `dependency:<feature>` for every corresponding baseline item.

Each criterion names required successor pairs and a rationale explaining full
coverage. All successors need reviewed applicability, a concrete admitted/pinned
profile and a workflow row. Their evidence may still be pending, which prevents
completion. Original dependency names must remain required in each successor's
profile. Covered requirements/capabilities and original upstream sources cannot
be omitted. This conservative first mechanism permits no scope exclusions.
An authorized exclusion needs its own future reviewed contract.

The scope-review JSON contains `schema: 1`, `status: "APPROVED_SCOPE"`, a named
`reviewer`, `baseline_sha256` and `transfer_sha256`. The latter hashes the exact
transfer object excluding its `review` reference. This binds the review to its
scope declaration; it does not authenticate a reviewer or prove the truth of a
behavioral coverage rationale. Independent review must inspect those semantics,
including every split method/value/event restriction. A narrow smoke cannot
justify full-scope approval, and a scope approval is not source-code approval or
artifact promotion.

Original required pairs/features/profiles remain present. Transferred historical
rows remain byte-equivalent JSON objects, preserving their original failures or
receipts. Chains must be acyclic. Only reviewed, fully mapped parent obligations
are removed from the *terminal* completion count; required terminal successors
still need all ordinary functional/identity/observer gates and qualified status.
`required_pairs` counts retained physical pairs, while v3 additionally reports
`original_required_pairs` and `transferred_required_pairs`; neither count is a
feature-completeness percentage. A transferred parent cannot double-count as a
second completed workflow. Optional failures remain recorded and optional.

The current CPU controls exercise missing/changed origins, partial coverage,
optional replacement, missing dependencies, duplicate criteria/dispositions,
cycles, stale scope approvals and relabelled evidence, plus migration overwrite
refusal and synthetic terminal qualification through all existing gates. Real
profile mappings, scope review, cumulative implementation review, a candidate
manifest and installed G2 work remain pending.
