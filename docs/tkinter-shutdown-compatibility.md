# Tk shutdown diagnostics and native progress failures

This source packet covers a test-host teardown defect and a shared native
polling defect. It does not qualify an installed Tk profile, physical DPI/input,
the separate Linux toolkit/capture and scissor failures, or the mandatory
Windows threedee workflow.

## Host-owned interpreter teardown

The Windows Tk/Tcl 8.6.12 source suite previously emitted
`ttk::ThemeChanged` after an interpreter was destroyed. Minimal fresh-process
plain-Tk, standalone and embedded controls did not reproduce it. One bounded
421-case phase trace located it immediately after the host destroy-binding
case, while the next case created its interpreter.

That case correctly required VisPy quit to preserve the adopted root and its
host binding, but then the test host destroyed the root without draining its
idle work. The other host cleanup paths already drained idle work. The host
now calls `update_idletasks()` immediately before its own `destroy()`, after
the ownership and callback-preservation assertions. VisPy quit still does not
pump unrelated callbacks on a borrowed/adopted interpreter.

The new [fresh-process regression](../tests/native/test_tkinter_shutdown.py)
executes the destroy-binding and subsequent command workflows with the exact
parent native module origin. It creates a sentinel interpreter and writes a
known marker through Tcl's actual stderr channel. The unchanged host teardown
fails with the original ThemeChanged diagnostic; the corrected host teardown
passes. There is no error hook replacement or diagnostic suppression.

The pinned WSL software profile's existing DPI-unavailable and two Dawn
dynamic-buffer-limit advisories are retained verbatim and classified by their
exact lines. GPU profiles admit none of those advisory lines. All profiles
require exactly one Tcl capture marker and reject every other stderr line.
Those software advisories do not establish physical-DPI qualification.

Per-test file-descriptor capture was rejected as a harness: Tcl retained its
stderr channel across descriptor replacement and produced bad-file-number
errors on Windows. Its source and eight failed/one passing cases remain
retained. The regression captures one fresh process through unchanged stdout
and stderr pipes instead.

When a host has finished using its interpreter, it may drain its idle work
before explicitly destroying it. This is the host's lifecycle decision;
calling VisPy quit alone must preserve unrelated jobs, bindings and images.

## Shared progress failure and explicit retry

The broader isolated suite exposed a separate defect: a ready draw callback and
native progress timer could both poll a failed native device and report the
same failure to an externally driven loop. Two deterministic callback-order
controls reproduced three reports where one was required.

Both routes now use the root state's poll operation. A native poll failure
stops/cancels automatic progress before delivering the original exception.
Already scheduled draws do not poll again while progress is disabled. An
explicit redraw or application event-loop re-entry enables a retry. Other
host jobs survive; successful progress adds no submission, wait or presentation.

If cancellation itself fails, the original native error and traceback are
reported, the secondary error is logged, and the cancellation handle stays
owned for retry. A dedicated control verifies that the corrected owner can
later retire that handle. This does not deduplicate independent user callback
errors or replace the host's exception handler.

## Source evidence and remaining gates

The focused error/shutdown selection passes 28 cases. Full affected suites pass
425 Windows and 411 WSL software cases, with nine zero native shutdown gauges
per profile and no ThemeChanged diagnostic. All 38 CPU/package/source-preservation
contracts pass. Native bundles, SDKs and environments were reused unchanged.

Raw failures remain recorded: the initial serialization/capture harness errors,
the original deferred Tcl diagnostic, unrelated pytest-plugin contamination,
the software advisory classification, and the duplicate native poll reports.
Plugin autoload is disabled in the controlled producer, as in the original
qualification policy; the OpenGL-import assertion remains unchanged.

The broad runs used CRLF copies of the edited test fixtures. Their original LF
convention was restored afterward with an AST-equality record and retained
tested copies. Runtime bytes are identical to the passing runs. This source
evidence is not an exact installed-wheel or promotion receipt.

Preferred sources, commands, actual exits/waits and cleanup records are retained
locally in `build/runs/tk-shutdown-20/`, `tk-theme-trace-21/`,
`tk-shutdown-regression-22/` and `tk-progress-23/`. The known diagnostic is now
attributed and regression-covered for this source workflow. Independent
cumulative implementation review, concrete required-profile mapping and exact
installed functional/member/observer/CI gates remain pending; historical
optional observations keep their original identities.
