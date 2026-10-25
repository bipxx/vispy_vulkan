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

The follow-up `build/runs/scissor-command-trace-43/` compiles only a separate,
small pass-through diagnostic Vulkan layer using the existing compiler and
headers. The retained renderer, its original submit layer and driver are unchanged.
A first four-case attempt observed viewport/scissor/pipeline state but omitted
Dawn's dynamic-rendering entry point; its records are preserved. A second
four-case attempt adds that interception and records actual loaded library hashes.
Both attempts produce two matching left-rectangle cases and two failing
right-rectangle cases, with identical output hashes and nine zero shutdown gauges.

The second trace observes scissor `[150,0,151,177]`, viewport `[0,177,301,-177]`,
dynamic render area `[0,0,301,177]`, and four-sample pipelines. Thus the submitted
rectangle matches the independent expected bounds while outside column 149 still
contains `[128,0,0,255]`. No missing dispatch was logged. This eliminates wrong
submitted scissor/viewport/render-area values as the explanation in these cases;
it does not isolate driver rasterization from resolve or other pipeline state.
The loaded diagnostic library and system llvmpipe hashes are retained. Both
small diagnostic binaries, their sources, original licenses, commands and actual
exits/waits are retained outside scratch. Managed cleanup removed six files /
1,464,698 bytes; all 32 retained records were rehashed and scratch is absent.

The independent control in `build/runs/direct-vulkan-scissor-44/` now reproduces
that same outside column without linking VisPy or Dawn. Its versioned source is
[`tools/vulkan_scissor_control.cpp`](../tools/vulkan_scissor_control.cpp).
It creates four-sample RGBA8 storage and a single-sample average-resolve target,
uses explicit minimal vertex/constant-red fragment SPIR-V, and independently
checks exact black/red pixels after a synchronized host readback. The same
negative-height viewport and full-target render area are used. Four cases compare
left/right rectangles under conventional render passes and dynamic rendering.

Both left cases match; both right cases contain 177 incorrect pixels at column
149, starting with `[128,0,0,255]`. The executable reports an awaited device and
destroys its objects before exit 1. Loader diagnostics identify the system
llvmpipe library; its SHA-256 matches the previous source-run driver. Therefore
this failure exists below VisPy/Dawn in the tested Vulkan implementation and is
not specific to Dawn's dynamic-rendering path. This is not proof of a fixed Mesa
version, nor a waiver for the selected Linux profile. No validation-layer pass
or additional GPU support is claimed.

The reproducer needs only the existing C++ compiler, Vulkan loader and retained
Vulkan/SPIR-V headers. In a registered hygiene run, its compile command is:

```text
g++ -std=c++20 -O1 \
  -Ithird_party/dawn/third_party/vulkan-headers/src/include \
  -Ithird_party/dawn/third_party/spirv-headers/src/include \
  tools/vulkan_scissor_control.cpp -Wl,-l:libvulkan.so.1 \
  -o build/work/<registered-run-id>/control
```

Run with an explicitly selected ICD, owned cache directory and 120-second child
deadline. Exit 0 means the four pixel comparisons match, 1 means a reproduced
pixel mismatch, and 2 means setup/execution failed. Keep the actual terminal
record; a setup failure is not a passing graphics result. The exact successful
compile and failing execution commands, compiler/loader/driver hashes, header
input references, source, binary and licenses are retained in run 44. Cleanup
removed four files / 1,348,316 bytes; all 16 retained records were rehashed and
scratch is absent. No renderer/wheel/SDK rebuild or dependency install occurred.

Next: identify a compatible driver fix or discriminating driver-state control
using this minimal reproducer, then rerun the full scissor regression and original
Tk resize/device-loss capture test on affected profiles. The original Linux
producer, host, review, installed-artifact and hardware gates remain open.
