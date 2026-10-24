# Astra max review: workflow and implementation contracts

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Reviewed the canonical compatibility plan/specification,
earlier reviews, compatibility status and relevant ledger/backend source.
Publication source baseline: `e6709ee60a3e0123f24f247cad9eef03e4cb585b`.
The reviewer also considered the coordinator's new section 11 during this pass.
Review was read-only: no builds, installations, tests or scratch allocation.

Disposition: **accept all four refinements**. They are incorporated into the
plan and specification. Requirements added here do not imply implementation,
artifact qualification or closure of earlier findings.

| ID / priority | Finding and reviewed reference | Adopted disposition |
| --- | --- | --- |
| B1 / P1 | Qualified gate normalization checks gate/status/controls/identity, not the observed workflow (`tools/compatibility_inventory.py:217–223`). Same-wheel headless evidence could accompany separately tested Tk functionality. | Section 11 requires hash-bound scenario/script, arguments, covered workflow IDs, observer/control identity and raw reports. Add adapter/validator coverage checks and unrelated-workflow negative controls. Use the existing script scenario and discovery/inventory/fresh replay protocol, not another auditor. **Implementation pending.** |
| B2 / P1 | Feature-wide `required` and global `required_profiles` form a Cartesian requirement; existing optional-profile rows can also block closure (`tools/compatibility_inventory.py:232–239`). | Require reviewed required/applicable feature-profile pairs and nonapplicability rationale. Preserve required scope; absent hardware remains blocked required work. Migrate the ledger/validator and test missing required pairs, optional rows and hardware exclusions. **Implementation pending.** |
| B3 / P2 | G4a's whole-G2 prerequisite couples independent shader work to unrelated Linux Tk failures. | Plan G4a and section 11 permit bounded feasibility/source work from a hash-known baseline once actual prerequisites hold. Affected-profile G2 and dependent-workflow requalification remain mandatory before promotion. **Planning correction applied.** |
| B4 / P2 | Advertised backend capabilities and constructor configuration are insufficiently qualified by standalone/embedded mode (`_dawn_tk.py:23–25,363–387,521–563`). | Require a mode-specific capability/options table, requested/granted attachments, UI-thread policy and observable behavior or contextual refusal. Sharing requires two consumers, update visibility, independent closure and retirement. **Acceptance/implementation assessment pending; no new runtime failure demonstrated.** |

Line references describe the reviewed source and may move. Backend paths are
relative to `src/vispy/app/backends/`.

The reviewer accepted section 11's input sequences, operation/query records,
shader decision records and change-impact/evidence-reuse rules as addressing
the other requested detail. No additional shader blocker was established.
The coordinator also removed stale prose describing source-fixed flush/finish
behavior as still unimplemented; exact installed qualification remains open.

The revised [execution plan](../plans/2026-10-24-vispy-compatibility-gaps.md)
and [specification](../specs/2026-10-24-vispy-compatibility-gap-closure.md)
retain broad scope and the mandatory threedee row. WSL software evidence does
not qualify native Linux GPU; Metal remains experimental without Mac hardware.
Optical display parity stays deferred. No runtime edits or new artifacts were
needed for this documentation review.

## Implementation follow-up: B2 applicability

A later source packet implements ledger v2, explicit pair status/rationale/review
and per-profile dependencies, plus a non-overwriting v1 migration. All 142 seed
pairs stay required and unreviewed; rows and receipt identities are preserved.
The optional-profile regression fails before the fix and the final 68 CPU cases
pass. Controls cover absent required rows, hardware blockers, optional work,
nonapplicability, pair completeness, local dependency cycles and migration.
This is coordinator-recorded source evidence, not an independent implementation
re-review, reviewed inventory or artifact qualification. B1 remains open.

## Implementation follow-up: B1 workflow evidence

A later source packet adds reviewed row workflow mappings, independently
recorded controller/worker scenario hashes and arguments, covered feature IDs,
collector identity and control report hashes. The adapter consumes original
discovery/inventory/dependency/replay/control reports; the ledger validator
recomputes normalized gates and rejects the original unrelated-headless regression.
A bounded real Tk/state script is available through the existing script scenario.
Selected protocol suites pass 141 Windows and 141 Linux cases, with the existing
symlink-venv case explicitly deselected. The new functional script passes on both
retained native candidates with nine zero shutdown gauges. No new installed wheel
or actual native control run was qualified. Independent implementation review,
complete workflow mapping and G2 artifact gates remain required; this is a
coordinator source checkpoint rather than an independent closure of B1.
