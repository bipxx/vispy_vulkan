# -*- coding: utf-8 -*-
from unittest import mock

from vispy.color import Colormap
from vispy.scene import Image, PanZoomCamera
from vispy.visuals.image import ImageVisual
from vispy.testing import (requires_application, TestingCanvas,
                           run_tests_if_main, IS_CI)
from vispy.testing.image_tester import assert_image_approved, downsample

import numpy as np
import pytest

from vispy.testing.rendered_array_tester import compare_render, max_for_dtype


@requires_application()
@pytest.mark.parametrize('is_3d', [True, False])
def test_image(is_3d):
    """Test image visual"""
    size = (100, 50)
    with TestingCanvas(size=size, bgcolor='w') as c:
        image = Image(cmap='grays', clim=[0, 1], parent=c.scene)
        shape = (size[1]-10, size[0]-10) + ((3,) if is_3d else ())
        np.random.seed(379823)
        data = np.random.rand(*shape)
        image.set_data(data)
        assert_image_approved(c.render(), "visuals/image%s.png" %
                              ("_rgb" if is_3d else "_mono"))

        # change to auto clims after first draw
        image.clim = "auto"
        assert_image_approved(c.render(), "visuals/image%s.png" %
                              ("_rgb" if is_3d else "_mono"))


@requires_application()
@pytest.mark.parametrize('gamma', [None, -0.5, "0.5"])
def test_bad_init_gamma(gamma):
    """Test creating an Image with a bad gamma value."""
    with TestingCanvas(size=(100, 50)) as c:
        pytest.raises((TypeError, ValueError), Image, gamma=gamma, parent=c.scene)


def _make_test_data(shape, input_dtype):
    data = np.random.random_sample(shape)
    if data.ndim == 3 and data.shape[-1] == 4:
        # RGBA - make alpha fully opaque
        data[..., -1] = 1.0
    max_val = max_for_dtype(input_dtype)
    if max_val != 1:
        data *= max_val
    data = data.astype(input_dtype)
    return data


def _set_image_data(image, data, should_fail):
    if should_fail:
        pytest.raises(ValueError, image.set_data, data)
        return
    image.set_data(data)


def _get_orig_and_new_clims(input_dtype):
    new_clim = (0.3, 0.8)
    max_val = max_for_dtype(input_dtype)
    if np.issubdtype(input_dtype, np.integer):
        new_clim = (int(new_clim[0] * max_val), int(new_clim[1] * max_val))
    return (0, max_val), new_clim


@requires_application()
@pytest.mark.parametrize('data_on_init', [False, True])
@pytest.mark.parametrize('clim_on_init', [False, True])
@pytest.mark.parametrize('num_channels', [0, 1, 3, 4])
@pytest.mark.parametrize('texture_format', [None, '__dtype__', 'auto'])
@pytest.mark.parametrize('input_dtype', [np.uint8, np.uint16, np.float32, np.float64])
def test_image_clims_and_gamma(input_dtype, texture_format, num_channels,
                               clim_on_init, data_on_init):
    """Test image visual with clims and gamma on shader."""
    size = (80, 80)
    if texture_format == '__dtype__':
        texture_format = input_dtype
    shape = size + (num_channels,) if num_channels > 0 else size
    np.random.seed(0)
    data = _make_test_data(shape, input_dtype)
    orig_clim, new_clim = _get_orig_and_new_clims(input_dtype)
    # 16-bit integers and above seem to have precision loss when scaled on the CPU
    is_16int_cpu_scaled = (np.dtype(input_dtype).itemsize >= 2 and
                           np.issubdtype(input_dtype, np.integer) and
                           texture_format is None)
    clim_atol = 2 if is_16int_cpu_scaled else 1
    gamma_atol = 3 if is_16int_cpu_scaled else 2

    kwargs = {}
    if clim_on_init:
        kwargs['clim'] = orig_clim
    if data_on_init:
        kwargs['data'] = data
    # default is RGBA, anything except auto requires reformat
    set_data_fails = (num_channels != 4 and
                      texture_format is not None and
                      texture_format != 'auto')

    with TestingCanvas(size=size[::-1], bgcolor="w") as c:
        image = Image(cmap='grays', texture_format=texture_format,
                      parent=c.scene, **kwargs)
        if not data_on_init:
            _set_image_data(image, data, set_data_fails)
            if set_data_fails:
                return
        rendered = c.render()
        _dtype = rendered.dtype
        shape_ratio = rendered.shape[0] // data.shape[0]
        rendered1 = downsample(rendered, shape_ratio, axis=(0, 1)).astype(_dtype)
        compare_render(data, rendered1)

        # adjust color limits
        image.clim = new_clim
        rendered2 = downsample(c.render(), shape_ratio, axis=(0, 1)).astype(_dtype)
        scaled_data = (np.clip(data, new_clim[0], new_clim[1]) - new_clim[0]) / (new_clim[1] - new_clim[0])
        compare_render(scaled_data, rendered2, rendered1, atol=clim_atol)

        # adjust gamma
        image.gamma = 2
        rendered3 = downsample(c.render(), shape_ratio, axis=(0, 1)).astype(_dtype)
        compare_render(scaled_data ** 2, rendered3, rendered2, atol=gamma_atol)


@pytest.mark.xfail(IS_CI, reason="CI environments sometimes treat NaN as 0")
@requires_application()
@pytest.mark.parametrize('texture_format', [None, 'auto'])
@pytest.mark.parametrize('bad_color', [None, (1, 0, 0, 1)])
def test_image_nan(texture_format, bad_color):
    size = (80, 80)
    data = np.ones(size)
    data[:20, :20] = np.nan
    data[-20: -20:] = 0

    expected = (np.ones(size + (4,)) * 255).astype(np.uint8)
    expected[-20: -20:] = (0, 0, 0, 225)
    if texture_format is None:
        # CPU scaling's NaNs get converted to 0s
        expected[:20, :20] = (0, 0, 0, 255)
    else:
        # GPU receives NaNs
        # nan - mapped to bad color
        if bad_color is None:
            # no bad color means transparent, so we should see the green canvas
            bad_color = (0, 1, 0, 1)
        expected[:20, :20] = np.array(bad_color) * 255

    with TestingCanvas(size=size[::-1], bgcolor=(0, 1, 0)) as c:
        image = Image(data, cmap='grays', clim=(0, 1),
              texture_format=texture_format, parent=c.scene)
        image.bad_color = bad_color
        rendered = c.render()
        np.testing.assert_allclose(rendered, expected)


@requires_application()
@pytest.mark.parametrize('num_bands', [3, 4])
@pytest.mark.parametrize('texture_format', [None, 'auto'])
def test_image_nan_rgb(texture_format, num_bands):
    size = (40, 40)
    data = np.ones((40, 40, num_bands))
    data[:5, :5, :3] = np.nan  # upper left - RGB all NaN
    data[:5, 20:25, 0] = np.nan  # upper middle - R NaN
    data[:5, -5:, :3] = 0  # upper right - opaque RGB black square
    data[-5:, -5:, :] = np.nan  # lower right RGBA all NaN
    if num_bands == 4:
        data[-5:, :5, 3] = np.nan  # lower left - Alpha NaN

    expected = (np.ones((40, 40, 4)) * 255).astype(np.uint8)
    # upper left - NaN goes to opaque black
    expected[:5, :5, :3] = 0
    # upper middle -> NaN R goes to 0
    expected[:5, 20:25, 0] = 0
    # upper right - opaque RGB black square
    expected[:5, -5:, :3] = 0
    # lower right - NaN RGB/A goes to 0
    # RGBA case - we see the green background behind the image
    expected[-5:, -5:, 0] = 0
    expected[-5:, -5:, 2] = 0
    if num_bands == 3:
        # RGB case - opaque black because Alpha defaults 1
        expected[-5:, -5:, 1] = 0
    # lower left - NaN Alpha goes to 0
    if num_bands == 4:
        # see the green background behind the image
        expected[-5:, :5, 0] = 0
        expected[-5:, :5, 2] = 0

    with TestingCanvas(size=size[::-1], bgcolor=(0, 1, 0)) as c:
        Image(data, cmap='grays',
              texture_format=texture_format, parent=c.scene)
        rendered = c.render()
        np.testing.assert_allclose(rendered, expected)


@requires_application()
@pytest.mark.parametrize('num_channels', [0, 1, 3, 4])
@pytest.mark.parametrize('texture_format', [None, 'auto'])
def test_image_equal_clims(texture_format, num_channels):
    """Test image visual with equal clims."""
    size = (40, 40)
    input_dtype = np.uint8
    shape = size + (num_channels,) if num_channels > 0 else size
    np.random.seed(0)
    data = _make_test_data(shape, input_dtype)
    with TestingCanvas(size=size[::-1], bgcolor="w") as c:
        Image(data, cmap='viridis',
              texture_format=texture_format,
              clim=(128.0, 128.0),
              parent=c.scene)
        rendered = c.render()[..., :3]

        if num_channels >= 3:
            # RGBs don't have colormaps
            assert rendered.sum() == 0
            return

        # not all black
        assert rendered.sum() != 0
        # not all white
        assert rendered.sum() != 255 * rendered.size
        # should be all the same value
        r_unique = np.unique(rendered[..., 0])
        g_unique = np.unique(rendered[..., 1])
        b_unique = np.unique(rendered[..., 2])
        assert r_unique.size == 1
        assert g_unique.size == 1
        assert b_unique.size == 1


@requires_application()
def test_image_vertex_updates():
    """Test image visual coordinates are only built when needed."""
    size = (40, 40)
    with TestingCanvas(size=size, bgcolor="w") as c:
        shape = size + (3,)
        np.random.seed(0)
        image = Image(cmap='grays', clim=[0, 1], parent=c.scene)
        with mock.patch.object(
                image, '_build_vertex_data',
                wraps=image._build_vertex_data) as build_vertex_mock:
            data = np.random.rand(*shape)
            image.set_data(data)
            c.render()
            build_vertex_mock.assert_called_once()
            build_vertex_mock.reset_mock()  # reset the count to 0

            # rendering again shouldn't cause vertex coordinates to be built
            c.render()
            build_vertex_mock.assert_not_called()

            # changing to data of the same shape shouldn't cause it
            data = np.zeros_like(data)
            image.set_data(data)
            c.render()
            build_vertex_mock.assert_not_called()

            # changing to another shape should
            data = data[:-5, :-5]
            image.set_data(data)
            c.render()
            build_vertex_mock.assert_called_once()


@requires_application()
@pytest.mark.parametrize(
    ("dtype", "init_clim"),
    [
        (np.float32, "auto"),
        (np.float32, (0, 5)),
        (np.uint8, "auto"),
        (np.uint8, (0, 5)),
    ]
)
def test_change_clim_float(dtype, init_clim):
    """Test that with an image of floats, clim is correctly set from the first try.

    See https://github.com/vispy/vispy/pull/2245.
    """
    size = (40, 40)
    np.random.seed(0)
    data = (np.random.rand(*size) * 100).astype(dtype)

    with TestingCanvas(size=size[::-1], bgcolor="w") as c:
        image = Image(data=data, clim=init_clim, parent=c.scene)

        # needed to properly initialize the canvas
        c.render()

        image.clim = 0, 10
        rendered1 = c.render()
        # set clim to same values
        image.clim = 0, 10
        rendered2 = c.render()

        assert np.allclose(rendered1, rendered2)


@requires_application()
def test_image_interpolation():
    """Test different interpolations"""
    size = (81, 81)
    data = np.array([[0, 1]], dtype=int)
    left = (40, 0)
    right = (40, 80)
    center_left = (40, 39)
    center = (40, 40)
    center_right = (40, 41)
    white = (255, 255, 255, 255)
    black = (0, 0, 0, 255)
    gray = (128, 128, 128, 255)

    with TestingCanvas(size=size[::-1], bgcolor="w") as c:
        view = c.central_widget.add_view(border_width=0)
        view.camera = PanZoomCamera((0, 0, 2, 1))
        image = Image(data=data, cmap='grays',
                      parent=view.scene)

        # needed to properly initialize the canvas
        render = c.render()

        image.interpolation = 'nearest'
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)
        assert np.allclose(render[center_left], black)
        assert np.allclose(render[center_right], white)

        image.interpolation = 'linear'
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)
        assert np.allclose(render[center], gray, atol=5)  # we just want gray, this is not quantitative

        image.interpolation = 'custom'
        image.custom_kernel = np.array([[0]])  # no sampling
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], black)
        assert np.allclose(render[center], black)

        image.custom_kernel = np.array([[1]])  # same as linear
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)
        assert np.allclose(render[center], gray, atol=5)  # we just want gray, this is not quantitative


@requires_application()
def test_image_set_data_different_dtype():
    size = (80, 80)
    data = np.array([[0, 127]], dtype=np.int8)
    left = (40, 10)
    right = (40, 70)
    white = (255, 255, 255, 255)
    black = (0, 0, 0, 255)

    with TestingCanvas(size=size[::-1], bgcolor="w") as c:
        view = c.central_widget.add_view()
        view.camera = PanZoomCamera((0, 0, 2, 1))
        image = Image(data=data, cmap='grays', clim=[0, 127],
                      parent=view.scene)

        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)

        # same data as float should change nothing
        image.set_data(data.astype(np.float32))
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)

        # something inverted, different dtype
        new_data = np.array([[127, 0]], dtype=np.float16)
        image.set_data(new_data)
        render = c.render()
        assert np.allclose(render[left], white)
        assert np.allclose(render[right], black)

        # out of bounds should clip (2000 > 127)
        new_data = np.array([[0, 2000]], dtype=np.float64)
        image.set_data(new_data)
        render = c.render()
        assert np.allclose(render[left], black)
        assert np.allclose(render[right], white)


def _resize_image(interpolation='cubic', method='subdivide', texture_format=None):
    image = ImageVisual(np.arange(6, dtype=np.float32).reshape(2, 3) / 6,
                        interpolation=interpolation, method=method, clim=(0., 1.),
                        texture_format=texture_format,
                        custom_kernel=np.ones((3, 3), dtype=np.float32) / 9)
    if interpolation in ('bilinear', 'bicubic'):
        with pytest.warns(DeprecationWarning):
            image._prepare_draw(image)
    else:
        image._prepare_draw(image)
    assert image._need_vertex_update is False
    assert image._need_interpolation_update is False
    return image


def _resize_lookup_shape(image):
    return tuple(np.asarray(image._data_lookup_fn['shape'].value).tolist())


def _resize_program_size(program):
    return tuple(np.asarray(program['image_size']).tolist())


def test_image_filtered_lookup_shape_follows_resize():
    for interpolation in ('cubic', 'custom'):
        image = _resize_image(interpolation)
        lookup = image._data_lookup_fn
        assert _resize_lookup_shape(image) == (3, 2)
        for shape in ((6, 8), (3, 5)):
            image.set_data(np.ones(shape, dtype=np.float32))
            image._prepare_draw(image)
            assert image._data_lookup_fn is lookup
            assert image._texture.shape[:2] == shape
            assert _resize_lookup_shape(image) == shape[::-1]
            assert _resize_program_size(image.shared_program) == shape[::-1]


def test_image_nearest_linear_resize_refreshes_program_size():
    for interpolation in ('nearest', 'linear'):
        for method in ('subdivide', 'impostor'):
            image = _resize_image(interpolation, method)
            lookup = image._data_lookup_fn
            image.set_data(np.ones((6, 8), dtype=np.float32))
            image._prepare_draw(image)
            assert image._data_lookup_fn is lookup
            assert image._texture.shape[:2] == (6, 8)
            assert _resize_program_size(image.shared_program) == (8, 6)
            assert _resize_program_size(image.view_program) == (8, 6)
            assert image._texture.interpolation == interpolation
            with pytest.raises(KeyError):
                image._data_lookup_fn['shape']


def test_image_same_size_replacement_reuses_lookup_and_geometry():
    for interpolation in ('nearest', 'linear', 'cubic', 'custom'):
        image = _resize_image(interpolation)
        lookup = image._data_lookup_fn
        shape_variable = lookup['shape'] if interpolation in ('cubic', 'custom') else None
        with mock.patch.object(image, '_build_interpolation', wraps=image._build_interpolation) as build_lookup, \
                mock.patch.object(image, '_build_vertex_data', wraps=image._build_vertex_data) as build_geometry, \
                mock.patch.object(image._texture, 'scale_and_set_data', wraps=image._texture.scale_and_set_data) as upload:
            image.set_data(np.full((2, 3), .5, dtype=np.float32))
            image._prepare_draw(image)
            image._prepare_draw(image)
            assert build_lookup.call_count == build_geometry.call_count == 0
            assert upload.call_count == 1
        assert image._data_lookup_fn is lookup
        if shape_variable is not None:
            assert lookup['shape'] is shape_variable
            assert _resize_lookup_shape(image) == (3, 2)


def test_image_resize_rebuilds_once_through_real_prepare():
    for interpolation in ('nearest', 'linear', 'cubic', 'custom'):
        image = _resize_image(interpolation)
        with mock.patch.object(image, '_build_interpolation', wraps=image._build_interpolation) as build_lookup, \
                mock.patch.object(image._subdiv_position, 'set_data', wraps=image._subdiv_position.set_data) as positions, \
                mock.patch.object(image._subdiv_texcoord, 'set_data', wraps=image._subdiv_texcoord.set_data) as texcoords:
            image.set_data(np.ones((6, 8), dtype=np.float32))
            assert image._need_vertex_update is True
            image._prepare_draw(image)
            image._prepare_draw(image)
            assert build_lookup.call_count == 1
            assert (positions.call_count, texcoords.call_count) == (1, 1)
            assert image._need_vertex_update is image._need_interpolation_update is False


def test_image_resize_interpolation_aliases_remain_valid():
    for alias, canonical in (('bicubic', 'cubic'), ('bilinear', 'linear')):
        image = _resize_image(alias)
        image.set_data(np.ones((6, 8), dtype=np.float32))
        with pytest.warns(DeprecationWarning):
            image._prepare_draw(image)
        assert image._data_lookup_fn is image._interpolation_fun[canonical]
        assert _resize_program_size(image.shared_program) == (8, 6)
        if canonical == 'cubic':
            assert _resize_lookup_shape(image) == (8, 6)
        assert image._texture.interpolation == ('nearest' if canonical == 'cubic' else 'linear')


def test_image_invalid_replacement_preserves_prepared_state():
    for interpolation in ('nearest', 'linear', 'cubic', 'custom'):
        for texture_format in (None, np.float32):
            image = _resize_image(interpolation, texture_format=texture_format)
            previous = image._data
            lookup = image._data_lookup_fn
            observed = []
            image.events.update.connect(lambda event: observed.append(event))
            invalid_inputs = [np.ones((6, 8), dtype=np.complex64)]
            if texture_format is not None:
                invalid_inputs.append(np.ones((6, 8), dtype=np.uint8))
            for invalid in invalid_inputs:
                with pytest.raises((TypeError, ValueError)):
                    image.set_data(invalid)
                assert image._data is previous
                assert image._data_lookup_fn is lookup
                assert image._need_texture_upload is False
                assert image._need_vertex_update is False
                assert image._need_interpolation_update is False
                assert _resize_program_size(image.shared_program) == (3, 2)
            assert observed == []


def test_image_resize_updates_existing_second_view_uniform():
    for interpolation in ('nearest', 'linear', 'cubic', 'custom'):
        for method in ('subdivide', 'impostor'):
            image = _resize_image(interpolation, method=method)
            other = image.view()
            assert other._need_method_update is True
            assert other._method_used is None
            image._prepare_draw(other)
            assert other._need_method_update is False
            assert other._method_used == method
            assert _resize_program_size(other.view_program) == (3, 2)
            image.set_data(np.ones((6, 8), dtype=np.float32))
            image._prepare_draw(image)
            assert _resize_program_size(image.view_program) == (8, 6)
            assert _resize_program_size(other.view_program) == (8, 6)
            image._prepare_draw(other)
            assert _resize_program_size(other.view_program) == (8, 6)
            later = image.view()
            image._prepare_draw(later)
            assert later._method_used == method
            assert _resize_program_size(later.view_program) == (8, 6)


def test_image_failed_geometry_resize_stays_dirty_for_retry():
    image = _resize_image('cubic')
    image.set_data(np.ones((6, 8), dtype=np.float32))
    with mock.patch.object(image._subdiv_texcoord, 'set_data', side_effect=RuntimeError('synthetic geometry refusal')):
        with pytest.raises(RuntimeError, match='synthetic geometry refusal'):
            image._prepare_draw(image)
    assert image._need_vertex_update is True
    with mock.patch.object(image._subdiv_position, 'set_data', wraps=image._subdiv_position.set_data) as positions, \
            mock.patch.object(image._subdiv_texcoord, 'set_data', wraps=image._subdiv_texcoord.set_data) as texcoords:
        image._prepare_draw(image)
        image._prepare_draw(image)
        assert (positions.call_count, texcoords.call_count) == (1, 1)
    assert image._need_vertex_update is False
    assert _resize_lookup_shape(image) == _resize_program_size(image.shared_program) == (8, 6)


def test_image_multiple_pending_resizes_prepare_final_shape_once():
    image = _resize_image('custom')
    with mock.patch.object(image, '_build_interpolation', wraps=image._build_interpolation) as build_lookup, \
            mock.patch.object(image, '_build_vertex_data', wraps=image._build_vertex_data) as build_geometry, \
            mock.patch.object(image._texture, 'scale_and_set_data', wraps=image._texture.scale_and_set_data) as upload:
        image.set_data(np.ones((6, 8), dtype=np.float32))
        image.set_data(np.ones((4, 7), dtype=np.float32))
        image._prepare_draw(image)
        image._prepare_draw(image)
        assert build_lookup.call_count == build_geometry.call_count == upload.call_count == 1
    assert image._texture.shape[:2] == (4, 7)
    assert _resize_lookup_shape(image) == _resize_program_size(image.shared_program) == (7, 4)




def _lut_image(method):
    return ImageVisual(np.arange(6, dtype=np.float32).reshape(2, 3) / 5,
                       cmap=Colormap(['black', 'red', 'white']), clim=(0., 1.),
                       interpolation='nearest', method=method)


@pytest.mark.parametrize('method', ['subdivide', 'impostor'])
def test_image_lut_reaches_existing_public_view(method):
    image = _lut_image(method)
    other = image.view()
    image._prepare_draw(image)
    lut = image.view_program['texture2D_LUT']
    assert lut.shape == (1024, 1, 4)
    assert other.view_program['texture2D_LUT'] is lut
    image._prepare_draw(other)
    assert other.view_program['texture2D_LUT'] is lut


@pytest.mark.parametrize('method', ['subdivide', 'impostor'])
def test_image_lut_reaches_late_public_view(method):
    image = _lut_image(method)
    image._prepare_draw(image)
    lut = image.view_program['texture2D_LUT']
    later = image.view()
    assert later.view_program['texture2D_LUT'] is lut
    image._prepare_draw(later)
    assert later.view_program['texture2D_LUT'] is lut


@pytest.mark.parametrize('method', ['subdivide', 'impostor'])
def test_image_lut_public_view_prepared_before_primary(method):
    image = _lut_image(method)
    other = image.view()
    image._prepare_draw(other)
    lut = other.view_program['texture2D_LUT']
    assert image.view_program['texture2D_LUT'] is lut
    image._prepare_draw(image)
    later = image.view()
    assert image.view_program['texture2D_LUT'] is lut
    assert later.view_program['texture2D_LUT'] is lut
    image._prepare_draw(later)
    assert later.view_program['texture2D_LUT'] is lut


@pytest.mark.parametrize('method', ['subdivide', 'impostor'])
def test_image_changed_lut_reaches_all_and_future_views(method):
    image = _lut_image(method)
    first = image.view()
    image._prepare_draw(image)
    image._prepare_draw(first)
    previous = image.view_program['texture2D_LUT']
    image.cmap = Colormap(['black', 'blue', 'white'])
    with mock.patch.object(image.cmap, 'texture_lut', wraps=image.cmap.texture_lut) as make_lut:
        image._prepare_draw(first)
        current = first.view_program['texture2D_LUT']
        assert current is not previous
        assert image.view_program['texture2D_LUT'] is current
        later = image.view()
        assert later.view_program['texture2D_LUT'] is current
        image._prepare_draw(image)
        image._prepare_draw(first)
        image._prepare_draw(later)
        assert make_lut.call_count == 1
        assert image.view_program['texture2D_LUT'] is current
        assert first.view_program['texture2D_LUT'] is current
        assert later.view_program['texture2D_LUT'] is current



def _channel_data(channels):
    if channels == 0:
        return np.arange(6, dtype=np.float32).reshape(2, 3) / 5
    if channels == 1:
        return _channel_data(0)[..., None]
    data = np.zeros((2, 3, channels), dtype=np.float32)
    data[..., 0] = 1
    data[:, 1, 0] = 0
    data[:, 1, 2] = 1
    if channels == 4:
        data[..., 3] = .5
    return data


def _channel_transform(image):
    return image.shared_program.frag['color_transform']


@pytest.mark.parametrize('old_channels,new_channels', [(0, 3), (0, 4), (3, 0), (4, 0)])
def test_image_scalar_color_transition_rebuilds_transform(old_channels, new_channels):
    image = ImageVisual(_channel_data(old_channels), cmap='grays', clim=(0., 1.),
                        texture_format=None)
    image._prepare_draw(image)
    previous = _channel_transform(image)
    assert len(previous.functions) == (4 if old_channels < 2 else 3)
    assert image._need_colortransform_update is False
    with mock.patch.object(image, '_build_color_transform', wraps=image._build_color_transform) as rebuild, \
            mock.patch.object(image, '_build_vertex_data', wraps=image._build_vertex_data) as geometry, \
            mock.patch.object(image._texture, 'scale_and_set_data', wraps=image._texture.scale_and_set_data) as upload:
        image.set_data(_channel_data(new_channels))
        image._prepare_draw(image)
        current = _channel_transform(image)
        assert len(current.functions) == (4 if new_channels < 2 else 3)
        assert current is not previous
        assert rebuild.call_count == upload.call_count == 1
        assert geometry.call_count == 0
        image._prepare_draw(image)
        assert rebuild.call_count == upload.call_count == 1
        assert geometry.call_count == 0
    assert image._texture.internalformat is None
    assert image._texture.shape[-1] == (new_channels or 1)
    assert image._need_colortransform_update is image._need_texture_upload is False
    # Existing shortcut setters must target the new chain without rebuilding it.
    image.gamma = 2.
    image.clim = (.25, .75)
    image._prepare_draw(image)
    assert _channel_transform(image) is current
    assert current.functions[2]['gamma'].value == 2.
    np.testing.assert_equal(current.functions[1]['clim'].value, image._texture.clim_normalized)


@pytest.mark.parametrize('old_channels,new_channels', [(0, 1), (1, 0), (3, 4), (4, 3)])
def test_image_same_channel_semantics_reuses_transform(old_channels, new_channels):
    image = ImageVisual(_channel_data(old_channels), cmap='grays', clim=(0., 1.),
                        texture_format=None)
    image._prepare_draw(image)
    previous = _channel_transform(image)
    with mock.patch.object(image, '_build_color_transform', wraps=image._build_color_transform) as rebuild, \
            mock.patch.object(image, '_build_vertex_data', wraps=image._build_vertex_data) as geometry, \
            mock.patch.object(image._texture, 'scale_and_set_data', wraps=image._texture.scale_and_set_data) as upload:
        image.set_data(_channel_data(new_channels))
        image._prepare_draw(image)
        assert _channel_transform(image) is previous
        assert rebuild.call_count == geometry.call_count == 0
        assert upload.call_count == 1
    assert len(previous.functions) == (4 if new_channels < 2 else 3)
    assert image._texture.shape[-1] == (new_channels or 1)


def test_image_invalid_channel_replacement_preserves_transform():
    for old_channels, invalid_channels in ((0, 3), (3, 0)):
        image = ImageVisual(_channel_data(old_channels), cmap='grays', clim=(0., 1.),
                            texture_format=None)
        image._prepare_draw(image)
        previous = _channel_transform(image)
        data = image._data
        shape = image._texture.shape
        updates = []
        image.events.update.connect(lambda event: updates.append(event))
        with pytest.raises(TypeError, match='Complex data types not supported'):
            image.set_data(_channel_data(invalid_channels).astype(np.complex64))
        assert image._data is data
        assert _channel_transform(image) is previous
        assert image._texture.shape == shape
        assert image._need_colortransform_update is image._need_texture_upload is False
        assert image._need_vertex_update is image._need_interpolation_update is False
        assert updates == []

run_tests_if_main()
