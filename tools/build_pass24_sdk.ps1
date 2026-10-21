param(
    [string]$Preparation = 'compat/cp312-candidate/preparation.json',
    [string]$Snapshot = 'build/w9/source',
    [string]$Build = 'build/native-pass24-sdk',
    [string]$Evidence = 'build/evidence/native-pass-24',
    [string]$Sdk = 'build/native-sdk/windows-x64-release-3',
    [switch]$ResumeConfigured
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = (Resolve-Path -LiteralPath $Snapshot).Path
$sdkRoot = (Resolve-Path -LiteralPath $Sdk).Path
$evidenceRoot = (Resolve-Path -LiteralPath $Evidence).Path
$buildRoot = [System.IO.Path]::GetFullPath($Build)
if ((Test-Path -LiteralPath $buildRoot) -and -not $ResumeConfigured) { throw 'Pass24 build cache must be new' }
if ($ResumeConfigured -and -not (Test-Path -LiteralPath (Join-Path $buildRoot 'CMakeCache.txt'))) { throw 'Resume requires the already configured owned pass24 cache' }
$prepared = Get-Content -LiteralPath $Preparation -Raw | ConvertFrom-Json
$frozen = Get-Content -LiteralPath (Join-Path $evidenceRoot 'frozen-inputs.json') -Raw | ConvertFrom-Json
$sourceManifest = Get-Content -LiteralPath (Join-Path $sourceRoot 'wheel-source-manifest.json') -Raw | ConvertFrom-Json
if ($sourceManifest.source_tree_sha256 -ne $frozen.source_tree_sha256) { throw 'Frozen source manifest differs from harness evidence' }
$python = Join-Path $prepared.environment 'Scripts/python.exe'
$cmake = $prepared.cmake.origin
$sdkDigest = '7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2'
if ((Get-FileHash -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sdkDigest) { throw 'Unexpected SDK3 manifest' }
if ((Get-FileHash -LiteralPath $cmake -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prepared.cmake.sha256) { throw 'Prepared CMake changed' }
$scriptArchive = if ($ResumeConfigured) { 'resume-script.ps1' } else { 'build-script.ps1' }
Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $evidenceRoot $scriptArchive)
Copy-Item -LiteralPath $Preparation -Destination (Join-Path $evidenceRoot 'build-preparation.json')
Copy-Item -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Destination (Join-Path $evidenceRoot 'native-sdk-manifest.json')

function Get-ProtectedBinaries {
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $workspaceRoot 'src/vispy') -Recurse -File) {
        if ($file.Extension -in @('.pyd','.dll')) {
            $result[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    return $result
}

function Assert-FrozenInputs {
    foreach ($property in $sourceManifest.source_files.PSObject.Properties) {
        if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw "Frozen source changed: $($property.Name)" }
    }
    foreach ($property in $frozen.harness_files.PSObject.Properties) {
        if ((Get-FileHash -LiteralPath (Join-Path $frozen.harness_root $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw "Frozen harness changed: $($property.Name)" }
    }
}

function Invoke-RecordedNative {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Executable @Arguments *> $Log
        $processExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    return $processExit
}

$before = Get-ProtectedBinaries
$before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-before.json') -Encoding UTF8
$savedMpCount = [Environment]::GetEnvironmentVariable('CL_MPCount', 'Process')
try {
    $env:CL_MPCount = '3'
    Assert-FrozenInputs
    $configure = @('-S',$sourceRoot,'-B',$buildRoot,'-G','Visual Studio 17 2022','-A','x64','-T',$prepared.toolchain.generator_toolset,
        '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CONFIGURATION_TYPES=Release',"-DCMAKE_SYSTEM_VERSION=$($prepared.toolchain.windows_sdk)",
        "-DPython_EXECUTABLE=$python","-DPython3_EXECUTABLE=$python",'-DVISPY_INPLACE=OFF','-DVISPY_VERIFY_DEPENDENCIES=ON',
        '-DVISPY_EXPORT_NATIVE_SDK=OFF','-DVISPY_LEGACY_MSVC_CRT_MUTEX=ON','-DVISPY_BUILD_CONTRACT_TESTS=ON',
        "-DVISPY_NATIVE_SDK=$sdkRoot","-DVISPY_NATIVE_SDK_MANIFEST_SHA256=$sdkDigest",
        "-DVISPY_CONTRACT_TESTS_ROOT=$($frozen.harness_root)/tests","-DVISPY_CONTRACT_DATASETS_ROOT=$($frozen.harness_root)/datasets")
    @{'executable'=$cmake; 'arguments'=$configure; 'CL_MPCount'='3'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'configure-command.json') -Encoding UTF8
    if (-not $ResumeConfigured) {
        if ((Invoke-RecordedNative $cmake $configure (Join-Path $evidenceRoot 'configure.log')) -ne 0) { throw 'Pass24 configure failed; evidence retained' }
    } else {
        $sourceSetting = Get-Content -LiteralPath (Join-Path $buildRoot 'CMakeCache.txt') | Where-Object { $_.StartsWith('CMAKE_HOME_DIRECTORY:INTERNAL=') }
        $configuredSource = $sourceSetting.Substring('CMAKE_HOME_DIRECTORY:INTERNAL='.Length)
        if ((Resolve-Path -LiteralPath $configuredSource).Path -ne $sourceRoot) { throw 'Resume cache belongs to another source snapshot' }
    }
    $attest = @((Join-Path $PSScriptRoot 'verify_native_contract_cache.py'),'--build',$buildRoot,'--sdk',$sdkRoot,'--output',(Join-Path $evidenceRoot 'generated-cpp-policy.json'))
    if ((Invoke-RecordedNative $python $attest (Join-Path $evidenceRoot 'generated-cpp-policy.log')) -ne 0) { throw 'Pass24 generated compiler policy failed; compilation not launched' }
    $compile = @('--build',$buildRoot,'--config','Release','--parallel','3','--target','_dawn','_sdf_cpu','VkLayer_vispy_submit',
        'shader_contract','point_contract','artifact_contract','texture_contract','state_contract','readback_contract','timestamp_contract',
        'native_contract','vk_layer_contract','--','/p:CL_MPCount=3')
    @{'executable'=$cmake; 'arguments'=$compile; 'CL_MPCount'='3'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'build-command.json') -Encoding UTF8
    if ((Invoke-RecordedNative $cmake $compile (Join-Path $evidenceRoot 'build.log')) -ne 0) { throw 'Pass24 build failed; evidence retained' }
    $ctest = Join-Path (Split-Path -Parent $cmake) 'ctest.exe'
    $tests = @('--test-dir',$buildRoot,'-C','Release','--output-on-failure','--output-junit',(Join-Path $evidenceRoot 'ctest.xml'))
    @{'executable'=$ctest; 'arguments'=$tests} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'ctest-command.json') -Encoding UTF8
    if ((Invoke-RecordedNative $ctest $tests (Join-Path $evidenceRoot 'ctest.log')) -ne 0) { throw 'Pass24 CTest failed; evidence retained' }
    Assert-FrozenInputs
    if ((Invoke-RecordedNative $python @((Join-Path $sourceRoot 'cmake/verify_dependencies.py')) (Join-Path $evidenceRoot 'dependencies-after.log')) -ne 0) { throw 'Immutable vendor source verification failed after pass24' }
    New-Item -ItemType Directory -Path (Join-Path $evidenceRoot 'binaries') | Out-Null
    $hashes = @{}
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $buildRoot 'Release') -File) {
        if ($file.Extension -in @('.pyd','.dll','.exe','.pdb','.json')) {
            Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $evidenceRoot 'binaries')
            $hashes[$file.Name] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $layerManifest = Join-Path $buildRoot 'generated/VkLayer_vispy_submit.json'
    Copy-Item -LiteralPath $layerManifest -Destination (Join-Path $evidenceRoot 'binaries')
    $hashes['VkLayer_vispy_submit.json'] = (Get-FileHash -LiteralPath $layerManifest -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath (Join-Path $buildRoot 'CMakeCache.txt') -Destination (Join-Path $evidenceRoot 'CMakeCache.txt')
    $hashes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'binary-hashes.json') -Encoding UTF8
    @{status='build_and_ctest_passed'; source_tree_sha256=$frozen.source_tree_sha256; sdk_manifest_sha256=$sdkDigest;
      in_place_copy=$false; gpu_qualified=$false; sdk_tint_reader_enabled=$false;
      separate_full_source_tint_proof='full-source-tint-proof/evidence.json'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'status.json') -Encoding UTF8
} finally {
    [Environment]::SetEnvironmentVariable('CL_MPCount',$savedMpCount,'Process')
    $after = Get-ProtectedBinaries
    $after | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-after.json') -Encoding UTF8
    if ($before.Count -ne $after.Count) { throw 'Protected source binary inventory changed' }
    foreach ($path in $before.Keys) { if ($before[$path] -ne $after[$path]) { throw "Protected source binary changed: $path" } }
}
Write-Output 'Pass24 SDK build and matched CPU contracts passed; no source binary copy or GPU qualification.'
