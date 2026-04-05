#!/bin/bash
# Launch the rover simulator via Windows Python for GPU-accelerated rendering.
# Use this from WSL when GPU passthrough (/dev/dri) isn't available.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv-gpu/Scripts/python.exe"

if [ ! -f "$VENV" ]; then
    echo "Windows GPU venv not found at .venv-gpu/"
    echo ""
    echo "Create it from a Windows terminal (cmd or PowerShell):"
    WIN_DIR="$(wslpath -w "$DIR" 2>/dev/null || echo 'C:\path\to\3d-env')"
    echo "  cd ${WIN_DIR}"
    echo "  python -m venv .venv-gpu"
    echo "  .venv-gpu\\Scripts\\python -m pip install -r requirements.txt"
    exit 1
fi

cd "$DIR"

if ! "$VENV" -c "import p3dimgui, imgui_bundle" >/dev/null 2>&1; then
    echo "Installing missing GUI dependencies into .venv-gpu..."
    WIN_REQ="$(wslpath -w "$DIR/requirements.txt" 2>/dev/null || echo 'requirements.txt')"
    "$VENV" -m pip install -r "$WIN_REQ"
fi

exec "$VENV" simulator/main.py
