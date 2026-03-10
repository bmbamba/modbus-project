@echo off
title Modbus Build Script
echo ============================================
echo  Modbus App Builder
echo ============================================
echo.

:: Go to the folder where this .bat file lives
cd /d "%~dp0"

echo [Step 1/4] Installing required packages...
py -m pip install pyinstaller pillow pyside6 pymodbus --quiet
echo  Done.
echo.

echo [Step 2/4] Generating icons...
py generate_icons.py
echo.

echo [Step 3/4] Building ModbusServer.exe...
py -m PyInstaller --noconfirm --clean --windowed ^
    --name ModbusServer ^
    --icon server_icon.ico ^
    --add-data "setpoints.py;." ^
    --add-data "app_icons.py;." ^
    --hidden-import pymodbus ^
    --hidden-import pymodbus.server ^
    --hidden-import pymodbus.datastore ^
    --hidden-import pymodbus.datastore.store ^
    --hidden-import pymodbus.framer ^
    --hidden-import pymodbus.device ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    server.py
echo.

echo [Step 4/4] Building ModbusClient.exe...
py -m PyInstaller --noconfirm --clean --windowed ^
    --name ModbusClient ^
    --icon client_icon.ico ^
    --add-data "setpoints.py;." ^
    --add-data "app_icons.py;." ^
    --hidden-import pymodbus ^
    --hidden-import pymodbus.client ^
    --hidden-import pymodbus.client.tcp ^
    --hidden-import pymodbus.framer ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    client.py
echo.

echo ============================================
echo  BUILD COMPLETE
echo ============================================
echo.
echo  Test your apps:
echo    dist\ModbusServer\ModbusServer.exe
echo    dist\ModbusClient\ModbusClient.exe
echo.
echo  Then open Inno Setup and compile:
echo    server_installer.iss
echo    client_installer.iss
echo.
pause
