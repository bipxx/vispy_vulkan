param(
    [string] $Executable,
    [string[]] $Arguments = @(),
    [string] $OutputDirectory = "build/native-debugger/evidence",
    [string] $WorkingDirectory = "",
    [string] $SymbolPath = "",
    [int] $TimeoutSeconds = 900,
    [switch] $AllThreads,
    [switch] $CaptureFirstChance,
    [switch] $DebugChildren,
    [switch] $BuildOnly
)

$ErrorActionPreference = "Stop"
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$taskBuild = Join-Path $taskRoot "build/native-debugger"
[void] [IO.Directory]::CreateDirectory($taskBuild)
$taskSource = Join-Path $PSScriptRoot "windows_native_debugger.cpp"
$taskLauncher = Join-Path $taskBuild "windows_native_debugger.exe"

if ($BuildOnly -or -not (Test-Path -LiteralPath $taskLauncher) -or
    (Get-Item -LiteralPath $taskSource).LastWriteTimeUtc -gt (Get-Item -LiteralPath $taskLauncher).LastWriteTimeUtc) {
    $taskVswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio/Installer/vswhere.exe"
    if (-not (Test-Path -LiteralPath $taskVswhere)) { throw "VS2022 vswhere.exe was not found" }
    $taskVs = & $taskVswhere -latest -version "[17.0,18.0)" -products "*" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $taskVs) { throw "VS2022 C++ tools were not found" }
    $taskVcvars = Join-Path $taskVs "VC/Auxiliary/Build/vcvars64.bat"
    # Capture vcvars' environment without printing it. Compilation arguments are
    # then passed directly to cl; user-provided executable arguments use no shell.
    $taskCompilerEnvironment = & $env:COMSPEC /d /s /c ('"{0}" >nul && set' -f $taskVcvars)
    if ($LASTEXITCODE -ne 0) { throw "vcvars64 failed with exit $LASTEXITCODE" }
    foreach ($taskVariable in $taskCompilerEnvironment) {
        $taskEquals = $taskVariable.IndexOf('=')
        if ($taskEquals -gt 0) {
            [Environment]::SetEnvironmentVariable($taskVariable.Substring(0, $taskEquals), $taskVariable.Substring($taskEquals + 1), "Process")
        }
    }
    $taskCompileArguments = @('/nologo', '/std:c++20', '/EHsc', '/MD', '/Zi', '/Od', '/W4',
        "/Fe:$taskLauncher", "/Fo:$(Join-Path $taskBuild 'windows_native_debugger.obj')",
        "/Fd:$(Join-Path $taskBuild 'compiler.pdb')", $taskSource, '/link', 'Dbghelp.lib',
        '/DEBUG', "/PDB:$(Join-Path $taskBuild 'windows_native_debugger.pdb')")
    & cl.exe @taskCompileArguments
    if ($LASTEXITCODE -ne 0) { throw "native debugger compilation failed with exit $LASTEXITCODE" }
}
if ($BuildOnly) { Write-Output "Built $taskLauncher"; exit 0 }
if (-not $Executable) { throw "-Executable is required unless -BuildOnly is used" }
if ($TimeoutSeconds -lt 0 -or $TimeoutSeconds -gt 86400) { throw "TimeoutSeconds must be 0..86400" }
$taskChild = (Resolve-Path -LiteralPath $Executable).Path
if (-not $WorkingDirectory) { $WorkingDirectory = $taskRoot }
$taskCwd = (Resolve-Path -LiteralPath $WorkingDirectory).Path
$taskOutput = if ([IO.Path]::IsPathRooted($OutputDirectory)) { $OutputDirectory } else { Join-Path $taskRoot $OutputDirectory }
[void] [IO.Directory]::CreateDirectory($taskOutput)
$taskLog = Join-Path $taskOutput "native-stack.log"
$taskDump = Join-Path $taskOutput "native-crash.dmp"
$taskStdout = Join-Path $taskOutput "child.stdout.log"
$taskStderr = Join-Path $taskOutput "child.stderr.log"
$taskNativeArguments = @('--log', $taskLog, '--dump', $taskDump, '--cwd', $taskCwd,
    '--timeout-seconds', [string] $TimeoutSeconds)
if ($SymbolPath) { $taskNativeArguments += @('--symbols', $SymbolPath) }
if ($AllThreads) { $taskNativeArguments += '--all-threads' }
if ($CaptureFirstChance) { $taskNativeArguments += '--capture-first-chance' }
if ($DebugChildren) { $taskNativeArguments += '--debug-children' }
$taskNativeArguments += @('--', $taskChild)
$taskNativeArguments += $Arguments

function ConvertTo-NativeArgument([string] $Value) {
    $taskQuoted = [Text.StringBuilder]::new()
    [void] $taskQuoted.Append([char] '"')
    $taskSlashes = 0
    foreach ($taskCharacter in $Value.ToCharArray()) {
        if ($taskCharacter -eq [char] '\') { $taskSlashes++; continue }
        if ($taskCharacter -eq [char] '"') { [void] $taskQuoted.Append([char] '\', ($taskSlashes * 2 + 1)) }
        else { [void] $taskQuoted.Append([char] '\', $taskSlashes) }
        [void] $taskQuoted.Append($taskCharacter)
        $taskSlashes = 0
    }
    [void] $taskQuoted.Append([char] '\', ($taskSlashes * 2))
    [void] $taskQuoted.Append([char] '"')
    return $taskQuoted.ToString()
}
$taskStart = [Diagnostics.ProcessStartInfo]::new()
$taskStart.FileName = $taskLauncher
$taskStart.Arguments = (($taskNativeArguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
$taskStart.WorkingDirectory = $taskCwd
$taskStart.UseShellExecute = $false
$taskStart.CreateNoWindow = $true
$taskStart.RedirectStandardOutput = $true
$taskStart.RedirectStandardError = $true
$taskProcess = [Diagnostics.Process]::new()
$taskProcess.StartInfo = $taskStart
$taskOutFile = [IO.FileStream]::new($taskStdout, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite, 1, $true)
$taskErrFile = [IO.FileStream]::new($taskStderr, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite, 1, $true)
try {
    if (-not $taskProcess.Start()) { throw "native debugger process failed to start" }
    Write-Output "Debugger PID $($taskProcess.Id); live logs: $taskLog; $taskStdout; $taskStderr"
    $taskOutCopy = $taskProcess.StandardOutput.BaseStream.CopyToAsync($taskOutFile)
    $taskErrCopy = $taskProcess.StandardError.BaseStream.CopyToAsync($taskErrFile)
    $taskProcess.WaitForExit()
    [void] $taskOutCopy.GetAwaiter().GetResult()
    [void] $taskErrCopy.GetAwaiter().GetResult()
    $taskExit = $taskProcess.ExitCode
} finally {
    $taskOutFile.Dispose()
    $taskErrFile.Dispose()
    $taskProcess.Dispose()
}
Write-Output "Native debugger child exit $taskExit; stack: $taskLog; dump (when a native crash occurs): $taskDump"
exit $taskExit
