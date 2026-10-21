# Opt-in exports of the real configured vendor targets. ABI leaves are excluded.
include(CMakePackageConfigHelpers)

function(vispy_json_quote output value)
    string(REPLACE "\\" "\\\\" value "${value}")
    string(REPLACE "\"" "\\\"" value "${value}")
    string(REPLACE "\n" "\\n" value "${value}")
    set(${output} "\"${value}\"" PARENT_SCOPE)
endfunction()

function(vispy_export_native_sdk)
    if(NOT WIN32 OR NOT MSVC OR VISPY_CPU_CONTRACTS_ONLY OR VISPY_NATIVE_SDK)
        message(FATAL_ERROR "Native SDK export currently requires the full Windows/MSVC Vulkan producer")
    endif()
    set(component VispyNativeSDK)
    install(TARGETS webgpu_dawn dawn_public_config glslang
        glslang-default-resource-limits SPIRV-Tools-static SPIRV-Tools-opt
        EXPORT VispyNativeSDKTargets
        ARCHIVE DESTINATION lib COMPONENT ${component})
    install(EXPORT VispyNativeSDKTargets NAMESPACE vispy_native::
        DESTINATION lib/cmake/VispyNativeSDK COMPONENT ${component})
    configure_package_config_file("${CMAKE_CURRENT_FUNCTION_LIST_DIR}/VispyNativeSDKConfig.cmake.in"
        "${CMAKE_CURRENT_BINARY_DIR}/native-sdk/VispyNativeSDKConfig.cmake"
        INSTALL_DESTINATION lib/cmake/VispyNativeSDK)
    install(FILES "${CMAKE_CURRENT_BINARY_DIR}/native-sdk/VispyNativeSDKConfig.cmake"
        DESTINATION lib/cmake/VispyNativeSDK COMPONENT ${component})

    # Preserve the public build include layout, including generated API headers.
    install(DIRECTORY "${DAWN_SRC}/include/" "${DAWN_BUILD_GEN_DIR}/include/"
        DESTINATION include COMPONENT ${component}
        FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
    install(DIRECTORY "${DAWN_SRC}/third_party/glslang/src/glslang"
        "${DAWN_SRC}/third_party/glslang/src/SPIRV"
        DESTINATION include COMPONENT ${component}
        FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.hpp11"
        PATTERN "*.inc" PATTERN "*.inl")
    install(FILES "${CMAKE_BINARY_DIR}/include/glslang/build_info.h"
        DESTINATION include/glslang COMPONENT ${component})
    install(DIRECTORY "${DAWN_SRC}/third_party/spirv-tools/src/include/"
        "${DAWN_SRC}/third_party/spirv-headers/src/include/"
        "${DAWN_SRC}/third_party/vulkan-headers/src/include/"
        DESTINATION include COMPONENT ${component}
        FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.hpp11")
    install(FILES "${CMAKE_SOURCE_DIR}/cmake/dependencies.lock.json"
        DESTINATION share/VispyNativeSDK COMPONENT ${component})
    install(FILES "${CMAKE_SOURCE_DIR}/LICENSE"
        "${CMAKE_SOURCE_DIR}/LICENSE-BSD" "${CMAKE_SOURCE_DIR}/LICENSING.md"
        DESTINATION share/VispyNativeSDK/licenses COMPONENT ${component})
    install(DIRECTORY "${CMAKE_SOURCE_DIR}/third_party/licenses/"
        DESTINATION share/VispyNativeSDK/licenses COMPONENT ${component})

    set(settings "{\n")
    foreach(pair IN ITEMS
            "system|CMAKE_SYSTEM_NAME" "architecture|CMAKE_SYSTEM_PROCESSOR"
            "generator|CMAKE_GENERATOR" "generator_platform|CMAKE_GENERATOR_PLATFORM"
            "cmake_version|CMAKE_VERSION" "compiler|CMAKE_CXX_COMPILER"
            "compiler_version|CMAKE_CXX_COMPILER_VERSION"
            "windows_sdk|CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION"
            "cxx_flags|CMAKE_CXX_FLAGS" "release_flags|CMAKE_CXX_FLAGS_RELEASE"
            "msvc_mutex_policy|VISPY_MSVC_MUTEX_POLICY"
            "dawn_backend_vulkan|DAWN_ENABLE_VULKAN" "dawn_backend_metal|DAWN_ENABLE_METAL"
            "dawn_backend_null|DAWN_ENABLE_NULL" "dawn_monolithic|DAWN_BUILD_MONOLITHIC_LIBRARY"
            "dawn_rtti|DAWN_ENABLE_RTTI")
        string(REPLACE "|" ";" parts "${pair}")
        list(GET parts 0 key)
        list(GET parts 1 variable)
        vispy_json_quote(value "${${variable}}")
        string(APPEND settings "  \"${key}\": ${value},\n")
    endforeach()
    string(APPEND settings "  \"archive_origins\": {\n")
    string(APPEND settings "    \"webgpu_dawn.lib\": \"$<TARGET_FILE:webgpu_dawn>\",\n")
    string(APPEND settings "    \"glslang.lib\": \"$<TARGET_FILE:glslang>\",\n")
    string(APPEND settings "    \"glslang-default-resource-limits.lib\": \"$<TARGET_FILE:glslang-default-resource-limits>\",\n")
    string(APPEND settings "    \"SPIRV-Tools.lib\": \"$<TARGET_FILE:SPIRV-Tools-static>\",\n")
    string(APPEND settings "    \"SPIRV-Tools-opt.lib\": \"$<TARGET_FILE:SPIRV-Tools-opt>\"\n  },\n")
    vispy_json_quote(gen_include "${DAWN_BUILD_GEN_DIR}/include")
    string(APPEND settings "  \"generated_header_origin\": ${gen_include},\n")
    string(APPEND settings "  \"configuration\": \"$<CONFIG>\",\n  \"pointer_bytes\": ${CMAKE_SIZEOF_VOID_P},\n  \"runtime\": \"MultiThreadedDLL\"\n}\n")
    file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/native-sdk/producer-$<CONFIG>.json"
        CONTENT "${settings}")
    install(FILES "${CMAKE_CURRENT_BINARY_DIR}/native-sdk/producer-$<CONFIG>.json"
        DESTINATION share/VispyNativeSDK RENAME producer.json COMPONENT ${component})
endfunction()

function(vispy_import_native_sdk)
    if(NOT WIN32 OR NOT MSVC OR VISPY_CPU_CONTRACTS_ONLY)
        message(FATAL_ERROR "Native SDK reuse currently supports Windows/MSVC Vulkan Release only")
    endif()
    if(NOT VISPY_NATIVE_SDK_MANIFEST_SHA256)
        message(FATAL_ERROR "Native SDK requires its immutable VISPY_NATIVE_SDK_MANIFEST_SHA256")
    endif()
    if(CMAKE_BUILD_TYPE AND NOT CMAKE_BUILD_TYPE STREQUAL "Release")
        message(FATAL_ERROR "The imported native SDK requires Release")
    endif()
    if(CMAKE_MSVC_RUNTIME_LIBRARY AND NOT CMAKE_MSVC_RUNTIME_LIBRARY STREQUAL "MultiThreadedDLL"
            AND NOT CMAKE_MSVC_RUNTIME_LIBRARY STREQUAL "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
        message(FATAL_ERROR "The imported native SDK requires the Release DLL CRT")
    endif()
    # Prevent multi-config generators from silently using Release archives in Debug.
    set(CMAKE_CONFIGURATION_TYPES Release CACHE STRING "SDK-qualified configuration" FORCE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "SDK-qualified configuration" FORCE)
    set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL CACHE STRING "SDK-qualified CRT" FORCE)
    set(_vispy_sdk_dependency_lock "${CMAKE_SOURCE_DIR}/cmake/dependencies.lock.json")
    if(VISPY_DEPENDENCY_ORIGIN_WORKSPACE)
        if(NOT VISPY_DEPENDENCY_LOCK OR NOT IS_ABSOLUTE "${VISPY_DEPENDENCY_LOCK}")
            message(FATAL_ERROR "SDK immutable origins require their separate absolute dependency lock")
        endif()
        set(_vispy_sdk_dependency_lock "${VISPY_DEPENDENCY_LOCK}")
    elseif(VISPY_DEPENDENCY_LOCK)
        message(FATAL_ERROR "A separate SDK dependency lock requires explicit immutable origin authority")
    endif()
    execute_process(COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/native_sdk.py"
        verify --sdk "${VISPY_NATIVE_SDK}" --manifest-sha256 "${VISPY_NATIVE_SDK_MANIFEST_SHA256}"
        --dependency-lock "${_vispy_sdk_dependency_lock}"
        --system "${CMAKE_SYSTEM_NAME}" --architecture "${CMAKE_SYSTEM_PROCESSOR}"
        --pointer-bytes "${CMAKE_SIZEOF_VOID_P}" --configuration Release --runtime MultiThreadedDLL
        --cmake-version "${CMAKE_VERSION}" --compiler "${CMAKE_CXX_COMPILER}"
        --compiler-version "${CMAKE_CXX_COMPILER_VERSION}"
        --windows-sdk "${CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION}"
        "--cxx-flags=${CMAKE_CXX_FLAGS}" "--release-flags=${CMAKE_CXX_FLAGS_RELEASE}"
        "--msvc-mutex-policy=${VISPY_MSVC_MUTEX_POLICY}"
        COMMAND_ERROR_IS_FATAL ANY)
    find_package(VispyNativeSDK CONFIG REQUIRED
        PATHS "${VISPY_NATIVE_SDK}/lib/cmake/VispyNativeSDK" NO_DEFAULT_PATH)
    foreach(target IN ITEMS webgpu_dawn glslang glslang-default-resource-limits SPIRV-Tools-static SPIRV-Tools-opt)
        add_library(${target} ALIAS vispy_native::${target})
    endforeach()
endfunction()
