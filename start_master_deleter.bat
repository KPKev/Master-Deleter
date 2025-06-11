@echo off
title Master Deleter - Supervised Launch
echo.
echo =================================
echo   Master Deleter Hypervisor
echo =================================
echo.
echo Starting with automatic crash recovery...
echo Press Ctrl+C to stop
echo.

python launch_supervised.py

echo.
echo Master Deleter has been stopped.
pause