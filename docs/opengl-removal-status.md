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

Stock Qt feasibility is platform-specific. Windows Qt6Gui/qwindows PE inspection
found no direct GL imports; a selected OS-resolved transitive closure still has
unresolved optional dependencies and is not a complete Gate 3 pass. Linux stock
PyQt6-Qt6 6.11.2 QtGui requires libEGL.so.1 and libGL.so.1; qxcb requires libGL.so.1.
Therefore stock Linux GUI packages fail the strict installation/link gate.
A real no-GL Qt and binding build is underway; removing Python QtOpenGL imports
alone cannot qualify that dependency graph.

The Windows native collector observes startup/transient DLL events, native
symbol lookup and public GL calls across the debuggee process tree. Independent
C controls detect lookup without invocation, direct calls and load/unload of a
forbidden runtime name; a safe control passes. The Linux glibc collector compiles
with warnings as errors and detects loader events and native dlsym bindings.
Its direct local-call control exposes missing API coverage, so Linux aggregate
execution/load absence gates remain UNVERIFIED pending native debugger tracing.

Local evidence from this validation worktree is retained under
`build/no-opengl/`: stock Qt dependency reports, Windows/Linux collector controls,
source import checks and 27 CPU package/observation contract tests. These are
development evidence, not an installed-artifact release claim. The coordinator
is building fresh Windows/Linux wheels and owns integrated runtime qualification.

Remaining work includes Linux process/API observation, the no-GL Qt package and
its complete runtime graph, fresh installed-artifact headless/Qt functional and
recovery runs, and each required host/plugin workflow. Napari-threedee rendering
admission is still pending; its prior source/import inventory is not rendering
qualification. DIVE and visbrain remain explicitly unadmitted inventory rows.
No historical OpenGL oracle captures or frozen fixture provenance were rewritten.
