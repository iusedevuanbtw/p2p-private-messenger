@echo off
echo ============================================
echo   P2P Messenger VPN - Windows Setup
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found.
echo.

set INSTALL_DIR=C:\p2p_messenger_vpn
set VENV_DIR=C:\p2pvpn_env

echo Creating virtual environment...
python -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Copying project files...
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
xcopy /E /I "%~dp0" "%INSTALL_DIR%"

echo Creating launcher...
echo @echo off > "%INSTALL_DIR%\run.bat"
echo "%VENV_DIR%\Scripts\python.exe" "%INSTALL_DIR%\main.py" >> "%INSTALL_DIR%\run.bat"
echo pause >> "%INSTALL_DIR%\run.bat"

echo.
echo ============================================
echo   Installation complete.
echo   Run: %INSTALL_DIR%\run.bat
echo ============================================
pause
