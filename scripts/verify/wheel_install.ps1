<#
.SYNOPSIS
    Build the wheel and prove it works in a clean environment.

.DESCRIPTION
    A wheel that builds is not a wheel that works. This script builds, checks the
    metadata, installs into a fresh venv that has nothing but the declared
    dependencies, and then exercises the entry points. It exists because the first
    clean-venv install found `ModuleNotFoundError: No module named 'numpy'` after
    `hcs-therapy kb index` — a defect no source-tree test could see.

    It never publishes anything. Publishing needs credentials and explicit
    authorisation (AGENTS.md §14.2).

.EXAMPLE
    pwsh -File scripts/verify/wheel_install.ps1
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch]$KeepEnvironment
)

$ErrorActionPreference = 'Stop'
Set-Location $RepoRoot

$venv = Join-Path $env:TEMP 'hcs-wheel-verify'
$home2 = Join-Path $env:TEMP 'hcs-wheel-verify-home'
$failures = New-Object System.Collections.Generic.List[string]

function Step {
    param([string]$Name, [scriptblock]$Body)
    Write-Host "==> $Name" -ForegroundColor Cyan
    try {
        & $Body
        Write-Host "    ok" -ForegroundColor Green
    } catch {
        $failures.Add("$Name : $($_.Exception.Message)")
        Write-Host "    FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Step 'build sdist and wheel' {
    Remove-Item -Recurse -Force (Join-Path $RepoRoot 'dist') -ErrorAction SilentlyContinue
    & .\.venv\Scripts\python.exe -m build
    if ($LASTEXITCODE -ne 0) { throw 'python -m build failed' }
    $wheel = Get-ChildItem dist\*.whl | Select-Object -First 1
    if (-not $wheel) { throw 'no wheel produced' }
}

Step 'twine check' {
    & .\.venv\Scripts\python.exe -m twine check dist\*
    if ($LASTEXITCODE -ne 0) { throw 'twine check failed' }
}

Step 'wheel contains the package and no data' {
    & .\.venv\Scripts\python.exe -c @"
import glob, sys, zipfile
wheel = glob.glob('dist/*.whl')[0]
names = zipfile.ZipFile(wheel).namelist()
problems = []
if any(n.startswith('tests/') for n in names):
    problems.append('tests/ shipped inside the wheel')
if any(n.endswith('.gguf') or n.endswith('.safetensors') for n in names):
    problems.append('model weights shipped inside the wheel')
if any(n.endswith('content.key') for n in names):
    problems.append('a private key shipped inside the wheel')
if not any(n == 'hcs_therapy/cli.py' for n in names):
    problems.append('the CLI module is missing')
if problems:
    print('; '.join(problems)); sys.exit(1)
print(f'{len(names)} entries, no data files')
"@
    if ($LASTEXITCODE -ne 0) { throw 'wheel contents check failed' }
}

Step 'install into a clean venv' {
    Remove-Item -Recurse -Force $venv -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $home2 -ErrorAction SilentlyContinue
    uv venv --python 3.14 $venv | Out-Null
    $wheel = (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
    uv pip install --python (Join-Path $venv 'Scripts\python.exe') $wheel
    if ($LASTEXITCODE -ne 0) { throw 'clean install failed' }
}

$env:HCS_THERAPY_HOME = $home2
$cli = Join-Path $venv 'Scripts\hcs-therapy.exe'

Step 'the CLI starts' {
    & $cli --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'hcs-therapy --version failed' }
}

Step 'doctor reports this machine' {
    $json = & $cli doctor --json | ConvertFrom-Json
    if (-not $json.hardware.cpu_name) { throw 'doctor returned no CPU name' }
    if ($json.product -ne 'HCS Therapy Studio') { throw 'doctor product mismatch' }
}

Step 'kb index and search work without the dev venv' {
    $note = Join-Path $env:TEMP 'wheel-verify-note.md'
    Set-Content -Path $note -Value "# Notiz`n`nPruefungsangst und schlechter Schlaf haengen zusammen." -Encoding utf8
    & $cli kb index $note --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'kb index failed' }
    $hits = (& $cli kb search 'Pruefungsangst' --json | ConvertFrom-Json).hits
    if (-not $hits -or $hits.Count -lt 1) { throw 'kb search returned nothing' }
}

Step 'the safety gate fires from the installed wheel' {
    $assess = & $cli safety assess 'Ich bringe mich heute Nacht um.' --json | ConvertFrom-Json
    if ($assess.level -ne 'IMMINENT') { throw "expected IMMINENT, got $($assess.level)" }
}

Step 'eval suites are registered' {
    $suites = (& $cli eval suites --json | ConvertFrom-Json).local_suites
    if ($suites -notcontains 'hcs-core') { throw 'hcs-core suite missing' }
}

Step 'the MCP entry point exists' {
    if (-not (Test-Path (Join-Path $venv 'Scripts\hcs-therapy-mcp.exe'))) {
        throw 'hcs-therapy-mcp was not installed'
    }
}

if (-not $KeepEnvironment) {
    Remove-Item -Recurse -Force $venv -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $home2 -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
    Write-Host ''
    Write-Host "$($failures.Count) step(s) failed:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host ''
Write-Host 'wheel verified: builds, checks, installs clean, and every entry point runs.' -ForegroundColor Green
exit 0
