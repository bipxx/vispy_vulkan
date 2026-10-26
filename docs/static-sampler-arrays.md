# Static sampler arrays and cube resources

The SH-2 source implementation now retains ordered sampler-array dimensions,
expands bounded literal-index leaves, and assigns each leaf its own texture and
sampler bindings. It supports the existing six scalar sampler types: sampler1D,
sampler2D, sampler3D, samplerCube, isampler2D and usampler2D. Cross-stage shape
matching distinguishes equal-product shapes. Partial, excessive, out-of-bounds,
floating and dynamic indices reject explicitly. Dynamic indexing remains SH-1
work; this packet does not provide it.

The first Windows rendering attempt passed 113 checks and failed all three cube
array ranks because native command dispatch did not support TextureCube. The
failed module, source and results remain retained. The correction implements
six square CPU faces using a 2D six-layer allocation and explicit cube view,
cube-aware sampler layouts, dimension validation, and ordered face uploads.
Cube and volume allocations remain distinct. Original AGPL, BSD and dependency
notices are preserved.

The corrected source passes 165 focused pytest cases on Windows Vulkan and WSL
Mesa 26.1.8 software Vulkan. Each platform also passes the exact installed-smoke
helpers against its fresh source module: eight uniform-order cases, 48 numeric
array cases, 48 composed-array cases, 18 sampler type/rank cases, and a six-face
cube control with one-face partial update. All nine shutdown gauges are zero.
The sampler tests and installed smoke share the pixel oracle, including a clear
before every draw, distinct full-width integer values and leaf rebinding.
Native normalization/reflection and texture CPU contracts pass on both platforms;
Windows state, uniform-update and artifact contracts also pass. These SDK-based
CPU contracts do not directly enable the Tint reader; rendering exercises the
actual Dawn device path.

Local reconstruction records are under
`build/runs/sampler-array-shapes-61/`: the initial `windows-sampler` failure,
`cube-failure-native.json`, corrected `windows-final`/`linux-final` results,
native build commands and terminal retention/cleanup receipts. Retained native
leaves are source-functional development artifacts, not admitted producers or
installed wheel qualification. The existing SDK and immutable vendor archives
were reused; no dependency rebuild or new environment was needed.

Published head `79111ac22166de56db6983dc1b30c3d15f6d80ad` is an earlier Python
checkpoint. Its Linux wheel job passed; CPU CI exposed a missing deviation entry
for the intentionally changed Variable source. Adding that entry passes the
original local parity assertion without changing upstream hashes or the test.
That earlier head supplies no sampler/cube CI evidence. Old-head success does
not transfer to the new source.

Product source is now frozen locally at
`efa3ced2ceef44896fd1357a466e6d8ea0eb4f0f`. Fresh complete eight-branch Tk
composites pass on both retained modules, with all nine shutdown gauges zero.
New static-sampler profiles preserve the previous composition profiles and bind
the changed native/source identities; the requested criteria, closure and original
execution ledger are unchanged. All 527 affected source/preparation/inventory
checks pass. The real subject remains incomplete and admitted false. Records
are in `build/runs/sampler-array-preparation-62/`; publication and new-head CI
remain separate next steps. The native packet's cleanup reclaimed 141,551,220
bytes and rehashed 193 retained records, including the meaningful failure.

Remaining obligations include dynamic sampler indices, other opaque/storage and
stage-interface forms, matrix/array attributes and the wider shader inventory.
Cube mipmaps, depth sampling, rendering into faces and edge/seam behavior are
not established by the center-face/upload controls here. Full parent support,
independent review, producer admission, installed qualification and mandatory
host/hardware proof remain open. Metal remains experimental.
