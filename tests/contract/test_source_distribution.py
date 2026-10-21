"""Source archives retain vendored inputs hidden by upstream Git ignores."""
import json
from pathlib import Path
import tarfile
import tempfile

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

from scikit_build_core.build import build_sdist


ROOT = Path(__file__).resolve().parents[2]


def test_sdist_retains_ignored_vendor_sources_without_build_junk(monkeypatch):
    settings = tomllib.loads((ROOT / 'pyproject.toml').read_text())['tool']['scikit-build']
    required = (
        'third_party/dawn/third_party/abseil-cpp/absl/base/config.h',
        'third_party/dawn/third_party/glslang/src/glslang/CMakeLists.txt',
        'third_party/dawn/third_party/spirv-headers/src/include/spirv/spirv.h',
        'third_party/dawn/third_party/spirv-tools/src/source/spirv.cpp',
        'third_party/dawn/third_party/vulkan-headers/src/include/vulkan/vulkan.h',
        'third_party/dawn/third_party/vulkan-loader/src/loader/loader.c',
        'third_party/dawn/third_party/vulkan-utility-libraries/src/CMakeLists.txt',
        'third_party/dawn/third_party/jinja2/__init__.py',
        'third_party/dawn/third_party/markupsafe/__init__.py',
        'third_party/dawn/tools/android/gradle/wrapper/gradle-wrapper.properties',
        'LICENSE', 'LICENSE-BSD', 'LICENSING.md',
    )
    junk = tuple('third_party/dawn/third_party/glslang/src/' + suffix for suffix in (
        '__pycache__/cached.pyc', '.git/config', 'build/leftover.o', 'out/leftover.o', '.cache/leftover',
    )) + ('build/leftover.o', 'dist/old.whl', 'src/vispy/_dawn.fake.so')
    with tempfile.TemporaryDirectory(prefix='vispy-sdist-contract-') as temporary:
        source = Path(temporary) / 'source'
        source.mkdir()
        for name in (*required, *junk):
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        for name in ('.gitignore', 'third_party/dawn/.gitignore', 'third_party/dawn/tools/android/.gitignore'):
            (source / name).write_bytes((ROOT / name).read_bytes())
        (source / 'pyproject.toml').write_text(
            '[project]\nname="sdist-fixture"\nversion="1.0"\n'
            '[tool.scikit-build]\nminimum-version="0.10"\n'
            'sdist.include=' + json.dumps(settings['sdist'].get('include', [])) + '\n'
            'sdist.exclude=' + json.dumps(settings['sdist']['exclude']) + '\n'
        )
        output = Path(temporary) / 'artifacts'
        with monkeypatch.context() as context:
            context.chdir(source)
            filename = build_sdist(str(output))
        with tarfile.open(output / filename, 'r:gz') as archive:
            names = {member.name.removeprefix('sdist_fixture-1.0/') for member in archive if member.isfile()}
        assert set(required) <= names
        assert not (set(junk) & names)
