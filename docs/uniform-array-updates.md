# Uniform array update ordering

Date: 2026-10-25. The renderer now applies overlapping uniform assignments in
command order. An indexed update followed by a whole-array upload uses the later
whole-array values. A subsequent indexed update overrides its element again.
Previously, the draw packer always reapplied the stored indexed value, even when
that value was older than the whole-array upload.

The retained old development module fails four independent pixel cases covering
float, int, bool and mat2 arrays. The regression now checks both an intervening
draw and assignments queued before the first draw. Expected output is authored
from the assigned values, not from the renderer's packed buffer.

`cpp/runtime_uniform_updates.hpp` replaces the parent and retires its older
indexed descendants in both typed value stores. Unrelated names and sibling
elements remain intact. Replacement storage is acquired before retiring prior
values. Ordered maps provide prefix lookup/removal without scanning every
uniform for each scalar assignment. The CPU contract covers parent replacement,
later elements, typed replacement, sibling/prefix distinctions and nested parent
retirement. That last bookkeeping control does not implement multidimensional
shader declarations, reflection or uploads; SH-2 remains open.

Verification uses committed product source
`794f03f3827b8c5a30e8e44cf20f34dda6ab636f`:

- Windows and WSL each pass all 82 rendering checks: eight ordering cases,
  sixteen existing uniform/packing cases and 58 scissor/Tk capture cases.
- Both selected source environments pass all eight required Tk state/resource/
  failure composite branches. Every final graphics child reports nine zero
  live-resource gauges.
- Windows uniform/state/shader/artifact CPU contracts and the Linux uniform
  contract pass. The shader contract includes normalization, reflection,
  SPIR-V validation and packing.
- All 337 affected native/epoch/index/inventory source checks pass. The original
  required obligations and selected criterion/dependency closure remain intact.

The existing installed-wheel immediate-state CI smoke now includes eight array
oracles and verifies the program/GLIR source members as well as its prior four
members. Its pixel helper passes against both fresh source modules. A targeted
control verifies six actual members of the older installed wheel and catches
the old array pixel error. The initial attempt to use the entire current smoke
on that legacy wheel stops earlier because it predates immediate `glViewport`
support; that separate result is retained and is not evidence of the array oracle.
The complete updated installed entry point still needs its fresh-head CI wheel.

Only first-party native leaves were rebuilt. Windows reused the verified
immutable SDK, and Linux reused its existing vendor archives under its explicit
experimental source-only status. No vendor build, environment installation or
source-history clone occurred. Original licenses and source/exit/wait evidence
are retained under `build/runs/uniform-write-order-52/` and
`build/runs/uniform-order-native-53/`.

Preparation now references fresh source observations for both native leaves and
the tested Mesa 26.1.8 Linux configuration. Previous profile files and failures
remain preserved. These observations are not independent approvals, installed
candidate receipts, native producer admission or full API completion. Both
candidate wheels and promotion proofs remain absent.

Cleanup removed 20,630 owned scratch files / 333,322,636 bytes from the native
packet. All 297 retained source/evidence/artifact/license records were rehashed
and scratch is absent. The earlier failing regression packet is also retained
and cleaned. Current/previous native leaves remain immutable; vendor origins
were neither moved nor rewritten.
