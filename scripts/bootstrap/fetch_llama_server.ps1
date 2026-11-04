# Fetch and verify the pinned llama.cpp runtime (Windows x64, Vulkan build)
#
# The runtime is deliberately NOT vendored into git: it is 37 MB of binaries with
# its own release cadence. This script downloads the exact pinned artifact,
# verifies its SHA-256, and unpacks it into the per-user runtime directory where
# `hcs-therapy` looks for `llama-server.exe`.
#
# Usage:
#   pwsh -File scripts/bootstrap/fetch_llama_server.ps1
#   pwsh -File scripts/bootstrap/fetch_llama_server.ps1 -Force
#
# The hash and tag below are also recorded in licenses/manifest.yaml
# (entry: llama-cpp-runtime).

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Tag      = "b12102"
$Commit   = "bbb02c93e9b83255b70ac1a755bb02b0a251f9a7"
$Asset    = "llama-$Tag-bin-win-vulkan-x64.zip"
$Url      = "https://github.com/ggml-org/llama.cpp/releases/download/$Tag/$Asset"
$Sha256   = "b322f7d6ce8b2a31cf16980aa38986a6a27da2e55e406e770f0221621c38de08"

$Root     = if ($env:HCS_THERAPY_HOME) { $env:HCS_THERAPY_HOME } else { Join-Path $env:LOCALAPPDATA "HCS\TherapyStudio" }
$Runtime  = Join-Path $Root "runtime"
$Server   = Join-Path $Runtime "llama-server.exe"

if ((Test-Path $Server) -and -not $Force) {
    Write-Host "llama-server already present at $Server (use -Force to replace)"
    exit 0
}

New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
$Zip = Join-Path $env:TEMP $Asset

Write-Host "Downloading $Asset ($Tag, commit $($Commit.Substring(0,8)))..."
Invoke-WebRequest -Uri $Url -OutFile $Zip -TimeoutSec 600

$Actual = (Get-FileHash $Zip -Algorithm SHA256).Hash.ToLower()
if ($Actual -ne $Sha256) {
    Remove-Item $Zip -Force
    throw "SHA-256 mismatch for $Asset. Expected $Sha256, got $Actual. Refusing to install."
}
Write-Host "SHA-256 verified: $Actual"

Expand-Archive -Path $Zip -DestinationPath $Runtime -Force
Remove-Item $Zip -Force

if (-not (Test-Path $Server)) {
    throw "Extraction completed but llama-server.exe is missing. The archive layout changed; update this script."
}

Write-Host "Installed: $Server"
& $Server --version
