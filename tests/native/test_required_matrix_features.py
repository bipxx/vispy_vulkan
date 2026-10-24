"""Functional mandatory-feature probes using independently authored landmarks.

The historical full-frame OpenGL comparison suites and fixtures are unchanged.
These tests qualify actual scientific values on the selected Vulkan artifact;
they do not mark unsupported array/input/LOD variants as completed features.
"""
import numpy as np
import pytest

from vispy import _dawn
from tools import fixture_gloo, fixture_mesh_layout_extensions as mesh

pytestmark = pytest.mark.gpu


def assert_vulkan_retired():
    info = _dawn.device_info()
    assert info["ok"], info["error"]
    assert info["backend"] == "Vulkan"
    _dawn.process_events()
    after = _dawn.probe()
    assert after["pending_tickets"] == after["pending_draws"] == after["queued_frames"] == 0
    assert after["line_resource_pool_busy_slots"] == 0


@pytest.mark.parametrize("name", ["mesh_flat", "mesh_smooth", "surface_plot", "mesh_texture_clip"])
def test_required_mesh_has_authored_lighting_clipping_and_background_landmarks(name):
    image, commands, shaders, parameters, extras = mesh.render(name, backend="dawn_headless")
    assert commands and shaders
    assert any(command[0] == "DRAW" for command in commands)
    for key, expected in mesh.case_contract(name).items():
        assert parameters[key] == expected
    assert not extras, "mesh fixtures must not substitute a precomputed image or text atlas"
    mesh.assert_landmarks(name, image)
    assert_vulkan_retired()


@pytest.mark.parametrize("name", ["depth_occlusion", "depth_clear_only", "depth_range", "stencil"])
def test_required_depth_order_and_stencil_produce_authored_visible_values(name):
    image, commands, shaders, reads = fixture_gloo.render(name, backend="dawn_headless")
    assert commands and shaders and reads == 1
    fixture_gloo.assert_expected_regions(name, image)
    assert image.dtype == np.uint8
    assert_vulkan_retired()


@pytest.mark.parametrize("name", ["scalar_array", "vector_array", "matrix_array", "mat2", "mat3", "mat4",
                                 "bool_uniform", "constant_attribute", "interleaved"])
def test_required_existing_uniform_array_and_vertex_input_values(name):
    image, commands, shaders, reads = fixture_gloo.render(name, backend="dawn_headless")
    assert commands and shaders and reads == 1
    fixture_gloo.assert_expected_regions(name, image)
    fixture_gloo.assert_numeric_landmarks(name, image)
    assert image.dtype == np.uint8 and np.any(image[..., :3]), "blank data transport is not feature proof"
    assert_vulkan_retired()
