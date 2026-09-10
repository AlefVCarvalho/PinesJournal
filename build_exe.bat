@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   Pine's Journal - Build Windows
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado.
    echo Instale Python 3.11 ou superior e marque Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Pine's Journal.spec" del /q "Pine's Journal.spec"

pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "Pine's Journal" ^
  --icon "app_icon.ico" ^
  --add-data "app_icon.ico;." ^
  --add-data "assets;assets" ^
  task_app.py
if errorlevel 1 goto :error

if exist "dist\Pine's Journal.exe" (
    echo.
    echo Build concluido:
    echo %CD%\dist\Pine's Journal.exe
    explorer "%CD%\dist"
    pause
    exit /b 0
)

:error
echo.
echo O build falhou. Verifique as mensagens acima.
pause
exit /b 1
