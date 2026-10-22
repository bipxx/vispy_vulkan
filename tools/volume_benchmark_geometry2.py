# SPDX-License-Identifier: AGPL-3.0-only
"""Runtime obligations for an observer-free, pinned volume measured interval."""
from __future__ import annotations
import math
from . import volume_geometry_causality as causal
from . import volume_benchmark_geometry as legacy

require=causal.require


def validate_handoff(proof, expected, warm_count):
    evidence, warm=proof['evidence'],proof['warm']
    require(evidence['schema']==2 and evidence['detached'] and evidence['pristine_parser_captured'] and
            evidence['no_per_frame_override'] and evidence['handoff_parse_calls']==0 and evidence['handoff_queue_unchanged'],
            'Incomplete observer hand-off proof')
    require(evidence['frozen_parser_code_verified'] is True,'Frozen parser code identity absent')
    require(evidence['calls_before']==evidence['calls_after'] and evidence['observer_invocation_delta']==0 and
            evidence['measured_parser_identity']==evidence['measured_parser_identity_after'], 'Observer changed during measured frames')
    require(type(evidence['measured_parser_identity']) is int and evidence['measured_parser_identity']>0 and
            type(evidence['calls_before']) is int and evidence['calls_before']>=warm_count,'Malformed observer identity/count')
    require(not warm['errors'] and warm['expected']==expected, 'Warm geometry observation differs')
    ids=warm['geometry_ids'];require(set(ids)==set(legacy.BUFFER_TYPES) and len(set(ids.values()))==2, 'Warm geometry IDs differ')
    for kind,identifier in ids.items():
        rows=[row for row in warm['cold'] if row[1]==identifier]
        require([row for row in rows if row[0]=='CREATE']==[['CREATE',identifier,kind]], 'Cold typed geometry binding differs')
        require(any(row[0]=='DATA' for row in rows), 'Cold geometry bytes not observed')
        for row in rows:
            if row[0]=='SIZE':require(row==['SIZE',identifier,expected[kind]['size']], 'Cold size differs')
            if row[0]=='DATA':require(row==['DATA',identifier,0,expected[kind]['payload']], 'Cold payload differs')
            require(row[0]!='DELETE','Cold geometry was deleted')
    return warm,ids


def validate_run(run, samples, *, kind, admission, proof):
    try:
        expected=causal.original.expected_geometry(admission['workload'])
        warm,ids=validate_handoff(proof['handoff'],expected,run['warmup_frames'])
        parser_kind=['vispy.gloo.glir','GlirParser.parse'] if kind=='upstream' else ['vispy.gloo.dawn_parser','DawnGlirParser.parse']
        require(proof['handoff']['evidence']['pristine_parser_kind']==parser_kind,'Pristine parser kind differs')
        before,after=proof['scene_before'],proof['scene_after']
        require(before==after and before['visible'] is True and before['single_volume_scene'] is True,
                'Measured scene/shape/object identity changed')
        workload=run['workload'];shape=list(workload['shape'])
        require(before['physical_size']==list(workload['viewport']),'Measured physical extent differs')
        require(before['shape']==before['last_data_shape']==shape and before['last_data_dtype']=='<f4', 'Scalar volume shape/dtype differs')
        require(before['vertex_id']==ids['VertexBuffer'] and before['index_id']==ids['IndexBuffer'], 'Draw buffers were rebound')
        require(len(samples)==run['measured_frames'] and [sample['frame_id'] for sample in samples]==list(range(run['warmup_frames'],run['warmup_frames']+run['measured_frames'])), 'Measured sample range differs')
        generic=legacy.GENERIC_WORK_GATE(run,kind,update=workload['update']!='resident')
        if kind=='candidate':
            require(generic['status']=='passed','Candidate generic work gate did not pass')
            require(not warm['frames'] and not warm['unattributed'],'Candidate warm geometry was not resident')
            hot=causal.original.benchmark.NATIVE_RESIDENT_ZERO
            if workload['update']=='full':
                hot=tuple(key for key in hot if key not in ('texture_uploads','texture_conversion_ns'))
                count=run['measured_frames'];size=math.prod(shape)*4
                require(run['counter_delta'].get('texture_uploads')==count and run['counter_delta'].get('texture_upload_bytes')==count*size,
                        'Full source upload count/bytes differs')
            require(all(type(run['counter_delta'].get(key)) is int and run['counter_delta'][key]==0 for key in hot),
                    'Candidate warm cache/geometry work differs')
            return dict(status='passed',reasons=[],observer_effect_removed_by_construction=True,
                        proof_kind='frozen-parser-detach-and-generic-native-work',generic=generic)
        require(before['need_vertex_update'] is True, 'Original cube is not prepared at each draw')
        source=causal.source_obligations(causal.ROOT/'third_party/parity/vispy/vispy',admission['artifacts']['upstream']['installed_package_sha256'],admission['workload'])
        require(proof['source_obligations']==source,'Source causality obligations differ')
        rows=[row for name in legacy.BUFFER_TYPES for row in (['SIZE',ids[name],expected[name]['size']],['DATA',ids[name],0,expected[name]['payload']])]
        require(set(warm['frames'])==set(map(str,range(run['warmup_frames']))) and all(value==rows for value in warm['frames'].values()), 'Warm cube payloads differ')
        require(len(warm['unattributed'])%4==0 and warm['unattributed']==rows*(len(warm['unattributed'])//4), 'Unknown non-owned warm buffer work')
        counters=run['counter_delta'];count=run['measured_frames']
        require(counters['gl_buffer_upload_calls']==2*count and counters['gl_buffer_upload_bytes']==152*count and counters['gl_draw_calls']==count, 'Measured upload/draw lower and upper bounds do not meet')
        if workload['update']=='full':
            require(counters['gl_texture_upload_calls']==count and counters['gl_texture_upload_bytes']==count*math.prod(shape)*4,
                    'Original full source upload count/bytes differs')
        zeros=tuple(key for key in causal.original.benchmark.OPENGL_RESIDENT_ZERO+causal.original.benchmark._work.OPENGL_NO_WAIT if key not in legacy.BUFFER_COUNTERS)
        if workload['update']=='full':zeros=tuple(key for key in zeros if key not in ('gl_texture_upload_calls','gl_texture_upload_bytes'))
        zeros+=('gl_buffer_create_calls','gl_buffer_delete_calls','gl_buffer_storage_calls')
        require(all(type(counters.get(key)) is int and counters[key]==0 for key in zeros),'Extra measured GL work invalidates source squeeze')
        for sample in samples:
            require(sample['python_cpu']['python_draw_calls']==1,'Measured frame draw ownership differs')
            api=sample['opengl_paint_counters']
            require(api['gl_draw_calls']==1 and api['gl_buffer_upload_calls']==2 and api['gl_buffer_upload_bytes']==152,
                    'A measured paint lacks its exact original cube uploads')
            require(api['gl_failed_api_calls']==api['gl_buffer_storage_calls']==0,'A measured paint used an error/fallback/storage path')
        return dict(status='passed',reasons=[],observer_effect_removed_by_construction=True,
                    proof_kind='pinned-program-invariants-warm-corroboration-and-raw-counter-squeeze',
                    frames=count,uploads=2*count,bytes=152*count,other_required_zero=list(zeros))
    except (ValueError,KeyError,TypeError,IndexError,StopIteration,AttributeError,OSError) as error:
        return dict(status='unproven',reasons=[str(error)])
