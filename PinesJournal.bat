@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="setup" goto :setup
if /I "%~1"=="run" goto :run
if /I "%~1"=="build" goto :build
if not "%~1"=="" goto :usage

echo ========================================
echo   Pine's Journal
 echo ========================================
echo.
echo [1] Preparar ambiente
 echo [2] Executar aplicativo
 echo [3] Gerar EXE
 echo [4] Sair
 echo.
choice /C 1234 /N /M "Escolha: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto :build
if errorlevel 2 goto :run
if errorlevel 1 goto :setup

:check_python
where py >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado.
    echo Instale Python 3.11 ou superior e marque Add Python to PATH.
    exit /b 1
)
exit /b 0

:ensure_venv
call :check_python
if errorlevel 1 exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 exit /b 1
)
exit /b 0

:setup
call :ensure_venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error
echo.
echo Ambiente pronto.
pause
exit /b 0

:run
call :ensure_venv
if errorlevel 1 goto :error
if not exist ".venv\Scripts\pythonw.exe" goto :error
start "" ".venv\Scripts\pythonw.exe" task_app.py
exit /b 0

:build
call :ensure_venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

if not exist "app_icon.ico" (
    echo app_icon.ico nao foi encontrado.
    goto :error
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Pine's Journal.spec" del /q "Pine's Journal.spec"

set "ASSET_ARGS="
if exist "assets" set "ASSET_ARGS=--add-data assets;assets"

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "Pine's Journal" ^
  --icon "app_icon.ico" ^
  --add-data "app_icon.ico;." ^
  %ASSET_ARGS% ^
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
goto :error

:usage
echo Uso: PinesJournal.bat [setup^|run^|build]
pause
exit /b 1

:error
echo.
echo A operacao falhou. Verifique as mensagens acima.
pause
exit /b 1
