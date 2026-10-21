"""SDK policy contracts use explicit synthetic vendor artifacts; no native builds."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sdk_policy", ROOT / "cmake/native_sdk.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


@pytest.fixture
def prepared(tmp_path):
    prefix = tmp_path / "SDK"
    compiler = tmp_path / "compiler.exe"
    compiler.write_bytes(b"synthetic compiler fingerprint; never executed")
    settings = dict(system="Windows", architecture="AMD64", pointer_bytes=8,
                    configuration="Release", runtime="MultiThreadedDLL", cmake_version="4.4.4",
                    compiler=str(compiler), compiler_version="19.44.35225.0", windows_sdk="10.0.22621.0",
                    cxx_flags="/DWIN32 /D_WINDOWS /EHsc /D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR",
                    msvc_mutex_policy="msvc-stl-init-in-situ-v1", release_flags="/O2 /Ob2 /DNDEBUG",
                    dawn_backend_vulkan="ON", dawn_backend_null="OFF", dawn_backend_metal="OFF",
                    dawn_monolithic="STATIC")
    (prefix / "lib").mkdir(parents=True)
    for name in sorted(sdk.ARCHIVES):
        (prefix / "lib" / name).write_bytes(b"synthetic archive: " + name.encode())
    (prefix / "include").mkdir()
    (prefix / "include/test.h").write_text("// immutable synthetic header\n")
    metadata = prefix / "share/VispyNativeSDK"
    metadata.mkdir(parents=True)
    lock = ROOT / "cmake/dependencies.lock.json"
    shutil.copyfile(lock, metadata / "dependencies.lock.json")
    (metadata / "producer.json").write_text(json.dumps(settings), encoding="utf-8")
    config = prefix / "lib/cmake/VispyNativeSDK"
    config.mkdir(parents=True)
    (config / "VispyNativeSDKConfig.cmake").write_text(
        'include("${CMAKE_CURRENT_LIST_DIR}/VispyNativeSDKTargets.cmake")\n')
    export = 'get_filename_component(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)\n'
    for name, filename in [("webgpu_dawn", "webgpu_dawn.lib"), ("glslang", "glslang.lib"),
                           ("glslang-default-resource-limits", "glslang-default-resource-limits.lib"),
                           ("SPIRV-Tools-static", "SPIRV-Tools.lib"), ("SPIRV-Tools-opt", "SPIRV-Tools-opt.lib")]:
        export += f'add_library(vispy_native::{name} STATIC IMPORTED)\n'
        export += f'set_target_properties(vispy_native::{name} PROPERTIES IMPORTED_LOCATION "${{_IMPORT_PREFIX}}/lib/{filename}" INTERFACE_INCLUDE_DIRECTORIES "${{_IMPORT_PREFIX}}/include")\n'
    export += 'set_target_properties(vispy_native::SPIRV-Tools-opt PROPERTIES INTERFACE_LINK_LIBRARIES vispy_native::SPIRV-Tools-static)\n'
    (config / "VispyNativeSDKTargets.cmake").write_text(export)
    record = dict(format_version=2, qualification="vendor_artifact_reuse_only",
                  producer=settings, compiler_sha256=sdk.sha256(compiler),
                  producer_cpp_project_policies={"synthetic.vcxproj": {"cpp_items": 1, "policy": settings["msvc_mutex_policy"]}},
                  dependency_lock_sha256=sdk.sha256(lock), files=sdk.inventory(prefix))
    manifest = prefix / "manifest.json"
    manifest.write_text(json.dumps(record), encoding="utf-8")
    return prefix, sdk.sha256(manifest), lock, settings


def test_sdk_inventory_relocates_without_original_sdk_directory(prepared, tmp_path):
    prefix, digest, lock, settings = prepared
    relocated = tmp_path / "relocated" / "SDK Unicode \u03c0"
    shutil.copytree(prefix, relocated)
    assert prefix.resolve().parent == tmp_path.resolve()
    shutil.rmtree(prefix)
    assert sdk.verify(relocated, digest, lock, settings)["files"]


@pytest.mark.parametrize("field,value", [("architecture", "ARM64"), ("pointer_bytes", 4),
    ("configuration", "Debug"), ("runtime", "MultiThreaded"), ("system", "Linux"),
    ("compiler_version", "19.40"), ("windows_sdk", "10.0.19041.0"),
    ("cxx_flags", "/D_ITERATOR_DEBUG_LEVEL=2"), ("release_flags", "/MDd"), ("cmake_version", "3.22")])
def test_incompatible_consumer_rejected(prepared, field, value):
    prefix, digest, lock, settings = prepared
    with pytest.raises(sdk.SDKError, match="mismatch"):
        sdk.verify(prefix, digest, lock, dict(settings, **{field: value}))


@pytest.mark.parametrize("path", ["lib/webgpu_dawn.lib", "include/test.h",
                                  "lib/cmake/VispyNativeSDK/VispyNativeSDKTargets.cmake"])
def test_tampered_archive_header_or_export_rejected(prepared, path):
    prefix, digest, lock, settings = prepared
    with (prefix / path).open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(sdk.SDKError, match="inventory/checksum"):
        sdk.verify(prefix, digest, lock, settings)


def test_rewritten_manifest_wrong_pins_or_changed_compiler_rejected(prepared, tmp_path):
    prefix, digest, lock, settings = prepared
    wrong_lock = tmp_path / "wrong-pins.json"
    wrong_lock.write_text("{}")
    with pytest.raises(sdk.SDKError, match="source pins"):
        sdk.verify(prefix, digest, wrong_lock, settings)
    Path(settings["compiler"]).write_bytes(b"different compiler")
    with pytest.raises(sdk.SDKError, match="compiler binary"):
        sdk.verify(prefix, digest, lock, settings)
    (prefix / "manifest.json").write_text("{}")
    with pytest.raises(sdk.SDKError, match="manifest checksum"):
        sdk.verify(prefix, digest, lock, settings)


def test_abi_leaf_or_external_export_cannot_be_readmitted_with_new_manifest(prepared):
    prefix, _, lock, settings = prepared
    record = json.loads((prefix / "manifest.json").read_text())
    (prefix / "lib/nanobind-static.lib").write_bytes(b"ABI leaf")
    record["files"] = sdk.inventory(prefix)
    (prefix / "manifest.json").write_text(json.dumps(record))
    with pytest.raises(sdk.SDKError, match="five vendor archives"):
        sdk.verify(prefix, sdk.sha256(prefix / "manifest.json"), lock, settings)
    (prefix / "lib/nanobind-static.lib").unlink()
    export = prefix / "lib/cmake/VispyNativeSDK/VispyNativeSDKTargets.cmake"
    export.write_text('set(ROOT_BUILD "C:/original/build")')
    record["files"] = sdk.inventory(prefix)
    (prefix / "manifest.json").write_text(json.dumps(record))
    with pytest.raises(sdk.SDKError, match="external build/ABI"):
        sdk.verify(prefix, sdk.sha256(prefix / "manifest.json"), lock, settings)


def test_cmake_generator_expressions_are_not_misread_as_drive_paths(prepared):
    prefix, _, lock, settings = prepared
    record = json.loads((prefix / "manifest.json").read_text())
    path = prefix / "lib/cmake/VispyNativeSDK/VispyNativeSDKTargets.cmake"
    with path.open("a") as stream:
        stream.write('\n# \\$<LINK_ONLY:\\$<\\$<BOOL:LIBRT-NOTFOUND>:-lrt>>\n')
    record["files"] = sdk.inventory(prefix)
    (prefix / "manifest.json").write_text(json.dumps(record))
    assert sdk.verify(prefix, sdk.sha256(prefix / "manifest.json"), lock, settings)


def test_relocated_sdk_cmake_import_and_aliases_configure_without_compilation(prepared, tmp_path):
    prefix, digest, _, settings = prepared
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    variables = dict(WIN32="TRUE", MSVC="TRUE", VISPY_CPU_CONTRACTS_ONLY="FALSE",
                     VISPY_NATIVE_SDK=prefix.as_posix(), VISPY_NATIVE_SDK_MANIFEST_SHA256=digest,
                     Python_EXECUTABLE=Path(sys.executable).as_posix(),
                     CMAKE_SYSTEM_NAME=settings["system"], CMAKE_SYSTEM_PROCESSOR=settings["architecture"],
                     CMAKE_SIZEOF_VOID_P="8", CMAKE_CXX_COMPILER=Path(settings["compiler"]).as_posix(),
                     CMAKE_CXX_COMPILER_VERSION=settings["compiler_version"],
                     CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION=settings["windows_sdk"],
                     CMAKE_CXX_FLAGS=settings["cxx_flags"], CMAKE_CXX_FLAGS_RELEASE=settings["release_flags"])
    variables["VISPY_MSVC_MUTEX_POLICY"] = settings["msvc_mutex_policy"]
    text = "cmake_minimum_required(VERSION 3.22)\nproject(SDKImport LANGUAGES NONE)\n"
    for name, value in variables.items():
        text += f'set({name} "{value}")\n'
    text += f'set(CMAKE_SOURCE_DIR "{ROOT.as_posix()}")\ninclude("{ROOT.as_posix()}/cmake/NativeSDK.cmake")\nvispy_import_native_sdk()\n'
    text += 'foreach(name webgpu_dawn glslang glslang-default-resource-limits SPIRV-Tools-static SPIRV-Tools-opt)\nif(NOT TARGET ${name})\nmessage(FATAL_ERROR "SDK alias missing")\nendif()\nendforeach()\n'
    text += 'get_target_property(deps SPIRV-Tools-opt INTERFACE_LINK_LIBRARIES)\nif(NOT deps STREQUAL "vispy_native::SPIRV-Tools-static")\nmessage(FATAL_ERROR "SDK static dependency missing")\nendif()\n'
    (consumer / "CMakeLists.txt").write_text(text, encoding="utf-8")
    import cmake
    executable = Path(cmake.CMAKE_BIN_DIR) / ("cmake.exe" if sys.platform == "win32" else "cmake")
    result = subprocess.run([str(executable), "-S", str(consumer), "-B", str(tmp_path / "cache"),
                             "-G", "Ninja"], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_old_sdk_schema_and_wrong_archive_compiler_policy_are_rejected(prepared):
    prefix, digest, lock, settings = prepared
    with pytest.raises(sdk.SDKError, match="msvc_mutex_policy mismatch"):
        sdk.verify(prefix, digest, lock, dict(settings, msvc_mutex_policy="msvc-stl-constexpr-v1"))
    manifest = prefix / "manifest.json"
    record = json.loads(manifest.read_text())
    record["format_version"] = 1
    manifest.write_text(json.dumps(record))
    with pytest.raises(sdk.SDKError, match="Unsupported SDK format"):
        sdk.verify(prefix, sdk.sha256(manifest), lock, settings)
    record["format_version"] = 2
    record["producer_cpp_project_policies"]["synthetic.vcxproj"]["policy"] = "msvc-stl-constexpr-v1"
    manifest.write_text(json.dumps(record))
    with pytest.raises(sdk.SDKError, match=r"archive C\+\+ compiler policy"):
        sdk.verify(prefix, sdk.sha256(manifest), lock, settings)


def test_actual_project_item_override_cannot_hide_an_unqualified_vendor_object(tmp_path):
    path = tmp_path / "vendor.vcxproj"
    template = '''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
<ClCompile><PreprocessorDefinitions>NDEBUG;_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR</PreprocessorDefinitions></ClCompile>
</ItemDefinitionGroup><ItemGroup><ClCompile Include="vendor.cpp">{item}</ClCompile></ItemGroup></Project>'''
    path.write_text(template.format(item=""))
    assert sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")["cpp_items"] == 1
    path.write_text(template.format(item="<PreprocessorDefinitions>NDEBUG</PreprocessorDefinitions>"))
    with pytest.raises(sdk.SDKError, match="compiler mutex policy mismatch"):
        sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")
    path.write_text(template.format(item="<PreprocessorDefinitions>LOCAL;%(PreprocessorDefinitions)</PreprocessorDefinitions>"))
    assert sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")["cpp_items"] == 1


@pytest.mark.parametrize("properties", [
    "<AdditionalOptions>/U_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR</AdditionalOptions>",
    "<AdditionalOptions>/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR /U _DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR</AdditionalOptions>",
    "<UndefinePreprocessorDefinitions>_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR</UndefinePreprocessorDefinitions>",
])
def test_project_explicit_undefinition_cannot_attest_compatible_mutex_policy(tmp_path, properties):
    path = tmp_path / "vendor.vcxproj"
    path.write_text('''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'"><ClCompile>
<PreprocessorDefinitions>_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR</PreprocessorDefinitions>
''' + properties + '''</ClCompile></ItemDefinitionGroup>
<ItemGroup><ClCompile Include="vendor.cpp" /></ItemGroup></Project>''')
    with pytest.raises(sdk.SDKError, match="macro undefinition"):
        sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")


def test_project_missing_common_compiler_settings_is_a_policy_error(tmp_path):
    path = tmp_path / "vendor.vcxproj"
    path.write_text('''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
<ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" />
<ItemGroup><ClCompile Include="vendor.cpp" /></ItemGroup></Project>''')
    with pytest.raises(sdk.SDKError, match="Missing Release/x64 ClCompile"):
        sdk.project_mutex_policy(path, "msvc-stl-init-in-situ-v1")


@pytest.mark.parametrize("flags", ["/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR", '/D "_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR=1"'])
def test_macro_definition_requires_an_exact_name(flags):
    assert sdk.mutex_macro_defined("", flags)
    assert not sdk.mutex_macro_defined("", "/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR_SUFFIX")
    assert not sdk.mutex_macro_defined("", "/FI_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR")


def test_sdk_producer_flags_cannot_attest_an_explicit_undefinition(prepared):
    prefix, _, lock, settings = prepared
    settings["release_flags"] += " /U_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR"
    (prefix / "share/VispyNativeSDK/producer.json").write_text(json.dumps(settings))
    manifest = prefix / "manifest.json"
    record = json.loads(manifest.read_text())
    record["producer"] = settings
    record["files"] = sdk.inventory(prefix)
    manifest.write_text(json.dumps(record))
    with pytest.raises(sdk.SDKError, match="macro undefinition"):
        sdk.verify(prefix, sdk.sha256(manifest), lock, settings)


def test_windows_policy_is_idempotent_and_explicitly_reversible(tmp_path):
    script = tmp_path / "policy.cmake"
    helper = (ROOT / "cmake/WindowsCompilerPolicy.cmake").as_posix()
    script.write_text(f'''set(WIN32 TRUE)
set(MSVC TRUE)
set(CMAKE_CXX_FLAGS "/DWIN32 /EHsc")
include("{helper}")
include("{helper}")
string(REGEX MATCHALL "_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR" matches "${{CMAKE_CXX_FLAGS}}")
list(LENGTH matches count)
if(NOT count EQUAL 1 OR NOT VISPY_MSVC_MUTEX_POLICY STREQUAL "msvc-stl-init-in-situ-v1")
message(FATAL_ERROR "Global policy was not applied exactly once")
endif()
set(VISPY_LEGACY_MSVC_CRT_MUTEX OFF CACHE BOOL "" FORCE)
include("{helper}")
if(NOT CMAKE_CXX_FLAGS STREQUAL "/DWIN32 /EHsc" OR NOT VISPY_MSVC_MUTEX_POLICY STREQUAL "msvc-stl-constexpr-v1")
message(FATAL_ERROR "Explicit modern policy did not remove its owned switch")
endif()
''')
    import cmake
    executable = Path(cmake.CMAKE_BIN_DIR) / ("cmake.exe" if sys.platform == "win32" else "cmake")
    result = subprocess.run([str(executable), "-P", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
