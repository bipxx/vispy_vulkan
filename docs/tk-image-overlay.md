# Image and line overlay on Tk

The [runnable example](../examples/tk_image_overlay.py) uses familiar VisPy
`SceneCanvas`, `Image`, `Line`, `STTransform` and `PanZoomCamera` interfaces.
It displays a nearest-filtered RGBA image and a horizontal AGG line overlay.
Drag to pan, use the camera's wheel interaction to zoom, resize the window,
and close it to exit.

Use an existing installed Vulkan/Tk environment with NumPy. The
[Tk installation recipe](install-tk-cp312.md) describes the selected wheelhouse
and its external interpreter, toolkit and driver prerequisites; its public
download remains unpublished. From an existing source checkout:

```console
python examples/tk_image_overlay.py
```

The example is a standalone source file; it can also be copied into the
installed environment without cloning or building the dependency trees.
It uses manual event pumping and closes its canvas/application on exit.
The image camera uses downward-positive Y coordinates to display the first
array row at the top. Image and overlay data can be updated through their
ordinary `set_data` methods.

## Verified finite behavior

The [source regression](../tests/native/test_tkinter_image_overlay.py) runs the
example's actual scene factory. It passes on Windows hardware Vulkan and WSL
software Vulkan with the unchanged admitted native libraries and matching pure
package sources. Independent literal 3-by-3 RGBA patches and actual Tk RGB
presentation points check:

- Four authored image quadrants and an opaque white overlay.
- A cyan image update, a moved magenta line, and pixels vacated by the old line.
- Rejection of complex image data, preserved output, and a valid orange update
  on the same image and line objects.
- Resizing from 240-by-180 to 360-by-240 with the same world rectangle.
- A generated right36/down24 drag producing rectangle(-.4,-.3,4,3), correctly
  moved image/line samples and a vacated overlay sample.

Reached controls that ignore the image update, ignore the line update or ignore
panning each fail their intended assertion on both profiles. Every worker ends
with all nine native resource gauges at zero. The code needed no renderer/SDK
build or new environment. Local reconstruction/evidence entry points are
`build/runs/image-overlay-windows-187/` and `build/runs/image-overlay-wsl-188/`;
their native projections and caches were cleaned after retention.

This is source workflow coverage. It does not establish a new installed Image/
Line admission, full-image parity, all data formats/interpolation/clim/line
joins/caps, default wheel sensitivity, mixed-monitor DPI or physical input
qualification. The canvas requests samples0; these checks do not qualify actual
multisample storage. The historical installed admissions and the broader API
inventory retain their original scope in the [practical baseline](qualified-tk-baseline.md).
