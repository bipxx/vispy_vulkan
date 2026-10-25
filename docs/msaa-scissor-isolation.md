# Multisample scissor boundary isolation

Date: 2026-10-25. Status: reproduced and narrowed; **not fixed**. This is
source-functional evidence from retained native leaves, not installed/profile
qualification or proof that Mesa alone is responsible.

The independent regression is `tests/native/test_scissor_boundaries.py`:
48 cases cover single/four-sample storage, 256x128 / 257x129 / 301x177 targets,
clear versus ordinary draw, and left/right/upper/inset rectangles. It asserts
actual granted sample count and exact RGBA pixels against a separately authored
rectangle. The original eight blue-background/granted-allocation cases are
also retained unchanged, so the module now collects 56 cases. This packet
executed the 48-case extension before restoring those original cases; its exact
source remains in each run record. There is no Tk dependency, shader-discard workaround, single-sample
substitution, tolerance increase or xfail hiding the result.

| Profile/control | Result | Evidence scope |
| --- | --- | --- |
| Windows retained native leaf on NVIDIA hardware | 48 passed | Actual source regression; no new wheel/SDK was built. |
| WSL llvmpipe, Mesa 25.2.8-0ubuntu0.24.04.2 | 38 passed, 10 failed | Corrected pytest launch collected all 48 cases. All failures use four-sample storage. |
| Headless clear/draw isolation under that driver | 38 matching, 10 mismatching cases | Same failure pattern in clear and ordinary draw; no Tk presentation or resize is needed. |
| Existing retained Mesa 25.2.8-0ubuntu0.24.04.4 library | Same 10 failures; all 48 output hashes identical to .2 | Library selected by a controlled local ICD descriptor; actual loaded library hash recorded. Dependencies remain system-resolved. This is not a tested newer major Mesa release. |

All completed graphics children report nine zero shutdown gauges. The native
leaf hashes are `d4148a6ce99f341e33e83ac372a543d7a7f50de19eb4f1381939f58601c1cb4c`
(Windows) and `4f502d48a453a9776ffad3d8226252f2334e7142f68b6ef26e9658868a393ba6`
(Linux); their original producer/qualification limitations remain unchanged.

The Linux failures include the right/upper boundaries of 301x177 and the inset
rectangle on all three sizes. For the right rectangle beginning at x=150,
column149 incorrectly contains half-intensity red while independently expected
black. Inset failures include fractional coverage at the adjacent outside row/
column. The strict rectangle oracle follows the half-open scissor bounds in the
[Vulkan fragment-operations specification](https://docs.vulkan.org/spec/latest/chapters/fragops.html#fragops-scissor).
No numerical waiver follows from partial multisample coverage outside that bound.

This eliminates a Tk-only or masked-clear-only explanation. The remaining
suspects are shared native/Dawn/Vulkan raster/scissor/resolve behavior. The two
Mesa revisions do not discriminate those layers. No upstream-driver defect or
fix is claimed without a lower-level control.

One Linux pytest launch collected no cases because output capture attempted to
truncate a missing temporary file on the Windows-mounted TMPDIR. Its original
traceback and failed exit remain retained. A second launch changed only output
directory and `-s`, matching the existing source-runner policy; it then reproduced
the 10 graphics failures. Windows was not rerun to manufacture a favorable result.

Retained local runs:

- `build/runs/msaa-scissor-39/`: bounded headless diagnostic, exact rectangles,
  per-case pixel hashes/error boxes/colors, original driver identity and failure.
- `build/runs/msaa-driver-control-40/`: existing .4 library control, loaded library
  hashes, unchanged output comparison and failure.
- `build/runs/scissor-regression-41/`: Windows48 pass and original Linux capture
  harness failure, source and exact launch/exit/wait records.
- `build/runs/scissor-linux-42/`: corrected Linux launch, all48 collected, exact
  10 failure names, stderr/JUnit and original nine-zero shutdown result.

Each run retains source/evidence/reproducer/licenses and has an applied, verified
cleanup receipt. Across these four runs, 45 retained records were verified and
5,243,356 bytes of owned shader-cache/marker/ICD scratch were removed; every scratch
root is absent. No native compiler, SDK/wheel build, package installation or new
environment was used. Existing dependency/driver origins were not moved.

Next: trace the actual Vulkan dynamic scissor/viewport/render-area values or run
an independent direct-Vulkan raster control with the same sample geometry. Keep
this regression as a failing requirement until a causal fix passes it and the
original Tk resize/device-loss capture test on affected profiles. The original
Linux producer, host, review, installed-artifact and hardware gates remain open.
