"""Pure measured-work admission shared by capture and saved release gates.

Event counts/bytes are cumulative-counter deltas. Inclusive transient-uniform
upload or cache-lookup CPU time is deliberately not a resident-zero condition.
"""
NATIVE_RESIDENT_ZERO = (
    'texture_uploads', 'buffer_uploads', 'geometry_upload_bytes', 'texture_conversion_ns',
    'point_conversion_builds', 'point_conversion_bytes',
    'vertex_input_conversion_builds', 'vertex_input_conversion_bytes',
    'line_endpoint_conversion_builds', 'line_endpoint_conversion_bytes',
    'pipeline_misses', 'portable_shader_misses',
    'shader_normalizations', 'shader_parse_calls', 'shader_link_calls', 'shader_spirv_stages',
    'shader_module_creations', 'render_pipeline_creations', 'compute_pipeline_creations',
)
NATIVE_NO_WAIT = ('completion_waits', 'finish_calls')
OPENGL_RESIDENT_ZERO = (
    'gl_texture_upload_calls', 'gl_texture_upload_bytes',
    'gl_buffer_upload_calls', 'gl_buffer_upload_bytes',
    'gl_shader_compile_calls', 'gl_program_link_calls',
)
OPENGL_NO_WAIT = ('gl_finish_calls', 'gl_blocking_client_wait_calls', 'gl_server_wait_calls', 'gl_readback_calls', 'gl_failed_api_calls')


def measured_work_gate(run, kind, *, update=False):
    """Reject missing/malformed evidence separately from observed forbidden work."""
    if kind not in ('upstream', 'candidate'):
        raise ValueError('explicit upstream/candidate measured-work role required')
    required = NATIVE_NO_WAIT if kind == 'candidate' else OPENGL_NO_WAIT
    if not update:
        required += NATIVE_RESIDENT_ZERO if kind == 'candidate' else OPENGL_RESIDENT_ZERO
    counters = run.get('counter_delta')
    if not isinstance(counters, dict):
        return dict(status='unproven', reasons=['measured counter_delta missing'], required_zero=list(required))
    invalid, nonzero = [], []
    for name in required:
        value = counters.get(name)
        # Native clocks, counters and GL invocation/byte observations are ints.
        # Accept no bool, coercion, negative delta, infinity or missing default.
        if type(value) is not int or value < 0:
            invalid.append(name)
        elif value != 0:
            nonzero.append(name)
    if invalid:
        return dict(status='unproven', reasons=['missing or malformed measured work: '+', '.join(invalid)],
                    required_zero=list(required), forbidden_nonzero=nonzero)
    return dict(status='failed' if nonzero else 'passed',
                reasons=['forbidden measured work: '+', '.join(nonzero)] if nonzero else [],
                required_zero=list(required), forbidden_nonzero=nonzero)
