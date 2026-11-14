# Remaining gaps checklist

## Latest checkpoint — 2026-11-14

**Qt key-parent amendment reviewed, 2026-11-14:**
[786 independent review](../compat/api-acceptance/qt-key-parent-amendment-review-v1.json) approves the exact28-file source delta
`ca51efbd7cfed3bdfac674e62cb715dc7e706b5c5530bacd6dcf3f0a90a08105`
with conditions and no required changes. This is source-review approval only;
LIF-06/API-06 remain partial. Exact local-head tests before push, normal protected
integration and separate changed-artifact acceptance remain required. The review
recomputed no hashes and assessed only the evidence listed in its decision;
prior negative decisions and all withheld scope remain preserved. No current
head, CI, admission, published-wheel or full-parent coverage is claimed.

**Parent key replay fixed and verified at source scope, 2026-11-14:**
[780/781gap](../compat/api-acceptance/qt-key-parent-replay-gap-v1.json) records a second CHANGES_REQUIRED
verdict and empirical405fregression:1key causes2callbacks/2hook reports through
oneparentforward. No approval is transferred. Revised `1c68488e` leaves native
acceptedstate unchanged after a workinghosthook; private_keyEvent delegates to
guarded delivery and consumes suspended-key replay instead of bypassing safety.
[782Windows](../compat/api-acceptance/qt-input-callback-windows-source-v4.json)/
[783WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v4.json) each pass93CPUcases:47input,
including12keypress/release xcanvas/privateparent xdefault/host/brokenhook routes,
plus46paint/window. Cases verify onecallback/error report, no replay/abort,
originalerror/hook identity, laterdelivery and native-loop survival as applicable.
[784Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v3.json)/
[785WSL](../compat/api-acceptance/qt-input-callback-rendered-wsl-v3.json) each pass21same-source rendered
cases:6default-peer/3host-samecanvas/12controls;9childorigin/nativeSHA/10zero-gauge
proofs, parent10zero. Host/default acceptedstate is asserted separately.537original
members verify before1QtPythonoverlay;536/native unchanged. ExistingfilteredQt/
9c5softwaredriver unchanged/Xvfb0; all5WSLprocesses0awaited. Parent-rendered cases
remain parentless; the12parent-forwarding paths are CPU/realQt evidence, notfull
napari qualification. Privateclosed/post-C++-destruction host lookups are not
separately covered. PyQt5/PySide6, BaseException, otherinput and paint-hosthook
limits remain open. All7owned779–785scratch roots cleaned; renderedtargets remove
47,774,775bytes.785initialreadonlyplan refused a livePID; same PID/manifest/verifier
later reportsnotlive and v2plan/apply succeeds. No kill, skippedPIDcheck, changed
registry or deletionretry after reviewrejection; original refusal is retained.
Next exactcumulative re-review, then actualhead source tests and normalprotected
integration. Source-only/source-overlay evidence, no CI/wheel/admission/release
or fullparent claim. Older405f/a47areceipts remain historicalfinite passes.

**Host-hook correction now passes matching source suites, 2026-11-14:**
[774Windows](../compat/api-acceptance/qt-input-callback-windows-source-v3.json)/
[775WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v3.json) each pass81CPUcases(35input,
including7working-host/native-loop and7broken-hook cases;46paint/window).
[777Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v2.json)/
[778WSL](../compat/api-acceptance/qt-input-callback-rendered-wsl-v2.json) each pass21rendered cases:
6default-error peer recovery,3custom-host same-canvas redraw/peer recovery,
12ordinaryinput/PanZoom/draw controls. All9children verify origin/nativeSHA and
10zero gauges; parent10zero. Exactly1QtPythonoverlay on unchanged536/native,
all537original members verify first; existing Qt/WSL9c5driver unchanged/Xvfb0.
Same runtime `405f766f` on both profiles. [771/773gap](../compat/api-acceptance/qt-input-host-hook-gap-v1.json)
records CHANGES_REQUIRED/noapproval for oldera47a: nativehostloop prematurely
exits1 despite customhook. Revisedguard invokes workinghosthook without stopping
canvas/loop; brokenhook falls back to originalsafe deferral. Olda47areceipts
remain historicalfinitepasses, not approval. [776failure](../compat/api-acceptance/qt-input-host-hook-render-fixture-failure-v1.json)
retains3redrawtimeouts after fixturequitclosedwindows;777exit0+keptopen checks
fix the fixture without relaxing pixels/recovery/native/gauge assertions.
Allowned770/771/773–778scratch cleaned; rendered776/777/778remove65,675,375bytes,
retained19/18/26checks. Earlier769cleanup ordering defect stays recorded;
subsequent applies require separate successful inspection. No new build/wheel/
environment. Commonpolicy affects allQtbindings, but PyQt5/PySide6changes remain
unqualified; BaseException is not contained. Closed/detachedinput now ignored
and may propagate to parents. Paint-path customhook behavior is separateopen
work, not fixed here. Source405f/tests/newreceipts need exactamendmentreview and
protectedintegration; no CI/fullnapari/public-wheel/full-parent claim.

**PR80integration verified separately:**
[772](../compat/api-acceptance/lifecycle-panzoom-protected-integration-v1.json) verifies normalprotected
merge `bff61230`, tree `7abcfdbc` equal testedmerge/sourcefreeze, all11required
checks and20delta blobs;702committed frozeninputs match, old16feQt reconstructed
from retainedsource. ForeignHEAD/index and then-current825localWIP inputs stay
unchanged. OptionalMacCPUjobs were pending; no all21job claim. The callbackpatch
was not included. Future source integration uses this actualparent after drift
checks; prior55fd/currentwheel qualification is not transferred.

**Matching WSL rendered callback recovery passes, 2026-11-14:**
[769](../compat/api-acceptance/qt-input-callback-rendered-wsl-v1.json) passes18same-source cases as
[768Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v1.json):6isolated key/mouse/
wheel error-recovery proofs plus12ordinaryinput/PanZoom/draw-callback cases.
Child import/nativeSHA, original exception identity, failed-canvas no-redraw,
peer green/blue recovery after close and10zero gauges pass in all6children;
parent10gauges zero.537original members verify before1Qtwrapper overlay,
536/native unchanged after; filteredQt/9c5softwareVulkan origins stay unchanged.
All5processes0/awaited, privateXvfb0. Scratch570files/29,871,553bytes removed,
26retained hashes verified; no build/environment/newwheel. Cleanup ordering
mistake is explicitly retained: coordinator's prefix inspection missed2declared
Mesa cache files and failed, but following apply stillran; tool independently
validated exact owned target/registry/hashes. Post-apply snapshot audit confirms
only ownedlinux/cache files/marker. Future apply requires a successful separate
inspection step; no deletion was retried or protected origin targeted.
Next independent cumulative source/fixture/evidence review and protected source
integration; changed-wrapper installed/public admission remains separate. Source
WIP is outside frozenPR80; no broader parent/CI/physicalhardware claim.

**Windows real-canvas callback recovery verified at source-overlay scope, 2026-11-14:**
[768](../compat/api-acceptance/qt-input-callback-rendered-windows-v1.json) passes18cases:6newkey/mouse/
wheel error cases across process_events/run plus8ordinaryinput,2PanZoom and2draw
callback cases. Each new child verifies exact parent import origin/nativeSHA,
original exception identity, failed-canvas no-redraw, peer green thenblue after
failed-canvas close and ten zero shutdown gauges. Parent gauges also zero.
537original wheel members verify BEFORE exactlyoneQtwrapper source overlay;
536members/native remain unchanged, no wheel/build/admission claim. Both child
fixtures now use-I-S plus explicit parent paths: [767failure](../compat/api-acceptance/qt-input-callback-child-origin-failure-v1.json)
retains6origin rejections/2editable native mismatches and10ordinary passes;
no runtime/native rebuild or relaxed origin assertion resolved it. Both Windows
targets cleaned35,802,088bytes total,19/18retained checks; CPU763–766cleanup and
old diagnostics remain separately recorded. Source WIP remains outside PR80.
Next matching WSL rendered recovery, independent cumulative source/fixture review,
protected integration and exact changed-wrapper installed acceptance as needed.
LIF-06/API-06 remain partial; no HID/native-presented/optical/other-binding/full
parity/CI/public-wheel claim.

**Callback source CPU acceptance now matches Windows/WSL, 2026-11-14:**
[765Windows](../compat/api-acceptance/qt-input-callback-windows-source-v2.json)/
[766WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v2.json) pass67same-source cases each,
including21newinput cases. The release fixture now initializes _vispy_canvas
like a real backend and asserts no queued application error before/after destroy;
766has no deleted-widget diagnostic. Earlier764also passed67but logged that
fixture diagnostic; its [v1record](../compat/api-acceptance/qt-input-callback-wsl-source-v1.json) stays
qualified accordingly.763failed before collection due DrvFS fd capture;764/766
use existing-s/no-capture convention, not weakened assertions. Borrowed WSL
Qt/Python origins and source hashes stay unchanged; all children0/awaited.
Scratch markers763–766cleaned358bytes, retained15/16/8/16records respectively.
No renderer/GPU allocation, build or environment install. Next real Dawn-canvas
rendered recovery, then independent review/integration and changed-wrapper
installed acceptance. CPU passes are not public-wheel/CI/other-binding/full-parent
coverage. Source WIP remains outside frozen PR80.

**Qt input callback abort reproduced and source fix verified, 2026-11-14:**
[762source CPU acceptance](../compat/api-acceptance/qt-input-callback-source-v1.json) passes67Windows/
PyQt6cases:21new real offscreen Qt-dispatch cases and46existing paint/window
checks. Seven mouse/wheel/key virtuals now contain ordinary callback exceptions,
ignore the triggering event, suspend the failed canvas and preserve the original
exception for process_events()/run(); errors surface once, peer delivery and
ignored-error same-widget recovery pass.761baseline key callback aborts child
3221226505;760earlier fixture weakref error is separate and both remain retained.
No GPU/native canvas was allocated. All3scratch markers cleaned263bytes total;
762verifies20retained records. This is source-only wrapper WIP outside frozen
PR80: `_qt.py` is the sole intentional drift among810prior guards; prior source
receipts stay unchanged. Next WSL counterpart and actual Dawn-canvas recovery,
then review/integration and exact changed-wrapper installed acceptance as needed.
No new wheel/build, current PR80 result, CI coverage, other-binding or full-parent
claim is made. LIF-06/API-06 remain partial.

**Reviewed combined batch submitted as PR80, 2026-11-14:**
[759source head](../compat/api-acceptance/lifecycle-panzoom-source-head-v1.json) records
`af21f74c` on verified parent `96b1187e`, exact20approved source/evidence/metadata
files.810critical guards/702committed parent inputs match; originalfaulttest and
foreign HEAD/index stay unchanged. Archived approved bytes were staged, with no
checkout/reset/force/admin bypass. [PR80](https://github.com/bipxx/vispy_vulkan/pull/80)
has normal protected auto-merge enabled; fresh required checks/actual merge are
pending. Private index/marker cleaned15,128,875bytes,111retained inputs verified,
scratch absent. No new runtime/native build, wheel release, test CI coverage or
admission claim. This later checkpoint/source-head receipt stays outside PR80's
frozen20-file snapshot; do not amend it merely to record its own CI status.

**Combined integration amendment approved, 2026-11-14:**
[758review](../compat/api-acceptance/lifecycle-panzoom-combined-review-v1.json) approves the exact
19-file composition `4b85c65c` on actual PR79merge `96b1187e`, with no required
changes. It explicitly replaces754's separate750merge prerequisite with one
protected PR, keeping exact parent/file/810guard checks and fresh required CI.
The strengthened PanZoom delivery witness is independently reviewed; prior750
non-doc results and754v1receipts stay unchanged. Coordinator checks702committed
parent inputs and prior approved doc text; only the reviewed PanZoom child moves
to v2evidence. Next stage the approved bytes plus this permitted review receipt
and additive checkpoints through a32MiB private index. No branch/head/CI pass,
new GPU-test CI coverage, admission, release or full-parent closure is claimed.

**Current investigation plan refreshed, 2026-11-14:**
[Ordered closure packets](superpowers/plans/2026-11-13-remaining-gap-closure.md#investigation-and-closure-queue--2026-11-14-current-revision)
now prioritize completed-work integration, stale-record reconciliation, Qt callback
exception handling, ordinary Qt routing and one useful rendering combination.
[PR79 actual merge `96b1187e`](../compat/api-acceptance/qt-input-protected-integration-v1.json) is verified by retained753 (11 required checks,
matching tested tree,810 unchanged guards/foreign index). Strengthened PanZoom
[755Windows](../compat/api-acceptance/qt-panzoom-windows-v2.json)/
[756WSL](../compat/api-acceptance/qt-panzoom-wsl-v2.json) pass2cases each with an
explicit post-release move-delivery witness;756cleanup reclaimed29,870,467bytes,
24retained checks/scratch absent. Review750's approved lifecycle/MSAA batch and
strengthened PanZoom still need guarded integration; combining them requires an
explicit review amendment to754's sequential-merge condition. No new experiment,
build, CI-test coverage, public-wheel qualification or full-parent closure is
claimed by this planning change. Older pending labels below are historical;
source/local-installed/merged/public-delivered scopes remain distinct.

**Qt input now reaches a real scene camera at finite installed scope:**
[751](../compat/api-acceptance/qt-panzoom-windows-v1.json)/[752](../compat/api-acceptance/qt-panzoom-wsl-v1.json)
each pass2same-source PanZoom pan/release/recovery and cursor-wheel/reverse cases
with literal world rectangles,3x3marker centers and image-exact restoration in
explicit240x180SceneCanvasrender.537members/no overlays/ten zero gauges,
awaited exits, WSL Xvfb0/borrowed origins unchanged.47,770,425bytes cleaned/
42retained checks, no new build/environment. Later WIP outside PR79/750approval;
review/integration next. No native-display/optical/HID/focus/DPI/other-camera or
broad LIF-06/SCI-03/API-06 claim.

**Combined evidence/test delta approved for guarded integration:**
[750](../compat/api-acceptance/lifecycle-msaa-review-v1.json) approves amended
12-file scope with conditions/no required changes,810guards/823review inputs.
Color-before-redraw assertion and stale WSL row corrections are confirmed;
16strengthened capture cases and11original submission-fault cases pass per
profile at their exact recorded hashes. All eight result receipts stay unchanged.
Reviewer exits0/awaited,91bytes/839inputs cleaned/verified, no scratch/build/env.
Next protected PR79merge, actual-parent join and exact approved delta/private
index/fresh checks; no new branch or CI/admission/full-parent coverage claimed.

**Review follow-up now tested:**
[748](../compat/api-acceptance/msaa-depth-stencil-windows-v2.json)/[749](../compat/api-acceptance/msaa-depth-stencil-wsl-v2.json)
pass16matching cases each with exact color checked after mutation capture and
BEFORE redraw,537members/no overlays/ten zero gauges. Both targets cleaned
47,770,447bytes/39retained checks, actual exits0/awaited and WSL origins unchanged.
No native build/environment. Original745/746results stay frozen; their color
observation was after redraw.747approved original10-file scope with conditions
and noted this improvement plus stale Windows-child WSL wording; both corrected.
Amended source/v2receipts await a focused amendment review, not transferred
approval. Existing parent/edge/format/surface/physical-memory/CI limits remain.

**Default depth/stencil MSAA capture subset verified:**
[745](../compat/api-acceptance/msaa-depth-stencil-windows-v1.json)/[746](../compat/api-acceptance/msaa-depth-stencil-wsl-v1.json)
each pass16same-source cases: samples0/4, depth/stencil float/byte, full/crop,
analytic values, mutation/refusal/restoration and color preservation on current
wheels/runtime2b8. Actual sample allocation checked,537members/no overlays/ten
zero gauges; awaited exits and WSL origin checks pass.47,770,447scratch bytes
cleaned/39retained verifications, no native build/new environment/display server.
Depth-float tolerance1e-6; other/restored output exact. Uniform samples do not
prove mixed-sample edge selection. New test/records are outside PR79; next
review/integrate alongside later bounded records. LIF-05/SCI-06/API-06 stay
partial; real surface acquisition/physical-memory and other format/feature cells
remain open, with no deterministic existing native acquisition control found.

**Qt input follow-up submitted as PR79:**
[743](../compat/api-acceptance/qt-input-source-head-v1.json) pushes434f1326with
exact9approved files on verifiedbf1e4212parent; test hash joins736/738installed
results,810guards/702parent inputs verify. Frozen approved snapshots are staged,
newer live fault/merge worklist changes and foreign index preserved. PR79normal
protected auto-merge enabled; original CPU43571683051/Linux43571683050checks
live, no CI-coverage/profile claim for new test.15,126,858private-index bytes
cleaned/87retained inputs, scratch absent. Next actual required checks/merge;
submission-fault records and later live checkpoints remain separate WIP.

**PR78 merged under normal protection:**
[742](../compat/api-acceptance/post-preview-protected-integration-v1.json)
verifies bf1e4212at actualheada2dbe39a, merge treef3a86179equal testedPRtree and
all11required checks successful. Optional macOS CPU jobs stilllive/queued;
no all21-job claim.810source guards/foreign index unchanged, no admin/force/
checkout/scratch. A racing already-merged precheck sent no additional merge
request. Next the exact739approved Qt snapshot, preserving later fault records
and live-worklist edits outside that reviewed delta.

**Submission-fault subset complete at local installed scope:**
[740](../compat/api-acceptance/submission-fault-windows-v1.json)/[741](../compat/api-acceptance/submission-fault-wsl-v1.json)
each pass11identical-source pre/post-submit/query-frame failure/recovery,
ticket-retention/non-replay and retirement cases on current wheels/runtime2b8.
537members/no overlays/ten zero gauges each, actual children0/awaited, WSL
borrowed origins unchanged.47,770,449scratch bytes removed/40retained checks;
no new test code/environment/native build. Real surface-acquisition failure,
physical-memory accounting and broad LIF-01/API-06 remain open. New records/docs
are outside PR78/739Qt approval; their future evidence integration is separate.

**Next native-fault evidence subset passes Windows:**
[740](../compat/api-acceptance/submission-fault-windows-v1.json) passes11existing
pre/post-submit/query-frame failure cases, with ticket retention, no replay,
explicit recovery and ownership retirement on current9e4/runtime2b8.537members/
no overlays/ten zero gauges; actual exit0/awaited.17,899,970scratch bytes removed/
20retained checks. No new test code/native build/environment. Next same WSL
subset; actual surface acquisition and physical-memory accounting stay open.
New740records/worklist edits are outside PR78/739Qt delta; approved739metadata
sources are retained for exact staging without adopting this later WIP.

**Qt input review complete; protected integration remains:**
[739](../compat/api-acceptance/qt-input-review-v1.json) approves exact8-file scope
with conditions/no required changes.810source guards/818frozen inputs, reviewer
exit0/awaited, cleanup82bytes/835inputs verified. Test/four receipts unchanged.
"Visible/rendered" in736/738means2x2origin internal framebuffer readback after
an actual draw, not optical/presented-display/whole-canvas proof; restoration
means green after reconnect. Target isolation tests emitter cross-wiring, not
focus routing. The original/patched driver wording refers to one retained Mesa
artifact `9c5c41b3a7b9d759b0960c868f10375281798ad084150716d6d122c8789b9e12`.
Application input-callback abort-safety with ignore_callback_errors=False stays
open. Next wait for protected PR78merge, join actual parent and integrate with
fresh required checks; no new branch, CI coverage, profile or full-parent claim.

**Selected Qt input acceptance complete on Windows/WSL:**
[736](../compat/api-acceptance/qt-input-windows-v1.json)/[738](../compat/api-acceptance/qt-input-wsl-v1.json)
each pass8identical-source payload/render/handled-state/disconnect-reconnect/
target-isolation cases,537members/no overlays/ten zero gauges on current wheels.
WSL uses retained filtered PyQt6 and original software driver/private Xvfb;
borrowed origins unchanged, all children exit0/awaited.737wrong dependency path
fails before collection and stays retained;738selects existing GUI dependencies
with an import precheck.59,740,928WSLscratch bytes removed/48retained checks;
95,540,838bytes cleaned across735–738. No new environment/native build.
Next review/integrate the new Qt test/records after PR78's existing checks;
no source change to its pushed head. LIF-06/API-06 stay partial beyond the named
subset; no physicalHID/focus/gesture/trackpad/DPI/other-binding/CI/admission claim.

**Next behavior gap partially closed on Windows:**
[736](../compat/api-acceptance/qt-input-windows-v1.json) passes8PyQt6generated
key/wheel/mouse cases with exact public payloads, rendered response, handled/
ignored behavior, disconnect/reconnect and target isolation on9e4e30cc/runtime2b8.
537members/no overlays/ten zero gauges, exits0/awaited.735fixture ndarray/Qt
callback abort remains failed with source/reproducer; corrected validation runs
outside Qt callback dispatch. Both targets cleaned35,799,910bytes/40retained
verifications. New test/receipts are outside PR78. Next WSL counterpart, then
review/integration; LIF-06/API-06 stay partial, no focus/HID/CI/admission claim.

**Independent impact review and local commit A complete:**
[731/732](../compat/api-acceptance/post-preview-reviewed-commit-v1.json) approves
the exact78-file delta with conditions/no required changes and records local
commit `63abac6b8a6317766ee1b0a8cfa72da135f2c906`.810source guards/702Git inputs,
885frozen review inputs, exact staged blobs/path set and doc API links verify;
foreign index unchanged.8local collected nodes join by exact test bytes, not CI
coverage or new qualification/admission. Review/private-index scratch removed
15,126,134bytes total;900/51inputs verified. Next the allowed metadata checkpoint,
then push/PR and actual protected checks/merge. No push/integration result yet.
717notes hash refers to retained pre-publication notes, not the current doc;
prior snapshot receipts stay unchanged.

**Later-WIP inventory verified; review/integration remain:**
[730](../compat/api-acceptance/post-preview-delta-audit-v1.json) checks the77-file
owned delta snapshot,810unchanged source guards and702matching frozen committed
Git inputs; foreign index unchanged.8newcamera/filter cases collect locally,
exit0/awaited, without execution or CI claims.729wrong source-versus-Git namespace
adapter failure is retained; corrected730uses the authoritative committed map.
No environment/native build/scratch or cleanup target created. Next freeze the
updated owned delta including this receipt, obtain explicit independent impact
review and integrate normally under branch protection. The77count describes
the audit snapshot, not subsequent documentation/receipt additions.

**Public preview delivery closed; later-WIP integration next:**
[726publication](../compat/api-acceptance/preview-publication-v1.json) and
[728readback](../compat/api-acceptance/preview-public-delivery-v1.json) prove
exact55fd prerelease/two preview paths, both public wheel hashes and all four
served HTML pages. Stable assets/latest/index unchanged. Windows clear/WSL
ABI-only smokes join by exact bytes, not another GPU qualification.727buffered
HTML checker failure stays failed; corrected adapter changes no published content.
All children awaited;17,377,805scratch bytes cleaned across726–728, scratch absent.
Next review/integrate later records/docs/two tests at their actual new head,
then audit stale feature rows before choosing another behavior gap.

**Linux draft smoke complete:** [725](../compat/api-acceptance/preview-draft-wsl-channel-v1.json)
passes authenticated a2715d26 download hash/size, offline isolated install,
537members/23notice inputs/22notice texts and native ABI import with no overlays.
Guest/backing-volume checks pass, existing WSL dependencies unchanged, all
processes exit0/awaited.569scratch files removed/28retained inputs verified;
no scratch remains. Scope is ABI-only, not GPU or public delivery. Both draft
smokes now pass; next public prerelease, separate preview index and actual
public-byte/channel readback, then later-WIP integration.

**Current investigation order — planning only:** follow the
[authoritative closure queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#authoritative-next-actions--2026-11-14).
Next: FIX-06 WSL draft ABI check, public prerelease/index and public-byte readback;
then FIX-04/06/API-06 later-WIP delta review and protected integration. Audit
API/SCI/lifecycle/clipping rows against newer evidence before running more tests.
After that, select finite Qt input, camera/state, filter, lifecycle/capture or
rendering cases in that proposed order, skipping already-proved behavior.
Admitted/merged 718/719 work is not repeated. Broader parents stay partial and
hardware/full-parity boundaries remain unchanged. No execution or new pass claimed.

**Windows authenticated draft smoke complete:** [724](../compat/api-acceptance/preview-draft-windows-channel-v1.json)
passes exact537members/23notice inputs/22notice texts and64x64Vulkan clear,
zero overlays/ten zero gauges on the current9e4wheel.722successful transport
is reused; original adapter failure is not relabelled. Exits0/awaited and target
cleaned. WSL ABI transport/install, public prerelease/index and public-byte
readback remain next; this is not yet public delivery.

**Windows draft delivery adapter failure retained:** [722](../compat/api-acceptance/preview-channel-adapter-failure-v1.json)
downloads/installs exact draft9e4bytes but stops before native import on a wrong
license-directory count. [723](../compat/api-acceptance/preview-notice-placement-v1.json)
proves all23source notice inputs/22notice texts per wheel; manifest.json is
metadata and is packaged under vispy/_licenses. No license/artifact is missing.
24,713,237bytes/18inputs cleaned/verified, failed exit1awaited. Next corrected
smoke reuses the authenticated receipt and immutable original without redownload.

**Draft preview ready for delivery smokes:** [721](../compat/api-acceptance/preview-release-draft-v1.json)
retains draft release445068448, exact55fdtarget and two uploaded current wheel
SHA256/size matches. Stable delivery.json/two wheels/index untouched; not public.
All children exit0/awaited,85bytes cleaned/30inputs verified. Next draft-asset
download/install checks Windows/WSL, then reviewed public prerelease/index and
public byte/channel readback. No new native build or artifact qualification.

**Delivery precheck correction needed:** [720](../compat/api-acceptance/preview-draft-precheck-failure-v1.json)
retains an adapter assertion before any release mutation: stable assets include
delivery.json plus the two expected wheels. All remain unchanged. Failed exit1/
awaited; duplicate-retained-path cleanup refusal0deletions preserved, corrected
new manifest succeeds85bytes/15inputs. Next successor checks only exact wheel
digests and preserves the complete stable-asset baseline; no native rebuild.

**Protected PR77source merge complete:** [719](../compat/api-acceptance/parent-protected-integration-v1.json)
records mergeba49b468with tree4260039fidentical to the23-job tested PR tree.
Exact55fdhead pin/required checks pass; no protection bypass, force or shared
checkout/index changes. Connector ready permission error retained; authorized
existing CLI performs ready/body/auto-merge and verifies actual merge. No
scratch. Next exact55fdprerelease/tag, separate preview-index delivery and
isolated delivered-byte/channel checks; later records/docs/two tests still
require their own explicit delta/impact/protected integration.

**Selected successor admitted; integration/delivery remain:**
[718](../compat/api-acceptance/parent-final-admission-v1.json) passes actual
strict128-binding admission and all8reviewed current mandatory rows. Source
view equals55fdGit blobs; all14canonical/702committed inputs restore exactly,
foreign checkout/index unchanged. New matrix viewe1efb9ad…preserves the original
230b12f3matrix, six optional historical and two NOT_ADMITTED rows; manual foreign
retention stays separate from generic Tk retention. Actual exit0/awaited;
87scratch bytes removed/44inputs verified. Next protected integration and
delivery under714/716conditions, with separate delta/impact check for post-head
data/docs/tests. This does not close broader capability parents or publish assets.

**Exact final review approved; execution guards pending clarification:**
[714](../compat/api-acceptance/parent-promotion-review-v1.json) approves exact
basis/eight manual-retention rows/preview scope; conditions and unread/hash-
reliance limits retained. Actual exit0/awaited;89bytes cleaned/886inputs verified.
[715](../compat/api-acceptance/admission-source-guard-v1.json) proves702source
files equal55fdGit blobs without changing foreign checkout HEAD/index. Focused
716review is active for that topology and the sole temporary ledger exception;
actual admission is still unexecuted. [717](../compat/api-acceptance/preview-publication-corrections-v1.json)
records exact55fdtag target, separate-index/direct-hash installation and installed
byte identification notes. No publication, artifact change or stable upgrade.

**Exact basis711sealed; final independent review714active:**
[Basis711](../compat/api-acceptance/parent-promotion-basis-v1.json) binds full709CI,
exact impact702and subject86efb22b/head55fd4e8as basis1e92e7de…. All702committed
inputs unchanged, small subject copy byte-identical, no origin moves or scratch;
assembly exit0/awaited. Read-only reviewer714has871frozen inputs and requests
separate exact basis/eight-row/preview-channel decisions. Final admission,
protected integration and delivery are still pending; review is not approval.

**All23final-head CI jobs validated:** [709](../compat/api-acceptance/parent-final-head-ci-v1.json)
joins all20CPU/Linux/twoMetal jobs at55fd4e8with original histories, attempts
and checkout identities through the unchanged validator.15CPU/3native reports
reused, only5small archives downloaded(1,012,805bytes). Actual exits0/awaited;
cleanup removes1,012,877bytes/6files, verifies84inputs, scratch absent. Next
seal exact basis, obtain final independent review, execute guarded scoped
admission/restoration, then protected integration/delivery. This is not admission.

**SCI-02-COLOR-ALPHA-COMPOSITION installed subset complete:** [Windows712](../compat/api-acceptance/mesh-color-alpha-windows-v1.json)
and [WSL713](../compat/api-acceptance/mesh-color-alpha-wsl-v1.json) each pass six
Alpha/ColorFilter/TextureFilter/PlanesClipper cases on current9e4e30cc/a2715d26/
runtime2b8bccd. All before/change/restored32x24RGBA frames match literal expected
values; all three revisions stay queued(pending2/4/6). Includes detach/reattach,
zero alpha and valid replacement after invalid-alpha ValueError.537members/
zero overlays/ten zero gauges each; controller/Xvfb exits0/awaited, borrowed
WSL origins unchanged. Both targets cleaned47,787,437bytes/1,150files and
68retained-input verifications. Post-head tests do not broaden frozen55fdCI or
admission; general filter ordering/compositions/blending/MSAA stay open.

**SCI-02/API-06 Windows composition subset:** [712](../compat/api-acceptance/mesh-color-alpha-windows-v1.json)
passes six Alpha+ColorFilter+TextureFilter+PlanesClipper cases on runtime2b8bccd/
wheel9e4e30cc. Literal32x24RGBA frames match exactly for before/change/restoration;
pending draws remain2/4/6 before any read. Covers alpha/color updates,
detach/reattach, zero alpha and valid replacement after invalid-alpha ValueError.
537members/no overlays/ten zero gauges; actual exit0/awaited.17,908,464scratch
bytes removed/33inputs verified. WSL, broader composition/order/blending/MSAA
and final review/integration/admission remain separate; test source is post-head.

[Local package-index preview710](../compat/api-acceptance/parent-index-preview-v1.json)
is now concrete: two exact current-wheel links in the proposed separate
`previews/qt-lifecycle-55fd4e8/simple/` namespace, generated by the unchanged
package-index tool. Both stable index blobs were fetched and byte/hash-checked;
their four asset links remain untouched. Preview files total763bytes. Actual
preparation exit0/awaited; no scratch/native build/remote write. This remains an
unapproved channel proposal, not publication or a stable-version upgrade. Final
review must accept its scope after complete CI/admission and protected integration.

The original CPU run43554619087completed20/20successfully.709validates all23jobs/
history, reusing15CPU/3native identities and downloading only five missing
archives. Collection scratch is removed. Final promotion/admission remains pending.
The seven-row SCI-05record reconciliation is complete at the finite scope
[recorded by708](../compat/api-acceptance/scientific-current-dispositions-v2.json);
broader API/capability obligations remain open.

Promotion-basis assembly711has completed after full709CI validation and cleanup.
Independent final review714is active; guarded scoped admission/restoration
remains separate. Earlier19pass/1active snapshots are historical.

## Current execution status — 2026-11-13

**SCI-05 seven-row reconciliation completed (2026-11-13; API-05/06 partial):** [708](../compat/api-acceptance/scientific-current-dispositions-v2.json) verifies33input hashes, both current44-case JUnits, two camera packets and six current Qt rows' seven-stage functional/collector/worker reports. [Route/value table](api-method-reconciliation.md#current-seven-row-reconciliation--2026-11-13) classifies U05/E03/E04as finite current installed subsets, Q12as six current observations awaiting admission, Q11/Q13as open capture/input scope and H03as historical upstream-only. Runtime2b8bccd/current9e4e30cc/a2715d26scope; no stock failure,142-obligation or984-operation promotion. Initial707adapter's wrong literal status assertion remains exit1/reproducer;708checks actual exact tokens, exits0/awaited. No new graphics/install/scratch/native build. This closes record reconciliation only; broad capability/release gates stay open.

**Current qualification inputs preserved; original CPU CI live (2026-11-13; FIX-04/06, TOOL-01):** After adding the separate camera tests, all702committed qualification inputs still match699hashes exactly. Original CPU43554619087poll5has16SUCCESS/4in-progress/no failures; same handles continue. Retained704identities still cover15CPUjobs, with remaining identities/full23-job bundle/history required at completion. New camera observations do not alter the frozen subject or grant final admission.

**SCI-03 camera-mutation subset now installed-tested on both platforms (2026-11-13):** [Windows705](../compat/api-acceptance/camera-mutation-windows-v1.json) and [WSL706](../compat/api-acceptance/camera-mutation-wsl-v1.json) each pass2azimuth/center mutation/restoration cases on runtime2b8bccd/current9e4e30cc/a2715d26wheels. Both show4,032/2,969changed pixels, exact fresh-scene changed-pose equivalence, exact frozen baseline/restoration and comparison-peer closure isolation.537members/zero overlays/ten zero gauges verify per profile. WSL pinned software Vulkan/private Xvfb and borrowed origins verify; actual controller/Xvfb exits0/awaited. All new scratch removed:47,787,811bytes/1,142files,65retained-input verifications. Test source is post-head55fd; no final-head CI, admission or independent changed-pose upstream oracle is claimed. Broader camera/state combinations stay open.

**SCI-03/API-06 selected Windows camera mutation gap closed at local installed scope (2026-11-13):** [705](../compat/api-acceptance/camera-mutation-windows-v1.json) passes two public TurntableCamera mutations (`azimuth=80`, `center=(.3,-.2,0)`) on current Windows9e4e30cc/runtime2b8bccd. Both visibly change the scene(4,032/2,969pixels), exactly match a fresh scene at the changed pose, survive comparison-peer closure and restore the original frozen upstream image exactly. Changed-pose oracle is fresh-construction equivalence, not an independent upstream reference.537members/zero overlays/ten zero shutdown gauges verify; actual exit0/awaited. New test source is post-head55fd, without runtime changes or transferred CI/admission. Cleanup removes17,908,651bytes/570files and verifies32inputs. WSL counterpart and broader camera/plane/depth/stencil combinations remain open.

**Fifteen completed CPU checkout identities verified (2026-11-13; FIX-04/06, TOOL-01 partial):** [704](../compat/api-acceptance/parent-cpu-ci-identities-v1.json) retains original run/jobs/artifact metadata and15completed CPU job identities for55fd4e8/run43554619087attempt1. Artifact byte counts/SHA256, exact successful job joins, PR checked-head/source-parent, workflow/collector pins and schema verify. Five CPU jobs remain live in that snapshot; this is not complete23-job CI/history validation. Reuse these15reports plus native700reports when collecting the remaining5; no second download of completed transports. Actual collector/download exits0/awaited; managed cleanup removes3,017,597bytes/16files and verifies83inputs, scratch absent. No wheel/SDK extraction or native rebuild.

**Original final-head CI live, latest poll4 (2026-11-13; FIX-04/06, TOOL-01):** CPU43554619087now15SUCCESS/5in-progress/0queued, no failures. Three native identities remain verified separately. Continue these same handles; full23-job original identities/history and final scoped admission/promotion are still required. No redispatch or build allocation.

**Candidate review-reference transition verified (2026-11-13; FIX-04/06, TOOL-01):** [Source-only audit703](../compat/api-acceptance/candidate12-review-transition-v1.json) compares the original674archived candidate b7458444with current f931132eand original675before-hashes. Only `reviews` and `manifest_sha256` differ; both scopes recompute to4c2295f5and bound review hashes/statuses verify. This supplies coordinator evidence for702nonblocking F4 without changing the independent review or its limits. Actual exit0/awaited; no scratch/build/replay. Final CI/admission/promotion remains pending.

**Exact-head change-impact review approved (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Review702](../compat/api-acceptance/parent-head-change-impact-v1.json) approves reuse only for subject86efb22b/head55fd4e8/runtime2b8bccd; required changes empty. Complete read-only decision and its unread/hash-reliance limits remain retained. Admission must re-materialize the proved ledger under the existing guard and restore all14files; approval does not cover a new head containing later receipts. No CI, matrix/Tk admission, promotion or delivery approval. Actual reviewer exit0/awaited; managed cleanup removes8,908bytes/2files and verifies828inputs, scratch absent. Latest original CPU43554619087poll3has14SUCCESS/5running/1queued, no failures; unfinished jobs are macOS CPU builds/vendor restoration, not Metal graphics qualification. Continue original handles; collect full23-job identities/history before final promotion review.

**Stale installed-scope wording reconciled (2026-11-13; API-06, SCI-01/02/03/05/06):** Re-read both current664/665selected JUnit reports, verified their hashes against [the current installed packet](../compat/api-acceptance/qt-parent-current-installed-v1.json), and confirmed44matching no-failure/no-error/no-skip cases each at runtime2b8bccd/Windows9e4e30cc/Linuxa2715d26. Each includes11numeric-zero/flag/recovery cases,8stencil routes,10point controls(8rendered reference cases),4pending-filter revisions and2fixed scenes, alongside9Qt lifecycle cases. Earlier "unpassed/unpushed/installed pending" descriptions are historical checkpoints. [Stencil disposition](stencil-wrapper-disposition.md) now states the exact current scope. This closes a stale-record task only: camera mutation, broader filter/layout/format combinations, original stock failures, final admission and public delivery remain open; no rendering replay, build or scratch allocation.

**Investigation plan refreshed (2026-11-13; FIX-04/06, API-05/06, SCI-05, LIF/SCI backlog):** The [next investigation queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#next-investigation-queue--2026-11-13-planning-revision) starts with refreshing the original final-head CI handles and completing exact admission/integration/delivery gates, then reconciles stale public-route records before selecting one lifecycle or scientific gap. Baseline is subject699/head55fd4e8/runtime2b8bccd, wheels9e4e30cc/a2715d26,128bindings/64criteria, eight observations and three verified native CI identities. CI was not refreshed by this planning change. Existing parent-destruction observations are reused rather than repeated. Each packet has a finish condition, evidence-first path and stop rule; full parity and cybersecurity work remain excluded. No capability, admission or delivery status changes; no tests, scratch, builds or publication.

**Original CPU CI still progressing (2026-11-13; FIX-04/06, TOOL-01 pending):** Retained698job poll2for original CPU43554619087has2SUCCESS/13in-progress/5queued,20jobs total, no failures. Linux1/Metal2successful job checkout identities are separately verified by [700](../compat/api-acceptance/parent-native-ci-identities-v1.json); no all23-job bundle/history/admission or merge claim. Continue these same handles without redispatch. Local native-identity transport scratch is absent after202,058,005bytes cleaned/36inputs verified; no SDK extraction/build.

**Three current native CI checkout identities verified (2026-11-13; FIX-04/06, TOOL-01 partial):** [700](../compat/api-acceptance/parent-native-ci-identities-v1.json) retains original Linux43554619086and Metal43554619080attempt1job/identity evidence for source55fd4e8, successful job IDs and actual PR checked-head/source-parent joins, exact workflow/collector hashes. Three artifact transports match API byte counts/digests(total202,057,916bytes); only small ci-identity JSONs/member lists retained, no SDK/wheel/native payload extraction or rebuild. Actual collector/download exits0/awaited; cleanup removes202,058,005bytes/4files, verifies36inputs, scratch absent. This verifies3native-job identities, not the required23-job complete bundle/history or hardware/release admission. Continue same CPU43554619087handle, then collect20CPUidentities/fullhistory and exact promotion/admission/integration/delivery. Original14preparation files and other-owner index remain unchanged.

**Final-head installed subject renewed; CI still active (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [699](../compat/api-acceptance/parent-head-installed-subject-v1.json) proves128selected criterion/profile bindings/64criteria at qualification head55fd4e8and runtime2b8bccd, zero missing/blocked, using original current wheels, five strict Tk attempts/approved failure disposition and782-input retention.702committed input joins verify(608runtime/build/license,83preparation tools,14canonical files with overlaps). All14files restore against675hashes; original684frozen archive reused, no scratch/environment/native build. Copied prepare console's old624label is separately disclosed; actual materialization/restoration references684correctly. Other-owner index unchanged. [PR77](https://github.com/bipxx/vispy_vulkan/pull/77) stays draft. Retained698job poll1records Linux1/Metal2jobsSUCCESS andCPU20jobs15running/5queued; no observed failures, no full23-job/checkout-artifact/history/admission claim. Next poll same handles, collect complete exact CI basis, final reviewed matrix/Tk admission/promotion and protected integration/delivery.

**DraftPR77 and exact-head automatic CI are live (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [698](../compat/api-acceptance/parent-head-ci-start-v1.json) opens [PR77](https://github.com/bipxx/vispy_vulkan/pull/77) draft at55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1and retains three original pull_request attempt1handles: CPU43554619087queued, Metal43554619080in progress, Linux43554619086completed SUCCESS in the latest snapshot.23jobs remain required; no full CI/admission result is inferred. Linux/Metal use existing workflow reuse defaults; zero manual dispatches/duplicate runs. Connector PR creation first rejects a caller field then integration403; both errors retained, authorized existing CLI creates the draft and readback verifies exact head/base. No local consumer/cache/index/scratch allocated; actual CLI exits/waits and raw API metadata retained. Poll these same handles, retain jobs/artifact/checkout identities and complete histories; next guarded head-proof renewal and exact promotion/admission/integration/delivery. PR stays draft pending gates.

**Owned final qualification head pushed (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [697](../compat/api-acceptance/parent-qualification-source-head-v1.json) commits/pushes110owned files/3,738,502bytes as55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1on the existing WIP branch. All608runtime/build/license inputs are byte-identical to tested2b8bccd; no native rebuild, force push, checkout, deletion or other-owner index change. Includes approved preparation12/current row proofs, synchronized CPU/Linux selectors+policy hashes, regression test and two installed GPU no-op assertions. Correct root-only policy call passes; failed696remains retained. Private-index cleanup removes15,115,728bytes/2files and verifies51inputs within32MiB budget; scratch absent. Next exact-head23-job CI (avoid duplicate PR/manual runs), guarded head-proof renewal, exact admission/promotion and protected integration/delivery; not yet admitted or merged.

**Final freeze adapter setup failure retained (2026-11-13; FIX-04/06 partial):** [696](../compat/api-acceptance/parent-qualification-freeze-setup-v1.json) exits1before commit/ref updates because the caller passes two arguments to unchanged validate_policy(root). Original adapter/traceback/minimal reproducer and actual exit/wait retained. Cleanup removes15,100,811bytes/2files and verifies17inputs; other-owner index unchanged. Correct successor will use the inspected root-only signature; no runtime/qualification failure or approval/admission change.

**Current mandatory pre-admission review and exact688disposition approved (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [695](../compat/api-acceptance/parent-mandatory-peer-review-v1.json) approves the eight current row bindings, selected fixture reuse, manual original-retention scope, finite nine-attempt/eight-discovery history and the one exact Windows688UNVERIFIED disposition; required changes empty. Original failure stays failed; later PASS selection is justified without transferring682approval. Reviewer read selected ranges/spot checks, did not independently recompute hashes/ZIP contents or inspect every row; all explicit withheld areas remain attached, including unknown intermittent child-process origin and no machine/all-time history claim.1145input guards and coordinator arithmetic retained. This is not generic qualification-index retention, final-head CI, matrix/Tk admission, promotion, integration or delivery approval. Actual reviewer exit0/awaited; cleanup removes88marker bytes and verifies1156inputs, scratch absent; all14canonical preparation files unchanged. Next owned final qualification-head freeze/23-job CI identities/history, guarded head-proof renewal, exact final admission/promotion and protected integration/delivery.

**Current eight-row bindings and finite histories validate (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [693/694](../compat/api-acceptance/parent-mandatory-bindings-v1.json) bind all8current observations to source2b8bccd/preparation12, exact9e4e30cc/a2715d26wheels,24gates,537members/ten zero gauges each,1036original-retention checks and492reused fixture-archive members.15foreign dependency origins remain protected and unchanged; this manual audit does not claim generic qualification-index retention acceptance for those envelopes. Equivalent duplicate inventories are byte-verified and all originals retained;690initial zero-delete PID refusal/observed-absent/successful guarded retry are separately checked without changing the original plan or terminal. Native rg prefilter parses344of17,732JSONs at cutoff, finds9exact strict attempts(8pass/1preserved688UNVERIFIED),8separate discoveries,0unattributed controllers/later failures.14canonical preparation files unchanged. Actual audit/scan exits0/awaited; source-only metadata, no scratch/build/install. Next independent exact current scope/fixture/history review and688failure disposition, final owned-head23-job CI and reviewed admission/integration/delivery.

**All eight current mandatory observations collected (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Current8-row aggregate](../compat/api-acceptance/mandatory-parent-current-wheels-observations-v1.json) binds source2b8bccd/Windows9e4e30cc/Linuxa2715d26 across headless/PyQt5/PyQt6/PySide6. [692WSL headless](../compat/api-acceptance/mandatory-parent-wsl-headless-v1.json) passes95GPU/36authored science/rendering/4096markers and first strict replay on pinned Mesa9c5/private Xvfb. Every row verifies537installed members/origins, zero overlays and ten final zero gauges. Nine strict attempts are indexed:8pass/1preserved688Windows UNVERIFIED requiring new independent disposition; discovery stays distinct. Original wrappers/locked dependencies/notices reused read-only, identical resource budgets, no native build.692controller/Xvfb exits0/awaited and host mounts absent; cleanup removes92,589,429bytes/12files, verifies239inputs. AllfourWSL runs reclaim370,357,709bytes/48files; all8reclaim818,059,241bytes/8941files, no owned scratch.690original zero-delete live-PID refusal and actual successful retry remain preserved.14canonical preparation files unchanged. Observations complete, not matrix/profile/release admission. Next exact eight-row bindings/history,688failure review, final owned-head23-job CI and reviewed admission/integration/delivery.

**All three current WSL Qt observations pass (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [689–691aggregate](../compat/api-acceptance/mandatory-parent-wsl-qt-observations-v1.json) binds PyQt6/PyQt5/PySide6 seven-stage/first strict replay results on source2b8bccd/Linuxa2715d26/pinned Mesa9c5. Each537installed members/origins, exact selected binding/device and ten zero final gauges verify. Original matching roots/sites, standalone Python/driver/LLVM, locked fingerprints/versions and notice archives reused read-only; no native build or dependency/rootfs/notice copy. Controller/Xvfb exits0/awaited, guest mounts absent,14canonical files unchanged.691cleanup removes92,589,428bytes/12files/103verified inputs; all three reclaim277,768,280bytes/36files with103inputs verified per run, no scratch.690initial live-PID cleanup refusal remains preserved, with unchanged guarded successful retry explicitly referenced.7of8current observations complete; only WSL headless remains, followed by688failure disposition, final-head CI and reviewed admission/integration/delivery.

**Current WSL PyQt5 mandatory observation passes; cleanup refusal resolved (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [690](../compat/api-acceptance/mandatory-parent-wsl-pyqt5-v1.json) passes seven stages/first strict replay on source2b8bccd/Linuxa2715d26/pinned Mesa9c5 using its original separate PyQt5 root/site.537members/origins, binding/device and ten zero final gauges verify; borrowed fingerprints/versions/notices match630, archive reused. Resource-profile successor documents original binding-specific roots with identical512MiB limits;14canonical preparation files unchanged. Controller/Xvfb exit0/awaited, guest mounts absent/origins unchanged. Initial managed apply refuses with zero deletion because recorded controller PID is live again; later native observation finds PID absent. Original refusal/exit2and plan/terminal stay unchanged; same guarded apply succeeds with separate actual-exit/wait receipt. Cleanup removes92,589,426bytes/12files, verifies103inputs, scratch absent.6of8current observations complete; no profile/matrix/release admission. Next WSL PySide6/headless, exact688failure disposition and final-head CI/admission/integration.

**Current WSL PyQt6 mandatory observation passes (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [689](../compat/api-acceptance/mandatory-parent-wsl-pyqt6-v1.json) renews seven QWidget stages/first strict replay on source2b8bccd/Linuxa2715d26/pinned patched Mesa9c5/CPython3.12.13/private Xvfb.537installed members/origins, selected binding/device and ten zero final gauges verify. Original dependency lower fingerprints/versions and notice-archive members rehash against629; archive reused without duplication. Successor resource profile selectsa271with identical512MiB/240MiB visible+tmpfs limits; predecessor unchanged. Guest/backing capacity and all14frozen preparation hashes verify. Actual controller/Xvfb exits0/awaited; guest precheck confirms no run mounts, debugger/driver/LLVM unchanged. Cleanup removes92,589,426bytes/12files and verifies103inputs, scratch absent.5of8current mandatory observations complete; no matrix/profile/release admission. Next WSL PyQt5/PySide6/headless, exact688failure disposition, final-head CI and reviewed integration/delivery.

**All four current Windows mandatory observations pass (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Windows aggregate](../compat/api-acceptance/mandatory-parent-windows-observations-v1.json) adds [688headless](../compat/api-acceptance/mandatory-parent-windows-headless-v1.json) to685–687Qt profiles on exact source2b8bccd/wheel9e4e30cc. Headless passes95GPU/36authored science/rendering/4096marker checks,537installed members/origins and ten zero shutdown gauges. Replay0functionally passes but remains UNVERIFIED for one additional loaded file; expanded receipt replay1passes, exact failed-attempt disposition still pending. Original fixture versions/RECORD-listed files and source/license archive are reused; only GPU wrapper report source label changes. New successor headless resource profile selects9e4wheel/archive reuse with identical256MiB budget and expectations; old profile unchanged. Actual controller exit0/awaited;688cleanup removes69,192,235bytes/2129files, verifies293inputs. AllWindows runs together reclaim447,701,532bytes/8893files, no owned scratch;14canonical preparation files unchanged.4of8current observations complete, no matrix/profile/release admission. Next four WSL profiles, final-head CI and exact reviewed admission/integration/delivery.

**Three current Windows Qt mandatory observations pass (2026-11-13; FIX-06, LIF-02/04, API-06, PLAT-08, TOOL-01 partial):** [685–687aggregate](../compat/api-acceptance/mandatory-parent-windows-qt-observations-v1.json) binds fresh PyQt6/PyQt5/PySide6 seven-stage QWidget/first strict replay results on exact source2b8bccd/wheel9e4e30cc. Each verifies537installed members/origins, selected binding/device and ten zero final gauges; all14preparation files unchanged. Original filtered locked closures and source/license archives reused; no native builds. All actual controller exits0/awaited; cleanups remove378,509,297bytes/6764files and verify65inputs per run, no owned scratch remains. This is3of8current mandatory observations, without matrix/profile/release admission. Next Windows headless and four WSL profiles, then final owned-head CI, exact reviewed admission/promotion, protected integration and delivery.

**Current mandatory Windows PyQt5 observation passes (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [686](../compat/api-acceptance/mandatory-parent-windows-pyqt5-v1.json) renews the seven-stage plain QWidget workflow on exact source2b8bccd/Windows wheel9e4e30cc using the original filtered locked PyQt5 closure. First strict replay passes, binding/537installed members/origins and ten zero final gauges verify;14canonical files unchanged. Discovery remains distinct; no native build or source/archive duplication. Actual controller exit0/awaited; cleanup removes113,809,395bytes/2346files, verifies65inputs, scratch absent. Together685/686complete2of8current mandatory observations; no matrix/profile/release admission. Next PySide6 and remaining profiles, then final-head CI and admission/integration.

**Current mandatory Windows PyQt6 observation passes (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [685](../compat/api-acceptance/mandatory-parent-windows-pyqt6-v1.json) renews the seven-stage plain QWidget workflow on exact source2b8bccd/Windows wheel9e4e30cc with original filtered locked PyQt6 dependencies. First strict replay passes; discovery remains distinct.537installed members/origins, Vulkan device/binding and all ten final zero gauges verify;14canonical preparation files unchanged. Existing source/license archives reused, no native build. Actual controller exit0/awaited; cleanup removes129,752,954bytes/2423files and verifies65inputs, scratch absent. This is1of8current mandatory observations, not matrix/profile/release admission. Next seven remaining current profiles, final owned-head CI and exact admission/integration/delivery.

**Current selected installed subject proved (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [684](../compat/api-acceptance/preparation12-installed-subject-v1.json) proves all128criterion/profile bindings(64distinct criteria/32selected rows) on source2b8bccd/current9e4e30cc/a2715d26wheels using approved preparation12, original native/archive proofs, separate strict/pytest consumers, five complete strict attempts, one exact independent failure disposition and782-input contributing retention. Zero missing/blocked bindings; artifact remains unadmitted. Guarded derived-ledger materialization restores all14canonical preparation files byte for byte against675hashes, preserving142original required obligations. Actual assembly exit0/awaited; no scratch/environment/native build, only110,487-byte minimal frozen JSON backup for restoration.682/683marker cleanups removed181bytes and verified122/782inputs; no owned scratch remains. Next eight current mandatory profile observations/admission, owned final qualification-head integration/23-job CI, independent exact promotion basis and successor delivery; no full API/hardware coverage transfer.

**Current contributing retention validates (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [683](../compat/api-acceptance/preparation12-proof-retention-v1.json) revalidates both full native/archive proofs and774existing immutable proof inputs, then retains782inputs with actual audit/cleanup exits and waits. The unchanged generic retention validator passes after marker-only cleanup;93bytes removed, scratch absent. No wheel/SDK/environment/source-history copies or origin moves. One additional foreign Windows baseline is hash-verified at its original origin and separately disclosed outside this new generic namespace; original terminal/cleanup records remain retained. Selected32-row receipts, five strict attempts, one approved exact failure disposition, separate pytest phases and original licenses are covered. Canonical ledger is excluded for guarded materialization; no subject/profile/CI/admission is granted. Next guarded128-binding subject proof and exact restored14files, mandatory profiles and final-head integration.

**Exact current failed-attempt disposition independently approved (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [682](../compat/api-acceptance/preparation12-failure-dispositions-v1.json) approves the one676Windows UNVERIFIED receipt-expansion disposition and subsequent PASS selection as draft only; required changes empty, original failure remains failed. Complete read-only CLI stream/decision,104input guards, coordinator attempt-digest arithmetic and four separately indexed discovery reports are retained. Peer did not recompute hashes, execute tools or inspect all ranges/WSL/capture/source internals; its explicit withheld list remains attached. No retention/subject/profile/CI/promotion admission is approved. Actual reviewer exit0/awaited; cleanup removes88marker bytes and verifies122inputs, scratch absent. Next contributing retention through unchanged generic validation and guarded subject proof, then mandatory profiles/final-head CI/integration.

**Current strict attempt histories inventoried (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [681](../compat/api-acceptance/preparation12-attempt-history-drafts-v1.json) scans17,422retained JSONs/79strict controllers and identifies5exact current-wheel/profile attempts: Windows3(2pass/1UNVERIFIED), WSL2pass;0unattributed current-wheel strict reports. Four selected workflow attempts validate through unchanged history validation. Original676receipt-expansion failure remains failed; one exact independent disposition is pending, not inherited from old reviews. Discovery-only and other-environment reports remain distinct. Actual scan/draft/finish exits0/awaited retained; source-only work allocates no scratch, environment or build, and14canonical preparation files remain unchanged. Next independent failure review, contributing retention and guarded subject proof; mandatory profiles/final-head CI/admission/integration remain pending.

**Current selected row bindings validate (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [680](../compat/api-acceptance/preparation12-installed-row-bindings-v1.json) derives32source-local row receipts from676/678strict reports and separate677/679genuine pytest phases on exact source2b8bccd/current9e4e30cc/a2715d26wheels. Unchanged inventory/normalization/pytest validators prove128criterion-profile bindings/96raw gate checks in an overlay; all142original obligations remain incomplete. All14canonical preparation files and execution scope stay unchanged; no ledger promotion or artifact admission. Actual build/finish exits0/awaited retained; no scratch/build/install allocated. Next complete current strict attempt histories, independent failed-attempt disposition, contributing retention and subject proof; mandatory profiles/final-head CI/integration remain open.

**Current WSL genuine pytest receipts pass (2026-11-13; FIX-06/API-06 partial):** [679](../compat/api-acceptance/preparation12-wsl-criterion-phases-v1.json) passes2installed Tk state/capture tests/all6phases on source2b8bccd/wheela2715d26/pinned Mesa9c5; existing passed_pytest validates16selected WSL row fixtures.537members, installed loaded origins, zero overlays, ten zero shutdown gauges and Linux561archive-file/566RECORD checks verify. Separate dependency-site consumer does not inherit678strict fingerprint. Borrowed driver/LLVM/pcre/Python/Xvfb origins rehash unchanged; private Xvfb exit0/awaited;14frozen preparation files unchanged. Existing source/license archives reused. Cleanup removes29,870,483bytes/570files, verifies30inputs; scratch absent. Windows677and WSL679now supply all selected genuine phase receipts. Next32-row derived binding overlay, exact attempt/history/disposition/retention and subject proof; mandatory profiles/final-head CI/admission/integration remain pending.

**Current WSL strict cohort passes (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [678](../compat/api-acceptance/preparation12-wsl-strict-cohort-v1.json) validates both workflows at replay0on exact source2b8bccd/Linux wheela2715d26, approved preparation12 and pinned patched Mesa9c5/Tk9/CPython3.12.13. All16feature joins/48raw gate checks share one installed fingerprint;537members, zero overlays and shutdown gauges verify. Both discovery reports remain UNVERIFIED and distinct. Guest/backing filesystems are writable with capacity reserve; original userspace/Python/driver/dependencies borrowed read-only in a private namespace. Controller/Xvfb exit0and waits retained, host mounts absent and borrowed origins unchanged;14frozen preparation files unchanged. Source/license archive reused by hash. Cleanup removes92,589,423bytes/12files and verifies119inputs, scratch absent. Together676/678supply32strict feature joins/96gate checks on the two current wheels, not admitted rows. Next genuine WSL pytest phases, exact selected proof/history/retention with676failed-attempt disposition, mandatory profiles, final-head CI and promotion/integration.

**Current Windows genuine pytest receipts pass (2026-11-13; FIX-06/API-06 partial):** [677](../compat/api-acceptance/preparation12-windows-criterion-phases-v1.json) passes2installed Tk state/capture tests and all6setup/call/teardown phases on source2b8bccd/wheel9e4e30cc. Existing passed_pytest validates every16selected Windows row fixture;537members, loaded installed origins, zero overlays and ten zero shutdown gauges verify. This consumer borrows the existing dependency site and does not inherit676strict environment fingerprint. Frozen14preparation files unchanged; existing focused/source/license archives reused. Setup adapter initially expected a different newline and failed before scripts/install; original failure retained, corrected adapter/runtime exit0and actual child wait recorded. Cleanup removes17,899,973bytes/568files, verifies25inputs, scratch absent. Next current WSL strict cohort and genuine phases; proof/history/retention, mandatory profiles, final-head CI and admission/integration remain open.

**Current Windows strict cohort passes (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [676](../compat/api-acceptance/preparation12-windows-strict-cohort-v1.json) validates both state/resource/failure and capture workflows on exact source2b8bccd/Windows wheel9e4e30cc with approved preparation12. All16feature joins/48raw gate checks share one installed environment;537members, zero overlays and final shutdown gauges verify. State replay0 remains UNVERIFIED pending expanded receipt, replay1passes; capture replay0passes. Both discovery records stay distinct, and the failed strict attempt still needs its exact disposition review. All14frozen preparation hashes remain unchanged. Existing source/license archive is rehashed/reused; no native rebuild. Actual controller exit0/child awaited; cleanup removes62,906,058bytes/1636files and verifies65retained inputs, scratch absent. Genuine pytest phase receipts, WSL strict cohort, selected proof/history/retention, eight mandatory profiles, final-head CI and promotion/integration remain pending. No profile or artifact admitted.

**Investigation/closure plan refreshed (2026-11-13; FIX-04/06, API-05/06, SCI-05 and related open parents; planning only):** The [active queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#active-investigation-and-closure-queue--2026-11-13) supersedes older next-work notes: exact-wheel strict/pytest receipts, selected binding/history proof, eight mandatory profiles, owned final-head CI, then admission/integration/delivery. Baseline is source2b8bccd, unreleased Windows9e4e30cc/Linuxa2715d26, approved preparation12/scope4c2295f5; [675](../compat/api-acceptance/preparation12-approved-bindings-v1.json) remains unqualified and [664/665](../compat/api-acceptance/qt-parent-current-installed-v1.json) remains local installed scope. A claim-by-claim feature investigation table gives the shortest next case and exit evidence for API, scientific, lifecycle, shader, host and tooling gaps. Reconcile existing evidence before replay; optional hardware/full parity remain deferred. No capability closed, source/artifact changed, experiment launched or cleanup claimed by this planning update.

**Preparation12 exact approvals bound; reviewed gates pass (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [674source/scope/reuse review](../compat/api-acceptance/preparation12-peer-review-v1.json) approves scope4c2295f5and the two exact native-reuse hashes with no required changes. Its file-reading-only/hash-reliance/uninspected-ledger/native/SDK limits remain explicit; it grants no installed/profile/CI/admission approval. [675binding](../compat/api-acceptance/preparation12-approved-bindings-v1.json) recomputes exact scope/reuse/map identities and passes unchanged candidate/coverage/execution/selection, both full native records and both archives;14canonical files are frozen by hash. All330historical JSONs remain unchanged,142original obligations still required. Initial673CLI capture retained only a trailing notification; its incomplete decision remains unbound, with raw/task output preserved and5,225bytes/19inputs cleaned.674uses complete event capture and no shell tools, removes88scratch bytes/verifies21inputs.675is source-only with no scratch/native build. Next: current exact-wheel strict workflows and genuine pytest receipts, mandatory profiles, final-head CI identities/history, promotion/integration.

**CI coupling gaps reproduced and fixed; successor12 awaits review (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Review669](../compat/api-acceptance/preparation11-peer-review-v1.json) approves runtime reasoning but withholds scope/reuse: CPU selector changes lacked required-CI hash renewal, and Linux reuse still chose10. [670/671correction](../compat/api-acceptance/preparation12-ci-coupling-v1.json) reproduces policy refusal and selector-test failure, then fixes both selectors to12and updates exact workflow hashes without reducing23jobs/collector checks. New preparation12validates at scope4c2295f5; both retained native proofs/new archives revalidate and actual review gates remain closed. All330prior JSONs, including unapproved11, stay unchanged. [672](../compat/api-acceptance/preparation12-policy-contracts-v1.json) passes326source cases:282reuse/native plus44CIpolicy cases including the new cross-workflow regression. Cleanup removes8,945,392bytes/4930files, verifies8inputs;669review marker85bytes/18inputs also cleaned. No new CI/build/install launched. Next: independently review new scope/reuse digests, adding seal/execution-scope and policy-selector consistency arithmetic before strict observations and final qualification.

**Preparation11/current-wheel bindings valid, review pending (2026-11-13; FIX-04/06, API-06, LIF-02/04 partial):** [666](../compat/api-acceptance/qt-parent-preparation11-wip-v1.json) creates fresh unreviewed preparation11/source2b8bccd with64criteria/128bindings/32selected rows and all142original obligations retained;318historical JSON records unchanged. Four CPU CI selector arguments point to11before its preparation-tool hash freeze. [667](../compat/api-acceptance/qt-parent-preparation11-bindings-v1.json) revalidates both original native proofs and new9e4e30cc/a2715d26archives through unchanged validators; no new source snapshot, native build or wheel reassembly. Actual source/scope gates refuse, as required. Scope5dd73de0and both new reuse digests need independent approval;669review is active. [668](../compat/api-acceptance/preparation11-reuse-contracts-v1.json) passes282source reuse/native-evidence contract cases; cleanup removes8,945,357bytes/4930files, verifies9inputs, scratch absent.666/667allocate no scratch. No strict/profile/head/admission transfer; prior records/approvals and failed profiles remain unchanged.

**Both new wheels pass local installed acceptance (2026-11-13; FIX-04/06, LIF-02/04, API-06, SCI-01–03/05/06 partial):** [664/665](../compat/api-acceptance/qt-parent-current-installed-v1.json) each pass44selected lifecycle/clear/stencil/point/filter/fixed-scene cases and56Tkbaseline cases plus composite recovery on exact Windows9e4e30cc/Linuxa2715d26/source2b8bccd. Each isolated process verifies537members and loaded installed origins, zero source overlays and ten final zero gauges. Both parent-deletion orders now exercise recommended real-Canvas create_native/update no-ops; two external test lines remain uncommitted and are retained by exact delta/source archive. WSL uses patched Mesa9c5/private Xvfb; metadata561archive-file checks/566RECORD entries and borrowed origins verify, Xvfb exited/awaited. No native rebuild or environment copy. Cleanup removes48,168,056bytes/1210files, verifies59inputs; scratch absent.665retention adapter initially used wrong phase-receipt filename; original zero-delete refusal is retained, corrected metadata adapter changes no runtime/verifier. Earlier [6d6CI](../compat/api-acceptance/frozen6d6-ci-completed-v1.json) has all3workflows/23jobs successful at attempt1, metadata-only and not transferred to2b8bccd. Next: exact successor candidate/reuse/strict/profile/head qualification, owned test integration and promotion. Broader scientific/lifecycle parents remain open.

**Reviewed source pushed and two Python-only candidate archives assembled (2026-11-13; FIX-04/06, LIF-02/04, API-06 partial):** [Freeze661](../compat/api-acceptance/qt-parent-source-head-v1.json) commits/pushes22owned files/610,003bytes as2b8bccd0ac886f771c3e37255a3d5559c254b3cd, preserving the other owner's index and606unchanged runtime/build/license inputs; only the two approved Python runtime members differ. Source cleanup removes15,100,800bytes/2files and verifies85inputs, within32MiB full-index budget. [Package663](../compat/api-acceptance/qt-parent-python-package-v1.json) produces unreleased Windows9e4e30cc/Linuxa2715d26wheels at that head using unchanged retained native payloads. Exact archive and payload audits pass: only `_qt.py`, `canvas.py` and RECORD differ; notices/metadata/tags/native bytes remain exact. Published Vulkan.2 assets untouched. Failed662system-Python missing-packaging setup exits1before outputs;663uses existing project environment with no installation, exits0/awaited. Both packaging marker scratches cleaned174bytes, verifying6+15inputs. No new installed/strict/head/admission/merge claim. Next: exact-wheel installed parent/regression acceptance, renewed qualification and integration; earlier6d6b233CI remains scoped to its own bytes.

**Exact source/tests review approved (2026-11-13; LIF-02/04, API-06 partial):** [Renewal660](../compat/api-acceptance/qt-parent-review-approved-v1.json) approves the inspected two-file runtime correction and parent CPU/GPU tests with no required changes. It resolves651F1–F3, reads native register/destroy logic for duplicate-destroy safety, and checks current source, binding and rendered evidence within retained read-only limits. No hashes/tests rerun by reviewer; unread native correspondence/Qt/event/log/cleanup scopes remain explicit. Source guards were independently checked by coordinator; source/license archives reused by hash. Review cleanup removes84bytes/1file and verifies17inputs. Notes retained: binding-origin audit covers prefix-filtered .py/.pyd members, not Qt DLLs/co-loaded-binding absence; parent-deletion callbacks cannot use live-native accessors after detachment; real rendered create_native/update control is recommended for installed qualification.651CHANGES_REQUIRED remains unchanged. No candidate-scope/profile/wheel/release admission. Next: bounded owned-source freeze/push, Python-only packaging with retained natives and exact installed/strict/head qualification/integration.

**Three-binding CPU ownership controls pass (2026-11-13; LIF-02/04, API-06 partial):** [656/658/659](../compat/api-acceptance/qt-parent-binding-source-v1.json) verifies the generic fixture in separate Windows binding processes: PyQt5/PySide6 each11focused cases and PyQt6 cumulative68cases including those11. Original locked filtered Qt wheels are reused with no environment tree copy, version refresh or native build.657passes11tests but fails a separate origin helper on12embedded PySide6.support virtual paths; its original exit1/JUnit/diagnosis remains retained.658classifies exactly those12aliases and hashes all7real loaded binding members against exact locked wheel members, with no wildcard or existing project-verifier change. Managed cleanups remove194,984,317bytes/1431files and verify50inputs;659is scratch-free. Scope is CPU source/native doubles, not rendered or installed/strict PyQt5/PySide6 coverage.660read-only exact review renewal is active;651is not relabeled approved. New Python package/head qualification and integration remain open.

**Corrected destruction orders rendered on both platforms (2026-11-13; LIF-02/04, API-06 partial):** [654/655](../compat/api-acceptance/qt-parent-followup-rendered-v1.json) each pass8GPU cases on the current653Python bytes plus retained native payloads. Both direct parent deletion and explicit close-then-parent-deletion preserve pending green and subsequent blue peer pixels exactly;537package/overlay hashes and ten final zero gauges verify. Actual exits0/awaited, owned WSL Xvfb exits0/awaited; no native rebuild. Cleanup reclaims47,770,459bytes/1138files and verifies34retained inputs, leaving no scratch. Binding scope is PyQt6 only: the current Windows .venv lacks PyQt5/PySide6/shiboken6, and no packages were installed. Reuse their original locked closures for further selected binding checks. Review651 remains CHANGES_REQUIRED until renewed on these hashes;68CPU source passes and these two8-case observations do not confer installed/strict/new-head or release coverage. Next: exact review renewal, selected binding checks and changed-Python package qualification/integration.

**Independent review findings reproduced and corrected at CPU source scope (2026-11-13; LIF-02/04, API-06 partial):** [Review651](../compat/api-acceptance/qt-parent-destruction-peer-review-v1.json) returns CHANGES_REQUIRED, preserving its read-only/no-hash-recomputation and uninspected-native/binding limits. It confirms reentrant close can dereference a detached backend and create_native can attempt recreation after destruction. [Before652/after653](../compat/api-acceptance/qt-parent-destruction-reentrant-source-v1.json) reproduces3failures/8controls, then passes68CPU cases after both fixes; original raising-handler identity survives without a secondary cleanup error. Real explicit-close/parent-delete and late create_native/update controls pass. Scope remains PyQt6 only. Expanded GPU test now includes both destruction orders but is unexecuted on these new hashes;648/650do not cover the changed canvas.py. Review scratch86bytes cleaned/14inputs verified; source runs allocate none. Next: eight-case Windows/WSL reruns, selected other-binding controls and renewed exact review/package/head qualification. Live-native accessors after destruction remain unavailable; first-error recorder/finalization limits stay explicit. No approval/admission is inferred from completed review execution.

**WSL parent deletion/shared-peer source pass (2026-11-13; LIF-02/04, API-06 partial):** [650evidence](../compat/api-acceptance/qt-parent-destruction-wsl-source-v1.json) passes the same7rendered cases on retained Linux wheelb728b575/native5740b28a with two Python overlays, patched Mesa9c5 software Vulkan and owned abstract-local Xvfb. Actual hidden/readback parent destruction closes/detaches its owner once, preserves pending shared-peer green and subsequent blue pixels (4x4RGBA exact each);537members/overlay hashes and ten final zero gauges verify. Actual exit0/awaited, Xvfb exit0/awaited; borrowed driver/pcre/LLVM/interpreter/Xvfb origins rehash unchanged. Initial649fails before GPU execution because default Xvfb filesystem socket cannot bind WSLg's directory; previous qualified629transport flags resolve setup without system changes. Failed/successful attempts retain original exits/evidence/licenses. Cleanups remove568+570files/57,643,258bytes and verify16+21inputs; both scratch roots absent. No native build, installed-wheel/physical-GPU/full-WSI transfer. Next: independent source review, selected binding controls, changed-Python package/head qualification and integration.

**Windows parent-owned deletion/shared-peer rendered pass (2026-11-13; LIF-02/04, API-06 partial):** [648evidence](../compat/api-acceptance/qt-parent-destruction-windows-source-v1.json) passes7GPU cases on retained Windows wheel6de6d77f/native6dc06d2c with two explicit current Python overlays. Actual hidden/readback parent destruction closes its Canvas once, preserves pending shared-peer green and subsequent blue pixels (4x4RGBA exact each), with537package/overlay hashes and ten final zero gauges. Existing native/readback close/layout controls also pass. Actual exit0/awaited; no native rebuild. Cleanup removes568files/17,899,700bytes, verifies12retained inputs and leaves no scratch. First cleanup terminal adapter used unsupported state complete; its zero-delete refusal and original manifest are retained, corrected successor manifest passes unchanged hygiene checks. Next: WSL rendered source check, independent review and changed-Python package/head qualification. No installed-wheel, other-binding or physical-WSI transfer.

**Parent-owned destruction fixed at CPU source scope (2026-11-13; LIF-02/04, API-06 partial):** [Fix647](../compat/api-acceptance/qt-parent-destruction-source-fix-v1.json) passes64focused CPU cases. Real PyQt6 offscreen parent deletion now detaches the deleted backend, settles Canvas ownership/close once and permits repeated close. Controls cover callback failure/first-error preservation, collected weak owner, native-release error containment and destruction after explicit close, alongside existing paint/close/window-state cases. Initial644failure and645four-failure intermediate fix are retained;646passes63before the final idempotence control. Actual exits1/0/0and waits recorded; source snapshots/licenses retained, no scratch/native build. New Python changes in `_qt.py` and `canvas.py` are outside frozen6d6b233/current-wheel qualification: do not transfer running CI or wheel proof. Next: rendered shared-peer Windows/WSL checks, review and successor Python packaging/qualification using unchanged native payload. Parent IDs remain open.

**Confirmed parent-owned destruction failure (2026-11-13; LIF-02/04, API-06 open):** [Run644](../compat/api-acceptance/qt-parent-destruction-source-failure-v1.json) uses real offscreen PyQt6 deferred parent deletion, the actual Canvas.close implementation and a native-resource double. The child QWidget is genuinely destroyed and its native release slot runs, but the Python Canvas remains `_closed=False`; one test fails at that ownership assertion. Actual pytest exit1/awaited; exact reproducer/JUnit/logs/source hashes retained. No runtime change, GPU claim, environment, scratch or native build. Root license-filename adapter error is recorded separately; AGPL and original BSD references are preserved. Next: settle Python ownership without invoking deleted Qt methods, retain GC-safe release/callback containment, then idempotence/error/peer controls and installed verification. Frozen6d6b233CI remains unchanged; this is a new open defect, not a pass.

**Live exact-head CI job check (2026-11-13; FIX-04/06, TOOL-01 pending):** Original handles remain active at6d6b233. The latest retained job-level response in run641 has CPU43530224577:10completed successfully,6in progress,4queued; Metal43530230265:2queued. Linux43530227494 is completed successfully. No failed jobs observed in this snapshot; no full23-job success, admission or merge is claimed. Keep polling the same handles and retain original identities/history before promotion.

**Stale scientific rows reconciled (2026-11-13; API-05/06, SCI-05, LIF-05/06 partial):** [Source-only audit643](../compat/api-acceptance/scientific-stale-row-reconciliation-v1.json) verifies all six current Qt packet/hash joins, seven stages/537members/zero overlays/ten zero gauges each, and records finite U05/E03/E04/H03 dispositions. Q12 now records six current installed observations without admission or hardware transfer. Corrected the plan's erroneous Q11–Q13 volume mapping: these IDs concern MSAA depth/stencil, platforms/bindings and input; volumes are V01–V09. Q11 and broader Q13 stay open. Actual exit0/awaited, no runtime replay, scratch, native build or cleanup allocation. Existing point/filter/scene/Glue manifests are hash-pinned; their transitive histories are not independently revalidated by this audit.

**Plan refreshed; qualification-head proof complete (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Proof642](../compat/api-acceptance/current-head-installed-subject-v1.json) validates128selected bindings/64criteria at6d6b233, zero missing/blocked, with702committed input joins and all14canonical files restored. Runtime remains99719f1/current wheels6de6d77f/b728b575; the frozen archive is reused, with no scratch, environment or native build. This does not admit or deliver artifacts. The [refreshed sequence](superpowers/plans/2026-11-13-remaining-gap-closure.md#next-investigation-and-closure-sequence--planning-refresh) prioritizes existing23-job CI collection, exact admission and integration; then API/stale-evidence reconciliation, parent-owned canvas destruction and selected scientific workflows. Retained641poll4 records Linux success and CPU/Metal queued; refresh those same handles before action. All eight mandatory observations already pass. Planning adds no test, dispatch, capability closure or release claim; optional hardware/full parity/cybersecurity work remains outside scope.

**Owned qualification head pushed; final CI started (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Private-index source freeze639](../compat/api-acceptance/current-qualification-source-head-v1.json) commits/pushes109owned files/2,338,177bytes as `6d6b233fe80f19887726c6b91a247aa863f6dfee` on the existing WIP branch, with no deletions, force push, checkout or other-owner index changes. All608runtime/build/license inputs remain byte-identical to tested99719; no native rebuild. [Exact-head CI dispatch640](../compat/api-acceptance/current-head-ci-dispatch-v1.json) starts the23required jobs with original Linux/Metal reuse: CPU43530224577, Linux43530227494, Metal43530230265. Latest retained poll641shows Linux completed SUCCESS; CPU/Metal remain QUEUED, so final CI is not passed. Source639cleanup removed15,098,948bytes/verified261inputs; dispatcher640removed84bytes/verified28inputs. The private index exceeded the8MiB estimate because it represents the full base tree; the miss is retained and policy now requires measured-index sizing. No original preflight/limit was raised, and shared20GiB/10GiB policy was not exceeded. Frozen14preparation files and owner index remain unchanged. Poll the same handles without duplicate dispatch; exact admission/promotion review, protected integration/delivery and broader feature work remain open.

**Independent current mandatory pre-admission review approved (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Review638](../compat/api-acceptance/current-mandatory-peer-review-v1.json) approves row bindings, locked fixture reuse, manual original-retention scope and finite histories, with no required changes. It independently rehashes1050frozen inputs,945retained entries,492fixture archive members/487RECORD payload hashes and all8row/24gate joins; both current wheels, feature sets, devices, binding versions,95matching headless case IDs and seven Qt stages verify. Its independent current-wheel worker search finds no other mandatory-row attempts. Source/producer labels are the only Windows GPU-wrapper changes; original failure adapters remain failed. All15foreign origins remain protected; no generic retention acceptance or admission is granted. Unread/recomputation limits remain in the raw review: no execution of624subject validation, no791-input623rehash or recomputation of rendering native hashes/537member lists, no original466JUnit comparison, and no full log/mount/drive content or outside-root/all-time history audit. The cleaned environments cannot be re-inspected. Reviewer observations about receipt-to-discovery links, WSL helper labels and guest-vs-coordinator registry hashes stay explicit. Actual exit0/child awaited; cleanup removed89bytes/verified1062retained inputs. Next: owned final-head freeze/23-job CI, exact admission/promotion basis and integration/delivery. No native rebuild or published-release/full-parity transfer.

**Current mandatory bindings and histories validate (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Dossier636/history637](../compat/api-acceptance/current-mandatory-bindings-v1.json) joins all8current rows/24gates,537installed members and ten zero gauges per row, with945original managed cleanup input checks. All15foreign retained dependency origins remain unchanged and protected by registry613; this manual original-envelope hash audit does not claim generic qualification-index retention acceptance. The492fixture archive members verify, and the Windows GPU wrapper differs only in two provenance labels, with assertions unchanged. The finite two-root history scan enumerates16,910JSON files, parses304literal collector-key candidates and finds8exact strict passes plus8separate discoveries, zero unattributed controllers/later failures. Its prefilter/cutoff scope stays explicit. Two source-only setup failures remain retained:634assumed a rendering wheel field that the helper does not emit;635passed an absolute raw archive origin to the relative evidence resolver. Explicit package/native-member and origin joins fix those assumptions without changing a verifier or runtime report. Runs exit1/1/0/0respectively, awaited; no scratch/build/environment created. All14frozen preparation files remain unchanged. Independent cumulative review, final-head23-job CI, exact admission/promotion basis, integration and delivery remain open.

**All8current mandatory observations pass (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Current eight-row aggregatev3](../compat/api-acceptance/mandatory-current-wheels-observations-v3.json) renews the finite authored Windows/WSL headless and PyQt5/PyQt6/PySide6 observations on runtime99719f1/wheels6de6d77f/b728b575; canonical matrix and published qualification remain unchanged. New [WSL headless632](../compat/api-acceptance/mandatory-current-wsl-headless-v1.json) and [Windows headless633](../compat/api-acceptance/mandatory-current-windows-headless-v1.json) each pass the original95GPU cases, rendering/clear/smooth-text checks,4096marker smoke and36scientific cases in discovery and first strict replay, with537installed members/origins and ten zero final gauges. WSL retains software-Vulkan/private-Xvfb scope. Windows reuses five locked pytest-related distributions:492RECORD-verified files, source/licenses archived once, no environment tree copy or upgrade to cached pytest9.2.0; two stale GPU-wrapper provenance labels are corrected without changing assertions. [Windows256MiB](../compat/build-profiles/mandatory-current-headless-windows-v1.json) and [WSL512MiB](../compat/build-profiles/mandatory-current-headless-wsl-v1.json) policies are explicit; no native rebuild. Runs632/633actual exit0/children awaited; cleaned161,779,696bytes/2141files and verified446retained inputs. Exact matrix admission/bindings, final-head23-job CI, independent promotion review, protected integration and delivery remain open. This is8/8observations, not full API/scientific-quality/performance/hardware or release admission.

**All current Qt mandatory observations pass —6/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Six exact Qt profile packets](../compat/api-acceptance/mandatory-current-qt-observations-v1.json) now cover Windows and WSL PyQt5/PyQt6/PySide6 on runtime99719f1/current wheels6de6d77f/b728b575. New WSL629–631each pass seven original plain-QWidget stages and first strict replay,537installed members/origins and ten zero shutdown gauges with separate original locked dependency lowers, CPython3.12.13/private Xvfb and patched Mesa9c5 software Vulkan. Tracked borrowed origins rehash, owned Xvfb exits/waits, guest/backing health and no-leftover-mount prechecks pass. No native rebuild, rootfs/SDK/environment copy or package refresh. The629pre-runtime optional-registry-key generator failure remains retained; all previous protected/blocked paths are inherited. [WSL storage policyv1](../compat/build-profiles/mandatory-current-wsl-v1.json) and [matching-root clarificationv2](../compat/build-profiles/mandatory-current-wsl-v2.json) keep identical512MiB limits; prior policy/evidence stay unchanged. Runs629–631cleaned277,768,283bytes/36files and verified305retained inputs. Windows/WSL headless observations, exact matrix admission/promotion basis, final-head CI, integration and delivery remain open; no broad Qt/input, physical GPU/Metal or release transfer.

**Current Windows Qt mandatory observations pass —3/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Three exact profile packets](../compat/api-acceptance/mandatory-current-windows-qt-v1.json) now cover PyQt5, PyQt6 and PySide6 on source99719f1/wheel6de6d77f/Windows CPython3.12.8/RTX4090 Vulkan. New627/628each pass all7original plain-QWidget stages, discovery plus first strict replay,537installed members/origins and ten zero shutdown gauges, using their own locked binding closures and distinct environments. Capture/image ownership, overlay/hide/restore, injected loss/recovery and close are finite authored checks, not broader lifecycle/input parity. Dependencies were reused offline and shared source archives referenced in place; no native rebuild. Both actual exits0/children awaited;627/628cleaned248,752,405bytes/4341files and verified128retained inputs. Windows headless and all4WSL mandatory rows remain, followed by exact admission/promotion basis, final-head CI, integration and delivery. Original published qualification stays at its own bytes.

**Current Windows PyQt6 mandatory observation passes —1/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Source-only identity audit625](../compat/api-acceptance/mandatory-current-gap-audit-v1.json) confirms all8historical mandatory rows use different published wheels; their qualification stays historical. [New row626](../compat/api-acceptance/mandatory-current-windows-pyqt6-v1.json) passes the unchanged seven-stage plain-QWidget scenario and first strict replay on source99719f1/wheel6de6d77f, Windows CPython3.12.8/filtered PyQt6/RTX4090 Vulkan, environment95bae638. Exact537members/installed origins, capture/update/image ownership, overlay/hide/restore, injected loss/recovery, close and ten zero shutdown gauges verify. Locked core/Qt wheels were reused offline; no native build. Initial generator indentation failure occurred before driver/runtime execution and remains retained. Row626actual exit0/child awaited; cleanup removed2423files, reclaimed129,750,985bytes and verified66retained inputs. Seven current mandatory observations, exact admission/promotion basis, final-head CI, integration and delivery remain open. No broader Qt/input, other-binding, WSL/hardware or release transfer.

**Current installed subject proof passes (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Run624 unchanged subject validation](../compat/api-acceptance/preparation10-installed-subject-v1.json) proves128criterion/profile bindings (64distinct criteria) on preparation10/runtime99719f1/current Windows and WSL wheels, with zero missing/blocked joins. All14frozen preparation files are restored after the guarded32-row overlay. [Independent review621](../compat/api-acceptance/preparation10-failure-dispositions-v1.json) approves both exact Windows failure dispositions and draft latest-workflow selections; the two originals remain UNVERIFIED. Reviewer limits remain explicit. Its discovery-index wording finding is corrected by a separate four-report index, without rewriting620. [Contributing retention623](../compat/api-acceptance/preparation10-proof-retention-v1.json) validates791inputs in place. Run622 cleanup passed but its post-cleanup retention validation failed on one extra baseline outside selected roots; that failure remains retained. The corrected new event excludes that extra foreign-origin entry, verifies its unchanged hash/origin, and preserves original records; no verifier or dependency origin changed. Runs621–623 cleaned274bytes/1646retained-input verifications;624created no scratch. Original142obligations, mandatory-eight-row renewal, final-head23-job CI, promotion review, protected integration and delivery remain open; no broad API/hardware or published-wheel admission.

**Exact current attempt histories reconstructed (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Run620 history drafts](../compat/api-acceptance/preparation10-attempt-history-drafts-v1.json) scan16,617retained JSON files/66strict controllers and identify6exact wheel/environment replays, with zero unattributed current-wheel reports. Windows has2UNVERIFIED first replays and2later passes; WSL has2first-replay passes. Unchanged workflow-history validation accepts the complete ordered lists and4latest workflow selections. Original failures, discovery reports and other environment variants stay retained and distinct. Both Windows failed-attempt dispositions still need independent approval; contributing retention and subject admission remain pending. Scan/draft exit0 and are awaited; no scratch/build/environment created. This does not renew mandatory rows, final-head CI, release or broad API/hardware coverage.

**Current selected installed row bindings validate (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Run619 derived overlay](../compat/api-acceptance/preparation10-installed-row-bindings-v1.json) passes unchanged inventory validation for32selected Windows/WSL rows,64distinct criteria/128profile bindings and96raw gate checks on runtime99719f1/current wheels. Strict observer identities remain separate from the genuine same-wheel pytest processes. All14frozen preparation10JSON files and execution scope remain unchanged; all142original required rows remain incomplete. Run618's failed secondary-store row path and reproducer remain retained; source-local new receipts resolve that exact storage requirement without changing a verifier. Source-only runs exit1/0 respectively, awaited, with no scratch/build/environment or cleanup allocation. Exact attempt histories, independent failed-attempt resolutions, contributing retention, subject admission, mandatory rows, final CI and integration remain pending.

**Current WSL genuine pytest phases pass (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Run617 installed phase evidence](../compat/api-acceptance/preparation10-wsl-criterion-phases-v1.json) passes both selected Tk state/capture nodes and all6setup/call/teardown phases on exact Linux wheelb728b575/runtime99719f1 with patched Mesa software Vulkan. Unchanged `passed_pytest` accepts all16selected Linux fixture rows;537installed members/origins,561archive members,566RECORD entries, zero source overlays and ten final zero gauges verify. Existing Python/test dependencies were reused; no native build. Actual exit0/child awaited; cleanup removed570scratch files and verified26retained inputs. This separate pytest process does not claim strict observer fingerprint423ba184 or profile admission. Next: exact Windows/WSL subject/profile/history/retention joins, required mandatory profiles/final-head CI and protected integration. Broad API and hardware coverage remains open.

**Current investigation order and WSL strict checkpoint (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [The revised active plan](superpowers/plans/2026-11-13-remaining-gap-closure.md#current-investigation-plan--2026-11-13) supersedes older next-step queues: current WSL pytest phases → exact subject/history/retention joins → mandatory-profile/final-head CI/integration → bounded API/lifecycle/science investigations. [Run616 WSL strict evidence](../compat/api-acceptance/preparation10-wsl-strict-cohort-v1.json) passes both workflows/16feature joins/48gate checks on source99719f1, wheelb728b575 and patched Mesa software Vulkan, environment423ba184. Installed537members/origins and zero shutdown gauges verify; actual exit0/child awaited. Managed cleanup passed, deleting12files and verifying120retained inputs. No subject, mandatory-row, CI, release or physical-GPU admission. Planning adds no test result; current WSL genuine pytest phases remain the immediate missing proof. Older pending statements below are historical at their own checkpoints.

**Windows strict workflows and selected pytest fixtures pass (2026-11-13; FIX-04/06, API-06/TOOL-01):** [strict matched cohort614](../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json) validates16feature joins/48raw gate checks on exact wheel6de6d77f/source99719f1 with one environmentd664beb3. [Separate installed criterion phase615](../compat/api-acceptance/preparation10-windows-criterion-phases-v1.json) passes the two genuine selected pytest nodes/all6phases, satisfying all16Windows row fixtures;537members/installed origins, zero overlays and ten final zero gauges verify. This pytest process borrows existing test dependencies and does not claim the strict observer fingerprint. Both strict discovery/receipt-extension histories remain retained. Runs614/615 cleaned80,802,081bytes and verified95retained inputs. Windows raw/fixture prerequisites are observed; no selected subject, mandatory-eight-row, final CI or release admission. Current WSL strict/pytest proofs, exact profile/history/retention joins, final-head CI, protected integration and delivery remain pending.

**Current Windows strict matched observations pass (2026-11-13; FIX-04/06, API-06/TOOL-01):** [wheel6de6d77f/source99719f1/preparation10 evidence](../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json) passes both state/resource/failure and capture workflows with one exact environment fingerprintd664beb3. All16feature joins/48raw gate checks validate,537installed members and required shutdown gauges verify; initial discovery and first-replay UNVERIFIED reports remain retained with their receipt extensions. The existing locked CPython/dependency wheels were reused offline; one bounded clean consumer was required by the isolated collector. Run614 cleaned62,904,083bytes/verified71inputs. This is current Windows strict observation, not selected-subject/mandatory-eight-row/CI/release admission. Fresh selected pytest receipts, WSL matched observations, formal bindings/retention and final-head integration remain pending.

**Preparation10 source/scope/reuse approvals bound; full records pass (2026-11-13; FIX-04/06, API-05/06, LIF-01–04, SCI-01–03/05/06 partial):** [independent review609](../compat/api-acceptance/preparation10-peer-review-v1.json) approves exact scope0b668996 and both reuse digests with no blocking changes, independently checking142required obligations,158original rows,272prior files and64criteria/128bindings. Its unread/recomputation limits remain recorded; coordinator separately reproduces execution-scope projection. [Full reviewed source/coverage/execution/selection/native/archive gates now pass](../compat/api-acceptance/preparation10-approved-bindings-v1.json), without changing runtime, scope, reuse digests or validators. Two partial attempts remain failed:611omitted map-hash approval references;612exposed a missing source-local C++ snapshot. Exact existing source bytes521,666are now retained at the required source-local path with both origins protected by [successor registry613](../compat/api-acceptance/preparation10-source-local-binding-v1.json). [282source contracts pass](../compat/api-acceptance/preparation10-reuse-contracts-v1.json). Runs609/610/613 cleaned8,945,534bytes/verified38inputs;611/612created no scratch. Strict installed profiles, required final-head CI, protected integration and delivery remain pending. Two of16selected features (wrapper raster/submission;8criteria) are additive new scope, not parent subsets; all original parents stay required.

**Preparation10 and exact bindings validate, unreviewed (2026-11-13; FIX-04/06, API-06):** [fresh preparation](../compat/api-acceptance/lifecycle-preparation10-wip-v1.json) uses source99719f1, current installed baseline observations and final CI/Metal/Linux pin hashes; scope0b668996. It preserves272prior JSON records and all142original dispositions, with64distinct criteria/128profile bindings. [Both native proofs and both current wheel archives](../compat/api-acceptance/lifecycle-preparation10-bindings-v1.json) validate without compilation, retagging or reassembly. Both actual review gates refuse admission as required; no approvals transfer. Source-only runs607/608 exit0/awaited and create no scratch. Independent source/scope/reuse review, strict profiles, required final-head CI, protected integration and delivery remain pending. Runs604–606 cleanup reclaimed73,387,744bytes and verified221retained inputs.

**Current Metal producers verified and reuse pin renewed (2026-11-13; TOOL-01, PLAT-04 experimental, FIX-04/06):** [both original architectures](../compat/api-acceptance/lifecycle-metal-current-originals-v1.json) validate at exact source99719f1/run43495769632 with whole-run success: original archive/native/configuration, source-before/after, installed CPU imports and producer cleanup. All97original members per architecture are retained by hash; matching files are referenced once, without moving any pinned origin. compat/metal-ci-reuse.json now binds these current producers; no graphics or admission/review approval is inferred. Run606 cleaned25,561,769bytes/verified170retained files. Preparation10 can now freeze against the final pin hashes; reviews, strict profiles, final-head CI and integration remain open.

**SCI-03/E04 two current Windows reference scenes pass (2026-11-13; SCI-05/API-06 partial):** [exact source99719f1/wheel6de6d77f evidence](../compat/api-acceptance/scene-state-current-windows-v1.json) verifies fixed Turntable perspective and coplanar depth/polygon-offset scenes against frozen upstream inputs and criteria. Both observed max differences are0 across71,680pixels;537runtime members/installed origins and ten zero final gauges verify. New test is uncommitted. Camera mutation, broader plane/depth/stencil combinations, other platforms and strict/release admission remain open. Run605 cleaned17,952,038bytes/verified25inputs; no runtime/native rebuild.

**SCI-02/E03 selected WSL filter revisions pass (2026-11-13; SCI-05/API-06 partial):** [Linux wheelb728b575](../compat/api-acceptance/mesh-filter-pending-linux-v1.json), runtime99719f1/test9ac765ab on CPython3.12.13/pinned Mesa9c5 software Vulkan, passes the same four pending-filter cases as Windows. Native pending_draws2→4, all6,144analytic pixels exact,537runtime members/installed origins, zero overlays and ten final zero gauges. Linux additionally verifies561archive members,566installer RECORD entries and manylinux_2_39 tag. Test remains uncommitted; full filter inventory, E04 scene/camera/state and strict/release admission stay open. Run604 cleaned29,873,937bytes and verified26retained inputs; no native rebuild or source overlay.

**SCI-02/E03 native-pending filter revisions verified (2026-11-13; SCI-05/API-06 partial):** [four exact Windows installed cases](../compat/api-acceptance/mesh-filter-pending-windows-v1.json) on runtime source99719f1/wheel6de6d77f use new uncommitted test9ac765ab. Texture replacement/enabled, clipping-plane count+values and detach preserve both expected targets, with native pending_draws2before mutation and4before captures in every case. All6,144analytic pixels match,537runtime members/176loaded origins verify, zero overlays and ten final zero gauges. No runtime/native rebuild or release admission. Earlier constructor/unbound-capture setup failures remain retained; full filter inventory, WSL and scene/camera/state coverage stay open. Runs600–603 cleaned71,604,957bytes/verified101retained inputs; source-only retention generator/copy errors are recorded separately from actual test outcomes.

**SCI-02/E03 before-capture mutations pass (2026-11-13):** [four Windows installed cases](../compat/api-acceptance/mesh-filter-before-capture-windows-v1.json) on source99719f1/wheel6de6d77f match all6,144analytic before/after pixels, with537verified members, installed origins and ten zero final gauges. Renderer/native bytes unchanged. Test source is a new uncommitted file; no broad filter inventory, WSL or release claim. This revision does not yet assert native pending counts; that witness is added next and is unexecuted. Initial constructor/capture-setup failures remain retained. Runs600–602 cleaned53,701,531bytes/verified75retained inputs.

**SCI-02/E03 capture fixture corrected (2026-11-13):** [run601 failure](../compat/api-acceptance/mesh-filter-unbound-capture-v1.json) contains four actual capture assertions and saved transparent before/after images: the test read after pop_fbo without rebinding its targets. FrameBuffer.read samples the active framebuffer. No filter defect established. The corrected test binds each target for capture while retaining both draws before either read. Run601 cleaned17,901,713bytes/verified27inputs; exact failed source, captures and copied-console-message correction are retained. Corrected assertions remain pending; runtime/native/wheels unchanged.

**SCI-02/E03 pending-filter investigation started (2026-11-13):** new four-case source test covers texture replacement, enable toggling, plane-count mutation and detach after an earlier draw and before dependent captures. [Initial attempt](../compat/api-acceptance/mesh-filter-pending-setup-v1.json) fails all four cases at the test's unsupported RenderBuffer format string, before drawing; no renderer defect or pass is established. Exact failed test/logs and zero final gauges are retained. Corrected test uses public color format and fixture-scoped cleanup; its pending-draw assertions are not yet run. Run600 cleaned17,898,000bytes and verified24retained inputs. Native/runtime/wheels unchanged.

**SCI-05/HOST-06 H03 upstream disposition reconciled (2026-11-13):** [source-only evidence](../compat/api-acceptance/h03-upstream-disposition-v1.json) verifies the existing Windows CPython3.12.8/PyQt6/RTX4090 upstream0.17.0 admission, matching fixture/requirements/manifest hashes and corrected reference members. The public Glue FRB invalidation-before-update protocol has an admitted volume_edit reference; the original failed packet remains failed. H03's stale blanket upstream-blocked description is corrected, without transferring historical candidate results to source99719f1/current wheels. Current Glue application/strict host qualification stays open. Run599 exits0/awaited; no rendering, install, native build or scratch was created.

**U05 cleanup completed (2026-11-13; SCI-01/SCI-05):** the unrelated process holding reused PID21404 exited. The original child identity and strict cleanup guard stayed unchanged; [WSL U05 acceptance](../compat/api-acceptance/point-identity-current-linux-v1.json) remains scoped to source99719f1/wheelb728b575/patched Mesa9c5. Run598 cleanup now passes:30,007,097bytes reclaimed,594files removed and27retained inputs verified, including the first zero-delete refusal. No managed scratch remains from this packet. Both selected Windows/WSL point observations pass; broader layouts and qualification remain open.

**SCI-01/SCI-05 U05 WSL installed pass (2026-11-13; API-05/06, SHD-03 partial):** [exact Linux wheelb728b575 evidence](../compat/api-acceptance/point-identity-current-linux-v1.json), source99719f1 on CPython3.12.13/pinned patched Mesa9c5 software Vulkan, passes the same10unchanged tests as Windows: eight rendered cases match all6,144pixels exactly, with analytic/trace/provenance controls,537runtime members, installed origins, zero overlays and ten final zero gauges. Linux archive/RECORD metadata also verifies. This completes both selected local U05 platform observations, not broader point/layout support or strict/release admission. Run598 scratch cleanup is pending: the verifier refused because the awaited child PID21404 has been reused by an unrelated live PowerShell process. Zero files deleted; refusal and observed identity retained. Preserve the guard and wait for that PID to disappear before applying cleanup or starting the next experiment.

**SCI-01/SCI-05 U05 bounded installed pass (2026-11-13; API-05/06, SHD-03 partial):** [current Windows point identity evidence](../compat/api-acceptance/point-identity-current-windows-v1.json), exact source99719f1/wheel6de6d77f, passes10unchanged tests: eight rendered indexed-ID/divisor/constant/ordered-revision cases and two provenance/analytic controls. All6,144pixels match independent references and analytic expectations exactly; trace assertions pass,537runtime members/installed origins verify and ten final shutdown gauges are zero. Seven cases use public Program.draw; nonzero_first_queue is explicitly internal, and the large ID uses constant geometry/inactive count. This replaces U05's stale no-candidate description for this Windows subset only. Broader SCI-01, WSL point checks and strict/release admission stay open. Run597 cleaned18,038,310bytes and verified24retained inputs; no renderer/native change.

**Metal arm64 original verified (2026-11-13; TOOL-01, PLAT-04 experimental, FIX-04/06):** [original capture and cleanup](../compat/api-acceptance/lifecycle-metal-arm64-original-v1.json) verifies CI43495769632 arm64 at exact source99719f1: original archive/native/Mach-O/configuration, source-before/after, installed CPU controls and successful producer cleanup. All97original members are retained once by hash. Local run596 cleaned23,608,182bytes and verified113retained files. The same x86_64 job is still actively building; no restart, whole-run success, Metal graphics, production reuse-pin renewal, preparation10 or review/admission is claimed.

**Both current wheels pass local installed acceptance (2026-11-13; API-05/06, LIF-01–04, SCI-06, SHD-06/PLAT-08 partial, FIX-06):** [Windows6de6d77f](../compat/api-acceptance/lifecycle-current-windows-installed-v1.json) and [Linuxb728b575](../compat/api-acceptance/lifecycle-current-linux-installed-v1.json), exact source `99719f1…`, each pass26selected cases,56Tk baseline cases and composite recovery using one offline installation per platform with separate consumer processes. Each process verifies537runtime members, installed loaded origins, zero source overrides and ten zero shutdown gauges. Linux uses pinned patched Mesa9c5 and additionally verifies561archive members,566installer RECORD entries and its manylinux_2_39 tag. System-Mesa25.2.8 failure stays failed; hidden native controls do not broaden WSI or hardware scope. Runs593–595 cleaned47,766,619bytes and verified72retained inputs in total. Preparation10, independent review, strict-profile admission, final-head CI, merge and delivery remain pending; published wheels are unchanged.

**Current Windows wheel accepted locally (2026-11-13; API-05/06, LIF-01–04, SCI-06, FIX-06):** [exact installed evidence](../compat/api-acceptance/lifecycle-current-windows-installed-v1.json) records wheel `6de6d77f…` from source `99719f1…`: 26 selected tests, 56 Tk baseline tests and composite recovery pass in separate processes on one offline Windows installation. Each verifies 537 runtime members, loaded installed origins, zero source overlays and ten zero shutdown gauges. This closes the current Windows local installed-check packet, not strict qualification, review, merge or delivery. WSL wheel `b728b575…` remains pending. Run593 packaging cleanup removed92bytes/verified15inputs; run594 removed17,898,008bytes/verified28inputs. The source-list preparation NameError is retained; no consumer ran on that failed preparation.

**Active plan refreshed (2026-11-13; API-05/06, LIF-01–07, SCI-01–06, SHD/STA/TEX/LIN, FIX-04/06):** follow the [revised investigation and closure order](superpowers/plans/2026-11-13-remaining-gap-closure.md#revised-investigation-and-closure-order--2026-11-13). Corrected source is pushed at `99719f1…`; [current Windows6de6d77f/Linuxb728b575 archives](../compat/api-acceptance/lifecycle-qt-repackage-v1.json) exist, but their installed acceptance and preparation10/review/CI/integration remain pending. Finish run593 cleanup first; then exact-wheel acceptance, final bindings and integration, stale-route reconciliation, selected lifecycle/scientific/rendering investigations, and optional breadth only for a concrete claim. Metal status must be refreshed from the existing run. This is a planning update: no test, cleanup, approval, closed capability or release claim is added; the published baseline and historical evidence are unchanged.

Latest source correction, 2026-11-13: [review588 requires changes](../compat/api-acceptance/lifecycle-cumulative-review-required-v1.json), with no source/scope/reuse approvals. Hidden native QWidget close and duplicate user resize callbacks are fixed at source scope: [57CPU passes](../compat/api-acceptance/qt-close-state-review-source-v1.json), [26Windows](../compat/api-acceptance/qt-close-state-windows-source-v1.json) and [26WSL source passes](../compat/api-acceptance/qt-close-state-wsl-source-v1.json), including explicit native/readback hidden close and independent pending-DELETE cases. Layout refusal cleanup and extra clear controls are covered. No native rebuild; old wheel/preparation9 evidence stays at its original bytes. Next: update CI selectors before new source/hash freeze, then repackaging, preparation and review. Top-level PyQt6 observations do not establish embedded-parent or other-binding coverage. Runs588–591 cleaned (37,687,548bytes); the intermediate refactor abort remains recorded.

Current binding checkpoint, 2026-11-13: [both native producer proofs and Windows archive prerequisite validate against preparation9](../compat/api-acceptance/lifecycle-producer-bindings-wip-v1.json); missing reviews still block admission. [Linux auditwheel/tag/archive prerequisite passes](../compat/api-acceptance/lifecycle-linux-manylinux-archive-v1.json), with only WHEEL/RECORD changed. Exact manylinux wheel30a40dcb now [passes21selected+56baseline tests and composite recovery on one matched-driver installation](../compat/api-acceptance/lifecycle-linux-manylinux-installed-v1.json), with runtime/metadata/installer RECORD checks and zero gauges. No approvals, strict profiles, CI selection, merge or release transferred. Runs585–587 are cleaned (52,668,442bytes reclaimed); review and final-head integration gates remain next.

Preparation checkpoint, 2026-11-13: [new unreviewed revision9 validates](../compat/api-acceptance/lifecycle-preparation9-wip-v1.json), conserving128selected criteria,142original obligations and260unchanged historical records. Fresh Windows and matched patched-Mesa Linux wheels each pass56baseline Tk tests plus composite recovery; [system Mesa25.2.8 still fails one MSAA capture case](../compat/api-acceptance/lifecycle-linux-system-mesa-msaa-failure-v1.json). This keeps LIF-05/SHD-06/PLAT-08 driver scopes distinct. Reviews/producer/archive bindings, current CI selection and final-head integration remain pending; no admission or delivery. Runs580–584 scratch is cleaned (105,929,160bytes reclaimed).

Latest installed checkpoint, 2026-11-13: [Linux8a793196 passes21selected installed tests](../compat/api-acceptance/lifecycle-linux-installed-selected-v1.json), matching the Windows test selection on sourcef93d80b. Linux verifies537members,57loaded origins,zero source overlays and ten zero shutdown gauges. Native bytes are reused; only the Python wrapper member is repackaged. Both are local candidate observations; formal reviews/profile qualification, required-head CI, merge and delivery remain pending. Run579 scratch cleaned (29,081,532bytes,26retained inputs rehashed); the initial zero-delete live-PID cleanup refusal remains recorded separately from its successful unchanged-plan follow-up.

Current package checkpoint, 2026-11-13: [owned sourcef93d80b pushed](../compat/api-acceptance/lifecycle-owned-source-head-v1.json); [21 Windows installed tests pass](../compat/api-acceptance/lifecycle-windows-installed-selected-v1.json) on candidate977357ad with537verified members,58loaded origins,zero overlays and ten zero shutdown gauges. Earlier native-presentation profile mismatch remains a retained failed attempt; the identical wheel passes explicit readback. No native rebuild, merge or release. Runs576–578 are cleaned (75,535,236 bytes). Next: Linux installed acceptance and formal candidate/CI/integration gates; broader capability parents remain open.

SCI-06 source investigation, 2026-11-13: [eight Windows](../compat/api-acceptance/stencil-public-routes-source-v1.json) and [eight WSL software-Vulkan](../compat/api-acceptance/stencil-public-routes-wsl-source-v1.json) cases pass. Four public stencil forms return exact reference values/crops/types and mutate; four raw calls are explicitly refused and recover through the wrapper. All cases assert nine zero gauges. [Disposition](stencil-wrapper-disposition.md) preserves all eight stock failures without treating them as eight Vulkan defects. Renderer unchanged; installed acceptance remains pending. Minor protocol-test review follow-up also passes90contracts. Both runs are cleaned (45,498,943 bytes reclaimed); managed scratch is empty.

Latest completed gates, 2026-11-13: [90 source contracts](../compat/api-acceptance/linux-protocol-contracts-source-v1.json), [independent protocol review](../compat/api-acceptance/linux-protocol-peer-source-v1.json), [original Linux native/archive proof](../compat/api-acceptance/linux-original-native-archive-v1.json), and [13 current WSL source passes](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json). This advances API-05/06, LIF-01–04 and SCI-06 for the exact selected software-Vulkan profile; parents stay open. No installed successor or release admission. Runs570–573 are cleaned, reclaiming32,221,412 bytes; all managed scratch is empty. Earlier pending/failure notes retain their historical scope. Next are the minor review follow-up, owned-source integration and installed qualification, plus separate investigation of broader public-wrapper gaps.

Latest source gate, 2026-11-13: [90 Linux validation contracts pass](../compat/api-acceptance/linux-protocol-contracts-source-v1.json), including the actual review gate on a consistent minimal source fixture and exact changed-tool refusal. Run570 cleanup reclaimed7,811,625 bytes and rehashed seven retained files. Earlier failing runs remain historical. Review and original retained-capture validation are next; no Linux runtime/installed coverage is promoted.

Protocol source follow-up, 2026-11-13: [88 contract passes / one retained failure](../compat/api-acceptance/linux-protocol-contracts-wip-v1.json). The positive workflow fixture now renews its CI identity consistently. Next repair the historical review-gate fixture's source/tool scope without bypassing the real validator, then obtain review and validate the original retained Linux capture. No artifact admission or new runtime pass is claimed. Run569 scratch is now cleaned: 16,886,403 bytes reclaimed, 13 retained files rehashed.

Planning checkpoint, 2026-11-13: follow the [active investigation queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#active-investigation-queue--2026-11-13) before the older phase order below. First resolve two run569 contract failures (87 pass), review bounded protocol support and validate the retained Linux artifact; then run selected WSL cases, investigate the eight public-wrapper failures and stale fixtures, and select further lifecycle/scientific/rendering cases. Run569 scratch cleanup is pending; earlier all-clean statements predate it. This is a documentation-only plan update, with no new pass, closed capability, artifact admission or release claim. Source, installed and delivered coverage remain distinct.

Latest Linux status: fresh CI43471568101 passed and all166original artifact members are retained. [The native verifier's exact workflow-authority refusal is preserved](../compat/api-acceptance/qt-linux-protocol-equivalence-v1.json): only an inactive reuse-arm candidate selector differs, with fresh producer code byte-identical. Review/implement bounded authority support, then validate the original capture and run WSL cases; no new native build is needed. No Linux source-runtime or installed qualification is promoted from a green CI job alone. All local scratch is cleaned.

Linux renewal is now [actually dispatched on isolated source head82ee](../compat/api-acceptance/qt-lifecycle-source-ci-v1.json), run43471568101. Wait for the existing fresh producer and then test its exact native artifact under WSL; do not rerun Windows compilation or treat queued/running CI as qualification. The published release remains unchanged.

Current native follow-up: [44native CTests and3Windows Vulkan source cases pass](../compat/api-acceptance/qt-lifecycle-windows-native-v1.json). The parsed-DELETE retirement defect is resolved on the rebuilt Windows leaf: live and pending-snapshot shared-peer cases both render exact pixels and end with all nine zero gauges. Build and GPU scratch is cleaned. Linux native renewal, successor installed qualification and broader lifecycle boundaries remain open.

Latest follow-up: [53CPU checks pass](../compat/api-acceptance/qt-lifecycle-review-followup-v1.json), including first-show initialize/resize ordering and pending callback-error identity. Independent review accepts the native parsed-DELETE cleanup for bounded compilation; it is not yet compiled. The pending peer-snapshot GPU test is added, not passed. Keep native/installed, embedded-parent, actual loss and broader lifecycle items open.

Post-release source work is in progress: [native-close/shared-context CPU follow-up](../compat/api-acceptance/qt-lifecycle-source-followup-v1.json) passes50cases. Windows GPU shared-peer recovery renders correctly but exposes24CPU/GPU-buffer bytes retained after explicit deletion/last close; the pending-DELETE cleanup patch is uncompiled and under review. This updates API-05/LIF-01–04 partially; it does not extend the published wheel's claims or close the parents.

Next work is organized in the [remaining-gap investigation and closure plan](superpowers/plans/2026-11-13-remaining-gap-closure.md): bounded startup diagnosis, lifecycle reliability, selected scientific workflows, then rendering breadth. Planning does not change any open coverage status or require full parity.

The selected `0.17.0+vulkan.2` release is published and its public delivery checks pass. [GitHub Release](https://github.com/bipxx/vispy_vulkan/releases/tag/v0.17.0-vulkan.2), [PEP503 index](https://bipxx.github.io/vispy_vulkan/simple/), [exact delivery evidence](../compat/api-acceptance/successor-public-delivery-v1.json).

- **FIX-04 — Integrated:** PR75 merged as `fc3b9734bbaf2af801e7b3bc81bbc352e5525708` after all eleven protected integration checks passed. Its tree preserves the qualified runtime, tools, workflows and policies; the other owner's index is unchanged.
- **FIX-06 — Qualified and delivered:** all 128 selected Tk criteria, eight mandatory VisPy-only Windows/WSL profiles, all 23 required jobs at implementation head `3ada644e85248bcae214e7e487b4b1684336fd8f`, independent final promotion and strict admission pass. Product source remains `b38c4f9068d6a425eef43b62313f0f4cf37f57d9` and the two exact wheels are unchanged. [Admission](../compat/api-acceptance/revision8-final-admission-v1.json).
- **Actual public channel:** Windows verifies 537 members, zero source overrides and an exact 64×64 Vulkan clear. Linux verifies 537 members, zero source overrides and native ABI import; its delivery smoke makes no new GPU claim. The four-link index preserves both vulkan.1 assets. AGPL, original BSD and dependency notices remain attached.
- **Hygiene and failures:** temporary installs are removed; 167,250,056 bytes reclaimed and 44 retained files rehashed. The draft lookup 404, connector 403 and Linux receipt collision remain recorded with their recoveries. The 18 legacy inputs remain protected at original origins; the manually reviewed mandatory retention boundary and its unchanged generic-verifier refusal are preserved separately from the Tk 599-input verified retention.

This closes the selected successor release, not all 142 broader compatibility obligations. Optional API/rendering/host/platform breadth remains explicitly tracked below. Metal graphics, physical Linux GPUs, other ABIs/architectures, full API/raster parity and laboratory latency remain outside the accepted release claim. See the [completion audit](selected-release-completion-audit.md).

## Historical progress checkpoints

These checkpoints retain their original source, artifact and review scope; the current status above supersedes their pending-work descriptions.

Metal reuse dependency fix (2026-11-13; TOOL-01 / FIX-04): arm64 CI reached repackaging but lacked the pure Python version validator `packaging`. An isolated no-site probe reproduces the failure; the existing129,956-byte locked packaging26.3wheel fixes it. The reuse workflow now exports/installs only that dependency, preserving hashed installation and the1GiB reuse budget. [Evidence](../compat/api-acceptance/metal-reuse-dependency-fix-v1.json). No wheel/SDK rebuild or new venv. All608runtime references remain unchanged. Successor preparation/policy renewal, independent reviews, CI and promotion remain pending; old reviewed records stay frozen. No admission.

Oracle-provenance head (2026-11-13; FIX-04): corrected test pushed as `4c39ff7f4d3b51c1a9f4c52475924f9c1a781b27`; the original capture producer is confirmed tracked byte-exact, all608runtime references and the other owner's index unchanged. Required reuse CI dispatched: CPU43404591396, Linux43404594197, Metal43404597011. [Freeze and CI evidence](../compat/api-acceptance/oracle-provenance-head-v1.json). The existing128-criterion subject proof remains scoped to head9cf; final-head renewal, independent follow-up/impact/promotion review and CI completion remain open. No admission.

Oracle comment correction (2026-11-13; FIX-04): independent review confirmed the provenance assertions preserve acceptance, but requested a comment correction. The actual collector change is candidate-version resolution; historical failure handling was already present. Corrected bytes pass18checks and have an identical executable AST to the512-case passing version. The exact-byte follow-up failed authentication (403), not a test or approval decision; no approval transferred. [Evidence](../compat/api-acceptance/frozen-oracle-comment-followup-v1.json). Branch CI may proceed; independent follow-up/final impact review and promotion remain pending.

Hosted CPU failure isolated (2026-11-13; FIX-04): Linux/macOS final-step logs show one historical oracle producer-hash mismatch (508 passes). The reference check now binds the existing byte-exact frozen capture authoring source rather than the newer live collector; all original oracle/provenance bytes remain unchanged. Eighteen reference checks, including three relabelling/source-tampering controls, and the full 512-case final CPU group pass locally on Windows CPython3.12.8. [Evidence](../compat/api-acceptance/frozen-oracle-producer-fix-v1.json). All 608 runtime references and candidate preparation tools remain unchanged; independent test-delta review and new-head CI remain pending. No artifact admitted.

Installed subject proof (2026-11-13; FIX-04): all 128 selected criteria prove end to end with zero missing or blocked joins, using the original native/archive/strict installed reports, six-attempt histories, reviewed failure disposition and 601-input contributing retention. [Evidence and reconstruction](../compat/api-acceptance/installed-subject-proof-v1.json). The temporary overlay was validated and the frozen preparation restored byte for byte. No artifact admitted. Head9cf Linux Vulkan reuse passed; the CPU matrix has failures in its final assertion step, still under diagnosis. Required CI completion, independent impact/promotion review and integration remain open. The 142 broader original requirements remain conserved, not claimed complete.

Installed bindings (2026-11-13; FIX-04): all 32 selected feature/profile rows validate against the two exact matched environment fingerprints, including 128 criteria and 96 raw gate joins. Thirty-two source-local receipts and two derived distribution audits are linked through a small reconstructible overlay; the frozen preparation ledger is unchanged. [Evidence](../compat/api-acceptance/installed-proof-bindings-v1.json). Separate same-wheel installed pytest phases retain their own scope. Original 142 requirements remain incomplete. Contributing retention, final subject/proof review, head CI and promotion remain open; no artifact admitted.

Qualification head (2026-11-13; FIX-04): reviewed source pushed as `9cf488acdae59ae3b80310ab2a19b5bcc4915a54`; all 608 runtime/build/lock/license references and the other owner's Git index remain unchanged. The 23 required jobs are dispatched at that exact head in native reuse mode (CPU43400135712, Linux43400153578, Metal43400158627). [Freeze and CI evidence](../compat/api-acceptance/qualification-reuse-head-v1.json). CI completion, final installed proof bindings and promotion remain pending; no artifact admitted.

Independent review (2026-11-13; FIX-04 / TOOL-01): revision7 source and finite scope are independently approved, including native CI reuse. The Windows receipt-refresh failure has an approved disposition and remains failed/UNVERIFIED in its complete history; the flagged inventory files are byte-identical. The fully reviewed Linux reuse path and original driver now validate, with zero Python reassembly changes. [Decision and exact bindings](../compat/api-acceptance/successor-peer-review-v4.json). Final installed bindings, frozen-head 23-job CI and promotion remain pending; no artifact admitted.

CI reuse repair (2026-11-13; TOOL-01 / FIX-04, source-tested): 1,117 compatibility contracts pass on Windows CPython 3.12.8. The three successful head340 native artifacts validate against current inputs and are pinned for reuse; Metal dispatch/managed-layout checks and reviewed-successor Linux selection have 116 focused passes. CPU event values now run after compilation. Transport cleanup removed 92,206,020 bytes and rehashed 286 retained files. [Evidence](../compat/api-acceptance/native-ci-reuse-repair-v1.json). Revision7 remains unreviewed; source-head CI, final installed bindings and promotion are pending. No native rebuild or artifact admission.

Exact-profile histories (2026-11-13): scan of15,217retained JSON files finds
6strict attempts for the selected wheels, exact matched fingerprints and candidate
workflows, with0unattributed current-wheel reports. Four latest workflow selections
and3contributing retention envelopes validate (62/94/80retained inputs).
[Evidence](../compat/api-acceptance/matched-profile-histories-wip-v1.json). One Windows UNVERIFIED receipt-refresh attempt
still needs independent disposition. Historical variants/other workflows stay
disclosed. Profile/receipt bindings, producer retention, review/CI and promotion
remain pending; no row or artifact admitted.


Matched WSL cohort (2026-11-13): state/failure and capture pass strict replay
in one identical consumer fingerprint, with537verified members, zero overlays
and9zero gauges. All16feature joins/48gate checks validate ([evidence](../compat/api-acceptance/wsl-matched-cohort-v1.json)).
Both platforms now have matched pairs (32joins/96checks) without collapsing
the old mismatched environments. Existing Python/driver/dependency sources were
borrowed read-only; no wheel/SDK build. Final profile/receipt/history/retention
bindings, revised review, head CI and promotion remain pending; no admission.


Matched Windows cohort (2026-11-13): state/failure and capture both pass strict
three-gate replay in one identical consumer fingerprint, with537verified members,
zero overrides and9zero shutdown gauges. All16Windows feature joins/48gate
checks validate ([evidence](../compat/api-acceptance/windows-matched-cohort-v1.json)). The intermediate unverified
receipt-refresh attempt is preserved. The original handle baseline remains in
place; its exact bytes/origin are retained in a small input archive. No SDK or
wheel was rebuilt, and no row admitted. WSL matching, final profile/history/
retention bindings, source/scope review, required CI and promotion remain open.


Provisional installed joins (2026-11-13): all32feature/profile pairs validate
three original observer gates and their installed pytest fixtures (96gate checks,
4original bundles). [Evidence](../compat/api-acceptance/installed-proof-joins-wip-v1.json). No rows/profiles admitted:
Windows state/capture use builds26200/26300; WSL kernels6.18.54/6.18.58 differ and
capture has5extra Python distributions. Replay each pair in one matched consumer
per platform rather than collapse distinct fingerprints. Raw reports and both
existing byte-identical inventory origins remain untouched. Complete histories,
retention, final profile/receipt bindings, review/CI and promotion stay pending.


Current-preparation verification (2026-11-13): all1,088 compatibility-contract
cases pass locally on WindowsCPython3.12.8 with the new fixture resolving the
explicit revision7CI selection. [Evidence](../compat/api-acceptance/current-preparation-contracts-v1.json). Historical
default refusal and strict review/scope controls remain intact; revision7
approvals, source-head CI and installed proof joins remain pending.


Compiler follow-up (2026-11-13): the existing CMake/MSVC profile passes the
real CPU cache shutdown-wrapper contract. Configure, build and executable exits
are0 and awaited; sources, commands and licenses are retained under a128MiB
managed lease ([evidence](../compat/api-acceptance/upload-shutdown-compiler-v1.json)). This closes run499s local
missing-PATH/compiler check; its902source passes and this1native pass remain
separate receipts. No installed graphics/native artifact qualification is claimed.
Revision7review, current-preparation contracts and hosted CI are still pending.


CI source grouping repair (2026-11-13): six benchmark files now run in a
separate provider-free process; all434cases pass with the strict import guard
unchanged. Scientific/event selection has902passes and1 local compiler-profile
setup failure (existing CMake is not on PATH). CPU event values are explicitly
classified in CI. Test fixtures resolve the explicit CI preparation rather than
hardcode a historical revision. Revision7preparation/128closure validates with
all164prior candidate records unchanged; independent revised approvals and
compatibility rerun are pending. [Partial evidence](../compat/api-acceptance/ci-source-grouping-repair-wip-v1.json).
The compiler contract needs managed existing-toolchain verification before a
full scientific pass claim; no runtime, wheel or artifact admission changed.


Hosted CI grouping findings (2026-11-13): corrected head340499b0 passes the
compatibility step on observed LinuxCPython3.10.19, then reports1,305 scientific
passes,2 failures and1 teardown error. Metrics import-isolation guards share a
process with legitimate provider-import tests; test_event_values is missing
from CI classification. [Failure evidence](../compat/api-acceptance/qualification-ci-grouping-failure-v1.json). Split those
processes, keep import guards, add CPU event fixtures and renew affected pins.
Native fresh builds are ongoing; no admission is claimed.


Corrected qualification head (2026-11-13): `340499b0ff81ca12dddf04b763477c93737fde89`
is frozen, pushed and bound by the detached subject. All23 required jobs are
dispatched on this exact head; Linux and experimental Metal use their existing
explicit fresh6GiB production profiles because original native inputs differ.
[Head, requests and run identities](../compat/api-acceptance/qualification-ci-correction-v1.json). Only tests, docs and
evidence changed since `152183d0…`; reviewed tools, candidate scope, all608 runtime
references and selected wheels are unchanged. Local WindowsCPU selection passes
1,088 cases; hosted results, installed proof joins and promotion remain pending.
Earlier failed-head evidence is preserved and does not qualify the corrected head.


CI fixture repairs (2026-11-13): the full compatibility-contract file selection
from the CPU workflow passes 1,088 cases locally on WindowsCPython3.12.8.
Current selection/review-gate/capture tests use revision6; frozen defaults retain
an explicit stale-tool refusal. Metal synthetic metadata declares project/version.
Capture corruption cases have a positive control first. All164 candidate JSON
records, validators and runtime bytes are unchanged. [Evidence](../compat/api-acceptance/ci-contract-fixture-fixes-v1.json).
The first focused run retained312passes/1missed old-runtime failure before its
correction. Hosted validation on the corrected head remains pending; fresh Linux
and experimental Metal production decisions are recorded separately.


Linux CI reuse disposition (2026-11-13): hash-verified artifact diagnostics
confirm the guard correctly refuses changed `cpp/runtime.cpp` bytes. The next
corrected source head will use the existing explicit `native_mode=fresh` route
(6GiB declared peak, managed lifecycle), not alter historical pins or relax reuse.
[Changed-input decision](../compat/api-acceptance/linux-ci-fresh-decision-v1.json). This is hosted source-head CI;
selected local wheels and their native producers remain unchanged. Fresh CI
execution and source-head success are still pending.


Required head CI findings (2026-11-13): Linux CPython3.12.8 reports 1,078
contract passes and 16 failures: nine stale candidate expectations, six incomplete
Metal metadata fixtures and one native-input pin expectation. Software Vulkan
also fails in original-native reuse; its retained child details need inspection.
[Failure evidence](../compat/api-acceptance/qualification-ci-failures-v1.json). Other jobs are still pending in this
snapshot. These failures block required CI; no job or validator is waived.


Required qualification CI dispatch (2026-11-13): reviewed head `152183d0…` was
pushed to `wip/qualification-reviewed-492`; all three policy workflows are
authoritatively queued/running with exact head and attempt identities retained
([runs](../compat/api-acceptance/qualification-head-ci-wip-v1.json)). All 23 jobs remain required. Dispatch is not a
passing CI result or artifact admission; preserve failures and rerun histories.


Qualification implementation freeze (2026-11-13): `152183d0e3d737bf036d0baad2c0981ab6fe981c`
binds 5,924 source files, including the reviewed tools, CI workflows, named tests
and qualification collector. All 608 runtime/build/lock/license references retain
product source `b38c4f9068d6a425eef43b62313f0f4cf37f57d9`. The subject is
now bound to this head as a detached local proof overlay. [Evidence](../compat/api-acceptance/qualification-source-freeze-v1.json).
The other checkout/index was preserved; only a private index was used. Initial
Windows argv-limit verification failure is retained; bounded-prefix verification
passes against the existing commit. Required hosted CI and installed proof joins
remain pending; no artifact is admitted.


Revision6 source/scope review (2026-11-13): independent decisions are approved
and bound to candidate, coverage, execution, admission closure and both native
reuse digests. [Decision](../compat/api-acceptance/successor-peer-review-v3.json). All four preparation validators
require and pass the new reviews; both original native producer joins validate.
Scope digests, runtime, fixtures and wheels are unchanged. No installed rows or
artifacts are admitted. Qualification Git head, installed receipt/history/retention
bindings, required hosted CI and promotion remain open.


Installed criterion receipt update (2026-11-13): both exact mapped pytest fixtures
pass on each selected Windows/WSL wheel, with all six setup/call/teardown events
per platform, 537 member checks, zero source overrides and zero shutdown gauges.
[Evidence](../compat/api-acceptance/installed-criterion-phases-v1.json). These fresh phase receipts close the missing
pytest-report format; qualified row/retention joins remain pending.


### Historical preparation — revision6 (2026-11-13)

`tk-state-resource-6` renews the independently approved qualification-tool
identities. Its 64 criteria / 128 profile bindings and prerequisite closure
validate; all earlier candidate records and 608 runtime/build/lock/license
references remain byte-exact. CI now explicitly selects revision6, validates
its admission selection and runs retained-evidence tests. All 23 required
jobs remain required. Five preparation CLIs pass locally; CI/retention
contracts pass 102 cases. [Evidence](../compat/api-acceptance/qualification-candidate-renewal-v1.json).

This is an **unreviewed preparation**, not installed or release qualification.
The subject now declares the store selector; producer references await new
candidate source/scope decisions. Qualification Git head, complete installed
histories/receipts/retention, required hosted CI and promotion remain open.
No native build, installation, artifact admission or new scratch occurred.
The earlier checkpoints below retain their original date and byte scope.



### Qualification-tool follow-up — 2026-11-13

Independent follow-up approves the exact eight tool/schema/test hashes for candidate
renewal only ([decision](../compat/api-acceptance/qualification-tools-followup-v1.json)). Coordinator rehashed those bytes; the review child
exited 0 and was awaited. Prior 372 contract passes and 6 focused passes remain
source evidence; no wheels were rebuilt or admitted. Renewed candidate/source/scope
bindings, the subject store selector, complete installed histories/receipts and
real producer retention remain pending. CI must select the renewed preparation
records **and run `tests/contract/test_retained_evidence.py`**, then renew its
workflow policy hash. No required job is waived. Low review limits (Windows
transitive retention, early-failure attribution and incremental failure reporting)
are recorded in the decision; they are not broader coverage claims.

Reviewed **2026-11-13** against local source, the
[coverage checklist](coverage-checklist.md), acceptance manifests and the
[consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md).
This is the concise execution view; those records retain detailed evidence and
stable IDs. An unchecked item can mean missing verification or disposition,
not necessarily missing implementation. Exact test scopes are linked below.

The [coverage gap review](coverage-gap-review-2026-11-08.md) identified three
current-wheel refresh needs. They are now closed: 57 event, 39 Tk input and
30 depth cases pass per platform on the latest wheels, with original cases and
source pins preserved. [Fresh exact-artifact evidence](../compat/api-acceptance/current-event-input-depth-v1.json)
is separate from the unchanged older results. The 32 literal-sampler cases are
also already included in current passing suites. Independent review and
installed/profile qualification remain the next release work.

The target remains practical VisPy compatibility. Full upstream parity, exact
OpenGL rasterization and laboratory display-latency parity are not required.
Optional scope below does not become a release requirement by appearing here.

## Current baseline

- Published release: `v0.17.0-vulkan.1`. Its approvals retain their original scope.
- Selected experimental successor: `0.17.0+vulkan.2`, Windows wheel `a86b030b…`
  and Linux wheel `48164e05…`, with current Tk, both headless, all three Windows Qt and all three WSL Qt observations.
- Earlier successor wheels `ba8a54c5…` / `4bc3cd77…` retain 75 sampler cases, 120 numeric
  uniform-array cases, and 285 attribute cases per platform across separate
  retained runs. These are finite suites, not exhaustive API coverage.
- See [samplers](../compat/api-acceptance/dynamic-explicit-samplers-wip.json),
  [uniforms](../compat/api-acceptance/uniform-arrays-v1.json) and
  [attributes](../compat/api-acceptance/attributes-v1.json) for exact hashes,
  values, platforms, failures and cleanup. Local functional passes do not
  supply successor review, strict-profile admission or release approval.

## Latest closed bounded task

- [x] **FIX-06-NATIVE-JOIN (2026-11-13):** original Windows402 and Linux414
  producer joins validated against the reviewed revision-5 records; both producer
  references were bound to the subject before the qualification-tool change.
  [Evidence](../compat/api-acceptance/qualification-binding-wip-v1.json). No artifact admission.
- [x] **FIX-06-WORKFLOW-ATTEMPT-SOURCE (2026-11-13):** optional per-workflow
  latest-success selection is implemented, preserving legacy subjects. Nine new
  selection/integration cases reject stale failures, omitted/duplicate workflows,
  incomplete histories and swapped runtime reports; 52 focused contract cases pass.
  Full-file run also retains one stale historical preparation-toolset failure.
  This is source-tested qualification tooling, not installed-wheel admission.
- [x] **FIX-06-EVIDENCE-ADAPTER-SOURCE (2026-11-13):** explicit secondary-store
  raw report references and mixed-root retention are implemented. Both original
  WSL state/resource and capture reports normalize all three gates. The original
  WSL cleanup validates all 80 inputs, including four exact archived documents.
  Source-local checks and all original report bytes remain intact.
  [Evidence](../compat/api-acceptance/secondary-evidence-adapter-wip-v1.json).
  Broad contracts: 344 pass; archive follow-up: 99 pass; final opt-in guard: 2 pass.
  Frozen-record tests retain scope and now reject stale current-tool claims.
  These are source-tool and retained-evidence joins, not artifact admission.
- [x] **FIX-06-EVIDENCE-BINDINGS (2026-11-13):** finite revision8 Tk subject binds complete six-attempt histories, separate installed pytest phases, distribution receipts and599-input contributing retention for the selected wheels. [Exact128-criterion proof](../compat/api-acceptance/revision8-installed-subject-v1.json). No full inventory or release admission.
- [x] **FIX-06-TOOL-REVIEW-FIXES-SOURCE (2026-11-13):** resolved-failure
  profile/wheel context, native/store namespaces and source-side scratch handling
  are fixed. Early failures have history-bound workflow attribution; derived
  cleanup views are checked against original process/result bytes. Full source
  contracts pass 372 cases; exact error follow-up passes 6. Both WSL reports and
  the 80-input cleanup still validate; native input joins check 245 Windows and
  167 Linux references. [Fix evidence](../compat/api-acceptance/qualification-tool-fixes-wip-v1.json).
- [x] **FIX-06-TOOL-FOLLOWUP-REVIEW (2026-11-13):** independent review approves
  the exact eight tool/schema/test hashes for candidate renewal only. Coordinator
  rehashed them. [Decision](../compat/api-acceptance/qualification-tools-followup-v1.json).
  Run486 remains authoritative for its old hashes; candidate reviews are pending.
- [x] **FIX-06-CI-PREPARATION-WIRING (2026-11-13):** CPU workflow explicitly
  validates revision6 preparation, coverage, execution and admission selection;
  retained-evidence tests are included and exact policy hash renewed. Five CLIs
  pass locally, 102 CI/retention contracts pass; all 23 required jobs are preserved.
- [x] **FIX-06-CI-EVIDENCE-DELIVERY (2026-11-13):** all23required jobs at head3ada validate against complete original history/run/jobs/checkout identities. [Evidence](../compat/api-acceptance/revision8-required-ci-v1.json). Independent final promotion and strict admission remain separate.
- [x] **FIX-06-QUALIFICATION-TOOL-REVIEW (2026-11-13):** exact tool follow-up
  and renewed revision6 source/scope decisions approved; new candidate identities
  and native joins validate. Revision5 approvals retain their original scope.
- [x] **FIX-06-INSTALLED-PYTEST-PHASES (2026-11-13):** both mapped fixtures pass
  on each selected wheel with complete setup/call/teardown records; 537 members
  verified, zero source overrides and shutdown gauges. [Receipts](../compat/api-acceptance/installed-criterion-phases-v1.json).
- [x] **FIX-06-QUALIFICATION-HEAD (2026-11-13):** isolated commit `152183d0…`
  freezes tools, CI and tests; 5,924 source-file blobs verified, 608 runtime refs
  unchanged, original index preserved. Subject head bound; hosted CI still pending.
  [Freeze evidence](../compat/api-acceptance/qualification-source-freeze-v1.json).
- [x] **FIX-06-INSTALLED-ROW-JOINS (2026-11-13):** all32selected Tk rows/96raw gate joins and128criteria prove at head3ada, using exact matched platform fingerprints and complete retained histories. [Proof](../compat/api-acceptance/revision8-installed-subject-v1.json). Eight mandatory matrix observations and final admission remain separately scoped.

- [x] **FIX-06-REVIEW-SCOPE-REPAIR:** merged capture into
  `tk-state-resource-5` with an enforced current-target prerequisite chain;
  corrected the four textured-program values and proposal; explicitly excluded
  experimental native presentation. Existing validators pass all 128 criteria
  with closure 128 and both archive prerequisites. Runtime/fixtures/wheels and
  all earlier candidate records are unchanged. [Scope repair](../compat/api-acceptance/tk-scope-repair-v1.json).
- [x] **FIX-06-REVISED-REVIEW (2026-11-13):** independent source and scope
  decisions are approved and bound to `tk-state-resource-5`. Candidate, coverage,
  execution and 128-criterion selection pass their review-required verifiers.
  Scope hashes are unchanged; no artifact is admitted. [Review evidence](../compat/api-acceptance/successor-peer-review-v2.json).
- [x] **FIX-06-CAPTURE-REBIND-WINDOWS (2026-11-13):** reviewed five-feature
  capture recipe passes fresh three-gate replay on wheel `a86b030b…`; same-child
  `tk-capture-1` validates all four branches, 537 members and nine zero counters.
  [Evidence](../compat/api-acceptance/tk-capture-rebind-windows-v1.json). No admission.
- [x] **FIX-06-CAPTURE-REBIND-WSL (2026-11-13):** reviewed five-feature
  capture recipe passes fresh three-gate replay on wheel `48164e05…`; same-child
  `tk-capture-1` validates all four branches, 537 members and nine zero counters.
  [Evidence](../compat/api-acceptance/tk-capture-rebind-wsl-v1.json).
- [x] **FIX-06-CAPTURE-REBIND:** both reviewed platform recipes now pass.
  The earlier WSL Drvfs setup failure is retained and cleaned; bounded POSIX
  temporary storage and borrowed read-only dependencies resolved the installer
  filesystem issue. Observations still need execution-attempt/subject bindings.

- [x] **FIX-06-WSL-PYSIDE6-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. Dependencies
  were borrowed read-only, with only the selected wheel in a private bounded overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyside6-v2.json). **All eight host-row observations collected.** Independent
  review and formal admission remain pending.

- [x] **FIX-06-WSL-PYQT6-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. The retained
  PyQt6 dependencies were borrowed read-only, with a private selected-wheel overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyqt6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WSL-PYQT5-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. Dependencies
  were borrowed read-only; only the selected wheel used a private bounded overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyqt5-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYSIDE6-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget stages, including rendering/capture ownership,
  parent/show/resize, overlays and input, hide/restore, device recovery and close.
  Installed inventory and fresh replay pass all three graphics gates; 537 package
  members and nine zero shutdown gauges are verified. Retained selected Qt wheels
  were installed offline without native builds.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyside6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYQT6-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget stages, including rendering/capture ownership,
  parent/show/resize, overlays and input, hide/restore, device recovery and close.
  Installed inventory and fresh replay pass all three graphics gates; 537 package
  members and nine zero shutdown gauges are verified. Retained selected Qt wheels
  were installed offline without native builds.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyqt6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYQT5-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget probe stages: exact installed payload and Vulkan device,
  parent/show/resize, capture/update ownership, overlays and input, hide/restore,
  device-loss recovery and close. Installed inventory and a fresh replay pass all
  three graphics gates; 537 members and nine zero shutdown gauges are verified.
  The retained selected Qt profile is installed offline without a native build.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyqt5-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WSL-HEADLESS-OBSERVATION:** the Linux wheel passes 95 GPU tests,
  rendering/compiled text, 4,096 markers and 36 scientific cases on pinned
  software Vulkan. Installed inventory and fresh replay pass all three gates,
  with 537 members verified. Dependencies are reused read-only, with only the
  selected wheel installed into a private overlay. The original pytest capture
  failure is retained; bounded POSIX temporary storage fixes its file semantics.
  [Observation packet](../compat/api-acceptance/mandatory-wsl-headless-v2.json).
  **All eight host-row observations collected.** No admissions transfer.

- [x] **FIX-06-WINDOWS-HEADLESS-OBSERVATION:** the current Windows wheel passes
  95 GPU tests, rendering/compiled text, a 4,096-marker scene and 36 scientific
  cases with the existing value/pixel oracles. Installed inventory and fresh
  replay pass all three graphics gates; 537 members and zero-resource cleanup
  are checked. [Observation packet](../compat/api-acceptance/mandatory-windows-headless-v2.json).
  Both headless observations are collected. Canonical matrix entries and
  admissions remain unchanged; all eight row observations are collected.

- [x] **FIX-06-WSL-COLLECTOR:** resolved the stale native collector mismatch.
  The old binary lacks the complete-record parser in frozen source and fails
  its fragmented-record controls. An unmodified-source rebuild passes all 20
  controls. Original binary/evidence retained; shipping source and wheels unchanged.
- [x] **FIX-06-TK-WSL-OBSERVATIONS:** all four workflows pass all three graphics
  gates in fresh installed replays on Linux wheel `48164e05…`. Each worker
  verifies 537 members with zero overrides. All workflows use the refreshed
  collector and one offline consumer. [Current packet](../compat/api-acceptance/tk-strict-wsl-v2.json).
  Independent source/scope review, candidate admission and formal admission of
  the eight mandatory host rows remain open. No previous approvals transfer.
- [x] **FIX-06-TK-WSL-OBSERVATIONS-PARTIAL:** earlier three-workflow and
  diagnostic packets remain historical, with failed attempts preserved.

- [x] **FIX-06-TK-WINDOWS-OBSERVATIONS:** all four pinned Tk candidate workflows
  pass installed dependency inventory and fresh replay with all three graphics
  gates on Windows wheel `a86b030b…`. The existing interpreter, native outputs,
  observer and offline dependency wheels were reused; the small managed consumer
  is disposable. [Exact reports and scope](../compat/api-acceptance/tk-strict-windows-v1.json).
  This closes the Windows observation collection step only. Candidate admission,
  independent review and eight mandatory host rows remain open.

- [x] **LIF-07-NATIVE-WHEELS:** new experimental Windows `a86b030b…` and Linux
  `48164e05…` wheels contain native Tk at source `b38c4f90`. Each passes 186
  installed cases, with 537 package members verified and zero source overrides.
  Functional validators and five active capture controls pass per platform.
  WSL native and raster checks use separately identified existing drivers;
  failed MSAA and stale-harness attempts remain retained. All six packaging/test
  scratch directories are cleaned. [Evidence](../compat/api-acceptance/tk-native-installed-v1.json).
  Candidate revision 4 renews preparation only. Next: independent source/scope
  review, then the unchanged strict installed/profile admission requirements.

- [x] **LIF-07-NATIVE-PROTOTYPE — Optional native Tk source prototype:**
  seven cases pass per Windows/WSL-X11 source overlay. Tk raster stays default;
  native mode avoids PhotoImage readback and uses the existing Vulkan surface
  APIs. WSL uses an explicitly hashed existing X11-capable system driver; the
  pinned headless clipping driver is unchanged and cannot present to X11.
  Both prototype proof and all failed/intermediate scratch are retained/cleaned.
  [Usage and exact limitations](tk-native-presentation.md). This historical
  source-overlay result is superseded for packaging by the installed task above;
  independent review and release qualification remain open.

- [x] **Current event/input/depth refresh:** all 126 cases pass on each current
  wheel using one offline installation per platform. All 537 installed members
  are checked per child; event semantics load no renderer/backend, while input
  and depth processes each retire ten resource gauges to zero. Both targets
  are removed (47,751,307 bytes), with 26/28 retained entries rehashed.
  [Finite scope and evidence](../compat/api-acceptance/current-event-input-depth-v1.json).

- [x] **SHD-05-BOUNDARIES — Seven generated-line refusal/recovery cases.**
  [The test](../tests/shaders/test_line_side_effect_boundaries.py) covers
  vertex storage writes, clip distance, fragment storage writes, atomics,
  image stores, barriers and early fragment tests. It expects explicit refusal
  followed by a valid draw on the same canvas. All seven pass without skips on
  Windows wheel `ba8a54c5…` and WSL software Vulkan wheel `4bc3cd77…`.
  Each process verifies 537 installed members, 56/55 loaded module origins,
  the expected recovery pixels and ten zero shutdown gauges. No native build
  or new dependency environment was needed. Both scratch targets are removed
  (47,751,313 bytes), with 15/17 retained entries rehashed. The earlier storage
  refusal remains a separate failed preflight, not a test result.
  [Exact acceptance and durable evidence](../compat/api-acceptance/line-side-effect-boundaries-v1.json).
  Parent SHD-05, independent review and strict-profile/release admission remain
  open. The next release prerequisites are cumulative review and installed/profile
  qualification below; record preparation is complete. Optional implementation
  work must select another finite scope.

## Successor release completion

- [x] **FIX-04-REVIEW — Independent source/scope review:** exact revision8digests and both native-reuse links are bound. [Decision](../compat/api-acceptance/successor-peer-review-v5.json). Corrected oracle test is independently approved; no transferred approvals or proof/admission claim.
- [x] **FIX-04 / FIX-06 — Final provenance/subject binding (2026-11-13):** revision8subject proves128/128criteria at head3ada using the exact32-row overlay, complete six-attempt histories and599-input contributing retention. Independent change-impact approval is bound; frozen preparation restored. [Current proof](../compat/api-acceptance/revision8-installed-subject-v1.json). Original producers, SDK origins, failures and notices stay intact.
- [x] **FIX-06-OBS — Current mandatory-profile observations collected:** all8Windows/WSL headless/PyQt5/PyQt6/PySide6 observations exist on the selected wheels. [Exact observation scope](../compat/api-acceptance/mandatory-current-wheels-observations-v2.json). Their later scoped admission is recorded separately in [revision8final admission](../compat/api-acceptance/revision8-final-admission-v1.json); the original observation packet remains unchanged.
- [x] **FIX-04-PROOF — Prior finite installed subject proved:** head9cf/revision7has128provedcriteria, zero missing/blocked joins, six complete attempts and601contributing retained inputs. [Proof](../compat/api-acceptance/installed-subject-proof-v1.json). Revision8renewal is now separately proved at head3ada; this prior record remains historical. No fresh graphics replay is justified without changed critical inputs.
- [x] **FIX-06 — Final promotion/admission (2026-11-13):** independent exact-basis approval and actual unchanged strict verifier admit128Tk criteria; eight selected mandatory rows have separate final approval/admission. Frozen preparation restored. [Evidence](../compat/api-acceptance/revision8-final-admission-v1.json). Protected integration and publication remain open; no all-API claim.
- [x] **FIX-04 — Integrate (2026-11-13):** protectedPR75 merged as `fc3b9734…`; qualified source tree and other owner index preserved.
- [x] **FIX-06 — Public delivery (2026-11-13):** the two exactvulkan.2wheels, four-link index and Windows537-member/Vulkan-clear plus Linux537-member/ABI-import channel checks pass; temporary installs cleaned. [Actual evidence](../compat/api-acceptance/successor-public-delivery-v1.json). No broader inventory or hardware claim.

## Rendering and shader scope

For each open parent, first select a finite supported subset or document an
explicit boundary; implementing every possible form is not required.

- [ ] **SHD-01 — Sampler breadth:** decide multidimensional runtime indexing,
  implicit-derivative/uniformity rules, additional preprocessor/helper forms,
  multilevel mip chains and wider filtering/LOD combinations. The proved path
  is direct explicit selection over one-dimensional arrays; retain intentional
  refusals and add value, binding-limit and recovery tests for any expansion.
- [ ] **SHD-02 — Array breadth:** settle remaining storage/interface classes,
  shape/type combinations, indexing, partial updates, reflection and shader-cache
  identity beyond the installed numeric uniform subset.
- [ ] **SHD-03 — Attribute breadth:** disposition constants, additional formats,
  shapes/divisors and mutation combinations beyond the finite matrix/array
  evidence. Retain route-specific raster versus generated-line input limits.
- [ ] **SHD-04 — Geometry consumers:** select supported compute/instanced
  expansion or an explicit application rewrite; prove topology, interpolation,
  clipping, depth and mutation/loss for that subset.
- [ ] **SHD-05 — Broader line semantics:** beyond the seven proved boundary cases above,
  decide any additional builtin, external-storage and early/late-depth support.
  Unsupported semantics must keep explicit diagnostics and recovery behavior.
- [ ] **SHD-06 — Mesa clipping preparation/admission:** reconcile the retained
  clip-axis patch, original CI driver record and selected prepared/installed
  profile. Source-functional driver evidence is not blanket profile admission;
  close this only when the required joins and observations are established.
  2026-11-13: [matched patched driver installed baseline](../compat/api-acceptance/lifecycle-linux-tk-matched-observation-v1.json)
  passes56Tk cases and recovery on current wheel8a793196. [System Mesa25.2.8](../compat/api-acceptance/lifecycle-linux-system-mesa-msaa-failure-v1.json)
  fails the four-sample quadrant case on the identical wheel/tests. Preparation9
  binds the actual patched driver; strict profile/CI joins remain pending.
- [ ] **STA-01 — Raster-state combinations:** reconcile dither, disabled
  multisampling, fractional polygon offset, mixed constant blending and stencil.
  Keep the already-proved reversed-depth subset separate.
- [ ] **TEX-01 — Typed sampling:** disposition Uint/Sint, unfilterable float,
  comparison sampling, half precision and NaN behavior on claimed layouts.
- [ ] **LIN-01 — Line partitioning:** bind chunk boundaries, endpoint carry,
  topology, resource limits and ordering to selected rendered acceptance cases.

## Scientific workflows and API reconciliation

- [ ] **API-05 — Methods, routes and aliases:** reconcile remaining public
  methods, wildcard exports, aliases and value-dependent dispatch with actual
  source routes. Parent-level app/gloo/scene/visual reviews are already recorded;
  the canonical inventory is still not a fully reviewed method inventory.
- [ ] **API-06 — Selected API acceptance:** for each claimed subset, record
  inputs/values, expected output, ordinary/mutation/failure/recovery behavior,
  exact installed artifact and explicit unsupported cases.
  Source progress, 2026-11-13: [numeric-zero clear acceptance](../compat/api-acceptance/gloo-clear-zero-source-v1.json)
  covers ordinary flags, numeric-zero mutation, NaN refusal/recovery and cleanup
  in9Windows rendered cases. The Python correction remains unpushed and has no
  successor installed qualification yet. [Nine current WSL source cases also pass](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json)
  using verified Linux native module5740b28a on Mesa25.2.8 software Vulkan;
  this is a source overlay, not the CI wheel's wrapper bytes.
- [ ] **SCI-01 — Indexed/instanced points:** rendered source-ID, divisor,
  constant-input and ordered-revision combinations.
- [ ] **SCI-02 — Mesh filters:** enumerate supported filters/compositions and
  prove meaningful output plus mutation behavior for selected combinations.
- [x] **SCI-02-COLOR-ALPHA-COMPOSITION — Finite installed subset, 2026-11-14:**
  Six exact-pixel queued-revision/mutation/boundary/recovery cases pass per
  current Windows/WSL wheel, with explicit single-sample/blend-disabled scope.
  [Windows](../compat/api-acceptance/mesh-color-alpha-windows-v1.json),
  [WSL](../compat/api-acceptance/mesh-color-alpha-wsl-v1.json). Other filters,
  composition ordering, blending/MSAA and final review/integration/admission
  of the post-head test remain separate; SCI-02 stays partial.
- [ ] **SCI-03 — Scenes/cameras:** reconcile selected 3D cameras, planes,
  depth/stencil and polygon-offset interactions.
- [x] **SCI-03-CAMERA-MUTATION — Finite local installed subset, 2026-11-13:**
  Public TurntableCamera azimuth/center mutation, fresh-construction equivalence,
  comparison-peer closure and frozen-pose restoration pass2cases per current
  Windows9e4e30cc/WSLa2715d26wheel, runtime2b8bccd. [Windows](../compat/api-acceptance/camera-mutation-windows-v1.json),
  [WSL](../compat/api-acceptance/camera-mutation-wsl-v1.json). Changed-pose
  equivalence is metamorphic; baseline/restoration has the independent frozen
  reference. Broader3Dstate/fov/event/other-camera combinations and final
  review/integration/admission of the post-head test remain separate.
- [ ] **SCI-04 — Large volumes:** separate scientific quality, mode, performance,
  platform and artifact claims; extend only the selected bounded workflow.
- [ ] **SCI-05 — Stale fixture dispositions:** reconcile U05, E03, E04, Q11–Q13
  and H03 against newer evidence before changing their status.
- [x] **SCI-05-RECONCILIATION — Seven-row disposition audit, 2026-11-13:**
  [708](../compat/api-acceptance/scientific-current-dispositions-v2.json) and the
  [route/value table](api-method-reconciliation.md#current-seven-row-reconciliation--2026-11-13)
  identify exact current/historical/open scope and reopening triggers for all
  seven rows. Record classification is complete; capability parents and final
  admission/public delivery remain partial. No broad source-route review inferred.
- [ ] **SCI-06 — Stencil wrapper:** resolve the upstream acceptance gap
  independently of already-passing native stencil capture cases.
  Selected source investigation is complete: [Windows/WSL route disposition](stencil-wrapper-disposition.md)
  verifies four improved public forms and four explicit raw-refusal/recovery
  forms. Original stock failures remain failed; installed acceptance is pending.
  Source improvement, 2026-11-13: numeric stencil0/depth0.0 now clear rather
  than skip;9rendered cases pass after5failures/4controls. This intentional
  correction does not admit the original8stock wrapper/facade failures.
  [Exact scope](../compat/api-acceptance/gloo-clear-zero-source-v1.json).

## Lifecycle, capture, input and known issues

- [x] **LIF-01-SUBMISSION-WINDOWS — Finite11-case installed subset:**
  [740](../compat/api-acceptance/submission-fault-windows-v1.json),2026-11-14:
  selected existing gloo/raw pre/post-submit/query-frame failure/recovery and
  retirement cases pass9e4e30cc,537members/no overlays/ten zero gauges; cleaned.
  Surface-acquisition, physical-memory and full-parent/integration scope open.
- [x] **LIF-01-SUBMISSION-WSL — Matching11-case installed subset:**
  [741](../compat/api-acceptance/submission-fault-wsl-v1.json),2026-11-14:
  exact740source/cases passa2715d26/softwareVulkan,537members/no overlays/ten
  zero gauges; unchanged borrowed origins, awaited exits, cleaned target.
  Actual surface, physical-memory and broader-parent/evidence integration open.
- [ ] **LIF-01 — Fault coverage:** audit acquisition failures, fault injection
  and physical-memory-accounting evidence; retain unresolved cases explicitly.
  New source failure, 2026-11-13: run557retains24CPU-buffer and24GPU-buffer
  bytes after final explicit deletion/close. The rebuilt native leaf resolves
  that exact case with all nine zero gauges on Windows (runs560/561); retain
  the original failure. Linux and broader fault/memory cases remain open.
- [ ] **LIF-02 — Reparenting:** selected real layout reparenting, WinIdChange,
  surface ownership and shared-resource lifetimes.
  Source progress, 2026-11-13: [Windows PyQt6 readback](../compat/api-acceptance/qt-layout-reparent-source-v1.json)
  passes two active layout moves, old-parent deletion after the move, actual
  WinIdChange, continued exact pixels and all nine zero shutdown gauges.
  No renderer change/rebuild; initial fixture QApplication-order failures are
  preserved. The same case now [passes on current WSL software Vulkan](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json).
  Installed, native-WSI and embedded-parent destruction remain open.
- [ ] **LIF-03 — Zero/minimized windows:** prove no-submit behavior and restoration
  beyond screenshots or overlay observations.
  Source progress, 2026-11-13: window-state events now suspend/restore without
  resize; real offscreen Qt before/after control and 43 CPU cases pass.
  [Evidence](../compat/api-acceptance/qt-window-state-source-v1.json). Physical
  Windows readback rendering now also passes no-submit while minimized,
  exact restored pixels and zero ticket/queue gauges after close
  ([source Vulkan evidence](../compat/api-acceptance/qt-window-state-windows-source-v1.json)).
  The same finite case also passes on [WSL software Vulkan](../compat/api-acceptance/qt-window-state-wsl-source-v1.json).
  Broader zero-size/resource cases and changed-artifact qualification remain
  open; the local-native and WSL bootstrap failures are retained separately.
- [ ] **LIF-04 — Close/loss:** selected in-flight close, actual surface loss,
  multicanvas recovery and resource retirement.
  Source progress, 2026-11-13: native QWidget close now invokes Canvas.close
  once, including callback-error cleanup. Shared-peer green pixels pass on
  Windows; rebuilt native final buffer retirement and pending-peer-snapshot
  preservation now pass ([evidence](../compat/api-acceptance/qt-lifecycle-windows-native-v1.json)).
  Both shared-close cases now [pass on the verified current Linux native payload under WSL](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json),
  including all nine zero gauges. Installed, embedded-parent lifecycle and actual surface loss remain open.
- [x] **LIF-05-DEFAULT-DEPTH-STENCIL — Finite16case local installed subset:**
  [748](../compat/api-acceptance/msaa-depth-stencil-windows-v2.json)/
  [749](../compat/api-acceptance/msaa-depth-stencil-wsl-v2.json),2026-11-14:
  same default target/sample/type/crop/mutation/refusal/restoration cases pass
  current wheels, color preserved BEFOREredraw,537members/no overlays/ten zero gauges;
  cleaned. Uniform
  samples only; mixed-edge/other-format/feature and review/integration scope open.
- [ ] **LIF-05 — MSAA capture:** disposition broader depth/stencil and
  format/feature combinations separately from existing color-resolve evidence.
- [x] **LIF-06-QT-WINDOWS — Finite8case installed PyQt6 subset:**
  [736](../compat/api-acceptance/qt-input-windows-v1.json),2026-11-14:
  generated key/wheel/mouse payload/rendering/handled-state/target-isolation
  cases pass Windows9e4e30cc, no overlays/ten zero gauges; scratch cleaned.
  WSL, integration, focus/physicalHID and broader parent scope remain open.
- [x] **LIF-06-QT-WSL — Matching8case installed PyQt6 subset:**
  [738](../compat/api-acceptance/qt-input-wsl-v1.json),2026-11-14:
  exact same736source passes currenta2715d26/softwareVulkan/privateXvfb,537members,
  no overlays/ten zero gauges; borrowed origins and cleanup verify.737dependency
  failure retained. Broad parent, other bindings, review/integration and CI open.
- [x] **LIF-06-QT-PANZOOM — Finite2-case installed scene-response subset:**
  [755](../compat/api-acceptance/qt-panzoom-windows-v2.json)/
  [756](../compat/api-acceptance/qt-panzoom-wsl-v2.json),2026-11-14:
  generated Qt PanZoom gestures drive literal rect/marker changes and exact
  restoration on current Windows/WSL wheels,537members/no overlays/ten zero
  gauges; cleaned. Explicit-size render, not native display/HID/focus/DPI.
  Review/integration and broader camera/parent scope open.
- [x] **LIF-06-QT-INPUT-CALLBACK-SOURCE — Revised Windows/WSL PyQt6 CPU subset, 2026-11-14:**
  [782Windows](../compat/api-acceptance/qt-input-callback-windows-source-v4.json)/
  [783WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v4.json) each93pass:
  47input/46paint-window,12parent key routes with default/working/broken hooks.
  780negative review and781doublecallback/doublehook reproducer retained;
  new1c68runtime preserveshostacceptedstate/guards privatekeydispatch/consumes
  suspendedreplay. Closed/post-C++-destroyed parent lookups not separately observed.
  Exactsource re-review/integration and installed qualification remain pending.
- [x] **LIF-06-QT-INPUT-CALLBACK-RENDERED-WINDOWS — Revised finite overlay subset, 2026-11-14:**
  [784](../compat/api-acceptance/qt-input-callback-rendered-windows-v3.json)
  passes21cases(6defaultpeer/3hostsamecanvas/12controls),9isolated origin/nativeSHA/
  zero-gauge proofs at1c68, host/defaultacceptedstate explicit.9e4native/536members
  unchanged,1QtPythonoverlay. Parent-forwarding evidence is the separateCPUsubset.
- [x] **LIF-06-QT-INPUT-CALLBACK-RENDERED-WSL — Matching revised overlay subset, 2026-11-14:**
  [785](../compat/api-acceptance/qt-input-callback-rendered-wsl-v3.json) same21cases/
  sourcehashes as784,9childzero-gauge proofs; a271native/536members unchanged,
  1QtPythonoverlay, borrowedQt/9c5driver unchanged/privateXvfb0; cleaned after
  transientPID-livenessplan refusal resolved with unchangedmanifest/verifier.
  Source re-review/protectedintegration, otherbindings/fullnapari, changed-wrapper
  installed/public admission and broader-parent scope remain open.
- [ ] **LIF-06 — Input forwarding:** selected Qt keyboard, wheel, focus, mouse,
  timer and coordinate delivery beyond the finite Tk subset. Touch, stylus,
  gestures and additional layouts need their own selected scope.
- [ ] **LIF-07 — Tk extensions:** decide camera/DPI/physical-input claims beyond
  the proved raster/manual-pump and toolkit-generated input cases.
  The opt-in native presentation prototype now has finite source-functional
  proof; it does not close DPI, physical-input or release/profile obligations.
- [ ] **BUG-01 — Rare Windows startup stall:** retain the external watcher and
  exact recurrence evidence; establish cause and a targeted regression. It is
  documented under D33; recurrence makes it release-blocking again.
- [ ] **BUG-02 — Historical PyQt5 OLE hang:** determine whether it shares BUG-01's
  cause or needs a separate documented disposition.

## Optional integrations, packaging and tooling

Select these only when needed for a product claim.

- [ ] **HOST-03:** renew optional strict napari/Glue/napari-threedee rows if
  claiming them on the successor artifact; old host qualifications do not transfer.
- [ ] **HOST-04:** resolve DIVE's supported binding/API and upstream baseline
  before claiming rendered workflows; PySide2 remains excluded.
- [ ] **HOST-05:** select rendered Visbrain/other-application workflows rather
  than treating imports or inventories as application acceptance.
- [ ] **HOST-06:** reconcile Glue's older volume-mutation gap with newer workflow
  results while preserving each evidence epoch.
- [ ] **PLAT-02:** produce and qualify other CPython ABI wheels only if selected;
  the current release claim is CPython 3.12 x86_64.
- [ ] **PLAT-08:** qualify additional Vulkan GPU/driver combinations before
  extending the current hardware claim.
- [ ] **PERF-02 / PERF-03:** select further imported-block conversions and batched
  buffer upload optimization only if measurements justify them.
- [ ] **PERF-04:** bounded cold-build/peak-memory measurements and reconciliation
  of historical review regressions if making those performance claims.
- [x] **TOOL-01 — Hosted reuse verified, 2026-11-13:** Linux software Vulkan and both actual Metal build/CPU-import jobs pass at reviewed head3ada, including locked minimal version validation. [Original API records](../compat/api-acceptance/revision8-native-ci-v1.json). No Metal graphics or release admission claim.
- [ ] **TOOL-02:** optional compiler-output cache with exact input identities and
  the shared storage budget.
- [ ] **TOOL-03:** reconcile the missing historical compiler-cache cleanup receipt.
  The new cleanup receipts do not establish the missing historical event.

## Explicit deferred or unavailable scope

- [ ] **LIN-02:** MSAA generated-line coverage remains deferred; an unshipped
  partial patch is not production support.
- [ ] **LIF-08:** cross-monitor changes and fractional DPI remain outside the
  selected release scope.
- [ ] **PLAT-03:** native Linux physical GPU qualification needs available
  hardware; WSL software Vulkan does not establish it.
- [ ] **PLAT-04:** macOS Metal remains experimental; no Mac is available for
  physical graphics/input/lifecycle qualification.
- [ ] **PLAT-05 / PLAT-06:** native Wayland is unsupported; ARM, free-threaded
  Python and ABI3 are outside the current release scope.

These are acknowledged boundaries, not a request to obtain hardware or expand
the release. No full-parity requirement is introduced.

## Update rule

Close one finite task at a time. Update its stable ID here and in the detailed
coverage checklist with source identity, exact wheel/platform, test counts,
failure/recovery result and durable evidence. Mark completion only at the proved
level; a parent stays open while broader claims are unsettled. Retain sources,
licenses and meaningful failures, apply the unchanged build-hygiene policy,
and record terminal cleanup before the next experiment. Do not derive a universal
coverage percentage from these different scopes.
