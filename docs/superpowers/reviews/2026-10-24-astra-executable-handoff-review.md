# Astra max review: executable qualification handoff

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Read-only review of the current compatibility plan/spec,
candidate/coverage declarations, validators and relevant observer code. Publication
baseline: `c59b44f41b73c4f2b3a49677e4362a8748ba365a`; the canonical workspace also
contains unfinished `observed-submission-30` script/fixture changes. No builds,
installations, tests, scratch allocation or implementation edits by the reviewer.

The reviewer returned four findings. The coordinator accepts them and records
their documentation disposition below. This is a plan review, not cumulative
source/fixture approval, semantic scope approval or installed qualification. The
coordinator's new clauses are an adopted specification, not a second independent
implementation review.

| ID / priority | Finding and inspected references | Adopted requirement |
| --- | --- | --- |
| H1 / P1 | Directly adding proposal IDs to the pinned baseline breaks preparation/coverage invariants: `tools/compatibility_candidate.py:68,163`, `tools/compatibility_coverage.py:42`; normalization needs a concrete execution row (`tools/compatibility_evidence.py:145`). | Freeze the original preparation baseline. Materialize selected additive required rows in a separate derived execution ledger with explicit proposal/criterion mapping and preservation checks. Existing inventory/evidence validators consume that ledger. No original parent discharge or global review/closure claim. |
| H2 / P1 | Script hashes, fixture counts and free-text injection are insufficient functional-result joins. The script probe discards the `runpy` result (`tools/no_opengl/probe.py:80`); the controller binds its worker report, but no structured scenario result (`tools/audit_no_opengl.py:114`); coverage/normalization do not validate branch outcomes (`tools/compatibility_coverage.py:96`, `tools/compatibility_evidence.py:60`). | Specify a closed result transport captured in the same observed worker, with controller/normalizer hash edges. Require exact unique route/delay/order branch sets, actual error/counter/pixel/retry/cleanup records and semantic rejection controls. Preserve all original absence gates and controls. |
| H3 / P1 | Current-head CI, source identity and final approval have no explicit noncyclic subject/envelope contract in the earlier index design. | Distinguish product inputs, qualification implementation/head, reviewed scope, immutable evidence subject and detached promotion envelope. Bind review to subject digest and CI to the exact required head/job set. Never require a self-containing commit/hash; a later head still needs current CI. |
| H4 / P2 | Windows-first admission is permitted, but requested-set and aggregate-result behavior is underspecified while the preparation includes both profiles. | Freeze requested criterion/profile set and same-profile dependency closure before final execution. Report requested/proved/blocked/missing sets. A Windows scoped success leaves WSL, total candidate and original obligations incomplete; silently dropping failed selected work is rejected. |

References describe inspected code and can move. Repository paths are relative
to the canonical workspace.

The [specification section 15](../specs/2026-10-24-vispy-compatibility-gap-closure.md#15-executable-handoff-from-proposals-to-scoped-qualification)
defines the input freeze, derived-ledger route, exact branch families/result
transport, subject/review/CI joins, scoped status and negative controls. The
[plan's concrete next packets](../plans/2026-10-24-vispy-compatibility-gaps.md#concrete-next-packets-after-this-review)
assign H0-H5 outputs, prerequisites and stop conditions. These requirements
remain future implementation until their own source review and evidence exist.

Required rejection cases include altered/lost parents, omitted or duplicate
criterion destinations, invented origins, wrong profiles/dependencies, using the
derived ledger as the preparation baseline, absent/duplicated/substituted branch
results, changed counters or missing retry, wrong observed child, stale subject/
approval/CI, missing required jobs and promotion of scoped success into total
qualification. Recompute metadata seals in semantic controls so stale hashes
alone do not satisfy their purpose.

The recommended order is: finish and retain packet 30; update its exact
declarations without premature readiness; freeze review inputs; obtain cumulative
source and semantic scope review; materialize the additive ledger and implement
result/index contracts; collect installed evidence and detached promotion review.
Source-only schema/index development may proceed during review; admission cannot.

The reviewer found the following existing boundaries adequate: all 142 original
obligations/residuals and mandatory host rows remain required; preparation cannot
qualify a wheel; source/scope reviews are null; expected-error scripts must verify
recovery/cleanup before success; the new script contains all four submission
variants but their cross-profile execution is not certified by this review;
Windows/WSL and old/new toolkit identities remain separate; native Linux GPU is
unqualified, Metal experimental, and optical/scanout parity deferred.

Coordinator status correction: Windows packet-30 source checks record 18 passes,
but Linux/direct-script completion and terminal cleanup remain pending. Current
declarations still expose eight source-only bindings. The active queue now
distinguishes the blocked original Tk8.6 profile from selected Tk9 development;
section 14 names three workflows. Historical results retain their original scope.
No source, scope, artifact, host or hardware gate is closed by this review.

Coordinator verification after editing: candidate and coverage validation both
exit zero; 112 bindings remain script-ready and eight source-only. Both review
requirements, strict script readiness and full-inventory closure still exit one
with their expected pending-work reasons. Four existing current-declaration CPU
contracts pass without skips. All 46 local documentation links/anchors checked
in the edited Markdown resolve; existing line endings are preserved. No native
build, installation, environment or scratch was created. The open packet-30
scratch and its pending terminal cleanup are not part of this documentation pass.
