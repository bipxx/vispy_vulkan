# SPDX-License-Identifier: AGPL-3.0-only
"""Explicitly synthetic full Linux capture: no commands or native build ran.

This constructs small report inputs for semantic validator tests. Synthetic
command receipts and ELF headers must never be used as real producer evidence.
"""
import io
import json
from pathlib import Path, PurePosixPath
import struct
import textwrap
import zipfile

from tools import qualification_linux_native as native
from tools.run_linux_native_contracts import MINIMUM


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


class Capture:
    def __init__(self, root, project, definitions):
        self.root = root
        self.workspace = PurePosixPath('/synthetic/workspace')
        self.source = PurePosixPath('/synthetic/source')
        self.run_id = 'native-ci-123-1'
        self.evidence = self.workspace/'build/runs'/self.run_id
        self.scratch = self.workspace/'build/work'/self.run_id
        self.native = self.scratch/'native'
        self.python = str(self.scratch/'env/bin/python')
        self.data = {}
        schema = root/native.SCHEMA
        schema.parent.mkdir(parents=True)
        schema.write_bytes(encoded({'$defs': definitions}))
        inputs = {name: (project/name).read_bytes() for name in native.PROTOCOL}
        assert all(native.sha(inputs[name]) == checksum for name, checksum in native.PROTOCOL.items())
        inputs.update({'compat/build-hygiene.json': (project/'compat/build-hygiene.json').read_bytes(),
                       'uv.lock': b'synthetic lock', 'pyproject.toml': b'synthetic project',
                       'cmake/dependencies.lock.json': b'synthetic dependency lock',
                       'src/renderer.cpp': b'// synthetic production source',
                       'LICENSE': b'Synthetic fixture; project license is retained separately'})
        self.production = {'src/renderer.cpp': native.sha(inputs['src/renderer.cpp'])}
        source_map = {name: native.sha(raw) for name, raw in inputs.items()}
        with io.BytesIO() as stream:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, raw in inputs.items(): archive.writestr(name, raw)
            self.put('source-inputs.zip', stream.getvalue())
        self.put('source-before.json', source_map)
        self.put('source-after.json', source_map)
        policy = json.loads(inputs['compat/build-hygiene.json'])
        self.put('hygiene-policy.json', inputs['compat/build-hygiene.json'])
        self.put('preflight.json', dict(status='PASS_PREFLIGHT', registered=True,
            owner='ci', scratch_root=str(self.scratch), max_scratch_bytes=policy['max_scratch_bytes'],
            min_free_bytes=policy['min_free_bytes'], expected_peak_bytes=1024,
            free_bytes=policy['min_free_bytes']+1024))
        settings = dict(VISPY_BUILD_CONTRACT_TESTS='ON', VISPY_CPU_CONTRACTS_ONLY='OFF',
            VISPY_INPLACE='OFF', VISPY_VERIFY_DEPENDENCIES='ON', DAWN_ENABLE_VULKAN='ON',
            DAWN_ENABLE_METAL='OFF', DAWN_ENABLE_NULL='OFF', TINT_BUILD_SPV_READER='ON',
            DAWN_ENABLE_SPIRV_VALIDATION='ON', CMAKE_HOME_DIRECTORY=str(self.source),
            CMAKE_CACHEFILE_DIR=str(self.native), CMAKE_BUILD_TYPE='Release', VISPY_NATIVE_SDK='',
            Python_EXECUTABLE=self.python, CMAKE_C_COMPILER='/synthetic/tools/cc',
            CMAKE_CXX_COMPILER='/synthetic/tools/c++',
            CMAKE_COMMAND=str(self.scratch/'env/lib/python3.12/site-packages/cmake/data/bin/cmake'),
            CMAKE_CTEST_COMMAND=str(self.scratch/'env/lib/python3.12/site-packages/cmake/data/bin/ctest'),
            CMAKE_MAKE_PROGRAM='/synthetic/tools/ninja')
        cache = ''.join(f'{key}:STRING={value}\n' for key,value in settings.items()).encode()
        graph = {'CMakeCache.txt': cache, 'build.ninja': b'# synthetic graph',
                 'CMakeFiles/rules.ninja': b'# synthetic rules', 'CTestTestfile.cmake': b'# synthetic tests',
                 'compile_commands.json': encoded([dict(directory=str(self.native),
                    file=str(self.source/'src/renderer.cpp'),
                    command='/synthetic/tools/c++ -o CMakeFiles/_dawn.dir/renderer.cpp.o -c /synthetic/source/src/renderer.cpp')])}
        raw_elf = bytearray(64); raw_elf[:6] = b'\x7fELF\x02\x01'; struct.pack_into('<H', raw_elf, 18, 62)
        raw_elf = bytes(raw_elf)+b'synthetic raw output'
        stripped = bytes(raw_elf[:64])+b'synthetic stripped output'
        wheel_members = {}; origins = {}
        for member, name in native.MEMBERS.items():
            raw = b'{"synthetic":true}' if member.endswith('.json') else raw_elf
            shipping = raw if member.endswith('.json') else stripped
            graph[name] = raw; wheel_members[member] = shipping
            self.put('native-origin/'+member, shipping)
            origins[member] = dict(raw_sha256=native.sha(raw), wheel_stripped_sha256=native.sha(shipping))
        artifact_map = {}
        for name, raw in graph.items():
            origin = self.workspace/'build/artifacts'/native.sha(raw)/PurePosixPath(name).name
            self.data[str(origin)] = raw
            artifact_map[name] = dict(path=str(origin), sha256=native.sha(raw))
        for phase in ('wheel-build','archive'): self.put(phase+'-build-inputs-outputs.json', artifact_map)
        tools = {role: dict(origin=settings[role], resolved=settings[role], sha256='a'*64)
                 for role in ('CMAKE_C_COMPILER','CMAKE_CXX_COMPILER','CMAKE_COMMAND','CMAKE_CTEST_COMMAND','CMAKE_MAKE_PROGRAM')}
        tools.update({'build-python':dict(origin=self.python, sha256='b'*64),
                      'python-environment':dict(synthetic=True)})
        for phase in ('wheel-build','archive'): self.put(phase+'-toolchain.json', tools)
        names = sorted(MINIMUM)
        self.put('native-contracts/discovery.json', dict(kind='ctestInfo',version=dict(major=1,minor=0),
                 tests=[dict(name=name) for name in names]))
        self.put('native-contracts/discovery.log', b'synthetic discovery stderr')
        self.put('native-contracts/ctest.log', b'synthetic CTest stdout')
        self.put('native-contracts/ctest.xml', ('<testsuite>'+''.join('<testcase name="'+name+'"/>' for name in names)+'</testsuite>').encode())
        ctest = str(self.scratch/'env/bin/ctest'); contract_dir = str(self.evidence/'native-contracts')
        contract = dict(status='PASS_LINUX_RENDERER_CONTRACTS', build=str(self.native),cache_sha256=native.sha(cache),
            producer_admitted=False,artifact_admitted=False,hardware_qualified=False,tests=names,
            files={name:native.sha(self.data[str(self.evidence/'native-contracts'/name)])
                   for name in ('discovery.json','discovery.log','ctest.xml','ctest.log')},
            ctest=dict(origin=ctest,sha256=native.sha(native.ctest_launcher_bytes(str(self.scratch/'env/bin/python3')))),commands=[
                dict(argv=[ctest,'--test-dir',str(self.native),'--show-only=json-v1'],exit_code=0,child_waited=True,child_pid=301),
                dict(argv=[ctest,'--test-dir',str(self.native),'--output-on-failure','--no-tests=error','--output-junit',contract_dir+'/ctest.xml'],
                     exit_code=0,child_waited=True,child_pid=302)])
        self.put('native-contracts/result.json', contract)
        wheel = str(self.evidence/'wheels/synthetic-cp312-cp312-linux_x86_64.whl')
        with io.BytesIO() as stream:
            with zipfile.ZipFile(stream,'w') as archive:
                for name,raw in wheel_members.items():archive.writestr(name,raw)
            self.data[wheel] = stream.getvalue()
        self.put('archive.json',dict(status='PASS_LINUX_RENDERER_WHEEL_ARCHIVE',hardware_qualified=False,
            manylinux_qualified=False,source_revision='a'*40,wheel=wheel,wheel_sha256=native.sha(self.data[wheel]),
            native_contracts=dict(tests=names,sha256=native.sha(encoded(contract))),native_origin=origins))
        self.put('source-revision.txt', ('a'*40).encode())
        self.put('ci-identity.json',dict(repository='bipxx/vispy_vulkan',checked_head='a'*40,run_id=123,attempt=1,
            workflow=dict(path='.github/workflows/linux-vulkan.yml',sha256=native.PROTOCOL['.github/workflows/linux-vulkan.yml'])))
        self.put('native-environment.json',dict(python_executable=self.python,machine='x86_64',python='3.12.8 synthetic',
            python_executable_sha256='b'*64,base_python_executable_sha256='b'*64,
            base_python_executable='/synthetic/base/bin/python',
            packages={**native.BUILD_PACKAGES,'numpy':'2.3.5'},
            input_sha256={name:source_map[name] for name in ('uv.lock','pyproject.toml','cmake/dependencies.lock.json')},
            commands=dict(git=dict(stdout='a'*40))))
        self.put('prepare-environment-aliases.json',dict(actions=[dict(
            link=str(self.scratch/'env/bin/python3'),target='/synthetic/base/bin/python3.12',
            action='copy-interpreter',sha256='b'*64)]))
        argv = {
            'native-environment':[self.python,'.github/workflows/qualification_gate.py','capture','--without-package','--output',str(self.evidence/'native-environment.json')],
            'dependency-before':[self.python,'cmake/verify_dependencies.py'],
            'dependency-after':[self.python,'cmake/verify_dependencies.py'],
            'wheel-build':['uv','build','--python',self.python,'--no-build-isolation','--wheel','--out-dir',str(self.evidence/'wheels'),
                '--config-setting','build-dir='+str(self.native),'--config-setting','cmake.define.VISPY_INPLACE=OFF',
                '--config-setting','cmake.define.VISPY_CPU_CONTRACTS_ONLY=OFF','--config-setting','cmake.define.VISPY_BUILD_CONTRACT_TESTS=ON',
                '--config-setting','cmake.define.VISPY_VERIFY_DEPENDENCIES=ON','--config-setting','cmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=ON'],
            'native-contracts':[self.python,'-B','tools/run_linux_native_contracts.py','--build-dir',str(self.native),'--ctest',ctest,'--output',contract_dir],
            'archive':[self.python,'-B','tools/audit_linux_wheel.py','--wheel',wheel,'--build-dir',str(self.native),
                '--contracts',contract_dir,'--output',str(self.evidence/'archive.json')]}
        # Independently dedent this pinned workflow's literal run blocks. This
        # fixture needs neither an optional YAML package nor a general parser.
        lines = inputs['.github/workflows/linux-vulkan.yml'].decode().splitlines(keepends=True)
        blocks = []
        for index, line in enumerate(lines):
            if line.strip() != 'run: |': continue
            indentation = len(line)-len(line.lstrip())
            block = []
            for following in lines[index+1:]:
                if following.strip() and len(following)-len(following.lstrip()) <= indentation: break
                block.append(following)
            blocks.append(textwrap.dedent(''.join(block)))
        for phase in ('prepare','driver'):
            body = next(block for block in blocks if 'run --phase '+phase+' --script-stdin' in block)
            script = body.split("<<'PHASE'\n",1)[1].rsplit('PHASE\n',1)[0]
            script = script.replace('${{ github.run_id }}','123').replace('${{ github.run_attempt }}','1')
            self.put(phase+'.sh',script.encode())
            argv[phase] = ['bash','--noprofile','--norc','-e','-o','pipefail',str(self.evidence/(phase+'.sh'))]
        commands = []
        for phase in ('prepare','driver',*native.NATIVE_PHASES):
            self.put(phase+'.log',b'explicitly synthetic process output')
            receipt = dict(argv=argv[phase],cwd=str(self.source),child_pid=200+len(commands),child_waited=True,
                actual_exit=0,log_sha256=native.sha(b'explicitly synthetic process output'),environment={})
            self.put(phase+'-process.json',receipt)
            commands.append(dict(path=str(self.evidence/(phase+'-process.json')),sha256=native.sha(encoded(receipt))))
        self.put('state.json',dict(schema=1,source=str(self.source),workspace=str(self.workspace),run_id=self.run_id,
            owner='ci',scratch=str(self.scratch),evidence=str(self.evidence),policy_sha256=native.sha(inputs['compat/build-hygiene.json']),
            registry_required=False,commands=commands,exit_code=0,active=None,admitted=False))

    def put(self,name,value):
        self.data[str(self.evidence/name)] = value if isinstance(value,bytes) else encoded(value)

    def document(self,name):return json.loads(self.data[str(self.evidence/name)])

    def edit(self,name,change):
        value = self.document(name)
        change(value)
        self.put(name,value)

    def refresh_receipts(self):
        def update(state):
            for row in state['commands']:row['sha256'] = native.sha(self.data[row['path']])
        self.edit('state.json',update)

    def refresh_contract_link(self):
        self.edit('archive.json', lambda value:value['native_contracts'].update(
            sha256=native.sha(self.data[str(self.evidence/'native-contracts/result.json')])) )

    def finish(self):
        retained = [dict(path=origin,sha256=native.sha(raw),roles=['source','licenses','evidence','repro'])
                    for origin,raw in self.data.items()]
        terminal = dict(schema=1,run_id=self.run_id,owner='ci',scratch_root=str(self.scratch),state='succeeded',
                        process_exit=0,child_waited=True,retained=retained)
        self.put('terminal.json',terminal)
        self.put('cleanup-plan.json',dict(schema=1,kind='build-hygiene-cleanup-plan',workspace=str(self.workspace),
            scratch_root=str(self.scratch),manifest=str(self.evidence/'terminal.json'),manifest_sha256=native.sha(encoded(terminal)),
            policy_sha256=native.sha(self.data[str(self.evidence/'hygiene-policy.json')]),registry=None,registry_sha256=None,
            run_id=self.run_id,owner='ci',retained=retained,snapshot=dict(files=[],directories=[dict(path='.')])) )
        self.put('cleanup-result.json',dict(status='PASS_APPLY',scratch_root=str(self.scratch),deleted=0,retained_verified=len(retained)))
        refs = {}
        for i,(origin,raw) in enumerate(self.data.items()):
            path = self.root/'retained'/str(i);path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
            refs[origin] = dict(path=path.relative_to(self.root).as_posix(),sha256=native.sha(raw))
        return dict(schema=1,kind='original-linux-ci-capture-v1',state=refs[str(self.evidence/'state.json')],
            terminal=refs[str(self.evidence/'terminal.json')],plan=refs[str(self.evidence/'cleanup-plan.json')],
            cleanup=refs[str(self.evidence/'cleanup-result.json')],
            files=[dict(origin=row['path'],file=refs[row['path']]) for row in retained])
