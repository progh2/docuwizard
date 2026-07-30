@echo off
REM DocuWizard — Windows
REM 사용: run.cmd 더블클릭 또는 터미널에서 run.cmd
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYLAUNCHER=1"
) else (
  set "PYLAUNCHER=0"
  where python >nul 2>&1
  if errorlevel 1 (
    echo [오류] Python 3이 PATH에 없습니다. https://www.python.org/downloads/ 에서 설치하세요.
    echo 설치 시 "Add python.exe to PATH"를 체크하세요.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [안내] 가상환경(.venv)을 만들고 패키지를 설치합니다…
  if "%PYLAUNCHER%"=="1" (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 (
    echo [오류] 가상환경 생성에 실패했습니다.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
  if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다.
    pause
    exit /b 1
  )
)

echo DocuWizard 시작…
".venv\Scripts\python.exe" -m docuwizard
set EXITCODE=%ERRORLEVEL%
if not %EXITCODE%==0 (
  echo.
  echo [오류] 종료 코드 %EXITCODE%. Ollama 실행 여부와 의존성 설치를 확인하세요.
  pause
)
exit /b %EXITCODE%
