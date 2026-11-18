@echo off
rem POC del dia 1: usa triscan en un proyecto real, paso a paso. Al final abre un resumen en el navegador.
chcp 65001 >nul
cd /d "%~dp0.."
python -m pip install -e . -q
if errorlevel 1 (
  echo No pude instalar. Revisa que Python este instalado: python --version
  pause
  exit /b 1
)
python scripts\poc_dia1.py
pause
