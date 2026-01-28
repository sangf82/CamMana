#!/bin/bash

# CamMana Remote Bootstrap Script
# Usage (Bash): curl -sSL https://gist.githubusercontent.com/sangf82/331662163264d794bfc4954c69e78490/raw/scripts.sh | bash
# Usage (PowerShell): irm https://gist.githubusercontent.com/sangf82/331662163264d794bfc4954c69e78490/raw/bootstrap.ps1 | iex

echo "🚀 Starting CamMana Remote Bootstrap..."

# 1. CLEANUP (Optional but requested: Start fresh)
TARGET_DIR="CamMana"
if [ -d "$TARGET_DIR" ]; then
    echo "🧹 Removing old version of $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
fi

# 2. Dependency Check: UV
if ! command -v uv &> /dev/null; then
    echo "📦 Installing 'uv'..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        export PATH="$HOME/.local/bin:$PATH"
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
        [ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
    fi
fi

# 3. Dependency Check: Node.js
if ! command -v node &> /dev/null; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "📦 Attempting to install Node.js via winget..."
        winget install OpenJS.NodeJS --accept-source-agreements --accept-package-agreements || echo "⚠️ Please install Node.js manually: https://nodejs.org/"
    fi
fi

# 4. Clone Repository
REPO_URL="https://github.com/sangf82/CamMana.git"
echo "📥 Cloning fresh repository: $REPO_URL..."
git clone --depth 1 "$REPO_URL"
cd "$TARGET_DIR"

# 5. Setup Python
echo "🐍 Syncing Python environment..."
uv sync

# 6. Setup Frontend
echo "⚛️ Installing Frontend dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    npm install
    cd ..
fi

# 7. Launch
echo "✨ Setup complete. Launching CamMana..."
uv run python app.py
