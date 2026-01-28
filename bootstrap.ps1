# CamMana Windows Bootstrap Script
# Usage: irm <RAW_GIST_URL> | iex

$ErrorActionPreference = "Continue"

Write-Host "🚀 Starting CamMana Remote Bootstrap..." -ForegroundColor Cyan

# 1. CLEANUP
$TargetDir = "CamMana"
if (Test-Path $TargetDir) {
    Write-Host "🧹 Removing old version of $TargetDir..." -ForegroundColor Yellow
    try {
        Remove-Item -Recurse -Force $TargetDir
    } catch {
        Write-Host "⚠️ Could not remove $TargetDir completely. It might be in use." -ForegroundColor Red
    }
}

# 2. Dependency Check: UV
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing 'uv'..." -ForegroundColor Green
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path += ";$HOME\.local\bin"
    # Try to find the actual path if the above guess is wrong
    $uvPath = Join-Path $HOME ".local/bin"
    if (Test-Path $uvPath) { $env:Path += ";$uvPath" }
}

# 3. Dependency Check: Node.js
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Attempting to install Node.js via winget..." -ForegroundColor Green
    winget install OpenJS.NodeJS --source winget --accept-source-agreements --accept-package-agreements
    # Update Path for current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# 4. Get Source Code
$RepoUrl = "https://github.com/sangf82/CamMana"
$ZipUrl = "$RepoUrl/archive/refs/heads/master.zip"
$ZipFile = "CamMana.zip"

Write-Host "📥 Getting source code..." -ForegroundColor Cyan

if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "📡 Cloning via Git..." -ForegroundColor Gray
    git clone --depth 1 "$RepoUrl.git"
} else {
    Write-Host "📦 Git not found. Downloading ZIP..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile
    Expand-Archive -Path $ZipFile -DestinationPath "." -Force
    
    # GitHub ZIPs extract to "RepoName-BranchName" (e.g. CamMana-master)
    $ExtractedDir = Get-ChildItem -Directory | Where-Object { $_.Name -like "CamMana-*" } | Select-Object -First 1
    if ($ExtractedDir) {
        Rename-Item -Path $ExtractedDir.FullName -NewName $TargetDir
    }
    Remove-Item $ZipFile
}

if (!(Test-Path $TargetDir)) {
    Write-Host "❌ Failed to obtain source code." -ForegroundColor Red
    exit
}
Set-Location $TargetDir

# 5. Setup Python
Write-Host "🐍 Syncing Python environment..." -ForegroundColor Green
# Ensure uv is in path for this session if just installed
$env:Path += ";$HOME\.local\bin"
uv sync

# 6. Setup Frontend
if (Test-Path "frontend") {
    Write-Host "⚛️ Installing Frontend dependencies..." -ForegroundColor Green
    Set-Location "frontend"
    # Ensure npm is available in this session
    npm install
    Set-Location ".."
}

# 7. Launch
Write-Host "✨ Setup complete. Launching CamMana..." -ForegroundColor Cyan
uv run python app.py
