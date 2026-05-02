#!/bin/bash
# Launch the rover simulator via Windows Python for GPU-accelerated rendering.
# Intended for WSL users who want to execute the Windows venv.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFERENCE="${ROVER_GPU_PREFERENCE:-nvidia}"
WIN_VENV="$DIR/.venv-gpu/Scripts/python.exe"
WIN_BAT="$DIR/run.bat"
NATIVE_VENV="$DIR/.venv/bin/python"

has_nvidia() {
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
        return 0
    fi
    if [ -x /usr/lib/wsl/lib/nvidia-smi ] && /usr/lib/wsl/lib/nvidia-smi -L >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

print_native_venv_help() {
    echo "Linux venv not found at .venv/"
    echo ""
    echo "Create it from this directory:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
}

print_missing_venv_help() {
    echo "Windows GPU venv not found at .venv-gpu/"
    echo ""
    echo "Create it from a Windows terminal (cmd or PowerShell):"
    WIN_DIR="$(wslpath -w "$DIR" 2>/dev/null || echo 'C:\path\to\3d-env')"
    echo "  cd ${WIN_DIR}"
    echo "  python -m venv .venv-gpu"
    echo "  .venv-gpu\\Scripts\\python -m pip install -r requirements.txt"
}

run_through_cmd() {
    local cmd_bin="$1"
    local win_bat_path
    win_bat_path="$(wslpath -w "$WIN_BAT" 2>/dev/null || echo '')"
    if [ -z "$win_bat_path" ]; then
        return 1
    fi
    "$cmd_bin" /c "\"$win_bat_path\"" 2>/dev/null
}

ensure_native_python() {
    local py_bin="$1"
    if ! "$py_bin" -c "import panda3d, p3dimgui, paho.mqtt.client" >/dev/null 2>&1; then
        echo "Installing missing simulator dependencies into .venv..."
        "$py_bin" -m pip install -r "$DIR/requirements.txt"
    fi
}

run_native_fallback() {
    local reason="$1"
    echo "$reason"
    echo "[GPU-LAUNCH] Falling back to native Linux / AMD-compatible OpenGL path."
    if [ ! -x "$NATIVE_VENV" ]; then
        print_native_venv_help
        exit 1
    fi
    export ROVER_LAUNCH_PATH="wsl-linux-fallback"
    ensure_native_python "$NATIVE_VENV"
    exec "$NATIVE_VENV" simulator/main.py
}

cd "$DIR"
echo "[GPU-LAUNCH] Preference: $PREFERENCE"
echo "[GPU-LAUNCH] Platform: wsl"

if [ "$PREFERENCE" = "amd" ]; then
    run_native_fallback "[GPU-LAUNCH] NVIDIA-first routing disabled by ROVER_GPU_PREFERENCE=$PREFERENCE."
fi

if ! has_nvidia; then
    run_native_fallback "[GPU-LAUNCH] NVIDIA requested but not detected in WSL."
fi

echo "[GPU-LAUNCH] NVIDIA detected; trying Windows GPU path first."

if [ ! -f "$WIN_VENV" ]; then
    print_missing_venv_help
    run_native_fallback "[GPU-LAUNCH] Windows GPU venv unavailable."
fi

# Fast path: direct Windows python via WSL interop.
if "$WIN_VENV" -c "import sys" >/dev/null 2>&1; then
    if ! "$WIN_VENV" -c "import panda3d, p3dimgui, imgui_bundle, numpy, paho.mqtt.client" >/dev/null 2>&1; then
        echo "Installing missing simulator dependencies into .venv-gpu..."
        WIN_REQ="$(wslpath -w "$DIR/requirements.txt" 2>/dev/null || echo 'requirements.txt')"
        "$WIN_VENV" -m pip install -r "$WIN_REQ"
        "$WIN_VENV" -m pip install --no-deps panda3d-imgui
    fi
    export ROVER_LAUNCH_PATH="wsl-windows-venv"
    exec "$WIN_VENV" simulator/main.py
fi

# Fallback path: delegate to run.bat through cmd.exe (if callable from this shell).
if command -v cmd.exe >/dev/null 2>&1; then
    echo "Direct Windows python launch failed; trying run.bat via cmd.exe..."
    if run_through_cmd "cmd.exe"; then
        exit 0
    fi
fi

if [ -x /mnt/c/Windows/System32/cmd.exe ]; then
    echo "Direct Windows python launch failed; trying run.bat via cmd.exe..."
    if run_through_cmd "/mnt/c/Windows/System32/cmd.exe"; then
        exit 0
    fi
fi

run_native_fallback "$(cat <<'EOF'
[GPU-LAUNCH] Cannot execute Windows binaries from this WSL shell.
[GPU-LAUNCH] Error type is typically 'Exec format error' when WSL interop is unavailable.
[GPU-LAUNCH] Fix options:
[GPU-LAUNCH]   1) Re-enable WSL interop, then restart WSL:
[GPU-LAUNCH]      - /etc/wsl.conf should include:
[GPU-LAUNCH]          [interop]
[GPU-LAUNCH]          enabled=true
[GPU-LAUNCH]          appendWindowsPath=true
[GPU-LAUNCH]      - In Windows PowerShell or CMD:
[GPU-LAUNCH]          wsl --shutdown
[GPU-LAUNCH]   2) Start the simulator from Windows directly with run.bat
EOF
)"
