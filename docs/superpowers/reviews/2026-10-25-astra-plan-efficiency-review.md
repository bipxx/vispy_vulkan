# Astra max review: execution efficiency and API routes

Date: 2026-10-25. Reviewer: `gpt-6-astra`, reasoning effort `max`, explicitly
requested by the user. Read-only planning review of the active compatibility
plan/spec, candidate/coverage/inventory and relevant qualification/native tooling.
Published input baseline: `997434d54b61e0afe5d066ef654542e57d4741ed`.
Canonical native-provenance source remains unfinalized local WIP. This review
provides no H2 implementation, fixture, scope, producer or artifact approval.

The coordinator accepts the following six findings. The active efficiency
revision at the top of the [plan](../plans/2026-10-24-vispy-compatibility-gaps.md)
and the [per-API routes](../../api-implementation-routes.md) record their execution
changes. Normative artifact/behavior gates and full parity scope remain intact.

| Priority / finding | Inspected mechanism and inefficiency | Adopted plan change |
| --- | --- | --- |
| P1 - native identity couples unrelated inputs | `tools/compatibility_candidate.py::scope_digest` includes preparation/spec/workflow/profile data. `tools/qualification_native.py` embeds it in a reviewed recipe and raw result, so a proof/docs change can invalidate unchanged native production. Test harness files also join production identity too broadly. This is a requalification cascade, not a literal hash cycle. | Native identity derives from actual native sources/dependencies/configuration/toolchain/ABI/outputs. Keep original test identities distinct; bind candidate scope through a separate reviewed impact/reuse link. Changed observers/scope still renew their own evidence/review. Fix this before adopting native WIP. |
| P1 - historical producer protocol rejected by new wrapper | Native WIP synthesizes exact five-phase/new target commands, while original `tools/native_epoch.py::build` used an additional MSBuild argument. A valid original record cannot truthfully pretend to have used the new command. | Add retained-original and new-build routes. Validate original immutable evidence under its frozen authority plus exact relevant source/output/ABI/config match; use a new managed build only for changed inputs or genuinely missing original proof. Never fabricate commands/PIDs/waits or weaken a verifier. |
| P1 - incomplete proof packets displace actual qualification | Source-complete helper checkpoints accumulate while source/scope reviews remain null and installed evidence absent. | Finish remaining H4 joins as one end-to-end integration, starting with a complete synthetic subject and real incomplete index. Freeze inputs and obtain actual cumulative H2 review, then fix findings and execute installed qualification. Another plan review does not substitute. |
| P2 - criterion count confused with workload count | All 120 current profile bindings target `tk-state-resource-failures`, containing 60 criteria on each of two profiles. | Run one full existing observer protocol per exact wheel/profile/composite identity and share its actual reviewed branch evidence. Preserve discovery/replay, all eight branches, three absence gates, independent controls and shutdown. Helper scripts need separate observation only for extra scope/controls. |
| P1 - real blockers outside the critical path | Generic H4 completion does not admit experimental Linux production, repair MSAA scissor or resolve Windows threedee. | Make producer decisions before packaging; run bounded causal diagnostics alongside integration/review. Both selected profiles remain required. A Windows-only milestone requires explicit reviewed selection with WSL failures/obligations retained. |
| P2 - repeated normative/status/CI churn | Repeated specification expansion and micro-pushes change pinned input sets and cancel expensive CI; repeated native tests do not necessarily add proof. | Keep routine status/routes in plan/appendix; freeze normative inputs before expensive runs. Batch coherent edits and use affected source checks during development, complete required 23-job CI for the final declared head, and renew affected reviews when inputs actually change. No old-head green transfer. |

The resulting sequence is: preserve scope/failures and decide native reuse;
complete integrated H4; freeze and obtain actual implementation/scope review;
resolve applicable platform blockers; reuse or build each necessary native leaf
once; package and run exact installed composite protocols; retain/clean actual
attempts; bind current-head CI and final promotion review. Continue full API/
method/value/example/event inventory and legal-state/shader/backend/host/hardware
work using that same qualification machinery.

For the current 15 candidate keys, the reviewer recommends existing implementations
and the shared composite first: raster/manual/canvas/current-context; shared
program/buffer/texture ownership; one public Timer transition and failure; explicit
recovery; raw/gloo immediate/delayed submission capacity/retry; independent RGBA
readback and final deletion/retirement. No shader extension is needed merely to
qualify the existing vec2 plus sampler2D triangle subset. Broader operations keep
their residual parent obligations and all four criterion/dependency requirements.

For the 142 canonical keys, the coordinator's route appendix proposes a first
reuse mechanism and decisive vector per key. Python geometry/layout/camera/math
stays in Python where already valid; composed visuals reuse mesh/line/point/
texture/program paths. New raw operations use existing native ownership/GLIR
mechanisms. Backend adapters need real no-GL display/input workflows; legacy
native-context semantics cannot be silently relabelled headless. Named geometry
consumers precede any universal translator. Independent state/shader packets
follow real dependency links, rather than an arbitrary serial chain.

Validation is documentation-only: exact unique coverage of 142 canonical plus
15 selected feature keys, required review/plan links and Markdown local anchors
are checked against current files. No runtime/source/schema/verifier change,
package install, native build, environment, source snapshot or managed scratch
is performed for this review. Existing unfinalized native WIP and its declaration
hashes are left for its corrected implementation packet. No new build asset needs
cleanup; no historical evidence or protected origin is removed.
