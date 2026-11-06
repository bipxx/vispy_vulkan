cmake_minimum_required(VERSION 3.20)
project(upload_cache_shutdown_contract LANGUAGES CXX)

add_executable(upload_cache_shutdown_contract shutdown_contract.cpp)
target_compile_features(upload_cache_shutdown_contract PRIVATE cxx_std_17)
target_include_directories(upload_cache_shutdown_contract PRIVATE "${VISPY_SOURCE_ROOT}/cpp" "${CMAKE_CURRENT_BINARY_DIR}")
if(MSVC)
    target_compile_definitions(upload_cache_shutdown_contract PRIVATE _DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR)
endif()
