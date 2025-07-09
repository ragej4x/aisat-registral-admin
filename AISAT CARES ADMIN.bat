@echo off

python --version >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python is already installed. Skipping installation.
    pip install -r requirements.txt
    python main.py
    goto end
) else (
    echo Python not found. Installing...
    start /wait "" "python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1
)


:end
echo Done.
pause
