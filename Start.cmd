@echo off
cd /d "%~dp0"
py -3 samsung_brightness.py
if errorlevel 1 (
  echo.
  echo Could not start. Install Python 3.10+ with Tcl/Tk and the py launcher.
  pause
)
