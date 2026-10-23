cmake_minimum_required(VERSION 3.22)
if(CMAKE_HOST_APPLE AND NOT CMAKE_OSX_DEPLOYMENT_TARGET)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "13.0" CACHE STRING "Minimum qualified macOS release" FORCE)
endif()
project(vispy_dawn LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(cmake/WindowsCompilerPolicy.cmake)

find_package(Python 3.10 REQUIRED COMPONENTS Interpreter Development.Module NumPy)
if(NOT nanobind_DIR)
    execute_process(COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_VARIABLE nanobind_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
        COMMAND_ERROR_IS_FATAL ANY)
endif()
find_package(nanobind CONFIG REQUIRED)
option(VISPY_INPLACE "Copy extension artifacts into src/vispy for direct source imports" OFF)
option(VISPY_VERIFY_DEPENDENCIES "Verify the immutable vendored source manifest" ON)
option(VISPY_BUILD_CONTRACT_TESTS "Build CPU shader, texture, state, and point contracts" OFF)
set(VISPY_CONTRACT_TESTS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/tests" CACHE PATH "Frozen C++ contract sources and shader corpus")
set(VISPY_CONTRACT_DATASETS_ROOT "" CACHE PATH "Optional frozen captured point, marker, text, and volume shader datasets")
option(VISPY_CPU_CONTRACTS_ONLY "Build CPU contracts with Dawn's null backend, without a renderer" OFF)
option(VISPY_EXPORT_NATIVE_SDK "Export the configured vendor libraries in a separate SDK install component" OFF)
set(VISPY_NATIVE_SDK "" CACHE PATH "Immutable SDK for ABI-isolated native leaf builds")
set(VISPY_NATIVE_SDK_MANIFEST_SHA256 "" CACHE STRING "Expected SHA-256 of the selected SDK manifest")
include(cmake/NativeSDK.cmake)
if(VISPY_CPU_CONTRACTS_ONLY AND SKBUILD)
    message(FATAL_ERROR "CPU contract mode cannot produce an installable renderer wheel")
endif()
# Optional immutable origin authority; every value is forwarded explicitly.
set(VISPY_DEPENDENCY_ORIGIN_WORKSPACE "" CACHE PATH "Original workspace containing admitted immutable origins")
set(VISPY_DEPENDENCY_LOCK "" CACHE FILEPATH "Separate new lock bound by admitted immutable origin authority")
set(_vispy_origin_names MODULE_SHA256 CONTEXT CONTEXT_SHA256 CAPTURE CAPTURE_SHA256
    CAPTURE_SEAL CAPTURE_SEAL_SHA256 ADMISSION ADMISSION_SHA256 ADMISSION_SEAL ADMISSION_SEAL_SHA256)
foreach(name IN LISTS _vispy_origin_names)
    set(VISPY_DEPENDENCY_ORIGIN_${name} "" CACHE STRING "Pinned immutable origin authority")
endforeach()
set(_vispy_origin_any "${VISPY_DEPENDENCY_ORIGIN_WORKSPACE}")
foreach(name IN LISTS _vispy_origin_names)
    string(APPEND _vispy_origin_any "${VISPY_DEPENDENCY_ORIGIN_${name}}")
endforeach()
set(_vispy_origin_args)
if(NOT _vispy_origin_any STREQUAL "")
    if(NOT VISPY_VERIFY_DEPENDENCIES OR NOT IS_ABSOLUTE "${VISPY_DEPENDENCY_ORIGIN_WORKSPACE}")
        message(FATAL_ERROR "Explicit immutable origins require verification and an absolute authority workspace")
    endif()
    if(VISPY_DEPENDENCY_LOCK STREQUAL "" OR NOT IS_ABSOLUTE "${VISPY_DEPENDENCY_LOCK}")
        message(FATAL_ERROR "Explicit immutable origins require their separate absolute dependency lock")
    endif()
    list(APPEND _vispy_origin_args --dependency-lock "${VISPY_DEPENDENCY_LOCK}")
    list(APPEND _vispy_origin_args --origin-workspace "${VISPY_DEPENDENCY_ORIGIN_WORKSPACE}")
    foreach(name IN LISTS _vispy_origin_names)
        if(VISPY_DEPENDENCY_ORIGIN_${name} STREQUAL "")
            message(FATAL_ERROR "Explicit immutable origins require every authority pin: ${name}")
        endif()
        string(TOLOWER "${name}" argument)
        string(REPLACE "_" "-" argument "${argument}")
        list(APPEND _vispy_origin_args "--origin-${argument}" "${VISPY_DEPENDENCY_ORIGIN_${name}}")
    endforeach()
elseif(NOT VISPY_DEPENDENCY_LOCK STREQUAL "")
    message(FATAL_ERROR "A separate dependency lock requires explicit immutable origin authority")
endif()
if(VISPY_VERIFY_DEPENDENCIES)
    set(_vispy_verify_args ${_vispy_origin_args})
    if(_vispy_origin_any STREQUAL "")
        list(APPEND _vispy_verify_args --restore-archive-metadata)
    endif()
    execute_process(
        COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/cmake/verify_dependencies.py" ${_vispy_verify_args}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMAND_ERROR_IS_FATAL ANY
    )
endif()

set(DAWN_SRC "${CMAKE_CURRENT_SOURCE_DIR}/third_party/dawn" CACHE PATH "Pinned Dawn source")
if(NOT VISPY_NATIVE_SDK AND NOT EXISTS "${DAWN_SRC}/CMakeLists.txt")
    message(FATAL_ERROR "Dawn pin is missing at ${DAWN_SRC}")
endif()

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(DAWN_FETCH_DEPENDENCIES OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_D3D11 OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_D3D12 OFF CACHE BOOL "" FORCE)
set(VISPY_PLATFORM_SOURCES cpp/platform/native_library.cpp)
set(VISPY_PLATFORM_LIBRARIES ${CMAKE_DL_LIBS})
if(VISPY_CPU_CONTRACTS_ONLY)
    set(VISPY_VULKAN OFF)
    set(VISPY_METAL OFF)
    set(VISPY_X11 OFF)
    set(DAWN_ENABLE_NULL ON CACHE BOOL "" FORCE)
elseif(WIN32)
    set(VISPY_VULKAN ON)
    set(VISPY_METAL OFF)
    set(VISPY_X11 OFF)
    list(APPEND VISPY_PLATFORM_SOURCES cpp/platform/surface_win32.cpp)
    set(DAWN_ENABLE_NULL OFF CACHE BOOL "" FORCE)
elseif(APPLE)
    enable_language(OBJCXX)
    set(CMAKE_OBJCXX_STANDARD 20)
    set(CMAKE_OBJCXX_STANDARD_REQUIRED ON)
    set(VISPY_VULKAN OFF)
    set(VISPY_METAL ON)
    set(VISPY_X11 OFF)
    list(APPEND VISPY_PLATFORM_SOURCES cpp/platform/surface_metal.mm)
    find_library(VISPY_COCOA_FRAMEWORK Cocoa REQUIRED)
    find_library(VISPY_QUARTZCORE_FRAMEWORK QuartzCore REQUIRED)
    find_library(VISPY_METAL_FRAMEWORK Metal REQUIRED)
    list(APPEND VISPY_PLATFORM_LIBRARIES
        ${VISPY_COCOA_FRAMEWORK} ${VISPY_QUARTZCORE_FRAMEWORK} ${VISPY_METAL_FRAMEWORK})
    set(DAWN_ENABLE_NULL OFF CACHE BOOL "" FORCE)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(VISPY_VULKAN ON)
    set(VISPY_METAL OFF)
    set(VISPY_X11 ON)
    find_package(X11 REQUIRED)
    list(APPEND VISPY_PLATFORM_SOURCES cpp/platform/surface_x11.cpp)
    list(APPEND VISPY_PLATFORM_LIBRARIES X11::X11)
    set(DAWN_ENABLE_NULL OFF CACHE BOOL "" FORCE)
else()
    message(FATAL_ERROR "Native renderer platforms are Windows, Linux X11, and macOS")
endif()
set(DAWN_ENABLE_METAL ${VISPY_METAL} CACHE BOOL "" FORCE)
set(DAWN_USE_X11 ${VISPY_X11} CACHE BOOL "" FORCE)
set(DAWN_USE_WAYLAND OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_DESKTOP_GL OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_OPENGLES OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_WEBGPU_ON_WEBGPU OFF CACHE BOOL "" FORCE)
set(DAWN_ENABLE_VULKAN ${VISPY_VULKAN} CACHE BOOL "" FORCE)
set(DAWN_ENABLE_SPIRV_VALIDATION ON CACHE BOOL "" FORCE)
set(DAWN_ENABLE_SWIFTSHADER OFF CACHE BOOL "" FORCE)
set(DAWN_BUILD_SAMPLES OFF CACHE BOOL "" FORCE)
set(DAWN_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(DAWN_BUILD_BENCHMARKS OFF CACHE BOOL "" FORCE)
set(DAWN_USE_GLFW OFF CACHE BOOL "" FORCE)
set(DAWN_BUILD_MONOLITHIC_LIBRARY "STATIC" CACHE STRING "" FORCE)
set(TINT_BUILD_SPV_READER ON CACHE BOOL "" FORCE)
set(TINT_BUILD_WGSL_WRITER ON CACHE BOOL "" FORCE)
set(TINT_BUILD_SPV_WRITER ON CACHE BOOL "" FORCE)
set(TINT_BUILD_MSL_WRITER ${VISPY_METAL} CACHE BOOL "" FORCE)
set(TINT_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(TINT_BUILD_CMD_TOOLS OFF CACHE BOOL "" FORCE)
set(TINT_BUILD_FUZZERS OFF CACHE BOOL "" FORCE)
set(DAWN_BUILD_PROTOBUF OFF CACHE BOOL "" FORCE)
# The extension uses Dawn's headers, not its optional C++ module interface.
# A successful module syntax probe does not imply Ninja dependency-scan support.
set(DAWN_SUPPORTS_CXX_MODULES OFF CACHE BOOL "Header-based VisPy extension" FORCE)
set(TINT_BUILD_IR_BINARY OFF CACHE BOOL "" FORCE)

if(VISPY_NATIVE_SDK)
    if(VISPY_EXPORT_NATIVE_SDK)
        message(FATAL_ERROR "A consumer SDK cannot also export a producer SDK")
    endif()
    vispy_import_native_sdk()
    set(VISPY_SHADER_INCLUDE_ROOT "${VISPY_NATIVE_SDK}/include")
    set(VISPY_VULKAN_INCLUDE_ROOT "${VISPY_NATIVE_SDK}/include")
else()
add_subdirectory("${DAWN_SRC}" "${CMAKE_BINARY_DIR}/dawn" EXCLUDE_FROM_ALL)

# Dawn only vendors glslang when Tint command-line tools are on. This fork
# calls TShader::parse itself, so build the pinned glslang here.
set(ENABLE_GLSLANG_BINARIES OFF CACHE BOOL "" FORCE)
set(GLSLANG_TESTS OFF CACHE BOOL "" FORCE)
set(GLSLANG_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
set(ENABLE_OPT OFF CACHE BOOL "" FORCE)
set(ENABLE_GLSLANG_JS OFF CACHE BOOL "" FORCE)
if(NOT TARGET glslang)
    add_subdirectory("${DAWN_SRC}/third_party/glslang/src" "${CMAKE_BINARY_DIR}/glslang" EXCLUDE_FROM_ALL)
endif()
set(VISPY_SHADER_INCLUDE_ROOT "${DAWN_SRC}/third_party/glslang/src")
set(VISPY_VULKAN_INCLUDE_ROOT "${DAWN_SRC}/third_party/vulkan-headers/src/include")
if(VISPY_EXPORT_NATIVE_SDK)
    vispy_export_native_sdk()
endif()
endif()

if(NOT VISPY_CPU_CONTRACTS_ONLY)
    nanobind_add_module(_dawn NB_STATIC
        cpp/bindings/module.cpp
        cpp/shader/normalize.cpp
        cpp/shader/glslang_spv.cpp
        cpp/shader/integer_sampling.cpp
        cpp/shader/line_evaluator.cpp
        cpp/shader/line_consumer.cpp
        cpp/runtime.cpp
        ${VISPY_PLATFORM_SOURCES}
    )
    target_include_directories(_dawn PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp"
        "${VISPY_SHADER_INCLUDE_ROOT}"
    )
    target_link_libraries(_dawn PRIVATE
        webgpu_dawn
        glslang
        glslang-default-resource-limits
        SPIRV-Tools-static
        SPIRV-Tools-opt
        ${VISPY_PLATFORM_LIBRARIES}
    )
    if(APPLE)
        target_compile_options(_dawn PRIVATE "$<$<COMPILE_LANGUAGE:OBJCXX>:-fobjc-arc>")
    endif()
    if(MSVC)
        target_compile_options(_dawn PRIVATE /bigobj /EHsc)
        target_compile_definitions(_dawn PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
    endif()
endif()
if(VISPY_BUILD_CONTRACT_TESTS)
    enable_testing()
    find_package(Threads REQUIRED)
    function(vispy_shader_contract target source)
        add_executable(${target} cpp/shader/normalize.cpp cpp/shader/glslang_spv.cpp cpp/shader/integer_sampling.cpp ${source} ${ARGN})
        target_include_directories(${target} PRIVATE
            "${CMAKE_CURRENT_SOURCE_DIR}/cpp" "${VISPY_SHADER_INCLUDE_ROOT}")
        target_link_libraries(${target} PRIVATE
            glslang glslang-default-resource-limits SPIRV-Tools-static SPIRV-Tools-opt)
    endfunction()
    vispy_shader_contract(shader_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/normalization_contract.cpp")
    vispy_shader_contract(point_contract "${VISPY_CONTRACT_TESTS_ROOT}/markers/point_contract.cpp")
    vispy_shader_contract(artifact_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/artifact_contract.cpp")
    vispy_shader_contract(typed_sampling_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/typed_sampling_contract.cpp")
    vispy_shader_contract(integer_sampling_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/integer_sampling_contract.cpp")
    vispy_shader_contract(integer_sampling_boundary_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/integer_sampling_boundary_contract.cpp")
    vispy_shader_contract(integer_sampling_artifact_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/integer_sampling_artifact_contract.cpp")
    vispy_shader_contract(batch_identity_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/batch_identity_contract.cpp")
    vispy_shader_contract(line_evaluator_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_evaluator_contract.cpp"
        cpp/shader/line_evaluator.cpp)
    vispy_shader_contract(line_consumer_generated_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_consumer_generated_contract.cpp"
        cpp/shader/line_evaluator.cpp cpp/shader/line_consumer.cpp)
    if(NOT VISPY_CPU_CONTRACTS_ONLY AND NOT VISPY_NATIVE_SDK)
        # Exercise the pinned Tint reader without creating a Dawn device. Use
        # Dawn's own utility configuration so assertion-dependent IR layouts
        # match the library in both Debug and Release configurations.
        target_compile_definitions(shader_contract PRIVATE VISPY_TEST_TINT_READER=1)
        target_include_directories(shader_contract PRIVATE "${DAWN_SRC}")
        target_link_libraries(shader_contract PRIVATE webgpu_dawn dawn_utils_config)
        if(MSVC)
            target_compile_options(shader_contract PRIVATE /Zc:preprocessor /utf-8)
        endif()
    endif()
    add_executable(texture_contract "${VISPY_CONTRACT_TESTS_ROOT}/textures/texture_contract.cpp")
    add_executable(owned_texture_contract "${VISPY_CONTRACT_TESTS_ROOT}/textures/owned_texture_contract.cpp")
    target_include_directories(owned_texture_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_link_libraries(owned_texture_contract PRIVATE webgpu_dawn)
    nanobind_add_module(owned_upload_contract NB_STATIC
        "${VISPY_CONTRACT_TESTS_ROOT}/bindings/owned_upload_contract.cpp")
    set_target_properties(owned_upload_contract PROPERTIES OUTPUT_NAME "_owned_upload_contract")
    target_include_directories(owned_upload_contract PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp" "${CMAKE_CURRENT_SOURCE_DIR}/cpp/bindings")
    target_link_libraries(owned_upload_contract PRIVATE webgpu_dawn)
    add_test(NAME owned_texture_contract COMMAND owned_texture_contract)
    add_test(NAME owned_upload_decoder_contract
        COMMAND "${Python_EXECUTABLE}" -I -B
        "${VISPY_CONTRACT_TESTS_ROOT}/bindings/owned_decoder_contract.py"
        "$<TARGET_FILE:owned_upload_contract>")
    add_test(NAME owned_upload_packing_contract
        COMMAND "${Python_EXECUTABLE}" -I -B
        "${VISPY_CONTRACT_TESTS_ROOT}/bindings/owned_packing_contract.py"
        "$<TARGET_FILE:owned_upload_contract>"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/vispy/gloo/dawn_parser.py")
    add_executable(integer_sampler_snapshot_contract "${VISPY_CONTRACT_TESTS_ROOT}/textures/integer_sampler_snapshot_contract.cpp")
    add_executable(state_contract "${VISPY_CONTRACT_TESTS_ROOT}/state/state_contract.cpp")
    add_executable(readback_contract "${VISPY_CONTRACT_TESTS_ROOT}/capture/readback_contract.cpp")
    add_executable(input_batch_contract "${VISPY_CONTRACT_TESTS_ROOT}/input_layout/batch_planner_contract.cpp")
    target_include_directories(input_batch_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(ordered_strip_runtime_contract "${VISPY_CONTRACT_TESTS_ROOT}/input_layout/ordered_strip_runtime_contract.cpp")
    target_include_directories(ordered_strip_runtime_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(ordinary_line_runtime_contract "${VISPY_CONTRACT_TESTS_ROOT}/input_layout/ordinary_line_runtime_contract.cpp")
    target_include_directories(ordinary_line_runtime_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(point_batch_contract "${VISPY_CONTRACT_TESTS_ROOT}/markers/point_batch_contract.cpp")
    target_include_directories(point_batch_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(point_partition_contract "${VISPY_CONTRACT_TESTS_ROOT}/markers/point_partition_contract.cpp")
    target_include_directories(point_partition_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    foreach(kind IN ITEMS owner topology routing capacity cache)
        if(kind STREQUAL "cache")
            set(source "${VISPY_CONTRACT_TESTS_ROOT}/input_layout/runtime_batch_cache_contract.cpp")
        else()
            set(source "${VISPY_CONTRACT_TESTS_ROOT}/input_layout/batch_${kind}_contract.cpp")
        endif()
        add_executable(input_batch_${kind}_contract "${source}")
        target_include_directories(input_batch_${kind}_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    endforeach()
    add_executable(timestamp_contract "${VISPY_CONTRACT_TESTS_ROOT}/benchmarks/timestamp_contract.cpp")
    add_executable(frame_lifecycle_contract "${VISPY_CONTRACT_TESTS_ROOT}/benchmarks/frame_lifecycle_contract.cpp")
    add_executable(line_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_contract.cpp")
    add_executable(line_batch_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_batch_contract.cpp")
    target_include_directories(line_batch_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(line_capture_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_capture_contract.cpp")
    target_include_directories(line_capture_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    add_executable(line_consumer_resource_contract cpp/shader/normalize.cpp
        "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_consumer_resource_contract.cpp")
    add_executable(artifact_consumer_contract cpp/shader/normalize.cpp
        "${VISPY_CONTRACT_TESTS_ROOT}/shaders/artifact_consumer_policy_contract.cpp")
    vispy_shader_contract(runtime_line_consumer_policy_contract
        "${VISPY_CONTRACT_TESTS_ROOT}/shaders/runtime_line_consumer_policy_contract.cpp")
    add_executable(runtime_line_variants_contract
        "${VISPY_CONTRACT_TESTS_ROOT}/shaders/runtime_line_variants_contract.cpp")
    add_executable(runtime_line_consumer_accounting_contract
        "${VISPY_CONTRACT_TESTS_ROOT}/shaders/runtime_line_consumer_accounting_contract.cpp")
    add_executable(line_pool_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_pool_contract.cpp")
    add_executable(line_pool_inspection_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_pool_inspection_contract.cpp")
    add_executable(line_ownership_contract "${VISPY_CONTRACT_TESTS_ROOT}/lines/line_ownership_contract.cpp")
    target_include_directories(timestamp_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(frame_lifecycle_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(line_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(line_consumer_resource_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(artifact_consumer_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(runtime_line_consumer_policy_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(runtime_line_variants_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(runtime_line_consumer_accounting_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(line_pool_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(line_pool_inspection_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_include_directories(line_ownership_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    foreach(contract IN ITEMS texture integer_sampler_snapshot state readback)
        target_include_directories(${contract}_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
        target_link_libraries(${contract}_contract PRIVATE webgpu_dawn)
    endforeach()
    foreach(contract IN ITEMS shader point point_batch point_partition artifact typed_sampling integer_sampling integer_sampling_boundary integer_sampling_artifact integer_sampler_snapshot batch_identity input_batch input_batch_owner input_batch_topology input_batch_routing input_batch_capacity input_batch_cache ordered_strip_runtime ordinary_line_runtime artifact_consumer runtime_line_consumer_policy runtime_line_variants runtime_line_consumer_accounting texture state readback timestamp frame_lifecycle line line_batch line_capture line_evaluator line_consumer_generated line_consumer_resource line_pool line_pool_inspection line_ownership)
        if(MSVC)
            target_compile_options(${contract}_contract PRIVATE /bigobj /EHsc)
            target_compile_definitions(${contract}_contract PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
        endif()
    endforeach()
    add_test(NAME shader_contract
        COMMAND shader_contract "${VISPY_CONTRACT_TESTS_ROOT}/shaders/corpus")
    add_test(NAME point_contract COMMAND point_contract)
    add_test(NAME artifact_contract COMMAND artifact_contract)
    add_test(NAME typed_sampling_contract COMMAND typed_sampling_contract)
    add_test(NAME integer_sampling_contract COMMAND integer_sampling_contract)
    add_test(NAME integer_sampling_boundary_contract COMMAND integer_sampling_boundary_contract)
    add_test(NAME integer_sampling_artifact_contract COMMAND integer_sampling_artifact_contract)
    add_test(NAME integer_sampler_snapshot_contract COMMAND integer_sampler_snapshot_contract)
    add_test(NAME input_batch_contract COMMAND input_batch_contract)
    add_test(NAME ordered_strip_runtime_contract COMMAND ordered_strip_runtime_contract)
    add_test(NAME ordinary_line_runtime_contract COMMAND ordinary_line_runtime_contract)
    add_test(NAME point_batch_contract COMMAND point_batch_contract)
    add_test(NAME point_partition_contract COMMAND point_partition_contract)
    add_test(NAME batch_identity_contract COMMAND batch_identity_contract)
    foreach(kind IN ITEMS owner topology routing capacity cache)
        add_test(NAME input_batch_${kind}_contract COMMAND input_batch_${kind}_contract)
    endforeach()
    add_test(NAME artifact_consumer_contract COMMAND artifact_consumer_contract)
    add_test(NAME runtime_line_consumer_policy_contract COMMAND runtime_line_consumer_policy_contract)
    add_test(NAME runtime_line_variants_contract COMMAND runtime_line_variants_contract)
    add_test(NAME runtime_line_consumer_accounting_contract COMMAND runtime_line_consumer_accounting_contract)
    add_test(NAME texture_contract COMMAND texture_contract)
    add_test(NAME state_contract COMMAND state_contract)
    add_test(NAME readback_contract COMMAND readback_contract)
    add_test(NAME timestamp_contract COMMAND timestamp_contract)
    add_test(NAME frame_lifecycle_contract COMMAND frame_lifecycle_contract)
    add_test(NAME line_contract COMMAND line_contract)
    add_test(NAME line_batch_contract COMMAND line_batch_contract)
    add_test(NAME line_capture_contract COMMAND line_capture_contract)
    add_test(NAME line_evaluator_contract COMMAND line_evaluator_contract)
    add_test(NAME line_consumer_generated_contract COMMAND line_consumer_generated_contract)
    add_test(NAME line_consumer_resource_contract COMMAND line_consumer_resource_contract)
    add_test(NAME line_pool_contract COMMAND line_pool_contract)
    add_test(NAME line_pool_inspection_contract COMMAND line_pool_inspection_contract)
    add_test(NAME line_ownership_contract COMMAND line_ownership_contract)
    if(VISPY_CONTRACT_DATASETS_ROOT)
        foreach(corpus IN ITEMS point-corpus marker-corpus text-corpus volume-corpus)
            if(NOT IS_DIRECTORY "${VISPY_CONTRACT_DATASETS_ROOT}/${corpus}")
                message(FATAL_ERROR "Frozen contract dataset is missing: ${corpus}")
            endif()
        endforeach()
        add_test(NAME point_identity_corpus COMMAND point_contract "${VISPY_CONTRACT_DATASETS_ROOT}/point-corpus" --points)
        add_test(NAME point_marker_corpus COMMAND point_contract "${VISPY_CONTRACT_DATASETS_ROOT}/marker-corpus")
        add_test(NAME point_volume_resources COMMAND point_contract "${VISPY_CONTRACT_DATASETS_ROOT}/volume-corpus" --resources)
        add_test(NAME shader_text_corpus COMMAND shader_contract "${VISPY_CONTRACT_DATASETS_ROOT}/text-corpus")
        add_test(NAME shader_volume_corpus COMMAND shader_contract "${VISPY_CONTRACT_DATASETS_ROOT}/volume-corpus")
    endif()

    add_library(native_library_fixture SHARED "${VISPY_CONTRACT_TESTS_ROOT}/platform/library_fixture.cpp")
    set(VISPY_NATIVE_CONTRACT_SOURCES cpp/platform/native_library.cpp)
    set(VISPY_NATIVE_CONTRACT_LIBRARIES ${CMAKE_DL_LIBS} Threads::Threads)
    if(NOT VISPY_CPU_CONTRACTS_ONLY)
        set(VISPY_NATIVE_CONTRACT_SOURCES ${VISPY_PLATFORM_SOURCES})
        list(APPEND VISPY_NATIVE_CONTRACT_LIBRARIES ${VISPY_PLATFORM_LIBRARIES})
    elseif(WIN32)
        # The hidden HWND lifetime test does not create a Dawn instance/device.
        list(APPEND VISPY_NATIVE_CONTRACT_SOURCES cpp/platform/surface_win32.cpp)
    endif()
    if(WIN32)
        list(APPEND VISPY_NATIVE_CONTRACT_LIBRARIES user32)
    endif()
    add_executable(native_contract "${VISPY_CONTRACT_TESTS_ROOT}/platform/native_contract.cpp" ${VISPY_NATIVE_CONTRACT_SOURCES})
    target_include_directories(native_contract PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/cpp")
    target_link_libraries(native_contract PRIVATE webgpu_dawn ${VISPY_NATIVE_CONTRACT_LIBRARIES})
    if(APPLE AND NOT VISPY_CPU_CONTRACTS_ONLY)
        target_compile_options(native_contract PRIVATE "$<$<COMPILE_LANGUAGE:OBJCXX>:-fobjc-arc>")
    endif()
    add_dependencies(native_contract native_library_fixture)
    add_test(NAME native_contract COMMAND native_contract "$<TARGET_FILE:native_library_fixture>")

    add_executable(vk_layer_contract "${VISPY_CONTRACT_TESTS_ROOT}/platform/vk_layer_contract.cpp" cpp/platform/vk_layer.cpp)
    target_include_directories(vk_layer_contract PRIVATE "${VISPY_VULKAN_INCLUDE_ROOT}")
    target_link_libraries(vk_layer_contract PRIVATE Threads::Threads)
    add_test(NAME vk_layer_contract COMMAND vk_layer_contract)
    if(MSVC)
        foreach(contract IN ITEMS native_contract vk_layer_contract)
            target_compile_options(${contract} PRIVATE /bigobj /EHsc)
            target_compile_definitions(${contract} PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
        endforeach()
    endif()
endif()

set(VISPY_PKG_DIR "${CMAKE_SOURCE_DIR}/src/vispy")
if(VISPY_INPLACE AND TARGET _dawn)
    add_custom_command(TARGET _dawn POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:_dawn>" "${VISPY_PKG_DIR}/$<TARGET_FILE_NAME:_dawn>"
    )
endif()

# Compile the pinned upstream implementation. Its function mutates float32
# input in place; text atlas generation intentionally ignores its return value.
execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import Cython; print(Cython.__version__)"
    RESULT_VARIABLE CYTHON_RESULT OUTPUT_VARIABLE CYTHON_VERSION
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT CYTHON_RESULT EQUAL 0)
    message(FATAL_ERROR "Cython is required to build VisPy's CPU text helper")
endif()
set(SDF_CPU_C "${CMAKE_CURRENT_BINARY_DIR}/generated/_sdf_cpu.c")
add_custom_command(OUTPUT "${SDF_CPU_C}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/generated"
    COMMAND "${Python_EXECUTABLE}" -m cython --3
        "${VISPY_PKG_DIR}/visuals/text/_sdf_cpu.pyx" --output-file "${SDF_CPU_C}"
    DEPENDS "${VISPY_PKG_DIR}/visuals/text/_sdf_cpu.pyx"
    VERBATIM
)
Python_add_library(_sdf_cpu MODULE WITH_SOABI "${SDF_CPU_C}")
target_link_libraries(_sdf_cpu PRIVATE Python::NumPy)
target_compile_definitions(_sdf_cpu PRIVATE NPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION)
if(VISPY_INPLACE)
    add_custom_command(TARGET _sdf_cpu POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:_sdf_cpu>"
            "${VISPY_PKG_DIR}/visuals/text/$<TARGET_FILE_NAME:_sdf_cpu>"
    )
endif()

if(VISPY_VULKAN)
add_library(VkLayer_vispy_submit SHARED cpp/platform/vk_layer.cpp)
set_target_properties(VkLayer_vispy_submit PROPERTIES
    PREFIX ""
    OUTPUT_NAME "VkLayer_vispy_submit"
)
target_include_directories(VkLayer_vispy_submit PRIVATE
    "${VISPY_VULKAN_INCLUDE_ROOT}"
)
set(VISPY_LAYER_LIBRARY_NAME "VkLayer_vispy_submit${CMAKE_SHARED_LIBRARY_SUFFIX}")
if(WIN32)
    set(VISPY_LAYER_LIBRARY_PATH ".\\\\${VISPY_LAYER_LIBRARY_NAME}")
else()
    set(VISPY_LAYER_LIBRARY_PATH "./${VISPY_LAYER_LIBRARY_NAME}")
endif()
set(VISPY_LAYER_MANIFEST "${CMAKE_CURRENT_BINARY_DIR}/generated/VkLayer_vispy_submit.json")
configure_file(cpp/platform/VkLayer_vispy_submit.json.in "${VISPY_LAYER_MANIFEST}" @ONLY)
if(VISPY_INPLACE)
    add_custom_command(TARGET VkLayer_vispy_submit POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:VkLayer_vispy_submit>" "${VISPY_PKG_DIR}/$<TARGET_FILE_NAME:VkLayer_vispy_submit>"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${VISPY_LAYER_MANIFEST}" "${VISPY_PKG_DIR}/VkLayer_vispy_submit.json"
    )
endif()
if(MSVC)
    target_compile_definitions(VkLayer_vispy_submit PRIVATE VK_USE_PLATFORM_WIN32_KHR NOMINMAX)
endif()
endif()

if(TARGET _dawn AND TARGET VkLayer_vispy_submit)
    add_dependencies(_dawn VkLayer_vispy_submit)
endif()

if(TARGET _dawn)
install(TARGETS _dawn
    RUNTIME DESTINATION vispy
    LIBRARY DESTINATION vispy
)
endif()
install(TARGETS _sdf_cpu
    RUNTIME DESTINATION vispy/visuals/text
    LIBRARY DESTINATION vispy/visuals/text
)
if(TARGET VkLayer_vispy_submit)
install(TARGETS VkLayer_vispy_submit
    RUNTIME DESTINATION vispy
    LIBRARY DESTINATION vispy
)
install(FILES "${VISPY_LAYER_MANIFEST}" DESTINATION vispy)
endif()
install(DIRECTORY third_party/licenses/ DESTINATION vispy/_licenses
    FILES_MATCHING PATTERN "*.txt" PATTERN "*.md" PATTERN "*.json")

install(FILES LICENSE LICENSE-BSD LICENSING.md DESTINATION vispy/_licenses)
