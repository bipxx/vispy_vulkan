# Astra max review: qualification-index plan and specification

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Read-only review of the active gap-closure plan, spec,
previous executable-handoff review, execution-ledger/functional-result records
and relevant existing validators. Starting publication checkpoint: `ac74c6ae38149e5445bc20c9b204e1630b49f696`.
The coordinator added section 16 while the review was in progress and adopted
the following findings. This record is planning review, not cumulative code,
fixture, semantic scope, producer or artifact approval.

| Finding | Evidence and risk | Adopted requirement and control |
| --- | --- | --- |
| P1 - final review/CI binding | Spec section 15 separates immutable subject from CI envelope, but subject-only review does not prove the reviewer considered a changed head/CI decision. | Section 16 defines an immutable promotion-basis digest over subject, repository/head, exact CI policy/receipt bundle and change-impact decision. Final review binds that basis. Keep subject S and valid review at head A, substitute passing head B and reseal: reject until renewed final review. |
| P1 - admission granularity | `tools/compatibility_execution.py` materializes one workflow/fixture set per row; `tools/compatibility_inventory.py` validates complete row proof and same-profile dependencies. Criterion-only admission could bypass that model. | Version 1 expands any requested criterion into the whole execution row/all four criteria, recursively through dependency rows. Preserve requested keys separately. Partial admission needs a reviewed row split. Reject ordinary-only admission, omitted dependency recovery and partly proved qualified rows; full composite branches remain mandatory. |
| P2 - attempt selection | Section 10 already requires later relevant failed attempts to stay visible, but selected report hashes alone do not enforce which attempts were considered. | Bind a closed attempt index with failures/cancellations, actual exits/waits, reproducers and explicit resolution/supersession; specify authoritative CI rerun selection. Reject older complete pass plus omitted newer relevant failure, even with resealed metadata. Preserve prior failures when a reviewed resolution produces a new subject. |

The reviewer confirms that H0 is complete and H1/H3 have source implementations.
H2 independent cumulative implementation/scope review, H4 exact-artifact index
and H5 promotion remain open. Earlier execution-ledger and worker-result findings
are resolved at source-design level and are not reissued as missing implementation.

The coordinator also expanded section 16 with owned outputs, read-only boundaries,
closed reference/schema rules, an acyclic selection/subject/basis/envelope graph,
exact wheel/member/source/producer joins, required CI policy, terminal retention,
explicit scoped status and resealed semantic controls. The plan now sequences
H4a-H4d and preserves all 142 original required obligations, mandatory hosts,
Windows/WSL distinctions and experimental Metal status. These are requirements
for future implementation, not a claim that an index already enforces them.

Verification: candidate, strict script-readiness coverage and execution-map
validators pass with 30 selected pairs, 120 bindings, 142 original parents and
zero discharge. Four existing current-declaration CPU contracts and 51 local documentation links/anchors pass. Real source/
scope approvals and wheels remain absent; strict review/admission gates remain
pending. No native build, package installation, source snapshot, environment or
managed scratch was created. There is no new build asset requiring cleanup.
