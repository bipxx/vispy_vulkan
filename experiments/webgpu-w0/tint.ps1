param(
    [Parameter(Mandatory)][string]$Tools,
    [Parameter(Mandatory)][string]$Output
)
$ErrorActionPreference = 'Stop'
$python = 'C:/Users/HEQ/Projects/vispy_vulkan/.venv/Scripts/python.exe'
$site = 'C:/Users/HEQ/Projects/vispy_vulkan/.venv/Lib/site-packages'
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$env:PYTHONPATH = "$repo/src;$site;$Tools/python-tools"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = $Output
$env:TMP = $Output
$vs = 'C:/Program Files/Microsoft Visual Studio/2022/Community'
$cmake = "$vs/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe"
$vcvars = "$vs/VC/Auxiliary/Build/vcvars64.bat"
$flags = @(
    '-DDAWN_BUILD_TESTS=OFF', '-DTINT_BUILD_TESTS=OFF', '-DDAWN_BUILD_SAMPLES=OFF',
    '-DDAWN_BUILD_PROTOBUF=OFF', '-DTINT_BUILD_IR_BINARY=OFF',
    '-DDAWN_BUILD_MONOLITHIC_LIBRARY=OFF', '-DDAWN_USE_GLFW=OFF',
    '-DDAWN_ENABLE_INSTALL=OFF', '-DDAWN_ENABLE_VULKAN=OFF',
    '-DDAWN_ENABLE_D3D11=OFF', '-DDAWN_ENABLE_D3D12=OFF',
    '-DDAWN_ENABLE_DESKTOP_GL=OFF', '-DDAWN_ENABLE_OPENGLES=OFF', '-DDAWN_ENABLE_NULL=OFF',
    '-DTINT_BUILD_GLSL_VALIDATOR=OFF', '-DTINT_BUILD_SPV_READER=ON',
    '-DTINT_BUILD_WGSL_WRITER=ON', '-DCMAKE_BUILD_TYPE=Release',
    '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY'
)
# Use the existing MSVC environment for the standalone Tint CLI build.
$command = @"
@echo off
call "$vcvars" || exit /b 1
"$cmake" -G Ninja -S "$Tools/dawn-0194084" -B "$Output/tint-ninja" $flags "-DPython3_EXECUTABLE=$python" || exit /b 1
"$cmake" --build "$Output/tint-ninja" --target tint_cmd_tint_cmd --parallel 6
"@
$batch = "$Output/build-tint.cmd"
Set-Content -LiteralPath $batch -Value $command -Encoding ascii
& $batch
exit $LASTEXITCODE
