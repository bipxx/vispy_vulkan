# Remaining-gap investigation and closure plan

Latest execution checkpoint, 2026-11-13: the native cleanup patch is compiled
and passes44original native CTests plus all three [Windows Vulkan source lifecycle cases](../../../compat/api-acceptance/qt-lifecycle-windows-native-v1.json).
Both shared-close cases have all nine zero shutdown gauges; SDK was reused
and294,738,856scratch bytes removed. Next: changed Linux native verification,
then successor installed qualification/integration. Earlier checkpoint details
below retain their original scope; current source is not a published wheel.

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
