# Performance report (W8, PERF-1)

Date: 2026-10-29. This is the measured report that requirement PERF-1 of the
[gap-closure spec](superpowers/specs/2026-10-24-vispy-compatibility-gap-closure.md)
asks for, and that decision D3 of the
[consolidated plan](superpowers/plans/2026-10-28-consolidated-plan.md) makes the
performance gate. It compares the port against upstream VisPy on OpenGL. It
makes no speedup claim, and its numbers hold only for the machine and builds
named below.

## Summary

- Resident scenes (images, volumes and points that only move the camera) keep
  the display's refresh rate, about 60 frames per second, with one refresh more
  latency than OpenGL.
- Full uploads every frame are about half as fast as OpenGL. Partial texture
  updates are much slower: 3.7 frames per second against 60. The candidate
  copies the whole texture on the CPU for every partial update, and also on the
  GPU while a frame still uses it. napari's labels painting makes such updates.
- The port's Windows default presentation, readback, adds about 53 ms to every
  frame of a 1920x1080 canvas and over 200 ms at 3840x2160. With native
  swapchain presentation, a whole resident 3840x2160 frame takes about 2 ms, and
  the hot-swap gates pass on this machine. Under readback, interaction depends
  on a CPU readback, which the design forbids. So the data favour native
  presentation for the hot swap (decision D18, open).
- Cold start is no slower than upstream.

## What was measured

- **Machine.** Windows 11 Pro 10.0.26200, NVIDIA GeForce RTX 4090, driver
  610.88. The reference reports OpenGL 4.6.0; the candidate uses Vulkan through
  Dawn. Three monitors make up the desktop. The primary is an HP ENVY 32 at
  2560x1440, 59 Hz nominal, on the RTX 4090. To its right are a portrait
  1080x1920 monitor on the RTX 4090, then a 1920x1080 monitor on the Intel UHD
  770.
- **Reference.** Upstream VisPy 0.17.0 on PyQt6 6.11.0 (Qt 6.11.2), CPython
  3.12.8 and NumPy 2.5.3, in `build/oracle-opengl`.
- **Candidate.** The stock napari lock with only `vispy` replaced, by the local
  R2 test wheel `66e7e9ad...` (the released `444402` plus R2's fixes; not
  admitted). The same PyQt6, Qt, CPython and NumPy.
- **Harness.** The pinned `tools/benchmark_frames.py`. Each workload ran five
  alternating upstream/candidate pairs, each with 100 warm-up and 1000 measured
  frames, a queue depth of 3 and vsync pacing (`--vsync`). Latency is the time
  from issuing a frame to its presented completion. Each run starts in a fresh
  process, and the cold start is recorded. The RGBA workload ran on
  `tools/benchmark_frames_w8.py`, which runs the harness's code with its RGBA
  format and two environment settings fixed (plan O6).
- **Workloads.** Eight of the harness's 66, covering each family and update
  kind. Images are 4096x4096 in a 3840x2160 viewport: one float32 layer, with
  the camera panning (resident) or the whole image uploaded every frame (full);
  and eight translucent RGBA layers, each with a 64x64 patch updated every
  frame (patch). Volumes are 256-cubed in 1024x1024 (MIP and translucent,
  resident) and 512-cubed in 2048x2048 (iso, the whole volume uploaded every
  frame). Points are 1,000,000 markers in 1920x1080: resident discs, and
  instanced stars with new positions every frame.
- **Window placement.** The points windows (1920x1080) and the 256-cubed volume
  windows (1024x1024) fit on the primary monitor. The 3840x2160 image viewports
  are wider than it, so their windows spanned all three monitors and both GPUs.
  Windows also clamped their height to 1901 rows, its maximum window height on
  this desktop (1940 rows with the frame), and Qt reported the clamp. The
  2048x2048 iso volume window was clamped the same way and extended below the
  primary monitor. VisPy still reported the requested size, which the harness
  checks. How those windows were composited and paced was not measured. Both
  renderers met the same layout, and the quality captures render offscreen at
  the full size.
- **Presentation.** The harness can only time native presentation, so all
  timings below use it. The cost of readback presentation, the port's Windows
  default, was measured separately (below).
- **Run.** `build/runs/w8-paced-benchmark-245` (local evidence). The first
  campaign ran from 09:07 to 12:26 local time under both presentations, and the
  user approved it as the full set. Windows turned the display off during the
  two points workloads, so they ran again, with the RGBA workload, from 12:34 to
  13:56 with the display held on (approved by the user). The tables come from
  the run's `report2.py`.

## Results with native presentation

Each value is the median over the measured runs of each run's median or p95
frame latency, or of its completed throughput. Upstream does not depend on the
port's presentation setting, so its numbers come from the same pairs.

| Workload | Upstream median / p95 | Upstream fps | Candidate median / p95 | Candidate fps | Runs measured (upstream, candidate) |
| --- | --- | --- | --- | --- | --- |
| `image-scalar-1-translucent-resident` | 16.99 / 33.49 ms | 59.98 | 32.78 / 39.84 ms | 59.48 | 5, 5 |
| `image-scalar-1-translucent-full` | 58.90 / 72.34 ms | 31.88 | 74.81 / 94.20 ms | 16.66 | 5, 4 |
| `image-rgba-8-translucent-patch` | 17.23 / 33.72 ms | 59.98 | 515.31 / 564.27 ms | 3.66 | 4, 5 |
| `volume-256-1024-mip-resident` | refused (see below) | - | 32.76 / 35.69 ms | 59.09 | 0, 5 |
| `volume-256-1024-translucent-resident` | refused (see below) | - | 32.76 / 36.39 ms | 59.22 | 0, 5 |
| `volume-512-2048-iso-full` | 369.45 / 445.37 ms | 5.26 | 687.50 / 851.27 ms | 1.92 | 5, 5 |
| `points-points-disc-4-flat-resident` | 16.65 / 33.37 ms | 59.97 | 33.09 / 34.89 ms | 59.97 | 5, 5 |
| `points-instanced-star-16-flat-positions` | 130.20 / 196.37 ms | 10.95 | 168.55 / 189.13 ms | 9.29 | 4, 5 |

- **Resident scenes keep pace.** Both renderers sustain the display's refresh
  rate, about 60 frames per second, on resident images, volumes and points. The candidate's frames complete about
  one refresh later: a median of two refresh intervals from issue to presented
  completion, where OpenGL takes one. Its tail is tighter (p95 within 40 ms).
- **Full uploads are about half as fast.** Uploading a 64 MiB image every frame,
  the candidate completes 16.7 frames per second against 31.9; uploading a
  512 MiB volume, 1.9 against 5.3. Re-uploading the markers' vertex data (56 MB)
  with new positions every frame, 9.3 against 11.0. Upstream's four run
  medians on that workload fall into two groups, 100-102 ms and 159-164 ms, so
  its median latency describes neither.
- **Partial texture updates are much slower.** Updating a 64x64 patch of each of
  eight 4096x4096 RGBA layers every frame, the candidate completes 3.7 frames per
  second against 60. The cause is below.
- **Cold start is no slower.** The harness's cold start covers importing the
  renderer, building the scene and taking three offscreen quality captures,
  saved to disk. It takes 1.6-4.2 s on the candidate against 1.7-4.6 s
  upstream (2.4 s against 4.1 s for the resident image).

### Where the candidate's frame time goes

From the harness's per-frame telemetry, in milliseconds per measured frame: the
median over runs of each run's median, except native interpretation and
texture conversion, which are the measured window's totals divided by its
frames.

| Workload | Candidate paint (CPU) | GLIR parse | Python packing | Native interpretation | Texture conversion | Candidate GPU passes | Upstream paint (CPU) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Image, resident | 1.37 | 0.67 | 0.04 | 0.58 | 0 | 0.33 | 13.96 |
| Image, full 64 MiB upload | 42.11 | 40.53 | 18.27 | 23.03 | 5.36 | 0.20 | 14.67 |
| RGBA, eight 64x64 patches | 269.54 | 268.15 | 0.16 | 243.01 | 128.80 | 1.90 | 14.50 |
| Volume MIP, resident | 2.61 | 1.24 | 0.08 | 1.09 | 0 | 0.59 | refused |
| Volume translucent, resident | 2.76 | 1.29 | 0.08 | 1.17 | 0 | 1.05 | refused |
| Volume iso, full 512 MiB upload | 322.25 | 319.85 | 143.60 | 180.19 | 25.11 | 3.47 | 97.77 |
| Points discs, resident | 0.99 | 0.66 | 0.04 | 0.59 | 0 | 2.16 | 14.29 |
| Points instanced, new positions | 43.04 | 41.92 | 10.62 | 17.36 | 0 | 11.40 | 21.82 |

The GLIR parse runs inside the paint, and the Python packing and native
interpretation run inside the parse. The candidate's GPU time (timestamp
queries over its render passes, 64 µs resolution, uploads and copies excluded)
is small in every case. Its upload frames are bound by CPU work in the paint:
Python's packing of the uploaded array into GLIR commands, then the native
interpretation's conversion and staging of it. That is the cost to reduce if
full-frame uploads matter.

The upstream paint includes OpenGL's blocking buffer swap, so it is not a
measure of its CPU work. Upstream's GPU time is recorded as a timestamp pair
around its whole paint. On every paced resident scene it reads 12-14 ms, which
matches the wait for the next refresh rather than drawing work, so it is not
comparable with the candidate's pass times and is left out.

### Partial texture updates

The candidate keeps a CPU shadow of each texture and versions it. When an update
arrives while a queued frame still uses the texture, the candidate makes a new
revision instead of changing the texture in place. With the harness's queue
depth of 3, every patch meets a queued frame. So for each 64x64 patch
(16 KiB), the candidate:

- copies the texture's 64 MiB CPU shadow into the new revision (the GLIR `DATA`
  handler in `cpp/runtime.cpp`);
- copies the whole shadow again to apply the patch, because
  `apply_texture_data` (`cpp/runtime_texture.hpp`) rebuilds the shadow for every
  partial update, even when no frame uses the texture. This second copy is the
  128.8 ms of texture conversion per frame for eight patches. The first copy and
  the GPU work below fall in the rest of the 243 ms of native interpretation;
- allocates a new 64 MiB GPU texture and copies the old one into it on the GPU
  (`upload_texture`): 7,992 texture allocations and 536 GB copied over the
  1,000 measured frames.

OpenGL uploads 16 KiB per texture in place, with no new storage.

This matters for the hot swap. napari 0.9.2 paints labels with partial texture
updates (`napari/_vispy/layers/labels.py`, `_on_partial_labels_update`). Every
brush event on a large labels layer therefore costs at least one full CPU copy
of the labels texture. While a queued frame still uses the texture, it also
costs a second CPU copy and a full GPU copy. A 3D labels volume makes each copy
proportionally larger. Backlog B18.

## Readback presentation

Readback is the port's Windows default for Qt canvases. Each paint draws the
scene, reads the framebuffer back to the CPU and paints it with `QPainter`. The
harness cannot time it (see below), so `readback_cost.py` draws the harness's
own scenes unpaced, 100 warm-up and 1000 measured frames, and times the
backend's three paint steps. Medians in milliseconds, at 3840x2160:

| Workload | Presentation | Scene draw | Framebuffer readback | Qt image paint | Interval between paints |
| --- | --- | --- | --- | --- | --- |
| Image, resident | readback | 1.12 | 209.22 | 3.65 | 225.93 |
| Image, resident | native | 0.66 | - | - | 2.27 |
| Image, full 64 MiB upload | readback | 30.74 | 196.89 | 3.17 | 250.58 |
| Image, full 64 MiB upload | native | 30.54 | - | - | 46.46 |

So readback limits a 4K canvas to about 4 frames per second, whatever the scene.
`readback_split.py` splits the readback into its steps, on a hidden canvas with
20 reads per size:

| Framebuffer | Native read | NumPy copy | `bytes` copy | `QImage` copy |
| --- | --- | --- | --- | --- |
| 1920x1080 | 47.71 | 1.80 | 1.64 | 1.85 |
| 2560x1440 | 84.51 | 2.97 | 2.80 | 3.09 |
| 3840x2160 | 193.22 | 7.27 | 6.91 | 7.21 |

The native read costs about 23 ns per pixel. It allocates a new staging buffer
for every read, waits for it to map, and converts every texel through a generic
per-format routine (`read_canvas` in `cpp/runtime.cpp`). The backend then copies
the image three more times in Python (`_read_dawn_framebuffer` in
`src/vispy/app/backends/_qt.py`). Even at 1920x1080, readback costs about 53 ms
per frame, so a canvas of that size cannot exceed about 19 frames per second.
Backlog B19 is to make the read a row copy into a reused buffer and to remove
the extra copies.

## Presentation choice (D3)

D3 takes the presentation path from these measurements. The data:

- **Cost.** At 3840x2160, readback paints are 226 ms apart for a resident image;
  native paints, 2.3 ms. The design forbids interaction that depends on a CPU
  readback (design :631).
- **Gates.** Stock napari's hot-swap audit (`tools/audit_hot_swap.py`, scenario
  `stock_napari`) passes under both presentations on this machine
  (`gates-presentation/`): `renderer_gl` and `no_gl_context_or_draw` both PASS,
  with no renderer or context GL events. Both records show the same host GL
  events, napari's own Qt OpenGL and PyOpenGL imports. The audit watches public
  GL exports, entry-point resolution, native loads and the process tree; it
  does not cover private or statically linked GL implementations. So the W3
  question, how a driver's GL activity inside a native swapchain path counts,
  did not arise here: none was observed with this driver.
- **Reliability.** Native presentation lost one presented completion in 50
  candidate runs. Upstream lost two in 85, so lost completions are not specific
  to native presentation. All three happened in windows that spanned monitors
  (run-level findings).
- **Unverified.** The napari parity suites, including Qt screenshots and
  overlays, ran under readback. Native presentation also stays outside strict
  Windows no-OpenGL qualification, because some Vulkan Win32 drivers resolve
  WGL entry points (`_qt.py`).

**Recommendation (D18, open for the user).**
- Select native presentation for the hot swap on Windows, at R2, once the
  napari parity suites pass under it.
- Count GL activity that the audit attributes to a driver's presentation path,
  outside the renderer, as host activity in the hot-swap profile only.
- Keep readback for strict no-OpenGL qualification, and make it cheaper (B19).

## What the pinned harness could not measure

- **Readback presentation.** Under readback, the candidate reports no
  presentation completions, so every candidate run stops at frame 0 ("failed or
  unpresented completion frame 0"). Its cost is measured separately above.
- **Upstream resident volumes.** Upstream VisPy re-uploads two 76-byte buffers in
  every resident volume frame (2,000 uploads over 1,000 frames). The harness's
  resident rule allows no uploads, so it refuses those runs ("forbidden measured
  work"). Their recorded latency, a median of 16.7-17.8 ms at 60 frames per
  second, shows them paced like the resident image.
- **RGBA images.** The pinned harness passes `texture_format="rgba8"`, and VisPy
  expands the `r` of a format to the data's channels, so both renderers reject
  the resulting `rgbagba8` in every RGBA workload. The RGBA results above come
  from `tools/benchmark_frames_w8.py`, which fixes that line.

## Run-level findings

- **Lost completions, on both sides.** Three runs never received a presented
  completion for one frame. The harness waited its full 1,200 s and failed the
  run:
  - candidate, native presentation: the full-upload image, after 66 of 68
    warm-up frames completed;
  - upstream: the resident image after 136 presents, and the RGBA patch workload
    after 67.

  All three were image workloads, whose windows spanned the three monitors and
  both GPUs. Those workloads account for 40 of the runs that could report
  completions. The other 95, whose windows did not span monitors, lost none.
  The cause was not found.
- **The display's power state changes presentation.** Windows turned the
  display off after its 10-minute idle timeout (Kernel-Power event 566, reason
  12) from 11:51:49 to 12:24:18 local time, during the two points workloads.
  OpenGL then presented unpaced (547 frames per second on resident points),
  and the candidate's swapchain presented at about 7 Hz. Those runs were
  discarded and repeated with the display held on.
- **Unattributed paints come from desktop activity.** The plan asked why
  unattributed Qt expose paints invalidated the Native65 five-pair timing run.
  Five runs here show work outside the harness's frames. Where the source is
  recorded, it is the desktop in use:
  - one paint across the display waking at 12:24:18, on mouse input;
  - two paints at 12:35, with the display held on (source not recorded);
  - 56 and 53 unattributed upstream presents at 12:43-12:47: Qt repainted the
    window outside the harness's frames, most likely because other windows
    covered or exposed it;
  - 11 and 7 offscreen renders with readbacks inside two upstream measured
    windows (12:45 and 09:43). Upstream VisPy's `SceneCanvas` renders offscreen
    to pick a visual on every mouse press, wheel or gesture event over the
    canvas, so these are mouse input.

  The harness fails a run with readbacks ("forbidden measured work"). It only
  flags unattributed paints and presents as instrumentation gaps, so such runs
  count as measured. Two of them are in the tables: a candidate resident-points
  run and an upstream instanced-points run. Their numbers match their
  undisturbed neighbours'.

  Whether the Native65 run met the same desktop activity was not recorded.
  Clean timing needs an idle desktop: the display held on, no input, and no
  window over the canvas.

## Caveats

- One machine and one driver. The image and iso-volume windows did not fit the
  primary monitor (above).
- The candidate is a local test wheel with R2's fixes, not an admitted artifact.
- The desktop was in use during parts of the campaign (above). This session's
  own light work (git operations, small scripts) ran from about 10:16 to 10:30
  local time, during the full-upload image runs, including the candidate run
  that lost a completion.
- The readback costs come from unpaced draws of the harness's scenes on the
  candidate, not from the harness's paired runs.
