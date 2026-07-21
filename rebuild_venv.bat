@echo off
cd /d "%~dp0"
echo ============================================
echo   Rebuild venv from scratch
echo ============================================
echo.

echo [1/6] Removing old venv...
rmdir /s /q "backend\.venv" 2>nul
echo         Done

echo.
echo [2/6] Creating fresh venv with Python 3.11...
set "PYTHON="
for %%p in (python python3 "%LOCALAPPDATA%\Programs\Python\Python311\python.exe") do (
    if not defined PYTHON (
        if exist %%p set "PYTHON=%%p"
    )
)
if not defined PYTHON (
    echo [ERROR] Python 3.11 not found
    pause
    exit /b 1
)
%PYTHON% --version
%PYTHON% -m venv "backend\.venv"
echo         Venv created

echo.
echo [3/6] Installing dependencies (Flask, ChromaDB, LLM, etc.)...
backend\.venv\Scripts\pip.exe install -r backend\requirements.txt --disable-pip-version-check
if errorlevel 1 (
    echo [WARN] requirements.txt install had issues, continuing...
)

echo.
echo [4/6] Installing PaddleOCR 2.x (OCR engine)...
backend\.venv\Scripts\pip.exe install "paddleocr>=2.7,<3.0" "paddlepaddle>=2.6,<3.0" "opencv-python>=4.9.0" --disable-pip-version-check

echo.
echo [5/6] Fixing albumentations (no torch)...
backend\.venv\Scripts\pip.exe install albumentations --no-deps --disable-pip-version-check 2>nul
if exist "backend\.venv\Lib\site-packages\torch" rmdir /s /q "backend\.venv\Lib\site-packages\torch"
echo         Done

echo.
echo [6/6] Verifying PaddleOCR...
backend\.venv\Scripts\python.exe -c "import paddleocr; from paddleocr import PaddleOCR; print('PaddleOCR version:', paddleocr.__version__); print('OK')"

if errorlevel 1 (
    echo [ERROR] PaddleOCR import failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Venv ready! Run start.bat to launch.
echo ============================================
pause
