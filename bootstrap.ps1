$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
$Version = "v2.3.0"

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
    Write-Host "`nMáy bạn đang chặn chạy script ($Policy)." -ForegroundColor White
    $Choice = Read-Host "Bạn có muốn cấp quyền (RemoteSigned) để cài đặt không? (Y/N)"
    if ($Choice -eq "Y" -or $Choice -eq "y") {
        try {
            # Thiết lập cho CurrentUser để không cần quyền Admin cao nhất
            Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
            Write-Success "Đã cập nhật ExecutionPolicy thành RemoteSigned."
        } catch {
            Write-Error-Custom "Lỗi: Vui lòng chạy PowerShell với quyền Admin để sửa lỗi này."
            exit 1
        }
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

# 1. CHUẨN BỊ MÔI TRƯỜNG & KIỂM TRA QUYỀN GHI
Write-Step "Đang khởi tạo môi trường làm việc..."

# Kiểm tra quyền ghi vào thư mục hiện tại
$TempFile = "test_perm_$($PID).tmp"
try {
    New-Item -Path "." -Name $TempFile -ItemType "file" -ErrorAction Stop | Out-Null
    Remove-Item -Path $TempFile -Force
} catch {
    Write-Error-Custom "Lỗi: Bạn không có quyền ghi vào thư mục này: $($PWD.Path)"
    Write-Host "Hãy thử chạy lại ở một thư mục khác (ví dụ: Desktop)." -ForegroundColor Gray
    exit 1
}

# Ngăn chặn lồng thư mục CamMana/CamMana/...
if ($PWD.Path -match "CamMana\\CamMana") {
    Write-Warning "Phát hiện thư mục đang bị lồng nhau. Đang cố gắng nhảy về gốc..."
    while ($PWD.Path -match "CamMana\\CamMana") {
        Set-Location ".."
    }
}

$ProjectName = "CamMana"
if (Test-Path "pyproject.toml") {
    $TargetDir = "."
    Write-Success "Đã xác định gốc dự án tại: $($PWD.Path)"
} else {
    $TargetDir = $ProjectName
}

# Dọn dẹp tệp tin ZIP cũ
Get-ChildItem -Path "." -Filter "CamMana*.zip" -File | Remove-Item -Force -ErrorAction SilentlyContinue

# 2. CÀI ĐẶT CÔNG CỤ (uv, Git, Node.js)
Write-Step "Kiểm tra công cụ hệ thống..."
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
Write-Step "Đang chuẩn bị mã nguồn..."
$RepoUrl = "https://github.com/sangf82/CamMana.git"

if ($TargetDir -ne ".") {
    if (Test-Path $TargetDir) {
        Write-Warning "Dọn dẹp thư mục cũ..."
        Remove-Item -Recurse -Force $TargetDir -ErrorAction SilentlyContinue
    }
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git clone --depth 1 $RepoUrl $TargetDir
    } else {
        Write-Warning "Không có Git, tải ZIP..."
        Invoke-WebRequest -Uri "https://github.com/sangf82/CamMana/archive/refs/heads/master.zip" -OutFile "src.zip"
        Expand-Archive -Path "src.zip" -DestinationPath "." -Force
        $ExtDir = Get-ChildItem -Directory | Where-Object { $_.Name -like "CamMana-*" } | Select-Object -First 1
        if ($ExtDir) { Rename-Item -Path $ExtDir.FullName -NewName $TargetDir }
        Remove-Item "src.zip"
    }
    Set-Location $TargetDir
}

# 5. THIẾT LẬP PYTHON
Write-Step "Đang đồng bộ môi trường Python..."
if (!(Test-Path ".env") -and (Test-Path ".env.example")) { Copy-Item ".env.example" ".env" }
& uv sync
Write-Success "Python đã sẵn sàng."

# 6. THIẾT LẬP FRONTEND (BUILD PROD)
if (Test-Path "frontend") {
    Write-Step "Đang đóng gói Frontend..."
    try {
        Set-Location "frontend"
        if (!(Test-Path "out")) {
            Write-Host "📦 Đang cài đặt và build (lần đầu)..." -ForegroundColor Gray
            cmd /c "npm install --no-audit --no-fund"
            cmd /c "npm run build"
            Write-Success "Đóng gói Frontend thành công."
        } else {
            Write-Success "Đã có sẵn bản build."
        }
        Set-Location ".."
    } catch {
        Write-Warning "Lỗi build Frontend: $_"
        Set-Location ".."
    }
}

# 7. CHẠY ỨNG DỤNG
Write-Step "Khởi động CamMana ($($Version))..."
& uv run python app.py --prod
