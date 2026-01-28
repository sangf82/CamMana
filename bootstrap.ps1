$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
$Version = "v2.1.0"

# --- HELPER FUNCTIONS ---
function Write-Step ([string]$msg) {
    Write-Host "`n🚀 $msg" -ForegroundColor Cyan
}

function Write-Success ([string]$msg) {
    Write-Host "✅ $msg" -ForegroundColor Green
}

function Write-Warning ([string]$msg) {
    Write-Host "⚠️ $msg" -ForegroundColor Yellow
}

function Write-Error-Custom ([string]$msg) {
    Write-Host "❌ $msg" -ForegroundColor Red
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $PossiblePaths = @("$HOME\.local\bin", "$env:APPDATA\uv\bin", "$env:ProgramFiles\nodejs", "$env:ProgramFiles\Git\cmd")
    foreach ($p in $PossiblePaths) {
        if (Test-Path $p) { if ($env:Path -notlike "*$p*") { $env:Path += ";$p" } }
    }
}

# --- 0. KIỂM TRA QUYỀN CHẠY SCRIPT (Execution Policy) ---
$Policy = Get-ExecutionPolicy
if ($Policy -eq "Restricted" -or $Policy -eq "Undefined") {
    Write-Host "****************************************************" -ForegroundColor Yellow
    Write-Host "*                                                  *" -ForegroundColor Yellow
    Write-Host "* 🔥 CẦN CẤP QUYỀN CHẠY SCRIPT ĐỂ TIẾP TỤC         *" -ForegroundColor Yellow
    Write-Host "*                                                  *" -ForegroundColor Yellow
    Write-Host "****************************************************" -ForegroundColor Yellow
    Write-Host "`nHiện tại máy bạn đang chặn chạy script PowerShell ($Policy)." -ForegroundColor White
    $Choice = Read-Host "Bạn có muốn cấp quyền (RemoteSigned) để cài đặt ứng dụng không? (Y/N)"
    if ($Choice -eq "Y" -or $Choice -eq "y") {
        try {
            # Thiết lập cho CurrentUser để không cần quyền Admin cao nhất
            Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
            Write-Success "Đã cập nhật ExecutionPolicy thành RemoteSigned."
        } catch {
            Write-Error-Custom "Không thể thay đổi quyền. Vui lòng chạy PowerShell với quyền 'Run as Administrator'."
            exit 1
        }
    } else {
        Write-Warning "Đã từ chối cấp quyền. Quá trình cài đặt Frontend có thể sẽ thất bại."
    }
}

Write-Host @"
****************************************************
*                                                  *
*       CAMMANA - HỆ THỐNG QUẢN LÝ CAMERA          *
*           BOOTSTRAP & AUTO-INSTALLER             *
*                Phiên bản: $Version               *
*                                                  *
****************************************************
"@ -ForegroundColor Magenta

# 1. CHUẨN BỊ MÔI TRƯỜNG & DỌN DẸP
Write-Step "Đang khởi tạo môi trường làm việc..."
if ($PWD.Path -like "*system32*") { Set-Location $HOME }

# Logic xác định thư mục dự án thông minh
$ProjectName = "CamMana"
if (Test-Path "pyproject.toml") {
    $TargetDir = "."
} elseif (Test-Path $ProjectName) {
    Set-Location $ProjectName
    if (Test-Path "pyproject.toml") { $TargetDir = "." } else { $TargetDir = $ProjectName }
    Set-Location ".."
} else {
    $TargetDir = $ProjectName
}

# Dọn dẹp tệp tin ZIP cũ
Get-ChildItem -Path "." -Filter "CamMana*.zip" -File | Remove-Item -Force -ErrorAction SilentlyContinue

# 2. CÀI ĐẶT CÔNG CỤ (uv, Git, Node.js)
Write-Step "Kiểm tra và cài đặt công cụ hệ thống..."
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
    }
}
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install OpenJS.NodeJS --source winget --accept-source-agreements --accept-package-agreements
    }
}
Refresh-Path

# 4. TẢI MÃ NGUỒN
Write-Step "Đang tải mã nguồn ứng dụng..."
$RepoUrl = "https://github.com/sangf82/CamMana.git"

if ($TargetDir -ne ".") {
    if (Test-Path $TargetDir) {
        Write-Warning "Thư mục $TargetDir đã tồn tại. Đang dọn dẹp..."
        Remove-Item -Recurse -Force $TargetDir -ErrorAction SilentlyContinue
    }
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git clone --depth 1 $RepoUrl $TargetDir
    } else {
        Write-Warning "Không có Git, tải ZIP..."
        $ZipUrl = "https://github.com/sangf82/CamMana/archive/refs/heads/master.zip"
        Invoke-WebRequest -Uri $ZipUrl -OutFile "CamMana.zip"
        Expand-Archive -Path "CamMana.zip" -DestinationPath "." -Force
        $ExtDir = Get-ChildItem -Directory | Where-Object { $_.Name -like "CamMana-*" } | Select-Object -First 1
        if ($ExtDir) { Rename-Item -Path $ExtDir.FullName -NewName $TargetDir }
        Remove-Item "CamMana.zip"
    }
    Set-Location $TargetDir
}

# 5. THIẾT LẬP MÔI TRƯỜNG PYTHON
Write-Step "Đang cấu hình Python (uv sync)..."
if (!(Test-Path ".env") -and (Test-Path ".env.example")) { Copy-Item ".env.example" ".env" }
& uv sync
Write-Success "Môi trường Python đã sẵn sàng."

# 6. THIẾT LẬP FRONTEND
if (Test-Path "frontend") {
    Write-Step "Đang cấu hình Frontend..."
    if (Test-Path "frontend/out") {
        Write-Success "Đã có bản build sẵn."
    } else {
        try {
            Set-Location "frontend"
            # Cách gọi npm an toàn nhất để tránh lỗi Execution Policy
            Write-Host "📦 Cài đặt thư viện..." -ForegroundColor Gray
            cmd /c "npm install --no-audit --no-fund"
            
            Write-Host "🏗️ Đang biên dịch frontend..." -ForegroundColor Gray
            cmd /c "npm run build"
            
            Set-Location ".."
            Write-Success "Frontend đã hoàn tất."
        } catch {
            Write-Warning "Lỗi build Frontend: $_"
            Set-Location ".."
        }
    }
}

# 7. CHẠY ỨNG DỤNG
Write-Step "Khởi động CamMana (Production Mode)..."
& uv run python app.py --prod
