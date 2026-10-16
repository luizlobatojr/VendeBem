@echo off
cd /d "%~dp0"
if errorlevel 1 (
    echo Nao foi possivel abrir a pasta do programa.
    pause
    exit /b 1
)
py "%~dp0app.py"
if errorlevel 1 pause
