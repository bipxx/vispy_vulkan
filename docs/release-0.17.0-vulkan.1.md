# VisPy Vulkan 0.17.0+vulkan.1

This is the first public release of the VisPy 0.17.0 compatibility fork using
Dawn for Vulkan rendering. The GitHub Release tag is `v0.17.0-vulkan.1`.

## Install

```sh
pip install "vispy==0.17.0+vulkan.1" --extra-index-url https://bipxx.github.io/vispy_vulkan/simple/
```

The [PEP 503 index](https://bipxx.github.io/vispy_vulkan/simple/) links to the
release assets with SHA256 fragments. Pin the exact local version as shown so
a PyPI VisPy release cannot take precedence.

## Wheels

Both wheels require CPython 3.12 and x86_64. Assets are under
`https://github.com/bipxx/vispy_vulkan/releases/download/v0.17.0-vulkan.1/`.

| Wheel | Bytes | SHA256 |
| --- | --- | --- |
| `vispy-0.17.0+vulkan.1-cp312-cp312-win_amd64.whl` | 6,808,394 | `5c7142f38b0867fc744a7fe6025b8397f1bada46641b6d05da0d54dadbfab29e` |
| `vispy-0.17.0+vulkan.1-cp312-cp312-manylinux_2_39_x86_64.whl` | 10,557,399 | `66f35ab0dae878af1744f2061be1042bd2c5abfd24d3192c7456865f2c6fd3f7` |

## Qualification and limits

On these exact wheels, all eight mandatory strict no-OpenGL rows pass: headless
and QWidget with selected PyQt5, PyQt6 and PySide6 profiles, on Windows Vulkan
and WSL Linux lavapipe X11. These are the selected no-OpenGL profiles recorded
in the matrix; the install command alone does not supply those profiles.
Both Tk candidates are strictly admitted: `tk-state-resource-1` (120 criteria)
and `tk-capture-1` (8 criteria). All 23 required CI jobs pass.

Tk uses manual event pumping and copies RGB through CPU memory to a PhotoImage;
RGBA capture is separate. This mode does not promise Vulkan window presentation,
vsync or transparent window compositing. Recovery checks use injected device
loss. See the [finite Tk scope and differences](https://github.com/bipxx/vispy_vulkan/blob/main/docs/practical-compatibility-release.md).

Linux requires glibc 2.38, GCC 13's libstdc++ (`GLIBCXX_3.4.31`) and libX11.
Auditwheel's tag is `manylinux_2_39_x86_64`. Only WSL software Vulkan is
qualified on Linux; native Linux GPUs are unverified. No wheels for other
Python versions or macOS are included. Metal is experimental, build-only and
not qualified for graphics. The napari 0.10.0, Glue and napari-threedee host
rows are optional evidence. Full upstream parity is not the release target.

## Known Windows startup stall

A rare Windows startup stall remains documented as backlog B22 (D33) and is
not release-blocking. A captured recurrence lost the process's default thread
pool early in startup; the closer is unidentified. To report a recurrence,
run the launch under the external watcher from a repository checkout:

```text
python tools/pool_watch_external.py --output <events.jsonl> -- <command>
```

Include the events file, launch command, package versions and platform details
in the report. See the [startup diagnosis](https://github.com/bipxx/vispy_vulkan/blob/main/docs/threedee-startup-diagnosis.md).
D33 makes the stall release-blocking again if it recurs.

## Licensing and evidence

This implementation is AGPL-3.0-only. The unchanged original VisPy BSD license
(`LICENSE-BSD`) and third-party notices ship in the wheels; see
[LICENSING.md](https://github.com/bipxx/vispy_vulkan/blob/main/LICENSING.md).

The [R2 release plan](https://github.com/bipxx/vispy_vulkan/blob/main/docs/superpowers/plans/2026-11-04-r2-release.md) records the
qualification and promotion work. The [consolidated plan](https://github.com/bipxx/vispy_vulkan/blob/main/docs/superpowers/plans/2026-10-28-consolidated-plan.md)
records scope and decisions D32-D36. The [no-OpenGL matrix](https://github.com/bipxx/vispy_vulkan/blob/main/compat/no-opengl-matrix.json)
binds the strict results to exact artifacts, environments and evidence.
