@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    REM set "INPUT_FILE=input.txt"
	echo Provide file name or directory path as argument
	echo.
	echo Example:
	echo   %0 F:\Pentest\logs\
	pause
	exit /b 1
) else (
    set "INPUT_FILE=%~1"
)

pushd %~dp0

set PYTHON_PATH=python.exe
set SCRIPT_PATH=duplicate-line-identifier.py
set "OPTIONS="

set OPTIONS=!OPTIONS! --disable-line-number
set OPTIONS=!OPTIONS! --disable-tags
set OPTIONS=!OPTIONS! --keep-empty-duplicates
REM set OPTIONS=!OPTIONS! --case-sensitive

set CMD=!PYTHON_PATH! "!SCRIPT_PATH!" "!INPUT_FILE!"
if defined OPTIONS set CMD=!CMD! !OPTIONS!


echo COMMAND: !CMD!
echo.
echo ---------------------------------- TASK STARTED ------------------------------------
!CMD!
echo ---------------------------------- TASK COMPELTED ----------------------------------
echo.

pause

