# VisPy Vulkan 0.17.0+vulkan.2

Qualification completed on 2026-11-13. See the [GitHub Release](https://github.com/bipxx/vispy_vulkan/releases/tag/v0.17.0-vulkan.2) for current asset availability and public-channel delivery checks.

This successor includes the reviewed Tk state/resource fixes and finite shader,
scene and lifecycle compatibility work. It preserves the selected Vulkan
implementation and original native producers; this release assembly does not
rebuild the wheels. Full upstream VisPy parity is not the release target.

## Install

```sh
pip install "vispy==0.17.0+vulkan.2" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

Pin the exact local version. The index retains vulkan.1 as well as vulkan.2 and
uses SHA256 fragments for each GitHub Release asset.

## Exact assets

Both wheels require CPython 3.12 and x86_64. The release tag is
`v0.17.0-vulkan.2`.

| Wheel | Bytes | SHA256 |
| --- | --- | --- |
| `vispy-0.17.0+vulkan.2-cp312-cp312-win_amd64.whl` | 6,811,895 | `a86b030b005cba455f46ccaeffc56bf3f438142e490999f88156370e6093fb6c` |
| `vispy-0.17.0+vulkan.2-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,560,735 | `48164e052ddc3d8e5376a3a1f13fa652583142f4634438ae9067e204aab8b6ce` |

Product source is `b38c4f9068d6a425eef43b62313f0f4cf37f57d9`;
qualification implementation head is `3ada644e85248bcae214e7e487b4b1684336fd8f`.
Later proof declarations and documentation must preserve those runtime,
workflow, policy and qualification-tool inputs.

## Verified observations and release gates

All 128 selected Tk criteria prove on the exact wheels. Eight mandatory
VisPy-level observations pass: headless and plain QWidget with selected PyQt5,
PyQt6 and PySide6 profiles, on Windows Vulkan and WSL software Vulkan/X11.
These are exact selected no-OpenGL dependency profiles; the install command
alone does not provide those Qt profiles. Ordinary upstream Qt or host installs
are not covered by this strict claim.

Independent source/scope, change-impact and final exact-basis promotion reviews
are approved. All 23 same-head required CI jobs pass. The unchanged strict verifier
admits all 128 selected Tk criteria, and the eight mandatory successor rows have
separate reviewed admission. Protected source integration and public-channel
delivery are verified separately on the GitHub Release.

The legacy mandatory-row cleanup audit preserves the original two-root verifier
refusal: eighteen pinned historical Qt/control inputs stay at their original
paths, with additive cleanup protection. Their manually reviewed 957-input
retention audit is separate from the Tk subject's generic-verifier-accepted
599-input contributing retention. The frozen historical matrix remains intact.

## Limits and differences

Tk uses manual pumping and RGB copies to PhotoImage; RGBA capture is separate.
The admitted raster path does not promise native window presentation, vsync,
transparent compositing, physical-input parity or laboratory display latency.
Recovery evidence uses explicit device-loss injection.

Qt uses the selected plain-QWidget readback path. Host application qualifications
from earlier artifacts do not transfer to these wheels. Optional napari, Glue,
napari-threedee and other host work remains separately scoped.

The Linux tag is `manylinux_2_39_x86_64`, requiring glibc 2.39 or newer.
Only WSL software Vulkan is qualified on Linux. Physical Linux GPUs, native
Wayland, other ABIs/architectures and additional GPU/driver combinations are
outside this release claim. Metal remains experimental with hosted build/CPU
import checks only; no macOS wheel or Metal graphics qualification is included.
No full API or pixel-for-pixel VisPy parity or broad performance claim is made.

## Known Windows startup stall

A rare early-startup stall remains documented under D33; its cause is unresolved.
Recurrence is release-blocking. Preserve a recurrence with the external watcher:

```text
python tools/pool_watch_external.py --output <events.jsonl> -- <command>
```

See `docs/threedee-startup-diagnosis.md` for the retained diagnosis.

## Licensing and evidence

This implementation is AGPL-3.0-only. The unchanged original VisPy BSD license
and third-party notices remain attached to both wheels and the source.
See `LICENSING.md`, `docs/coverage-checklist.md` and the exact source-local
acceptance records under `compat/api-acceptance/`. Finite admission does not
complete the 142 broader original compatibility obligations.


The [exact admission record](../compat/api-acceptance/revision8-final-admission-v1.json)
links actual strict results, independent decisions, original row evidence,
materialization and the retained overlay. Canonical preparation remains frozen;
directly validating it does not replay the installed proof. Maintainer replay
uses the guarded materializer and then re-hashes the restored ledger and subject.
Raw local evidence is separate from the normal wheel/source checkout.


## Public channel verification — 2026-11-13

The release and index are public. Both actual installs verify all 537 VisPy
members against the exact released wheels with zero source overrides. Windows
also passes a 64×64 Vulkan clear/readback; Linux passes native binary import,
without a new GPU-rendering claim. All temporary installs are removed.
The [delivery record](../compat/api-acceptance/successor-public-delivery-v1.json)
retains the exact scopes, process receipts, recoveries and cleanup.
