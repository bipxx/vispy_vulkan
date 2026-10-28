# Windows threedee startup diagnosis

Date: 2026-10-25. The bounded three-start diagnostic packet is complete. The
current exact installed artifact passes its full host workflow and all three
no-OpenGL gates. The historical OLE/RPC stall was not reproduced or causally
explained, so HOST-1/HOST-2 and final-candidate admission remain open.

The original 300-second timeout, its native stack in `RegisterDragDrop` through
OLE/RPC, and its incomplete functional report remain preserved. The same
installed environment and unchanged fixture were reused; all four wheel inputs
were checked against their original hashes before each launch. No environment,
package, renderer or observer implementation was changed for this packet.

| Diagnostic start | Controlled launch | Actual result |
| --- | --- | --- |
| 1, `threedee-startup-diagnosis-49` | Plain pinned environment Python, exact host fixture; no worker/native observer | Exit 0, 51.77 seconds. All eight functional stages and six captures pass. Owned-process debugger queries report no debugger. |
| 2, `threedee-worker-diagnosis-50` | Same fixture/environment plus the worker, original environment receipt and shutdown checks; no native observer | Exit 0, 24.05 seconds. `PASS_SCENARIO`, exact environment identity verified, nine zero live-resource gauges. |
| 3, `threedee-observed-diagnosis-51` | Restore the native observer and original independent handle-fidelity baseline around the same worker/fixture | Exit 0, 44.03 seconds. `PASS_ALL_NO_OPENGL_GATES`, all three gates PASS, no observer errors, all observed PIDs exited, nine zero live-resource gauges. |

The functional stages cover exact installed inputs, device/Qt binding, patched
host artifacts, registered plugin activation, real Qt selection/translation,
data update and device recovery, callback retirement, and close. The six captured
frames are byte-identical across the three launches. The observed trial actually
records debugger presence on its traced processes; the plain/worker comparisons
record its absence. They are distinct controls, not repeated favorable retries.

The artifact is `62df5e4c31bf9a1bb1bea47fd68d50e4198d6ec13d2551c991da1e7f30a2b38f`.
The worker and observed environment identity is
`405ab8e5a25f63e8edf1a1f9dcb16563b576d5c105c657a76d8f4ccd14c3015a`.
The fixture SHA-256 is
`d420e143f852d4799cc08f25a9de1b8d2e1f538fc8bf98a2ad85edba25d605eb`.
These results apply to those installed inputs, not the pending Tk candidate wheel.

Each launch retained the original five-minute deadline, a 20-second stack-capture
grace and a 32 MiB text-log cap. The observed controller also schedules a bounded
capture before the observer's deadline, preventing the earlier failure mode where
the worker had already exited before all-thread state could be collected. Its
stack/wait-chain triggers were not reached. The WCT helper passed a separate
coordinator-only control; that is not a stalled-application wait chain. Microsoft's
[WCT documentation](https://learn.microsoft.com/en-us/windows/win32/api/wct/nf-wct-getthreadwaitchain)
also limits a snapshot to supported waits and the state at the instant of capture.

The three starts exhaust the diagnostic budget. No causal fix was identified,
so the reserved targeted confirmation is unused. No additional startup retry
follows from this packet. If the genuine stall recurs in this exact profile, the
next evidence is the owned worker's native stacks and WCT owner/server chain
while it is still alive, together with observer pending-step/thread state before
the original deadline. A new hypothesis or that evidence is needed to extend the
experiment. A passing replay alone does not close an intermittent historical
failure. The mandatory row and original failure evidence remain intact.

Local records are under `build/runs/<run-id>/`: exact commands, source/input
hashes, functional and worker reports, debugger observations, raw observed gates,
six frame identities, actual exits/child waits and cleanup receipts. Run 51
references matching retained frames rather than keeping another live copy.
Across the three runs, cleanup removed 24 scratch files / 3,563,439 bytes and
verified 122 retained records. All three scratch roots are absent. No native
build, SDK, source-history clone, package installation or new environment was used.

## Sequence-contention hypothesis trial (H-SEQ) - 2026-10-28

New hypothesis, approved by the user for one bounded trial: the stall is an
intermittent out-of-process RPC wait inside OLE `RegisterDragDrop`
(`InternalRegisterWindowPropInterface2` -> `RoGetAgileReference` -> ALPC),
triggered by rapid successive Qt GUI process creation rather than by
napari-threedee or the renderer. Basis: the original threedee start began
0.75 seconds after the preceding napari host exited, as the third back-to-back
start of the `qwidget -> napari -> threedee` loop; the earlier Qt5 `repro5` stall
was the third concurrent PyQt5/PySide6 pair, in plain QWidget, with the same
native stack. All three isolated diagnostics above passed. Launch flags
(`CREATE_NO_WINDOW`) match in every case, so a launch-context difference is not
supported.

Run `threedee-sequence-contention-201` replayed the original loop four times
with no gap (12 launches) on the same artifact, environment, fixture and host
wheels, without the native observer. Live native-stack/WCT capture was armed
at 75 and 150 seconds, with the original 300-second deadline.

| Result | Detail |
| --- | --- |
| Startup stall | Not reproduced. Every launch exited within 43.3 seconds; no capture trigger was reached. |
| Functional | 11 of 12 passed. `r4-threedee` failed (exit 1, 10.2 s) in `threedee_real_qt_selection_translation` at `translation[2] > .25`: the generated press selected translator 2 and the release ended the drag, but the layer was not translated past 0.25 along Z. |

H-SEQ is not supported by this sample. Given the historical rate (one stall in
roughly 40 comparable starts), 12 launches cannot exclude it either. The
startup cause therefore remains unexplained, and the trial is not repeated.

The `r4-threedee` failure is a separate, newly observed intermittent failure
in the generated-input interaction stage: it passed in rounds 1-3 and in
diagnostics 49-51. It is preserved as a failure and was not retried. The
mandatory row's `interaction` feature now has an open intermittent defect in
addition to the unexplained startup stall. Its report and the two frames
captured before the failure are retained in the run's `functional/` directory.
Cleanup removed 105 scratch files / 7,831,055 bytes and verified 41 retained
records. The row stays mandatory and `PENDING`, and no qualification is claimed.

## Root cause of the `r4-threedee` selection-translation failure - 2026-10-28

This is a race in the probe's synthetic drag, not a renderer or startup defect.
The stage at `tools/no_opengl_host_probe.py:575-591` sends press, move1, one
`process_events()`, move2, one `process_events()`, release. Three upstream
behaviors combine:

- napari 0.9.2 wraps canvas mouse-move handling in superqt
  `qthrottled(timeout=5)` (`napari/_vispy/canvas.py:249`). It is a
  leading-edge throttle whose window reopens only when the Qt event loop
  dispatches its single-shot `QTimer`, however much wall time has passed.
- napari-threedee's `TranslatorDragManager.setup_drag` takes the first
  delivered move, not the press, as the drag origin. A drag that receives
  only one move therefore translates by exactly 0.
- Qt 6 `QTest.mouseMove(..., delay)` only advances event timestamps; it does
  not wait. vispy's `BaseCanvasBackend._vispy_mouse_move` also drops moves
  within 10 ms of the previous delivered move (`vispy/app/base.py:197`,
  unchanged from upstream vispy 0.15.2/0.16.2).

When the single `process_events()` after move1 does not dispatch napari's
throttle timer, move2 is deferred. The next single `process_events()` does not
run it either, so the synthetic release ends the drag first and the deferred
move reaches no drag generator. `layer.translate` stays `(0, 0, 0)`, which
passes the `origin == translate` and `translate[:2] == 0` checks and fails
`translate[2] > .25`, matching r4 exactly.

Run `threedee-drag-race-202` rebuilt the exact probe scene in the same
installed environment and instrumented vispy delivery, napari throttling and
the napari-threedee drag manager:

| Variant | Passed | Cause of every failure |
| --- | --- | --- |
| Probe's exact sequence | 12/20 | napari deferred move2 past the release (8/8); vispy delivered both moves |
| Moves with no gap | 1/3 | vispy 10 ms drop |
| 15 ms gap without event processing | 0/3 | napari deferral past the release |
| 50 ms event processing between moves, then wait for translation before release | 10/10 | none |

Passes and failures separate completely on whether napari's throttle timer was
still active when move2 arrived. Failures occurred with 12-49 ms of wall time
between moves, so elapsed time alone does not decide the outcome. Every
both-moves-delivered drag gives the same `1.0690530849669262`. No physical
(non-synthetic) mouse moves were observed. The first instrumented attempt
renamed napari's release callback, which vispy resolves by method name, so
napari never received the release. That attempt is preserved as an
instrumentation error, not used as evidence.

### Fix

The probe now delivers drag moves through `settled_moves()`. Before each
move it processes events for 50 ms, which covers vispy's 10 ms drop window and
the dispatch of napari's throttle timer. After the last move it waits, with a
2-second timeout, until the drag has been applied, and only then releases. The
wait condition (`translate[2] != 0`) checks only that the move arrived; the
existing `origin == translate`, `translate[:2] == 0` and `translate[2] > .25`
assertions still decide correctness. The stage now records the translation
before releasing, so a failure reports the value it saw. The release is in a
`finally` block, so a timeout still releases the button. The probe fixture
identity changes from `d420e143...` to
`d38afcfa2e32598a2f42c14cfb648d1651d5b6f1dbbc8bd66dd543070b588113`. Earlier
evidence keeps its original fixture binding.

`tests/hosts/test_no_gl_probe_contract.py` models both throttles with an
injected clock. It reproduces the original single-pump race, requires
`settled_moves()` to apply the final move even with no settle time, and
requires a timeout when the final move is lost. These tests were written first
and failed before the helper existed. A source guard also fails if `threedee()`
stops using `settled_moves()` or calls `mouseMove()` directly. The guard fails
on the original probe.

An independent review approved the change with three nits, all applied: move
the release into `finally`, correct the test model's timing comment, and add the
source guard. Runs 203 and 204 verified the intermediate probe `e694a736...`,
which differs from the final probe only by the `finally` release. Run
`threedee-drag-fix-final-206` verified the final bytes:

| Check | Result |
| --- | --- |
| Windows, fresh full `threedee` scenario | 4/4, each exactly `1.0690530849669262` |
| Windows, real stage with the final move lost | exit 1, `TimeoutError` in the stage, translation `[0, 0, 0]` recorded, close stage passed |
| WSL lavapipe, fresh full `threedee` scenario | 2/2, each exactly `1.0690530849669262` |

The review also found the same single-pump drag sequence in
`tools/fixture_napari_threedee.py`, which asserts the translation right after
one `processEvents()`. That fixture's source hash is pinned by the OpenGL
reference that `tests/hosts/test_napari_threedee_parity.py` checks. Fixing it
means regenerating that reference, a separate follow-up; it is unchanged here.

Run `threedee-drag-fix-203` used the real installed environment and wheel:

| Check | Result |
| --- | --- |
| Same process, interleaved: original protocol | 15/20 stage passes; 5 failures at exactly `0.0` |
| Same process, interleaved: the probe's actual `settled_moves()` | 20/20, each exactly `1.0690530849669262` |
| Lost-final-move control through `settled_moves()` | 3/3 `TimeoutError`; stage fails |
| Full fixed probe `threedee` scenario, 8 fresh processes | 8/8, all stages passed, each exactly `1.0690530849669262` |

Run `threedee-drag-fix-wsl-204` repeated the checks in the qualified WSL rootfs
on lavapipe, with the qualified renderer `374a74ea...` and the same host wheels:

| Check | Result |
| --- | --- |
| Full fixed probe `threedee` scenario, 4 fresh processes | 4/4, all stages passed, each exactly `1.0690530849669262` |
| Same process, interleaved, with non-synthetic input logging: original protocol | 20/20; slower software rendering lets napari's throttle timer fire, so the race is not reached |
| Same process, interleaved, with input logging: the probe's actual `settled_moves()` | 20/20, each exactly `1.0690530849669262`; no non-synthetic mouse events in 43 trials |
| Lost-final-move control | 3/3 `TimeoutError` |

The first WSL in-process comparison, run before input logging was added, had
an interference episode. Translations that the synthetic points cannot produce
appeared, and for 24 trials the press stopped selecting the handle in both
protocols, consistent with an external camera change. Its source was not
captured. That run is preserved as unexplained, and it is not used as evidence
for or against the fix.

The identical probe copy in the `vispy_vulkan-opengl-python` worktree was not
modified, because historical run records execute it. Future runs should use the
fixed probe. This fix resolves the intermittent interaction failure observed in
run 201. The startup stall above remains unexplained and separate, and the
Windows napari-threedee row stays mandatory and `PENDING`.

## Startup stall: live recurrence and mechanism - 2026-10-28

A cells3d launch hung in `window.show()` and was captured live. The launch used
the dev environment: stock napari 0.9.2, PyQt6 6.11.0, CPython 3.12.8 and vispy
source on Dawn/Vulkan, RTX 4090. Run `napari-startup-stall-recurrence-209` holds
two minidumps, symbolized all-thread stacks and a wait chain. Run
`com-stall-harness-213` analysed them.

| Finding | Evidence |
| --- | --- |
| The main thread waits forever in UI Automation's first initialisation (`CDllHost::MTAInitializeActivators`). | Symbolized stacks in two snapshots, 89 s apart |
| A CPython `platform` WMI query thread, started by numba's import, waits forever in `ConnectServer` on an RPCSS activation. | Stacks and wait chain |
| The process's default thread pool has lost its worker factory. Healthy processes have two factories: the default pool's (maximum 768 threads) and the parallel loader's (maximum 3). The hung process has only the loader's, at handle 156. Handle 28 holds a `Semaphore`. In healthy trials the default pool's factory is at 28 in 2,016 of 2,090, and otherwise at 32-48. | Handle tables of both dumps; healthy trials |
| The pool's two workers were created at 06:58:28.94 UTC, 2.1 s after the main thread. They began spinning within about a second of creation, at about 100% CPU each, mostly kernel. | Thread creation times, and CPU in the dump and at about 07:01:33 |
| The surviving WMI query thread started 1.05 s after the workers. numba's call makes two WMI queries, and the other query's thread had exited. | Thread timeline; trial records |

Early in startup, between process start and about 06:58:30, something closed
the default thread pool's worker-factory handle. That was no later than about a
second after the process's first COM RPC, at 06:58:28.94. After that, work
queued to that pool never runs, including COM work. So the UI Automation
activation in `window.show()` waits forever. It is unresolved whether the pool
was already dead when the WMI queries ran.

One explanation is refuted: a pending COM activation does not block the next.
A WMI activation was held pending, with a stack identical from `ConnectServer`
down and the same wait chain. UI Automation initialisation still took 5-9 ms,
in 6 of 6 trials.

CPython's WMI timeout path is not excluded. The hung process took it: its main
thread moved on while the WMI query thread stayed in `ConnectServer`. Under
8-way concurrency, 6 of 1,920 queries took that path (`WinError 258`) with no
pool loss. That bounds the path but does not exclude it.

The lost handle exists before any user code runs, and is never released. A bare
`python -S` interpreter already has the default pool's factory among its first
handles. So an ordinary double close should not reach it. The closer more
likely used a garbage or foreign handle value, or another process closed the
handle remotely. vispy, the `_dawn` native module and Dawn's Windows code paths
contain no handle closing that could reach it. That audit does not cover the
Vulkan loader, the NVIDIA driver, Qt, CPython or the other host libraries that
ran in the same window.

The 2026-10-23 stalled qualification run was traced by the debugger-based
observer, which recorded no invalid or protected handle close. However, the
observer cannot see a close of a valid, unprotected handle, and a stray close of
the factory would be exactly that. The run's `RegisterDragDrop` stack is
consistent with the same failure, but its pool state was not captured.

Each reproduction attempt checked the worker factories after every stage:

| Campaign | Trials | Lost pool | Stalls |
| --- | --- | --- | --- |
| Headless, sequential (napari, Qt with Dawn, bare COM) | 450 | 0 | 0 |
| napari window shown, 2 s event loop: 100 plain, and 100 with the factory protected from close, which cannot show a loss | 200 | 0 | 0 |
| 8 concurrent workers with kernel handle tracing (Qt, napari) | 1,440 | 0 | 0 |
| Under a debugger that records bad handle closes | 5 | 0 | 0 |

The event is rare in these conditions:

- 0 in 733 unprotected napari launches, which bounds it below about 0.41% per launch (95%);
- 0 in the 1,995 trials able to detect a loss.

The closer is not identified, and the Windows napari-threedee row stays
mandatory and `PENDING`. The next step is to instrument and wait:

- Hot-swap and diagnostic napari launches will carry the stage-wise
  worker-factory check.
- Outside qualification evidence they will also carry kernel handle tracing.
  Tracing makes invalid handle use raise, which is why qualification runs stay
  without it.

The next natural recurrence should then identify the closing process, or the
closing thread's start module if that thread is still running.
