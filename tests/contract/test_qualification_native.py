# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic raw build results exercise joins without compiling any code."""
from copy import deepcopy
import io

import pytest

from tools import qualification_native as qn


class Project(io.BytesIO):
    """Use the actual XML/mutex verifier and hash reader on retained bytes."""
    def open(self, mode):
        assert mode == 'rb'
        return io.BytesIO(self.getvalue())


def project(cpp=True, defined=True):
    data = ('<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
            '<ItemGroup><ClCompile Include="source.' + ('cpp' if cpp else 'c') + '"/></ItemGroup>'
            '<ItemDefinitionGroup Condition="\'$(Configuration)|$(Platform)\'==\'Release|x64\'">'
            '<ClCompile><PreprocessorDefinitions>' + ('_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR;' if defined else '')
            + '</PreprocessorDefinitions></ClCompile></ItemDefinitionGroup></Project>').encode()
    return Project(data)


def sample():
    sources = {'cpp/runtime.cpp': '1' * 64, 'tests/shaders/contract.cpp': '2' * 64}
    tools = [{'role': role, 'origin': 'C:/tools/' + role + '.exe',
              'sha256': qn.COMPILER_SHA if role == 'compiler' else '3' * 64} for role in sorted(qn.ROLES)]
    recipe = {'schema': 1, 'kind': 'windows-native-leaf-recipe', 'platform': 'windows-x86_64-cp312',
              'production_inputs_sha256': qn.digest({k:v for k,v in sources.items() if not k.startswith('tests/')}), 'source_inputs_sha256': qn.digest(sources), 'sdk_sha256': qn.SDK_SHA,
              'sdk_record_sha256': '5' * 64, 'preparation_sha256': '7' * 64, 'targets': sorted(qn.MIN_TARGETS),
              'ctest_names': sorted(qn.MIN_TESTS), 'toolchain': tools}
    consumer = {'cxx_flags': '/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR /EHsc',
                'release_flags': '/O2 /DNDEBUG', 'windows_sdk': '10.0.22621.0'}
    locations = {'source': 'C:/source', 'build': 'C:/source/build/work/unit-only/native',
                 'sdk': 'C:/source/build/native-sdk/admitted', 'ctest_output': 'C:/source/build/work/unit-only/ctest.xml'}
    cache = ('\r\n'.join(name + ':STRING=' + value for name, value in qn.cache_policy(recipe, consumer, locations).items()) + '\r\n').encode()
    projects = {target: (project(cpp=target != '_sdf_cpu'), project(cpp=target != '_sdf_cpu')) for target in recipe['targets']}
    ctest = ('<testsuite failures="0" errors="0" skipped="0">' + ''.join(
        '<testcase name="' + name + '" status="run"/>' for name in recipe['ctest_names']) + '</testsuite>').encode()
    outputs = {name: '6' * 64 for name in ('vispy/_dawn.cp312-win_amd64.pyd',
               'vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd', 'vispy/VkLayer_vispy_submit.dll', 'vispy/VkLayer_vispy_submit.json')}
    commands = qn.commands(recipe, consumer, locations)
    raw = {'schema': 1, 'kind': 'native-leaf-build-result', 'recipe_sha256': qn.recipe_digest(recipe),
           'source_before_sha256': qn.digest(sources), 'source_after_sha256': qn.digest(sources),
           'cache_before_sha256': qn.sha(cache), 'cache_after_sha256': qn.sha(cache), 'ctest_sha256': qn.sha(ctest),
           'locations': locations, 'environment': dict(qn.ENVIRONMENT),
           'commands': [{'phase': phase, 'argv': commands[phase], 'exit_code': 0, 'child_waited': True,
                         'child_pid': index + 100, 'log': {'path': 'unit-only.log', 'sha256': '0' * 64}}
                        for index, phase in enumerate(qn.PHASES)],
           'project_sha256': [{'target': name, 'sha256': qn.sha(pair[0].getvalue())} for name, pair in sorted(projects.items())],
           'outputs': [{'member': name, 'sha256': value} for name, value in sorted(outputs.items())]}
    return recipe, raw, sources, deepcopy(sources), deepcopy(sources), cache, cache, consumer, projects, ctest, outputs


def test_complete_synthetic_native_join_preserves_crlf_and_c_only_target():
    result = qn.validate_proofs(*sample())
    assert result['native_build_verified'] and not result['artifact_admitted']
    assert not result['hardware_qualified'] and len(result['native_output_hashes']) == 4


def test_resealed_parent_path_cannot_escape_managed_build_run():
    recipe, raw, expected, before, after, cb, ca, consumer, projects, ctest, outputs = sample()
    raw['locations']['build'] = 'C:/source/build/work/../native'
    raw['locations']['ctest_output'] = 'C:/source/build/work/../ctest.xml'
    cb = ca = ('\n'.join(name + ':STRING=' + value for name, value in qn.cache_policy(recipe, consumer, raw['locations']).items()) + '\n').encode()
    raw['cache_before_sha256'] = raw['cache_after_sha256'] = qn.sha(cb)
    commands = qn.commands(recipe, consumer, raw['locations'])
    for command in raw['commands']: command['argv'] = commands[command['phase']]
    with pytest.raises(qn.InventoryError, match='canonical absolute Windows paths'):
        qn.validate_proofs(recipe, raw, expected, before, after, cb, ca, consumer, projects, ctest, outputs)


@pytest.mark.parametrize('change', ['source', 'source-after', 'unrelated-source', 'unrelated-cache',
                                   'cache-change', 'cache-policy', 'duplicate-cache', 'missing-phase',
                                   'reorder-phase', 'wrong-command', 'nonzero', 'unawaited', 'bool-exit',
                                   'missing-project', 'changed-project', 'mutex-policy', 'no-cpp',
                                   'unrelated-project', 'ctest-skipped', 'ctest-missing', 'unrelated-ctest',
                                   'output-bytes', 'missing-output', 'unreviewed-recipe', 'compiler',
                                   'missing-tool', 'vendor-target', 'omitted-target', 'omitted-test',
                                   'unmanaged-build', 'scratch-sdk', 'relative-tool', 'ambient-flag', 'unknown-field'])
def test_resealed_native_provenance_controls(change):
    recipe, raw, expected, before, after, cb, ca, consumer, projects, ctest, outputs = sample()
    if change == 'source':
        before['cpp/runtime.cpp'] = '9' * 64; after.update(before)
        raw['source_before_sha256'] = raw['source_after_sha256'] = qn.digest(before)
    elif change == 'source-after': after['cpp/runtime.cpp'] = '9' * 64; raw['source_after_sha256'] = qn.digest(after)
    elif change == 'unrelated-source': raw['source_before_sha256'] = '9' * 64
    elif change == 'unrelated-cache': raw['cache_before_sha256'] = '9' * 64
    elif change == 'cache-change': ca += b'changed:STRING=1\n'; raw['cache_after_sha256'] = qn.sha(ca)
    elif change == 'cache-policy':
        cb = ca = cb.replace(b'MultiThreadedDLL', b'MultiThreaded'); raw['cache_before_sha256'] = raw['cache_after_sha256'] = qn.sha(cb)
    elif change == 'duplicate-cache':
        cb = ca = cb + b'VISPY_INPLACE:BOOL=OFF\n'; raw['cache_before_sha256'] = raw['cache_after_sha256'] = qn.sha(cb)
    elif change == 'missing-phase': raw['commands'].pop()
    elif change == 'reorder-phase': raw['commands'].reverse()
    elif change == 'wrong-command': raw['commands'][2]['argv'].append('webgpu_dawn')
    elif change == 'nonzero': raw['commands'][2]['exit_code'] = 1
    elif change == 'unawaited': raw['commands'][2]['child_waited'] = False
    elif change == 'bool-exit': raw['commands'][2]['exit_code'] = False
    elif change == 'missing-project': projects.pop('_dawn')
    elif change == 'changed-project': projects['_dawn'] = (projects['_dawn'][0], Project(project().getvalue() + b' '))
    elif change == 'mutex-policy': projects['_dawn'] = (project(defined=False), project(defined=False))
    elif change == 'no-cpp': projects['_dawn'] = (project(cpp=False), project(cpp=False))
    elif change == 'unrelated-project': raw['project_sha256'][0]['sha256'] = '9' * 64
    elif change == 'ctest-skipped':
        ctest = ctest.replace(b'status="run"/>', b'status="run"><skipped/></testcase>', 1); raw['ctest_sha256'] = qn.sha(ctest)
    elif change == 'ctest-missing':
        ctest = b'<testsuite/>'; raw['ctest_sha256'] = qn.sha(ctest)
    elif change == 'unrelated-ctest': raw['ctest_sha256'] = '9' * 64
    elif change == 'output-bytes': outputs['vispy/_dawn.cp312-win_amd64.pyd'] = '9' * 64
    elif change == 'missing-output':
        outputs.pop('vispy/visuals/text/_sdf_cpu.cp312-win_amd64.pyd')
        raw['outputs'] = [{'member': name, 'sha256': value} for name, value in sorted(outputs.items())]
    elif change == 'unreviewed-recipe': raw['recipe_sha256'] = '9' * 64
    elif change == 'compiler': recipe['toolchain'][2]['sha256'] = '9' * 64
    elif change == 'missing-tool': recipe['toolchain'].pop()
    elif change == 'vendor-target': recipe['targets'] = sorted(recipe['targets'] + ['webgpu_dawn'])
    elif change == 'omitted-target': recipe['targets'].remove('_dawn')
    elif change == 'omitted-test': recipe['ctest_names'].pop()
    elif change == 'unmanaged-build': raw['locations']['build'] = 'C:/source/build/unmanaged'
    elif change == 'scratch-sdk': raw['locations']['sdk'] = 'C:/source/build/work/unit-only/sdk'
    elif change == 'relative-tool': recipe['toolchain'][0]['origin'] = 'compiler.exe'
    elif change == 'ambient-flag': raw['environment']['CL'] = '/MDd'
    else: raw['native_leaf_admitted'] = True
    with pytest.raises((qn.InventoryError, qn.native_sdk.SDKError, qn.native_epoch.EpochError)):
        qn.validate_proofs(recipe, raw, expected, before, after, cb, ca, consumer, projects, ctest, outputs)


def test_default_native_cli_is_an_explicit_missing_provenance_result(capsys):
    assert qn.main([]) == 0
    result = capsys.readouterr().out
    assert 'NATIVE_PROVENANCE_REQUIRED' in result and '"native_leaf_admitted": false' in result


def test_harness_change_preserves_production_identity_but_changes_test_protocol():
    recipe, raw, expected, before, after, cb, ca, consumer, projects, ctest, outputs = sample()
    identity = qn.production_identity(recipe, outputs)
    original_recipe = qn.recipe_digest(recipe)
    expected['tests/shaders/contract.cpp'] = '9' * 64
    recipe['source_inputs_sha256'] = qn.digest(expected)
    recipe['ctest_names'] = sorted(recipe['ctest_names'] + ['new_contract'])
    assert qn.production_identity(recipe, outputs) == identity
    assert qn.recipe_digest(recipe) != original_recipe


@pytest.mark.parametrize('change', ['native', 'output', 'compiler', 'abi'])
def test_actual_production_changes_invalidate_reuse_identity(change):
    recipe, *rest = sample()
    outputs = rest[-1]
    original = qn.production_identity(recipe, outputs)
    if change == 'native': recipe['production_inputs_sha256'] = '9' * 64
    elif change == 'output': outputs['vispy/_dawn.cp312-win_amd64.pyd'] = '9' * 64
    elif change == 'compiler': recipe['toolchain'][2]['sha256'] = '9' * 64
    else: recipe['platform'] = 'windows-x86_64-cp313'
    assert qn.production_identity(recipe, outputs) != original


def test_unrelated_preparation_and_qualification_changes_do_not_change_compiler_inputs():
    runtime = qn.read_json(qn.ROOT / 'compat/candidates/tk-state-resource-1/runtime-inputs.json')
    original = qn.production_inputs(runtime)
    changed = deepcopy(runtime)
    for item in changed['build']:
        if item['path'] == 'cmake/prepare_cp310_candidate.py': item['sha256'] = '9' * 64
    changed['specification'] = 'unrelated spec update'
    changed['observer'] = 'unrelated observer update'
    assert qn.production_inputs(changed) == original
    changed['native'][0]['sha256'] = '9' * 64
    assert qn.production_inputs(changed) != original


def test_real_native_input_scope_includes_cpp_harness_and_shader_corpus():
    runtime = qn.read_json(qn.ROOT / 'compat/candidates/tk-state-resource-1/runtime-inputs.json')
    inputs = qn.source_inputs(runtime)
    for name in ('cpp/runtime.cpp', 'src/vispy/visuals/text/_sdf_cpu.pyx',
                 'tests/shaders/normalization_contract.cpp', 'tests/shaders/corpus/function-blue.frag'):
        assert inputs[name] == qn.sha((qn.ROOT / name).read_bytes())


def record_stub(candidate):
    ref = {'path': 'unit-only.json', 'sha256': '0' * 64}
    return {'schema': 1, 'kind': 'native-leaf-provenance', 'candidate': candidate,
            **{name: deepcopy(ref) for name in ('recipe', 'sdk', 'result', 'preparation', 'source_before',
                                               'source_after', 'cache_before', 'cache_after', 'ctest')},
            'projects': [{'target': '_dawn', 'before': ref, 'after': ref}],
            'outputs': [{'member': 'vispy/_dawn.cp312-win_amd64.pyd', 'file': ref}],
            'reuse': {'candidate_scope_sha256':'0'*64, 'profile':'unit-only', 'recipe_sha256':'0'*64, 'production_sha256':'0'*64, 'impact':'unit only'},
            'source_inputs': [{'path':'cpp/unit.cpp','file':ref}]}


def test_real_candidate_cannot_reach_sdk_or_proofs_without_review(monkeypatch):
    path = qn.ROOT / 'compat/candidates/tk-state-resource-1/candidate.json'
    ref = {'path': path.relative_to(qn.ROOT).as_posix(), 'sha256': qn.sha(path.read_bytes())}
    monkeypatch.setattr(qn, 'validate_sdk', lambda *args: pytest.fail('unreviewed producer reached SDK verifier'))
    with pytest.raises(qn.InventoryError, match='source and scope review remain pending'):
        qn.validate_record(record_stub(ref))


@pytest.mark.parametrize('kind,string_binding', [('source', False), ('scope', False), ('source', True)])
def test_both_existing_review_kinds_must_bind_the_exact_native_recipe(monkeypatch, kind, string_binding):
    # Isolate the new review extension; no real approvals or records are written.
    recipe = sample()[0]
    def ref(name): return {'path': name, 'sha256': '0' * 64}
    candidate = {'profiles': [{'id': 'unit-only', 'observation': ref('profile.json')}],
                 'reviews': {'source': ref('source.json'), 'scope': ref('scope.json')}}
    reuse_scope = qn.scope_digest(candidate)
    checksum = qn.recipe_digest(recipe)
    data = {'candidate.json': candidate, 'unit-only.json': recipe,
            'profile.json': {'kind': 'windows-gpu', 'architecture': 'x86_64', 'python_abi': 'cp312'},
            'source.json': {'native_reuse_links': [checksum]}, 'scope.json': {'native_reuse_links': [checksum]}}
    data[kind + '.json']['native_reuse_links'] = checksum if string_binding else ['9' * 64]
    read = qn.read_json
    monkeypatch.setattr(qn, 'read_json', lambda path: data[path.name] if path.name in data else read(path))
    monkeypatch.setattr(qn, 'retained_file', lambda root, reference: root / reference['path'])
    def existing_reviewed(value, root, require_reviewed):
        assert require_reviewed is True
    monkeypatch.setattr(qn, 'validate_candidate', existing_reviewed)
    with pytest.raises(qn.InventoryError, match='lacks bound independent review'):
        record = record_stub(ref('candidate.json'))
        record['reuse'].update(candidate_scope_sha256=reuse_scope, recipe_sha256=checksum)
        qn.validate_record(record)
