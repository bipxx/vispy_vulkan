# Remaining-gap investigation and closure plan

## Authoritative next actions — 2026-11-14

This queue supersedes all older next-action instructions below. Older dated
checkpoints remain evidence history, including failures; their pending labels
are not current blockers. The original planning revision ran no experiments;
subsequent execution updates below distinguish actual delivery from remaining work.

### Starting point and finish line

The selected 128-binding subject and eight mandatory profile rows were admitted
in [718](../../../compat/api-acceptance/parent-final-admission-v1.json).
Protected PR77 integration completed in [719](../../../compat/api-acceptance/parent-protected-integration-v1.json),
with the same tree as the 23-job tested PR tree. Do not repeat those gates for
unchanged inputs. Release target remains exact `55fd4e8`, runtime `2b8bccd`;
later records and two regression tests are a separate integration delta.

The current preview is public and delivery-verified by
[728](../../../compat/api-acceptance/preview-public-delivery-v1.json) after
[726publication](../../../compat/api-acceptance/preview-publication-v1.json).
Windows draft smoke
[724](../../../compat/api-acceptance/preview-draft-windows-channel-v1.json)
passes on wheel `9e4e30cc…`; Linux candidate is `a2715d26…`.
The next milestone is integration of the later owned records/tests. Broader parents close
only for explicitly selected capabilities or documented support boundaries;
full VisPy parity is not the finish line.

### Ordered closure checklist

Order3 source audit/collection progress, 2026-11-14:
[730](../../../compat/api-acceptance/post-preview-delta-audit-v1.json) verifies
the77-file owned snapshot,810unchanged source guards and702frozen committed
Git inputs; foreign index unchanged.8newtests collect locally, not CI/GPU
execution. Failed729namespace assumption is preserved; corrected730uses the
authoritative699committed map. No scratch/build/install. Next refresh/freeze
the explicit delta including this new receipt and docs, obtain independent
impact review, commit/push only owned files and require actual branch protection.
Any critical change invalidates the unchanged-input path. Do not claim this
collection at a future integration head until its exact file hashes are joined.

Order2 complete, 2026-11-14:726publishes exact reviewed prerelease/tag and two
separate index paths without changing stable release/index/latest.728verifies
both public wheel hashes via727closed-output receipts and all four public HTML
pages. Exact bytes join724Windows clear/725WSL ABI-only smokes.727buffered-file
hash checker failure stays retained; the corrected adapter changes no release
content. Actual children awaited;726–728scratch cleaned17,377,805bytes, scratch
absent. Proceed to order3; unchanged bytes need no new native build/install replay.

Order1 completed at finite draft-channel scope, 2026-11-14:
[725](../../../compat/api-acceptance/preview-draft-wsl-channel-v1.json)
passes actual Linux asset hash/size, 537 installed members, 23 notice inputs,
22 license texts and native ABI import, with zero source overlays. Guest and
backing-volume checks pass, existing dependencies reused, actual exits0/awaited.
Managed cleanup removes569files and verifies28retained inputs; scratch absent.
This does not add GPU or public-channel coverage. Proceed to order2, preserving
Windows724/Linux725 exact-byte smoke receipts and the unchanged stable channel.

| Order / tracking IDs | Investigation and easiest path | Done when |
|---|---|---|
| 1. FIX-06: Linux draft delivery | Reuse the qualified Linux wheel, existing WSL Python/dependencies and corrected 724 adapter. Check guest filesystem/backing-volume health, download the authenticated draft asset once, verify SHA256/size, install offline into one registered scratch target. | Exact 537 runtime members, 23 source notice inputs and 22 dist-info notice texts match; all imports originate in the target; native ABI imports successfully. Retain actual exits/waits and cleanup result. This channel smoke is ABI-only, not another GPU qualification. |
| 2. FIX-06: public preview | Reuse draft 721 and generated index 710. Recheck reviewed tag target and two asset hashes, publish the prerelease, then add only the two preview-index paths. Keep stable release assets and stable index bytes unchanged. | Public tag resolves to exact 55fd source; actual public wheel bytes match both qualified hashes; public index bytes/links match the reviewed files. Same-version installation instructions use a separate channel/direct hashes. Public bytes may reuse draft installed-smoke evidence only after exact hash equality. |
| 3. FIX-04/06, API-06: later WIP integration | Enumerate owned post-55fd changes: records/docs, camera-mutation test and color/alpha composition test. Compare runtime/native/build/lock/workflow/tool inputs explicitly; preserve foreign edits and frozen records. | An explicit delta/impact assessment supports evidence reuse, selected tests are actually collected at the new head, required branch protection passes and the owned delta merges normally. Do not label the new head 55fd or transfer its approval automatically. |
| 4. API-05/06, SCI-05/06, SHD-06, LIF-01–04: record audit | Join each open row to its newest exact evidence before selecting another experiment. Start with stale stencil, minimized-window, parent-destruction, clipping and admission wording. Reuse 664/665, 708 and 718 rather than replaying them. | Each selected row names the supported route/values, exact profile/artifact, evidence level and genuinely missing behavior. Close only matching finite items; retain historical upstream/driver failures. An evidence-only wording fix requires no native rebuild. |
| 5. LIF-06 / API-06: Qt input | First inspect delivered-event fixtures for keyboard, wheel, focus, mouse, timer and coordinate routing. Select one missing ordinary public interaction; do not expand to physical HID or gestures. | A focused toolkit-delivered event produces the expected payload/coordinate and response, with focus isolation, mutation/recovery where applicable, and teardown on Windows/WSL. Mock dispatch alone is labelled source-tested. |
| 6. SCI-03 / STA-01: camera and state | Preserve completed azimuth/center mutations. Audit remaining camera projection, clipping-plane and depth/stencil interactions; select one useful uncovered combination with an analytic or frozen oracle. | Before/change/restored pixels, state isolation and cleanup prove the named combination on both current installed profiles. Fresh-scene equivalence is labelled metamorphic rather than an independent upstream oracle. |
| 7. SCI-02: filter breadth | Compare implemented filter routes against the six completed color/alpha composition cases. Select one useful missing ordering or blending interaction, not a Cartesian product of every filter. | Deterministic expected pixels, queued before/change/restored revisions, detach/reattach and invalid-input recovery cover the selected composition. Unselected filters, blending and MSAA remain explicit boundaries. |
| 8. LIF-01–05: lifecycle and capture | Audit actual acquisition/fault/surface-loss evidence and MSAA depth/stencil cells. Choose one missing failure or format cell only after distinguishing it from completed minimize/reparent/close controls. | A real selected failure/capture case verifies recovery or explicit refusal, shared-peer behavior and resource retirement. Driver-specific outcomes stay pinned to their driver; no physical-GPU claim from WSL. |
| 9. SHD-01–05, TEX-01, LIN-01, SCI-01/04: rendering breadth | For each parent, map implemented forms, intentional refusals and existing rendered evidence. Prioritize a concrete application need; use supported forms before changing compiler/native code. | One named type/layout/index/LOD/line/volume case has a deterministic oracle, mutation, limit/refusal/recovery and exact installed scope, or its support boundary is documented without claiming implementation. Large-volume quality and performance remain separate claims. |

Orders 1–4 complete delivery and establish the trustworthy remaining feature
queue. Orders 5–9 are a proposed priority, not a requirement to implement every
variant. After each packet, select the next demonstrated user-visible gap from
the audit; skip a packet whose exact behavior already has adequate evidence.

### Per-gap investigation contract

1. Write a small claim record under the existing checklist ID: public API and
   values, desired behavior, current source route, latest evidence and one
   missing observation. Classify it as defect, missing test, stale wording,
   intentional improvement/refusal or deferred scope.
2. Inspect source and existing tests first. For a defect, retain a bounded
   failing reproducer and expected oracle before changing code. For missing
   evidence, test the existing implementation. For stale wording, update the
   record without running graphics or building a wheel.
3. Fix the smallest responsible layer. Reuse native payloads when their inputs
   match; changed Python packaging does not by itself require a native rebuild.
   Record any source-only result separately from installed qualification.
4. Verify the named ordinary/mutation/failure/recovery cases as applicable.
   Run broader tests only when changed dependencies or an observed failure
   justify them. Preserve failed attempts; do not weaken a verifier.
5. Update both live checklists with date, evidence, source/artifact/profile and
   exact boundaries. Retain actual exit/child-wait records and finish managed
   cleanup before starting the next experiment or handing off.

Use `docs/build-hygiene.md`, `compat/build-hygiene.json`, the coordinator-selected
managed root and current protected/blocked registry. Register before writable
scratch; one experiment at a time, declared peak budget, no new unmanaged build
trees/environments or copied evidence histories. Budget/filesystem failures stop
allocation. Preserve source, original notices, minimal reproducers and current
qualification evidence; retain small reconstruction references for superseded
successes. Unknown-owner files and identity-pinned origins are not cleanup targets.

BUG-01/02 receive a new campaign only for recurrence or a new causal hypothesis;
record the known unresolved boundary otherwise. Optional hosts, new ABIs/GPU
families, cache/performance projects and historical cleanup receipt audits are
separate follow-ups, not automatic delivery blockers. Native physical Linux,
Metal graphics, Wayland, ARM/free-threaded Python, fractional DPI and generated-line
MSAA keep their existing unavailable/deferred scope. No cybersecurity work or
full-parity requirement is introduced. No universal coverage percentage is valid.

## Historical execution checkpoints

Windows draft smoke724passed, 2026-11-14:
[record](../../../compat/api-acceptance/preview-draft-windows-channel-v1.json)
verifies537members/23source notice inputs/22dist-info texts, no overlays, exact
64x64Vulkan clear and ten zero gauges. Reuses722transport/current original9e4
bytes without redownload; preserves the earlier verifier failure. All exits
awaited, target cleaned. Next WSL draft download/installed ABI-only check, then
actual public prerelease/separate index/byte readback. No native rebuild needed.

Draft Windows smoke722adapter failure, 2026-11-14:
[receipt](../../../compat/api-acceptance/preview-channel-adapter-failure-v1.json)
records successful authenticated transport/installation, then an assertion before
native import. [723](../../../compat/api-acceptance/preview-notice-placement-v1.json)
verifies23source-defined notice inputs(all exact) and22dist-info notice texts;
the extra input is metadata manifest.json in vispy/_licenses. Correct only the
adapter namespace/count, not wheels or validators. Failed exit1/awaited;
24,713,237bytes cleaned/18inputs verified. Reuse original9e4wheel and exact722
download receipt for the successor smoke; do not download it again solely for
this verifier correction. Later public-byte readback still remains required.

Delivery draft721created, 2026-11-14:
[record](../../../compat/api-acceptance/preview-release-draft-v1.json) verifies
draft prerelease445068448at exact55fdand two unchanged wheel digests/sizes.
Stable delivery.json/two wheels and two index blobs untouched. Actual exits0/
awaited;85bytes cleaned/30inputs verified. Next one bounded draft-asset download/
isolated install at a time: Windows exact537members/Vulkan clear, WSL537members/
native ABI import. Clean each before the next. Only then publish exact prerelease,
add the two reviewed preview-index paths without stable changes and verify
actual public bytes/index; retain explicit Linux channel ABI-only scope.

Delivery preflight720failed before remote mutation, 2026-11-14:
[record](../../../compat/api-acceptance/preview-draft-precheck-failure-v1.json)
shows the stable release has delivery.json as well as two correct wheel hashes.
Correct successor must filter exactly the two wheels and preserve all three
assets, not overwrite/remove the receipt. Actual exit1/awaited; original cleanup
duplicate-path refusal0deletion preserved, corrected new manifest/unchanged
tool cleans85bytes and verifies15inputs. No release/native/qualification change.

Packet3protected source integration complete, 2026-11-14:
[719](../../../compat/api-acceptance/parent-protected-integration-v1.json) verifies
PR77mergeba49b468tree4260039fequals the exact23-job tested PR tree37e718a1.
Exact55fdsource head pinned, required checks pass, no force/admin bypass or
shared checkout/index change; source702hashes remain unchanged. Connector ready
permission failure is retained; existing authorized CLI completes protected
auto-merge, actual exits awaited, no scratch. Next publish only the reviewed
exact55fdcommit-stamped prerelease/preview namespace after draft-asset/install
checks, then public byte/channel readback. Later post-head records/docs/two
tests require separate explicit delta/impact/protected integration; do not
label their future head55fd or transfer the old review to new critical bytes.

Packet2actual admission complete, 2026-11-14:
[718](../../../compat/api-acceptance/parent-final-admission-v1.json) passes
unchanged strict128-binding admission plus8current mandatory rows at reviewed
manual-retention scope. Exact guard sequence716runs before/after materialization,
immediately around validation and after matrix derivation; all14canonical/
702committed files restore and foreign HEAD/index stay unchanged. New derived
matrix viewe1efb9ad…preserves original230b12f3and all8other rows(6optional
historical/2NOT_ADMITTED). Actual exit0/awaited;87bytes cleaned/44inputs verified.
Next packet3: fresh protected PR77state/source identity audit and authorized
integration, separate delta/impact check for later data/docs/two tests, exact
55fdpreview tag/prerelease, draft-asset byte/install checks and public channel
readback.714/716conditions and717notes/tag corrections remain binding. Broader
API/hardware/optional-host work is not discharged by this selected admission.

Packet2final review approved, 2026-11-14:
[714](../../../compat/api-acceptance/parent-promotion-review-v1.json) approves
exact basis/eight manual-retention rows/commit-preview scope, preserving all
conditions and limits.89scratch bytes cleaned/886inputs verified, actual exit0/
awaited. Before admission, resolve F4precisely: source workspace has no.git and
all702inputs include the one intentionally overlaid ledger. [715](../../../compat/api-acceptance/admission-source-guard-v1.json)
proves all702actual files equal55fdGit blobs without changing foreign HEAD/index;
focused716review now assesses the exact701-nonledger/positive-ledger guard and
full702restoration sequence. No actual admission yet. [717](../../../compat/api-acceptance/preview-publication-corrections-v1.json)
addresses F2/F3notes/tag prerequisites as new records, preserving frozen701/714.
Then derive the new current-row matrix identity while leaving the historical
matrix/six optional/two NOT_ADMITTED rows unchanged, execute actual guarded
admission and complete protected integration/delivery. No verifier is weakened.

Packet2actual basis/review progress, 2026-11-14:
[711](../../../compat/api-acceptance/parent-promotion-basis-v1.json) seals exact
basis1e92e7de…for subject86efb22b…/head55fd4e8with full709CI/impact702.702committed
inputs unchanged; byte-identical small subject copy satisfies the outer source-
local reference namespace, preserving transitive origins. Actual assembly exit0/
awaited, no scratch. Read-only714final review is now active with871input guards;
separate basis/eight-row/channel decisions required. Guarded actual admission/
restoration, protected integration and delivery remain future gates. Older
prepared/unexecuted and live-CPU snapshots below are historical.

Packet1complete, 2026-11-14: [709](../../../compat/api-acceptance/parent-final-head-ci-v1.json)
passes unchanged full23-job original CI/history/attempt/checkout validation at
55fd4e8.15CPU/3native reports reused; only5small CPUarchives downloaded. Actual
exits0/awaited;1,012,877bytes cleaned/84inputs verified, scratch absent. Proceed
to711exact basis and714independent final review, then actual guarded admission/
restoration, protected integration and delivery. Earlier live-job snapshots
below are historical; no CI/admission claim is transferred to another head.

Packet6SCI-02selected composition subset complete, 2026-11-14:
[Windows712](../../../compat/api-acceptance/mesh-color-alpha-windows-v1.json) and
[WSL713](../../../compat/api-acceptance/mesh-color-alpha-wsl-v1.json) each pass
six Alpha/ColorFilter/TextureFilter/PlanesClipper cases. Literal32x24pixels match
for all three queued revisions(pending2/4/6), including detach/reattach, zero
alpha and invalid-input recovery. Both targets cleaned47,787,437bytes/1,150files,
68retained-input verifications; exits awaited and native inputs unchanged.
BroaderSCI-02stays partial. Original CPU43554619087still19success/1active in the
latest verified poll; return to its completion and final709/711gates. Post-head
tests do not change the frozen-head qualification claim.

Packet6SCI-02composition progress, 2026-11-14:
[Windows712](../../../compat/api-acceptance/mesh-color-alpha-windows-v1.json)
passes six Alpha/ColorFilter/TextureFilter/PlanesClipper mutation cases with
literal32x24pixels, three queued snapshots(pending2/4/6), detach/reattach, zero
alpha and immediate recovery after invalid input. Existing wheel/runtime reused,
no native change. Actual exit0/awaited;17,908,464bytes cleaned/33inputs verified.
Next run only this finite counterpart on WSL, then return to original CI/final
admission. General filter ordering/compositions/blending/MSAA remain open.

Packet3local delivery preparation, 2026-11-14:
[preview710](../../../compat/api-acceptance/parent-index-preview-v1.json) generates
two separate763-byte-total package-index pages using the unchanged generator.
The proposed commit-stamped prerelease namespace links exact existing wheel
bytes; stable four-link index blobs are fetched/verified and untouched. No
scratch/native build/remote write; actual exit0/awaited. This proposal still
requires final review acceptance and complete CI/admission/protected integration
before publication and actual channel checks. Same version is not a stable upgrade.

Latest continuation checkpoint, 2026-11-14: original CPU43554619087has19passes
and1active macOS x86_64 CPython3.11.14build, no observed failures. Final collector709is prepared
and syntax-checked but unexecuted/unregistered; it reuses704's15CPU reports and
700's3native reports, downloads only five missing small archives and requires
all23original jobs/history before creating a valid bundle. No scratch allocated
for this preparation. Continue the same handles, then exact promotion-basis
review and scoped admission.708completes seven-row record reconciliation only.

Promotion-basis assembler711is also prepared/syntax-checked, not executed. It
requires709complete validation and cleanup, rechecks702committed input hashes,
materializes only the necessary small immutable subject JSON in the outer
envelope's source-local namespace and preserves all transitive evidence origins.
Only then may it seal the exact basis for independent final review. No gate
or verifier is changed and no scratch is allocated by this preparation.

Final review-packet builder714is prepared/syntax-checked, not executed. It
requires actual709CI/711basis outputs, freezes original run/jobs/identity/history
objects and exact eight-row/manual-retention evidence, includes the concrete
701/710preview proposal and explicitly withholds broad API/hardware claims.
It requests separate exact promotion/eight-row/channel decisions and later
controlled-integration conditions. Original CPU run remains19pass/1active at
the latest verified poll; do not register or launch review before prerequisites.

## Next investigation queue — 2026-11-13 planning revision

This queue supersedes older next-action instructions below. This revision is
planning only: no CI refresh, experiments, admission or publication was run.
Recorded CI snapshots are historical until refreshed. Do not repeat already
completed preparation, installed observations or parent-destruction fixes.

### Starting evidence and scope

The [head-bound subject](../../../compat/api-acceptance/parent-head-installed-subject-v1.json)
records 128 proved criterion/profile bindings across 64 criteria at qualification
head `55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1`, runtime `2b8bccd`,
Windows wheel `9e4e30cc…` and Linux wheel `a2715d26…`. This is finite installed
proof, not admission. [All eight mandatory observations](../../../compat/api-acceptance/mandatory-parent-current-wheels-observations-v1.json)
and their [pre-admission review](../../../compat/api-acceptance/parent-mandatory-peer-review-v1.json)
already exist. [Three native CI identities](../../../compat/api-acceptance/parent-native-ci-identities-v1.json)
are verified; the complete final-head 23-job evidence remains unverified in the
records inspected for this revision. Published Vulkan.2 remains a separate,
immutable release. None of these counts measures full VisPy parity.

### Ordered packets and finish conditions

Packet4seven-row record reconciliation complete, 2026-11-13:
[708](../../../compat/api-acceptance/scientific-current-dispositions-v2.json)
verifies33input hashes, both44-case JUnits, both camera packets and six current
Qt rows' original seven-stage reports. The existing method-reconciliation
document now maps U05/E03/E04/Q11–Q13/H03to exact current, historical or open
scope and next claims.707adapter failure is retained; corrected708exits0/awaited,
no replay/install/scratch. Broad API/capability review and admission remain open.

Packet1latest verified wait, 2026-11-13: original CPU43554619087poll5has
16success/4in-progress/no failures. All702committed qualification inputs still
rehash unchanged after separate camera tests. Reuse15CPU/3native retained
identities; final full23-job/history validation remains pending.

Packet6selected camera-mutation subset complete at local installed scope,
2026-11-13: [Windows705](../../../compat/api-acceptance/camera-mutation-windows-v1.json)
and [WSL706](../../../compat/api-acceptance/camera-mutation-wsl-v1.json) each pass
2public TurntableCamera azimuth/center mutations with exact fresh-scene changed
poses, visible-change controls, peer-scene closure and independent frozen-pose
restoration. Current wheels/runtime unchanged; post-head test is not final CI
or admission proof. Ten zero gauges each; all exits awaited. Both temporary
targets cleaned47,787,811bytes/65retained-input verifications. SCI-03 remains
partial for other cameras, projection/event and plane/depth/stencil interactions.

Packet6bounded progress during original CI wait, 2026-11-13:
[Windows camera705](../../../compat/api-acceptance/camera-mutation-windows-v1.json)
passes public TurntableCamera azimuth/center mutation, fresh-scene equivalence,
peer-scene closure and exact frozen-pose restoration on the existing wheel.
Two tests are post-head source, no runtime/native changes. Changed poses have
metamorphic, not independent upstream, oracles.537members/zero overlays/ten zero
gauges; exit0/awaited;17,908,651bytes cleaned/32inputs verified. Next renew this
same finite case on WSL; broader3Dstate combinations and final release gates
remain separate. Original CI was verified live before choosing this task.

Packet1partial completion, 2026-11-13: [704](../../../compat/api-acceptance/parent-cpu-ci-identities-v1.json)
verifies15completed CPU identities against original attempt1/run43554619087
metadata, artifact byte counts/digests and exact source/PRcheckout/workflow pins.
Five CPU jobs remain pending in the retained snapshot. Final collection must
reuse704's15reports and700's3native reports, download only missing identities,
refresh all original run/jobs/history and validate the unchanged23-job bundle.
Collector exits0/awaited;3,017,597bytes cleaned/83inputs verified, no scratch.

Latest packet1wait, 2026-11-13: original CPU43554619087poll4verifies15success/
5in-progress/0queued, no failures. Keep the same live handles. No all23-job
bundle or final admission/promotion is inferred from this snapshot.

Packet2 supplement, 2026-11-13: [audit703](../../../compat/api-acceptance/candidate12-review-transition-v1.json)
checks702F4against the original674candidate archive and675before-hashes. Only
review references and the seal change; both scope digests and approval hashes
verify. Coordinator source-only evidence does not broaden the independent
review. Actual exit0/awaited, no scratch/build or new admission.

Packets1–2 checkpoint, 2026-11-13: [impact review702](../../../compat/api-acceptance/parent-head-change-impact-v1.json)
approves exact subject86efb22b/head55fd4e8 reuse only, with no required changes;
read/hash-reliance limits and later-head exclusion remain attached. Reviewer
exit0/awaited;8,908scratch bytes removed,828inputs verified. Original CPU
run43554619087poll3has14success/5running/1queued, no failures; remaining work is
macOS CPU builds/vendor restoration. Complete the same handles'23-job identity
and history bundle, then obtain exact promotion-basis review. Do not transfer
this approval to new source commits or skip guarded ledger restoration.

| Order / IDs | Question and cheapest first action | Required result / stop rule |
| --- | --- | --- |
| 1. FIX-04/06, TOOL-01 | Refresh PR77, its exact head and the existing CPU43554619087, Linux43554619086 and Metal43554619080 attempts. Inspect any incomplete change-impact review registration before resuming or creating scratch. | Record current state, not an inferred pass. Collect missing CPU identities and complete original run/job/attempt histories; reuse the three verified native identities. Validate all23 jobs at the exact head. Queue delay alone never triggers redispatch or rebuilding. A failure gets one diagnosis and a minimal reproducer before a retry. |
| 2. FIX-04/06, API-06, SHD-06 | Join the head-bound subject, eight-row dossier, exact failure dispositions and complete CI. Identify the first invalid field before repeating a graphics test. | Exact source-to-artifact impact review, then exact promotion-basis review and unchanged scoped admission validators. Keep generic Tk retention separate from the mandatory rows' manual foreign-origin audit. Preserve all14 canonical files and original failures. Missing joins remain open. |
| 3. FIX-04/06 | Review the owned delta and current main; inspect the existing publication proposal before selecting a delivery identity. | Protected integration, then actual delivered-byte and isolated channel-install checks if publishing. Resolve the current wheels' unchanged `0.17.0+vulkan.2` version versus different published bytes explicitly: never overwrite stable assets or invent a version by renaming a wheel. A preview proposal is not an approved or completed delivery. Preserve AGPL, original BSD and dependency notices. |
| 4. API-05/06, SCI-05/06 | Reconcile U05/E03/E04/Q11–Q13/H03 and numeric-zero/stencil wording against current evidence. Use the existing method catalog and public-route documents, not a fresh full inventory. | A compact route/value/evidence table in the live checklist: source, artifact/profile, observed behavior, missing assertion, disposition and reopening trigger. Q11 is MSAA depth/stencil; Q13 is input, not volume coverage. Correct stale statements without promoting historical/source proof to current installed admission. |
| 5. LIF-01–06 | Audit existing real-toolkit reparent, parent deletion, minimize/restore, close and injected-loss checks. Select the first missing observable transition, not an entire lifecycle rewrite. | One finite case with callback/order, no-submit or exact peer output, failure/recovery and final resource gauges as relevant. Keep toolkit/readback evidence separate from physical WSI loss. Add a runtime fix only after a demonstrated failure. |
| 6. SCI-01–04, STA-01 | Rank point, filter, camera and volume combinations by an actual supported workflow. Begin with a public camera mutation in the existing two-scene fixture if reconciliation finds no smaller confirmed gap. | One analytic or frozen-reference before/after result, relevant boundary/recovery case and exact profile. Reuse existing point/filter passes; select volume quality, modes and performance separately. Do not turn every possible combination into a required test. |
| 7. SHD-01–06, TEX-01, LIN-01, LIF-05–07 | Expand shader, texture, line, MSAA or input forms only when packets4–6 identify a needed route. Start with parser/refusal and retained driver/profile evidence. | Named supported values, positive result, boundary/refusal and recovery. A documented restriction closes only its disposition task. Broad parent capability remains partial where appropriate. |
| 8. BUG-01/02, HOST/PLAT/PERF/TOOL backlog | Inspect existing startup campaigns and historical receipts first. Select optional hosts or optimization only for an actual application claim or measured bottleneck. | Startup investigation requires recurrence or a new causal hypothesis; bounded non-recurrence does not prove a fix. Search once for missing historical cleanup proof; never recreate it through another deletion. Unselected work remains deferred with a reopening trigger. |

### One-gap execution protocol

Packet4 partial progress, 2026-11-13: both664/665selected JUnit files were
rehashed against the current installed packet and their44case IDs/results
compared. Stencil and live-checklist wording now records the existing local
installed11clear/8stencil/10point/4filter/2scene/9Qt cases per platform.
No runtime replay or broader admission follows. Remaining reconciliation must
still distinguish Q11 MSAA, Q13 input, H03 historical host scope and the specific
uncovered camera/filter/point combinations.

1. State the public route, selected values/profile and exact missing observation.
   Classify the item as a confirmed defect, evidence gap, stale record, explicit
   restriction or deferred scope. Record the cheapest falsifying check.
2. Read existing evidence before running anything. Start with source-only checks
   in the existing environment. For an experiment, predeclare attempt/time/storage
   bounds in its run manifest; stop on the first useful failure or budget limit.
3. Fix only the demonstrated route. Add a regression that distinguishes the old
   and corrected behavior. Rebuild native code only when native inputs changed;
   qualify only artifacts/profiles affected by the change-impact assessment.
4. Update the affected IDs in both live checklists with date, source/artifact,
   profile, result, evidence and remaining boundary. Keep source-tested,
   installed-qualified, admitted and publicly delivered states separate.
5. Retain failures, sources/notices and actual exit/child wait. Inspect/apply the
   managed cleanup plan and record its result before the next experiment.

Use the coordinator storage root and current protected/blocked registry under
[build hygiene](../../build-hygiene.md), with one registered run per writable
scratch allocation. Do not copy environments, SDKs or evidence histories. This
planning revision creates no scratch, build assets or temporary environment.

The immediate milestone is completion of packets1–3 for the selected successor,
followed by one selected feature gap at a time. The142 original obligations and
984 unreviewed operation groups are inventories, not confirmed defects or a new
full-parity target. Windows/WSL remain the practical target; Metal graphics stays
experimental, with physical Linux GPUs, Wayland, other ABIs/architectures,
fractional DPI and lab scanout measurements retaining their existing boundaries.
Cybersecurity work is excluded.

## Active investigation and closure queue — 2026-11-13

This section supersedes the older next-work instructions below; their evidence
and checkpoint descriptions remain historical. This is a planning change only.
Do not start experiments as part of this update. Work one bounded gap at a time,
updating both live checklists with the exact result before starting the next.

### Baseline to preserve

- Runtime source: `2b8bccd0ac886f771c3e37255a3d5559c254b3cd`.
- Unreleased candidate wheels: Windows `9e4e30cc…`, Linux `a2715d26…`.
  [Installed acceptance](../../../compat/api-acceptance/qt-parent-current-installed-v1.json)
  records 44 selected cases plus 56 Tk baseline cases and composite recovery per
  platform. These observations establish local installed scope, not admission.
- [Preparation12 approved bindings](../../../compat/api-acceptance/preparation12-approved-bindings-v1.json):
  scope `4c2295f5…`, 14 frozen canonical files, 64 distinct criteria,
  128 profile bindings and 32 selected rows. All 142 original obligations remain
  required; the selected subset does not discharge the full inventory.
- Use Windows Vulkan and WSL pinned software Vulkan for current claims. Metal
  remains experimental. Published Vulkan.2 assets and historical failures stay
  immutable. Keep AGPL and original BSD/dependency notices attached.

### Release-critical sequence

Current CI wait: original CPU43554619087poll2has2pass/13running/5queued, no failures. Same-handle continuation only; Linux/Metal3identities retained700, native transport cleaned. Next CPUcompletion/20identities/full23-job-history join, then exact admission/promotion/integration.

Step4 [700native identities](../../../compat/api-acceptance/parent-native-ci-identities-v1.json)verifies3successful original Linux/Metal PR job checkout/source-parent/workflow/collector joins at55fd.202,057,916transport bytes hash-verified, only identity/member metadata retained;202,058,005bytes cleaned/36inputs verified. No native extraction/build. Next original CPU43554619087completion,20CPUidentities and full23-job/history validation, then exact promotion/admission/integration.

Step4 [699exact55fd subject](../../../compat/api-acceptance/parent-head-installed-subject-v1.json)renews128bindings/zero missing-blocked,702committed input joins; all14files restored using684archive, no scratch/native build, owner index unchanged.698poll1hasLinux1/Metal2jobsSUCCESS,CPU15running/5queued. Next same-handle CI completion plus all identity/artifact/history joins, exact promotion/admission and PR77protected integration/delivery.

Step4 [698draftPR77/CI](../../../compat/api-acceptance/parent-head-ci-start-v1.json)starts exact55fd PR attempt1handles CPU43554619087/Metal43554619080/Linux43554619086, zero duplicate manual dispatches. Snapshot:LinuxSUCCESS(metadata only),CPUqueued,Metalin progress.23jobs/identities/full histories still required. No scratch. Next guarded55fd subject renewal while polling these original handles; no merge/admission yet.

Step4 [697owned head](../../../compat/api-acceptance/parent-qualification-source-head-v1.json)pushed55fd4e8:110files/3,738,502bytes, all608runtime/build/license inputs unchanged, other-owner index preserved.15,115,728bytes cleaned/51inputs verified; failed696caller setup preserved/cleaned separately. Next exact55fd CI23jobs, avoiding duplicate PR/manual dispatch; guarded head proof and final admission/integration remain open.

Step3 [695independent pre-admission review](../../../compat/api-acceptance/parent-mandatory-peer-review-v1.json)approved exact current bindings/fixtures/manual retention/finite history and688failure disposition, no required changes. Read-range/hash-reliance/unread-row/unknown-child limits retained; original failed status unchanged.88bytes cleaned/1156inputs verified,14canonical files unchanged. Next step4owned final head/23-job CI and head-proof renewal, then exact admission/promotion/integration/delivery; no release approval.

Step3 [693/694bindings/history](../../../compat/api-acceptance/parent-mandatory-bindings-v1.json)pass8rows/24gates/1036retention checks/492fixture members, with15foreign protected origins explicitly manual-scope only. Scan344of17,732JSONs yields9strict attempts(8pass/1preserved688UNVERIFIED),8discoveries,0unattributed/later failures. No scratch/14canonical changes. Next independent exact scope+688disposition review, final-head CI/admission/integration.

Step3 [all8current observations](../../../compat/api-acceptance/mandatory-parent-current-wheels-observations-v1.json)collected;692WSL headless adds95GPU/36science/rendering/4096markers with first strict replayPASS. Every profile537members/ten zero gauges. Nine strict attempts(8pass/1preserved688UNVERIFIED), exact failed-attempt review/bindings/history still needed. FourWSL cleanups370,357,709bytes; all8cleanups818,059,241bytes/8941files, no scratch.14canonical inputs unchanged. Next eight-row proof/history/admission, final owned-head CI and integration/delivery; no release admission.

Step3 [WSL Qt689–691](../../../compat/api-acceptance/mandatory-parent-wsl-qt-observations-v1.json)complete at observation scope; all six Windows/WSL Qt bindings pass.7of8mandatory observations; WSL headless is next. Three WSL consumers cleaned277,768,280bytes/36files,103inputs verified per run;690guard refusal and exact successful retry preserved. No admission.

Step3 [WSL PyQt5/690](../../../compat/api-acceptance/mandatory-parent-wsl-pyqt5-v1.json)passes7stages/first strict replay on its original matching root;537members/ten zero gauges. Initial cleanup live-PID refusal remains exit2/zero deletion; PID later absent, unchanged plan/guard retry succeeds,92,589,426bytes cleaned/103inputs verified.6of8current observations; next WSL PySide6/headless. No admission.

Step3 [WSL PyQt6/689](../../../compat/api-acceptance/mandatory-parent-wsl-pyqt6-v1.json)passes7stages/first strict replay/537members/ten zero gauges on a271wheel/pinned Mesa. Dependencies match original629fingerprints; notice archive reused, unchanged512MiB envelope.92,589,426bytes cleaned/103inputs verified, host mounts absent.5of8current observations; next WSL PyQt5/PySide6/headless. No admission.

Step3 [Windows688/aggregate](../../../compat/api-acceptance/mandatory-parent-windows-observations-v1.json)completes4of8current mandatory observations. Headless95GPU/36science/rendering/4096markers pass strict replay1; replay0UNVERIFIED(one file)retained and needs exact disposition.688cleanup69,192,235bytes/293inputs verified, allWindows447,701,532bytes cleaned. Original fixtures/archive reused; successor resource profile keeps256MiB/all expectations. Next four WSL profiles, then exact failure review/admission/final-head integration.

Step3 [Windows Qt685–687](../../../compat/api-acceptance/mandatory-parent-windows-qt-observations-v1.json)complete at observation scope:3bindings, each7stages/first strict replay/537members/ten zero gauges.378,509,297bytes cleaned,65inputs verified per run,14frozen files unchanged.3of8current mandatory observations; next Windows headless and four WSL profiles. No admission.

Step3 [Windows PyQt5/686](../../../compat/api-acceptance/mandatory-parent-windows-pyqt5-v1.json)passes seven stages/first strict replay;537members/binding and ten zero gauges.113,809,395bytes cleaned/65inputs verified.2of8current observations complete; next PySide6/remaining profiles. No admission.

Step3 [Windows PyQt6/685](../../../compat/api-acceptance/mandatory-parent-windows-pyqt6-v1.json)passes seven stages/first strict replay on9e4wheel;537members and ten zero gauges.129,752,954bytes cleaned/65inputs verified,1of8current observations complete. Next PyQt5 and remaining profiles; no admission.

Step2 finite subject proof now [684complete](../../../compat/api-acceptance/preparation12-installed-subject-v1.json):128bindings/64criteria/32rows, zero missing/blocked; five attempts and782-input retention validate. Exact14files restored against675hashes; no scratch or admission. Next step3eight current mandatory profiles, then owned final-head CI/integration and exact promotion/delivery. The142original obligations remain required and incomplete.

Step2 [683contributing retention](../../../compat/api-acceptance/preparation12-proof-retention-v1.json)passes unchanged generic validation for782inputs after marker-only93bytecleanup. Both native/archive proofs revalidated; no input copies/moves. Extra foreign original baseline is separately hash-verified/disclosed. Next guarded128-binding subject proof and14-file restoration; no admission.

Step2 [682failure disposition](../../../compat/api-acceptance/preparation12-failure-dispositions-v1.json)approved for the single676UNVERIFIED attempt and draft-only later PASS selection. Explicit peer reading/hash-reliance limits retained; original failure unchanged.88bytes cleaned/122inputs verified. Next contributing retention and guarded subject proof; no admission.

Step2 [681history inventory](../../../compat/api-acceptance/preparation12-attempt-history-drafts-v1.json)scans17,422JSONs/79controllers:5exact attempts(4pass/1Windows UNVERIFIED),0unattributed reports. Four latest workflow selections validate. One new exact failure disposition still needs independent approval; then contributing retention/guarded subject proof. No scratch, canonical change or admission.

Step2 row overlay now [680valid](../../../compat/api-acceptance/preparation12-installed-row-bindings-v1.json):32rows/128bindings/96gates, frozen14and execution scope unchanged,142original obligations incomplete. No scratch or admission. Next complete strict attempt histories, exact failed-attempt disposition and contributing retention before subject proof.

Step1 observations/receipts complete at their finite scopes: [WSL679](../../../compat/api-acceptance/preparation12-wsl-criterion-phases-v1.json)adds2nodes/6phases/16fixtures with exact Linux metadata, private Xvfb and borrowed-origin checks.29,870,483bytes cleaned/30inputs verified. Next step2derived32-row overlay and complete current attempt history/disposition/retention; no admission.

WSL step1 strict is now [678complete](../../../compat/api-acceptance/preparation12-wsl-strict-cohort-v1.json):both workflows pass replay0,16joins/48gates on a271wheel/pinned Mesa. Controller/Xvfb exited0/awaited;92,589,423bytes cleaned and119inputs verified. Both platforms now have current strict cohorts; genuine WSL pytest phases are next.14frozen inputs unchanged, no admission.

Windows step1 pytest receipts are now [677complete](../../../compat/api-acceptance/preparation12-windows-criterion-phases-v1.json):2nodes/6phases validate16row fixtures on9e4wheel. This is a separate consumer from676strict. Cleanup removes17,899,973bytes/25inputs verified. Next WSL strict/pytest; no admission.

Current step1 progress: [Windows676](../../../compat/api-acceptance/preparation12-windows-strict-cohort-v1.json)
passes both strict workflows,16feature joins/48gate checks on current9e4wheel;
14frozen preparation files unchanged. State replay0UNVERIFIED is retained and
needs exact disposition review; replay1and capture replay0pass. Consumer cleanup
reclaims62,906,058bytes, verifies65inputs; scratch absent. Next collect genuine
Windows pytest phase receipts, then current WSL strict/pytest observations.
No admission or transfer to mandatory Qt rows is granted.

| Order / IDs | Investigate first | Easiest closure path | Evidence required to finish |
|---|---|---|---|
| 1 — FIX-04/06, API-06 | Which strict observations and receipts are missing for these exact wheels? | Reuse the retained Windows 614 and WSL 616 recipes after inspecting their actual inputs; substitute current approved preparation/wheel identities. Run Windows first, clean, then WSL. Reuse locked dependencies and native artifacts. | Both state/resource/failure and capture workflows pass on each claimed exact consumer fingerprint; discovery and every strict attempt remain separately recorded. Genuine pytest receipts cover two nodes and all setup/call/teardown phases per platform. Frozen preparation hashes remain unchanged. |
| 2 — FIX-04/06 | Are all current selected rows connected to real observations? | Derive the 32-row overlay from retained current receipts; reuse existing binding/proof tools. Audit only contributing histories, retaining earlier failed attempts and their dispositions. | All 128 bindings/64 criteria and 96 gate joins validate; complete attributable attempt history, contributing retention and exact reviewed failure dispositions validate. Guarded subject-proof overlay is restored byte for byte across all 14 files. |
| 3 — FIX-06, LIF-02/04, API-06 | Which of the eight mandatory profile cells still refer to old wheels? | Renew only missing current headless/PyQt5/PyQt6/PySide6 Windows/WSL cells using their original locked closures, one consumer at a time. Reuse current observations only where exact identities and the verifier allow. | Eight exact-wheel observations with required output, failure/recovery, installed-origin and final resource checks. CPU binding tests alone do not close rendered profile cells. Observations and admission remain separate. |
| 4 — FIX-04, TOOL-01 | Are owned source, external test changes and CI selectors consistent? | Integrate only owned deltas, including the two parent-destruction GPU assertions, through a private index sized for the full tree. Synchronize workflow selectors and policy hashes before the final freeze; reuse native inputs. | Parent source/test identities, policy/selector tests and immutable runtime/native correspondence verified; other owner's index unchanged. Exact final head has all 23 required CI jobs, checkout/artifact identities and complete histories validated. Earlier 6d6 success stays historical. |
| 5 — FIX-04/06 | Does the exact promotion basis satisfy the unchanged admission tools? | Obtain the required exact-basis review, run existing admission validators, then use authorized protected integration and delivery. Settle a new release identity before publishing changed bytes. | Scoped admission, protected merge and installed delivery checks against the actual published assets. Never overwrite published Vulkan.2 files or claim final-head CI for a different head. |

Steps 2 and 3 may be prepared from existing metadata while step 1 runs, but do
not launch overlapping installations or duplicate CI. If a critical source or
artifact input changes, identify the affected claims and renew only their
required evidence; never relabel old evidence. A documentation-only update is
not a reason to assemble another wheel or rebuild Dawn.

### Feature investigation after the selected release blockers

Each investigation produces a small claim table: exact public route and values,
current implementation, reusable evidence identity, observed gap, disposition,
and one next acceptance case. Choose supported subset, intentional improvement,
explicit refusal or deferred scope before writing code. An untested route remains
open; a documented refusal closes only its selected boundary investigation.

| IDs | First question / shortest useful path | Closure evidence for the selected claim |
|---|---|---|
| API-05/06 | Reconcile method/value dispatch, aliases and wildcard exports against the completed parent namespace reviews. Prioritize routes used by existing fixtures; avoid a new full upstream inventory project. | A method-level claim map with ordinary, mutation, refusal/recovery cases and exact installed artifact links; retain canonical inventory's unreviewed/full-parity status. |
| SCI-05/06 | Reconcile stale U05/E03/E04/Q11–Q13/H03 and stencil descriptions against current installed 664/665 evidence before rerunning anything. | Update only matching finite dispositions; preserve upstream failures, historical epochs and separate host/admission claims. |
| LIF-01–04 | Audit existing fault, reparent, minimized/zero-size and close/loss controls; identify one genuinely missing observable behavior. Parent deletion is already fixed and locally installed-tested. | One focused real-toolkit case for each newly selected gap: no-submit/restoration or shared-peer output, failure recovery and final ownership/resource retirement. Native doubles support but do not replace rendered scope. |
| SCI-01, SHD-03 | Determine which additional indexed/instanced point layout or mutation is actually needed beyond the current eight rendered cases. | Small analytic rendered fixture with source/instance identity, before/after output, limits/refusal and cleanup; label internal queue controls separately from public API. |
| SCI-02 | Enumerate implemented filters and useful compositions; start with the largest uncovered supported composition, reusing current four pending-draw mutation controls. | Meaningful before/after pixels and pending-state witness for the selected composition, plus detach/refusal/recovery. No all-filter claim from four cases. |
| SCI-03, STA-01 | Extend two fixed scenes with one public camera mutation, then only needed plane/depth/stencil/polygon-offset interaction. | Frozen or analytic output before/after mutation, state isolation and recovery on selected profiles. |
| SCI-04 | Audit retained volume modes, mutation and quality evidence before selecting an additional mode or dataset. | Bounded quality/mutation fixture; performance and large-data claims need separate measurements and disk budget. |
| SHD-01/02, TEX-01 | Inventory parser/runtime refusals for sampler/array classes and typed sampling. Prefer existing supported forms and explicit diagnostics over broad compiler changes. | Selected shape/type/index/LOD limits, deterministic output, mutation and refusal/recovery; no implied support for all shader forms. |
| SHD-04/05, LIN-01/02 | Establish a concrete geometry/line consumer before extending expansion, chunking or builtins. | Topology/endpoint/ordering and selected clipping/depth/resource-limit fixtures. Generated-line MSAA remains deferred unless explicitly selected. |
| SHD-06, LIF-05 | Reconcile patched-Mesa provenance and actual MSAA format/depth/stencil cells; keep system-Mesa failure intact. | Current pinned driver joins and selected format/sample-count observations; no transfer to physical GPUs or other drivers. |
| LIF-06/07 | Select a missing Qt input or Tk camera behavior using existing delivered-event fixtures. | Toolkit-delivered event/coordinate and rendered response with focus isolation/recovery. Physical HID, gestures and fractional DPI stay outside current claims. |
| BUG-01/02 | Review retained failure identities and exhausted campaigns; reopen only for recurrence or a new causal hypothesis. | Cause-specific reproducer/regression or precise unresolved disposition; recurrence blocks promotion as documented. No blind retry campaign. |
| HOST-03–06 | Renew optional host rows only for a chosen real application workflow. Reconcile Glue's corrected upstream disposition first. | Actual application rendering/mutation/teardown on the exact candidate; imports and historical host passes are insufficient. |
| PERF-02–04, TOOL-02/03 | Audit measurements and missing historical receipt first. Optimize only a demonstrated bottleneck. | Bounded before/after metric with fixed inputs; missing past cleanup proof remains unresolved rather than recreated by another deletion. |

### Hygiene, stop rules and completion

Read `docs/build-hygiene.md` before builds, installs or artifact checks. Use the
shared managed root, versioned budget and current protected/blocked registry;
register a unique run before writable scratch. Check both WSL guest and backing
volume health/capacity. Reuse immutable wheels, SDKs, source archives and locked
environments. Retain the minimal reproducer, actual exits/child waits, output,
source identities and licenses; inspect/apply the exact cleanup plan and report
its result before the next experiment. Budget failures stop new allocation.
Unknown-owner files and identity-pinned dependency origins are not cleanup targets.

No new hardware, full API parity, lab scanout parity or cybersecurity work is
required by this queue. Native physical Linux, Metal graphics, Wayland, other
ABIs/architectures and cross-monitor fractional DPI retain their existing deferred
or experimental status. Finishing steps 1–5 closes the selected successor release
work, not every broad parent. A feature row closes only after its selected claim
and explicit boundary are recorded in both live checklists with date, evidence,
source, artifact and profile scope. This update closes no capability and runs no
tests, installations, builds, CI, publication or cleanup.

## Current investigation plan — 2026-11-13

This is the authoritative next-work order. All older queues and pending notes
below are historical checkpoints; consult the linked receipts before repeating
work. The goal is a documented, useful Windows/WSL Vulkan subset with intentional
improvements, not full VisPy parity. This planning update launches no tests,
builds, CI or publication and grants no new coverage admission.

### Verified baseline and actual blockers

### Next investigation and closure sequence — planning refresh

Latest approved checkpoint: [674](../../../compat/api-acceptance/preparation12-peer-review-v1.json)
approves exact source/scope4c2295f5and both reuse hashes, with all read-only,
hash-reliance and unread-evidence limits preserved. [675](../../../compat/api-acceptance/preparation12-approved-bindings-v1.json)
binds approvals and revalidates candidate/coverage/execution/selection plus both
full native proofs/archives.14canonical files frozen,330historical JSONs unchanged,
142original obligations still required/incomplete.673lost structured stdout is
retained as incomplete/unbound;674complete stream fixes capture without assuming
approval. Both peer runs cleaned5,313bytes;675needs no scratch/native build.
Next use these exact14inputs for Windows/WSL strict workflows and genuine pytest
receipts, then mandatory profiles and final-head CI/promotion/integration. Local
installed100cases/profile and source approvals do not themselves admit artifacts.

Latest correction: [669scope/reuse refusal](../../../compat/api-acceptance/preparation11-peer-review-v1.json)
found stale required-CI workflow hashes and Linux reuse still selecting10.
[670/671successor12](../../../compat/api-acceptance/preparation12-ci-coupling-v1.json)
reproduces both faults, synchronizes CPU/Linux selectors and policy hashes, and
revalidates preparation/native/archive bindings while preserving330prior JSONs.
Scope4c2295f5and both renewed reuse hashes are unreviewed;11stays unapproved.
[672](../../../compat/api-acceptance/preparation12-policy-contracts-v1.json) passes
326source cases (282reuse/native +44CIpolicy),8,945,392scratch bytes cleaned.
Before any future scope freeze: synchronize every workflow candidate selector,
update exact required-CI hashes without changing job/collector requirements,
validate policy and cross-workflow selection, then pin preparation tools and
generate scope/reuse digests. Review arithmetic must also check manifest seals,
execution-scope normalization and live policy-to-workflow consistency. Re-present
the new exact digests before strict observation/admission; no CI job was launched
against the known broken preparation11.

Latest qualification checkpoint: [preparation11/666](../../../compat/api-acceptance/qt-parent-preparation11-wip-v1.json)
validates64criteria/128bindings/32selected rows, preserving142original obligations
and318historical JSONs. CPU selectors choose11before tool-hash freeze. [667bindings](../../../compat/api-acceptance/qt-parent-preparation11-bindings-v1.json)
revalidate both original native proofs/current archives, with review gates closed,
no new source snapshot/native build. [668](../../../compat/api-acceptance/preparation11-reuse-contracts-v1.json)
passes282source contracts,8,945,357bytes/4930files cleaned/9inputs verified.
Independent669review is active for scope5dd73de0and its two exact reuse digests.
After approval, bind it without changing scope, then renew strict/pytest and
mandatory profile observations for current wheels before final-head integration.
Do not borrow old approvals or count142original obligations as completed.

Latest installed milestone: [664/665](../../../compat/api-acceptance/qt-parent-current-installed-v1.json)
each pass44selected lifecycle/scientific cases plus56Tkbaseline/recovery on
exact current Windows9e4e30cc/Linuxa2715d26wheels/source2b8bccd.537members/origins,
zero overlays and tenzero gauges verify per process. Review recommendationN1
now has real-Canvas installed proof; its two added external test lines remain
for owned integration. WSL metadata561/566, patched Mesa/private Xvfb and borrowed
origins verify. Both targets cleaned48,168,056bytes/1210files,59inputs verified.
Earlier6d6all3CIruns/23jobs completed successfully, retained as metadata-only
observation with no new-source transfer. Next renew exact candidate/reuse,
strict/profile/head bindings and integrate the test delta before promotion.
No native rebuild, installed-to-strict admission or broader API parity claim.

Latest integration checkpoint: [661](../../../compat/api-acceptance/qt-parent-source-head-v1.json)
pushes22owned files as2b8bccdwith606runtime/build/license inputs unchanged and
two reviewed Python corrections. Other-owner index preserved; private-index
scratch15,100,800bytes cleaned within32MiB budget. [663](../../../compat/api-acceptance/qt-parent-python-package-v1.json)
assembles Windows9e4e30cc/Linuxa2715d26candidate wheels around unchanged natives.
Archive/payload audits pass, only two Python files plus RECORD differ; notices,
metadata, version/tags and published assets unchanged. Initial662missing-host-
dependency setup remains failed; existing project environment resolves it.
Both packaging runs cleaned. Next exact installed-wheel parent/regression
acceptance, then candidate/strict/profile/final-head qualification and protected
integration/delivery. No earlier6d6b233CI or published coverage transfer.

Latest priority5 review milestone: [660approval](../../../compat/api-acceptance/qt-parent-review-approved-v1.json)
accepts exact inspected source/tests with no required changes, resolving651F1–F3
and reading native duplicate-destroy logic. Read-only/no-recomputation/unread
evidence limits remain; coordinator guards verify exact inputs. Review scratch
84bytes cleaned/17inputs verified; existing source/license archives reused.
Next freeze/push only owned reviewed changes through a full-index-sized private
index, package changed Python members around the retained natives, and renew
exact installed/strict/candidate/head qualification before integration/delivery.
No native rebuild or prior6d6b233CI transfer. Include recommended real-Canvas
create_native/update no-op assertions during installed GPU acceptance. Other
binding evidence remains CPU only; prefix-filtered .py/.pyd origin checks do not
qualify Qt DLLs or absence of a second binding. Destruction callback accessors
that require a live native backend remain unavailable.651stays CHANGES_REQUIRED.

Latest binding checkpoint: [656/658/659](../../../compat/api-acceptance/qt-parent-binding-source-v1.json)
passes11Windows CPU parent controls each on PyQt5/PySide6 and cumulative68on
PyQt6, with original locked filtered dependency wheels and current generic
fixture.657functional11pass/post-test origin failure is retained;658binds exactly
12generated virtual aliases and7actual loaded wheel-member hashes. No wildcard
exclusion, existing verifier change, version refresh or native build. Managed
targets cleaned194,984,317bytes;659source check uses no scratch. This is finite
CPU/native-double coverage only; rendered other-binding claims remain separate.
Exact read-only review660is active against current source, prior findings,
654/655rendered and656/658/659binding evidence. After its result, address required
findings before changed-Python package/head qualification and integration.

Latest priority5 verification: [654/655](../../../compat/api-acceptance/qt-parent-followup-rendered-v1.json)
each pass8rendered cases on corrected653Python source. Both parent-deletion
orders preserve pending green and subsequent blue shared-peer pixels;537package/
overlay hashes and ten zero gauges verify. All children/owned Xvfb awaited;
47,770,459bytes cleaned, no scratch or native build. This is PyQt6-only source
evidence, not a wheel/strict/new-head admission. Current Windows .venv lacks
PyQt5/PySide6; reuse their original locked closures rather than upgrade/install
new versions for selected checks. Next renew exact source review with preserved
651findings and653/654/655evidence, complete selected binding checks, then package
the changed Python bytes around the retained natives and qualify/integrate.

Latest review checkpoint: [651](../../../compat/api-acceptance/qt-parent-destruction-peer-review-v1.json)
returns CHANGES_REQUIRED. [652/653](../../../compat/api-acceptance/qt-parent-destruction-reentrant-source-v1.json)
reproduce3failures then pass68CPU cases after fixing reentrant backend detachment
and closed-canvas recreation. Real explicit-close-then-delete, late update and
original callback exception controls are included. Eight-case two-order GPU
test is authored, not rerun;648/650source hashes are historical to this follow-up.
Next rerun Windows/WSL overlays, then selected PyQt5/PySide6 controls and renewed
exact review before packaging. Only PyQt6 is currently tested for the fix.
Live-native accessors after destruction are unavailable; close/update/create_native
no-op behavior alone is claimed. Review cleanup removed86bytes/verified14inputs;
CPU source checks allocate no scratch. No approval or admission is conferred.

Latest priority5 milestone: [WSL650](../../../compat/api-acceptance/qt-parent-destruction-wsl-source-v1.json)
passes the same7rendered cases as Windows648with two explicit Python overlays,
retained Linux native payload and patched Mesa software Vulkan/private Xvfb.
Pending green/subsequent blue each4x4RGBA exact,537member/overlay hashes and ten
zero gauges verify. Borrowed origins unchanged, controller/Xvfb exited/awaited.
Initial649setup failed before GPU; existing629abstract-local transport flags
resolved it without system changes. Both attempts cleaned57,643,258bytes; failed
history retained. Next: independent review, selected binding controls and new
Python package/installed/head qualification. Do not transfer frozen6d6b233CI.

Latest rendered result: [Windows648](../../../compat/api-acceptance/qt-parent-destruction-windows-source-v1.json)
passes7GPU cases, including actual parent-owned deletion, pending shared-peer
green and subsequent blue readback (4x4RGBA each exact), and existing close/layout
controls. Base-wheel/native payload is reused with exactly two Python overlays;
537members/overlay hashes and ten final zero gauges verify. Cleanup removed
17,899,700bytes/568files, verified12retained inputs; scratch absent. No native build.
Next: same WSL source investigation, independent review, then changed-Python
packaging and exact installed/head qualification. No prior frozen6d6b233CI transfer.

Latest priority5 progress: [source fix647](../../../compat/api-acceptance/qt-parent-destruction-source-fix-v1.json)
passes64CPU controls, including real parent deletion, callback/error preservation,
weak-owner collection, native release failure and close idempotence. Initial644
and intermediate645failures remain retained. `_qt.py` plus `canvas.py` now differ
from frozen6d6b233; its running CI and existing wheels remain evidence only for
their original inputs. Before promoting the cumulative implementation, review
the new fix, verify rendered parent deletion/shared-peer recovery on Windows/WSL,
and renew exact Python package/installed/head bindings. Native inputs are unchanged;
reuse the verified native payload. No scratch or native build for these CPU runs.

Priority5 now has a confirmed [parent-owned destruction failure644](../../../compat/api-acceptance/qt-parent-destruction-source-failure-v1.json):
real offscreen Qt deletion destroys the child and invokes the native release
double, but leaves the actual Python Canvas open. One CPU test fails, actual
exit1/awaited, no runtime change/scratch/native build. Preserve frozen6d6b233CI.
Next implement Python ownership settlement without accessing deleted QWidget
methods; preserve module-rooted GC-safe release and contained callback errors.
Prove idempotence, callback failure, collected-owner and shared-peer behavior
before claiming installed closure. Native release alone is insufficient.

Source-only [reconciliation643](../../../compat/api-acceptance/scientific-stale-row-reconciliation-v1.json)
corrects the fixture mapping: Q11 is MSAA depth/stencil (LIF-05), Q12 is
binding/platform coverage, and Q13 is input forwarding (LIF-06). Volume workflows
are V01–V09. Six exact current Qt packet/hash joins verify seven stages each,
537members, zero overlays and ten zero gauges; this audit replays no runtime and
grants no admission. Q12 remains partial; Q11 and broader Q13 remain open.

This sequence supersedes completed prerequisites in the older packet table.
[Head-bound proof642](../../../compat/api-acceptance/current-head-installed-subject-v1.json)
now proves128selected bindings/64criteria at `6d6b233`, zero missing/blocked.
The audit joins702committed inputs, including608runtime/build/license inputs
unchanged from tested99719f1. All14canonical files are restored; the original
107,624-byte frozen archive is reused. All eight mandatory observations and
review638 already exist. Admission, integration and public delivery remain open.

| Priority / IDs | Investigation and easiest closure path | Required result / stop rule |
| --- | --- | --- |
| 1 — FIX-04/06, TOOL-01 | Refresh existing CPU43530224577, Linux43530227494 and Metal43530230265 at6d6b233. Retained641poll4 has Linux success and CPU/Metal queued; workflow and job states can differ. Inspect the first failing job if any, preserving all attempts. | Original checkout identities, full run/job/attempt histories and all23required results pass the unchanged CI validator. Queue delay does not justify redispatch or native rebuild. |
| 2 — FIX-06, API-06, SHD-06 | Join proof642, eight-row dossier636/637, reviews609/621/638 and final CI. Inspect a failed field before rerunning tests. Keep Tk retention623 validation separate from the mandatory rows' scoped original-envelope audit. | Independently reviewed exact admission basis for32selected Tk rows/128bindings and eight mandatory rows. Preserve14frozen files, historical matrix, failed attempts and142original obligations. Stop at unresolved joins; do not weaken validators. |
| 3 — FIX-04/06 | Query current main/branch state, review the owned delta and integrate through the protected path, preserving the other owner's checkout/index. Decide whether source integration alone or a successor release is warranted. | Merged source matches admitted scope. If publishing, use successor versioned artifacts and verify delivered bytes; never replace existing Vulkan.2 assets. A source merge alone is not public wheel delivery. |
| 4 — API-05/06, SCI-05 | Reconcile U05/E03/E04/Q11–Q13/H03 in one public-route/value/evidence table in the existing checklist. Reuse current point/filter/scene passes and the historical Glue disposition before adding assertions. | Each selected route has exact source/wheel/profile, existing proof, smallest missing assertion, disposition and reopening trigger. Distinguish stale wording from real defects; reuse only matching inputs/scope. |
| 5 — LIF-01–06 | First delete a parent that still owns a live canvas, retaining a shared peer. Inspect Qt destruction callbacks and existing close fixtures. Then select zero-size/restore, one named acquisition failure and a supported loss injection, one at a time. | Bounded reproducer verifies callback count/order, submit behavior, peer pixels/recovery and final resource gauges. Fix only a demonstrated defect. Unavailable WSI injection stays explicit; readback does not prove physical surface loss. |
| 6 — SCI-02/03/04/06, API-06 | Extend the existing two-scene fixture with one camera mutation, then one required plane/depth/stencil interaction. Inventory filter compositions and V01–V09 volume protocols before selecting another small workflow. | Analytic/frozen-reference output before/after mutation, relevant refusal/recovery, exact installed artifact and finite limits. Reuse current wheels if runtime inputs match. A demonstrated failing route determines wrapper versus native changes. |
| 7 — SHD/STA/TEX/LIN; optional HOST/PLAT/PERF/TOOL | Expand renderer forms only for a named workflow above. Search once for the historical cleanup receipt. Other hosts, ABIs, GPU vendors and optimization require a concrete claim or measured bottleneck. | Named positive/boundary/recovery cases close only their selected subsets. Otherwise record an explicit boundary/deferral and reopening trigger. Optional hardware and full parity do not block the Windows/WSL milestone. |

Before each experiment, record its hypothesis, exact command, expected observable
result and bounded attempt/time/storage budget. Produce verified existing support,
a confirmed defect/regression, an explicit boundary or a deferred dependency.
Update both live checklists; keep broader parents open. Do not repeat exhausted
BUG-01/02 campaigns without a new recurrence or causal hypothesis.

Immediate next action is refreshing the same three CI handles and collecting
original evidence when complete. Source-only reconciliation may proceed while
CI queues without advancing its frozen branch head. Use registry613 and shared
20GiB scratch/10GiB reserve; size future Git budgets from the measured full index.
Reuse wheels, locked dependencies and SDKs. Retain actual exits/waits, failures,
sources/licenses and evidence; inspect/apply cleanup before the next writable
experiment. This planning refresh creates no scratch and launches no tests,
builds, CI, publication or cybersecurity work.

Packet3 source/CI checkpoint: [owned freeze639](../../../compat/api-acceptance/current-qualification-source-head-v1.json)
pushes109files/2,338,177bytes as `6d6b233`, with608runtime/build/license references
unchanged from tested99719and the other owner's index untouched. No native build.
[CI640](../../../compat/api-acceptance/current-head-ci-dispatch-v1.json) dispatches
23required jobs with original native reuse. Retained poll641: Linux43530227494
SUCCESS, CPU43530224577and Metal43530230265QUEUED. Re-poll those exact handles;
do not redispatch on queue delay. Local source/dispatch scratch is cleaned:
15,099,032bytes removed/289retained-input verifications. The8MiB private-index
estimate missed the15,098,948-byte full-tree index; the actual overrun is retained,
old preflight unchanged, and hygiene policy now requires measured full-index sizing.
Next: renew qualification-head metadata/proof against frozen6d6b233without replaying
unchanged runtime observations, collect complete23-job evidence, then exact matrix/
Tk admission and independent promotion/protected integration/delivery. Broader
API/lifecycle/science parents remain bounded open work, not silently closed.

Packet3 review checkpoint: [independent638pre-admission approval](../../../compat/api-acceptance/current-mandatory-peer-review-v1.json)
covers all8row bindings, locked fixture reuse, manual original-retention and finite
history scope, with no required changes. It rehashes1050inputs/945retained entries
and492fixture archive members (487RECORD payload hashes), verifies24gates and the
original functional outcomes, and independently searches current-wheel workers.
Its narrative/JSON limitations are retained: no subject624execution,623retention
rehash, rendering-native/member-list recomputation, original466JUnit comparison or
full logs/mounts/outside-root history audit. Receipt/discovery links and distinct
guest/coordinator registry identities remain explicit. No final admission/CI or
promotion approval is conferred. Cleanup removed89bytes/verified1062inputs.
Next: freeze/push only owned current source/metadata through a private Git index,
preserving the other owner's index and frozen preparations; run required23-job
CI with original Linux/Metal reuse. Then exact admission/promotion/protected
integration/delivery. No native rebuild for this metadata/test/doc integration.

Packet3 binding checkpoint: [current dossier636/history637](../../../compat/api-acceptance/current-mandatory-bindings-v1.json)
validates all8rows/24gates and945original managed cleanup input hashes. All15foreign
origins remain protected under registry613; the original-envelope manual audit
stays distinct from generic qualification-index retention acceptance. Fixture
archive492members and the two metadata-only wrapper label changes verify. Current
history has8strict passes and8separate discoveries, zero unattributed controllers
or later failures within the explicit two-root/cutoff/literal-key-prefilter scope.
The scan parsed304of16,910JSON files, avoiding repeated parsing/hashing of unrelated
historical records. Source-only schema/namespace setup failures634/635remain
retained; no verifier/runtime report changed and no scratch/build was created.
All14frozen preparation files remain unchanged. Next: independent cumulative
row/fixture-copy/retention review, owned final-head freeze and23-job CI, then exact
matrix/Tk admission and promotion/protected integration/delivery.

Packet3 observation milestone: [all8current mandatory rows](../../../compat/api-acceptance/mandatory-current-wheels-observations-v3.json)
now pass on exact current Windows/WSL wheels; the canonical matrix is unchanged.
Headless632/633each pass original95GPU cases, rendering checks,4096marker smoke and
36scientific cases in discovery and first strict replay,537installed-member/origin
checks and ten zero final gauges. Windows reuses only five locked fixture
distributions (492RECORD-verified files), with minimal source/license archive and
no whole environment copy or version refresh; only two stale wrapper provenance
labels change. WSL uses its original read-only headless dependency lower and
patched Mesa/private Xvfb. No native build. Both runs are cleaned:
161,779,696bytes/2141files removed,446retained inputs verified.
Next: assemble exact current eight-row admission bindings, review the cumulative
qualification/fixture-copy basis, freeze the owned final head and complete23-job
CI, then independent promotion/protected integration/delivery. Eight observations
do not themselves admit rows or close broader API/science/performance/hardware scope.

Packet3 Qt milestone: [all six Qt observations](../../../compat/api-acceptance/mandatory-current-qt-observations-v1.json)
now pass across Windows/WSL PyQt5, PyQt6 and PySide6 on the exact current wheels.
WSL629–631reuse separate original read-only dependency roots, patched Mesa9c5 and
private owned Xvfb; each passes seven QWidget stages/first strict replay,537member
and origin checks and ten zero gauges. Original tracked inputs rehash and mount/
process exit checks pass. Source-only setup failure629remains retained. Storage
policyv2clarifies matching roots with the same512MiB budget, preservingv1.
Cleanup removed277,768,283bytes/36files and verified305inputs; no native build or
environment/rootfs copy. Current mandatory observations are6/8. Next: verify the
retained offline headless/pytest dependencies, renew Windows and WSL headless,
then exact matrix admission and final-head CI/promotion/integration/delivery.
These observations do not close broader lifecycle/input or hardware scope.

Packet3 Windows Qt checkpoint: [all three binding observations](../../../compat/api-acceptance/mandatory-current-windows-qt-v1.json)
pass on exact current wheel6de6d77f with distinct locked PyQt5/PyQt6/PySide6
environments. New627/628each pass seven original QWidget stages and first strict
replay,537installed members/origins and ten zero gauges. Both consumers are cleaned:
248,752,405bytes/4341files removed,128retained inputs verified. Shared source archives
and offline dependency packages were reused; no native build. Current mandatory
observations are3/8. Next: WSL profile prerequisite/guest/backing checks and exact
binding renewals; verify retained offline pytest closure before Windows headless
renewal. Then exact mandatory admission, owned head freeze/23-job CI, independent
promotion basis, protected integration and delivery. Do not repeat passed bindings
without changed critical inputs; broader lifecycle/input parents remain open.

Packet3 observation checkpoint: [audit625](../../../compat/api-acceptance/mandatory-current-gap-audit-v1.json)
finds all8historical mandatory rows tied to older wheels; none transfers to current
native cleanup/Qt-wrapper inputs. [Windows PyQt6 row626](../../../compat/api-acceptance/mandatory-current-windows-pyqt6-v1.json)
now passes seven original plain-QWidget stages and its first strict replay on
current wheel6de6d77f, with537members/installed origins and ten zero final gauges.
Locked dependencies were reused offline; no native build. Its pre-runtime generator
failure is preserved. Cleanup reclaimed129,750,985bytes/verified66inputs.
Current mandatory observations are1/8; remaining seven rows, admission, final-head
CI, promotion review, protected integration and delivery remain next. Renew the
other Windows binding rows with their original locked closures, then WSL profiles;
headless renewal additionally needs the retained functional/pytest closure verified
offline before execution. Do not repeat the PyQt6 row without changed inputs.

Packet2 proof checkpoint: [subject624](../../../compat/api-acceptance/preparation10-installed-subject-v1.json)
proves128selected criterion/profile bindings (64distinct criteria), zero missing or
blocked joins, using the unchanged subject validator. All14canonical preparation
files are restored. [Independent failure dispositions621](../../../compat/api-acceptance/preparation10-failure-dispositions-v1.json)
bind both original Windows UNVERIFIED attempts without relabeling them. Reviewer
limitations and the corrected separate discovery index are retained;620is unchanged.
[Contributing retention623](../../../compat/api-acceptance/preparation10-proof-retention-v1.json)
validates791inputs. The failed622post-cleanup namespace validation is preserved:
its additional external baseline remains pinned, and is excluded only from the new
selected-root manifest. Both actual cleanup events passed; no verifier changed.
Runs621–623 cleaned274bytes/1646input verifications;624created no scratch.
Next is packet3: mandatory-eight-row renewal/admission, owned final-head freeze,
23-job CI, independent exact promotion basis, protected integration and delivery.
This does not close the142original obligations or broader feature parents.

Packet2 history checkpoint: [run620 exact history drafts](../../../compat/api-acceptance/preparation10-attempt-history-drafts-v1.json)
scan16,617retained JSON files and identify6exact-profile replay attempts with zero
unattributed current-wheel reports. Windows retains two UNVERIFIED replays and
two later passes; WSL has two first-replay passes. Complete ordered histories and
four latest-workflow selections validate. Both failed-attempt dispositions still
need independent approval; contributing retention and subject proof remain next.
No reports were rewritten and no scratch/build/environment was created.

Packet2 progress: [current selected-row overlay619](../../../compat/api-acceptance/preparation10-installed-row-bindings-v1.json)
validates32rows/128criterion-profile bindings/96raw gate checks through the unchanged
inventory validator, with all14frozen preparation files/scope unchanged. The failed
618secondary-store receipt path remains retained; new source-local receipts meet
the existing validator's storage requirement. Neither run created scratch. Next:
complete exact attempt histories, independent failed-attempt resolutions and
contributing retention before subject proof/admission. All142original obligations
remain required and incomplete; no published-wheel or hardware coverage transfer.

Execution checkpoint: [packet1 completed in run617](../../../compat/api-acceptance/preparation10-wsl-criterion-phases-v1.json).
Both current installed WSL pytest nodes/all6phases pass and satisfy all16selected
Linux fixture rows. Installed members/origins, metadata/RECORD and ten zero final
gauges verify. The process exited0/was awaited; cleanup removed570files and
verified26retained inputs. No native build or strict environment/admission claim.
This supersedes the WSL-pytest pending sentence below. Packet2's exact joins are next.

- Runtime source is `99719f1`; current wheels are Windows `6de6d77f…` and Linux
  `b728b575…`. Both have local installed acceptance. Reuse these artifacts and
  their existing native producers unless an investigation changes critical inputs.
- Preparation10 scope `0b668996…` has approved source/scope/reuse bindings and
  passing prerequisite validators. Its finite scope is **64 distinct criteria /
  128 profile bindings**, while all142 original obligations remain required.
- [Windows strict observations](../../../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json)
  and [WSL strict observations](../../../compat/api-acceptance/preparation10-wsl-strict-cohort-v1.json)
  each validate16feature joins/48gate checks on those exact wheels. WSL uses
  patched Mesa software Vulkan, environment `423ba184…`; it is not physical
  Linux GPU coverage. Run616 exited0, its child was awaited, and managed cleanup
  passed with120retained inputs verified.
- [Windows genuine pytest phases](../../../compat/api-acceptance/preparation10-windows-criterion-phases-v1.json)
  pass the two selected nodes/all6phases. Equivalent current WSL pytest evidence
  is still missing. These separate pytest processes do not inherit strict
  observer environment fingerprints.
- Selected point/filter/scene observations exist; they do not close their broad
  API parents. New tests and evidence/docs still need owned integration.
- Current subject admission, eight mandatory profile rows, final-head23-job CI,
  protected integration and successor delivery remain open. The published
  Vulkan.2 qualification is historical and cannot be transferred.

### Ordered investigation packets

Finish and clean one packet before starting the next writable experiment.
Investigate existing support before implementing anything; classify each missing
claim as an evidence join, reproducible defect, intentional boundary or deferred
scope. A boundary disposition closes the investigation, not the capability.

| Order / coverage IDs | Smallest investigation and easiest path | Completion evidence / decision |
| --- | --- | --- |
| 1 — FIX-04/06, API-06, TOOL-01 | Reuse the exact Linux wheel, existing Python/test dependencies and patched driver. Run the two genuine Tk state/capture pytest nodes through the existing qualification runner. Check all setup/call/teardown phases and `passed_pytest` acceptance for the16selected Linux row fixtures. | Two cases/six phases pass,537installed members/origins verify, no source overlays, shutdown gauges zero; retain real failure phases if any. Record its own environment; do not reuse strict fingerprint423ba184. No native build. |
| 2 — FIX-04/06, API-06, SHD-06 | Use unchanged validators to join both platforms' strict observations, separate pytest receipts, exact wheel/profile/workflow identities, discovery/replay histories and contributing retention. Inspect the first missing join before rerunning a workflow. | Exact32selected rows/128criterion-profile bindings accounted for against64criteria; guarded subject proof/admission with exact review basis, or a named failed join and minimal correction. Preserve142original obligations and all failed attempts. Source approval alone is insufficient. |
| 3 — FIX-04/06, TOOL-01, PLAT-08 | Renew only missing/invalidated mandatory profile observations for the current wheels; inspect existing eight-row evidence before choosing reruns. Assemble the owned cumulative delta using a private Git index, freeze its final head and run the required23-job CI. Reuse original Linux/Metal producers where valid. | Eight mandatory rows have exact current qualification, final-head CI passes, independent promotion review names the exact basis, and protected integration/delivery checks pass. Any critical input change gets an impact assessment before reuse. Preserve the other owner's index and all licenses. |
| 4 — API-05/06, SCI-05 | Reconcile U05/E03/E04/Q11–Q13/H03 against existing tests and receipts. Build a compact route/value/evidence/disposition table in the live checklist; do not create another tracking system. Correct stale statements before adding tests. | Each selected route has exact artifact/profile scope, supported values, missing assertion or explicit boundary and reopening trigger. U05/filter passes and corrected historical Glue references must not be rerun merely because an old checklist says pending. |
| 5 — LIF-01–06 | Start with parent destruction while it still owns a canvas; moved-away-parent tests are insufficient. Next select zero-size/restore, a named acquisition failure, and a real supported loss/recovery injection. Investigate ignored native close/error callbacks from review609. Add only claimed Qt input routes that lack evidence. | Minimal before/after reproducer for each actual defect; callback order/counts, submit/no-submit behavior, observable pixels/refusal, shared-peer recovery where relevant and final resource retirement. Distinguish native WSI/readback, toolkit-generated/physical input and counters/physical memory. Unavailable injection stays explicit. |
| 6 — SCI-01–04/06, SHD-01–05, STA-01, TEX-01, LIN-01 | First extend the existing two-scene fixture with one camera mutation and one selected depth/stencil/plane interaction. Then inventory mesh-filter compositions beyond the four proved revisions. Inspect existing V01–V09 volume protocols before selecting one small mode/mutation workflow. Expand shader/texture/line forms only when those workflows require them. | Analytic/frozen-reference values or pixels, mutation, meaningful boundary/refusal and recovery on an exact installed wheel. Record finite mode/shape/format limits. Keep volume quality, large-data performance and broad renderer semantics separate; no automatic full inventory matrix. |
| 7 — HOST-03–06, PLAT-02/04/08, PERF-02–04, TOOL-02/03 | Pursue only a named application, distribution requirement, reproducible bottleneck or specific missing historical record. Search once for the historical cleanup receipt; a new cleanup cannot recreate it. | Rendered host acceptance for host claims, measured bottleneck for optimization, or an explicit deferral with trigger. Extra ABIs/drivers, optional compiler cache and hardware-dependent checks are not prerequisites for the selected first usable version. |

### Execution rules and finish line

For every selected child task, record its coverage ID, public route/values,
existing evidence, smallest missing assertion, exact source/wheel/profile,
reproducer command, expected result, outcome and next decision. Update both live
checklists in the same change. Never convert source/local passes into installed,
strict, merged or delivered claims without their own evidence.

Start with one bounded reproducer. Fix a demonstrated defect at the narrowest
route; fix evidence joins without renderer changes. Repeat or broaden tests only
for new changes, failures or unresolved concerns. BUG-01/02 campaigns stay closed
to repetition unless a new recurrence or causal hypothesis appears.

Use the shared D: hygiene root and current successor613 registry, register scratch
before writes and check guest plus Windows backing capacity for WSL. Reuse locked
dependencies, wheels, SDKs and original producers. Retain actual exits/waits,
failures, source/licenses and necessary evidence, then inspect/apply cleanup and
report it before the next experiment. Planning needs no build lease, clone or
environment. Keep AGPL and original BSD/dependency notices attached.

The first milestone is current qualification/integration (packets1–3). Remaining
selected feature investigations then close one by one; broad parents remain open
where only a subset is proved. Metal graphics stays experimental. Physical Linux
GPU, native Wayland, extra architectures/ABIs, cross-monitor/fractional DPI and
laboratory latency remain deferred unless explicitly selected. No cybersecurity
work is included.

## Earlier plan and execution checkpoints

## Revised investigation and closure order — 2026-11-13

This section is the active plan and supersedes older next-step descriptions below.
The target is a useful, explicitly supported VisPy Vulkan subset, with intentional
improvements allowed. Full VisPy/OpenGL parity is not an exit criterion.
This update is planning only; it does not execute tests or promote coverage.

Execution update after planning: [Windows current-wheel acceptance](../../../compat/api-acceptance/lifecycle-current-windows-installed-v1.json)
and [Linux current-wheel acceptance](../../../compat/api-acceptance/lifecycle-current-linux-installed-v1.json)
each pass26selected tests,56Tk baseline tests and composite recovery on source99719f1,
with537runtime members, installed origins, zero overlays and ten zero shutdown
gauges per process. Linux also verifies561archive members and566installer RECORD
entries. Runs593–595 are cleaned (47,766,619bytes;72retained-input verifications).
This completes packet1's local installed acceptance; strict qualification,
preparation10, review and integration stay open. Starting-point pending notes
below describe the state before these executed gates.

### Established starting point

Current Windows installed checkpoint: [strict cohort614](../../../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json)
passes both selected observer workflows in one fingerprintd664beb3 on wheel6de6d77f,
with16feature joins/48raw gate checks. [Genuine pytest phase615](../../../compat/api-acceptance/preparation10-windows-criterion-phases-v1.json)
passes the two selected nodes/all6phases and all16Windows row fixture checks.
It is a separate same-wheel test process with borrowed test dependencies, not
the strict observer fingerprint. All537runtime members/installed origins and
required shutdown gauges verify; no source overlays. A clean strict consumer
was needed because earlier targets were cleaned; existing base Python and
locked dependency wheels were reused offline under the new storage-only
strict-current-installed-v1 profile. No native build or existing-environment mutation.
Both receipt-extension histories stay retained. Runs614/615 cleaned80,802,081bytes
and verified95inputs. Next: current WSL matched strict observations and genuine
pytest phase, then subject/profile/history/retention bindings, all8mandatory
rows, required final-head CI and protected integration. No admission yet.

Latest reviewed checkpoint: [peer609 approves source/scope and both exact reuse edges](../../../compat/api-acceptance/preparation10-peer-review-v1.json)
at scope0b668996, independently confirming142original obligations,158baseline rows,
272prior files and64distinct criteria/128profile bindings. Its withheld computations
and unread files stay explicit. Coordinator separately reproduces the documented
execution-scope projection. [All full reviewed prerequisite gates now pass](../../../compat/api-acceptance/preparation10-approved-bindings-v1.json)
after retaining611's missing-map-reference refusal and612's source-local join refusal.
The latter needs one521,666-byte exact project-source snapshot at the unchanged
verifier's required source-local path. [Registry613](../../../compat/api-acceptance/preparation10-source-local-binding-v1.json)
preserves535's protections and adds both source origins/C: capacity; use it explicitly
for all subsequent managed operations. Runtime, candidate scope and reuse digests
are unchanged; no validator was relaxed and no native build occurred.

[282source reuse/qualification contracts pass](../../../compat/api-acceptance/preparation10-reuse-contracts-v1.json).
Runs609/610/613 cleaned8,945,534bytes/verified38inputs;611/612are source-only failures
with no scratch. Next: strict current installed profiles and required frozen-head
CI before protected integration. No artifact/strict-profile/release admission.
Of16selected features,14are bounded subsets and2wrapper features are additive new
scope (8criteria); no original parent is discharged. Low-priority review followups
remain outside these passes: a real ignored closeEvent/event-filter control,
fallback-close callback error control and hidden-resize/offscreen-render boundary.
Mesh tests assert positive/increasing pending draws;2→4and ten final zero gauges
are exact recorded observations/controller checks, not additional test assertions.

Current qualification checkpoint: [both Metal originals validate](../../../compat/api-acceptance/lifecycle-metal-current-originals-v1.json)
and whole run43495769632 succeeds; the current reuse pin is renewed before
[preparation10's scope freeze](../../../compat/api-acceptance/lifecycle-preparation10-wip-v1.json).
Scope0b668996 preserves272prior records/142original dispositions and64criteria
with128profile bindings. [Both native and both archive prerequisites validate](../../../compat/api-acceptance/lifecycle-preparation10-bindings-v1.json);
both actual review gates still refuse admission. Next: independent cumulative
source/scope/reuse review, strict profiles, final-head CI and protected integration.
No review/qualification transfers. Source-only runs607/608 create no scratch.

Science progress: [WSL pending-filter cases](../../../compat/api-acceptance/mesh-filter-pending-linux-v1.json)
match Windows's four actual-pending revisions and exact6,144analytic pixels;
[two current Windows scene references](../../../compat/api-acceptance/scene-state-current-windows-v1.json)
pass71,680pixels with max error0. Full filter inventory, camera mutation and
broader depth/stencil/plane/platform claims stay open. Runs604–606 cleaned
73,387,744bytes and verified221retained inputs. New test sources remain uncommitted.

Mesh-filter investigation executed: [four native-pending Windows cases](../../../compat/api-acceptance/mesh-filter-pending-windows-v1.json)
pass texture replacement/enabled, plane count+values and detach on exact wheel6de6d77f.
The new uncommitted test9ac765ab observes pending_draws2before mutation and4before
captures, with exact6,144analytic pixels and ten final zero gauges. Two initial
test setup failures (constructor format and unbound read target) are retained;
no renderer change was needed. Runs600–603 cleaned71,604,957bytes/101retained
input verifications. Next science work: the same selected WSL check and finite
E04 scene/camera/state interactions; full mesh-filter inventory remains open.

Latest executed reconciliation: [WSL U05 installed acceptance](../../../compat/api-acceptance/point-identity-current-linux-v1.json)
now matches Windows's ten unchanged tests/eight exact rendered cases on wheelb728b575
and patched Mesa9c5, including installed origins, metadata/RECORD and ten final zero
gauges. Run598 cleanup reclaimed30,007,097bytes/verified27inputs after waiting for
an unrelated process that reused the original awaited child's PID; refusal retained,
child identity and verifier unchanged. [H03 upstream disposition](../../../compat/api-acceptance/h03-upstream-disposition-v1.json)
also verifies the existing corrected Glue cache-invalidation admission and20reference
members; original failure remains failed. This source-only check created no scratch
and grants no current-wheel host qualification. E03/E04/Q11–Q13, broader scientific
workflow acceptance and current candidate qualification remain open.

Further executed progress: [Metal arm64 originals](../../../compat/api-acceptance/lifecycle-metal-arm64-original-v1.json)
validate current source/archive/native/installed CPU/producer cleanup without
changing the production reuse pin. The existing x86_64 job remains live; collect
its originals after success and require whole-run success before pin renewal.
While waiting, [U05 Windows installed acceptance](../../../compat/api-acceptance/point-identity-current-windows-v1.json)
passes eight unchanged rendered reference cases plus two controls on wheel6de6d77f,
with exact6,144pixels and ten zero final gauges. This resolves the stale
no-candidate description for that finite Windows subset; broader SCI-01 and
current WSL point acceptance remain open. Runs596/597 are cleaned, reclaiming
41,646,492bytes and verifying137retained inputs. No native rebuild or admission.

- Corrected source is pushed at `99719f1f7bdbb320318cf1ccd0eed39f336c7cce`.
  CI selectors now name preparation10; preparation10 must be materialized and
  reviewed before dispatching its CPU/Linux reuse workflows.
- Current source has57CPU,26Windows and26WSL selected passes. These observations
  are limited to their recorded source, profiles and modes.
- [Current candidate archives](../../../compat/api-acceptance/lifecycle-qt-repackage-v1.json)
  contain the corrected Qt member: Windows `6de6d77f…`, Linux
  `b728b575…`. Native payloads, licenses and tags are reused unchanged.
  Installed acceptance for these exact archives is still pending.
- Review588 requires changes; corrected source has no transferred approval.
  Preparation9 and previous installed results remain historical at their own hashes.
- Metal run43495769632 was last recorded in progress. Query that same run;
  a saved status is not a live completion claim. Only build/CPU acceptance is
  intended; physical Metal graphics remain experimental.
- Run593 has a successful awaited process and retained terminal record, but no
  cleanup result was present at this planning inspection. Resolve its lease and
  cleanup before the next experiment. Do not infer cleanup from process success.

### Ordered work packets

| Order / IDs | Investigation and cheapest path | Evidence and exit gate |
| --- | --- | --- |
| 1. Finish current candidate — FIX-04/06, API-05/06, LIF-01–04, SCI-06 | First finish run593 cleanup. Install each current wheel once in registered scratch, using existing dependencies. Run26selected cases and56Tk baseline cases plus composite recovery in separate processes against that same installation. Windows uses its recorded Vulkan profile; WSL uses the exact patched Mesa profile. Reuse native560/Linux572; no native rebuild for Qt Python changes. | Verify installed file hashes/origins, zero source overrides, exact profile and zero shutdown gauges. Preserve failures separately, including the existing system-Mesa MSAA failure. Do not borrow prior-wheel acceptance. |
| 2. Finish provenance, review and integration — FIX-04/06, SHD-06, PLAT-08, TOOL-01 | Collect the existing Metal run's original results and cleanup evidence. Renew its reuse pin before freezing preparation10 tool/scope hashes. Materialize preparation10 and native/archive bindings once. Obtain follow-up review of corrections, all relevant failures including577, coverage, execution and ledger records. | Independently account for128selected criteria,142original obligations and unchanged historical records; approval must name exact scope/reuse digests. Complete required23-job head CI, affected strict installed profiles and protected integration. Keep the published Vulkan.2 release unchanged until a separately qualified successor is ready. |
| 3. Reconcile remaining routes — API-05/06, SCI-05, TOOL-03 | Create a small route-to-evidence table from the existing inventory. Start with U05, E03, E04, Q11–Q13 and H03. Check source, values, expected output and artifact/profile identity before writing code. Search for the missing historical cleanup receipt once; never recreate an event from newer cleanup evidence. | Each selected route is verified existing support, a reproducible defect, an intentional unsupported boundary or deferred with a reopening trigger. Stale fixture disposition does not erase its original failure or close a whole API parent. |
| 4. Lifecycle reliability — LIF-01–07 | Begin with destruction of a parent still owning a canvas; current moved-away-parent tests do not cover it. Then examine explicit zero-size/restore, one named acquisition failure and actual loss/recovery through existing injection hooks. Add selected Qt keyboard/wheel/focus/mouse/timer/coordinate checks only where a claimed route lacks evidence. | For each transition require callback order/counts, observable rendering or expected refusal, submit behavior, shared-peer recovery where relevant and resource retirement. Separate readback from native WSI and toolkit-generated from physical input. Unsupported/unavailable loss paths remain open. |
| 5. Scientific workflows — SCI-01–04/06 | Select one small indexed/instanced point workflow, one mesh-filter composition, one3D scene/camera interaction and one bounded volume mode. Exercise existing routes first; correct the narrow public wrapper before changing the renderer. Reuse the eight stencil-route cases rather than treating upstream stock failures as eight new Vulkan defects. | Each selected workflow has meaningful reference values/pixels, mutation, boundary/failure and recovery checks on an exact installed wheel. Volume quality, large-data performance and general mode support remain separate claims. |
| 6. Rendering dependencies — SHD-01–06, STA-01, TEX-01, LIN-01 | Expand only forms required by the selected scientific workflow. Investigate sampler/array shape and indexing, attribute/divisor updates, state and typed-texture boundaries, then line chunk/endpoint ordering. For geometry consumers prefer existing compute/instanced expansion or an explicit application rewrite. | Each added form needs a positive case, a meaningful boundary/refusal and recovery. Preserve derivative/uniformity, binding/resource-limit and unsupported raster semantics. The patched-driver profile must remain distinct from failing system Mesa. |
| 7. Optional breadth — HOST-03–06, PLAT-02/08, PERF-02–04, TOOL-02 | Select only when a named application, required distribution or measured bottleneck needs it. Reuse existing host environments and artifacts. Measure before optimizing or adding compiler caches. | Rendered application acceptance is required for host claims; import success is insufficient. Additional ABIs/drivers require their own installed qualification. Otherwise leave these items explicitly unselected. |

### Investigation contract and stop rules

For each selected child task, record: stable coverage ID; exact public route and
supported values; current evidence; smallest missing assertion; source/wheel/profile;
reproducer command; expected output and cleanup; outcome; next action/reopening trigger.
Use the existing live checklist rather than introducing another coverage database.

Start with one minimal reproducer and existing tests. A demonstrated defect gets a
focused before/after regression; an evidence mismatch gets a corrected join, not a
renderer rewrite. If no defect reproduces, record the bounded result and choose the
next task. BUG-01/02 campaigns are exhausted: reopen only on new recurrence or a
specific new causal hypothesis; recurrence in a release profile follows D33.

Complete and clean one packet before creating the next writable experiment.
Read the hygiene policy, use the shared coordinator root/budget and mandatory
registry, register unique scratch, retain source/licenses/failures/actual exits and
child waits, then inspect/apply the exact cleanup plan and report its result.
Never move identity-pinned origins or retry automatic-review-rejected cleanup.
Documentation and small source checks do not justify a new wheel, SDK or environment.

Update affected IDs in both live checklists in the same implementation/verification
change. Keep source-tested, installed-qualified, merged and delivered states distinct.
A disposition closes the investigation task, not an unsupported capability.

Physical Linux GPUs, physical Metal graphics, native Wayland, additional architectures/
ABIs, fractional/cross-monitor DPI, laboratory latency and full parity remain deferred
unless explicitly selected later. No cybersecurity work is included.

## Active investigation queue — 2026-11-13

Latest executed gates (supersede pending descriptions below):

- [x] [Independent review588 completed with CHANGES_REQUIRED](../../../compat/api-acceptance/lifecycle-cumulative-review-required-v1.json);
  preparation9/current reuse digests remain unapproved.
- [x] Hidden native QWidget accepted close now reaches Canvas cleanup; state
  changes reconfigure without duplicate user resize events. [57CPU checks pass](../../../compat/api-acceptance/qt-close-state-review-source-v1.json)
  after three before regressions and a retained intermediate refactor abort.
- [x] [26Windows](../../../compat/api-acceptance/qt-close-state-windows-source-v1.json)
  and [26WSL source cases](../../../compat/api-acceptance/qt-close-state-wsl-source-v1.json)
  pass with existing native modules. Mode-declared hidden close is separate
  from programmatic DELETE retirement; layout refusal cleans up; integer0 and
  legacy NumPyTrue controls are covered. No broad WSI/embedding/binding claim.
  Runs588–591 cleaned:37,687,548bytes,59retained-file rehashes.
- [ ] Apply next-revision CI selectors BEFORE computing preparation tool/scope/
  reuse digests. Freeze/push corrected Python source, repackage existing native
  outputs, renew preparation/installed checks and obtain follow-up review of
  unread conservation/scope records. Old preparation9/wheel passes remain at
  sourcef93d80b; no approvals transfer.

- [x] [Current preparation9 native proof bindings](../../../compat/api-acceptance/lifecycle-producer-bindings-wip-v1.json)
  revalidate Windows560/Linux43471568101; real review gates remain closed.
- [x] [Current auditwheel verdict and Linux archive prerequisite](../../../compat/api-acceptance/lifecycle-linux-manylinux-archive-v1.json)
  pass, changing only WHEEL/RECORD to the required manylinux_2_39 tag.
- [x] Exact wheel30a40dcb [passes21selected+56baseline cases and composite recovery](../../../compat/api-acceptance/lifecycle-linux-manylinux-installed-v1.json)
  on one matched patched-Mesa installed target, with537runtime members,
  561archive members excluding installer RECORD,566installer RECORD entries,
  zero overlays and ten zero gauges per process. SystemMesa failure stays failed.
  Runs585–587 cleaned:52,668,442bytes reclaimed,69retained-file rehashes.
- [ ] Cumulative independent source/scope/native-reuse review; current CI
  selection and required head checks; strict qualification/profile bindings and
  protected integration. No approval, admission or delivery is inferred above.

- [x] Fresh baseline Tk observations on both current installed wheels:56tests
  and composite recovery pass on Windows and the existing exact patched Mesa
  Linux profile, with537members,zero overlays and zero shutdown gauges.
  SystemMesa25.2.8 remains failed at one MSAA capture case; do not collapse
  its55passes/1failure with the patched-driver result.
- [x] [Unreviewed preparation9 validates](../../../compat/api-acceptance/lifecycle-preparation9-wip-v1.json),
  with fresh runtime/tool/profile bindings,128selected criteria and142original
  obligations preserved;260historical records unchanged. No approval transfers.
  Runs580–584 cleaned:105,929,160bytes reclaimed,95retained-file rehashes.
- [ ] Build exact current native/archive reuse records; obtain cumulative
  independent review, then update explicit CI selection and run required head
  checks before protected integration. CI still selects8; preparation9 is local
  and NOT_QUALIFIED, not a release or formal installed-profile admission.

- [x] [Linux candidate8a793196 passes21selected installed cases](../../../compat/api-acceptance/lifecycle-linux-installed-selected-v1.json)
  at sourcef93d80b:537members,57loaded origins,zero source overlays and ten zero
  shutdown gauges. Only the wrapper Python member changed; verified native
  output, metadata and notices reused. Run579 is cleaned (29,081,532bytes),
  with26retained inputs rehashed. Initial zero-delete live-PID refusal and its
  successful unchanged-plan follow-up are preserved.
- [ ] Renew current candidate/tool/source bindings and cumulative independent
  review; execute affected required final-head CI and protected integration.
  Exact local installed passes do not supply formal qualification or delivery.

- [x] [Owned sourcef93d80b pushed](../../../compat/api-acceptance/lifecycle-owned-source-head-v1.json)
  on the existing WIP branch with the other-owner index untouched.
- [x] [21 selected Windows installed tests pass](../../../compat/api-acceptance/lifecycle-windows-installed-selected-v1.json)
  on exact candidate977357ad:537package members,58loaded origins,zero source
  overrides and ten zero gauges. The first native-mode controller mismatch
  remains failed; the same wheel passes explicit readback. No native rebuild.
  Runs576–578 are cleaned;75,535,236 bytes reclaimed and184retained-file rehashes.
- [ ] Linux audited pure-member repackaging and selected installed acceptance;
  candidate reviews, required final-head CI and protected integration. Local
  installed acceptance does not confer strict profile or release admission.

- [x] Review's minor workflow-test coupling fixed using pinned data;90contracts pass.
- [x] SCI-06's eight historical failure routes investigated: [eight Windows cases](../../../compat/api-acceptance/stencil-public-routes-source-v1.json)
  and [eight WSL source cases](../../../compat/api-acceptance/stencil-public-routes-wsl-source-v1.json)
  pass exact public-wrapper capture/mutation or explicit raw-refusal/recovery,
  with all nine zero shutdown gauges in each case. No renderer change/rebuild.
  [Disposition](../../stencil-wrapper-disposition.md) preserves original stock
  failures and leaves installed acceptance open. Runs574/575 are cleaned,
  reclaiming45,498,943 bytes and rehashing30 retained inputs.

- [x] 90 source contracts and the real review/identity refusal controls pass;
  [exact source scope](../../../compat/api-acceptance/linux-protocol-contracts-source-v1.json).
- [x] [Independent bounded protocol review](../../../compat/api-acceptance/linux-protocol-peer-source-v1.json)
  permits original capture validation. Non-blocking follow-up: construct the
  historical workflow test from pinned data instead of the live workflow.
- [x] [Original Linux native capture and wheel archive validate](../../../compat/api-acceptance/linux-original-native-archive-v1.json)
  at head82ee, without rewriting run568. Current Python wrapper is explicitly
  different from the original wheel; no admission is conferred.
- [x] [All13 selected WSL source cases pass](../../../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json)
  on PyQt6 xcb/WSLg readback and Mesa25.2.8 software Vulkan, using the verified
  native payload: four lifecycle cases plus nine numeric-zero clear cases.
- [x] Runs570–573 retention/cleanup completes; 32,221,412 bytes reclaimed,
  47 retained-file rehash checks, no managed scratch remains.
- [ ] Minor review follow-up, cumulative owned-source integration and installed
  successor qualification. Broader public-wrapper, lifecycle, scientific and
  rendering investigations below remain open, with the same deferred boundaries.

This section supersedes the execution order and pending-work descriptions in
the historical checkpoints below. The user requested an investigation plan;
this update makes no implementation, artifact-admission or release claim.
The objective is useful, bounded VisPy compatibility with explicit differences,
not full API or pixel parity. Work sequentially through the gates below; do not
start parallel native builds or another startup campaign.

### 1. Finish the current provenance investigation

Affected IDs: API-05/06, LIF-01–04 and qualification tooling.

Current source gate: [90 contracts pass](../../../compat/api-acceptance/linux-protocol-contracts-source-v1.json).
The existing minimal synthetic candidate fixture executes the real full candidate
validator and native review-before-capture route, with a separate changed-tool
identity refusal. This avoids a historical source snapshot. Run570 is cleaned;
independent protocol review and original artifact validation remain pending.

Follow-up: [88 contracts pass, one remains failed](../../../compat/api-acceptance/linux-protocol-contracts-wip-v1.json).
The workflow fixture CI identity is corrected; historical candidate/source/tool
scope is the remaining fixture problem. The earlier 87/2 checkpoint below is
preserved as history, not the current test result. Review/admission remain pending.
Run569 retention/cleanup completed with 16,886,403 bytes reclaimed and 13 retained
files rehashed; the earlier pending-cleanup checkpoint below is historical.

- [ ] Reconcile the exact WIP before another experiment: branch head `82ee789e…`
  contains the lifecycle implementation; the layout test, numeric-zero wrapper
  correction and protocol-support WIP are later local changes. Record their
  exact file hashes separately from the CI wheel's Python members.
- [ ] Inspect the two retained contract failures in
  `D:/vispy-vulkan-managed/build/runs/linux-protocol-source-569/after.log`.
  The suite currently has 87 passes and two failures; protocol support is not
  yet verified. The positive fixture changes workflow bytes without renewing
  its CI identity hash. The real review-gate fixture uses an old candidate
  against changed live source/tools and therefore fails before the intended
  review gate. Neither failure establishes a renderer defect.
- [ ] Correct fixture identities, using a minimal immutable historical source
  view for the historical candidate if needed. Do not weaken production
  identity checks, skip a refusal test or accept arbitrary workflow revisions.
  Preserve before/after receipts and the original run568 protocol refusal.
- [ ] Require positive historical/current exact-protocol controls, unknown
  protocol rejection, identity-tampering rejection and actual unreviewed
  candidate refusal before capture. Obtain independent review of the bounded
  workflow-authority change before consuming it as admission evidence.
- [ ] Validate the original retained CI capture and archive from run568 using
  a new report, without rewriting the original failed report. Check source,
  production, native outputs, wheel members and license joins. Require the
  known Python-wrapper delta to be explicit; current local Python source is
  not the Python source packaged by head82ee.
- [ ] Finish run569 retention and managed cleanup before the next experiment.
  Its source-test scratch remains pending cleanup at this planning checkpoint;
  earlier claims that all scratch is clean predate this run.

Exit: both contract failures resolved for the intended reasons, review recorded,
and the exact retained Linux native artifact verified. A green hosted build by
itself does not satisfy this gate. Reuse CI43471568101; no native rebuild.

### 2. Verify the existing fixes on WSL

Affected IDs: API-05/06, LIF-01–04, SCI-06.

- [ ] Reuse the existing WSL Python/PyQt6 environment and the verified CI native
  payload with both submission-layer sidecars. Check guest/backing-volume health
  and storage budget; register one bounded run. Use direct pytest logging to
  avoid the already-diagnosed DrvFs capture failure.
- [ ] Run the four selected lifecycle cases: minimize/restore with no submission
  while minimized; native close with a live shared peer; pending peer snapshot
  after parsed DELETE; and actual layout reparent/WinIdChange.
- [ ] Run the nine numeric-zero/flag/refusal/recovery clear cases against the
  current source wrapper. Verify expected color/depth/stencil values and all
  nine shutdown gauges where required by the fixture.
- [ ] Classify any failure as environment/fixture, public Python route, native
  runtime or unsupported profile before editing implementation. Preserve the
  first useful reproducer; do not rerun unchanged failures indefinitely.

Exit: exact source/artifact/profile receipts for the selected cases, or a
reproduced bounded failure with a next action. WSL software Vulkan remains
distinct from physical Linux GPU coverage and installed-wheel acceptance.

### 3. Investigate the remaining public-route gaps

Use existing tests and retained evidence first; select the smallest useful
case before adding implementation. Each investigation ends as verified support,
confirmed defect, stale evidence, explicit unsupported boundary or deferred work.

| Order / IDs | First investigation | Completion evidence |
| --- | --- | --- |
| A — SCI-06, API-05/06 | Recover the eight historical stock wrapper/facade failures; map each public call and expected value to its actual route. Separate upstream limitations from Vulkan regressions. Numeric-zero acceptance does not settle these eight cases. | Per-case disposition; for confirmed defects, a failing public-route regression followed by a passing fix and failure/recovery control. |
| B — SCI-05, TOOL-03 | Reconcile U05, E03, E04, Q11–Q13 and H03 against newer exact-scope evidence. Search for the historical compiler-cache cleanup receipt once; if absent, retain an explicit missing-record disposition. | Evidence links and scope for every selected stale item; no recreated claim of a past cleanup event. |
| C — LIF-01–06 | Audit untested zero-size, embedded-parent destruction, actual surface loss, fault acquisition, MSAA depth/stencil and Qt input paths. Choose one real application transition at a time. | Observable rendering/event behavior, expected submission or refusal, recovery and resource retirement. Mocked loss is identified separately from actual loss. |
| D — SCI-01–04 | Select one small point, mesh-filter, camera/depth and volume workflow from the inventory. Reuse current tests before inventing a new harness. | Meaningful expected output and mutation/recovery for the named subset; performance/quality claims separately measured. |
| E — SHD-06, STA-01, TEX-01, LIN-01, SHD-01–05 | Resolve the Mesa clipping evidence join first; then investigate only rendering forms required by selected workflows. Document supported types/limits and application rewrites where appropriate. | Exact installed-profile join or focused positive/boundary/refusal/recovery cases; no general raster or shader-equivalence claim. |

### 4. Qualify and integrate one bounded change set

- [ ] Review the cumulative owned delta and selected scope after source gates
  pass. Preserve the publication checkout's other-owner index and edits.
- [ ] Reuse verified native outputs when inputs match. Package current Python
  changes once; renew candidate/tool identities and reviews without changing
  frozen historical records. Do not create a native build for Python/doc edits.
- [ ] Verify exact installed Windows/WSL wheel members with zero source overrides,
  then run affected lifecycle/public-route acceptance and required CI on the
  frozen integration head. Source passes cannot substitute for this check.
- [ ] Update affected live checklist IDs in the same change, retaining partial,
  failed, installed and delivered scopes separately. Merge through the existing
  protected path; publish only a concrete qualified successor when warranted.
- [ ] Retain reconstruction inputs, AGPL/original BSD/dependency notices and
  actual process exits; inspect/apply cleanup plans and report reclaimed bytes.

Exit: selected claims match merged source and, if published, delivered bytes.
Unselected parents remain open; the known-good Vulkan.2 release stays distinct.

### Stop rules and deferred scope

BUG-01/02 retain their exhausted diagnostic history. Reopen only for a new
recurrence or a specific new hypothesis with a predeclared bounded experiment;
the older first-startup packet below is not authorization to repeat it now.
Optional hosts, ABIs, performance/cache work and broader shader forms need a
concrete use case or measured bottleneck before entering this queue. Metal
graphics remains experimental; physical Linux GPU, native Wayland, fractional
DPI and laboratory latency retain their documented boundaries. No new hardware
is assumed. A failed gate stops promotion, not unrelated read-only diagnosis.

## Historical execution checkpoints

Latest Linux status, 2026-11-13: CI43471568101 passed; all166original members
were retained and artifact digest checked. The unchanged native verifier refuses
current workflow authority `7fc072af…`. [Exact comparison](../../../compat/api-acceptance/qt-linux-protocol-equivalence-v1.json)
proves that only a candidate8selector in the inactive reuse arm changed; fresh
code is byte-identical. Next: review/support exactly this authority while
preserving unknown-protocol rejection and the original refusal; validate the
retained capture, then WSL-test lifecycle/reparent/numeric-zero cases. Do not
rerun native production. No Linux runtime/installed claim is made yet.

SCI-06 / API-06 progress, 2026-11-13: [numeric-zero clear semantics](../../../compat/api-acceptance/gloo-clear-zero-source-v1.json)
now have9rendered Windows source passes after5failures/4controls, using
unchanged tests/native payload. The separate Python wrapper correction keeps
False/None behavior and validates failure/recovery; no native rebuild or
installed claim. The original8upstream-wrapper failures remain open. Add this
case to WSL verification of the completed native artifact and the next source
integration; the running CI head remains immutable.

LIF-02 source progress, 2026-11-13: one [active Windows readback layout case](../../../compat/api-acceptance/qt-layout-reparent-source-v1.json)
passes two parent moves, deletion of the old parents, real WinIdChange,
continued rendering and nine zero shutdown gauges. Renderer/native inputs are
unchanged; only the new Python test was added. Two fixture-order failures were
diagnosed and retained; all scratch was cleaned. Linux and installed coverage,
native WSI loss and deleting a parent still owning a live canvas stay open.

Latest execution checkpoint, 2026-11-13: the native cleanup patch is compiled
and passes44original native CTests plus all three [Windows Vulkan source lifecycle cases](../../../compat/api-acceptance/qt-lifecycle-windows-native-v1.json).
Both shared-close cases have all nine zero shutdown gauges; SDK was reused
and294,738,856scratch bytes removed. Next: changed Linux native verification,
then successor installed qualification/integration. Earlier checkpoint details
below retain their original scope; current source is not a published wheel.

The19owned changes are now pushed on `wip/qt-lifecycle-native-562` at
`82ee789e0fc096e88f7b37537889a2b2407941ef`; [Linux fresh CI43471568101](../../../compat/api-acceptance/qt-lifecycle-source-ci-v1.json)
is active. Reuse its actual completed artifact for WSL verification; poll the
same run rather than restarting a live build. Source and private-index cleanup
are retained; no PR merge, installed qualification or new release is claimed.

Date: 2026-11-13. Status: in progress. LIF-03 has a source-tested window-state
fix ([CPU evidence](../../../compat/api-acceptance/qt-window-state-source-v1.json))
and finite [Windows Vulkan source verification](../../../compat/api-acceptance/qt-window-state-windows-source-v1.json).
[WSL software Vulkan source verification](../../../compat/api-acceptance/qt-window-state-wsl-source-v1.json)
also passes the same finite case. Broader zero-size/resource cases and installed qualification remain pending. Startup
history confirms the prior diagnostic budget is exhausted; no new hypothesis
or recurrence justifies repeating it. BUG-01/02 stay open.

Native QWidget close and Dawn sharing now have [50 cumulative source CPU passes](../../../compat/api-acceptance/qt-lifecycle-source-followup-v1.json).
Windows shared-peer rendering passes, but mandatory final buffer accounting
exposes a pending-DELETE lifetime defect (run557). The native cleanup patch is
uncompiled and under independent read-only review. Next: reuse the existing
Windows SDK under the versioned768MiB leaf profile, build/verify the changed
native leaf and rerun both finite lifecycle cases before packaging. Keep all
nine shutdown gauges; do not transfer old installed/release qualification.

Review follow-up now has [53 cumulative CPU passes](../../../compat/api-acceptance/qt-lifecycle-review-followup-v1.json).
Native cleanup bytes match the reviewed patch. First-show state and initial
resize defer until initialize; original callback-error identity is covered.
The required pending-peer-snapshot GPU control is authored but unexecuted.
Next native producer may reuse `dynamic-sampler-native-402/produce.py` as source,
with a new run/owner, exact current runtime-input hashes, and the explicit
successor hygiene registry; do not rerun old frozen drivers. Use
`compat/build-profiles/windows-native-secondary-v1.json`, original SDK in place,
all44original CTests and three GPU cases (minimize plus both close cases).
Only `cpp/runtime.cpp` differs from the prior native production inputs; do not
rebuild the SDK. Retain source delta and reference existing source archives.

The practical Vulkan.2 release is complete. PR76 merged as
`7c7a39f6bc341abb6b3ee6d417843892b0e29e8f`; the final merge audit passed.
This plan follows that release and preserves its finite claims. It does not
require full VisPy parity, new hardware, or renewed optional host support.

The [live coverage checklist](../../coverage-checklist.md) owns coverage status.
The [remaining checklist](../../remaining-gaps-checklist.md) owns gap IDs.
Historical records and the original 142 obligations remain intact. Those
obligations are an inventory, not a count of confirmed defects.

## Closure rules

For each ID, record one of these outcomes with exact evidence:

1. **Verified existing support:** reuse evidence only when source, artifact,
   inputs, environment and acceptance scope match. Reconcile stale records.
2. **Implemented and source-tested:** a confirmed missing behavior has a focused
   fix and meaningful regression checks; installed qualification stays pending.
3. **Installed-qualified:** the selected behavior passes on an identified
   artifact/profile, including ordinary use, mutation, failure and recovery
   where applicable. This does not imply public delivery.
4. **Explicit unsupported boundary:** document the restriction, useful error and
   recovery behavior. This closes a disposition task, not the capability gap.
5. **Deferred or externally blocked:** name the missing dependency or decision
   and the reopening trigger; leave capability coverage open.

Every completed unit updates affected coverage IDs in the same change with
date, command, actual exit/wait, source/artifact hashes, profile and evidence
link. A parent remains partial until all its selected children have a recorded
outcome. No non-recurrence result establishes the cause of an intermittent bug.

## Execution order and acceptance

| Phase | IDs | Investigation and easiest justified path | Exit condition |
| --- | --- | --- | --- |
| 0. Reconcile the queue | API-05, API-06, SCI-05, TOOL-03; all open parents | Build a compact table of public route, existing tests/evidence, missing assertion and proposed outcome. Start with stale fixture IDs U05, E03, E04, Q11–Q13 and H03. Reference retained inputs; do not copy their histories. | Each open ID has a next action and classification. Evidence-only closures cite exact matching inputs. Missing historical cleanup evidence remains missing unless found. |
| 1. Startup reliability | BUG-01, BUG-02 | Read `docs/threedee-startup-diagnosis.md` and original failures first. Reuse the approved external watcher; compare a minimal VisPy launch with the relevant host launch. Keep the qualification stall, development thread-pool loss and PyQt5 OLE hang as separate cases until evidence links them. | A recurrence has a minimal reproducer and targeted before/after regression, or a bounded non-recurrence report leaves the bug explicitly unresolved. |
| 2. Window and input reliability | LIF-01–LIF-07 | Use existing selected Windows/WSL consumers. Exercise one lifecycle transition at a time: zero/minimize/restore, close in flight, surface loss/recovery, then reparenting and input. Reuse proven capture/resource gauges; expand assertions rather than rebuild the harness. | Each selected transition has observable output, expected submit behavior and resource retirement. Unsupported events and untested hardware cases stay explicit. |
| 3. Scientific workflows | SCI-01–SCI-04, SCI-06 | Select small point, mesh, scene and volume examples that exercise missing combinations. Reconcile existing native stencil evidence with the public wrapper before changing native code. Fix the narrowest public route responsible. | Selected workflows have expected rendered values, mutation and recovery checks on exact artifacts; quality and performance claims remain separate. |
| 4. Rendering semantics | SHD-01–SHD-06, STA-01, TEX-01, LIN-01 | Start with the Mesa clipping evidence join, then line boundaries and texture/state cases needed by phase 3. Prefer explicit supported forms and diagnostics to wholesale emulation. Geometry consumers may use bounded compute/instanced expansion or a documented application rewrite. | Each selected form has a positive case, meaningful boundary/failure case and recovery check. No blanket shader or raster equivalence claim. |
| 5. Optional expansion | HOST-03–HOST-06, PLAT-02, PLAT-08, PERF-02–PERF-04, TOOL-02 | Select only for a concrete application, distribution or measured bottleneck. Renew host workflows on the actual successor artifact. Additional wheel ABIs need installed qualification. Optimize only after a reproducible measurement. | Claim-specific acceptance passes, or the item remains explicitly unselected. Import-only checks do not establish application support. |
| 6. Integrate and deliver selected changes | All changed IDs | Review the cumulative patch, run affected source/native checks, freeze inputs, qualify changed artifacts, use protected merge, then publish only if a new release is warranted. Preserve the known-good Vulkan.2 artifacts. | Changed claims match the merged source and delivered bytes; cleanup and failure records are retained. Documentation-only work creates no new wheel. |

Phases express dependencies, not a requirement to exhaust every possible form.
API reconciliation continues alongside each phase. Phase 1 produces a bounded
decision before phase 2 proceeds; an unreproduced optional-host bug must not
consume an indefinite experiment loop. A recurrence in a release profile follows
the existing D33 release-blocking rule.

## First investigation packet: startup and hangs

- [ ] Locate the original stall reports, watcher command, exact environment and
  startup timeout. Preserve their original identities and failed status.
- [ ] Write a compact case table: minimal VisPy, the historically implicated
  host, and PyQt5 OLE. Record binding, package versions, artifact and launch mode.
- [ ] Inspect startup ownership and the earlier thread-pool diagnosis; identify
  observable checkpoints before adding instrumentation. Use the existing
  out-of-process watcher; do not revive the previously crashing in-process one.
- [ ] Set the attempt count and wall-clock limit in the run manifest before
  launching. Initial budget: at most 10 launches per selected case, with a
  per-launch timeout taken from the retained protocol. Use a documented new
  timeout only if that protocol has none. Stop on the first useful recurrence.
- [ ] On a recurrence, retain elapsed checkpoints, child/process state and the
  smallest relevant logs. Terminate only owned processes after evidence capture.
  Derive a focused reproducer before proposing a fix.
- [ ] If no recurrence occurs, record the exact number and profiles tested,
  keep BUG-01/02 open and move to the next bounded task. Do not certify a cure.
- [ ] For a confirmed fix, demonstrate failure before and success after using
  the reproducer; add a targeted regression. Do not require the old private
  environment to become a permanent second installation.

## Per-area acceptance details

| IDs | Minimum selected acceptance |
| --- | --- |
| API-05/06 | Named public method/alias, implementation route, supported values, observable result and explicit unsupported values. Review imports separately from behavior. |
| LIF-01 | Named acquisition/fault point, useful error, clean shutdown and subsequent successful use; do not infer physical-memory accounting from Python object counts. |
| LIF-02 | Real layout reparenting and native-window change with correct surface ownership and shared-resource lifetime. |
| LIF-03/04 | Zero/minimized no-submit behavior, restoration, in-flight close and selected loss/recovery; observe retirement rather than rely on a screenshot. |
| LIF-05 | Selected color/depth/stencil formats and resolve behavior, including unsupported combinations. Existing color resolve is not general MSAA capture. |
| LIF-06/07 | Selected keyboard, wheel, focus, mouse, timer and coordinate events. Distinguish toolkit-generated from physical input and source prototype from shipped support. |
| SCI-01 | Indexed/instanced point source IDs, divisors, constant inputs and mutation ordering with expected pixels or equivalent meaningful rendered values. |
| SCI-02/03 | Named mesh-filter compositions and 3D camera/plane/depth/stencil/offset combinations, before and after mutation. |
| SCI-04/06 | Bounded volume data/mode and quality checks; independently exercise the public stencil wrapper. Record upstream baseline limitations. |
| SHD-01/02 | Selected sampler/array type, shape, indexing, update and cache/reflection behavior; binding limits and derivative/uniformity restrictions remain explicit. |
| SHD-03/04/05 | Selected attributes or geometry/line expansion with topology, interpolation, clipping and depth checks; reject unsupported semantics clearly. |
| SHD-06 | Bind the actual retained Mesa patch and original driver to the chosen installed profile; source driver success alone cannot admit that profile. |
| STA-01/TEX-01 | Named state combinations and texture layouts/types, boundary values and recovery; separate NaN/half/filter/comparison restrictions. |
| LIN-01 | Chunk boundary, endpoint carry, ordering and resource-limit cases with rendered acceptance. |
| HOST-03–06 | Named host version/binding and real rendered/mutation workflow; distinguish older Glue/napari evidence from successor qualification. |
| PLAT-02/08 | Exact ABI, architecture, GPU/driver and installed wheel. Existing CPU CI is not wheel availability or physical GPU coverage. |
| PERF-02–04/TOOL-02 | Reproducible baseline and changed result, selected workload, memory/storage cost, and a stated reason to keep an optimization/cache. |

## Boundaries that remain deferred

LIN-02 generated-line MSAA, LIF-08 cross-monitor/fractional DPI, PLAT-03 native
Linux physical GPUs, PLAT-04 Metal graphics and PLAT-05/06 Wayland/ARM/free-threaded
Python/ABI3 retain their existing boundaries. No available Mac, physical Linux
GPU or calibrated latency equipment is assumed. Record these as deferred,
unsupported or experimental as appropriate, not completed implementations.
Optional hosts and performance work do not become required by appearing here.

## Build, evidence and storage controls

Follow [build hygiene](../../build-hygiene.md) and `compat/build-hygiene.json`.
Use coordinator root `D:/vispy-vulkan-managed` and explicit successor registry
`D:/vispy-vulkan-managed/build/.hygiene/registry-mandatory-successor-535.json`.
All work shares the 20 GiB scratch limit and 10 GiB free-space reserve.

- Audit existing evidence first. Reuse matching wheels, locked environments,
  immutable sources and SDKs. No native rebuild for tests, docs or report edits.
- Before writable scratch or installed checks, register a unique bounded run;
  keep scratch only in `build/work/<run-id>`. Check WSL guest and backing-volume
  capacity before WSL builds. A budget refusal stops new allocations.
- Prefer existing source-only environments with bytecode and incidental test
  caches disabled. Never clone build/evidence/environment history into a run.
- Before a native rebuild, document changed native inputs and which existing
  artifact fails to match. Batch compatible native changes into one candidate;
  do not rebuild after each individual Python/test/doc edit.
- Await owned children. Retain source, command, exact exit, evidence, licenses
  and minimal failure reproducer outside scratch. Hash references to protected
  origins; never relocate them or alter frozen records.
- Generate, inspect and apply the managed cleanup plan after every terminal
  experiment; record reclaimed bytes and any refusal before starting the next.
  Load protected/blocked records and never retry rejected cleanup targets.
- Preserve other owners' edits and the publication checkout's dirty index.
  AGPL, original BSD and dependency notices remain attached.

## Progress reporting

Report confirmed defects fixed, evidence reconciled, newly qualified selected
cases, unresolved bugs and deferred boundaries separately. Use completed
selected tasks over selected tasks for this plan; do not present a percentage
of full VisPy compatibility. At each phase exit, identify the next smallest
useful task and whether it requires implementation, evidence or user scope.
