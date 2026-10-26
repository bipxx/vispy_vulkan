# Astra max review: next implementation packets

Date: 2026-10-24. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Read-only continuation of the earlier Astra detail
review, against publication source baseline
`1c189975a42241a2366f9ff3c7ba5791df8b432c` and the canonical plan/specification.
The reviewer also checked the coordinator's new specification section 12.
No builds, installations, native tests or scratch allocation were performed.

Disposition: accept all three refinements below. They identify design/acceptance
ambiguities; this review demonstrates no new runtime defect and does not close
an implementation or qualification finding.

| ID / priority | Finding | Adopted disposition |
| --- | --- | --- |
| C1 / P1 | A native state-query snapshot could accidentally report effective pipeline or last-draw state. `cpp/runtime_state.hpp` rewrites MIN/MAX factors, gates effective depth writes by depth testing, and adapts front/back stencil for converted draws. Those descriptors need not equal accepted logical API state. | Section 12 requires committed canvas RenderState before lowering, including disabled-feature values and newly committed values before a draw. Add paired cases for depth mask with depth disabled, nondefault factors under MIN/MAX, and distinct front/back stencil. Actual attachments remain the authority for target/configuration queries. **Design clarified; implementation and fixtures pending.** |
| C2 / P2 | The plan required independent implementation review before artifacts existed, while specification section 11 required the same review to inspect final artifact receipts. | Make two checkpoints explicit: source/fixture review before packaging, then promotion-evidence review after exact installed-wheel, auditor, observer/control and required CI receipts exist. Both must pass; neither this plan review nor one checkpoint substitutes for the other. **Planning inconsistency corrected.** |
| C3 / P2 | The old-module guard explicitly precedes queue draining, but malformed/unsupported selector validation needed the same explicit boundary. A valid query failing in earlier queued execution is a different case. | Section 12 requires type and admitted-selector membership checks before draining; invalid/unsupported selectors preserve pending state and draw commands. A valid selector propagates a queued execution failure with its committed prefix recorded. Add separate controls for both paths. **Acceptance clarified; implementation/fixtures pending.** |

The expanded specification adds bounded query authority/version/order/type and
rectangle-scope decisions; counterexamples for remaining legal state gaps; and
concrete G0/backend capability outputs. The plan identifies Q1, I1, B4, legal
state packets and G2 outputs and exit conditions, without restarting source-fixed
input/submission work or treating ownership labels as new-agent instructions.

The mutable-state query packet is otherwise materially specified for the next
implementation. Selector details, signed-mask conversion and default rectangle
semantics still need the explicit pre-implementation decisions required there.
A smaller proven subset cannot qualify a broader required feature/profile row.
The complete inventory, legal setter gaps, Linux blockers, mandatory threedee
row and exact artifact gates remain open. Metal remains experimental without a
Mac; WSL software results do not qualify native Linux GPU. Optical display parity
remains deferred.

Validation for this documentation packet: local Markdown targets/anchors and
plan/spec consistency; scoped publication whitespace check. No build or package
assets were generated, so no managed scratch cleanup was necessary. Historical
reviews and meaningful failures are preserved. See the updated
[plan](../plans/2026-10-24-vispy-compatibility-gaps.md) and
[specification](../specs/2026-10-24-vispy-compatibility-gap-closure.md#12-next-packet-designs-and-exit-checks).


## Coordinator follow-up: Q1 source evidence

A later packet implements logical native query projection and the guarded Python
route. Thirty-seven native query cases cover C1's disabled-state/MIN/MAX/front-back
vectors and C3's actual pending-work preservation versus native committed-prefix
failure. Final affected regressions pass 323 Windows and 309 WSL software cases,
with nine zero shutdown gauges per profile; CPU/protocol and C++ contracts pass.
This is coordinator-recorded source evidence. It is not an independent re-review
or closure of C1/C3 at the artifact gate. C2's two implementation-review checkpoints
remain required; this plan review cannot fulfill either.
