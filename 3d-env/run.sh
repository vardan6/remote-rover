#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFERENCE="${ROVER_GPU_PREFERENCE:-nvidia}"
NATIVE_VENV="$DIR/.venv/bin/python"

is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null
}

print_native_venv_help() {
    echo "Linux venv not found at .venv/"
    echo ""
    echo "Create it from this directory:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
}

ensure_native_python() {
    local py_bin="$1"
    if ! "$py_bin" -c "import panda3d, p3dimgui, numpy, paho.mqtt.client" >/dev/null 2>&1; then
        echo "Installing missing simulator dependencies into the Linux environment..."
        "$py_bin" -m pip install -r "$DIR/requirements.txt"
        "$py_bin" -m pip install --no-deps panda3d-imgui
    fi
}

run_native() {
    if [ ! -x "$NATIVE_VENV" ]; then
        print_native_venv_help
        exit 1
    fi
    export ROVER_LAUNCH_PATH="linux-native"
    ensure_native_python "$NATIVE_VENV"
    exec "$NATIVE_VENV" "$DIR/simulator/main.py"
}

cd "$DIR"

if is_wsl; then
    export ROVER_GPU_PREFERENCE="$PREFERENCE"
    exec "$DIR/run_gpu.sh"
fi

echo "[GPU-LAUNCH] Preference: $PREFERENCE"
echo "[GPU-LAUNCH] Platform: linux"
run_native
