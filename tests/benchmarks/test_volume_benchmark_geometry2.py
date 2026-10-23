# SPDX-License-Identifier: AGPL-3.0-only
"""Semantic proof controls using retained real GL receipts, not new timings."""
import copy
import json
from pathlib import Path
import pytest
from tools import volume_benchmark_geometry2 as geometry

base=geometry.causal.original
NAME='volume-256-1024-mip-resident'
ROOT=geometry.causal.ROOT


@pytest.fixture(scope='module')
def example():
    folder=ROOT/'tests/reference/volume-benchmark-diagnostics/upstream'
    run=json.loads((folder/'run.json').read_bytes());samples=json.loads((folder/'samples.json').read_bytes())
    admission=base.load_admission(ROOT/'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'/(NAME+'.json'),NAME)
    warm=copy.deepcopy(run['original_geometry']);warm['frames']={key:value for key,value in warm['frames'].items() if int(key)<100}
    source=geometry.causal.source_obligations(ROOT/'third_party/parity/vispy/vispy',admission['artifacts']['upstream']['installed_package_sha256'],NAME)
    # Synthetic boundary identities exercise the validator. They do not qualify
    # the prior measured run or stand in for the real Qt hand-off harness.
    scene=dict(visible=True,single_volume_scene=True,shape=[256]*3,last_data_shape=[256]*3,last_data_dtype='<f4',
               vertex_id=warm['geometry_ids']['VertexBuffer'],index_id=warm['geometry_ids']['IndexBuffer'],
               need_vertex_update=True,physical_size=[1024]*2,volume_object=123)
    evidence=dict(schema=2,detached=True,pristine_parser_captured=True,no_per_frame_override=True,
        handoff_parse_calls=0,handoff_queue_unchanged=True,frozen_parser_code_verified=True,calls_before=444,calls_after=444,
        observer_invocation_delta=0,measured_parser_identity=22,measured_parser_identity_after=22,
        pristine_parser_kind=['vispy.gloo.glir','GlirParser.parse'])
    return run,samples,admission,dict(handoff=dict(evidence=evidence,warm=warm),scene_before=scene,
                                    scene_after=copy.deepcopy(scene),source_obligations=source)


def test_closed_program_warm_corroboration_and_real_counter_squeeze_are_required(example):
    run,samples,admission,proof=example
    result=geometry.validate_run(run,samples,kind='upstream',admission=admission,proof=proof)
    assert result['status']=='passed' and result['bytes']==152000 and result['uploads']==2000


@pytest.mark.parametrize('mutation',['warm_missing','warm_payload','detached','inner','call','queue','parser_identity',
    'object','shape','viewport','flag','source','extra_upload','storage','per_frame_upload','draw',
    'rebind','parser_kind','parser_code','cold_type','unowned','sample_range'])
def test_every_runtime_obligation_fails_closed(example,mutation):
    run,samples,admission,proof=copy.deepcopy(example)
    warm=proof['handoff']['warm'];evidence=proof['handoff']['evidence']
    if mutation=='warm_missing':warm['frames'].pop('0')
    if mutation=='warm_payload':warm['frames']['0'][1][3]['array']['sha256']='0'*64
    if mutation=='detached':evidence['detached']=False
    if mutation=='inner':evidence['pristine_parser_captured']=False
    if mutation=='call':evidence['calls_after']+=1
    if mutation=='queue':evidence['handoff_queue_unchanged']=False
    if mutation=='parser_identity':evidence['measured_parser_identity_after']+=1
    if mutation=='object':proof['scene_after']['volume_object']+=1
    if mutation=='shape':proof['scene_after']['shape']=[1]*3
    if mutation=='viewport':proof['scene_before']['physical_size']=proof['scene_after']['physical_size']=[64]*2
    if mutation=='flag':proof['scene_before']['need_vertex_update']=proof['scene_after']['need_vertex_update']=False
    if mutation=='source':proof['source_obligations']['factory_sha256']='0'*64
    if mutation=='extra_upload':run['counter_delta']['gl_buffer_upload_calls']+=1
    if mutation=='storage':run['counter_delta']['gl_buffer_storage_calls']=1
    if mutation=='per_frame_upload':samples[0]['opengl_paint_counters']['gl_buffer_upload_bytes']=151
    if mutation=='draw':samples[0]['opengl_paint_counters']['gl_draw_calls']=0
    if mutation=='rebind':proof['scene_before']['vertex_id']=proof['scene_after']['vertex_id']=999
    if mutation=='parser_kind':evidence['pristine_parser_kind']=['other','parse']
    if mutation=='parser_code':evidence['frozen_parser_code_verified']=False
    if mutation=='cold_type':warm['cold'][0][2]='IndexBuffer'
    if mutation=='unowned':warm['unattributed'].append(['DATA',999,0,{}])
    if mutation=='sample_range':samples.pop()
    assert geometry.validate_run(run,samples,kind='upstream',admission=admission,proof=proof)['status']!='passed'


def test_saved_json_roundtrip_preserves_revalidation(example):
    run,samples,admission,proof=json.loads(json.dumps(example))
    assert geometry.validate_run(run,samples,kind='upstream',admission=admission,proof=proof)['status']=='passed'


@pytest.mark.parametrize('kind',['upstream','candidate'])
@pytest.mark.parametrize('mutation',['none','texture_calls','texture_bytes','geometry','rebind','parser'])
def test_shape_preserving_full_update_contract_and_native_hot_work(example,kind,mutation):
    run,samples,_,proof=copy.deepcopy(example)
    name='volume-256-1024-mip-full'
    admission=base.load_admission(ROOT/'compat/scientific-admissions/volume-native58-cp312-numpy246-v5'/(name+'.json'),name)
    run['workload']=json.loads(json.dumps(__import__('dataclasses').asdict(base.benchmark.CATALOG[name])))
    count=run['measured_frames'];size=256**3*4
    if kind=='upstream':
        run['counter_delta']['gl_texture_upload_calls']=count;run['counter_delta']['gl_texture_upload_bytes']=count*size
        proof['source_obligations']=geometry.causal.source_obligations(ROOT/'third_party/parity/vispy/vispy',admission['artifacts']['upstream']['installed_package_sha256'],name)
        calls,bytekey='gl_texture_upload_calls','gl_texture_upload_bytes'
    else:
        real=json.loads((ROOT/'tests/reference/volume-benchmark-diagnostics/candidate/run.json').read_bytes())
        run['counter_delta']=real['counter_delta'];run['counter_delta'].update(texture_uploads=count,texture_upload_bytes=count*size)
        proof['handoff']['evidence']['pristine_parser_kind']=['vispy.gloo.dawn_parser','DawnGlirParser.parse']
        proof['scene_before']['need_vertex_update']=proof['scene_after']['need_vertex_update']=False
        proof['source_obligations']={};proof['handoff']['warm']['frames']={}
        proof['handoff']['warm']['unattributed']=[]
        calls,bytekey='texture_uploads','texture_upload_bytes'
    if mutation=='texture_calls':run['counter_delta'][calls]-=1
    if mutation=='texture_bytes':run['counter_delta'][bytekey]-=4
    if mutation=='geometry':run['counter_delta']['gl_buffer_upload_calls' if kind=='upstream' else 'buffer_uploads']+=1
    if mutation=='rebind':proof['scene_before']['vertex_id']=proof['scene_after']['vertex_id']=999
    if mutation=='parser':proof['handoff']['evidence']['pristine_parser_kind']=['other','parse']
    result=geometry.validate_run(run,samples,kind=kind,admission=admission,proof=proof)
    assert result['status']==('passed' if mutation=='none' else 'unproven'),result
