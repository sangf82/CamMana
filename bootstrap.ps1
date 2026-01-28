# CamMana Windows Bootstrap Script
# Mục tiêu: Thiết lập môi trường từ con số 0 và chạy ứng dụng CamMana.
# Cách dùng: Mở PowerShell và dán:
# irm https://raw.githubusercontent.com/sangf82/CamMana/master/bootstrap.ps1 | iex

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

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
    $PossiblePaths = @(
        "$HOME\.local\bin",
        "$env:APPDATA\uv\bin",
        "$env:ProgramFiles\nodejs",
        "$env:ProgramFiles\Git\cmd"
    )
    foreach ($p in $PossiblePaths) {
        if (Test-Path $p) {
            if ($env:Path -notlike "*$p*") { $env:Path += ";$p" }
        }
    }
}

Write-Host @"
****************************************************
*                                                  *
*       CAMMANA - HỆ THỐNG QUẢN LÝ CAMERA          *
*           BOOTSTRAP & AUTO-INSTALLER             *
*                                                  *
****************************************************
"@ -ForegroundColor Magenta

# 1. CHUẨN BỊ MÔI TRƯỜNG & DỌN DẸP
Write-Step "Đang khởi tạo môi trường làm việc..."

# Đảm bảo chạy ở thư mục an toàn (Tránh chạy trong system32)
if ($PWD.Path -like "*system32*") {
    Set-Location $HOME
}
Write-Host "📂 Thư mục làm việc: $($PWD.Path)" -ForegroundColor Gray

# Dọn dẹp tệp tin ZIP và thư mục cũ sót lại từ các lần chạy trước
$OldFiles = Get-ChildItem -Path "." -Filter "CamMana*" -File
$OldDirs = Get-ChildItem -Path "." -Filter "CamMana-*" -Directory

if ($OldFiles -or $OldDirs) {
    Write-Host "🧹 Đang dọn dẹp các tệp tin/thư mục cũ..." -ForegroundColor Gray
    $OldFiles | Remove-Item -Force -ErrorAction SilentlyContinue
    $OldDirs | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# KIỂM TRA QUYỀN ADMIN (Tùy chọn nhưng khuyến khích cho winget)
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Ứng dụng đang chạy không có quyền Admin. Một số tác vụ cài đặt có thể yêu cầu quyền này."
}

# 2. CÀI ĐẶT CÁC CÔNG CỤ CẦN THIẾT (uv, Git, Node.js)
Write-Step "Kiểm tra và cài đặt các công cụ hệ thống..."

# Cài đặt uv
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Đang cài đặt uv..." -ForegroundColor Gray
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

# Cài đặt Git (Bắt buộc để clone repo)
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git chưa có. Đang cài đặt Git qua winget..." -ForegroundColor Gray
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
            Write-Success "Đã cài đặt Git."
        } catch {
            Write-Error-Custom "Không thể cài đặt Git qua winget."
        }
    } else {
        Write-Warning "Không tìm thấy winget để cài đặt Git."
    }
}

# Cài đặt Node.js
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Đang cài đặt Node.js qua winget..." -ForegroundColor Gray
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            winget install OpenJS.NodeJS --source winget --accept-source-agreements --accept-package-agreements
            Write-Success "Đã cài đặt Node.js."
        } catch {
            Write-Warning "Lỗi cài đặt Node.js."
        }
    }
}

# Cập nhật lại Path để nhận diện các công cụ vừa cài
Refresh-Path

# Kiểm tra lại Git sau khi cài đặt
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "Git vẫn chưa khả dụng. Sẽ thử dùng phương pháp tải ZIP nếu cần."
} else {
    Write-Success "Các công cụ hệ thống đã sẵn sàng."
}

# 4. TẢI MÃ NGUỒN
Write-Step "Đang tải mã nguồn ứng dụng..."
$TargetDir = "CamMana"
$RepoUrl = "https://github.com/sangf82/CamMana.git"

if (Test-Path $TargetDir) {
    Write-Warning "Thư mục $TargetDir đã tồn tại. Đang dọn dẹp..."
    try {
        Remove-Item -Recurse -Force $TargetDir
    } catch {
        $TargetDir = "$TargetDir-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    }
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "Đang thực hiện Git Clone từ: $RepoUrl" -ForegroundColor Gray
    git clone --depth 1 $RepoUrl $TargetDir
} else {
    Write-Warning "Không tìm thấy Git. Đang dùng phương thức tải ZIP dự phòng..."
    $BaseUrl = $RepoUrl.Replace(".git", "")
    $ZipFile = "CamMana.zip"
    $ZipUrl = "$BaseUrl/archive/refs/heads/master.zip"
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile
    Expand-Archive -Path $ZipFile -DestinationPath "." -Force
    $ExtractedDir = Get-ChildItem -Directory | Where-Object { $_.Name -like "CamMana-*" } | Select-Object -First 1
    if ($ExtractedDir) { Rename-Item -Path $ExtractedDir.FullName -NewName $TargetDir }
    Remove-Item $ZipFile
}

if (!(Test-Path $TargetDir)) {
    Write-Error-Custom "Không thể tải mã nguồn."
    exit 1
}
Set-Location $TargetDir

# 5. THIẾT LẬP MÔI TRƯỜNG PYTHON & CẤU HÌNH
Write-Step "Đang cấu hình môi trường Python (uv sync)..."
try {
    # Tạo file .env nếu chưa có (Rất quan trọng cho Backend)
    if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
        Write-Host "📝 Tạo file .env từ mẫu..." -ForegroundColor Gray
        Copy-Item ".env.example" ".env"
    }

    & uv sync
    Write-Success "Cấu hình Python và môi trường thành công."
} catch {
    Write-Error-Custom "Lỗi khi đồng bộ môi trường: $_"
    exit 1
}

# 6. THIẾT LẬP FRONTEND
if (Test-Path "frontend") {
    Write-Step "Đang cài đặt và đóng gói Frontend (Production)..."
    try {
        Set-Location "frontend"
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            Write-Host "📦 Cài đặt thư viện..." -ForegroundColor Gray
            & npm install --no-audit --no-fund
            
            Write-Host "🏗️ Đang biên dịch frontend (Build)..." -ForegroundColor Gray
            & npm run build
            
            Set-Location ".."
            Write-Success "Frontend đã được đóng gói sẵn sàng."
        } else {
            Write-Warning "Không tìm thấy 'npm', bỏ qua bước build frontend."
            Set-Location ".."
        }
    } catch {
        Write-Warning "Lỗi khi build Frontend: $_"
        Set-Location ".."
    }
}

# 7. CHẠY ỨNG DỤNG
Write-Step "Hoàn tất! Đang khởi động CamMana (Production Mode)..."
Write-Host "----------------------------------------------------" -ForegroundColor Gray
& uv run python app.py --prod
