param(
    [Parameter(Mandatory = $true)][string]$Preparation,
    [Parameter(Mandatory = $true)][string]$Snapshot,
    [Parameter(Mandatory = $true)][string]$SourceSha256,
    [Parameter(Mandatory = $true)][string]$Build,
    [Parameter(Mandatory = $true)][string]$Evidence
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$snapshotRoot = (Resolve-Path -LiteralPath $Snapshot).Path
$buildRoot = [System.IO.Path]::GetFullPath($Build)
$evidenceRoot = [System.IO.Path]::GetFullPath($Evidence)
$prepared = Get-Content -LiteralPath $Preparation -Raw | ConvertFrom-Json
$buildPython = Join-Path $prepared.environment 'Scripts/python.exe'
$cmake = $prepared.cmake.origin
if ((Get-FileHash -LiteralPath $cmake -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prepared.cmake.sha256) { throw 'Prepared CMake changed' }
$sourceManifest = Get-Content -LiteralPath (Join-Path $snapshotRoot 'wheel-source-manifest.json') -Raw | ConvertFrom-Json
if ($sourceManifest.source_tree_sha256 -ne $SourceSha256) { throw 'Unexpected frozen source identity' }
if ($sourceManifest.source_files.'pyproject.toml' -ne $prepared.pyproject_sha256 -or $sourceManifest.source_files.'uv.lock' -ne $prepared.root_lock_sha256) { throw 'Prepared environment differs from frozen packaging inputs' }
if (Test-Path -LiteralPath $buildRoot) { throw 'Producer build directory must be new; old vendor archives must not be reused' }
if (Test-Path -LiteralPath $evidenceRoot) { throw 'Evidence directory must be new' }
New-Item -ItemType Directory -Path $evidenceRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $snapshotRoot 'wheel-source-manifest.json') -Destination (Join-Path $evidenceRoot 'wheel-source-manifest.json')
Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $evidenceRoot 'build-script.ps1')
Copy-Item -LiteralPath $Preparation -Destination (Join-Path $evidenceRoot 'build-preparation.json')

function Get-ProtectedBinaries {
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $workspaceRoot 'src/vispy') -Recurse -File) {
        if ($file.Extension -in @('.pyd', '.dll')) {
            $result[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    return $result
}

function Assert-FrozenSource {
    foreach ($property in $sourceManifest.source_files.PSObject.Properties) {
        $actual = (Get-FileHash -LiteralPath (Join-Path $snapshotRoot $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $property.Value) { throw "Frozen source changed: $($property.Name)" }
    }
}

function Invoke-RecordedNative {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    # Windows PowerShell wraps stderr in NativeCommandError even for a command
    # that succeeds. Preserve it and judge the real process exit code.
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Executable @Arguments *> $Log
        $processExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    return $processExit
}

$before = Get-ProtectedBinaries
$before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-before.json')
try {
    Assert-FrozenSource
    $configure = @('-S', $snapshotRoot, '-B', $buildRoot, '-G', 'Visual Studio 17 2022', '-A', 'x64', '-T', $prepared.toolchain.generator_toolset,
        '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CONFIGURATION_TYPES=Release', "-DCMAKE_SYSTEM_VERSION=$($prepared.toolchain.windows_sdk)",
        "-DPython_EXECUTABLE=$buildPython", "-DPython3_EXECUTABLE=$buildPython", '-DVISPY_INPLACE=OFF', '-DVISPY_VERIFY_DEPENDENCIES=ON',
        '-DVISPY_EXPORT_NATIVE_SDK=ON', '-DVISPY_LEGACY_MSVC_CRT_MUTEX=ON', '-DVISPY_BUILD_CONTRACT_TESTS=OFF', '--log-level=ERROR')
    @{'cmake'=$cmake; 'arguments'=$configure} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'configure-command.json')
    if ((Invoke-RecordedNative $cmake $configure (Join-Path $evidenceRoot 'configure.log')) -ne 0) { throw 'Producer configure failed; log preserved' }
    $attest = @((Join-Path $PSScriptRoot 'verify_native_producer.py'), '--build', $buildRoot, '--output', (Join-Path $evidenceRoot 'generated-cpp-policy.json'))
    if ((Invoke-RecordedNative $buildPython $attest (Join-Path $evidenceRoot 'generated-cpp-policy.log')) -ne 0) { throw 'Generated compiler policy rejected; no compilation launched' }
    $compile = @('--build', $buildRoot, '--config', 'Release', '--parallel', '3', '--target', '_dawn', '_sdf_cpu', '--', '/p:CL_MPCount=3')
    @{'cmake'=$cmake; 'arguments'=$compile} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'build-command.json')
    if ((Invoke-RecordedNative $cmake $compile (Join-Path $evidenceRoot 'build.log')) -ne 0) { throw 'Producer build failed; log preserved' }
    Assert-FrozenSource
    $verifySources = @((Join-Path $snapshotRoot 'cmake/verify_dependencies.py'))
    if ((Invoke-RecordedNative $buildPython $verifySources (Join-Path $evidenceRoot 'dependencies-after.log')) -ne 0) { throw 'Vendor sources changed during compilation' }
    @{status='built'; native_graphics_qualified=$false; sdk_staged=$false; wheel_qualified=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'status.json')
} finally {
    $after = Get-ProtectedBinaries
    $after | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-after.json')
    if ($before.Count -ne $after.Count) { throw 'Source native inventory changed during isolated producer build' }
    foreach ($path in $before.Keys) {
        if ($after[$path] -ne $before[$path]) { throw "Source native artifact changed during isolated producer build: $path" }
    }
}
Write-Output 'Compatible producer built from a new cache; SDK staging and installed consumer qualification remain pending.'
