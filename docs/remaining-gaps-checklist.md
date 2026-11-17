# Remaining gaps checklist

## Comprehensive current gap register

**Wave 5 (`API-05` / `API-06` collections `9/9` + `jupyter_rfb` Dawn backend, `PLAT-02` `cp311`/`cp313` wheels, & `tk-state-resource-17` unreviewed preparation) update — 2026-11-16:**
- `W5-TIER1` (`API-05`, `API-06`, `API-06-READBACK-GEOMETRY`, `LIF-05`, `app.backend.jupyter-rfb`): [tier1-collections-jupyter-rfb](../compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json) (`2a3ec57f…`); `installed-functional` at source freeze `1006` (`e3ee53ca…`, commit `3daf19be…`, tree `6c8d3bad…`, base `88c0e651…`, `6` CRLF runtime files + `3` LF test files, `85/85` CPU contracts `12/5/41/6/21` in `cpu-checks.log` `0ca3ae9b…` + CPython `3.14.0` asyncio `TimerBackend` pass): resolves all `3` former Wave 3 `vispy.visuals.collections` bounds (`9/9` collection configurations rendered) and verifies `vispy.app.backends._jupyter_rfb` / `_offscreen_util` (`3/3` live GPU `0` skipped, `10/10` zero Dawn shutdown gauges).
- `W5-PLAT02` (`PLAT-01`, `PLAT-02`, `PLAT-03`, `PLAT-08`, `LIF-07`): [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`); `installed-functional` across `6` retained `0.17.0+vulkan.2` wheels (`win_amd64`: `cp311` `834fe5f7…` `1008`, `cp312` `ec8097cf…` `1007`/`1007b`, `cp313` `793dab79…` `1009`; `manylinux_2_39_x86_64`: `cp311` `fc8dd6cc…` `1011`, `cp312` `513088c1…` `1010`/`1010b`, `cp313` `1362eb6a…` `1012`), passing `44/44` CTests on fresh `cp311`/`cp313`, `75/75` GPU cases per ABI on Windows RTX 4090 & WSL Mesa `9c5c41b3…`, `14/14` `cp312` Tk capture/4-phase recovery (`1007b`/`1010b`), and `225/225` (`75/75` × `3` ABIs) on physical Colab `NVIDIA Tesla T4` (`1013` `254329bd…`).
- `Preparation 17` (`gap-w5-preparation17-1014` `71511a45…`, `review-packet.json` `b7e06cb0…`, `reviewed-delta.json` `fcf60301…`): unreviewed [tk-state-resource-17](../compat/candidates/tk-state-resource-17/candidate.json) (`de906e31…`, scope `9e11b4f6…`, `reviews: null` UNBOUND pending `1014r`/`1015`), conserving `142` obligations / `128` bindings / `8` mandatory rows. `PLAT-02` (`cp310`/`cp314` GPU wheels, strict admission, and public delivery unclaimed), `PLAT-03`, `PLAT-08`, `API-05`, and `API-06` remain `[ ]` open.

**Wave 4 (`PLAT-03` / `PLAT-08` Linux physical NVIDIA GPU `installed-functional`) update — 2026-11-15:**
- `W4` (`PLAT-01`, `PLAT-03`, `PLAT-08` + `API-05`, `API-06`, `API-06-READBACK-GEOMETRY`, `STA-01`, `TEX-01`, `SCI-06`, `SHD-01`–`06`, `LIN-01`, `SCI-01`–`05`, `LIF-01`–`08`, `LIF-07-NATIVE-ADMISSION`): [plat03-08-linux-nvidia-colab](../compat/api-acceptance/plat03-08-linux-nvidia-colab-v1.json) (`b8a5bd8e…`, hygiene audit `1001` `7a26baec…`); `installed-functional` on exact `manylinux_2_39_x86_64` wheel `e600b29e…` (`_dawn` `fcf0c5a8…`, source `613cacfb…`, `repo_main_base` `3ba0cd50…`, `537/537` members verified before/after, `0` source overrides, `10/10` zero Dawn shutdown gauges per worker, `default_sessions_unchanged: true`) across two Google Colab `Linux x86_64 glibc 2.39` (`kernel 6.6.159+`; `Ubuntu 24.04.4 LTS` observed via `/etc/os-release` in `998`; `Xvfb :99`, `NVIDIA 580.82.07`, Vulkan `1.4.312`) physical discrete GPU cells:
  - **Cell 1 — NVIDIA Tesla T4 (Turing):** `gap-w4-1-colab-t4-core-998` (`1bbfe275…`, `117/117` `installed-functional` pass: `56` `W1` readback/query + `11` `W2-2` + `10` `W2-3` + `24` `W2-4` + `16` `W3-3` across 5 `-B -I` workers) and `gap-w4-2-colab-t4-gui-999` (`c6aec5e3…`, `31/31` `installed-functional` GUI pass: `19/19` `W2-5` `PyQt6 6.12.1`/Qt `6.12.0` + `tkinter 8.6` raster and `12/12` `W3-2` across `PyQt5 5.15.11`/`PyQt6 6.12.1`/`PySide6 6.12.0` incl. `1.5x` HiDPI with `0` competing Qt modules; plus separate `11/11` `installed-experimental` `W3-1` native Tk X11 WSI probe with `default_presentation: "raster"`, `native_admitted_mandatory_matrix: false`, `wsi_boundary_observed: false`).
  - **Cell 2 — NVIDIA L4 (Ada Lovelace):** `gap-w4-3-colab-l4-1000` (`747a7b0c…`, `136/136` `installed-functional` pass: `56 + 11 + 10 + 24 + 16 + 19` across 6 `-B -I` workers).
  - **Open boundaries (`PLAT-03` & `PLAT-08` remain `[ ]`):** `scoped_admitted: false`, `artifact_admitted: false`, `publicly_delivered: false`, `published: false`, `full_inventory_complete: false`; non-NVIDIA Linux GPUs (AMD RADV, Intel ANV) and Mesa NVK (`non_nvidia_linux_gpus_claimed: false`), physical Xorg monitor scanout vs `Xvfb` (`physical_display_scanout_claimed: false`), physical HID/multi-monitor (`physical_hid_claimed: false`, `physical_multimonitor_claimed: false`), and native Wayland `PLAT-05` (`wayland_claimed: false`) remain open (superseding only the prior total absence of physical Linux GPU evidence in the historical Wave 3 / Post-971 notes below).

**Wave 3 installed-experimental (`W3-1`), installed-functional (`W3-2`/`W3-3`), & additive `W3-4a` update — 2026-11-15:**
- `W3-1` (`LIF-07`, `LIF-07-NATIVE-ADMISSION`): [tk-native-current-wheels](../compat/api-acceptance/tk-native-current-wheels-v1.json) (`224701fe…`, `985`/`986`, `11/11` pass/platform); installed-experimental on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + system Mesa `25.2.8`); `default_presentation: "raster"`, `native_admitted_mandatory_matrix: false`, `scoped_admitted: false`; no full upstream parity claim.
- `W3-2` (`LIF-02`/`03`/`04`/`06`, programmatic single-display `LIF-08`): [lif02-08-qt-multibinding-windows](../compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json) (`9001513c…`, `987`) & [lif02-08-qt-multibinding-wsl](../compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json) (`5fb417d3…`, `988`, `12/12` pass/platform across PyQt5/PyQt6/PySide6); installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `physical_multimonitor_claimed: false`, `physical_hid_claimed: false`, `scoped_admitted: false`; no full upstream parity claim.
- `W3-3` (`API-05`/`06`): [api05-plot-transforms-windows](../compat/api-acceptance/api05-plot-transforms-windows-v1.json) (`4278e1bd…`, `989`) & [api05-plot-transforms-wsl](../compat/api-acceptance/api05-plot-transforms-wsl-v1.json) (`6cd157b0…`, `990`, `16/16` pass/platform) (6 rendered collections + 3 documented upstream bounds: `PointCollection` agg/local WGSL link, `SegmentCollection` raw/shared Py3 float division, `PathCollection` raw `NullTransform() + str`); installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `scoped_admitted: false`; no full upstream parity claim.
- `W3-4a` (`HOST-03`): [no-opengl-optional-hosts-current-v1.json](../compat/no-opengl-optional-hosts-current-v1.json) (`0f7159d7…`); additive current-wheel optional-host view on `9919a280`/`e600b29e` (preserving `no-opengl-matrix.json` `230b12f3…` untouched without `r1`, and `no-opengl-napari-0.10.0.json` `a724432b…` row `windows-vulkan-napari-threedee-pyqt6` `r1 == "open"`); not scoped-admitted, not delivered, no full upstream parity claim. Hardware-blocked (`PLAT-03/04/05`, physical `LIF-06`/`LIF-08`), `PERF-01` optical timing, `DIVE` Qt6, and upstream collections bounds remain open.

As of 2026-11-14, the selected Windows/WSL release is delivered. Its exact
artifacts are Windows `4f537748…` and Linux `dfe1033f…`, qualified at `90348a8`
and merged as `76cc5e8c` from runtime source `275888b5`.
[Release evidence](../compat/api-acceptance/orphan-release-public-delivery-v1.json)
and the [public delivery report](https://github.com/bipxx/vispy_vulkan/releases/download/v0.17.0-vulkan.2-orphan-retirement-90348a8/delivery.json)
separate that completed subset from the broader backlog below.

This register covers **44 documented workstreams and two named
subcases**. These are tracking groups, not 46 missing features or 46 defects.
Some combine implemented behavior with missing combination/profile evidence.
The original 142 inventory obligations and historical discovery catalogs keep
their original meaning; a complete method-level compatibility audit remains API-05.

Types distinguish known issues, partial coverage, evidence/qualification gaps,
unsupported or deferred boundaries, and optional work. A completion condition
may establish a bounded supported contract or an explicit unsupported disposition;
it must not turn a boundary into an implementation claim. No new feature or
hardware campaign is selected by listing it here. Cybersecurity work is excluded.

### Complete list at a glance

2026-11-16 (Wave 5 collections `9/9`, `jupyter_rfb` Dawn backend, `cp311`/`cp313` wheels, & unreviewed `tk-state-resource-17`): [tier1-collections-jupyter-rfb](../compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json) (`2a3ec57f…`) and [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`) record `installed-functional` verification at source `3daf19be…` (`1006` `e3ee53ca…`, `85/85` CPU contracts `12/5/41/6/21` in `cpu-checks.log` `0ca3ae9b…`) across `6` `0.17.0+vulkan.2` wheels (`cp311`/`cp312`/`cp313` × `win_amd64` & `manylinux_2_39_x86_64`: `834fe5f7…`, `ec8097cf…`, `793dab79…`, `fc8dd6cc…`, `513088c1…`, `1362eb6a…`) on Windows RTX 4090 (`1007`/`1007b`/`1008`/`1009`), WSL Mesa `9c5c41b3…` (`1010`/`1010b`/`1011`/`1012`), and physical Colab `NVIDIA Tesla T4` (`1013` `254329bd…`, `225/225`), resolving all `3` former Wave 3 `collections` bounds (`9/9` rendered) and passing `3/3` live `jupyter_rfb` GPU cases (`0` skipped). Source-only `gap-w5-preparation17-1014` (`71511a45…`, `review-packet.json` `b7e06cb0…`) prepares unreviewed `tk-state-resource-17` (`de906e31…`, `reviews: null`); `PLAT-02` (`plat02_closed: false`), `PLAT-03`, `PLAT-08`, `API-05`, and `API-06` remain `[ ]` open (`scoped_admitted: false`, `publicly_delivered: false`).

2026-11-15 (Wave 4 Linux physical NVIDIA GPU `installed-functional`): [plat03-08-linux-nvidia-colab](../compat/api-acceptance/plat03-08-linux-nvidia-colab-v1.json) (`b8a5bd8e…`) records `installed-functional` execution of exact Linux wheel `e600b29e…` (`_dawn` `fcf0c5a8…`, source `613cacfb…`) on Google Colab physical NVIDIA discrete GPUs (`Linux x86_64 glibc 2.39`, `kernel 6.6.159+`; `Ubuntu 24.04.4 LTS` observed via `/etc/os-release` in `998`; `NVIDIA 580.82.07`, Vulkan `1.4.312`, `Xvfb :99`): `Tesla T4` (`998` `1bbfe275…` `117/117` core + `999` `c6aec5e3…` `31/31` Qt5/Qt6/PySide6/Tk GUI, plus separate `11/11` `installed-experimental` `W3-1` native Tk X11 WSI probe) and `NVIDIA L4` (`1000` `747a7b0c…` `136/136` core+GUI), with hygiene audit `1001` (`7a26baec…`). `PLAT-01` gains Linux physical NVIDIA `installed-functional` evidence alongside WSL software Vulkan, while `PLAT-03` and `PLAT-08` remain open (`[ ]`) for non-NVIDIA Linux GPUs (AMD RADV, Intel ANV) and Mesa NVK, physical Xorg monitor scanout vs `Xvfb`, physical HID/multi-monitor, Wayland (`PLAT-05`), and strict release/scoped admission (`scoped_admitted: false`, `artifact_admitted: false`, `publicly_delivered: false`).

2026-11-15 (Post-971 consolidation): `API-06-READBACK-GEOMETRY` / `tk-state-resource-16`
(`128` bindings / `8` mandatory rows, `full_inventory_complete=false`) is `scoped-admitted`
+ `publicly-delivered` (`965`–`971`/`980`–`983`, release `v0.17.0-vulkan.2-readback-geometry-f5c00c9`,
PR #85 `38753fc0…`, `delivery.json` `a4737a31…`, `completion-audit.json` `92b932ea…`).
`installed-functional` on `9919a280`/`e600b29e` (`Windows RTX 4090` + `WSL Xvfb Mesa 9c5`):
`W2-2/W2-3` (`972`/`973`/`973r` `ef86bcbb…`; [sta01-tex01-sci06-windows](../compat/api-acceptance/sta01-tex01-sci06-windows-v1.json), [sta01-tex01-sci06-wsl](../compat/api-acceptance/sta01-tex01-sci06-wsl-v1.json), [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json)), `W2-4` (`974`/`975`/`975r` `f21aa13f…`; [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json)),
`W2-5` (`976`/`977`/`977r` `863bcb65…`; [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json)), `W2-6` (`978` `4dc8b6d5…`/`979` `d7576be2…`/`979r` decision `56c8b9a4…`, [host01-06-current-wheels](../compat/api-acceptance/host01-06-current-wheels-v1.json) `e36a08c2…`). `historical-reconciled`: `W2-1` (`959` `af7cc83d…`/`959r` decision `b7ed4d1c…`, `dba78b6f…`). Remaining `excluded/deferred/hardware-bounded` (16 items):
`MAC-01..03`, physical Linux GPU/HID/Wayland, physical optical timing, cybersecurity skipped,
and broader upstream API parity (`full_inventory_complete=false`).

2026-11-15: `legacy-project-cleanup-945` (`8cc281b5…` / `5d9b772d…` / `f9de0fc3…`)
reclaimed 7.9153 GiB physical (7.94 GiB `C:\`; 9,655 files, 4,984 empty dirs, 0
overlaps), restoring `C:\` reserve. [WSL945](../compat/api-acceptance/readback-wsl-strict-v1.json)
(`29bce237…`, `PASS_READBACK_WSL_STRICT_MATCHED_COHORT_AND_JOINED_943_ACCEPTANCE`) then
passed on exact Linux wheel `e600b29e…` (`_dawn` `fcf0c5a8…`) and source `613cacfb…`
(CPython 3.12.13, Tk 9.0 raster, pinned patched Mesa `9c5c41b3`, Xvfb, 537 members,
0 source overrides, 16 Linux feature-profile joins / 48 strict raw gates across
`tk-state-resource-failures` and `tk-capture-formats` on `replay-0`, 0 shutdown gauges),
joined without rerunning pytest to `943` (`324e2f41…`); scratch cleaned (`12` files /
`92,589,425` bytes reclaimed, `151` retained inputs verified, `T\build\work == ['p']`,
WSL `build/work == []`; `readback-wsl-strict-945-capacity-refusal` preserved; no
row/artifact/strict-selection admission claimed).

2026-11-15: [Windows944](../compat/api-acceptance/readback-windows-strict-v1.json)
passes the current Windows CPython 3.12.8 / RTX 4090 / Tk 8.6 strict
runtime-observer cohort on exact wheel `9919a280…` and source `613cacf…` (16
feature-profile joins, 48 strict raw gates across `tk-state-resource-failures`
replay-1 and `tk-capture-formats` replay-0, zero source overrides, 537 installed
members, nine zero workflow shutdown gauges), joined without rerunning pytest
to exact declared acceptance `942` (2 tests / 6 pytest phases, 10 zero shutdown
gauges); scratch cleaned (`62,914,104` bytes / `1,636` files removed, `77`
retained inputs verified; no row/artifact admission; `replay-0` attempt retained
for attempt-history review). Pre-registration `tools/build_hygiene.py preflight`
for `readback-wsl-strict-945` (`512 MiB` peak) refused with exit 2
(`Expected peak would cross minimum disk reserve at C:\`, retained at
`D:/vispy-vulkan-managed/build/runs/readback-wsl-strict-945-capacity-refusal/verification.json`,
zero scratch created) because external workstation activity reduced `C:\` free
space below the `10 GiB` reserve while `D:\` retains ~`273.96 GiB` free; new
scratch work stopped per `AGENTS.md` disk-budget rule.

[940 scope review](../compat/api-acceptance/readback-preparation16-reviewed-scope-v1.json)
and [941 binding](../compat/api-acceptance/readback-preparation16-bound-v1.json)
now validate the prepared source/scope, both original native producers and both
new archives. [Windows942](../compat/api-acceptance/readback-declared-acceptance-windows-v1.json)
and [WSL943](../compat/api-acceptance/readback-declared-acceptance-wsl-v1.json)
each pass the two exact declared acceptance fixtures/all six pytest phases with
zero overlays and zero shutdown gauges. Both targets are cleaned. Remaining
readback delivery work: strict runtime-observer/host-profile evidence, contributing
retention, final-head CI, protected integration and verified publication. Broader
API/scientific/lifecycle/host/platform workstreams below remain open.

Latest qualification progress: [936 Windows Tk](../compat/api-acceptance/readback-candidate-tk-windows-v1.json)
and [937 WSL Tk](../compat/api-acceptance/readback-candidate-tk-wsl-v1.json) each
pass 14 display/capture tests plus four recovery phases on the new wheels; both
targets are cleaned. [Preparation16](../compat/api-acceptance/readback-preparation16-v1.json)
validates the current runtime/profiles/two archives, preserving 142 obligations,
128 bindings/eight required host rows and all 537 historical candidate JSONs.
The initial 44 CI policy contracts pass. Fresh940review and941binding now
validate source/scope and both original native producer joins; strict installed/
profile admission remains separate.
Native schema validation is not producer admission. Fresh independent review,
current strict workflow/host evidence, final CI, integration and delivery remain.

Readback artifact follow-through: [932](../compat/api-acceptance/readback-source-freeze-v1.json)
freezes the reviewed source at `613cacf…`, with unchanged native inputs.
[933 Windows](../compat/api-acceptance/readback-candidate-windows-v1.json)
installs new candidate `9919a280…` offline and passes all 56 state/query/readback
tests with zero overrides, 537 members and ten zero shutdown gauges. Windows
scratch is cleaned. Linux candidate `e600b29e…` is assembled; a launcher-only934
failure is preserved/cleaned and successor935 installed verification passes below.
Artifact admission, final CI, protected integration and verified delivery remain.

Successor [WSL935](../compat/api-acceptance/readback-candidate-wsl-v1.json) now
also passes all 56 cases after an actual offline install of `e600b29e…`, with
zero overlays, 537 package members before/after and ten zero shutdown gauges.
Its scratch is cleaned (27,783,492 bytes; 104 retained inputs verified). Both
updated wheels have finite installed proof; independent artifact/profile
admission, final qualification metadata/CI, integration and delivery remain.

| Area | Workstreams | IDs | Remaining scope |
| --- | ---: | --- | --- |
| Reliability | 2 | BUG-01/02 | Rare startup stall and historical OLE-hang relationship. |
| Public API | 2 | API-05/06 | Method/value inventory and exact artifact/profile coverage. |
| Rendering | 10 | SHD-01–06, STA-01, TEX-01, LIN-01/02 | Shader forms, layouts, geometry replacements, state, typed sampling, line partitioning and deferred line MSAA. |
| Scientific/scene | 6 | SCI-01–06 | Points, filter composition, cameras, volumes, fixture applicability and stencil capture. |
| Lifecycle/input | 9 | LIF-01–08, LIF-07-NATIVE-ADMISSION | Real faults, window ownership, minimized restoration, capture, input, Tk and monitor/DPI behavior. |
| Applications | 4 | HOST-03–06 | Current napari/Glue/threedee profiles, DIVE, Visbrain and rendered host workflows. |
| Platforms/packaging | 6 | PLAT-02–06, PLAT-08 | Additional Python/architecture wheels, physical Linux GPUs, Metal graphics, Wayland and driver cells. |
| Performance/tooling/history | 5 | PERF-02–04, TOOL-02/03 | Conversion/batch optimization, measured build/memory claims, compiler caching and a missing historical receipt. |
| **Total** | **44** | | Detailed remaining behavior and completion conditions follow. |

Two named subcases remain under these parents: **API-06-READBACK-GEOMETRY**
and **SCI-02-CLIP-ALPHA-BLEND**. The former has an accepted source fix and
Windows/WSL zero-overlay candidate install evidence; formal artifact qualification,
integration and delivery remain. The latter's maintained test is already merged;
broader composition and scientific claim/profile mapping remain.

Current readback successor: [925](../compat/api-acceptance/readback-native-int-range-source-v1.json)
also fixes signed native-int conversion overflow before submission. Its exact
source passes 57 related CPU contracts and 19 rendered/recovery cases each in
[Windows926](../compat/api-acceptance/readback-native-int-range-windows-overlay-v1.json)
and [WSL927](../compat/api-acceptance/readback-native-int-range-wsl-overlay-v1.json).
These supersede 922/923 only for the new source hash; earlier evidence remains
historical. Final-source review928 rejected patch presentation; corrected byte-exact929
packet preserves identical tested source and fresh correction review930 accepts the unchanged exact source; no release qualification is implied.

[930 final source acceptance](../compat/api-acceptance/readback-native-int-range-source-review-v1.json)
withdraws 928's EOL finding based on the [929 byte-exact patch](../compat/api-acceptance/readback-byte-exact-patch-v1.json).
The earlier expanded patch and rejection remain preserved. The tested source
hashes are unchanged, and the functional proofs still apply. Updated-wheel production
and finite zero-overlay installed proof now pass in933/935. What remains is
artifact/profile admission, final qualification metadata/CI, integration and verified delivery; parent API-06/LIF-05
remain partial.

Available-machine work should start with the readback follow-through and concrete
API/rendering cases, then scientific/lifecycle/host contracts. Hardware checks
require the relevant machine/device; optional optimizations need a measured
benefit. Full upstream parity is not a release requirement. These different kinds
of work cannot support a meaningful single percentage-complete calculation.

### Reliability investigations

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| BUG-01 | Known issue | Rare Windows startup stall; cause and a reliable regression remain unresolved. | Capture recurrence with the existing watcher, identify the cause and add a targeted regression. A recurrence is promotion-blocking under D33. |
| BUG-02 | Historical investigation | The historical PyQt5 OLE hang has no settled relationship to the startup stall. | Establish a shared cause or a separate version/profile-specific disposition; retain the original hang evidence. |

### Public API coverage

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| API-05 | Partial inventory | Public methods, properties, operators, aliases, exports, event routes and value-dependent dispatch are not exhaustively reconciled. Discovery catalogs are not reviewed compatibility contracts. | Map a selected public route and representative values to implementation, documented differences and installed evidence; continue the method inventory without treating discovery counts as coverage. |
| API-06 | Evidence and claim coverage | The admitted 128 bindings and eight profiles cover selected workflows. Additional API values, examples, mutation/failure/recovery modes and profiles need their own claims. | Bind each new promised subset to exact source, wheel, dependency/driver profile, expected result and negative/recovery cases. Reuse justified unchanged evidence before rerunning tests. |

**API-06-READBACK-GEOMETRY — source fixed; Windows/WSL candidate installs verified:**
Negative origins, nonpositive extents and native-int conversion overflow now
fail before consuming queued work. [925 source proof](../compat/api-acceptance/readback-native-int-range-source-v1.json)
retains the overflow reproductions and 57 related CPU passes; [930 review](../compat/api-acceptance/readback-native-int-range-source-review-v1.json)
accepts the exact source at frozen commit `613cacf…`. [Windows933](../compat/api-acceptance/readback-candidate-windows-v1.json)
and [WSL935](../compat/api-acceptance/readback-candidate-wsl-v1.json) install exact
new wheels `9919a280…`/`e600b29e…` and each pass all 56 state/query/readback cases,
including 19 readback/recovery controls. Both have zero source overlays, 537
members verified before/after, ten zero shutdown gauges and cleaned scratch.
Earlier921–930 packets keep their original source/overlay/review scope. Remaining:
independent artifact/profile admission, exact qualification metadata/final CI,
protected integration and verified delivery. Published4f/dfe wheels are unchanged;
this finite source/installed fix does not close broad API-06 or LIF-05.
2026-11-15: [Windows944](../compat/api-acceptance/readback-windows-strict-v1.json)
passes the Windows strict runtime-observer cohort joined to `942` (16 joins / 48
gates, 537 members, zero overrides/gauges; scratch cleaned, no admission),
while pre-registration `preflight` for `readback-wsl-strict-945` (`512 MiB`
peak) refused with exit 2 (`Expected peak would cross minimum disk reserve at C:\`;
`D:/vispy-vulkan-managed/build/runs/readback-wsl-strict-945-capacity-refusal/verification.json`)
because external workstation activity reduced `C:\` below the `10 GiB` reserve.
Subsequently (`legacy-project-cleanup-945`: `8cc281b5…` / `5d9b772d…` / `f9de0fc3…`,
9,655 files / 7.9153 GiB physical / 7.94 GiB `C:\` reclaimed, 4,984 empty dirs,
0 overlaps), [WSL945](../compat/api-acceptance/readback-wsl-strict-v1.json) (`29bce237…`,
`PASS_READBACK_WSL_STRICT_MATCHED_COHORT_AND_JOINED_943_ACCEPTANCE`) passed on exact
Linux wheel `e600b29e…` (`_dawn` `fcf0c5a8…`) and source `613cacfb…` (16 joins / 48
strict raw gates across `tk-state-resource-failures` and `tk-capture-formats` on
`replay-0`, 0 overrides/gauges, joined without rerunning pytest to `943` `324e2f41…`;
scratch cleaned, `151` retained inputs verified, `T\build\work == ['p']`, WSL
`build/work == []`; no row/artifact/strict-selection admission claimed).

### Shaders raster state textures and lines

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| SHD-01 | Partial functionality and evidence | Beyond direct explicit one-dimensional sampler selection: multidimensional indexing, implicit derivatives/uniformity, more helper/preprocessor forms, multilevel mip chains and filtering/LOD combinations. | Choose supported forms and sampler families; check index/value/binding limits, rebinding and recovery with analytic output oracles. Keep unsupported forms explicit. |
| SHD-02 | Partial functionality and evidence | Array storage/interface classes, shape/type combinations, indexing, partial updates, reflection and shader-cache identity beyond the finite numeric uniform-array subset. | Specify one extension, verify packing/reflection/cache identity and meaningful rendered mutation/recovery on the selected artifact. |
| SHD-03 | Partial functionality and evidence | Additional attribute formats/constants, locations, strides, offsets, shapes/divisors, instancing and mutation/input-limit combinations. Selected matrix/array cases already exist. | Select uncovered layout/value combinations; prove packing and independent rendered geometry, boundary diagnostics and same-canvas recovery. |
| SHD-04 | Compatibility boundary | General geometry-dependent consumers need a supported compute/instanced expansion path or an application rewrite; existing generated geometry is a finite subset. | Document the chosen replacement and prove topology, interpolation, clipping, depth, mutation and loss/recovery for that consumer. |
| SHD-05 | Compatibility boundary | Broader generated-line external-storage, builtin, image/atomic/barrier and early/late-depth semantics remain restricted. Existing refusal/recovery tests do not implement those semantics. | Either retain a clear supported boundary or implement one selected form with ordering/side-effect and recovery evidence. |
| SHD-06 | Driver portability and evidence | The selected patched Mesa 9c5 profile is qualified. Broader Mesa/system-driver portability is open; the earlier Mesa 25.2.8 four-sample failure retains its original wheel scope. | For a new driver claim, reproduce the specific sample/clipping case on the exact current wheel, then fix or document the driver boundary and qualify that driver cell. |
| STA-01 | Partial state coverage | Dither, disabled multisampling, fractional polygon offset, mixed constant blending and stencil combinations remain incompletely reconciled. Reversed-depth subsets already have evidence. | Specify supported state/value combinations and prove actual pixels/depth/stencil, queued mutations, refusals and restoration on the chosen profile. |
| TEX-01 | Partial sampling coverage | Uint/Sint, unfilterable float, comparison sampling, half precision and NaN behavior across additional texture/layout combinations. | Select formats/layouts and test meaningful sampling results, filtering restrictions and refusal/recovery rather than generalizing from ordinary float textures. |
| LIN-01 | Verification gap | Chunk boundaries, endpoint carry, topology, resource limits and retained ordering across broader line partitioning routes. | Use rendered cases spanning partition/resource boundaries and queued revisions, with independent continuity/order checks. |
| LIN-02 | Deferred feature | MSAA generated-line coverage is deferred; an unshipped partial patch is not production support. | Select this feature explicitly before implementation; define sample/geometry scope and independent coverage oracles, then verify the exact installed artifact. |

### Scientific visuals and scene behavior

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| SCI-01 | Partial rendered coverage | Indexed/instanced point source IDs, divisors, constants, layouts and ordered revisions beyond the finite tested combinations. | Bind selected uncovered combinations to independent rendered identity/position checks on the intended artifact/profile. |
| SCI-02 | Partial filter coverage | Additional mesh filters, composition order, detach/reattach and mutation interactions, including broader clipping/alpha/blending/MSAA combinations. | Enumerate a supported composition, verify meaningful queued before/change/restored output, and map it to the intended artifact/profile claim. |
| SCI-03 | Partial scene coverage | Additional 3D cameras/FOV, planes, depth/stencil and polygon-offset interactions. Fixed-pose and selected Turntable mutation evidence do not cover all cameras. | Select a camera/state interaction and use independent reference landmarks plus mutation/restoration and failure controls; identify metamorphic-only observations. |
| SCI-04 | Bounded workflow and measurement gap | Large-volume mode, scientific quality, memory/performance, platform and artifact claims are not a complete cross-product. | Choose a bounded workload/mode, define a meaningful quality oracle and measured limits, and qualify only the exact promised environment. |
| SCI-05 | Conditional evidence reconciliation | The seven-row fixture disposition audit is complete. Changed U05/E03/E04/Q11-Q13/H03 claims still need exact current applicability; whole-host/scientific support does not follow from a headless pass. | Reopen only the row affected by a new route, artifact, host version or product claim; preserve earlier epochs and avoid repeating the completed blanket reconciliation. |
| SCI-06 | Compatibility boundary and evidence | Additional public stencil formats/types/crops/MSAA combinations remain outside finite wrapper proofs. Unsupported raw reads retain their deliberate refusal boundary. | Select a public wrapper form and prove its values, mutation and refusal/recovery on the exact artifact; keep original stock failures historical. |

**SCI-02-CLIP-ALPHA-BLEND — named subcase:** earlier three-case packets remain
historical. The maintained clipping/blending test is present in the current
merged qualification tree and the maintained Windows/WSL regression packets
([Windows](../compat/api-acceptance/orphan-current-windows-v1.json),
[WSL](../compat/api-acceptance/orphan-current-wsl-v1.json)). Its remaining work is
any broader composition or explicit scientific claim/profile mapping under
SCI-02/API-06. It is not a missing implementation or an unmerged test anymore.

### Lifecycle capture and input

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| LIF-01 | Broader fault coverage | Actual surface acquisition/loss and physical-memory accounting remain distinct from proved injected submission/query/upload failures and logical retirement gauges. | Select a real fault/accounting claim, reproduce it with a matching control and verify recovery; do not substitute injected faults or logical zero gauges for physical behavior. |
| LIF-02 | Native window qualification | Native-WSI reparenting, WinIdChange, embedded-parent destruction, surface ownership and shared-resource lifetime breadth beyond finite layout/readback observations. | Exercise the selected native window ownership transition on an exact installed profile, including parent destruction, continued rendering and teardown. |
| LIF-03 | Broader window-state coverage | Zero-size/minimized no-submit/restoration coverage beyond the existing finite cases, especially additional native surfaces and resource combinations. | Select the uncovered state transition and prove submission behavior, resource preservation, exact restoration and cleanup on its claimed artifact. |
| LIF-04 | Broader loss and embedding coverage | Actual surface/device loss and embedded-parent/multicanvas recovery breadth. Selected pending-close, peer isolation and orphan retirement paths are fixed. | Reproduce the specific backend/ownership loss path and verify peer survival, recovery and retirement without broadening injected-loss evidence. |
| LIF-05 | Partial capture coverage | Mixed-sample edges and additional depth/stencil formats, output types and resolve/feature combinations beyond finite color/default capture cases. | Define sample/format/crop semantics, independently verify preserved color and captured values, and test mutation/refusal/restoration. |
| LIF-06 | Partial input coverage | Physical HID, touch/stylus/gestures, additional layouts/timers/coordinates and binding-specific details beyond selected toolkit-generated keyboard/mouse/wheel/focus routes. | Select an actual input route/binding and verify recipient, payload, handled state, rendering and recovery. Keep generated-event and physical-input claims separate. |
| LIF-07 | Partial Tk coverage | Tk camera, DPI, embedding and physical-input breadth beyond admitted raster/manual-pump and finite generated-input behavior. | Choose one additional Tk contract and qualify its exact artifact/Tk version; keep raster and native presentation claims separate. |
| LIF-07-NATIVE-ADMISSION | Native presentation qualification | Opt-in native Tk source/earlier installed observations exist; native presentation still needs its own current artifact, WSI driver, independent scope review and strict profile admission. | Select the native profile and driver, verify the finite presentation/lifecycle controls on exact wheel bytes, then review/admit without changing raster qualification. |
| LIF-08 | Deferred hardware behavior | Cross-monitor moves and fractional DPI remain outside the selected release scope. | Select real monitor/DPI configurations and verify coordinate/size changes, rendering, input and lifecycle before promising support. |

### Application integrations

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| HOST-03 | Optional artifact qualification | Optional strict napari, Glue and napari-threedee profiles retain older artifact identities. Stock-host hot-swap and patched strict-host acceptance are different claims. | Choose the host/version and acceptance mode, then bind or renew the exact current wheel workflow; do not transfer old host admission automatically. |
| HOST-04 | Unadmitted application | DIVE has unresolved supported binding/API and upstream-baseline questions. PySide2 is excluded. | Resolve the binding and baseline, then prove an actual rendered application workflow and teardown on a supported configuration. |
| HOST-05 | Rendered workflow gap | Visbrain and other application imports/source inventories do not establish working rendered workflows. | Select representative application interactions and verify output, mutation and shutdown with the intended versions/artifact. |
| HOST-06 | Conditional host evidence reconciliation | Glue historical volume-mutation and newer workflow evidence must retain their separate versions/scopes. Corrected upstream reference admission does not qualify the current fork artifact. | For a current Glue claim, reconcile the relevant upstream result and execute or justify reuse of the exact candidate host workflow. |

### Platforms drivers and release packaging

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| PLAT-02 | Packaging and qualification | Current published wheels are CPython 3.12 x86_64. Source/CPU CI for other Python versions is not current release-wheel qualification. | If selected, produce matching wheels and verify installation, ABI, graphics/lifecycle and required gates for each added ABI. |
| PLAT-03 | Unqualified hardware | Native Linux physical GPUs are unqualified; WSL software Vulkan covers a different environment. | Select available physical hardware and complete installed rendering/lifecycle/driver-profile checks before making this claim. |
| PLAT-04 | Experimental graphics platform | Both Metal architectures have build/CPU evidence. Real macOS Metal graphics, interaction and shutdown qualification are missing. | Use a physical Mac for the selected graphics/lifecycle profile; retain experimental status until that evidence exists. |
| PLAT-05 | Unsupported platform | Native Wayland is unsupported; the qualified Linux windowing scope is X11/xcb. | Select a native Wayland implementation and profile, then verify presentation/input/ownership/loss behavior; do not count XWayland as native Wayland. |
| PLAT-06 | Outside release qualification | Windows/Linux ARM release configurations, free-threaded Python and ABI3 are outside the current release claim. Metal arm64 build/CPU evidence is narrower. | Select the architecture/runtime/ABI independently and verify its artifacts, native lifetime/threading and graphics profile. |
| PLAT-08 | Additional hardware qualification | Additional Vulkan vendors, GPU models and driver versions need their own cells beyond the admitted Windows and pinned WSL software environments. | Select a device/driver cell and run the relevant installed rendering, recovery and lifecycle cases before broadening the hardware claim. |

**PLAT-01 / PLAT-03 / PLAT-08 — Wave 4 Linux physical NVIDIA GPU `installed-functional` update (2026-11-15):** [plat03-08-linux-nvidia-colab](../compat/api-acceptance/plat03-08-linux-nvidia-colab-v1.json) (`b8a5bd8e…`, runs `998` `1bbfe275…`, `999` `c6aec5e3…`, `1000` `747a7b0c…`, hygiene `1001` `7a26baec…`) establishes `installed-functional` evidence on exact Linux wheel `e600b29e…` across two physical Linux NVIDIA discrete GPU cells (`Tesla T4` Turing `117/117` core + `31/31` mandatory GUI, and `NVIDIA L4` Ada Lovelace `136/136` core+GUI; plus separate `11/11` `installed-experimental` `W3-1` native Tk X11 WSI probe on `T4` with `default_presentation: "raster"` and `native_admitted_mandatory_matrix: false`) under `Linux x86_64 glibc 2.39` (`kernel 6.6.159+`, `Ubuntu 24.04.4 LTS` observed via `/etc/os-release` in `998`) / `NVIDIA 580.82.07` / Vulkan `1.4.312` / `Xvfb :99`. Both `PLAT-03` and `PLAT-08` remain open because non-NVIDIA Linux GPUs (AMD RADV, Intel ANV) and Mesa NVK (`non_nvidia_linux_gpus_claimed: false`), physical Xorg monitor scanout vs `Xvfb` (`physical_display_scanout_claimed: false`), physical HID/multi-monitor (`physical_hid_claimed: false`, `physical_multimonitor_claimed: false`), native Wayland (`PLAT-05`; `wayland_claimed: false`), and strict release/scoped admission (`scoped_admitted: false`, `artifact_admitted: false`) remain open.

### Optional performance tooling and historical evidence

| ID | Type | Remaining gap | Completion condition |
| --- | --- | --- | --- |
| PERF-02 | Optional optimization | Additional imported-block conversions/copies, such as RGB to RGBA, are not covered by the direct-upload optimization. | Measure a selected conversion workload, implement only justified changes and prove correctness/ownership plus the measured benefit. |
| PERF-03 | Optional optimization | Batched draw routes still upload during the pass; streamed-buffer improvements do not establish batched-route performance. | Benchmark a selected batch workload, optimize that route and retain correctness/order/lifetime controls and bounded measurements. |
| PERF-04 | Conditional measurement gap | Cold-build/peak-memory claims need bounded measurements and reconciliation of historical review regressions; those records are not automatically current runtime defects. | Select a performance claim, use an explicit storage profile and collect reproducible cold-build/peak-memory evidence without reviving a universal parity target. |
| TOOL-02 | Optional tooling | Compiler-output caching is not selected as a completed optimization. | Choose a cache only if it preserves source/toolchain/configuration identities and the shared disk budget; measure its benefit and cleanup behavior. |
| TOOL-03 | Historical evidence gap | A historical compiler-cache cleanup receipt is missing. New cleanup receipts cannot prove that older event. | Audit retained original records and either reconstruct supported evidence or record the remaining unknown; do not repeat deletion or invent reclaimed-byte totals. |

### Crosscutting evidence and documentation work

- For broader claims, keep historical specialized sampler, uniform, attribute,
  event, scientific and lifecycle packets on their recorded source/wheel/profile.
  The selected release admission does not qualify every older test vector.
  Check causal input applicability and use reviewed unchanged-proof reuse before
  selecting a focused rerun. This work belongs to API-06 and the relevant parent.
- Keep the current patched Mesa profile separate from system-driver observations.
  The historical Mesa 25.2.8 failure is not a newly reproduced defect on `dfe1033f`.
- Source-only, source-overlay, installed-functional, admitted and publicly
  delivered evidence remain distinct. Preserve original failures and unknown
  exits; none becomes a pass merely because a successor check succeeds.
- Older paragraphs below are preserved progress history. Use this register and
  the latest completion checkpoint for current status, rather than treating an
  old pending sentence as a new release blocker.

### Completed items excluded from the backlog

The selected `LIF-06-PANZOOM-RETIREMENT`, `LIF-06-HOST-IMPORT-RETIREMENT` and
`LIF-06-QT-FOCUS` contracts are integrated/admitted/delivered. Their broader
lifecycle/input parents remain partial. Final promotion, all 23 required CI jobs,
protected PR84 integration, distinct publication, actual Windows/WSL installation,
AGPL/original BSD notices and owned delivery-scratch cleanup are complete.
Both Metal architectures have completed build/CPU checks; Metal graphics remains
PLAT-04. The seven-row SCI-05 classification audit is complete; only changed
claims reopen the relevant row. These completed tasks must not be duplicated.

### Accepted limits and selection rules

Full upstream API or exact OpenGL rasterizer parity and laboratory optical
input-to-visible/scanout equivalence are outside the agreed target. Performance
improvements over VisPy are acceptable. Missing Mac/physical-Linux/input/display
hardware does not create a procurement task. Physical and optional expansion
items remain unselected until the user chooses a concrete supported use case.

For selected work: identify a route/value/profile, establish existing evidence,
reproduce the exact gap, make the smallest justified change and verify that
claim. Reuse matching wheels/SDKs/locked dependencies; follow
[build hygiene](build-hygiene.md) for real experiments and update the affected
IDs in [the live coverage checklist](coverage-checklist.md). This documentation
change creates no scratch, build assets or new environment.

Detailed source records: [API](coverage-checklist.md#api-breadth-and-inventory-review),
[shader/rendering](coverage-checklist.md#shader-and-rendering-edge-coverage),
[scientific](coverage-checklist.md#scientific-workflow-reconciliation),
[lifecycle](coverage-checklist.md#resource-lifecycle-capture-and-input),
[hosts](coverage-checklist.md#host-integrations),
[platforms](coverage-checklist.md#platform-and-packaging-boundaries), and
[performance/tooling](coverage-checklist.md#performance-tooling-and-evidence-hygiene).

## Latest checkpoint — 2026-11-14

**Remaining-gap goal active; readback geometry source fix — 2026-11-14:**
[921 source evidence](../compat/api-acceptance/readback-geometry-source-v1.json)
adds API-06-READBACK-GEOMETRY under API-06/LIF-05. Six CPU controls reproduce
queued-command draining for explicit negative-origin/nonpositive-size reads
before the fix; valid-read ordering passes. Validation now rejects those inputs
before finish, preserving native RuntimeError diagnostics. All26query/readback
contracts and45related contracts (including those26) pass, actual exits/waits
retained. Six real native/rendered recovery cases are added but unexecuted.
Source hashes and903baseline/three-file patch retained; no scratch/native build/
environment/install. Published4f/dfe wheels remain unchanged; independent review,
matching installed validation and batch source/artifact renewal remain open.
The new goal targets the complete remaining register; broad parents stay open,
hardware limits remain explicit and historical startup campaigns are not repeated
without recurrence or new causal evidence.

**Comprehensive current gap register reconciled — 2026-11-14:**
The [current register](#comprehensive-current-gap-register)
consolidates44broader workstreams plus the SCI-02 clipping/blending subcase,
with gap type, exact remaining scope and completion evidence. It covers API,
shader/state/texture/line, scientific, lifecycle/input, host, platform, known
bug, optional performance/tooling and historical-evidence work. The selected
PanZoom/host-import retirement and Qt focus headings now reflect actual delivered
closure; their earlier paragraphs remain historical. Current source275888b5,
qualifier90348a8, merge76cc5e8c and Windows4f/Linuxdfe release scope are unchanged.
The patched Mesa9c5 profile and both Metal build/CPU jobs are complete at their
named scopes; wider drivers/Metal graphics remain open. No new implementation,
rendering, admission, native build, package install or cleanup was performed.

**Final selected-milestone audit passes — 2026-11-14:**
[920 requirement audit](../compat/api-acceptance/orphan-release-completion-audit-v1.json)
checks13explicit requirements against current source, unchanged validators,
exact CI/independent review/admission/restoration, protected source integration,
public assets/licensing, actual install workers and cleanup. All13pass; no
selected requirement remains. Both wheels match all510current shipped source
members and537package members; all323tools,488historical candidate JSONs and18
protected originals remain exact. Only permitted live-documentation checkpoints
differ from the852input source freeze. Actual source-only audit exits0/waits;
foreign HEAD/index unchanged and all owned scratch absent. Broader API/state/
scientific/lifecycle/hardware parents remain partial or deferred; fullinventory
false. This completes the agreed finite Windows/WSL milestone, with original
failures/unknown exits and Metal experimental scope preserved.

**Bounded Windows/WSL public release delivered — 2026-11-14:**
[Final delivery](../compat/api-acceptance/orphan-release-public-delivery-v1.json)
and its [public report](https://github.com/bipxx/vispy_vulkan/releases/download/v0.17.0-vulkan.2-orphan-retirement-90348a8/delivery.json)
verify distinct release445706472/tagv0.17.0-vulkan.2-orphan-retirement-90348a8,
source merge76cc5e8c/tree9ff4c6d5, qualifier90348a8/product275888b5. All23CI,
reviewed128selected bindings/eight profiles and protected integration pass.
Windows4f/native057d: actual public same-version replacement,537members/zero
overlays, exact64x64Vulkan clear and ten zero shutdown gauges. WSLdfe/nativefcf:
actual public replacement,537members/zerooverlays/locked dependencies and ABI
import, ten zero gauges. Three guest installer subprocesses exit0/waited; a
same-target follow-up worker AND launcher exit0/waited. Original919monitor
controller staysfailed/initial launcher exitunknown;917origin/918owner failures
and913admission precondition failure remain unchanged.920report-join key failure
is retained separately, corrected source-only report build exits0/waits. No GPU
claim is added by WSL delivery smoke.13public assets include exact AGPL/original
BSD/third-party notices; final report anonymously downloads byte-exact. All4old
releases/assets and source275reachable ref remain. Delivery scratch cleanup
removes81029222bytes across917–919; all owned targets absent, unownedp preserved.
FIX-04/06, selected API-06/LIF-06, PLAT-08 and TOOL-01/04 close at this finite
integrated/admitted/delivered scope. API-05, STA-01, SCI-02/03/05/06 and broader
LIF/platform parents remain partial. Fullinventory/parity false; Metal graphics,
physical Linux GPU/HID/display, native surface/reparenting and arbitrary format/
composition coverage remain explicit boundaries. No new SDK/native build/env.

**Windows public delivery passes; WSL owner refusal retained — 2026-11-14:**
[918 Windows subphase](../compat/api-acceptance/orphan-release-windows-public-channel-v1.json)
uses no-site startup/explicit existing locked dependencies: publicURL/hash force
reinstall replaces same-version9e4with4f,537members/zerooverlays/native057d match,
64x64Vulkan clear exact, ten shutdown gauges zero. Controller remainsfailed:
WSLguard retains a copied917owner ID and refuses before guest writes/installation.
Actual controller exit1/waited, logs/repro retained; cleanup removes17907561bytes/
569files and verifies44retained. No package/env/verifier changes. FIX-06/PLAT-04/08/
TOOL-04 are Windows-delivery complete only. New919will run only WSL with its
registered exactowner; preserve917/918failedcontrollers and reuse Windows proof.

**Distinct release published; delivery harness failure preserved — 2026-11-14:**
[917 partial publication](../compat/api-acceptance/orphan-release-publication-partial-v1.json)
creates distinct prereleasev0.17.0-vulkan.2-orphan-retirement-90348a8/id445706472,
actualtag76cc5e8c;12anonymous asset hashes/AGPL-originalBSD-notices pass, all4old
releases unchanged. ExactURL/hash forced Windows install replaces9e4same-version
seed with4f successfully. Smoke then exits1/waited at source-origin assertion:
existing scikit-build editable finder intercepts import before native/rendering.
Read-only diagnosis confirms sourcepackage/no nativeimport. Originalfailedrun,
commands/repro and12download results retained; cleanup removes35338947bytes/
579files and verifies65retained, scratch absent. No product/verifier/environment
mutation. FIX-06/PLAT-04/08/TOOL-04 remain delivery-pending: next use isolated
no-site startup plus explicit retained dependencies in a separate bounded run,
then actual Windows clear/WSL ABI and537member checks. No success relabeling.

**Protected PR84 integration verified — 2026-11-14:**
[916 actual integration](../compat/api-acceptance/orphan-release-protected-integration-v1.json)
normal protected auto-merge succeeds as76cc5e8c04c9747b3f0485c4ac2e6a4f56b7f0b6.
Actualmain equals this merge, and its fulltree9ff4c6d5equals qualification90348a8
exactly.11branch-required checks and all23release-policy jobs pass;128bindings/
eight rows are admitted under914/915. Foreign checkout HEAD/index unchanged;
no scratch, force, bypass, source/runtime change or branch deletion. FIX-04 and
TOOL-01 advance at integrated-source scope; FIX-06/PLAT-04/08/TOOL-04 still need
distinct actualasset publication, hash-specific installation and checked delivery.
Older assets and source275reachable reference must remain. No fullparity claim.

**Current128-binding and eight-row admission passes — 2026-11-14:**
[914 fresh correction review](../compat/api-acceptance/orphan-release-final-correction-review-v1.json)
approves exact915driverf8d96ea1/basise1fcc058; only ZIP basename lookup and
successor identities changed.467inputs, backup3933abc1, selectorb164e3fd and323
actual903Gittool blobs pass immediate checks. Review scratch cleaned102bytes/
485retained. [915 actual admission](../compat/api-acceptance/orphan-release-current-scoped-admission-v1.json)
exits0/waited via existing interpreter: unchanged strict validator admits128
selected bindings; separate independently reviewed sidecar admits eight exact
Windows4f/WSLdfe profiles. All11canonical files restore byte-exact; frozen matrix
unchanged. Four genericforeign refusals/eightUNVERIFIEDdiscovery/875limits remain;
manualforeignretention acceptance staysfalse. No scratch/environment/build.
Original913failedattempt and912approval remain immutable and are not reused;
915uses914approvalonly. FIX-04/06,API-06,finiteLIF-02/04/06,PLAT-04/08,TOOL-01/04
advance at scoped admission only. All23CI passes; protected integration and
distinct actualasset delivery remain open. Fullinventory/release/parity false.

**Final review approved; admission precondition failed unchanged — 2026-11-14:**
Fresh912review approves exacte1fcc058basis/128bindings/eight rows, with retained
unread/condition limits. All431inputs rehash and323committed tools modules match
903head byte-exact. Review scratch cleaned97bytes/451retained. The exact reviewed
913driver then exits1/waited before canonical writes: it used repository-relative
member names in898backup, which stores11basenames. [Original failure](../compat/api-acceptance/orphan-release-admission-precondition-failure-v1.json)
retains repro/log/process; all11canonical hashes and backup3933abc1 remain exact,
no scratch/environment/validator change. No admission is claimed. TOOL-01/04,
FIX-04/06,API-06 and finiteLIF-06 require a narrow successor-driver review before
another admission attempt; all23CI remains valid, integration/delivery open.

**All23CI and exact detached promotion basis pass — 2026-11-14:**
[908 completed CI](../compat/api-acceptance/orphan-release-complete-required-ci-v1.json)
validates all23original same-head90348a8 jobs, complete run/job/history exports,
20CPU plus3native checkout identities with unchanged policy.20CPU transports
use4050273bytes; managed cleanup removes4050356bytes/21files and verifies119
retained inputs, scratch absent. [911 basis](../compat/api-acceptance/orphan-release-final-promotion-basis-v1.json)
now binds exact905subject334e726d,907impact and complete908CI. Actual children
exit0/waited; no native wheel, SDK or environment rebuilt. TOOL-01/PLAT-04/08
advance at completeCI/basis scope; API-06/FIX-04/06/LIF-06 still require fresh
final912review, guarded128-binding/eight-row admission, protected integration
and distinct verified delivery. No final approval, admission or publication yet.

**Required CI advances to22/23 — 2026-11-14:**
Original CPU run43648741602/head90348a8 poll31 records CPython3.10.19 job
132612247914 completing successfully:19/20CPU plus3native required checks pass,
0failures. Only132612248003(CP3.13.8) remains running. Original exports and
actual child exits/waits stay in managed run904. TOOL-01/PLAT-04/08 advance at
observed CI scope only. Collector908 awaits the completed full run; no redispatch,
admission, build, scratch or publication.

**Required CI advances to21/23 — 2026-11-14:**
Original CPU run43648741602/head90348a8 poll17 records CPython3.12.8 job
132612247880 completing successfully. Poll18 confirms18/20CPU successes plus
three previously verified native jobs:21/23required checks pass,0failures;
132612247914(CP3.10.19) and132612248003(CP3.13.8) remain running. Original raw
job exports/actual exits/waits are retained in managed run904. TOOL-01/PLAT-04/08
advance at observed CI scope only. Collector908 remains unexecuted until the
full run succeeds; no redispatch, admission, scratch, build or publication.

**Final gate drivers prepared — 2026-11-14:**
[911/913 preparation](../compat/api-acceptance/orphan-release-prepared-gate-drivers-v1.json)
provides syntax-checked scripts for the exact905subject/907impact/908CI detached
basis and guarded128-binding/eight-row admission. Neither script executed.
913requires a fresh912independent final review of its exact bytes, final basis
and actual909raw joins; it rehashes original observations/foreign protections,
checks all11frozen canonical files and restores them after strict validation.
No old538approval is reused. TOOL-01/04,FIX-04/06,API-06 and finiteLIF-06 advance
at preparation scope only; no admission/merge/delivery. Actual904poll11 confirms
17CPU+3native successes and the same3CPUjobs still compiling on90348a8, no
failures or redispatch. No scratch, environment or native build was created.

**Local delivery packet prepared — 2026-11-14:**
[910 draft preparation](../compat/api-acceptance/orphan-release-local-delivery-preparation-v1.json)
rehashes exact Windows4f537748/Linuxdfe1033f wheels and checks all four original
license/notice sources in both runtime and dist-info locations (eight joins per
wheel;537runtime/562total members). Draft release notes and hash-pinned platform
requirements use a proposed distinct tag; no tag/release/install exists yet.
The first draft auditor failed by conflating runtime and total member counts;
original exit1/reproducer stays retained, corrected source-only child exits0/waits.
No product or qualification validator changed. TOOL-04/PLAT-04/08 advance at
local preparation scope only; admission/merge/published hashes/install smoke
remain open. No scratch or disposable assets created; cleanup not required.

**Remaining-gap investigation plan refreshed — 2026-11-14 (planning only):**
The [ordered investigation queue](superpowers/plans/2026-11-14-gap-investigation-next.md#planning-refresh-investigate-and-close-the-remaining-gaps--2026-11-14)
now separates six delivery gates from concrete behavior investigations: existing
exact-head CI, complete CI collection, final promotion review, guarded scoped
admission/restoration, protected integration and distinct verified delivery.
API-05/06, STA-01, SCI-02/03/05/06, LIF-01–06, FIX-04/06, PLAT-04/08 and
TOOL-01/04 retain their existing partial/source/installed/historical scopes.
Baseline: qualification head90348a8/product275888b5; 905 proves128bindings,
907 approves finite impact reuse, 909 joins eight observations/admitted_rows=0.
Last retained904poll8 is20/23successful with3unfinished CPU jobs; no fresh live
status is claimed. No tests, scratch, build, CI dispatch, admission, merge or
publication occurred in this planning change. Full parity remains outside scope.

**CI readiness checkpoint — 2026-11-14:** 904poll7 verifies17CPU+3native
successes (20of23),0failures,3live Mac Intel CPU jobs132612247880(CP3.12.8),
132612247914(CP3.10.19),132612248003(CP3.13.8). Their original run remains
43648741602/head90348a8; no restart/redispatch. The908collector is prepared to
retain the20original CPU checkout identities and complete original same-head
history/jobs, reuse906's3native identities, then call the unchanged23-job CI
validator. It has not executed or allocated scratch while CI is incomplete.
Next fullCIjoin, detached promotion basis/final independent review of909's eight
rows, guarded strict/matrix admission, protected integration and distinct delivery.
TOOL-01/PLAT-04/08 advance at observed CI scope only; no admission or full-API/
Metalgraphics claim. All owned906/907scratch stays absent; no new local build.


**Exact-head subject/impact and matrix review inputs ready — 2026-11-14:**
[905](../compat/api-acceptance/orphan-release-corrected-head-installed-subject-v1.json)
binds head90348a8/subject334e726d:128proved/0missing/blocked,1324retained inputs,
all11canonical files restored. Existing898backup reused, no duplicate archive.
[906](../compat/api-acceptance/orphan-release-corrected-native-ci-identities-v1.json)
retains3original native-job checkout identities for903;177423373transport bytes
plus104marker bytes cleaned (177423477total),29retained verified;no native
payload extraction. [907](../compat/api-acceptance/orphan-release-corrected-impact-review-v1.json)
freshly approves exact-head/subject impact and finite880basis reuse,with original
limits/refusals;18foreign origins rehashed/protected,15used,none relocated.
Bare7fieldapproval created; review scratch cleaned98bytes/236retained verified.
Reviewer read/unread/hash reliance retained; F6byte wording clarified from actual
snapshot, no old record changed. [909](../compat/api-acceptance/orphan-release-mandatory-prepromotion-join-v1.json)
checks8raw worker/report/receipt/wheel/environment/feature joins,537members/no
source overrides/nine worker+ten APIzero gauges;admitted_rows=0. CI904poll5has
14CPU+3native successes (17of23),5running/1queued,no failures. Follow same3runs.
FIX-04/06,API-06,LIF-02/04/06,PLAT-04/08,TOOL-01/04advance only at finite reviewed
proof/source/CI-input scope. Next complete23-job join,detached promotion basis/
independent final eight-row review,strict/matrix admission,protected integration
and distinct delivery. Full inventory/parity/physicalGPU/HID/Metalgraphics remain
outside these claims. No renderer or SDK rebuild, no writable scratch remains.


**Reviewed CPU curation fix pushed; corrected-head CI active — 2026-11-14:**
[903/904](../compat/api-acceptance/orphan-release-corrected-qualification-source-freeze-v1.json)
creates normal child90348a8064b1091eb989bb8d0fbf787b6afc4f43/tree9ff4c6d5on
PR84after902review.9changed paths give159combined owned paths:2test-only curation
edits,4raw-byte-verified insert-only dated docs,3own evidence records. Every other
899blob and all11current15declarations stay unchanged. Actual852source joins
include133native/628Metalinputs and both537member release wheels/notices; no
runtime/workflow/pin/scope/validator change or SDK/wheel rebuild. Source-index
scratch cleaned15157347bytes/68retained verified;901fixture+managed cleanup is
separately verified and902had no new scratch. Preparation observer UTF8/newline
mistakes are retained; only own doc insertion corrected to preserve old endings.
Normal push and REST PR84verify90348a8; immediate stale GraphQL observation is
preserved, with no repeat push. Original646head finishes20CPUfail/3nativepass;
none are relabeled as corrected-head success. New original runs43648741602CPU,
43648741629Linux,43648741524Metal have23jobs (initial16running/7queued/no failures).
Follow these handles without redispatch. Local12new cases+registration pass,
full local435pass/1CMake-profile failure staysfailed. TOOL-01/04,FIX-04/06,API-06
advance at reviewed test integration/frozen-source scope only. Current-head CI,
impact/promotion, protected merge, matrix/strict admission and distinct delivery
remain open. This detached checkpoint does not mutate frozen head90348a8.


**CPU curation gap reproduced and fix reviewed — 2026-11-14:**
Original PR84/head646c986d Linux and both Metal jobs pass; CPU jobs fail at the
curated scientific-contract step. The retained Linux CP310log identifies missing
registration of test_dawn_orphan_retirement_contract. [901](../compat/api-acceptance/orphan-release-curated-ci-fix-v1.json)
reproduces it before the fix. Two test-only edits add that module to MODULES and
export its8functions/12parametrized cases through __all__; no exemption or
assertion change. All12new cases and registration pass locally; full curated
run remains435pass/1failure because this shell lacks the existing CMake profile.
[902](../compat/api-acceptance/orphan-release-curated-ci-review-v1.json) freshly
approves exact source diff66e3ffc7 plus audited fixture cleanup, with reviewer
limits explicit. All11preparation15JSONs and runtime/native/workflow/pin/validator
inputs remain unchanged, so no successor preparation or renderer rebuild.
The broad local run created2one-commit/no-remote publication test clones, which
correctly blocked managed cleanup. Original refusal and902structural preflight
refusal remain; read-only recovery review used the existing901lease. Verified
bundles/exact approved whole-clone retirement remove58860bytes; successor ordinary
managed cleanup removes1106368bytes/617files and verifies72retained inputs.
A post-cleanup wrapper print fails separately; actual cleanup child exits0/waits
and scratch is absent, with no cleanup rerun. See the dated hygiene note before
any future full local curated run. TOOL-01/04,FIX-04/06 and API-06 advance at
reviewed test-integration scope only. Next causal corrected PR84head freeze and
all23required hosted checks, then impact/promotion/protected integration/admission/
delivery. Original CPU failure and local full-suite failure are not relabeled.


**Qualification source frozen and PR84 CI started — 2026-11-14:**
[899/900](../compat/api-acceptance/orphan-release-qualification-source-freeze-v1.json)
freezes reviewed145paths plus9permitted own review/evidence additions as154files,
qualification head646c986dc67289beaeae46bd4d8af3e114d316f3/tree75193706,
baseactualmain7209f119. Only approved4metadata changes/3insert-only dated docs
changed after892review;488historical candidates unchanged. Actual Git blobs join
847source files,133native/628Metalinputs and both exact537member Windows4f/
Linuxdfe release wheels, including510pure members and original notices. No tests,
renderer, SDK or wheel rebuilt. Foreign HEAD/index unchanged. Private-index
scratch cleaned15156947bytes/357retained verified. [PR84](https://github.com/bipxx/vispy_vulkan/pull/84)
opens after verified normal push; connector403integration refusal is retained,
existing authorized CLI fallback succeeds. Original required runs43646024484CPU,
43646024476Linux and43646024486Metal contain23jobs: initial snapshot16running/
7queued, none complete. Observe these same handles; do not redispatch on delay.
TOOL-01/04,FIX-04/06,API-06,PLAT-04/08 advance at exact-source/content-join scope;
CI/impact/promotion/protected integration/matrix/strict admission/delivery remain
open. No release/Metalgraphics/full-parity admission. This dated checkpoint is
detached progress evidence; frozen qualification commit remains646c986d.


**Reviewed15 current retention and exact subject pass — 2026-11-14:**
[895 failure](../compat/api-acceptance/orphan-release-preparation15-retention-failure-v1.json)
remains failed: an untyped collector treated an upstream-manifest member path as
a repository path. Actual exit1/waited, original reproducer retained, scratch
cleaned102bytes/29inputs. [897 review](../compat/api-acceptance/orphan-release-retention-namespace-review-v1.json)
approves exact896collector c42ca506: upstream pins stay manifest keys, native/
archive inputs use existing typed namespaces and review paths stay exact. No
verifier/product/test/CI/scope change; reviewer limitations retained. Review
scratch cleaned101bytes/45inputs. [896 retention](../compat/api-acceptance/orphan-release-preparation15-proof-retention-v1.json)
passes unchanged validator for1324current contributing inputs after both native/
archive validators; scratch cleaned102bytes/1324verified, no payload copies.
Five original strict attempts are separately counted4passes/1nonpass; collector
895is a distinct preserved failure. Historical892/893/895cleanup records are not
promoted to current transitive rehashes; reviewed documentation originals remain
hash-retained. [898 subject](../compat/api-acceptance/orphan-release-preparation15-installed-subject-v1.json)
then proves128selected bindings with0missing/blocked using original32receipts and
Windows4f537748/Linuxdfe1033f, fresh15reviews and new retention. All11canonical
JSONs restore exactly; actual exit0/waited, no scratch/environment/rendering run.
FIX-04/06, API-06, LIF-06 and TOOL-01/04 advance only at current reviewed-subject
scope. admitted=false/release_complete=false. Next final owned-source freeze/
23-job qualification-head CI, independent impact/promotion, protected integration,
matrix/strict admission and distinct delivery. No full-parity or parent closure.


**Combined review and reviewed15 reuse bindings pass — 2026-11-14:**
[892](../compat/api-acceptance/orphan-release-combined-review-v1.json) freshly
approves exact145owned-source delta3e9a3fef/preparation15scopee6acf758/both native
reuse digests, with no blocking changes. Raw read/unread and coordinator-hash/test
reliance limits remain explicit; no release approval. Review scratch cleaned
90bytes/210retained verified. [893](../compat/api-acceptance/orphan-release-preparation15-reviewed-bindings-v1.json)
applies only two reviews, candidate reseal/provenance pointers and32review flags.
Both full native/archive records and actual Linux/two-architecture Metal reuse
paths pass unchanged; scope/maps/reuse blocks and488historical candidate files
stay fixed. Scratch cleaned92bytes/175retained verified. [894](../compat/api-acceptance/orphan-release-preparation15-installed-bindings-v1.json)
derives reviewed15overlay from all32original receipts,128bindings/96gates checked
again; zero new receipts or graphics runs, all11canonical files unchanged.
Reviewed documentation versions are retained by hash before this checkpoint.
TOOL-01/04, FIX-04/06, API-06, PLAT-04/08 and finite LIF-06 work advance at
review/metadata-proof scope only. Clarification F1: empty host-import cleanup is
an event-boundary action whenever no Ticket is outstanding; it can also occur
with open canvases. It does not depend on global shutdown. F5 exception-cause
diagnostics remain a nonblocking advisory; no product/test change was made.
Next new contributing retention/current guarded subject, then final-source freeze/
23-job CI/impact/promotion/protected integration/matrix and strict admission/
distinct delivery. Broad parent coverage and Metal graphics stay unqualified.


**Owned-source and claim triage recorded — 2026-11-14:**
[891](../compat/api-acceptance/orphan-release-final-source-inventory-v1.json)
rechecks actual remote main7209f119 and inventories144proposed owned files,
110generated/unrelated differences preserved outside, no missing baseline paths,
foreign HEAD/index unchanged. Its six claim groups distinguish API-05/06 current
binding work, STA-01/SCI-02/03/06 finite/historical boundaries, SCI-05 stale-claim
risk, LIF-06 retirement/focus integration, broader LIF-01–06 boundaries and
PLAT-04/08/TOOL-01/04 final qualification. This is proposed triage, not an
exhaustive API audit or independent approval; no parent checkbox is closed.
No scratch, build, tests, staging or CI dispatch. Inventory precedes its own
acceptance wrapper/this dated checkpoint; include those mechanical additions
when freezing the combined review packet. Next fresh preparation15 source/scope/
native-reuse review, then guarded current subject and final-head release gates.


**Investigation plan refreshed — 2026-11-14 (planning only):**
The [current closure queue](superpowers/plans/2026-11-14-gap-investigation-next.md#current-investigation-queue--2026-11-14)
replaces stale pending/running steps with six bounded packets: owned-path/claim
triage, fresh preparation-15 combined review, current subject/retention bindings,
exact-head required CI, promotion/protected integration/admission, and distinct
delivery. API-05/06, STA-01, SCI-02/03/05/06, LIF-01–06, PLAT-04/08 and TOOL-01/04
remain bounded by their existing evidence; no parent completion or new proof is
claimed. Baseline remains889's850source passes,878/880's eight observed/reviewed
profile results and890's32receipt/128binding/96gate equality preflight. Both Metal
jobs are complete at build/CPU scope. No new tests, scratch, build or CI dispatch.


**Metal producer complete; preparation15 source checks pass — 2026-11-14:**
[886](../compat/api-acceptance/orphan-release-metal-reuse-pin-v1.json) renews
both validated build/CPU originals.887's seven stale14guard failures are retained;
[888](../compat/api-acceptance/orphan-release-preparation15-v1.json) creates an
additive metadata successor without changing runtime/profiles/obligations/tests.
[889](../compat/api-acceptance/orphan-release-preparation15-contracts-v1.json)
passes850cases; [890](../compat/api-acceptance/orphan-release-preparation15-proof-reuse-v1.json)
proves original32receipts/96gates equal under15, with no duplicate receipts or
graphics reruns. All884/885/887/888/889scratch cleaned; original failures retained.
Next fresh exact source/scope/native-reuse review, current guarded subject/
retention bindings, final-source freeze/23-job CI/impact/promotion/protected
integration/admission and distinct delivery. Metal graphics stays experimental.

**One current Metal architecture validated; second still running — 2026-11-14:**
[884](../compat/api-acceptance/orphan-release-metal-arm64-original-v1.json)
validates arm64 fresh source275888b5/wheel8f6f4f8f build/installed-CPU,628source
joins/eight awaited commands/original cleanup. Local scratch cleaned23646911bytes,
116retained verified. x86_64 remains in the original43634581736 build step;
production reuse pin unchanged. Observe it, validate originals, then renew only
the exact combined pin. Final source review/23-job CI/impact/promotion/protected
integration/admission/distinct delivery remain open; Metal graphics experimental.

**Eight-row evidence basis reviewed; final CI inputs next — 2026-11-14:**
[879/880](../compat/api-acceptance/orphan-release-mandatory-review-v1.json)
approves current observation/attempt/retention basis after949file audit. Four
Windows generic refusals stay refused; only15exact protected foreign inputs have
fresh manual approval. Review limitations retained; scratch cleaned91bytes/
1026retained verified. Actual matrix/release admission remains pending final-head
review/CI/impact/promotion/protected integration and distinct delivery.
881confirms3native Metal inputs invalidate reuse; a single fresh build/CPU-smoke
run[43634581736](https://github.com/bipxx/vispy_vulkan/actions/runs/43634581736)
is active on275888b5. Observe that same run, validate original outputs and renew
its reuse pin before final23-job CI. Metal graphics remains experimental.

**All eight mandatory observations complete — 2026-11-14:**
[878](../compat/api-acceptance/orphan-release-mandatory-observations-v1.json)
binds Windows4f537748/WSLdfe1033f headless and three Qt bindings, eight strict
passes/eight separately retained discovery UNVERIFIED reports.537members/no
overrides/ten zero gauges per profile; headless95GPU/36science/4096markers.
All scratch cleaned818088505bytes;14canonical files unchanged.875transient
cleanup refusal remains retained. Next exact eight-row contributing retention/
independent review/matrix admission, then final-source review/freeze/23-job CI,
impact/promotion/protected integration/strict admission and distinct delivery.
Observations and selected128-binding subject proof remain separate from admission.

**Seven of eight current mandatory observations complete — 2026-11-14:**
WSL[PyQt6](../compat/api-acceptance/orphan-release-wsl-pyqt6-v1.json)/[PyQt5](../compat/api-acceptance/orphan-release-wsl-pyqt5-v1.json)/[PySide6](../compat/api-acceptance/orphan-release-wsl-pyside6-v1.json)
pass exactdfe1033f seven-stage strict observations,537members/ten zero gauges.
277768274bytes scratch cleaned, borrowed origins unchanged;875PID-reuse refusal
preserved and original guard subsequently passes.877WSL headless is running.
Then exact eight-row history/retention review/admission, final combined-source
review/freeze/23-job CI/protected integration/promotion and distinct delivery.
No profile/matrix/release admission is implied by these observations.

**Windows half of current mandatory observations complete — 2026-11-14:**
[870–873](../compat/api-acceptance/orphan-release-windows-mandatory-v1.json)
passes headless/PyQt6/PyQt5/PySide6 on4f537748, each with strict replay,
537members/no overlays/ten zero gauges.447730804bytes scratch cleaned; retained
inventories verified and14canonical files unchanged. Next four exactdfe1033f
WSL rows, then complete matrix attempt/retention review/admission, final combined
source review/freeze/23-job CI, protected integration/promotion and distinct
delivery. Four observations do not constitute eight-row or release admission.

**One of eight current mandatory observations complete — 2026-11-14:**
[870 Windows headless](../compat/api-acceptance/orphan-release-windows-headless-v1.json)
passes95GPU/36science/4096marker/rendering checks on exact4f537748, strict replay,
537members/no overlays/ten zero gauges. Scratch cleaned69199553bytes/212retained
verified. Next Windows PyQt6/PyQt5/PySide6, then four WSL profiles, exact matrix
review/admission and final-source23-job CI/protected integration/promotion/delivery.
This observation does not admit the whole matrix or broaden scientific parity.

**Selected subject gap closed; release gates remain — 2026-11-14:**
[869](../compat/api-acceptance/orphan-release-installed-subject-v1.json) proves
all128selected bindings with exact4f537748/dfe1033f artifacts, five attempts,
approved failure resolution and870-input retention. All14canonical files restore
exactly; actual exit0/waited, no scratch/env. No selected obligation missing or
blocked, but admitted=false. Next eight current-wheel mandatory observations
(headless/PyQt5/PyQt6/PySide6 on Windows and WSL), then final combined-source
review/freeze/23-job required CI, independent promotion, protected integration,
strict admission and distinct delivery. No new renderer build is indicated.

**Contributing retention complete — 2026-11-14:**
[868](../compat/api-acceptance/orphan-release-proof-retention-v1.json) passes
the unchanged validator for870existing proof/source/license inputs. Both full
native/archive validators pass; no payload copies. Scratch cleaned94bytes and
870retained verified. Guarded exact-subject validation869 is running. Remaining
release gates: eight current-wheel mandatory rows, final-source review/23-job
current-head CI/protected integration, independent promotion/admission and
distinct delivery. No release admission follows from retained evidence alone.

**History/resolution gap closed at review scope — 2026-11-14:**
[866](../compat/api-acceptance/orphan-release-attempt-history-v1.json) audits
five exact strict attempts/four separate discovery reports; [867](../compat/api-acceptance/orphan-release-attempt-review-v1.json)
independently justifies the one failed Windows replay without relabeling it.
Draft selection only; retention and subject admission remain pending. Original
collector exit2/scenario exit0 and all setup/ancestor scopes remain explicit.
Review scratch cleaned89bytes/69retained verified. Next contributing retention
and exact subject, then current-wheel eight mandatory rows, final-head release
CI/protected integration/admission and distinct delivery.

**Current investigation order — 2026-11-14:**
Follow the [refreshed queue](superpowers/plans/2026-11-14-gap-investigation-next.md#current-investigation-queue--2026-11-14):
finish866history audit, one independent attempt resolution, contributing
retention, guarded exact subject, actual mandatory-profile/promotion obligation
inventory, final combined review/current-head CI/protected integration, then
admission and distinct delivery. Selected release checks already pass32rows/
128bindings/96gates; remaining142original rows are not automatically142defects
or new milestone obligations. Broader API/scientific/lifecycle claims stay
partial or explicitly bounded. Planning only; no new execution or admission.

**32selected release-wheel rows pass — 2026-11-14:**
[863](../compat/api-acceptance/orphan-current-release-archives-v1.json) audits
and metadata-retags Linux to manylinux_2_39/dfe1033f; native/runtime/licenses
unchanged, both release archive prerequisites pass. [864](../compat/api-acceptance/orphan-release-wsl-strict-v1.json)
then passes both strict workflows/two acceptance nodes on that exact artifact,
16joins/48gates/537members/no overlays/ten zero final gauges. [865](../compat/api-acceptance/orphan-release-installed-row-bindings-v1.json)
combines it with Windows4f537748for32rows/128bindings/96gates, reusing all16Windows
proofs rather than duplicating them. Canonical14files and142original required
rows are preserved; no subject/profile/artifact admission yet. Failed860and
raw861/862remain historical. All860/861/863/864scratch cleaned302672441bytes;
111/139/33/138retained verified. Next attempt history/resolutions, contributing
retention, exact subject/promotion, final source/required-release CI/protected
integration/admission and distinct delivery. No native/SDK rebuild was needed.

**Windows current strict observations complete — 2026-11-14:**
[859](../compat/api-acceptance/orphan-current-windows-strict-v1.json) passes the
two selected strict workflows with one environment identity,16feature/profile
joins/48raw gates,537members/no overlays. Two installed criterion nodes also
pass with ten zero final gauges. The pre-test helper-input failure and all
discovery/receipt-extension attempts are retained; assertions unchanged.
Scratch cleaned62913430bytes,83retained verified. Next matching WSL strict
cohort and two nodes, then32row128binding subject/profile/retention/promotion,
combined final CI/protected integration/admission and distinct delivery. This
Windows result grants no Linux, formal profile or public-artifact qualification.

**Current native/provenance preparation gap closed — 2026-11-14:**
[857/858](../compat/api-acceptance/orphan-preparation14-reviewed-native-bindings-v1.json)
binds fresh source/scope/native-reuse approval for corrected14scope d1133224.
Both full native record validators and actual current Linux CI reuse input/
capture/driver/package validation pass unchanged. Scope/maps/reuse blocks and
426historical candidate files remain unchanged;32review-only ledger flags
applied through the existing CLI. Transient package bytes discarded; no new
wheel/build/environment. Scratch cleaned192bytes,22+16retained verified.
Next two strict selected workflows/two acceptance nodes per profile,32rows/
128bindings, exact artifact subject/promotion/final CI/protected integration
and distinct delivery. No strict profile/artifact/release admission yet.

**Corrected current preparation passes768contracts — 2026-11-14:**
[856](../compat/api-acceptance/orphan-current-ci-pin-contracts-v1.json) covers
corrected CI pin/current14scope. Five production/four test blobs also match
approved842source, committed275888b5and current files. Existing test/license
archives reused; scratch cleaned1406337bytes,12retained verified. Fresh16path
review857 is active. Next bind only its exact approval if granted, pass full
native record and actual Linux CI reuse-input validation, then two selected
strict workflows/two acceptance nodes per profile. No32row/profile admission,
combined final integration or publication is implied.

**Current CI artifact pin fixed before applying review — 2026-11-14:**
[855 correction](../compat/api-acceptance/orphan-preparation14-linux-ci-pin-v1.json)
replaces the stale native568pin with current freshCI43615452982/artifact14122723473
and renews only affected unapproved preparation14scope/map links. Runtime,
profiles,32selected rows/128bindings and426historical files remain unchanged.
[854 review](../compat/api-acceptance/orphan-preparation14-review-v1.json) approved
the prior exact scope conditionally; it was never applied or transferred.
Current source/scope/native-reuse review remains pending after affected contract
rechecks. Then full native validators, two selected composite observer workflows/
two acceptance nodes per profile, final integration/admission and distinct
delivery. Scratch cleaned182bytes across854/855,21+10retained verified.

**Avoid redundant Tk observer runs — 2026-11-14:**
[Selected-edge audit](../compat/api-acceptance/preparation14-execution-path-audit-v1.json)
shows the actual128bindings require two selected logical workflows and two
acceptance nodes per profile. Composite already covers embedded/standalone
ownership; the broader four-workflow/seven-mode declarations are not seven
distinct required processes. Retain discovery/inventory/replay and permitted
extensions, one environment per profile, all32rows/128bindings and original
strict validators. No observation, row, criterion or original obligation is
waived, and no installed/profile admission follows from this planning audit.

**768 preparation14 source contracts pass — 2026-11-14:**
[853 receipt](../compat/api-acceptance/orphan-preparation14-contracts-v1.json)
records all768passes/no skips or failures. Eleven selected source suites cover
candidate/native/reuse/CI/transport and evidence controls. One duplicate-ZIP
warning belongs to the deliberate ambiguity refusal test. Scratch cleaned
1406334bytes,9retained verified. Independent preparation review854 is running;
strict current observer/worker/collector rows, final integration/admission and
distinct delivery remain open. The [per-ID claim audit](superpowers/plans/2026-11-14-gap-investigation-next.md#per-id-investigation-decisions--2026-11-14)
separates current selected routes from historical scientific/host evidence and
explicit compatibility boundaries; no full parity obligation is introduced.

**Successor preparation14 created — 2026-11-14:**
[852](../compat/api-acceptance/orphan-preparation14-bindings-v1.json) binds the
current native/runtime and installed Tk baseline inputs, passing original
Windows/Linux producer rechecks. Historical candidates and142original
dispositions remain unchanged;64criteria/128bindings retained. CI selection is
updated to14, but independent source/scope/native-reuse review and current
strict observers are pending. No artifact/profile admission or publication.
Three immutable source-local inputs required by the unchanged verifier total
596000bytes; no build/SDK/environment copy. Scratch cleaned89bytes,19retained
verified. Next source contract checks/review,32installed rows/128bindings,
combined required/release-policy CI, protected integration and distinct delivery.

**Matching current Tk installed baselines pass — 2026-11-14:**
[850/851 receipt](../compat/api-acceptance/orphan-current-tk-baselines-v1.json)
records56state/capture cases and direct failure/recovery per profile on current
Windows4f537748/WSLe99616e1, source275888b5.537members/no overlays/ten zero final
gauges, actual exits0/awaited; existing Tk8.6.12/Tk9 environments reused.
47787129bytes scratch cleaned,24+27retained files verified. This establishes the
finite API-06/STA-01/LIF-01/LIF-05/LIF-07 baseline on current artifacts; it does
not replace declared observers or strict profile admission. Next additive
preparation14 and the required32installed rows/128bindings, combined source/CI
integration and distinct admitted delivery. No renderer rebuild is needed for
these observation or binding changes alone.

**Current Linux/WSL development evidence complete — 2026-11-14:**
[Fresh Linux producer](../compat/api-acceptance/orphan-current-linux-producer-v1.json)
passes exact capture/archive validation at275888b5/e99616e1;
[bounded reader review](../compat/api-acceptance/linux-candidate13-reader-review-v1.json)
is approved without required changes, preserving130source controls and the old
reader refusal. [Current WSL](../compat/api-acceptance/orphan-current-wsl-v1.json)
passes82selected cases/two expected retained-canvas refusals,47CPUorigins and
nine lifetime controls with ten zero gauges before shutdown. All retained
inventories/terminal cleanup receipts reverify;848removed29879831bytes and
verified38retained files. LIF-06-PANZOOM-RETIREMENT/HOST-IMPORT-RETIREMENT,
LIF-06-QT-FOCUS and SCI-02-CLIP-ALPHA-BLEND now have finite current installed
Windows/WSL development evidence; LIF-06-LINUX-PRODUCER has its exact capture.
These are not strict Tk/profile or release qualifications. Next current installed
Tk baselines, preparation14/32rows128bindings, combined review/protected
integration and distinct admitted delivery. Prior pending checkpoints remain
historical. Follow the [active ordered plan](superpowers/plans/2026-11-14-gap-investigation-next.md#active-remaining-gap-plan--2026-11-14).

**Exact Linux workflow authority reader prepared — 2026-11-14:**
[846](../compat/api-acceptance/linux-candidate13-protocol-source-v1.json) retains
the old refusal, proves only inactive candidate13selector bytes differ, and
passes130source controls after adding exact706a9d26support. Other selectors or
fresh/capacity/condition/comment edits remain rejected.9060242byte source-test
scratch cleaned/19retained verified. Review this bounded reader change before
validating the real capture; keep current Linux CI43615452982 running. No runtime/
workflow change, new native build or WSL/qualification coverage is claimed.

**Linux producer started from exact reviewed source — 2026-11-14:**
[843/844](../compat/api-acceptance/orphan-lifetime-source-head-v1.json) freezes/
pushes23paths at275888b5/treeb939a659, verifies510runtime/133native/537members,
test/mutation identity and82+2collection. Private index cleaned15137954bytes,
104retained verified; foreign HEAD/index unchanged. Fresh Linux run43615452982
is in progress at pinned software-Vulkan repair, not yet a passing wheel/proof.
Observe that same run without redispatch; retain actual outputs then use the
exact wheel in WSL. No PR/merge, successor strict32row128binding qualification,
admission or publication yet. This checkpoint is outside frozen23path source.

**Independent source review approved for Linux CI branch — 2026-11-14:**
[842](../compat/api-acceptance/orphan-lifetime-source-review-v1.json) approves
exact22path4fec1545 delta on7209f119, no required changes. Coordinator rechecks
920inputs/native/wholearchive and9+73positive/2negative/47origin raw results;
reviewer did not read the execution evidence.94byte scratch cleaned/62retained
verified. Next permitted23path freeze/actual-head joins, unmerged fresh Linux CI
producer and WSL acceptance; protected integration and32row/128binding artifact
qualification remain open. Advisory boundaries stay recorded; no release claim.

**Current Windows candidate passes82selected positives — 2026-11-14:**
[9lifetime cases](../compat/api-acceptance/host-import-retirement-windows-v1.json)
and[73regressions/two resource refusals](../compat/api-acceptance/orphan-current-windows-v1.json)
match4f537748/native057d13e6,537members/no overlays.44native CTests pass. The
host-import pin is fixed through event-boundary retirement; failure recovery
submits once. Preserve835's1MiB failure and840's72/73stale-baseline attempt.
Amended focus entry collects/drains before its baseline; all ten exit gauges
still equal entry, and both deliberate retained canvases are refused. Four
latest scratch roots cleaned359881092bytes/146+38+28+32retained verified.
Next exact-delta review/source freeze, fresh matching Linux producer and WSL
acceptance, protected integration and successor32row/128binding qualification.
Known SDK roots839 contain only Windows SDKs; WSL/backing volumes are writable
and have reserve. Keep LIF-06 parent/subitems partial beyond this Windows scope.

**Windows installed lifetime controls:6pass/1failure — 2026-11-14:**
[834/835](../compat/api-acceptance/orphan-retirement-windows-v1.json) verifies
44native CTests and537installed members for26017072/native33a96aff. Repeated
PanZoom, live-peer/helper-thread, pending-snapshot, held-context and unknown-ID
controls pass before shutdown. The large host-import case leaves1MiB pinned;
track LIF-06-HOST-IMPORT-RETIREMENT next, retaining the failing wheel/assertion.
Both scratch roots cleaned324069472bytes/145+39retained verified. WSL, fresh
review/integration and strict successor qualification remain open; no release
coverage or seven-case pass is claimed.

**Orphan retirement patch source-tested, native validation open — 2026-11-14:**
[833](../compat/api-acceptance/orphan-retirement-source-controls-v1.json) passes
33CPU/protocol cases for orphan/late DELETE, association and failed-flush
ownership, preserving lazy uploads and primary errors. Original13failure
control and guarded backend-selection failure remain retained. New native API
is uncompiled; current wheels remain unfixed. Next add native live-peer,
pending-snapshot/helper-thread/host-import controls, reuse immutable SDKs for
matching leaf builds, and prove installed Windows/WSL retirement before review,
integration and successor strict qualification. Peer831 scratch cleaned85bytes,
19retained verified;833 had no scratch. LIF-06-PANZOOM-RETIREMENT stays open.

**Orphan-retirement design constraint verified — 2026-11-14:**
[832](../compat/api-acceptance/orphan-queue-finalizer-order-v1.json) demonstrates
shared-queue finalization before GLObject DELETE emission in an unreachable
cycle. A pending-DELETE-only finalizer would miss this case. Preserve ownership
across finalizer order/queue merges in the fix, then validate native and installed
behavior. Source-only probe exit0/waited, no scratch; LIF-06 remains open.

**PR83 merge gate complete — 2026-11-14:**
[830](../compat/api-acceptance/current-installed-protected-integration-v1.json)
verifies actual7209f119/tree457bfb57,11required checks,14frozen source blobs and
517runtime/test joins, preserving later WIP and foreign HEAD/index. No scratch
was created. Continue with LIF-06-PANZOOM-RETIREMENT; source integration does not
close the32installed rows/128bindings or artifact/publication gates.

**Updated closure order — 2026-11-14 (planning only):**
Follow the [current execution plan](superpowers/plans/2026-11-14-gap-investigation-next.md#current-execution-plan-investigate-fix-then-qualify):
verify PR83 integration; investigate safe orphan deletion and close
LIF-06-PANZOOM-RETIREMENT with matching Windows/WSL native and installed proof;
audit remaining bounded claims; qualify the final artifacts against the 32
selected installed rows/128 bindings; complete release review/admission and
distinct delivery. Explicit completion tests and storage stop rules are in the
plan. This update adds no execution evidence or full-parity requirement.

**PanZoom lifetime diagnosis complete, fix open — 2026-11-14:**
[829](../compat/api-acceptance/panzoom-retirement-diagnosis-v1.json) excludes
retained scene/widget/camera/canvas objects: weakrefs die afterGC but native
gauges remain704/936/691200bytes. Two retained contexts expose10DELETEs each,
then fail `missing canvas 0` while flushing after canvas removal. Next implement
safe context-independent orphan deletion, preserving shared/pending resources,
and validate Windows/WSL with matching native builds/proofs. No current wheel is
claimed fixed. Diagnostic target cleaned17,902,134bytes/22retained verified.

**PR83 pushed with protected auto-merge — 2026-11-14:**
[828](../compat/api-acceptance/current-installed-source-head-v1.json) records
14reviewed/permitted paths at6a4d0f11/tree457bfb57 on26e9ea5f. Exactcurrenthead
joins510runtime/all7tests/Qt/wheels/mutant;73+2cases collect without nativeimport.
Private index cleaned15,136,356bytes/79retained verified, foreign index preserved.
RequiredCI/actualmerge pending. Next diagnose PanZoom ownership/retirement and
renew exactcurrent selectedTk installed proofs/admission;73Qtcase passes do not
close those gates. This later receipt/checkpoint stays outside frozenPR83.

**Expanded source review complete — 2026-11-14:**
[825 approval](../compat/api-acceptance/current-installed-source-review-v1.json)
covers exact13file delta9bb9fe55 on26e9ea5f, no required changes.1,314inputs
reverified;96byte scratch cleaned/38retained verified. Earlier review-pending
and original receipts' WSL-pending fields stay historical. Next final14path
metadata freeze, actual-head joins/collection and normal protectedCI/integration.
Keep **LIF-06-PANZOOM-RETIREMENT open**:352buffer/468CPU/345600texture bytes per
closed scene accumulate on old/new wheels until process shutdown; test-reference
versus runtime-retirement cause is unproved. Weak-reference/owned-Qt-destruction
controls are next. Separately, audit826 identifies32installed rows/128bindings
for4Tkworkflows×2profiles before existing strict admission;73Qt cases do not
substitute. No current artifact/profile/release approval follows from this review.

**Matching current-wheel installed checks pass — 2026-11-14:**
[Windows822/823 andWSL824](../compat/api-acceptance/qt-callback-installed-v1.json)
each pass73selected cases with537members/no overlays/47CPU origins and ten zero
process-shutdown gauges. Two deliberately retained-canvas cases are refused per
profile; original820failure and822partial mutation outcome are preserved.
Newfocus source/event proofs match; unrelated entry resources are not claimed
retired. WSL borrowed inputs unchanged, six actual processes awaited (negative1
expected, others0), private Xvfb0. WSL scratch cleaned29,872,635bytes/33retained
verified. Next expanded source/evidence review and protected integration, then
artifact/profile admission; no broad parity or public-release claim.

**Windows resource-baseline check complete — 2026-11-14:**
[821–823](../compat/api-acceptance/qt-focus-resource-baseline-v1.json) records
73passing installed cases and two deliberate retained-canvas refusals with
explicit module ownership. Preserve the previous1of2control outcome. New test
bytes restore all ten entry gauges, without claiming unrelated prior scenes
retired. All three targets cleaned71,606,279bytes. Matching WSL and fresh source
review/integration remain; earlier clip/blend approval is not transferred to the
additional focus-test change. New artifact/profile/release admission stays open.

**Installed focus diagnosis and test correction — 2026-11-14:**
Managed821 reproduces identical pre-focus resource retention on original/new
wheels; fresh new-wheel focus2passes. The revised focus test checks quiescent
work and restoration of all ten entry gauges rather than global zero in a
process that has other scenes. Windows822 passes73selected installed cases,
537members/no overlays/47CPU origins/final shutdownzero. A deliberately added
canvas control rejects1of2; correct its object retention before claiming a
reliable refusal.821/822 scratch cleaned53,704,150bytes/27+29retained verified.
Next corrected negative control, matching WSL and independent review including
the additional focus-test change. Earlier review816 is not transferred to it;
new-wheel admission/release stays open and original failures are preserved.

**Focus source integrated; installed follow-up remains open — 2026-11-14:**
PR82 actual merge26e9ea5f/tree3c39641e equals tested head, all11required checks
pass and16sourceblobs/510runtime/810guards verify in managed run818. Later
blending work and foreign index remain unchanged. Its source integration is
complete. CandidateWindows820 installed run has71passes/2focus gauge failures
after earlier scene tests, not73passes.537members/no overlays/47CPU child origins
verify; final shutdown gaugeszero. Cause needs minimal sequence/original-wheel
controls before a fixture or runtime diagnosis. Failed scratch cleaned17,902,126
bytes/25retained files verified. Installed/admission/release acceptance stays open.

**Changed-wrapper wheels prepared, not installed — 2026-11-14:**
Managed run819 (`callback-python-package-819/verification.json`) retains
unreleased Windows18e11361/Linux9efb556e wheels for already merged PR81 runtime.
Native proofs/source/archive audits pass; only `_qt.py` and RECORD change from
original9e4/a271. Metadata/native/notices/version/tags remain unchanged. Scratch
cleaned17,376,340bytes/30retained verifications; original diagnostic failure is
preserved. Next zero-overlay installed acceptance and profile/artifact review.
No new public release or transferred installed qualification is claimed.

**Clipped blending amendment approved — 2026-11-14:**
[816](../compat/api-acceptance/mesh-clip-blend-review-v1.json) approves exact
eight-file delta `b44c8d71` on PR82 source head `2f07a13f` with no required
changes. All 1,287 inputs reverified; 89-byte review scratch cleaned and 38 files
retained/verified. The encoding failure after saving the complete reviewer
response is retained; reviewer exit 0/awaited and source decision are distinct.
Alpha invalid-value evidence proves immediate valid recovery, not atomic state
rollback. Earlier WSL/review pending labels are superseded; actual PR82 merge,
actual-head joins/three-case collection and protected integration remain next.

**Matching clipped blending complete at finite installed scope — 2026-11-14:**
[814 Windows](../compat/api-acceptance/mesh-clip-blend-windows-v1.json)/
[815 WSL](../compat/api-acceptance/mesh-clip-blend-wsl-v1.json) each pass three
cases on retained 9e4/a271 wheels/runtime2b8 with no overlays, 537 members
verified and ten zero gauges. Both report identical exact pixels, queued counts
2/4/6, 576 changed pixels and restoration. WSL borrowed origins stay unchanged;
install/tests/Xvfb/controller exit 0/awaited. Both targets cleaned 47,778,839
bytes, 25/28 retained files verified. SCI-02-CLIP-ALPHA-BLEND still needs
independent review and source integration; no broad parity/new artifact claim.

**SCI-02-CLIP-ALPHA-BLEND Windows verification complete — 2026-11-14:**
[814](../compat/api-acceptance/mesh-clip-blend-windows-v1.json) passes three
installed 9e4/runtime2b8 cases with no overlays, 537 members verified and ten
zero shutdown gauges. Three queued revisions have counts 2/4/6, exact analytic
pixels/restoration and clipping isolation; invalid alpha is immediately replaced
with a valid value, not an atomic-setter-state guarantee. Scratch cleaned
17,904,165 bytes; 25 retained files verified. Next matching WSL, then review
and integration. No newer-wrapper artifact/admission/release claim.

**Next finite rendering investigation selected:** SCI-02-CLIP-ALPHA-BLEND adds
three source cases for clipped textured/tinted alpha blending over opaque blue,
including zero-alpha and invalid-value recovery with queued restoration.
Existing color/alpha composition evidence uses `blend=False`; camera mutation
already has finite Windows/WSL proof and needs no repeat. Windows814 now passes
and is cleaned; matching WSL and review/integration remain pending. The finite
installed observation does not close broader SCI-02 or qualify a newer artifact.

**Reviewed focus source pushed — 2026-11-14:**
[PR82/head receipt](../compat/api-acceptance/qt-focus-source-head-v1.json)
binds commit `2f07a13f`/tree `3c39641e`, 16 reviewed/permitted paths on `a69505ce`.
Actual-head joins cover 510 runtime members and the retained CPU/rendered inputs;
both GPU cases collect. Private index/marker cleaned 15,135,281 bytes with 134
retained files verified; foreign checkout/index preserved. Normal protected
head-pinned auto-merge is enabled; required CI and actual merge remain pending.
Source/overlay acceptance does not qualify a changed installed/public artifact.
This later receipt/checkpoint is outside the frozen PR82 batch.

**Focus test/record amendment approved — 2026-11-14:**
[811](../compat/api-acceptance/qt-focus-amendment-review-v1.json) approves exact
15-file delta `86afc518` on verified parent `a69505ce`, no required changes.
Observed destruction/omitted-deletion refusal resolve 808F1; original negative
review and v1 raw records remain. All 1,315 frozen inputs reverified; review
scratch cleaned 7,604 bytes, 40 retained files verified. Earlier revised-WSL,
cleanup and re-review pending wording is superseded. Next freeze permitted
additive metadata, join tests to the actual head and integrate through normal
protected CI. No broader parent, installed, CI-collection or release claim.

**Current queue supersedes older next-action wording:** PR81 is merged, as
recorded by [805](../compat/api-acceptance/qt-callback-protected-integration-v1.json).
LIF-06-QT-FOCUS still needs the revised CPU test's WSL verification, truthful
superseding teardown evidence, re-review and integration. Review 808 found a
constant teardown-success flag; Windows 809 now verifies four actual widget
destructions and a missing-deletion refusal. Its cleanup apply remains to be
verified. Retain original v1 proofs; rendered Windows/WSL evidence 806/807 stays
reusable only for matching inputs. Then audit remaining claims before selecting
one useful rendering/lifecycle case, and keep changed-artifact acceptance
separate. See the [ordered active plan](superpowers/plans/2026-11-14-gap-investigation-next.md#active-investigation-and-closure-queue--2026-11-14).
No full-parity, new CI collection or new installed/public-wheel claim is made.

**Focus CPU follow-up completed — 2026-11-14:**
[v2 evidence](../compat/api-acceptance/qt-focus-source-tests-v2.json) records
two revised passing cases each on Windows 809 and WSL 810, matching event/focus
and observed four-object destruction proofs, plus the missing-deletion control.
Both scratch roots are cleaned; 14/16 retained files verified. The WSL/cleanup
actions in the preceding checkpoint are complete. Next is re-review and
integration of this finite source test/record batch. Preserve v1 as historical;
its constant flag did not establish destruction. Parent LIF-06 stays partial.

**Reviewed callback source submitted as PR81, 2026-11-14:**
[800source push](../compat/api-acceptance/qt-callback-source-head-v1.json) publishes exactfinalhead`a9b60236`/tree`4c27b9c1`,
49reviewedsource/metadata paths onverifiedbase`bff61230`; runtimecommit`2c609627`
remainsreachablefirstparent. [PR81](https://github.com/bipxx/vispy_vulkan/pull/81)
hashead-pinned normalprotected auto-merge enabled. Actualfinalhead tests798/799
each pass49cases(47CPUinput+2rendereddrawerror); bothoriginalnativeproofs and
LinuxCIreuse input/capture/packagevalidation pass. No missingpaint-scopejoin is
claimed. All795–799scratch cleaned62,908,825bytes; frozen49filebytes/source
ancestryandforeignindexverified. CurrentLinuxCI passednative-reuse step and
CPUjobsareactive; requiredchecks/actualmerge stillpending. Connectormutation
403s retained; authorizedCLIcreatedPRandheadpinnedauto-merge. Thislaterreceipt/
livecheckpoint staysoutsidefrozen49filePR. Source/overlay results remainfinite;
no newtestCIcoverage, strictprofile/admission/publicwheel/release/fullparentclaim.

**Expanded source/scope/reuse review bound, 2026-11-14:**
[795/796review and bindings](../compat/api-acceptance/qt-callback-preparation13-review-bindings-v1.json) approve exact46-file delta
`e4dff5132f3439c967249b82666d2ed375caba80ff465b148fea9c0ac018067c` and the twoexactnative-reuse
digests. Candidate13source/scope refs, reviewonlyledgerflags and nativecandidate
hashpointers are bound without changing scope/maps/reuseobjects. Both original
nativeproofvalidators and actualLinuxCI input/capture/currentPythonpackage
validation pass unchanged; transientpackagebytes are discarded, notadmitted.
414historicalcandidateJSONs and all23existingAPIreceipts remain unchanged.
Reviewer recomputed nohashes; coordinator verifies1,286frozeninputs and records
its receiptcount/test-join errata. Use permittedfallback: namedQtCPU/drawtests
at exactfinalhead beforepush, not a fabricatedpaint-scopejoin. Next retain2c
asfirstcommit, appendone reviewedmetadatafollowup and requirefresh protectedCI.
Source/scope/reuseapproval only: no finalhead/CI/merge/installed/admission/
publicwheel/release or fullparent claim; LIF-06/API-06 remainpartial.

**Current candidate/CI successor prepared, 2026-11-14:**
[790–794source work](../compat/api-acceptance/qt-callback-preparation13-wip-v1.json) creates unreviewedpreparation13 and couples
CPU/Linux selectors and policydigests to it.510Pythonmembers bind current1c68Qt;
native/build/lock/license inputs unchanged,414historicalcandidateJSONs preserved,
64criteria/128bindings/142origin dispositions retained. Fresh56caseTk baselines
+failure/recovery pass Windows/WSL with1QtPythonoverlay, notnewwheelqualification.
Native133input maps match retainedproduction; all3actualreview gates stayclosed.
Contracts793:760pass/2setupfailures from reusedtmp names; unique factory-owned
sibling fix passesall5variants underbothretentionmodes (10targetedcases). No new
full762suitepass.792budgetguard stop47.3MB is retained; failed-onlytmp retention
reduces793sampledpeak to1.9MB. All790–794scratch cleaned98,180,495bytes, including
failedruns. Next independent expandedsource/scope/reuse review, then actual
combined-head acceptance/protectedCI. Sourcepush/merge/release remainpending;
LIF-06/API-06 remainpartial and no historicalqualification transfers.

**Qt callback exact local-head acceptance, 2026-11-14:**
[788Windows/789WSL](../compat/api-acceptance/qt-key-parent-actual-head-v1.json) each pass68cases at localcommit
`2c609627`:47CPU input +21rendered, with47isolatedCPU origin/native proofs and
9rendered recovery proofs per profile;537original members checked before1Qt
overlay,536/native unchanged and tenzero shutdown gauges. This is source-overlay
acceptance, not a new qualified wheel. Both targets cleaned47,774,767bytes;
787private index also cleaned15,131,785bytes. Allactualchildren exited0/awaited.
Push is held: requiredCI selects frozenpreparation12, which rejects exactlythe
changedQt wrapper among510Pythonmembers. Next create/review a truthful successor
and coupledCI binding without altering historical qualification/verifier policy.
No push/merge/CI/publicwheel claim; LIF-06/API-06 stay partial. This receipt and
later livecheckpoints remain outside the frozen29-file localcommit.

**Qt key-parent amendment reviewed, 2026-11-14:**
[786 independent review](../compat/api-acceptance/qt-key-parent-amendment-review-v1.json) approves the exact28-file source delta
`ca51efbd7cfed3bdfac674e62cb715dc7e706b5c5530bacd6dcf3f0a90a08105`
with conditions and no required changes. This is source-review approval only;
LIF-06/API-06 remain partial. Exact local-head tests before push, normal protected
integration and separate changed-artifact acceptance remain required. The review
recomputed no hashes and assessed only the evidence listed in its decision;
prior negative decisions and all withheld scope remain preserved. No current
head, CI, admission, published-wheel or full-parent coverage is claimed.

**Parent key replay fixed and verified at source scope, 2026-11-14:**
[780/781gap](../compat/api-acceptance/qt-key-parent-replay-gap-v1.json) records a second CHANGES_REQUIRED
verdict and empirical405fregression:1key causes2callbacks/2hook reports through
oneparentforward. No approval is transferred. Revised `1c68488e` leaves native
acceptedstate unchanged after a workinghosthook; private_keyEvent delegates to
guarded delivery and consumes suspended-key replay instead of bypassing safety.
[782Windows](../compat/api-acceptance/qt-input-callback-windows-source-v4.json)/
[783WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v4.json) each pass93CPUcases:47input,
including12keypress/release xcanvas/privateparent xdefault/host/brokenhook routes,
plus46paint/window. Cases verify onecallback/error report, no replay/abort,
originalerror/hook identity, laterdelivery and native-loop survival as applicable.
[784Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v3.json)/
[785WSL](../compat/api-acceptance/qt-input-callback-rendered-wsl-v3.json) each pass21same-source rendered
cases:6default-peer/3host-samecanvas/12controls;9childorigin/nativeSHA/10zero-gauge
proofs, parent10zero. Host/default acceptedstate is asserted separately.537original
members verify before1QtPythonoverlay;536/native unchanged. ExistingfilteredQt/
9c5softwaredriver unchanged/Xvfb0; all5WSLprocesses0awaited. Parent-rendered cases
remain parentless; the12parent-forwarding paths are CPU/realQt evidence, notfull
napari qualification. Privateclosed/post-C++-destruction host lookups are not
separately covered. PyQt5/PySide6, BaseException, otherinput and paint-hosthook
limits remain open. All7owned779–785scratch roots cleaned; renderedtargets remove
47,774,775bytes.785initialreadonlyplan refused a livePID; same PID/manifest/verifier
later reportsnotlive and v2plan/apply succeeds. No kill, skippedPIDcheck, changed
registry or deletionretry after reviewrejection; original refusal is retained.
Next exactcumulative re-review, then actualhead source tests and normalprotected
integration. Source-only/source-overlay evidence, no CI/wheel/admission/release
or fullparent claim. Older405f/a47areceipts remain historicalfinite passes.

**Host-hook correction now passes matching source suites, 2026-11-14:**
[774Windows](../compat/api-acceptance/qt-input-callback-windows-source-v3.json)/
[775WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v3.json) each pass81CPUcases(35input,
including7working-host/native-loop and7broken-hook cases;46paint/window).
[777Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v2.json)/
[778WSL](../compat/api-acceptance/qt-input-callback-rendered-wsl-v2.json) each pass21rendered cases:
6default-error peer recovery,3custom-host same-canvas redraw/peer recovery,
12ordinaryinput/PanZoom/draw controls. All9children verify origin/nativeSHA and
10zero gauges; parent10zero. Exactly1QtPythonoverlay on unchanged536/native,
all537original members verify first; existing Qt/WSL9c5driver unchanged/Xvfb0.
Same runtime `405f766f` on both profiles. [771/773gap](../compat/api-acceptance/qt-input-host-hook-gap-v1.json)
records CHANGES_REQUIRED/noapproval for oldera47a: nativehostloop prematurely
exits1 despite customhook. Revisedguard invokes workinghosthook without stopping
canvas/loop; brokenhook falls back to originalsafe deferral. Olda47areceipts
remain historicalfinitepasses, not approval. [776failure](../compat/api-acceptance/qt-input-host-hook-render-fixture-failure-v1.json)
retains3redrawtimeouts after fixturequitclosedwindows;777exit0+keptopen checks
fix the fixture without relaxing pixels/recovery/native/gauge assertions.
Allowned770/771/773–778scratch cleaned; rendered776/777/778remove65,675,375bytes,
retained19/18/26checks. Earlier769cleanup ordering defect stays recorded;
subsequent applies require separate successful inspection. No new build/wheel/
environment. Commonpolicy affects allQtbindings, but PyQt5/PySide6changes remain
unqualified; BaseException is not contained. Closed/detachedinput now ignored
and may propagate to parents. Paint-path customhook behavior is separateopen
work, not fixed here. Source405f/tests/newreceipts need exactamendmentreview and
protectedintegration; no CI/fullnapari/public-wheel/full-parent claim.

**PR80integration verified separately:**
[772](../compat/api-acceptance/lifecycle-panzoom-protected-integration-v1.json) verifies normalprotected
merge `bff61230`, tree `7abcfdbc` equal testedmerge/sourcefreeze, all11required
checks and20delta blobs;702committed frozeninputs match, old16feQt reconstructed
from retainedsource. ForeignHEAD/index and then-current825localWIP inputs stay
unchanged. OptionalMacCPUjobs were pending; no all21job claim. The callbackpatch
was not included. Future source integration uses this actualparent after drift
checks; prior55fd/currentwheel qualification is not transferred.

**Matching WSL rendered callback recovery passes, 2026-11-14:**
[769](../compat/api-acceptance/qt-input-callback-rendered-wsl-v1.json) passes18same-source cases as
[768Windows](../compat/api-acceptance/qt-input-callback-rendered-windows-v1.json):6isolated key/mouse/
wheel error-recovery proofs plus12ordinaryinput/PanZoom/draw-callback cases.
Child import/nativeSHA, original exception identity, failed-canvas no-redraw,
peer green/blue recovery after close and10zero gauges pass in all6children;
parent10gauges zero.537original members verify before1Qtwrapper overlay,
536/native unchanged after; filteredQt/9c5softwareVulkan origins stay unchanged.
All5processes0/awaited, privateXvfb0. Scratch570files/29,871,553bytes removed,
26retained hashes verified; no build/environment/newwheel. Cleanup ordering
mistake is explicitly retained: coordinator's prefix inspection missed2declared
Mesa cache files and failed, but following apply stillran; tool independently
validated exact owned target/registry/hashes. Post-apply snapshot audit confirms
only ownedlinux/cache files/marker. Future apply requires a successful separate
inspection step; no deletion was retried or protected origin targeted.
Next independent cumulative source/fixture/evidence review and protected source
integration; changed-wrapper installed/public admission remains separate. Source
WIP is outside frozenPR80; no broader parent/CI/physicalhardware claim.

**Windows real-canvas callback recovery verified at source-overlay scope, 2026-11-14:**
[768](../compat/api-acceptance/qt-input-callback-rendered-windows-v1.json) passes18cases:6newkey/mouse/
wheel error cases across process_events/run plus8ordinaryinput,2PanZoom and2draw
callback cases. Each new child verifies exact parent import origin/nativeSHA,
original exception identity, failed-canvas no-redraw, peer green thenblue after
failed-canvas close and ten zero shutdown gauges. Parent gauges also zero.
537original wheel members verify BEFORE exactlyoneQtwrapper source overlay;
536members/native remain unchanged, no wheel/build/admission claim. Both child
fixtures now use-I-S plus explicit parent paths: [767failure](../compat/api-acceptance/qt-input-callback-child-origin-failure-v1.json)
retains6origin rejections/2editable native mismatches and10ordinary passes;
no runtime/native rebuild or relaxed origin assertion resolved it. Both Windows
targets cleaned35,802,088bytes total,19/18retained checks; CPU763–766cleanup and
old diagnostics remain separately recorded. Source WIP remains outside PR80.
Next matching WSL rendered recovery, independent cumulative source/fixture review,
protected integration and exact changed-wrapper installed acceptance as needed.
LIF-06/API-06 remain partial; no HID/native-presented/optical/other-binding/full
parity/CI/public-wheel claim.

**Callback source CPU acceptance now matches Windows/WSL, 2026-11-14:**
[765Windows](../compat/api-acceptance/qt-input-callback-windows-source-v2.json)/
[766WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v2.json) pass67same-source cases each,
including21newinput cases. The release fixture now initializes _vispy_canvas
like a real backend and asserts no queued application error before/after destroy;
766has no deleted-widget diagnostic. Earlier764also passed67but logged that
fixture diagnostic; its [v1record](../compat/api-acceptance/qt-input-callback-wsl-source-v1.json) stays
qualified accordingly.763failed before collection due DrvFS fd capture;764/766
use existing-s/no-capture convention, not weakened assertions. Borrowed WSL
Qt/Python origins and source hashes stay unchanged; all children0/awaited.
Scratch markers763–766cleaned358bytes, retained15/16/8/16records respectively.
No renderer/GPU allocation, build or environment install. Next real Dawn-canvas
rendered recovery, then independent review/integration and changed-wrapper
installed acceptance. CPU passes are not public-wheel/CI/other-binding/full-parent
coverage. Source WIP remains outside frozen PR80.

**Qt input callback abort reproduced and source fix verified, 2026-11-14:**
[762source CPU acceptance](../compat/api-acceptance/qt-input-callback-source-v1.json) passes67Windows/
PyQt6cases:21new real offscreen Qt-dispatch cases and46existing paint/window
checks. Seven mouse/wheel/key virtuals now contain ordinary callback exceptions,
ignore the triggering event, suspend the failed canvas and preserve the original
exception for process_events()/run(); errors surface once, peer delivery and
ignored-error same-widget recovery pass.761baseline key callback aborts child
3221226505;760earlier fixture weakref error is separate and both remain retained.
No GPU/native canvas was allocated. All3scratch markers cleaned263bytes total;
762verifies20retained records. This is source-only wrapper WIP outside frozen
PR80: `_qt.py` is the sole intentional drift among810prior guards; prior source
receipts stay unchanged. Next WSL counterpart and actual Dawn-canvas recovery,
then review/integration and exact changed-wrapper installed acceptance as needed.
No new wheel/build, current PR80 result, CI coverage, other-binding or full-parent
claim is made. LIF-06/API-06 remain partial.

**Reviewed combined batch submitted as PR80, 2026-11-14:**
[759source head](../compat/api-acceptance/lifecycle-panzoom-source-head-v1.json) records
`af21f74c` on verified parent `96b1187e`, exact20approved source/evidence/metadata
files.810critical guards/702committed parent inputs match; originalfaulttest and
foreign HEAD/index stay unchanged. Archived approved bytes were staged, with no
checkout/reset/force/admin bypass. [PR80](https://github.com/bipxx/vispy_vulkan/pull/80)
has normal protected auto-merge enabled; fresh required checks/actual merge are
pending. Private index/marker cleaned15,128,875bytes,111retained inputs verified,
scratch absent. No new runtime/native build, wheel release, test CI coverage or
admission claim. This later checkpoint/source-head receipt stays outside PR80's
frozen20-file snapshot; do not amend it merely to record its own CI status.

**Combined integration amendment approved, 2026-11-14:**
[758review](../compat/api-acceptance/lifecycle-panzoom-combined-review-v1.json) approves the exact
19-file composition `4b85c65c` on actual PR79merge `96b1187e`, with no required
changes. It explicitly replaces754's separate750merge prerequisite with one
protected PR, keeping exact parent/file/810guard checks and fresh required CI.
The strengthened PanZoom delivery witness is independently reviewed; prior750
non-doc results and754v1receipts stay unchanged. Coordinator checks702committed
parent inputs and prior approved doc text; only the reviewed PanZoom child moves
to v2evidence. Next stage the approved bytes plus this permitted review receipt
and additive checkpoints through a32MiB private index. No branch/head/CI pass,
new GPU-test CI coverage, admission, release or full-parent closure is claimed.

**Current investigation plan refreshed, 2026-11-14:**
[Ordered closure packets](superpowers/plans/2026-11-13-remaining-gap-closure.md#investigation-and-closure-queue--2026-11-14-current-revision)
now prioritize completed-work integration, stale-record reconciliation, Qt callback
exception handling, ordinary Qt routing and one useful rendering combination.
[PR79 actual merge `96b1187e`](../compat/api-acceptance/qt-input-protected-integration-v1.json) is verified by retained753 (11 required checks,
matching tested tree,810 unchanged guards/foreign index). Strengthened PanZoom
[755Windows](../compat/api-acceptance/qt-panzoom-windows-v2.json)/
[756WSL](../compat/api-acceptance/qt-panzoom-wsl-v2.json) pass2cases each with an
explicit post-release move-delivery witness;756cleanup reclaimed29,870,467bytes,
24retained checks/scratch absent. Review750's approved lifecycle/MSAA batch and
strengthened PanZoom still need guarded integration; combining them requires an
explicit review amendment to754's sequential-merge condition. No new experiment,
build, CI-test coverage, public-wheel qualification or full-parent closure is
claimed by this planning change. Older pending labels below are historical;
source/local-installed/merged/public-delivered scopes remain distinct.

**Qt input now reaches a real scene camera at finite installed scope:**
[751](../compat/api-acceptance/qt-panzoom-windows-v1.json)/[752](../compat/api-acceptance/qt-panzoom-wsl-v1.json)
each pass2same-source PanZoom pan/release/recovery and cursor-wheel/reverse cases
with literal world rectangles,3x3marker centers and image-exact restoration in
explicit240x180SceneCanvasrender.537members/no overlays/ten zero gauges,
awaited exits, WSL Xvfb0/borrowed origins unchanged.47,770,425bytes cleaned/
42retained checks, no new build/environment. Later WIP outside PR79/750approval;
review/integration next. No native-display/optical/HID/focus/DPI/other-camera or
broad LIF-06/SCI-03/API-06 claim.

**Combined evidence/test delta approved for guarded integration:**
[750](../compat/api-acceptance/lifecycle-msaa-review-v1.json) approves amended
12-file scope with conditions/no required changes,810guards/823review inputs.
Color-before-redraw assertion and stale WSL row corrections are confirmed;
16strengthened capture cases and11original submission-fault cases pass per
profile at their exact recorded hashes. All eight result receipts stay unchanged.
Reviewer exits0/awaited,91bytes/839inputs cleaned/verified, no scratch/build/env.
Next protected PR79merge, actual-parent join and exact approved delta/private
index/fresh checks; no new branch or CI/admission/full-parent coverage claimed.

**Review follow-up now tested:**
[748](../compat/api-acceptance/msaa-depth-stencil-windows-v2.json)/[749](../compat/api-acceptance/msaa-depth-stencil-wsl-v2.json)
pass16matching cases each with exact color checked after mutation capture and
BEFORE redraw,537members/no overlays/ten zero gauges. Both targets cleaned
47,770,447bytes/39retained checks, actual exits0/awaited and WSL origins unchanged.
No native build/environment. Original745/746results stay frozen; their color
observation was after redraw.747approved original10-file scope with conditions
and noted this improvement plus stale Windows-child WSL wording; both corrected.
Amended source/v2receipts await a focused amendment review, not transferred
approval. Existing parent/edge/format/surface/physical-memory/CI limits remain.

**Default depth/stencil MSAA capture subset verified:**
[745](../compat/api-acceptance/msaa-depth-stencil-windows-v1.json)/[746](../compat/api-acceptance/msaa-depth-stencil-wsl-v1.json)
each pass16same-source cases: samples0/4, depth/stencil float/byte, full/crop,
analytic values, mutation/refusal/restoration and color preservation on current
wheels/runtime2b8. Actual sample allocation checked,537members/no overlays/ten
zero gauges; awaited exits and WSL origin checks pass.47,770,447scratch bytes
cleaned/39retained verifications, no native build/new environment/display server.
Depth-float tolerance1e-6; other/restored output exact. Uniform samples do not
prove mixed-sample edge selection. New test/records are outside PR79; next
review/integrate alongside later bounded records. LIF-05/SCI-06/API-06 stay
partial; real surface acquisition/physical-memory and other format/feature cells
remain open, with no deterministic existing native acquisition control found.

**Qt input follow-up submitted as PR79:**
[743](../compat/api-acceptance/qt-input-source-head-v1.json) pushes434f1326with
exact9approved files on verifiedbf1e4212parent; test hash joins736/738installed
results,810guards/702parent inputs verify. Frozen approved snapshots are staged,
newer live fault/merge worklist changes and foreign index preserved. PR79normal
protected auto-merge enabled; original CPU43571683051/Linux43571683050checks
live, no CI-coverage/profile claim for new test.15,126,858private-index bytes
cleaned/87retained inputs, scratch absent. Next actual required checks/merge;
submission-fault records and later live checkpoints remain separate WIP.

**PR78 merged under normal protection:**
[742](../compat/api-acceptance/post-preview-protected-integration-v1.json)
verifies bf1e4212at actualheada2dbe39a, merge treef3a86179equal testedPRtree and
all11required checks successful. Optional macOS CPU jobs stilllive/queued;
no all21-job claim.810source guards/foreign index unchanged, no admin/force/
checkout/scratch. A racing already-merged precheck sent no additional merge
request. Next the exact739approved Qt snapshot, preserving later fault records
and live-worklist edits outside that reviewed delta.

**Submission-fault subset complete at local installed scope:**
[740](../compat/api-acceptance/submission-fault-windows-v1.json)/[741](../compat/api-acceptance/submission-fault-wsl-v1.json)
each pass11identical-source pre/post-submit/query-frame failure/recovery,
ticket-retention/non-replay and retirement cases on current wheels/runtime2b8.
537members/no overlays/ten zero gauges each, actual children0/awaited, WSL
borrowed origins unchanged.47,770,449scratch bytes removed/40retained checks;
no new test code/environment/native build. Real surface-acquisition failure,
physical-memory accounting and broad LIF-01/API-06 remain open. New records/docs
are outside PR78/739Qt approval; their future evidence integration is separate.

**Next native-fault evidence subset passes Windows:**
[740](../compat/api-acceptance/submission-fault-windows-v1.json) passes11existing
pre/post-submit/query-frame failure cases, with ticket retention, no replay,
explicit recovery and ownership retirement on current9e4/runtime2b8.537members/
no overlays/ten zero gauges; actual exit0/awaited.17,899,970scratch bytes removed/
20retained checks. No new test code/native build/environment. Next same WSL
subset; actual surface acquisition and physical-memory accounting stay open.
New740records/worklist edits are outside PR78/739Qt delta; approved739metadata
sources are retained for exact staging without adopting this later WIP.

**Qt input review complete; protected integration remains:**
[739](../compat/api-acceptance/qt-input-review-v1.json) approves exact8-file scope
with conditions/no required changes.810source guards/818frozen inputs, reviewer
exit0/awaited, cleanup82bytes/835inputs verified. Test/four receipts unchanged.
"Visible/rendered" in736/738means2x2origin internal framebuffer readback after
an actual draw, not optical/presented-display/whole-canvas proof; restoration
means green after reconnect. Target isolation tests emitter cross-wiring, not
focus routing. The original/patched driver wording refers to one retained Mesa
artifact `9c5c41b3a7b9d759b0960c868f10375281798ad084150716d6d122c8789b9e12`.
Application input-callback abort-safety with ignore_callback_errors=False stays
open. Next wait for protected PR78merge, join actual parent and integrate with
fresh required checks; no new branch, CI coverage, profile or full-parent claim.

**Selected Qt input acceptance complete on Windows/WSL:**
[736](../compat/api-acceptance/qt-input-windows-v1.json)/[738](../compat/api-acceptance/qt-input-wsl-v1.json)
each pass8identical-source payload/render/handled-state/disconnect-reconnect/
target-isolation cases,537members/no overlays/ten zero gauges on current wheels.
WSL uses retained filtered PyQt6 and original software driver/private Xvfb;
borrowed origins unchanged, all children exit0/awaited.737wrong dependency path
fails before collection and stays retained;738selects existing GUI dependencies
with an import precheck.59,740,928WSLscratch bytes removed/48retained checks;
95,540,838bytes cleaned across735–738. No new environment/native build.
Next review/integrate the new Qt test/records after PR78's existing checks;
no source change to its pushed head. LIF-06/API-06 stay partial beyond the named
subset; no physicalHID/focus/gesture/trackpad/DPI/other-binding/CI/admission claim.

**Next behavior gap partially closed on Windows:**
[736](../compat/api-acceptance/qt-input-windows-v1.json) passes8PyQt6generated
key/wheel/mouse cases with exact public payloads, rendered response, handled/
ignored behavior, disconnect/reconnect and target isolation on9e4e30cc/runtime2b8.
537members/no overlays/ten zero gauges, exits0/awaited.735fixture ndarray/Qt
callback abort remains failed with source/reproducer; corrected validation runs
outside Qt callback dispatch. Both targets cleaned35,799,910bytes/40retained
verifications. New test/receipts are outside PR78. Next WSL counterpart, then
review/integration; LIF-06/API-06 stay partial, no focus/HID/CI/admission claim.

**Independent impact review and local commit A complete:**
[731/732](../compat/api-acceptance/post-preview-reviewed-commit-v1.json) approves
the exact78-file delta with conditions/no required changes and records local
commit `63abac6b8a6317766ee1b0a8cfa72da135f2c906`.810source guards/702Git inputs,
885frozen review inputs, exact staged blobs/path set and doc API links verify;
foreign index unchanged.8local collected nodes join by exact test bytes, not CI
coverage or new qualification/admission. Review/private-index scratch removed
15,126,134bytes total;900/51inputs verified. Next the allowed metadata checkpoint,
then push/PR and actual protected checks/merge. No push/integration result yet.
717notes hash refers to retained pre-publication notes, not the current doc;
prior snapshot receipts stay unchanged.

**Later-WIP inventory verified; review/integration remain:**
[730](../compat/api-acceptance/post-preview-delta-audit-v1.json) checks the77-file
owned delta snapshot,810unchanged source guards and702matching frozen committed
Git inputs; foreign index unchanged.8newcamera/filter cases collect locally,
exit0/awaited, without execution or CI claims.729wrong source-versus-Git namespace
adapter failure is retained; corrected730uses the authoritative committed map.
No environment/native build/scratch or cleanup target created. Next freeze the
updated owned delta including this receipt, obtain explicit independent impact
review and integrate normally under branch protection. The77count describes
the audit snapshot, not subsequent documentation/receipt additions.

**Public preview delivery closed; later-WIP integration next:**
[726publication](../compat/api-acceptance/preview-publication-v1.json) and
[728readback](../compat/api-acceptance/preview-public-delivery-v1.json) prove
exact55fd prerelease/two preview paths, both public wheel hashes and all four
served HTML pages. Stable assets/latest/index unchanged. Windows clear/WSL
ABI-only smokes join by exact bytes, not another GPU qualification.727buffered
HTML checker failure stays failed; corrected adapter changes no published content.
All children awaited;17,377,805scratch bytes cleaned across726–728, scratch absent.
Next review/integrate later records/docs/two tests at their actual new head,
then audit stale feature rows before choosing another behavior gap.

**Linux draft smoke complete:** [725](../compat/api-acceptance/preview-draft-wsl-channel-v1.json)
passes authenticated a2715d26 download hash/size, offline isolated install,
537members/23notice inputs/22notice texts and native ABI import with no overlays.
Guest/backing-volume checks pass, existing WSL dependencies unchanged, all
processes exit0/awaited.569scratch files removed/28retained inputs verified;
no scratch remains. Scope is ABI-only, not GPU or public delivery. Both draft
smokes now pass; next public prerelease, separate preview index and actual
public-byte/channel readback, then later-WIP integration.

**Current investigation order — planning only:** follow the
[authoritative closure queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#authoritative-next-actions--2026-11-14).
Next: FIX-06 WSL draft ABI check, public prerelease/index and public-byte readback;
then FIX-04/06/API-06 later-WIP delta review and protected integration. Audit
API/SCI/lifecycle/clipping rows against newer evidence before running more tests.
After that, select finite Qt input, camera/state, filter, lifecycle/capture or
rendering cases in that proposed order, skipping already-proved behavior.
Admitted/merged 718/719 work is not repeated. Broader parents stay partial and
hardware/full-parity boundaries remain unchanged. No execution or new pass claimed.

**Windows authenticated draft smoke complete:** [724](../compat/api-acceptance/preview-draft-windows-channel-v1.json)
passes exact537members/23notice inputs/22notice texts and64x64Vulkan clear,
zero overlays/ten zero gauges on the current9e4wheel.722successful transport
is reused; original adapter failure is not relabelled. Exits0/awaited and target
cleaned. WSL ABI transport/install, public prerelease/index and public-byte
readback remain next; this is not yet public delivery.

**Windows draft delivery adapter failure retained:** [722](../compat/api-acceptance/preview-channel-adapter-failure-v1.json)
downloads/installs exact draft9e4bytes but stops before native import on a wrong
license-directory count. [723](../compat/api-acceptance/preview-notice-placement-v1.json)
proves all23source notice inputs/22notice texts per wheel; manifest.json is
metadata and is packaged under vispy/_licenses. No license/artifact is missing.
24,713,237bytes/18inputs cleaned/verified, failed exit1awaited. Next corrected
smoke reuses the authenticated receipt and immutable original without redownload.

**Draft preview ready for delivery smokes:** [721](../compat/api-acceptance/preview-release-draft-v1.json)
retains draft release445068448, exact55fdtarget and two uploaded current wheel
SHA256/size matches. Stable delivery.json/two wheels/index untouched; not public.
All children exit0/awaited,85bytes cleaned/30inputs verified. Next draft-asset
download/install checks Windows/WSL, then reviewed public prerelease/index and
public byte/channel readback. No new native build or artifact qualification.

**Delivery precheck correction needed:** [720](../compat/api-acceptance/preview-draft-precheck-failure-v1.json)
retains an adapter assertion before any release mutation: stable assets include
delivery.json plus the two expected wheels. All remain unchanged. Failed exit1/
awaited; duplicate-retained-path cleanup refusal0deletions preserved, corrected
new manifest succeeds85bytes/15inputs. Next successor checks only exact wheel
digests and preserves the complete stable-asset baseline; no native rebuild.

**Protected PR77source merge complete:** [719](../compat/api-acceptance/parent-protected-integration-v1.json)
records mergeba49b468with tree4260039fidentical to the23-job tested PR tree.
Exact55fdhead pin/required checks pass; no protection bypass, force or shared
checkout/index changes. Connector ready permission error retained; authorized
existing CLI performs ready/body/auto-merge and verifies actual merge. No
scratch. Next exact55fdprerelease/tag, separate preview-index delivery and
isolated delivered-byte/channel checks; later records/docs/two tests still
require their own explicit delta/impact/protected integration.

**Selected successor admitted; integration/delivery remain:**
[718](../compat/api-acceptance/parent-final-admission-v1.json) passes actual
strict128-binding admission and all8reviewed current mandatory rows. Source
view equals55fdGit blobs; all14canonical/702committed inputs restore exactly,
foreign checkout/index unchanged. New matrix viewe1efb9ad…preserves the original
230b12f3matrix, six optional historical and two NOT_ADMITTED rows; manual foreign
retention stays separate from generic Tk retention. Actual exit0/awaited;
87scratch bytes removed/44inputs verified. Next protected integration and
delivery under714/716conditions, with separate delta/impact check for post-head
data/docs/tests. This does not close broader capability parents or publish assets.

**Exact final review approved; execution guards pending clarification:**
[714](../compat/api-acceptance/parent-promotion-review-v1.json) approves exact
basis/eight manual-retention rows/preview scope; conditions and unread/hash-
reliance limits retained. Actual exit0/awaited;89bytes cleaned/886inputs verified.
[715](../compat/api-acceptance/admission-source-guard-v1.json) proves702source
files equal55fdGit blobs without changing foreign checkout HEAD/index. Focused
716review is active for that topology and the sole temporary ledger exception;
actual admission is still unexecuted. [717](../compat/api-acceptance/preview-publication-corrections-v1.json)
records exact55fdtag target, separate-index/direct-hash installation and installed
byte identification notes. No publication, artifact change or stable upgrade.

**Exact basis711sealed; final independent review714active:**
[Basis711](../compat/api-acceptance/parent-promotion-basis-v1.json) binds full709CI,
exact impact702and subject86efb22b/head55fd4e8as basis1e92e7de…. All702committed
inputs unchanged, small subject copy byte-identical, no origin moves or scratch;
assembly exit0/awaited. Read-only reviewer714has871frozen inputs and requests
separate exact basis/eight-row/preview-channel decisions. Final admission,
protected integration and delivery are still pending; review is not approval.

**All23final-head CI jobs validated:** [709](../compat/api-acceptance/parent-final-head-ci-v1.json)
joins all20CPU/Linux/twoMetal jobs at55fd4e8with original histories, attempts
and checkout identities through the unchanged validator.15CPU/3native reports
reused, only5small archives downloaded(1,012,805bytes). Actual exits0/awaited;
cleanup removes1,012,877bytes/6files, verifies84inputs, scratch absent. Next
seal exact basis, obtain final independent review, execute guarded scoped
admission/restoration, then protected integration/delivery. This is not admission.

**SCI-02-COLOR-ALPHA-COMPOSITION installed subset complete:** [Windows712](../compat/api-acceptance/mesh-color-alpha-windows-v1.json)
and [WSL713](../compat/api-acceptance/mesh-color-alpha-wsl-v1.json) each pass six
Alpha/ColorFilter/TextureFilter/PlanesClipper cases on current9e4e30cc/a2715d26/
runtime2b8bccd. All before/change/restored32x24RGBA frames match literal expected
values; all three revisions stay queued(pending2/4/6). Includes detach/reattach,
zero alpha and valid replacement after invalid-alpha ValueError.537members/
zero overlays/ten zero gauges each; controller/Xvfb exits0/awaited, borrowed
WSL origins unchanged. Both targets cleaned47,787,437bytes/1,150files and
68retained-input verifications. Post-head tests do not broaden frozen55fdCI or
admission; general filter ordering/compositions/blending/MSAA stay open.

**SCI-02/API-06 Windows composition subset:** [712](../compat/api-acceptance/mesh-color-alpha-windows-v1.json)
passes six Alpha+ColorFilter+TextureFilter+PlanesClipper cases on runtime2b8bccd/
wheel9e4e30cc. Literal32x24RGBA frames match exactly for before/change/restoration;
pending draws remain2/4/6 before any read. Covers alpha/color updates,
detach/reattach, zero alpha and valid replacement after invalid-alpha ValueError.
537members/no overlays/ten zero gauges; actual exit0/awaited.17,908,464scratch
bytes removed/33inputs verified. WSL, broader composition/order/blending/MSAA
and final review/integration/admission remain separate; test source is post-head.

[Local package-index preview710](../compat/api-acceptance/parent-index-preview-v1.json)
is now concrete: two exact current-wheel links in the proposed separate
`previews/qt-lifecycle-55fd4e8/simple/` namespace, generated by the unchanged
package-index tool. Both stable index blobs were fetched and byte/hash-checked;
their four asset links remain untouched. Preview files total763bytes. Actual
preparation exit0/awaited; no scratch/native build/remote write. This remains an
unapproved channel proposal, not publication or a stable-version upgrade. Final
review must accept its scope after complete CI/admission and protected integration.

The original CPU run43554619087completed20/20successfully.709validates all23jobs/
history, reusing15CPU/3native identities and downloading only five missing
archives. Collection scratch is removed. Final promotion/admission remains pending.
The seven-row SCI-05record reconciliation is complete at the finite scope
[recorded by708](../compat/api-acceptance/scientific-current-dispositions-v2.json);
broader API/capability obligations remain open.

Promotion-basis assembly711has completed after full709CI validation and cleanup.
Independent final review714is active; guarded scoped admission/restoration
remains separate. Earlier19pass/1active snapshots are historical.

## Current execution status — 2026-11-13

**SCI-05 seven-row reconciliation completed (2026-11-13; API-05/06 partial):** [708](../compat/api-acceptance/scientific-current-dispositions-v2.json) verifies33input hashes, both current44-case JUnits, two camera packets and six current Qt rows' seven-stage functional/collector/worker reports. [Route/value table](api-method-reconciliation.md#current-seven-row-reconciliation--2026-11-13) classifies U05/E03/E04as finite current installed subsets, Q12as six current observations awaiting admission, Q11/Q13as open capture/input scope and H03as historical upstream-only. Runtime2b8bccd/current9e4e30cc/a2715d26scope; no stock failure,142-obligation or984-operation promotion. Initial707adapter's wrong literal status assertion remains exit1/reproducer;708checks actual exact tokens, exits0/awaited. No new graphics/install/scratch/native build. This closes record reconciliation only; broad capability/release gates stay open.

**Current qualification inputs preserved; original CPU CI live (2026-11-13; FIX-04/06, TOOL-01):** After adding the separate camera tests, all702committed qualification inputs still match699hashes exactly. Original CPU43554619087poll5has16SUCCESS/4in-progress/no failures; same handles continue. Retained704identities still cover15CPUjobs, with remaining identities/full23-job bundle/history required at completion. New camera observations do not alter the frozen subject or grant final admission.

**SCI-03 camera-mutation subset now installed-tested on both platforms (2026-11-13):** [Windows705](../compat/api-acceptance/camera-mutation-windows-v1.json) and [WSL706](../compat/api-acceptance/camera-mutation-wsl-v1.json) each pass2azimuth/center mutation/restoration cases on runtime2b8bccd/current9e4e30cc/a2715d26wheels. Both show4,032/2,969changed pixels, exact fresh-scene changed-pose equivalence, exact frozen baseline/restoration and comparison-peer closure isolation.537members/zero overlays/ten zero gauges verify per profile. WSL pinned software Vulkan/private Xvfb and borrowed origins verify; actual controller/Xvfb exits0/awaited. All new scratch removed:47,787,811bytes/1,142files,65retained-input verifications. Test source is post-head55fd; no final-head CI, admission or independent changed-pose upstream oracle is claimed. Broader camera/state combinations stay open.

**SCI-03/API-06 selected Windows camera mutation gap closed at local installed scope (2026-11-13):** [705](../compat/api-acceptance/camera-mutation-windows-v1.json) passes two public TurntableCamera mutations (`azimuth=80`, `center=(.3,-.2,0)`) on current Windows9e4e30cc/runtime2b8bccd. Both visibly change the scene(4,032/2,969pixels), exactly match a fresh scene at the changed pose, survive comparison-peer closure and restore the original frozen upstream image exactly. Changed-pose oracle is fresh-construction equivalence, not an independent upstream reference.537members/zero overlays/ten zero shutdown gauges verify; actual exit0/awaited. New test source is post-head55fd, without runtime changes or transferred CI/admission. Cleanup removes17,908,651bytes/570files and verifies32inputs. WSL counterpart and broader camera/plane/depth/stencil combinations remain open.

**Fifteen completed CPU checkout identities verified (2026-11-13; FIX-04/06, TOOL-01 partial):** [704](../compat/api-acceptance/parent-cpu-ci-identities-v1.json) retains original run/jobs/artifact metadata and15completed CPU job identities for55fd4e8/run43554619087attempt1. Artifact byte counts/SHA256, exact successful job joins, PR checked-head/source-parent, workflow/collector pins and schema verify. Five CPU jobs remain live in that snapshot; this is not complete23-job CI/history validation. Reuse these15reports plus native700reports when collecting the remaining5; no second download of completed transports. Actual collector/download exits0/awaited; managed cleanup removes3,017,597bytes/16files and verifies83inputs, scratch absent. No wheel/SDK extraction or native rebuild.

**Original final-head CI live, latest poll4 (2026-11-13; FIX-04/06, TOOL-01):** CPU43554619087now15SUCCESS/5in-progress/0queued, no failures. Three native identities remain verified separately. Continue these same handles; full23-job original identities/history and final scoped admission/promotion are still required. No redispatch or build allocation.

**Candidate review-reference transition verified (2026-11-13; FIX-04/06, TOOL-01):** [Source-only audit703](../compat/api-acceptance/candidate12-review-transition-v1.json) compares the original674archived candidate b7458444with current f931132eand original675before-hashes. Only `reviews` and `manifest_sha256` differ; both scopes recompute to4c2295f5and bound review hashes/statuses verify. This supplies coordinator evidence for702nonblocking F4 without changing the independent review or its limits. Actual exit0/awaited; no scratch/build/replay. Final CI/admission/promotion remains pending.

**Exact-head change-impact review approved (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Review702](../compat/api-acceptance/parent-head-change-impact-v1.json) approves reuse only for subject86efb22b/head55fd4e8/runtime2b8bccd; required changes empty. Complete read-only decision and its unread/hash-reliance limits remain retained. Admission must re-materialize the proved ledger under the existing guard and restore all14files; approval does not cover a new head containing later receipts. No CI, matrix/Tk admission, promotion or delivery approval. Actual reviewer exit0/awaited; managed cleanup removes8,908bytes/2files and verifies828inputs, scratch absent. Latest original CPU43554619087poll3has14SUCCESS/5running/1queued, no failures; unfinished jobs are macOS CPU builds/vendor restoration, not Metal graphics qualification. Continue original handles; collect full23-job identities/history before final promotion review.

**Stale installed-scope wording reconciled (2026-11-13; API-06, SCI-01/02/03/05/06):** Re-read both current664/665selected JUnit reports, verified their hashes against [the current installed packet](../compat/api-acceptance/qt-parent-current-installed-v1.json), and confirmed44matching no-failure/no-error/no-skip cases each at runtime2b8bccd/Windows9e4e30cc/Linuxa2715d26. Each includes11numeric-zero/flag/recovery cases,8stencil routes,10point controls(8rendered reference cases),4pending-filter revisions and2fixed scenes, alongside9Qt lifecycle cases. Earlier "unpassed/unpushed/installed pending" descriptions are historical checkpoints. [Stencil disposition](stencil-wrapper-disposition.md) now states the exact current scope. This closes a stale-record task only: camera mutation, broader filter/layout/format combinations, original stock failures, final admission and public delivery remain open; no rendering replay, build or scratch allocation.

**Investigation plan refreshed (2026-11-13; FIX-04/06, API-05/06, SCI-05, LIF/SCI backlog):** The [next investigation queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#next-investigation-queue--2026-11-13-planning-revision) starts with refreshing the original final-head CI handles and completing exact admission/integration/delivery gates, then reconciles stale public-route records before selecting one lifecycle or scientific gap. Baseline is subject699/head55fd4e8/runtime2b8bccd, wheels9e4e30cc/a2715d26,128bindings/64criteria, eight observations and three verified native CI identities. CI was not refreshed by this planning change. Existing parent-destruction observations are reused rather than repeated. Each packet has a finish condition, evidence-first path and stop rule; full parity and cybersecurity work remain excluded. No capability, admission or delivery status changes; no tests, scratch, builds or publication.

**Original CPU CI still progressing (2026-11-13; FIX-04/06, TOOL-01 pending):** Retained698job poll2for original CPU43554619087has2SUCCESS/13in-progress/5queued,20jobs total, no failures. Linux1/Metal2successful job checkout identities are separately verified by [700](../compat/api-acceptance/parent-native-ci-identities-v1.json); no all23-job bundle/history/admission or merge claim. Continue these same handles without redispatch. Local native-identity transport scratch is absent after202,058,005bytes cleaned/36inputs verified; no SDK extraction/build.

**Three current native CI checkout identities verified (2026-11-13; FIX-04/06, TOOL-01 partial):** [700](../compat/api-acceptance/parent-native-ci-identities-v1.json) retains original Linux43554619086and Metal43554619080attempt1job/identity evidence for source55fd4e8, successful job IDs and actual PR checked-head/source-parent joins, exact workflow/collector hashes. Three artifact transports match API byte counts/digests(total202,057,916bytes); only small ci-identity JSONs/member lists retained, no SDK/wheel/native payload extraction or rebuild. Actual collector/download exits0/awaited; cleanup removes202,058,005bytes/4files, verifies36inputs, scratch absent. This verifies3native-job identities, not the required23-job complete bundle/history or hardware/release admission. Continue same CPU43554619087handle, then collect20CPUidentities/fullhistory and exact promotion/admission/integration/delivery. Original14preparation files and other-owner index remain unchanged.

**Final-head installed subject renewed; CI still active (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [699](../compat/api-acceptance/parent-head-installed-subject-v1.json) proves128selected criterion/profile bindings/64criteria at qualification head55fd4e8and runtime2b8bccd, zero missing/blocked, using original current wheels, five strict Tk attempts/approved failure disposition and782-input retention.702committed input joins verify(608runtime/build/license,83preparation tools,14canonical files with overlaps). All14files restore against675hashes; original684frozen archive reused, no scratch/environment/native build. Copied prepare console's old624label is separately disclosed; actual materialization/restoration references684correctly. Other-owner index unchanged. [PR77](https://github.com/bipxx/vispy_vulkan/pull/77) stays draft. Retained698job poll1records Linux1/Metal2jobsSUCCESS andCPU20jobs15running/5queued; no observed failures, no full23-job/checkout-artifact/history/admission claim. Next poll same handles, collect complete exact CI basis, final reviewed matrix/Tk admission/promotion and protected integration/delivery.

**DraftPR77 and exact-head automatic CI are live (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [698](../compat/api-acceptance/parent-head-ci-start-v1.json) opens [PR77](https://github.com/bipxx/vispy_vulkan/pull/77) draft at55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1and retains three original pull_request attempt1handles: CPU43554619087queued, Metal43554619080in progress, Linux43554619086completed SUCCESS in the latest snapshot.23jobs remain required; no full CI/admission result is inferred. Linux/Metal use existing workflow reuse defaults; zero manual dispatches/duplicate runs. Connector PR creation first rejects a caller field then integration403; both errors retained, authorized existing CLI creates the draft and readback verifies exact head/base. No local consumer/cache/index/scratch allocated; actual CLI exits/waits and raw API metadata retained. Poll these same handles, retain jobs/artifact/checkout identities and complete histories; next guarded head-proof renewal and exact promotion/admission/integration/delivery. PR stays draft pending gates.

**Owned final qualification head pushed (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [697](../compat/api-acceptance/parent-qualification-source-head-v1.json) commits/pushes110owned files/3,738,502bytes as55fd4e82e1a1d7bcb9d3c93a5e66c1bc825b09a1on the existing WIP branch. All608runtime/build/license inputs are byte-identical to tested2b8bccd; no native rebuild, force push, checkout, deletion or other-owner index change. Includes approved preparation12/current row proofs, synchronized CPU/Linux selectors+policy hashes, regression test and two installed GPU no-op assertions. Correct root-only policy call passes; failed696remains retained. Private-index cleanup removes15,115,728bytes/2files and verifies51inputs within32MiB budget; scratch absent. Next exact-head23-job CI (avoid duplicate PR/manual runs), guarded head-proof renewal, exact admission/promotion and protected integration/delivery; not yet admitted or merged.

**Final freeze adapter setup failure retained (2026-11-13; FIX-04/06 partial):** [696](../compat/api-acceptance/parent-qualification-freeze-setup-v1.json) exits1before commit/ref updates because the caller passes two arguments to unchanged validate_policy(root). Original adapter/traceback/minimal reproducer and actual exit/wait retained. Cleanup removes15,100,811bytes/2files and verifies17inputs; other-owner index unchanged. Correct successor will use the inspected root-only signature; no runtime/qualification failure or approval/admission change.

**Current mandatory pre-admission review and exact688disposition approved (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [695](../compat/api-acceptance/parent-mandatory-peer-review-v1.json) approves the eight current row bindings, selected fixture reuse, manual original-retention scope, finite nine-attempt/eight-discovery history and the one exact Windows688UNVERIFIED disposition; required changes empty. Original failure stays failed; later PASS selection is justified without transferring682approval. Reviewer read selected ranges/spot checks, did not independently recompute hashes/ZIP contents or inspect every row; all explicit withheld areas remain attached, including unknown intermittent child-process origin and no machine/all-time history claim.1145input guards and coordinator arithmetic retained. This is not generic qualification-index retention, final-head CI, matrix/Tk admission, promotion, integration or delivery approval. Actual reviewer exit0/awaited; cleanup removes88marker bytes and verifies1156inputs, scratch absent; all14canonical preparation files unchanged. Next owned final qualification-head freeze/23-job CI identities/history, guarded head-proof renewal, exact final admission/promotion and protected integration/delivery.

**Current eight-row bindings and finite histories validate (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [693/694](../compat/api-acceptance/parent-mandatory-bindings-v1.json) bind all8current observations to source2b8bccd/preparation12, exact9e4e30cc/a2715d26wheels,24gates,537members/ten zero gauges each,1036original-retention checks and492reused fixture-archive members.15foreign dependency origins remain protected and unchanged; this manual audit does not claim generic qualification-index retention acceptance for those envelopes. Equivalent duplicate inventories are byte-verified and all originals retained;690initial zero-delete PID refusal/observed-absent/successful guarded retry are separately checked without changing the original plan or terminal. Native rg prefilter parses344of17,732JSONs at cutoff, finds9exact strict attempts(8pass/1preserved688UNVERIFIED),8separate discoveries,0unattributed controllers/later failures.14canonical preparation files unchanged. Actual audit/scan exits0/awaited; source-only metadata, no scratch/build/install. Next independent exact current scope/fixture/history review and688failure disposition, final owned-head23-job CI and reviewed admission/integration/delivery.

**All eight current mandatory observations collected (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Current8-row aggregate](../compat/api-acceptance/mandatory-parent-current-wheels-observations-v1.json) binds source2b8bccd/Windows9e4e30cc/Linuxa2715d26 across headless/PyQt5/PyQt6/PySide6. [692WSL headless](../compat/api-acceptance/mandatory-parent-wsl-headless-v1.json) passes95GPU/36authored science/rendering/4096markers and first strict replay on pinned Mesa9c5/private Xvfb. Every row verifies537installed members/origins, zero overlays and ten final zero gauges. Nine strict attempts are indexed:8pass/1preserved688Windows UNVERIFIED requiring new independent disposition; discovery stays distinct. Original wrappers/locked dependencies/notices reused read-only, identical resource budgets, no native build.692controller/Xvfb exits0/awaited and host mounts absent; cleanup removes92,589,429bytes/12files, verifies239inputs. AllfourWSL runs reclaim370,357,709bytes/48files; all8reclaim818,059,241bytes/8941files, no owned scratch.690original zero-delete live-PID refusal and actual successful retry remain preserved.14canonical preparation files unchanged. Observations complete, not matrix/profile/release admission. Next exact eight-row bindings/history,688failure review, final owned-head23-job CI and reviewed admission/integration/delivery.

**All three current WSL Qt observations pass (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [689–691aggregate](../compat/api-acceptance/mandatory-parent-wsl-qt-observations-v1.json) binds PyQt6/PyQt5/PySide6 seven-stage/first strict replay results on source2b8bccd/Linuxa2715d26/pinned Mesa9c5. Each537installed members/origins, exact selected binding/device and ten zero final gauges verify. Original matching roots/sites, standalone Python/driver/LLVM, locked fingerprints/versions and notice archives reused read-only; no native build or dependency/rootfs/notice copy. Controller/Xvfb exits0/awaited, guest mounts absent,14canonical files unchanged.691cleanup removes92,589,428bytes/12files/103verified inputs; all three reclaim277,768,280bytes/36files with103inputs verified per run, no scratch.690initial live-PID cleanup refusal remains preserved, with unchanged guarded successful retry explicitly referenced.7of8current observations complete; only WSL headless remains, followed by688failure disposition, final-head CI and reviewed admission/integration/delivery.

**Current WSL PyQt5 mandatory observation passes; cleanup refusal resolved (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [690](../compat/api-acceptance/mandatory-parent-wsl-pyqt5-v1.json) passes seven stages/first strict replay on source2b8bccd/Linuxa2715d26/pinned Mesa9c5 using its original separate PyQt5 root/site.537members/origins, binding/device and ten zero final gauges verify; borrowed fingerprints/versions/notices match630, archive reused. Resource-profile successor documents original binding-specific roots with identical512MiB limits;14canonical preparation files unchanged. Controller/Xvfb exit0/awaited, guest mounts absent/origins unchanged. Initial managed apply refuses with zero deletion because recorded controller PID is live again; later native observation finds PID absent. Original refusal/exit2and plan/terminal stay unchanged; same guarded apply succeeds with separate actual-exit/wait receipt. Cleanup removes92,589,426bytes/12files, verifies103inputs, scratch absent.6of8current observations complete; no profile/matrix/release admission. Next WSL PySide6/headless, exact688failure disposition and final-head CI/admission/integration.

**Current WSL PyQt6 mandatory observation passes (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [689](../compat/api-acceptance/mandatory-parent-wsl-pyqt6-v1.json) renews seven QWidget stages/first strict replay on source2b8bccd/Linuxa2715d26/pinned patched Mesa9c5/CPython3.12.13/private Xvfb.537installed members/origins, selected binding/device and ten zero final gauges verify. Original dependency lower fingerprints/versions and notice-archive members rehash against629; archive reused without duplication. Successor resource profile selectsa271with identical512MiB/240MiB visible+tmpfs limits; predecessor unchanged. Guest/backing capacity and all14frozen preparation hashes verify. Actual controller/Xvfb exits0/awaited; guest precheck confirms no run mounts, debugger/driver/LLVM unchanged. Cleanup removes92,589,426bytes/12files and verifies103inputs, scratch absent.5of8current mandatory observations complete; no matrix/profile/release admission. Next WSL PyQt5/PySide6/headless, exact688failure disposition, final-head CI and reviewed integration/delivery.

**All four current Windows mandatory observations pass (2026-11-13; FIX-06, API-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Windows aggregate](../compat/api-acceptance/mandatory-parent-windows-observations-v1.json) adds [688headless](../compat/api-acceptance/mandatory-parent-windows-headless-v1.json) to685–687Qt profiles on exact source2b8bccd/wheel9e4e30cc. Headless passes95GPU/36authored science/rendering/4096marker checks,537installed members/origins and ten zero shutdown gauges. Replay0functionally passes but remains UNVERIFIED for one additional loaded file; expanded receipt replay1passes, exact failed-attempt disposition still pending. Original fixture versions/RECORD-listed files and source/license archive are reused; only GPU wrapper report source label changes. New successor headless resource profile selects9e4wheel/archive reuse with identical256MiB budget and expectations; old profile unchanged. Actual controller exit0/awaited;688cleanup removes69,192,235bytes/2129files, verifies293inputs. AllWindows runs together reclaim447,701,532bytes/8893files, no owned scratch;14canonical preparation files unchanged.4of8current observations complete, no matrix/profile/release admission. Next four WSL profiles, final-head CI and exact reviewed admission/integration/delivery.

**Three current Windows Qt mandatory observations pass (2026-11-13; FIX-06, LIF-02/04, API-06, PLAT-08, TOOL-01 partial):** [685–687aggregate](../compat/api-acceptance/mandatory-parent-windows-qt-observations-v1.json) binds fresh PyQt6/PyQt5/PySide6 seven-stage QWidget/first strict replay results on exact source2b8bccd/wheel9e4e30cc. Each verifies537installed members/origins, selected binding/device and ten zero final gauges; all14preparation files unchanged. Original filtered locked closures and source/license archives reused; no native builds. All actual controller exits0/awaited; cleanups remove378,509,297bytes/6764files and verify65inputs per run, no owned scratch remains. This is3of8current mandatory observations, without matrix/profile/release admission. Next Windows headless and four WSL profiles, then final owned-head CI, exact reviewed admission/promotion, protected integration and delivery.

**Current mandatory Windows PyQt5 observation passes (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [686](../compat/api-acceptance/mandatory-parent-windows-pyqt5-v1.json) renews the seven-stage plain QWidget workflow on exact source2b8bccd/Windows wheel9e4e30cc using the original filtered locked PyQt5 closure. First strict replay passes, binding/537installed members/origins and ten zero final gauges verify;14canonical files unchanged. Discovery remains distinct; no native build or source/archive duplication. Actual controller exit0/awaited; cleanup removes113,809,395bytes/2346files, verifies65inputs, scratch absent. Together685/686complete2of8current mandatory observations; no matrix/profile/release admission. Next PySide6 and remaining profiles, then final-head CI and admission/integration.

**Current mandatory Windows PyQt6 observation passes (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [685](../compat/api-acceptance/mandatory-parent-windows-pyqt6-v1.json) renews the seven-stage plain QWidget workflow on exact source2b8bccd/Windows wheel9e4e30cc with original filtered locked PyQt6 dependencies. First strict replay passes; discovery remains distinct.537installed members/origins, Vulkan device/binding and all ten final zero gauges verify;14canonical preparation files unchanged. Existing source/license archives reused, no native build. Actual controller exit0/awaited; cleanup removes129,752,954bytes/2423files and verifies65inputs, scratch absent. This is1of8current mandatory observations, not matrix/profile/release admission. Next seven remaining current profiles, final owned-head CI and exact admission/integration/delivery.

**Current selected installed subject proved (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [684](../compat/api-acceptance/preparation12-installed-subject-v1.json) proves all128criterion/profile bindings(64distinct criteria/32selected rows) on source2b8bccd/current9e4e30cc/a2715d26wheels using approved preparation12, original native/archive proofs, separate strict/pytest consumers, five complete strict attempts, one exact independent failure disposition and782-input contributing retention. Zero missing/blocked bindings; artifact remains unadmitted. Guarded derived-ledger materialization restores all14canonical preparation files byte for byte against675hashes, preserving142original required obligations. Actual assembly exit0/awaited; no scratch/environment/native build, only110,487-byte minimal frozen JSON backup for restoration.682/683marker cleanups removed181bytes and verified122/782inputs; no owned scratch remains. Next eight current mandatory profile observations/admission, owned final qualification-head integration/23-job CI, independent exact promotion basis and successor delivery; no full API/hardware coverage transfer.

**Current contributing retention validates (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [683](../compat/api-acceptance/preparation12-proof-retention-v1.json) revalidates both full native/archive proofs and774existing immutable proof inputs, then retains782inputs with actual audit/cleanup exits and waits. The unchanged generic retention validator passes after marker-only cleanup;93bytes removed, scratch absent. No wheel/SDK/environment/source-history copies or origin moves. One additional foreign Windows baseline is hash-verified at its original origin and separately disclosed outside this new generic namespace; original terminal/cleanup records remain retained. Selected32-row receipts, five strict attempts, one approved exact failure disposition, separate pytest phases and original licenses are covered. Canonical ledger is excluded for guarded materialization; no subject/profile/CI/admission is granted. Next guarded128-binding subject proof and exact restored14files, mandatory profiles and final-head integration.

**Exact current failed-attempt disposition independently approved (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [682](../compat/api-acceptance/preparation12-failure-dispositions-v1.json) approves the one676Windows UNVERIFIED receipt-expansion disposition and subsequent PASS selection as draft only; required changes empty, original failure remains failed. Complete read-only CLI stream/decision,104input guards, coordinator attempt-digest arithmetic and four separately indexed discovery reports are retained. Peer did not recompute hashes, execute tools or inspect all ranges/WSL/capture/source internals; its explicit withheld list remains attached. No retention/subject/profile/CI/promotion admission is approved. Actual reviewer exit0/awaited; cleanup removes88marker bytes and verifies122inputs, scratch absent. Next contributing retention through unchanged generic validation and guarded subject proof, then mandatory profiles/final-head CI/integration.

**Current strict attempt histories inventoried (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [681](../compat/api-acceptance/preparation12-attempt-history-drafts-v1.json) scans17,422retained JSONs/79strict controllers and identifies5exact current-wheel/profile attempts: Windows3(2pass/1UNVERIFIED), WSL2pass;0unattributed current-wheel strict reports. Four selected workflow attempts validate through unchanged history validation. Original676receipt-expansion failure remains failed; one exact independent disposition is pending, not inherited from old reviews. Discovery-only and other-environment reports remain distinct. Actual scan/draft/finish exits0/awaited retained; source-only work allocates no scratch, environment or build, and14canonical preparation files remain unchanged. Next independent failure review, contributing retention and guarded subject proof; mandatory profiles/final-head CI/admission/integration remain pending.

**Current selected row bindings validate (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [680](../compat/api-acceptance/preparation12-installed-row-bindings-v1.json) derives32source-local row receipts from676/678strict reports and separate677/679genuine pytest phases on exact source2b8bccd/current9e4e30cc/a2715d26wheels. Unchanged inventory/normalization/pytest validators prove128criterion-profile bindings/96raw gate checks in an overlay; all142original obligations remain incomplete. All14canonical preparation files and execution scope stay unchanged; no ledger promotion or artifact admission. Actual build/finish exits0/awaited retained; no scratch/build/install allocated. Next complete current strict attempt histories, independent failed-attempt disposition, contributing retention and subject proof; mandatory profiles/final-head CI/integration remain open.

**Current WSL genuine pytest receipts pass (2026-11-13; FIX-06/API-06 partial):** [679](../compat/api-acceptance/preparation12-wsl-criterion-phases-v1.json) passes2installed Tk state/capture tests/all6phases on source2b8bccd/wheela2715d26/pinned Mesa9c5; existing passed_pytest validates16selected WSL row fixtures.537members, installed loaded origins, zero overlays, ten zero shutdown gauges and Linux561archive-file/566RECORD checks verify. Separate dependency-site consumer does not inherit678strict fingerprint. Borrowed driver/LLVM/pcre/Python/Xvfb origins rehash unchanged; private Xvfb exit0/awaited;14frozen preparation files unchanged. Existing source/license archives reused. Cleanup removes29,870,483bytes/570files, verifies30inputs; scratch absent. Windows677and WSL679now supply all selected genuine phase receipts. Next32-row derived binding overlay, exact attempt/history/disposition/retention and subject proof; mandatory profiles/final-head CI/admission/integration remain pending.

**Current WSL strict cohort passes (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [678](../compat/api-acceptance/preparation12-wsl-strict-cohort-v1.json) validates both workflows at replay0on exact source2b8bccd/Linux wheela2715d26, approved preparation12 and pinned patched Mesa9c5/Tk9/CPython3.12.13. All16feature joins/48raw gate checks share one installed fingerprint;537members, zero overlays and shutdown gauges verify. Both discovery reports remain UNVERIFIED and distinct. Guest/backing filesystems are writable with capacity reserve; original userspace/Python/driver/dependencies borrowed read-only in a private namespace. Controller/Xvfb exit0and waits retained, host mounts absent and borrowed origins unchanged;14frozen preparation files unchanged. Source/license archive reused by hash. Cleanup removes92,589,423bytes/12files and verifies119inputs, scratch absent. Together676/678supply32strict feature joins/96gate checks on the two current wheels, not admitted rows. Next genuine WSL pytest phases, exact selected proof/history/retention with676failed-attempt disposition, mandatory profiles, final-head CI and promotion/integration.

**Current Windows genuine pytest receipts pass (2026-11-13; FIX-06/API-06 partial):** [677](../compat/api-acceptance/preparation12-windows-criterion-phases-v1.json) passes2installed Tk state/capture tests and all6setup/call/teardown phases on source2b8bccd/wheel9e4e30cc. Existing passed_pytest validates every16selected Windows row fixture;537members, loaded installed origins, zero overlays and ten zero shutdown gauges verify. This consumer borrows the existing dependency site and does not inherit676strict environment fingerprint. Frozen14preparation files unchanged; existing focused/source/license archives reused. Setup adapter initially expected a different newline and failed before scripts/install; original failure retained, corrected adapter/runtime exit0and actual child wait recorded. Cleanup removes17,899,973bytes/568files, verifies25inputs, scratch absent. Next current WSL strict cohort and genuine phases; proof/history/retention, mandatory profiles, final-head CI and admission/integration remain open.

**Current Windows strict cohort passes (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [676](../compat/api-acceptance/preparation12-windows-strict-cohort-v1.json) validates both state/resource/failure and capture workflows on exact source2b8bccd/Windows wheel9e4e30cc with approved preparation12. All16feature joins/48raw gate checks share one installed environment;537members, zero overlays and final shutdown gauges verify. State replay0 remains UNVERIFIED pending expanded receipt, replay1passes; capture replay0passes. Both discovery records stay distinct, and the failed strict attempt still needs its exact disposition review. All14frozen preparation hashes remain unchanged. Existing source/license archive is rehashed/reused; no native rebuild. Actual controller exit0/child awaited; cleanup removes62,906,058bytes/1636files and verifies65retained inputs, scratch absent. Genuine pytest phase receipts, WSL strict cohort, selected proof/history/retention, eight mandatory profiles, final-head CI and promotion/integration remain pending. No profile or artifact admitted.

**Investigation/closure plan refreshed (2026-11-13; FIX-04/06, API-05/06, SCI-05 and related open parents; planning only):** The [active queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#active-investigation-and-closure-queue--2026-11-13) supersedes older next-work notes: exact-wheel strict/pytest receipts, selected binding/history proof, eight mandatory profiles, owned final-head CI, then admission/integration/delivery. Baseline is source2b8bccd, unreleased Windows9e4e30cc/Linuxa2715d26, approved preparation12/scope4c2295f5; [675](../compat/api-acceptance/preparation12-approved-bindings-v1.json) remains unqualified and [664/665](../compat/api-acceptance/qt-parent-current-installed-v1.json) remains local installed scope. A claim-by-claim feature investigation table gives the shortest next case and exit evidence for API, scientific, lifecycle, shader, host and tooling gaps. Reconcile existing evidence before replay; optional hardware/full parity remain deferred. No capability closed, source/artifact changed, experiment launched or cleanup claimed by this planning update.

**Preparation12 exact approvals bound; reviewed gates pass (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [674source/scope/reuse review](../compat/api-acceptance/preparation12-peer-review-v1.json) approves scope4c2295f5and the two exact native-reuse hashes with no required changes. Its file-reading-only/hash-reliance/uninspected-ledger/native/SDK limits remain explicit; it grants no installed/profile/CI/admission approval. [675binding](../compat/api-acceptance/preparation12-approved-bindings-v1.json) recomputes exact scope/reuse/map identities and passes unchanged candidate/coverage/execution/selection, both full native records and both archives;14canonical files are frozen by hash. All330historical JSONs remain unchanged,142original obligations still required. Initial673CLI capture retained only a trailing notification; its incomplete decision remains unbound, with raw/task output preserved and5,225bytes/19inputs cleaned.674uses complete event capture and no shell tools, removes88scratch bytes/verifies21inputs.675is source-only with no scratch/native build. Next: current exact-wheel strict workflows and genuine pytest receipts, mandatory profiles, final-head CI identities/history, promotion/integration.

**CI coupling gaps reproduced and fixed; successor12 awaits review (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Review669](../compat/api-acceptance/preparation11-peer-review-v1.json) approves runtime reasoning but withholds scope/reuse: CPU selector changes lacked required-CI hash renewal, and Linux reuse still chose10. [670/671correction](../compat/api-acceptance/preparation12-ci-coupling-v1.json) reproduces policy refusal and selector-test failure, then fixes both selectors to12and updates exact workflow hashes without reducing23jobs/collector checks. New preparation12validates at scope4c2295f5; both retained native proofs/new archives revalidate and actual review gates remain closed. All330prior JSONs, including unapproved11, stay unchanged. [672](../compat/api-acceptance/preparation12-policy-contracts-v1.json) passes326source cases:282reuse/native plus44CIpolicy cases including the new cross-workflow regression. Cleanup removes8,945,392bytes/4930files, verifies8inputs;669review marker85bytes/18inputs also cleaned. No new CI/build/install launched. Next: independently review new scope/reuse digests, adding seal/execution-scope and policy-selector consistency arithmetic before strict observations and final qualification.

**Preparation11/current-wheel bindings valid, review pending (2026-11-13; FIX-04/06, API-06, LIF-02/04 partial):** [666](../compat/api-acceptance/qt-parent-preparation11-wip-v1.json) creates fresh unreviewed preparation11/source2b8bccd with64criteria/128bindings/32selected rows and all142original obligations retained;318historical JSON records unchanged. Four CPU CI selector arguments point to11before its preparation-tool hash freeze. [667](../compat/api-acceptance/qt-parent-preparation11-bindings-v1.json) revalidates both original native proofs and new9e4e30cc/a2715d26archives through unchanged validators; no new source snapshot, native build or wheel reassembly. Actual source/scope gates refuse, as required. Scope5dd73de0and both new reuse digests need independent approval;669review is active. [668](../compat/api-acceptance/preparation11-reuse-contracts-v1.json) passes282source reuse/native-evidence contract cases; cleanup removes8,945,357bytes/4930files, verifies9inputs, scratch absent.666/667allocate no scratch. No strict/profile/head/admission transfer; prior records/approvals and failed profiles remain unchanged.

**Both new wheels pass local installed acceptance (2026-11-13; FIX-04/06, LIF-02/04, API-06, SCI-01–03/05/06 partial):** [664/665](../compat/api-acceptance/qt-parent-current-installed-v1.json) each pass44selected lifecycle/clear/stencil/point/filter/fixed-scene cases and56Tkbaseline cases plus composite recovery on exact Windows9e4e30cc/Linuxa2715d26/source2b8bccd. Each isolated process verifies537members and loaded installed origins, zero source overlays and ten final zero gauges. Both parent-deletion orders now exercise recommended real-Canvas create_native/update no-ops; two external test lines remain uncommitted and are retained by exact delta/source archive. WSL uses patched Mesa9c5/private Xvfb; metadata561archive-file checks/566RECORD entries and borrowed origins verify, Xvfb exited/awaited. No native rebuild or environment copy. Cleanup removes48,168,056bytes/1210files, verifies59inputs; scratch absent.665retention adapter initially used wrong phase-receipt filename; original zero-delete refusal is retained, corrected metadata adapter changes no runtime/verifier. Earlier [6d6CI](../compat/api-acceptance/frozen6d6-ci-completed-v1.json) has all3workflows/23jobs successful at attempt1, metadata-only and not transferred to2b8bccd. Next: exact successor candidate/reuse/strict/profile/head qualification, owned test integration and promotion. Broader scientific/lifecycle parents remain open.

**Reviewed source pushed and two Python-only candidate archives assembled (2026-11-13; FIX-04/06, LIF-02/04, API-06 partial):** [Freeze661](../compat/api-acceptance/qt-parent-source-head-v1.json) commits/pushes22owned files/610,003bytes as2b8bccd0ac886f771c3e37255a3d5559c254b3cd, preserving the other owner's index and606unchanged runtime/build/license inputs; only the two approved Python runtime members differ. Source cleanup removes15,100,800bytes/2files and verifies85inputs, within32MiB full-index budget. [Package663](../compat/api-acceptance/qt-parent-python-package-v1.json) produces unreleased Windows9e4e30cc/Linuxa2715d26wheels at that head using unchanged retained native payloads. Exact archive and payload audits pass: only `_qt.py`, `canvas.py` and RECORD differ; notices/metadata/tags/native bytes remain exact. Published Vulkan.2 assets untouched. Failed662system-Python missing-packaging setup exits1before outputs;663uses existing project environment with no installation, exits0/awaited. Both packaging marker scratches cleaned174bytes, verifying6+15inputs. No new installed/strict/head/admission/merge claim. Next: exact-wheel installed parent/regression acceptance, renewed qualification and integration; earlier6d6b233CI remains scoped to its own bytes.

**Exact source/tests review approved (2026-11-13; LIF-02/04, API-06 partial):** [Renewal660](../compat/api-acceptance/qt-parent-review-approved-v1.json) approves the inspected two-file runtime correction and parent CPU/GPU tests with no required changes. It resolves651F1–F3, reads native register/destroy logic for duplicate-destroy safety, and checks current source, binding and rendered evidence within retained read-only limits. No hashes/tests rerun by reviewer; unread native correspondence/Qt/event/log/cleanup scopes remain explicit. Source guards were independently checked by coordinator; source/license archives reused by hash. Review cleanup removes84bytes/1file and verifies17inputs. Notes retained: binding-origin audit covers prefix-filtered .py/.pyd members, not Qt DLLs/co-loaded-binding absence; parent-deletion callbacks cannot use live-native accessors after detachment; real rendered create_native/update control is recommended for installed qualification.651CHANGES_REQUIRED remains unchanged. No candidate-scope/profile/wheel/release admission. Next: bounded owned-source freeze/push, Python-only packaging with retained natives and exact installed/strict/head qualification/integration.

**Three-binding CPU ownership controls pass (2026-11-13; LIF-02/04, API-06 partial):** [656/658/659](../compat/api-acceptance/qt-parent-binding-source-v1.json) verifies the generic fixture in separate Windows binding processes: PyQt5/PySide6 each11focused cases and PyQt6 cumulative68cases including those11. Original locked filtered Qt wheels are reused with no environment tree copy, version refresh or native build.657passes11tests but fails a separate origin helper on12embedded PySide6.support virtual paths; its original exit1/JUnit/diagnosis remains retained.658classifies exactly those12aliases and hashes all7real loaded binding members against exact locked wheel members, with no wildcard or existing project-verifier change. Managed cleanups remove194,984,317bytes/1431files and verify50inputs;659is scratch-free. Scope is CPU source/native doubles, not rendered or installed/strict PyQt5/PySide6 coverage.660read-only exact review renewal is active;651is not relabeled approved. New Python package/head qualification and integration remain open.

**Corrected destruction orders rendered on both platforms (2026-11-13; LIF-02/04, API-06 partial):** [654/655](../compat/api-acceptance/qt-parent-followup-rendered-v1.json) each pass8GPU cases on the current653Python bytes plus retained native payloads. Both direct parent deletion and explicit close-then-parent-deletion preserve pending green and subsequent blue peer pixels exactly;537package/overlay hashes and ten final zero gauges verify. Actual exits0/awaited, owned WSL Xvfb exits0/awaited; no native rebuild. Cleanup reclaims47,770,459bytes/1138files and verifies34retained inputs, leaving no scratch. Binding scope is PyQt6 only: the current Windows .venv lacks PyQt5/PySide6/shiboken6, and no packages were installed. Reuse their original locked closures for further selected binding checks. Review651 remains CHANGES_REQUIRED until renewed on these hashes;68CPU source passes and these two8-case observations do not confer installed/strict/new-head or release coverage. Next: exact review renewal, selected binding checks and changed-Python package qualification/integration.

**Independent review findings reproduced and corrected at CPU source scope (2026-11-13; LIF-02/04, API-06 partial):** [Review651](../compat/api-acceptance/qt-parent-destruction-peer-review-v1.json) returns CHANGES_REQUIRED, preserving its read-only/no-hash-recomputation and uninspected-native/binding limits. It confirms reentrant close can dereference a detached backend and create_native can attempt recreation after destruction. [Before652/after653](../compat/api-acceptance/qt-parent-destruction-reentrant-source-v1.json) reproduces3failures/8controls, then passes68CPU cases after both fixes; original raising-handler identity survives without a secondary cleanup error. Real explicit-close/parent-delete and late create_native/update controls pass. Scope remains PyQt6 only. Expanded GPU test now includes both destruction orders but is unexecuted on these new hashes;648/650do not cover the changed canvas.py. Review scratch86bytes cleaned/14inputs verified; source runs allocate none. Next: eight-case Windows/WSL reruns, selected other-binding controls and renewed exact review/package/head qualification. Live-native accessors after destruction remain unavailable; first-error recorder/finalization limits stay explicit. No approval/admission is inferred from completed review execution.

**WSL parent deletion/shared-peer source pass (2026-11-13; LIF-02/04, API-06 partial):** [650evidence](../compat/api-acceptance/qt-parent-destruction-wsl-source-v1.json) passes the same7rendered cases on retained Linux wheelb728b575/native5740b28a with two Python overlays, patched Mesa9c5 software Vulkan and owned abstract-local Xvfb. Actual hidden/readback parent destruction closes/detaches its owner once, preserves pending shared-peer green and subsequent blue pixels (4x4RGBA exact each);537members/overlay hashes and ten final zero gauges verify. Actual exit0/awaited, Xvfb exit0/awaited; borrowed driver/pcre/LLVM/interpreter/Xvfb origins rehash unchanged. Initial649fails before GPU execution because default Xvfb filesystem socket cannot bind WSLg's directory; previous qualified629transport flags resolve setup without system changes. Failed/successful attempts retain original exits/evidence/licenses. Cleanups remove568+570files/57,643,258bytes and verify16+21inputs; both scratch roots absent. No native build, installed-wheel/physical-GPU/full-WSI transfer. Next: independent source review, selected binding controls, changed-Python package/head qualification and integration.

**Windows parent-owned deletion/shared-peer rendered pass (2026-11-13; LIF-02/04, API-06 partial):** [648evidence](../compat/api-acceptance/qt-parent-destruction-windows-source-v1.json) passes7GPU cases on retained Windows wheel6de6d77f/native6dc06d2c with two explicit current Python overlays. Actual hidden/readback parent destruction closes its Canvas once, preserves pending shared-peer green and subsequent blue pixels (4x4RGBA exact each), with537package/overlay hashes and ten final zero gauges. Existing native/readback close/layout controls also pass. Actual exit0/awaited; no native rebuild. Cleanup removes568files/17,899,700bytes, verifies12retained inputs and leaves no scratch. First cleanup terminal adapter used unsupported state complete; its zero-delete refusal and original manifest are retained, corrected successor manifest passes unchanged hygiene checks. Next: WSL rendered source check, independent review and changed-Python package/head qualification. No installed-wheel, other-binding or physical-WSI transfer.

**Parent-owned destruction fixed at CPU source scope (2026-11-13; LIF-02/04, API-06 partial):** [Fix647](../compat/api-acceptance/qt-parent-destruction-source-fix-v1.json) passes64focused CPU cases. Real PyQt6 offscreen parent deletion now detaches the deleted backend, settles Canvas ownership/close once and permits repeated close. Controls cover callback failure/first-error preservation, collected weak owner, native-release error containment and destruction after explicit close, alongside existing paint/close/window-state cases. Initial644failure and645four-failure intermediate fix are retained;646passes63before the final idempotence control. Actual exits1/0/0and waits recorded; source snapshots/licenses retained, no scratch/native build. New Python changes in `_qt.py` and `canvas.py` are outside frozen6d6b233/current-wheel qualification: do not transfer running CI or wheel proof. Next: rendered shared-peer Windows/WSL checks, review and successor Python packaging/qualification using unchanged native payload. Parent IDs remain open.

**Confirmed parent-owned destruction failure (2026-11-13; LIF-02/04, API-06 open):** [Run644](../compat/api-acceptance/qt-parent-destruction-source-failure-v1.json) uses real offscreen PyQt6 deferred parent deletion, the actual Canvas.close implementation and a native-resource double. The child QWidget is genuinely destroyed and its native release slot runs, but the Python Canvas remains `_closed=False`; one test fails at that ownership assertion. Actual pytest exit1/awaited; exact reproducer/JUnit/logs/source hashes retained. No runtime change, GPU claim, environment, scratch or native build. Root license-filename adapter error is recorded separately; AGPL and original BSD references are preserved. Next: settle Python ownership without invoking deleted Qt methods, retain GC-safe release/callback containment, then idempotence/error/peer controls and installed verification. Frozen6d6b233CI remains unchanged; this is a new open defect, not a pass.

**Live exact-head CI job check (2026-11-13; FIX-04/06, TOOL-01 pending):** Original handles remain active at6d6b233. The latest retained job-level response in run641 has CPU43530224577:10completed successfully,6in progress,4queued; Metal43530230265:2queued. Linux43530227494 is completed successfully. No failed jobs observed in this snapshot; no full23-job success, admission or merge is claimed. Keep polling the same handles and retain original identities/history before promotion.

**Stale scientific rows reconciled (2026-11-13; API-05/06, SCI-05, LIF-05/06 partial):** [Source-only audit643](../compat/api-acceptance/scientific-stale-row-reconciliation-v1.json) verifies all six current Qt packet/hash joins, seven stages/537members/zero overlays/ten zero gauges each, and records finite U05/E03/E04/H03 dispositions. Q12 now records six current installed observations without admission or hardware transfer. Corrected the plan's erroneous Q11–Q13 volume mapping: these IDs concern MSAA depth/stencil, platforms/bindings and input; volumes are V01–V09. Q11 and broader Q13 stay open. Actual exit0/awaited, no runtime replay, scratch, native build or cleanup allocation. Existing point/filter/scene/Glue manifests are hash-pinned; their transitive histories are not independently revalidated by this audit.

**Plan refreshed; qualification-head proof complete (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Proof642](../compat/api-acceptance/current-head-installed-subject-v1.json) validates128selected bindings/64criteria at6d6b233, zero missing/blocked, with702committed input joins and all14canonical files restored. Runtime remains99719f1/current wheels6de6d77f/b728b575; the frozen archive is reused, with no scratch, environment or native build. This does not admit or deliver artifacts. The [refreshed sequence](superpowers/plans/2026-11-13-remaining-gap-closure.md#next-investigation-and-closure-sequence--planning-refresh) prioritizes existing23-job CI collection, exact admission and integration; then API/stale-evidence reconciliation, parent-owned canvas destruction and selected scientific workflows. Retained641poll4 records Linux success and CPU/Metal queued; refresh those same handles before action. All eight mandatory observations already pass. Planning adds no test, dispatch, capability closure or release claim; optional hardware/full parity/cybersecurity work remains outside scope.

**Owned qualification head pushed; final CI started (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Private-index source freeze639](../compat/api-acceptance/current-qualification-source-head-v1.json) commits/pushes109owned files/2,338,177bytes as `6d6b233fe80f19887726c6b91a247aa863f6dfee` on the existing WIP branch, with no deletions, force push, checkout or other-owner index changes. All608runtime/build/license inputs remain byte-identical to tested99719; no native rebuild. [Exact-head CI dispatch640](../compat/api-acceptance/current-head-ci-dispatch-v1.json) starts the23required jobs with original Linux/Metal reuse: CPU43530224577, Linux43530227494, Metal43530230265. Latest retained poll641shows Linux completed SUCCESS; CPU/Metal remain QUEUED, so final CI is not passed. Source639cleanup removed15,098,948bytes/verified261inputs; dispatcher640removed84bytes/verified28inputs. The private index exceeded the8MiB estimate because it represents the full base tree; the miss is retained and policy now requires measured-index sizing. No original preflight/limit was raised, and shared20GiB/10GiB policy was not exceeded. Frozen14preparation files and owner index remain unchanged. Poll the same handles without duplicate dispatch; exact admission/promotion review, protected integration/delivery and broader feature work remain open.

**Independent current mandatory pre-admission review approved (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Review638](../compat/api-acceptance/current-mandatory-peer-review-v1.json) approves row bindings, locked fixture reuse, manual original-retention scope and finite histories, with no required changes. It independently rehashes1050frozen inputs,945retained entries,492fixture archive members/487RECORD payload hashes and all8row/24gate joins; both current wheels, feature sets, devices, binding versions,95matching headless case IDs and seven Qt stages verify. Its independent current-wheel worker search finds no other mandatory-row attempts. Source/producer labels are the only Windows GPU-wrapper changes; original failure adapters remain failed. All15foreign origins remain protected; no generic retention acceptance or admission is granted. Unread/recomputation limits remain in the raw review: no execution of624subject validation, no791-input623rehash or recomputation of rendering native hashes/537member lists, no original466JUnit comparison, and no full log/mount/drive content or outside-root/all-time history audit. The cleaned environments cannot be re-inspected. Reviewer observations about receipt-to-discovery links, WSL helper labels and guest-vs-coordinator registry hashes stay explicit. Actual exit0/child awaited; cleanup removed89bytes/verified1062retained inputs. Next: owned final-head freeze/23-job CI, exact admission/promotion basis and integration/delivery. No native rebuild or published-release/full-parity transfer.

**Current mandatory bindings and histories validate (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Dossier636/history637](../compat/api-acceptance/current-mandatory-bindings-v1.json) joins all8current rows/24gates,537installed members and ten zero gauges per row, with945original managed cleanup input checks. All15foreign retained dependency origins remain unchanged and protected by registry613; this manual original-envelope hash audit does not claim generic qualification-index retention acceptance. The492fixture archive members verify, and the Windows GPU wrapper differs only in two provenance labels, with assertions unchanged. The finite two-root history scan enumerates16,910JSON files, parses304literal collector-key candidates and finds8exact strict passes plus8separate discoveries, zero unattributed controllers/later failures. Its prefilter/cutoff scope stays explicit. Two source-only setup failures remain retained:634assumed a rendering wheel field that the helper does not emit;635passed an absolute raw archive origin to the relative evidence resolver. Explicit package/native-member and origin joins fix those assumptions without changing a verifier or runtime report. Runs exit1/1/0/0respectively, awaited; no scratch/build/environment created. All14frozen preparation files remain unchanged. Independent cumulative review, final-head23-job CI, exact admission/promotion basis, integration and delivery remain open.

**All8current mandatory observations pass (2026-11-13; FIX-06, API-06, PLAT-08, TOOL-01 partial):** [Current eight-row aggregatev3](../compat/api-acceptance/mandatory-current-wheels-observations-v3.json) renews the finite authored Windows/WSL headless and PyQt5/PyQt6/PySide6 observations on runtime99719f1/wheels6de6d77f/b728b575; canonical matrix and published qualification remain unchanged. New [WSL headless632](../compat/api-acceptance/mandatory-current-wsl-headless-v1.json) and [Windows headless633](../compat/api-acceptance/mandatory-current-windows-headless-v1.json) each pass the original95GPU cases, rendering/clear/smooth-text checks,4096marker smoke and36scientific cases in discovery and first strict replay, with537installed members/origins and ten zero final gauges. WSL retains software-Vulkan/private-Xvfb scope. Windows reuses five locked pytest-related distributions:492RECORD-verified files, source/licenses archived once, no environment tree copy or upgrade to cached pytest9.2.0; two stale GPU-wrapper provenance labels are corrected without changing assertions. [Windows256MiB](../compat/build-profiles/mandatory-current-headless-windows-v1.json) and [WSL512MiB](../compat/build-profiles/mandatory-current-headless-wsl-v1.json) policies are explicit; no native rebuild. Runs632/633actual exit0/children awaited; cleaned161,779,696bytes/2141files and verified446retained inputs. Exact matrix admission/bindings, final-head23-job CI, independent promotion review, protected integration and delivery remain open. This is8/8observations, not full API/scientific-quality/performance/hardware or release admission.

**All current Qt mandatory observations pass —6/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Six exact Qt profile packets](../compat/api-acceptance/mandatory-current-qt-observations-v1.json) now cover Windows and WSL PyQt5/PyQt6/PySide6 on runtime99719f1/current wheels6de6d77f/b728b575. New WSL629–631each pass seven original plain-QWidget stages and first strict replay,537installed members/origins and ten zero shutdown gauges with separate original locked dependency lowers, CPython3.12.13/private Xvfb and patched Mesa9c5 software Vulkan. Tracked borrowed origins rehash, owned Xvfb exits/waits, guest/backing health and no-leftover-mount prechecks pass. No native rebuild, rootfs/SDK/environment copy or package refresh. The629pre-runtime optional-registry-key generator failure remains retained; all previous protected/blocked paths are inherited. [WSL storage policyv1](../compat/build-profiles/mandatory-current-wsl-v1.json) and [matching-root clarificationv2](../compat/build-profiles/mandatory-current-wsl-v2.json) keep identical512MiB limits; prior policy/evidence stay unchanged. Runs629–631cleaned277,768,283bytes/36files and verified305retained inputs. Windows/WSL headless observations, exact matrix admission/promotion basis, final-head CI, integration and delivery remain open; no broad Qt/input, physical GPU/Metal or release transfer.

**Current Windows Qt mandatory observations pass —3/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Three exact profile packets](../compat/api-acceptance/mandatory-current-windows-qt-v1.json) now cover PyQt5, PyQt6 and PySide6 on source99719f1/wheel6de6d77f/Windows CPython3.12.8/RTX4090 Vulkan. New627/628each pass all7original plain-QWidget stages, discovery plus first strict replay,537installed members/origins and ten zero shutdown gauges, using their own locked binding closures and distinct environments. Capture/image ownership, overlay/hide/restore, injected loss/recovery and close are finite authored checks, not broader lifecycle/input parity. Dependencies were reused offline and shared source archives referenced in place; no native rebuild. Both actual exits0/children awaited;627/628cleaned248,752,405bytes/4341files and verified128retained inputs. Windows headless and all4WSL mandatory rows remain, followed by exact admission/promotion basis, final-head CI, integration and delivery. Original published qualification stays at its own bytes.

**Current Windows PyQt6 mandatory observation passes —1/8renewed (2026-11-13; FIX-06, LIF-02/04, PLAT-08, TOOL-01 partial):** [Source-only identity audit625](../compat/api-acceptance/mandatory-current-gap-audit-v1.json) confirms all8historical mandatory rows use different published wheels; their qualification stays historical. [New row626](../compat/api-acceptance/mandatory-current-windows-pyqt6-v1.json) passes the unchanged seven-stage plain-QWidget scenario and first strict replay on source99719f1/wheel6de6d77f, Windows CPython3.12.8/filtered PyQt6/RTX4090 Vulkan, environment95bae638. Exact537members/installed origins, capture/update/image ownership, overlay/hide/restore, injected loss/recovery, close and ten zero shutdown gauges verify. Locked core/Qt wheels were reused offline; no native build. Initial generator indentation failure occurred before driver/runtime execution and remains retained. Row626actual exit0/child awaited; cleanup removed2423files, reclaimed129,750,985bytes and verified66retained inputs. Seven current mandatory observations, exact admission/promotion basis, final-head CI, integration and delivery remain open. No broader Qt/input, other-binding, WSL/hardware or release transfer.

**Current installed subject proof passes (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Run624 unchanged subject validation](../compat/api-acceptance/preparation10-installed-subject-v1.json) proves128criterion/profile bindings (64distinct criteria) on preparation10/runtime99719f1/current Windows and WSL wheels, with zero missing/blocked joins. All14frozen preparation files are restored after the guarded32-row overlay. [Independent review621](../compat/api-acceptance/preparation10-failure-dispositions-v1.json) approves both exact Windows failure dispositions and draft latest-workflow selections; the two originals remain UNVERIFIED. Reviewer limits remain explicit. Its discovery-index wording finding is corrected by a separate four-report index, without rewriting620. [Contributing retention623](../compat/api-acceptance/preparation10-proof-retention-v1.json) validates791inputs in place. Run622 cleanup passed but its post-cleanup retention validation failed on one extra baseline outside selected roots; that failure remains retained. The corrected new event excludes that extra foreign-origin entry, verifies its unchanged hash/origin, and preserves original records; no verifier or dependency origin changed. Runs621–623 cleaned274bytes/1646retained-input verifications;624created no scratch. Original142obligations, mandatory-eight-row renewal, final-head23-job CI, promotion review, protected integration and delivery remain open; no broad API/hardware or published-wheel admission.

**Exact current attempt histories reconstructed (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Run620 history drafts](../compat/api-acceptance/preparation10-attempt-history-drafts-v1.json) scan16,617retained JSON files/66strict controllers and identify6exact wheel/environment replays, with zero unattributed current-wheel reports. Windows has2UNVERIFIED first replays and2later passes; WSL has2first-replay passes. Unchanged workflow-history validation accepts the complete ordered lists and4latest workflow selections. Original failures, discovery reports and other environment variants stay retained and distinct. Both Windows failed-attempt dispositions still need independent approval; contributing retention and subject admission remain pending. Scan/draft exit0 and are awaited; no scratch/build/environment created. This does not renew mandatory rows, final-head CI, release or broad API/hardware coverage.

**Current selected installed row bindings validate (2026-11-13; FIX-04/06, API-06, SHD-06, TOOL-01 partial):** [Run619 derived overlay](../compat/api-acceptance/preparation10-installed-row-bindings-v1.json) passes unchanged inventory validation for32selected Windows/WSL rows,64distinct criteria/128profile bindings and96raw gate checks on runtime99719f1/current wheels. Strict observer identities remain separate from the genuine same-wheel pytest processes. All14frozen preparation10JSON files and execution scope remain unchanged; all142original required rows remain incomplete. Run618's failed secondary-store row path and reproducer remain retained; source-local new receipts resolve that exact storage requirement without changing a verifier. Source-only runs exit1/0 respectively, awaited, with no scratch/build/environment or cleanup allocation. Exact attempt histories, independent failed-attempt resolutions, contributing retention, subject admission, mandatory rows, final CI and integration remain pending.

**Current WSL genuine pytest phases pass (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [Run617 installed phase evidence](../compat/api-acceptance/preparation10-wsl-criterion-phases-v1.json) passes both selected Tk state/capture nodes and all6setup/call/teardown phases on exact Linux wheelb728b575/runtime99719f1 with patched Mesa software Vulkan. Unchanged `passed_pytest` accepts all16selected Linux fixture rows;537installed members/origins,561archive members,566RECORD entries, zero source overlays and ten final zero gauges verify. Existing Python/test dependencies were reused; no native build. Actual exit0/child awaited; cleanup removed570scratch files and verified26retained inputs. This separate pytest process does not claim strict observer fingerprint423ba184 or profile admission. Next: exact Windows/WSL subject/profile/history/retention joins, required mandatory profiles/final-head CI and protected integration. Broad API and hardware coverage remains open.

**Current investigation order and WSL strict checkpoint (2026-11-13; FIX-04/06, API-06, TOOL-01 partial):** [The revised active plan](superpowers/plans/2026-11-13-remaining-gap-closure.md#current-investigation-plan--2026-11-13) supersedes older next-step queues: current WSL pytest phases → exact subject/history/retention joins → mandatory-profile/final-head CI/integration → bounded API/lifecycle/science investigations. [Run616 WSL strict evidence](../compat/api-acceptance/preparation10-wsl-strict-cohort-v1.json) passes both workflows/16feature joins/48gate checks on source99719f1, wheelb728b575 and patched Mesa software Vulkan, environment423ba184. Installed537members/origins and zero shutdown gauges verify; actual exit0/child awaited. Managed cleanup passed, deleting12files and verifying120retained inputs. No subject, mandatory-row, CI, release or physical-GPU admission. Planning adds no test result; current WSL genuine pytest phases remain the immediate missing proof. Older pending statements below are historical at their own checkpoints.

**Windows strict workflows and selected pytest fixtures pass (2026-11-13; FIX-04/06, API-06/TOOL-01):** [strict matched cohort614](../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json) validates16feature joins/48raw gate checks on exact wheel6de6d77f/source99719f1 with one environmentd664beb3. [Separate installed criterion phase615](../compat/api-acceptance/preparation10-windows-criterion-phases-v1.json) passes the two genuine selected pytest nodes/all6phases, satisfying all16Windows row fixtures;537members/installed origins, zero overlays and ten final zero gauges verify. This pytest process borrows existing test dependencies and does not claim the strict observer fingerprint. Both strict discovery/receipt-extension histories remain retained. Runs614/615 cleaned80,802,081bytes and verified95retained inputs. Windows raw/fixture prerequisites are observed; no selected subject, mandatory-eight-row, final CI or release admission. Current WSL strict/pytest proofs, exact profile/history/retention joins, final-head CI, protected integration and delivery remain pending.

**Current Windows strict matched observations pass (2026-11-13; FIX-04/06, API-06/TOOL-01):** [wheel6de6d77f/source99719f1/preparation10 evidence](../compat/api-acceptance/preparation10-windows-strict-cohort-v1.json) passes both state/resource/failure and capture workflows with one exact environment fingerprintd664beb3. All16feature joins/48raw gate checks validate,537installed members and required shutdown gauges verify; initial discovery and first-replay UNVERIFIED reports remain retained with their receipt extensions. The existing locked CPython/dependency wheels were reused offline; one bounded clean consumer was required by the isolated collector. Run614 cleaned62,904,083bytes/verified71inputs. This is current Windows strict observation, not selected-subject/mandatory-eight-row/CI/release admission. Fresh selected pytest receipts, WSL matched observations, formal bindings/retention and final-head integration remain pending.

**Preparation10 source/scope/reuse approvals bound; full records pass (2026-11-13; FIX-04/06, API-05/06, LIF-01–04, SCI-01–03/05/06 partial):** [independent review609](../compat/api-acceptance/preparation10-peer-review-v1.json) approves exact scope0b668996 and both reuse digests with no blocking changes, independently checking142required obligations,158original rows,272prior files and64criteria/128bindings. Its unread/recomputation limits remain recorded; coordinator separately reproduces execution-scope projection. [Full reviewed source/coverage/execution/selection/native/archive gates now pass](../compat/api-acceptance/preparation10-approved-bindings-v1.json), without changing runtime, scope, reuse digests or validators. Two partial attempts remain failed:611omitted map-hash approval references;612exposed a missing source-local C++ snapshot. Exact existing source bytes521,666are now retained at the required source-local path with both origins protected by [successor registry613](../compat/api-acceptance/preparation10-source-local-binding-v1.json). [282source contracts pass](../compat/api-acceptance/preparation10-reuse-contracts-v1.json). Runs609/610/613 cleaned8,945,534bytes/verified38inputs;611/612created no scratch. Strict installed profiles, required final-head CI, protected integration and delivery remain pending. Two of16selected features (wrapper raster/submission;8criteria) are additive new scope, not parent subsets; all original parents stay required.

**Preparation10 and exact bindings validate, unreviewed (2026-11-13; FIX-04/06, API-06):** [fresh preparation](../compat/api-acceptance/lifecycle-preparation10-wip-v1.json) uses source99719f1, current installed baseline observations and final CI/Metal/Linux pin hashes; scope0b668996. It preserves272prior JSON records and all142original dispositions, with64distinct criteria/128profile bindings. [Both native proofs and both current wheel archives](../compat/api-acceptance/lifecycle-preparation10-bindings-v1.json) validate without compilation, retagging or reassembly. Both actual review gates refuse admission as required; no approvals transfer. Source-only runs607/608 exit0/awaited and create no scratch. Independent source/scope/reuse review, strict profiles, required final-head CI, protected integration and delivery remain pending. Runs604–606 cleanup reclaimed73,387,744bytes and verified221retained inputs.

**Current Metal producers verified and reuse pin renewed (2026-11-13; TOOL-01, PLAT-04 experimental, FIX-04/06):** [both original architectures](../compat/api-acceptance/lifecycle-metal-current-originals-v1.json) validate at exact source99719f1/run43495769632 with whole-run success: original archive/native/configuration, source-before/after, installed CPU imports and producer cleanup. All97original members per architecture are retained by hash; matching files are referenced once, without moving any pinned origin. compat/metal-ci-reuse.json now binds these current producers; no graphics or admission/review approval is inferred. Run606 cleaned25,561,769bytes/verified170retained files. Preparation10 can now freeze against the final pin hashes; reviews, strict profiles, final-head CI and integration remain open.

**SCI-03/E04 two current Windows reference scenes pass (2026-11-13; SCI-05/API-06 partial):** [exact source99719f1/wheel6de6d77f evidence](../compat/api-acceptance/scene-state-current-windows-v1.json) verifies fixed Turntable perspective and coplanar depth/polygon-offset scenes against frozen upstream inputs and criteria. Both observed max differences are0 across71,680pixels;537runtime members/installed origins and ten zero final gauges verify. New test is uncommitted. Camera mutation, broader plane/depth/stencil combinations, other platforms and strict/release admission remain open. Run605 cleaned17,952,038bytes/verified25inputs; no runtime/native rebuild.

**SCI-02/E03 selected WSL filter revisions pass (2026-11-13; SCI-05/API-06 partial):** [Linux wheelb728b575](../compat/api-acceptance/mesh-filter-pending-linux-v1.json), runtime99719f1/test9ac765ab on CPython3.12.13/pinned Mesa9c5 software Vulkan, passes the same four pending-filter cases as Windows. Native pending_draws2→4, all6,144analytic pixels exact,537runtime members/installed origins, zero overlays and ten final zero gauges. Linux additionally verifies561archive members,566installer RECORD entries and manylinux_2_39 tag. Test remains uncommitted; full filter inventory, E04 scene/camera/state and strict/release admission stay open. Run604 cleaned29,873,937bytes and verified26retained inputs; no native rebuild or source overlay.

**SCI-02/E03 native-pending filter revisions verified (2026-11-13; SCI-05/API-06 partial):** [four exact Windows installed cases](../compat/api-acceptance/mesh-filter-pending-windows-v1.json) on runtime source99719f1/wheel6de6d77f use new uncommitted test9ac765ab. Texture replacement/enabled, clipping-plane count+values and detach preserve both expected targets, with native pending_draws2before mutation and4before captures in every case. All6,144analytic pixels match,537runtime members/176loaded origins verify, zero overlays and ten final zero gauges. No runtime/native rebuild or release admission. Earlier constructor/unbound-capture setup failures remain retained; full filter inventory, WSL and scene/camera/state coverage stay open. Runs600–603 cleaned71,604,957bytes/verified101retained inputs; source-only retention generator/copy errors are recorded separately from actual test outcomes.

**SCI-02/E03 before-capture mutations pass (2026-11-13):** [four Windows installed cases](../compat/api-acceptance/mesh-filter-before-capture-windows-v1.json) on source99719f1/wheel6de6d77f match all6,144analytic before/after pixels, with537verified members, installed origins and ten zero final gauges. Renderer/native bytes unchanged. Test source is a new uncommitted file; no broad filter inventory, WSL or release claim. This revision does not yet assert native pending counts; that witness is added next and is unexecuted. Initial constructor/capture-setup failures remain retained. Runs600–602 cleaned53,701,531bytes/verified75retained inputs.

**SCI-02/E03 capture fixture corrected (2026-11-13):** [run601 failure](../compat/api-acceptance/mesh-filter-unbound-capture-v1.json) contains four actual capture assertions and saved transparent before/after images: the test read after pop_fbo without rebinding its targets. FrameBuffer.read samples the active framebuffer. No filter defect established. The corrected test binds each target for capture while retaining both draws before either read. Run601 cleaned17,901,713bytes/verified27inputs; exact failed source, captures and copied-console-message correction are retained. Corrected assertions remain pending; runtime/native/wheels unchanged.

**SCI-02/E03 pending-filter investigation started (2026-11-13):** new four-case source test covers texture replacement, enable toggling, plane-count mutation and detach after an earlier draw and before dependent captures. [Initial attempt](../compat/api-acceptance/mesh-filter-pending-setup-v1.json) fails all four cases at the test's unsupported RenderBuffer format string, before drawing; no renderer defect or pass is established. Exact failed test/logs and zero final gauges are retained. Corrected test uses public color format and fixture-scoped cleanup; its pending-draw assertions are not yet run. Run600 cleaned17,898,000bytes and verified24retained inputs. Native/runtime/wheels unchanged.

**SCI-05/HOST-06 H03 upstream disposition reconciled (2026-11-13):** [source-only evidence](../compat/api-acceptance/h03-upstream-disposition-v1.json) verifies the existing Windows CPython3.12.8/PyQt6/RTX4090 upstream0.17.0 admission, matching fixture/requirements/manifest hashes and corrected reference members. The public Glue FRB invalidation-before-update protocol has an admitted volume_edit reference; the original failed packet remains failed. H03's stale blanket upstream-blocked description is corrected, without transferring historical candidate results to source99719f1/current wheels. Current Glue application/strict host qualification stays open. Run599 exits0/awaited; no rendering, install, native build or scratch was created.

**U05 cleanup completed (2026-11-13; SCI-01/SCI-05):** the unrelated process holding reused PID21404 exited. The original child identity and strict cleanup guard stayed unchanged; [WSL U05 acceptance](../compat/api-acceptance/point-identity-current-linux-v1.json) remains scoped to source99719f1/wheelb728b575/patched Mesa9c5. Run598 cleanup now passes:30,007,097bytes reclaimed,594files removed and27retained inputs verified, including the first zero-delete refusal. No managed scratch remains from this packet. Both selected Windows/WSL point observations pass; broader layouts and qualification remain open.

**SCI-01/SCI-05 U05 WSL installed pass (2026-11-13; API-05/06, SHD-03 partial):** [exact Linux wheelb728b575 evidence](../compat/api-acceptance/point-identity-current-linux-v1.json), source99719f1 on CPython3.12.13/pinned patched Mesa9c5 software Vulkan, passes the same10unchanged tests as Windows: eight rendered cases match all6,144pixels exactly, with analytic/trace/provenance controls,537runtime members, installed origins, zero overlays and ten final zero gauges. Linux archive/RECORD metadata also verifies. This completes both selected local U05 platform observations, not broader point/layout support or strict/release admission. Run598 scratch cleanup is pending: the verifier refused because the awaited child PID21404 has been reused by an unrelated live PowerShell process. Zero files deleted; refusal and observed identity retained. Preserve the guard and wait for that PID to disappear before applying cleanup or starting the next experiment.

**SCI-01/SCI-05 U05 bounded installed pass (2026-11-13; API-05/06, SHD-03 partial):** [current Windows point identity evidence](../compat/api-acceptance/point-identity-current-windows-v1.json), exact source99719f1/wheel6de6d77f, passes10unchanged tests: eight rendered indexed-ID/divisor/constant/ordered-revision cases and two provenance/analytic controls. All6,144pixels match independent references and analytic expectations exactly; trace assertions pass,537runtime members/installed origins verify and ten final shutdown gauges are zero. Seven cases use public Program.draw; nonzero_first_queue is explicitly internal, and the large ID uses constant geometry/inactive count. This replaces U05's stale no-candidate description for this Windows subset only. Broader SCI-01, WSL point checks and strict/release admission stay open. Run597 cleaned18,038,310bytes and verified24retained inputs; no renderer/native change.

**Metal arm64 original verified (2026-11-13; TOOL-01, PLAT-04 experimental, FIX-04/06):** [original capture and cleanup](../compat/api-acceptance/lifecycle-metal-arm64-original-v1.json) verifies CI43495769632 arm64 at exact source99719f1: original archive/native/Mach-O/configuration, source-before/after, installed CPU controls and successful producer cleanup. All97original members are retained once by hash. Local run596 cleaned23,608,182bytes and verified113retained files. The same x86_64 job is still actively building; no restart, whole-run success, Metal graphics, production reuse-pin renewal, preparation10 or review/admission is claimed.

**Both current wheels pass local installed acceptance (2026-11-13; API-05/06, LIF-01–04, SCI-06, SHD-06/PLAT-08 partial, FIX-06):** [Windows6de6d77f](../compat/api-acceptance/lifecycle-current-windows-installed-v1.json) and [Linuxb728b575](../compat/api-acceptance/lifecycle-current-linux-installed-v1.json), exact source `99719f1…`, each pass26selected cases,56Tk baseline cases and composite recovery using one offline installation per platform with separate consumer processes. Each process verifies537runtime members, installed loaded origins, zero source overrides and ten zero shutdown gauges. Linux uses pinned patched Mesa9c5 and additionally verifies561archive members,566installer RECORD entries and its manylinux_2_39 tag. System-Mesa25.2.8 failure stays failed; hidden native controls do not broaden WSI or hardware scope. Runs593–595 cleaned47,766,619bytes and verified72retained inputs in total. Preparation10, independent review, strict-profile admission, final-head CI, merge and delivery remain pending; published wheels are unchanged.

**Current Windows wheel accepted locally (2026-11-13; API-05/06, LIF-01–04, SCI-06, FIX-06):** [exact installed evidence](../compat/api-acceptance/lifecycle-current-windows-installed-v1.json) records wheel `6de6d77f…` from source `99719f1…`: 26 selected tests, 56 Tk baseline tests and composite recovery pass in separate processes on one offline Windows installation. Each verifies 537 runtime members, loaded installed origins, zero source overlays and ten zero shutdown gauges. This closes the current Windows local installed-check packet, not strict qualification, review, merge or delivery. WSL wheel `b728b575…` remains pending. Run593 packaging cleanup removed92bytes/verified15inputs; run594 removed17,898,008bytes/verified28inputs. The source-list preparation NameError is retained; no consumer ran on that failed preparation.

**Active plan refreshed (2026-11-13; API-05/06, LIF-01–07, SCI-01–06, SHD/STA/TEX/LIN, FIX-04/06):** follow the [revised investigation and closure order](superpowers/plans/2026-11-13-remaining-gap-closure.md#revised-investigation-and-closure-order--2026-11-13). Corrected source is pushed at `99719f1…`; [current Windows6de6d77f/Linuxb728b575 archives](../compat/api-acceptance/lifecycle-qt-repackage-v1.json) exist, but their installed acceptance and preparation10/review/CI/integration remain pending. Finish run593 cleanup first; then exact-wheel acceptance, final bindings and integration, stale-route reconciliation, selected lifecycle/scientific/rendering investigations, and optional breadth only for a concrete claim. Metal status must be refreshed from the existing run. This is a planning update: no test, cleanup, approval, closed capability or release claim is added; the published baseline and historical evidence are unchanged.

Latest source correction, 2026-11-13: [review588 requires changes](../compat/api-acceptance/lifecycle-cumulative-review-required-v1.json), with no source/scope/reuse approvals. Hidden native QWidget close and duplicate user resize callbacks are fixed at source scope: [57CPU passes](../compat/api-acceptance/qt-close-state-review-source-v1.json), [26Windows](../compat/api-acceptance/qt-close-state-windows-source-v1.json) and [26WSL source passes](../compat/api-acceptance/qt-close-state-wsl-source-v1.json), including explicit native/readback hidden close and independent pending-DELETE cases. Layout refusal cleanup and extra clear controls are covered. No native rebuild; old wheel/preparation9 evidence stays at its original bytes. Next: update CI selectors before new source/hash freeze, then repackaging, preparation and review. Top-level PyQt6 observations do not establish embedded-parent or other-binding coverage. Runs588–591 cleaned (37,687,548bytes); the intermediate refactor abort remains recorded.

Current binding checkpoint, 2026-11-13: [both native producer proofs and Windows archive prerequisite validate against preparation9](../compat/api-acceptance/lifecycle-producer-bindings-wip-v1.json); missing reviews still block admission. [Linux auditwheel/tag/archive prerequisite passes](../compat/api-acceptance/lifecycle-linux-manylinux-archive-v1.json), with only WHEEL/RECORD changed. Exact manylinux wheel30a40dcb now [passes21selected+56baseline tests and composite recovery on one matched-driver installation](../compat/api-acceptance/lifecycle-linux-manylinux-installed-v1.json), with runtime/metadata/installer RECORD checks and zero gauges. No approvals, strict profiles, CI selection, merge or release transferred. Runs585–587 are cleaned (52,668,442bytes reclaimed); review and final-head integration gates remain next.

Preparation checkpoint, 2026-11-13: [new unreviewed revision9 validates](../compat/api-acceptance/lifecycle-preparation9-wip-v1.json), conserving128selected criteria,142original obligations and260unchanged historical records. Fresh Windows and matched patched-Mesa Linux wheels each pass56baseline Tk tests plus composite recovery; [system Mesa25.2.8 still fails one MSAA capture case](../compat/api-acceptance/lifecycle-linux-system-mesa-msaa-failure-v1.json). This keeps LIF-05/SHD-06/PLAT-08 driver scopes distinct. Reviews/producer/archive bindings, current CI selection and final-head integration remain pending; no admission or delivery. Runs580–584 scratch is cleaned (105,929,160bytes reclaimed).

Latest installed checkpoint, 2026-11-13: [Linux8a793196 passes21selected installed tests](../compat/api-acceptance/lifecycle-linux-installed-selected-v1.json), matching the Windows test selection on sourcef93d80b. Linux verifies537members,57loaded origins,zero source overlays and ten zero shutdown gauges. Native bytes are reused; only the Python wrapper member is repackaged. Both are local candidate observations; formal reviews/profile qualification, required-head CI, merge and delivery remain pending. Run579 scratch cleaned (29,081,532bytes,26retained inputs rehashed); the initial zero-delete live-PID cleanup refusal remains recorded separately from its successful unchanged-plan follow-up.

Current package checkpoint, 2026-11-13: [owned sourcef93d80b pushed](../compat/api-acceptance/lifecycle-owned-source-head-v1.json); [21 Windows installed tests pass](../compat/api-acceptance/lifecycle-windows-installed-selected-v1.json) on candidate977357ad with537verified members,58loaded origins,zero overlays and ten zero shutdown gauges. Earlier native-presentation profile mismatch remains a retained failed attempt; the identical wheel passes explicit readback. No native rebuild, merge or release. Runs576–578 are cleaned (75,535,236 bytes). Next: Linux installed acceptance and formal candidate/CI/integration gates; broader capability parents remain open.

SCI-06 source investigation, 2026-11-13: [eight Windows](../compat/api-acceptance/stencil-public-routes-source-v1.json) and [eight WSL software-Vulkan](../compat/api-acceptance/stencil-public-routes-wsl-source-v1.json) cases pass. Four public stencil forms return exact reference values/crops/types and mutate; four raw calls are explicitly refused and recover through the wrapper. All cases assert nine zero gauges. [Disposition](stencil-wrapper-disposition.md) preserves all eight stock failures without treating them as eight Vulkan defects. Renderer unchanged; installed acceptance remains pending. Minor protocol-test review follow-up also passes90contracts. Both runs are cleaned (45,498,943 bytes reclaimed); managed scratch is empty.

Latest completed gates, 2026-11-13: [90 source contracts](../compat/api-acceptance/linux-protocol-contracts-source-v1.json), [independent protocol review](../compat/api-acceptance/linux-protocol-peer-source-v1.json), [original Linux native/archive proof](../compat/api-acceptance/linux-original-native-archive-v1.json), and [13 current WSL source passes](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json). This advances API-05/06, LIF-01–04 and SCI-06 for the exact selected software-Vulkan profile; parents stay open. No installed successor or release admission. Runs570–573 are cleaned, reclaiming32,221,412 bytes; all managed scratch is empty. Earlier pending/failure notes retain their historical scope. Next are the minor review follow-up, owned-source integration and installed qualification, plus separate investigation of broader public-wrapper gaps.

Latest source gate, 2026-11-13: [90 Linux validation contracts pass](../compat/api-acceptance/linux-protocol-contracts-source-v1.json), including the actual review gate on a consistent minimal source fixture and exact changed-tool refusal. Run570 cleanup reclaimed7,811,625 bytes and rehashed seven retained files. Earlier failing runs remain historical. Review and original retained-capture validation are next; no Linux runtime/installed coverage is promoted.

Protocol source follow-up, 2026-11-13: [88 contract passes / one retained failure](../compat/api-acceptance/linux-protocol-contracts-wip-v1.json). The positive workflow fixture now renews its CI identity consistently. Next repair the historical review-gate fixture's source/tool scope without bypassing the real validator, then obtain review and validate the original retained Linux capture. No artifact admission or new runtime pass is claimed. Run569 scratch is now cleaned: 16,886,403 bytes reclaimed, 13 retained files rehashed.

Planning checkpoint, 2026-11-13: follow the [active investigation queue](superpowers/plans/2026-11-13-remaining-gap-closure.md#active-investigation-queue--2026-11-13) before the older phase order below. First resolve two run569 contract failures (87 pass), review bounded protocol support and validate the retained Linux artifact; then run selected WSL cases, investigate the eight public-wrapper failures and stale fixtures, and select further lifecycle/scientific/rendering cases. Run569 scratch cleanup is pending; earlier all-clean statements predate it. This is a documentation-only plan update, with no new pass, closed capability, artifact admission or release claim. Source, installed and delivered coverage remain distinct.

Latest Linux status: fresh CI43471568101 passed and all166original artifact members are retained. [The native verifier's exact workflow-authority refusal is preserved](../compat/api-acceptance/qt-linux-protocol-equivalence-v1.json): only an inactive reuse-arm candidate selector differs, with fresh producer code byte-identical. Review/implement bounded authority support, then validate the original capture and run WSL cases; no new native build is needed. No Linux source-runtime or installed qualification is promoted from a green CI job alone. All local scratch is cleaned.

Linux renewal is now [actually dispatched on isolated source head82ee](../compat/api-acceptance/qt-lifecycle-source-ci-v1.json), run43471568101. Wait for the existing fresh producer and then test its exact native artifact under WSL; do not rerun Windows compilation or treat queued/running CI as qualification. The published release remains unchanged.

Current native follow-up: [44native CTests and3Windows Vulkan source cases pass](../compat/api-acceptance/qt-lifecycle-windows-native-v1.json). The parsed-DELETE retirement defect is resolved on the rebuilt Windows leaf: live and pending-snapshot shared-peer cases both render exact pixels and end with all nine zero gauges. Build and GPU scratch is cleaned. Linux native renewal, successor installed qualification and broader lifecycle boundaries remain open.

Latest follow-up: [53CPU checks pass](../compat/api-acceptance/qt-lifecycle-review-followup-v1.json), including first-show initialize/resize ordering and pending callback-error identity. Independent review accepts the native parsed-DELETE cleanup for bounded compilation; it is not yet compiled. The pending peer-snapshot GPU test is added, not passed. Keep native/installed, embedded-parent, actual loss and broader lifecycle items open.

Post-release source work is in progress: [native-close/shared-context CPU follow-up](../compat/api-acceptance/qt-lifecycle-source-followup-v1.json) passes50cases. Windows GPU shared-peer recovery renders correctly but exposes24CPU/GPU-buffer bytes retained after explicit deletion/last close; the pending-DELETE cleanup patch is uncompiled and under review. This updates API-05/LIF-01–04 partially; it does not extend the published wheel's claims or close the parents.

Next work is organized in the [remaining-gap investigation and closure plan](superpowers/plans/2026-11-13-remaining-gap-closure.md): bounded startup diagnosis, lifecycle reliability, selected scientific workflows, then rendering breadth. Planning does not change any open coverage status or require full parity.

The selected `0.17.0+vulkan.2` release is published and its public delivery checks pass. [GitHub Release](https://github.com/bipxx/vispy_vulkan/releases/tag/v0.17.0-vulkan.2), [PEP503 index](https://bipxx.github.io/vispy_vulkan/simple/), [exact delivery evidence](../compat/api-acceptance/successor-public-delivery-v1.json).

- **FIX-04 — Integrated:** PR75 merged as `fc3b9734bbaf2af801e7b3bc81bbc352e5525708` after all eleven protected integration checks passed. Its tree preserves the qualified runtime, tools, workflows and policies; the other owner's index is unchanged.
- **FIX-06 — Qualified and delivered:** all 128 selected Tk criteria, eight mandatory VisPy-only Windows/WSL profiles, all 23 required jobs at implementation head `3ada644e85248bcae214e7e487b4b1684336fd8f`, independent final promotion and strict admission pass. Product source remains `b38c4f9068d6a425eef43b62313f0f4cf37f57d9` and the two exact wheels are unchanged. [Admission](../compat/api-acceptance/revision8-final-admission-v1.json).
- **Actual public channel:** Windows verifies 537 members, zero source overrides and an exact 64×64 Vulkan clear. Linux verifies 537 members, zero source overrides and native ABI import; its delivery smoke makes no new GPU claim. The four-link index preserves both vulkan.1 assets. AGPL, original BSD and dependency notices remain attached.
- **Hygiene and failures:** temporary installs are removed; 167,250,056 bytes reclaimed and 44 retained files rehashed. The draft lookup 404, connector 403 and Linux receipt collision remain recorded with their recoveries. The 18 legacy inputs remain protected at original origins; the manually reviewed mandatory retention boundary and its unchanged generic-verifier refusal are preserved separately from the Tk 599-input verified retention.

This closes the selected successor release, not all 142 broader compatibility obligations. Optional API/rendering/host/platform breadth remains explicitly tracked below. Metal graphics, physical Linux GPUs, other ABIs/architectures, full API/raster parity and laboratory latency remain outside the accepted release claim. See the [completion audit](selected-release-completion-audit.md).

## Historical progress checkpoints

These checkpoints retain their original source, artifact and review scope; the current status above supersedes their pending-work descriptions.

Metal reuse dependency fix (2026-11-13; TOOL-01 / FIX-04): arm64 CI reached repackaging but lacked the pure Python version validator `packaging`. An isolated no-site probe reproduces the failure; the existing129,956-byte locked packaging26.3wheel fixes it. The reuse workflow now exports/installs only that dependency, preserving hashed installation and the1GiB reuse budget. [Evidence](../compat/api-acceptance/metal-reuse-dependency-fix-v1.json). No wheel/SDK rebuild or new venv. All608runtime references remain unchanged. Successor preparation/policy renewal, independent reviews, CI and promotion remain pending; old reviewed records stay frozen. No admission.

Oracle-provenance head (2026-11-13; FIX-04): corrected test pushed as `4c39ff7f4d3b51c1a9f4c52475924f9c1a781b27`; the original capture producer is confirmed tracked byte-exact, all608runtime references and the other owner's index unchanged. Required reuse CI dispatched: CPU43404591396, Linux43404594197, Metal43404597011. [Freeze and CI evidence](../compat/api-acceptance/oracle-provenance-head-v1.json). The existing128-criterion subject proof remains scoped to head9cf; final-head renewal, independent follow-up/impact/promotion review and CI completion remain open. No admission.

Oracle comment correction (2026-11-13; FIX-04): independent review confirmed the provenance assertions preserve acceptance, but requested a comment correction. The actual collector change is candidate-version resolution; historical failure handling was already present. Corrected bytes pass18checks and have an identical executable AST to the512-case passing version. The exact-byte follow-up failed authentication (403), not a test or approval decision; no approval transferred. [Evidence](../compat/api-acceptance/frozen-oracle-comment-followup-v1.json). Branch CI may proceed; independent follow-up/final impact review and promotion remain pending.

Hosted CPU failure isolated (2026-11-13; FIX-04): Linux/macOS final-step logs show one historical oracle producer-hash mismatch (508 passes). The reference check now binds the existing byte-exact frozen capture authoring source rather than the newer live collector; all original oracle/provenance bytes remain unchanged. Eighteen reference checks, including three relabelling/source-tampering controls, and the full 512-case final CPU group pass locally on Windows CPython3.12.8. [Evidence](../compat/api-acceptance/frozen-oracle-producer-fix-v1.json). All 608 runtime references and candidate preparation tools remain unchanged; independent test-delta review and new-head CI remain pending. No artifact admitted.

Installed subject proof (2026-11-13; FIX-04): all 128 selected criteria prove end to end with zero missing or blocked joins, using the original native/archive/strict installed reports, six-attempt histories, reviewed failure disposition and 601-input contributing retention. [Evidence and reconstruction](../compat/api-acceptance/installed-subject-proof-v1.json). The temporary overlay was validated and the frozen preparation restored byte for byte. No artifact admitted. Head9cf Linux Vulkan reuse passed; the CPU matrix has failures in its final assertion step, still under diagnosis. Required CI completion, independent impact/promotion review and integration remain open. The 142 broader original requirements remain conserved, not claimed complete.

Installed bindings (2026-11-13; FIX-04): all 32 selected feature/profile rows validate against the two exact matched environment fingerprints, including 128 criteria and 96 raw gate joins. Thirty-two source-local receipts and two derived distribution audits are linked through a small reconstructible overlay; the frozen preparation ledger is unchanged. [Evidence](../compat/api-acceptance/installed-proof-bindings-v1.json). Separate same-wheel installed pytest phases retain their own scope. Original 142 requirements remain incomplete. Contributing retention, final subject/proof review, head CI and promotion remain open; no artifact admitted.

Qualification head (2026-11-13; FIX-04): reviewed source pushed as `9cf488acdae59ae3b80310ab2a19b5bcc4915a54`; all 608 runtime/build/lock/license references and the other owner's Git index remain unchanged. The 23 required jobs are dispatched at that exact head in native reuse mode (CPU43400135712, Linux43400153578, Metal43400158627). [Freeze and CI evidence](../compat/api-acceptance/qualification-reuse-head-v1.json). CI completion, final installed proof bindings and promotion remain pending; no artifact admitted.

Independent review (2026-11-13; FIX-04 / TOOL-01): revision7 source and finite scope are independently approved, including native CI reuse. The Windows receipt-refresh failure has an approved disposition and remains failed/UNVERIFIED in its complete history; the flagged inventory files are byte-identical. The fully reviewed Linux reuse path and original driver now validate, with zero Python reassembly changes. [Decision and exact bindings](../compat/api-acceptance/successor-peer-review-v4.json). Final installed bindings, frozen-head 23-job CI and promotion remain pending; no artifact admitted.

CI reuse repair (2026-11-13; TOOL-01 / FIX-04, source-tested): 1,117 compatibility contracts pass on Windows CPython 3.12.8. The three successful head340 native artifacts validate against current inputs and are pinned for reuse; Metal dispatch/managed-layout checks and reviewed-successor Linux selection have 116 focused passes. CPU event values now run after compilation. Transport cleanup removed 92,206,020 bytes and rehashed 286 retained files. [Evidence](../compat/api-acceptance/native-ci-reuse-repair-v1.json). Revision7 remains unreviewed; source-head CI, final installed bindings and promotion are pending. No native rebuild or artifact admission.

Exact-profile histories (2026-11-13): scan of15,217retained JSON files finds
6strict attempts for the selected wheels, exact matched fingerprints and candidate
workflows, with0unattributed current-wheel reports. Four latest workflow selections
and3contributing retention envelopes validate (62/94/80retained inputs).
[Evidence](../compat/api-acceptance/matched-profile-histories-wip-v1.json). One Windows UNVERIFIED receipt-refresh attempt
still needs independent disposition. Historical variants/other workflows stay
disclosed. Profile/receipt bindings, producer retention, review/CI and promotion
remain pending; no row or artifact admitted.


Matched WSL cohort (2026-11-13): state/failure and capture pass strict replay
in one identical consumer fingerprint, with537verified members, zero overlays
and9zero gauges. All16feature joins/48gate checks validate ([evidence](../compat/api-acceptance/wsl-matched-cohort-v1.json)).
Both platforms now have matched pairs (32joins/96checks) without collapsing
the old mismatched environments. Existing Python/driver/dependency sources were
borrowed read-only; no wheel/SDK build. Final profile/receipt/history/retention
bindings, revised review, head CI and promotion remain pending; no admission.


Matched Windows cohort (2026-11-13): state/failure and capture both pass strict
three-gate replay in one identical consumer fingerprint, with537verified members,
zero overrides and9zero shutdown gauges. All16Windows feature joins/48gate
checks validate ([evidence](../compat/api-acceptance/windows-matched-cohort-v1.json)). The intermediate unverified
receipt-refresh attempt is preserved. The original handle baseline remains in
place; its exact bytes/origin are retained in a small input archive. No SDK or
wheel was rebuilt, and no row admitted. WSL matching, final profile/history/
retention bindings, source/scope review, required CI and promotion remain open.


Provisional installed joins (2026-11-13): all32feature/profile pairs validate
three original observer gates and their installed pytest fixtures (96gate checks,
4original bundles). [Evidence](../compat/api-acceptance/installed-proof-joins-wip-v1.json). No rows/profiles admitted:
Windows state/capture use builds26200/26300; WSL kernels6.18.54/6.18.58 differ and
capture has5extra Python distributions. Replay each pair in one matched consumer
per platform rather than collapse distinct fingerprints. Raw reports and both
existing byte-identical inventory origins remain untouched. Complete histories,
retention, final profile/receipt bindings, review/CI and promotion stay pending.


Current-preparation verification (2026-11-13): all1,088 compatibility-contract
cases pass locally on WindowsCPython3.12.8 with the new fixture resolving the
explicit revision7CI selection. [Evidence](../compat/api-acceptance/current-preparation-contracts-v1.json). Historical
default refusal and strict review/scope controls remain intact; revision7
approvals, source-head CI and installed proof joins remain pending.


Compiler follow-up (2026-11-13): the existing CMake/MSVC profile passes the
real CPU cache shutdown-wrapper contract. Configure, build and executable exits
are0 and awaited; sources, commands and licenses are retained under a128MiB
managed lease ([evidence](../compat/api-acceptance/upload-shutdown-compiler-v1.json)). This closes run499s local
missing-PATH/compiler check; its902source passes and this1native pass remain
separate receipts. No installed graphics/native artifact qualification is claimed.
Revision7review, current-preparation contracts and hosted CI are still pending.


CI source grouping repair (2026-11-13): six benchmark files now run in a
separate provider-free process; all434cases pass with the strict import guard
unchanged. Scientific/event selection has902passes and1 local compiler-profile
setup failure (existing CMake is not on PATH). CPU event values are explicitly
classified in CI. Test fixtures resolve the explicit CI preparation rather than
hardcode a historical revision. Revision7preparation/128closure validates with
all164prior candidate records unchanged; independent revised approvals and
compatibility rerun are pending. [Partial evidence](../compat/api-acceptance/ci-source-grouping-repair-wip-v1.json).
The compiler contract needs managed existing-toolchain verification before a
full scientific pass claim; no runtime, wheel or artifact admission changed.


Hosted CI grouping findings (2026-11-13): corrected head340499b0 passes the
compatibility step on observed LinuxCPython3.10.19, then reports1,305 scientific
passes,2 failures and1 teardown error. Metrics import-isolation guards share a
process with legitimate provider-import tests; test_event_values is missing
from CI classification. [Failure evidence](../compat/api-acceptance/qualification-ci-grouping-failure-v1.json). Split those
processes, keep import guards, add CPU event fixtures and renew affected pins.
Native fresh builds are ongoing; no admission is claimed.


Corrected qualification head (2026-11-13): `340499b0ff81ca12dddf04b763477c93737fde89`
is frozen, pushed and bound by the detached subject. All23 required jobs are
dispatched on this exact head; Linux and experimental Metal use their existing
explicit fresh6GiB production profiles because original native inputs differ.
[Head, requests and run identities](../compat/api-acceptance/qualification-ci-correction-v1.json). Only tests, docs and
evidence changed since `152183d0…`; reviewed tools, candidate scope, all608 runtime
references and selected wheels are unchanged. Local WindowsCPU selection passes
1,088 cases; hosted results, installed proof joins and promotion remain pending.
Earlier failed-head evidence is preserved and does not qualify the corrected head.


CI fixture repairs (2026-11-13): the full compatibility-contract file selection
from the CPU workflow passes 1,088 cases locally on WindowsCPython3.12.8.
Current selection/review-gate/capture tests use revision6; frozen defaults retain
an explicit stale-tool refusal. Metal synthetic metadata declares project/version.
Capture corruption cases have a positive control first. All164 candidate JSON
records, validators and runtime bytes are unchanged. [Evidence](../compat/api-acceptance/ci-contract-fixture-fixes-v1.json).
The first focused run retained312passes/1missed old-runtime failure before its
correction. Hosted validation on the corrected head remains pending; fresh Linux
and experimental Metal production decisions are recorded separately.


Linux CI reuse disposition (2026-11-13): hash-verified artifact diagnostics
confirm the guard correctly refuses changed `cpp/runtime.cpp` bytes. The next
corrected source head will use the existing explicit `native_mode=fresh` route
(6GiB declared peak, managed lifecycle), not alter historical pins or relax reuse.
[Changed-input decision](../compat/api-acceptance/linux-ci-fresh-decision-v1.json). This is hosted source-head CI;
selected local wheels and their native producers remain unchanged. Fresh CI
execution and source-head success are still pending.


Required head CI findings (2026-11-13): Linux CPython3.12.8 reports 1,078
contract passes and 16 failures: nine stale candidate expectations, six incomplete
Metal metadata fixtures and one native-input pin expectation. Software Vulkan
also fails in original-native reuse; its retained child details need inspection.
[Failure evidence](../compat/api-acceptance/qualification-ci-failures-v1.json). Other jobs are still pending in this
snapshot. These failures block required CI; no job or validator is waived.


Required qualification CI dispatch (2026-11-13): reviewed head `152183d0…` was
pushed to `wip/qualification-reviewed-492`; all three policy workflows are
authoritatively queued/running with exact head and attempt identities retained
([runs](../compat/api-acceptance/qualification-head-ci-wip-v1.json)). All 23 jobs remain required. Dispatch is not a
passing CI result or artifact admission; preserve failures and rerun histories.


Qualification implementation freeze (2026-11-13): `152183d0e3d737bf036d0baad2c0981ab6fe981c`
binds 5,924 source files, including the reviewed tools, CI workflows, named tests
and qualification collector. All 608 runtime/build/lock/license references retain
product source `b38c4f9068d6a425eef43b62313f0f4cf37f57d9`. The subject is
now bound to this head as a detached local proof overlay. [Evidence](../compat/api-acceptance/qualification-source-freeze-v1.json).
The other checkout/index was preserved; only a private index was used. Initial
Windows argv-limit verification failure is retained; bounded-prefix verification
passes against the existing commit. Required hosted CI and installed proof joins
remain pending; no artifact is admitted.


Revision6 source/scope review (2026-11-13): independent decisions are approved
and bound to candidate, coverage, execution, admission closure and both native
reuse digests. [Decision](../compat/api-acceptance/successor-peer-review-v3.json). All four preparation validators
require and pass the new reviews; both original native producer joins validate.
Scope digests, runtime, fixtures and wheels are unchanged. No installed rows or
artifacts are admitted. Qualification Git head, installed receipt/history/retention
bindings, required hosted CI and promotion remain open.


Installed criterion receipt update (2026-11-13): both exact mapped pytest fixtures
pass on each selected Windows/WSL wheel, with all six setup/call/teardown events
per platform, 537 member checks, zero source overrides and zero shutdown gauges.
[Evidence](../compat/api-acceptance/installed-criterion-phases-v1.json). These fresh phase receipts close the missing
pytest-report format; qualified row/retention joins remain pending.


### Historical preparation — revision6 (2026-11-13)

`tk-state-resource-6` renews the independently approved qualification-tool
identities. Its 64 criteria / 128 profile bindings and prerequisite closure
validate; all earlier candidate records and 608 runtime/build/lock/license
references remain byte-exact. CI now explicitly selects revision6, validates
its admission selection and runs retained-evidence tests. All 23 required
jobs remain required. Five preparation CLIs pass locally; CI/retention
contracts pass 102 cases. [Evidence](../compat/api-acceptance/qualification-candidate-renewal-v1.json).

This is an **unreviewed preparation**, not installed or release qualification.
The subject now declares the store selector; producer references await new
candidate source/scope decisions. Qualification Git head, complete installed
histories/receipts/retention, required hosted CI and promotion remain open.
No native build, installation, artifact admission or new scratch occurred.
The earlier checkpoints below retain their original date and byte scope.



### Qualification-tool follow-up — 2026-11-13

Independent follow-up approves the exact eight tool/schema/test hashes for candidate
renewal only ([decision](../compat/api-acceptance/qualification-tools-followup-v1.json)). Coordinator rehashed those bytes; the review child
exited 0 and was awaited. Prior 372 contract passes and 6 focused passes remain
source evidence; no wheels were rebuilt or admitted. Renewed candidate/source/scope
bindings, the subject store selector, complete installed histories/receipts and
real producer retention remain pending. CI must select the renewed preparation
records **and run `tests/contract/test_retained_evidence.py`**, then renew its
workflow policy hash. No required job is waived. Low review limits (Windows
transitive retention, early-failure attribution and incremental failure reporting)
are recorded in the decision; they are not broader coverage claims.

Reviewed **2026-11-13** against local source, the
[coverage checklist](coverage-checklist.md), acceptance manifests and the
[consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md).
This is the concise execution view; those records retain detailed evidence and
stable IDs. An unchecked item can mean missing verification or disposition,
not necessarily missing implementation. Exact test scopes are linked below.

The [coverage gap review](coverage-gap-review-2026-11-08.md) identified three
current-wheel refresh needs. They are now closed: 57 event, 39 Tk input and
30 depth cases pass per platform on the latest wheels, with original cases and
source pins preserved. [Fresh exact-artifact evidence](../compat/api-acceptance/current-event-input-depth-v1.json)
is separate from the unchanged older results. The 32 literal-sampler cases are
also already included in current passing suites. Independent review and
installed/profile qualification remain the next release work.

The target remains practical VisPy compatibility. Full upstream parity, exact
OpenGL rasterization and laboratory display-latency parity are not required.
Optional scope below does not become a release requirement by appearing here.

## Current baseline

- Published release: `v0.17.0-vulkan.1`. Its approvals retain their original scope.
- Selected experimental successor: `0.17.0+vulkan.2`, Windows wheel `a86b030b…`
  and Linux wheel `48164e05…`, with current Tk, both headless, all three Windows Qt and all three WSL Qt observations.
- Earlier successor wheels `ba8a54c5…` / `4bc3cd77…` retain 75 sampler cases, 120 numeric
  uniform-array cases, and 285 attribute cases per platform across separate
  retained runs. These are finite suites, not exhaustive API coverage.
- See [samplers](../compat/api-acceptance/dynamic-explicit-samplers-wip.json),
  [uniforms](../compat/api-acceptance/uniform-arrays-v1.json) and
  [attributes](../compat/api-acceptance/attributes-v1.json) for exact hashes,
  values, platforms, failures and cleanup. Local functional passes do not
  supply successor review, strict-profile admission or release approval.

## Latest closed bounded task

- [x] **FIX-06-NATIVE-JOIN (2026-11-13):** original Windows402 and Linux414
  producer joins validated against the reviewed revision-5 records; both producer
  references were bound to the subject before the qualification-tool change.
  [Evidence](../compat/api-acceptance/qualification-binding-wip-v1.json). No artifact admission.
- [x] **FIX-06-WORKFLOW-ATTEMPT-SOURCE (2026-11-13):** optional per-workflow
  latest-success selection is implemented, preserving legacy subjects. Nine new
  selection/integration cases reject stale failures, omitted/duplicate workflows,
  incomplete histories and swapped runtime reports; 52 focused contract cases pass.
  Full-file run also retains one stale historical preparation-toolset failure.
  This is source-tested qualification tooling, not installed-wheel admission.
- [x] **FIX-06-EVIDENCE-ADAPTER-SOURCE (2026-11-13):** explicit secondary-store
  raw report references and mixed-root retention are implemented. Both original
  WSL state/resource and capture reports normalize all three gates. The original
  WSL cleanup validates all 80 inputs, including four exact archived documents.
  Source-local checks and all original report bytes remain intact.
  [Evidence](../compat/api-acceptance/secondary-evidence-adapter-wip-v1.json).
  Broad contracts: 344 pass; archive follow-up: 99 pass; final opt-in guard: 2 pass.
  Frozen-record tests retain scope and now reject stale current-tool claims.
  These are source-tool and retained-evidence joins, not artifact admission.
- [x] **FIX-06-EVIDENCE-BINDINGS (2026-11-13):** finite revision8 Tk subject binds complete six-attempt histories, separate installed pytest phases, distribution receipts and599-input contributing retention for the selected wheels. [Exact128-criterion proof](../compat/api-acceptance/revision8-installed-subject-v1.json). No full inventory or release admission.
- [x] **FIX-06-TOOL-REVIEW-FIXES-SOURCE (2026-11-13):** resolved-failure
  profile/wheel context, native/store namespaces and source-side scratch handling
  are fixed. Early failures have history-bound workflow attribution; derived
  cleanup views are checked against original process/result bytes. Full source
  contracts pass 372 cases; exact error follow-up passes 6. Both WSL reports and
  the 80-input cleanup still validate; native input joins check 245 Windows and
  167 Linux references. [Fix evidence](../compat/api-acceptance/qualification-tool-fixes-wip-v1.json).
- [x] **FIX-06-TOOL-FOLLOWUP-REVIEW (2026-11-13):** independent review approves
  the exact eight tool/schema/test hashes for candidate renewal only. Coordinator
  rehashed them. [Decision](../compat/api-acceptance/qualification-tools-followup-v1.json).
  Run486 remains authoritative for its old hashes; candidate reviews are pending.
- [x] **FIX-06-CI-PREPARATION-WIRING (2026-11-13):** CPU workflow explicitly
  validates revision6 preparation, coverage, execution and admission selection;
  retained-evidence tests are included and exact policy hash renewed. Five CLIs
  pass locally, 102 CI/retention contracts pass; all 23 required jobs are preserved.
- [x] **FIX-06-CI-EVIDENCE-DELIVERY (2026-11-13):** all23required jobs at head3ada validate against complete original history/run/jobs/checkout identities. [Evidence](../compat/api-acceptance/revision8-required-ci-v1.json). Independent final promotion and strict admission remain separate.
- [x] **FIX-06-QUALIFICATION-TOOL-REVIEW (2026-11-13):** exact tool follow-up
  and renewed revision6 source/scope decisions approved; new candidate identities
  and native joins validate. Revision5 approvals retain their original scope.
- [x] **FIX-06-INSTALLED-PYTEST-PHASES (2026-11-13):** both mapped fixtures pass
  on each selected wheel with complete setup/call/teardown records; 537 members
  verified, zero source overrides and shutdown gauges. [Receipts](../compat/api-acceptance/installed-criterion-phases-v1.json).
- [x] **FIX-06-QUALIFICATION-HEAD (2026-11-13):** isolated commit `152183d0…`
  freezes tools, CI and tests; 5,924 source-file blobs verified, 608 runtime refs
  unchanged, original index preserved. Subject head bound; hosted CI still pending.
  [Freeze evidence](../compat/api-acceptance/qualification-source-freeze-v1.json).
- [x] **FIX-06-INSTALLED-ROW-JOINS (2026-11-13):** all32selected Tk rows/96raw gate joins and128criteria prove at head3ada, using exact matched platform fingerprints and complete retained histories. [Proof](../compat/api-acceptance/revision8-installed-subject-v1.json). Eight mandatory matrix observations and final admission remain separately scoped.

- [x] **FIX-06-REVIEW-SCOPE-REPAIR:** merged capture into
  `tk-state-resource-5` with an enforced current-target prerequisite chain;
  corrected the four textured-program values and proposal; explicitly excluded
  experimental native presentation. Existing validators pass all 128 criteria
  with closure 128 and both archive prerequisites. Runtime/fixtures/wheels and
  all earlier candidate records are unchanged. [Scope repair](../compat/api-acceptance/tk-scope-repair-v1.json).
- [x] **FIX-06-REVISED-REVIEW (2026-11-13):** independent source and scope
  decisions are approved and bound to `tk-state-resource-5`. Candidate, coverage,
  execution and 128-criterion selection pass their review-required verifiers.
  Scope hashes are unchanged; no artifact is admitted. [Review evidence](../compat/api-acceptance/successor-peer-review-v2.json).
- [x] **FIX-06-CAPTURE-REBIND-WINDOWS (2026-11-13):** reviewed five-feature
  capture recipe passes fresh three-gate replay on wheel `a86b030b…`; same-child
  `tk-capture-1` validates all four branches, 537 members and nine zero counters.
  [Evidence](../compat/api-acceptance/tk-capture-rebind-windows-v1.json). No admission.
- [x] **FIX-06-CAPTURE-REBIND-WSL (2026-11-13):** reviewed five-feature
  capture recipe passes fresh three-gate replay on wheel `48164e05…`; same-child
  `tk-capture-1` validates all four branches, 537 members and nine zero counters.
  [Evidence](../compat/api-acceptance/tk-capture-rebind-wsl-v1.json).
- [x] **FIX-06-CAPTURE-REBIND:** both reviewed platform recipes now pass.
  The earlier WSL Drvfs setup failure is retained and cleaned; bounded POSIX
  temporary storage and borrowed read-only dependencies resolved the installer
  filesystem issue. Observations still need execution-attempt/subject bindings.

- [x] **FIX-06-WSL-PYSIDE6-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. Dependencies
  were borrowed read-only, with only the selected wheel in a private bounded overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyside6-v2.json). **All eight host-row observations collected.** Independent
  review and formal admission remain pending.

- [x] **FIX-06-WSL-PYQT6-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. The retained
  PyQt6 dependencies were borrowed read-only, with a private selected-wheel overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyqt6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WSL-PYQT5-OBSERVATION:** the selected Linux wheel passes
  all seven unmodified plain-QWidget stages on pinned software Vulkan, including
  capture/update ownership, overlays/input, resize/hide/restore, device recovery
  and close. Installed inventory and fresh replay pass all three graphics gates;
  537 package members and nine zero shutdown counters are verified. Dependencies
  were borrowed read-only; only the selected wheel used a private bounded overlay.
  [Evidence](../compat/api-acceptance/mandatory-wsl-pyqt5-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYSIDE6-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget stages, including rendering/capture ownership,
  parent/show/resize, overlays and input, hide/restore, device recovery and close.
  Installed inventory and fresh replay pass all three graphics gates; 537 package
  members and nine zero shutdown gauges are verified. Retained selected Qt wheels
  were installed offline without native builds.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyside6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYQT6-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget stages, including rendering/capture ownership,
  parent/show/resize, overlays and input, hide/restore, device recovery and close.
  Installed inventory and fresh replay pass all three graphics gates; 537 package
  members and nine zero shutdown gauges are verified. Retained selected Qt wheels
  were installed offline without native builds.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyqt6-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WINDOWS-PYQT5-OBSERVATION:** the selected Windows wheel passes
  all seven plain-QWidget probe stages: exact installed payload and Vulkan device,
  parent/show/resize, capture/update ownership, overlays and input, hide/restore,
  device-loss recovery and close. Installed inventory and a fresh replay pass all
  three graphics gates; 537 members and nine zero shutdown gauges are verified.
  The retained selected Qt profile is installed offline without a native build.
  [Evidence](../compat/api-acceptance/mandatory-windows-pyqt5-v2.json). **All eight host-row observations collected.** Independent review and formal admission remain pending.

- [x] **FIX-06-WSL-HEADLESS-OBSERVATION:** the Linux wheel passes 95 GPU tests,
  rendering/compiled text, 4,096 markers and 36 scientific cases on pinned
  software Vulkan. Installed inventory and fresh replay pass all three gates,
  with 537 members verified. Dependencies are reused read-only, with only the
  selected wheel installed into a private overlay. The original pytest capture
  failure is retained; bounded POSIX temporary storage fixes its file semantics.
  [Observation packet](../compat/api-acceptance/mandatory-wsl-headless-v2.json).
  **All eight host-row observations collected.** No admissions transfer.

- [x] **FIX-06-WINDOWS-HEADLESS-OBSERVATION:** the current Windows wheel passes
  95 GPU tests, rendering/compiled text, a 4,096-marker scene and 36 scientific
  cases with the existing value/pixel oracles. Installed inventory and fresh
  replay pass all three graphics gates; 537 members and zero-resource cleanup
  are checked. [Observation packet](../compat/api-acceptance/mandatory-windows-headless-v2.json).
  Both headless observations are collected. Canonical matrix entries and
  admissions remain unchanged; all eight row observations are collected.

- [x] **FIX-06-WSL-COLLECTOR:** resolved the stale native collector mismatch.
  The old binary lacks the complete-record parser in frozen source and fails
  its fragmented-record controls. An unmodified-source rebuild passes all 20
  controls. Original binary/evidence retained; shipping source and wheels unchanged.
- [x] **FIX-06-TK-WSL-OBSERVATIONS:** all four workflows pass all three graphics
  gates in fresh installed replays on Linux wheel `48164e05…`. Each worker
  verifies 537 members with zero overrides. All workflows use the refreshed
  collector and one offline consumer. [Current packet](../compat/api-acceptance/tk-strict-wsl-v2.json).
  Independent source/scope review, candidate admission and formal admission of
  the eight mandatory host rows remain open. No previous approvals transfer.
- [x] **FIX-06-TK-WSL-OBSERVATIONS-PARTIAL:** earlier three-workflow and
  diagnostic packets remain historical, with failed attempts preserved.

- [x] **FIX-06-TK-WINDOWS-OBSERVATIONS:** all four pinned Tk candidate workflows
  pass installed dependency inventory and fresh replay with all three graphics
  gates on Windows wheel `a86b030b…`. The existing interpreter, native outputs,
  observer and offline dependency wheels were reused; the small managed consumer
  is disposable. [Exact reports and scope](../compat/api-acceptance/tk-strict-windows-v1.json).
  This closes the Windows observation collection step only. Candidate admission,
  independent review and eight mandatory host rows remain open.

- [x] **LIF-07-NATIVE-WHEELS:** new experimental Windows `a86b030b…` and Linux
  `48164e05…` wheels contain native Tk at source `b38c4f90`. Each passes 186
  installed cases, with 537 package members verified and zero source overrides.
  Functional validators and five active capture controls pass per platform.
  WSL native and raster checks use separately identified existing drivers;
  failed MSAA and stale-harness attempts remain retained. All six packaging/test
  scratch directories are cleaned. [Evidence](../compat/api-acceptance/tk-native-installed-v1.json).
  Candidate revision 4 renews preparation only. Next: independent source/scope
  review, then the unchanged strict installed/profile admission requirements.

- [x] **LIF-07-NATIVE-PROTOTYPE — Optional native Tk source prototype:**
  seven cases pass per Windows/WSL-X11 source overlay. Tk raster stays default;
  native mode avoids PhotoImage readback and uses the existing Vulkan surface
  APIs. WSL uses an explicitly hashed existing X11-capable system driver; the
  pinned headless clipping driver is unchanged and cannot present to X11.
  Both prototype proof and all failed/intermediate scratch are retained/cleaned.
  [Usage and exact limitations](tk-native-presentation.md). This historical
  source-overlay result is superseded for packaging by the installed task above;
  independent review and release qualification remain open.

- [x] **Current event/input/depth refresh:** all 126 cases pass on each current
  wheel using one offline installation per platform. All 537 installed members
  are checked per child; event semantics load no renderer/backend, while input
  and depth processes each retire ten resource gauges to zero. Both targets
  are removed (47,751,307 bytes), with 26/28 retained entries rehashed.
  [Finite scope and evidence](../compat/api-acceptance/current-event-input-depth-v1.json).

- [x] **SHD-05-BOUNDARIES — Seven generated-line refusal/recovery cases.**
  [The test](../tests/shaders/test_line_side_effect_boundaries.py) covers
  vertex storage writes, clip distance, fragment storage writes, atomics,
  image stores, barriers and early fragment tests. It expects explicit refusal
  followed by a valid draw on the same canvas. All seven pass without skips on
  Windows wheel `ba8a54c5…` and WSL software Vulkan wheel `4bc3cd77…`.
  Each process verifies 537 installed members, 56/55 loaded module origins,
  the expected recovery pixels and ten zero shutdown gauges. No native build
  or new dependency environment was needed. Both scratch targets are removed
  (47,751,313 bytes), with 15/17 retained entries rehashed. The earlier storage
  refusal remains a separate failed preflight, not a test result.
  [Exact acceptance and durable evidence](../compat/api-acceptance/line-side-effect-boundaries-v1.json).
  Parent SHD-05, independent review and strict-profile/release admission remain
  open. The next release prerequisites are cumulative review and installed/profile
  qualification below; record preparation is complete. Optional implementation
  work must select another finite scope.

## Successor release completion

- [x] **FIX-04-REVIEW — Independent source/scope review:** exact revision8digests and both native-reuse links are bound. [Decision](../compat/api-acceptance/successor-peer-review-v5.json). Corrected oracle test is independently approved; no transferred approvals or proof/admission claim.
- [x] **FIX-04 / FIX-06 — Final provenance/subject binding (2026-11-13):** revision8subject proves128/128criteria at head3ada using the exact32-row overlay, complete six-attempt histories and599-input contributing retention. Independent change-impact approval is bound; frozen preparation restored. [Current proof](../compat/api-acceptance/revision8-installed-subject-v1.json). Original producers, SDK origins, failures and notices stay intact.
- [x] **FIX-06-OBS — Current mandatory-profile observations collected:** all8Windows/WSL headless/PyQt5/PyQt6/PySide6 observations exist on the selected wheels. [Exact observation scope](../compat/api-acceptance/mandatory-current-wheels-observations-v2.json). Their later scoped admission is recorded separately in [revision8final admission](../compat/api-acceptance/revision8-final-admission-v1.json); the original observation packet remains unchanged.
- [x] **FIX-04-PROOF — Prior finite installed subject proved:** head9cf/revision7has128provedcriteria, zero missing/blocked joins, six complete attempts and601contributing retained inputs. [Proof](../compat/api-acceptance/installed-subject-proof-v1.json). Revision8renewal is now separately proved at head3ada; this prior record remains historical. No fresh graphics replay is justified without changed critical inputs.
- [x] **FIX-06 — Final promotion/admission (2026-11-13):** independent exact-basis approval and actual unchanged strict verifier admit128Tk criteria; eight selected mandatory rows have separate final approval/admission. Frozen preparation restored. [Evidence](../compat/api-acceptance/revision8-final-admission-v1.json). Protected integration and publication remain open; no all-API claim.
- [x] **FIX-04 — Integrate (2026-11-13):** protectedPR75 merged as `fc3b9734…`; qualified source tree and other owner index preserved.
- [x] **FIX-06 — Public delivery (2026-11-13):** the two exactvulkan.2wheels, four-link index and Windows537-member/Vulkan-clear plus Linux537-member/ABI-import channel checks pass; temporary installs cleaned. [Actual evidence](../compat/api-acceptance/successor-public-delivery-v1.json). No broader inventory or hardware claim.

## Rendering and shader scope

For each open parent, first select a finite supported subset or document an
explicit boundary; implementing every possible form is not required.

- [ ] **SHD-01 — Sampler breadth:** decide multidimensional runtime indexing,
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  implicit-derivative/uniformity rules, additional preprocessor/helper forms,
  multilevel mip chains and wider filtering/LOD combinations. The proved path
  is direct explicit selection over one-dimensional arrays; retain intentional
  refusals and add value, binding-limit and recovery tests for any expansion.
- [ ] **SHD-02 — Array breadth:** settle remaining storage/interface classes,
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  shape/type combinations, indexing, partial updates, reflection and shader-cache
  identity beyond the installed numeric uniform subset.
- [ ] **SHD-03 — Attribute breadth:** disposition constants, additional formats,
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  shapes/divisors and mutation combinations beyond the finite matrix/array
  evidence. Retain route-specific raster versus generated-line input limits.
- [ ] **SHD-04 — Geometry consumers:** select supported compute/instanced
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  expansion or an explicit application rewrite; prove topology, interpolation,
  clipping, depth and mutation/loss for that subset.
- [ ] **SHD-05 — Broader line semantics:** beyond the seven proved boundary cases above,
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  decide any additional builtin, external-storage and early/late-depth support.
  Unsupported semantics must keep explicit diagnostics and recovery behavior.
- [ ] **SHD-06 — Broader Mesa driver portability:** the patched Mesa9c5
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  profile is admitted for the selected release. Wider system-driver support
  needs its own exact current artifact/driver observations. Historical
  pre-qualification checkpoint follows; it does not reopen current admission.
  2026-11-13: [matched patched driver installed baseline](../compat/api-acceptance/lifecycle-linux-tk-matched-observation-v1.json)
  passes56Tk cases and recovery on current wheel8a793196. [System Mesa25.2.8](../compat/api-acceptance/lifecycle-linux-system-mesa-msaa-failure-v1.json)
  fails the four-sample quadrant case on the identical wheel/tests. Preparation9
  binds the actual patched driver; strict profile/CI joins remain pending.
- [ ] **STA-01 — Raster-state combinations:** reconcile dither, disabled
  2026-11-15: [sta01-tex01-sci06-windows](../compat/api-acceptance/sta01-tex01-sci06-windows-v1.json), [sta01-tex01-sci06-wsl](../compat/api-acceptance/sta01-tex01-sci06-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  multisampling, fractional polygon offset, mixed constant blending and stencil.
  Keep the already-proved reversed-depth subset separate.
- [ ] **TEX-01 — Typed sampling:** disposition Uint/Sint, unfilterable float,
  2026-11-15: [sta01-tex01-sci06-windows](../compat/api-acceptance/sta01-tex01-sci06-windows-v1.json), [sta01-tex01-sci06-wsl](../compat/api-acceptance/sta01-tex01-sci06-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  comparison sampling, half precision and NaN behavior on claimed layouts.
- [ ] **LIN-01 — Line partitioning:** bind chunk boundaries, endpoint carry,
  2026-11-15: [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [shd01-06-lin01-wsl](../compat/api-acceptance/shd01-06-lin01-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  topology, resource limits and ordering to selected rendered acceptance cases.

## Scientific workflows and API reconciliation

- [ ] **API-05 — Methods, routes and aliases:** reconcile remaining public
  2026-11-16: [tier1-collections-jupyter-rfb](../compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json) (`2a3ec57f…`, source `3daf19be…`, `1006`–`1013`): `installed-functional` resolution of all `3` former Wave 3 `collections` bounds (`9/9` rendered) + `app.backend.jupyter-rfb` Dawn lifecycle/readback/HiDPI/CPython-3.14-timer (`3/3` live GPU `0` skipped, `85/85` CPU contracts in `cpu-checks.log` `0ca3ae9b…`); `scoped_admitted: false`, `publicly_delivered: false`, no full upstream parity claim.
  2026-11-15: [api05-plot-transforms-windows](../compat/api-acceptance/api05-plot-transforms-windows-v1.json) (`4278e1bd…`, `989`) & [api05-plot-transforms-wsl](../compat/api-acceptance/api05-plot-transforms-wsl-v1.json) (`6cd157b0…`, `990`, `16/16` pass/platform): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [sta01-tex01-sci06-windows](../compat/api-acceptance/sta01-tex01-sci06-windows-v1.json), [shd01-06-lin01-windows](../compat/api-acceptance/shd01-06-lin01-windows-v1.json), [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  methods, wildcard exports, aliases and value-dependent dispatch with actual
  source routes. Parent-level app/gloo/scene/visual reviews are already recorded;
  the canonical inventory is still not a fully reviewed method inventory.
- [ ] **API-06 — Selected API acceptance:** for each claimed subset, record
  2026-11-16: [tier1-collections-jupyter-rfb](../compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json) (`2a3ec57f…`) & [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`, source `3daf19be…`): `installed-functional` `75/75` GPU pass per ABI across `cp311`/`cp312`/`cp313` on Windows RTX 4090, WSL Mesa `9c5c41b3…`, and Colab `Tesla T4` (`225/225` in `1013`), plus `14/14` `cp312` Tk capture/recovery (`1007b`/`1010b`) and unreviewed `tk-state-resource-17` (`1014` `71511a45…`, `reviews: null`); `scoped_admitted: false`, `publicly_delivered: false`.
  2026-11-15: [api05-plot-transforms-windows](../compat/api-acceptance/api05-plot-transforms-windows-v1.json) (`4278e1bd…`, `989`) & [api05-plot-transforms-wsl](../compat/api-acceptance/api05-plot-transforms-wsl-v1.json) (`6cd157b0…`, `990`, `16/16` pass/platform): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `scoped_admitted: false`; no full upstream parity claim.
  inputs/values, expected output, ordinary/mutation/failure/recovery behavior,
  exact installed artifact and explicit unsupported cases.
- [x] **API-06-CLEAR-ZERO-INSTALLED — Eleven finite cases per profile:**
  [Record audit, 2026-11-14](../compat/api-acceptance/current-gap-record-reconciliation-v1.json)
  rechecks the original 664/665 JUnit and result hashes: numeric-zero depth and
  stencil clears, Python/NumPy flags, mutation and invalid-depth recovery pass
  on runtime `2b8bccd`, Windows `9e4e30cc` and WSL `a2715d26`, with 537 members,
  no overlays and ten zero gauges. The older nine-case source packets remain
  historical. This closes installed observation for these values, not broader
  API acceptance or qualification of the newer callback wrapper.
- [ ] **SCI-01 — Indexed/instanced points:** rendered source-ID, divisor,
  2026-11-15: [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  constant-input and ordered-revision combinations.
- [ ] **SCI-02 — Mesh filters:** enumerate supported filters/compositions and
  2026-11-15: [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  prove meaningful output plus mutation behavior for selected combinations.
- [x] **SCI-02-COLOR-ALPHA-COMPOSITION — Finite installed subset, 2026-11-14:**
  Six exact-pixel queued-revision/mutation/boundary/recovery cases pass per
  current Windows/WSL wheel, with explicit single-sample/blend-disabled scope.
  [Windows](../compat/api-acceptance/mesh-color-alpha-windows-v1.json),
  [WSL](../compat/api-acceptance/mesh-color-alpha-wsl-v1.json). Other filters,
  composition ordering, blending/MSAA and final review/integration/admission
  of the post-head test remain separate; SCI-02 stays partial.
- [ ] **SCI-03 — Scenes/cameras:** reconcile selected 3D cameras, planes,
  2026-11-15: [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  depth/stencil and polygon-offset interactions.
- [x] **SCI-03-CAMERA-MUTATION — Finite local installed subset, 2026-11-13:**
  Public TurntableCamera azimuth/center mutation, fresh-construction equivalence,
  comparison-peer closure and frozen-pose restoration pass2cases per current
  Windows9e4e30cc/WSLa2715d26wheel, runtime2b8bccd. [Windows](../compat/api-acceptance/camera-mutation-windows-v1.json),
  [WSL](../compat/api-acceptance/camera-mutation-wsl-v1.json). Changed-pose
  equivalence is metamorphic; baseline/restoration has the independent frozen
  reference. Broader3Dstate/fov/event/other-camera combinations and final
  review/integration/admission of the post-head test remain separate.
- [ ] **SCI-04 — Large volumes:** separate scientific quality, mode, performance,
  2026-11-15: [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  platform and artifact claims; extend only the selected bounded workflow.
- [ ] **SCI-05 — Stale fixture dispositions:** reconcile U05, E03, E04, Q11–Q13
  2026-11-15: [sci01-05-windows](../compat/api-acceptance/sci01-05-windows-v1.json), [sci01-05-wsl](../compat/api-acceptance/sci01-05-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  and H03 against newer evidence before changing their status.
- [x] **SCI-05-RECONCILIATION — Seven-row disposition audit, 2026-11-13:**
  [708](../compat/api-acceptance/scientific-current-dispositions-v2.json) and the
  [route/value table](api-method-reconciliation.md#current-seven-row-reconciliation--2026-11-13)
  identify exact current/historical/open scope and reopening triggers for all
  seven rows. Record classification is complete; capability parents and final
  admission/public delivery remain partial. No broad source-route review inferred.
- [ ] **SCI-06 — Stencil wrapper:** track additional selected formats and
  2026-11-15: [sta01-tex01-sci06-windows](../compat/api-acceptance/sta01-tex01-sci06-windows-v1.json), [sta01-tex01-sci06-wsl](../compat/api-acceptance/sta01-tex01-sci06-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  compatibility boundaries separately from native capture. Original stock
  failures remain historical failures; complete stock parity is not required.
- [x] **SCI-06-PUBLIC-ROUTES-INSTALLED — Eight finite cases per profile:**
  [801 record audit](../compat/api-acceptance/current-gap-record-reconciliation-v1.json)
  verifies four public value/type/crop/mutation forms and four raw-read
  refusal/public-wrapper recovery cases in the original 664/665 installed
  reports. Scope: runtime `2b8bccd`, exact Windows `9e4e30cc` / WSL `a2715d26`,
  no overlays and ten zero gauges. [Route disposition](stencil-wrapper-disposition.md)
  retains the eight original stock failures and unsupported raw operation.
  Other formats/MSAA, formal profile admission and the new callback artifact
  remain separate; this is an evidence reconciliation, not a new rendering run.

## Lifecycle, capture, input and known issues

- [x] **LIF-01-SUBMISSION-WINDOWS — Finite11-case installed subset:**
  [740](../compat/api-acceptance/submission-fault-windows-v1.json),2026-11-14:
  selected existing gloo/raw pre/post-submit/query-frame failure/recovery and
  retirement cases pass9e4e30cc,537members/no overlays/ten zero gauges; cleaned.
  Surface-acquisition, physical-memory and full-parent/integration scope open.
- [x] **LIF-01-SUBMISSION-WSL — Matching11-case installed subset:**
  [741](../compat/api-acceptance/submission-fault-wsl-v1.json),2026-11-14:
  exact740source/cases passa2715d26/softwareVulkan,537members/no overlays/ten
  zero gauges; unchanged borrowed origins, awaited exits, cleaned target.
  Actual surface, physical-memory and broader-parent/evidence integration open.
- [ ] **LIF-01 — Fault coverage:** audit acquisition failures, fault injection
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  and physical-memory-accounting evidence; retain unresolved cases explicitly.
  New source failure, 2026-11-13: run557retains24CPU-buffer and24GPU-buffer
  bytes after final explicit deletion/close. The rebuilt native leaf resolves
  that exact case with all nine zero gauges on Windows (runs560/561); retain
  the original failure. Linux and broader fault/memory cases remain open.
- [ ] **LIF-02 — Reparenting:** selected real layout reparenting, WinIdChange,
  2026-11-15: [lif02-08-qt-multibinding-windows](../compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json) (`9001513c…`, `987`) & [lif02-08-qt-multibinding-wsl](../compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json) (`5fb417d3…`, `988`, `12/12` pass/platform across PyQt5/PyQt6/PySide6): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `physical_multimonitor_claimed: false`, `physical_hid_claimed: false`, `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  surface ownership and shared-resource lifetimes.
  Source progress, 2026-11-13: [Windows PyQt6 readback](../compat/api-acceptance/qt-layout-reparent-source-v1.json)
  passes two active layout moves, old-parent deletion after the move, actual
  WinIdChange, continued exact pixels and all nine zero shutdown gauges.
  No renderer change/rebuild; initial fixture QApplication-order failures are
  preserved. The same case now [passes on current WSL software Vulkan](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json).
  Installed, native-WSI and embedded-parent destruction remain open.
- [ ] **LIF-03 — Zero/minimized windows:** prove no-submit behavior and restoration
  2026-11-15: [lif02-08-qt-multibinding-windows](../compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json) (`9001513c…`, `987`) & [lif02-08-qt-multibinding-wsl](../compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json) (`5fb417d3…`, `988`, `12/12` pass/platform across PyQt5/PyQt6/PySide6): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `physical_multimonitor_claimed: false`, `physical_hid_claimed: false`, `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  beyond screenshots or overlay observations.
  Source progress, 2026-11-13: window-state events now suspend/restore without
  resize; real offscreen Qt before/after control and 43 CPU cases pass.
  [Evidence](../compat/api-acceptance/qt-window-state-source-v1.json). Physical
  Windows readback rendering now also passes no-submit while minimized,
  exact restored pixels and zero ticket/queue gauges after close
  ([source Vulkan evidence](../compat/api-acceptance/qt-window-state-windows-source-v1.json)).
  The same finite case also passes on [WSL software Vulkan](../compat/api-acceptance/qt-window-state-wsl-source-v1.json).
  Broader zero-size/resource cases and changed-artifact qualification remain
  open; the local-native and WSL bootstrap failures are retained separately.
- [ ] **LIF-04 — Close/loss:** selected in-flight close, actual surface loss,
  2026-11-15: [lif02-08-qt-multibinding-windows](../compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json) (`9001513c…`, `987`) & [lif02-08-qt-multibinding-wsl](../compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json) (`5fb417d3…`, `988`, `12/12` pass/platform across PyQt5/PyQt6/PySide6): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `physical_multimonitor_claimed: false`, `physical_hid_claimed: false`, `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  multicanvas recovery and resource retirement.
  Source progress, 2026-11-13: native QWidget close now invokes Canvas.close
  once, including callback-error cleanup. Shared-peer green pixels pass on
  Windows; rebuilt native final buffer retirement and pending-peer-snapshot
  preservation now pass ([evidence](../compat/api-acceptance/qt-lifecycle-windows-native-v1.json)).
  Both shared-close cases now [pass on the verified current Linux native payload under WSL](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json),
  including all nine zero gauges. Installed, embedded-parent lifecycle and actual surface loss remain open.
- [x] **LIF-05-DEFAULT-DEPTH-STENCIL — Finite16case local installed subset:**
  [748](../compat/api-acceptance/msaa-depth-stencil-windows-v2.json)/
  [749](../compat/api-acceptance/msaa-depth-stencil-wsl-v2.json),2026-11-14:
  same default target/sample/type/crop/mutation/refusal/restoration cases pass
  current wheels, color preserved BEFOREredraw,537members/no overlays/ten zero gauges;
  cleaned. Uniform
  samples only. Independent review and evidence integration are complete in
  [PR80](../compat/api-acceptance/lifecycle-panzoom-protected-integration-v1.json);
  mixed-edge selection, other formats/features and broader admission stay open.
- [ ] **LIF-05 — MSAA capture:** disposition broader depth/stencil and
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  format/feature combinations separately from existing color-resolve evidence.
- [x] **LIF-06-QT-WINDOWS — Finite8case installed PyQt6 subset:**
  [736](../compat/api-acceptance/qt-input-windows-v1.json),2026-11-14:
  generated key/wheel/mouse payload/rendering/handled-state/target-isolation
  cases pass Windows9e4e30cc, no overlays/ten zero gauges; scratch cleaned.
  The matching WSL subset is recorded below. Evidence integration is complete
  in [PR79](../compat/api-acceptance/qt-input-protected-integration-v1.json);
  focus/physical HID, broader parent and profile admission remain separate.
- [x] **LIF-06-QT-WSL — Matching8case installed PyQt6 subset:**
  [738](../compat/api-acceptance/qt-input-wsl-v1.json),2026-11-14:
  exact same736source passes currenta2715d26/softwareVulkan/privateXvfb,537members,
  no overlays/ten zero gauges; borrowed origins and cleanup verify.737dependency
  failure retained. Evidence integration is complete in
  [PR79](../compat/api-acceptance/qt-input-protected-integration-v1.json).
  Broad parent/other bindings and new-test CI coverage remain outside the proof.
- [x] **LIF-06-QT-PANZOOM — Finite2-case installed scene-response subset:**
  [755](../compat/api-acceptance/qt-panzoom-windows-v2.json)/
  [756](../compat/api-acceptance/qt-panzoom-wsl-v2.json),2026-11-14:
  generated Qt PanZoom gestures drive literal rect/marker changes and exact
  restoration on current Windows/WSL wheels,537members/no overlays/ten zero
  gauges; cleaned. Explicit-size render, not native display/HID/focus/DPI.
  Independent review and evidence integration are complete in
  [PR80](../compat/api-acceptance/lifecycle-panzoom-protected-integration-v1.json).
  Broader camera/parent and profile-admission scope remain open.
- [x] **LIF-06-QT-INPUT-CALLBACK-SOURCE — Revised Windows/WSL PyQt6 CPU subset, 2026-11-14:**
  [782Windows](../compat/api-acceptance/qt-input-callback-windows-source-v4.json)/
  [783WSL](../compat/api-acceptance/qt-input-callback-wsl-source-v4.json) each93pass:
  47input/46paint-window,12parent key routes with default/working/broken hooks.
  780negative review and781doublecallback/doublehook reproducer retained;
  new1c68runtime preserveshostacceptedstate/guards privatekeydispatch/consumes
  suspendedreplay. Closed/post-C++-destroyed parent lookups not separately observed.
  Exactsource re-review/integration and installed qualification remain pending.
  Update, 2026-11-14: [PR81 integration verified](../compat/api-acceptance/qt-callback-protected-integration-v1.json)
  closes source review/protected integration at merge `a69505ce`, exact tested
  49-file tree and 11 required checks. Final-head callback fallback tests pass
  49 cases per profile. Installed/release qualification of the changed wrapper
  and other bindings remain separate; the original source observations stay finite.
- [x] **LIF-06-QT-INPUT-CALLBACK-RENDERED-WINDOWS — Revised finite overlay subset, 2026-11-14:**
  [784](../compat/api-acceptance/qt-input-callback-rendered-windows-v3.json)
  passes21cases(6defaultpeer/3hostsamecanvas/12controls),9isolated origin/nativeSHA/
  zero-gauge proofs at1c68, host/defaultacceptedstate explicit.9e4native/536members
  unchanged,1QtPythonoverlay. Parent-forwarding evidence is the separateCPUsubset.
- [x] **LIF-06-QT-INPUT-CALLBACK-RENDERED-WSL — Matching revised overlay subset, 2026-11-14:**
  [785](../compat/api-acceptance/qt-input-callback-rendered-wsl-v3.json) same21cases/
  sourcehashes as784,9childzero-gauge proofs; a271native/536members unchanged,
  1QtPythonoverlay, borrowedQt/9c5driver unchanged/privateXvfb0; cleaned after
  transientPID-livenessplan refusal resolved with unchangedmanifest/verifier.
  Source re-review/protectedintegration, otherbindings/fullnapari, changed-wrapper
  installed/public admission and broader-parent scope remain open.
  Update: source re-review and protected integration are complete in PR81 above.
  Other bindings, hosts and changed-wrapper installed/public admission stay open.
- [ ] **LIF-06 — Input forwarding:** selected Qt keyboard, wheel, focus, mouse,
  2026-11-15: [lif02-08-qt-multibinding-windows](../compat/api-acceptance/lif02-08-qt-multibinding-windows-v1.json) (`9001513c…`, `987`) & [lif02-08-qt-multibinding-wsl](../compat/api-acceptance/lif02-08-qt-multibinding-wsl-v1.json) (`5fb417d3…`, `988`, `12/12` pass/platform across PyQt5/PyQt6/PySide6): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + Mesa `9c5`); `physical_multimonitor_claimed: false`, `physical_hid_claimed: false`, `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity; no physical-HID claim.
  timer and coordinate delivery beyond the finite Tk subset. Touch, stylus,
  gestures and additional layouts need their own selected scope.
- [x] **LIF-06-QT-FOCUS — Selected interaction integrated, admitted and delivered:**
  Current completion, 2026-11-14: the selected finite contract is integrated,
  admitted and delivered at source275888b5/qualifier90348a8/merge76cc5e8c,
  Windows4f537748 and Linuxdfe1033f. [Final release evidence](../compat/api-acceptance/orphan-release-public-delivery-v1.json).
  The following progress paragraphs retain their earlier evidence stages.
  Historical interaction: two canvases plus a host
  text entry, QWindow key routing, focus isolation/recovery and a finite rendered
  response. The [execution contract](superpowers/plans/2026-11-14-gap-investigation-next.md#next-selected-interaction-lif-06-qt-focus)
  distinguishes this from existing direct-widget event delivery. The source
  prototype, maintained CPU tests and real-canvas cases below pass. Current
  [Windows](../compat/api-acceptance/orphan-current-windows-v1.json) and
  [WSL](../compat/api-acceptance/orphan-current-wsl-v1.json) selections also pass
  maintained focus cases with537members/no overlays and two deliberate resource
  refusals per profile. Combined protected integration and strict installed
  admission remain open; old overlay evidence below stays historical.
- [x] **LIF-06-QT-FOCUS-RENDERED-WINDOWS — Two finite cases:**
  [806](../compat/api-acceptance/qt-focus-rendered-windows-v1.json) proves actual
  A/B/A and A/host-entry/A routing through one QWindow, key payload/order and
  literal 2×2 framebuffer colors with peer/entry isolation and recovery.
  Ten zero gauges per case and parent; unchanged qualified native plus exactly
  one Qt Python overlay matching merged `a69505ce`. No physical/display claim.
- [x] **LIF-06-QT-FOCUS-RENDERED-WSL — Matching two cases:**
  [807](../compat/api-acceptance/qt-focus-rendered-wsl-v1.json) has identical
  source and proofs on private Xvfb/software Vulkan; borrowed origins unchanged,
  all children awaited and ten gauges zero per case/parent. Both targets cleaned.
  This is source-overlay acceptance, not a new installed-wheel or CI claim.
- [x] **LIF-06-QT-FOCUS-SOURCE-TESTS — Two tests each on Windows/WSL:**
  [809/810 v2](../compat/api-acceptance/qt-focus-source-tests-v2.json) verify A/B/A
  and A/host-entry/A with fixed host QWindow injection, exact key payload/order,
  isolation and restored delivery. Matching source/proofs observe all four owned
  widgets destroyed; the missing-deletion control is rejected. Old 803/804/v1
  records remain historical; their constant flag did not prove destruction.
  Native calls are forbidden. Offscreen QWidget doubles only, no Dawn canvas.
  Both targets cleaned; new source/evidence remain outside PR81 and CI claims.
- [x] **LIF-06-QT-FOCUS-SOURCE-PROTOTYPE — Finite Windows offscreen protocol:**
  [802](../compat/api-acceptance/qt-focus-source-prototype-v1.json) routes fixed
  host QWindow input through actual A/B/A/host-entry/B focus. Eight canvas key
  events, entry isolation and restored delivery pass with production key handlers;
  native setup/painting are bypassed and native calls forbidden. Exit 0/awaited,
  seven retained files verified, scratch absent. No rendered/WSL/installed claim.
- [ ] **LIF-07 — Tk extensions:** decide camera/DPI/physical-input claims beyond
  2026-11-15: [tk-native-current-wheels](../compat/api-acceptance/tk-native-current-wheels-v1.json) (`224701fe…`, `985`/`986`, `11/11` pass/platform, `default_presentation: "raster"`): installed-experimental on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb` + system Mesa `25.2.8`); `default_presentation: "raster"`, `native_admitted_mandatory_matrix: false`, `scoped_admitted: false`; no full upstream parity claim.
  2026-11-15: [lif01-07-windows](../compat/api-acceptance/lif01-07-windows-v1.json), [lif01-07-wsl](../compat/api-acceptance/lif01-07-wsl-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  the proved raster/manual-pump and toolkit-generated input cases.
  The opt-in native presentation prototype now has finite source-functional
  proof; it does not close DPI, physical-input or release/profile obligations.
- [ ] **BUG-01 — Rare Windows startup stall:** retain the external watcher and
  exact recurrence evidence; establish cause and a targeted regression. It is
  documented under D33; recurrence makes it release-blocking again.
- [ ] **BUG-02 — Historical PyQt5 OLE hang:** determine whether it shares BUG-01's
  cause or needs a separate documented disposition.

## Optional integrations, packaging and tooling

Select these only when needed for a product claim.

- [ ] **HOST-03:** renew optional strict napari/Glue/napari-threedee rows if
  2026-11-15: [no-opengl-optional-hosts-current-v1.json](../compat/no-opengl-optional-hosts-current-v1.json) (`0f7159d7…`): additive current-wheel optional-host view on `9919a280`/`e600b29e` (preserving `no-opengl-matrix.json` `230b12f3…` untouched without `r1`, and `no-opengl-napari-0.10.0.json` `a724432b…` row `windows-vulkan-napari-threedee-pyqt6` `r1 == "open"`); not scoped-admitted, not delivered, no full upstream parity claim.
  2026-11-15: [host01-06-current-wheels](../compat/api-acceptance/host01-06-current-wheels-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity; HOST-01 is hot-swap only.
  claiming them on the successor artifact; old host qualifications do not transfer.
- [ ] **HOST-04:** resolve DIVE's supported binding/API and upstream baseline
  2026-11-15: [host01-06-current-wheels](../compat/api-acceptance/host01-06-current-wheels-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity; HOST-04 is NOT_ADMITTED.
  before claiming rendered workflows; PySide2 remains excluded.
- [ ] **HOST-05:** select rendered Visbrain/other-application workflows rather
  2026-11-15: [host01-06-current-wheels](../compat/api-acceptance/host01-06-current-wheels-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity; Visbrain is NOT_ADMITTED, phylib is import-only.
  than treating imports or inventories as application acceptance.
- [ ] **HOST-06:** reconcile Glue's older volume-mutation gap with newer workflow
  2026-11-15: [host01-06-current-wheels](../compat/api-acceptance/host01-06-current-wheels-v1.json): installed-functional on `9919a280`/`e600b29e` (`Windows RTX 4090` / `WSL Xvfb Mesa 9c5`); not scoped-admitted, not delivered, no full parity.
  results while preserving each evidence epoch.
- [ ] **PLAT-02:** produce and qualify other CPython ABI wheels only if selected;
  the current release claim is CPython 3.12 x86_64.
  2026-11-16: [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`, source `3daf19be…`): `installed-functional` `0.17.0+vulkan.2` wheels built and verified for `cp311` (`834fe5f7…` Win `1008`, `fc8dd6cc…` manylinux `1011`) and `cp313` (`793dab79…` Win `1009`, `1362eb6a…` manylinux `1012`) alongside `cp312` (`ec8097cf…`/`513088c1…`), passing `44/44` CTests, `75/75` GPU cases per ABI on Windows RTX 4090 & WSL Mesa `9c5c41b3…`, and `225/225` on Colab `Tesla T4` (`1013` `254329bd…`); `PLAT-02` stays `[ ]` OPEN (`plat02_closed: false`, `cp310`/`cp314` GPU wheels, strict mandatory admission, and public release delivery not claimed).
- [ ] **PLAT-08:** qualify additional Vulkan GPU/driver combinations before
  extending the current hardware claim.
  2026-11-16: [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`, run `1013` `254329bd…`): `225/225` `installed-functional` pass across `cp311`/`cp312`/`cp313` on physical Linux `NVIDIA Tesla T4` (`NVIDIA 580.82.07`, `Xvfb :99`) at source `3daf19be…`; parent `PLAT-08` stays `[ ]` (`scoped_admitted: false`).
  2026-11-15: [plat03-08-linux-nvidia-colab](../compat/api-acceptance/plat03-08-linux-nvidia-colab-v1.json) (`b8a5bd8e…`, runs `998` `1bbfe275…`, `999` `c6aec5e3…`, `1000` `747a7b0c…`, hygiene `1001` `7a26baec…`): `installed-functional` on `e600b29e…` across Linux `Tesla T4` (`117/117` + `31/31`) and `NVIDIA L4` (`136/136`) on `NVIDIA 580.82.07` / `Xvfb :99` (plus `11/11` `installed-experimental` `W3-1` native Tk X11 WSI on `T4`); parent `PLAT-08` stays `[ ]` (`non_nvidia_linux_gpus_claimed: false`, `physical_display_scanout_claimed: false`, `scoped_admitted: false`).
- [ ] **PERF-02 / PERF-03:** select further imported-block conversions and batched
  buffer upload optimization only if measurements justify them.
- [ ] **PERF-04:** bounded cold-build/peak-memory measurements and reconciliation
  of historical review regressions if making those performance claims.
- [x] **TOOL-01 — Hosted reuse verified, 2026-11-13:** Linux software Vulkan and both actual Metal build/CPU-import jobs pass at reviewed head3ada, including locked minimal version validation. [Original API records](../compat/api-acceptance/revision8-native-ci-v1.json). No Metal graphics or release admission claim.
- [ ] **TOOL-02:** optional compiler-output cache with exact input identities and
  the shared storage budget.
- [ ] **TOOL-03:** reconcile the missing historical compiler-cache cleanup receipt.
  The new cleanup receipts do not establish the missing historical event.

## Explicit deferred or unavailable scope

- [ ] **LIN-02:** MSAA generated-line coverage remains deferred; an unshipped
  partial patch is not production support.
- [ ] **LIF-08:** cross-monitor changes and fractional DPI remain outside the
  selected release scope.
- [ ] **PLAT-03:** native Linux physical GPU qualification needs available
  hardware; WSL software Vulkan does not establish it.
  2026-11-16: [tier1-collections-jupyter-rfb](../compat/api-acceptance/tier1-collections-jupyter-rfb-v1.json) (`2a3ec57f…`) & [plat02-cp311-cp313-wheels](../compat/api-acceptance/plat02-cp311-cp313-wheels-v1.json) (`df12d6ce…`, run `1013` `254329bd…`): `225/225` `installed-functional` pass across `cp311`/`cp312`/`cp313` manylinux wheels (`fc8dd6cc…`/`513088c1…`/`1362eb6a…`) on physical Linux `NVIDIA Tesla T4` (`580.82.07`, `Xvfb :99`) at source `3daf19be…`; parent `PLAT-03` stays `[ ]` (`scoped_admitted: false`, non-NVIDIA Linux GPUs, physical scanout/HID, and Wayland remain open).
  2026-11-15: [plat03-08-linux-nvidia-colab](../compat/api-acceptance/plat03-08-linux-nvidia-colab-v1.json) (`b8a5bd8e…`, runs `998` `1bbfe275…`, `999` `c6aec5e3…`, `1000` `747a7b0c…`, hygiene `1001` `7a26baec…`): Linux physical NVIDIA GPUs (`Tesla T4` + `NVIDIA L4` on `580.82.07` + X11/`Xvfb`, `Linux x86_64 glibc 2.39` with `Ubuntu 24.04.4 LTS` observed via `/etc/os-release` in `998`) now have `installed-functional` evidence on `e600b29e…` (plus `11/11` `installed-experimental` `W3-1` native Tk X11 WSI on `T4`), while parent `PLAT-03` stays `[ ]` for non-NVIDIA Linux GPUs (AMD RADV, Intel ANV) and Mesa NVK, physical Xorg scanout vs `Xvfb`, physical HID/multi-monitor, Wayland (`PLAT-05`), and strict release admission (`scoped_admitted: false`).
- [ ] **PLAT-04:** macOS Metal remains experimental; no Mac is available for
  physical graphics/input/lifecycle qualification.
- [ ] **PLAT-05 / PLAT-06:** native Wayland is unsupported; ARM, free-threaded
  Python and ABI3 are outside the current release scope.

These are acknowledged boundaries, not a request to obtain hardware or expand
the release. No full-parity requirement is introduced.

## Update rule

Close one finite task at a time. Update its stable ID here and in the detailed
coverage checklist with source identity, exact wheel/platform, test counts,
failure/recovery result and durable evidence. Mark completion only at the proved
level; a parent stays open while broader claims are unsettled. Retain sources,
licenses and meaningful failures, apply the unchanged build-hygiene policy,
and record terminal cleanup before the next experiment. Do not derive a universal
coverage percentage from these different scopes.
