# Compatibility workflow inventory

`compat/vispy-compatibility.json` is the selected G0 feature/profile ledger.
Its versioned shape is `compat/vispy-compatibility.schema.json`; the validator
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
capabilities/dependencies, scope rationale, ordinary and mutation acceptance and
owner. Each feature/profile row carries state, latest outcome, exact fixture
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
reimplement or relax those verifiers. Retain their raw inputs/outputs and tool
identity in the packet report. Adapters from current auditor/observer outputs to
this normalized receipt format remain pending; the seed admits no installed or
qualified claims. The validator checks identity and evidence integrity, not
whether an arbitrary author actually performed a claimed experiment.

Follow [build hygiene](build-hygiene.md) for experiments. Keep durable receipts
outside scratch and reference stable artifacts by hash. A new validator/schema
or inventory edit requires CPU checks, not a native wheel or environment clone.
