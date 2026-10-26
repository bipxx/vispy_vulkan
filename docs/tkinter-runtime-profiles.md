# Tk runtime profiles and source compatibility

The alternate Linux development profile uses the already-installed standalone
CPython 3.12.13 and Tcl/Tk 9.0.3. It is a new profile, not qualification of the
older CPython 3.12.8/Tk 8.6 profile. Native leaves, SDKs and locked package paths
are reused without an install, environment or native rebuild. Exact new pins
are in `compat/candidates/tk-state-resource-1/linux-tk90-profile.json`.

## Toolkit attribution

Three bounded fresh-process controls on the original interpreter reproduce its
Xlib/XCB abort at first Label creation, before teardown. Eager collection and
sharing one interpreter do not repair it. Each actual child exits by SIGABRT;
no VisPy or Vulkan code is imported. The old interpreter SHA-256 remains
`0dc3a692fa85fcdb7f1a5877d2adf179809ac417a07ffde2373c832863800a15`.
Sources, failed logs, actual exits/waits and verified terminal cleanup are retained
in local `build/runs/linux-toolkit-cause-27/`.

Upstream [issue 503](https://github.com/astral-sh/python-build-standalone/issues/503)
reports the same error on that Python version. Maintainers linked the broader
[issue 146](https://github.com/astral-sh/python-build-standalone/issues/146) to
[PR 676](https://github.com/astral-sh/python-build-standalone/pull/676), which
changed Tcl/Tk linking and Xcursor configuration. This is an upstream attribution
lead; a newer-runtime pass does not establish the exact local native mechanism.

The identical retained baseline control passes all 12 Label/window lifecycles
on the existing 3.12.13 runtime. Its Python SHA-256 is
`339de109f072e52523066d97a2b3372e358a10cc00c6a9df62c28a6618061900`.
Its shared `_tkinter`, Tcl 9.0.3 and Tk 9.0.3 binaries are separately identified.
The interpreter, toolkit and runtime closure differ; retain the old blocked
profile and all of its original observations rather than rewriting their pins.

## Backend changes

Tcl 9 returns typed Tcl namespace/command objects. The backend now splits Tcl
lists and converts names to plain strings before building namespace patterns or
comparing host commands. A real nested-namespace regression covers both object
and string result modes and confirms that the host command remains callable.
The initial focused test fails before this correction.

[TIP 474](https://core.tcl-lang.org/tips/doc/main/tip/474.md) changes X11 wheel
delivery from Tk 8.7 onward. Linux Tk 8.6 Button4/5 notifications still map to
wheel +1/-1. Newer Tk uses MouseWheel; its script buttons4/5 are extra buttons.
The backend no longer mistakes those new extra buttons for wheel events.
Two synthetic translation controls fail before the version guard. Live-widget
cases preserve fractional/signed deltas, held buttons and native metadata;
extra buttons remain press/release events. Physical-device qualification is
separate from these generated-input checks.

## Thread fixture ownership

A broad Windows run terminated with Tcl_AsyncDelete while a worker triggered
collection of earlier test-owned interpreter cycles. Two fresh plain-Tk controls
isolate collection order: worker-only collection aborts; collecting the retired
interpreter on its UI thread first succeeds. The thread-rejection fixture now
collects earlier test garbage on the owner before starting its worker and releases
its tested error traceback cycle there after assertions. Current canvas/timer
objects stay live. UI-thread rejection, public state/jobs, deadlines and all nine
shutdown gauges remain unchanged. No production global GC policy was added.
This fixture correction does not promise arbitrary cross-thread Tcl destruction.

## Submission progress fixture

Releasing the diagnostic completion hold does not promise that the GPU has
already completed. A source regression assumed one process_events call would
free the only slot. Both routes now wait for observed ticket retirement with a
five-second bound before explicit retry. Controlled delayed-progress variants
fail before the fixture correction. Submission/no-wait/no-presentation counts,
retained queued work and exact green readback remain strict; no production
synchronization path changed.

## macOS CPU contract

The retained e8973a48 job diagnostics show a successful script worker and an
OpenGL framework already loaded before VisPy. The controller correctly returns
FAIL with no_gl_loads=FAIL. The CLI binding/argument CPU contract now verifies
that exact failure when native violations exist; it verifies import-only success
only when they do not. Unexpected script/import errors still fail the contract.
An actual Linux baseline-GL preload control also preserves FAIL/exit1 while the
script succeeds. No observer, dependency, native-load or aggregate shipping gate
was relaxed. Passing this CPU contract cannot qualify the Mac profile or Metal.

## Evidence boundary

The separate odd-size four-sample scissor defect remains reproduced with the
same original pixel expectations and driver. The alternate toolkit fixes neither
that graphics defect nor the old toolkit profile. The full capture selection
therefore remains incomplete despite successful single-sample/crop/lifecycle
cases. Required threedee, complete inventory/conservation, independent source
and scope review, exact installed-wheel/member/closure and all original absence
and promotion gates stay open. Linux native producer provenance stays
experimental; WSL software, native Linux GPU and Metal remain distinct.

The active packet is local `build/runs/linux-toolkit-profile-28/`. Its final
reports and terminal cleanup receipt determine the actual validated selections;
source passes alone do not promote a profile. Licensing and preferred-source
requirements remain unchanged, including external toolkit/runtime admission.

The final affected source selections pass 69 Windows and 68 new-profile Linux
cases, with all nine shutdown gauges zero. They include real Label hosts created
before/after an embedded Vulkan canvas, exact whole-target green output and host
widget/job preservation after quit. Readiness requires the displayed image's
extent to match the current configured target. The retained broad and partial
failures are not counted as passes. The full Linux capture failure for the
four-sample boundary remains separately visible; the final scoped selection
explicitly excludes that one known failing case. Direct composite scripts and
five legacy-Tk8.6 input/name controls retain separate source receipts.
