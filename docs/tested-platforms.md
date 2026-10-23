# Tested Windows and WSL milestone

Updated 2026-10-23. This first usable milestone targets Windows Vulkan and WSL
Linux software Vulkan. macOS Metal remains experimental. The results below
cover source commit `3f2012b38ae380a48c52a52c034425010ffd0ac0`; subsequent
status documentation does not change the renderer.

| Target | Verified scope |
| --- | --- |
| Windows x86_64, CPython 3.10–3.14, RTX 4090 Vulkan | Five freshly built wheels; isolated installed-package checks for two renderbuffer formats, zero initialization, clears, resize and queued-clear ownership, zero CPU texture uploads for those allocations, clear rendering, two fractional smooth widths, pipeline reuse and compiled SDF text. Package bytes, native-library origins and nine zero live-resource gauges pass. |
| Windows CPython 3.12 host/scientific checks | 23 mesh/layout, Glue and napari-threedee functional cases; 30 original scientific volume/image cases. The 30 scientific frames match exactly. Twelve mesh frames match exactly; axes/colorbar uses the documented functional check. Glue/plugin checks retain their interaction/state/landmark scope. |
| WSL Ubuntu, CPython 3.12, llvmpipe Vulkan | Full native wheel built directly from the corrected source distribution, without project overlays or reused native outputs. Isolated renderbuffer, clear, smooth-line, text and million-marker checks pass. Controlled stripped native origins, package/license checks and shutdown cleanup pass. |
| WSLg X11/xcb, PyQt6 | Five mapped-window Qt framebuffer cases pass, including alpha, redraw, independently owned QImage data after close, actual X11 surface calls and presentation. Saved capture semantics and nine zero shutdown gauges were checked. |

The source distribution contains all 99,063 tracked inputs byte-for-byte, plus
its generated PKG-INFO. Its SHA256 is
`e8c7906af3788fde2270b68d4c47c75a7a066f68b2ce11e27c3badb088374ffa`.
Implementation licensing is AGPL-3.0-only; original BSD and third-party license
payloads remain attached unchanged.

## Retained artifact hashes

These artifacts are retained locally with the validation reports. They have not
been uploaded as a GitHub release or published to a package index.

| Python | Wheel | SHA256 |
| --- | --- | --- |
| 3.10.19 | `vispy-0.17.0+vulkan.1-cp310-cp310-win_amd64.whl` | `08bcd8d22da697dd56c19e402bc016a868d37095905edcb890b0a1d6fb5c3fa0` |
| 3.11.14 | `vispy-0.17.0+vulkan.1-cp311-cp311-win_amd64.whl` | `e53a18035b77e0328b15bd652e83bd8bd836ff6b0495821e337c8532f652e443` |
| 3.12.8 | `vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl` | `459be77bed067410dbfaf52150cd8e9a16b458714c1fc317a82ddaff5b31c140` |
| 3.13.8 | `vispy-0.17.0+vulkan.1-cp313-cp313-win_amd64.whl` | `8762544bfd0b8a4955f1bd551a3ff1b913c2555924df58b427f1cb79cd963ef7` |
| 3.14.0 | `vispy-0.17.0+vulkan.1-cp314-cp314-win_amd64.whl` | `b114e023655fc4a04df169ed6a2e11d5fef8ba30b899428a12de5ad1722cae34` |
| 3.12.8 (WSL Linux) | `vispy-0.17.0+vulkan.1-cp312-cp312-linux_x86_64.whl` | `47d93d415127a777f95d956c8215973f53450a29dead05f2c795a8dd2647dcbb` |

## Limitations and follow-up

- Metal has no completed graphics qualification and is explicitly experimental.
- WSL validation uses a CPU software adapter. Native Linux GPU hardware and
  manylinux/distribution portability remain unverified.
- Analytic smooth-line edges approximate OpenGL. Exact driver rasterizer parity
  and additional MSAA line coverage are deferred; the unfinished MSAA experiment
  is not shipped. See [smooth-line support](smooth-lines.md).
- These are bounded functional/package results, not a claim that every upstream
  API, host version, GPU, desktop DPI setting or performance gate passes. No
  calibrated input-to-visible latency or universal speedup is claimed.
- Historical failed comparisons and build attempts remain retained. Earlier CI
  results keep their recorded source revisions; CPU CI is not GPU qualification.

Disposable build objects, owned consumer environments/caches and temporary
interpreters were removed after terminal validation. The four first-attempt
Windows caches whose deletion was rejected by automatic approval review remain
in place; that denied cleanup was not retried.
