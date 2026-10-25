# SPDX-License-Identifier: AGPL-3.0-only
"""Run the actual Linux renderer's complete discovered native contract set.

This captures a producer prerequisite, not producer or artifact admission.
"""
import argparse
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

try:
    from .native_epoch import check_ctest
except ImportError:
    from native_epoch import check_ctest

# All 44 current non-dataset renderer tests, not just the historical epoch core.
# Discovery can add tests; it cannot silently remove one of these obligations.
MINIMUM = set('''
owned_texture_contract owned_upload_decoder_contract owned_upload_packing_contract
shader_contract point_contract artifact_contract typed_sampling_contract
integer_sampling_contract integer_sampling_boundary_contract integer_sampling_artifact_contract
integer_sampler_snapshot_contract input_batch_contract ordered_strip_runtime_contract
ordinary_line_runtime_contract point_batch_contract point_partition_contract batch_identity_contract
input_batch_owner_contract input_batch_topology_contract input_batch_routing_contract
input_batch_capacity_contract input_batch_cache_contract artifact_consumer_contract
uniform_updates_contract runtime_line_consumer_policy_contract runtime_line_variants_contract
runtime_line_consumer_accounting_contract texture_contract state_contract readback_contract
framebuffer_configuration_contract timestamp_contract frame_lifecycle_contract line_contract
line_batch_contract line_capture_contract line_evaluator_contract line_consumer_generated_contract
line_consumer_resource_contract line_pool_contract line_pool_inspection_contract
line_ownership_contract native_contract vk_layer_contract
'''.split())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def discovered_names(data):
    discovery = json.loads(data)
    major = discovery.get('version', {}).get('major')
    if discovery.get('kind') != 'ctestInfo' or type(major) is not int or major != 1:
        raise ValueError('Expected original CTest JSON discovery version 1')
    names = [item['name'] for item in discovery['tests']]
    if (not all(isinstance(name, str) and name for name in names)
            or len(names) != len(set(names)) or not MINIMUM <= set(names)):
        raise ValueError('Incomplete or duplicate renderer contract discovery')
    return sorted(names)


def validate_reports(discovery, junit):
    names = discovered_names(discovery)
    check_ctest(io.BytesIO(junit), names)
    return names


def renderer_cache(data):
    values = {}
    for line in data.decode('utf-8-sig').splitlines():
        if line and not line.startswith(('#', '//')) and ':' in line and '=' in line:
            key, value = line.split('=', 1)
            key = key.split(':', 1)[0]
            if key in values:
                raise ValueError('Duplicate CMake cache setting: ' + key)
            values[key] = value
    for key, expected in {
        'VISPY_BUILD_CONTRACT_TESTS': 'ON', 'VISPY_CPU_CONTRACTS_ONLY': 'OFF',
        'VISPY_INPLACE': 'OFF', 'VISPY_VERIFY_DEPENDENCIES': 'ON',
        'DAWN_ENABLE_VULKAN': 'ON', 'DAWN_ENABLE_METAL': 'OFF',
        'DAWN_ENABLE_NULL': 'OFF', 'TINT_BUILD_SPV_READER': 'ON',
        'DAWN_ENABLE_SPIRV_VALIDATION': 'ON',
    }.items():
        if values.get(key) != expected:
            raise ValueError('Native renderer contract configuration differs: ' + key)
    return values


def run(build, output, ctest):
    build = Path(build).resolve(strict=True)
    ctest = Path(ctest).resolve(strict=True)
    output = Path(output).resolve()
    cache = (build / 'CMakeCache.txt').read_bytes()
    output.mkdir(parents=True, exist_ok=False)
    record = dict(status='FAILED_PRESERVED', build=str(build), commands=[],
                  ctest=dict(origin=str(ctest), sha256=sha(ctest.read_bytes())),
                  cache_sha256=sha(cache), producer_admitted=False,
                  artifact_admitted=False, hardware_qualified=False)

    def execute(arguments, stdout_name, stderr_name=None):
        argv = [str(ctest), '--test-dir', str(build), *arguments]
        with ExitStack() as stack:
            stdout = stack.enter_context((output / stdout_name).open('xb'))
            stderr = (stack.enter_context((output / stderr_name).open('xb'))
                      if stderr_name else subprocess.STDOUT)
            child = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
            code = None
            try:
                code = child.wait()
            except BaseException:
                child.terminate()
                try:
                    code = child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    code = child.wait()
                raise
            finally:
                record['commands'].append(dict(argv=argv, exit_code=code,
                                               child_pid=child.pid, child_waited=code is not None))
        if code:
            raise RuntimeError('Native contract child failed: ' + str(code))

    try:
        renderer_cache(cache)
        execute(['--show-only=json-v1'], 'discovery.json', 'discovery.log')
        discovered_names((output / 'discovery.json').read_bytes())
        execute(['--output-on-failure', '--no-tests=error', '--output-junit',
                 str(output / 'ctest.xml')], 'ctest.log')
        record['tests'] = validate_reports((output / 'discovery.json').read_bytes(),
                                           (output / 'ctest.xml').read_bytes())
        if (build / 'CMakeCache.txt').read_bytes() != cache:
            raise ValueError('Native renderer cache changed during contract execution')
        record['status'] = 'PASS_LINUX_RENDERER_CONTRACTS'
    except BaseException as error:
        record['error'] = str(error)
        raise
    finally:
        record['files'] = {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())
                           if p.is_file()}
        (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def validate_retained(directory, build, cache):
    """Join a captured prerequisite to the archive's unchanged build cache."""
    directory = Path(directory)
    record = json.loads((directory / 'result.json').read_bytes())
    renderer_cache(cache)
    if (record['status'] != 'PASS_LINUX_RENDERER_CONTRACTS'
            or record['build'] != str(Path(build).resolve())
            or record['cache_sha256'] != sha(cache)
            or record['producer_admitted'] is not False
            or record['artifact_admitted'] is not False
            or record['hardware_qualified'] is not False):
        raise ValueError('Native contract result does not bind this renderer build')
    if set(record['files']) != {'discovery.json', 'discovery.log', 'ctest.xml', 'ctest.log'}:
        raise ValueError('Incomplete native contract evidence')
    if sha(Path(record['ctest']['origin']).read_bytes()) != record['ctest']['sha256']:
        raise ValueError('Native contract CTest tool changed')
    for name, expected in record['files'].items():
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError('Native contract evidence changed: ' + name)
    expected_arguments = [
        ['--show-only=json-v1'],
        ['--output-on-failure', '--no-tests=error', '--output-junit',
         str(directory.resolve() / 'ctest.xml')],
    ]
    if len(record['commands']) != 2:
        raise ValueError('Native contract commands missing or duplicated')
    for command, arguments in zip(record['commands'], expected_arguments):
        if (command['argv'] != [record['ctest']['origin'], '--test-dir',
                                record['build'], *arguments]
                or type(command['exit_code']) is not int or command['exit_code'] != 0
                or command['child_waited'] is not True
                or type(command['child_pid']) is not int or command['child_pid'] <= 0):
            raise ValueError('Native contract command failed or differs')
    names = validate_reports((directory / 'discovery.json').read_bytes(),
                             (directory / 'ctest.xml').read_bytes())
    if record['tests'] != names:
        raise ValueError('Native contract test inventory changed')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ctest', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Actual renderer contract capture requires Linux')
    result = run(args.build_dir, args.output, args.ctest)
    print(result['status'], len(result['tests']))


if __name__ == '__main__':
    main()
