# OpenGL runtime observation

These tools distinguish Python requests, native loader events, native entry-point
resolution/calls, declared binary dependency closure and installed environment
evidence. An import check is not graphics qualification. A final module snapshot
cannot establish that a transient library was never loaded.

`tools/audit_no_opengl.py dependencies --root <binary> --search-dir <directory>
--output <new.json>` reads PE normal/delayed imports and ELF DT_NEEDED without
executing the inspected file. `--qt-root` selects QtGui and its Windows/XCB
platform plugin. Unknown imports remain unresolved; Windows API-set contracts
are resolved by the actual OS loader in the audit process and recorded. A PASS
here applies only to the declared closure, not the complete environment.

`tools/audit_no_opengl.py run --python <fresh-consumer-python> --wheel <wheel>
--scenario headless --output <new.json>` starts a fresh isolated process and
checks exact installed package bytes against the wheel's shipping manifest.
Use `--scenario qt --binding pyqt6` for the QWidget clear/capture scenario.
`--scenario script --script <host-probe.py> -- <host arguments>` wraps a real host
fixture; successful SystemExit(0) is supported. Each script must perform its own
functional/recovery/shutdown assertions. Source checks are explicitly labelled:
`--source-root <checkout> --dependency-path <site-packages> --gates imports`.
Use base Python there, since an editable redirect finder can override sys.path.

For compatibility-ledger qualification, also supply `--workflow-id <id>` and
repeated `--covered-feature <feature-id>` options before the argument boundary.
The controller and worker record matching script hashes and actual arguments;
literal `--` arguments within a script command are preserved. The worker fails
if the script changes during execution. Collector source/native-tool identities
and independent control report hashes are retained for the normalization adapter.
Unlabelled historical runs remain readable but cannot promote a new ledger row.

`--scenario script --script tools/tkinter_state_scenario.py --workflow-id
tk-state-smoke --covered-feature app.canvas --covered-feature gloo.flush` selects
the bounded real Tk/state flow. Run it through the same discovery, inventory and
fresh replay sequence below. It does not substitute for the full Tk/state suite.
The [workflow inventory guide](../../docs/compatibility-inventory.md#workflow-bound-qualification)
describes raw report bundles and `tools/compatibility_evidence.py`; the adapter
does not run or relax the collectors or full installed-distribution auditor.

Windows x64 uses OS debugger process-tree events from before the first
instruction. It records startup/transient DLL loads and unloads, traps public
GL-shaped exports, and observes GetProcAddress and
LdrGetProcedureAddress[Ex] named/ordinal lookups. Non-GL resolver instructions
are single-stepped with peer threads suspended until the breakpoint is restored.
Unknown image paths, forwarded GL exports, instrumentation errors and incomplete
process termination prevent an absence PASS. Private implementations and manual
export parsing are outside this public API observer's scope.

Linux x86-64 uses `--native-auditor <loader_audit.so> --native-debugger
<debugger_linux>`. The ptrace collector follows fork/vfork/clone/exec/exit and the
cooperating glibc collector stops on object open/close, before constructors or
user code resume. It instruments ELF public GL exports with call breakpoints,
including local -Bsymbolic calls, and records glibc bindings such as dlsym.
Unknown ELF formats, missing symbol tables, GL IFUNC exports, collector errors,
incomplete task lifecycles or unobserved execs prevent PASS. Dynamic execs restore
the collector variables in the initial stack before loader entry, including when
an application launches a helper with a sanitized environment. Static execs are
identified by actual ELF PT_INTERP absence; mapping syscalls observe executable
images and instrument their GL symbols. Observable static dlsym/dlvsym resolvers
are trapped too. A static process mapping a DSO without an observable resolver,
or needing multithreaded resolver single-stepping, remains unsupported and fails
closed. Private/non-exported stripped implementations and manual export parsing
remain outside its public API scope.
The auditor alone still produces UNVERIFIED aggregate execution/load gates.

Build the independent synthetic native controls (they implement no graphics):

```text
# Linux, in an owned build directory
cc -shared -fPIC -O2 -Wall -Wextra -Werror -o loader_audit.so tools/no_opengl/loader_audit_linux.c
cc -O2 -Wall -Wextra -Werror -o debugger_linux tools/no_opengl/debugger_linux.c
cc -shared -fPIC -O0 -Wall -Wextra -Werror -Wl,-Bsymbolic -o negative_api.so tools/no_opengl/negative_probe.c -ldl
cc -static -O0 -Wall -Wextra -Werror -o static_negative_probe tools/no_opengl/static_negative_probe.c -ldl
PYTHONPATH=tools python -B -m no_opengl.negative_controls --fixture negative_api.so --native-auditor loader_audit.so --native-debugger debugger_linux --static-fixture static_negative_probe --output <new-directory>

# Windows: VS developer shell, explicit Windows SDK import library if needed
cl /nologo /LD /GS- /Zl /Fonegative_probe.obj /Fenegative_api.dll tools/no_opengl/negative_probe.c /link /NODEFAULTLIB /NOENTRY kernel32.lib
$env:PYTHONPATH='tools'
python -B -m no_opengl.negative_controls --fixture negative_api.dll --output <new-directory>
```

The controls run without Python audit hooks: safe export, native symbol lookup
without a call, direct native call, and transient load/unload of the fixture
under a forbidden loader name. Forked and exec'd child controls check inherited
traps and new executables. Linux's -Bsymbolic call exposes the auditor-only blind
spot and is caught with the debugger. PASS_CONTROLS describes the controls, never a
candidate artifact. Keep failed traces as evidence.

All three candidate gates also require a fresh GL-free installed environment
bound to the exact wheel hash. A declared dependency report alone does not meet
that requirement. Matrix requirements live in `compat/no-opengl-matrix.json`;
pending rows remain pending until functional and same-artifact evidence exists.

`tools/audit_no_opengl.py inventory --python <consumer-python> --wheel <wheel>
--runtime-report <successful-native-runtime.json> --output <new-receipt.json>`
validates all installed candidate bytes, distribution metadata/active requirements,
installed native package files and their dependency graph. On Linux it also
inventories system packages and scans system library directories for GL runtimes.
Windows records its actual API-set namespace, OS-file version resources and
resolver results for absent delayed OS components unused in that successful
flow. The full raw OS optional-extension closure remains UNVERIFIED; the receipt
separately establishes the selected candidate installation boundary. Candidate
unresolved imports and GL-specific imports are never waived. Windows' installed
OS opengl32.dll is allowed; candidate/selected package dependencies are not.

Pass that receipt to a fresh `run --dependencies-report <receipt.json>`. The
worker recomputes the environment fingerprint and all recorded native hashes;
the controller checks that every newly loaded file belongs to the audited graph.
Different wheels, package changes, changed native bytes, unseen loaded files,
failed scenarios and import-only runs cannot qualify the complete matrix.

Windows can raise diagnostic bad-handle exceptions only because a process is
being debugged, where ordinary CloseHandle returns FALSE/error 6. See the
[Microsoft CloseHandle contract](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle).
The default observer forwards exceptions. An optional `--handle-baseline
<controls.json>` enables a narrowly proved fidelity correction: only first-chance
invalid/protected-handle exceptions at the actual OS exception dispatcher, with a
real x64 unwind frame inside OS CloseHandle/NtClose, resume ordinary return
behavior. The baseline binds both implementation DLL hashes and control source.
Unrelated and second-chance exceptions and every GL load/lookup/call remain
unchanged. No application monkeypatch or OS configuration change is involved.

Build `handle_negative_probe_windows.c` without a CRT using the VS/SDK toolchain:

```text
cl /nologo /Od /GS- /Zl /Fohandle.obj /Fehandle.exe tools/no_opengl/handle_negative_probe_windows.c /link /NODEFAULTLIB /ENTRY:control_main /SUBSYSTEM:CONSOLE kernel32.lib
python -B -m no_opengl.windows_handle_controls --control handle.exe --fixture negative_api.dll --output <new-directory>
```

The independent controls compare invalid/protected handles against undebugged
native FALSE/error 6, prove unrelated exceptions still terminate, and perform GL
lookup and direct calls after each bad handle to prove those traps still fire.
Use only a resulting `PASS_HANDLE_FIDELITY_CONTROLS` report for the same OS bytes.

Ordinary Windows symbol lookup is also exercised concurrently. A peer can have
queued a resolver INT3 before the first debug event suspended the process. The
observer keeps the original step owner and its peer holds, rewinds the queued
peer's unexecuted instruction and retries it only after restoring the trap.
Overwriting the owner would lose those holds and deadlock both threads. Timeout
reports retain pending step state for diagnosis.

```text
cl /nologo /O2 /GS- /Zl /Foresolver.obj /Feresolver.exe tools/no_opengl/resolver_race_probe_windows.c /link /NODEFAULTLIB /ENTRY:control_main /SUBSYSTEM:CONSOLE /EXPORT:GetProcAddress=auditGetProcAddress kernel32.lib
python -B -m no_opengl.windows_resolver_controls --control resolver.exe --output <new-directory>
```

The 32-thread native control performs 1024 real ordinary lookups and 1024
counted intercepted entries. Its first entry instruction is an atomic increment;
an exact count and argument/return checks prove entries were not executed twice
or altered. All threads must finish. GL lookup and direct-call negative controls
then prove observation remains active after queued peers are released. The
runner verifies the compiled entry bytes and requires actual queued deferrals.
