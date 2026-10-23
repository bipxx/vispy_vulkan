# OpenGL runtime removal status

The runtime-removal implementation is in progress. No complete release matrix
is qualified yet. `compat/no-opengl-matrix.json` records the mandatory Windows
Vulkan and WSL software Vulkan/X11 rows, their binding/host pins, features and
three independent gates. Metal remains experimental. Native Linux hardware
qualification remains separate from WSL software results.

The explicit shipping contract retains the Dawn `gl2`/`glplus` compatibility
aliases and excludes 16 executable legacy OpenGL loaders/backends. Exact wheel
membership and source-byte audits use the manifest; extracted snapshots need no
Git metadata. Original BSD and third-party notices remain packaged alongside the
AGPL implementation license. Framebuffer configuration has a CPU contract target.

Stock Qt feasibility is platform-specific. Linux stock QtGui/qxcb require GL
or EGL, and stock PyQt5/PySide6 bindings contain unresolved QOpenGL references.
The Linux PyQt6 profile has therefore been built from preferred Qt/PyQt source
with OpenGL/EGL disabled. Its relocated 48-ELF payload, original notices and
exact system runtime pins are packaged reproducibly. Linux Qt5/PyQt5 and
Qt6.12/PySide6 source builds and their qualification remain separate work.

Windows selected PyQt6, PyQt5 and PySide6 profiles now have explicit manifests,
offline hash-pinned requirements and preserved native bytes/original notices.
Repeated package builds are byte-identical; fresh installed module and QWidget
paint/capture checks pass. Optional GL/Quick/WebEngine modules are excluded.
These package checks alone do not qualify the full binding matrix. The admitted
Windows GUI path renders Vulkan offscreen and presents through QImage/QPainter:
a Qt-free Win32 Vulkan WSI control reproduced an NVIDIA ICD GL load/lookup,
so native Win32 Vulkan presentation is outside the strict profile.

The Windows native collector observes startup/transient DLL events, native
symbol lookup and public GL calls across the debuggee process tree. Independent
C controls detect lookup without invocation, direct calls and load/unload of a
forbidden runtime name; a safe control passes. The Linux glibc collector compiles
with warnings as errors and detects loader events and native dlsym bindings.
The cooperating ptrace debugger now follows the complete fork/exec task tree and
stops at loader object boundaries to instrument public GL exports before user
code resumes. Independent controls detect direct local -Bsymbolic calls as well
as inherited fork and new exec child calls. Sanitized dynamic exec environments
and static ldconfig helper coverage have real controls. Auditor-only mode remains
explicitly UNVERIFIED for aggregate absence gates. Private implementations/manual
export parsing are outside both platform observers' public API scope.

Dependency receipts bind exact installed wheel bytes, package/native inventory,
actual selected process loads and resolved native dependencies. Linux receipts
also scan system runtime files and package inventory in the fresh rootfs.
Windows permits platform-owned opengl32 to exist; candidate GL imports remain
blocking. Absent optional delayed OS components retain raw closure limitations
and require evidence that the selected admitted flow succeeds without them.
Installed script runs require explicit global native shutdown and all nine
resource gauges at zero; process exit alone is insufficient.

Local evidence from this validation worktree is retained under
`build/no-opengl/`: stock Qt dependency reports, Windows/Linux collector controls,
source import checks and 60 passing CPU package/observation contract tests
(one platform-specific test skipped on Windows, with a separate real WSL
launcher control). These development checks are distinct from the installed
artifact results below. The coordinator owns integrated runtime qualification.

Recorded installed-artifact results are scoped to the exact tested bytes:

- Linux renderer SHA256
  `2e7097e77df6da99e233eb7eb4f6021678e3698bc575c00f6c1a72da4fc76dc2`:
  source-built PyQt6 mapped X11 QWidget passes all three gates. Actual napari,
  registered napari-threedee and Glue workflows also pass all three gates,
  complete functional lifecycle/recovery and explicit nine-zero shutdown.
  Host evidence is `vispy_vulkan-opengl-python/build/no-opengl-linux-hosts-2/summary1.json`
  and each `<scenario>-native1/qualified2.json`. These are WSL Lavapipe software
  results, with exact pinned CPU runtime additions; they do not qualify Linux
  hardware or another binding.
- Windows readback renderer SHA256
  `20c4436325eebbd1ade61779e49c7ca1344627bdeff0c5a95e336e002949eb64`:
  persistent selected PyQt6 Glue workflow passes all three gates with functional
  lifecycle and nine-zero shutdown (`no-opengl-persistent-native1/profile-glue-fixed-glue-allgates2.json`
  in the Python worktree). Other recorded QWidget/host flows pass native
  execution/load gates; final selected dependency closure and replay remain
  per-environment requirements. The core-only pinned TBB profile addresses the
  Windows Numba TBB runtime closure without shipping unused HWLOC plugins.
- Earlier Windows `6bef4403...` headless clear/lines/text/image/recovery, markers
  and ten framebuffer cases have scoped three-gate receipts. These remain
  historical evidence and do not qualify a newer renderer artifact.
- Fresh Linux N23 wheel SHA256
  `39a725766dab08dc6e284af807d40c44202584d4972e5714f34691e6e4375c41`
  built successfully from source `531b...`; installed qualification is pending.
  Newly integrated endpoint/sample-zero native changes also require GPU
  qualification on freshly built artifacts. No older result is transferred to
  these changed native bytes.

At the 2026-10-23 execution checkpoint, Linux continuation is blocked by the
WSL filesystem state. The resumed Qt 6.12 build reached 1480/1636 actions before
terminating with `EROFS`; both the resume receipt and terminal build-results
write failed with `OSError 30: Read-only file system`. All 15 recorded build
processes subsequently exited. The filesystem reported an emergency read-only
fallback, and even `/bin/lsblk` returned an I/O error. The retained Windows-side
receipt is
`vispy_vulkan-opengl-native/build/no-opengl-qt-build-1/qt612-resume-erofs1.json`.
This is an infrastructure blocker, not a successful Qt/PySide build or a new
runtime qualification result. No WSL builds or repair commands are running.
An offline filesystem check/repair awaits explicit user approval because it
changes filesystem metadata and there is insufficient space for a 135 GB
backup. Historical Linux proofs above remain scoped to their earlier exact
artifacts; filesystem recovery and fresh installed verification are required
before relying on those environments for further qualification.

The separate Windows N3/N4/N5 SDK-backed build was still running at this
checkpoint from source `99d110b6b` and frozen source snapshot `dc290a...`.
Its actual 92 GPU cases remain pending. Current Windows CPU checks pass:
60 no-OpenGL contract tests with one platform skip, plus six canonical
package/source-contract tests. Those checks do not replace the pending native
build, installed GPU runs or three-gate receipts for the changed artifact.

Remaining work includes final changed-native-artifact GPU/functional/native
replays, all mandatory feature cases, Windows selected PyQt5/PySide6 complete
receipts, Linux Qt5/PyQt5 and Qt6.12/PySide6 source packaging and actual runtime
qualification, and the remaining required host/platform matrix. The initial
PyQt6 host results above are real rendering admission for those exact artifacts;
the complete release matrix remains incomplete. DIVE and visbrain remain
explicitly unadmitted inventory rows.
No historical OpenGL oracle captures or frozen fixture provenance were rewritten.
