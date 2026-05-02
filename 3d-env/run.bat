@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if "%ROVER_GPU_PREFERENCE%"=="" set "ROVER_GPU_PREFERENCE=nvidia"
set "ROVER_LAUNCH_PATH=windows-venv"
echo [GPU-LAUNCH] Preference: %ROVER_GPU_PREFERENCE%
echo [GPU-LAUNCH] Platform: windows
if /I "%ROVER_GPU_PREFERENCE%"=="nvidia" (
    nvidia-smi -L >nul 2>nul
    if errorlevel 1 (
        echo [GPU-LAUNCH] NVIDIA requested but not detected. Falling back to native OpenGL.
    ) else (
        echo [GPU-LAUNCH] NVIDIA detected. Launching Windows GPU environment.
    )
)
call :ensure_venv || goto :fail

:: ── Optimus / dual-GPU fix ──────────────────────────────────────────────────
:: Panda3D uses WGL (legacy OpenGL). NVIDIA Optimus routes WGL to the discrete
:: GPU only when the process loads a DLL that exports NvOptimusEnablement=1.
:: The registry UserGpuPreferences key only works for DirectX/DXGI apps.
::
:: If optimus_hint.dll exists we pass it via ROVER_OPTIMUS_HINT so main.py
:: loads it via ctypes before Panda3D initialises the display pipe.
::
:: To build optimus_hint.dll from source (one-time, needs MinGW or MSVC):
::   MinGW:  gcc -shared -o optimus_hint\optimus_hint.dll optimus_hint\optimus_hint.c
::   MSVC:   cl /LD optimus_hint\optimus_hint.c /Fe:optimus_hint\optimus_hint.dll
::              /link /EXPORT:NvOptimusEnablement /EXPORT:AmdPowerXpressRequestHighPerformance
::
:: Alternatively, in NVIDIA Control Panel:
::   3D Settings > Manage 3D Settings > Program Settings
::   > Add python.exe from .venv-gpu\Scripts\
::   > "OpenGL rendering GPU" = your NVIDIA card
if /I "%ROVER_GPU_PREFERENCE%"=="nvidia" (
    if exist "optimus_hint\optimus_hint.dll" (
        set "ROVER_OPTIMUS_HINT=%~dp0optimus_hint\optimus_hint.dll"
        echo [GPU-LAUNCH] Optimus hint DLL found; will load before Panda3D init.
    ) else (
        echo [GPU-LAUNCH] optimus_hint\optimus_hint.dll not found.
        echo [GPU-LAUNCH] If NVIDIA is not active, build it ^(see optimus_hint\optimus_hint.c^)
        echo [GPU-LAUNCH] or set python.exe to High Performance in NVIDIA Control Panel.
    )
)
.\.venv-gpu\Scripts\python.exe -c "import panda3d, p3dimgui, imgui_bundle, numpy, paho.mqtt.client" >nul 2>nul
if errorlevel 1 (
    echo Installing missing simulator dependencies into .venv-gpu...
    call :install_deps || goto :fail
)
.venv-gpu\Scripts\python.exe simulator\main.py
pause
goto :eof

:ensure_venv
if not defined ROVER_PYTHON set "ROVER_PYTHON=python"

if exist ".\.venv-gpu\Scripts\python.exe" (
    .\.venv-gpu\Scripts\python.exe -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo [GPU-LAUNCH] Existing .venv-gpu is stale or broken. Recreating it.
        rmdir /s /q ".venv-gpu" || exit /b 1
    ) else goto :eof
)

echo [GPU-LAUNCH] Creating Windows GPU venv with %ROVER_PYTHON%...
%ROVER_PYTHON% -c "import sys; print('[GPU-LAUNCH] Using Python ' + sys.version.split()[0] + ' at ' + sys.executable)" || exit /b 1
%ROVER_PYTHON% -m venv ".venv-gpu" || exit /b 1
".\.venv-gpu\Scripts\python.exe" -m pip install --upgrade pip || exit /b 1
goto :eof

:install_deps
".\.venv-gpu\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
".\.venv-gpu\Scripts\python.exe" -m pip install --no-deps panda3d-imgui || exit /b 1
goto :eof

:fail
echo Failed to install required dependencies for the simulator.
pause
