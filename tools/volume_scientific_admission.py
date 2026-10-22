# SPDX-License-Identifier: AGPL-3.0-only
"""Bind actual large-workload data to independently checked small-volume controls.

This is a scientific admission producer, not a performance qualification. The
timing adapter must additionally bind its actual installed artifact fingerprint;
the older benchmark's seven Python source hashes alone are insufficient.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
if sys.flags.optimize:
    raise RuntimeError('Scientific admission requires Python assertions; optimized mode is forbidden')
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if not __package__:sys.path.insert(0,str(ROOT/'tools'))
try:
    from . import benchmark_frames as benchmark
    from . import large_volume_wheel_suite as large
    from . import volume_wheel_reference as small
except ImportError:
    import benchmark_frames as benchmark
    import large_volume_wheel_suite as large
    import volume_wheel_reference as small

CONTROLS_SHA='e9f2ef17e59a222372a4588dd5faa639f73beab0a8ad41e6713625864bbd406f'
LARGE_CANDIDATE_SHA='e3f285bcbf97d4a40cb75e031bda9c23abf5fc5d35cf2ad6047c0c8ada9cd576'
LARGE_ORIGINAL_SHA='af7919c6f59dca7addee614a674942697b33d53df3446df0cea422ef980bf2ac'
CONTROL_ROOT=ROOT/'tests/reference/volume-scientific-controls-numpy246'
LARGE_ROOT=ROOT/'tests/reference/large-volume-native58'
ORIGINAL_ROOT=ROOT/'tests/reference/large-volume-opengl'
CHECK_CASES={
    'categorical_background':tuple(name for name in small.CASES if name not in small.DIRECT_CASES),
    'depth_mesh':('mesh_front_iso',),
    'clipping_plane':('clipped_mip','categorical_clip'),
    'iso_mip_numeric':('mip','mip_linear','iso','plane_mip'),
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def write(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def bounded(root,relative):
    relative=Path(relative)
    assert not relative.is_absolute() and '..' not in relative.parts
    result=(Path(root)/relative).resolve(strict=True)
    assert result.is_relative_to(Path(root).resolve(strict=True))
    return result


def device_cell(device):
    assert device['ok'] and device['backend']=='Vulkan' and not device['software']
    assert device['vendor_id']==4318 and device['device_id']==9860
    assert device['device']=='NVIDIA GeForce RTX 4090' and '610.88' in device['driver']


def verify_controls(directory=CONTROL_ROOT):
    directory=Path(directory).resolve(strict=True)
    assert sha(directory/'manifest.json')==CONTROLS_SHA
    manifest=read(directory/'manifest.json')
    assert manifest['schema']==1 and manifest['status']=='PASS_ALL17_NUMPY246_VOLUME_CONTROLS'
    assert manifest['cases']==list(small.CASES) and manifest['wheel_sha256']==large.CANDIDATE_SHA
    evidence={directory/'manifest.json':CONTROLS_SHA}
    # The private launch driver remains historical metadata. All public inputs
    # used by the verifier must be retained in the portable evidence closure.
    for relative,digest in manifest['sources_sha256'].items():
        if relative=='build/volume-admission-prep-root-1/run_controls1.py':
            path=bounded(directory,'driver.py');assert sha(path)==digest;evidence[path]=digest
            continue
        path=bounded(ROOT,relative);assert sha(path)==digest;evidence[path]=digest
    for packet,digest in small.PACKETS.items():
        base=small.REFERENCE/packet
        path=base/'manifest.json';assert sha(path)==digest;evidence[path]=digest
        original=small.load_manifest(packet)
        stem='volume' if packet=='volume-opengl' else 'napari_volume'
        producers={f'tools/fixture_{stem}.py':original['provenance']['volume_fixture_sha256'],
                   f'tools/oracle_{stem}_capture.py':original['provenance']['volume_capture_sha256'],
                   'tools/fixture_gloo.py':original['provenance']['fixture_source_sha256']}
        if packet=='napari-volume-opengl':
            producers['tools/oracle_napari_requirements.txt']=original['provenance']['host_requirements_sha256']
        for relative,digest in producers.items():
            path=bounded(ROOT,relative);assert sha(path)==digest;evidence[path]=digest
        for record in original['fixtures'].values():
            for key in small.ARTIFACTS:
                item=record[key];path=bounded(base,item['file'])
                assert sha(path)==item['sha256'];evidence[path]=item['sha256']
    for relative,digest in manifest['files'].items():
        path=bounded(directory,relative);assert sha(path)==digest;evidence[path]=digest
    parent=read(directory/'parent.json')
    assert sha(directory/'parent.json')==manifest['parent_sha256']
    assert parent['status']=='PASS_ALL17_NUMPY246_VOLUME_CONTROLS' and not parent.get('error')
    assert set(parent['cases'])==set(small.CASES)
    assert parent['owned_cache_removed'] and not parent['cache_preserved_for_unverified_worker']
    package=None;cases={}
    for name in small.CASES:
        worker=read(directory/name/'result.json');process=read(directory/name/'process.json')
        assert worker==process['worker']
        assert process['process_exit']==worker['process_exit']==parent['cases'][name]['process_exit']==0
        assert process['child_waited'] and process['actual_worker_terminal']['terminal']
        assert parent['cases'][name]['actual_worker_terminal']['terminal']
        assert process['launch_id']==worker['launch_id']==parent['cases'][name]['launch_id']
        assert sha(directory/name/'result.json')==process['report_sha256']==parent['cases'][name]['report_sha256']
        assert worker['status']=='PASS_INSTALLED_WHEEL_VOLUME_CASE' and worker['case']==name
        assert worker['wheel_sha256']==large.CANDIDATE_SHA and worker['python'].startswith('3.12.8 ')
        assert worker['dependencies']['numpy']=='2.4.6'
        assert worker['cleanup_passed'] and worker['native_origins_verified'] and worker['reference_preserved']
        assert len(worker['shutdown_zeros'])==8 and set(worker['shutdown_zeros'].values())=={0}
        assert worker['reference_manifests_sha256']==small.PACKETS
        for source,digest in worker['producer_sources_sha256'].items():
            path=bounded(ROOT,source);assert sha(path)==digest;evidence[path]=digest
        for leaf,digest in worker['artifacts'].items():
            assert Path(leaf).name==leaf and sha(directory/name/leaf)==digest
        device_cell(worker['device'])
        assert worker['render_attempted'] and worker['excluded_pixels']==0 and worker['compared_pixels']==96*96
        commands=read(directory/name/'commands.json')
        assert any(row[0]=='DRAW' for row in commands)
        assert read(directory/name/'shaders.json')
        if name not in small.DIRECT_CASES:
            assert worker['host']['napari']=='0.9.2' and worker['host']['numba']=='0.68.0'
            assert worker['host']['qt_binding']=='PyQt6'
        current=worker['installed_package_sha256']
        if package is None:package=current
        assert current==package
        reference,expected=small.load_case(name)
        image=np.load(directory/name/'rgba.npy',allow_pickle=False)
        params=read(directory/name/'parameters.json')
        comparison=small.compare_case(name,image,reference,params,expected)
        assert comparison['comparison_criteria_passed'] and np.array_equal(image,reference)
        cases[name]=dict(result_sha256=sha(directory/name/'result.json'),parameters_sha256=sha(directory/name/'parameters.json'),
                         compared_pixels=image.shape[0]*image.shape[1],max_channel_error=0)
    return dict(cases=cases,evidence=evidence,package_sha256=package)


def verify_large_case(name,controls,candidate_root=LARGE_ROOT,original_root=ORIGINAL_ROOT):
    assert name in large.CASES
    candidate_root=Path(candidate_root).resolve(strict=True);original_root=Path(original_root).resolve(strict=True)
    assert sha(candidate_root/'manifest.json')==LARGE_CANDIDATE_SHA
    parent=read(candidate_root/'manifest.json');large.assert_successful_parent(parent,'candidate')
    assert parent['wheel_sha256']==large.CANDIDATE_SHA and parent['sources_sha256']==large.sources()
    reference=large.load_reference(original_root,LARGE_ORIGINAL_SHA,name)
    folder=candidate_root/name;worker=read(folder/'result.json');row=parent['workers'][name]
    assert sha(folder/'result.json')==row['report_sha256']
    assert worker['process_exit']==0 and worker['status']=='PASS_CANDIDATE_LARGE_VOLUME'
    assert worker['case']==name and worker['kind']=='candidate' and worker['sources_sha256']==large.sources()
    assert worker['process_stamp']['pid']==worker['pid'] and worker['process_stamp']['parent_pid']==row['pid']
    assert worker['cleanup_passed'] and worker['native_origins_verified'] and worker['visible_windows_after_close']==0
    assert worker['wheel_sha256']==large.CANDIDATE_SHA and worker['dependencies']==large.VERSIONS
    assert len(worker['shutdown_zeros'])==8 and set(worker['shutdown_zeros'].values())=={0}
    device_cell(worker['device'])
    package={key:value for key,value in worker['installed_wheel_payloads_sha256'].items() if key.startswith('vispy/')}
    assert package==controls['package_sha256'], 'Small and large controls must qualify the exact same installed artifact'
    evidence={candidate_root/'manifest.json':LARGE_CANDIDATE_SHA,original_root/'manifest.json':LARGE_ORIGINAL_SHA}
    for base,record in ((folder,worker),(reference,read(reference/'result.json'))):
        evidence[base/'result.json']=sha(base/'result.json')
        for leaf,digest in record['artifacts'].items():
            assert Path(leaf).name==leaf and sha(base/leaf)==digest;evidence[base/leaf]=digest
    params=read(folder/'parameters.json');original_params=read(reference/'parameters.json')
    for key in large.case_contract(name):assert params[key]==json.loads(json.dumps(large.case_contract(name)[key]))==original_params[key]
    assert params['data_sha256']==original_params['data_sha256']
    assert params['actual_volume_controls']==original_params['actual_volume_controls']
    identifiers=set();initial=None;maximum=0;changes={}
    with np.load(reference/'initial.npz',allow_pickle=False) as original, np.load(folder/'initial.npz',allow_pickle=False) as candidate:
        initial_original=original['rgba'];initial_candidate=candidate['rgba']
        for stage in large.STAGES:
            meta=read(folder/(stage+'.json'));identifiers.add(tuple(meta[k] for k in ('source_texture_id','target_texture_id','framebuffer_id')))
            with np.load(folder/(stage+'.npz'),allow_pickle=False) as archive:image=archive['rgba']
            measured=large.assert_stage(name,stage,image,meta,'candidate',reference)
            with np.load(reference/(stage+'.npz'),allow_pickle=False) as archive:original_image=archive['rgba']
            assert image.shape==original_image.shape and image.dtype==original_image.dtype==np.uint8
            full_maximum=int(np.abs(image.astype(np.int16)-original_image.astype(np.int16)).max())
            assert full_maximum<=2
            maximum=max(maximum,full_maximum)
            if stage=='initial':
                assert measured['source_upload_sha256']==params['data_sha256']
            if stage=='repeat':assert np.array_equal(image,initial_candidate)
            if stage in ('probe7','probe73'):
                with np.load(reference/(stage+'.npz'),allow_pickle=False) as archive:old=archive['rgba']
                check=large.change_discrimination(initial_original,old,initial_candidate,image)
                assert check['passed'];changes[stage]=check
    assert len(identifiers)==1
    assert worker['excluded_pixels']==0 and worker['compared_pixels']==initial_candidate.shape[0]*initial_candidate.shape[1]*len(large.STAGES)
    return dict(evidence=evidence,maximum_channel_error=maximum,changes=changes,
                workload_sha256=params['workload_sha256'],data_sha256=params['data_sha256'],
                package_sha256=package,original_package_sha256={k:v for k,v in read(reference/'result.json')['installed_wheel_payloads_sha256'].items() if k.startswith('vispy/')})


def measurement_identity(admission,run):
    """Supplement validate_admission and validate_hardware with artifact identity.

    This is not a standalone timing, workload or hardware qualification gate.
    """
    reasons=[];provenance=run.get('provenance',{});kind=provenance.get('kind')
    if kind not in ('upstream','candidate'):return dict(status='unproven',reasons=['explicit renderer role missing'])
    expected=admission['artifacts'][kind]
    if provenance.get('wheel_sha256')!=expected['wheel_sha256']:reasons.append('actual wheel digest missing or different')
    if provenance.get('installed_package_sha256')!=expected['installed_package_sha256']:reasons.append('actual complete installed package fingerprint missing or different')
    if run.get('data_sha256')!=admission['benchmark_data_sha256']:reasons.append('actual benchmark data differs')
    if provenance.get('python')!='3.12.8' or provenance.get('versions',{}).get('numpy')!='2.4.6':reasons.append('actual Python/NumPy cell differs')
    return dict(status='passed' if not reasons else 'unproven',reasons=reasons)


def produce(output,controls_root=CONTROL_ROOT,candidate_root=LARGE_ROOT,original_root=ORIGINAL_ROOT):
    destination=Path(output).resolve()
    output=destination.with_name(destination.name+'.pending')
    assert not output.exists() and not destination.exists(),'Preserve prior admission sets, including failed pending sets'
    assert set(benchmark.SCIENTIFIC_CHECKS['volume'])=={'primary_modes',*CHECK_CASES}
    assert all(set(names)<=set(small.CASES) for names in CHECK_CASES.values())
    controls=verify_controls(controls_root);output.mkdir(parents=True)
    assert set(controls['cases'])==set(small.CASES)
    plan={};reports={}
    for name in large.CASES:
        result=verify_large_case(name,controls,candidate_root,original_root)
        evidence=dict(controls['evidence']);evidence.update(result['evidence'])
        # Bind the verifier and all shared producers consumed by this admission.
        for relative in ('tools/volume_scientific_admission.py',*large.SOURCES):
            p=bounded(ROOT,relative);evidence[p]=sha(p)
        record=dict(schema=1,status='passed',workload=name,workload_sha256=result['workload_sha256'],
            benchmark_data_sha256=result['data_sha256'],checks={key:'passed' for key in benchmark.SCIENTIFIC_CHECKS['volume']},
            check_cases=dict(primary_modes=[name],**{key:list(value) for key,value in CHECK_CASES.items()}),
            control_scope='Exact large scalar workload plus independent small categorical/background, clipping, depth and numeric controls; same candidate artifact and NumPy2.4.6 device cell.',
            artifacts=dict(candidate=dict(wheel_sha256=large.CANDIDATE_SHA,installed_package_sha256=result['package_sha256']),
                           upstream=dict(wheel_sha256=large.ORIGINAL_SHA,installed_package_sha256=result['original_package_sha256'])),
            cell=dict(python='3.12.8',numpy='2.4.6',backend='Vulkan',vendor_id=4318,device_id=9860,driver='610.88'),
            evidence=[dict(file=Path(os.path.relpath(p,output)).as_posix(),sha256=h) for p,h in sorted(evidence.items(),key=lambda item:str(item[0]))],
            performance_qualified=False,other_cells_qualified=False)
        path=output/(name+'.json');write(path,record)
        plan[name]=dict(scientific_admission=path.name,exact=False)
        gate=benchmark.validate_admission(plan[name],benchmark.CATALOG[name],[dict(data_sha256=result['data_sha256'])]*2,output)
        assert gate['status']=='passed',gate
        reports[name]=dict(admission_sha256=sha(path),maximum_channel_error=result['maximum_channel_error'],visible_change_checks=2)
    write(output/'quality-plan.json',plan)
    write(output/'qualification.json',dict(schema=1,status='PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS',cases=reports,
        controls_manifest_sha256=CONTROLS_SHA,large_candidate_manifest_sha256=LARGE_CANDIDATE_SHA,
        large_original_manifest_sha256=LARGE_ORIGINAL_SHA,controls=controls['cases'],
        measured_performance_claimed=False,measurement_identity_required=True,full_release_qualified=False))
    output.rename(destination)
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();reports=produce(args.output)
    print(json.dumps(dict(status='PASS_24_BOUND_VOLUME_SCIENTIFIC_ADMISSIONS',cases=len(reports),output=str(args.output.resolve()))))

if __name__=='__main__':main()
