# CamMana Windows One-Click Setup (PowerShell) - Private Repo Version
# This script handles cases where Git or WSL are NOT installed and the repo is PRIVATE.
# Usage: $env:GH_TOKEN="your_token"; irm https://.../setup.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting CamMana Private Setup..." -ForegroundColor Cyan

# 1. Handle Private Access Token
$Token = $env:GH_TOKEN
if (!$Token) {
    Write-Host "🔐 Repository is PRIVATE." -ForegroundColor Yellow
    $Token = Read-Host "Please enter your GitHub Personal Access Token (PAT)"
    if (!$Token) { throw "Access Token is required for private repositories." }
}

# 2. CLEANUP
$TargetDir = "CamMana-main"
$ZipFile = "CamMana.zip"
if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }

# 3. Install/Check UV
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing 'uv'..." -ForegroundColor Green
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path += ";$HOME\.local\bin"
}

# 4. Install/Check Node.js
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing Node.js via winget..." -ForegroundColor Green
    winget install OpenJS.NodeJS --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# 5. Download Private Source Code
Write-Host "📥 Downloading private source code via GitHub API..." -ForegroundColor Cyan
$Headers = @{
    "Authorization" = "token $Token"
    "Accept"        = "application/vnd.github.v3.raw"
}

# Use the API URL for downloads from private repos
$RepoUrl = "https://api.github.com/repos/sangf82/CamMana/zipball/main"

try {
    Invoke-WebRequest -Uri $RepoUrl -Headers $Headers -OutFile $ZipFile
} catch {
    throw "Failed to download repository. Check your Token permissions (must have 'repo' or 'contents:read' access)."
}

Write-Host "📦 Extracting..." -ForegroundColor Cyan
Expand-Archive -Path $ZipFile -DestinationPath "." -Force
Remove-Item $ZipFile

# GitHub ZIPs create a folder like "sangf82-CamMana-Hash"
$ExtractedDir = Get-ChildItem -Directory | Where-Object { $_.Name -like "sangf82-CamMana-*" } | Select-Object -First 1
if (!$ExtractedDir) { throw "Could not find extracted directory." }
Rename-Item -Path $ExtractedDir.FullName -NewName $TargetDir
Set-Location $TargetDir

# 6. Setup Environments
Write-Host "🐍 Syncing Python..." -ForegroundColor Green
uv sync
Write-Host "⚛️ Installing Frontend..." -ForegroundColor Green
if (Test-Path "frontend") {
    Set-Location "frontend"
    npm install
    Set-Location ".."
}

# 7. Launch
Write-Host "✨ Setup complete! Launching CamMana..." -ForegroundColor Cyan
uv run python app.py
