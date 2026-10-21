# Refresh package metadata only after a package-level install/import correction.
if(NOT VISPY_SDK_PRODUCER_BUILD OR NOT EXISTS "${VISPY_SDK_PRODUCER_BUILD}/native-sdk/producer-Release.json")
    message(FATAL_ERROR "An existing SDK producer configuration is required")
endif()
include(CMakePackageConfigHelpers)
configure_package_config_file("${CMAKE_CURRENT_LIST_DIR}/VispyNativeSDKConfig.cmake.in"
    "${VISPY_SDK_PRODUCER_BUILD}/native-sdk/VispyNativeSDKConfig.cmake"
    INSTALL_DESTINATION lib/cmake/VispyNativeSDK)
