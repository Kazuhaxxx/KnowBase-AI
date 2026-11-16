@echo off
title KnowBase AI Stopper
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_demo.ps1"
