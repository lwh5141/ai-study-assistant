@echo off
title AI Study Assistant - Launcher
cd /d "%~dp0"

set "VENV_DIR=backend\.venv"
set "REQUIREMENTS=backend\requirements.txt"

echo.
echo ============================================
echo   AI Study Assistant - Launcher
echo ============================================
echo.

:: ================================================================
:: [1/7] Check Node.js
:: ================================================================
echo [1/7] Checking Node.js...

where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Node.js not found. Install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo          Node.js %%i [OK]

call npm --version >nul 2>&1
if errorlevel 1 (
    echo   [WARN] npm may not be working correctly
)

:: ================================================================
:: [2/7] Check Python
:: ================================================================
echo [2/7] Checking Python...

set "PYTHON="

for %%p in (python python3 py) do (
    if not defined PYTHON (
        %%~p --version >nul 2>&1
        if not errorlevel 1 set "PYTHON=%%~p"
    )
)

if not defined PYTHON (
    for %%p in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
    ) do (
        if not defined PYTHON (
            if exist %%p set "PYTHON=%%p"
        )
    )
)

if not defined PYTHON (
    echo   [ERROR] Python 3.11+ not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do echo          %%i [OK]

:: ================================================================
:: [3/7] Setup backend venv
:: ================================================================
echo [3/7] Setting up backend venv...

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo   [INFO] Creating virtual environment, please wait...
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo         venv created [OK]
) else (
    echo         venv [OK]
)

set "VPYTHON=%VENV_DIR%\Scripts\python.exe"
set "VPIP=%VENV_DIR%\Scripts\pip.exe"

:: ================================================================
:: [4/7] Install backend dependencies
:: ================================================================
echo [4/7] Installing backend dependencies...

if not exist "%VENV_DIR%\.deps_installed" (
    echo   [INFO] Installing packages, please wait...
    echo.
    "%VPIP%" install -r "%REQUIREMENTS%" --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo   [INFO] Standard install failed, trying fallback...
        "%VPIP%" install Flask Flask-SQLAlchemy Flask-Migrate Flask-CORS python-dotenv PyMuPDF python-pptx python-docx markdown openai sentence-transformers socksio --disable-pip-version-check
        "%VPIP%" install chromadb --only-binary=chroma-hnswlib --disable-pip-version-check
    )

    "%VPYTHON%" -c "import flask" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Dependencies may be incomplete, launch may fail
    ) else (
        echo. > "%VENV_DIR%\.deps_installed"
        echo         Dependencies installed [OK]
    )
) else (
    echo         Dependencies [OK]
)

:: ================================================================
:: [5/7] Check config file
:: ================================================================
echo [5/7] Checking config file...

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy "backend\.env.example" "backend\.env" >nul
        echo   [WARN] backend\.env was created from .env.example
        echo.
        echo   ==========================================
        echo   Before proceeding, open backend\.env and set:
        echo.
        echo   LLM_API_KEY=sk-your-deepseek-key
        echo   EMBEDDING_API_KEY=sk-your-bailian-key
        echo.
        echo   DeepSeek : https://platform.deepseek.com
        echo   Bailian  : https://bailian.console.aliyun.com
        echo   ==========================================
        echo.
        echo   Re-run this script after configuring keys.
        pause
        exit /b 0
    )
) else (
    echo         Config [OK]
)

:: ================================================================
:: [6/7] Check frontend dependencies
:: ================================================================
echo [6/7] Checking frontend dependencies...

if not exist "node_modules\" (
    echo   [WARN] node_modules not found, installing...
    echo.
    call npm install
    if errorlevel 1 (
        echo.
        echo   [ERROR] Frontend dependency install failed
        pause
        exit /b 1
    )
    echo.
    echo         Frontend deps installed [OK]
) else (
    echo         Frontend deps [OK]
)

:: ================================================================
:: [7/7] Check port availability
:: ================================================================
echo [7/7] Checking port availability...

set "BK_PORT_FREE=1"
set "FE_PORT_FREE=1"

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 set "BK_PORT_FREE=0"

netstat -ano | findstr ":5173 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 set "FE_PORT_FREE=0"

if "%BK_PORT_FREE%"=="0" (
    echo   [WARN] Port 8000 is in use (backend may already be running)
) else (
    echo         Port 8000 [free]
)

if "%FE_PORT_FREE%"=="0" (
    echo   [WARN] Port 5173 is in use (frontend may already be running)
) else (
    echo         Port 5173 [free]
)

:: ================================================================
:: Launch services
:: ================================================================
echo.
echo ============================================
echo   Checks passed, launching services...
echo ============================================
echo.

:: --- Launch backend ---
echo [Launch] Backend (http://localhost:8000)

set "BK_LAUNCH_CMD=title AI-Study-Backend && echo ============================================ && echo   Backend starting... && echo   Health: http://localhost:8000/api/v1/health && echo   Press Ctrl+C to stop && echo ============================================ && echo. && %VPYTHON% backend\run.py"

if "%BK_PORT_FREE%"=="0" (
    echo         Port 8000 already listening, skipping
    set "BK_ALREADY_RUNNING=1"
) else (
    start "AI-Study-Backend" /d "%~dp0" cmd /k "%BK_LAUNCH_CMD%"
    echo         Backend window launched [OK]
)

:: --- Wait for backend ---
echo [Wait] Waiting for backend...

set "BK_READY=0"
if defined BK_ALREADY_RUNNING set "BK_READY=1"

if "%BK_READY%"=="0" (
    for /l %%i in (1,1,20) do (
        powershell -Command "try { (Invoke-WebRequest 'http://localhost:8000/api/v1/health' -TimeoutSec 2).StatusCode; exit 0 } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 (
            set "BK_READY=1"
            goto :bk_ready
        )
        timeout /t 2 /nobreak >nul
    )
)

:bk_ready
if "%BK_READY%"=="1" (
    echo         Backend ready [OK]
) else (
    echo   [WARN] Backend startup timeout, continuing...
)

:: --- Launch frontend ---
echo.
echo [Launch] Frontend (http://localhost:5173)

if "%FE_PORT_FREE%"=="0" (
    echo         Port 5173 already listening, skipping
) else (
    start "AI-Study-Frontend" /d "%~dp0" cmd /k "title AI-Study-Frontend && echo Frontend starting... && npm run dev"
    echo         Frontend window launched [OK]
)

:: --- Wait for frontend ---
echo [Wait] Waiting for frontend...

set "FE_READY=0"
if "%FE_PORT_FREE%"=="0" set "FE_READY=1"

if "%FE_READY%"=="0" (
    for /l %%i in (1,1,10) do (
        powershell -Command "try { (Invoke-WebRequest 'http://localhost:5173' -TimeoutSec 2).StatusCode; exit 0 } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 (
            set "FE_READY=1"
            goto :fe_ready
        )
        timeout /t 2 /nobreak >nul
    )
)

:fe_ready

:: ================================================================
:: Done
:: ================================================================
echo.
echo ============================================
echo   Launch complete!
echo ============================================
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   Health   : http://localhost:8000/api/v1/health
echo.
echo   Closing this window will NOT stop the services.
echo   Backend  window title: AI-Study-Backend
echo   Frontend window title: AI-Study-Frontend
echo.
echo ============================================

:: --- Open browser ---
start http://localhost:5173
echo   Browser opened

echo.
pause
