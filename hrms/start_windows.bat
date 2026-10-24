@echo off
setlocal
cd /d "%~dp0"
title Golden Marketing HR Management
where python >nul 2>&1
if errorlevel 1 (
 echo Python was not found. Install Python 3.12 or newer and enable Add Python to PATH.
 pause
 exit /b 1
)
if not exist ".venv-hr\Scripts\python.exe" (
 python -m venv .venv-hr
 if errorlevel 1 goto failed
)
.venv-hr\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv-hr\Scripts\python.exe launch.py
pause
exit /b
:failed
echo Setup could not finish. Read the error above and share it for help.
pause
exit /b 1
