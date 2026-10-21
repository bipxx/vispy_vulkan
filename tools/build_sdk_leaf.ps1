param(
    [Parameter(Mandatory = $true)][string]$Preparation,
    [Parameter(Mandatory = $true)][string]$Snapshot,
    [Parameter(Mandatory = $true)][string]$Evidence,
    [Parameter(Mandatory = $true)][string]$Sdk,
    [Parameter(Mandatory = $true)][string]$SdkManifestSha256
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$snapshotRoot = (Resolve-Path -LiteralPath $Snapshot).Path
$sdkRoot = (Resolve-Path -LiteralPath $Sdk).Path
$evidenceRoot = [System.IO.Path]::GetFullPath($Evidence)
$prepared = Get-Content -LiteralPath $Preparation -Raw | ConvertFrom-Json
$buildPython = Join-Path $prepared.environment 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) { throw 'Prepared build interpreter is missing' }
$resolverVersion = & uv --version
if ($prepared.resolver) {
    if ($resolverVersion -ne $prepared.resolver) { throw 'uv differs from the preparation manifest' }
} elseif (-not $resolverVersion.StartsWith('uv 0.12.5 ')) {
    throw 'Legacy preparation requires the observed uv 0.12.5 toolchain'
}
$preparedAbi = $prepared.abi
if (-not $preparedAbi) {
    $versionParts = $prepared.interpreter_pin.Split('.')
    $preparedAbi = "cp$($versionParts[0])$($versionParts[1])"
}
$sourceManifestPath = Join-Path $snapshotRoot 'wheel-source-manifest.json'
$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
if ($sourceManifest.source_files.'pyproject.toml' -ne $prepared.pyproject_sha256 -or $sourceManifest.source_files.'uv.lock' -ne $prepared.root_lock_sha256) { throw 'Snapshot packaging inputs differ from the prepared environment' }
if ((Get-FileHash -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $SdkManifestSha256) { throw 'Unexpected SDK manifest' }
if (Test-Path -LiteralPath $evidenceRoot) { throw 'Evidence directory must be new' }
New-Item -ItemType Directory -Path $evidenceRoot | Out-Null

function Get-ProtectedBinaries {
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $workspaceRoot 'src/vispy') -Recurse -File) {
        if ($file.Extension -in @('.pyd', '.dll')) {
            $result[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
    return $result
}

$before = Get-ProtectedBinaries
$before | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-before.json')
Copy-Item -LiteralPath (Join-Path $sdkRoot 'manifest.json') -Destination (Join-Path $evidenceRoot 'native-sdk-manifest.json')
Copy-Item -LiteralPath $sourceManifestPath -Destination (Join-Path $evidenceRoot 'wheel-source-manifest.json')
$savedEnvironment = @{}
foreach ($name in @('CMAKE_GENERATOR', 'CMAKE_GENERATOR_PLATFORM', 'CMAKE_GENERATOR_TOOLSET', 'CMAKE_BUILD_PARALLEL_LEVEL')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$settings = @(
    '--config-setting', "build-dir=build/sdk-$preparedAbi",
    '--config-setting', 'cmake.build-type=Release',
    '--config-setting', "cmake.define.Python_EXECUTABLE=$buildPython",
    '--config-setting', "cmake.define.Python3_EXECUTABLE=$buildPython",
    '--config-setting', "cmake.define.CMAKE_SYSTEM_VERSION=$($prepared.toolchain.windows_sdk)",
    '--config-setting', 'cmake.define.VISPY_INPLACE=OFF',
    '--config-setting', 'cmake.define.VISPY_VERIFY_DEPENDENCIES=ON',
    '--config-setting', 'cmake.define.VISPY_EXPORT_NATIVE_SDK=OFF',
    '--config-setting', "cmake.define.VISPY_NATIVE_SDK=$sdkRoot",
    '--config-setting', "cmake.define.VISPY_NATIVE_SDK_MANIFEST_SHA256=$SdkManifestSha256"
)
Push-Location -LiteralPath $snapshotRoot
try {
    $env:CMAKE_GENERATOR = 'Visual Studio 17 2022'
    $env:CMAKE_GENERATOR_PLATFORM = 'x64'
    $env:CMAKE_GENERATOR_TOOLSET = $prepared.toolchain.generator_toolset
    $env:CMAKE_BUILD_PARALLEL_LEVEL = '3'
    & uv build --python $buildPython --no-build-isolation --wheel --out-dir (Join-Path $evidenceRoot 'wheels') @settings
    $buildExit = $LASTEXITCODE
} finally {
    Pop-Location
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
    $after = Get-ProtectedBinaries
    $after | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'protected-source-binaries-after.json')
    if ($before.Count -ne $after.Count) { throw 'Source native inventory changed' }
    foreach ($path in $before.Keys) {
        if ($after[$path] -ne $before[$path]) { throw "Source native artifact changed: $path" }
    }
}
if ($buildExit -ne 0) { throw 'SDK leaf wheel build failed; evidence retained' }
$wheels = @(Get-ChildItem -LiteralPath (Join-Path $evidenceRoot 'wheels') -Filter '*.whl' -File)
if ($wheels.Count -ne 1 -or $wheels[0].Name -ne $prepared.expected_wheel) { throw 'Unexpected wheel or ABI tag' }
Get-FileHash -LiteralPath $wheels[0].FullName -Algorithm SHA256 | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceRoot 'wheel-sha256.json')
Write-Output "SDK leaf $preparedAbi wheel built; external consumer, rollback and graphics qualification remain pending."
