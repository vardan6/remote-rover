@echo off
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
