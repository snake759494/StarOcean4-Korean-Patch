@echo off
cd /d "%~dp0"
python -X utf8 safe_build_and_apply.py
:done
pause
