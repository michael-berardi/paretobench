# ParetoBench installer for Windows:  irm https://github.com/michael-berardi/paretobench/releases/latest/download/install.ps1 | iex
# Downloads the latest release (a small pure-Python bundle), checks its SHA-256, and puts `paretobench` (and `pb`)
# on your PATH. Needs Python 3.11+ already on this machine; there are no dependencies, so no venv is created.
# Works in Windows PowerShell 5.1 and PowerShell 7, and under PowerShell 7 on Linux for testing.
# Environment: PARETOBENCH_HOME (default %LOCALAPPDATA%\ParetoBench, ~/.paretobench on Linux),
# PARETOBENCH_BIN_DIR (default <home>\bin, ~/.local/bin on Linux), PARETOBENCH_VERSION (e.g. 0.1.0),
# PARETOBENCH_RELEASE_BASE (override the download base URL, used by tests).
function Install-ParetoBench {
    $ErrorActionPreference = 'Stop'

$repo = 'michael-berardi/paretobench'
$base = if ($env:PARETOBENCH_RELEASE_BASE) { $env:PARETOBENCH_RELEASE_BASE }
        elseif ($env:PARETOBENCH_VERSION) { "https://github.com/$repo/releases/download/v$($env:PARETOBENCH_VERSION.TrimStart('v'))" }
        else { "https://github.com/$repo/releases/latest/download" }
$isWin = ($PSVersionTable.PSEdition -eq 'Desktop') -or ($IsWindows -eq $true)
$userHome = if ($isWin) { $env:USERPROFILE } else { $HOME }
$homeDir = if ($env:PARETOBENCH_HOME) { $env:PARETOBENCH_HOME }
           elseif ($isWin) { Join-Path $env:LOCALAPPDATA 'ParetoBench' }
           else { Join-Path $HOME '.paretobench' }
$binDir = if ($env:PARETOBENCH_BIN_DIR) { $env:PARETOBENCH_BIN_DIR }
          elseif ($isWin) { Join-Path $homeDir 'bin' }
          else { Join-Path $HOME '.local/bin' }
$homeDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($homeDir)
$binDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($binDir)
$appDir = Join-Path $homeDir 'app'

# Python 3.11+ on this machine; there are no dependencies, so the system Python is used directly.
$pyHint = if ($isWin) { 'winget install -e --id Python.Python.3.13 (then open a new terminal and run this again)' }
          else { 'sudo apt-get install -y python3.12 (or your distribution''s equivalent)' }
$pyCandidates = if ($isWin) { @(@('py', '-3'), @('python'), @('python3')) } else { @(@('python3.13'), @('python3.12'), @('python3.11'), @('python3')) }
$pyExe = $null; $pyArgs = @()
foreach ($cand in $pyCandidates) {
    $exe = $cand[0]; $args0 = @($cand | Select-Object -Skip 1)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    try {
        & $exe @args0 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $pyExe = $exe; $pyArgs = $args0; break }
    } catch { continue }
}
if (-not $pyExe) { throw "ParetoBench needs Python 3.11 or newer and none was found; install it with: $pyHint" }
# On Windows use the system bsdtar: a GNU tar earlier on PATH (Git for Windows) misreads drive-letter paths.
$tarExe = 'tar'
if ($isWin -and $env:SystemRoot -and (Test-Path "$env:SystemRoot\System32\tar.exe")) { $tarExe = "$env:SystemRoot\System32\tar.exe" }
if (-not (Get-Command $tarExe -ErrorAction SilentlyContinue)) { throw 'ParetoBench needs tar (built in on Windows 10+ and Linux).' }

$tmp = Join-Path ([IO.Path]::GetTempPath()) ('paretobench-install-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$savedPythonPath = $env:PYTHONPATH; $savedTasks = $env:PARETOBENCH_TASKS
$stage = $null; $old = Join-Path $homeDir 'app.old'
$marker = 'ParetoBench launcher, written by install'
# True when $path may be written: absent, or one of our own shims (marker, or the unmarked shape 0.2.0 wrote).
function Test-OurShim($path) {
    if (-not (Test-Path -LiteralPath $path)) { return $true }
    $text = Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return $false }
    return ($text.Contains($marker) -or ($text.Contains('paretobench.cli') -and $text.Contains('PARETOBENCH_TASKS')))
}
try {
    if ($PSVersionTable.PSEdition -eq 'Desktop') {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
    }
    Write-Host 'Downloading ParetoBench...'
    $archive = Join-Path $tmp 'paretobench.tar.gz'
    $sumsFile = Join-Path $tmp 'SHA256SUMS'
    Invoke-WebRequest "$base/paretobench.tar.gz" -OutFile $archive -UseBasicParsing
    Invoke-WebRequest "$base/SHA256SUMS" -OutFile $sumsFile -UseBasicParsing
    $want = (Get-Content $sumsFile | Where-Object { $_ -match '\s+\*?paretobench\.tar\.gz$' } | Select-Object -First 1)
    $want = if ($want) { ($want -split '\s+')[0].ToLower() } else { '' }
    if (-not $want) { throw 'no checksum for paretobench.tar.gz in SHA256SUMS; nothing was installed.' }
    $got = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
    if ($got -ne $want) { throw 'checksum mismatch for paretobench.tar.gz; nothing was installed.' }

    # Unpack straight into a staging folder inside PARETOBENCH_HOME: the final move is a same-volume rename
    # (Move-Item from %TEMP% fails across drives on Windows PowerShell 5.1) and nothing is half-installed.
    New-Item -ItemType Directory -Path $homeDir -Force | Out-Null
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    $stage = Join-Path $homeDir ('.app.new-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    & $tarExe -xzf $archive -C $stage
    if ($LASTEXITCODE -ne 0) { throw 'cannot unpack the download (tar failed).' }
    if (-not (Test-Path (Join-Path $stage 'paretobench/cli.py')) -or -not (Test-Path (Join-Path $stage 'tasks/tasks.json'))) {
        throw 'the download is not a ParetoBench release.'
    }
    $verLine = Get-Content (Join-Path $stage 'paretobench/__init__.py') | Where-Object { $_ -like '__version__ = *' } | Select-Object -First 1
    if (-not $verLine -or $verLine -notmatch '^__version__ = "([^"]+)"') { throw 'cannot read the release version.' }
    $version = $Matches[1]

    $env:PYTHONPATH = $stage; $env:PARETOBENCH_TASKS = Join-Path $stage 'tasks'
    # Windows PowerShell 5.1 turns the first stderr line of a native call into a terminating error under 'Stop'.
    $ErrorActionPreference = 'Continue'
    $got = (& $pyExe @pyArgs -m paretobench.cli --version 2>&1 | Out-String).Trim()
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($rc -ne 0 -or $got -ne "paretobench $version") {
        throw "the new copy reports '$got', not paretobench $version; nothing was changed."
    }
    Write-Host "Installing ParetoBench $version..."
    if (Test-Path $old) { Remove-Item -Recurse -Force $old }
    if (Test-Path $appDir) { Move-Item $appDir $old }
    Move-Item $stage $appDir
    $stage = $null
    if (Test-Path $old) { Remove-Item -Recurse -Force $old }

    # The models config lives outside the install so upgrades keep it. Seed the documented example when absent.
    $models = if ($env:PARETOBENCH_CONFIG) { $env:PARETOBENCH_CONFIG } else { Join-Path $userHome '.config/paretobench/models.json' }
    if (-not (Test-Path $models)) {
        New-Item -ItemType Directory -Path (Split-Path $models -Parent) -Force | Out-Null
        Copy-Item (Join-Path $appDir 'configs/models.example.json') $models
        Write-Host "Seeded example models config at $models; edit it with your own models and routes before running a bench."
    }

    # Shims: run the installed copy with the right PYTHONPATH and task set; a user-set PARETOBENCH_TASKS wins.
    # A file in the bin folder that this installer did not write is never overwritten.
    $tasksDir = Join-Path $appDir 'tasks'
    $launcher = $null
    if ($isWin) {
        $pyCmd = (@($pyExe) + $pyArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
        # In the default bin folder (<home>\bin) the shim finds the app relative to itself, so a profile path with
        # non-ASCII characters never has to be encoded. A BIN_DIR elsewhere gets absolute paths in the OEM code page.
        $relative = $binDir.TrimEnd('\', '/') -ieq (Join-Path $homeDir 'bin').TrimEnd('\', '/')
        $appRef = if ($relative) { '%~dp0..\app' } else { $appDir }
        $tasksRef = if ($relative) { '%~dp0..\app\tasks' } else { $tasksDir }
        foreach ($name in @('paretobench', 'pb')) {
            $shim = Join-Path $binDir "$name.cmd"
            if (-not (Test-OurShim $shim)) {
                Write-Host "Left $shim alone: it was not written by this installer. Use paretobench instead."
                continue
            }
            $cmd = (@(
                '@echo off',
                'setlocal',
                "REM $marker.ps1. Re-run the installer to upgrade.",
                "if not defined PARETOBENCH_TASKS set ""PARETOBENCH_TASKS=$tasksRef""",
                "set ""PYTHONPATH=$appRef;%PYTHONPATH%""",
                "$pyCmd -m paretobench.cli %*"
            ) -join "`r`n") + "`r`n"
            $oem = [Text.Encoding]::GetEncoding([Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage)
            [IO.File]::WriteAllText($shim, $cmd, $oem)
            if ($name -eq 'paretobench') { $launcher = $shim }
        }
        # Add the bin folder to the USER Path only when absent. The raw value is read without expanding %VAR% entries
        # and written back with its original registry type, so a stock %USERPROFILE%\... entry keeps expanding.
        $envKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
        try {
            $userPath = [string]$envKey.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            $already = @($userPath -split ';' | Where-Object {
                $_ -and (($_.TrimEnd('\') -ieq $binDir.TrimEnd('\')) -or ([Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') -ieq $binDir.TrimEnd('\')))
            })
            if ($already.Count -eq 0) {
                $newPath = if ($userPath) { $userPath.TrimEnd(';') + ';' + $binDir } else { $binDir }
                $kind = if ($null -ne $envKey.GetValue('Path', $null)) { $envKey.GetValueKind('Path') } else { [Microsoft.Win32.RegistryValueKind]::ExpandString }
                $envKey.SetValue('Path', $newPath, $kind)
                # Setting and clearing a dummy user variable broadcasts the change so new terminals pick the Path up.
                [Environment]::SetEnvironmentVariable('PARETOBENCH_PATH_REFRESH', '1', 'User')
                [Environment]::SetEnvironmentVariable('PARETOBENCH_PATH_REFRESH', $null, 'User')
                Write-Host "Added $binDir to your user PATH; open a new terminal to use it."
            }
        } finally { if ($envKey) { $envKey.Close() } }
    } else {
        foreach ($name in @('paretobench', 'pb')) {
            $path = Join-Path $binDir $name
            if (-not (Test-OurShim $path)) {
                Write-Host "Left $path alone: it was not written by this installer. Use paretobench instead."
                continue
            }
            $sh = @(
                '#!/bin/sh',
                "# $marker.ps1. Re-run the installer to upgrade.",
                "PARETOBENCH_TASKS=""`${PARETOBENCH_TASKS:-$tasksDir}""",
                "PYTHONPATH=""$appDir`${PYTHONPATH:+:`$PYTHONPATH}""",
                'export PARETOBENCH_TASKS PYTHONPATH',
                "exec ""$pyExe"" -m paretobench.cli ""`$@"""
            ) -join "`n"
            Set-Content -Path $path -Value ($sh + "`n") -Encoding Ascii -NoNewline
            & chmod 755 $path
            if ($LASTEXITCODE -ne 0) { throw "cannot make $path executable." }
            if ($name -eq 'paretobench') { $launcher = $path }
        }
        if (($env:PATH -split ':') -notcontains $binDir) {
            Write-Host "Add $binDir to your PATH:  export PATH=""${binDir}:`$PATH"""
        }
    }

    Write-Host "ParetoBench $version installed ($binDir)."
    $env:PYTHONPATH = $appDir; $env:PARETOBENCH_TASKS = $tasksDir
    if (-not $launcher) { $launcher = $pyExe }
    $launchArgs = if ($launcher -eq $pyExe) { @($pyArgs + @('-m', 'paretobench.cli')) } else { @() }
    & $launcher @launchArgs validate
    if ($LASTEXITCODE -ne 0) { throw 'paretobench validate failed after install (see the error above).' }
    Write-Host 'Checking harness executables (paretobench doctor):'
    & $launcher @launchArgs doctor
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'doctor: some harness executables are missing; that is fine for installing. Add them before running a bench.'
    }
    Write-Host 'Next: paretobench selftest'
} finally {
    $env:PYTHONPATH = $savedPythonPath; $env:PARETOBENCH_TASKS = $savedTasks
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    if ($stage) { Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue }
    # An install that died between the two moves leaves the previous release in app.old: put it back.
    if ((Test-Path $old) -and -not (Test-Path $appDir)) { Move-Item $old $appDir -ErrorAction SilentlyContinue }
}
}
Install-ParetoBench
