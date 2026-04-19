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
if not exist ".\.venv-gpu\Scripts\python.exe" goto :missing_venv

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
.\.venv-gpu\Scripts\python.exe -c "import panda3d, p3dimgui, imgui_bundle, paho.mqtt.client" >nul 2>nul
if errorlevel 1 (
    echo Installing missing simulator dependencies into .venv-gpu...
    .\.venv-gpu\Scripts\python.exe -m pip install -r requirements.txt || goto :fail
)
.venv-gpu\Scripts\python.exe simulator\main.py
pause
goto :eof

:missing_venv
echo Windows GPU venv not found at .venv-gpu\
echo.
echo Create it from this directory in Command Prompt or PowerShell:
echo   python -m venv .venv-gpu
echo   .venv-gpu\Scripts\python -m pip install -r requirements.txt
pause
goto :eof

:fail
echo Failed to install required dependencies for the simulator.
pause
