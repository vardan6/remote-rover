@echo off
cd /d "%~dp0"
.\.venv-gpu\Scripts\python.exe -c "import p3dimgui, imgui_bundle" >nul 2>nul
if errorlevel 1 (
    echo Installing missing GUI dependencies into .venv-gpu...
    .\.venv-gpu\Scripts\python.exe -m pip install -r requirements.txt || goto :fail
)
.venv-gpu\Scripts\python.exe simulator\main.py
pause
goto :eof

:fail
echo Failed to install required dependencies for the simulator.
pause
