# SPDX-License-Identifier: AGPL-3.0-only
"""One index of the user-approved documented differences and of the tests that are expected to fail.

The comparisons stay beside their hash-bound fixtures, one module per decision group. DIFFERENCES names, for each
decision, the modules that apply it and the cases and limits they must hold; tests/contract/test_documented_outcomes.py
checks it against those modules, so this index cannot drift from the rules that run. The decisions themselves are
recorded in docs/superpowers/plans/2026-10-28-consolidated-plan.md.

EXPECTED_FAILURES are tests that fail by decision (D8) or that belong to a superseded oracle fixture, retained beside
its admitted successor (D6). They keep failing: the evidence rules forbid skip and xfail. tests/hosts/conftest.py and
tests/parity/conftest.py only label them in pytest's report, count the failures this index does not explain, and name
any listed test that passed.
"""
from __future__ import annotations

from typing import NamedTuple


class Difference(NamedTuple):
    rule: str
    modules: tuple  # modules under tools/ that apply the decision; each names it
    bindings: tuple  # (module, attribute, value); a set compares unordered


class Failure(NamedTuple):
    decision: str
    reason: str


DIFFERENCES = {
    'D5': Difference(
        'Smooth (antialiased) lines use the smooth-line criterion: interiors (uniform 3x3 reference neighbourhoods) '
        'exact, every other pixel within 32 levels, at most 1% of the frame differing. It covers Glue scatter_axes, '
        'the mesh axes/colorbar scene and the five napari-threedee fixture suites (a CPU contract checks those); '
        'everything else stays exact.',
        ('glue_wheel_suite', 'mesh_layout_smooth_line'),
        (('smooth_line_parity', 'EDGE_TOLERANCE', 32), ('smooth_line_parity', 'MAX_DIFFERING_FRACTION', .01),
         ('glue_wheel_suite', 'SMOOTH_LINE', {'scatter_axes'}),
         ('mesh_layout_smooth_line', 'SMOOTH_LINE', {'axes_colorbar'}))),
    'D9': Difference(
        'Mesh axes_colorbar: the smooth-line criterion without its 1% frame cap; alpha and landmarks exact.',
        ('mesh_layout_smooth_line',),
        (('mesh_layout_smooth_line', 'DOCUMENTED_DIFFERENCE', {'axes_colorbar'}),)),
    'D10': Difference(
        'napari tracks and shapes_selected (W4, M11): as D9.',
        ('napari_vector_layers_comparison',),
        (('napari_vector_layers_comparison', 'DOCUMENTED_DIFFERENCE', {'tracks', 'shapes_selected'}),)),
    'D11': Difference(
        'napari colorbar and histogram (W4): as D9.',
        ('napari_layer_families_comparison',),
        (('napari_layer_families_comparison', 'DOCUMENTED_DIFFERENCE', {'colorbar', 'histogram'}),)),
    'D12': Difference(
        'napari surface_shaded (W4): interiors exact; at most 0.1% of the frame may differ, on edge pixels only, by '
        'any amount.',
        ('napari_layer_families_comparison',),
        (('napari_layer_families_comparison', 'EDGE_PIXELS', {'surface_shaded'}),
         ('napari_layer_families_comparison', 'MAX_EDGE_FRACTION', .001))),
    'D13': Difference(
        "H01's glFinish counts are recorded as evidence, not compared; the screenshot after a layer removal stays "
        'exact.',
        ('napari_layer_controls_comparison',),
        (('napari_layer_controls_comparison', 'COMPARED_PARAMETERS', ('layer_types', 'layer_names', 'ndisplay')),)),
    'D14': Difference(
        'napari volume_iso (V04): pixels with a uniform reference 3x3 neighbourhood exact; at most 0.1% of the frame '
        'may differ, each by at most 4 levels.',
        ('napari_layer_controls_comparison',),
        (('napari_layer_controls_comparison', 'SHADING', {'volume_iso'}),
         ('napari_layer_controls_comparison', 'MAX_SHADING_FRACTION', .001),
         ('napari_layer_controls_comparison', 'MAX_SHADING_LEVELS', 4))),
    'D15': Difference(
        "M08: every wide-line case whose specification sets line_smooth, and the defined-depth successor's smooth "
        'case, use the smooth-line criterion without the frame cap, with exact alpha; aliased cases stay exact.',
        ('wide_lines_comparison',),
        ()),
    'D16': Difference(
        'The wide-line reference tests pin both shared-fixture hashes: the one the packets were captured with and '
        'the reviewed replacement.',
        ('wide_lines_comparison',),
        (('wide_lines_comparison', 'CAPTURED_SHARED_FIXTURE_SHA256',
          'f689a08a8df084058eaa5cacf9c9833a155b1a2c210bcd8ad325c182852d750c'),
         ('wide_lines_comparison', 'CANONICAL_SHARED_FIXTURE_SHA256',
          '2568d76fa52e1c1f252ec0913f3c0e6d8a2b226ef55a2cdc2bd6c64baf004ed5'))),
    'D17': Difference(
        'Markers, under D4. M02 (all symbols): uniform pixels exact; at most 0.1% of the frame may differ, on edge '
        'pixels only, by any amount. M06 (one million markers): at most 0.5% of pixels beyond 2 levels, every other '
        'pixel within 2.',
        ('fixture_markers_all_symbols', 'fixture_markers_million'),
        (('fixture_markers_all_symbols', 'CRITERIA', dict.fromkeys(
            ('points_aa0', 'points_aa1', 'instanced_aa0', 'instanced_aa1', 'points_scene_zoom2'), 'edge_pixels')),
         ('fixture_markers_all_symbols', 'MAX_EDGE_FRACTION', .001),
         ('fixture_markers_million', 'CRITERIA', dict.fromkeys(('points', 'instanced'), 'within_2_levels')),
         ('fixture_markers_million', 'LEVELS', 2), ('fixture_markers_million', 'MAX_BEYOND_FRACTION', .005))),
}


def _cases(test, cases, decision, reason):
    return {'%s[%s]' % (test, case): Failure(decision, reason) for case in cases}


_PLUGIN = '::test_registered_plugin_qt_workflow_matches_independent_upstream'
_PLANE = '::test_registered_render_plane_qt_workflow_matches_upstream'
_MARKERS = '::test_marker_methods_depth_and_revisions_match_independent_opengl'
_THREEDEE_SUCCESSOR = ('its OpenGL capture is unadmitted, an oracle-side failure. The admitted successor is '
                       'tools/fixture_napari_threedee_overlay.py, which initialises both camera modes before '
                       "napari-threedee adds its empty rotator markers and draws the volume translucent_no_depth.")
_PLANE_SUCCESSOR = 'The admitted successor is tools/fixture_napari_render_plane_scheduled.py (D6, W10).'
_MARKER_SUCCESSOR = ('the OpenGL capture process for this case exited 1, so its reference is unadmitted. The '
                     'serialized packet (tests/parity/test_marker_extensions_serialized_parity.py) supersedes both '
                     'marker-extension packets.')

EXPECTED_FAILURES = {
    **_cases('tests/hosts/test_napari_render_plane_scheduled_parity.py' + _PLANE,
             ('plane_handles', 'plane_translation', 'plane_rotation', 'plane_clipped'), 'D8',
             "napari-threedee's manipulator strokes, smooth 3D lines (Line(width=3, method='gl'), antialias 2), "
             'exceed the smooth-line edge bound: GL smooths short 3D segments in a driver-defined way. A documented '
             'failure, with no tolerance.'),
    **_cases('tests/hosts/test_napari_threedee_parity.py' + _PLUGIN,
             ('handles', 'selection', 'translation', 'miss', 'retirement'), 'D6',
             'Superseded oracle fixture: ' + _THREEDEE_SUCCESSOR),
    **_cases('tests/hosts/test_napari_threedee_initialized_parity.py' + _PLUGIN,
             ('handles', 'selection', 'translation', 'miss'), 'D6',
             'Superseded oracle fixture: ' + _THREEDEE_SUCCESSOR),
    **_cases('tests/hosts/test_napari_render_plane_parity.py' + _PLANE, ('plane_translation', 'plane_rotation'), 'D6',
             "Superseded oracle fixture: its OpenGL capture is unadmitted; the oracle did not deliver napari's "
             'throttled mouse moves (the drag race, W0). ' + _PLANE_SUCCESSOR),
    **_cases('tests/hosts/test_napari_render_plane_parity.py' + _PLANE, ('plane_handles', 'plane_clipped'), 'D6',
             "Superseded oracle fixture. Like D8's cases, it fails on the manipulator's smooth 3D strokes. "
             + _PLANE_SUCCESSOR),
    **_cases('tests/parity/test_marker_extensions_parity.py' + _MARKERS,
             ('points_style_grid', 'points_camera_visual', 'points_color_revision', 'points_position_revision',
              'instanced_style_grid', 'instanced_camera_visual', 'instanced_spherical_depth',
              'instanced_color_revision', 'instanced_position_revision'), 'D6',
             'Superseded capture: ' + _MARKER_SUCCESSOR),
    **_cases('tests/parity/test_marker_extensions_corrected_parity.py' + _MARKERS,
             ('points_style_grid', 'points_camera_fixed', 'points_camera_scene', 'points_camera_visual',
              'points_spherical_depth', 'points_color_revision', 'points_position_revision', 'instanced_style_grid',
              'instanced_camera_fixed', 'instanced_camera_scene', 'instanced_camera_visual',
              'instanced_spherical_depth', 'instanced_color_revision', 'instanced_position_revision'), 'D6',
             'Superseded capture: ' + _MARKER_SUCCESSOR),
    **_cases('tests/parity/test_wide_line_parity.py::test_native_wide_smooth_line_matches_independent_exact_driver',
             ('depth_occlusion_smooth',), 'D6',
             'Retained original capture: it was taken before the shared fixture cleared depth, so its upstream '
             'admission is unresolved. The defined-depth successor (tests/parity/test_wide_line_depth_parity.py) '
             'passes under D15.'),
}


def label_report(item, report):
    """Attach the documented reason to a failing call of an expected failure. The outcome never changes."""
    failure = EXPECTED_FAILURES.get(item.nodeid)
    if failure is not None and report.when == 'call' and report.failed:
        text = '%s: %s' % failure
        report.sections.append(('documented failure (tools/documented_outcomes.py)', text))
        report.user_properties.append(('documented_failure', text))
        item.user_properties.append(('documented_failure', text))  # JUnit XML takes them from the teardown report


def summarize(terminalreporter, config):
    """After a run, list the documented failures, count the others, and name every listed test that passed."""
    if getattr(config, '_documented_outcomes_summarized', False):  # each conftest that labels reports calls this
        return
    config._documented_outcomes_summarized = True
    stats = terminalreporter.stats
    failed = [report.nodeid for report in stats.get('failed', ()) if report.when == 'call']
    passed = [report.nodeid for report in stats.get('passed', ()) if report.when == 'call']
    documented = [nodeid for nodeid in failed if nodeid in EXPECTED_FAILURES]
    unexpectedly_passed = [nodeid for nodeid in passed if nodeid in EXPECTED_FAILURES]
    if not documented and not unexpectedly_passed:
        return
    terminalreporter.section('documented failures (tools/documented_outcomes.py)')
    for nodeid in documented:
        terminalreporter.write_line('%s  [%s]' % (nodeid, EXPECTED_FAILURES[nodeid].decision))
    for nodeid in unexpectedly_passed:
        terminalreporter.write_line('%s  [%s] passed; update the index' % (nodeid, EXPECTED_FAILURES[nodeid].decision))
    terminalreporter.write_line('%d failed as documented, %d failed without a documented reason, %d listed but passed'
                                % (len(documented), len(failed) - len(documented), len(unexpectedly_passed)))
