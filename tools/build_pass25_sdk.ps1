param(
    [string]$Preparation = 'compat/cp312-candidate/preparation.json',
    [string]$Snapshot = 'build/w11/source',
    [string]$Build = 'build/native-pass25-sdk',
    [string]$Evidence = 'build/evidence/native-pass-25',
    [string]$Sdk = 'build/native-sdk/windows-x64-release-3',
    [switch]$ResumeConfigured,
    [string]$Attempt = 'initial',
    [string]$FrozenInputsSha256 = '',
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
# Read-only preflight runs before ANY output creation/copy, including on resume.
# The guard compares physical canonical paths, the whole frozen/CPU archive,
# activated pass24 artifacts, prepared tools, SDK, and cache ownership/settings.
$guardPython = Join-Path $workspaceRoot '.venv/Scripts/python.exe'
$guardArgs = @('-B',(Join-Path $PSScriptRoot 'pass25_guard.py'),'--snapshot',$Snapshot,
    '--evidence',$Evidence,'--build',$Build,'--sdk',$Sdk,'--preparation',$Preparation,'--attempt',$Attempt)
if ($ResumeConfigured) { $guardArgs += '--resume' }
if ($FrozenInputsSha256) { $guardArgs += @('--frozen-inputs-sha256',$FrozenInputsSha256) }
$guardOutput = & $guardPython @guardArgs
if ($LASTEXITCODE -ne 0) { throw 'Pass25 preflight rejected before writes' }
$guard = $guardOutput | ConvertFrom-Json
if ($PreflightOnly) { Write-Output $guardOutput; exit 0 }
$sourceRoot = $guard.paths.snapshot
$sdkRoot = $guard.paths.sdk
$packetEvidenceRoot = $guard.paths.evidence
$evidenceRoot = $guard.attempt_root
$buildRoot = $guard.paths.build
$Preparation = $guard.paths.preparation
$prepared = Get-Content -LiteralPath $Preparation -Raw | ConvertFrom-Json
$frozen = Get-Content -LiteralPath (Join-Path $packetEvidenceRoot 'frozen-inputs.json') -Raw | ConvertFrom-Json
$sourceManifest = Get-Content -LiteralPath (Join-Path $sourceRoot 'wheel-source-manifest.json') -Raw | ConvertFrom-Json
if ($sourceManifest.source_tree_sha256 -ne $frozen.source_tree_sha256) { throw 'Frozen source manifest differs from harness evidence' }
$python = Join-Path $prepared.environment 'Scripts/python.exe'
$cmake = $prepared.cmake.origin
$sdkDigest = '7ace20d9c52d2e8eaaf40cb4138637e3b3a1f56bcec89ffef64b604a3b9875c2'
if ((Get-FileHash -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sdkDigest) { throw 'Unexpected SDK3 manifest' }
if ((Get-FileHash -LiteralPath $cmake -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prepared.cmake.sha256) { throw 'Prepared CMake changed' }

function Get-ProtectedBinaries {
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $workspaceRoot 'src/vispy') -Recurse -File) {
        if ($file.Extension -in @('.pyd','.dll')) {
            $result[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    $activationPath = Join-Path $workspaceRoot 'build/evidence/native-pass-24/activation.json'
    if ((Get-FileHash -LiteralPath $activationPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $guard.owner.activation_manifest_sha256) { throw 'Activated pass24 manifest changed' }
    $activation = Get-Content -LiteralPath $activationPath -Raw | ConvertFrom-Json
    foreach ($property in $activation.activated.PSObject.Properties) {
        $relative = if ($property.Name.StartsWith('_sdf_cpu.')) { 'src/vispy/visuals/text/' + $property.Name } else { 'src/vispy/' + $property.Name }
        $path = Join-Path $workspaceRoot $relative
        $digest = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -ne $property.Value) { throw "Activated pass24 baseline changed: $relative" }
        $result[$path] = $digest.ToUpperInvariant()
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
Assert-FrozenInputs
# Claim the attempt exclusively only after every read-only guard passed.
if ($ResumeConfigured) {
    New-Item -ItemType Directory -Path $evidenceRoot -ErrorAction Stop | Out-Null
} else {
    $claim = [System.IO.File]::Open((Join-Path $evidenceRoot 'initial-attempt.json'),
        [System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes(($guard.owner | ConvertTo-Json -Depth 8))
        $claim.Write($bytes,0,$bytes.Length)
    } finally { $claim.Dispose() }
    $guard.owner | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $packetEvidenceRoot 'cache-owner.json') -Encoding UTF8
}
Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $evidenceRoot 'build-script.ps1')
Copy-Item -LiteralPath $Preparation -Destination (Join-Path $evidenceRoot 'build-preparation.json')
Copy-Item -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Destination (Join-Path $evidenceRoot 'native-sdk-manifest.json')
$guard | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'preflight.json') -Encoding UTF8
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
        if ((Invoke-RecordedNative $cmake $configure (Join-Path $evidenceRoot 'configure.log')) -ne 0) { throw 'Pass25 configure failed; evidence retained' }
    }
    @{owner=$guard.owner; cache_sha256=(Get-FileHash -LiteralPath (Join-Path $buildRoot 'CMakeCache.txt') -Algorithm SHA256).Hash.ToLowerInvariant()} |
        ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $packetEvidenceRoot 'cache-state.json') -Encoding UTF8
    $attest = @((Join-Path $PSScriptRoot 'verify_native_contract_cache.py'),'--build',$buildRoot,'--sdk',$sdkRoot,'--output',(Join-Path $evidenceRoot 'generated-cpp-policy.json'))
    if ((Invoke-RecordedNative $python $attest (Join-Path $evidenceRoot 'generated-cpp-policy.log')) -ne 0) { throw 'Pass25 generated compiler policy failed; compilation not launched' }
    $compile = @('--build',$buildRoot,'--config','Release','--parallel','3','--target','_dawn','_sdf_cpu','VkLayer_vispy_submit',
        'shader_contract','point_contract','artifact_contract','texture_contract','state_contract','readback_contract','timestamp_contract',
        'native_contract','vk_layer_contract','--','/p:CL_MPCount=3')
    @{'executable'=$cmake; 'arguments'=$compile; 'CL_MPCount'='3'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'build-command.json') -Encoding UTF8
    if ((Invoke-RecordedNative $cmake $compile (Join-Path $evidenceRoot 'build.log')) -ne 0) { throw 'Pass25 build failed; evidence retained' }
    $ctest = Join-Path (Split-Path -Parent $cmake) 'ctest.exe'
    $tests = @('--test-dir',$buildRoot,'-C','Release','--output-on-failure','--output-junit',(Join-Path $evidenceRoot 'ctest.xml'))
    @{'executable'=$ctest; 'arguments'=$tests} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'ctest-command.json') -Encoding UTF8
    if ((Invoke-RecordedNative $ctest $tests (Join-Path $evidenceRoot 'ctest.log')) -ne 0) { throw 'Pass25 CTest failed; evidence retained' }
    Assert-FrozenInputs
    if ((Invoke-RecordedNative $python @((Join-Path $sourceRoot 'cmake/verify_dependencies.py')) (Join-Path $evidenceRoot 'dependencies-after.log')) -ne 0) { throw 'Immutable vendor source verification failed after pass25' }
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
    @{owner=$guard.owner; cache_sha256=(Get-FileHash -LiteralPath (Join-Path $buildRoot 'CMakeCache.txt') -Algorithm SHA256).Hash.ToLowerInvariant()} |
        ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $packetEvidenceRoot 'cache-state.json') -Encoding UTF8
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
Write-Output 'Pass25 SDK build and matched CPU contracts passed; no source binary copy or GPU qualification.'
