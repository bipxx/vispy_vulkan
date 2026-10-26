# SPDX-License-Identifier: AGPL-3.0-only
"""Shared source/installed compatibility regressions; no admission claim."""


def compatibility_render_checks(app, gloo, scene, np, native, root, evidence, result=None):
    app.use_app('dawn_headless')
    from aggregate_attribute_smoke import (
        aggregate_attribute_checks, aggregate_indexed_checks,
        composed_attribute_checks, aggregate_batch_checks,
    )
    from instanced_mesh_smoke import instanced_mesh_checks
    from original_instanced_mesh_replay import original_instanced_mesh_checks

    result = {} if result is None else result
    canvas = app.Canvas(app='dawn_headless', size=(8, 8), show=False,
                        config={'samples': 0})
    try:
        canvas.set_current()
        result['aggregate'] = aggregate_attribute_checks(
            gloo, np, native.device_info()['max_vertex_attributes'])
        result['indexed'] = aggregate_indexed_checks(gloo, np)
        result['composed'] = composed_attribute_checks(gloo, np)
    finally:
        canvas.close()
    result['batch'] = aggregate_batch_checks(app, gloo, np, native)
    result['visuals'] = instanced_mesh_checks(scene, np, evidence=evidence)
    result['original_body_replay'] = original_instanced_mesh_checks(root, scene, np)
    return result
