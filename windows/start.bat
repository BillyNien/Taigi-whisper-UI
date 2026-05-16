@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ================================================
echo   Taigi-whisper-UI - 混合語音辨識工具
echo ================================================
echo.

REM 檢查 Python 是否安裝
python --version > nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python！
    echo.
    echo 請先安裝 Python 3.10 或更新版本：
    echo https://www.python.org/downloads/
    echo.
    echo 安裝時請勾選 "Add Python to PATH"
    pause
    exit /b 1
)

REM 取得 Python 版本號（主版本.次版本）
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)

if %PYMAJ% LSS 3 (
    echo [錯誤] Python 版本太舊（目前：%PYVER%），需要 3.10 或更新版本
    pause
    exit /b 1
)
if %PYMAJ% EQU 3 if %PYMIN% LSS 10 (
    echo [錯誤] Python 版本太舊（目前：%PYVER%），需要 3.10 或更新版本
    pause
    exit /b 1
)

echo [OK] Python %PYVER% 已確認

REM 建立虛擬環境（若尚未存在）
if not exist "venv\" (
    echo 正在建立虛擬環境...
    python -m venv venv
    if errorlevel 1 (
        echo [錯誤] 無法建立虛擬環境
        pause
        exit /b 1
    )
    echo [OK] 虛擬環境建立完成
)

REM 啟動安裝程式 / 主程式
venv\Scripts\python.exe setup_and_run.py
