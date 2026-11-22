param(
    [Parameter(Mandatory)][string]$Tools,
    [Parameter(Mandatory)][string]$Output
)
$ErrorActionPreference = 'Stop'
$python = 'C:/Users/HEQ/Projects/vispy_vulkan/.venv/Scripts/python.exe'
$site = 'C:/Users/HEQ/Projects/vispy_vulkan/.venv/Lib/site-packages'
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$repo/src;$site;$Tools/python-tools"
$env:TEMP = $Output
$env:TMP = $Output
$env:EM_FROZEN_CACHE = '1'
$env:EM_CONFIG = "$Tools/em-config-5.0.3"
$env:EMSDK_PYTHON = $python
$env:EMCC_CORES = '4'
$node = (Get-Command node.exe).Source.Replace('\', '/')
$sdk = "$Tools/emscripten-5.0.3/install"
$env:EM_CACHE = "$sdk/emscripten/cache"
$dawn = "$Tools/dawn-0194084"
$port = "$dawn/third_party/emdawnwebgpu/pkg/webgpu/src"

function Run-Python {
    & $python -B -S @args
    if ($LASTEXITCODE -ne 0) { throw "Python child exited $LASTEXITCODE" }
}

New-Item -ItemType Directory -Force "$Output/gen" | Out-Null
@"
LLVM_ROOT = r'$sdk/bin'
BINARYEN_ROOT = r'$sdk'
NODE_JS = r'$node'
"@ | Set-Content -Encoding ascii $env:EM_CONFIG

Run-Python "$sdk/emscripten/emcc.py" --version
Run-Python "$dawn/generator/dawn_json_generator.py" "--dawn-json=$dawn/src/dawn/dawn.json" `
    "--template-dir=$dawn/generator/templates" '--targets=emdawnwebgpu_headers,emdawnwebgpu_js' "--output-dir=$Output/gen"
$gen = "$Output/gen/src/emdawnwebgpu"
$snippets = "$dawn/src/emdawnwebgpu/snippets"
Run-Python "$sdk/emscripten/tools/gen_struct_info.py" -q "$gen/struct_info_webgpu.json" `
    "-I=$gen/include" "-o=$gen/struct32.json"
# The Dawn port validates both layout tables even for a wasm32 link.
$env:EM_FROZEN_CACHE = '0'
$env:EM_CACHE = "$Tools/em-cache-5.0.3"
Run-Python "$sdk/emscripten/tools/gen_struct_info.py" -q "$gen/struct_info_webgpu.json" --wasm64 `
    "-I=$gen/include" "-o=$gen/struct64.json"
$env:EM_CACHE = "$sdk/emscripten/cache"
$env:EM_FROZEN_CACHE = '1'
Run-Python "$dawn/src/emdawnwebgpu/concat.py" "$gen/library_webgpu_generated_struct_info.js" `
    "$snippets/library_webgpu_struct_info_part1.txt" "$gen/struct32.json" `
    "$snippets/library_webgpu_struct_info_part2.txt" "$gen/struct64.json" `
    "$snippets/library_webgpu_struct_info_part3.txt"

Run-Python "$sdk/emscripten/emcc.py" "$PSScriptRoot/spike.cpp" "$port/webgpu.cpp" `
    "-I$gen/include" "-I$dawn/include" `
    "--js-library=$gen/library_webgpu_enum_tables.js" `
    "--js-library=$gen/library_webgpu_generated_sig_info.js" `
    "--js-library=$gen/library_webgpu_generated_struct_info.js" `
    "--js-library=$port/library_webgpu.js" `
    -std=c++20 -Oz -Wall -Werror -Wno-error=experimental --no-entry -sEXPORT_ES6 -sENVIRONMENT=web `
    -sJSPI -sJSPI_EXPORTS=read_pixel -sEXPORTED_FUNCTIONS=_read_pixel `
    -sEXPORTED_RUNTIME_METHODS=ccall -o "$Output/spike.mjs"
