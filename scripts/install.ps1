# ParetoBench installer for Windows:  irm https://github.com/michael-berardi/paretobench/releases/latest/download/install.ps1 | iex
# Downloads the latest release (a small pure-Python bundle), checks its SHA-256, and puts `paretobench` (and `pb`)
# on your PATH. Needs Python 3.11+ already on this machine; there are no dependencies, so no venv is created.
# Works in Windows PowerShell 5.1 and PowerShell 7, and under PowerShell 7 on Linux for testing.
# Environment: PARETOBENCH_HOME (default %LOCALAPPDATA%\ParetoBench, ~/.paretobench on Linux),
# PARETOBENCH_BIN_DIR (default <home>\bin, ~/.local/bin on Linux), PARETOBENCH_VERSION (e.g. 0.1.0),
# PARETOBENCH_RELEASE_BASE (override the download base URL, used by tests).
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
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) { throw 'ParetoBench needs tar (built in on Windows 10+ and Linux).' }

$tmp = Join-Path ([IO.Path]::GetTempPath()) ('paretobench-install-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$savedPythonPath = $env:PYTHONPATH; $savedTasks = $env:PARETOBENCH_TASKS
try {
    if ($PSVersionTable.PSEdition -eq 'Desktop') {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    }
    Write-Host 'Downloading ParetoBench...'
    $archive = Join-Path $tmp 'paretobench.tar.gz'
    $sumsFile = Join-Path $tmp 'SHA256SUMS'
    Invoke-WebRequest "$base/paretobench.tar.gz" -OutFile $archive -UseBasicParsing
    Invoke-WebRequest "$base/SHA256SUMS" -OutFile $sumsFile -UseBasicParsing
    $want = (Get-Content $sumsFile | Where-Object { $_ -match '\sparsebench\.tar\.gz$' } | Select-Object -First 1)
    $want = if ($want) { ($want -split '\s+')[0].ToLower() } else { '' }
    if (-not $want) { throw 'no checksum for paretobench.tar.gz in SHA256SUMS; nothing was installed.' }
    $got = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
    if ($got -ne $want) { throw 'checksum mismatch for paretobench.tar.gz; nothing was installed.' }

    $src = Join-Path $tmp 'src'
    New-Item -ItemType Directory -Path $src | Out-Null
    & tar -xzf $archive -C $src
    if ($LASTEXITCODE -ne 0) { throw 'cannot unpack the download (tar failed).' }
    if (-not (Test-Path (Join-Path $src 'paretobench/cli.py')) -or -not (Test-Path (Join-Path $src 'tasks/tasks.json'))) {
        throw 'the download is not a ParetoBench release.'
    }
    $verLine = Get-Content (Join-Path $src 'paretobench/__init__.py') | Where-Object { $_ -like '__version__ = *' } | Select-Object -First 1
    if (-not $verLine -or $verLine -notmatch '^__version__ = "([^"]+)"') { throw 'cannot read the release version.' }
    $version = $Matches[1]

    # Stage inside PARETOBENCH_HOME so the final move is a same-volume rename; nothing is half-installed.
    New-Item -ItemType Directory -Path $homeDir -Force | Out-Null
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    $stage = Join-Path $homeDir ('.app.new-' + [guid]::NewGuid().ToString('N'))
    Move-Item $src $stage
    $env:PYTHONPATH = $stage; $env:PARETOBENCH_TASKS = Join-Path $stage 'tasks'
    $got = (& $pyExe @pyArgs -m paretobench.cli --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $got -ne "paretobench $version") {
        Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
        throw "the new copy reports '$got', not paretobench $version; nothing was changed."
    }
    Write-Host "Installing ParetoBench $version..."
    $old = Join-Path $homeDir 'app.old'
    if (Test-Path $old) { Remove-Item -Recurse -Force $old }
    if (Test-Path $appDir) { Move-Item $appDir $old }
    Move-Item $stage $appDir
    if (Test-Path $old) { Remove-Item -Recurse -Force $old }

    # The models config lives outside the install so upgrades keep it. Seed the documented example when absent.
    $models = if ($env:PARETOBENCH_CONFIG) { $env:PARETOBENCH_CONFIG } else { Join-Path $userHome '.config/paretobench/models.json' }
    if (-not (Test-Path $models)) {
        New-Item -ItemType Directory -Path (Split-Path $models -Parent) -Force | Out-Null
        Copy-Item (Join-Path $appDir 'configs/models.example.json') $models
        Write-Host "Seeded example models config at $models; edit it with your own models and routes before running a bench."
    }

    # Shims: run the installed copy with the right PYTHONPATH and task set; a user-set PARETOBENCH_TASKS wins.
    $tasksDir = Join-Path $appDir 'tasks'
    if ($isWin) {
        $pyCmd = (@($pyExe) + $pyArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
        foreach ($name in @('paretobench', 'pb')) {
            $cmd = @(
                '@echo off',
                "if not defined PARETOBENCH_TASKS set ""PARETOBENCH_TASKS=$tasksDir""",
                "set ""PYTHONPATH=$appDir;%PYTHONPATH%""",
                "$pyCmd -m paretobench.cli %*"
            ) -join "`r`n"
            Set-Content -Path (Join-Path $binDir "$name.cmd") -Value $cmd -Encoding Ascii
        }
        $launcher = Join-Path $binDir 'paretobench.cmd'
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        if (-not $userPath) { $userPath = '' }
        if (($userPath -split ';') -notcontains $binDir) {
            $newPath = if ($userPath) { "$userPath;$binDir" } else { $binDir }
            [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
            Write-Host "Added $binDir to your user PATH; open a new terminal to use it."
        }
    } else {
        foreach ($name in @('paretobench', 'pb')) {
            $sh = @(
                '#!/bin/sh',
                '# ParetoBench launcher, written by install.ps1. Re-run the installer to upgrade.',
                "PARETOBENCH_TASKS=""`${PARETOBENCH_TASKS:-$tasksDir}""",
                "PYTHONPATH=""$appDir`${PYTHONPATH:+:`$PYTHONPATH}""",
                'export PARETOBENCH_TASKS PYTHONPATH',
                "exec ""$pyExe"" -m paretobench.cli ""`$@"""
            ) -join "`n"
            $path = Join-Path $binDir $name
            Set-Content -Path $path -Value ($sh + "`n") -Encoding Ascii -NoNewline
            & chmod 755 $path
            if ($LASTEXITCODE -ne 0) { throw "cannot make $path executable." }
        }
        $launcher = Join-Path $binDir 'paretobench'
        if (($env:PATH -split ':') -notcontains $binDir) {
            Write-Host "Add $binDir to your PATH:  export PATH=""${binDir}:`$PATH"""
        }
    }

    Write-Host "ParetoBench $version installed ($binDir)."
    $env:PYTHONPATH = $appDir; $env:PARETOBENCH_TASKS = $tasksDir
    & $launcher validate
    if ($LASTEXITCODE -ne 0) { throw 'paretobench validate failed after install (see the error above).' }
    Write-Host 'Checking harness executables (paretobench doctor):'
    & $launcher doctor
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'doctor: some harness executables are missing; that is fine for installing. Add them before running a bench.'
    }
    Write-Host 'Next: paretobench selftest'
} finally {
    $env:PYTHONPATH = $savedPythonPath; $env:PARETOBENCH_TASKS = $savedTasks
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}