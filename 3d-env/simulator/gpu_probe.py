import json
import os
import shutil
import subprocess
import sys


def normalize_preference(value=None):
    pref = str(value or os.environ.get("ROVER_GPU_PREFERENCE", "nvidia")).strip().lower()
    if pref not in {"nvidia", "amd", "auto"}:
        return "nvidia"
    return pref


def is_wsl():
    try:
        with open("/proc/version", "r", encoding="utf-8") as handle:
            return "microsoft" in handle.read().lower()
    except (FileNotFoundError, OSError):
        return False


def _run_command(args):
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr or "").strip()


def _classify_text(*values):
    text = " ".join(v for v in values if v).lower()
    if not text:
        return "unknown"
    if any(token in text for token in ("llvmpipe", "swrast", "softpipe", "software rasterizer")):
        return "software"
    if "nvidia" in text:
        return "nvidia"
    if any(token in text for token in ("amd", "radeon", "advanced micro devices", "ati")):
        return "amd"
    if "intel" in text:
        return "intel"
    return "unknown"


def _detect_with_nvidia_smi():
    candidates = []
    if shutil.which("nvidia-smi"):
        candidates.append("nvidia-smi")
    if os.path.exists("/usr/lib/wsl/lib/nvidia-smi"):
        candidates.append("/usr/lib/wsl/lib/nvidia-smi")
    for candidate in candidates:
        output = _run_command([candidate, "-L"])
        if output:
            return True, candidate, output.splitlines()[0]
    return False, None, None


def _detect_glxinfo():
    cmd = shutil.which("glxinfo")
    if not cmd:
        return {}
    output = _run_command([cmd, "-B"])
    if not output:
        return {}
    renderer = None
    vendor = None
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "opengl renderer string":
            renderer = value
        elif key == "opengl vendor string":
            vendor = value
    return {
        "renderer": renderer,
        "vendor": vendor,
        "classification": _classify_text(renderer, vendor),
    }


def _detect_lspci():
    cmd = shutil.which("lspci")
    if not cmd:
        return {}
    output = _run_command([cmd])
    if not output:
        return {}
    lines = []
    classifications = []
    for line in output.splitlines():
        lowered = line.lower()
        if not any(token in lowered for token in ("vga", "3d controller", "display controller")):
            continue
        lines.append(line.strip())
        classifications.append(_classify_text(line))
    merged = "unknown"
    if "nvidia" in classifications:
        merged = "nvidia"
    elif "amd" in classifications:
        merged = "amd"
    elif "intel" in classifications:
        merged = "intel"
    return {
        "lines": lines,
        "classification": merged,
    }


def detect_startup_environment(preference=None):
    pref = normalize_preference(preference)
    wsl = is_wsl()
    platform_name = "windows" if os.name == "nt" else ("wsl" if wsl else "linux")
    nvidia_found, nvidia_probe, nvidia_summary = _detect_with_nvidia_smi()
    gl_info = _detect_glxinfo()
    pci_info = _detect_lspci()

    fallback_vendor = "unknown"
    for candidate in (gl_info.get("classification"), pci_info.get("classification")):
        if candidate in {"amd", "intel", "nvidia", "software"}:
            fallback_vendor = candidate
            break

    amd_found = fallback_vendor == "amd"
    software_only = gl_info.get("classification") == "software"

    if pref == "nvidia":
        selected = "nvidia" if nvidia_found else fallback_vendor
    elif pref == "amd":
        selected = "amd" if amd_found else ("nvidia" if nvidia_found else fallback_vendor)
    else:
        selected = "nvidia" if nvidia_found else fallback_vendor

    if selected not in {"nvidia", "amd", "intel", "software"}:
        selected = "unknown"

    return {
        "preference": pref,
        "platform": platform_name,
        "launch_path": os.environ.get("ROVER_LAUNCH_PATH", "direct"),
        "is_wsl": wsl,
        "nvidia_available": nvidia_found,
        "nvidia_probe": nvidia_probe,
        "nvidia_summary": nvidia_summary,
        "amd_available": amd_found,
        "software_only": software_only,
        "gl_renderer_hint": gl_info.get("renderer"),
        "gl_vendor_hint": gl_info.get("vendor"),
        "gl_classification": gl_info.get("classification", "unknown"),
        "pci_classification": pci_info.get("classification", "unknown"),
        "selected_vendor": selected,
        "threaded_rendering_supported": os.path.exists("/dev/dri/renderD128") if wsl else True,
    }


def classify_runtime_driver(renderer, vendor):
    return _classify_text(renderer, vendor)


def format_preflight_lines(info):
    lines = [
        f"[GPU-PREFLIGHT] Launch path: {info['launch_path']}",
        f"[GPU-PREFLIGHT] Platform: {info['platform']}",
        f"[GPU-PREFLIGHT] Preference: {info['preference']}",
    ]
    if info["nvidia_available"]:
        details = f" via {info['nvidia_probe']}" if info.get("nvidia_probe") else ""
        lines.append(f"[GPU-PREFLIGHT] NVIDIA detected{details}.")
    else:
        lines.append("[GPU-PREFLIGHT] NVIDIA not detected.")

    if info["selected_vendor"] == "nvidia":
        if info["preference"] == "nvidia":
            lines.append("[GPU-PREFLIGHT] NVIDIA path requested and available.")
        else:
            lines.append("[GPU-PREFLIGHT] NVIDIA is available and selected as the preferred path.")
    elif info["selected_vendor"] in {"amd", "intel"}:
        lines.append(f"[GPU-PREFLIGHT] Falling back to {info['selected_vendor'].upper()} / native OpenGL.")
    elif info["selected_vendor"] == "software":
        lines.append("[GPU-PREFLIGHT] Only software rendering is visible to the process.")
    else:
        lines.append("[GPU-PREFLIGHT] Hardware probe inconclusive; runtime renderer will decide.")

    renderer = info.get("gl_renderer_hint")
    vendor = info.get("gl_vendor_hint")
    if renderer:
        lines.append(f"[GPU-PREFLIGHT] OpenGL hint: {renderer}")
    if vendor:
        lines.append(f"[GPU-PREFLIGHT] OpenGL vendor hint: {vendor}")
    return lines


def format_runtime_lines(renderer, vendor, preference=None):
    runtime = classify_runtime_driver(renderer, vendor)
    pref = normalize_preference(preference)
    on_windows = os.name == "nt"
    lines = [
        f"[GPU] Renderer: {renderer}",
        f"[GPU] Vendor:   {vendor}",
        f"[GPU] Active class: {runtime}",
    ]
    if pref == "nvidia" and runtime != "nvidia":
        if runtime in {"amd", "intel"}:
            lines.append(f"[GPU] NVIDIA requested but not active; using {runtime.upper()} fallback.")
            if on_windows:
                lines.append("[GPU] Optimus dual-GPU: WGL was routed to the integrated GPU.")
                lines.append("[GPU] Fix A: build optimus_hint\\optimus_hint.dll (see optimus_hint\\optimus_hint.c)")
                lines.append("[GPU]         gcc -shared -o optimus_hint\\optimus_hint.dll optimus_hint\\optimus_hint.c")
                lines.append("[GPU] Fix B: NVIDIA Control Panel > Manage 3D Settings > Program Settings")
                lines.append("[GPU]         > add .venv-gpu\\Scripts\\python.exe")
                lines.append("[GPU]         > OpenGL rendering GPU = your NVIDIA card")
        elif runtime == "software":
            lines.append("[GPU] NVIDIA requested but not active; using software fallback.")
        else:
            lines.append("[GPU] NVIDIA requested but runtime vendor is unknown.")
    elif pref == "amd" and runtime != "amd":
        if runtime == "nvidia":
            lines.append("[GPU] AMD requested but NVIDIA is the active renderer.")
        elif runtime == "software":
            lines.append("[GPU] AMD requested but only software rendering is active.")
    return lines, runtime == "software", runtime


def main(argv=None):
    argv = argv or sys.argv[1:]
    info = detect_startup_environment(normalize_preference())
    if "--json" in argv:
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    for line in format_preflight_lines(info):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
