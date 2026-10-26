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
