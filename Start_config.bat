@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title AgentSelfSave
echo Working directory: %cd%
echo Asks agent name in this window.
echo Database password: a window titled AgentSelfSave. Check the taskbar if you miss it.
echo First-save paste: a second window so you can Copy all. Not written to a file.
echo Creates .secrets\secrets_Name.txt
echo Creates .cursor\rules from the house rules, plus Name.mdc (revive prompt).
echo Port 3306 is closed. Use phpMyAdmin. It will not work.
echo.

set "PYEXE=python"
set "PYARGS="
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo python was not found on PATH.
    echo Open a terminal in this folder and run: python prepare_agent.py
    echo.
    pause
    exit /b 1
  )
  set "PYEXE=py"
  set "PYARGS=-3"
)

%PYEXE% %PYARGS% -u prepare_agent.py
echo.
echo Exit code: %ERRORLEVEL%
echo.
pause
