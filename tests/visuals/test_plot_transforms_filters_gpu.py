# SPDX-License-Identifier: AGPL-3.0-only
"""GPU acceptance for W3-3 (API-05/API-06): vispy.plot, transforms, filters, PNG roundtrip, and collections."""
from __future__ import annotations

import gc
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _cleanup_collection(coll) -> None:
    """Explicitly release standalone Collection GLObjects before canvas teardown."""
    if coll is None:
        return
    for prog in list(getattr(coll, '_programs', ()) or ()):
        try:
            prog.delete()
        except Exception:
            pass
    for attr in ('_vertices_buffer', '_indices_buffer', '_uniforms_texture'):
        obj = getattr(coll, attr, None)
        if obj is not None:
            try:
                obj.delete()
            except Exception:
                pass


def test_plot_fig_subplots_2d_3d_colorbar_and_png_roundtrip(tmp_path: Path):
    """Verify Fig & PlotWidget subplots (.plot, scatter, .image, .colorbar, .histogram, .mesh) and lossless PNG IO."""
    from vispy import _dawn, scene
    from vispy.geometry import create_sphere
    from vispy.io import read_png, write_png
    import vispy.plot as vplot
    from vispy.plot import Fig, PlotWidget

    assert not hasattr(vplot, 'SubPlot')
    fig = Fig(
        bgcolor='black',
        size=(640, 480),
        show=False,
        app='dawn_headless',
        config={'samples': 0},
    )
    try:
        fig.set_current()
        assert fig.plot_widgets == ()

        # Top-left [0, 0]: 2D line + markers (.plot) plus marker-only scatter series (width=0) and scene.Markers.
        ax_line = fig[0, 0]
        assert isinstance(ax_line, PlotWidget)
        assert not hasattr(ax_line, 'scatter')
        xs = np.linspace(0.0, 2.0 * math.pi, 32, dtype=np.float32)
        ys = np.sin(xs).astype(np.float32)
        line_vis = ax_line.plot(
            np.column_stack([xs, ys]),
            color='#00ff40',
            width=3.0,
            symbol='o',
            marker_size=8.0,
            face_color='#ff2040',
            edge_color='white',
            title='Sine & Scatter',
            xlabel='Phase',
            ylabel='Amplitude',
        )
        assert line_vis is not None
        assert ax_line.title.text == 'Sine & Scatter'
        assert ax_line.xlabel.text == 'Phase'
        assert ax_line.ylabel.text == 'Amplitude'
        assert ax_line.xaxis is not None and ax_line.yaxis is not None

        scatter_pts = np.column_stack(
            [
                np.linspace(0.4, 5.8, 10, dtype=np.float32),
                np.cos(np.linspace(0.4, 5.8, 10, dtype=np.float32)),
            ]
        )
        scatter_line = ax_line.plot(
            scatter_pts,
            width=0.0,
            symbol='s',
            marker_size=10.0,
            face_color='#2090ff',
            edge_color='yellow',
        )
        assert scatter_line in ax_line.visuals
        extra_markers = scene.Markers(
            pos=np.array([[math.pi, 0.0]], dtype=np.float32),
            size=12.0,
            face_color='magenta',
            edge_color='white',
            parent=ax_line.view.scene,
        )
        assert extra_markers is not None

        # Top-right [0, 1]: 2D scalar image + right colorbar.
        ax_img = fig[0, 1]
        gx = np.linspace(0.0, 1.0, 32, dtype=np.float32)
        gy = np.linspace(0.0, 1.0, 24, dtype=np.float32)
        scalar_field = (0.65 * gx[None, :] + 0.35 * gy[:, None]).astype(np.float32)
        img_vis = ax_img.image(scalar_field, cmap='viridis', clim=(0.0, 1.0), fg_color='white')
        cbar_vis = ax_img.colorbar(
            cmap='viridis',
            position='right',
            label='Scale',
            clim=(0.0, 1.0),
            border_width=1.0,
            border_color='white',
        )
        assert img_vis is not None and cbar_vis is not None

        # Bottom-left [1, 0]: 1D histogram.
        ax_hist = fig[1, 0]
        rng = np.random.default_rng(20261115)
        hist_samples = rng.normal(loc=0.0, scale=1.0, size=400).astype(np.float32)
        hist_vis = ax_hist.histogram(hist_samples, bins=8, color='#ff8800', orientation='h')
        assert hist_vis is not None

        # Bottom-right [1, 1]: 3D smooth-shaded sphere mesh.
        ax_mesh = fig[1, 1]
        sphere_md = create_sphere(rows=12, cols=16, radius=1.2, method='latitude')
        mesh_vis = ax_mesh.mesh(
            meshdata=sphere_md,
            color=(0.15, 0.75, 1.0, 1.0),
            shading='smooth',
        )
        assert mesh_vis is not None
        assert len(fig.plot_widgets) == 4

        frame_rgba = np.array(fig.render(alpha=True), copy=True)
        assert frame_rgba.shape == (480, 640, 4)
        assert frame_rgba.dtype == np.uint8

        q00 = frame_rgba[:240, :320]
        q01 = frame_rgba[:240, 320:]
        q10 = frame_rgba[240:, :320]
        q11 = frame_rgba[240:, 320:]

        for idx, quad in enumerate((q00, q01, q10, q11)):
            non_black = np.any(quad[..., :3] > 10, axis=-1)
            assert float(non_black.mean()) > 0.08, f'Quadrant {idx} unexpectedly empty'
            uniq = np.unique(quad.reshape(-1, 4), axis=0)
            assert len(uniq) >= 8, f'Quadrant {idx} has too few distinct colors: {len(uniq)}'

        # Quadrant [0, 0]: green line (#00ff40) and red/blue/magenta markers must appear.
        green_line_px = (q00[..., 1] > 180) & (q00[..., 0] < 90) & (q00[..., 2] < 120)
        warm_marker_px = (q00[..., 0] > 180) & (q00[..., 1] < 100)
        assert int(green_line_px.sum()) >= 15
        assert int(warm_marker_px.sum()) >= 6

        # Quadrant [0, 1]: viridis high-end yellow-green and low-end purple-blue pixels must appear.
        viridis_hi = (q01[..., 0] > 180) & (q01[..., 1] > 190) & (q01[..., 2] < 100)
        viridis_lo = (q01[..., 2] > 95) & (q01[..., 0] < 90) & (q01[..., 1] < 90)
        assert int(viridis_hi.sum()) >= 25
        assert int(viridis_lo.sum()) >= 25

        # Quadrant [1, 0]: orange histogram bars (#ff8800).
        orange_bars = (q10[..., 0] > 200) & (q10[..., 1] > 95) & (q10[..., 2] < 60)
        assert int(orange_bars.sum()) >= 40

        # Quadrant [1, 1]: smooth-shaded cyan-blue 3D sphere (B > R + 40 with shading gradient).
        sphere_px = (q11[..., 2].astype(np.int16) - q11[..., 0].astype(np.int16)) > 40
        assert int(sphere_px.sum()) >= 80
        assert float(q11[sphere_px, 2].std()) > 5.0

        # Lossless PNG roundtrip of fig.render(alpha=True) RGBA frame.
        png_path = tmp_path / 'fig_render_rgba.png'
        write_png(str(png_path), frame_rgba)
        reloaded = read_png(str(png_path))
        assert reloaded.shape == frame_rgba.shape and reloaded.dtype == np.uint8
        np.testing.assert_array_equal(reloaded, frame_rgba)
    finally:
        fig.close()
        gc.collect()
        _dawn.process_events()


def test_gpu_polar_log_and_chain_transforms_pixel_displacement():
    """Verify GPU PolarTransform, LogTransform, and ChainTransform displace rendered geometry accurately."""
    from vispy import _dawn, scene
    from vispy.visuals.transforms import (
        ChainTransform,
        LogTransform,
        NullTransform,
        PolarTransform,
        STTransform,
    )

    size = (128, 128)
    canvas = scene.SceneCanvas(
        app='dawn_headless',
        size=size,
        show=False,
        bgcolor='black',
        config={'samples': 0},
    )
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(
            rect=(0, 0, *size), aspect=None, flip=(False, True, False)
        )

        # 1. PolarTransform + STTransform in ChainTransform:
        # Input vertices in (theta, r, z) around theta=0, r in [36, 48].
        polar_verts_east = np.array(
            [[-0.12, 36.0, 0.0], [-0.12, 48.0, 0.0], [0.12, 36.0, 0.0], [0.12, 48.0, 0.0]],
            dtype=np.float32,
        )
        quad_faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
        polar_mesh = scene.visuals.Mesh(
            vertices=polar_verts_east,
            faces=quad_faces,
            color=(1.0, 0.0, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        polar_mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)

        polar_chain = ChainTransform([STTransform(translate=(64.0, 64.0, 0.0)), PolarTransform()])
        polar_mesh.transform = polar_chain
        img_east = np.array(canvas.render(size=size, alpha=True), copy=True)
        # CPU reference maps (0, 42, 0) -> (106, 64, 0).
        cpu_east = polar_chain.map(np.array([[0.0, 42.0, 0.0]], dtype=np.float32))[0]
        np.testing.assert_allclose(cpu_east[:2], [106.0, 64.0], atol=1e-4)
        np.testing.assert_allclose(img_east[64, 106], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(img_east[106, 64], [0, 0, 0, 255], atol=2)

        # Displace theta by +pi/2 -> maps (pi/2, 42, 0) -> (64, 106, 0).
        polar_verts_south = polar_verts_east.copy()
        polar_verts_south[:, 0] += math.pi / 2.0
        polar_mesh.set_data(vertices=polar_verts_south, faces=quad_faces, color=(1.0, 0.0, 0.0, 1.0))
        img_south = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(img_south[106, 64], [255, 0, 0, 255], atol=2)
        np.testing.assert_allclose(img_south[64, 106], [0, 0, 0, 255], atol=2)

        polar_mesh.parent = None

        # 2. LogTransform + ChainTransform:
        # Raw quad spans x in [10, 100], y in [4, 16].
        log_verts = np.array(
            [[10.0, 4.0, 0.0], [100.0, 4.0, 0.0], [10.0, 16.0, 0.0], [100.0, 16.0, 0.0]],
            dtype=np.float32,
        )
        log_mesh = scene.visuals.Mesh(
            vertices=log_verts,
            faces=quad_faces,
            color=(0.0, 1.0, 0.0, 1.0),
            shading=None,
            parent=view.scene,
        )
        log_mesh.set_gl_state(blend=False, depth_test=False, cull_face=False)
        log_mesh.transform = NullTransform()
        img_untransformed = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(img_untransformed[10, 55], [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(img_untransformed[70, 40], [0, 0, 0, 255], atol=2)

        # LogTransform(base=(10, 2, 0)) maps x:[10,100]->[1,2], y:[4,16]->[2,4];
        # STTransform(scale=(20, 20, 1), translate=(10, 10, 0)) maps x->[30, 50], y->[50, 90].
        log_chain = ChainTransform(
            [
                STTransform(scale=(20.0, 20.0, 1.0), translate=(10.0, 10.0, 0.0)),
                LogTransform(base=(10.0, 2.0, 0.0)),
            ]
        )
        cpu_bounds = log_chain.map(log_verts)[:, :2]
        np.testing.assert_allclose(cpu_bounds.min(axis=0), [30.0, 50.0], atol=1e-4)
        np.testing.assert_allclose(cpu_bounds.max(axis=0), [50.0, 90.0], atol=1e-4)

        log_mesh.transform = log_chain
        img_log = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(img_log[70, 40], [0, 255, 0, 255], atol=2)
        np.testing.assert_allclose(img_log[10, 55], [0, 0, 0, 255], atol=2)
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_gpu_filters_alpha_color_clipper_wireframe_isoline_attach_update_remove():
    """Verify GPU attach, property mutation, and detach pixel deltas for Alpha, ColorFilter, Clipper, WireframeFilter, and IsolineFilter."""
    from vispy import _dawn, scene
    from vispy.visuals.filters import (
        Alpha,
        Clipper,
        ColorFilter,
        IsolineFilter,
        WireframeFilter,
    )

    size = (96, 96)
    canvas = scene.SceneCanvas(
        app='dawn_headless',
        size=size,
        show=False,
        bgcolor='black',
        config={'samples': 0},
    )
    try:
        canvas.set_current()
        canvas.central_widget.border_width = 0
        view = canvas.central_widget.add_view(border_width=0)
        view.camera = scene.cameras.PanZoomCamera(
            rect=(0, 0, *size), aspect=None, flip=(False, True, False)
        )

        full_verts = np.array(
            [[0.0, 0.0, 0.0], [96.0, 0.0, 0.0], [0.0, 96.0, 0.0], [96.0, 96.0, 0.0]],
            dtype=np.float32,
        )
        faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
        mesh = scene.visuals.Mesh(
            vertices=full_verts,
            faces=faces,
            color='white',
            shading=None,
            parent=view.scene,
        )
        mesh.set_gl_state(
            blend=True,
            blend_func=('src_alpha', 'one_minus_src_alpha', 'one', 'one_minus_src_alpha'),
            depth_test=False,
            cull_face=False,
        )

        # --- Part A: Alpha + ColorFilter + Clipper ---
        base_img = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(base_img[48, 48], [255, 255, 255, 255], atol=1)

        f_color = ColorFilter((1.0, 0.5, 0.0, 1.0))
        f_alpha = Alpha(0.5)
        f_clip = Clipper(bounds=(24, 16, 48, 64))
        for flt in (f_color, f_alpha, f_clip):
            mesh.attach(flt)

        filtered_1 = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(filtered_1[48, 48, :3], [128, 64, 0], atol=3)
        np.testing.assert_allclose(filtered_1[48, 8, :3], [0, 0, 0], atol=1)
        np.testing.assert_allclose(filtered_1[4, 48, :3], [0, 0, 0], atol=1)

        # Mutate properties dynamically.
        f_color.filter = (0.0, 1.0, 0.5, 1.0)
        f_alpha.alpha = 0.8
        f_clip.bounds = (0, 0, 48, 96)
        filtered_2 = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(filtered_2[48, 24, :3], [0, 204, 102], atol=3)
        np.testing.assert_allclose(filtered_2[48, 72, :3], [0, 0, 0], atol=1)

        # Detach all three -> exact baseline restoration.
        for flt in (f_clip, f_alpha, f_color):
            mesh.detach(flt)
        restored_a = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_array_equal(restored_a, base_img)

        # --- Part B: WireframeFilter ---
        mesh.set_data(vertices=full_verts, faces=faces, color=(0.0, 0.0, 0.8, 1.0))
        blue_base = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_allclose(blue_base[24, 72, :3], [0, 0, 204], atol=2)
        np.testing.assert_allclose(blue_base[48, 48, :3], [0, 0, 204], atol=2)

        f_wire = WireframeFilter(color=(1.0, 1.0, 0.0, 1.0), width=3.0, wireframe_only=False)
        mesh.attach(f_wire)
        wire_overlay = np.array(canvas.render(size=size, alpha=True), copy=True)
        # Diagonal shared edge passes through (y=48, x=96-48=48) or (y=48, x=48):
        # faces [[0,1,2],[1,3,2]] split along (96,0)-(0,96), passing right through (48, 48)!
        assert wire_overlay[48, 48, 0] > 180 and wire_overlay[48, 48, 1] > 180
        # Deep interior away from edges remains solid blue.
        np.testing.assert_allclose(wire_overlay[20, 20, :3], [0, 0, 204], atol=3)

        f_wire.wireframe_only = True
        wire_only = np.array(canvas.render(size=size, alpha=True), copy=True)
        assert wire_only[48, 48, 0] > 180 and wire_only[48, 48, 1] > 180
        np.testing.assert_allclose(wire_only[20, 20, :3], [0, 0, 0], atol=2)

        mesh.detach(f_wire)
        restored_b = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_array_equal(restored_b, blue_base)

        # --- Part C: IsolineFilter ---
        # IsolineFilter computes isolines from fragment RGB luminance
        # `dot(gl_FragColor.rgb, vec3(0.299, 0.587, 0.114))` (`fwidth(value)`).
        # Use a green-blue luminance ramp (R == 0 everywhere in base) across x = 0..96.
        iso_colors = np.array(
            [
                [0.0, 0.10, 0.20, 1.0],
                [0.0, 0.90, 1.00, 1.0],
                [0.0, 0.10, 0.20, 1.0],
                [0.0, 0.90, 1.00, 1.0],
            ],
            dtype=np.float32,
        )
        mesh.set_data(vertices=full_verts, faces=faces, vertex_colors=iso_colors)
        iso_base = np.array(canvas.render(size=size, alpha=True), copy=True)
        assert int((iso_base[..., 0] > 20).sum()) == 0

        f_iso = IsolineFilter(level=6.0, width=2.5, color=(1.0, 0.25, 0.0, 1.0))
        mesh.attach(f_iso)
        iso_orange = np.array(canvas.render(size=size, alpha=True), copy=True)
        orange_px = int((iso_orange[..., 0] > 120).sum())
        assert orange_px >= 150

        f_iso.level = 12.0
        f_iso.color = (1.0, 0.0, 1.0, 1.0)
        iso_magenta = np.array(canvas.render(size=size, alpha=True), copy=True)
        magenta_px = int(
            ((iso_magenta[..., 0] > 120) & (iso_magenta[..., 1] < 80) & (iso_magenta[..., 2] > 120)).sum()
        )
        assert magenta_px > orange_px
        assert not np.array_equal(iso_magenta, iso_orange)

        mesh.detach(f_iso)
        restored_c = np.array(canvas.render(size=size, alpha=True), copy=True)
        np.testing.assert_array_equal(restored_c, iso_base)
    finally:
        canvas.close()
        gc.collect()
        _dawn.process_events()


def test_gpu_collections_runtime_behavior_and_bounds():
    """Exercise all 5 vispy.visuals.collections factories on Dawn Vulkan and assert truthful runtime behavior."""
    from vispy import _dawn, gloo, scene
    from vispy.visuals.collections import (
        PathCollection,
        PointCollection,
        PolygonCollection,
        SegmentCollection,
        TriangleCollection,
    )

    size = (96, 96)
    canvas = scene.SceneCanvas(
        app='dawn_headless',
        size=size,
        show=False,
        bgcolor='black',
        config={'samples': 0},
    )
    color_rb = fbo = None
    created = []
    outcomes: dict[str, dict] = {}

    def _run_collection_case(name: str, builder):
        coll = None
        try:
            coll = builder()
            created.append(coll)
            with fbo:
                gloo.set_viewport(0, 0, size[0], size[1])
                gloo.set_state(
                    blend=True,
                    blend_func=('src_alpha', 'one_minus_src_alpha', 'one', 'one_minus_src_alpha'),
                    depth_test=False,
                    cull_face=False,
                )
                gloo.clear(color=(0.0, 0.0, 0.0, 1.0), depth=False)
                coll.draw()
                img = np.array(fbo.read(alpha=True), copy=True)
            lit = int(np.any(img[..., :3] > 20, axis=-1).sum())
            outcomes[name] = {
                'status': 'rendered' if lit > 0 else 'zero_lit_pixels',
                'lit_pixels': lit,
                'max_rgb': [int(v) for v in img[..., :3].max(axis=(0, 1))],
                'uses_shared_utype': bool(coll.utype),
            }
        except Exception as exc:
            outcomes[name] = {
                'status': 'error',
                'error_type': type(exc).__name__,
                'error_message': str(exc)[:400],
                'uses_shared_utype': bool(getattr(coll, 'utype', None)),
            }

    try:
        canvas.set_current()
        color_rb = gloo.RenderBuffer(size[::-1], format='color')
        fbo = gloo.FrameBuffer(color=color_rb)

        # 1. TriangleCollection (mode='raw', local color, no shared uniform texture)
        def _make_tri():
            c = TriangleCollection(mode='raw')
            c.append(
                np.array([[-0.6, -0.6, 0.0], [0.6, -0.6, 0.0], [0.0, 0.7, 0.0]], dtype=np.float32),
                np.array([[0, 1, 2]], dtype=np.uint32),
                color=(1.0, 0.2, 0.1, 1.0),
            )
            return c

        # 2. PolygonCollection (mode='raw', local color, triangulated convex/concave polygon)
        def _make_poly():
            c = PolygonCollection(mode='raw')
            c.append(
                np.array([[-0.5, -0.5, 0.0], [0.5, -0.5, 0.0], [0.5, 0.5, 0.0], [-0.5, 0.5, 0.0]], dtype=np.float32),
                color=(0.1, 0.9, 0.2, 1.0),
            )
            return c

        # 3. PointCollection (mode='raw', explicit local color/size attributes)
        def _make_pt_raw():
            c = PointCollection(mode='raw', color='local', size='local')
            pts = np.array([[-0.4, 0.0, 0.0], [0.0, 0.0, 0.0], [0.4, 0.0, 0.0]], dtype=np.float32)
            c.append(pts, color=(1.0, 1.0, 0.0, 1.0), size=9.0)
            return c

        # 4. PointCollection (mode='agg', local color/size)
        def _make_pt_agg():
            c = PointCollection(mode='agg', color='local', size='local')
            pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
            c.append(pts, color=(0.2, 0.8, 1.0, 1.0), size=16.0)
            return c

        # 5. SegmentCollection (mode='raw', shared color -> tests fetchcode/uniforms texture!)
        def _make_seg_raw_shared():
            c = SegmentCollection(mode='raw', color='shared')
            c.append(
                np.array([[-0.7, -0.7, 0.0]], dtype=np.float32),
                np.array([[0.7, 0.7, 0.0]], dtype=np.float32),
                color=(1.0, 0.5, 0.0, 1.0),
            )
            return c

        # 6. SegmentCollection (mode='agg', global uniforms -> avoids shared float32 uniform texture)
        def _make_seg_agg_global():
            c = SegmentCollection(mode='agg', color='global', linewidth='global', antialias='global')
            c.append(
                np.array([[-0.7, 0.0, 0.0]], dtype=np.float32),
                np.array([[0.7, 0.0, 0.0]], dtype=np.float32),
            )
            c['color'] = (0.0, 1.0, 0.5, 1.0)
            c['linewidth'] = 6.0
            c['antialias'] = 1.0
            c['viewport'] = (0.0, 0.0, float(size[0]), float(size[1]))
            return c

        # 7. SegmentCollection (mode='agg', default shared uniforms -> tests fetchcode/uniforms texture!)
        def _make_seg_agg_shared():
            c = SegmentCollection(mode='agg')
            c.append(
                np.array([[-0.7, 0.0, 0.0]], dtype=np.float32),
                np.array([[0.7, 0.0, 0.0]], dtype=np.float32),
                color=(0.0, 1.0, 0.5, 1.0),
                linewidth=6.0,
            )
            c['viewport'] = (0.0, 0.0, float(size[0]), float(size[1]))
            return c

        # 8. PathCollection (mode='agg', default global uniforms)
        def _make_path_agg():
            c = PathCollection(mode='agg')
            c.append(
                np.array([[-0.6, -0.4, 0.0], [0.0, 0.5, 0.0], [0.6, -0.4, 0.0]], dtype=np.float32),
                closed=False,
            )
            c['color'] = (0.9, 0.2, 0.9, 1.0)
            c['linewidth'] = 5.0
            c['antialias'] = 1.0
            c['viewport'] = (0.0, 0.0, float(size[0]), float(size[1]))
            return c

        # 9. PathCollection (mode='raw', local color)
        def _make_path_raw():
            c = PathCollection(mode='raw')
            c.append(
                np.array([[-0.6, -0.4, 0.0], [0.0, 0.5, 0.0], [0.6, -0.4, 0.0]], dtype=np.float32),
                closed=False,
                color=(0.9, 0.5, 0.2, 1.0),
            )
            return c

        for case_name, fn in (
            ('TriangleCollection_raw_local', _make_tri),
            ('PolygonCollection_raw_local', _make_poly),
            ('PointCollection_raw_local', _make_pt_raw),
            ('PointCollection_agg_local', _make_pt_agg),
            ('SegmentCollection_raw_shared', _make_seg_raw_shared),
            ('SegmentCollection_agg_global', _make_seg_agg_global),
            ('SegmentCollection_agg_shared', _make_seg_agg_shared),
            ('PathCollection_agg_global', _make_path_agg),
            ('PathCollection_raw', _make_path_raw),
        ):
            _run_collection_case(case_name, fn)

        telemetry_out = os.environ.get('VISPY_W3_3_TELEMETRY')
        if telemetry_out:
            Path(telemetry_out).write_bytes(
                (json.dumps({'collections': outcomes}, indent=2) + '\n').encode('utf-8')
            )

        # All 9/9 collection configurations render cleanly on Dawn Vulkan (including shared float32 uniform textures):
        assert len(outcomes) == 9
        for case_name, info in outcomes.items():
            assert info['status'] == 'rendered', f'{case_name} failed: {info}'
            assert info['lit_pixels'] > 0, f'{case_name} produced zero lit pixels: {info}'

        assert outcomes['TriangleCollection_raw_local']['lit_pixels'] >= 400
        assert outcomes['PolygonCollection_raw_local']['lit_pixels'] >= 1500
        assert outcomes['PointCollection_raw_local']['lit_pixels'] >= 3
        assert outcomes['PointCollection_agg_local']['lit_pixels'] >= 30
        assert outcomes['SegmentCollection_raw_shared']['lit_pixels'] >= 10
        assert outcomes['SegmentCollection_raw_shared']['uses_shared_utype'] is True
        assert outcomes['SegmentCollection_agg_global']['lit_pixels'] >= 150
        assert outcomes['SegmentCollection_agg_shared']['lit_pixels'] >= 80
        assert outcomes['SegmentCollection_agg_shared']['uses_shared_utype'] is True
        assert outcomes['PathCollection_agg_global']['lit_pixels'] >= 150
        assert outcomes['PathCollection_raw']['lit_pixels'] >= 10
    finally:
        for coll in created:
            _cleanup_collection(coll)
        created.clear()
        if fbo is not None:
            fbo.delete()
        if color_rb is not None:
            color_rb.delete()
        canvas.close()
        gc.collect()
        _dawn.process_events()
