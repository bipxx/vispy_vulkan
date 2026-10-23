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
incomplete task lifecycles or execs without an auditor prevent PASS. Private
implementations and manual export parsing remain outside its public API scope.
The auditor alone still produces UNVERIFIED aggregate execution/load gates.

Build the independent synthetic native controls (they implement no graphics):

```text
# Linux, in an owned build directory
cc -shared -fPIC -O2 -Wall -Wextra -Werror -o loader_audit.so tools/no_opengl/loader_audit_linux.c
cc -O2 -Wall -Wextra -Werror -o debugger_linux tools/no_opengl/debugger_linux.c
cc -shared -fPIC -O0 -Wall -Wextra -Werror -Wl,-Bsymbolic -o negative_api.so tools/no_opengl/negative_probe.c -ldl
PYTHONPATH=tools python -B -m no_opengl.negative_controls --fixture negative_api.so --native-auditor loader_audit.so --native-debugger debugger_linux --output <new-directory>

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
