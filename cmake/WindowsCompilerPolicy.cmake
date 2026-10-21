# The pinned Qt5 bindings ship an older MSVC runtime. This policy must reach
# vendor object libraries as well as the renderer, layer and Python ABI leaves.
option(VISPY_LEGACY_MSVC_CRT_MUTEX "Use MSVC mutex initialization compatible with the pinned Qt5 CRT" ON)
set(VISPY_MSVC_MUTEX_POLICY "non-msvc-v1")
if(WIN32 AND MSVC)
    # Own only this exact switch; leave the caller's other compiler flags intact.
    string(REGEX REPLACE "(^| )/D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR( |$)" " "
        _vispy_cxx_flags "${CMAKE_CXX_FLAGS}")
    string(STRIP "${_vispy_cxx_flags}" _vispy_cxx_flags)
    if(VISPY_LEGACY_MSVC_CRT_MUTEX)
        string(APPEND _vispy_cxx_flags " /D_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR")
        set(VISPY_MSVC_MUTEX_POLICY "msvc-stl-init-in-situ-v1")
    else()
        set(VISPY_MSVC_MUTEX_POLICY "msvc-stl-constexpr-v1")
    endif()
    set(CMAKE_CXX_FLAGS "${_vispy_cxx_flags}" CACHE STRING "Flags used by all C++ compilation" FORCE)
endif()
