"""Small analytic volume fixtures shared by installed OpenGL and Dawn."""

from __future__ import annotations

import hashlib

import numpy as np

try:
    from .fixture_gloo import freeze
except ImportError:
    from fixture_gloo import freeze

SIZE = (96, 96)
METHODS = ("mip", "minip", "attenuated_mip", "translucent", "additive", "iso", "average")
CASES = METHODS + ("mip_linear", "plane_mip", "clipped_mip", "mesh_front_iso")


def phantom():
    axis = np.linspace(-1, 1, 32, dtype=np.float32)
    z, y, x = np.meshgrid(axis, axis, axis, indexing="ij")
    inside = (x / .7) ** 2 + (y / .55) ** 2 + (z / .4) ** 2 <= 1
    return np.where(inside, 1.0, .2).astype(np.float32)


def render(name, backend="dawn_headless"):
    if name not in CASES:
        raise ValueError(name)
    from vispy import scene
    from vispy.visuals.volume import VolumeVisual

    canvas = scene.SceneCanvas(app=backend, size=SIZE, show=backend == "pyqt6",
        decorate=False, bgcolor=(0, 0, 0, 1), config={"samples": 0})
    if backend == "pyqt6":
        canvas.app.native.setQuitOnLastWindowClosed(False)
        canvas._backend._vispy_warmup()
    commands, shaders = [], {}
    parser = canvas.context.shared.parser
    original = parser.parse

    def log(batch):
        for command in batch:
            commands.append(freeze(command))
            if command[0] == "DATA" and isinstance(command[3], str):
                shaders[str(command[1])] = command[3]
        return original(batch)

    parser.parse = log
    try:
        data = phantom()
        method = name if name in METHODS else ("iso" if name == "mesh_front_iso" else "mip")
        view = canvas.central_widget.add_view()
        camera = scene.cameras.TurntableCamera(fov=0, azimuth=0, elevation=0,
            distance=100, center=(15.5, 15.5, 15.5), scale_factor=40, up="+z")
        view.camera = camera
        kwargs = {"method": method, "clim": (0, 1), "cmap": "grays",
                  "relative_step_size": .5, "threshold": .6,
                  "interpolation": "linear" if name == "mip_linear" else "nearest",
                  "texture_format": "r32f"}
        if name == "plane_mip":
            kwargs.update(raycasting_mode="plane", plane_position=(15.5, 15.5, 15.5),
                          plane_normal=(0, 1, 0), plane_thickness=1)
        if name == "clipped_mip":
            kwargs.update(clipping_planes=np.array([[[15.5, 15.5, 15.5], [1, 0, 0]]], np.float32),
                          clipping_planes_coord_system="visual")
        if name == "mesh_front_iso":
            vertices = np.array([[12.5, -5, 12.5], [18.5, -5, 12.5],
                                 [12.5, -5, 18.5], [18.5, -5, 18.5]], np.float32)
            mesh = scene.visuals.Mesh(vertices=vertices,
                faces=np.array([[0, 1, 2], [2, 1, 3]], np.uint32),
                color=(1, 0, 0, 1), shading=None, parent=view.scene)
            mesh.order = 0
        volume = scene.visuals.Volume(data, parent=view.scene, **kwargs)
        volume.order = 1
        image = np.array(canvas.render(size=SIZE, alpha=True), copy=True)
        params = {"case": name, "method": method, "size": list(SIZE),
            "shape": list(data.shape), "dtype": data.dtype.str,
            "data_sha256": hashlib.sha256(data.tobytes()).hexdigest(),
            "clim": [0, 1], "texture_format": "r32f", "relative_step_size": .5,
            "interpolation": kwargs["interpolation"], "threshold": .6,
            "raycasting_mode": kwargs.get("raycasting_mode", "volume"),
            "camera": {"fov": 0, "azimuth": 0, "elevation": 0, "distance": 100,
                       "center": [15.5, 15.5, 15.5], "scale_factor": 40, "up": "+z"},
            "exposed_methods": list(VolumeVisual._rendering_methods),
            "exposed_raycasting_modes": list(VolumeVisual._raycasting_modes)}
        return image, commands, shaders, params
    finally:
        canvas.close()


def masks(name, shape):
    """Fixed one-pixel bands from camera projection and analytic data."""
    height, width = shape[:2]
    y, x = np.mgrid[:height, :width]
    world_x = 15.5 + (x + .5 - width / 2) / 2.4
    world_z = 15.5 + (height / 2 - y - .5) / 2.4
    xi = np.clip(np.floor(world_x + .5).astype(int), 0, 31)
    zi = np.clip(np.floor(world_z + .5).astype(int), 0, 31)
    projected = phantom().max(axis=1)[zi, xi] > .6
    outer = (world_x >= -.5) & (world_x <= 31.5) & (world_z >= -.5) & (world_z <= 31.5)
    categories = projected.astype(np.uint8) + outer.astype(np.uint8)
    if name == "clipped_mip":
        categories *= world_x >= 15.5
    if name == "mesh_front_iso":
        categories += ((world_x >= 12.5) & (world_x <= 18.5) &
                       (world_z >= 12.5) & (world_z <= 18.5)).astype(np.uint8) * 4
    boundary = np.zeros_like(projected)
    for axis in (0, 1):
        boundary |= categories != np.roll(categories, 1, axis=axis)
        boundary |= categories != np.roll(categories, -1, axis=axis)
    edge = boundary.copy()
    for axis in (0, 1):
        edge |= np.roll(boundary, 1, axis=axis) | np.roll(boundary, -1, axis=axis)
    return ~edge, edge


def assert_landmarks(name, image):
    assert image.shape == (96, 96, 4)
    assert image[2, 2].tolist() == [0, 0, 0, 255]
    if name in ("mip", "mip_linear", "plane_mip", "additive"):
        assert image[48, 48, :3].min() >= 250, (name, image[48, 48])
    if name == "minip":
        assert np.max(np.abs(image[48, 48, :3].astype(int) - 51)) <= 1
    if name == "mesh_front_iso":
        assert image[48, 48].tolist() == [255, 0, 0, 255]
    if name == "clipped_mip":
        assert image[48, 32].tolist() == [0, 0, 0, 255]
        assert image[48, 64, :3].min() >= 250
    assert np.any(image[..., :3] != 0), "a blank frame cannot admit a volume method"
