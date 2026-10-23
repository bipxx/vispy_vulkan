# SPDX-License-Identifier: AGPL-3.0-only
"""Portable, immutable original mesh/layout regression references."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import numpy as np
try:
    from .fixture_mesh_layout_extensions import CASES,array_record,assert_landmarks,case_contract
except ImportError:
    from fixture_mesh_layout_extensions import CASES,array_record,assert_landmarks,case_contract

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=Path(os.environ.get('VISPY_MESH_LAYOUT_REFERENCE',ROOT/'tests/reference/mesh-layout-opengl'))
MANIFEST_SHA256='d4bdd74c7de56c9f2f615f6d0f9d591bf0de3670e762f7fc28b48e356719c153'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_record(directory,record):
    directory=Path(directory).resolve()
    path=(directory/record['file']).resolve()
    if not path.is_relative_to(directory):raise ValueError('Reference member outside packet')
    body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=record['sha256']:
        raise ValueError(f'Reference bytes differ: {record["file"]}')
    return body


def load_manifest(directory=REFERENCE,*,producer_root=ROOT,expected_sha256=MANIFEST_SHA256):
    directory=Path(directory)
    body=(directory/'manifest.json').read_bytes()
    if hashlib.sha256(body).hexdigest()!=expected_sha256:raise ValueError('Reference manifest differs')
    manifest=json.loads(body)
    assert manifest['schema']==1 and manifest['kind']=='upstream'
    assert manifest['cases']==list(CASES) and set(manifest['fixtures'])==set(CASES)
    assert manifest['size']==[224,160] and manifest['original_upstream_cases_passed']==13
    assert not manifest['reference_bytes_modified']
    for name,digest in manifest['fixture_sources_sha256'].items():
        assert sha(Path(producer_root)/name)==digest, f'Fixture differs from original capture: {name}'
    for record in manifest['historical'].values():read_record(directory,record)
    for record in manifest['licenses'].values():read_record(directory,record)
    author=json.loads(read_record(directory,manifest['historical']['authoring.json']))
    assert author['candidate_pixels_seen'] is False and author['GPU_invoked'] is False
    assert author['cases']=={name:case_contract(name) for name in CASES}
    return manifest


def load_case(name,directory=REFERENCE,*,producer_root=ROOT):
    if name not in CASES:raise ValueError(f'Unknown required mesh/layout case: {name}')
    manifest=load_manifest(directory,producer_root=producer_root)
    record=manifest['fixtures'][name]
    source=json.loads(read_record(directory,record['source_report']))
    assert source['kind']=='upstream' and source['case']==name
    assert source['status']=='PASS_UPSTREAM_CASE' and source['process_exit']==0
    assert source['authoring_sha256']==manifest['historical']['authoring.json']['sha256']
    artifacts=record['artifacts']
    assert source['artifacts']=={leaf:item['sha256'] for leaf,item in artifacts.items()}
    bodies={leaf:read_record(directory,item) for leaf,item in artifacts.items()}
    params=json.loads(bodies['parameters.json'])
    assert params==source['parameters'], (name,'recorded parameters')
    for key,value in case_contract(name).items():assert params[key]==value, (name,key)
    assert json.loads(bodies['commands.json']) and json.loads(bodies['shaders.json'])
    image=np.load(io.BytesIO(bodies['rgba.npy']),allow_pickle=False)
    assert_landmarks(name,image)
    extras={}
    for key,expected in params['cpu_atlases'].items():
        array=np.load(io.BytesIO(bodies[key+'.npy']),allow_pickle=False)
        assert array_record(array)==expected, (name,key)
        array.setflags(write=False)
        extras[key]=array
    assert {leaf for leaf in bodies if leaf.endswith('.npy')}=={'rgba.npy',*(key+'.npy' for key in extras)}
    image.setflags(write=False)
    return image,params,extras
